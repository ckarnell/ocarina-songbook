"""Notes on Link's ocarina: pitch names, MIDI numbers and button spellings.

The ocarina plays five buttons, each one fixed pitch, and four modifiers
bend them (vanilla Ocarina of Time, so this works on any version):

    A = D4, C_DOWN = F4, C_RIGHT = A4, C_LEFT = B4, C_UP = D5
    R = one semitone up, Z = one semitone down,
    UP / DOWN (control stick) = two semitones up / down

A note is written BUTTON(+MODIFIER)*, e.g. "C_DOWN+R" (F#4). Its range is
B3..F5 (MIDI 59..77). SPELLINGS gives every pitch in that range its
simplest spelling: a plain button beats a bend, one modifier beats two,
R/Z beat a stick bend.
"""
from __future__ import annotations

import re

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = {"Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B"}

BUTTONS = ("A", "C_UP", "C_DOWN", "C_LEFT", "C_RIGHT")
MODIFIERS = ("R", "Z", "UP", "DOWN")
REST = "REST"

BUTTON_PITCH = {"A": 62, "C_DOWN": 65, "C_RIGHT": 69, "C_LEFT": 71, "C_UP": 74}
MODIFIER_SHIFT = {"R": 1, "Z": -1, "UP": 2, "DOWN": -2}

OCARINA_LOW = 59   # B3
OCARINA_HIGH = 77  # F5
SPELLINGS = {
    59: "A+DOWN+Z",    # B3
    60: "A+DOWN",      # C4
    61: "A+Z",         # C#4
    62: "A",           # D4
    63: "A+R",         # D#4
    64: "A+UP",        # E4
    65: "C_DOWN",      # F4
    66: "C_DOWN+R",    # F#4
    67: "C_DOWN+UP",   # G4
    68: "C_RIGHT+Z",   # G#4
    69: "C_RIGHT",     # A4
    70: "C_LEFT+Z",    # A#4
    71: "C_LEFT",      # B4
    72: "C_UP+DOWN",   # C5
    73: "C_UP+Z",      # C#5
    74: "C_UP",        # D5
    75: "C_UP+R",      # D#5
    76: "C_UP+UP",     # E5
    77: "C_UP+UP+R",   # F5
}

_LETTER_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d)$")


def midi(letter: str) -> int:
    """'G#4' or 'Ab4' -> 68 (C4 = 60)."""
    m = _LETTER_RE.match(letter.strip())
    if not m:
        raise ValueError(f"not a note with an octave: {letter!r} (write it like D4, F#4, Bb3)")
    name = m.group(1).upper() + m.group(2)
    name = FLATS.get(name, name)
    return 12 * (int(m.group(3)) + 1) + NOTE_NAMES.index(name)


def letter_of(m: int) -> str:
    """68 -> 'G#4'."""
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


def note_ok(note: str) -> bool:
    """A playable note string: BUTTON(+MODIFIER)*, or REST."""
    if note == REST:
        return True
    key, *mods = str(note).split("+")
    return key in BUTTONS and all(m in MODIFIERS for m in mods)


def pitch_of(note: str) -> int | None:
    """The MIDI pitch a note string sounds (None for a rest or a bad note)."""
    if note == REST or not note_ok(note):
        return None
    key, *mods = note.split("+")
    return BUTTON_PITCH[key] + sum(MODIFIER_SHIFT[m] for m in mods)


def spell(m: int) -> str | None:
    """The ocarina spelling of MIDI note m, or None when it is out of range."""
    return SPELLINGS.get(m)


def spelling_cost(s: str) -> float:
    """Modifiers a spelling needs; a stick bend counts a little more than R/Z."""
    return sum(1.2 if mod in ("UP", "DOWN") else 1.0 for mod in s.split("+")[1:])


def best_shift(notes: list[int]) -> int:
    """The transposition (semitones) that fits every note in B3..F5 with the
    fewest modifiers; ties go to the smallest move."""
    if not notes:
        return 0
    lo, hi = min(notes), max(notes)
    shifts = range(OCARINA_LOW - lo, OCARINA_HIGH - hi + 1)
    if not shifts:
        raise ValueError(
            f"the tune spans {letter_of(lo)}..{letter_of(hi)}, wider than the "
            f"ocarina's B3..F5 (18 semitones): pick a shorter passage or move one "
            f"phrase by an octave")
    return min(shifts, key=lambda s: (sum(spelling_cost(SPELLINGS[n + s]) for n in notes), abs(s)))


def parse_letters(text: str) -> list[int | None]:
    """'D4 F#4 A4 R B4 | ...' -> MIDI numbers, None for a rest (R or REST).
    Bar lines (|) are ignored."""
    out: list[int | None] = []
    for tok in text.replace("|", " ").split():
        if tok.upper() in ("R", "REST", "-"):
            out.append(None)
        else:
            out.append(midi(tok))
    return out
