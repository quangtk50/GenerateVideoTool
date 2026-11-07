# 1. Cài đặt và chạy trên Windows

## 1.1. Yêu cầu

| Thành phần | Phiên bản | Cài bằng |
| --- | --- | --- |
| Python | 3.10 – 3.12 | `winget install Python.Python.3.12` |
| FFmpeg | 6 trở lên (bản có libass) | `winget install Gyan.FFmpeg` |
| Internet | | Gọi API Claude, Seedance, Edge TTS... |

Sau khi cài, **mở cửa sổ CMD mới** rồi kiểm tra:

```bat
python --version
ffmpeg -version
```

## 1.2. Cài đặt lần đầu

Cách nhanh: nhấp đúp `setup_windows.bat`. File này sẽ:

1. Tạo môi trường ảo `.venv`.
2. Cài thư viện trong `requirements.txt`.
3. Tạo file `.env` từ `.env.example` (nếu chưa có).
4. Chạy `python -m app.cli check` để kiểm tra.

Hoặc làm tay:

```bat
cd /d E:\KHUE\GenerateVideoTool
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.cli check
```

> Nếu bạn đã có file `.env` từ bản MVP: giữ nguyên, rồi copy thêm các dòng mới từ `.env.example` (phần TTS, fal.ai, Pexels, đăng bài, lịch tự động). Thiếu dòng nào thì hệ thống dùng giá trị mặc định.

## 1.3. Điền cấu hình tối thiểu

Mở `.env` bằng Notepad. Tối thiểu để có video thật:

```ini
ANTHROPIC_API_KEY=sk-ant-...      # mọi agent viết/phân tích
ARK_API_KEY=...                   # Seedance tạo video AI
TTS_PROVIDER=edge                 # giọng Việt miễn phí
DEFAULT_RESOLUTION=720p
```

Nên thêm để tiết kiệm chi phí video AI:

```ini
PEXELS_API_KEY=...                # video stock miễn phí cho cảnh chung chung
FAL_KEY=...                       # ảnh AI (Flux) cho cảnh minh hoạ; cũng có Kling/Wan
```

Chưa có `FAL_KEY` và `PEXELS_API_KEY` thì cảnh "ảnh AI" và "stock" sẽ tự chuyển sang Seedance, nên tốn hơn. Muốn chắc chắn chỉ dùng Seedance, đặt `VISUAL_MODE=ai_video`.

Cách lấy từng key: xem [3_CAU_HINH_API_VA_TAI_KHOAN.md](3_CAU_HINH_API_VA_TAI_KHOAN.md).

## 1.4. Thêm nhạc nền và logo (tuỳ chọn)

- Copy file nhạc có bản quyền hợp lệ vào `assets\music\`. Tên file nên có từ khoá mood, ví dụ `lofi_chill_nhe-nhang.mp3`.
- Đặt logo PNG nền trong suốt tại `assets\logo.png`.

## 1.5. Chạy

Nhấp đúp `start.bat`, hoặc:

```bat
.venv\Scripts\activate
python run.py
```

Mở http://127.0.0.1:8000. Góc trên bên phải hiển thị module nào đang chạy **thật** (màu xanh) hay **giả lập**.

## 1.6. Quy trình sử dụng

1. **Tạo video**: nhập chủ đề, hoặc để trống và bấm "Tự tạo ý tưởng". Chọn thời lượng, độ phân giải, nguồn hình, nền tảng sẽ đăng.
2. **Chờ kịch bản**: Claude viết, agent phản biện chấm điểm và yêu cầu viết lại nếu dưới `CRITIC_MIN_SCORE`.
3. **Cổng 1**: sửa lời thoại, thời lượng, xoá cảnh, hoặc gửi góp ý để viết lại. Bấm **Duyệt và sản xuất video**.
4. **Sản xuất tự động**: phân cảnh → lời thoại → hình/video → dựng → QA → tiêu đề, thumbnail. Trang tự làm mới.
5. **Cổng 2**: xem video, báo cáo QA, sửa tiêu đề/caption. Cảnh nào chưa ổn thì sửa prompt hoặc đổi nguồn rồi bấm **Render lại shot này**; hệ thống chỉ làm lại cảnh đó rồi dựng lại.
6. **Đăng**: chọn nền tảng, bấm **Duyệt và đăng**. Mặc định `PUBLISH_DRY_RUN=1` chỉ giả lập. Khi đã cấu hình tài khoản, đổi thành `0`.

Nếu một bước lỗi (mất mạng, hết quota...), trang dự án có nút **Tiếp tục từ bước đang dở**. Phần đã xong được giữ lại, không tốn tiền làm lại.

## 1.7. Chạy hoàn toàn tự động

Thêm vào `.env`:

```ini
SCHEDULER_ENABLED=1
AUTO_TIMES=08:30,19:45        # mỗi ngày tạo 2 video
AUTO_APPROVE_SCRIPT=1         # bỏ Cổng 1
AUTO_PUBLISH=1                # tự đăng khi QA đạt (QA có lỗi nặng thì dừng ở Cổng 2)
DEFAULT_PLATFORMS=youtube,tiktok
PUBLISH_DRY_RUN=0
```

Máy phải bật và `start.bat` phải đang chạy vào các giờ đó. Muốn chạy 24/7, nên đưa lên VPS ([2_DEPLOY_VPS.md](2_DEPLOY_VPS.md)).

Khuyến nghị: chạy vài tuần **có** Cổng 1 và Cổng 2 để kiểm soát chất lượng, sau đó mới bật tự động hoàn toàn.

## 1.8. Chạy bằng dòng lệnh

```bat
python -m app.cli run --topic "3 mẹo ngủ ngon" --duration 30 --resolution 720p
python -m app.cli run --auto --publish youtube
```

## 1.9. Dữ liệu nằm ở đâu

```
data\projects\<id>\project.json   trạng thái, kịch bản, shot list, log, chi phí
data\projects\<id>\voice\         lời thoại từng cảnh
data\projects\<id>\shots\         video/ảnh từng cảnh
data\projects\<id>\final.mp4      video hoàn chỉnh
data\projects\<id>\thumbnail.jpg
data\secrets\                     token YouTube/TikTok (không chia sẻ)
data\insights.md                  bài học từ số liệu kênh
```

Sao lưu thư mục `data\` là đủ để giữ toàn bộ dự án.
