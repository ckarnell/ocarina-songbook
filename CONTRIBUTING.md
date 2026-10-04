# Sending a song to the stream

1. **One song, one file:** `songs/<slug>.json`, the slug in lowercase words
   joined by `_` (`songs/never_gonna.json`). Make it with `ocarina build`
   (see the README); edit by hand only if you know the format.
2. **Run `ocarina validate`** until it says *all good*. The same check runs
   on your pull request, and again on the stream before the song loads.
3. **Open a pull request** that adds just that file. Say in the description
   what part of the song it is and anything worth knowing.
4. **Review:** the stream owner listens and merges. A merged song reaches
   Jev within a few minutes; when he plays it, chat is told it is yours
   (your `contributor` handle).

## What gets a song merged

- A short, recognisable passage (10-20 s is ideal, 45 s at most).
- A real source: link the transcription you worked from in `sources`.
- Nothing hateful, sexual, or harassing, in the song or its fields.
- Not a song Jev already knows (the validator checks the names it can).

## What the validator checks

- Every note is a real ocarina note (`BUTTON+MOD...` or `REST`) and there
  is one length in `beats` per note.
- `bpm` 20-400; the whole song fits its time cap (20 s, or `max_seconds` up
  to 45).
- Only these fields: `name`, `artist`, `contributor`, `part`, `key`,
  `letters`, `sources`, `bpm`, `beats`, `notes`, and optionally `drums`,
  `bass`, `parts`, `max_seconds`.
- `contributor` is a plain handle; `sources` are links; drum styles and
  instruments are ones the stream's band has.
- The file name doesn't clash with a song Jev already has, and no two songs
  here have the same name.

A song file is data only: nothing in it ever runs.
