"""When each note is pressed and released -- exactly as the Jev harness
times a song (play.py song_timing_), so what you preview is what plays.

With a sane "bpm" and "beats" the notes keep the song's rhythm, slowed
evenly if the shortest note is too short to sound; without them every note
is even. Nothing runs past the song's time cap.
"""
from __future__ import annotations

from .pitch import note_ok, REST

HOLD_FRACTION = 0.875   # of each note's length, the button is down
MIN_GAP = 0.05          # seconds between notes, at least
MIN_HOLD = 0.08         # seconds a note is held, at least
MAX_SECONDS = 20.0      # default cap on a song's length
MAX_SECONDS_ANY = 90.0  # never longer, whatever the entry says
MAX_NOTES = 400


def _sounded(note: str) -> bool:
    return note != REST and note_ok(note)


def song_timing(entry: dict) -> list[tuple[str | None, float, float]]:
    """(note, hold_s, gap_s) for each note of a song entry; note None is a
    rest (nothing pressed for hold_s + gap_s)."""
    notes = [str(n) for n in (entry.get("notes") or [])][:MAX_NOTES]
    bpm, beats = entry.get("bpm"), entry.get("beats")
    durs = None
    try:
        if (bpm is not None and isinstance(beats, list) and len(beats) == len(notes)
                and not isinstance(bpm, bool)):
            bpm_f = float(bpm)
            b_f = [float(b) for b in beats]
            if 20.0 <= bpm_f <= 400.0 and b_f and all(0.0 < b <= 16.0 for b in b_f):
                durs = [b * 60.0 / bpm_f for b in b_f]
    except (TypeError, ValueError):
        durs = None
    out: list[tuple[str | None, float, float]] = []
    if durs is None:
        hold = 0.22 if len(notes) > 8 else 0.32
        out = [(n if _sounded(n) else None, hold, 0.08) for n in notes]
    else:
        sounded = [d for n, d in zip(notes, durs) if _sounded(n)]
        shortest = min(sounded) if sounded else MIN_HOLD + MIN_GAP
        scale = max(1.0, (MIN_HOLD + MIN_GAP) / shortest, MIN_HOLD / (HOLD_FRACTION * shortest))
        for n, d in zip(notes, durs):
            d *= scale
            if not _sounded(n):
                out.append((None, d, 0.0))
                continue
            gap = max(d * (1.0 - HOLD_FRACTION), MIN_GAP)
            out.append((n, max(d - gap, MIN_HOLD), gap))
    try:
        cap = min(float(entry.get("max_seconds") or MAX_SECONDS), MAX_SECONDS_ANY)
    except (TypeError, ValueError, AttributeError):
        cap = MAX_SECONDS
    kept, total = [], 0.0
    for n, h, g in out:
        if total + h + g > cap:
            break
        kept.append((n, h, g))
        total += h + g
    return kept


def total_seconds(entry: dict) -> float:
    return sum(h + g for _, h, g in song_timing(entry))
