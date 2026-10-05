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

1. Find a transcription of the part you want. Best is a per-note tab:
   `.venv/bin/ocarina fetch search "<artist> <song>"`, then `fetch meta` and
   `fetch track` give every note of every instrument from Songsterr (lyrics
   stripped); `fetch hooktheory` gives a Hooktheory melody to check it
   against. Sheet music or a letter-note site works too. Pick a short,
   recognisable passage: about 16 beats (10-20 seconds) is ideal, 45 s at
   most. See `examples/` for songs exactly as Jev plays them on stream.
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

It is the same process the stream's own composer uses for every song Jev
knows. `examples/` has six of them (Green Hill Zone, Seinfeld, Through the
Fire and Flames, Toxic, Dire Dire Docks, In the End), each with a `rhythm`
note on how its notes, beats and tempo were worked out: compare your result
with those.

## Hear the band, and use the stream's OoT instruments

On stream every song's band (drums, bass, parts) is played with a SoundFont
built from **Ocarina of Time's own instrument samples**. It is laid out on
General MIDI program numbers, so a part asks for an OoT instrument just by
its `program`:

| GM program | OoT instrument |
|---|---|
| 0 | Piano |
| 6 | Harpsichord |
| 9 | Glockenspiel |
| 12 | Marimba |
| 19 | Church Organ |
| 21 | Accordion |
| 24 | Nylon Guitar |
| 33 | Finger Bass |
| 36 | Slap Bass |
| 38 | Synth Bass |
| 40 | Viola |
| 45 | Pizzicato |
| 46 | Harp |
| 48 | Strings |
| 52 | Choir Aahs |
| 53 | Voice Oohs |
| 56 | Trumpet |
| 57 | Trombone |
| 58 | Tuba |
| 60 | French Horn |
| 68 | Oboe |
| 70 | Bassoon |
| 71 | Clarinet |
| 73 | Flute |
| 79 | Ocarina |
| 104 | Sitar |
| 105 | Banjo |
| 107 | Koto |
| 110 | Fiddle |
| 114 | Steel Drum |

Drums (any `drums` style) use the game's own kit on the standard GM drum keys
(35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 63, 64, 70). A program not in the table has no OoT sound on stream: stick to the
table.

**Hear it** with the band, as on stream:

```bash
.venv/bin/ocarina preview songs/your_song.json --band
```

That needs [FluidSynth](https://www.fluidsynth.org/) (`brew install fluid-synth`,
`apt install fluidsynth`) and a General MIDI SoundFont. Without the OoT one,
a free GM font such as [GeneralUser GS](https://schristiancollins.com/generaluser.php)
(put the .sf2 in `~/Library/Audio/Sounds/Banks/` or `~/.local/share/soundfonts/`)
plays the same programs with ordinary instruments: close enough to hear the
parts, the levels and the timing. Without FluidSynth you get a `.mid` to open
in any MIDI player. `--soundfont PATH` picks a font.

**The real OoT sound**, if you have Ship of Harkinian set up with your own
ROM: `ocarina soundfont --o2r path/to/oot.o2r` builds `OoT-Jev.sf2` from your
own copy, and `preview --band` uses it from then on. This repo has no game
data in it, and you never need the ROM to contribute a song.

## What the band adds on stream

On stream Jev's ocarina plays with a backing band. A song may ask for:

- `"drums"`: best, the song's own groove from its drum track:
  `{"style": "custom", "pattern": [8, [[beat, gm_drum_key, velocity], ...]], "intro_beats": 4}`
  (the pattern repeats from the first note; `"start"` shifts it for a
  pickup). Or a stock style: `rock`, `ballad`, `shuffle`, `waltz`,
  `sixeight`, `march`, `stomp`, `disco`, `orchestral`, `none` (or
  `{"style": "rock", "intro_beats": 4}` for a count-in);
- `"bass"`: `{"program": 33, "velocity": 80, "notes": [[beat, midi_pitch, length_beats], ...]}`,
  beats counted from the first ocarina note (negative = before it);
- `"parts"`: up to 3 more instruments in the same form (General MIDI programs);
- `"rhythm"`: one line on where the notes, beats and tempo came from.

The ocarina has to stay the loudest voice: bass velocity at most 84, parts at
most 66, and keep parts out of the ocarina's register (B3..F5) where you can.

The preview plays the melody only.
