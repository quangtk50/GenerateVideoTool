# 3. Lấy API key và kết nối tài khoản đăng bài

Tất cả điền vào file `.env`. Sau khi sửa `.env` phải **khởi động lại** ứng dụng (tắt `start.bat` rồi mở lại, hoặc `docker compose up -d` trên VPS).

> Tên model, giá và quy trình duyệt của các nền tảng thay đổi thường xuyên. Kiểm tra trang chính thức trước khi dùng thật.

## 3.1. Claude (bắt buộc cho chạy thật)

1. Vào https://console.anthropic.com → **API Keys** → **Create Key**.
2. Nạp credit trong **Billing**.
3. Điền:

```ini
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5          # model chính: biên kịch, đạo diễn
CLAUDE_MODEL_FAST=                      # tuỳ chọn: model rẻ hơn cho phản biện, QA, SEO
```

Kiểm tra tên model đang có tại https://docs.claude.com/en/docs/about-claude/models.

Mỗi video dùng khoảng 6–9 lượt gọi Claude (ý tưởng, kịch bản, 1–2 vòng phản biện, đạo diễn, QA có ảnh, SEO).

## 3.2. Video AI

### Seedance (BytePlus ModelArk), đang dùng từ bản MVP

```ini
ARK_API_KEY=...
SEEDANCE_MODEL=dreamina-seedance-2-0-260128   # đúng model tài khoản bạn được bật
VIDEO_PROVIDER=seedance
```

### fal.ai (một key dùng được nhiều model)

1. Đăng ký https://fal.ai → **Keys** → tạo key, nạp credit.
2. Điền:

```ini
FAL_KEY=...
FAL_VIDEO_MODEL=fal-ai/kling-video/v2.1/standard/text-to-video
FAL_IMAGE_MODEL=fal-ai/flux/schnell
```

Muốn dùng fal.ai làm nguồn video chính: `VIDEO_PROVIDER=fal`. Đổi model bằng cách copy "model id" từ trang model trên fal.ai. Model có tham số riêng thì đặt vào `FAL_VIDEO_EXTRA` dạng JSON.

### Định tuyến nguồn hình

`VISUAL_MODE=auto` cho phép agent đạo diễn chọn cho từng cảnh:

| Nguồn | Khi nào dùng | Chi phí |
| --- | --- | --- |
| `ai_video` | Cảnh có nhân vật hành động, hook | Cao nhất |
| `ai_image` | Minh hoạ, đồ vật, khái niệm (ảnh AI + zoom chậm) | Thấp |
| `stock` | Phố xá, thiên nhiên, văn phòng (Pexels) | Miễn phí |

Nếu nguồn được chọn lỗi hoặc chưa có key, hệ thống tự chuyển nguồn kế tiếp và ghi vào nhật ký.

## 3.3. Pexels (video stock miễn phí)

1. https://www.pexels.com/api/ → đăng ký → nhận key.
2. `PEXELS_API_KEY=...`

## 3.4. Lời thoại (TTS)

| Nhà cung cấp | Cấu hình | Ghi chú |
| --- | --- | --- |
| Edge TTS (mặc định) | `TTS_PROVIDER=edge`, `EDGE_VOICE=vi-VN-HoaiMyNeural` (nữ) hoặc `vi-VN-NamMinhNeural` (nam) | Miễn phí, không cần key, có mốc thời gian từng từ cho phụ đề. Là dịch vụ không chính thức, có thể bị giới hạn khi gọi nhiều |
| ElevenLabs | `TTS_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Giọng tự nhiên nhất, clone giọng riêng. Lấy Voice ID trong Voice Library |
| FPT.AI | `TTS_PROVIDER=fpt`, `FPT_API_KEY`, `FPT_VOICE=banmai` | Giọng Việt bản địa. Đăng ký tại console.fpt.ai |
| Không lồng tiếng | `TTS_PROVIDER=none` | Chỉ phụ đề + nhạc |

Độ dài cảnh tự giãn theo lời thoại: nếu giọng đọc dài hơn thời lượng kịch bản, cảnh được kéo dài cho vừa.
## 3.5. YouTube

1. Vào https://console.cloud.google.com → tạo Project.
2. **APIs & Services → Library** → bật **YouTube Data API v3**.
3. **OAuth consent screen**: chọn External, điền tên ứng dụng, thêm email của bạn vào **Test users**.
4. **Credentials → Create credentials → OAuth client ID → Desktop app** → tải file JSON.
5. Đổi tên file thành `youtube_client_secret.json`, đặt vào `data\secrets\`.
6. Chạy trên máy có trình duyệt:

```bat
python -m app.cli youtube-auth
```

Đăng nhập đúng tài khoản sở hữu kênh, cho phép quyền. Token lưu ở `data\secrets\youtube_token.json`.

Lưu ý:

- Ứng dụng ở chế độ "Testing" có thể khiến token hết hạn sau 7 ngày. Khi dùng lâu dài, chuyển consent screen sang "In production".
- Quota mặc định 10.000 đơn vị/ngày và upload là thao tác tốn quota nhiều nhất (xem bảng chi phí quota hiện hành trong tài liệu YouTube Data API). Đăng nhiều video/ngày thì xin tăng quota.
- Video từ project API chưa được Google kiểm duyệt có thể bị khoá ở chế độ riêng tư. Bắt đầu với `YOUTUBE_PRIVACY=private`, kiểm tra rồi chuyển `public` khi ổn.
- Hệ thống tự gắn nhãn nội dung tổng hợp (`containsSyntheticMedia`). Thumbnail tuỳ chỉnh yêu cầu kênh đã xác minh số điện thoại.

## 3.6. TikTok

1. https://developers.tiktok.com → tạo App → thêm sản phẩm **Login Kit** và **Content Posting API** (bật Direct Post).
2. Xin scope `video.publish` (và `user.info.basic`).
3. Lấy **access token** và **refresh token** của tài khoản đăng qua luồng OAuth của Login Kit (cần redirect URI HTTPS; có thể dùng tên miền VPS).
4. Điền:

```ini
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_REFRESH_TOKEN=...      # hệ thống tự đổi lấy access token mới, lưu ở data/secrets/tiktok_token.json
TIKTOK_PRIVACY=SELF_ONLY
```

App **chưa qua audit** của TikTok chỉ đăng được ở chế độ riêng tư (`SELF_ONLY`). Gửi audit trong trang developer để đăng công khai (`PUBLIC_TO_EVERYONE`). Hệ thống tự gắn cờ nội dung AI (`is_aigc`).

## 3.7. Facebook Reels và Instagram Reels

Yêu cầu: một Facebook Page; tài khoản Instagram **Business/Creator** liên kết với Page đó.

1. https://developers.facebook.com → tạo App (loại Business).
2. Thêm quyền: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`.
3. Dùng **Graph API Explorer** lấy User token với các quyền trên → đổi sang **long-lived token** → gọi `/me/accounts` để lấy **Page access token** (không hết hạn nếu tạo từ long-lived user token) và Page ID.
4. Lấy Instagram user ID: gọi `/{page-id}?fields=instagram_business_account`.
5. Điền:

```ini
META_GRAPH_VERSION=v23.0
FB_PAGE_ID=...
FB_PAGE_TOKEN=...
IG_USER_ID=...
IG_ACCESS_TOKEN=          # để trống = dùng FB_PAGE_TOKEN
```

App ở chế độ Development chỉ đăng được bằng tài khoản có vai trò trong App. Muốn dùng cho tài khoản khác thì cần App Review.

## 3.8. Bật đăng thật

Sau khi thử với dry run và kiểm tra token:

```ini
PUBLISH_DRY_RUN=0
DEFAULT_PLATFORMS=youtube,tiktok,facebook,instagram
```

Lỗi ở một nền tảng không ảnh hưởng nền tảng khác. Bấm **Đăng lại nền tảng chưa xong** để thử lại những nền tảng lỗi.

## 3.9. Bản quyền và chính sách

- Chỉ dùng nhạc có giấy phép thương mại (YouTube Audio Library, Pixabay Music, nhạc AI gói trả phí...).
- Video Pexels miễn phí sử dụng; nên ghi nguồn khi có thể.
- Giọng clone: chỉ clone giọng của chính bạn hoặc người đã đồng ý bằng văn bản.
- Nội dung hàng loạt chất lượng thấp có thể bị giảm phân phối hoặc tắt kiếm tiền. Giữ Cổng 1/Cổng 2 trong giai đoạn đầu.
