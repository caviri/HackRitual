"""Procedural demo art — specimens grown from a seed string, never fetched.

Four motifs mirror the frontend's SVG placeholders (bloom, nucleus, sprout,
lattice) so seeded covers and portraits sit naturally beside the procedural
placeholders. Everything is deterministic: the same seed always yields the
same bytes, which keeps the seeder idempotent (stable sha256) and screenshots
reproducible.
"""

from __future__ import annotations

import hashlib
import io
import math
import random
from typing import Literal

from PIL import Image, ImageDraw

from app.services import images

Motif = Literal["bloom", "nucleus", "sprout", "lattice"]

MOTIFS: tuple[Motif, ...] = ("bloom", "nucleus", "sprout", "lattice")


def _rng(seed: str) -> random.Random:
    """Deterministic generator from a seed string (sha256-derived)."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _field(draw: ImageDraw.ImageDraw, size: tuple[int, int], rng: random.Random) -> None:
    """Background: soft gray gradient noise + a faint grid."""
    w, h = size
    for _ in range(int(w * h / 900)):
        x, y = rng.randrange(w), rng.randrange(h)
        tone = rng.randint(190, 235)
        r = rng.randint(1, 3)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=tone)
    step = 32
    for gx in range(0, w, step):
        draw.line([(gx, 0), (gx, h)], fill=225, width=1)
    for gy in range(0, h, step):
        draw.line([(0, gy), (w, gy)], fill=225, width=1)


def _bloom(draw: ImageDraw.ImageDraw, size: tuple[int, int], rng: random.Random) -> None:
    w, h = size
    cx = w // 2 + rng.randint(-w // 8, w // 8)
    cy = h // 2 + rng.randint(-h // 8, h // 8)
    petals = rng.randint(6, 12)
    reach = min(w, h) * rng.uniform(0.26, 0.38)
    for i in range(petals):
        angle = (2 * math.pi / petals) * i + rng.uniform(-0.1, 0.1)
        dist = reach * rng.uniform(0.7, 1.0)
        px = cx + dist * math.cos(angle)
        py = cy + dist * math.sin(angle)
        r = min(w, h) * rng.uniform(0.07, 0.13)
        tone = rng.randint(30, 90)
        draw.ellipse([px - r, py - r, px + r, py + r], outline=tone, width=3)
        draw.line([(cx, cy), (px, py)], fill=tone + 40, width=2)
    core = min(w, h) * 0.07
    draw.ellipse([cx - core, cy - core, cx + core, cy + core], fill=20)


def _nucleus(draw: ImageDraw.ImageDraw, size: tuple[int, int], rng: random.Random) -> None:
    w, h = size
    cx, cy = w // 2, h // 2
    rings = rng.randint(4, 7)
    max_r = min(w, h) * 0.42
    for i in range(rings):
        r = max_r * (i + 1) / rings
        tone = rng.randint(30, 110)
        box = [cx - r, cy - r, cx + r, cy + r]
        if rng.random() < 0.45:
            # Dashed ring: arc segments with gaps.
            start = rng.randint(0, 359)
            seg = rng.randint(25, 60)
            a = start
            while a < start + 360:
                draw.arc(box, a, a + seg, fill=tone, width=3)
                a += seg + rng.randint(10, 30)
        else:
            draw.ellipse(box, outline=tone, width=3)
        # A satellite on the ring.
        angle = rng.uniform(0, 2 * math.pi)
        sx = cx + r * math.cos(angle)
        sy = cy + r * math.sin(angle)
        sr = rng.randint(4, 9)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=tone)
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=15)


def _sprout(draw: ImageDraw.ImageDraw, size: tuple[int, int], rng: random.Random) -> None:
    w, h = size
    base_x = w // 2 + rng.randint(-w // 10, w // 10)
    base_y = int(h * 0.92)
    top_y = int(h * rng.uniform(0.12, 0.25))
    lean = rng.randint(-w // 12, w // 12)
    draw.line([(base_x, base_y), (base_x + lean, top_y)], fill=30, width=4)
    branches = rng.randint(3, 6)
    for i in range(branches):
        t = (i + 1) / (branches + 1)
        bx = base_x + lean * t
        by = base_y + (top_y - base_y) * t
        side = 1 if i % 2 == 0 else -1
        length = min(w, h) * rng.uniform(0.12, 0.24) * (1.0 - t * 0.5)
        angle = math.radians(rng.uniform(20, 50)) * side
        ex = bx + length * math.cos(angle) * side
        ey = by - length * math.sin(abs(angle))
        tone = rng.randint(40, 100)
        draw.line([(bx, by), (ex, ey)], fill=tone, width=3)
        lr = rng.randint(6, 14)
        draw.ellipse([ex - lr, ey - lr, ex + lr, ey + lr], outline=tone, width=3)
    draw.ellipse(
        [base_x + lean - 6, top_y - 6, base_x + lean + 6, top_y + 6], fill=20
    )


def _lattice(draw: ImageDraw.ImageDraw, size: tuple[int, int], rng: random.Random) -> None:
    w, h = size
    step = rng.choice([24, 32, 40])
    for gx in range(step, w, step):
        for gy in range(step, h, step):
            if rng.random() < 0.25:
                continue
            r = rng.randint(2, max(3, step // 4))
            tone = rng.randint(25, 140)
            if rng.random() < 0.2:
                draw.rectangle([gx - r, gy - r, gx + r, gy + r], outline=tone, width=2)
            else:
                draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=tone)


_PAINTERS = {
    "bloom": _bloom,
    "nucleus": _nucleus,
    "sprout": _sprout,
    "lattice": _lattice,
}


def generate_art(seed: str, motif: Motif, size: tuple[int, int] = (640, 480)) -> bytes:
    """Render a grayscale PNG for the seed/motif pair. Deterministic."""
    rng = _rng(f"{motif}:{seed}")
    im = Image.new("L", size, color=245)
    draw = ImageDraw.Draw(im)
    _field(draw, size, rng)
    _PAINTERS[motif](draw, size, rng)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def generate_processed_art(
    seed: str,
    motif: Motif,
    *,
    effect: images.ImageEffect = "dither",
    size: tuple[int, int] = (640, 480),
    contrast: float = 1.8,
    brightness: int = 0,
    scale: float = 0.4,
) -> bytes:
    """Generate art and push it through the platform's effect pipeline."""
    raw = generate_art(seed, motif, size)
    return images.process(raw, effect, contrast=contrast, brightness=brightness, scale=scale)
