# KIỂM THỬ HỘP TRẮNG – FR3: GIỎ HÀNG (Control Flow Testing)

| Thuộc tính | Chi tiết |
| :--- | :--- |
| Phân hệ | Quản lý giỏ hàng (FR3) – [`cart/views.py`](../cart/views.py) |
| Người thực hiện | Lê Bá Hoài Phong |
| Kỹ thuật | Chương 4, IV.4 – Control Flow Testing: đồ thị luồng điều khiển, độ phức tạp Cyclomatic, bao phủ câu lệnh, bao phủ nhánh, bao phủ điều kiện / nhánh – điều kiện / tổ hợp điều kiện |
| Chức năng | PHẦN 1: Thêm sản phẩm vào giỏ (`cart_add`) · PHẦN 2: Giảm số lượng (`cart_decrease`) – cả 2 đã kiểm thử hộp đen ở [`TestCase_FR3_Cart_EP_BVA.md`](TestCase_FR3_Cart_EP_BVA.md) |
| Mã nguồn kiểm thử | [`cart/tests_whitebox.py`](../cart/tests_whitebox.py) – 4 bộ test, 10 lần chạy |
| Report | Sheet `WhiteBox_Phong` trong [`Report.xlsx`](Report.xlsx) |
| Kết quả | **10/10 PASS**. `cart_add`: câu lệnh 9/9, nhánh 4/4. `cart_decrease`: câu lệnh 8/8, nhánh 2/2 |

Mọi số độ phủ dưới đây đo bằng `coverage.py --branch`, tính riêng trong thân từng hàm (bỏ dòng `def` và decorator).

---

# PHẦN 1 – Thêm sản phẩm vào giỏ: `cart_add` (views.py dòng 16–32)

```python
16  def cart_add(request, product_id):
17      if not request.user.is_authenticated:
18          return redirect(f"/accounts/login/?next=/cart/add/{product_id}/")
20      product = get_object_or_404(Product, id=product_id)
21      cart = get_user_cart(request.user)
23      cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
28      if not created and cart_item.quantity < MAX_QUANTITY:
29          cart_item.quantity += 1
30          cart_item.save()
32      return redirect('cart_detail')
```

## I. Đồ thị luồng điều khiển

<img src="img/cfg/cfg_cart_add.png" alt="CFG cart_add" width="250">

| Nút | Dòng code | Nội dung | Loại nút |
| :---: | :---: | :--- | :---: |
| 1 | 17 | D1: `if not request.user.is_authenticated` | Điều kiện |
| 2 | 18 | `return redirect("/accounts/login/?next=/cart/add/<id>/")` | Lệnh |
| 3 | 20–26 | Lấy sản phẩm (404 nếu không có), lấy giỏ của user, `get_or_create` dòng giỏ → `(cart_item, created)` | Lệnh |
| 4 | 28 | D2: `if not created` (A) `and cart_item.quantity < MAX_QUANTITY` (B) | Điều kiện |
| 5 | 29–30 | `cart_item.quantity += 1; cart_item.save()` | Lệnh |
| 6 | 32 | `return redirect('cart_detail')` | Lệnh |
| 7 | – | Kết thúc | Kết thúc |

`get_object_or_404` (dòng 20) và `get_or_create` (dòng 23) là lời gọi hàm của Django, không phải lệnh `if` trong hàm, nên được gộp vào nút lệnh 3.

## II. Độ phức tạp Cyclomatic

| Công thức | Thay số | V(G) |
| :--- | :--- | :---: |
| V(G) = E − N + 2 | E = 8 cạnh, N = 7 nút → 8 − 7 + 2 | 3 |
| V(G) = P + 1 | P = 2 nút điều kiện (D1, D2) → 2 + 1 | 3 |
| V(G) = R | R = 2 miền kín + 1 miền ngoài | 3 |

## III. Bao phủ câu lệnh (Statement coverage)

1. **Có bao nhiêu câu lệnh?** → 9 câu lệnh: dòng 17, 18, 20, 21, 23, 28, 29, 30, 32
2. **Test case TC-CART-EP-04 (đã đăng nhập, giỏ rỗng, thêm A) bao phủ bao nhiêu % câu lệnh?** → 6/9 = 66,7% (đi qua nút 1-3-4-6-7; thiếu dòng 18, 29, 30)
   **Test case TC-CART-EP-01 (chưa đăng nhập, thêm A) bao phủ bao nhiêu % câu lệnh?** → 2/9 = 22,2% (đi qua nút 1-2-7)
3. **Tối thiểu bao nhiêu test case để bao phủ 100% câu lệnh?** → 2 test case. Nhánh True của D1 kết thúc hàm ngay bằng `return`, nên 1 test case không thể chạy cả dòng 18 lẫn các dòng 20–32.

| Test case | Input (`GET /cart/add/<id>/`) | Đường đi (nút) | Câu lệnh phủ | Expected output | Unit test | Kết quả |
| :---: | :--- | :---: | :---: | :--- | :--- | :---: |
| WB-ADD-S1 | Chưa đăng nhập; thêm A | 1-2-7 | 2/9 | 302 → `/accounts/login/?next=/cart/add/<A>/`, không tạo CartItem | `CartAddStatementTests.test_wb_add_s1_chua_dang_nhap` | PASS |
| WB-ADD-S2 | Đã đăng nhập; giỏ có A × 1; thêm A | 1-3-4-5-6-7 | 8/9 | 302 → `/cart/`, A có quantity = 2 | `CartAddStatementTests.test_wb_add_s2_san_pham_da_co_trong_gio` | PASS |
| **Tổng** | | | **9/9 = 100%** | Đo được: câu lệnh 9/9 = 100%, nhánh 3/4 = 75%. Nhánh chưa chạy: 28→32 (nhánh False của D2) | | |

## IV. Bao phủ nhánh (Decision/Branch coverage)

1. **Có bao nhiêu nhánh?** → 4 nhánh = 2 nút điều kiện × 2 (True, False)
2. **Test case TC-CART-EP-04 bao phủ bao nhiêu % nhánh?** → 2/4 = 50% (D1 F, D2 F)
   **Test case TC-CART-EP-01 bao phủ bao nhiêu % nhánh?** → 1/4 = 25% (D1 T)
3. **Tối thiểu bao nhiêu test case để bao phủ 100% nhánh?** → 3 test case. D1 T kết thúc hàm ngay nên cần 1 test riêng; khi D1 F, hai nhánh D2 T và D2 F cần 2 lần chạy khác nhau.

| Nhánh | Ý nghĩa | WB-ADD-S1 | WB-ADD-S2 | WB-ADD-B3 |
| :---: | :--- | :---: | :---: | :---: |
| D1 T / D1 F | Chưa / đã đăng nhập | T | F | F |
| D2 T / D2 F | Tăng / không tăng số lượng | – | T | F |
| Số nhánh phủ | | 1/4 | 2/4 | 2/4 |

| Test case | Input (`GET /cart/add/<id>/`) | Đường đi (nút) | Nhánh phủ | Expected output | Unit test | Kết quả |
| :---: | :--- | :---: | :---: | :--- | :--- | :---: |
| WB-ADD-S1 | Chưa đăng nhập; thêm A | 1-2-7 | 1/4 | 302 → trang đăng nhập, không tạo CartItem | `CartAddBranchTests.test_wb_add_s1_chua_dang_nhap` | PASS |
| WB-ADD-S2 | Đã đăng nhập; giỏ có A × 1; thêm A | 1-3-4-5-6-7 | 2/4 | A có quantity = 2 | `CartAddBranchTests.test_wb_add_s2_san_pham_da_co_trong_gio` | PASS |
| WB-ADD-B3 | Đã đăng nhập; giỏ rỗng; thêm A | 1-3-4-6-7 | 2/4 | A được thêm với quantity = 1 | `CartAddBranchTests.test_wb_add_b3_gio_rong` | PASS |
| **Tổng** | | | **4/4 = 100%** | Đo được: câu lệnh 9/9 = 100%, nhánh 4/4 = 100% | | |

## V. Bao phủ điều kiện cho nút điều kiện ghép D2

A = `not created` (sản phẩm đã có trong giỏ), B = `cart_item.quantity < MAX_QUANTITY` (chưa đạt 2.147.483.647).

- **Bao phủ điều kiện:** A và B đều phải nhận T và F. Chỉ cần WB-ADD-C2 (A T, B F) và WB-ADD-C3 (A F, B T) là đủ, nhưng cả hai đều cho D2 = F nên không bao phủ nhánh.
- **Bao phủ nhánh – điều kiện:** thêm WB-ADD-C1 (A T, B T → D2 T) → 3 test WB-ADD-C1, C2, C3.
- **Bao phủ tổ hợp điều kiện:** có 4 tổ hợp, nhưng A F – B F không xảy ra được vì dòng giỏ vừa tạo luôn có quantity = 1 < MAX. Còn 3 tổ hợp khả thi → 3 test case.
- Bao phủ nhánh không bắt buộc thử A T – B F (sản phẩm đã ở số lượng tối đa). Đây chính là trường hợp của lỗi **BUG-CART-01**: trước khi sửa, thêm sản phẩm đang có 2.147.483.647 sẽ lưu 2.147.483.648.

| Test case | A | B | D2 | Input | Expected output | Kết quả |
| :---: | :---: | :---: | :---: | :--- | :--- | :---: |
| WB-ADD-C1 | T | T | T | Giỏ có A × 1; thêm A | quantity = 2 | PASS |
| WB-ADD-C2 | T | F | F | Giỏ có A × 2.147.483.647; thêm A | Giữ quantity = 2.147.483.647, không lỗi | PASS |
| WB-ADD-C3 | F | (T) | F | Giỏ rỗng; thêm A | A được thêm với quantity = 1 | PASS |
| – | F | F | – | Không khả thi | – | – |

(T): Python không xét B vì A đã sai (toán tử `and` ngắt mạch); nếu được xét, B nhận T vì dòng mới có quantity = 1. Unit test: `CartAddConditionTests.test_c1_a_dung_b_dung`, `test_c2_a_dung_b_sai`, `test_c3_a_sai`.

## VI. Kết luận

| Độ phức tạp Cyclomatic | Số test nhỏ nhất: Statement coverage | Số test nhỏ nhất: Branch coverage | Tổ hợp điều kiện (D2) |
| :---: | :---: | :---: | :---: |
| 3 | 2 | 3 | 3 (khả thi) |

- So sánh: 33 TC EP/BVA hộp đen ([`cart/tests.py`](../cart/tests.py)) cũng đạt 100% câu lệnh và 100% nhánh của `cart_add`, còn bộ hộp trắng chỉ cần 3 test chọn theo nhánh để đạt cùng mức.
- Độ phủ phụ thuộc cách chọn test case, không phụ thuộc số lượng. Độ bao phủ 100% cũng không có nghĩa là đã test 100%: 3 test phủ nhánh không có trường hợp A T – B F của BUG-CART-01, phải thêm bao phủ điều kiện (WB-ADD-C2) mới kiểm tra được.

---

# PHẦN 2 – Giảm số lượng: `cart_decrease` (views.py dòng 57–70)

```python
57  @login_required(login_url='login')
58  def cart_decrease(request, product_id):
59      cart = get_user_cart(request.user)
60      product = get_object_or_404(Product, id=product_id)
62      cart_item = get_object_or_404(CartItem, cart=cart, product=product)
63      cart_item.quantity -= 1
65      if cart_item.quantity <= 0:
66          cart_item.delete()
67      else:
68          cart_item.save()
70      return redirect('cart_detail')
```

## I. Đồ thị luồng điều khiển

<img src="img/cfg/cfg_cart_decrease.png" alt="CFG cart_decrease" width="190">

| Nút | Dòng code | Nội dung | Loại nút |
| :---: | :---: | :--- | :---: |
| 1 | 59–63 | Lấy giỏ, lấy sản phẩm và dòng giỏ (404 nếu không có); `cart_item.quantity -= 1` | Lệnh |
| 2 | 65 | D1: `if cart_item.quantity <= 0` | Điều kiện |
| 3 | 66 | `cart_item.delete()` – xóa sản phẩm khỏi giỏ | Lệnh |
| 4 | 68 | `cart_item.save()` – lưu số lượng mới | Lệnh |
| 5 | 70 | `return redirect('cart_detail')` | Kết thúc |

`@login_required` (dòng 57) chặn khách chưa đăng nhập trước khi vào hàm, nên không nằm trong đồ thị của hàm.

## II. Độ phức tạp Cyclomatic

| Công thức | Thay số | V(G) |
| :--- | :--- | :---: |
| V(G) = E − N + 2 | E = 5 cạnh, N = 5 nút → 5 − 5 + 2 | 2 |
| V(G) = P + 1 | P = 1 nút điều kiện (D1) → 1 + 1 | 2 |
| V(G) = R | R = 1 miền kín + 1 miền ngoài | 2 |

## III. Bao phủ câu lệnh (Statement coverage)

1. **Có bao nhiêu câu lệnh?** → 8 câu lệnh: dòng 59, 60, 62, 63, 65, 66, 68, 70
2. **Test case TC-CART-BVA-07 (giỏ có A × 1, giảm A) bao phủ bao nhiêu % câu lệnh?** → 7/8 = 87,5% (đi qua nút 1-2-3-5; thiếu dòng 68)
   **Test case TC-CART-BVA-08 (giỏ có A × 2, giảm A) bao phủ bao nhiêu % câu lệnh?** → 7/8 = 87,5% (đi qua nút 1-2-4-5; thiếu dòng 66)
3. **Tối thiểu bao nhiêu test case để bao phủ 100% câu lệnh?** → 2 test case. Nhánh `if` (dòng 66) và nhánh `else` (dòng 68) đều có lệnh riêng nên 1 test case không đủ.

| Test case | Input (`GET /cart/decrease/<id>/`) | Đường đi (nút) | Câu lệnh phủ | Expected output | Unit test | Kết quả |
| :---: | :--- | :---: | :---: | :--- | :--- | :---: |
| WB-DEC-S1 | Đã đăng nhập; giỏ có A × 1; giảm A | 1-2-3-5 | 7/8 | 302 → `/cart/`, A bị xóa khỏi giỏ | `CartDecreaseStatementTests.test_wb_dec_s1_so_luong_1_bi_xoa` | PASS |
| WB-DEC-S2 | Đã đăng nhập; giỏ có A × 2; giảm A | 1-2-4-5 | 7/8 | 302 → `/cart/`, A còn quantity = 1 | `CartDecreaseStatementTests.test_wb_dec_s2_so_luong_2_con_1` | PASS |
| **Tổng** | | | **8/8 = 100%** | Đo được: câu lệnh 8/8 = 100%, nhánh 2/2 = 100% | | |

## IV. Bao phủ nhánh (Decision/Branch coverage)

1. **Có bao nhiêu nhánh?** → 2 nhánh = 1 nút điều kiện × 2 (True, False)
2. **Test case TC-CART-BVA-07 bao phủ bao nhiêu % nhánh?** → 1/2 = 50% (D1 T)
3. **Tối thiểu bao nhiêu test case để bao phủ 100% nhánh?** → 2 test case: WB-DEC-S1 (D1 T) và WB-DEC-S2 (D1 F) ở bảng trên.

## V. Bao phủ điều kiện

D1 chỉ có 1 điều kiện đơn (`quantity <= 0`, sau khi đã trừ 1), không có điều kiện ghép. Vì vậy bao phủ điều kiện, bao phủ nhánh – điều kiện và bao phủ tổ hợp điều kiện đều trùng với bao phủ nhánh: điều kiện nhận T ở WB-DEC-S1 và F ở WB-DEC-S2.

| Test case | quantity <= 0 | D1 | Input | Expected output | Kết quả |
| :---: | :---: | :---: | :--- | :--- | :---: |
| WB-DEC-S1 | T (1 − 1 = 0) | T | Giỏ có A × 1; giảm A | A bị xóa khỏi giỏ | PASS |
| WB-DEC-S2 | F (2 − 1 = 1) | F | Giỏ có A × 2; giảm A | A còn quantity = 1 | PASS |

## VI. Kết luận

| Độ phức tạp Cyclomatic | Số test nhỏ nhất: Statement coverage | Số test nhỏ nhất: Branch coverage | Tổ hợp điều kiện (D1) |
| :---: | :---: | :---: | :---: |
| 2 | 2 | 2 | 2 |

- So sánh: 2 TC BVA hộp đen TC-CART-BVA-07 và TC-CART-BVA-08 (giảm từ 1 và từ 2) đi đúng 2 nhánh của D1, nên riêng 2 TC này đã đạt 100% câu lệnh và 100% nhánh của `cart_decrease`.
- Với điều kiện đơn, chọn giá trị biên quanh điểm quyết định (quantity = 1 và 2) cũng chính là chọn test theo nhánh.

---

# Cách chạy và đo độ phủ

```bash
# Chạy toàn bộ test hộp trắng
python manage.py test cart.tests_whitebox -v 2

# Đo độ phủ một bộ test, tính riêng cho 1 hàm
coverage erase
coverage run --branch --source=cart manage.py test cart.tests_whitebox.<TênClass>
coverage json -o coverage.json
python tools/build_cart_whitebox_report.py --measure coverage.json cart_add      # hoặc cart_decrease

# Tạo lại sheet WhiteBox_Phong và ảnh CFG (đóng Report.xlsx trước)
python tools/build_cart_whitebox_report.py
```

| Class | Số test | Trả lời câu hỏi |
| :--- | :---: | :--- |
| `CartAddStatementTests` | 2 | Tối thiểu bao nhiêu test để phủ 100% câu lệnh của `cart_add` |
| `CartAddBranchTests` | 3 (kế thừa 2 test trên + 1) | Tối thiểu bao nhiêu test để phủ 100% nhánh của `cart_add` |
| `CartAddConditionTests` | 3 | Bao phủ nhánh – điều kiện / tổ hợp điều kiện của D2 |
| `CartDecreaseStatementTests` | 2 | Tối thiểu bao nhiêu test để phủ 100% câu lệnh và nhánh của `cart_decrease` |
