import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from PIL import Image


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from roborock_q10_map import decode_map_file  # noqa: E402
from roborock_q10_map.render import render_layout, render_mask, scaled_save  # noqa: E402


def decode_payload(path: Path, output_dir: Path) -> dict:
    decoded_map = decode_map_file(path)
    stem = path.stem
    layout_path = output_dir / f"{stem}.layout.png"
    layout_flip_path = output_dir / f"{stem}.layout.flip_y.png"
    mask_path = output_dir / f"{stem}.mask.png"

    layout_image = render_layout(decoded_map)
    scaled_save(layout_image, layout_path)
    scaled_save(layout_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM), layout_flip_path)
    scaled_save(render_mask(decoded_map), mask_path)

    summary = decoded_map.to_summary()
    summary["outputs"] = {
        "layout": str(layout_path),
        "layout_flip_y": str(layout_flip_path),
        "mask": str(mask_path),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode Roborock Q10/S5+ B01 map_response payloads.")
    parser.add_argument("payloads", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/roborock/decoded"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "payloads": [decode_payload(path, output_dir) for path in args.payloads],
    }
    report_path = args.report or output_dir / "q10_decoded_maps.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(report_path.resolve())
    for payload in report["payloads"]:
        room_names = ", ".join(room["display_name"] for room in payload["rooms"])
        print(f"{Path(payload['file']).name}: {payload['width']}x{payload['height']} rooms={room_names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
