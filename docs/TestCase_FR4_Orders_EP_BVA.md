# KIỂM THỬ HỘP ĐEN – FR4: PHÂN HỆ ĐẶT HÀNG & THANH TOÁN ĐA KÊNH

| Thông tin | Chi tiết |
| :--- | :--- |
| Hệ thống | Green Shop |
| Phân hệ | FR4 – Đặt hàng & Thanh toán đa kênh (UC04) |
| Người thực hiện | Trần Đình Đức (Thành viên 4) |
| Kỹ thuật | Phân hoạch tương đương (EP), Phân tích giá trị biên (BVA) |
| Công cụ thực thi | Django TestCase – [`orders/tests.py`](../orders/tests.py); Postman – collection `Green Shop - Orders & Payment (FR4)` |
| Số test case | 52 (TC-ORD-01 → TC-ORD-52) |
| Ngày thực thi | …/11/2026 (điền sau khi chạy) |

> **Lưu ý:** cột "Dự đoán" dựa trên đọc mã nguồn. Hãy chạy `python manage.py test orders -v 2` rồi điền cột "Kết quả thực tế" trong file Excel `docs/orders_testcase.xlsx`.

---

## 1. Functional Requirements (trích SRS mục 3.4 & UC04)

| Mã FR | Tên | Mô tả | Endpoint |
| :---: | :--- | :--- | :--- |
| FR4.1 | Nhập thông tin giao nhận | Bắt buộc Họ tên, SĐT, Địa chỉ; Ghi chú tùy chọn. Thiếu trường bắt buộc → chặn gửi form (A1). | `POST /orders/checkout/` |
| FR4.2 | Chọn phương thức thanh toán | 1 trong 3: `cod`, `qr`, `mock`. | `POST /orders/checkout/` |
| FR4.3 | Thanh toán COD | Order `pending`, sao chép giỏ sang `OrderItem`, xóa giỏ, chuyển `order_success`. | `GET /orders/success/<id>/` |
| FR4.4 | Thanh toán VietQR | Order `awaiting_transfer`, sinh QR (STK, số tiền, nội dung `THANH TOAN DH{id}`); nút "Đã thanh toán" → `paid`. | `GET /orders/qr/<id>/`, `POST /orders/qr/<id>/confirm/` |
| FR4.5 | Thanh toán Mock | Order `pending` → trang Sandbox; Thành công → `paid` + xóa giỏ; Thất bại → `failed` (A2). | `/orders/mock/<id>/`, `.../success/`, `.../fail/` |
| FR4.6 | Xác nhận đơn hàng | Hiển thị mã đơn, người nhận, phương thức, trạng thái, danh sách món, tổng tiền. | `GET /orders/success/<id>/` |
| BR04.1 | Snapshot | `OrderItem` lưu bản sao tên & giá lúc mua. | – |
| BR04.2 | Dọn giỏ | Sau khi tạo đơn giỏ phải rỗng để tránh đặt trùng. | – |

---

## 2. Bảng phân hoạch tương đương (EP)

| Điều kiện đầu vào | Lớp hợp lệ | Lớp không hợp lệ |
| :--- | :--- | :--- |
| Trạng thái đăng nhập | V1: đã đăng nhập | I1: khách chưa đăng nhập → chuyển login |
| Giỏ hàng | V2: có ≥ 1 CartItem | I2: chưa có Cart; I3: Cart rỗng → về /cart/ |
| Họ tên (sau strip) | V3: 1 ≤ độ dài ≤ 255 | X1: rỗng/toàn khoảng trắng; X4: > 255 |
| Số điện thoại (sau strip) | V4: 1 ≤ độ dài ≤ 20 | X2: rỗng; X5: > 20 |
| Địa chỉ (sau strip) | V5: độ dài ≥ 1 | X3: rỗng |
| Ghi chú | V6: bất kỳ (kể cả rỗng / không gửi) | – |
| Phương thức thanh toán | V7: cod (hoặc không gửi → mặc định cod); V8: qr; V9: mock | X6: giá trị khác {cod, qr, mock} |
| Tổng tiền đơn | V10: 1 ≤ tổng ≤ 99.999.999 | X7: ≥ 100.000.000 |
| Trạng thái/PT của đơn khi xác nhận QR / Mock | V11: đúng PT và đúng trạng thái trước đó | I7: sai PT hoặc đã ở trạng thái cuối/khác |
| Phương thức HTTP của hành động đổi trạng thái | V12: POST (+CSRF) | I8: GET |
| Chủ sở hữu đơn | V13: đúng user | I9: user khác → 404 |
| order_id | V14: số nguyên dương, tồn tại | I10: không tồn tại → 404; I11: không phải số/âm → 404 |

## 3. Bảng phân tích giá trị biên (BVA: min-, min, min+, nominal, max-, max, max+)

| Biến | min- | min | min+ | nominal | max- | max | max+ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Họ tên (ký tự) | B1: 0 | B2: 1 | B3: 2 | ~13 | B5: 254 | B6: 255 | B7: 256 |
| SĐT (ký tự) | B8: 0 | B9: 1 | B10: 2 | 10 | B12: 19 | B13: 20 | B14: 21 |
| Địa chỉ (ký tự) | B15: 0 | B16: 1 | B17: 2 | ~30 | – | – | – |
| Tổng tiền (VND) | 0 (không xảy ra: giỏ rỗng) | B18: 1 | B19: 2 | 130.000 | 99.999.998 | B20: 99.999.999 | B21: 100.000.000 |

Giới hạn lấy từ model: `Order.full_name` max_length=255, `Order.phone` max_length=20, `Order.total_price` DecimalField(max_digits=10, decimal_places=2) → tối đa **99.999.999**.

---

## 4. Bảng test case

| Mã TC | FR | Tên | Tag | Dữ liệu vào | Kết quả mong đợi | Dự đoán | Lỗi |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **A. Truy cập & tiền điều kiện** | | | | | | | |
| TC-ORD-01 | UC04-Pre | Khách GET checkout | I1 | Chưa đăng nhập; GET /orders/checkout/ | 302 → /accounts/login/?next=... | PASS |  |
| TC-ORD-02 | UC04-Pre | Khách POST checkout | I1 | Chưa đăng nhập; POST dữ liệu hợp lệ | 302 → login; không tạo Order | PASS |  |
| TC-ORD-03 | UC04-Pre | User chưa có Cart | I2 | Đăng nhập; chưa có bản ghi Cart; GET checkout | 302 → /cart/ | PASS |  |
| TC-ORD-04 | UC04-Pre | Giỏ rỗng - GET | I3 | Đăng nhập; Cart có 0 CartItem; GET checkout | 302 → /cart/ | PASS |  |
| TC-ORD-05 | UC04-Pre | Giỏ rỗng - POST | I3 | Đăng nhập; giỏ rỗng; POST dữ liệu hợp lệ | 302 → /cart/; không tạo Order | PASS |  |
| TC-ORD-06 | FR4.1/4.2 | GET checkout có hàng | V1 V2 | Giỏ: A×2 (50.000) + B×1 (30.000) | 200; hiện tên SP, tổng 130.000, đủ 3 radio cod/qr/mock | PASS |  |
| **B. FR4.1 Thông tin giao nhận (EP/BVA)** | | | | | | | |
| TC-ORD-07 | FR4.1 | Tất cả ở min | V3 V4 V5 B2 B9 B16 | full_name="A", phone="0", address="B", note="" | 302; Order lưu đúng 3 giá trị | PASS |  |
| TC-ORD-08 | FR4.1 | Tất cả ở min+ | V3 V4 V5 B3 B10 B17 | full_name 2 ký tự, phone 2 ký tự, address 2 ký tự | 302; tạo 1 Order | PASS |  |
| TC-ORD-09 | FR4.1 | Nominal - lưu đúng ghi chú | V3 V4 V5 V6 | Tên "Trần Đình Đức", SĐT 0901234567, địa chỉ + note "Giao giờ hành chính" | 302; Order lưu chính xác cả 4 trường | PASS |  |
| TC-ORD-10 | FR4.1 | Họ tên max-, SĐT max- | B5 B12 | full_name 254 ký tự, phone 19 ký tự | 302; tạo Order, độ dài giữ nguyên | PASS |  |
| TC-ORD-11 | FR4.1 | Họ tên max, SĐT max | B6 B13 | full_name 255 ký tự, phone 20 ký tự | 302; tạo Order, độ dài giữ nguyên | PASS |  |
| TC-ORD-12 | FR4.1 | Họ tên rỗng (min-) | X1 B1 | full_name="" | 200 hiển thị lại form + cảnh báo; KHÔNG tạo Order (A1) | FAIL | BUG-ORD-02 |
| TC-ORD-13 | FR4.1 | Họ tên toàn khoảng trắng | X1 | full_name="     " | Như TC-12 (sau khi cắt khoảng trắng = rỗng) | FAIL | BUG-ORD-02 |
| TC-ORD-14 | FR4.1 | SĐT rỗng (min-) | X2 B8 | phone="" | Như TC-12 | FAIL | BUG-ORD-02 |
| TC-ORD-15 | FR4.1 | Địa chỉ rỗng (min-) | X3 B15 | address="" | Như TC-12 | FAIL | BUG-ORD-02 |
| TC-ORD-16 | FR4.1 | Bỏ trống cả 3 trường | X1 X2 X3 | full_name="", phone="", address="" | Như TC-12 | FAIL | BUG-ORD-02 |
| TC-ORD-17 | FR4.1 | Họ tên 256 ký tự (max+) | X4 B7 | full_name 256 ký tự | Chặn, không tạo Order (vượt max_length=255) | FAIL | BUG-ORD-03 |
| TC-ORD-18 | FR4.1 | SĐT 21 ký tự (max+) | X5 B14 | phone 21 ký tự | Chặn, không tạo Order (vượt max_length=20) | FAIL | BUG-ORD-03 |
| TC-ORD-19 | FR4.1 | Không gửi trường note | V6 | Form không có key note | 302; tạo Order, note rỗng (note là tùy chọn) | PASS |  |
| TC-ORD-20 | FR4.1 | Cắt khoảng trắng đầu/cuối | V3 V4 V5 | full_name="  Đức  ", phone=" 0901234567 ", address="  HCM  " | Lưu "Đức", "0901234567", "HCM" | PASS |  |
| **C. FR4.2 Chọn phương thức thanh toán** | | | | | | | |
| TC-ORD-21 | FR4.2 | Không gửi payment_method | V7 | Form không có payment_method | Mặc định cod: Order pending | PASS |  |
| TC-ORD-22 | FR4.2 | payment_method không hợp lệ | X6 | payment_method = "bitcoin" / "COD" / "" | Chặn, không tạo Order, không âm thầm đổi sang COD | FAIL | BUG-ORD-09 |
| **D. FR4.3 Thanh toán COD** | | | | | | | |
| TC-ORD-23 | FR4.3 | COD tạo đơn pending | V7 | Giỏ A×2; payment_method=cod | 302 → /orders/success/<id>/; status=pending; total=100.000; đúng user | PASS |  |
| TC-ORD-24 | FR4.3 | Sao chép giỏ → OrderItem | V7 | Giỏ A×2, B×3 | 2 OrderItem đúng product_name, price, quantity | PASS |  |
| TC-ORD-25 | FR4.3 / BR04.2 | COD dọn giỏ | V7 | Giỏ 2 SP; đặt COD | CartItem còn 0 | PASS |  |
| TC-ORD-26 | BR04.1 | OrderItem là snapshot | V7 | Đặt xong rồi đổi giá/tên SP trong bảng Product | OrderItem giữ giá/tên lúc mua | PASS |  |
| TC-ORD-27 | FR4.3 | Tổng tiền = Σ giá × SL | V7 | A×2 (50.000) + B×1 (30.000) | total_price = 130.000 | PASS |  |
| TC-ORD-28 | BR04.2 | Gửi lại form lần 2 | I3 | Đặt COD xong, POST lại cùng dữ liệu | 302 → /cart/; vẫn chỉ 1 Order | PASS |  |
| **E. FR4.4 Thanh toán VietQR** | | | | | | | |
| TC-ORD-29 | FR4.4 | QR tạo đơn awaiting_transfer | V8 | payment_method=qr | 302 → /orders/qr/<id>/; status=awaiting_transfer; giỏ rỗng | PASS |  |
| TC-ORD-30 | FR4.4 | Trang QR đúng thông tin | V8 | Đơn qr, total 150.000 | Ảnh img.vietqr.io có STK, amount=150000, addInfo=THANH TOAN DH{id}; có nút xác nhận | PASS |  |
| TC-ORD-31 | FR4.4 | Xác nhận đã chuyển khoản | V8 | POST /orders/qr/<id>/confirm/ trên đơn awaiting_transfer | status=paid; 302 → success | PASS |  |
| TC-ORD-32 | FR4.4 | Confirm bằng GET | V8 | GET /orders/qr/<id>/confirm/ | Không đổi trạng thái | PASS |  |
| TC-ORD-33 | NFR2 | Confirm thiếu CSRF token | V8 | POST confirm, client bật enforce_csrf_checks | 403; trạng thái không đổi | PASS |  |
| TC-ORD-34 | FR4.4 | Confirm trên đơn không phải QR | I7 | Đơn cod/mock (pending); POST confirm | Trạng thái giữ pending (không được thành paid) | FAIL | BUG-ORD-04 |
| TC-ORD-35 | FR4.4 | Confirm trên đơn completed/cancelled/failed | I7 | Đơn qr trạng thái completed, cancelled, failed; POST confirm | Trạng thái giữ nguyên | FAIL | BUG-ORD-04 |
| **F. FR4.5 Thanh toán Mock** | | | | | | | |
| TC-ORD-36 | FR4.5 | Mock tạo đơn pending | V9 | payment_method=mock | 302 → /orders/mock/<id>/; pending; giỏ chưa xóa | PASS |  |
| TC-ORD-37 | FR4.5 | Trang Sandbox hiển thị | V9 | GET /orders/mock/<id>/ | 200; có 2 nút trỏ /success/ và /fail/ | FAIL | BUG-ORD-01 |
| TC-ORD-38 | FR4.5 | Mock thành công | V9 | POST /orders/mock/<id>/success/ | status=paid; giỏ rỗng; 302 → success | PASS |  |
| TC-ORD-39 | FR4.5 | Mock thất bại | V9 | POST /orders/mock/<id>/fail/ | status=failed; giỏ giữ nguyên | PASS |  |
| TC-ORD-40 | A2 | Trang kết quả khi thất bại | V9 | Sau TC-39, mở trang kết quả | Báo thanh toán thất bại, không hiện "Đặt hàng thành công" | FAIL | BUG-ORD-08 |
| TC-ORD-41 | FR4.5 | Mock success trên đơn COD | I7 | Đơn cod pending + giỏ mới 1 SP; POST mock success | Đơn vẫn pending; giỏ không bị xóa | FAIL | BUG-ORD-05 |
| TC-ORD-42 | FR4.5 | Mock fail trên đơn đã paid | I7 | Đơn mock paid; POST mock fail | Vẫn paid | FAIL | BUG-ORD-05 |
| TC-ORD-43 | NFR2 | Đổi trạng thái bằng GET | I8 | GET /orders/mock/<id>/success/ và /fail/ | Không đổi trạng thái (chỉ nhận POST) | FAIL | BUG-ORD-06 |
| **G. FR4.6 Trang xác nhận đơn hàng** | | | | | | | |
| TC-ORD-44 | FR4.6 | Hiển thị đủ thông tin đơn | V7 | Đặt COD giỏ A×2 + B×1; mở trang success | Có: mã đơn, người nhận, SĐT, địa chỉ, phương thức, trạng thái, danh sách món, tổng tiền | FAIL | BUG-ORD-07 |
| **H. Phân quyền chủ đơn & định danh** | | | | | | | |
| TC-ORD-45 | NFR2 | User khác truy cập đơn người khác | I9 | User B gọi 6 endpoint với order_id của user A | 404 tất cả; trạng thái đơn không đổi | PASS |  |
| TC-ORD-46 | NFR3 | Mã đơn không tồn tại | I10 | order_id=999999 trên 6 endpoint | 404 | PASS |  |
| TC-ORD-47 | NFR2 | Khách vào endpoint đơn hàng | I1 | Chưa đăng nhập gọi 6 endpoint | 302 → login; trạng thái không đổi | PASS |  |
| TC-ORD-48 | NFR3 | Mã đơn không phải số nguyên dương | I11 | order_id = abc, -1, 0x1 | 404 | PASS |  |
| **I. Biên tổng tiền & độ tin cậy** | | | | | | | |
| TC-ORD-49 | FR4.3 | Tổng tiền min | B18 | 1 SP giá 1 VND × 1 | 302; total=1 | PASS |  |
| TC-ORD-50 | FR4.3 | Tổng tiền max | B20 | 1 SP giá 99.999.999 × 1 | 302; total=99.999.999 | PASS |  |
| TC-ORD-51 | NFR3 | Tổng tiền max+ | X7 B21 | 1 SP giá 100.000.000 × 1 | Không lỗi 500; báo vượt giới hạn; KHÔNG lưu Order/OrderItem | FAIL | BUG-ORD-10 |
| TC-ORD-52 | NFR3 | Tính nguyên tử (ACID) | NFR3 | Giả lập lỗi khi lưu OrderItem | Rollback: không còn Order mồ côi; giỏ giữ nguyên | FAIL | BUG-ORD-11 |

---

## 5. Danh sách lỗi phát hiện

| Mã lỗi | Mức độ | FR | Tiêu đề | Test case | Hướng sửa |
| :--- | :---: | :---: | :--- | :---: | :--- |
| BUG-ORD-01 | Cao | FR4.5 | Trang Sandbox thanh toán Mock lỗi 500 | TC-37 | Dùng order.id, order.total_price; nút chuyển thành form POST. |
| BUG-ORD-02 | Cao | FR4.1 / A1 | Server không kiểm tra Họ tên / SĐT / Địa chỉ trống | TC-12 → TC-16 | Thêm validate_checkout_form(); hiển thị lại form kèm lỗi. |
| BUG-ORD-03 | Trung bình | FR4.1 | Không giới hạn độ dài Họ tên (255) / SĐT (20) | TC-17, TC-18 | Kiểm tra len() trước khi lưu; thêm maxlength ở HTML. |
| BUG-ORD-04 | Cao | FR4.4 | Nút "Đã thanh toán" áp dụng được cho mọi đơn, mọi trạng thái | TC-34, TC-35 | Chỉ đổi khi payment_method=qr và status=awaiting_transfer. |
| BUG-ORD-05 | Cao | FR4.5 | Mock success/fail áp dụng cho mọi đơn, mọi trạng thái; success còn xóa giỏ hiện tại | TC-41, TC-42 | Chỉ success khi mock + (pending/failed); chỉ fail khi mock + pending. |
| BUG-ORD-06 | Trung bình | NFR2 | Đổi trạng thái đơn bằng request GET | TC-43 | Dùng @require_POST và form có csrf_token. |
| BUG-ORD-07 | Cao | FR4.6 | Trang xác nhận không hiển thị thông tin đơn hàng | TC-44 | Bổ sung khối thông tin đơn vào template. |
| BUG-ORD-08 | Trung bình | A2 | Thanh toán Mock thất bại nhưng trang báo "Đặt hàng thành công" | TC-40 | Template rẽ nhánh theo status=failed, kèm link thử lại. |
| BUG-ORD-09 | Thấp | FR4.2 | payment_method không hợp lệ bị âm thầm đổi thành COD | TC-22 | Báo lỗi thay vì đổi ngầm. |
| BUG-ORD-10 | Trung bình | NFR3 / NFR5 | Không chặn đơn có tổng tiền vượt giới hạn cột (≥ 100.000.000 VND) | TC-51 | Kiểm tra tổng ≤ 99.999.999 và báo lỗi thân thiện (hoặc nâng max_digits). |
| BUG-ORD-11 | Trung bình | NFR3 | Không dùng transaction khi tạo đơn | TC-52 | Bọc trong transaction.atomic(). |

### BUG-ORD-01 – Trang Sandbox thanh toán Mock lỗi 500
- **Mức độ:** Cao  |  **Yêu cầu liên quan:** FR4.5  |  **Test case phát hiện:** TC-37
- **Nguyên nhân (đọc mã):** orders/templates/orders/mock_payment.html dùng order.order_code và order.total_amount (là trường của model cũ đã bị xóa ở migration cart 0002). Thẻ {% url ... order.order_code %} nhận chuỗi rỗng nên Django ném NoReverseMatch.
- **Cách tái hiện / hậu quả:** Đặt hàng chọn "Thanh toán online mô phỏng" → trang /orders/mock/<id>/ báo lỗi 500; không thể bấm Thành công/Thất bại.
- **Hướng sửa:** Dùng order.id, order.total_price; nút chuyển thành form POST.

### BUG-ORD-02 – Server không kiểm tra Họ tên / SĐT / Địa chỉ trống
- **Mức độ:** Cao  |  **Yêu cầu liên quan:** FR4.1 / A1  |  **Test case phát hiện:** TC-12 → TC-16
- **Nguyên nhân (đọc mã):** checkout() chỉ strip() rồi lưu; chỉ có thuộc tính required ở HTML (bypass được bằng Postman/DevTools).
- **Cách tái hiện / hậu quả:** POST với full_name rỗng → vẫn tạo Order và chuyển trang thành công, trái SRS (A1: chặn gửi form).
- **Hướng sửa:** Thêm validate_checkout_form(); hiển thị lại form kèm lỗi.

### BUG-ORD-03 – Không giới hạn độ dài Họ tên (255) / SĐT (20)
- **Mức độ:** Trung bình  |  **Yêu cầu liên quan:** FR4.1  |  **Test case phát hiện:** TC-17, TC-18
- **Nguyên nhân (đọc mã):** SQLite không ép max_length nên lưu được chuỗi dài; PostgreSQL sẽ lỗi 500 (NFR5 yêu cầu đổi DB không phải sửa code).
- **Cách tái hiện / hậu quả:** POST full_name 256 ký tự hoặc phone 21 ký tự vẫn tạo đơn.
- **Hướng sửa:** Kiểm tra len() trước khi lưu; thêm maxlength ở HTML.

### BUG-ORD-04 – Nút "Đã thanh toán" áp dụng được cho mọi đơn, mọi trạng thái
- **Mức độ:** Cao  |  **Yêu cầu liên quan:** FR4.4  |  **Test case phát hiện:** TC-34, TC-35
- **Nguyên nhân (đọc mã):** confirm_qr_paid() chỉ kiểm tra POST, không kiểm tra payment_method=qr và status=awaiting_transfer.
- **Cách tái hiện / hậu quả:** Khách tự đưa đơn COD/đã hoàn tất/đã hủy/thất bại sang paid → Dashboard (BR06.1) tính sai doanh thu.
- **Hướng sửa:** Chỉ đổi khi payment_method=qr và status=awaiting_transfer.

### BUG-ORD-05 – Mock success/fail áp dụng cho mọi đơn, mọi trạng thái; success còn xóa giỏ hiện tại
- **Mức độ:** Cao  |  **Yêu cầu liên quan:** FR4.5  |  **Test case phát hiện:** TC-41, TC-42
- **Nguyên nhân (đọc mã):** mock_payment_success/fail không kiểm tra payment_method và status.
- **Cách tái hiện / hậu quả:** Gọi mock success vào đơn COD cũ → đơn thành paid và giỏ hàng đang mua dở bị xóa sạch; gọi fail vào đơn paid → hạ xuống failed.
- **Hướng sửa:** Chỉ success khi mock + (pending/failed); chỉ fail khi mock + pending.

### BUG-ORD-06 – Đổi trạng thái đơn bằng request GET
- **Mức độ:** Trung bình  |  **Yêu cầu liên quan:** NFR2  |  **Test case phát hiện:** TC-43
- **Nguyên nhân (đọc mã):** Link <a href> gọi mock_payment_success/fail; không có require_POST/CSRF. Trình duyệt prefetch hoặc thẻ <img src> độc hại có thể kích hoạt.
- **Cách tái hiện / hậu quả:** GET /orders/mock/<id>/success/ làm đơn thành paid.
- **Hướng sửa:** Dùng @require_POST và form có csrf_token.

### BUG-ORD-07 – Trang xác nhận không hiển thị thông tin đơn hàng
- **Mức độ:** Cao  |  **Yêu cầu liên quan:** FR4.6  |  **Test case phát hiện:** TC-44
- **Nguyên nhân (đọc mã):** success.html là trang tĩnh, không dùng biến order nào.
- **Cách tái hiện / hậu quả:** Thiếu mã đơn, người nhận, phương thức, trạng thái, danh sách món, tổng tiền (SRS FR4.6).
- **Hướng sửa:** Bổ sung khối thông tin đơn vào template.

### BUG-ORD-08 – Thanh toán Mock thất bại nhưng trang báo "Đặt hàng thành công"
- **Mức độ:** Trung bình  |  **Yêu cầu liên quan:** A2  |  **Test case phát hiện:** TC-40
- **Nguyên nhân (đọc mã):** mock_payment_fail redirect sang order_success, template luôn hiện thông báo thành công.
- **Cách tái hiện / hậu quả:** Khách hiểu nhầm đơn đã thành công dù trạng thái là failed.
- **Hướng sửa:** Template rẽ nhánh theo status=failed, kèm link thử lại.

### BUG-ORD-09 – payment_method không hợp lệ bị âm thầm đổi thành COD
- **Mức độ:** Thấp  |  **Yêu cầu liên quan:** FR4.2  |  **Test case phát hiện:** TC-22
- **Nguyên nhân (đọc mã):** if payment_method not in [...]: payment_method = "cod".
- **Cách tái hiện / hậu quả:** Request giả mạo vẫn sinh đơn COD mà khách không chọn.
- **Hướng sửa:** Báo lỗi thay vì đổi ngầm.

### BUG-ORD-10 – Không chặn đơn có tổng tiền vượt giới hạn cột (≥ 100.000.000 VND)
- **Mức độ:** Trung bình  |  **Yêu cầu liên quan:** NFR3 / NFR5  |  **Test case phát hiện:** TC-51
- **Nguyên nhân (đọc mã):** Order.total_price là DecimalField(max_digits=10, decimal_places=2) → tối đa 99.999.999, nhưng view không kiểm tra. SQLite không ép giới hạn nên vẫn lưu được; PostgreSQL/MySQL sẽ báo lỗi và trả 500. Giỏ rất dễ vượt (cart cho phép số lượng tới 2.147.483.647).
- **Cách tái hiện / hậu quả:** Kết quả chạy thật trên SQLite: đặt giỏ 100.000.000 VND → KHÔNG lỗi 500, đơn vẫn được lưu (Order.objects.count() = 1, mong đợi 0). Khi đổi sang CSDL khác (NFR5) sẽ lỗi 500.
- **Hướng sửa:** Kiểm tra tổng ≤ 99.999.999 và báo lỗi thân thiện (hoặc nâng max_digits).

### BUG-ORD-11 – Không dùng transaction khi tạo đơn
- **Mức độ:** Trung bình  |  **Yêu cầu liên quan:** NFR3  |  **Test case phát hiện:** TC-52
- **Nguyên nhân (đọc mã):** Order.objects.create() rồi vòng lặp OrderItem.objects.create() và xóa giỏ, không bọc transaction.atomic().
- **Cách tái hiện / hậu quả:** Nếu lỗi giữa chừng, còn lại Order rỗng (không có món) trong CSDL; SRS NFR3 yêu cầu ACID.
- **Hướng sửa:** Bọc trong transaction.atomic().

---

## 6. Tổng hợp kết quả (điền sau khi chạy)

| Lần chạy | Tổng | PASS | FAIL | Ghi chú |
| :--- | :---: | :---: | :---: | :--- |
| Trước fix | 52 | 34 | 18 | Chạy thực tế: Django báo failures=22 vì subtest được đếm riêng (18 test, 22 dòng lỗi) |
| Sau fix | 52 | … | … | Áp dụng `orders_fix.patch` |

## 7. Cách chạy

```bash
python manage.py test orders -v 2
python manage.py test orders.tests.CheckoutFormTests -v 2   # chạy 1 nhóm
```
