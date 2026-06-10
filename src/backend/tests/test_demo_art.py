"""Demo art tests — determinism, validity, the four motifs."""

from __future__ import annotations

import io


def test_same_seed_same_bytes():
    from app.services.demo_art import generate_art

    a = generate_art("mycelium-mesh", "bloom")
    b = generate_art("mycelium-mesh", "bloom")
    assert a == b


def test_different_seeds_differ():
    from app.services.demo_art import generate_art

    assert generate_art("a", "bloom") != generate_art("b", "bloom")
    assert generate_art("a", "bloom") != generate_art("a", "lattice")


def test_all_motifs_render_valid_png():
    from PIL import Image

    from app.services.demo_art import MOTIFS, generate_art

    for motif in MOTIFS:
        data = generate_art(f"seed-{motif}", motif, size=(320, 240))
        im = Image.open(io.BytesIO(data))
        assert im.format == "PNG"
        assert im.size == (320, 240)


def test_processed_art_is_monochrome_png():
    from PIL import Image

    from app.services.demo_art import generate_processed_art

    data = generate_processed_art("portrait:ada@demo.rite", "sprout", size=(480, 480))
    im = Image.open(io.BytesIO(data)).convert("L")
    tones = {p for p in im.getdata()}
    # Dithered output is two-tone (or nearly so after PNG round-trip).
    assert len(tones) <= 4


def test_processed_art_deterministic():
    from app.services.demo_art import generate_processed_art

    a = generate_processed_art("cover:lichen-loom", "nucleus")
    b = generate_processed_art("cover:lichen-loom", "nucleus")
    assert a == b
