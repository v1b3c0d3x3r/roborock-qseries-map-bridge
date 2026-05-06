from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import RoborockQ10MapCoordinator


@dataclass(frozen=True, kw_only=True)
class RoborockQ10SensorDescription(SensorEntityDescription):
    value_key: str


SENSOR_DESCRIPTIONS = (
    RoborockQ10SensorDescription(key="bridge_state", translation_key="bridge_state", value_key="bridge_state"),
    RoborockQ10SensorDescription(key="floorplan_x", translation_key="floorplan_x", value_key="floorplan_x"),
    RoborockQ10SensorDescription(key="floorplan_y", translation_key="floorplan_y", value_key="floorplan_y"),
    RoborockQ10SensorDescription(key="trace_point_count", translation_key="trace_point_count", value_key="trace_point_count"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: RoborockQ10MapCoordinator = entry.runtime_data
    entities = []
    for robot_entity_id in coordinator.robot_entity_ids:
        entities.extend(RoborockQ10Sensor(coordinator, robot_entity_id, description) for description in SENSOR_DESCRIPTIONS)
    async_add_entities(entities)


class RoborockQ10Sensor(CoordinatorEntity[RoborockQ10MapCoordinator], SensorEntity):
    entity_description: RoborockQ10SensorDescription

    def __init__(
        self,
        coordinator: RoborockQ10MapCoordinator,
        robot_entity_id: str,
        description: RoborockQ10SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.robot_entity_id = robot_entity_id
        self.entity_description = description
        slug = robot_entity_id.replace(".", "_")
        self._attr_unique_id = f"{slug}_{description.key}"
        self._attr_name = f"{robot_entity_id} {description.key.replace('_', ' ')}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get(self.robot_entity_id, {}).get(self.entity_description.value_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data.get(self.robot_entity_id, {})
        return {
            "robot_entity_id": self.robot_entity_id,
            "vacuum_state": data.get("vacuum_state"),
            "latest_trace_point": data.get("latest_trace_point"),
            "trace_bounds": data.get("trace_bounds"),
            "configured_trace_bounds": data.get("configured_trace_bounds"),
            "live_trace_bounds": data.get("live_trace_bounds"),
            "retained_trace": data.get("retained_trace"),
            "trace_fade_seconds_remaining": data.get("trace_fade_seconds_remaining"),
            "map_id": data.get("map_id"),
            "map_sha256": data.get("map_sha256"),
            "trace_sha256": data.get("trace_sha256"),
            "binary_packet_count": data.get("binary_packet_count"),
            "message_count": data.get("message_count"),
            "error": data.get("error"),
        }
