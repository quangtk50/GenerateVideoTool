# GenerateVideoTool – MVP (Tuần 1–2)

Luồng: **Claude viết kịch bản → Cổng 1 (duyệt trên web) → Claude phân cảnh → Seedance render 480p → FFmpeg ghép demo 360×640 có phụ đề.**

## Cài đặt (Windows)

1. Cài Python 3.10+ và FFmpeg: `winget install Python.Python.3.12` và `winget install Gyan.FFmpeg` (mở terminal mới sau khi cài).
2. Trong thư mục này:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
3. Mở `.env`, điền `ANTHROPIC_API_KEY` và `ARK_API_KEY` (BytePlus ModelArk). Kiểm tra `SEEDANCE_MODEL` đúng model mà tài khoản của bạn được bật.
4. Chạy `python run.py` rồi mở http://127.0.0.1:8000

Chưa có key? Cứ chạy: hệ thống tự dùng **chế độ thử** (kịch bản mẫu + video test) để bạn xem trọn luồng mà không tốn tiền.

## Cấu trúc

| File | Vai trò |
| --- | --- |
| `app/schemas.py` | Schema JSON: Script, ShotList, Project |
| `app/claude_client.py` | Gọi Claude, ép trả về đúng schema (tool use) |
| `app/script_writer.py` | Agent Biên kịch (Bước 2) |
| `app/director.py` | Agent Đạo diễn: shot list + prompt Seedance (Bước 3) |
| `app/seedance.py` | Gọi API Seedance: tạo task, chờ, tải video; retry khi lỗi 429/5xx |
| `app/assembler.py` | FFmpeg: chuẩn hóa, nối, phụ đề |
| `app/pipeline.py` | Điều phối, chạy nền, render song song |
| `app/web.py` + `templates/` | Giao diện duyệt |
| `data/projects/<id>/` | project.json, shots/, demo.mp4 |

## Ghi chú

- Seedance yêu cầu thời lượng tối thiểu mỗi lần gọi (mặc định 4s). Cảnh ngắn hơn sẽ được render 4s rồi cắt bớt khi ghép.
- Seed được lưu cho từng shot. Chỉ bật `SEEDANCE_SEND_SEED=1` nếu model của bạn hỗ trợ tham số `seed`.
- `cost_log` trong project.json ghi token Claude và usage Seedance của từng bước để tính giá thành/video.
- Giai đoạn sau: Cổng 2 chọn take, render Full HD, nhạc Suno, Cổng 3.
