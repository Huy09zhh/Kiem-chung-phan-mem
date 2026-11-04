# Hướng dẫn cấu hình email sau khi tải project

Người tải Green Shop từ Git cần cấu hình SMTP cho môi trường của mình để gửi
email thật. Project đã có phần gửi thư và chức năng quên mật khẩu.

Một tài khoản SMTP gửi thư chung cho hệ thống. Admin và người dùng thường nhận
liên kết đặt lại mật khẩu tại email gắn với tài khoản Green Shop của họ; họ không
cần tự cấu hình SMTP khi sử dụng website đã triển khai.

## 1. Chuẩn bị file cấu hình

1. Mở thư mục gốc project, nơi chứa `manage.py` và `.env.example`.
2. Nếu chưa có `.env`, sao chép `.env.example` và đổi tên bản sao thành `.env`.
   Kiểm tra tên file không bị thêm đuôi `.txt`.
3. Nếu đã có `.env`, giữ nguyên file và chỉ cập nhật các mục email cần thiết.

File mẫu để trống tài khoản và mật khẩu. Sao chép file mẫu chưa làm hệ thống gửi
email thật; cần hoàn tất các bước tiếp theo.

## 2. Chuẩn bị Gmail gửi thư

1. Đăng nhập Gmail hoặc tài khoản trường sử dụng Google Workspace.
2. Bật **Xác minh 2 bước** trong cài đặt bảo mật tài khoản.
3. Mở [Mật khẩu ứng dụng](https://myaccount.google.com/apppasswords).
4. Tạo mật khẩu ứng dụng với tên **Green Shop**.
5. Lưu mã 16 ký tự được cấp để điền vào `.env`; bỏ khoảng trắng phân nhóm khi sao chép.

Với tài khoản trường, tính năng này còn phụ thuộc chính sách của trường. Nếu đã
bật Xác minh 2 bước mà vẫn không có Mật khẩu ứng dụng, liên hệ quản trị viên trường.
Project hiện sử dụng SMTP bằng mật khẩu ứng dụng; Gmail API/OAuth hoặc SMTP relay
cần được triển khai, cấu hình riêng.

Tham khảo: [Hướng dẫn của Google](https://support.google.com/accounts/answer/185833?hl=vi).

## 3. Điền thông tin vào `.env`

| Mục cấu hình | Giá trị cần điền |
|---|---|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | Gmail hoặc email trường dùng gửi thư |
| `EMAIL_HOST_PASSWORD` | Mật khẩu ứng dụng 16 ký tự vừa tạo |
| `DEFAULT_FROM_EMAIL` | Không bắt buộc. Nếu dùng, bỏ dấu chú thích ở dòng mẫu và thay địa chỉ bằng email gửi thư của bạn |

Không dùng mật khẩu đăng nhập Gmail thông thường thay cho mật khẩu ứng dụng.
Giữ nguyên các cấu hình khác trong `.env`.

Project đọc `.env` khi khởi động. Những biến email đã được đặt sẵn trong môi trường
chạy sẽ được ưu tiên hơn giá trị trong file này.

## 4. Khởi động lại và kiểm tra

1. Lưu `.env`, dừng server Django rồi khởi động lại theo cách chạy project.
2. Mở trang [Quên mật khẩu trên localhost](http://127.0.0.1:8000/accounts/password/reset/).
3. Nhập email của tài khoản Green Shop đang hoạt động và đã có mật khẩu nội bộ.
4. Bấm **Gửi liên kết đặt lại mật khẩu**.
5. Kiểm tra hộp thư đến và thư rác của địa chỉ vừa nhập.
6. Mở email **Đặt lại mật khẩu Green Shop**, truy cập liên kết và đặt mật khẩu mới.

Website giữ cùng thông báo cho email tồn tại và không tồn tại. Vì vậy, thấy
“Đã gửi email” chưa đủ để xác nhận gửi thành công; cần kiểm tra hộp thư người nhận.

Liên kết lấy địa chỉ từ website đang truy cập. Link `127.0.0.1` phải được mở trên
máy chạy project. Khi triển khai, gửi yêu cầu từ địa chỉ website mà người nhận
có thể truy cập.

## 5. Hành vi của hệ thống

| Trạng thái cấu hình | Hành vi |
|---|---|
| Có `EMAIL_HOST_USER` | Chọn backend SMTP; cần thông tin xác thực hợp lệ để gửi thành công. Hộp thư dev tắt |
| `EMAIL_HOST_USER` trống, `DEBUG=True` | Email lưu trong `sent_emails/`; hộp thư dev chỉ dành cho superuser đang hoạt động |
| `EMAIL_HOST_USER` trống, `DEBUG=False` | Email lưu vào file; không gửi email thật và không có hộp thư dev |

Người chưa đăng nhập, customer và staff không phải superuser không được xem/xóa
hộp thư dev. Superuser quên mật khẩu và chưa đăng nhập cũng không được đọc hộp thư
này. Website phục vụ người dùng thật cần cấu hình gửi email thật.
