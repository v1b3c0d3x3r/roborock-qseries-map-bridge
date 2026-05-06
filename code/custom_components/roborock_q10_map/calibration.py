from __future__ import annotations

import math
from dataclasses import dataclass

from .q10_parser import Bounds, Point


@dataclass(frozen=True)
class FloorplanBox:
    center_x_pct: float
    center_y_pct: float
    width_pct: float
    height_pct: float
    rotate_deg: float = 0.0
    source_width: float | None = None
    source_height: float | None = None


@dataclass(frozen=True)
class TraceCalibration:
    bounds: Bounds
    floorplan_box: FloorplanBox
    flip_x: bool = False
    flip_y: bool = True


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


def floorplan_pixel(point: Point, calibration: TraceCalibration, floorplan_width: int, floorplan_height: int) -> tuple[float, float]:
    x, y = normalize_trace_point(point, calibration.bounds, calibration.flip_x, calibration.flip_y)
    box = calibration.floorplan_box
    box_width = floorplan_width * box.width_pct / 100
    box_height = floorplan_height * box.height_pct / 100
    content_width, content_height = contain_size(box_width, box_height, box.source_width, box.source_height)
    local_x = (x - 0.5) * content_width
    local_y = (y - 0.5) * content_height
    if box.rotate_deg:
        angle = math.radians(box.rotate_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        local_x, local_y = (
            local_x * cos_a - local_y * sin_a,
            local_x * sin_a + local_y * cos_a,
        )
    return (
        floorplan_width * box.center_x_pct / 100 + local_x,
        floorplan_height * box.center_y_pct / 100 + local_y,
    )


def floorplan_point(
    point: Point,
    calibration: TraceCalibration,
    floorplan_width: int = 1920,
    floorplan_height: int = 1080,
) -> tuple[float, float]:
    pixel_x, pixel_y = floorplan_pixel(point, calibration, floorplan_width, floorplan_height)
    return pixel_x / floorplan_width * 100, pixel_y / floorplan_height * 100


def contain_size(
    box_width: float,
    box_height: float,
    source_width: float | None,
    source_height: float | None,
) -> tuple[float, float]:
    if not source_width or not source_height or source_width <= 0 or source_height <= 0:
        return box_width, box_height
    source_aspect = source_width / source_height
    box_aspect = box_width / max(1, box_height)
    if box_aspect > source_aspect:
        content_height = box_height
        return content_height * source_aspect, content_height
    content_width = box_width
    return content_width, content_width / source_aspect
