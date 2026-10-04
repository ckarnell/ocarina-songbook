"""Checks a contributed song file before it can be merged and played.

The same checks run on your machine (`ocarina validate`), in CI on every
pull request, and in the Jev harness before it loads a song -- so a song
that passes here is exactly what plays on stream.

A song lives in songs/<slug>.json; its key in the harness is
PLAY_<SLUG> (songs/never_gonna.json -> PLAY_NEVER_GONNA).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .pitch import REST, note_ok
from .timing import MAX_SECONDS, song_timing, total_seconds

SLUG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{2,40}$")
URL_RE = re.compile(r"^https?://[^\s]+$")

# A contributed song is at most this long (the harness allows up to 90 s,
# but a long one has to be asked for).
CONTRIB_MAX_SECONDS = 45.0
MAX_NOTES = 240
MAX_TEXT = 300

# The drum grooves every copy of the harness has (ootjev/drums.py STYLES).
DRUM_STYLES = ("rock", "ballad", "shuffle", "waltz", "sixeight", "march", "stomp",
               "disco", "orchestral", "none")
# The ocarina stays the loudest, clearest voice (a full band once drowned
# it on stream): at most 3 extra parts, and quieter than the ocarina.
MAX_PARTS = 3
MAX_VELOCITY = {"bass": 84, "parts": 66}
MAX_PART_NOTES = 600

REQUIRED = ("name", "artist", "contributor", "notes", "bpm", "beats", "letters", "key",
            "part", "sources")
OPTIONAL = ("drums", "bass", "parts", "max_seconds")
FIELD_HELP = {
    "name": "the song's title",
    "artist": "who made the original",
    "contributor": "your handle, credited on stream (letters, digits, _)",
    "notes": "the ocarina notes, BUTTON(+MOD)* or REST",
    "bpm": "tempo in beats a minute",
    "beats": "each note's length in beats, one per note",
    "letters": "the melody in note names, as you transcribed it",
    "key": "the key it is in on the ocarina (and the original's)",
    "part": "which part of the song this is (verse, chorus hook...)",
    "sources": "links to the transcription(s) you worked from",
}

RESERVED_FILE = Path(__file__).with_name("reserved_keys.txt")


def reserved_keys() -> set[str]:
    try:
        return {k.strip() for k in RESERVED_FILE.read_text().split() if k.strip()}
    except OSError:
        return set()


def key_for(path: Path | str) -> str:
    return "PLAY_" + Path(path).stem.upper()


def _text_ok(v: Any, limit: int = MAX_TEXT) -> bool:
    return (isinstance(v, str) and v.strip() != "" and len(v) <= limit
            and not any(ord(c) < 32 for c in v))


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def _note_list_errors(where: str, notes: Any) -> list[str]:
    errs = []
    if not isinstance(notes, list) or not notes:
        return [f"{where}.notes must be a non-empty list of [beat, midi_pitch, length_beats]"]
    if len(notes) > MAX_PART_NOTES:
        errs.append(f"{where}.notes has {len(notes)} notes; at most {MAX_PART_NOTES}")
    for i, n in enumerate(notes):
        ok = (isinstance(n, list) and len(n) == 3 and _num(n[0]) is not None
              and isinstance(n[1], int) and not isinstance(n[1], bool) and 0 <= n[1] <= 127
              and _num(n[2]) is not None and 0 < n[2] <= 16)
        if not ok:
            errs.append(f"{where}.notes[{i}] = {n!r}: want [beat, midi pitch 0-127, length 0-16 beats]")
            break
    return errs


def _instrument_errors(where: str, v: Any, max_vel: int = 127) -> list[str]:
    if not isinstance(v, dict):
        return [f"{where} must be an object {{program, velocity, notes}}"]
    errs = []
    extra = set(v) - {"program", "velocity", "notes"}
    if extra:
        errs.append(f"{where}: unknown field(s) {sorted(extra)}")
    prog = v.get("program", 33)
    if not isinstance(prog, int) or isinstance(prog, bool) or not 0 <= prog <= 127:
        errs.append(f"{where}.program must be a General MIDI program 0-127")
    vel = v.get("velocity", min(80, max_vel))
    if not isinstance(vel, int) or isinstance(vel, bool) or not 1 <= vel <= max_vel:
        errs.append(f"{where}.velocity must be 1-{max_vel} (the ocarina has to stay on top)")
    return errs + _note_list_errors(where, v.get("notes"))


def validate_entry(key: str, entry: Any) -> list[str]:
    """Every problem with one song, as sentences; [] when it can be merged."""
    if not isinstance(entry, dict):
        return ["the file must hold one JSON object (the song)"]
    errs: list[str] = []
    if key in reserved_keys():
        errs.append(f"{key} is already one of Jev's songs: pick another file name")
    for f in REQUIRED:
        if f not in entry:
            errs.append(f"missing \"{f}\": {FIELD_HELP[f]}")
    unknown = set(entry) - set(REQUIRED) - set(OPTIONAL)
    if unknown:
        errs.append(f"unknown field(s) {sorted(unknown)}; allowed: {list(REQUIRED + OPTIONAL)}")
    for f in ("name", "artist"):
        if f in entry and not _text_ok(entry[f], 80):
            errs.append(f"\"{f}\" must be one line of text, at most 80 characters")
    for f in ("letters", "key", "part"):
        if f in entry and not _text_ok(entry[f], 2000 if f == "letters" else MAX_TEXT):
            errs.append(f"\"{f}\" must be text without line breaks")
    if "contributor" in entry and not (isinstance(entry["contributor"], str)
                                       and HANDLE_RE.match(entry["contributor"])):
        errs.append("\"contributor\" must be a handle: 2-40 letters, digits or _")
    src = entry.get("sources")
    if "sources" in entry and not (isinstance(src, list) and src
                                   and all(isinstance(u, str) and URL_RE.match(u) for u in src)):
        errs.append("\"sources\" must be a list of http(s) links to the transcriptions you used")

    notes = entry.get("notes")
    if "notes" in entry:
        if not isinstance(notes, list) or not 2 <= len(notes) <= MAX_NOTES:
            errs.append(f"\"notes\" must be a list of 2-{MAX_NOTES} notes")
            notes = None
        else:
            bad = [n for n in notes if not (isinstance(n, str) and note_ok(n))]
            if bad:
                errs.append(f"not ocarina notes: {bad[:5]} (write BUTTON(+R/Z/UP/DOWN) or REST; "
                            f"buttons A, C_UP, C_DOWN, C_LEFT, C_RIGHT)")
            elif all(n == REST for n in notes):
                errs.append("\"notes\" has no sounded note")
    bpm = _num(entry.get("bpm"))
    if "bpm" in entry and (bpm is None or not 20 <= bpm <= 400):
        errs.append("\"bpm\" must be a number from 20 to 400")
    beats = entry.get("beats")
    if "beats" in entry:
        if not isinstance(beats, list) or not all(
                _num(b) is not None and 0 < b <= 16 for b in beats):
            errs.append("\"beats\" must be a list of note lengths, each more than 0 and at most 16")
        elif isinstance(notes, list) and len(beats) != len(notes):
            errs.append(f"\"beats\" has {len(beats)} lengths for {len(notes)} notes: one each")

    if "max_seconds" in entry:
        ms = _num(entry["max_seconds"])
        if ms is None or not 5 <= ms <= CONTRIB_MAX_SECONDS:
            errs.append(f"\"max_seconds\" must be 5-{CONTRIB_MAX_SECONDS:g}")

    d = entry.get("drums")
    if "drums" in entry:
        spec = {"style": d} if isinstance(d, str) else d
        if not isinstance(spec, dict) or spec.get("style") not in DRUM_STYLES:
            errs.append(f"\"drums\" must be one of {list(DRUM_STYLES)} or "
                        f"{{\"style\": ..., \"intro_beats\": n, \"start\": beat, \"ending\": bool}}")
        else:
            extra = set(spec) - {"style", "intro_beats", "start", "ending"}
            if extra:
                errs.append(f"\"drums\": unknown field(s) {sorted(extra)}")
            ib = spec.get("intro_beats", 0)
            if _num(ib) is None or not 0 <= ib <= 16:
                errs.append("\"drums\".intro_beats must be 0-16")
            if "start" in spec and _num(spec["start"]) is None:
                errs.append("\"drums\".start must be a number (a beat)")
            if "ending" in spec and not isinstance(spec["ending"], bool):
                errs.append("\"drums\".ending must be true or false")
    if "bass" in entry:
        errs += _instrument_errors("bass", entry["bass"], MAX_VELOCITY["bass"])
    if "parts" in entry:
        parts = entry["parts"]
        if not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS:
            errs.append(f"\"parts\" must be a list of 1-{MAX_PARTS} instruments")
        else:
            for i, p in enumerate(parts):
                errs += _instrument_errors(f"parts[{i}]", p, MAX_VELOCITY["parts"])

    if not errs:
        # The whole song must fit its time cap: past it the harness drops notes.
        cap = float(entry.get("max_seconds") or MAX_SECONDS)
        played = song_timing(entry)
        if len(played) < len(notes):
            errs.append(f"the song runs {_full_seconds(entry):.1f} s; it must fit in {cap:g} s "
                        f"(set \"max_seconds\" up to {CONTRIB_MAX_SECONDS:g}, or shorten it)")
    return errs


def _full_seconds(entry: dict) -> float:
    return total_seconds({**entry, "max_seconds": 10_000})


def validate_file(path: Path | str) -> list[str]:
    path = Path(path)
    if path.suffix != ".json":
        return [f"{path.name}: songs are .json files"]
    if not SLUG_RE.match(path.stem):
        return [f"{path.name}: the file name must be lowercase words joined by _ "
                f"(e.g. never_gonna.json)"]
    try:
        entry = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return [f"{path.name}: not valid JSON ({e})"]
    return [f"{path.name}: {e}" for e in validate_entry(key_for(path), entry)]


def validate_dir(folder: Path | str) -> list[str]:
    """Every song file in a folder, plus clashes between them."""
    errs: list[str] = []
    names: dict[str, str] = {}
    for p in sorted(Path(folder).glob("*.json")):
        errs += validate_file(p)
        try:
            n = str(json.loads(p.read_text()).get("name", "")).strip().lower()
        except (OSError, ValueError, AttributeError):
            continue
        if n and n in names:
            errs.append(f"{p.name}: \"{n}\" is already in {names[n]}")
        names.setdefault(n, p.name)
    return errs
