"""From a melody in note names to an ocarina song entry.

You (or an AI) write the melody as you would read it off a transcription
-- "E4 E4 F4 G4 | G4 F4 E4 D4" with one length in beats per note -- and
this picks the transposition that needs the fewest modifiers and spells
every note for the ocarina. No hand-spelling of buttons.
"""
from __future__ import annotations

from .pitch import REST, best_shift, letter_of, parse_letters, spell


def spell_melody(letters: str, shift: int | None = None) -> tuple[list[str], int]:
    """(ocarina notes, semitones moved). `shift` forces a transposition."""
    pitches = parse_letters(letters)
    sounded = [p for p in pitches if p is not None]
    if not sounded:
        raise ValueError("the melody has no notes")
    s = best_shift(sounded) if shift is None else shift
    notes: list[str] = []
    for p in pitches:
        if p is None:
            notes.append(REST)
            continue
        n = spell(p + s)
        if n is None:
            raise ValueError(f"{letter_of(p)} moved {s:+d} is {letter_of(p + s)}, outside B3..F5")
        notes.append(n)
    return notes, s


def build_entry(*, name: str, artist: str, contributor: str, letters: str,
                beats: list[float], bpm: float, part: str, sources: list[str],
                shift: int | None = None, drums: str | dict | None = None,
                max_seconds: float | None = None) -> dict:
    """A complete song entry, ready for songs/<slug>.json."""
    notes, s = spell_melody(letters, shift)
    if len(beats) != len(notes):
        raise ValueError(f"{len(beats)} beat lengths for {len(notes)} notes: give one per note "
                         f"(rests included)")
    sounded = [p for p in parse_letters(letters) if p is not None]
    entry = {
        "name": name,
        "artist": artist,
        "contributor": contributor,
        "part": part,
        "key": (f"moved {s:+d} semitones onto the ocarina "
                f"({letter_of(min(sounded) + s)}..{letter_of(max(sounded) + s)})"),
        "letters": " ".join(letters.split()),
        "sources": list(sources),
        "bpm": bpm,
        "beats": list(beats),
        "notes": notes,
    }
    if drums is not None:
        entry["drums"] = drums
    if max_seconds is not None:
        entry["max_seconds"] = max_seconds
    return entry
