"""Bước 7 (bản demo) - Ghép các shot bằng FFmpeg: chuẩn hóa, nối, phụ đề."""
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from . import config
from .schemas import Script


def _run(args: List[str], cwd: Optional[Path] = None) -> None:
    r = subprocess.run([config.FFMPEG_BIN, "-y", "-loglevel", "error", *args],
                       cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg lỗi: {r.stderr.strip()[-800:]}")


def normalize(src: Path, dst: Path, seconds: float, w: int, h: int, fps: int, crf: int = 28) -> None:
    """Đưa clip về cùng kích thước, fps, codec; cắt/kéo dài đúng thời lượng cảnh."""
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
          f"fps={fps},setsar=1,tpad=stop_mode=clone:stop_duration=15")
    _run(["-i", str(src), "-t", f"{seconds:.2f}", "-vf", vf, "-an",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", str(dst)])


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(script: Script, path: Path) -> None:
    t, lines, n = 0.0, [], 1
    for sc in script.scenes:
        if sc.voiceover.strip():
            lines += [str(n), f"{_ts(t)} --> {_ts(t + sc.duration)}", sc.voiceover.strip(), ""]
            n += 1
        t += sc.duration
    path.write_text("\n".join(lines), encoding="utf-8")


def assemble_demo(script: Script, clips: List[Tuple[int, Path]], workdir: Path,
                  out_name: str = "demo.mp4") -> Path:
    """clips: [(scene_id, file)] theo đúng thứ tự cảnh."""
    w, h, fps = config.DEMO_W, config.DEMO_H, config.DEMO_FPS
    tmp = workdir / "tmp"
    tmp.mkdir(exist_ok=True)
    durations = {s.id: s.duration for s in script.scenes}

    norm_files = []
    for scene_id, src in clips:
        dst = tmp / f"norm_{scene_id:02d}.mp4"
        normalize(src, dst, durations[scene_id], w, h, fps)
        norm_files.append(dst)

    (tmp / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in norm_files), encoding="utf-8")
    _run(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=tmp)

    # Phụ đề: chạy ffmpeg trong thư mục tmp để tránh lỗi đường dẫn Windows trong filter subtitles
    write_srt(script, tmp / "subs.srt")
    out = workdir / out_name
    style = "FontName=Arial,FontSize=14,Outline=2,Alignment=2,MarginV=40"
    try:
        _run(["-i", "joined.mp4", "-vf", f"subtitles=subs.srt:force_style='{style}'",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
              "-movflags", "+faststart", str(out.resolve())], cwd=tmp)
    except RuntimeError:
        # FFmpeg không có libass -> xuất bản không phụ đề
        _run(["-i", "joined.mp4", "-c", "copy", "-movflags", "+faststart", str(out.resolve())], cwd=tmp)
    return out
