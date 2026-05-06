# Step-By-Step Implementation

These are the successful steps only.

## 1. Start From Home Assistant's Roborock Integration

- Add the robots to the Roborock mobile app.
- Add the official Roborock integration in Home Assistant.
- Confirm each robot has a working `vacuum.*` entity.
- Confirm normal vacuum commands work in HA.

## 2. Create A Custom HA Integration

- Create `custom_components/roborock_q10_map`.
- Add a `manifest.json` with dependency `"roborock"`.
- Add a config flow that accepts:
  - comma-separated robot entity IDs.
  - poll interval in seconds.
- Add platforms:
  - `sensor`
  - `camera`

## 3. Reuse The Official Roborock Runtime

- At update time, inspect HA's loaded Roborock config entries:
  - `hass.config_entries.async_entries("roborock")`
- Read each entry's runtime data.
- For Q10/B01 devices, look under:
  - `config_entry.runtime_data.b01_q10`
- Match the bridge robot entity to the official integration coordinator.
- Prefer matching by entity registry unique ID.
- Fall back to friendly name if needed.
- Extract the already-authenticated `api` object from that coordinator.

## 4. Request Q10 Map Data

- Import:
  - `B01_Q10_DP` from `roborock.data.b01_q10.b01_q10_code_mappings`
  - `decode_rpc_response` from `roborock.protocols.b01_q10_protocol`
- Subscribe to the Q10 channel stream before sending the command:
  - `channel.subscribe_stream()`
- Send a map list request if no map ID is known:
  - command: `B01_Q10_DP.COMMON`
  - params: `{str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}}`
- Extract map IDs from decoded RPC messages under the `MULTI_MAP` data list.
- Send a map get request:
  - command: `B01_Q10_DP.COMMON`
  - params: `{str(B01_Q10_DP.MULTI_MAP.code): {"op": "get", "id": map_id}}`
- Keep collecting stream messages for a short window, usually 3 to 5 seconds.

## 5. Separate Binary Packets

- Treat payloads beginning with `01 01` as map packets.
- Treat payloads beginning with `02 01` as trace/path packets.
- Ignore other messages unless they decode as normal RPC responses.

## 6. Decode Full Map Packets

- Read the map ID from bytes `2..6` as big-endian integer.
- Read width from byte offset `8` as little-endian `u16`.
- Read the compressed layout length from the layout block header.
- Inflate the layout block with LZ4 block decoding.
- Infer height by finding the room metadata block at the end of the inflated layout.
- Parse room records.
- Find the second compressed block with the same decoded length as the layout.
- Inflate it as the binary map mask.
- Keep the remaining tail bytes for future feature decoding.

## 7. Decode Trace Packets

- Require prefix `02 01`.
- Treat the first 18 bytes as the trace header.
- Decode the remainder as repeated 4-byte coordinate pairs:
  - signed big-endian `i16 x`
  - signed big-endian `i16 y`
- Use the final point as the current robot position.
- Use all points as the live path.
- Use min/max x/y as observed trace bounds.

## 8. Render A Transparent Overlay

- Create a transparent RGBA image matching the HA floorplan dimensions.
- Convert Q10 trace coordinates into floorplan pixels using:
  - configured trace bounds.
  - configured floorplan box percentage.
  - optional X/Y flip.
  - optional rotation.
- Draw the trace line.
- Draw a robot marker at the final point.
- Clip rendering to the calibrated floorplan box polygon.
- Return the PNG bytes from a Home Assistant `Camera` entity.

## 9. Expose Debug Sensors

- Bridge state:
  - `waiting_for_roborock`
  - `ok`
  - `no_live_payload`
  - `idle`
  - `idle_fading`
  - `error`
- Floorplan X/Y.
- Trace point count.
- Attributes for:
  - latest trace point.
  - live trace bounds.
  - configured trace bounds.
  - map ID.
  - map/trace hashes.
  - binary packet count.
  - message count.
  - retained trace fade state.

## 10. Add It To A Floorplan

- Add the overlay camera as an `image` element in a picture-elements card.
- Set it to cover the same 1920x1080 floorplan coordinate space.
- Give it a lower z-index than normal icons and glows.
- Calibrate the overlay box until the trace matches the real floorplan.

## 11. Handle End Of Clean

- Keep the most recent path in memory while the robot is cleaning.
- When the robot becomes docked/idle, retain the final path briefly.
- Fade it out over 60 seconds.
- Clear the retained trace and transparent overlay after the fade.

