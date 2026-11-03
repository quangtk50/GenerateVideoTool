"""Schema dữ liệu dùng chung giữa các bước. Claude phải trả về đúng các schema này."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Kịch bản (Bước 2) ----------
class Scene(BaseModel):
    id: int = Field(..., description="Số thứ tự cảnh, bắt đầu từ 1")
    duration: float = Field(..., ge=1, le=15, description="Thời lượng cảnh tính bằng giây")
    visual: str = Field(..., description="Mô tả hình ảnh: nhân vật, hành động, bối cảnh")
    voiceover: str = Field("", description="Lời thoại / chữ hiển thị trên màn hình (phụ đề)")


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


# ---------- Phân cảnh đạo diễn (Bước 3) ----------
class Shot(BaseModel):
    scene_id: int
    framing: str = Field(..., description="Cỡ cảnh: extreme close-up, close-up, medium, wide...")
    angle: str = Field(..., description="Góc máy: eye level, low angle, high angle, over-the-shoulder...")
    camera_move: str = Field(..., description="Chuyển động máy: static, push-in, pull-out, pan, orbit, handheld...")
    lighting: str
    action: str = Field(..., description="Hành động và diễn xuất của nhân vật")
    emotion: str
    prompt: str = Field(..., description="Prompt tiếng Anh hoàn chỉnh gửi cho model video")


class ShotList(BaseModel):
    style: str = Field(..., description="Phong cách hình ảnh chung cho mọi shot")
    characters: str = Field("", description="Mô tả cố định ngoại hình nhân vật để giữ đồng nhất")
    shots: List[Shot]


# ---------- Trạng thái dự án ----------
class Status(str, Enum):
    WRITING = "writing"
    REVIEW_SCRIPT = "review_script"      # Cổng 1
    DIRECTING = "directing"
    RENDERING = "rendering"
    ASSEMBLING = "assembling"
    DEMO_READY = "demo_ready"            # chờ Cổng 2 (giai đoạn sau)
    FAILED = "failed"


STATUS_LABEL = {
    Status.WRITING: "Claude đang viết kịch bản",
    Status.REVIEW_SCRIPT: "Chờ duyệt kịch bản (Cổng 1)",
    Status.DIRECTING: "Claude đang phân cảnh",
    Status.RENDERING: "Seedance đang render demo",
    Status.ASSEMBLING: "FFmpeg đang ghép demo",
    Status.DEMO_READY: "Demo đã sẵn sàng",
    Status.FAILED: "Lỗi",
}


class Brief(BaseModel):
    topic: str
    platform: str = "TikTok"
    duration: int = 30
    tone: str = "cuốn hút, cảm xúc"
    audience: str = ""
    language: str = "Tiếng Việt"


class ShotRender(BaseModel):
    scene_id: int
    seed: int
    status: str = "pending"          # pending | running | done | failed
    task_id: Optional[str] = None
    file: Optional[str] = None
    error: Optional[str] = None


class Project(BaseModel):
    id: str
    created_at: str
    brief: Brief
    status: Status
    script: Optional[Script] = None
    shot_list: Optional[ShotList] = None
    renders: List[ShotRender] = []
    demo_file: Optional[str] = None
    error: Optional[str] = None
    log: List[str] = []
    cost_log: List[dict] = []
