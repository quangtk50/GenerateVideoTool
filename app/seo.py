"""Bước 10 - Agent SEO: tiêu đề, mô tả, hashtag cho từng nền tảng + chữ trên thumbnail."""
from . import config
from .claude_client import ask_structured
from .schemas import Brief, Metadata, Script

SYSTEM = """Bạn là chuyên gia tăng trưởng kênh YouTube Shorts, TikTok, Facebook Reels, Instagram Reels.
Viết metadata cho video dựa trên kịch bản:
- Tiêu đề YouTube: gây tò mò nhưng không giật tít sai sự thật, có từ khoá chính, <= 90 ký tự, kết thúc bằng #Shorts.
- Caption mỗi nền tảng hợp văn hoá nền tảng đó (TikTok ngắn và bắt trend; Facebook kể chuyện hơn; Instagram thẩm mỹ).
- Hashtag: mix 1-2 hashtag rộng + 3-4 hashtag ngách, đúng ngôn ngữ người xem.
- thumbnail_text: tối đa 5 từ, đọc được trong 1 giây.
- Viết bằng ngôn ngữ của kịch bản."""


def make_metadata(brief: Brief, script: Script) -> tuple:
    if config.use_mock_claude():
        tags = ["meo hay", "video ngan", "shorts"]
        return Metadata(
            youtube_title=f"{script.title[:70]} #Shorts",
            youtube_description=f"{script.hook} {script.cta}\n#Shorts #meohay",
            tags=tags, tiktok_caption=f"{script.hook} #fyp #meohay",
            facebook_caption=f"{script.hook}\n{script.cta}",
            instagram_caption=f"{script.hook} #reels #meohay",
            hashtags=["#meohay", "#shorts"], thumbnail_text=script.hook[:30]), {"model": "mock"}
    prompt = (f"Đối tượng: {brief.audience or 'đại chúng'}\nTone: {brief.tone}\n\n"
              f"Kịch bản:\n{script.model_dump_json(indent=2)}")
    return ask_structured(SYSTEM, prompt, Metadata, max_tokens=2500, model=config.CLAUDE_MODEL_FAST)
