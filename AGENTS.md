<!-- The same guide as .claude/skills/make-ocarina-song/SKILL.md, for Codex and other agents. Keep the two in step. -->

# Making an ocarina song (the stream's own process)

You are helping someone add a song to this songbook, to be played on Link's
ocarina by Jev on stream. This is the same process the stream's composer
uses for every song Jev knows; `examples/` holds six of those songs exactly
as Jev plays them (read two before you start -- their `rhythm` field says how
each one was worked out). Your job is the musical part: find the real melody,
rhythm and band parts. The `ocarina` tool does the spelling and checking.
Never spell ocarina buttons by hand.

## Hard rules

- **Never print lyrics or raw tab/page text.** Parse sources silently in
  Python and print only note names / MIDI numbers, beats, bar numbers,
  track names and tempos. `ocarina fetch` strips lyric fields for you; use
  it instead of raw API calls. Name sections ("the chorus hook"), never words.
- **Never invent a melody from memory.** If no real transcription can be
  found, say so and stop.
- **Never play audio** (no browser on song/piano pages, no playing the WAV):
  render it and tell the person where it is.

## Steps

1. **Ask who to credit** if you don't know: their handle goes in
   `--contributor` (letters, digits, `_`).

2. **Get a real per-note transcription.** Best first, in this order:
   - **Songsterr** (most songs, every instrument on its own track, exact
     rhythm):
     ```bash
     ocarina fetch search "<artist> <song>"          # songId, title, instruments
     ocarina fetch meta <songId>                     # revisionId, image, tracks
     ocarina fetch track <songId> <revisionId> <image> <trackIndex>
     ```
     In a track: `duration` is `[num, den]` of a whole note and already
     includes dots and tuplets (quarter = [1,4] = 1 beat, so beats =
     4*num/den); pitch = `tuning[string] + fret` (drums: `fret` is the GM
     drum key); `tie` extends the previous note; rests are `rest: true`;
     tempo is in `automations.tempo`. The vocal is often its own track
     (sometimes named after the singer, played by a wind instrument).
   - **Hooktheory** (melody + key, great for checking): grep the hash from
     `https://www.hooktheory.com/theorytab/view/<artist>/<song>` (regex
     `"hash":"..."`, don't print the page), then `ocarina fetch hooktheory <hash>`.
   - **Sheet music / letter notes** (pianoletternotes, musescore, a tab's
     rhythm line W H Q E S = 4 2 1 0.5 0.25 beats; a dot adds half).
   Check the melody against a second source: per-singer tracks lie (one
   "lead" track was a harmony a third above the tune in the chorus).

3. **Pick the passage.** The main part only -- the lead vocal, or the
   signature riff -- of the part everyone knows (the chorus or the famous
   hook, not an intro). **About 16 beats** (four bars of 4/4; the stream's
   rule for new songs), ending on a note that sounds finished. Drop
   harmony, backing vocals and accompaniment. Where the lead rests and
   another lead instrument answers (a trumpet stab), that answer may fill
   the gap.

4. **Write the rhythm exactly.** One length per note, **onset to next
   onset**, rests as `R` with their own length (keep every rest of half a
   beat or more; don't fold it into a long note). Take the tempo from the
   source (a Songsterr tempo automation, a tab header `Q=200`, or a tempo
   site -- pick the one where the beats you counted feel right). Write the
   real tempo; never pre-slow it.

5. **No slow-down.** The ocarina needs at least 0.08 s per note: if any
   note would be held shorter, the stream slows the WHOLE song and the
   band feels off. Sixteenths survive up to ~110 BPM, eighths up to ~220.
   If the hook has a figure too fast, take a passage without it or
   simplify that figure. Check after building:
   ```python
   import json; from ocarina_songbook.timing import song_timing, total_seconds
   e = json.load(open("songs/<slug>.json")); t = song_timing(e)
   assert min(h for _n, h, _g in t) >= 0.08
   assert abs(total_seconds(e) - sum(e["beats"]) * 60 / e["bpm"]) < 0.01   # not stretched
   ```

6. **Build it:**
   ```bash
   ocarina build --slug <lowercase_words> --name "<Title>" --artist "<Artist>" \
     --contributor <handle> --part "<which part, e.g. the chorus hook>" \
     --letters "<notes, R = rest>" --beats "<lengths>" --bpm <n> \
     --source <url> [--source <url2>]
   ```
   It transposes into the ocarina's range (B3..F5) with the fewest
   modifiers and reports the shift; keep the original key if it fits.
   Then add a `"rhythm"` field by hand: one line on where the notes, beats
   and tempo came from (source, track, bars, reasoning) -- see the examples.

7. **The band, from the song's own tracks** (every song gets one unless
   the person wants the ocarina alone). All band notes are
   `[beat, MIDI pitch, length in beats]`, beats counted from the first
   ocarina note (negative = in the intro), **moved by exactly the melody's
   shift** so everything stays in tune.
   - **Drums: the song's own groove, not a stock style.** Read the drum
     track for the same bars and write it into the file:
     ```json
     "drums": {"style": "custom", "pattern": [8, [[0, 36, 110], [1, 38, 100], [0, 42, 70], ...]],
               "intro_beats": 4, "start": 0}
     ```
     `pattern` = [length in beats, [[beat, GM drum key, velocity], ...]]
     (36 kick, 38 snare, 42 closed hat, 46 open hat, 49 crash, 51 ride,
     41/45/50 toms), repeating from the first note. Often 2 bars (8 beats)
     covers it; a pattern may span the whole song. A pickup: set `start` to
     its length so the pattern's beat 1 falls on the downbeat.
     `intro_beats`: drums alone before the tune, ending on a bar line (4, 8,
     or 8 minus the pickup). A song with no kit in the original still gets
     a soft kick/snare backbone under its own percussion. Stock styles
     (`rock`, `ballad`, ... see `ocarina build --help`) are only a fallback.
   - **Bass** (`"bass": {"program": 33, "velocity": 84, "notes": [...]}`):
     the song's bass track for the same bars; an octave up carries better.
   - **Up to 3 `parts`** (`{"program": 48, "velocity": 60, "notes": [...]}`)
     from the song's own tracks for those roles (strings, brass stabs,
     flute). Leave out dense strumming and sixteenth pads; they bury the
     ocarina.
   - **The ocarina stays the loudest voice**: bass velocity at most 84,
     parts 50-66 (quietest for anything in B3..F5); move parts an octave
     away from the melody where the song allows.
   - Programs: only the OoT ones in README's table (48 strings, 56 trumpet,
     73 flute, 46 harp, 114 steel drum, 33 finger bass, ...): on stream they
     sound with Ocarina of Time's own samples.

8. **Prove the sync, silently.** Every ocarina, bass and part onset must
   land on a drum hit:
   ```python
   import json; from ocarina_songbook import band; from ocarina_songbook.timing import song_timing
   e = json.load(open("songs/<slug>.json")); t = song_timing(e)
   hits, intro = band.plan(t, e)
   spb = sum(h + g for _n, h, g in t) / sum(e["beats"][:len(t)])
   drum_times = {round(s, 3) for s, _k, _v in hits}
   onsets = []; x = 0.0
   for n, b in zip(e["notes"], e["beats"]):
       if n != "REST":                          # a rest needs no drum hit
           onsets.append(round(x * spb, 3))
       x += b
   for inst in [e.get("bass")] + (e.get("parts") or []):
       for beat, _p, _l in (inst or {}).get("notes", []):
           onsets.append(round(beat * spb, 3))
   missing = [o for o in onsets if all(abs(o - d) > 0.001 for d in drum_times)]
   print(missing)   # add a quiet closed hat (key 42, velocity 30) at each of these
   ```
   The one exception: a pickup the original sings before the band comes in
   (examples/in_the_end.json: three vocal notes, drums from beat 2.5).
   Also check a kick on the first downbeat and nothing after the song's end.

9. **Check it**: `ocarina validate` must say *all good*. Then
   `ocarina preview songs/<slug>.json --band` and tell the person where the
   WAV is so they can listen (the ocarina should stay on top).

10. **Hand over**: the file is ready; they send it as a pull request with
    just that one file to THIS repo, github.com/ckarnell/ocarina-songbook
    (fork, branch, PR; see CONTRIBUTING.md). The stream's harness is
    private and pulls merged songs from here: never look for it or send
    songs anywhere else.

## Don'ts

- Don't edit other songs, `examples/`, the tool, or the reserved list.
- Don't add fields the validator rejects (no `soundfont`, no `asked_by`).
- Don't open the pull request for them unless they ask you to.
- Never ask the contributor for a ROM; the OoT sound font is built only from
  their own game files (`ocarina soundfont`).
