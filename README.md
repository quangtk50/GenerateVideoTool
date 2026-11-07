# GenerateVideoTool

Hệ thống tự động tạo video ngắn theo workflow, từ ý tưởng đến đăng bài:

**Ý tưởng → Kịch bản → Phản biện → Cổng 1 (duyệt kịch bản) → Đạo diễn phân cảnh → Lời thoại (TTS) → Hình/Video (AI video · ảnh AI · stock) → Nhạc nền → Dựng FFmpeg (phụ đề, logo, ducking, -14 LUFS) → QA (kỹ thuật + Claude vision) → SEO + thumbnail → Cổng 2 (duyệt video) → Đăng YouTube / TikTok / Facebook / Instagram → Thống kê & insights**

Không có API key vẫn chạy được: module nào thiếu key sẽ tự giả lập để bạn xem trọn luồng mà không tốn tiền.

## Bắt đầu nhanh

| Bạn muốn | Đọc |
| --- | --- |
| Cài và chạy trên máy Windows | [docs/1_CAI_DAT_VA_CHAY_WINDOWS.md](docs/1_CAI_DAT_VA_CHAY_WINDOWS.md) |
| Deploy lên VPS (Docker, HTTPS) | [docs/2_DEPLOY_VPS.md](docs/2_DEPLOY_VPS.md) |
| Lấy API key, kết nối tài khoản đăng bài | [docs/3_CAU_HINH_API_VA_TAI_KHOAN.md](docs/3_CAU_HINH_API_VA_TAI_KHOAN.md) |
| Hiểu kiến trúc, mở rộng hệ thống | [docs/4_KIEN_TRUC.md](docs/4_KIEN_TRUC.md) |
| Gặp lỗi | [docs/5_XU_LY_LOI.md](docs/5_XU_LY_LOI.md) |

Tóm tắt trên Windows:

```bat
setup_windows.bat      :: cài thư viện, tạo .env, kiểm tra FFmpeg
notepad .env           :: điền ANTHROPIC_API_KEY, ARK_API_KEY...
start.bat              :: mở http://127.0.0.1:8000
```

Tóm tắt trên VPS:

```bash
cp .env.example .env && nano .env      # điền key, đặt WEB_USER/WEB_PASSWORD
docker compose up -d --build
```

## Module và AI sử dụng

| Bước | File | AI / công cụ |
| --- | --- | --- |
| 1. Ý tưởng | `app/idea_generator.py` | Claude (đọc thêm `data/insights.md`) |
| 2. Kịch bản | `app/script_writer.py` | Claude |
| 2b. Phản biện | `app/critic.py` | Claude, chấm điểm và yêu cầu viết lại nếu dưới ngưỡng |
| Cổng 1 | giao diện web | Người duyệt (hoặc tự duyệt) |
| 3. Đạo diễn | `app/director.py` | Claude: cỡ cảnh, góc máy, prompt, chọn nguồn hình từng cảnh |
| 5. Lời thoại | `app/tts.py` | Edge TTS (miễn phí) · ElevenLabs · FPT.AI |
| 6. Hình/Video | `app/visuals.py` | Seedance · fal.ai (Kling/Wan/Veo, Flux) · Pexels, tự chuyển nguồn khi lỗi |
| 7. Nhạc | `app/music.py` | Thư viện nhạc của bạn trong `assets/music` |
| 8. Dựng | `app/assembler.py`, `app/subtitles.py` | FFmpeg: Ken Burns, phụ đề karaoke, logo, ducking, loudnorm |
| 9. QA | `app/qa.py` | FFprobe + Claude vision |
| 10. SEO | `app/seo.py`, `app/thumbnail.py` | Claude + Pillow |
| Cổng 2 | giao diện web | Người duyệt (hoặc tự đăng khi QA đạt) |
| 11. Đăng | `app/publishers/` | YouTube Data API · TikTok Content Posting API · Meta Graph API |
| 12. Thống kê | `app/analytics.py` | YouTube API + Claude rút bài học |
| Điều phối | `app/pipeline.py`, `app/scheduler.py` | Python, chạy nền, tiếp tục được khi lỗi, lịch tự động |

## Lệnh dòng lệnh

```bash
python -m app.cli check                                # kiểm tra cấu hình
python -m app.cli run --topic "Chủ đề..." --duration 30   # tạo 1 video, tự duyệt
python -m app.cli run --auto --publish youtube,tiktok     # AI tự nghĩ ý tưởng, tạo và đăng
python -m app.cli resume <project_id>                     # chạy tiếp dự án dở
python -m app.cli youtube-auth                            # đăng nhập YouTube lần đầu
python -m app.cli analytics                               # cập nhật số liệu + insights
pytest -q                                                 # kiểm thử toàn luồng ở chế độ giả lập
```
