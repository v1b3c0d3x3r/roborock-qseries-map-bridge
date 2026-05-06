# Feature Roadmap

This table maps the official Roborock map drawables to what this Q-series bridge currently knows.

| Feature | Status | Notes |
|---|---|---|
| Charger | Workaround | Use calibrated HA floorplan dock icons. Native dock coordinates are not decoded yet. |
| Cleaned area | Promising | A binary mask is decoded and changes between static/live captures. Needs controlled validation. |
| Go-to path | Unknown | Capture during a go-to run and compare trace behavior. |
| Ignored obstacles | Unknown/low | No obvious decoded structure yet. |
| Ignored obstacles with photo | Very unlikely | Likely model/app dependent. |
| Mop path | Unknown | May be same trace path or a separate packet/layer. Needs mop-specific capture. |
| No carpet zones | Unknown | Requires app feature and before/after packet diff. |
| No-go zones | Promising | Add one temporary no-go zone and diff the map tail/payload. |
| No mopping zones | Promising | Add one temporary no-mop zone and diff the map tail/payload. |
| Obstacles | Unknown/low | Needs deliberate obstacle capture and packet diff. |
| Obstacles with photo | Very unlikely | Depends on model support and app exposure. |
| Path | Implemented | Decoded from `02 01` trace packet. |
| Predicted path | Very unlikely | Not seen in decoded packets. May be app-side/model-side only. |
| Vacuum position | Implemented | Last trace point. |
| Virtual walls | Promising | Add one temporary virtual wall and diff the map tail/payload. |
| Zones | Promising | Run zone clean and capture packets before/during/after. |
| Show background | Implemented offline | Full map layout can be rendered, but the HA bridge currently renders transparent trace overlays only. |

## Recommended Next Reverse-Engineering Tests

Run each test one at a time:

1. Capture current map packet.
2. Add exactly one temporary item in the Roborock app.
3. Capture map packet again.
4. Remove the temporary item.
5. Diff:
   - full packet bytes.
   - decoded layout.
   - decoded mask.
   - tail bytes.
   - room metadata.

Best first tests:

- one virtual wall.
- one no-go zone.
- one no-mop zone.
- one zone clean command.
- one go-to command.

