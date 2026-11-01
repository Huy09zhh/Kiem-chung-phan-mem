# SCRUM-42 — Hoàn thành khắc phục và kiểm thử

**Kết quả kiểm thử lại: PASS.**

**Nguyên nhân:** Hộp thư dev chỉ kiểm tra chế độ dev, chưa kiểm tra quyền truy cập.
Người chưa đăng nhập có thể đọc email chứa liên kết đặt lại mật khẩu của tài khoản
khác và truy cập endpoint xóa thư. Trang “Đã gửi email” cũng hiển thị liên kết hộp thư
cho người dùng không có quyền.

**Cách sửa:** Chỉ superuser đang hoạt động được xem/xóa hộp thư khi tính năng dev được
bật và `DEBUG=True`. Chặn người chưa đăng nhập, customer, staff không phải superuser;
ẩn liên kết tương ứng và ngăn cache phản hồi. Xóa thư tiếp tục yêu cầu POST và CSRF.

**Kết quả đã xác minh:**

- 31/31 test tự động PASS trên CSDL kiểm thử riêng: 16 test bảo mật hộp thư dev và
  15 test accounts hiện có.
- Người không có quyền không đọc/xóa được thư, kể cả POST có CSRF hợp lệ.
- Superuser được thao tác trong dev; thiếu CSRF trả 403, GET tới endpoint xóa trả 405.
- Tắt tính năng hoặc `DEBUG=False` đều chặn truy cập hộp thư dev.
- Luồng đặt lại mật khẩu hợp lệ vẫn hoạt động trong kiểm thử tích hợp.
- Đã cấu hình SMTP bằng tài khoản trường trên máy kiểm thử và xác nhận email thử đã
  tới hộp thư. Thao tác quên mật khẩu từ localhost cũng gửi và nhận email thành công.
- Sau khi bật SMTP, `/dev/mailbox/` trả 404; trang “Đã gửi email” không hiển thị liên
  kết hộp thư dev. Lượt kiểm tra SMTP thực tế không thay đổi mật khẩu tài khoản.

**Kết luận:** Hoàn thành khắc phục SCRUM-42 và kiểm thử lại trong phạm vi trên.
Cấu hình SMTP thật được giữ trong `.env` riêng, không đưa lên Git. Người tải project
cần cấu hình SMTP của môi trường mình theo [hướng dẫn](../SMTP_SETUP.md).

Ngày xác nhận SMTP: 01/11/2026. Bộ test bảo mật: [core/tests.py](../../core/tests.py).
