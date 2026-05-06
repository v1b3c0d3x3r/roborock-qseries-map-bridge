import argparse
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


Q10_BINARY_PREFIXES = {b"\x01\x01", b"\x02\x01"}


def walk_payload_base64(node: Any) -> list[str]:
    values: list[str] = []
    if isinstance(node, dict):
        payload = node.get("payload_base64")
        if isinstance(payload, str):
            values.append(payload)
        for child in node.values():
            values.extend(walk_payload_base64(child))
    elif isinstance(node, list):
        for child in node:
            values.extend(walk_payload_base64(child))
    return values


def decode_candidate(value: str) -> bytes | None:
    try:
        payload = base64.b64decode(value, validate=False)
    except ValueError:
        return None
    if len(payload) < 2 or payload[:2] not in Q10_BINARY_PREFIXES:
        return None
    return payload


def extract_report(report_path: Path, output_dir: Path, type_filter: set[str] | None) -> list[dict[str, Any]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted = []
    seen_hashes = set()
    for value in walk_payload_base64(report):
        payload = decode_candidate(value)
        if payload is None:
            continue
        packet_type = payload[:2].hex()
        if type_filter and packet_type not in type_filter:
            continue
        sha256 = hashlib.sha256(payload).hexdigest()
        if sha256 in seen_hashes:
            continue
        seen_hashes.add(sha256)
        output_path = output_dir / f"{report_path.stem}_payload_{len(extracted) + 1:02d}_{packet_type}_{len(payload)}.bin"
        output_path.write_bytes(payload)
        extracted.append(
            {
                "file": str(output_path),
                "sha256": sha256,
                "length": len(payload),
                "packet_type": packet_type,
                "prefix_hex": payload[:32].hex(),
            }
        )
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Q10 binary map/trace payloads from saved probe JSON reports.")
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--types", help="Comma-separated packet prefixes to keep, for example 0101,0201.")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    type_filter = set(args.types.split(",")) if args.types else None
    all_extracted = []
    for report_path in args.reports:
        output_dir = args.output_dir or report_path.parent
        all_extracted.extend(extract_report(report_path, output_dir, type_filter))

    report = {
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "payloads": all_extracted,
    }
    report_path = args.report or (args.output_dir or args.reports[0].parent) / "q10_extracted_payloads.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(report_path.resolve())
    for item in all_extracted:
        print(f"{Path(item['file']).name}: type={item['packet_type']} length={item['length']} sha256={item['sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
