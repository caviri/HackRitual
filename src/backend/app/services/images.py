"""Server-side image processing — Floyd-Steinberg dither + halftone.

Both effects produce monochrome PNGs that read well after the platform's CSS
tints them via theme colors.

Tunable parameters:
  - contrast   (0.5–3.0, default 1.8) — pre-process histogram stretch
  - brightness (-50..+50, default 0)  — pre-process additive shift
  - scale      (0.1..1.0, default 0.4)— downsample BEFORE dithering; chunkier
                                        dither dots at lower values. Pair with
                                        `image-rendering: pixelated` in CSS to
                                        keep the upscale crisp.
  - cell       (3-12, halftone only)  — dot grid cell size in pixels

Pillow only — no ImageMagick.
"""

from __future__ import annotations

import io
from typing import Literal

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

ImageEffect = Literal["none", "dither", "halftone"]


def _normalise(im: Image.Image, max_side: int = 1024) -> Image.Image:
    """EXIF-rotate, RGB, bound the longer edge."""
    im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    longest = max(w, h)
    if longest > max_side:
        s = max_side / longest
        im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
    return im


def _downsample(im: Image.Image, scale: float, min_side: int = 64) -> Image.Image:
    """Reduce resolution by `scale` (0.1..1.0). Floor at min_side for legibility."""
    if scale >= 1.0:
        return im
    w, h = im.size
    new_w = max(min_side, int(w * scale))
    new_h = max(min_side, int(h * scale))
    return im.resize((new_w, new_h), Image.BILINEAR)


def _prepare(
    im: Image.Image,
    contrast: float = 1.8,
    brightness: int = 0,
) -> Image.Image:
    """Grayscale + brightness shift + histogram stretch + contrast.

    Auto-contrasts harder when contrast > 1 so the highlights/shadows are
    pushed before the dither error-diffusion runs.
    """
    gray = im.convert("L")
    if brightness:
        gray = Image.eval(gray, lambda p: max(0, min(255, p + brightness)))
    # cutoff stretches harder when contrast is dialed up
    cutoff = int(max(0.0, contrast - 1) * 8)
    gray = ImageOps.autocontrast(gray, cutoff=cutoff)
    if contrast != 1.0:
        gray = ImageEnhance.Contrast(gray).enhance(contrast)
    return gray


def apply_dither(
    data: bytes,
    contrast: float = 1.8,
    brightness: int = 0,
    scale: float = 0.4,
) -> bytes:
    """Floyd-Steinberg dither — chunky, visible 2-tone.

    Pre-downsamples by `scale` so each dither cell takes up multiple display
    pixels after the front-end's `image-rendering: pixelated` upscale.
    """
    src = _normalise(Image.open(io.BytesIO(data)), max_side=1024)
    src = _downsample(src, scale)
    prepared = _prepare(src, contrast=contrast, brightness=brightness)
    dithered = prepared.convert("1", dither=Image.FLOYDSTEINBERG)
    out = io.BytesIO()
    dithered.save(out, format="PNG", optimize=True)
    return out.getvalue()


def apply_halftone(
    data: bytes,
    contrast: float = 1.6,
    brightness: int = 0,
    cell: int = 6,
    scale: float = 1.0,
) -> bytes:
    """Newsprint-style halftone — each cell becomes a dot sized to brightness."""
    src = _normalise(Image.open(io.BytesIO(data)), max_side=1024)
    src = _downsample(src, scale)
    gray = _prepare(src, contrast=contrast, brightness=brightness)
    w, h = gray.size

    out = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(out)

    px = gray.load()
    if px is None:
        return data

    for y0 in range(0, h, cell):
        for x0 in range(0, w, cell):
            x1 = min(x0 + cell, w)
            y1 = min(y0 + cell, h)
            total = 0
            count = 0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    total += px[xx, yy]
                    count += 1
            if not count:
                continue
            avg = total / count
            darkness = 1.0 - (avg / 255)
            radius = darkness * (cell / 2)
            if radius < 0.3:
                continue
            cx = x0 + cell / 2
            cy = y0 + cell / 2
            draw.ellipse(
                [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                fill=0,
            )

    final = out.convert("1", dither=Image.NONE)
    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def apply_passthrough(data: bytes) -> bytes:
    """No-op effect, but still normalised + re-encoded as PNG for consistency."""
    src = _normalise(Image.open(io.BytesIO(data)))
    out = io.BytesIO()
    src.save(out, format="PNG", optimize=True)
    return out.getvalue()


def process(
    data: bytes,
    effect: ImageEffect,
    contrast: float = 1.8,
    brightness: int = 0,
    scale: float = 0.4,
) -> bytes:
    """Dispatch by effect name. Unknown values pass through unchanged."""
    if effect == "dither":
        return apply_dither(data, contrast=contrast, brightness=brightness, scale=scale)
    if effect == "halftone":
        return apply_halftone(data, contrast=contrast, brightness=brightness, scale=scale)
    if effect == "none":
        return apply_passthrough(data)
    return data
