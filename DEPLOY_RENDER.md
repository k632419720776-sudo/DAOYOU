# DAOYOU — Deploy công khai miễn phí bằng Render

## 1. Đưa project lên GitHub

Tạo repository mới tên `daoyou`, sau đó upload toàn bộ nội dung thư mục này.

## 2. Tạo Render Web Service

- Đăng nhập Render.
- New -> Web Service.
- Connect GitHub.
- Chọn repository `daoyou`.
- Runtime: Python.
- Plan: Free.
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Health Check Path: `/health`

`render.yaml` trong project đã chứa cấu hình tương ứng.

## 3. Environment Variables

Tạo:
- `DAOYOU_SECRET_KEY` = một chuỗi bí mật dài.
- `SEED_DEMO` = `true` cho bản demo lớp học.

## 4. URL

Sau khi deploy, Render cấp một URL công khai dạng:

`https://daoyou-xxxx.onrender.com`

Thầy giáo và bạn bè có thể mở URL này từ máy/điện thoại khác.

## 5. Giới hạn của bản miễn phí

Render Free có thể sleep sau 15 phút không có traffic; lần truy cập sau có thể mất khoảng một phút để khởi động lại.

Filesystem của Free Web Service là ephemeral, vì vậy SQLite và file upload local có thể mất khi service restart/redeploy. Bản này phù hợp cho demo/MVP, không phải production.

## 6. Nếu muốn domain riêng

Domain riêng như `daoyou.com` hoặc `daoyou.vn` thường cần mua. Render hỗ trợ custom domain và tự cấp TLS/HTTPS; nhưng việc mua domain là chi phí riêng.

## 7. Tài khoản demo

Admin:
admin@daoyou.local / Admin@123

Tourist:
tourist@daoyou.local / Tourist@123

Guide:
guide@daoyou.local / Guide@123

Guide 2:
guide2@daoyou.local / Guide@123
