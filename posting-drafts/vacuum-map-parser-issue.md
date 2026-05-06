# Draft: Vacuum Map Parser Issue/Discussion

Title:

```text
Roborock Q-series/B01 Q10 map packet notes and parser proof of concept
```

Body:

```text
I have a sanitized proof-of-concept parser for Roborock Q-series/B01 Q10 map and live trace packets.

It currently decodes:
- 01 01 full map/layout packets.
- room records and room names.
- a binary mask block.
- packet tail bytes for future work.
- 02 01 live trace packets as repeated signed i16 coordinate pairs.
- current vacuum position from the last trace point.

The working Home Assistant proof-of-concept renders live traces as transparent camera overlays on a floorplan. The packet notes may be useful for adding Q-series support to the existing map rendering stack.

Repo:
<PUBLIC_REPO_URL>

Open areas where map-renderer expertise would help:
- naming the binary mask layer.
- identifying no-go/no-mop/virtual-wall geometry.
- rendering cleaned area, zones, and other official Roborock drawables.
- aligning Q10/B01 packet semantics with existing Roborock map parser abstractions.

No credentials, private captures, map IDs, or household calibration are included.
```

