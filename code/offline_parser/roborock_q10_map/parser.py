import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOM_RECORD_LENGTH = 47
LAYOUT_BLOCK_HEADER_OFFSET = 24
LAYOUT_COMPRESSED_OFFSET = 29
TRACE_HEADER_LENGTH = 18


@dataclass(frozen=True)
class RoomRecord:
    id: int
    name: str
    display_name: str
    pixel_value: int
    pixel_count: int
    order_hint: int
    type_hint: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "pixel_value": self.pixel_value,
            "pixel_count": self.pixel_count,
            "order_hint": self.order_hint,
            "type_hint": self.type_hint,
        }


@dataclass(frozen=True)
class LayoutBlock:
    header_offset: int
    compressed_offset: int
    declared_decoded_length: int
    compressed_length: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "header_offset": self.header_offset,
            "compressed_offset": self.compressed_offset,
            "declared_decoded_length": self.declared_decoded_length,
            "compressed_length": self.compressed_length,
        }


@dataclass(frozen=True)
class MaskBlock:
    header_offset: int
    declared_decoded_length: int
    compressed_length: int
    values: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "header_offset": self.header_offset,
            "declared_decoded_length": self.declared_decoded_length,
            "compressed_length": self.compressed_length,
            "values": list(self.values),
        }


@dataclass(frozen=True)
class Q10Map:
    source: str
    sha256: str
    map_id: int
    width: int
    height: int
    layout: bytes
    mask: bytes
    tail: bytes
    layout_block: LayoutBlock
    mask_block: MaskBlock
    rooms: tuple[RoomRecord, ...]

    @property
    def layout_pixels(self) -> int:
        return len(self.layout)

    def to_summary(self) -> dict[str, Any]:
        return {
            "file": self.source,
            "sha256": self.sha256,
            "map_id": self.map_id,
            "width": self.width,
            "height": self.height,
            "layout_pixels": self.layout_pixels,
            "layout_block": self.layout_block.to_dict(),
            "mask_block": self.mask_block.to_dict(),
            "tail_length": len(self.tail),
            "tail_hex": self.tail.hex(),
            "room_count": len(self.rooms),
            "rooms": [room.to_dict() for room in self.rooms],
        }


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def to_list(self) -> list[int]:
        return [self.x, self.y]


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
        return {
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
        }


@dataclass(frozen=True)
class TracePacket:
    source: str
    sha256: str
    length: int
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
    def state_hint(self) -> int:
        return read_i16be(self.header, 10)

    @property
    def record_hint(self) -> int:
        return read_u16be(self.header, 16)

    def to_summary(self, include_points: bool = True) -> dict[str, Any]:
        summary = {
            "file": self.source,
            "sha256": self.sha256,
            "length": self.length,
            "header_hex": self.header.hex(),
            "packet_type": self.header[:2].hex(),
            "sequence_hint": self.sequence_hint,
            "state_hint": self.state_hint,
            "record_hint": self.record_hint,
            "point_count": len(self.points),
            "bounds": self.bounds.to_dict(),
            "first_points": [point.to_list() for point in self.points[:8]],
            "last_points": [point.to_list() for point in self.points[-8:]],
        }
        if include_points:
            summary["points"] = [point.to_list() for point in self.points]
        return summary


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


def parse_rooms(room_data: bytes, layout: bytes) -> tuple[RoomRecord, ...]:
    rooms = []
    room_count = room_data[1]
    for index in range(room_count):
        start = 2 + index * ROOM_RECORD_LENGTH
        record = room_data[start : start + ROOM_RECORD_LENGTH]
        room_id = read_u16be(record, 0)
        name_length = record[26]
        name = record[27 : 27 + name_length].decode("ascii", errors="replace")
        pixel_value = room_id * 4
        rooms.append(
            RoomRecord(
                id=room_id,
                name=name,
                display_name=name.removeprefix("rr_").replace("_", " "),
                pixel_value=pixel_value,
                pixel_count=layout.count(pixel_value),
                order_hint=read_u16le(record, 2),
                type_hint=read_u16le(record, 4),
            )
        )
    return tuple(rooms)


def find_mask_block(payload: bytes, start: int, expected_length: int) -> tuple[int, int, bytes, bytes]:
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
            return offset, compressed_length, decoded, payload[body_end:]
    raise ValueError("Could not find Q10 mask/coverage block")


def decode_map_payload(payload: bytes, source: str = "") -> Q10Map:
    if len(payload) < LAYOUT_COMPRESSED_OFFSET or payload[:2] != b"\x01\x01":
        raise ValueError("Payload does not look like a Q10 full map packet")

    map_id = int.from_bytes(payload[2:6], "big")
    width = read_u16le(payload, 8)
    declared_layout_length = read_u16be(payload, 25)
    compressed_layout_length = read_u16be(payload, 27)
    layout_end = LAYOUT_COMPRESSED_OFFSET + compressed_layout_length
    decoded_layout = decode_lz4_block(payload[LAYOUT_COMPRESSED_OFFSET:layout_end])
    if len(decoded_layout) != declared_layout_length:
        raise ValueError(
            f"Decoded layout length {len(decoded_layout)} did not match declared length {declared_layout_length}"
        )

    height, layout, room_data = infer_layout(decoded_layout, width)
    rooms = parse_rooms(room_data, layout)
    mask_offset, compressed_mask_length, mask, tail = find_mask_block(payload, layout_end, len(layout))

    return Q10Map(
        source=source,
        sha256=hashlib.sha256(payload).hexdigest(),
        map_id=map_id,
        width=width,
        height=height,
        layout=layout,
        mask=mask,
        tail=tail,
        layout_block=LayoutBlock(
            header_offset=LAYOUT_BLOCK_HEADER_OFFSET,
            compressed_offset=LAYOUT_COMPRESSED_OFFSET,
            declared_decoded_length=declared_layout_length,
            compressed_length=compressed_layout_length,
        ),
        mask_block=MaskBlock(
            header_offset=mask_offset,
            declared_decoded_length=len(mask),
            compressed_length=compressed_mask_length,
            values=tuple(sorted(set(mask))),
        ),
        rooms=rooms,
    )


def decode_map_file(path: Path) -> Q10Map:
    return decode_map_payload(path.read_bytes(), source=str(path))


def parse_trace_payload(payload: bytes, source: str = "") -> TracePacket:
    if len(payload) < TRACE_HEADER_LENGTH:
        raise ValueError("Payload is too short for a Q10 trace packet")
    if payload[:2] != b"\x02\x01":
        raise ValueError("Payload does not look like a Q10 trace packet")
    if (len(payload) - TRACE_HEADER_LENGTH) % 4:
        raise ValueError("Trace point payload is not divisible into 4-byte coordinate pairs")

    points = []
    for offset in range(TRACE_HEADER_LENGTH, len(payload), 4):
        points.append(Point(read_i16be(payload, offset), read_i16be(payload, offset + 2)))

    return TracePacket(
        source=source,
        sha256=hashlib.sha256(payload).hexdigest(),
        length=len(payload),
        header=payload[:TRACE_HEADER_LENGTH],
        points=tuple(points),
    )


def parse_trace_file(path: Path) -> TracePacket:
    return parse_trace_payload(path.read_bytes(), source=str(path))
