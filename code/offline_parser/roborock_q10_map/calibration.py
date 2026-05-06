import math
from dataclasses import dataclass
from typing import Any

from .parser import Bounds, Point


@dataclass(frozen=True)
class FloorplanBox:
    center_x_pct: float
    center_y_pct: float
    width_pct: float
    height_pct: float
    rotate_deg: float = 0.0

    @property
    def left_pct(self) -> float:
        return self.center_x_pct - self.width_pct / 2

    @property
    def top_pct(self) -> float:
        return self.center_y_pct - self.height_pct / 2

    def to_dict(self) -> dict[str, float]:
        return {
            "center_x_pct": self.center_x_pct,
            "center_y_pct": self.center_y_pct,
            "width_pct": self.width_pct,
            "height_pct": self.height_pct,
            "rotate_deg": self.rotate_deg,
        }


@dataclass(frozen=True)
class TraceCalibration:
    bounds: Bounds
    floorplan_box: FloorplanBox
    flip_x: bool = False
    flip_y: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "bounds": self.bounds.to_dict(),
            "floorplan_box": self.floorplan_box.to_dict(),
            "flip_x": self.flip_x,
            "flip_y": self.flip_y,
        }


def normalize_trace_point(point: Point, bounds: Bounds, flip_x: bool = False, flip_y: bool = True) -> tuple[float, float]:
    if bounds.min_x is None or bounds.max_x is None or bounds.min_y is None or bounds.max_y is None:
        raise ValueError("Trace bounds are incomplete")
    width = max(1, bounds.max_x - bounds.min_x)
    height = max(1, bounds.max_y - bounds.min_y)
    x = (point.x - bounds.min_x) / width
    y = (point.y - bounds.min_y) / height
    if flip_x:
        x = 1 - x
    if flip_y:
        y = 1 - y
    return x, y


def floorplan_point(point: Point, calibration: TraceCalibration) -> tuple[float, float]:
    x, y = normalize_trace_point(point, calibration.bounds, calibration.flip_x, calibration.flip_y)
    local_x = (x - 0.5) * calibration.floorplan_box.width_pct
    local_y = (y - 0.5) * calibration.floorplan_box.height_pct

    if calibration.floorplan_box.rotate_deg:
        angle = math.radians(calibration.floorplan_box.rotate_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        local_x, local_y = (
            local_x * cos_a - local_y * sin_a,
            local_x * sin_a + local_y * cos_a,
        )

    return (
        calibration.floorplan_box.center_x_pct + local_x,
        calibration.floorplan_box.center_y_pct + local_y,
    )
