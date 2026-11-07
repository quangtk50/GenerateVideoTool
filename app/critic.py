"""Bước 2b - Agent Phản biện: chấm kịch bản, nếu dưới ngưỡng thì trả góp ý cho biên kịch viết lại."""
from . import config
from .claude_client import ask_structured
from .schemas import Brief, Critique, Script

SYSTEM = """Bạn là biên tập viên khó tính của một kênh video ngắn triệu view.
Chấm kịch bản theo các tiêu chí:
1. Hook 3 giây đầu có khiến người xem dừng lướt không?
2. Nhịp: mỗi cảnh có thông tin mới, không lan man; có cao trào; CTA rõ.
3. Lời thoại đọc vừa thời lượng từng cảnh (~3 từ tiếng Việt/giây), tự nhiên khi đọc to.
4. Chính xác: không sai sự thật, không lời khuyên y tế/tài chính nguy hiểm.
5. Chính sách nền tảng: không bạo lực, nội dung người lớn, người nổi tiếng thật, thương hiệu thật.
6. Khả thi khi dựng bằng AI video/ảnh/stock: tránh chữ trong khung hình, đám đông tương tác phức tạp.
7. Tổng thời lượng đúng brief (sai số 10%).
Cho điểm khắt khe (7 = dùng được, 9 = xuất sắc). "fixes" phải là chỉ dẫn sửa cụ thể, làm được ngay."""


def critique(brief: Brief, script: Script) -> tuple:
    if config.use_mock_claude():
        return Critique(score=8, hook_score=8, strengths=["(mock) hook rõ"], problems=[],
                        fixes=""), {"model": "mock"}
    prompt = (f"Brief:\nChủ đề: {brief.topic}\nNền tảng: {brief.platform}\nThời lượng: {brief.duration}s\n"
              f"Tone: {brief.tone}\nĐối tượng: {brief.audience or 'đại chúng'}\n\n"
              f"Kịch bản (tổng {script.total_duration:.0f}s):\n{script.model_dump_json(indent=2)}")
    return ask_structured(SYSTEM, prompt, Critique, max_tokens=2000, model=config.CLAUDE_MODEL_FAST)


def feedback_text(c: Critique) -> str:
    probs = "\n".join(f"- {p}" for p in c.problems)
    return f"Điểm {c.score}/10 (hook {c.hook_score}/10).\nVấn đề:\n{probs}\nCách sửa: {c.fixes}"
