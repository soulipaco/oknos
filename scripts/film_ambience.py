"""Make the films' quiet background: wind, cicadas, a distant goat bell. Original, made from numbers.

    uv run python scripts/film_ambience.py             # all three films
    uv run python scripts/film_ambience.py f3          # one film
    uv run python scripts/film_ambience.py --wav DIR   # also keep the WAVs (to listen before encoding)

Nothing is recorded or downloaded: every sound is filtered noise or a sum of sine waves, shaped by a
seeded random generator, so the same command makes the same files. The output is CC BY-SA 4.0, like
the rest of docs/brand/animations/.

Each film gets one loop, docs/brand/animations/ambience/<film>.mp3, matched to its mood:

  f1  Delphi, a mountainside: wind with gusts and a thin whistle, goat bells far off with an echo
  f2  a village by day: a light breeze, a few cicadas, now and then a bell
  f3  noon under the olive tree: warm air, leaves, a chorus of cicadas that swells and fades

The loop is seamless: every slow change (gusts, swells, the cicadas' pulse) repeats a whole number of
times in the loop, the noise is cross-faded from the loop's end into its start, and the bells are
placed around the loop so that one ringing at the end carries on at the start. film.js plays it
under the voice when "Play with sound" is on (and ducks it under each clip).

Needs only the standard library to make the sound and ffmpeg (with libmp3lame) on the PATH to encode
it. Takes about half a minute per film.
"""

from __future__ import annotations

import argparse
import math
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "brand" / "animations" / "ambience"

SR = 22050            # enough for wind and cicadas (both below 8 kHz here), and half the size of 44.1 kHz
LOOP = 30.0           # seconds; the films are about 45-70 s, so a listener hears the loop at most twice
N = int(SR * LOOP)
XF = int(SR * 2.0)    # the cross-fade from the loop's end into its start
L = N + XF            # noise is made this long, then folded into N
BITRATE = "64k"       # stereo MP3: about 240 KB for 30 s
TARGET_DB = -24.0     # the loop's RMS level, dBFS; film.js sets how loud it plays under the voice
TAU = 2 * math.pi


# ---- building blocks (plain lists of floats, one value per sample) ----

def noise(rng: random.Random, n: int = L) -> array:
    r = rng.random
    return array("d", [r() * 2.0 - 1.0 for _ in range(n)])


def lowpass(x: array, fc: float) -> array:
    """One-pole low-pass."""
    a = math.exp(-TAU * fc / SR)
    b = 1.0 - a
    y = array("d", bytes(8 * len(x)))
    s = 0.0
    for i, v in enumerate(x):
        s = b * v + a * s
        y[i] = s
    return y


def highpass(x: array, fc: float) -> array:
    lo = lowpass(x, fc)
    return array("d", [v - w for v, w in zip(x, lo)])


def bandpass(x: array, fc, q: float) -> array:
    """RBJ band-pass (0 dB peak). `fc` is a number or a list (one per sample, read every 32 samples)."""
    y = array("d", bytes(8 * len(x)))
    x1 = x2 = y1 = y2 = 0.0
    varying = not isinstance(fc, (int, float))
    b0 = b2 = a1 = a2 = 0.0

    def coeffs(f):
        w = TAU * min(f, SR * 0.45) / SR
        al = math.sin(w) / (2 * q)
        n = 1 + al
        return al / n, -al / n, -2 * math.cos(w) / n, (1 - al) / n

    if not varying:
        b0, b2, a1, a2 = coeffs(fc)
    for i, v in enumerate(x):
        if varying and i % 32 == 0:
            b0, b2, a1, a2 = coeffs(fc[i])
        o = b0 * v + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, v
        y2, y1 = y1, o
        y[i] = o
    return y


def slow(rng: random.Random, cycles: list[int], n: int = L) -> array:
    """A smooth wandering line in [-1, 1] that repeats exactly every N samples (whole cycles per loop)."""
    parts = [(rng.uniform(0.5, 1.0) / (k ** 0.5), k, rng.uniform(0, TAU)) for k in cycles]
    total = sum(a for a, _, _ in parts)
    out = array("d", bytes(8 * n))
    for a, k, ph in parts:
        w = TAU * k / N
        for i in range(n):
            out[i] += a * math.sin(w * i + ph)
    return array("d", [v / total for v in out])


def whole(f: float) -> float:
    """The nearest frequency that fits a whole number of times in the loop."""
    return max(1, round(f * LOOP)) / LOOP


def rms(x) -> float:
    return math.sqrt(sum(v * v for v in x) / len(x))


def norm(x: array) -> array:
    k = 1.0 / (rms(x) or 1.0)
    return array("d", [v * k for v in x])


class Mix:
    """A stereo bus of length L (noise beds) that folds into the loop."""

    def __init__(self):
        self.l = array("d", bytes(8 * L))
        self.r = array("d", bytes(8 * L))

    def add(self, x: array, gain: float, pan: float = 0.0, env: array | None = None):
        """pan -1 (left) .. 1 (right), equal power."""
        gl = gain * math.cos((pan + 1) * math.pi / 4)
        gr = gain * math.sin((pan + 1) * math.pi / 4)
        if env is None:
            for i, v in enumerate(x):
                self.l[i] += gl * v
                self.r[i] += gr * v
        else:
            for i, v in enumerate(x):
                e = env[i]
                self.l[i] += gl * v * e
                self.r[i] += gr * v * e

    def add_lr(self, xl: array, xr: array, gain: float, env: array | None = None):
        for i in range(L):
            e = gain * (env[i] if env is not None else 1.0)
            self.l[i] += xl[i] * e
            self.r[i] += xr[i] * e

    def fold(self) -> tuple[array, array]:
        """Cross-fade the tail (samples N..L) into the head: the loop's last sample then runs into its
        first. Every slow change repeats every N samples, so only the noise differs between the two,
        and an equal-power fade keeps the level even."""
        out = []
        for ch in (self.l, self.r):
            y = ch[:N]
            for i in range(XF):
                th = (i / XF) * math.pi / 2
                y[i] = ch[i] * math.sin(th) + ch[i + N] * math.cos(th)
            out.append(y)
        return out[0], out[1]


# ---- the sounds ----

def wind(mix: Mix, rng: random.Random, level: float, whistle: float, gusts: list[int]):
    """Low rumble and a breathy band that rises with each gust; a thin whistle on the strongest."""
    g = slow(rng, gusts)
    env = array("d", [0.18 + 0.82 * ((v + 1) / 2) ** 1.6 for v in g])
    rumble = norm(highpass(lowpass(lowpass(noise(rng), 180), 180), 30))
    mix.add(rumble, level * 0.55, 0.0, env)
    fc = [300 + 650 * e for e in env]
    breath_l = norm(bandpass(noise(rng), fc, 0.8))
    breath_r = norm(bandpass(noise(rng), [f * 1.07 for f in fc], 0.8))
    mix.add_lr(breath_l, breath_r, level * 0.45, env)
    if whistle:
        wf = [700 + 900 * e for e in env]
        w = norm(bandpass(bandpass(noise(rng), wf, 9), wf, 9))
        wenv = array("d", [max(0.0, e - 0.45) ** 1.5 * 2.2 for e in env])
        mix.add(w, level * whistle * 0.25, rng.uniform(-0.4, 0.4), wenv)


def leaves(mix: Mix, rng: random.Random, level: float, gusts: list[int]):
    """Olive leaves: high, grainy noise that comes with the air."""
    g = slow(rng, gusts)
    grain = lowpass(array("d", [abs(v) for v in lowpass(noise(rng), 40)]), 12)
    grain = norm(grain)
    env = array("d", [((v + 1) / 2) ** 2.5 * (0.4 + 0.6 * k) for v, k in zip(g, grain)])
    hiss_l = norm(lowpass(highpass(noise(rng), 1800), 6000))
    hiss_r = norm(lowpass(highpass(noise(rng), 1800), 6000))
    mix.add_lr(hiss_l, hiss_r, level, env)


def cicada(mix: Mix, rng: random.Random, level: float, fc: float, pulse: float, pan: float,
           swell: list[int], floor: float):
    """One cicada: a narrow buzz pulsing tens of times a second, in a slow swell, softened by distance."""
    buzz = norm(lowpass(bandpass(bandpass(noise(rng), fc, 5), fc * 1.02, 5), 6500))
    fp, ft = whole(pulse), whole(rng.uniform(2.5, 6.0))
    ph1, ph2 = rng.uniform(0, TAU), rng.uniform(0, TAU)
    s = slow(rng, swell)
    env = array("d", bytes(8 * L))
    for i in range(L):
        t = i / SR
        p = (0.5 + 0.5 * math.sin(TAU * fp * t + ph1)) ** 3
        trill = 0.65 + 0.35 * math.sin(TAU * ft * t + ph2)
        sw = floor + (1 - floor) * max(0.0, s[i]) ** 1.3
        env[i] = p * trill * sw
    mix.add(buzz, level * 1.6, pan, env)


def bells(rng: random.Random, groups: list[tuple[float, float, float]], gain: float) -> tuple[array, array]:
    """Goat bells far off: clusters of a few strikes (a goat moving), each strike a few inharmonic
    partials with a short click, low-passed for the distance and with a mountain echo. Placed around
    the loop, so a strike near its end rings on at its start. groups: (time, pitch, pan)."""
    ratios, decays, amps = (1.0, 2.71, 5.17, 8.4), (0.55, 0.32, 0.18, 0.1), (1.0, 0.55, 0.3, 0.16)
    bl, br = array("d", bytes(8 * N)), array("d", bytes(8 * N))
    for t0, f0, pan in groups:
        t = t0
        for _ in range(rng.randint(2, 5)):
            g = gain * rng.uniform(0.45, 1.0)
            f = f0 * rng.uniform(0.985, 1.015)
            gl, gr = g * math.cos((pan + 1) * math.pi / 4), g * math.sin((pan + 1) * math.pi / 4)
            start = int(t * SR)
            n = int(1.6 * SR)
            for i in range(n):
                tt = i / SR
                v = sum(a * math.exp(-tt / d) * math.sin(TAU * f * r * tt) for r, d, a in zip(ratios, decays, amps))
                if i < 90:
                    v += 0.6 * (1 - i / 90) * (rng.random() * 2 - 1)
                v *= min(1.0, i / 12)
                j = (start + i) % N
                bl[j] += gl * v
                br[j] += gr * v
            t += rng.uniform(0.22, 0.7)
    out = []
    for ch in (bl, br):
        # distance (low-pass, run round the loop twice so its start matches its end) and an echo
        a = math.exp(-TAU * 2400 / SR)
        s = 0.0
        y = array("d", bytes(8 * N))
        for _ in range(2):
            for i in range(N):
                s = (1 - a) * ch[i] + a * s
                y[i] = s
        e = array("d", y)
        for delay, k in ((0.21, 0.28), (0.47, 0.13)):
            d = int(delay * SR)
            for i in range(N):
                e[i] += k * y[(i - d) % N]
        out.append(e)
    return out[0], out[1]


def spread(rng: random.Random, count: int, gap: tuple[float, float]) -> list[float]:
    """Times for `count` bell clusters around the loop, at least gap[0] seconds apart."""
    t, times = rng.uniform(0, LOOP), []
    for _ in range(count):
        times.append(t % LOOP)
        t += rng.uniform(*gap)
    return times


# ---- the three films ----

def film(stem: str) -> tuple[array, array]:
    rng = random.Random({"f1": 101, "f2": 202, "f3": 303}[stem])
    mix = Mix()
    bell = None
    if stem == "f1":  # Delphi, a mountainside, day and night for centuries
        wind(mix, rng, 1.0, whistle=0.7, gusts=[1, 2, 3, 5, 8])
        times = spread(rng, 3, (8.0, 11.0))
        bell = bells(rng, [(t, rng.choice((640.0, 760.0, 905.0)), rng.uniform(-0.7, 0.7)) for t in times], 0.2)
    elif stem == "f2":  # a village by day: rope for sale, coins in a jar
        wind(mix, rng, 0.55, whistle=0.0, gusts=[1, 3, 4, 7])
        for fc, pulse, pan in ((4300, 46, -0.6), (5100, 61, 0.5), (3900, 38, 0.1)):
            cicada(mix, rng, 0.32, fc, pulse, pan, swell=[1, 2, 3], floor=0.15)
        times = spread(rng, 2, (12.0, 16.0))
        bell = bells(rng, [(t, rng.choice((720.0, 850.0)), rng.uniform(-0.8, 0.8)) for t in times], 0.1)
    else:  # f3: noon under the olive tree, dozing into a dream
        wind(mix, rng, 0.45, whistle=0.0, gusts=[1, 2, 5])
        leaves(mix, rng, 0.28, gusts=[1, 2, 3, 4])
        for fc, pulse, pan in ((4500, 52, -0.7), (5300, 70, 0.6), (4000, 44, -0.2), (4800, 58, 0.25), (5600, 80, 0.85)):
            cicada(mix, rng, 0.36, fc, pulse, pan, swell=[1, 2], floor=0.3)
    left, right = mix.fold()
    if bell:
        for i in range(N):
            left[i] += bell[0][i]
            right[i] += bell[1][i]
    k = 10 ** (TARGET_DB / 20) / (math.sqrt((rms(left) ** 2 + rms(right) ** 2) / 2) or 1.0)
    peak = max(max(map(abs, left)), max(map(abs, right))) * k
    if peak > 0.7:  # leave headroom for the encoder
        k *= 0.7 / peak
    return array("d", [v * k for v in left]), array("d", [v * k for v in right])


def write_wav(path: Path, left: array, right: array, rng: random.Random):
    frames = array("h", bytes(4 * N))
    for i in range(N):
        for c, v in enumerate((left[i], right[i])):
            d = (rng.random() - rng.random()) / 32768  # triangular dither
            frames[2 * i + c] = max(-32768, min(32767, round((v + d) * 32767)))
    if sys.byteorder == "big":
        frames.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames.tobytes())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("films", nargs="*", help="f1, f2 or f3 (default: all three)")
    ap.add_argument("--wav", type=Path, help="also keep the WAVs in this folder")
    args = ap.parse_args(argv)
    args.films = args.films or ["f1", "f2", "f3"]
    if set(args.films) - {"f1", "f2", "f3"}:
        ap.error("the films are f1, f2 and f3")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg is not on the PATH: it encodes the MP3s.", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for stem in args.films:
            left, right = film(stem)
            wav = (args.wav or Path(tmp)) / f"{stem}.wav"
            wav.parent.mkdir(parents=True, exist_ok=True)
            write_wav(wav, left, right, random.Random(7))
            mp3 = OUT / f"{stem}.mp3"
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
                            "-c:a", "libmp3lame", "-b:a", BITRATE, "-map_metadata", "-1",
                            "-metadata", "title=Oknos film ambience " + stem,
                            "-metadata", "copyright=CC BY-SA 4.0, Oknos project (scripts/film_ambience.py)",
                            str(mp3)], check=True)
            print(f"{mp3.relative_to(ROOT).as_posix()}: {mp3.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
