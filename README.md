# DAOYOU

DAOYOU là website demo/MVP xây dựng bằng Python Flask, mô phỏng nền tảng kết nối du khách quốc tế với hướng dẫn viên.

## Có sẵn trong bản demo

- Đăng ký/đăng nhập và phân quyền Tourist / Guide / Admin.
- Tìm kiếm hướng dẫn viên theo địa điểm, ngôn ngữ, chuyên môn, ngân sách, rating.
- Trang chi tiết hướng dẫn viên.
- Đăng ký trở thành hướng dẫn viên và trạng thái chờ duyệt.
- Admin duyệt/từ chối hồ sơ hướng dẫn viên.
- Booking.
- Tính phí nền tảng 10% đối với khách và 10% hoa hồng phía HDV.
- Tạo QR demo cho đơn hàng.
- Xác nhận thanh toán demo và trạng thái Escrow.
- Guide xem yêu cầu booking, chấp nhận/từ chối.
- Tourist xem lịch sử booking.
- Review sau chuyến đi.
- SOS 24/7 dạng demo: lưu tọa độ và hiển thị cho Admin.
- Dashboard Admin.
- Google Maps link cho điểm hẹn (không cần API key ở bản demo).

## Lưu ý quan trọng

VNPay, Google Maps API, email/SMS, upload giấy tờ thật và chuyển tiền thật chưa được kích hoạt trong demo vì cần tài khoản/API key/merchant credentials. Code đã tách phần cấu hình để có thể tích hợp sau.

## Chạy project

Windows PowerShell:

```powershell
cd DAOYOU
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Sau đó mở: http://127.0.0.1:5000

Tài khoản admin demo:
- Email: admin@daoyou.local
- Password: Admin@123

Có thể chạy `python app.py --seed` để tạo dữ liệu demo.

## Cấu trúc

- `app.py`: backend Flask + database models + routes.
- `templates/`: giao diện HTML/Jinja.
- `static/css/style.css`: CSS.
- `static/js/app.js`: JavaScript.
- `instance/daoyou.db`: SQLite được tạo tự động khi chạy.


## Deploy công khai miễn phí

Project đã được chuẩn bị cho Render:
- `render.yaml`
- `Procfile`
- `gunicorn`
- bind port theo biến môi trường
- `/health` health check
- `SEED_DEMO=true` để tạo dữ liệu demo khi database mới.

Xem `DEPLOY_RENDER.md`.
