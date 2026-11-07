"""Bước 1 (tuỳ chọn) - Agent Lên ý tưởng: tự nghĩ chủ đề video khi người dùng bấm "Tự tạo ý tưởng"."""
import random
from typing import List

from . import config
from .claude_client import ask_structured
from .schemas import Brief, Idea

SYSTEM = """Bạn là chuyên gia chiến lược nội dung video ngắn (TikTok, Reels, Shorts).
Nhiệm vụ: đề xuất MỘT ý tưởng video mới, có khả năng giữ chân người xem và dễ chia sẻ.
Quy tắc:
- Cụ thể, có góc nhìn riêng (không chung chung kiểu "mẹo sống khỏe").
- Thể hiện được bằng hình ảnh do AI video tạo: tránh người nổi tiếng, logo thương hiệu thật,
  chữ dài trong khung hình, cảnh nhiều nhân vật tương tác phức tạp.
- Đa dạng lĩnh vực: đời sống, công việc, tài chính cá nhân, sức khỏe, tâm lý, du lịch, ẩm thực,
  công nghệ, kiến thức thú vị, truyện ngắn cảm xúc...
- KHÔNG trùng hoặc gần giống các chủ đề đã làm gần đây.
- Viết bằng ngôn ngữ được yêu cầu."""

MOCK_IDEAS = [
    ("3 thói quen buổi sáng giúp làm việc hiệu quả hơn", "dân văn phòng 22-30", "năng động, truyền cảm hứng"),
    ("Quy tắc 50/30/20: chia lương sao cho cuối tháng vẫn còn tiền", "người mới đi làm", "gần gũi, thực tế"),
    ("Chuyện chú mèo hoang mỗi tối đợi bà cụ bán xôi", "đại chúng", "ấm áp, cảm động"),
    ("Vì sao bạn luôn mệt dù ngủ đủ 8 tiếng?", "người trẻ hay thức khuya", "tò mò, khoa học"),
    ("1 ngày khám phá phố cổ Hội An chỉ với 300 nghìn", "sinh viên thích du lịch", "vui tươi, phiêu lưu"),
    ("Mẹo bàn làm việc gọn gàng trong 5 phút", "người làm việc tại nhà", "nhẹ nhàng, thư giãn"),
    ("Món trứng chiên 'nhà hàng' chỉ với 3 nguyên liệu", "người bận rộn", "hấp dẫn, nhanh gọn"),
    ("Điều gì xảy ra với cơ thể khi bạn bỏ điện thoại 1 ngày?", "đại chúng", "bất ngờ, suy ngẫm"),
]


def generate_idea(brief: Brief, recent_topics: List[str]) -> tuple[Idea, dict]:
    if config.use_mock_claude():
        pool = [i for i in MOCK_IDEAS if i[0] not in recent_topics] or MOCK_IDEAS
        topic, audience, tone = random.choice(pool)
        return Idea(topic=topic, audience=audience, tone=tone, reason="(ý tưởng mẫu - chế độ thử)"), {"model": "mock"}

    recent = "\n".join(f"- {t}" for t in recent_topics) or "(chưa có)"
    prompt = (f"Nền tảng: {brief.platform}\nThời lượng: {brief.duration} giây\nNgôn ngữ: {brief.language}\n\n"
              f"Các chủ đề đã làm gần đây (tránh trùng):\n{recent}\n\nHãy đề xuất 1 ý tưởng mới.")
    return ask_structured(SYSTEM, prompt, Idea, max_tokens=1500)
