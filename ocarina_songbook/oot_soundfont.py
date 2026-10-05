#!/usr/bin/env python3
"""Build OoT-Jev.sf2: a General MIDI-laid-out SoundFont 2 made from Ocarina
of Time's own instrument and drum samples, for the FluidSynth backing track
(ootjev/drums.py) under Jev's ocarina songs.

    python3 tools/build_oot_soundfont.py [--o2r PATH] [--out PATH]

Stdlib only. Reads Ship of Harkinian's game archive (oot.o2r, a zip):

  audio/samples/<name>_META  SoH AudioSample V2 resource: 0x40-byte header,
      then (little endian) codec u8, medium u8, unk u8, relocated u8,
      size u32, <size> bytes of sample data, loop start u32, loop end u32,
      loop count u32 (0 = no loop, 0xFFFFFFFF = forever), n u32 + n s16 loop
      predictor state, book order s32, npredictors s32, n u32 + n s16 book.
      Codec 0 = VADPCM (9-byte frames of 16 samples), 3 = "small" VADPCM
      (5-byte frames, 2-bit residuals); decoded as the decomp's
      tools/audio/sampleconv vdecodeframe does.
  audio/fonts/<nn>_<name>    SoH AudioSoundFont V2 (read here only to
      document where each sample/tuning comes from; the tunings below are
      the game's values copied from these banks).

Pitch: the game plays a sound at note z (z64 note, C4 = 39 = MIDI 60) with
a resample ratio of tuning * 2^((z - 39) / 12) against its 32 kHz output, so
a sample with tuning t sounds right when stored at 32000 * t Hz with root
key 60 (tools/audio/extraction/tuning.py in the decomp: t = rate / 32000 *
2^((60 - basenote) / 12)). Drums play at the fixed ratio of their tuning.
"""
from __future__ import annotations

import argparse
import math
import os
import struct
import zipfile
from pathlib import Path

O2R = Path("~/Documents/Shipwright/oot.o2r").expanduser()
OUT = Path("~/Library/Audio/Sounds/Banks/OoT-Jev.sf2").expanduser()

# Overall level (centibels of attenuation on every zone), set so a render is
# about as loud as the same MIDI on GeneralUser-GS (the harness's gain is
# tuned for that font).
GLOBAL_ATTEN_CB = 60

# ---------------------------------------------------------------- melodic
# GM program -> (preset name, release seconds, zones). A zone is
# (lowest MIDI key, highest MIDI key, sample name, game tuning). Key splits
# are the game's own (normalRangeLo/Hi in z64 notes + 21 = MIDI). Sources
# are the SoH banks named in the comments.
MELODIC = {
    # 03_Orchestra inst 13 is Harpsichord / Piano / Piano (Soft); the piano
    # preset uses the piano sample below the split instead of harpsichord.
    0: ("OoT Piano", 0.5, [(0, 65, "Piano", 1.0),
                           (66, 127, "Piano (Soft)", 0.5)]),
    6: ("OoT Harpsichord", 0.3, [(0, 127, "Harpsichord", 2.3177)]),
    9: ("OoT Glockenspiel", 0.8, [(0, 127, "Glockenspiel", 0.5297)]),
    12: ("OoT Marimba", 0.4, [(0, 71, "Marimba 1", 0.8909),        # Orchestra 15
                              (72, 127, "Marimba 2", 0.4454)]),
    19: ("OoT Church Organ", 0.3, [(0, 71, "Church Organ", 1.0),     # Ganon organ 0
                                   (72, 127, "Electric Organ", 0.5)]),
    21: ("OoT Accordion", 0.2, [(0, 127, "Accordion", 1.0)]),
    24: ("OoT Nylon Guitar", 0.4, [(0, 66, "Acoustic Guitar 1", 1.2599),  # Kakariko 1
                                   (67, 127, "Acoustic Guitar 2", 0.4204)]),
    33: ("OoT Finger Bass", 0.15, [(0, 127, "Bass Guitar", 2.3811)]),   # Shops 2
    36: ("OoT Slap Bass", 0.15, [(0, 127, "Bass Guitar", 2.3811)]),
    38: ("OoT Synth Bass", 0.15, [(0, 127, "Bass Guitar", 2.3811)]),
    40: ("OoT Viola", 0.3, [(0, 127, "Viola", 0.5946)]),
    45: ("OoT Pizzicato", 0.3, [(0, 127, "Pizzicato Violin", 0.5612)]),
    46: ("OoT Harp", 0.8, [(0, 68, "Harp 2", 0.75),                    # Orchestra 14
                           (69, 127, "Harp 1", 0.375)]),
    48: ("OoT Strings", 0.4, [(0, 50, "Strings (Low)", 4.0),         # Orchestra 10
                              (51, 61, "Strings 1", 1.2599),
                              (62, 127, "Strings 2", 0.63)]),
    52: ("OoT Choir Aahs", 0.4, [(0, 127, "Vocal Aahs", 0.5162)]),
    53: ("OoT Voice Oohs", 0.4, [(0, 55, "Vocal Oohs", 0.9745),       # Fairy Fountain 6
                                 (56, 127, "Vocal Eees", 0.6891)]),
    56: ("OoT Trumpet", 0.2, [(0, 127, "Trumpet", 0.5)]),            # Orchestra 5
    57: ("OoT Trombone", 0.2, [(0, 127, "Trombone", 0.6674)]),
    58: ("OoT Tuba", 0.2, [(0, 127, "Tuba", 3.1748)]),
    60: ("OoT French Horn", 0.3, [(0, 127, "Horn", 1.0)]),
    68: ("OoT Oboe", 0.2, [(0, 127, "Oboe", 0.3969)]),
    70: ("OoT Bassoon", 0.2, [(0, 127, "Bassoon", 2.3784)]),
    71: ("OoT Clarinet", 0.2, [(0, 127, "Clarinet", 0.5)]),
    73: ("OoT Flute", 0.2, [(0, 127, "Flute", 0.3337)]),              # Orchestra 0
    79: ("OoT Ocarina", 0.2, [(0, 127, "Ocarina_Looped", 0.63)]),     # Kakariko 3
    104: ("OoT Sitar", 0.4, [(0, 127, "Sitar", 1.7818)]),
    105: ("OoT Banjo", 0.3, [(0, 61, "Banjo (Low)", 1.7818),          # Horse Race 0
                             (62, 127, "Banjo", 1.1892)]),
    107: ("OoT Koto", 0.4, [(0, 127, "Koto", 0.8909)]),
    110: ("OoT Fiddle", 0.2, [(0, 127, "Fiddle", 0.63)]),
    114: ("OoT Steel Drum", 0.4, [(0, 72, "Steel Drum", 1.0),         # Zora's 0
                                  (73, 127, "Steel Drum (High)", 0.4454)]),
}

# Presets whose sample sounds an octave above the game's nominal note (the
# game's sequences write those parts an octave low; FFT of a rendered A4
# shows 880 Hz): moved down an octave so a MIDI note sounds its own pitch.
# Measured by rendering every preset at A3/A4/A5; all others are within a
# few cents of equal temperament (Koto, Steel Drum and Pizzicato are the
# game's own ~+14 cents).
OCTAVE_FIX = {9: -1, 21: -1, 73: -1, 79: -1}

# ------------------------------------------------------------------ drums
# GM key -> (sample, game tuning, release s, exclusive class, note).
# FluidSynth's release falls linearly in dB to -100 dB, so a hit reaches
# -40 dB about 0.4 x release after its (short) MIDI note ends.
# Tunings are the game's drum-key values: 03_Orchestra kit (Bass Drum 1,
# Snare Drum 1/2, Cymbal, Timpani), 05_Market / 08_Kakariko kit (Tom Drum,
# Drum Sidestick, Finger Cymbals), 21_Zora's / 22_Shops kit (Drum 1,
# Drum 2, Shaker), and percussion instruments (Fire Temple "Off Hi-Hat"
# 0.868, Gerudo Valley "Clap" 0.5, Shops "Cowbell" 0.2102 played two
# octaves up).
DRUMS = {
    35: ("Bass Drum 1", 0.4590, 0.8, 0, "acoustic kick (Orchestra kit 3)"),
    36: ("Bass Drum 1", 0.5146, 0.6, 0, "kick (Orchestra kit 5)"),
    37: ("Drum Sidestick", 1.0, 0.3, 0, "side-stick (Kakariko kit 27)"),
    38: ("Snare Drum 1", 1.0, 0.5, 0, "snare (Orchestra kit 16)"),
    39: ("Clap", 0.5, 0.3, 0, "clap (Gerudo Valley inst 10)"),
    40: ("Snare Drum 2", 1.0595, 0.5, 0, "snare 2 (Orchestra kit 18)"),
    41: ("Tom Drum", 0.3337, 1.5, 0, "low floor tom (Kakariko kit 7)"),
    42: ("Off Hi-Hat", 1.0, 0.08, 1, "closed hat (Fire Temple inst 6, choked)"),
    43: ("Tom Drum", 0.3968, 1.5, 0, "high floor tom (Kakariko kit 10)"),
    44: ("Off Hi-Hat", 0.868, 0.15, 1, "pedal hat (Fire Temple inst 6, choked)"),
    45: ("Tom Drum", 0.4719, 1.5, 0, "low tom (Kakariko kit 13)"),
    46: ("Off Hi-Hat", 0.868, 1.3, 1, "open hat (Fire Temple inst 6)"),
    47: ("Tom Drum", 0.5612, 1.5, 0, "low-mid tom (Kakariko kit 16)"),
    48: ("Tom Drum", 0.6674, 1.5, 0, "hi-mid tom (Kakariko kit 19)"),
    49: ("Cymbal", 1.0, 4.0, 0, "crash (Orchestra kit 28)"),
    50: ("Tom Drum", 0.7937, 1.5, 0, "high tom (Kakariko kit 22)"),
    51: ("Finger Cymbals", 1.0, 1.2, 0, "ride (Kakariko kit 29)"),
    52: ("Cymbal", 0.7492, 4.0, 0, "china (Orchestra kit 23)"),
    53: ("Finger Cymbals", 1.1892, 1.2, 0, "ride bell (Kakariko kit 32)"),
    54: ("Finger Cymbals", 1.2599, 0.4, 0, "tambourine (Kakariko kit 33)"),
    55: ("Cymbal", 1.2599, 2.5, 0, "splash (Orchestra kit 32)"),
    56: ("Cowbell", 0.8409, 0.4, 0, "cowbell (Shops inst 10)"),
    57: ("Cymbal", 0.8909, 4.0, 0, "crash 2 (Orchestra kit 26)"),
    60: ("Drum 2", 1.0, 0.6, 0, "hi bongo (Zora's kit 39)"),
    61: ("Drum 2", 0.7937, 0.6, 0, "low bongo (Zora's kit 35)"),
    62: ("Drum 1", 0.6674, 0.2, 0, "mute hi conga (Zora's kit 20)"),
    63: ("Drum 1", 0.63, 0.8, 0, "open hi conga (Zora's kit 19)"),
    64: ("Drum 1", 0.5, 0.9, 0, "low conga (Zora's kit 15)"),
    70: ("Shaker", 1.0, 0.3, 0, "maracas/shaker (Zora's kit 60)"),
}


# ------------------------------------------------------------ o2r reading
def read_sample(raw: bytes) -> dict:
    p = 0x40
    codec = raw[p]
    size = struct.unpack_from("<I", raw, p + 4)[0]
    p += 8
    data = raw[p:p + size]
    p += size
    ls, le, lc, nst = struct.unpack_from("<IIII", raw, p)
    p += 16 + 2 * nst
    order, npred, nb = struct.unpack_from("<iiI", raw, p)
    p += 12
    book = struct.unpack_from("<%dh" % nb, raw, p)
    return dict(codec=codec, data=data, loop_start=ls, loop_end=le,
                loop_count=lc, order=order, npred=npred, book=book)


def _expand_book(book, order, npred):
    """The decomp's expand_codebook: per predictor an 8 x (order + 8)
    FIR matrix in Q11."""
    tables = []
    for i in range(npred):
        t = [[0] * (order + 8) for _ in range(8)]
        bd = book[i * order * 8:(i + 1) * order * 8]
        for j in range(order):
            for k in range(8):
                t[k][j] = bd[j * 8 + k]
        for k in range(1, 8):
            t[k][order] = t[k - 1][order - 1]
        t[0][order] = 1 << 11
        for k in range(1, 8):
            for j in range(k, 8):
                t[j][k + order] = t[j - k][order]
        tables.append(t)
    return tables


def decode(s: dict) -> list[int]:
    """VADPCM (codec 0 / 3) or raw big-endian s16 (codec 5) to s16 PCM."""
    codec = s["codec"]
    if codec in (2, 5):
        n = len(s["data"]) // 2
        return list(struct.unpack(">%dh" % n, s["data"][:2 * n]))
    if codec not in (0, 3):
        raise ValueError("unsupported codec %d" % codec)
    fs = 9 if codec == 0 else 5
    order = s["order"]
    tables = _expand_book(s["book"], order, s["npred"])
    data = s["data"]
    out: list[int] = []
    state = [0] * 16
    for f in range(len(data) // fs):
        fr = data[f * fs:(f + 1) * fs]
        scale = 1 << (fr[0] >> 4)
        page = tables[min(fr[0] & 15, len(tables) - 1)]
        ix = []
        if fs == 9:
            for c in fr[1:9]:
                ix += [c >> 4, c & 15]
            ix = [(v - 16 if v >= 8 else v) * scale for v in ix]
        else:
            for c in fr[1:5]:
                ix += [(c >> 6) & 3, (c >> 4) & 3, (c >> 2) & 3, c & 3]
            ix = [(v - 4 if v >= 2 else v) * scale for v in ix]
        new = [0] * 16
        for j in range(2):
            src = state if j == 0 else new
            base = (2 - j) * 8 - order
            vec = [src[base + i] for i in range(order)] + [0] * 8
            for i in range(8):
                vec[order + i] = ix[j * 8 + i]
                row = page[i]
                acc = 0
                for k in range(order + i):
                    acc += row[k] * vec[k]
                new[j * 8 + i] = (acc >> 11) + ix[j * 8 + i]
        state = new
        out += new
    return [32767 if v > 32767 else -32768 if v < -32768 else v for v in out]


# ------------------------------------------------------------ SF2 writing
def _chunk(tag: bytes, data: bytes) -> bytes:
    pad = b"\0" if len(data) % 2 else b""
    return tag + struct.pack("<I", len(data)) + data + pad


def _list(tag: bytes, body: bytes) -> bytes:
    return _chunk(b"LIST", tag + body)


def _name(s: str) -> bytes:
    return s.encode("ascii", "replace")[:19].ljust(20, b"\0")


def _tc(seconds: float) -> int:
    """Seconds to SF2 timecents."""
    return int(round(1200 * math.log2(max(seconds, 0.001))))


def _cents(ratio: float) -> tuple[int, int]:
    c = 1200 * math.log2(ratio)
    coarse = int(round(c / 100))
    return coarse, int(round(c - 100 * coarse))


# generator operators
KEYRANGE, SAMPLEID, INSTRUMENT, SAMPLEMODES = 43, 53, 41, 54
ROOTKEY, COARSE, FINE, SCALETUNE, EXCL = 58, 51, 52, 56, 57
ATTACK, HOLD, DECAY, SUSTAIN, RELEASE, ATTEN = 34, 35, 36, 37, 38, 48


class Builder:
    def __init__(self, zf: zipfile.ZipFile):
        self.zf = zf
        self.smpl = bytearray()
        self.shdr = []          # (name, start, end, ls, le, rate, root)
        self.samples = {}       # name -> (index, ref tuning, octave shift m)
        self.inst = []          # (name, [zone gens])
        self.presets = []       # (name, program, bank, inst index)

    def sample(self, name: str, tuning: float) -> tuple[int, float, int]:
        if name in self.samples:
            return self.samples[name]
        s = read_sample(self.zf.read("audio/samples/%s_META" % name))
        pcm = decode(s)
        n = len(pcm)
        looped = s["loop_count"] != 0 and s["loop_end"] <= n
        if looped:
            ls, le = s["loop_start"], s["loop_end"]
            pcm = pcm[:le + 8] if le + 8 <= n else pcm
        else:
            pcm = pcm[:min(n, s["loop_end"])]
            ls, le = 0, 0
        # Stored at 32000 * tuning Hz (the game's pitch for MIDI 60), moved
        # by octaves into 8..48 kHz; the root key moves with it.
        m = 0
        while 32000 * tuning / 2 ** m > 48000:
            m += 1
        while 32000 * tuning / 2 ** m < 8000:
            m -= 1
        rate = int(round(32000 * tuning / 2 ** m))
        start = len(self.smpl) // 2
        self.smpl += struct.pack("<%dh" % len(pcm), *pcm) + b"\0" * 92
        end = start + len(pcm)
        if looped:
            ls, le = start + ls, start + le
        else:
            ls, le = start, end
        self.shdr.append((name, start, end, ls, le, rate, 60 - 12 * m))
        self.samples[name] = (len(self.shdr) - 1, tuning, m, looped)
        return self.samples[name]

    def instrument(self, name: str, zones: list[list[tuple[int, int]]]) -> int:
        self.inst.append((name, zones))
        return len(self.inst) - 1

    def melodic_zone(self, lo, hi, sname, tuning, release, octave=0):
        idx, tref, m, looped = self.sample(sname, tuning)
        coarse, fine = _cents(tuning / tref)
        coarse += 12 * octave
        g = [(KEYRANGE, lo | hi << 8), (ATTEN, GLOBAL_ATTEN_CB),
             (ATTACK, _tc(0.005)), (RELEASE, _tc(release))]
        if coarse:
            g.append((COARSE, coarse))
        if fine:
            g.append((FINE, fine))
        if looped:
            g.append((SAMPLEMODES, 1))
        g.append((SAMPLEID, idx))
        return g

    def drum_zone(self, key, sname, tuning, release, excl):
        idx, tref, m, looped = self.sample(sname, tuning)
        # Fixed pitch: scale tuning 0 plays the sample at its header rate
        # (32000 * tref / 2^m) whatever the key; retune to 32000 * tuning.
        coarse, fine = _cents(tuning / tref * 2 ** m)
        g = [(KEYRANGE, key | key << 8), (ATTEN, GLOBAL_ATTEN_CB),
             (ATTACK, _tc(0.001)), (RELEASE, _tc(release)),
             (SCALETUNE, 0), (ROOTKEY, key)]
        if excl:
            g.append((EXCL, excl))
        if key == 42:     # closed hat: choke the long sample quickly
            g += [(HOLD, _tc(0.03)), (DECAY, _tc(0.12)), (SUSTAIN, 1440)]
        if key == 44:
            g += [(HOLD, _tc(0.05)), (DECAY, _tc(0.2)), (SUSTAIN, 1440)]
        if coarse:
            g.append((COARSE, coarse))
        if fine:
            g.append((FINE, fine))
        if looped:
            g.append((SAMPLEMODES, 1))
        g.append((SAMPLEID, idx))
        return g

    def build(self) -> bytes:
        for prog in sorted(MELODIC):
            pname, rel, zones = MELODIC[prog]
            octave = OCTAVE_FIX.get(prog, 0)
            zs = [self.melodic_zone(lo, hi, s, t, rel, octave) for lo, hi, s, t in zones]
            self.presets.append((pname, prog, 0, self.instrument(pname, zs)))
        kit = [self.drum_zone(k, *DRUMS[k][:4]) for k in sorted(DRUMS)]
        self.presets.append(("OoT Drum Kit", 0, 128, self.instrument("OoT Drum Kit", kit)))
        return self.serialize()

    def serialize(self) -> bytes:
        def zstr(text: str) -> bytes:   # zero-terminated, even length
            b = text.encode("ascii") + b"\0"
            return b + b"\0" * (len(b) % 2)
        info = (_chunk(b"ifil", struct.pack("<HH", 2, 1))
                + _chunk(b"isng", zstr("EMU8000"))
                + _chunk(b"INAM", zstr("OoT-Jev (Ocarina of Time samples)"))
                + _chunk(b"ICMT", zstr("Built by oot-jev-harness tools/build_oot_soundfont.py"
                                       " from Ship of Harkinian's oot.o2r")))
        sdta = _chunk(b"smpl", bytes(self.smpl))
        # presets: one global-less zone each, pointing at its instrument
        phdr = b""
        pbag = b""
        pgen = b""
        pmod = b""
        gi = 0
        order = sorted(self.presets, key=lambda p: (p[2], p[1]))
        for bi, (name, prog, bank, inst) in enumerate(order):
            phdr += _name(name) + struct.pack("<HHHIII", prog, bank, bi, 0, 0, 0)
            pbag += struct.pack("<HH", gi, 0)
            pgen += struct.pack("<HH", INSTRUMENT, inst)
            gi += 1
        phdr += _name("EOP") + struct.pack("<HHHIII", 0, 0, len(order), 0, 0, 0)
        pbag += struct.pack("<HH", gi, 0)
        pgen += struct.pack("<HH", 0, 0)
        pmod += b"\0" * 10
        inst = b""
        ibag = b""
        igen = b""
        bag = 0
        gi = 0
        for name, zones in self.inst:
            inst += _name(name) + struct.pack("<H", bag)
            for z in zones:
                ibag += struct.pack("<HH", gi, 0)
                for op, amt in z:
                    fmt = "<HH" if op in (KEYRANGE, SAMPLEID, SAMPLEMODES, ROOTKEY, EXCL) else "<Hh"
                    igen += struct.pack(fmt, op, amt)
                    gi += 1
                bag += 1
        inst += _name("EOI") + struct.pack("<H", bag)
        ibag += struct.pack("<HH", gi, 0)
        igen += struct.pack("<HH", 0, 0)
        imod = b"\0" * 10
        shdr = b""
        for name, start, end, ls, le, rate, root in self.shdr:
            shdr += _name(name) + struct.pack("<IIIIIBbHH", start, end, ls, le, rate, root, 0, 0, 1)
        shdr += _name("EOS") + struct.pack("<IIIIIBbHH", 0, 0, 0, 0, 0, 0, 0, 0, 0)
        pdta = b"".join(_chunk(t, d) for t, d in [
            (b"phdr", phdr), (b"pbag", pbag), (b"pmod", pmod), (b"pgen", pgen),
            (b"inst", inst), (b"ibag", ibag), (b"imod", imod), (b"igen", igen),
            (b"shdr", shdr)])
        body = b"sfbk" + _list(b"INFO", info) + _list(b"sdta", sdta) + _list(b"pdta", pdta)
        return _chunk(b"RIFF", body)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--o2r", type=Path, default=O2R)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    with zipfile.ZipFile(a.o2r) as zf:
        b = Builder(zf)
        data = b.build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out.with_suffix(".sf2.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, a.out)
    print("wrote %s (%.1f MB, %d samples, %d presets)"
          % (a.out, len(data) / 1e6, len(b.shdr), len(b.presets)))
    for name, start, end, ls, le, rate, root in b.shdr:
        print("  %-20s %7d frames @ %5d Hz root %3d%s"
              % (name, end - start, rate, root, "  loop %d-%d" % (ls - start, le - start) if le - ls and (ls, le) != (start, end) else ""))


if __name__ == "__main__":
    main()
