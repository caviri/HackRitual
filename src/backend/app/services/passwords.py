"""
Access-password generation — the keys to the ritual.

Each user holds a single generated access password (`word-word-NNNN`) that is
both their credential and their identity at the gate: login is a lookup on the
unique `users.access_password` column. Passwords are admin-distributed by hand
(copy/mailto from the admin panel), so they are stored in plaintext and remain
visible to the keeper. The per-IP login throttle in `services/auth.py` is what
keeps the ~27 bits of entropy honest.
"""

from __future__ import annotations

import secrets

from sqlalchemy.orm import Session

# Short, unambiguous, lowercase words — easy to read aloud and to retype.
WORDS = (
    "amber", "anvil", "arrow", "ashen", "aster", "birch", "blade", "bloom",
    "bolt", "briar", "brook", "candle", "cedar", "chime", "cinder", "cliff",
    "cloud", "clover", "coal", "comet", "coral", "crane", "crow", "crypt",
    "dawn", "delta", "drift", "dusk", "ember", "fable", "falcon", "fern",
    "field", "flint", "forge", "fox", "frost", "gale", "garnet", "glade",
    "gleam", "glyph", "grove", "hare", "hawk", "hazel", "heron", "hollow",
    "ibis", "iris", "ivory", "ivy", "jasper", "juniper", "kestrel", "knoll",
    "lantern", "larch", "lark", "lichen", "linden", "lotus", "lumen", "lynx",
    "maple", "marsh", "meadow", "mist", "moss", "moth", "newt", "north",
    "oak", "ochre", "onyx", "opal", "orchid", "osprey", "otter", "owl",
    "pebble", "pine", "plume", "pond", "poppy", "prism", "quail", "quartz",
    "quill", "raven", "reed", "ridge", "river", "robin", "rowan", "rune",
    "sable", "sage", "shale", "shore", "sigil", "slate", "sparrow", "spire",
    "spruce", "stone", "storm", "swift", "thistle", "thorn", "tide", "torch",
    "trout", "tulip", "umber", "vale", "vesper", "violet", "vixen", "wander",
    "wave", "willow", "wren", "yarrow", "zephyr",
)


def generate_password() -> str:
    """Return a fresh `word-word-NNNN` access password."""
    a = secrets.choice(WORDS)
    b = secrets.choice(WORDS)
    n = secrets.randbelow(9000) + 1000
    return f"{a}-{b}-{n}"


def generate_unique_password(db: Session) -> str:
    """Generate a password no existing user holds. The unique index on
    `users.access_password` is the backstop for the race window."""
    from app.models.user import User

    password = generate_password()
    while db.query(User).filter(User.access_password == password).first():
        password = generate_password()
    return password
