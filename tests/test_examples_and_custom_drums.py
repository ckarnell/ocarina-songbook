"""The examples are songs exactly as Jev plays them on stream, and the
custom-groove format they use (Poodleskirt, 2026-10-05)."""
import json
from pathlib import Path

import pytest

from ocarina_songbook import band, cli, validate as v
from ocarina_songbook.timing import song_timing

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.json"))


def test_there_are_examples():
    assert len(EXAMPLES) >= 5


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_each_example_validates(path, monkeypatch):
    # Their keys are Jev's own songs (reserved for new contributions).
    monkeypatch.setattr(v, "reserved_keys", lambda: set())
    entry = json.loads(path.read_text())
    assert v.validate_entry("PLAY_" + path.stem.upper(), entry) == []
    hits, _intro = band.plan(song_timing(entry), entry)
    assert hits, "an example plays with its band"


def _song(drums):
    return {"name": "T", "artist": "A", "contributor": "someone", "notes": ["A", "C_DOWN", "C_RIGHT", "A"],
            "bpm": 120, "beats": [1, 1, 1, 1], "letters": "D4 F4 A4 D4", "key": "D", "part": "test",
            "sources": ["https://example.com/x"], "drums": drums}


def test_custom_pattern_validates_and_plays():
    pat = [4, [[0, 36, 110], [1, 38, 100], [2, 36, 100], [3, 38, 100]]]
    s = _song({"style": "custom", "pattern": pat})
    assert v.validate_entry("PLAY_T_CUSTOM_X", s) == []
    hits, _ = band.plan(song_timing(s), s)
    keys = [k for t, k, _v in hits if t < 1.9]
    assert keys.count(38) == 2 and 36 in keys   # snares on beats 1 and 3


@pytest.mark.parametrize("bad", [
    {"style": "custom"},                                        # no pattern
    {"style": "custom", "pattern": [4, [[4, 36, 100]]]},        # beat outside the bar
    {"style": "custom", "pattern": [4, [[0, 12, 100]]]},        # not a drum key
    {"style": "rock", "pattern": [4, [[0, 36, 100]]]},          # pattern without custom
])
def test_bad_custom_patterns_are_refused(bad):
    assert v.validate_entry("PLAY_T_CUSTOM_Y", _song(bad))


def test_fetch_is_a_command():
    with pytest.raises(SystemExit):
        cli.main(["fetch", "--help"])
