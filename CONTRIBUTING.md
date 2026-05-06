# Contributing

This repository is a technical proof-of-concept and research package, not a polished end-user integration.

Useful contributions:

- Verify the Q10/B01 packet format on other Q-series models.
- Add controlled before/after captures for no-go zones, no-mop zones, virtual walls, zone clean, go-to, and obstacle cases.
- Improve parser naming when a byte field is understood.
- Convert the bridge logic into a cleaner upstream implementation for `python-roborock`.
- Port decoded map features into existing vacuum map parser/rendering projects.

Please do not publish:

- Account credentials.
- Home Assistant tokens.
- Roborock session material.
- Device identifiers.
- Private home floorplans unless deliberately sanitized.
- Raw captures that expose a private home layout.

When adding packet examples, prefer:

- synthetic payloads.
- heavily cropped/sanitized payloads.
- decoded summaries with hashes removed if needed.

