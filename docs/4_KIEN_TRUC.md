# 4. Kiến trúc hệ thống

## 4.1. Luồng xử lý

```
 [Web / CLI / Lịch tự động]
            │ Brief (chủ đề, thời lượng, nền tảng, nguồn hình...)
            ▼
 ① Ý tưởng (Claude + insights.md)          IDEATING
 ② Biên kịch (Claude) ⇄ Phản biện (Claude)  WRITING / CRITIQUING   tối đa CRITIC_MAX_ROUNDS vòng
            │
 ■ CỔNG 1: người duyệt kịch bản             REVIEW_SCRIPT          (bỏ qua nếu auto_approve_script)
            │
 ③ Đạo diễn (Claude): góc máy, prompt, nguồn hình từng cảnh      DIRECTING
 ④ Lời thoại (Edge/ElevenLabs/FPT) → thời lượng thật từng cảnh   VOICING
 ⑤ Hình/Video song song: Seedance | fal.ai | Pexels | ảnh AI      RENDERING
 ⑥ Nhạc nền (assets/music)
 ⑦ Dựng FFmpeg: chuẩn hoá cảnh, Ken Burns, nối, track lời thoại,
    phụ đề karaoke, logo, ducking nhạc, loudnorm -14 LUFS         ASSEMBLING
 ⑧ QA: FFprobe/blackdetect + Claude vision                        QA
 ⑨ SEO (Claude) + thumbnail (Pillow)                              PACKAGING
            │
 ■ CỔNG 2: người duyệt video, sửa caption   REVIEW_FINAL           (bỏ qua nếu auto_publish và QA đạt)
            │
 ⑩ Đăng: YouTube | TikTok | Facebook | Instagram                  PUBLISHING → PUBLISHED
 ⑪ Thống kê (YouTube API) → Claude rút bài học → data/insights.md → quay lại ①
```

## 4.2. Nguyên tắc thiết kế

1. **Dữ liệu có cấu trúc giữa các bước.** Mọi agent trả về JSON đúng schema Pydantic (`app/schemas.py`), ép bằng tool use bắt buộc của Claude (`app/claude_client.py`). Không truyền văn bản tự do giữa các module.
2. **Mỗi bước idempotent.** Trạng thái lưu trong `project.json` sau mỗi bước. Chạy lại chỉ làm phần còn thiếu, nên nút "Tiếp tục" không tốn tiền làm lại.
3. **Tự chuyển nguồn khi lỗi.** `visuals.py` thử nguồn đạo diễn chọn, lỗi thì thử nguồn khác. Lỗi đăng một nền tảng không chặn nền tảng khác.
4. **Thời lượng theo lời thoại.** Thời lượng cảnh = max(kịch bản, giọng đọc + 0,35s). Shot được render theo con số này.
5. **Người kiểm soát ở 2 điểm rẻ nhất.** Cổng 1 trước khi tốn tiền tạo video; Cổng 2 trước khi đăng công khai.
6. **Chạy được không cần key.** Mọi module có chế độ giả lập để phát triển và kiểm thử (`pytest`).

## 4.3. Cấu trúc mã nguồn

```
app/
  config.py            đọc .env, tính kích thước khung hình, cờ giả lập
  schemas.py           mọi schema dữ liệu + trạng thái
  claude_client.py     gọi Claude, ép schema, hỗ trợ gửi ảnh
  idea_generator.py    agent ý tưởng
  script_writer.py     agent biên kịch
  critic.py            agent phản biện
  director.py          agent đạo diễn
  seo.py               agent SEO
  tts.py               lời thoại
  visuals.py           định tuyến nguồn hình, hình giả lập, tìm font
  seedance.py          client Seedance
  fal_ai.py            client fal.ai (video + ảnh)
  pexels.py            client Pexels
  music.py             chọn nhạc nền
  subtitles.py         phụ đề ASS tô màu từng từ
  assembler.py         dựng video FFmpeg
  qa.py                kiểm tra chất lượng
  thumbnail.py         thumbnail
  publishers/          youtube.py, tiktok.py, meta.py
  analytics.py         số liệu + insights
  pipeline.py          điều phối
  scheduler.py         lịch tự động
  storage.py           lưu project.json
  web.py, templates/   giao diện
  cli.py               dòng lệnh
tests/                 kiểm thử toàn luồng (chế độ giả lập)
deploy/                Caddyfile, systemd service
```

## 4.4. Mở rộng thường gặp

**Thêm nhà cung cấp video mới** (ví dụ Runway, Veo trực tiếp): viết hàm `render_video(prompt, seconds, dest) -> dict` giống `fal_ai.py`, rồi thêm một nhánh trong `visuals.render()` và tên nhà cung cấp trong `_video_providers()`.

**Thêm LLM khác** (GPT, Gemini): viết hàm `ask_structured(system, prompt, schema, ...)` tương đương trong file mới, chọn bằng biến môi trường trong `claude_client.py`. Các agent không cần sửa.

**Avatar/lip-sync** (HeyGen, Hedra, sync.so): thêm `source = "avatar"` trong `schemas.VisualSource`, viết client nhận file lời thoại của cảnh (`p.voices`) và ảnh nhân vật, trả về mp4 đã khớp khẩu hình. Ở `assembler.voice_track` bỏ qua lời thoại riêng của cảnh đó nếu video đã có tiếng.

**Thêm nền tảng đăng** (Zalo Video, Threads...): thêm file trong `publishers/`, một nhánh trong `publishers/__init__.py` và khoá trong `schemas.PLATFORMS`.

**Template dựng đẹp hơn** (chữ động, lower-third): dùng Remotion (React/TypeScript) như một service riêng; `assembler.py` gọi Remotion render lớp đồ hoạ trong suốt rồi `overlay` bằng FFmpeg.

## 4.5. Mở rộng quy mô (khi vượt vài chục video/ngày)

| Hiện tại | Khi cần mở rộng |
| --- | --- |
| `project.json` trên đĩa | PostgreSQL (SQLAlchemy). Thay các hàm trong `storage.py`; giữ nguyên interface `load / save / update / list_all` |
| Thread nền trong tiến trình web | Hàng đợi Celery + Redis hoặc Temporal: `pipeline.produce`, `write_flow`, `publish_flow` đã là hàm thuần nhận `pid`, bọc thành task là xong |
| Lịch trong tiến trình | Celery beat / cron gọi `python -m app.cli run --auto` |
| File media trên đĩa | S3 / MinIO, phát qua CDN |
| 1 máy chủ | Web và worker tách container; worker scale theo số video |
