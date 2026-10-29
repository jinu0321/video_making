"""Edge TTS narration: one request per sentence, word timings from WordBoundary.

Run with the edge-tts tool environment:
  ~/.local/share/uv/tools/edge-tts/bin/python tools/tts.py

Writes assets/audio/narration.wav and build/timing.json.
"""
import asyncio
import hashlib
import json
import subprocess
import wave
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "tts_cache"
SR = 48000
LEAD = 0.06          # keep this much before the first word
TAIL = 0.20          # keep this much after the last word ends
GAP_IN_SHOT = 0.22   # silence between sentences of one shot
GAP_SHOT = 0.32      # silence between shots
START_PAD = 0.15     # silence before the first word of the film
END_HOLD = 1.6       # last frame holds this long after the voice ends


def sentence_parts(s, pronounce):
    """(shown text, spoken text). An explicit "say" wins; otherwise terms in content["pronounce"] are swapped."""
    if not isinstance(s, str):
        if "say" in s:
            return s["text"], s["say"]
        s = s["text"]
    say = s
    for term in sorted(pronounce, key=len, reverse=True):   # longest first, so "MySQL" goes before "SQL"
        say = say.replace(term, pronounce[term])
    return s, say


async def synth(text, voice, rate):
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16]
    mp3, meta = CACHE / f"{key}.mp3", CACHE / f"{key}.json"
    if mp3.exists() and meta.exists():
        return mp3, json.loads(meta.read_text())
    words = []
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"text": chunk["text"],
                              "start": chunk["offset"] / 1e7,
                              "end": (chunk["offset"] + chunk["duration"]) / 1e7})
    meta.write_text(json.dumps(words, ensure_ascii=False))
    return mp3, words


def decode(mp3):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return raw


def fade(raw, n_in, n_out):
    import array
    a = array.array("h", raw)
    for i in range(min(n_in, len(a))):
        a[i] = int(a[i] * i / n_in)
    for i in range(min(n_out, len(a))):
        a[-1 - i] = int(a[-1 - i] * i / n_out)
    return a.tobytes()


def main():
    content = json.loads((ROOT / "content.json").read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    pcm = bytearray(b"\x00\x00" * int(START_PAD * SR))
    shots = []
    for si, shot in enumerate(content["shots"]):
        if si > 0:
            hold = content["shots"][si - 1].get("hold", 0)
            pcm += b"\x00\x00" * int((GAP_SHOT + hold) * SR)
        sents = []
        for k, s in enumerate(shot["sentences"]):
            if k > 0:
                pcm += b"\x00\x00" * int(GAP_IN_SHOT * SR)
            text, say = sentence_parts(s, content.get("pronounce", {}))
            mp3, words = asyncio.run(synth(say, content["voice"], content["rate"]))
            raw = decode(mp3)
            dur = len(raw) / 2 / SR
            t0 = max(0.0, words[0]["start"] - LEAD)
            t1 = min(dur, words[-1]["end"] + TAIL)
            seg = fade(raw[int(t0 * SR) * 2:int(t1 * SR) * 2], int(0.005 * SR), int(0.04 * SR))
            base = len(pcm) / 2 / SR
            pcm += seg
            shown = text.split()
            if len(shown) != len(words):
                raise SystemExit(f"word count mismatch in shot {si + 1}: {text!r} "
                                 f"vs {[w['text'] for w in words]}")
            sents.append({
                "text": text,
                "start": round(base, 3),
                "end": round(base + (t1 - t0), 3),
                "words": [{"text": shown[i],
                           "start": round(base + w["start"] - t0, 3),
                           "end": round(base + w["end"] - t0, 3)} for i, w in enumerate(words)],
            })
        shots.append({"sentences": sents})
    voice_end = len(pcm) / 2 / SR
    pcm += b"\x00\x00" * int(END_HOLD * SR)

    raw_wav = ROOT / "build" / "narration_raw.wav"
    with wave.open(str(raw_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(pcm))
    out = ROOT / "assets" / "audio" / "narration.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw_wav),
                    "-af", "loudnorm=I=-17:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "1",
                    str(out)], check=True)
    raw_wav.unlink()
    timing = {"duration": round(len(pcm) / 2 / SR, 3), "voice_end": round(voice_end, 3),
              "shots": shots}
    (ROOT / "build" / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1))
    print(f"narration {voice_end:.2f}s, film {timing['duration']:.2f}s, "
          f"{sum(len(s['sentences']) for s in shots)} sentences")


if __name__ == "__main__":
    main()
