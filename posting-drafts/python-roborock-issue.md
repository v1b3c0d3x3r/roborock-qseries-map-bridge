# Draft: python-roborock Issue/Discussion

Title:

```text
Q-series / B01 Q10 map and live trace packets decoded via HA runtime bridge
```

Body:

```text
I have a working sanitized proof-of-concept for Roborock Q-series/B01 Q10 map and live trace extraction in Home Assistant.

Tested with Roborock Q10 S5+ devices.

Key finding:
- Reuse Home Assistant's official Roborock integration runtime after it has authenticated.
- Locate the loaded Q10 runtime under HA's Roborock config entry runtime data.
- Use the existing Q10 API object rather than doing a separate Roborock login.
- Send COMMON / MULTI_MAP list/get through the Q10 API object.
- Listen to the Q10 channel stream.
- Decode binary packets:
  - 01 01 = full map/layout packet.
  - 02 01 = live trace/path packet.
- Render the trace as a transparent HA camera overlay.

The package includes:
- sanitized custom component proof-of-concept.
- offline parser and renderer.
- packet format notes.
- step-by-step implementation notes.
- feature roadmap for cleaned area, zones, virtual walls, etc.

Repo:
<PUBLIC_REPO_URL>

No credentials, tokens, map IDs, device identifiers, private captures, or household calibration are included.

I am sharing this so it can be reviewed, corrected, and hopefully folded into python-roborock / Home Assistant properly instead of depending on HA runtime internals from a custom bridge.
```

