"""ocarina -- make, check, hear and play songs for Link's ocarina.

    ocarina build --slug ode_to_joy --name "Ode to Joy" --artist "Beethoven" \\
        --contributor yourname --part "main theme" \\
        --letters "E4 E4 F4 G4 G4 F4 E4 D4" --beats "1 1 1 1 1 1 1 1" --bpm 120 \\
        --source https://example.com/sheet
    ocarina validate                     # every file in songs/
    ocarina validate songs/ode_to_joy.json
    ocarina preview songs/ode_to_joy.json   # writes ode_to_joy.wav
    ocarina play songs/ode_to_joy.json --keys keys.json   # into your own game
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import fetch as fetch_mod
from . import validate as v
from .build import build_entry
from .timing import total_seconds

SONGS = Path("songs")


def _beats(text: str) -> list[float]:
    return [float(b) for b in text.replace(",", " ").replace("|", " ").split()]


def cmd_build(a) -> int:
    if not v.SLUG_RE.match(a.slug):
        print("--slug: lowercase words joined by _ (e.g. ode_to_joy)", file=sys.stderr)
        return 2
    try:
        entry = build_entry(name=a.name, artist=a.artist, contributor=a.contributor,
                            letters=a.letters, beats=_beats(a.beats), bpm=a.bpm, part=a.part,
                            sources=a.source, shift=a.shift,
                            drums=a.drums, max_seconds=a.max_seconds)
    except ValueError as e:
        print(f"cannot build: {e}", file=sys.stderr)
        return 1
    out = Path(a.out or SONGS / f"{a.slug}.json")
    errs = v.validate_entry(v.key_for(out), entry)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(entry, indent=2) + "\n")
    print(f"wrote {out} ({len(entry['notes'])} notes, {total_seconds(entry):.1f} s; {entry['key']})")
    for e in errs:
        print(f"  problem: {e}")
    return 1 if errs else 0


def cmd_validate(a) -> int:
    errs: list[str] = []
    if not a.files:
        errs = v.validate_dir(SONGS)
        count = len(list(SONGS.glob("*.json")))
    else:
        for f in a.files:
            errs += v.validate_file(f)
        count = len(a.files)
    for e in errs:
        print(e)
    print(f"{count} song(s) checked: " + ("all good" if not errs else f"{len(errs)} problem(s)"))
    return 1 if errs else 0


def cmd_preview(a) -> int:
    from .preview import render, render_band
    entry = json.loads(Path(a.file).read_text())
    out = Path(a.out or Path(a.file).with_suffix(".wav").name)
    if a.band:
        f, how = render_band(entry, out, a.soundfont)
        if f.suffix == ".mid":
            print(f"wrote {f} ({how}: open it in a MIDI player, or install FluidSynth and "
                  "a GM SoundFont -- see README, 'Hear the band')")
        else:
            print(f"wrote {f} (the band and the ocarina, with {how})")
        return 0
    secs = render(entry, out)
    print(f"wrote {out} ({secs:.1f} s)")
    return 0


def cmd_soundfont(a) -> int:
    from . import oot_soundfont
    argv = ["--o2r", a.o2r] + (["--out", a.out] if a.out else [])
    return oot_soundfont.main(argv) or 0


def cmd_play(a) -> int:
    from .keyboard_play import load_keys, play
    entry = json.loads(Path(a.file).read_text())
    keys = load_keys(a.keys)
    print(f"playing {entry.get('name')} in {a.countdown:g} s: focus the game, ocarina out")
    play(entry, keys, a.countdown)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ocarina", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="melody in note names -> songs/<slug>.json")
    b.add_argument("--slug", required=True)
    b.add_argument("--name", required=True)
    b.add_argument("--artist", required=True)
    b.add_argument("--contributor", required=True)
    b.add_argument("--part", required=True, help="which part of the song (verse, chorus...)")
    b.add_argument("--letters", required=True, help='e.g. "D4 F#4 A4 R B4" (R = rest)')
    b.add_argument("--beats", required=True, help='one length per note, e.g. "1 1 0.5 0.5 2"')
    b.add_argument("--bpm", required=True, type=float)
    b.add_argument("--source", required=True, action="append", help="transcription link (repeat)")
    b.add_argument("--shift", type=int, help="force a transposition (semitones)")
    b.add_argument("--drums", choices=v.DRUM_STYLES)
    b.add_argument("--max-seconds", type=float)
    b.add_argument("--out")
    b.set_defaults(fn=cmd_build)

    c = sub.add_parser("validate", help="check song files (default: all of songs/)")
    c.add_argument("files", nargs="*")
    c.set_defaults(fn=cmd_validate)

    w = sub.add_parser("preview", help="render a song's melody (or, with --band, the whole band) to a WAV")
    w.add_argument("file")
    w.add_argument("--out")
    w.add_argument("--band", action="store_true",
                   help="drums, bass and parts with the ocarina, as on stream (FluidSynth + a GM SoundFont)")
    w.add_argument("--soundfont", help="a .sf2 to render with (default: the OoT one if built, else a GM one)")
    w.set_defaults(fn=cmd_preview)

    f = sub.add_parser("soundfont", help="build the stream's OoT SoundFont from your own Ship of Harkinian oot.o2r")
    f.add_argument("--o2r", required=True, help="your SoH oot.o2r (made from your own ROM)")
    f.add_argument("--out", help="default ~/Library/Audio/Sounds/Banks/OoT-Jev.sf2")
    f.set_defaults(fn=cmd_soundfont)

    k = sub.add_parser("play", help="play a song into your own game with the keyboard")
    k.add_argument("file")
    k.add_argument("--keys", required=True, help="keys.json (see keys.example.json)")
    k.add_argument("--countdown", type=float, default=3.0)
    k.set_defaults(fn=cmd_play)

    x = sub.add_parser("fetch", help="note data from Songsterr / Hooktheory, lyrics stripped "
                                     "(search, meta, track, hooktheory)")
    x.add_argument("rest", nargs=argparse.REMAINDER,
                   help='e.g. search "never gonna give you up"; meta <songId>; '
                        "track <songId> <revisionId> <image> <trackIndex>; hooktheory <hash>")
    x.set_defaults(fn=lambda a: fetch_mod._main(a.rest))

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
