"""Bước 5 - Lời thoại: chuyển voiceover từng cảnh thành file audio (kèm mốc thời gian từng từ nếu có).

Nhà cung cấp (TTS_PROVIDER):
  edge        - Microsoft Edge TTS, miễn phí, giọng Việt vi-VN-HoaiMyNeural / vi-VN-NamMinhNeural
  elevenlabs  - giọng tự nhiên nhất, clone giọng riêng; trả kèm mốc thời gian từng ký tự
  fpt         - FPT.AI, giọng Việt bản địa (banmai, leminh, thuminh...)
  none        - không lồng tiếng (chỉ phụ đề + nhạc)
"""
import asyncio
import base64
import time
from pathlib import Path
from typing import List

import httpx

from . import config
from .ffutil import download, duration, ffmpeg
from .schemas import SceneAudio


def synthesize(text: str, dest: Path, voice: str = "") -> SceneAudio:
    """Tạo audio cho 1 đoạn thoại. dest không cần đuôi; hàm tự đặt .mp3."""
    text = text.strip()
    dest = dest.with_suffix(".mp3")
    provider = "mock" if config.mock_media() else config.TTS_PROVIDER
    if not text or provider == "none":
        return SceneAudio(scene_id=0, text=text, provider=provider)

    words: List[List] = []
    if provider == "edge":
        words = _edge(text, dest, voice or config.EDGE_VOICE)
    elif provider == "elevenlabs":
        words = _elevenlabs(text, dest, voice or config.ELEVENLABS_VOICE_ID)
    elif provider == "fpt":
        _fpt(text, dest, voice or config.FPT_VOICE)
    elif provider == "mock":
        _mock(text, dest)
    else:
        raise ValueError(f"TTS_PROVIDER không hợp lệ: {provider}")
    return SceneAudio(scene_id=0, text=text, file=dest.name, duration=round(duration(dest), 3),
                      provider=provider, words=words)


# ---------------- Edge TTS (miễn phí) ----------------
def _edge(text: str, dest: Path, voice: str) -> List[List]:
    import edge_tts

    async def run():
        try:
            comm = edge_tts.Communicate(text, voice, rate=config.EDGE_RATE, boundary="WordBoundary")
        except TypeError:   # bản edge-tts cũ không có tham số boundary (mặc định đã là WordBoundary)
            comm = edge_tts.Communicate(text, voice, rate=config.EDGE_RATE)
        words, audio = [], bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append([round(start, 3), round(start + chunk["duration"] / 1e7, 3), chunk["text"]])
        dest.write_bytes(bytes(audio))
        return words

    last = None
    for attempt in range(3):
        try:
            return asyncio.run(run())
        except Exception as e:  # noqa: BLE001 - lỗi mạng tạm thời
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Edge TTS lỗi: {last}")


# ---------------- ElevenLabs ----------------
def _elevenlabs(text: str, dest: Path, voice_id: str) -> List[List]:
    if not (config.ELEVENLABS_API_KEY and voice_id):
        raise RuntimeError("Thiếu ELEVENLABS_API_KEY hoặc ELEVENLABS_VOICE_ID")
    r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
                   params={"output_format": "mp3_44100_128"},
                   headers={"xi-api-key": config.ELEVENLABS_API_KEY},
                   json={"text": text, "model_id": config.ELEVENLABS_MODEL}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    dest.write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or {}
    return _chars_to_words(al.get("characters", []), al.get("character_start_times_seconds", []),
                           al.get("character_end_times_seconds", []))


def _chars_to_words(chars, starts, ends) -> List[List]:
    words, cur, s, e = [], "", None, None
    for ch, st, en in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append([round(s, 3), round(e, 3), cur])
            cur, s = "", None
            continue
        if s is None:
            s = st
        cur += ch
        e = en
    if cur:
        words.append([round(s, 3), round(e, 3), cur])
    return words


# ---------------- FPT.AI ----------------
def _fpt(text: str, dest: Path, voice: str) -> None:
    if not config.FPT_API_KEY:
        raise RuntimeError("Thiếu FPT_API_KEY")
    r = httpx.post("https://api.fpt.ai/hmi/tts/v5", content=text.encode("utf-8"), timeout=60,
                   headers={"api-key": config.FPT_API_KEY, "voice": voice, "speed": "", "format": "mp3"})
    data = r.json()
    if data.get("error") not in (0, None) or not data.get("async"):
        raise RuntimeError(f"FPT.AI lỗi: {data}")
    url = data["async"]
    for _ in range(40):          # file được tạo bất đồng bộ, thường mất 2-10 giây
        time.sleep(2)
        head = httpx.get(url, timeout=60)
        if head.status_code == 200 and len(head.content) > 1000:
            dest.write_bytes(head.content)
            return
    download(url, dest)


# ---------------- Mock ----------------
def _mock(text: str, dest: Path) -> None:
    """Âm thanh giả (tiếng 'bíp' nhỏ) dài theo số từ, để chạy thử không cần mạng."""
    secs = max(1.0, len(text.split()) * 0.33)
    ffmpeg(["-f", "lavfi", "-i", f"sine=frequency=330:duration={secs:.2f}",
            "-af", "volume=0.25", "-c:a", "libmp3lame", "-b:a", "128k", str(dest)])
