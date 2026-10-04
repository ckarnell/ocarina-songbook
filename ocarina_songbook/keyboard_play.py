"""Play a song into your own game (Ship of Harkinian, or an N64 emulator)
by pressing the keys your controller is mapped to.

Take out the ocarina in the game first, focus the game window, then run
`ocarina play songs/x.json --keys keys.json`. It counts down 3 seconds so
you can switch windows.

keys.json maps each ocarina button and modifier to a key, as set in your
game's controller settings (letters, or pynput names such as "up"):

    {"A": "x", "C_UP": "i", "C_DOWN": "k", "C_LEFT": "j", "C_RIGHT": "l",
     "R": "o", "Z": "z", "UP": "up", "DOWN": "down"}

UP / DOWN are the control stick held up / down (a two-semitone bend).
Needs `pip install pynput` (and, on macOS, Accessibility permission for
your terminal).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .timing import song_timing

NEEDED = ("A", "C_UP", "C_DOWN", "C_LEFT", "C_RIGHT", "R", "Z", "UP", "DOWN")


def load_keys(path: Path | str) -> dict[str, str]:
    keys = json.loads(Path(path).read_text())
    missing = [k for k in NEEDED if k not in keys]
    if missing:
        raise ValueError(f"{path}: no key for {missing}")
    return keys


def _key(name: str):
    from pynput.keyboard import Key  # imported here: optional dependency
    return getattr(Key, name) if len(name) > 1 else name


def play(entry: dict, keys: dict[str, str], countdown: float = 3.0) -> None:
    from pynput.keyboard import Controller
    kb = Controller()
    time.sleep(countdown)
    t0 = time.monotonic()
    at = 0.0
    for note, hold, gap in song_timing(entry):
        if note is None:
            at += hold + gap
            continue
        while time.monotonic() < t0 + at:
            time.sleep(0.001)
        button, *mods = note.split("+")
        # Modifiers down on the same moment as the button, held with it: a
        # modifier pressed alone first would sound as a note.
        down = [_key(keys[m]) for m in mods] + [_key(keys[button])]
        for k in down:
            kb.press(k)
        end = t0 + at + hold
        while time.monotonic() < end:
            time.sleep(0.001)
        for k in reversed(down):
            kb.release(k)
        at += hold + gap
