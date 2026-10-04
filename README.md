# Ocarina Songbook

Make songs for Link's ocarina, hear them, play them in your own game, and
send them to the Jev stream, where Jev (an AI playing *Ocarina of Time*)
plays them live, with credit to you.

```
melody in note names ──> ocarina build ──> songs/your_song.json ──> pull request
     "E4 E4 F4 G4"        (transposes and                            │
     + a length per note   spells every note)                        ▼
                                                     reviewed, merged ──> Jev plays it
```

## The ocarina in one table

Five buttons, each one pitch, and four modifiers that bend it. Range B3..F5.

| Button | Pitch | | Modifier | Effect |
|---|---|---|---|---|
| `A` | D4 | | `R` | one semitone up |
| `C_DOWN` | F4 | | `Z` | one semitone down |
| `C_RIGHT` | A4 | | `UP` (stick) | two semitones up |
| `C_LEFT` | B4 | | `DOWN` (stick) | two semitones down |
| `C_UP` | D5 | | | |

A note is written `BUTTON+MOD...` (e.g. `C_DOWN+R` is F#4), or `REST`. You
never have to spell these yourself: `ocarina build` does it.

## Set up

Python 3.10+, nothing else needed to build, check and preview.

```bash
git clone https://github.com/ckarnell/ocarina-songbook && cd ocarina-songbook
python3 -m venv .venv && .venv/bin/pip install -e '.[test]'
# optional, to play into your own game: .venv/bin/pip install -e '.[play]'
```

## Make a song

1. Find a transcription of the part you want (sheet music, a letter-note or
   tab site). Pick a short, recognisable passage: 10-20 seconds is ideal, 45
   at most.
2. Write it as note names with octaves, plus one length in beats per note
   (`R` is a rest and needs a length too):

   ```bash
   .venv/bin/ocarina build --slug ode_to_joy --name "Ode to Joy" \
     --artist "Ludwig van Beethoven" --contributor yourhandle \
     --part "the main theme" \
     --letters "E4 E4 F4 G4 | G4 F4 E4 D4 | C4 C4 D4 E4 | E4 D4 D4" \
     --beats   "1 1 1 1 1 1 1 1 1 1 1 1 1.5 0.5 2" --bpm 132 \
     --drums ballad --source https://link-to-the-sheet-you-used
   ```

   It moves the tune into the ocarina's range with the fewest modifiers and
   writes `songs/ode_to_joy.json`. A tune wider than 18 semitones won't fit:
   pick a shorter passage.
3. Listen: `.venv/bin/ocarina preview songs/ode_to_joy.json` writes a WAV of
   the melody, timed exactly as Jev will play it.
4. Optional: play it in your own game (Ship of Harkinian or an emulator).
   Map your controller to keys, copy `keys.example.json` to `keys.json` with
   your keys, take out the ocarina, then
   `.venv/bin/ocarina play songs/ode_to_joy.json --keys keys.json`.
5. Check it: `.venv/bin/ocarina validate`.
6. Open a pull request **to this repo** (fork, add your one new file, PR
   here). See [CONTRIBUTING.md](CONTRIBUTING.md). The stream's harness is
   private: once your song is merged here, the stream pulls it into Jev's
   songbook and he can play it, credited to the `contributor` you wrote.

## With an AI

Let an AI find the melody and rhythm for you; the tools here do the
spelling and the checking.

- **Claude Code:** open this folder and ask, e.g. *"make an ocarina song of
  the chorus of September by Earth, Wind & Fire"*. The `make-ocarina-song`
  skill in `.claude/skills/` walks it through.
- **Codex** and other agents: the same steps are in [AGENTS.md](AGENTS.md).

## What the band adds on stream

On stream Jev's ocarina plays with a backing band. A song may ask for:

- `"drums"`: one of `rock`, `ballad`, `shuffle`, `waltz`, `sixeight`,
  `march`, `stomp`, `disco`, `orchestral`, `none` (or
  `{"style": "rock", "intro_beats": 4}` for a count-in);
- `"bass"`: `{"program": 33, "velocity": 80, "notes": [[beat, midi_pitch, length_beats], ...]}`,
  beats counted from the first ocarina note (negative = before it);
- `"parts"`: up to 3 more instruments in the same form (General MIDI programs).

The ocarina has to stay the loudest voice: bass velocity at most 84, parts at
most 66, and keep parts out of the ocarina's register (B3..F5) where you can.

The preview plays the melody only.
