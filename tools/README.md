# Tools

These scripts are optional offline helpers.

## `roborock_q10_extract_payloads.py`

Extracts base64/hex payloads from a saved diagnostic report into `.bin` files.

## `roborock_q10_decode_map.py`

Decodes `01 01` full map packets and writes:

- rendered layout PNG.
- flipped layout PNG.
- binary mask PNG.
- JSON summary.

## `roborock_q10_decode_live.py`

Decodes `02 01` trace packets and writes:

- rendered trace PNG.
- JSON summary.

## `roborock_q10_report_summary.py`

Builds a compact summary from probe/report JSON.

## Notes

- These tools expect sanitized local payload captures.
- Do not publish raw captures if they contain private home layout data.
- The Home Assistant bridge itself does not need these tools at runtime.

