import argparse
import datetime as dt
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from roborock_q10_map import parse_trace_file  # noqa: E402
from roborock_q10_map.render import render_trace  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode Roborock Q10 live trace/path packets.")
    parser.add_argument("payloads", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/roborock/decoded"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    traces = []
    for payload_path in args.payloads:
        trace = parse_trace_file(payload_path)
        trace_path = output_dir / f"{payload_path.stem}.trace.png"
        render_trace(trace).save(trace_path)
        summary = trace.to_summary()
        summary["outputs"] = {"trace": str(trace_path)}
        traces.append(summary)

    report = {
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "payloads": traces,
    }
    report_path = args.report or output_dir / "q10_decoded_live_traces.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(report_path.resolve())
    for trace in traces:
        print(
            f"{Path(trace['file']).name}: points={trace['point_count']} "
            f"bounds={trace['bounds']} sequence={trace['sequence_hint']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
