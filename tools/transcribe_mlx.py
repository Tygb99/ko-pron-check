#!/usr/bin/env python3
"""Transcribe Korean TTS audio with mlx-whisper (Apple Silicon) for `kopron batch`.

    uv run --with mlx-whisper tools/transcribe_mlx.py --out transcripts audio/*.m4a

Writes <name>.txt (text only) and <name>-segments.json next to each other in --out.
Needs ffmpeg/ffprobe on PATH.

Two choices keep the transcript honest:
- condition_on_previous_text=False, so one misheard sentence is not carried into the next;
- segments that start after the last stretch of speech are dropped. Whisper tends to
  invent words ("감사합니다", "구독과 좋아요") in trailing silence. Dropped text is kept
  in the JSON so you can still look at it.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import mlx_whisper

MODEL = "mlx-community/whisper-large-v3-turbo"


def speech_end(path: Path) -> tuple[float, float]:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          "silencedetect=noise=-45dB:d=0.4", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "csv=p=0", str(path)],
                                 capture_output=True, text=True, check=True).stdout)
    if starts and len(starts) > len(ends):
        return starts[-1], total
    return total, total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("audio", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default=MODEL)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for audio in a.audio:
        result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=a.model, language="ko",
                                        condition_on_previous_text=False)
        end, total = speech_end(audio)
        kept = [s for s in result["segments"] if s["start"] < end - 0.2]
        dropped = [s["text"] for s in result["segments"] if s["start"] >= end - 0.2]
        (a.out / f"{audio.stem}.txt").write_text(" ".join(s["text"].strip() for s in kept) + "\n", encoding="utf-8")
        (a.out / f"{audio.stem}-segments.json").write_text(json.dumps(
            {"speech_end": round(end, 2), "duration": round(total, 2),
             "segments": [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"]}
                          for s in result["segments"]],
             "dropped_after_speech": dropped}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{audio.name}: {len(kept)} segments kept, {len(dropped)} dropped after speech", flush=True)


if __name__ == "__main__":
    main()
