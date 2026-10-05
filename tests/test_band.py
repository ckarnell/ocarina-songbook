"""The band preview: MIDI for every song, with the melody on GM 79."""
import json
from pathlib import Path

from ocarina_songbook import band

SONGS = sorted(Path(__file__).resolve().parents[1].glob("songs/*.json"))


def test_every_song_makes_midi_with_the_ocarina():
    for p in SONGS:
        m = band.song_midi(json.loads(p.read_text()))
        assert m[:4] == b"MThd", p.name
        assert bytes([0xC0 | band.MELODY_CHANNEL, band.OCARINA_PROGRAM]) in m, p.name


def test_bass_and_parts_land_on_their_channels():
    e = json.loads((SONGS[0].parent / "forgot_about_dre.json").read_text())
    m = band.song_midi(e, melody=False)
    assert bytes([0xC0, 33]) in m                 # bass, channel 1, finger bass
    assert bytes([0xC1, 48]) in m                 # first part, channel 2, OoT strings
