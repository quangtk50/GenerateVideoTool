"""Bước 9 - Kiểm tra chất lượng video thành phẩm.

- Kỹ thuật (FFprobe/FFmpeg): thời lượng, độ phân giải, có âm thanh, đoạn đen kéo dài.
- Hình ảnh (Claude vision): xem 1 khung hình mỗi cảnh, phát hiện tay/mặt méo, chữ lỗi, nội dung nhạy cảm,
  hình không khớp kịch bản.
"""
import re
from pathlib import Path
from typing import List

from . import config
from .claude_client import ask_structured
from .ffutil import ffmpeg, ffmpeg_stderr, probe
from .schemas import Project, QAIssue, QAReport

SYSTEM = """Bạn là người kiểm duyệt chất lượng video AI trước khi đăng.
Bạn nhận 1 khung hình giữa mỗi cảnh (theo thứ tự) và mô tả cảnh tương ứng.
Tìm lỗi: tay/ngón tay/mặt bị méo, nhân vật biến dạng, chữ vô nghĩa trong khung hình, logo thương hiệu thật,
nội dung nhạy cảm/vi phạm chính sách, hình không khớp mô tả, nhân vật không đồng nhất giữa các cảnh.
severity: high = phải sửa trước khi đăng; medium = nên sửa; low = góp ý nhỏ.
passed = false nếu có lỗi high."""


def technical(video: Path, expected: float, w: int, h: int) -> List[QAIssue]:
    issues = []
    info = probe(video)
    vs = [s for s in info["streams"] if s["codec_type"] == "video"]
    aus = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"].get("duration", 0))
    if not vs:
        return [QAIssue(severity="high", description="Không có luồng video")]
    if (vs[0]["width"], vs[0]["height"]) != (w, h):
        issues.append(QAIssue(severity="medium", description=f"Độ phân giải {vs[0]['width']}x{vs[0]['height']} khác {w}x{h}"))
    if not aus:
        issues.append(QAIssue(severity="high", description="Video không có âm thanh"))
    if abs(dur - expected) > 1.0:
        issues.append(QAIssue(severity="medium", description=f"Thời lượng {dur:.1f}s lệch dự kiến {expected:.1f}s"))
    log = ffmpeg_stderr(["-i", str(video), "-vf", "blackdetect=d=1.0:pix_th=0.10", "-an", "-f", "null", "-"])
    for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", log):
        s, e = float(m.group(1)), float(m.group(2))
        if s > 0.5 and e < dur - 0.8:
            issues.append(QAIssue(severity="high", description=f"Khung hình đen từ {s:.1f}s đến {e:.1f}s"))
    return issues


def _frames(p: Project, video: Path, tmp: Path) -> List[bytes]:
    out, t = [], 0.0
    durations = p.scene_durations()
    for sc in p.script.scenes:
        mid = t + durations[sc.id] / 2
        f = tmp / f"qa_{sc.id:02d}.jpg"
        ffmpeg(["-ss", f"{mid:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(f)])
        out.append(f.read_bytes())
        t += durations[sc.id]
    return out


def check(p: Project, video: Path, workdir: Path) -> tuple:
    w, h = config.frame_size(p.brief.resolution)
    durations = p.scene_durations()
    issues = technical(video, sum(durations.values()), w, h)
    usage = {"model": "none"}
    summary = "Kiểm tra kỹ thuật xong."
    if config.QA_VISION and not config.use_mock_claude():
        try:
            imgs = _frames(p, video, workdir / "tmp")
            shots = {s.scene_id: s for s in (p.shot_list.shots if p.shot_list else [])}
            desc = "\n".join(f"Cảnh {sc.id} (ảnh {i + 1}): {sc.visual}"
                             + (f" | prompt: {shots[sc.id].prompt}" if sc.id in shots else "")
                             for i, sc in enumerate(p.script.scenes))
            rep, usage = ask_structured(SYSTEM, "Mô tả các cảnh:\n" + desc, QAReport, max_tokens=2000,
                                        images=imgs, model=config.CLAUDE_MODEL_FAST)
            issues += rep.issues
            summary = rep.summary or summary
        except Exception as e:  # noqa: BLE001 - QA hình lỗi không chặn luồng
            issues.append(QAIssue(severity="low", description=f"Bỏ qua QA hình ảnh: {str(e)[:200]}"))
    passed = not any(i.severity == "high" for i in issues)
    return QAReport(passed=passed, summary=summary, issues=issues), usage
