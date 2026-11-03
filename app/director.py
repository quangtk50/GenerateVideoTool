"""Bước 3 - Agent Đạo diễn: kịch bản -> shot list + prompt Seedance."""
from . import config
from .claude_client import ask_structured
from .schemas import Script, Shot, ShotList

SYSTEM = """Bạn là đạo diễn hình ảnh cho video ngắn dọc 9:16, làm việc với model AI video (Seedance).
Nhiệm vụ: chuyển từng cảnh của kịch bản thành MỘT shot với ngôn ngữ điện ảnh.
Luật đạo diễn:
- Shot đầu tiên phải gây chú ý: close-up hoặc chuyển động máy mạnh.
- Xen kẽ cỡ cảnh (wide / medium / close-up), không để 2 shot liền nhau cùng cỡ cảnh và cùng góc máy.
- Mỗi shot chỉ 1 chuyển động máy chính, mô tả rõ (slow push-in, orbit left, handheld follow...).
- Diễn xuất cụ thể bằng hành động nhìn thấy được (nhíu mày, mỉm cười, ngẩng lên) thay vì từ trừu tượng.
- Giữ nhân vật đồng nhất: viết mô tả ngoại hình cố định trong "characters" và lặp lại nó trong mọi prompt.
- "prompt" viết bằng TIẾNG ANH, 40-90 từ, theo thứ tự: chủ thể + hành động, bối cảnh, cỡ cảnh + góc máy,
  chuyển động máy, ánh sáng, phong cách. Không đưa chữ/phụ đề vào khung hình, không logo, không người nổi tiếng.
- Số shot bằng đúng số cảnh, scene_id khớp với id cảnh."""


def make_shot_list(script: Script) -> tuple[ShotList, dict]:
    if config.use_mock_claude():
        return _mock(script), {"model": "mock"}
    prompt = "Kịch bản đã duyệt:\n" + script.model_dump_json(indent=2)
    shot_list, usage = ask_structured(SYSTEM, prompt, ShotList)
    ids = {s.id for s in script.scenes}
    shot_list.shots = [s for s in shot_list.shots if s.scene_id in ids]
    missing = ids - {s.scene_id for s in shot_list.shots}
    if missing:
        raise RuntimeError(f"Shot list thiếu cảnh: {sorted(missing)}")
    return shot_list, usage


def _mock(script: Script) -> ShotList:
    framings = ["close-up", "medium shot", "wide shot"]
    shots = []
    for i, sc in enumerate(script.scenes):
        f = framings[i % 3]
        shots.append(Shot(scene_id=sc.id, framing=f, angle="eye level", camera_move="slow push-in",
                          lighting="soft natural light", action=sc.visual, emotion="neutral",
                          prompt=f"{sc.visual}. {f}, eye level, slow push-in, soft natural light, cinematic"))
    return ShotList(style="cinematic, warm color grade", characters="young woman, 25, short black hair",
                    shots=shots)
