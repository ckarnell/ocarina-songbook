"""The band under a song, as the stream plays it: drums (a "drums" style),
the "bass" line and up to 3 more "parts", on the same clock as the ocarina
notes -- ported from the stream harness (ootjev/drums.py) so a preview here
sounds like the stream. Plus the melody itself on an ocarina voice (GM 79).

    from ocarina_songbook.band import song_midi
    open("song.mid", "wb").write(song_midi(entry))

Stdlib only. Render the MIDI with any General MIDI SoundFont (preview.py's
render_band, with FluidSynth); the stream uses one built from Ocarina of
Time's own samples (oot_soundfont.py), laid out on the same GM programs.
"""
from __future__ import annotations

import math
import struct

from .pitch import pitch_of
from .timing import song_timing

KICK, SIDESTICK, SNARE, CLAP, HAT, OPEN_HAT, CRASH, RIDE, TOM_LO, TOM_HI, TOM_FLOOR = (
    36, 37, 38, 39, 42, 46, 49, 51, 45, 50, 41)

# One bar of each groove: (bar length in beats, [(beat, key, velocity)]).
# The drum kit's keys: a style none of whose hits is one of these is silent
# (a clock for the band), and gets no ending accent.
KIT_KEYS = frozenset({KICK, SIDESTICK, SNARE, CLAP, HAT, OPEN_HAT, CRASH, RIDE,
                      TOM_LO, TOM_HI, TOM_FLOOR})
STYLES: dict[str, tuple[float, list[tuple[float, int, int]]]] = {
    "rock": (4, [(0, KICK, 110), (1, SNARE, 100), (2, KICK, 105), (2.5, KICK, 80), (3, SNARE, 100)]
             + [(b / 2, HAT, 70 if b % 2 else 85) for b in range(8)]),
    "ballad": (4, [(0, KICK, 90), (2, SIDESTICK, 80), (2.5, KICK, 60)]
               + [(float(b), HAT, 55) for b in range(4)]),
    "shuffle": (4, [(0, KICK, 105), (1, SNARE, 95), (2, KICK, 100), (3, SNARE, 95)]
                + [(b + f, HAT, 80 if f == 0 else 60) for b in range(4) for f in (0, 2 / 3)]),
    "waltz": (3, [(0, KICK, 100), (1, HAT, 70), (2, HAT, 70), (1, SIDESTICK, 60), (2, SIDESTICK, 60)]),
    "sixeight": (3, [(0, KICK, 95), (1.5, SIDESTICK, 75)] + [(b / 2, HAT, 60) for b in range(6)]),
    "march": (2, [(0, KICK, 110), (1, SNARE, 100), (1.5, SNARE, 70), (1.75, SNARE, 70)]
              + [(0.5, HAT, 60), (1.5, HAT, 60)]),
    "stomp": (2, [(0, KICK, 120), (0.5, KICK, 120), (1, CLAP, 120)]),
    "disco": (4, [(float(b), KICK, 110) for b in range(4)] + [(1, CLAP, 90), (3, CLAP, 90)]
              + [(b + 0.5, OPEN_HAT, 75) for b in range(4)]),
    # Low and grand (krazy_kev: "drums for some of the lower registers"):
    # bass drum and floor toms like timpani, a crash every two bars.
    "orchestral": (8, [(0, CRASH, 95), (0, KICK, 120), (0, TOM_FLOOR, 115), (2, TOM_FLOOR, 90),
                       (3.5, TOM_FLOOR, 75), (4, KICK, 110), (4, TOM_FLOOR, 105), (6, TOM_FLOOR, 90),
                       (7, TOM_LO, 80), (7.5, TOM_LO, 90)]),
}





def _spec(entry: dict) -> dict:
    d = entry.get("drums")
    if isinstance(d, str):
        d = {"style": d}
    return d if isinstance(d, dict) else {}


def _has_rhythm(entry: dict, n: int) -> bool:
    beats = entry.get("beats")
    return isinstance(beats, list) and len(beats) >= n > 0 and bool(entry.get("bpm"))


def plan(timing: list, entry: dict) -> tuple[list[tuple[float, int, int]], float]:
    """The drum hits (seconds from the first note, key, velocity) and the
    intro's length in seconds (drums alone before the first note).

    timing is song_timing_'s [(note or None, hold_s, gap_s)]: the notes as
    they will really be pressed."""
    spec = _spec(entry)
    style = str(spec.get("style") or "")
    # Opt-in (Poodleskirt, 2026-09-29, after chat found drums on every song
    # too much): a song without a "drums" field plays ocarina-only, unless
    # this request asks for drums (navi_play_song.py --drums).
    if not spec:
        return [], 0.0
    if style == "none" or not timing:
        return [], 0.0
    onsets, t = [], 0.0
    for _n, h, g in timing:
        onsets.append(t)
        t += h + g
    total = t
    if not _has_rhythm(entry, len(timing)):
        # Even notes: a soft pulse on the notes themselves.
        hits = [(o, HAT, 60) for o in onsets] + [(o, KICK, 85) for o in onsets[::4]]
        return sorted(hits + [(onsets[-1], CRASH, 80)]), 0.0
    beats = [float(b) for b in entry["beats"][: len(timing)]]
    spb = total / sum(beats)                     # seconds a beat, slow-downs included
    all_styles = STYLES
    bar_len, bar = all_styles.get(style) or all_styles["rock"]
    try:
        intro_beats = max(0.0, min(16.0, float(spec.get("intro_beats") or 0)))
        start = float(spec.get("start") or 0)
    except (TypeError, ValueError):
        intro_beats, start = 0.0, 0.0
    intro_s = intro_beats * spb
    hits = []
    first_bar = start - bar_len * math.ceil((start + intro_beats) / bar_len)
    b0 = first_bar
    while b0 < total / spb:
        for pos, key, vel in bar:
            beat = b0 + pos
            if -intro_beats - 1e-6 <= beat < total / spb - 1e-6:
                hits.append((beat * spb, key, vel))
        b0 += bar_len
    # The ending accent (and the intro's crash): not when the song opts out
    # ("drums": {"ending": false}) or its style has no audible kit at all --
    # a silent clock style kept for the band, as Giorno's Theme asked for no
    # drums (code8, via Bongo Bongo, 2026-10-01), still crashed at the end.
    audible_ = any(key in KIT_KEYS and vel > 0 for _p, key, vel in bar)
    if spec.get("ending", True) is not False and audible_:
        last = onsets[-1]
        hits.append((last, CRASH, 100))
        hits.append((last, KICK, 110))
        if intro_beats:
            hits.append((-intro_s, CRASH, 90))
    return sorted(hits), intro_s


def _vlq(n: int) -> bytes:
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, 0x80 | (n & 0x7F))
        n >>= 7
    return bytes(out)


def _part_plan(timing: list, entry: dict, spec) -> tuple[list[tuple[float, int, float, int]], int]:
    """One melodic part's notes (seconds from the first note, MIDI pitch,
    length in seconds, velocity) and its GM program, timed with the same
    seconds-a-beat as plan() so it sits exactly on the drums. Notes before
    the intro or after the song's end are dropped; one running past the end
    is cut there."""
    if not isinstance(spec, dict) or not timing or not _has_rhythm(entry, len(timing)):
        return [], 33
    try:
        program = max(0, min(127, int(spec.get("program", 33))))
        vel = max(1, min(127, int(spec.get("velocity", 95))))
    except (TypeError, ValueError):
        return [], 33
    total = sum(h + g for _n, h, g in timing)
    spb = total / sum(float(x) for x in entry["beats"][: len(timing)])
    _hits, intro_s = plan(timing, entry)
    out = []
    for n in spec.get("notes") or []:
        try:
            beat, pitch, length = float(n[0]), int(n[1]), float(n[2])
        except (TypeError, ValueError, IndexError):
            continue
        t, d = beat * spb, length * spb
        if t < -intro_s - 1e-6 or t >= total - 1e-6 or d <= 0 or not 0 <= pitch <= 127:
            continue
        out.append((t, pitch, min(d, total - t), vel))
    return sorted(out), program


def bass_plan(timing: list, entry: dict) -> tuple[list[tuple[float, int, float, int]], int]:
    """The song's "bass" part (see _part_plan)."""
    return _part_plan(timing, entry, entry.get("bass"))


# Melodic MIDI channels for "parts" (the bass has channel 1; 10 is drums).
PART_CHANNELS = (1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14)


def parts_plan(timing: list, entry: dict) -> list[tuple[int, int, list]]:
    """The song's extra instrument parts ("parts": [{"program", "velocity",
    "notes"}, ...]) as (MIDI channel index, program, notes), each timed like
    the bass on the drums' clock. At most 14 parts."""
    ps = entry.get("parts")
    if not isinstance(ps, list):
        return []
    out = []
    for ch, spec in zip(PART_CHANNELS, ps):
        notes, program = _part_plan(timing, entry, spec)
        if notes:
            out.append((ch, program, notes))
    return out


def midi_bytes(hits: list[tuple[float, int, int]], lead_s: float,
               bass: list[tuple[float, int, float, int]] | None = None,
               program: int = 33,
               parts: list[tuple[int, int, list]] | None = None) -> bytes:
    """A type-0 MIDI file of the hits on channel 10, at 60 BPM so a beat is
    a second; everything is moved later by lead_s (hits at negative times,
    the intro, become the start of the file). A bass line (bass_plan) goes
    on channel 1 with its program."""
    div = 480
    ev = []
    for t, key, vel in hits:
        tick = max(0, int(round((t + lead_s) * div)))
        ev.append((tick, 1, bytes([0x99, key, max(1, min(127, vel))])))
        ev.append((tick + 60, 0, bytes([0x89, key, 0])))
    melodic = ([(0, program, bass)] if bass else []) + list(parts or [])
    for ch, prog, notes in melodic:
        ev.append((0, -1, bytes([0xC0 | ch, prog & 0x7F])))
        for t, pitch, d, vel in notes:
            tick = max(0, int(round((t + lead_s) * div)))
            # Released a touch early, so a repeated note is struck again.
            off = tick + max(1, int(round(d * div * 0.9)))
            ev.append((tick, 1, bytes([0x90 | ch, pitch, max(1, min(127, vel))])))
            ev.append((off, 0, bytes([0x80 | ch, pitch, 0])))
    ev.sort(key=lambda e: (e[0], e[1]))
    trk = b"\x00\xff\x51\x03" + (1_000_000).to_bytes(3, "big")
    last = 0
    for tick, _o, data in ev:
        trk += _vlq(tick - last) + data
        last = tick
    trk += b"\x00\xff\x2f\x00"
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, div) + b"MTrk" + struct.pack(">I", len(trk)) + trk



OCARINA_PROGRAM = 79
MELODY_CHANNEL = 15


def melody_plan(timing: list) -> list[tuple[float, int, float, int]]:
    """The ocarina notes (seconds, MIDI pitch, held seconds, velocity)."""
    out, t = [], 0.0
    for n, h, g in timing:
        p = pitch_of(n) if n else None
        if p is not None:
            out.append((t, p, h, 110))
        t += h + g
    return out


def song_midi(entry: dict, melody: bool = True) -> bytes:
    """The whole song as a MIDI file: the band, and (melody) the ocarina
    line on channel 16 with GM program 79."""
    timing = song_timing(entry)
    hits, intro_s = plan(timing, entry)
    bass, program = bass_plan(timing, entry)
    parts = parts_plan(timing, entry)
    if melody:
        mel = melody_plan(timing)
        if mel:
            parts = parts + [(MELODY_CHANNEL, OCARINA_PROGRAM, mel)]
    return midi_bytes(hits, intro_s, bass, program, parts)
