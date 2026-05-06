# Technical Report

## Summary

The bridge works by piggybacking on Home Assistant's official Roborock integration after that integration has already authenticated and connected to the Q-series robot. The bridge does not perform Roborock account login, does not request email codes, and does not store Roborock credentials.

The important discovery is that the official integration runtime contains a Q10 API object with access to the robot's Q10/B01 command channel. Sending the `COMMON / MULTI_MAP` command and listening to the channel stream returns binary map and trace packets that can be decoded independently.

## High-Level Architecture

```text
Home Assistant official Roborock integration
  |
  | authenticated Q10 runtime coordinator
  v
Roborock Q10 Map Bridge custom integration
  |
  | COMMON / MULTI_MAP list/get
  v
Q10 channel stream
  |
  | binary packets
  v
Q10 parser
  |
  | trace points + map metadata
  v
Transparent PNG camera overlay + debug sensors
  |
  v
Home Assistant floorplan card
```

## Why Reusing HA Runtime Matters

The Q-series login path can be rate-limited and awkward to reproduce outside HA. If Home Assistant already controls the robot, the authenticated connection already exists. The custom bridge can use that existing runtime and avoid duplicating account login.

The bridge searches HA's Roborock config entries:

```python
for config_entry in hass.config_entries.async_entries("roborock"):
    runtime_data = getattr(config_entry, "runtime_data", None)
    candidates.extend(getattr(runtime_data, "b01_q10", []) or [])
```

For a matched Q10 coordinator, the bridge uses:

```python
api = getattr(coordinator, "api", None)
```

That `api` object has:

- a command sender.
- a channel with `subscribe_stream()`.
- access to the Q10 protocol helpers already installed with HA's Roborock integration.

## Command Path

The working request path is:

```python
await api.command.send(
    B01_Q10_DP.COMMON,
    params={str(B01_Q10_DP.MULTI_MAP.code): {"op": "get", "id": map_id}},
)
```

If the map ID is unknown, first request:

```python
await api.command.send(
    B01_Q10_DP.COMMON,
    params={str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
)
```

Decoded RPC responses from the list request include map IDs under the `MULTI_MAP` payload.

## Packet Types Observed

### Full Map Packet

- Prefix: `01 01`
- Contains:
  - map ID.
  - map width.
  - compressed layout block.
  - room metadata records.
  - compressed binary mask block.
  - short trailing data not fully decoded yet.

The parser currently extracts:

- map ID.
- width and inferred height.
- layout bytes.
- room records.
- room names.
- room pixel counts.
- room order/type hints.
- mask bytes.
- tail bytes.

### Trace Packet

- Prefix: `02 01`
- Header length: 18 bytes.
- Body format:
  - repeated coordinate pairs.
  - each point is two signed big-endian 16-bit integers.

The parser currently extracts:

- all trace points.
- first and last points.
- current robot position from the last point.
- trace bounds.
- header hints.
- SHA-256 of the raw trace packet for change detection/debugging.

## Rendering Approach

The bridge does not render the full Roborock app map in HA. Instead, it renders a transparent overlay aligned to an existing floorplan.

The conversion is:

1. Normalize a trace point into configured trace bounds.
2. Flip X/Y if needed.
3. Fit into a configured percentage box on the floorplan.
4. Preserve source aspect ratio where available.
5. Rotate around the configured box center if needed.
6. Draw line and robot marker.
7. Clip to the calibrated box.

This makes the output useful for custom floorplan dashboards, even if the Roborock map shape does not exactly match the house render.

## HA Entities

For each configured robot, the bridge creates:

- `camera.<robot_slug>_trace_overlay`
  - transparent PNG overlay.
- `sensor.<robot_slug>_bridge_state`
  - bridge status.
- `sensor.<robot_slug>_floorplan_x`
  - current X percentage/pixel-derived location.
- `sensor.<robot_slug>_floorplan_y`
  - current Y percentage/pixel-derived location.
- `sensor.<robot_slug>_trace_point_count`
  - point count in the current trace.

## Fade Behavior

The bridge keeps only the latest in-memory overlay per robot. When the robot is idle/docked:

1. The last trace is retained.
2. `bridge_state` becomes `idle_fading`.
3. Overlay opacity decreases for 60 seconds.
4. The retained trace is cleared.
5. The camera returns a fully transparent PNG.

No permanent path archive is created by the bridge.

## What Is Not Yet Decoded

The official renderer has options for obstacles, no-go zones, virtual walls, mop paths, predicted paths, and more. The Q10 packets we decoded so far prove map, rooms, mask, trace, and robot position. Other layers need controlled before/after captures.

The most promising next items are:

- cleaned area from the binary mask.
- room geometry and labels.
- virtual walls.
- no-go zones.
- no-mop zones.
- zone-clean geometry.

The least likely items are:

- obstacle photos.
- ignored obstacle photos.
- predicted path.

Those may be model-specific, app-side, or absent from this robot's Q10 packets.

## Files Of Interest

- `q10_client.py`
  - Finds the existing HA Roborock Q10 API and captures map/trace payloads.
- `q10_parser.py`
  - Decodes Q10 map and trace packet formats.
- `calibration.py`
  - Converts robot coordinates to floorplan coordinates.
- `overlay.py`
  - Renders transparent PNG overlays.
- `coordinator.py`
  - Poll loop, state retention, fade-out, and entity data.
- `camera.py`
  - Exposes overlay PNGs to HA.
- `sensor.py`
  - Exposes debug/state sensors.

## Main Integration Risk

This bridge uses Home Assistant/python-roborock internals:

- `config_entry.runtime_data.b01_q10`
- Q10 coordinator shape.
- Q10 API/channel internals.

Those are not a stable public API. A robust upstream implementation should move this logic into python-roborock or Home Assistant's official Roborock integration rather than depending on another integration's runtime internals from a separate custom component.

