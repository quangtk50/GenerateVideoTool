"""Tiện ích dùng chung: chạy FFmpeg/FFprobe, tải file."""
import json
import subprocess
from pathlib import Path
from typing import List, Optional

import httpx

from . import config


def ffmpeg(args: List[str], cwd: Optional[Path] = None, timeout: int = 1800) -> str:
    r = subprocess.run([config.FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", *args],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg lỗi: {r.stderr.strip()[-1200:]}")
    return r.stderr


def ffmpeg_stderr(args: List[str], cwd: Optional[Path] = None) -> str:
    """Chạy FFmpeg ở mức log info để đọc kết quả phân tích (blackdetect, loudnorm...)."""
    r = subprocess.run([config.FFMPEG_BIN, "-hide_banner", *args], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stderr


def probe(path: Path) -> dict:
    r = subprocess.run([config.FFPROBE_BIN, "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"FFprobe lỗi với {path.name}: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout)


def duration(path: Path) -> float:
    info = probe(path)
    try:
        return float(info["format"]["duration"])
    except (KeyError, ValueError):
        return max(float(s.get("duration", 0) or 0) for s in info.get("streams", [{}]))


def download(url: str, dest: Path, headers: Optional[dict] = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=300, follow_redirects=True, headers=headers) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
        tmp.replace(dest)
    return dest
