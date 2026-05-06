# Roborock Q-Series Map Bridge Proof Of Concept

This repository documents a working Home Assistant proof-of-concept bridge for Roborock Q-series/B01 Q10 map and live path data.

It is intended for developers working on Home Assistant, python-roborock, vacuum map renderers, or custom Q-series map implementations. It is not a finished HACS release.

## What This Proves

- A Q-series robot that is only partially supported by Home Assistant can still expose map/path payloads through Home Assistant's existing Roborock integration runtime.
- The bridge avoids a separate Roborock login by reusing the official HA integration's already-authenticated Q10 API object.
- The Q10 map stream contains at least two useful binary packet types:
  - `01 01`: full map/layout packet.
  - `02 01`: live trace/path packet.
- The live trace can be rendered as a transparent PNG camera entity and overlaid onto a Home Assistant floorplan.

## Package Contents

- `code/custom_components/roborock_q10_map/`
  - Sanitized Home Assistant custom component.
  - Exposes sensors and transparent camera overlays.
  - Uses placeholder calibration in `const.py`.
- `code/offline_parser/roborock_q10_map/`
  - Offline parser and renderer used while reverse engineering.
- `tools/`
  - Small decode/extract/report helper scripts.
- `docs/`
  - Step-by-step setup notes.
  - Technical report.
  - Packet format notes.
  - Feature roadmap.
- `examples/`
  - Placeholder calibration and Lovelace examples.

## Main Entry Points

- [Step-by-step implementation](docs/STEP_BY_STEP.md)
- [Technical report](docs/TECHNICAL_REPORT.md)
- [Packet format notes](docs/PACKET_FORMAT_NOTES.md)
- [Feature roadmap](docs/FEATURE_ROADMAP.md)
- [Publish/upstream checklist](posting-drafts/publish-checklist.md)

## Privacy Notes

This package intentionally excludes:

- Roborock account details.
- Roborock credentials, session material, device identifiers, and email codes.
- Home Assistant long-lived access tokens.
- Home Assistant `.storage` files.
- Private map captures and floorplan images.
- Real map IDs and household calibration.

## Quick Start

1. Install and configure Home Assistant's official Roborock integration first.
2. Confirm your Q-series robot appears as a `vacuum.*` entity.
3. Copy `code/custom_components/roborock_q10_map` into Home Assistant's `custom_components` folder.
4. Replace placeholder robot IDs and calibration in `const.py`.
5. Restart Home Assistant.
6. Add the `Roborock Q10 Map Bridge` integration.
7. Add the generated camera overlay entity to a floorplan/picture-elements card.
8. Run the robot and tune the calibration until the path overlay aligns.

See `docs/STEP_BY_STEP.md` for the full sequence.

## License

GPL-3.0-or-later. See `LICENSE`.

## Upstreaming Goal

The ideal end state is not this custom component. The useful pieces should move into:

- `python-roborock`, for Q-series map retrieval/parsing support.
- Home Assistant's official Roborock integration, for stable entity/camera support.
- Vacuum map parser/rendering projects, for richer map drawables.

This bridge intentionally shows the working path and the packet format so maintainers can reuse the useful parts without relying on this component long-term.
