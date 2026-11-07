"""Bước 2 - Agent Biên kịch."""
from typing import Optional

from . import config
from .claude_client import ask_structured
from .schemas import Brief, MusicBrief, Scene, Script

SYSTEM = """Bạn là biên kịch video ngắn (TikTok, Reels, Shorts) hàng đầu.
Quy tắc:
- 3 giây đầu phải có hook mạnh: câu hỏi gây tò mò, xung đột, hoặc hình ảnh bất ngờ.
- Mỗi cảnh dài 2-5 giây, tổng thời lượng đúng yêu cầu (sai số tối đa 10%).
- Mỗi cảnh phải thể hiện được bằng HÌNH ẢNH do AI video tạo ra: tránh chữ dài trong khung hình,
  tránh nhiều nhân vật tương tác phức tạp, tránh người nổi tiếng và logo thương hiệu thật.
- Trường "visual" mô tả cụ thể nhân vật, hành động, bối cảnh. Trường "voiceover" ngắn gọn, dùng làm phụ đề.
- Có cao trào và CTA rõ ràng ở cuối.
- Viết bằng ngôn ngữ được yêu cầu."""


def _brief_text(b: Brief) -> str:
    return (f"Chủ đề: {b.topic}\nNền tảng: {b.platform}\nThời lượng: {b.duration} giây\n"
            f"Tone: {b.tone}\nĐối tượng: {b.audience or 'đại chúng'}\nNgôn ngữ: {b.language}")


def write_script(brief: Brief, previous: Optional[Script] = None,
                 feedback: str = "") -> tuple[Script, dict]:
    if config.use_mock_claude():
        return _mock_script(brief), {"model": "mock"}

    prompt = "Viết kịch bản video ngắn theo brief sau:\n" + _brief_text(brief)
    if previous is not None:
        prompt += ("\n\nĐây là bản trước:\n" + previous.model_dump_json(indent=2) +
                   "\n\nHãy viết lại theo góp ý của người duyệt:\n" + (feedback or "làm hay hơn"))
    return ask_structured(SYSTEM, prompt, Script)


def _mock_script(b: Brief) -> Script:
    scenes = [
        Scene(id=1, duration=3, visual="Close-up a young woman waking up startled, alarm clock showing 9:00",
              voiceover="Bạn lại dậy muộn nữa à?"),
        Scene(id=2, duration=4, visual="She rushes through a small apartment kitchen, grabbing toast",
              voiceover=f"Thử ngay mẹo này: {b.topic}"),
        Scene(id=3, duration=4, visual="Calm morning, she sips coffee by a sunny window, smiling",
              voiceover="Chỉ 7 ngày, buổi sáng của bạn sẽ khác hẳn."),
        Scene(id=4, duration=3, visual="She waves at camera on a bright street, city background",
              voiceover="Theo dõi để xem thêm mẹo nhé!"),
    ]
    return Script(title=f"[MOCK] {b.topic}", hook="Bạn lại dậy muộn nữa à?", scenes=scenes,
                  cta="Theo dõi để xem thêm mẹo nhé!",
                  music_brief=MusicBrief(mood="tươi sáng, hứng khởi", genre="lo-fi pop", bpm=100))
