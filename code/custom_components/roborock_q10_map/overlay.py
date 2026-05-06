from __future__ import annotations

import math
from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance

from .calibration import TraceCalibration, contain_size, floorplan_pixel
from .q10_parser import TracePacket


def render_trace_overlay(
    trace: TracePacket | None,
    calibration: TraceCalibration | None,
    width: int,
    height: int,
    marker_style: dict | None = None,
) -> bytes:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if trace is None or calibration is None or len(trace.points) < 2:
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    trace_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(trace_layer)

    def to_px(point) -> tuple[int, int]:
        x_px, y_px = floorplan_pixel(point, calibration, width, height)
        return int(round(x_px)), int(round(y_px))

    path = [to_px(point) for point in trace.points]
    if len(path) >= 2:
        draw.line(path, fill=(30, 215, 255, 210), width=5, joint="curve")
    latest_x, latest_y = path[-1]
    heading = _path_heading(path)
    robot_marker = _robot_marker(heading, marker_style)
    marker_half = robot_marker.width // 2
    trace_layer.alpha_composite(robot_marker, (latest_x - marker_half, latest_y - marker_half))
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(_floorplan_box_polygon(calibration, width, height), fill=255)
    image = Image.composite(trace_layer, image, mask)

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def fade_overlay_bytes(image_bytes: bytes, opacity: float) -> bytes:
    opacity = max(0.0, min(1.0, opacity))
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    if opacity <= 0:
        faded = Image.new("RGBA", image.size, (0, 0, 0, 0))
    elif opacity >= 1:
        return image_bytes
    else:
        faded = image.copy()
        alpha = faded.getchannel("A")
        faded.putalpha(ImageEnhance.Brightness(alpha).enhance(opacity))
    output = BytesIO()
    faded.save(output, format="PNG")
    return output.getvalue()


def _path_heading(path: list[tuple[int, int]]) -> float:
    latest_x, latest_y = path[-1]
    for previous_x, previous_y in reversed(path[:-1]):
        delta_x = latest_x - previous_x
        delta_y = latest_y - previous_y
        if abs(delta_x) + abs(delta_y) >= 4:
            return math.degrees(math.atan2(delta_y, delta_x))
    return 0.0


def _robot_marker(heading_deg: float, style: dict | None = None) -> Image.Image:
    style = style or {}
    scale = max(0.5, min(2.0, float(style.get("scale", 1.25))))
    size = int(round(44 * scale))
    pad = size / 44
    theme = str(style.get("theme", "black")).lower()
    if theme == "white":
        body_fill = (242, 247, 250, 238)
        body_outline = (10, 18, 24, 235)
        inner_outline = (30, 215, 255, 235)
        side_fill = (8, 22, 31, 205)
        hub_fill = (225, 237, 243, 245)
        hub_outline = (10, 18, 24, 220)
        hub_dot = (10, 18, 24, 245)
    else:
        body_fill = (8, 22, 31, 232)
        body_outline = (255, 255, 255, 235)
        inner_outline = (30, 215, 255, 235)
        side_fill = (30, 215, 255, 185)
        hub_fill = (18, 52, 64, 245)
        hub_outline = (255, 255, 255, 215)
        hub_dot = (255, 255, 255, 245)

    def box(left: float, top: float, right: float, bottom: float) -> list[int]:
        return [round(left * pad), round(top * pad), round(right * pad), round(bottom * pad)]

    marker = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(marker)
    draw.rounded_rectangle(
        box(7, 7, 37, 37),
        radius=round(10 * pad),
        fill=body_fill,
        outline=body_outline,
        width=max(2, round(3 * pad)),
    )
    draw.rounded_rectangle(
        box(9, 9, 35, 35),
        radius=round(8 * pad),
        outline=inner_outline,
        width=max(1, round(2 * pad)),
    )
    draw.pieslice(box(5, 14, 17, 30), start=90, end=270, fill=side_fill)
    draw.pieslice(box(27, 14, 39, 30), start=270, end=90, fill=side_fill)
    draw.ellipse(box(16, 16, 28, 28), fill=hub_fill, outline=hub_outline, width=max(1, round(2 * pad)))
    draw.ellipse(box(20, 20, 24, 24), fill=hub_dot)
    draw.polygon([(round(x * pad), round(y * pad)) for x, y in [(32, 18), (39, 22), (32, 26)]], fill=(78, 226, 162, 235))
    draw.ellipse(box(27, 11, 33, 17), fill=(78, 226, 162, 245))
    return marker.rotate(heading_deg, resample=Image.Resampling.BICUBIC, center=(size / 2, size / 2))


def _floorplan_box_polygon(calibration: TraceCalibration, width: int, height: int) -> list[tuple[int, int]]:
    box = calibration.floorplan_box
    center_x = width * box.center_x_pct / 100
    center_y = height * box.center_y_pct / 100
    box_width = width * box.width_pct / 100
    box_height = height * box.height_pct / 100
    content_width, content_height = contain_size(box_width, box_height, box.source_width, box.source_height)
    half_width = content_width / 2
    half_height = content_height / 2
    angle = math.radians(box.rotate_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    corners = [
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ]
    return [
        (
            int(round(center_x + local_x * cos_a - local_y * sin_a)),
            int(round(center_y + local_x * sin_a + local_y * cos_a)),
        )
        for local_x, local_y in corners
    ]
