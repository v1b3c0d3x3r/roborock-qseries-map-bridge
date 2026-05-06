from pathlib import Path

from PIL import Image, ImageDraw

from .parser import Q10Map, TracePacket


ROOM_COLORS = [
    (249, 66, 79),
    (253, 208, 43),
    (70, 168, 144),
    (32, 140, 255),
    (250, 122, 128),
    (168, 231, 114),
    (73, 249, 202),
    (124, 248, 255),
    (243, 160, 164),
    (121, 228, 32),
    (101, 234, 243),
    (161, 136, 248),
]


def pixel_color(value: int) -> tuple[int, int, int]:
    if value in (243, 255):
        return (15, 20, 26)
    if value == 240:
        return (200, 200, 200)
    if value in (241, 248, 249, 251, 252, 253) or value % 4 in (1, 3):
        return (96, 104, 112)
    if value % 4 == 0:
        return ROOM_COLORS[(value // 4) % len(ROOM_COLORS)]
    return (40, 40, 40)


def render_layout(decoded_map: Q10Map) -> Image.Image:
    image = Image.new("RGB", (decoded_map.width, decoded_map.height))
    image.putdata([pixel_color(value) for value in decoded_map.layout])
    draw = ImageDraw.Draw(image)
    for room in decoded_map.rooms:
        xs = []
        ys = []
        for index, value in enumerate(decoded_map.layout):
            if value == room.pixel_value:
                xs.append(index % decoded_map.width)
                ys.append(index // decoded_map.width)
        if xs:
            draw.text((sum(xs) // len(xs), sum(ys) // len(ys)), str(room.id), fill=(255, 255, 255))
    return image


def render_mask(decoded_map: Q10Map) -> Image.Image:
    image = Image.new("RGB", (decoded_map.width, decoded_map.height))
    image.putdata([(96, 104, 112) if value else (249, 66, 79) for value in decoded_map.mask[: decoded_map.layout_pixels]])
    return image


def render_trace(trace: TracePacket) -> Image.Image:
    points = trace.points
    bounds = trace.bounds
    if (
        len(points) < 2
        or bounds.min_x is None
        or bounds.max_x is None
        or bounds.min_y is None
        or bounds.max_y is None
    ):
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    source_width = max(1, bounds.width)
    source_height = max(1, bounds.height)
    padding = 28
    target_max = 1100
    scale = min((target_max - padding * 2) / source_width, (target_max - padding * 2) / source_height)
    width = int(source_width * scale + padding * 2)
    height = int(source_height * scale + padding * 2)

    def to_image(point) -> tuple[int, int]:
        return (
            int((point.x - bounds.min_x) * scale + padding),
            int((bounds.max_y - point.y) * scale + padding),
        )

    image = Image.new("RGBA", (width, height), (8, 12, 18, 255))
    draw = ImageDraw.Draw(image)
    draw.line([to_image(point) for point in points], fill=(45, 210, 255, 210), width=3, joint="curve")
    for point, color, radius in ((points[0], (96, 255, 120, 255), 7), (points[-1], (255, 78, 78, 255), 8)):
        x, y = to_image(point)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
    return image


def scaled_save(image: Image.Image, path: Path) -> None:
    scale = max(1, min(6, 900 // max(image.width, image.height)))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST).save(path)
