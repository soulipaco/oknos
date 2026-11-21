"""Pre-generate audio for listening passages (docs/SPEC.md §9). Run by the coach, never by the app.

    uv run --with edge-tts python scripts/make_audio.py --engine edge --pack open-everyday-a1a2
    uv run python scripts/make_audio.py --engine windows --pack open-everyday-a1a2

For every item whose stimulus has `tts` text (and no audio file of its own), this writes
learner/audio/<pack-id>/<item-id>.<ext>. The app plays that file instead of the browser voice.
The files are derived from content text, never tracked, and can be regenerated at any time.

Engines, best first by the phase-3 listening test (SPEC §9):
  edge     Microsoft's online neural voices through edge-tts. Sends the passage text to Microsoft,
           so it is only allowed when profile.json has "edge_tts_ok": true (asked once per learner),
           and only for content packs: never for anything under learner/ (captured documents,
           writing, coach packs built from them).
  windows  The local Windows voice (Microsoft Stefanos) through the WinRT speech API. Offline.
  piper    Piper with a Greek voice model in .cache/oknos/piper/. Offline, but the CC0 voice
           garbled sentences in the phase-3 test, so it is a last resort.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oknos import packs, paths  # noqa: E402

EDGE_VOICE = "el-GR-AthinaNeural"
PIPER_MODEL = ROOT / ".cache" / "oknos" / "piper" / "el_GR-rapunzelina-low.onnx"

WINDOWS_PS = r"""
$ErrorActionPreference = "Stop"
[Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $type) { $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$synth.Voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | ? { $_.Language -eq 'el-GR' } | Select-Object -First 1
if (-not $synth.Voice) { throw "no Greek voice installed" }
$text = [System.IO.File]::ReadAllText($args[0], [System.Text.Encoding]::UTF8)
$stream = Await ($synth.SynthesizeTextToStreamAsync($text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
$size = [uint32]$stream.Size
Await ($reader.LoadAsync($size)) ([uint32]) | Out-Null
$bytes = New-Object byte[] $size
$reader.ReadBytes($bytes)
[System.IO.File]::WriteAllBytes($args[1], $bytes)
"""


def read_profile() -> dict:
    try:
        return json.loads(paths.profile_path().read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def edge(text: str, out: Path) -> Path:
    import edge_tts  # installed on demand: uv run --with edge-tts

    target = out.with_suffix(".mp3")
    # The free service sometimes answers with no audio; a retry a moment later usually works.
    for attempt in range(4):
        try:
            asyncio.run(edge_tts.Communicate(text, EDGE_VOICE, rate="-10%").save(str(target)))
            if target.stat().st_size > 1000:
                return target
        except edge_tts.exceptions.NoAudioReceived:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("edge-tts sent no audio after 4 tries")


def windows(text: str, out: Path) -> Path:
    target = out.with_suffix(".wav")
    with tempfile.TemporaryDirectory() as tmp:
        script, src = Path(tmp) / "say.ps1", Path(tmp) / "text.txt"
        script.write_text(WINDOWS_PS, encoding="utf-8-sig")
        src.write_text(text, encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(src), str(target)],
                       check=True, capture_output=True)
    return target


def piper(text: str, out: Path) -> Path:
    from piper import PiperVoice  # installed on demand: uv run --with piper-tts

    target = out.with_suffix(".wav")
    voice = PiperVoice.load(str(PIPER_MODEL))
    with wave.open(str(target), "wb") as wf:
        voice.synthesize_wav(text, wf) if hasattr(voice, "synthesize_wav") else voice.synthesize(text, wf)
    return target


ENGINES = {"edge": edge, "windows": windows, "piper": piper}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=ENGINES, required=True)
    ap.add_argument("--pack", required=True, help="the pack id")
    ap.add_argument("--min-words", type=int, default=8, help="only passages at least this long (default 8)")
    ap.add_argument("--force", action="store_true", help="regenerate files that already exist")
    args = ap.parse_args()

    catalog = packs.load_all()
    pack = next((p for p in catalog.packs if p.id == args.pack), None)
    if pack is None:
        print(f"There is no pack '{args.pack}'.")
        return 1
    if args.engine == "edge":
        if read_profile().get("edge_tts_ok") is not True:
            print('edge-tts sends text to Microsoft. It is off until the learner agrees and profile.json has "edge_tts_ok": true.')
            return 1
        learner = paths.learner_dir().resolve()
        if learner == pack.path.resolve() or learner in pack.path.resolve().parents:
            print("edge-tts is never used for packs under learner/ (they can contain the learner's own documents).")
            return 1

    out_dir = paths.audio_cache_dir() / pack.id
    out_dir.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for item in pack.items.values():
        st = item.stimulus
        if not st or not st.tts or st.audio or len(st.tts.split()) < args.min_words:
            continue
        if any(out_dir.glob(f"{item.id}.*")) and not args.force:
            skipped += 1
            continue
        try:
            path = ENGINES[args.engine](st.tts, out_dir / f"{item.id}.new")
        except Exception as e:  # keep whatever audio was there before
            print(f"  {item.id}: failed ({e}); the previous audio, if any, is kept")
            continue
        for old in out_dir.glob(f"{item.id}.*"):
            if old != path:
                old.unlink()
        path = path.rename(out_dir / f"{item.id}{path.suffix}")
        made += 1
        print(f"  {path.relative_to(paths.learner_dir())}")
    print(f"{made} audio file(s) written with {args.engine}, {skipped} already there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
