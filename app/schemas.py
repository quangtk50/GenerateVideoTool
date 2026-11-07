"""Schema dữ liệu dùng chung giữa các bước. Mọi agent Claude phải trả về đúng các schema này."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------- Bước 1: Ý tưởng ----------
class Idea(BaseModel):
    topic: str = Field(..., description="Chủ đề / ý tưởng video, 1-2 câu, cụ thể")
    audience: str = Field(..., description="Đối tượng người xem mục tiêu")
    tone: str = Field(..., description="Tone cảm xúc của video")
    reason: str = Field(..., description="Vì sao ý tưởng này hút người xem (1 câu)")


# ---------- Bước 2: Kịch bản ----------
class Scene(BaseModel):
    id: int = Field(..., description="Số thứ tự cảnh, bắt đầu từ 1")
    duration: float = Field(..., ge=1, le=15, description="Thời lượng cảnh tính bằng giây")
    visual: str = Field(..., description="Mô tả hình ảnh: nhân vật, hành động, bối cảnh")
    voiceover: str = Field("", description="Lời thoại đọc bằng giọng AI, cũng dùng làm phụ đề")


class MusicBrief(BaseModel):
    mood: str = Field(..., description="Cảm xúc nhạc nền")
    genre: str = Field(..., description="Thể loại nhạc")
    bpm: int = Field(..., ge=60, le=180)


class Script(BaseModel):
    title: str
    hook: str = Field(..., description="Câu/ý mở đầu giữ chân người xem trong 3 giây đầu")
    scenes: List[Scene]
    cta: str = Field(..., description="Lời kêu gọi hành động ở cuối video")
    music_brief: MusicBrief

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)


# ---------- Bước 2b: Agent phản biện ----------
class Critique(BaseModel):
    score: int = Field(..., ge=1, le=10, description="Điểm tổng thể 1-10")
    hook_score: int = Field(..., ge=1, le=10, description="Độ mạnh của hook 3 giây đầu")
    strengths: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list,
                                description="Vấn đề: hook yếu, sai sự thật, vi phạm chính sách, sai thời lượng, khó dựng bằng AI...")
    fixes: str = Field("", description="Hướng dẫn sửa cụ thể cho biên kịch")


# ---------- Bước 3: Phân cảnh đạo diễn ----------
VisualSource = Literal["ai_video", "ai_image", "stock"]


class Shot(BaseModel):
    scene_id: int
    framing: str = Field(..., description="Cỡ cảnh: extreme close-up, close-up, medium, wide...")
    angle: str = Field(..., description="Góc máy: eye level, low angle, high angle, over-the-shoulder...")
    camera_move: str = Field(..., description="Chuyển động máy: static, push-in, pull-out, pan, orbit, handheld...")
    lighting: str
    action: str = Field(..., description="Hành động và diễn xuất của nhân vật")
    emotion: str
    source: VisualSource = Field("ai_video", description=(
        "Nguồn hình: ai_video = cảnh có nhân vật/hành động cần AI video; "
        "ai_image = cảnh tĩnh, minh hoạ, khái niệm (ảnh AI + hiệu ứng zoom); "
        "stock = cảnh chung chung có sẵn ngoài đời (thành phố, thiên nhiên, đồ vật)"))
    stock_query: str = Field("", description="2-4 từ khoá TIẾNG ANH để tìm video stock (bắt buộc nếu source=stock)")
    prompt: str = Field(..., description="Prompt tiếng Anh hoàn chỉnh gửi cho model video/ảnh")


class ShotList(BaseModel):
    style: str = Field(..., description="Phong cách hình ảnh chung cho mọi shot")
    characters: str = Field("", description="Mô tả cố định ngoại hình nhân vật để giữ đồng nhất")
    shots: List[Shot]


# ---------- Bước 5: Lời thoại ----------
class SceneAudio(BaseModel):
    scene_id: int
    text: str = ""
    file: Optional[str] = None
    duration: float = 0.0
    provider: str = ""
    words: List[List] = Field(default_factory=list)   # [[start, end, "từ"], ...] tính từ đầu cảnh


# ---------- Bước 9: QA ----------
class QAIssue(BaseModel):
    scene_id: int = Field(0, description="0 = lỗi chung của cả video")
    severity: Literal["low", "medium", "high"] = "medium"
    description: str


class QAReport(BaseModel):
    passed: bool
    summary: str = ""
    issues: List[QAIssue] = Field(default_factory=list)


# ---------- Bước 10: SEO / metadata ----------
class Metadata(BaseModel):
    youtube_title: str = Field(..., description="Tiêu đề YouTube Shorts <= 90 ký tự, có từ khoá chính")
    youtube_description: str = Field(..., description="Mô tả YouTube 2-4 câu + hashtag")
    tags: List[str] = Field(default_factory=list, description="10-15 tag YouTube")
    tiktok_caption: str = Field(..., description="Caption TikTok ngắn, cuốn, kèm 3-5 hashtag")
    facebook_caption: str = Field(..., description="Caption Facebook Reels")
    instagram_caption: str = Field(..., description="Caption Instagram Reels kèm hashtag")
    hashtags: List[str] = Field(default_factory=list)
    thumbnail_text: str = Field(..., description="Chữ trên thumbnail, tối đa 5 từ, IN HOA được")


# ---------- Trạng thái dự án ----------
class Status(str, Enum):
    IDEATING = "ideating"
    WRITING = "writing"
    CRITIQUING = "critiquing"
    REVIEW_SCRIPT = "review_script"      # Cổng 1
    DIRECTING = "directing"
    VOICING = "voicing"
    RENDERING = "rendering"
    ASSEMBLING = "assembling"
    QA = "qa"
    PACKAGING = "packaging"
    REVIEW_FINAL = "review_final"        # Cổng 2
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    DEMO_READY = "demo_ready"            # tương thích dự án cũ của bản MVP
    FAILED = "failed"


STATUS_LABEL = {
    Status.IDEATING: "AI đang nghĩ ý tưởng",
    Status.WRITING: "Claude đang viết kịch bản",
    Status.CRITIQUING: "Agent phản biện đang chấm kịch bản",
    Status.REVIEW_SCRIPT: "Chờ duyệt kịch bản (Cổng 1)",
    Status.DIRECTING: "Claude đang phân cảnh",
    Status.VOICING: "Đang tạo lời thoại",
    Status.RENDERING: "Đang tạo hình ảnh/video",
    Status.ASSEMBLING: "FFmpeg đang dựng video",
    Status.QA: "Đang kiểm tra chất lượng",
    Status.PACKAGING: "Đang viết tiêu đề, thumbnail",
    Status.REVIEW_FINAL: "Chờ duyệt video (Cổng 2)",
    Status.PUBLISHING: "Đang đăng bài",
    Status.PUBLISHED: "Đã đăng",
    Status.DEMO_READY: "Demo (bản cũ)",
    Status.FAILED: "Lỗi",
}

BUSY = {Status.IDEATING, Status.WRITING, Status.CRITIQUING, Status.DIRECTING, Status.VOICING,
        Status.RENDERING, Status.ASSEMBLING, Status.QA, Status.PACKAGING, Status.PUBLISHING}

PLATFORMS = {"youtube": "YouTube Shorts", "tiktok": "TikTok",
             "facebook": "Facebook Reels", "instagram": "Instagram Reels"}


class Brief(BaseModel):
    topic: str
    platform: str = "TikTok"                # nền tảng chính để viết kịch bản
    duration: int = 30
    tone: str = "cuốn hút, cảm xúc"
    audience: str = ""
    language: str = "Tiếng Việt"
    resolution: str = "720p"
    visual_mode: str = "auto"               # auto | ai_video | ai_image | stock
    voice: str = ""                         # trống = theo .env
    with_music: bool = True
    platforms: List[str] = Field(default_factory=list)   # nơi sẽ đăng: youtube, tiktok, facebook, instagram
    auto_approve_script: bool = False
    auto_publish: bool = False


class ShotRender(BaseModel):
    scene_id: int
    seed: int
    status: str = "pending"          # pending | running | done | failed
    source: str = ""                 # nguồn thực tế đã dùng: ai_video | ai_image | stock | mock
    provider: str = ""
    task_id: Optional[str] = None
    file: Optional[str] = None
    error: Optional[str] = None


class PublishResult(BaseModel):
    platform: str
    status: str = "pending"          # pending | running | dry_run | done | failed
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    at: Optional[str] = None


class StatSnapshot(BaseModel):
    platform: str
    at: str
    views: int = 0
    likes: int = 0
    comments: int = 0


class Project(BaseModel):
    id: str
    created_at: str
    brief: Brief
    status: Status
    script: Optional[Script] = None
    critiques: List[Critique] = []
    script_approved: bool = False
    shot_list: Optional[ShotList] = None
    voices: List[SceneAudio] = []
    renders: List[ShotRender] = []
    music_file: Optional[str] = None
    final_file: Optional[str] = None
    demo_file: Optional[str] = None          # bản MVP cũ
    thumbnail_file: Optional[str] = None
    qa: Optional[QAReport] = None
    metadata: Optional[Metadata] = None
    publish: List[PublishResult] = []
    stats: List[StatSnapshot] = []
    error: Optional[str] = None
    log: List[str] = []
    cost_log: List[dict] = []

    def scene_durations(self) -> Dict[int, float]:
        """Thời lượng thật của từng cảnh = max(kịch bản, lời thoại + khoảng nghỉ)."""
        from . import config
        voice = {v.scene_id: v.duration for v in self.voices}
        out = {}
        for sc in (self.script.scenes if self.script else []):
            d = sc.duration
            if voice.get(sc.id):
                d = max(d, voice[sc.id] + config.VOICE_PADDING)
            out[sc.id] = round(d, 2)
        return out
