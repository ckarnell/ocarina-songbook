#!/usr/bin/env python3
"""Fetch song tab/transcription data for ocarina song learners, with any
lyric-bearing fields stripped out of the JSON before it ever reaches an
agent's context.

Why this exists: a song learner printing a raw Songsterr/Hooktheory response
can trip the API's own output content filter if that response happens to
carry lyric text (some tracks are typed as vocals with syllable/word data).
Earlier learners were told in prose to "never print lyrics" and still died
mid-run. This removes the risk at the source instead of relying on
discipline: every fetch here comes back pre-stripped, so there is nothing
lyric-shaped left to print by accident.

Usage (CLI, prints only stripped JSON):
    ocarina fetch search "<query>" [--size N]
    ocarina fetch meta <song_id>
    ocarina fetch track <song_id> <revision_id> <image> <track_index>
    ocarina fetch hooktheory <hash>

Library usage, same functions, for a learner that wants to post-process
further before printing anything.
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.parse
import urllib.request

# Keys that can hold lyric/vocal text in these APIs. Stripped recursively,
# wherever they appear, however deep.
LYRIC_KEYS = {
    "text", "lyrics", "lyric", "newLyrics", "newLyric",
    "syllable", "syllables", "word", "words", "verse", "verses",
}

_UA = {"User-Agent": "Mozilla/5.0"}


def _strip_lyrics(obj):
    if isinstance(obj, dict):
        return {k: _strip_lyrics(v) for k, v in obj.items() if k not in LYRIC_KEYS}
    if isinstance(obj, list):
        return [_strip_lyrics(v) for v in obj]
    return obj


def _get_json(url: str, gzipped: bool = False):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    if gzipped:
        data = gzip.decompress(data)
    return _strip_lyrics(json.loads(data))


def songsterr_search(query: str, size: int = 20):
    url = f"https://www.songsterr.com/api/songs?pattern={urllib.parse.quote(query)}&size={size}"
    results = _get_json(url)
    return [
        {
            "songId": r.get("songId"),
            "title": r.get("title"),
            "artist": r.get("artist"),
            "instruments": [t.get("instrument") for t in r.get("tracks", [])],
        }
        for r in results
    ]


def songsterr_meta(song_id):
    url = f"https://www.songsterr.com/api/meta/{song_id}"
    meta = _get_json(url)
    return {
        "revisionId": meta.get("revisionId"),
        "image": meta.get("image"),
        "tracks": [
            {"index": i, "name": t.get("name"), "instrument": t.get("instrument")}
            for i, t in enumerate(meta.get("tracks", []))
        ],
    }


def songsterr_track(song_id, revision_id, image, track_index):
    url = f"https://dqsljvtekg760.cloudfront.net/{song_id}/{revision_id}/{image}/{track_index}.json"
    return _get_json(url, gzipped=True)


def hooktheory_section(hash_: str):
    url = f"https://api.hooktheory.com/v1/songs/public/{hash_}?fields=ID,xmlData,song,jsonData"
    return _get_json(url)


def _main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "search":
        size = 20
        if "--size" in rest:
            i = rest.index("--size")
            size = int(rest[i + 1])
            rest = rest[:i] + rest[i + 2:]
        print(json.dumps(songsterr_search(rest[0], size=size), indent=2))
    elif cmd == "meta":
        print(json.dumps(songsterr_meta(rest[0]), indent=2))
    elif cmd == "track":
        print(json.dumps(songsterr_track(*rest[:4]), indent=2))
    elif cmd == "hooktheory":
        print(json.dumps(hooktheory_section(rest[0]), indent=2))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
