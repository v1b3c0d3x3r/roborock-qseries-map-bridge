from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import decode_rpc_response

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .q10_parser import Q10Map, TracePacket, decode_map_payload, parse_trace_payload, q10_packet_type

_LOGGER = logging.getLogger(__name__)
ROBOROCK_DOMAIN = "roborock"


@dataclass
class CaptureResult:
    map_id: str | None
    decoded_map: Q10Map | None
    trace: TracePacket | None
    binary_packet_count: int
    message_count: int


async def find_existing_q10_api(hass: HomeAssistant, robot_entity_id: str) -> Any | None:
    registry = er.async_get(hass)
    entity_entry = registry.async_get(robot_entity_id)
    unique_id = entity_entry.unique_id if entity_entry else None

    candidates = []
    for config_entry in hass.config_entries.async_entries(ROBOROCK_DOMAIN):
        runtime_data = getattr(config_entry, "runtime_data", None)
        candidates.extend(getattr(runtime_data, "b01_q10", []) or [])

    if unique_id:
        for coordinator in candidates:
            if getattr(coordinator, "duid_slug", None) == unique_id:
                return getattr(coordinator, "api", None)

    state = hass.states.get(robot_entity_id)
    friendly_name = (state.attributes.get("friendly_name") if state else None) or ""
    for coordinator in candidates:
        device = getattr(coordinator, "device", None)
        device_name = getattr(getattr(device, "device_info", None), "name", None)
        if device_name and device_name == friendly_name:
            return getattr(coordinator, "api", None)

    if len(candidates) == 1:
        return getattr(candidates[0], "api", None)

    return None


def _extract_map_ids_from_decoded(decoded: dict[Any, Any]) -> list[str]:
    multi_map = decoded.get(B01_Q10_DP.MULTI_MAP)
    if not isinstance(multi_map, dict):
        return []
    data = multi_map.get("data")
    if not isinstance(data, list):
        return []
    ids = []
    for item in data:
        if isinstance(item, dict) and item.get("id") is not None:
            ids.append(str(item["id"]))
    return ids


async def _collect_for_command(api: Any, command: B01_Q10_DP, params: Any, wait_seconds: float) -> tuple[list[bytes], list[str], int]:
    channel = getattr(api, "_channel", None)
    if channel is None:
        raise RuntimeError("Q10 API channel is unavailable")

    binary_payloads: list[bytes] = []
    map_ids: list[str] = []
    message_count = 0
    stop = asyncio.Event()

    async def collector() -> None:
        nonlocal message_count
        async for message in channel.subscribe_stream():
            if stop.is_set():
                return
            message_count += 1
            payload = getattr(message, "payload", None) or b""
            if q10_packet_type(payload):
                binary_payloads.append(payload)
                continue
            try:
                decoded = decode_rpc_response(message)
            except RoborockException:
                continue
            map_ids.extend(_extract_map_ids_from_decoded(decoded))

    task = asyncio.create_task(collector())
    try:
        await asyncio.sleep(0.2)
        await api.command.send(command, params=params)
        await asyncio.sleep(wait_seconds)
    finally:
        stop.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return binary_payloads, map_ids, message_count


async def capture_q10_map(api: Any, map_id: str | None, wait_seconds: float = 4.0) -> CaptureResult:
    discovered_map_id = map_id
    total_messages = 0
    if not discovered_map_id:
        _payloads, map_ids, message_count = await _collect_for_command(
            api,
            B01_Q10_DP.COMMON,
            {str(B01_Q10_DP.MULTI_MAP.code): {"op": "list"}},
            wait_seconds=wait_seconds,
        )
        total_messages += message_count
        discovered_map_id = map_ids[0] if map_ids else None

    if not discovered_map_id:
        return CaptureResult(None, None, None, 0, total_messages)

    payloads, _map_ids, message_count = await _collect_for_command(
        api,
        B01_Q10_DP.COMMON,
        {str(B01_Q10_DP.MULTI_MAP.code): {"op": "get", "id": discovered_map_id}},
        wait_seconds=wait_seconds,
    )
    total_messages += message_count

    decoded_maps = []
    traces = []
    for payload in payloads:
        packet_type = q10_packet_type(payload)
        try:
            if packet_type == "map":
                decoded_maps.append(decode_map_payload(payload))
            elif packet_type == "trace":
                traces.append(parse_trace_payload(payload))
        except ValueError as err:
            _LOGGER.debug("Failed to decode Q10 %s payload: %s", packet_type, err)

    trace = max(traces, key=lambda item: (len(item.points), item.sequence_hint), default=None)
    decoded_map = decoded_maps[-1] if decoded_maps else None
    return CaptureResult(discovered_map_id, decoded_map, trace, len(payloads), total_messages)
