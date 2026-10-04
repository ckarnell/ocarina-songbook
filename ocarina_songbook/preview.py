"""Hear a song before you send it: renders the ocarina line to a WAV file
with a simple flute-like tone, timed exactly as the harness plays it.
Standard library only. (The harness adds its band -- drums, bass, parts --
on stream; this preview is the melody.)
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from .pitch import pitch_of
from .timing import song_timing

RATE = 22050


def _tone(freq: float, seconds: float, volume: float = 0.35) -> list[float]:
    n = max(1, int(seconds * RATE))
    attack, release = int(0.015 * RATE), int(0.04 * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        vib = 1.0 + 0.004 * math.sin(2 * math.pi * 5.5 * t)
        ph = 2 * math.pi * freq * vib * t
        s = math.sin(ph) + 0.18 * math.sin(2 * ph) + 0.06 * math.sin(3 * ph)
        env = min(1.0, i / attack if attack else 1.0, (n - i) / release if release else 1.0)
        out.append(volume * env * s / 1.24)
    return out


def render(entry: dict, path: Path | str) -> float:
    """Write the song to a mono 16-bit WAV; returns its length in seconds."""
    samples: list[float] = []
    for note, hold, gap in song_timing(entry):
        p = pitch_of(note) if note else None
        if p is None:
            samples += [0.0] * int((hold + gap) * RATE)
            continue
        freq = 440.0 * 2 ** ((p - 69) / 12)
        samples += _tone(freq, hold)
        samples += [0.0] * int(gap * RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767))
                               for s in samples))
    return len(samples) / RATE
