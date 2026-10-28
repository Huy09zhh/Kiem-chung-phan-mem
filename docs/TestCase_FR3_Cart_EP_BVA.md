# KIỂM THỬ HỘP ĐEN – FR3: PHÂN HỆ QUẢN LÝ GIỎ HÀNG

| Thông tin | Chi tiết |
| :--- | :--- |
| Hệ thống | Green Shop |
| Phân hệ | FR3 – Quản lý giỏ hàng (UC03) |
| Người thực hiện | Lê Bá Hoài Phong |
| Kỹ thuật | Phân hoạch tương đương (Equivalence Partitioning), Phân tích giá trị biên (Boundary Value Analysis) |
| Công cụ thực thi | Django TestCase – [`cart/tests.py`](../cart/tests.py) |
| Ngày thực thi | 27/10/2026 |

---

## 1. Functional Requirements (trích SRS mục 3.3 & UC03)

| Mã FR | Tên | Mô tả | Endpoint |
| :---: | :--- | :--- | :--- |
| FR3.1 | Thêm SP vào giỏ | Chưa đăng nhập → chuyển login với `next=/cart/add/{id}/`. SP đã có → `quantity + 1`; chưa có → tạo `CartItem` với `quantity = 1`. | `GET /cart/add/<product_id>/` |
| FR3.2 | Xem giỏ & tính tiền | Hiển thị SP, đơn giá, số lượng, thành tiền và `Total = Σ(price × quantity)`. Giỏ rỗng → *"Giỏ hàng của bạn đang trống"*, ẩn nút đặt hàng. | `GET /cart/` |
| FR3.3 | Tăng / giảm số lượng | (+) `quantity + 1`. (−) `quantity − 1`; nếu `quantity <= 0` thì xóa SP khỏi giỏ. | `GET /cart/increase/<id>/`, `GET /cart/decrease/<id>/` |
| FR3.4 | Xóa SP khỏi giỏ | Xóa hẳn `CartItem`, không phụ thuộc số lượng. | `GET /cart/remove/<id>/` |
| BR03.1 | Giỏ theo tài khoản | Giỏ hàng gắn 1-1 với user; user khác không xem/sửa được. | – |

---

## 2. Xác định đầu vào (Input)

| # | Biến đầu vào | Miền giá trị | Ghi chú |
| :---: | :--- | :--- | :--- |
| 1 | Trạng thái đăng nhập | {Đã đăng nhập, Khách} | Session cookie |
| 2 | `product_id` | Số nguyên trên URL | Khóa chính `Product.id` |
| 3 | SP có trong giỏ? | {Có, Không} | Áp dụng cho increase / decrease / remove |
| 4 | `quantity` hiện tại | Số nguyên ≥ 1 | Áp dụng cho increase / decrease |
| 5 | Số SP trong giỏ | Số nguyên ≥ 0 | Áp dụng cho xem giỏ / tổng tiền |

---

## 3. Bảng phân hoạch tương đương (EP)

| Điều kiện đầu vào | Lớp hợp lệ | Lớp không hợp lệ |
| :--- | :--- | :--- |
| Trạng thái đăng nhập | **V1**: Đã đăng nhập | **I1**: Chưa đăng nhập (khách) → chuyển `/accounts/login/` |
| `product_id` | **V2**: Số nguyên dương, SP tồn tại | **I2**: Số nguyên dương, SP không tồn tại → 404<br>**I3**: Số âm (`-1`) → 404<br>**I4**: Không phải số (`abc`) → 404 |
| SP đã có trong giỏ khi **thêm** | **V3**: Chưa có → tạo mới `quantity = 1`<br>**V4**: Đã có → `quantity + 1` | – |
| SP có trong giỏ khi **tăng / giảm** | **V5**: Có trong giỏ | **I5**: Không có trong giỏ → 404 |
| SP có trong giỏ khi **xóa** | **V6**: Có → xóa hẳn<br>**V7**: Không có → 302, không lỗi | – |
| Số SP trong giỏ | **V8**: = 0 → thông báo giỏ trống<br>**V9**: ≥ 1 → hiển thị tổng tiền | – |
| Chủ sở hữu giỏ | **V10**: Đúng user | **I6**: User khác → không thấy, tăng bị 404 |

---

## 4. Bảng phân tích giá trị biên (BVA)

| Biến | Biên | Giá trị kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- | :--- |
| `product_id` (biên dưới) | `min_id` | `0` (min − 1, ngoài biên) | 404 |
| | | `min_id` (đúng biên) | Thêm thành công, `quantity = 1` |
| | | `min + 1` (id hợp lệ kế trên min) | Thêm thành công, `quantity = 1` |
| `product_id` (biên trên dữ liệu) | `max_id` | `max − 1` (id hợp lệ kế dưới max) | Thêm thành công, `quantity = 1` |
| | | `max_id` (đúng biên) | Thêm thành công, `quantity = 1` |
| | | `max_id + 1` (ngoài biên) | 404 |
| `product_id` (biên kiểu BIGINT) | 2⁶³ − 1 | `9223372036854775807` | 404 |
| | | `9223372036854775808` (tràn) | 404, **không được 500** |
| `quantity` khi giảm | biên xóa = 1 | `1` → 0 | SP bị xóa khỏi giỏ |
| | | `2` → 1 | Còn trong giỏ, `quantity = 1` |
| | | `3` → 2 | `quantity = 2` |
| `quantity` khi tăng | biên dưới = 1 | `1` → 2 | `quantity = 2` |
| `quantity` khi tăng | biên trên = 2.147.483.647 (giới hạn `PositiveIntegerField`) | `2147483646` → 2147483647 | `quantity = 2147483647` |
| | | `2147483647` → ? (vượt biên) | Không vượt 2147483647, không lỗi 500 |
| Số SP trong giỏ | 0 / 1 / 2 | 0 SP | Thông báo *"Giỏ hàng của bạn đang trống"* |
| | | 1 SP (A×1) | Tổng = 50.000 |
| | | 2 SP (A×2, B×1) | Tổng = 130.000 |

> Dữ liệu test: SP A *Bình nước tre* = 50.000đ, SP B *Túi vải canvas* = 30.000đ (thêm 2 SP phụ để `min + 1` và `max − 1` là 2 id khác nhau).
>
> SRS không quy định số lượng tối đa của 1 SP trong giỏ, nên biên trên của `quantity` lấy theo giới hạn kiểu dữ liệu `CartItem.quantity` (`PositiveIntegerField`: 0 → 2.147.483.647).

---

## 5. Test case & kết quả thực thi

### 5.1 Test case phân hoạch tương đương

| Mã TC | Lớp | Tiền điều kiện | Bước / Input | Kết quả mong đợi | Thực tế | KQ |
| :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| TC-CART-EP-01 | I1, V2 | Chưa đăng nhập | `GET /cart/add/{A}/` | 302 → `/accounts/login/?next=/cart/add/{A}/`, không tạo `CartItem` | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-02 | I1 | Chưa đăng nhập | `GET /cart/` | 302 → trang login | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-03 | I1 | Chưa đăng nhập | `GET /cart/increase/{A}/` | 302 → trang login | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-04 | V1, V2, V3 | Đăng nhập, giỏ rỗng | `GET /cart/add/{A}/` | 302 → `/cart/`, A có `quantity = 1` | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-05 | V1, V2, V4 | Giỏ có A×1 | `GET /cart/add/{A}/` | A có `quantity = 2`, vẫn 1 dòng | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-06 | I2 | Đăng nhập | `GET /cart/add/{max_id+100}/` | 404, không tạo `CartItem` | 404 | ✅ PASS |
| TC-CART-EP-07 | I3 | Đăng nhập | `GET /cart/add/-1/` | 404 | 404 | ✅ PASS |
| TC-CART-EP-08 | I4 | Đăng nhập | `GET /cart/add/abc/` | 404 | 404 | ✅ PASS |
| TC-CART-EP-09 | V5 | Giỏ có A×2 | `GET /cart/increase/{A}/` | A có `quantity = 3` | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-10 | I5 | Giỏ rỗng | `GET /cart/increase/{A}/` | 404 | 404 | ✅ PASS |
| TC-CART-EP-11 | I5 | Giỏ rỗng | `GET /cart/decrease/{A}/` | 404 | 404 | ✅ PASS |
| TC-CART-EP-12 | V6 | Giỏ có A×5 | `GET /cart/remove/{A}/` | 302, A bị xóa hẳn | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-13 | V7 | Giỏ rỗng | `GET /cart/remove/{A}/` | 302 → `/cart/`, không lỗi | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-14 | V8 | Giỏ rỗng | `GET /cart/` | 200, có *"Giỏ hàng của bạn đang trống"*, không có link checkout | Đúng như mong đợi | ✅ PASS |
| TC-CART-EP-15 | I6 | user1 có A×1; đăng nhập user2 | `GET /cart/`, `GET /cart/increase/{A}/` | user2 không thấy A; increase → 404; A của user1 vẫn = 1 | Đúng như mong đợi | ✅ PASS |

### 5.2 Test case giá trị biên

| Mã TC | Biến | Input | Kết quả mong đợi | Thực tế | KQ |
| :--- | :--- | :--- | :--- | :--- | :---: |
| TC-CART-BVA-01 | `product_id` | `0` | 404 | 404 | ✅ PASS |
| TC-CART-BVA-02 | `product_id` | `min_id` | Thêm thành công, `quantity = 1` | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-03 | `product_id` | `max_id` | Thêm thành công, `quantity = 1` | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-04 | `product_id` | `max_id + 1` | 404 | 404 | ✅ PASS |
| TC-CART-BVA-05 | `product_id` | `9223372036854775807` | 404 | 404 | ✅ PASS |
| TC-CART-BVA-06 | `product_id` | `9223372036854775808` cho cả add / increase / decrease / remove | 404, không 500 | 404 cả 4 endpoint | ✅ PASS |
| TC-CART-BVA-07 | `quantity` giảm | A×1 → decrease | A bị xóa khỏi giỏ | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-08 | `quantity` giảm | A×2 → decrease | `quantity = 1`, còn trong giỏ | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-09 | `quantity` giảm | A×3 → decrease | `quantity = 2` | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-10 | `quantity` tăng | A×1 → increase | `quantity = 2` | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-11 | Số SP = 1 | A×1 → `GET /cart/` | `total_price = 50.000` | 50.000 | ✅ PASS |
| TC-CART-BVA-12 | Số SP = 2 | A×2, B×1 → `GET /cart/` | `total_price = 130.000` | 130.000 | ✅ PASS |
| TC-CART-BVA-13 | Số SP 1 → 0 | A×1 → remove → `GET /cart/` | Thông báo giỏ trống | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-14 | `product_id` | `min + 1` | Thêm thành công, `quantity = 1` | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-15 | `product_id` | `max − 1` | Thêm thành công, `quantity = 1` | Đúng như mong đợi | ✅ PASS |
| TC-CART-BVA-16 | `quantity` tăng | A×2147483646 → increase | `quantity = 2147483647` | 2147483647 | ✅ PASS |
| TC-CART-BVA-17 | `quantity` tăng | A×2147483647 → increase | Không vượt 2147483647, không 500 | Trước fix: lưu `2147483648` ❌ · Sau fix: giữ `2147483647` | ✅ PASS (sau fix) |
| TC-CART-BVA-18 | `quantity` thêm | A×2147483647 → add | Không vượt 2147483647, không 500 | Trước fix: lưu `2147483648` ❌ · Sau fix: giữ `2147483647` | ✅ PASS (sau fix) |

> TC-CART-BVA-16 → 18 chỉ chạy bằng Django TestCase (không thể bấm "+" 2 tỷ lần bằng Postman).

**Bug phát hiện – BUG-CART-01 (đã fix):** `cart_increase` và `cart_add` cộng `quantity += 1` không kiểm tra giới hạn. Khi `quantity = 2147483647`, hệ thống lưu `2147483648`, vượt miền giá trị `PositiveIntegerField` (SQLite lưu im lặng dữ liệu sai; PostgreSQL/MySQL dự kiến báo lỗi integer out of range).

*Cách sửa* ([`cart/views.py`](../cart/views.py)): thêm hằng `MAX_QUANTITY = 2147483647`; `cart_add` và `cart_increase` chỉ tăng khi `quantity < MAX_QUANTITY`, đạt giới hạn thì giữ nguyên và quay về giỏ hàng. Kiểm thử hồi quy: BVA-17, BVA-18 FAIL trước fix → PASS sau fix; các TC còn lại vẫn PASS.

---

## 6. Tổng kết

| Kỹ thuật | Số TC | Số lần chạy (gồm sub-test) | PASS | FAIL |
| :--- | :---: | :---: | :---: | :---: |
| Phân hoạch tương đương | 15 | 15 | 15 | 0 |
| Giá trị biên | 18 | 21 (BVA-06 chạy 4 endpoint) | 18 | 0 |
| **Tổng** | **33** | **36** | **33** | **0** |

> Kết quả sau khi fix BUG-CART-01. Trước fix: 31 PASS, 2 FAIL (BVA-17, BVA-18).

**Nhận xét:**
- Phân hệ giỏ hàng đáp ứng đúng FR3.1 – FR3.4 và BR03.1 với mọi lớp tương đương và giá trị biên đã chọn.
- Kiểm thử giá trị biên phát hiện BUG-CART-01 (`quantity` vượt giới hạn kiểu dữ liệu tại biên trên), đã fix và kiểm thử hồi quy PASS.
- `product_id` vượt giới hạn BIGINT không gây lỗi 500 (Django 6 trả về rỗng cho giá trị ngoài miền số nguyên).
- Ngoài phạm vi EP/BVA: các endpoint giỏ hàng đổi dữ liệu bằng `GET` (đã được ghi nhận ở BUG-17 trong collection Postman `GreenShop-ShoppingCart`).
- SRS không quy định số lượng tối đa của một SP trong giỏ; nên bổ sung giới hạn này vào SRS.

---

## 7. Thực thi

### 7.1 Django TestCase

```bash
python manage.py test cart -v 2
```

Trước fix:

```text
FAIL: test_bva_17_increase_above_qty_max
FAIL: test_bva_18_add_above_qty_max
AssertionError: 2147483648 not less than or equal to 2147483647

Ran 33 tests in 1.499s

FAILED (failures=2)
```

Sau fix:

```text
Ran 33 tests in 1.537s

OK
```

### 7.2 Postman / Newman

Collection: `postman/collections/Green Shop - Shopping Cart (EP-BVA)/` (bản export: `postman/GreenShop-ShoppingCart-EP-BVA.postman_collection.json`).

| Folder | Nội dung |
| :--- | :--- |
| 00. Chuẩn bị | Lấy cookie `csrftoken`, đăng xuất phiên cũ, lấy `min_id`, `max_id`, id và giá SP A/B từ `/products/api/` |
| 01. Phân hoạch tương đương | TC-CART-EP-01 → 15 |
| 02. Giá trị biên | TC-CART-BVA-01 → 15 |

Request `[setup]` chỉ chuẩn bị dữ liệu; `TC-xx.1` thực hiện thao tác, `TC-xx.2` mở `/cart/` để kiểm tra số lượng / tổng tiền.

```bash
python manage.py shell -c "exec(open('postman/seed_test_data.py', encoding='utf-8').read())"
python manage.py runserver
cd postman
npx newman@6.2.1 run GreenShop-ShoppingCart-EP-BVA.postman_collection.json
```

```text
requests 84 | assertions 78 | failed 0
```
