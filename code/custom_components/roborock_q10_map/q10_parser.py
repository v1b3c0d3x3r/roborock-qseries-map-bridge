from __future__ import annotations

import hashlib
from dataclasses import dataclass


ROOM_RECORD_LENGTH = 47
LAYOUT_BLOCK_HEADER_OFFSET = 24
LAYOUT_COMPRESSED_OFFSET = 29
TRACE_HEADER_LENGTH = 18


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class Bounds:
    min_x: int | None
    max_x: int | None
    min_y: int | None
    max_y: int | None

    @property
    def width(self) -> int:
        if self.min_x is None or self.max_x is None:
            return 0
        return self.max_x - self.min_x

    @property
    def height(self) -> int:
        if self.min_y is None or self.max_y is None:
            return 0
        return self.max_y - self.min_y

    def to_dict(self) -> dict[str, int | None]:
        return {"min_x": self.min_x, "max_x": self.max_x, "min_y": self.min_y, "max_y": self.max_y}


@dataclass(frozen=True)
class TracePacket:
    sha256: str
    header: bytes
    points: tuple[Point, ...]

    @property
    def bounds(self) -> Bounds:
        if not self.points:
            return Bounds(None, None, None, None)
        xs = [point.x for point in self.points]
        ys = [point.y for point in self.points]
        return Bounds(min(xs), max(xs), min(ys), max(ys))

    @property
    def sequence_hint(self) -> int:
        return self.header[9]

    @property
    def latest_point(self) -> Point | None:
        return self.points[-1] if self.points else None


@dataclass(frozen=True)
class Q10Map:
    sha256: str
    map_id: int
    width: int
    height: int
    layout: bytes
    mask: bytes
    tail: bytes


def read_u16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def read_i16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big", signed=True)


def read_u16le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def decode_lz4_block(data: bytes) -> bytes:
    src_index = 0
    output = bytearray()

    def read_length(length: int) -> int:
        nonlocal src_index
        if length != 0x0F:
            return length
        while True:
            if src_index >= len(data):
                raise ValueError("Unexpected EOF while reading LZ4 length")
            part = data[src_index]
            src_index += 1
            length += part
            if part != 0xFF:
                return length

    while True:
        if src_index >= len(data):
            raise ValueError("Unexpected EOF while reading LZ4 token")
        token = data[src_index]
        src_index += 1

        literal_length = read_length((token >> 4) & 0x0F)
        literals_end = src_index + literal_length
        if literals_end > len(data):
            raise ValueError("Unexpected EOF while reading LZ4 literals")
        output.extend(data[src_index:literals_end])
        src_index = literals_end

        if src_index == len(data):
            return bytes(output)
        if src_index + 2 > len(data):
            raise ValueError("Unexpected EOF while reading LZ4 offset")

        offset = data[src_index] | (data[src_index + 1] << 8)
        src_index += 2
        if offset == 0 or offset > len(output):
            raise ValueError("Invalid LZ4 back-reference offset")

        match_length = read_length(token & 0x0F) + 4
        for _ in range(match_length):
            output.append(output[-offset])


def infer_layout(decoded: bytes, width: int) -> tuple[int, bytes, bytes]:
    for room_count in range(1, 32):
        room_data_length = 2 + room_count * ROOM_RECORD_LENGTH
        area = len(decoded) - room_data_length
        if area <= 0 or area % width:
            continue
        room_data = decoded[area:]
        if len(room_data) >= 2 and room_data[0] == 1 and room_data[1] == room_count:
            return area // width, decoded[:area], room_data
    raise ValueError("Could not infer Q10 layout dimensions / room records")


def find_mask_block(payload: bytes, start: int, expected_length: int) -> tuple[int, bytes, bytes]:
    for offset in range(start, min(len(payload) - 4, start + 16)):
        declared_length = read_u16be(payload, offset)
        compressed_length = read_u16be(payload, offset + 2)
        if declared_length != expected_length:
            continue
        body_start = offset + 4
        body_end = body_start + compressed_length
        if compressed_length <= 0 or body_end > len(payload):
            continue
        decoded = decode_lz4_block(payload[body_start:body_end])
        if len(decoded) == expected_length:
            return offset, decoded, payload[body_end:]
    raise ValueError("Could not find Q10 mask/coverage block")


def decode_map_payload(payload: bytes) -> Q10Map:
    if len(payload) < LAYOUT_COMPRESSED_OFFSET or payload[:2] != b"\x01\x01":
        raise ValueError("Payload does not look like a Q10 full map packet")
    map_id = int.from_bytes(payload[2:6], "big")
    width = read_u16le(payload, 8)
    declared_layout_length = read_u16be(payload, 25)
    compressed_layout_length = read_u16be(payload, 27)
    layout_end = LAYOUT_COMPRESSED_OFFSET + compressed_layout_length
    decoded_layout = decode_lz4_block(payload[LAYOUT_COMPRESSED_OFFSET:layout_end])
    if len(decoded_layout) != declared_layout_length:
        raise ValueError("Decoded layout length did not match declared length")
    height, layout, _room_data = infer_layout(decoded_layout, width)
    _mask_offset, mask, tail = find_mask_block(payload, layout_end, len(layout))
    return Q10Map(hashlib.sha256(payload).hexdigest(), map_id, width, height, layout, mask, tail)


def parse_trace_payload(payload: bytes) -> TracePacket:
    if len(payload) < TRACE_HEADER_LENGTH:
        raise ValueError("Payload is too short for a Q10 trace packet")
    if payload[:2] != b"\x02\x01":
        raise ValueError("Payload does not look like a Q10 trace packet")
    if (len(payload) - TRACE_HEADER_LENGTH) % 4:
        raise ValueError("Trace point payload is not divisible into 4-byte coordinate pairs")
    points = []
    for offset in range(TRACE_HEADER_LENGTH, len(payload), 4):
        points.append(Point(read_i16be(payload, offset), read_i16be(payload, offset + 2)))
    return TracePacket(hashlib.sha256(payload).hexdigest(), payload[:TRACE_HEADER_LENGTH], tuple(points))


def q10_packet_type(payload: bytes) -> str | None:
    if payload[:2] == b"\x01\x01":
        return "map"
    if payload[:2] == b"\x02\x01":
        return "trace"
    return None
