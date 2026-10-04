---
name: make-ocarina-song
description: Turn a real song into an ocarina song file for the Jev stream -- find a transcription, pick the hook, write it as note names and beats, build it with `ocarina build`, validate and preview it, and hand it over as a one-file pull request. Use whenever someone asks to make, add or transcribe a song for the ocarina.
---

# Making an ocarina song

You are helping someone add a song to this songbook, to be played on Link's
ocarina by Jev on stream. Your job is the musical part: find the melody and
its rhythm. The `ocarina` tool does the spelling and the checking. Never
spell ocarina buttons by hand.

## Steps

1. **Ask who to credit** if you don't know: their handle goes in
   `--contributor` (letters, digits, `_`).
2. **Find a real transcription** of the song: sheet music, a letter-note
   site, a tab, a hooktheory page. Use two sources if they disagree. Never
   invent or "reconstruct" a melody from memory: if you can't find one,
   say so and stop.
3. **Pick the passage**: the hook everyone knows (usually the chorus, or
   the signature riff), short: about 16 beats, 10-20 seconds. End on a
   note that sounds finished.
4. **Write it down** as note names with octaves (`D4 F#4 A4`, flats are
   fine: `Bb3`), `R` for a rest, bar lines `|` if you like; and one length
   in beats per note, rests included (a quarter note in 4/4 is 1). Take
   the tempo (bpm) from the source. The tune must span at most 18 semitones
   (B3..F5 after transposing); if it's wider, take a shorter passage or move
   one phrase by an octave.
5. **Build it:**

   ```bash
   ocarina build --slug <lowercase_words> --name "<Title>" --artist "<Artist>" \
     --contributor <handle> --part "<which part, e.g. the chorus hook>" \
     --letters "<notes>" --beats "<lengths>" --bpm <n> \
     --drums <rock|ballad|shuffle|waltz|sixeight|march|stomp|disco|orchestral|none> \
     --source <url> [--source <url2>]
   ```

   It transposes for the fewest modifiers and writes `songs/<slug>.json`.
   If it reports a problem, fix the input and build again.
6. **Check it**: `ocarina validate` must say *all good*. Then
   `ocarina preview songs/<slug>.json` and tell the person where the WAV
   is so they can listen. Don't play audio yourself.
7. **Optional band**: a `"bass"` and up to 3 `"parts"` can be added to the
   JSON by hand (see README, "What the band adds on stream"), in the same
   transposition as the melody, every note starting on a beat the drums
   hit, bass velocity at most 84, parts at most 66. Validate again.
8. **Hand over**: tell the person the file is ready and that they send it
   as a pull request with just that one file to THIS repo,
   github.com/ckarnell/ocarina-songbook (fork, branch, PR here; see
   CONTRIBUTING.md). The stream's harness is private and pulls merged songs
   from here: never look for it or send songs anywhere else.

## Don'ts

- Don't edit other songs, the tool, or the reserved list.
- Don't add fields the validator rejects (no `soundfont`, no `asked_by`).
- Don't open the pull request for them unless they ask you to.
