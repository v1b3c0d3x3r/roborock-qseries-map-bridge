from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .calibration import FloorplanBox, TraceCalibration, floorplan_point
from .const import (
    CONF_POLL_INTERVAL,
    CONF_ROBOTS,
    DEFAULT_CALIBRATION,
    DEFAULT_FLOORPLAN_HEIGHT,
    DEFAULT_FLOORPLAN_WIDTH,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .overlay import fade_overlay_bytes, render_trace_overlay
from .q10_client import capture_q10_map, find_existing_q10_api
from .q10_parser import Bounds


_LOGGER = logging.getLogger(__name__)

IDLE_STATES = {"docked", "idle", "unavailable", "unknown"}
TRACE_FADE_SECONDS = 60.0


class RoborockQ10MapCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.robot_entity_ids = list(entry.data.get(CONF_ROBOTS, []))
        poll_interval = int(entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
        self._poll_seconds = max(1, poll_interval)
        self._last_overlay_by_robot: dict[str, bytes] = {}
        self._last_trace_data_by_robot: dict[str, dict[str, Any]] = {}
        self._trace_fade_started_by_robot: dict[str, float] = {}
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self._poll_seconds),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        data = {}
        for entity_id in self.robot_entity_ids:
            vacuum_state = self.hass.states.get(entity_id)
            state = vacuum_state.state if vacuum_state else "unknown"
            calibration = self._calibration_for(entity_id)
            bridge_state = "waiting_for_roborock"
            floorplan_x = None
            floorplan_y = None
            trace_point_count = 0
            latest_trace_point = None
            map_id = self._robot_config(entity_id).get("map_id")
            map_sha256 = None
            trace_sha256 = None
            live_trace_bounds = None
            retained_trace = False
            trace_fade_seconds_remaining = None
            binary_packet_count = 0
            message_count = 0
            error = None

            if state in IDLE_STATES:
                retained = self._last_trace_data_by_robot.get(entity_id)
                if retained:
                    fade_started = self._trace_fade_started_by_robot.setdefault(entity_id, time.monotonic())
                    fade_elapsed = time.monotonic() - fade_started
                    trace_fade_seconds_remaining = round(max(0.0, TRACE_FADE_SECONDS - fade_elapsed), 1)
                    if fade_elapsed >= TRACE_FADE_SECONDS:
                        bridge_state = "idle"
                        self._last_trace_data_by_robot.pop(entity_id, None)
                        self._trace_fade_started_by_robot.pop(entity_id, None)
                        self._last_overlay_by_robot[entity_id] = render_trace_overlay(
                            None,
                            calibration,
                            DEFAULT_FLOORPLAN_WIDTH,
                            DEFAULT_FLOORPLAN_HEIGHT,
                        )
                    else:
                        bridge_state = "idle_fading"
                        floorplan_x = retained.get("floorplan_x")
                        floorplan_y = retained.get("floorplan_y")
                        trace_point_count = retained.get("trace_point_count", 0)
                        latest_trace_point = retained.get("latest_trace_point")
                        trace_sha256 = retained.get("trace_sha256")
                        live_trace_bounds = retained.get("live_trace_bounds")
                        retained_trace = True
                elif entity_id not in self._last_overlay_by_robot:
                    bridge_state = "idle"
                    self._trace_fade_started_by_robot.pop(entity_id, None)
                    self._last_overlay_by_robot[entity_id] = render_trace_overlay(
                        None,
                        calibration,
                        DEFAULT_FLOORPLAN_WIDTH,
                        DEFAULT_FLOORPLAN_HEIGHT,
                    )
                else:
                    bridge_state = "idle"
                    self._trace_fade_started_by_robot.pop(entity_id, None)
            else:
                self._trace_fade_started_by_robot.pop(entity_id, None)
                api = await find_existing_q10_api(self.hass, entity_id)
                if api is None:
                    bridge_state = "waiting_for_roborock"
                else:
                    try:
                        result = await capture_q10_map(
                            api,
                            str(map_id) if map_id else None,
                            wait_seconds=min(4.0, self._poll_seconds),
                        )
                        bridge_state = "ok" if result.trace or result.decoded_map else "no_live_payload"
                        map_id = result.map_id or map_id
                        binary_packet_count = result.binary_packet_count
                        message_count = result.message_count
                        if result.decoded_map:
                            map_sha256 = result.decoded_map.sha256
                        if result.trace:
                            live_trace_bounds = result.trace.bounds.to_dict()
                            calibration = self._calibration_for(entity_id, result.trace.bounds)
                            trace_sha256 = result.trace.sha256
                            trace_point_count = len(result.trace.points)
                            latest = result.trace.latest_point
                            if latest:
                                latest_trace_point = [latest.x, latest.y]
                                if calibration is not None:
                                    floorplan_x, floorplan_y = floorplan_point(latest, calibration)
                            self._last_overlay_by_robot[entity_id] = render_trace_overlay(
                                result.trace,
                                calibration,
                                DEFAULT_FLOORPLAN_WIDTH,
                                DEFAULT_FLOORPLAN_HEIGHT,
                                self._robot_config(entity_id).get("marker"),
                            )
                        elif entity_id not in self._last_overlay_by_robot:
                            self._last_overlay_by_robot[entity_id] = render_trace_overlay(
                                None,
                                calibration,
                                DEFAULT_FLOORPLAN_WIDTH,
                                DEFAULT_FLOORPLAN_HEIGHT,
                            )
                    except Exception as err:
                        error = f"{type(err).__name__}: {err}"
                        bridge_state = "error"
                        _LOGGER.debug("Failed to capture Q10 map for %s: %s", entity_id, err)

            robot_data = {
                "vacuum_state": state,
                "bridge_state": bridge_state,
                "floorplan_x": round(floorplan_x, 3) if floorplan_x is not None else None,
                "floorplan_y": round(floorplan_y, 3) if floorplan_y is not None else None,
                "trace_point_count": trace_point_count,
                "latest_trace_point": latest_trace_point,
                "trace_bounds": calibration.bounds.to_dict() if calibration is not None else None,
                "configured_trace_bounds": calibration.bounds.to_dict() if calibration is not None else None,
                "live_trace_bounds": live_trace_bounds,
                "retained_trace": retained_trace,
                "trace_fade_seconds_remaining": trace_fade_seconds_remaining,
                "map_id": map_id,
                "map_sha256": map_sha256,
                "trace_sha256": trace_sha256,
                "binary_packet_count": binary_packet_count,
                "message_count": message_count,
                "error": error,
            }
            if trace_point_count and live_trace_bounds:
                self._last_trace_data_by_robot[entity_id] = robot_data.copy()
            data[entity_id] = robot_data
        if not data:
            raise UpdateFailed("No Q10 robots configured")
        return data

    def overlay_bytes(self, robot_entity_id: str) -> bytes | None:
        overlay = self._last_overlay_by_robot.get(robot_entity_id)
        fade_started = self._trace_fade_started_by_robot.get(robot_entity_id)
        if overlay is None or fade_started is None:
            return overlay
        opacity = 1.0 - ((time.monotonic() - fade_started) / TRACE_FADE_SECONDS)
        if opacity <= 0:
            self._last_trace_data_by_robot.pop(robot_entity_id, None)
            self._trace_fade_started_by_robot.pop(robot_entity_id, None)
            transparent = render_trace_overlay(
                None,
                self._calibration_for(robot_entity_id),
                DEFAULT_FLOORPLAN_WIDTH,
                DEFAULT_FLOORPLAN_HEIGHT,
            )
            self._last_overlay_by_robot[robot_entity_id] = transparent
            return transparent
        return fade_overlay_bytes(overlay, opacity)

    def _robot_config(self, entity_id: str) -> dict[str, Any]:
        return DEFAULT_CALIBRATION.get(entity_id, {})

    def _calibration_for(self, entity_id: str, live_bounds: Bounds | None = None) -> TraceCalibration | None:
        config = self._robot_config(entity_id)
        bounds = self._merged_bounds(
            config.get("trace_bounds"),
            live_bounds if config.get("use_live_bounds_fallback") else None,
        )
        box = config.get("floorplan_box_pct")
        if bounds is None or not isinstance(box, dict):
            return None
        axis = config.get("axis", {})
        return TraceCalibration(
            bounds=bounds,
            floorplan_box=FloorplanBox(
                center_x_pct=float(box.get("center_x", 50)),
                center_y_pct=float(box.get("center_y", 50)),
                width_pct=float(box.get("width", 100)),
                height_pct=float(box.get("height", 100)),
                rotate_deg=float(box.get("rotate", 0)),
                source_width=float(box["source_width"]) if box.get("source_width") else None,
                source_height=float(box["source_height"]) if box.get("source_height") else None,
            ),
            flip_x=bool(axis.get("flip_x", False)),
            flip_y=bool(axis.get("flip_y", True)),
        )

    @staticmethod
    def _merged_bounds(configured: dict[str, Any] | None, live: Bounds | None) -> Bounds | None:
        bounds: list[Bounds] = []
        if isinstance(configured, dict):
            configured_bounds = Bounds(
                configured.get("min_x"),
                configured.get("max_x"),
                configured.get("min_y"),
                configured.get("max_y"),
            )
            if configured_bounds.width > 0 and configured_bounds.height > 0:
                bounds.append(configured_bounds)
        if live is not None and live.width > 0 and live.height > 0:
            bounds.append(live)
        if not bounds:
            return None
        return Bounds(
            min(bound.min_x for bound in bounds if bound.min_x is not None),
            max(bound.max_x for bound in bounds if bound.max_x is not None),
            min(bound.min_y for bound in bounds if bound.min_y is not None),
            max(bound.max_y for bound in bounds if bound.max_y is not None),
        )
