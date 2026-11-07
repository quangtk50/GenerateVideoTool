"""Bước 12 - Thống kê & vòng phản hồi.

1. Lấy số liệu (hiện hỗ trợ YouTube; TikTok/Meta cần thêm quyền đọc insights - xem docs).
2. Agent phân tích so sánh video hiệu quả / kém hiệu quả -> ghi data/insights.md.
3. Agent ý tưởng đọc insights.md ở lần tạo sau -> hệ thống tự cải thiện.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from . import config, storage
from .claude_client import ask_structured
from .schemas import Project, StatSnapshot

SYSTEM = """Bạn là chuyên gia phân tích tăng trưởng kênh video ngắn.
Từ bảng số liệu, rút ra 5-8 bài học CỤ THỂ, hành động được ngay: kiểu chủ đề, kiểu hook, độ dài, tone
nào hiệu quả hoặc kém. Kèm 3 gợi ý chủ đề tiếp theo. Viết tiếng Việt, gạch đầu dòng, ngắn gọn."""


class Insights(BaseModel):
    lessons: str = Field(..., description="Các bài học, dạng gạch đầu dòng markdown")
    next_topics: str = Field(..., description="3 gợi ý chủ đề tiếp theo, gạch đầu dòng")


def collect(log=print) -> int:
    """Cập nhật số liệu cho mọi video đã đăng YouTube thật. Trả về số video cập nhật."""
    projects = storage.list_all()
    yt = {r.post_id: p.id for p in projects for r in p.publish
          if r.platform == "youtube" and r.status == "done" and r.post_id}
    if not yt:
        return 0
    from .publishers import youtube
    stats = youtube.stats(list(yt))
    now = datetime.now().isoformat(timespec="seconds")
    for vid, s in stats.items():
        storage.update(yt[vid], lambda p, s=s: p.stats.append(StatSnapshot(platform="youtube", at=now, **s)))
    log(f"Cập nhật số liệu {len(stats)} video YouTube.")
    return len(stats)


def _latest(p: Project):
    return p.stats[-1] if p.stats else None


def write_insights(log=print) -> str:
    rows = []
    for p in storage.list_all():
        s = _latest(p)
        if s and p.script:
            rows.append((s.views, s.likes, s.comments, p))
    if len(rows) < 3:
        log("Chưa đủ 3 video có số liệu để phân tích.")
        return ""
    rows.sort(key=lambda r: r[0], reverse=True)
    table = "\n".join(
        f"| {v} | {lk} | {c} | {p.script.title} | {p.brief.topic} | {p.script.hook} | "
        f"{sum(p.scene_durations().values()):.0f}s | {p.brief.tone} |"
        for v, lk, c, p in rows[:40])
    header = "| views | likes | comments | tiêu đề | chủ đề | hook | thời lượng | tone |\n|---|---|---|---|---|---|---|---|\n"
    if config.use_mock_claude():
        text = "## Bài học (mock)\n- Video nhiều view nhất: " + rows[0][3].script.title
    else:
        ins, _ = ask_structured(SYSTEM, "Số liệu (sắp theo views):\n" + header + table, Insights,
                                max_tokens=2000, model=config.CLAUDE_MODEL_FAST)
        text = f"## Bài học\n{ins.lessons}\n\n## Gợi ý chủ đề tiếp theo\n{ins.next_topics}"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    config.INSIGHTS_FILE.write_text(f"# Insights kênh (cập nhật {stamp})\n\n{text}\n", encoding="utf-8")
    log("Đã cập nhật data/insights.md")
    return text


def run(log=print) -> None:
    try:
        collect(log)
    except Exception as e:  # noqa: BLE001
        log(f"Lấy số liệu lỗi: {e}")
    write_insights(log)
