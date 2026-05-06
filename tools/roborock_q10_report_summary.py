"""Summarize Q10 probe reports into compact JSON and optional Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def extract_maps(device: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract map-list entries from current and older probe report shapes."""
    maps: list[dict[str, Any]] = []

    for map_response in as_list(device.get("q10_map_lists")):
        for entry in as_list(map_response.get("maps") if isinstance(map_response, dict) else None):
            if isinstance(entry, dict):
                maps.append(entry)

    for message in as_list(device.get("q10_decoded_messages")):
        if not isinstance(message, dict):
            continue
        decoded = message.get("decoded_dps")
        if not isinstance(decoded, dict):
            continue
        multi_map = decoded.get("MULTI_MAP")
        if not isinstance(multi_map, dict):
            continue
        value = multi_map.get("value")
        if not isinstance(value, dict):
            continue
        for entry in as_list(value.get("data")):
            if isinstance(entry, dict):
                maps.append(entry)

    deduped: dict[str, dict[str, Any]] = {}
    for entry in maps:
        key = str(entry.get("id") or entry.get("map_id") or entry)
        deduped[key] = entry
    return list(deduped.values())


def extract_status(device: dict[str, Any]) -> dict[str, Any]:
    cached = device.get("cached_device_status")
    if not isinstance(cached, dict):
        return {}
    wifi = cached.get("101", {}).get("81") if isinstance(cached.get("101"), dict) else None
    if isinstance(wifi, dict):
        wifi = {
            "ip": wifi.get("ipAdress") or wifi.get("ipAddress"),
            "signal": wifi.get("signal"),
            "wifiName": wifi.get("wifiName"),
        }
    return {
        "battery": cached.get("122"),
        "state": cached.get("121"),
        "fan_power": cached.get("123"),
        "water_box_mode": cached.get("124"),
        "clean_task_type": cached.get("138"),
        "back_type": cached.get("139"),
        "cleaning_progress": cached.get("141"),
        "wifi": wifi,
    }


def summarize_report(path: Path) -> dict[str, Any]:
    report = load_json(path)
    devices = []
    for device in as_list(report.get("devices")):
        if not isinstance(device, dict):
            continue
        messages = as_list(device.get("q10_decoded_messages"))
        decode_errors = [message for message in messages if isinstance(message, dict) and message.get("decode_error")]
        maps = extract_maps(device)
        devices.append(
            {
                "name": device.get("name"),
                "model": device.get("model"),
                "firmware": device.get("firmware"),
                "online": device.get("online"),
                "connected": device.get("connected"),
                "local_connected": device.get("local_connected"),
                "message_count": len(messages),
                "decode_error_count": len(decode_errors),
                "map_count": len(maps),
                "maps": maps,
                "status": extract_status(device),
            }
        )

    manager = report.get("manager") if isinstance(report.get("manager"), dict) else {}
    return {
        "source": str(path),
        "created_at": report.get("created_at"),
        "fatal": report.get("fatal"),
        "manager": {
            "ok": manager.get("ok"),
            "device_count": manager.get("device_count"),
            "diagnostics": manager.get("diagnostics"),
        },
        "devices": devices,
    }


def write_markdown(summary: dict[str, Any], output: Path) -> None:
    lines = [
        "# Roborock Q10 Probe Summary",
        "",
        f"Source: `{summary['source']}`",
        "",
    ]
    if summary.get("fatal"):
        fatal = summary["fatal"]
        lines.extend([f"Fatal: `{fatal.get('error_type')}` - {fatal.get('error')}", ""])
    for device in summary["devices"]:
        lines.extend(
            [
                f"## {device.get('name')}",
                "",
                f"- Model: `{device.get('model')}`",
                f"- Firmware: `{device.get('firmware')}`",
                f"- Online/connected: `{device.get('online')}` / `{device.get('connected')}`",
                f"- Messages: `{device.get('message_count')}`",
                f"- Decode errors: `{device.get('decode_error_count')}`",
                f"- Maps found: `{device.get('map_count')}`",
            ]
        )
        for map_entry in device.get("maps") or []:
            lines.append(f"  - `{map_entry.get('id')}` {map_entry.get('name')} timestamp={map_entry.get('timestamp')}")
        status = device.get("status") or {}
        if any(value is not None for value in status.values()):
            lines.append(f"- Status: `{json.dumps(status, default=str)}`")
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Roborock Q10 probe report JSON.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, help="Output compact summary JSON path.")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown output path.")
    args = parser.parse_args()

    summary = summarize_report(args.report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(args.output.resolve())
    else:
        print(json.dumps(summary, indent=2, default=str))
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, args.markdown)
        print(args.markdown.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
