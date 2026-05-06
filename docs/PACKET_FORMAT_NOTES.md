# Packet Format Notes

These notes describe the Q10/B01 packets this package currently decodes.

## Packet Dispatch

```python
def q10_packet_type(payload: bytes) -> str | None:
    if payload[:2] == b"\x01\x01":
        return "map"
    if payload[:2] == b"\x02\x01":
        return "trace"
    return None
```

## Map Packet: `01 01`

Observed structure:

| Offset | Type | Meaning |
|---:|---|---|
| `0` | bytes | Packet marker `01 01` |
| `2` | u32be | Map ID |
| `8` | u16le | Layout width |
| `25` | u16be | Declared decoded layout length |
| `27` | u16be | Compressed layout length |
| `29` | bytes | LZ4 block compressed layout |

After inflating the first LZ4 block:

- The beginning is the map layout grid.
- The end contains room metadata records.
- Room data starts with `01 <room_count>`.
- Each room record is currently treated as 47 bytes.

The second compressed block:

- Is found shortly after the layout block.
- Declares the same decoded length as the layout grid.
- Inflates to a binary mask with values currently observed as `0` and `1`.

The map parser keeps tail bytes for future work.

## Room Record

Current decoded fields:

| Field | Notes |
|---|---|
| `id` | `u16be` at record offset `0` |
| `order_hint` | `u16le` at offset `2` |
| `type_hint` | `u16le` at offset `4` |
| `name_length` | byte at offset `26` |
| `name` | ASCII string from offset `27` |
| `pixel_value` | currently `room_id * 4` |
| `pixel_count` | count of `pixel_value` in layout grid |

## Trace Packet: `02 01`

Observed structure:

| Offset | Type | Meaning |
|---:|---|---|
| `0` | bytes | Packet marker `02 01` |
| `0..18` | bytes | Trace header |
| `18..end` | repeated i16be pairs | `x, y` points |

Current decoded header hints:

| Field | Offset | Notes |
|---|---:|---|
| `sequence_hint` | `9` | Useful when choosing latest trace packet |
| `state_hint` | `10` | Signed 16-bit value, not fully decoded |
| `record_hint` | `16` | Unsigned 16-bit value, not fully decoded |

The current robot position is the last decoded point.

## LZ4

The parser uses a small LZ4 block decoder rather than an external dependency. This matches the observed map block format.

## Coordinate System

Trace points are robot/map-space coordinates, not HA floorplan pixels. They need per-install calibration:

- trace min/max bounds.
- optional X/Y flips.
- floorplan box position and size.
- optional rotation.
- source aspect ratio.

