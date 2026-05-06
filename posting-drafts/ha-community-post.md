# Draft: Home Assistant Community Post

Suggested category:

```text
Share your Projects
```

Title:

```text
Roborock Q-series Q10 live map/path proof of concept
```

Body:

```text
I wanted to share a sanitized proof-of-concept for Roborock Q-series/B01 Q10 live map and path data in Home Assistant.

The official Roborock integration currently notes that newer Q-series devices are not fully supported because Roborock changed the protocol. This proof-of-concept works around that by reusing the official HA Roborock integration runtime after it has already authenticated, then requesting Q10 map data through the existing Q10 API object.

What is working:
- Q10 map list/get through COMMON / MULTI_MAP.
- 01 01 map/layout packet decoding.
- room metadata decoding.
- binary map mask extraction.
- 02 01 live trace/path packet decoding.
- current robot position from the final trace point.
- transparent camera overlay for picture-elements/floorplan dashboards.
- fade-out of the final path after docking.

Repo:
<PUBLIC_REPO_URL>

This is not a polished HACS integration. It is a technical package for developers and maintainers who want to review the packet format and potentially upstream proper Q-series support into python-roborock and Home Assistant.

The repo intentionally excludes credentials, tokens, map IDs, device identifiers, private captures, and household calibration.
```

