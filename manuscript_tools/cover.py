from __future__ import annotations

import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

PROMPT = (
    "A luminous abstract cover image in a Romantic-era relief-engraving inspired "
    "style for an academic manuscript about a William Blake digital corpus. "
    "Vertical portrait composition with a radiant golden sun disk, etched flame "
    "arcs, indigo night sky, umber ink lines, hand-colored print texture, "
    "parchment background, fine crosshatching, visionary scholarly atmosphere, "
    "no people, no bodies, no text, no imitation of a specific artwork, no "
    "museum object reproduction."
)

USAGE_NOTE = (
    "Generative visual interpretation for the manuscript title page; not an "
    "original William Blake work, corpus record, catalog image, or evidence item."
)


def generate_cover(project_root: Path | str) -> dict[str, Path]:
    root = Path(project_root)
    cover_dir = root / "output" / "cover"
    audit_dir = root / "analysis_output" / "data"
    cover_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    cover_path = cover_dir / "cover_blakean.png"
    provenance_path = audit_dir / "cover_image_provenance.json"
    source_image = root / "docs" / "manuscript" / "assets" / "cover_blakean_source.png"
    if source_image.exists():
        image = _cover_from_source(source_image)
        source_mode = "image_gen_source_with_local_provenance_footer"
    else:
        image = _draw_cover()
        source_mode = "deterministic_local_fallback"
    image.save(cover_path)

    provenance: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "output_path": str(cover_path),
        "prompt": PROMPT,
        "style": "abstract Romantic relief engraving; generated, not archival",
        "model_tool_provenance": {
            "creative_workflow": "BeCreative DomainSpecific",
            "image_generation_prompt_status": "accepted on second abstract prompt",
            "local_generator": "manuscript_tools.cover.generate_cover",
            "source_mode": source_mode,
            "source_image_path": str(source_image) if source_image.exists() else None,
        },
        "usage_note": USAGE_NOTE,
        "dimensions": {"width": image.width, "height": image.height},
    }
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return {"cover": cover_path, "provenance": provenance_path}


def _cover_from_source(source_image: Path) -> Image.Image:
    image = Image.open(source_image).convert("RGB")
    image = ImageOps.fit(
        image, (1600, 2300), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_footer_note(draw, image.width, image.height)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _draw_cover() -> Image.Image:
    width, height = 1600, 2300
    rng = random.Random(18270622)
    image = Image.new("RGB", (width, height), "#ead8af")
    pixels = image.load()
    for y in range(height):
        t = y / height
        for x in range(width):
            vignette = abs(x - width / 2) / (width / 2)
            r = int(237 - 96 * t - 38 * vignette)
            g = int(217 - 105 * t - 30 * vignette)
            b = int(174 - 126 * t - 26 * vignette)
            pixels[x, y] = (max(18, r), max(22, g), max(28, b))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_plate_border(draw, width, height)
    _draw_sun(draw, width, height, rng)
    _draw_flame_arcs(draw, width, height, rng)
    _draw_clouds(draw, width, height, rng)
    _draw_scholarly_geometry(draw, width, height, rng)
    _draw_crosshatching(draw, width, height, rng)
    _draw_footer_note(draw, width, height)
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    image = _add_print_texture(image, rng)
    return image.convert("RGB")


def _draw_plate_border(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    for i in range(28):
        inset = 42 + i * 3
        color = (35, 30, 24, max(18, 100 - i * 3))
        draw.rounded_rectangle(
            (inset, inset, width - inset, height - inset),
            radius=34,
            outline=color,
            width=2,
        )


def _draw_sun(
    draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random
) -> None:
    cx, cy, radius = width // 2, int(height * 0.31), 318
    for r in range(radius + 190, 8, -7):
        alpha = int(max(10, 230 * (1 - r / (radius + 210))))
        color = (248, 185, 62, alpha)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=2)
    for i in range(260):
        angle = 2 * math.pi * i / 260
        length = radius + rng.randint(180, 520)
        inner = radius * rng.uniform(0.72, 0.98)
        x0 = cx + math.cos(angle) * inner
        y0 = cy + math.sin(angle) * inner
        x1 = cx + math.cos(angle) * length
        y1 = cy + math.sin(angle) * length
        draw.line((x0, y0, x1, y1), fill=(246, 188, 74, rng.randint(72, 178)), width=1)
    for r in range(radius, 0, -9):
        alpha = int(255 * (1 - r / (radius + 20)))
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r), fill=(248, 203, 87, max(16, alpha))
        )
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        outline=(255, 229, 150, 230),
        width=5,
    )


def _draw_flame_arcs(
    draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random
) -> None:
    cx, cy = width // 2, int(height * 0.32)
    colors = [(229, 147, 51, 120), (178, 80, 38, 112), (255, 210, 111, 126)]
    for i in range(80):
        angle = -math.pi * 0.96 + i * math.pi * 1.92 / 79
        reach = rng.randint(470, 850)
        wiggle = rng.uniform(18, 58)
        points = []
        for step in range(44):
            t = step / 43
            a = angle + math.sin(t * math.pi * 3 + i) * 0.05
            r = 250 + reach * t
            x = cx + math.cos(a) * r + math.sin(t * math.pi * 5) * wiggle
            y = cy + math.sin(a) * r - 130 * math.sin(t * math.pi)
            points.append((x, y))
        draw.line(points, fill=colors[i % len(colors)], width=rng.randint(2, 5))


def _draw_clouds(
    draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random
) -> None:
    for band, y in enumerate((int(height * 0.55), int(height * 0.61))):
        for i in range(23):
            x = -120 + i * 86 + rng.randint(-28, 28)
            w = rng.randint(170, 320)
            h = rng.randint(42, 108)
            color = (205 - band * 18, 178 - band * 18, 128 - band * 10, 62)
            draw.ellipse(
                (x, y + rng.randint(-35, 35), x + w, y + h),
                fill=color,
                outline=(42, 37, 31, 70),
                width=1,
            )
    for i in range(96):
        y = int(height * 0.54) + rng.randint(0, 260)
        x0 = rng.randint(20, width - 20)
        draw.arc(
            (x0 - 120, y - 38, x0 + 120, y + 38),
            190,
            350,
            fill=(36, 31, 27, 58),
            width=1,
        )


def _draw_scholarly_geometry(
    draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random
) -> None:
    gold = (226, 170, 76, 145)
    ink = (18, 34, 45, 130)
    left_c = (310, int(height * 0.77))
    for r in (52, 96, 142, 190):
        draw.ellipse(
            (left_c[0] - r, left_c[1] - r, left_c[0] + r, left_c[1] + r),
            outline=gold,
            width=2,
        )
    draw.line(
        (left_c[0] - 210, left_c[1], left_c[0] + 210, left_c[1]), fill=gold, width=2
    )
    draw.line(
        (left_c[0], left_c[1] - 210, left_c[0], left_c[1] + 210), fill=gold, width=2
    )

    nodes: list[Tuple[int, int]] = []
    for _ in range(17):
        nodes.append(
            (
                rng.randint(width - 560, width - 95),
                rng.randint(int(height * 0.66), height - 315),
            )
        )
    for index, p0 in enumerate(nodes):
        for p1 in nodes[index + 1 :]:
            if rng.random() < 0.13:
                draw.line((*p0, *p1), fill=gold, width=2)
    for x, y in nodes:
        draw.ellipse(
            (x - 9, y - 9, x + 9, y + 9), fill=(232, 174, 75, 180), outline=ink, width=1
        )

    apex = (width // 2, int(height * 0.66))
    base_l = (260, height - 210)
    base_r = (width - 260, height - 210)
    draw.line((*apex, *base_l), fill=(237, 188, 95, 120), width=2)
    draw.line((*apex, *base_r), fill=(237, 188, 95, 120), width=2)
    draw.line((*base_l, *base_r), fill=(237, 188, 95, 120), width=2)


def _draw_crosshatching(
    draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random
) -> None:
    for i in range(520):
        x = rng.randint(-260, width + 40)
        y = rng.randint(40, height - 170)
        length = rng.randint(120, 520)
        slope = rng.choice((-0.22, 0.18, 0.42, -0.38))
        color = (15, 27, 36, rng.randint(20, 58))
        draw.line((x, y, x + length, y + length * slope), fill=color, width=1)
    for i in range(110):
        x = rng.randint(50, width - 50)
        y = rng.randint(70, int(height * 0.46))
        size = rng.randint(2, 6)
        draw.line((x - size, y, x + size, y), fill=(247, 209, 120, 125), width=1)
        draw.line((x, y - size, x, y + size), fill=(247, 209, 120, 125), width=1)


def _draw_footer_note(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    font = _font(34)
    note = "Generative visual interpretation; not corpus evidence."
    tw = draw.textlength(note, font=font)
    x = (width - tw) / 2
    y = height - 118
    draw.rounded_rectangle(
        (x - 28, y - 18, x + tw + 28, y + 54), radius=16, fill=(32, 27, 22, 125)
    )
    draw.text((x, y), note, font=font, fill=(246, 225, 176, 232))


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/Library/Fonts/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _add_print_texture(image: Image.Image, rng: random.Random) -> Image.Image:
    width, height = image.size
    noise = Image.effect_noise((width, height), 18).convert("L")
    sepia = Image.new("RGBA", (width, height), (72, 54, 32, 0))
    alpha = noise.point(lambda value: max(0, min(34, int((value - 122) * 0.7))))
    sepia.putalpha(alpha)
    image = Image.alpha_composite(image, sepia)
    draw = ImageDraw.Draw(image)
    for _ in range(2400):
        x = rng.randrange(width)
        y = rng.randrange(height)
        a = rng.randrange(16, 44)
        draw.point((x, y), fill=(245, 225, 180, a))
    return image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=122, threshold=3))
