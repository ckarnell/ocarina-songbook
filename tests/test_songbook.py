import json
import os
from pathlib import Path

import pytest

from ocarina_songbook import pitch, validate as v
from ocarina_songbook.build import build_entry, spell_melody
from ocarina_songbook.timing import song_timing

ROOT = Path(__file__).resolve().parents[1]


def test_every_spelling_sounds_its_pitch():
    for m, s in pitch.SPELLINGS.items():
        assert pitch.pitch_of(s) == m, (m, s)


def test_letters_and_flats():
    assert pitch.midi("C4") == 60 and pitch.midi("Bb3") == pitch.midi("A#3") == 58
    with pytest.raises(ValueError):
        pitch.midi("C")  # no octave


def test_transposes_into_range_with_fewest_modifiers():
    notes, s = spell_melody("D4 F4 A4")  # D minor triad: plain buttons already
    assert notes == ["A", "C_DOWN", "C_RIGHT"] and s == 0


def test_too_wide_a_tune_is_refused():
    with pytest.raises(ValueError, match="wider than the ocarina"):
        spell_melody("C3 C5")


def test_rests_are_kept():
    notes, _ = spell_melody("D4 R D4")
    assert notes[1] == "REST"


def _entry(**kw):
    e = build_entry(name="Test", artist="Nobody", contributor="tester", letters="D4 F4 A4 D5",
                    beats=[1, 1, 1, 1], bpm=120, part="all", sources=["https://example.com"])
    e.update(kw)
    return e


def test_a_built_entry_is_valid():
    assert v.validate_entry("PLAY_NEW_SONG", _entry()) == []


@pytest.mark.parametrize("change,word", [
    ({"notes": ["A", "B", "C_UP", "A"]}, "not ocarina notes"),
    ({"beats": [1, 1]}, "one each"),
    ({"bpm": 1000}, "bpm"),
    ({"contributor": "bad name!"}, "contributor"),
    ({"sources": ["not a link"]}, "sources"),
    ({"drums": "dubstep"}, "drums"),
    ({"soundfont": "~/x.sf2"}, "unknown field"),
    ({"asked_by": "someone"}, "unknown field"),
    ({"max_seconds": 600}, "max_seconds"),
    ({"bass": {"program": 33, "notes": [[0, 200, 1]]}}, "bass.notes"),
])
def test_bad_entries_are_refused(change, word):
    errs = v.validate_entry("PLAY_NEW_SONG", _entry(**change))
    assert any(word in e for e in errs), errs


def test_reserved_key_is_refused():
    assert any("already one of Jev's songs" in e
               for e in v.validate_entry("PLAY_ALL_STAR", _entry()))


def test_too_long_a_song_is_refused():
    long_ = _entry(notes=["A"] * 200, beats=[1] * 200, bpm=60)
    assert any("must fit" in e for e in v.validate_entry("PLAY_NEW_SONG", long_))


def test_example_songs_are_valid():
    assert v.validate_dir(ROOT / "songs") == []


HARNESS = Path(os.environ.get("JEV_HARNESS", Path.home() / "Documents/oot-jev-harness"))


@pytest.mark.skipif(not (HARNESS / "play.py").exists(), reason="the Jev harness is not here")
def test_timing_matches_the_harness_on_every_existing_song():
    """What you preview is what plays: the same timing as play.py's
    song_timing_, note for note, on every song Jev knows."""
    import importlib, sys
    sys.path.insert(0, str(HARNESS))
    play = importlib.import_module("play")
    songs = json.loads((HARNESS / "songs/extra_songs.json").read_text())
    for key, e in songs.items():
        assert song_timing(e) == play.song_timing_(e), key
