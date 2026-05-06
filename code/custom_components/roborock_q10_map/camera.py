from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import RoborockQ10MapCoordinator
from .overlay import render_trace_overlay
from .const import DEFAULT_FLOORPLAN_HEIGHT, DEFAULT_FLOORPLAN_WIDTH


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: RoborockQ10MapCoordinator = entry.runtime_data
    async_add_entities(RoborockQ10OverlayCamera(coordinator, robot_entity_id) for robot_entity_id in coordinator.robot_entity_ids)


class RoborockQ10OverlayCamera(CoordinatorEntity[RoborockQ10MapCoordinator], Camera):
    _attr_should_poll = False

    def __init__(self, coordinator: RoborockQ10MapCoordinator, robot_entity_id: str) -> None:
        Camera.__init__(self)
        CoordinatorEntity.__init__(self, coordinator)
        self.content_type = "image/png"
        self.robot_entity_id = robot_entity_id
        slug = robot_entity_id.replace(".", "_")
        self._attr_unique_id = f"{slug}_trace_overlay"
        self._attr_name = f"{robot_entity_id} trace overlay"

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return self.coordinator.overlay_bytes(self.robot_entity_id) or render_trace_overlay(
            None,
            None,
            DEFAULT_FLOORPLAN_WIDTH,
            DEFAULT_FLOORPLAN_HEIGHT,
        )
