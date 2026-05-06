# Example Entity Output

For robot entity:

```text
vacuum.example_q10_downstairs
```

Expected bridge entities:

```text
camera.vacuum_example_q10_downstairs_trace_overlay
sensor.vacuum_example_q10_downstairs_bridge_state
sensor.vacuum_example_q10_downstairs_floorplan_x
sensor.vacuum_example_q10_downstairs_floorplan_y
sensor.vacuum_example_q10_downstairs_trace_point_count
```

Useful sensor attributes:

```text
latest_trace_point
trace_bounds
configured_trace_bounds
live_trace_bounds
retained_trace
trace_fade_seconds_remaining
map_id
map_sha256
trace_sha256
binary_packet_count
message_count
error
```

