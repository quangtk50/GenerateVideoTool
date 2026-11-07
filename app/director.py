"""Bước 3 - Agent Đạo diễn: kịch bản -> shot list, góc máy, nguồn hình cho từng cảnh."""
from . import config
from .claude_client import ask_structured
from .schemas import Script, Shot, ShotList

SYSTEM = """Bạn là đạo diễn hình ảnh cho video ngắn dọc 9:16, làm việc với AI video, AI ảnh và kho video stock.
Nhiệm vụ: chuyển từng cảnh của kịch bản thành MỘT shot với ngôn ngữ điện ảnh và chọn nguồn hình.
Luật đạo diễn:
- Shot đầu tiên phải gây chú ý: close-up hoặc chuyển động máy mạnh.
- Xen kẽ cỡ cảnh (wide / medium / close-up), không để 2 shot liền nhau cùng cỡ cảnh và cùng góc máy.
- Mỗi shot chỉ 1 chuyển động máy chính, mô tả rõ (slow push-in, orbit left, handheld follow...).
- Diễn xuất cụ thể bằng hành động nhìn thấy được (nhíu mày, mỉm cười, ngẩng lên) thay vì từ trừu tượng.
- Giữ nhân vật đồng nhất: viết mô tả ngoại hình cố định trong "characters" và lặp lại nó trong mọi prompt có nhân vật.
- "prompt" viết bằng TIẾNG ANH, 40-90 từ, theo thứ tự: chủ thể + hành động, bối cảnh, cỡ cảnh + góc máy,
  chuyển động máy, ánh sáng, phong cách. Không đưa chữ/phụ đề vào khung hình, không logo, không người nổi tiếng.
- Chọn "source" để tiết kiệm chi phí mà vẫn đẹp:
  * ai_video: cảnh có nhân vật chính hành động/diễn xuất (đắt nhất, dùng cho cảnh quan trọng, hook).
  * ai_image: minh hoạ khái niệm, đồ vật, cảnh tĩnh (ảnh AI + hiệu ứng zoom chậm).
  * stock: cảnh chung chung ngoài đời (phố xá, thiên nhiên, văn phòng, đồ ăn) - điền stock_query tiếng Anh.
- Số shot bằng đúng số cảnh, scene_id khớp với id cảnh."""

MODE_HINT = {
    "ai_video": "BẮT BUỘC: mọi shot dùng source = ai_video.",
    "ai_image": "BẮT BUỘC: mọi shot dùng source = ai_image.",
    "stock": "BẮT BUỘC: mọi shot dùng source = stock, kèm stock_query.",
}


def make_shot_list(script: Script, visual_mode: str = "auto") -> tuple:
    if config.use_mock_claude():
        sl = _mock(script)
    else:
        prompt = "Kịch bản đã duyệt:\n" + script.model_dump_json(indent=2)
        if visual_mode in MODE_HINT:
            prompt += "\n\n" + MODE_HINT[visual_mode]
        sl, usage = ask_structured(SYSTEM, prompt, ShotList)
        ids = {s.id for s in script.scenes}
        sl.shots = [s for s in sl.shots if s.scene_id in ids]
        missing = ids - {s.scene_id for s in sl.shots}
        if missing:
            raise RuntimeError(f"Shot list thiếu cảnh: {sorted(missing)}")
    if visual_mode in MODE_HINT:            # ép lại cho chắc
        for s in sl.shots:
            s.source = visual_mode
    for s in sl.shots:
        if s.source == "stock" and not s.stock_query:
            s.stock_query = " ".join(s.action.split()[:4])
    return sl, ({"model": "mock"} if config.use_mock_claude() else usage)


def _mock(script: Script) -> ShotList:
    framings = ["close-up", "wide shot", "medium shot"]
    sources = ["ai_video", "stock", "ai_video", "ai_image"]
    shots = []
    for i, sc in enumerate(script.scenes):
        f = framings[i % 3]
        shots.append(Shot(scene_id=sc.id, framing=f, angle="eye level", camera_move="slow push-in",
                          lighting="soft natural light", action=sc.visual, emotion="neutral",
                          source=sources[i % len(sources)], stock_query="city morning",
                          prompt=f"{sc.visual}. {f}, eye level, slow push-in, soft natural light, cinematic"))
    return ShotList(style="cinematic, warm color grade", characters="young woman, 25, short black hair",
                    shots=shots)
