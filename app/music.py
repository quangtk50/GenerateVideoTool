"""Bước 7 - Nhạc nền: chọn file trong assets/music theo mood/genre của kịch bản.

Đặt nhạc có bản quyền hợp lệ (YouTube Audio Library, Pixabay Music, Suno bản trả phí...) vào assets/music/.
Đặt tên file có từ khoá để hệ thống chọn đúng, VD: "lofi_chill_vui-tuoi.mp3", "epic_cinematic_hung-tráng.mp3".
"""
import random
import unicodedata
from pathlib import Path
from typing import Optional

from . import config
from .schemas import MusicBrief

EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def pick(brief: Optional[MusicBrief], seed: int = 0) -> Optional[Path]:
    files = [f for f in config.MUSIC_DIR.rglob("*") if f.suffix.lower() in EXTS]
    if not files:
        return None
    if brief:
        words = {w for w in _norm(f"{brief.mood} {brief.genre}").replace(",", " ").replace("-", " ").split() if len(w) > 2}
        scored = [(sum(w in _norm(f.stem) for w in words), f) for f in files]
        best = max(s for s, _ in scored)
        if best > 0:
            files = [f for s, f in scored if s == best]
    return random.Random(seed).choice(files)
