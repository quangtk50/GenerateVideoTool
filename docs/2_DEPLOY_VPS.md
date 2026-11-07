# 2. Deploy lên VPS (chạy 24/7)

## 2.1. Chọn máy chủ

Hệ thống không cần GPU: việc tạo video AI chạy trên server của Seedance/fal.ai, máy chủ chỉ chạy FFmpeg để dựng.

| Quy mô | Cấu hình gợi ý |
| --- | --- |
| 2–5 video/ngày, 720p | 2 vCPU, 4 GB RAM, 40 GB SSD |
| 10–30 video/ngày, 1080p | 4 vCPU, 8 GB RAM, 80 GB SSD |

Hệ điều hành: Ubuntu 22.04 / 24.04. Mỗi video 1080p 30–60 giây chiếm khoảng 50–150 MB (gồm các shot), nên dọn hoặc sao lưu `data/` định kỳ.

## 2.2. Cài Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER     # đăng xuất rồi đăng nhập lại
docker compose version
```

## 2.3. Đưa mã nguồn lên máy chủ

Dùng git (khuyến nghị):

```bash
sudo mkdir -p /opt/GenerateVideoTool && sudo chown $USER /opt/GenerateVideoTool
git clone <repo-cua-ban> /opt/GenerateVideoTool
```

Hoặc copy từ Windows bằng `scp` (PowerShell):

```powershell
scp -r E:\KHUE\GenerateVideoTool\app E:\KHUE\GenerateVideoTool\deploy E:\KHUE\GenerateVideoTool\assets `
    E:\KHUE\GenerateVideoTool\Dockerfile E:\KHUE\GenerateVideoTool\docker-compose.yml `
    E:\KHUE\GenerateVideoTool\requirements.txt E:\KHUE\GenerateVideoTool\run.py `
    E:\KHUE\GenerateVideoTool\.env.example user@IP_VPS:/opt/GenerateVideoTool/
```

## 2.4. Cấu hình

```bash
cd /opt/GenerateVideoTool
cp .env.example .env
nano .env
```

Bắt buộc khi đưa lên Internet:

```ini
WEB_USER=admin
WEB_PASSWORD=mat-khau-dai-va-kho-doan
```

Các biến `HOST`, `DATA_ROOT`, `ASSETS_DIR`, `SUB_FONT` đã được `docker-compose.yml` đặt sẵn cho môi trường Docker, không cần sửa. Múi giờ cho lịch tự động: thêm `TZ=Asia/Ho_Chi_Minh` vào `.env`.

## 2.5. Chạy

### Cách A: chỉ truy cập nội bộ qua SSH tunnel (an toàn nhất, không cần tên miền)

```bash
docker compose up -d --build
docker compose logs -f app        # xem log, Ctrl+C để thoát
```

Cổng 8000 chỉ mở trong máy chủ. Từ máy Windows:

```powershell
ssh -L 8000:127.0.0.1:8000 user@IP_VPS
```

Rồi mở http://127.0.0.1:8000 trên máy bạn.

### Cách B: có tên miền và HTTPS tự động (Caddy)

1. Trỏ bản ghi DNS `A` của tên miền (ví dụ `video.congty.vn`) về IP VPS.
2. Thêm vào `.env`: `DOMAIN=video.congty.vn`
3. Mở cổng 80 và 443: `sudo ufw allow 80,443/tcp`
4. Chạy:

```bash
docker compose --profile https up -d --build
```

Caddy tự xin chứng chỉ Let's Encrypt. Truy cập https://video.congty.vn và đăng nhập bằng `WEB_USER`/`WEB_PASSWORD`.

## 2.6. Đăng nhập YouTube trên VPS

Bước đăng nhập YouTube cần trình duyệt, nên làm trên máy Windows rồi copy token lên:

1. Trên Windows: `python -m app.cli youtube-auth` (xem mục YouTube trong tài liệu 3).
2. Copy file token lên VPS:

```powershell
scp E:\KHUE\GenerateVideoTool\data\secrets\youtube_token.json user@IP_VPS:/opt/GenerateVideoTool/data/secrets/
```

Token tự làm mới, không cần làm lại trừ khi bạn thu hồi quyền.

## 2.7. Nhạc nền, logo

```bash
scp *.mp3 user@IP_VPS:/opt/GenerateVideoTool/assets/music/
scp logo.png user@IP_VPS:/opt/GenerateVideoTool/assets/logo.png
```

Không cần khởi động lại; video tiếp theo sẽ dùng.

## 2.8. Kiểm tra

```bash
docker compose exec app python -m app.cli check
docker compose exec app python -m app.cli run --topic "Thử nghiệm" --duration 15
```

## 2.9. Cập nhật phiên bản mới

```bash
cd /opt/GenerateVideoTool
git pull                         # hoặc copy file mới lên
docker compose up -d --build
```

Dự án đang chạy dở khi khởi động lại sẽ chuyển sang trạng thái Lỗi kèm nút **Tiếp tục**.

## 2.10. Sao lưu

```bash
# Sao lưu hằng ngày lúc 3h sáng, giữ 14 bản
crontab -e
0 3 * * * mkdir -p /backup && tar czf /backup/gvt-$(date +\%F).tgz --exclude='data/projects/*/shots' --exclude='data/projects/*/voice' -C /opt/GenerateVideoTool data .env && find /backup -name 'gvt-*.tgz' -mtime +14 -delete
```

Lệnh trên giữ token, insights, project.json, video hoàn chỉnh và thumbnail, bỏ qua các shot trung gian để nhẹ hơn. Nên copy thêm thư mục `/backup` sang nơi khác (Google Drive, S3...).

## 2.11. Chạy không dùng Docker (systemd)

```bash
sudo apt install -y python3-venv ffmpeg fonts-dejavu-core
sudo useradd -r -m gvt && sudo chown -R gvt /opt/GenerateVideoTool
cd /opt/GenerateVideoTool
sudo -u gvt python3 -m venv .venv
sudo -u gvt .venv/bin/pip install -r requirements.txt
# trong .env: HOST=127.0.0.1, SUB_FONT=DejaVu Sans
sudo cp deploy/gvt.service /etc/systemd/system/
sudo systemctl enable --now gvt
journalctl -u gvt -f
```

## 2.12. Giới hạn của kiến trúc hiện tại

- Toàn bộ chạy trong **một tiến trình**: web + hàng đợi + lịch. Phù hợp đến khoảng vài chục video/ngày.
- `MAX_CONCURRENT_PROJECTS` giới hạn số video sản xuất cùng lúc; `MAX_PARALLEL_RENDERS` giới hạn số shot gọi API song song cho mỗi video (tránh lỗi 429).
- Chỉ chạy **1 bản** (`replicas: 1`). Muốn nhiều máy chủ: xem phần "Mở rộng" trong [4_KIEN_TRUC.md](4_KIEN_TRUC.md).
