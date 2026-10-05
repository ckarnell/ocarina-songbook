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


# ---- the band ---------------------------------------------------------------
# The whole song as the stream plays it (band.song_midi), rendered with
# FluidSynth and a General MIDI SoundFont: the OoT one if you built it
# (`ocarina soundfont`), else a free GM one such as GeneralUser GS. Without
# FluidSynth the .mid is written, for any MIDI player.

SOUNDFONT_PLACES = (
    "~/Library/Audio/Sounds/Banks/OoT-Jev.sf2",
    "~/.local/share/soundfonts/OoT-Jev.sf2",
    "~/Library/Audio/Sounds/Banks/GeneralUser-GS.sf2",
    "~/.local/share/soundfonts/GeneralUser-GS.sf2",
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
)


def find_soundfont(given: str | None = None) -> Path | None:
    import os
    for p in ([given] if given else []) + list(SOUNDFONT_PLACES):
        q = Path(os.path.expanduser(p))
        if q.exists():
            return q
    return None


def render_band(entry: dict, path: Path | str, soundfont: str | None = None,
                melody: bool = True) -> tuple[Path, str]:
    """Write the song with its band: a WAV at `path` when FluidSynth and a
    SoundFont are found, else a .mid beside it. Returns (file, what font)."""
    import shutil
    import subprocess
    from .band import song_midi
    path = Path(path)
    mid = path.with_suffix(".mid")
    mid.write_bytes(song_midi(entry, melody=melody))
    fs = shutil.which("fluidsynth")
    sf = find_soundfont(soundfont)
    if not fs or not sf:
        return mid, ("no FluidSynth" if not fs else "no SoundFont found")
    subprocess.run([fs, "-ni", "-q", "-F", str(path), "-r", "44100", "-g", "0.8",
                    str(sf), str(mid)], check=True, timeout=120, capture_output=True)
    return path, sf.name
