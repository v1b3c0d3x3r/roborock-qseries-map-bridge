---
name: Feature layer diff
about: Document before/after captures for zones, walls, obstacles, or similar map layers
title: "Feature layer diff: <feature>"
labels: ["reverse-engineering"]
assignees: []
---

## Feature

Examples: virtual wall, no-go zone, no-mop zone, zone clean, go-to path, obstacle.

## Test Steps

1. Captured baseline map packet.
2. Added one temporary feature in the Roborock app.
3. Captured changed map packet.
4. Removed the temporary feature.
5. Captured final map packet.

## Observed Differences

- Full packet:
- Decoded layout:
- Decoded mask:
- Tail bytes:
- Trace packets:

## Files

Attach only sanitized summaries or synthetic/cropped examples.

