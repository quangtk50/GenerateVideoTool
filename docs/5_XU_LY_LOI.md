# 5. Xử lý lỗi thường gặp

Bước đầu tiên luôn là chạy `python -m app.cli check` và xem **Nhật ký** ở cuối trang dự án.

| Triệu chứng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `ffmpeg` không tìm thấy | Chưa cài hoặc chưa mở cửa sổ mới | `winget install Gyan.FFmpeg`, mở CMD mới. Hoặc đặt `FFMPEG_BIN`/`FFPROBE_BIN` là đường dẫn đầy đủ |
| Video không có phụ đề, nhật ký báo "thiếu libass" | Bản FFmpeg thiếu libass | Dùng bản "full" của Gyan; trên Linux dùng gói `ffmpeg` của Ubuntu |
| Phụ đề hiện ô vuông | Font thiếu tiếng Việt | Windows: `SUB_FONT=Arial`; Docker/Linux: `SUB_FONT=DejaVu Sans` |
| Góc trên báo Claude "giả lập" | Chưa có `ANTHROPIC_API_KEY` hoặc `MOCK_CLAUDE=1` | Điền key, đặt `MOCK_CLAUDE=auto`, khởi động lại |
| `Claude không trả về đúng schema` | Model trả JSON thiếu trường (hiếm) | Bấm Tiếp tục; nếu lặp lại, đổi `CLAUDE_MODEL` sang model mạnh hơn |
| Seedance `HTTP 400` | Sai tên model, độ phân giải hoặc thời lượng không hỗ trợ | Kiểm tra `SEEDANCE_MODEL`, `SEEDANCE_MIN/MAX_DURATION`, `RESOLUTION_OPTIONS` với tài khoản ModelArk |
| `HTTP 429` (nhiều nhà cung cấp) | Gọi quá nhanh / hết quota | Giảm `MAX_PARALLEL_RENDERS`; hệ thống đã tự thử lại có backoff |
| `Edge TTS lỗi: Cannot connect` | Mạng chặn `speech.platform.bing.com` hoặc bị giới hạn | Thử lại sau, hoặc đổi `TTS_PROVIDER=fpt` / `elevenlabs` |
| Cảnh "stock" lại dùng Seedance | Chưa có `PEXELS_API_KEY` nên tự chuyển nguồn | Thêm key Pexels, hoặc đặt `VISUAL_MODE=ai_video` cho rõ ràng |
| Không có nhạc nền | `assets/music` trống | Thêm file nhạc; nhật ký sẽ ghi tên nhạc đã chọn |
| QA báo "Khung hình đen" | Model video trả clip lỗi | Bấm "Render lại shot này" cho cảnh đó |
| YouTube `Chưa đăng nhập` | Chưa có token | `python -m app.cli youtube-auth`; trên VPS copy `youtube_token.json` |
| YouTube `invalid_grant` | Token bị thu hồi / hết hạn (app ở chế độ Testing) | Xoá `data/secrets/youtube_token.json`, chạy lại youtube-auth; chuyển consent screen sang Production |
| YouTube `quotaExceeded` | Hết 10.000 đơn vị/ngày | Chờ sang ngày (giờ Thái Bình Dương) hoặc xin tăng quota |
| TikTok `unaudited_client_can_only_post_to_private_accounts` | App chưa audit | Để `TIKTOK_PRIVACY=SELF_ONLY` hoặc gửi audit |
| TikTok `access_token_invalid` | Token hết hạn | Điền `TIKTOK_REFRESH_TOKEN` + client key/secret để tự làm mới |
| Meta `(#200) permissions` | Token thiếu quyền | Tạo lại token với đủ quyền ở tài liệu 3, mục 3.7 |
| Dự án kẹt ở trạng thái đang chạy sau khi tắt máy | Tiến trình bị dừng giữa chừng | Khởi động lại; dự án chuyển sang Lỗi, bấm **Tiếp tục** |
| Trên VPS trình duyệt hỏi mật khẩu | `WEB_USER`/`WEB_PASSWORD` đã bật | Đăng nhập bằng thông tin trong `.env` |

## Gỡ lỗi sâu hơn

- Toàn bộ trạng thái nằm trong `data/projects/<id>/project.json`: có thể mở để xem kịch bản, shot list, lỗi, `cost_log`.
- Thư mục `data/projects/<id>/tmp/` (nếu còn) chứa file trung gian của lần dựng lỗi: `scene_XX.mp4`, `voice.wav`, `subs.ass`.
- Chạy bằng dòng lệnh để thấy traceback đầy đủ: `python -m app.cli resume <id>`.
- Kiểm thử nhanh toàn luồng không tốn tiền: `pytest -q`.
