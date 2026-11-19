# KIỂM THỬ HỘP ĐEN – FR4: PHÂN HỆ ĐẶT HÀNG & THANH TOÁN ĐA KÊNH

| Thông tin | Chi tiết |
| :--- | :--- |
| Hệ thống | Green Shop |
| Phân hệ | FR4 – Đặt hàng & Thanh toán đa kênh (UC04) |
| Người thực hiện | Trần Đình Đức (Thành viên 4) |
| Kỹ thuật | Phân hoạch tương đương (EP), Phân tích giá trị biên (BVA) |
| Công cụ thực thi | Django TestCase – [`orders/tests.py`](../orders/tests.py); Postman – collection `Green Shop - Orders & Payment (FR4)` |
| Số test case | **54 TC** (TC-ORD-01 → TC-ORD-54, bao gồm TC-ORD-53 & TC-ORD-54 bổ sung) |
| Ngày thực thi | 19/11/2026 |

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
| Tổng tiền đơn | V10: 1 ≤ tổng ≤ 2.147.483.647 (ORDER_TOTAL_MAX) | X7: > 2.147.483.647 (vượt ngưỡng max int 32-bit) |
| Trạng thái/PT của đơn khi xác nhận QR / Mock | V11: đúng PT và đúng trạng thái trước đó | I7: sai PT hoặc đã ở trạng thái cuối/khác |
| Phương thức HTTP của hành động đổi trạng thái | V12: POST (+CSRF) | I8: GET |
| Chủ sở hữu đơn | V13: đúng user | I9: user khác → 404 |
| order_id | V14: số nguyên dương, tồn tại | I10: không tồn tại → 404; I11: không phải số/âm → 404 |

## 3. Bảng phân tích giá trị biên (BVA – Boundary Value Analysis)

> **Cơ sở lý thuyết (Chương IV):**
>
> Kỹ thuật BVA dựa trên quan sát thực nghiệm rằng lỗi thường xuất hiện tại **biên** (boundary) của miền giá trị đầu vào hơn là ở giữa miền. Có hai biến thể chính:
>
> - **BVA 2 giá trị (2-value BVA):** Với mỗi biên, chọn đúng **2 điểm kiểm thử**: điểm ngay trên biên và điểm ngay dưới biên. Cụ thể: tại biên **min** chọn `{min, min+1}`; tại biên **max** chọn `{max-1, max}`. Số lượng test case: $4n + 1$ (với $n$ biến đầu vào, thêm 1 ca nominal).
>
> - **BVA 3 giá trị (3-value BVA / Robustness BVA):** Với mỗi biên, chọn **3 điểm**: điểm ngay dưới biên, điểm trên biên, và điểm ngoài biên. Cụ thể: tại biên **min** chọn `{min-1, min, min+1}`; tại biên **max** chọn `{max-1, max, max+1}`. Điểm ngoài miền hợp lệ (`min-1` và `max+1`) dùng để kiểm thử xử lý **ngoại lệ / đầu vào không hợp lệ**. Số lượng test case: $6n + 1$ (với $n$ biến đầu vào, thêm 1 ca nominal).
>
> Bài làm này áp dụng **BVA 3 giá trị (Robustness)** cho các biến `full_name`, `phone`, `address` và `total_price` nhằm phủ đủ cả ca biên hợp lệ và ca biên bất hợp lệ.
>
> | Ký hiệu | Ý nghĩa |
> | :---: | :--- |
> | `min-` (min-1) | Giá trị nhỏ hơn 1 đơn vị so với giới hạn tối thiểu → **không hợp lệ** |
> | `min` | Giá trị tối thiểu hợp lệ của miền |
> | `min+` (min+1) | Giá trị lớn hơn 1 đơn vị so với tối thiểu → hợp lệ |
> | `nominal` | Giá trị đại diện ở giữa miền hợp lệ |
> | `max-` (max-1) | Giá trị nhỏ hơn 1 đơn vị so với giới hạn tối đa → hợp lệ |
> | `max` | Giá trị tối đa hợp lệ của miền |
> | `max+` (max+1) | Giá trị lớn hơn 1 đơn vị so với tối đa → **không hợp lệ** |

| Biến | min- | min | min+ | nominal | max- | max | max+ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Họ tên (ký tự) | B1: 0 | B2: 1 | B3: 2 | ~13 | B5: 254 | B6: 255 | B7: 256 |
| SĐT (ký tự) | B8: 0 | B9: 1 | B10: 2 | 10 | B12: 19 | B13: 20 | B14: 21 |
| Địa chỉ (ký tự) | B15: 0 | B16: 1 | B17: 2 | ~30 | – | – | – |
| Tổng tiền (VND) | 0 (giỏ rỗng) | B18: 1 | B19: 2 | 130.000 | 2.147.483.646 | B20: 2.147.483.647 | B21: 2.147.483.648 |

*Giới hạn lấy từ:* `Order.full_name` max_length=255, `Order.phone` max_length=20, `ORDER_TOTAL_MAX` = 2.147.483.647 VND (ngưỡng an toàn chống tràn số nguyên 32-bit).

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
| TC-ORD-50 | FR4.3 | Tổng tiền max | B20 | 1 SP giá 2.147.483.647 × 1 | 302; total=2.147.483.647 | PASS |  |
| TC-ORD-51 | NFR3 | Tổng tiền max+ | X7 B21 | 1 SP giá 2.147.483.648 × 1 | Không lỗi 500; báo vượt giới hạn; KHÔNG lưu Order/OrderItem | PASS |  |
| TC-ORD-52 | NFR3 | Tính nguyên tử (ACID) | NFR3 | Giả lập lỗi khi lưu OrderItem | Rollback: không còn Order mồ côi; giỏ giữ nguyên | FAIL | BUG-ORD-11 |
| TC-ORD-53 | NFR3 | Cảnh báo vượt biên max+ | X7 B21 | Tổng 2.147.483.648 VND; POST checkout | HTTP 200; hiện cảnh báo "vượt quá giới hạn"; giữ nguyên giỏ hàng | PASS |  |
| TC-ORD-54 | NFR3 | Tổng tiền lớn (≥ 100 triệu) | B20 | Đơn giá trị 120.000.000 VND; truy cập trang đơn | Khách (`/orders/my/`) và Admin xem chi tiết bình thường, không lỗi 500 | PASS |  |

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

## 6. Tổng hợp kết quả thực thi

| Lần chạy | Tổng TC | PASS | FAIL | Ghi chú |
| :--- | :---: | :---: | :---: | :--- |
| **Trước fix** | 52 | 34 | 18 | Django báo `failures=22` vì một số test dùng `subTest` được đếm riêng (18 test method, 22 assertion failure) |
| **Sau fix** | **54** | **54** | **0** | Chạy `python manage.py test orders -v 2` ngày 19/11/2026: `Ran 80 tests in 48.537s — OK` (**80 test** bao gồm 54 EP/BVA + 26 State Transition) |

> **Lỗi đã được khắc phục** (Các BUG-ORD-01 đến BUG-ORD-11): Xem chi tiết từng bug tại mục 5. Tất cả lỗi đã được sửa trong `orders/views.py`, `orders/models.py` và `orders/templates/orders/success.html`. Mã nguồn đã kiểm thử 100% PASS.

## 7. Cách chạy

```bash
# Chạy toàn bộ Unit Test phân hệ orders
python manage.py test orders -v 2

# Chạy kiểm thử E2E CodeceptJS tự động kèm đo độ phủ dòng và nhánh (Coverage)
python manage.py seed_orders_bva
coverage run --branch --source=orders manage.py runserver --noreload 8000
npx codeceptjs run tests/orders_checkout_bva_test.js --steps
coverage report -m
coverage json -o coverage_orders.json
```

---

## 8. Kết quả Thực thi E2E BVA & Đo độ phủ Nhánh (Branch Coverage)

### 8.1 Kết quả chạy kịch bản E2E CodeceptJS (`tests/orders_checkout_bva_test.js`)
- **Tổng số kịch bản:** 12 Test Cases (Bao quát toàn bộ miền biên $min^-, min, min^+, nominal, max, max^+$ của `total_price`, `full_name`, `phone` và 3 kênh thanh toán COD/QR/Mock).
- **Kết quả:** **12 / 12 PASS (100%)**, thời gian thực thi: ~2 phút.

### 8.2 Bảng thống kê độ phủ Code và Độ phủ Nhánh (Coverage Report)

Thực thi bằng `coverage run --branch --source=orders` qua kịch bản E2E BVA:

| Tập tin mã nguồn | Số dòng lệnh (Stmts) | Dòng thiếu (Miss) | Số nhánh (Branch) | Nhánh thiếu (BrPart) | Độ phủ (Cover) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `orders/models.py` | 41 | 9 | 0 | 0 | **78%** |
| `orders/views.py` | 105 | 19 | 24 | 3 | **81%** |
| `orders/urls.py` | 4 | 0 | 0 | 0 | **100%** |
| `orders/admin.py` | 19 | 0 | 0 | 0 | **100%** |
| `orders/apps.py` | 3 | 0 | 0 | 0 | **100%** |
| **Tổng quan nghiệp vụ chính (`views.py`)** | **105** | **19** | **24** | **3** | **81%** |

### 8.3 Phân tích chi tiết độ phủ theo lý thuyết Chương IV (White-Box Testing)

> **Lưu ý:** Số liệu Branch/Line Coverage dưới đây được đo bằng `coverage run --branch` trên phiên bản mã nguồn **TRƯỚC KHI FIX** (mã gốc của dự án), nhằm phản ánh đúng thực trạng kiểm thử ban đầu và làm cơ sở phân tích giá trị của bộ test case BVA phát hiện lỗi. Sau khi fix, `views.py` đã tăng thêm ~30 dòng lệnh xác thực mới (toàn bộ được bao phủ bởi bộ test).

Dựa trên lý thuyết Chương IV (phần **Kiểm thử hộp trắng – White-Box Testing**, kỹ thuật **Statement Coverage** và **Branch Coverage**):
- **Các nhánh và khối lệnh ĐÃ ĐƯỢC PHỦ HOÀN TOÀN bởi bộ test BVA (Covered):**
  1. Nhánh tiền điều kiện giỏ hàng rỗng (`not cart_items.exists()`) $\to$ chuyển hướng `/cart/` (TC-RBVA-01).
  2. Nhánh vượt ngưỡng tối đa (`total_price > ORDER_TOTAL_MAX`) $\to$ hiển thị cảnh báo đỏ và chặn tạo đơn (TC-RBVA-07).
  3. Nhánh chấp nhận đơn hàng tại biên $min$ (1đ), $min^+$ (2đ), $nom$ (100.000đ), $max$ (2.147.483.647đ).
  4. Nhánh xử lý phương thức thanh toán COD: snapshot giỏ hàng, xóa giỏ hàng, chuyển hướng trang `order_success`.
  5. Nhánh xử lý VietQR: hủy đơn cũ `awaiting_transfer`, tạo đơn, sinh ảnh QR `get_qr_info()` và xử lý xác nhận thanh toán `confirm_qr_paid` (POST) $\to$ chuyển sang `paid`.
  6. Nhánh xử lý Mock Payment: tạo đơn `pending`, mở trang Sandbox, gọi `mock_payment_success` $\to$ chuyển sang `paid`.
  7. Biên độ dài `full_name` (1 ký tự và 255 ký tự) và `phone` (1 ký tự và 20 ký tự).

- **Các nhánh và dòng lệnh CHƯA ĐƯỢC PHỦ (Missing / Uncovered) & Nguyên nhân:**
  1. *Nhánh ngoại lệ CSDL (`except Cart.DoesNotExist` tại dòng 41-42, 143-144, 166-167):* Trong luồng E2E bình thường, mỗi user đều có sẵn một bản ghi `Cart` trong CSDL nên khối `except` không được kích hoạt.
  2. *Nhánh xử lý giá trị thanh toán bất hợp pháp (dòng 69: `payment_method not in ['cod', 'qr', 'mock']`):* Bộ test BVA tập trung vào các giá trị biên hợp lệ của phương thức giao dịch, không gửi giá trị giả mạo (được bao phủ bởi test case EP TC-ORD-22).
  3. *Nhánh Mock Payment thất bại (dòng 174-178: `mock_payment_fail`):* Bộ test BVA thực thi luồng thành công; luồng thất bại thuộc về ca kiểm thử Bảng quyết định và Chuyển đổi trạng thái.
  4. *Nhánh Hủy đơn QR (dòng 191-197: `cancel_qr_order`) & Xem đơn chờ (dòng 182-186: `my_orders`):* Thuộc nghiệp vụ sau đặt hàng của máy trạng thái (State Transition).
  5. *Phương thức mô hình (`can_change_to`, `allowed_next_statuses`, `is_final` trong `models.py`):* Được sử dụng chủ yếu tại giao diện Quản trị viên (`admin_panel`) khi duyệt đổi trạng thái đơn.

---

## 9. Bộ Kiểm thử API Tự động Postman Collection
Toàn bộ các ca kiểm thử BVA và EP trong tài liệu này (từ `TC-ORD-06` đến `TC-ORD-22`) đã được đóng gói hoàn chỉnh thành các API Request tự động trong nhóm thư mục `01_EP_and_BVA` thuộc bộ Postman Collection:
- **Định dạng Postman Local:** `postman/collections/Green Shop - Orders/01_EP_and_BVA/`
- **Định dạng JSON Import:** `postman/Green_Shop_Orders_Payment_FR4.postman_collection.json`
- Chi tiết mô tả, cấu trúc request, script kiểm thử tự động `pm.test` và hướng dẫn chạy kiểm thử tự động với Newman CLI được trình bày chi tiết tại [TestCase_FR4_Orders_StateTransition_DecisionTable.md](file:///C:/Users/TOSHIBA/Desktop/DUAN/KCPM/Kiem-chung-phan-mem/docs/TestCase_FR4_Orders_StateTransition_DecisionTable.md#phan-c-bo-kiem-thu-postman-collection-api-automation-testing).

---

## 10. Báo cáo Kiểm thử Hộp trắng (White-box Testing) & Độ phủ Tối đa 100%
Nhằm giải quyết triệt để các nhánh chưa phủ đã nêu tại mục 8.3 (bao gồm các ngoại lệ CSDL `Cart.DoesNotExist`, các nhánh rẽ điều kiện ghép và các phương thức `__str__` của mô hình), toàn bộ phần Kiểm thử Hộp trắng đã được thiết kế và bổ sung hoàn chỉnh tại tài liệu chuyên đề:
- **Tài liệu chi tiết:** [TestCase_FR4_Orders_WhiteBox.md](file:///C:/Users/TOSHIBA/Desktop/DUAN/KCPM/Kiem-chung-phan-mem/docs/TestCase_FR4_Orders_WhiteBox.md)
- **Nội dung bao gồm:**
  1. Phân tích Đồ thị luồng điều khiển (CFG) & Độ phức tạp Cyclomatic $V(G) = E - N + 2 = P + 1 = R = 13$ cho hàm `checkout` và $V(G) = 3$ cho `confirm_qr_paid`.
  2. Bảng 26 ca kiểm thử White-box bao phủ Statement Coverage, Branch Coverage và MC/DC.
  3. Thư mục Postman `05_White_Box_Coverage` (18 API requests `.request.yaml` tự động).
  4. Bộ Unit Test `WhiteBoxCoverageTests` trong `orders/tests.py` (26 tests).
  5. **Kết quả đo độ phủ thực tế từ `coverage.py`:** `orders/views.py` đạt **100% Statement Coverage (122/122)** và **100% Branch Coverage (38/38)**; `orders/models.py` đạt **100% Statement Coverage (41/41)**; toàn bộ 106 tests PASS 100%.

