"""Tạo report kiểm thử hộp trắng FR3 - Giỏ hàng: CFG, Phủ điều kiện / MC/DC, Kiểm thử vòng lặp.

Việc script làm:
  1. Chạy cart.tests_whitebox dưới coverage (--branch) để lấy kết quả + giá trị thực tế từng ca.
  2. Chạy toàn bộ test của app cart dưới coverage để so sánh độ phủ.
  3. Vẽ đồ thị luồng điều khiển (CFG) của từng hàm ra docs/img/cfg/*.png.
  4. Ghi (hoặc ghi đè) sheet "Phong_CFG_MCDC_Loop" trong docs/Report.xlsx.

Chạy (từ thư mục gốc dự án, đóng Report.xlsx trong Excel trước):
  .venv\\Scripts\\python.exe tools/build_cart_whitebox_report.py
"""
import datetime
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs' / 'Report.xlsx'
IMG_DIR = ROOT / 'docs' / 'img' / 'cfg'
SHEET = 'Phong_CFG_MCDC_Loop'
OMIT = 'cart/tests*,cart/migrations/*,cart/management/*'

# ---------------------------------------------------------------------------
# Dữ liệu CFG: nút, cạnh, vị trí vẽ (đơn vị lưới) và các đường cơ sở
#   kind: stmt = khối lệnh, dec = quyết định, imp = quyết định ẩn của Django, exit = nút ra
#   edge: (từ, đến, nhãn, các điểm gấp khúc)
# ---------------------------------------------------------------------------
LOGIN = 'Đăng nhập (force_login)'
CFGS = [
    {
        'key': 'guc', 'func': 'get_user_cart', 'loc': 'cart/views.py:11-13',
        'nodes': [
            ('1', 'stmt', (1, 0), 'L12-13', '12-13', 'cart, created = Cart.objects.get_or_create(user=user); return cart', 'Khối lệnh'),
            ('E', 'exit', (1, 1), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [('1', 'E', '', [])],
        'paths': [
            ('WB-CFG-GUC-P1', '1 → E', 'Không có quyết định', 'User chưa có Cart; gọi get_user_cart 2 lần',
             'Lần 1 tạo Cart, lần 2 trả lại đúng Cart đó; user chỉ có 1 Cart', 'test_cfg_guc_p1_get_or_create_once',
             'Mọi ca đã đăng nhập (vd. TC-CART-EP-04)'),
        ],
    },
    {
        'key': 'add', 'func': 'cart_add', 'loc': 'cart/views.py:16-32',
        'nodes': [
            ('1', 'dec', (1, 0), 'L17', '17', 'if not request.user.is_authenticated', 'Quyết định D1'),
            ('2', 'stmt', (2.4, 0), 'L18', '18', 'return redirect("/accounts/login/?next=/cart/add/<id>/")', 'Khối lệnh (thoát sớm)'),
            ('3', 'imp', (1, 1), 'L20', '20', 'product = get_object_or_404(Product, id=product_id)', 'Quyết định ẩn I2: T = SP tồn tại, F = Http404'),
            ('4', 'stmt', (1.9, 1), '404', '—', 'raise Http404 (Django trả mã 404)', 'Khối lệnh (thoát)'),
            ('5', 'stmt', (1, 2), 'L21-26', '21-26', 'cart = get_user_cart(...); cart_item, created = CartItem.objects.get_or_create(...)', 'Khối lệnh'),
            ('6', 'dec', (1, 3), 'L28·A', '28', 'not created  (điều kiện A của D2)', 'Quyết định D2 - điều kiện A'),
            ('7', 'dec', (1, 4), 'L28·B', '28', 'cart_item.quantity < MAX_QUANTITY  (điều kiện B của D2)', 'Quyết định D2 - điều kiện B'),
            ('8', 'stmt', (1, 5), 'L29-30', '29-30', 'cart_item.quantity += 1; cart_item.save()', 'Khối lệnh'),
            ('9', 'stmt', (1, 6), 'L32', '32', "return redirect('cart_detail')", 'Khối lệnh'),
            ('E', 'exit', (1, 7), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [
            ('1', '2', 'T', []), ('1', '3', 'F', []), ('2', 'E', '', [(2.4, 7)]),
            ('3', '4', 'F', []), ('3', '5', 'T', []), ('4', 'E', '', [(1.9, 7)]),
            ('5', '6', '', []), ('6', '7', 'T', []), ('6', '9', 'F', [(0.35, 3), (0.35, 6)]),
            ('7', '8', 'T', []), ('7', '9', 'F', [(0.65, 4), (0.65, 6)]), ('8', '9', '', []), ('9', 'E', '', []),
        ],
        'paths': [
            ('WB-CFG-ADD-P1', '1 → 2 → E', 'D1 = T (khách)', 'Khách, GET /cart/add/{A}/',
             '302 → /accounts/login/?next=...; không tạo CartItem', 'test_cfg_add_p1_guest', 'TC-CART-EP-01, DT-R1'),
            ('WB-CFG-ADD-P2', '1 → 3 → 4 → E', 'D1 = F; I2 = F', f'{LOGIN}, GET /cart/add/999999/',
             '404; không tạo CartItem', 'test_cfg_add_p2_missing_product', 'TC-CART-EP-06, BVA-01, DT-R2'),
            ('WB-CFG-ADD-P3', '1 → 3 → 5 → 6 → 9 → E', 'D1 = F; I2 = T; A = F (SP mới)', f'{LOGIN}, giỏ chưa có A, GET /cart/add/{{A}}/',
             '302 → /cart/; q = 1', 'test_cfg_add_p3_new_item', 'TC-CART-EP-04, DT-R3'),
            ('WB-CFG-ADD-P4', '1 → 3 → 5 → 6 → 7 → 8 → 9 → E', 'A = T; B = T', f'{LOGIN}, A×1, GET /cart/add/{{A}}/',
             '302 → /cart/; q = 2', 'test_cfg_add_p4_existing_below_max', 'TC-CART-EP-05, DT-R4'),
            ('WB-CFG-ADD-P5', '1 → 3 → 5 → 6 → 7 → 9 → E', 'A = T; B = F', f'{LOGIN}, A×2147483647, GET /cart/add/{{A}}/',
             '302 → /cart/; giữ q = 2147483647', 'test_cfg_add_p5_existing_at_max', 'TC-CART-BVA-18, DT-R5'),
        ],
    },
    {
        'key': 'rem', 'func': 'cart_remove', 'loc': 'cart/views.py:35-41',
        'nodes': [
            ('1', 'imp', (1, 0), '@login', '35', '@login_required(login_url="login")', 'Quyết định ẩn I1: T = đã đăng nhập'),
            ('2', 'stmt', (2.4, 0), 'login', '—', 'redirect /accounts/login/?next=...', 'Khối lệnh (thoát sớm)'),
            ('3', 'imp', (1, 1), 'L37-38', '37-38', 'cart = get_user_cart(...); product = get_object_or_404(Product, ...)', 'Quyết định ẩn I2'),
            ('4', 'stmt', (1.9, 1), '404', '—', 'raise Http404', 'Khối lệnh (thoát)'),
            ('5', 'stmt', (1, 2), 'L40-41', '40-41', "CartItem.objects.filter(cart, product).delete(); return redirect('cart_detail')", 'Khối lệnh'),
            ('E', 'exit', (1, 3), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [
            ('1', '2', 'F', []), ('1', '3', 'T', []), ('2', 'E', '', [(2.4, 3)]),
            ('3', '4', 'F', []), ('3', '5', 'T', []), ('4', 'E', '', [(1.9, 3)]), ('5', 'E', '', []),
        ],
        'paths': [
            ('WB-CFG-REM-P1', '1 → 2 → E', 'I1 = F (khách)', 'Khách, GET /cart/remove/{A}/',
             '302 → /accounts/login/?next=...', 'test_cfg_rem_p1_guest', 'DT-R16'),
            ('WB-CFG-REM-P2', '1 → 3 → 4 → E', 'I1 = T; I2 = F', f'{LOGIN}, GET /cart/remove/999999/',
             '404', 'test_cfg_rem_p2_missing_product', 'DT-R17'),
            ('WB-CFG-REM-P3', '1 → 3 → 5 → E', 'I1 = T; I2 = T', f'{LOGIN}, A×5, GET /cart/remove/{{A}}/',
             '302 → /cart/; A bị xóa khỏi giỏ', 'test_cfg_rem_p3_delete', 'TC-CART-EP-12, EP-13, DT-R18, DT-R19'),
        ],
    },
    {
        'key': 'inc', 'func': 'cart_increase', 'loc': 'cart/views.py:44-54',
        'nodes': [
            ('1', 'imp', (1, 0), '@login', '44', '@login_required(login_url="login")', 'Quyết định ẩn I1'),
            ('2', 'stmt', (2.4, 0), 'login', '—', 'redirect /accounts/login/?next=...', 'Khối lệnh (thoát sớm)'),
            ('3', 'imp', (1, 1), 'L46-47', '46-47', 'cart = get_user_cart(...); product = get_object_or_404(Product, ...)', 'Quyết định ẩn I2'),
            ('4', 'stmt', (1.9, 1.5), '404', '—', 'raise Http404 (dùng chung cho nút 3 và 5)', 'Khối lệnh (thoát)'),
            ('5', 'imp', (1, 2), '<L49', '49', 'cart_item = get_object_or_404(CartItem, cart=cart, product=product)', 'Quyết định ẩn I3: T = SP có trong giỏ'),
            ('6', 'dec', (1, 3), 'L50', '50', 'if cart_item.quantity < MAX_QUANTITY', 'Quyết định D3'),
            ('7', 'stmt', (1, 4), 'L51-52', '51-52', 'cart_item.quantity += 1; cart_item.save()', 'Khối lệnh'),
            ('8', 'stmt', (1, 5), 'L54', '54', "return redirect('cart_detail')", 'Khối lệnh'),
            ('E', 'exit', (1, 6), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [
            ('1', '2', 'F', []), ('1', '3', 'T', []), ('2', 'E', '', [(2.4, 6)]),
            ('3', '4', 'F', []), ('3', '5', 'T', []), ('5', '4', 'F', []), ('5', '6', 'T', []),
            ('4', 'E', '', [(1.9, 6)]), ('6', '7', 'T', []), ('6', '8', 'F', [(0.4, 3), (0.4, 5)]),
            ('7', '8', '', []), ('8', 'E', '', []),
        ],
        'paths': [
            ('WB-CFG-INC-P1', '1 → 2 → E', 'I1 = F', 'Khách, GET /cart/increase/{A}/',
             '302 → /accounts/login/?next=...', 'test_cfg_inc_p1_guest', 'TC-CART-EP-03, DT-R6'),
            ('WB-CFG-INC-P2', '1 → 3 → 4 → E', 'I1 = T; I2 = F', f'{LOGIN}, GET /cart/increase/999999/',
             '404', 'test_cfg_inc_p2_missing_product', 'DT-R7'),
            ('WB-CFG-INC-P3', '1 → 3 → 5 → 4 → E', 'I2 = T; I3 = F', f'{LOGIN}, giỏ chưa có A, GET /cart/increase/{{A}}/',
             '404; không tự tạo CartItem', 'test_cfg_inc_p3_not_in_cart', 'TC-CART-EP-10, DT-R8'),
            ('WB-CFG-INC-P4', '1 → 3 → 5 → 6 → 7 → 8 → E', 'I3 = T; D3 = T', f'{LOGIN}, A×2, GET /cart/increase/{{A}}/',
             '302 → /cart/; q = 3', 'test_cfg_inc_p4_below_max', 'TC-CART-EP-09, BVA-10, BVA-16, DT-R9'),
            ('WB-CFG-INC-P5', '1 → 3 → 5 → 6 → 8 → E', 'I3 = T; D3 = F', f'{LOGIN}, A×2147483647, GET /cart/increase/{{A}}/',
             '302 → /cart/; giữ q = 2147483647', 'test_cfg_inc_p5_at_max', 'TC-CART-BVA-17, DT-R10'),
        ],
    },
    {
        'key': 'dec', 'func': 'cart_decrease', 'loc': 'cart/views.py:57-70',
        'nodes': [
            ('1', 'imp', (1, 0), '@login', '57', '@login_required(login_url="login")', 'Quyết định ẩn I1'),
            ('2', 'stmt', (2.4, 0), 'login', '—', 'redirect /accounts/login/?next=...', 'Khối lệnh (thoát sớm)'),
            ('3', 'imp', (1, 1), 'L59-60', '59-60', 'cart = get_user_cart(...); product = get_object_or_404(Product, ...)', 'Quyết định ẩn I2'),
            ('4', 'stmt', (1.9, 1.5), '404', '—', 'raise Http404 (dùng chung cho nút 3 và 5)', 'Khối lệnh (thoát)'),
            ('5', 'imp', (1, 2), '<L62', '62', 'cart_item = get_object_or_404(CartItem, cart=cart, product=product)', 'Quyết định ẩn I3'),
            ('6', 'dec', (1, 3), 'L63-65', '63-65', 'cart_item.quantity -= 1; if cart_item.quantity <= 0', 'Quyết định D4'),
            ('7', 'stmt', (0.4, 4), '<L66', '66', 'cart_item.delete()', 'Khối lệnh'),
            ('8', 'stmt', (1.6, 4), 'L68', '68', 'cart_item.save()', 'Khối lệnh'),
            ('9', 'stmt', (1, 5), 'vL70', '70', "return redirect('cart_detail')", 'Khối lệnh'),
            ('E', 'exit', (1, 6), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [
            ('1', '2', 'F', []), ('1', '3', 'T', []), ('2', 'E', '', [(2.4, 6)]),
            ('3', '4', 'F', []), ('3', '5', 'T', []), ('5', '4', 'F', []), ('5', '6', 'T', []),
            ('4', 'E', '', [(1.9, 6)]), ('6', '7', 'T', []), ('6', '8', 'F', []),
            ('7', '9', '', []), ('8', '9', '', []), ('9', 'E', '', []),
        ],
        'paths': [
            ('WB-CFG-DEC-P1', '1 → 2 → E', 'I1 = F', 'Khách, GET /cart/decrease/{A}/',
             '302 → /accounts/login/?next=...', 'test_cfg_dec_p1_guest', 'DT-R11'),
            ('WB-CFG-DEC-P2', '1 → 3 → 4 → E', 'I1 = T; I2 = F', f'{LOGIN}, GET /cart/decrease/999999/',
             '404', 'test_cfg_dec_p2_missing_product', 'DT-R12'),
            ('WB-CFG-DEC-P3', '1 → 3 → 5 → 4 → E', 'I2 = T; I3 = F', f'{LOGIN}, giỏ chưa có A, GET /cart/decrease/{{A}}/',
             '404', 'test_cfg_dec_p3_not_in_cart', 'TC-CART-EP-11, DT-R13'),
            ('WB-CFG-DEC-P4', '1 → 3 → 5 → 6 → 7 → 9 → E', 'I3 = T; D4 = T', f'{LOGIN}, A×1, GET /cart/decrease/{{A}}/',
             '302 → /cart/; A bị xóa', 'test_cfg_dec_p4_quantity_one_deletes', 'TC-CART-BVA-07, DT-R14'),
            ('WB-CFG-DEC-P5', '1 → 3 → 5 → 6 → 8 → 9 → E', 'I3 = T; D4 = F', f'{LOGIN}, A×3, GET /cart/decrease/{{A}}/',
             '302 → /cart/; q = 2', 'test_cfg_dec_p5_quantity_above_one_saves', 'TC-CART-BVA-08, BVA-09, DT-R15'),
        ],
    },
    {
        'key': 'det', 'func': 'cart_detail', 'loc': 'cart/views.py:73-82',
        'nodes': [
            ('1', 'imp', (1, 0), '@login', '73', '@login_required(login_url="login")', 'Quyết định ẩn I1'),
            ('2', 'stmt', (2.2, 0), 'login', '—', 'redirect /accounts/login/?next=/cart/', 'Khối lệnh (thoát sớm)'),
            ('3', 'stmt', (1, 1), 'L75-76', '75-76', "cart = get_user_cart(...); cart_items = cart.items.select_related('product')", 'Khối lệnh'),
            ('4', 'dec', (1, 2), 'L77', '77', 'Vòng lặp sum(...): còn item tiếp theo?', 'Quyết định D7 (điều kiện vòng lặp L1)'),
            ('5', 'stmt', (0.35, 3), '<L77', '77', 'Cộng item.product.price * item.quantity', 'Thân vòng lặp'),
            ('6', 'stmt', (1, 3), 'L79-82', '79-82', "return render(request, 'cart/detail.html', {..., 'total_price': ...})", 'Khối lệnh'),
            ('E', 'exit', (1, 4), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [
            ('1', '2', 'F', []), ('1', '3', 'T', []), ('2', 'E', '', [(2.2, 4)]),
            ('3', '4', '', []), ('4', '5', 'T', []), ('5', '4', '', [(0.35, 2)]), ('4', '6', 'F', []), ('6', 'E', '', []),
        ],
        'paths': [
            ('WB-CFG-DET-P1', '1 → 2 → E', 'I1 = F', 'Khách, GET /cart/',
             '302 → /accounts/login/?next=/cart/', 'test_cfg_det_p1_guest', 'TC-CART-EP-02, DT-R20'),
            ('WB-CFG-DET-P2', '1 → 3 → 4 → 6 → E', 'D7 = F ngay lần đầu (0 lần lặp)', f'{LOGIN}, giỏ trống, GET /cart/',
             '200; total_price = 0; hiện "Giỏ hàng của bạn đang trống"', 'test_cfg_det_p2_empty_cart_skips_loop', 'TC-CART-EP-14, BVA-13, DT-R21'),
            ('WB-CFG-DET-P3', '1 → 3 → 4 → 5 → 4 → 6 → E', 'D7 = T rồi F (1 lần lặp)', f'{LOGIN}, A×2 (50.000đ), GET /cart/',
             '200; total_price = 100.000', 'test_cfg_det_p3_one_item_loop_once', 'TC-CART-BVA-11, DT-R22'),
        ],
    },
    {
        'key': 'cic', 'func': 'cart_item_count', 'loc': 'cart/context_processors.py:3-11',
        'nodes': [
            ('1', 'dec', (1, 0), 'L4', '4', 'if request.user.is_authenticated', 'Quyết định D5'),
            ('7', 'stmt', (2.4, 0), 'L11', '11', "return {'cart_item_count': 0}", 'Khối lệnh'),
            ('2', 'imp', (1, 1), 'L5-7', '5-7', 'try: request.user.cart  (ném Cart.DoesNotExist nếu chưa có Cart)', 'Quyết định D6 (ngoại lệ): T = có Cart'),
            ('6', 'stmt', (1.9, 1), 'L9-10', '9-10', "except Cart.DoesNotExist: return {'cart_item_count': 0}", 'Khối lệnh'),
            ('3', 'dec', (1, 2), 'L7', '7', 'Vòng lặp sum(...): còn item tiếp theo?', 'Quyết định D8 (điều kiện vòng lặp L2)'),
            ('4', 'stmt', (0.35, 3), '<L7', '7', 'Cộng item.quantity', 'Thân vòng lặp'),
            ('5', 'stmt', (1, 3), 'L6-8', '6-8', "return {'cart_item_count': tổng}", 'Khối lệnh'),
            ('E', 'exit', (1, 4), '', '—', 'Kết thúc hàm', 'Nút ra'),
        ],
        'edges': [
            ('1', '2', 'T', []), ('1', '7', 'F', []), ('7', 'E', '', [(2.4, 4)]),
            ('2', '3', 'T', []), ('2', '6', 'F', []), ('6', 'E', '', [(1.9, 4)]),
            ('3', '4', 'T', []), ('4', '3', '', [(0.35, 2)]), ('3', '5', 'F', []), ('5', 'E', '', []),
        ],
        'paths': [
            ('WB-CFG-CIC-P1', '1 → 7 → E', 'D5 = F (khách)', 'Khách, GET /',
             'cart_item_count = 0', 'test_cfg_cic_p1_guest', 'DT-R23'),
            ('WB-CFG-CIC-P2', '1 → 2 → 6 → E', 'D5 = T; D6 = F (DoesNotExist)', 'User mới chưa có Cart, GET /',
             'cart_item_count = 0; không lỗi 500, không tạo Cart', 'test_cfg_cic_p2_no_cart_row', 'DT-R24'),
            ('WB-CFG-CIC-P3', '1 → 2 → 3 → 5 → E', 'D6 = T; D8 = F (0 lần lặp)', 'User có Cart rỗng, GET /',
             'cart_item_count = 0', 'test_cfg_cic_p3_cart_without_items', 'TC-CART-EP-14'),
            ('WB-CFG-CIC-P4', '1 → 2 → 3 → 4 → 3 → 5 → E', 'D6 = T; D8 = T rồi F', 'User có A×2, B×3, GET /',
             'cart_item_count = 5', 'test_cfg_cic_p4_cart_with_items', 'DT-R25'),
        ],
    },
]

MODEL_PATHS = [
    ('WB-CFG-MOD-P1', 'Cart.__str__', 'cart/models.py:10-11', 'Cart của user "cartuser"', '"Cart - cartuser"', 'test_cfg_mod_p1_cart_str'),
    ('WB-CFG-MOD-P2', 'CartItem.__str__', 'cart/models.py:22-23', 'CartItem: Bình nước tre × 3', '"Bình nước tre x 3"', 'test_cfg_mod_p2_cart_item_str'),
    ('WB-CFG-MOD-P3', 'CartItem.total_price', 'cart/models.py:25-27', 'CartItem: 50.000đ × 3', 'total_price = 150.000', 'test_cfg_mod_p3_cart_item_total_price'),
]

# Quyết định / điều kiện của phân hệ
DECISIONS = [
    ('D1', 'views.py:17 (cart_add)', 'not request.user.is_authenticated', '1', 'Tường minh', 'if'),
    ('D2', 'views.py:28 (cart_add)', 'not created and cart_item.quantity < MAX_QUANTITY', '2 (A = not created, B = quantity < MAX)', 'Tường minh', 'if - điều kiện kép, có ngắn mạch'),
    ('D3', 'views.py:50 (cart_increase)', 'cart_item.quantity < MAX_QUANTITY', '1', 'Tường minh', 'if'),
    ('D4', 'views.py:65 (cart_decrease)', 'cart_item.quantity <= 0  (sau khi trừ 1)', '1', 'Tường minh', 'if/else'),
    ('D5', 'context_processors.py:4', 'request.user.is_authenticated', '1', 'Tường minh', 'if'),
    ('D6', 'context_processors.py:5-10', 'request.user.cart có ném Cart.DoesNotExist?', '1', 'Tường minh', 'try/except'),
    ('D7', 'views.py:77 (cart_detail)', 'còn item trong cart_items?', '1', 'Tường minh', 'Điều kiện vòng lặp L1'),
    ('D8', 'context_processors.py:7', 'còn item trong cart.items.all()?', '1', 'Tường minh', 'Điều kiện vòng lặp L2'),
    ('I1', '@login_required: views.py:35, 44, 57, 73', 'request.user.is_authenticated', '1', 'Ẩn (Django)', 'Decorator'),
    ('I2', 'get_object_or_404(Product): views.py:20, 38, 47, 60', 'Product có id = product_id?', '1', 'Ẩn (Django)', 'Ném Http404'),
    ('I3', 'get_object_or_404(CartItem): views.py:49, 62', 'SP có trong giỏ của user?', '1', 'Ẩn (Django)', 'Ném Http404'),
]

# Bảng chân trị D2. Mỗi dòng: (#, A, B, kết quả, mã TC, dữ liệu vào → mong đợi, hàm test, vai trò MC/DC)
D2_TRUTH = [
    ('1', 'T', 'T', 'T', 'WB-MCDC-D2-01', f'{LOGIN}, A×1, GET /cart/add/{{A}}/ → 302 → /cart/; q = 2',
     'test_mcdc_d2_tc1_a_true_b_true', 'Cặp với #3 (chứng minh A) và với #2 (chứng minh B)'),
    ('1b', 'T', 'T (biên MAX − 1)', 'T', 'WB-MCDC-D2-04', f'{LOGIN}, A×2147483646, GET /cart/add/{{A}}/ → 302 → /cart/; q = 2147483647',
     'test_mcdc_d2_tc4_b_boundary_max_minus_1', 'Bổ sung: B = T tại đúng biên của toán tử <'),
    ('2', 'T', 'F', 'F', 'WB-MCDC-D2-02', f'{LOGIN}, A×2147483647, GET /cart/add/{{A}}/ → 302 → /cart/; giữ q = 2147483647',
     'test_mcdc_d2_tc2_a_true_b_false', 'Cặp với #1: A giữ T, B đổi → kết quả đổi'),
    ('3', 'F', 'T (không được đánh giá do ngắn mạch)', 'F', 'WB-MCDC-D2-03', f'{LOGIN}, giỏ chưa có A, GET /cart/add/{{A}}/ → 302 → /cart/; q = 1',
     'test_mcdc_d2_tc3_a_false', 'Cặp với #1: B giữ T, A đổi → kết quả đổi'),
    ('4', 'F', 'F', 'F (không khả thi)', 'WB-MCDC-D2-05', 'Kiểm tra default của quantity và SP vừa tạo → SP mới luôn có q = 1 < MAX',
     'test_mcdc_d2_tc5_a_false_b_false_is_infeasible', 'Chứng minh tổ hợp không khả thi: A = F thì B luôn T'),
]

# Các quyết định 1 điều kiện: (mã TC, quyết định, giá trị, dữ liệu vào, mong đợi, hàm test, ghi chú)
SINGLE_MCDC = [
    ('WB-CFG-ADD-P1', 'D1', 'T', 'Khách, GET /cart/add/{A}/', '302 → login', 'test_cfg_add_p1_guest', 'Dùng lại ca CFG'),
    ('WB-CFG-ADD-P3', 'D1', 'F', f'{LOGIN}, GET /cart/add/{{A}}/', '302 → /cart/; q = 1', 'test_cfg_add_p3_new_item', 'Dùng lại ca CFG'),
    ('WB-MCDC-D3-01', 'D3', 'T (biên MAX − 1)', f'{LOGIN}, A×2147483646, GET /cart/increase/{{A}}/', '302 → /cart/; q = 2147483647', 'test_mcdc_d3_tc1_true_at_max_minus_1', 'Chọn đúng biên của toán tử <'),
    ('WB-MCDC-D3-02', 'D3', 'F (biên MAX)', f'{LOGIN}, A×2147483647, GET /cart/increase/{{A}}/', '302 → /cart/; giữ q', 'test_mcdc_d3_tc2_false_at_max', 'Chọn đúng biên của toán tử <'),
    ('WB-MCDC-D4-01', 'D4', 'T (q: 1 → 0)', f'{LOGIN}, A×1, GET /cart/decrease/{{A}}/', '302 → /cart/; A bị xóa', 'test_mcdc_d4_tc1_true_quantity_one', ''),
    ('WB-MCDC-D4-02', 'D4', 'F (q: 2 → 1)', f'{LOGIN}, A×2, GET /cart/decrease/{{A}}/', '302 → /cart/; q = 1', 'test_mcdc_d4_tc2_false_quantity_two', ''),
    ('WB-MCDC-D4-03', 'D4', 'T (q: 0 → −1)', f'{LOGIN}, A×0 (dữ liệu bất thường), GET /cart/decrease/{{A}}/', '302 → /cart/; A bị xóa, không 500', 'test_mcdc_d4_tc3_true_quantity_zero', 'Kiểm tra toán tử <= (phân biệt với == 0)'),
    ('WB-MCDC-D5-01', 'D5', 'F', 'Gọi cart_item_count với AnonymousUser', "{'cart_item_count': 0}", 'test_mcdc_d5_tc1_authenticated_false', 'Gọi trực tiếp hàm'),
    ('WB-MCDC-D5-02', 'D5', 'T', 'Gọi cart_item_count với user có A×4', "{'cart_item_count': 4}", 'test_mcdc_d5_tc2_authenticated_true', 'Gọi trực tiếp hàm'),
    ('WB-CFG-CIC-P2', 'D6', 'F (ném DoesNotExist)', 'User chưa có Cart, GET /', 'cart_item_count = 0', 'test_cfg_cic_p2_no_cart_row', 'Dùng lại ca CFG'),
    ('WB-CFG-CIC-P4', 'D6', 'T (có Cart)', 'User có A×2, B×3, GET /', 'cart_item_count = 5', 'test_cfg_cic_p4_cart_with_items', 'Dùng lại ca CFG'),
    ('WB-LOOP-01', 'D7', 'F ngay lần đầu', 'Giỏ rỗng, GET /cart/', 'total_price = 0', 'test_loop_01_skip_zero_iterations', 'Dùng lại ca vòng lặp'),
    ('WB-LOOP-02', 'D7', 'T rồi F', 'Giỏ 1 SP, GET /cart/', 'total_price = 50.000', 'test_loop_02_one_iteration', 'Dùng lại ca vòng lặp'),
    ('WB-CFG-CIC-P3', 'D8', 'F ngay lần đầu', 'User có Cart rỗng, GET /', 'cart_item_count = 0', 'test_cfg_cic_p3_cart_without_items', 'Dùng lại ca CFG'),
    ('WB-CFG-CIC-P4', 'D8', 'T rồi F', 'User có A×2, B×3, GET /', 'cart_item_count = 5', 'test_cfg_cic_p4_cart_with_items', 'Dùng lại ca CFG'),
    ('WB-CFG-REM-P1', 'I1', 'F', 'Khách, GET /cart/remove/{A}/', '302 → login', 'test_cfg_rem_p1_guest', 'Cùng decorator ở 4 view: INC-P1, DEC-P1, DET-P1'),
    ('WB-CFG-REM-P3', 'I1', 'T', f'{LOGIN}, GET /cart/remove/{{A}}/', '302 → /cart/', 'test_cfg_rem_p3_delete', 'Dùng lại ca CFG'),
    ('WB-CFG-ADD-P2', 'I2', 'F', 'GET /cart/add/999999/', '404', 'test_cfg_add_p2_missing_product', 'Cả 4 vị trí: ADD-P2, REM-P2, INC-P2, DEC-P2'),
    ('WB-CFG-ADD-P3', 'I2', 'T', 'GET /cart/add/{A}/', '302 → /cart/', 'test_cfg_add_p3_new_item', 'Dùng lại ca CFG'),
    ('WB-CFG-INC-P3', 'I3', 'F', 'Giỏ chưa có A, GET /cart/increase/{A}/', '404', 'test_cfg_inc_p3_not_in_cart', 'Cả 2 vị trí: INC-P3, DEC-P3'),
    ('WB-CFG-INC-P4', 'I3', 'T', 'A×2, GET /cart/increase/{A}/', '302 → /cart/; q = 3', 'test_cfg_inc_p4_below_max', 'Dùng lại ca CFG'),
]

COVERAGE_CRITERIA = [
    ('Phủ quyết định (Decision / Branch coverage)', 'Mỗi quyết định nhận cả T và F',
     '11 quyết định (D1-D8, I1-I3)', '22/22 kết quả', 'Bảng 2.2, 2.3; coverage.py: 10/10 nhánh tường minh'),
    ('Phủ điều kiện (Condition coverage)', 'Mỗi điều kiện đơn nhận cả T và F',
     '12 điều kiện đơn (D2 có 2, các quyết định còn lại 1)', '24/24 giá trị', 'D2: A = T ở #1, F ở #3; B = T ở #1, F ở #2'),
    ('Phủ điều kiện / quyết định (C/DC)', 'Đạt đồng thời 2 tiêu chí trên', '11 quyết định, 12 điều kiện', 'Đạt', '—'),
    ('MC/DC', 'Mỗi điều kiện được chứng minh ảnh hưởng độc lập tới kết quả',
     'D2: n + 1 = 3 ca; quyết định 1 điều kiện: 2 ca', 'Đạt', 'D2: cặp (#1, #3) cho A, cặp (#1, #2) cho B'),
    ('Phủ đa điều kiện (Multiple condition coverage)', 'Mọi tổ hợp T/F của các điều kiện trong cùng quyết định',
     'D2: 4 tổ hợp, 1 tổ hợp không khả thi', '3/3 tổ hợp khả thi', 'Tổ hợp #4 (F, F) không thể xảy ra, có ca WB-MCDC-D2-05 chứng minh'),
]

# Kiểm thử vòng lặp: (mã TC, số lần lặp, mức kiểm thử, dữ liệu vào, mong đợi, hàm test)
LOOPS = [
    ('L1', 'cart/views.py:77 (cart_detail)', 'sum(item.product.price * item.quantity for item in cart_items)', 'Vòng lặp đơn',
     'Số dòng CartItem của giỏ', 'Tổng tiền total_price'),
    ("L1'", 'cart/templates/cart/detail.html:32', '{% for item in cart_items %} ... {% endfor %}', 'Vòng lặp đơn (cùng tập với L1)',
     'Số dòng CartItem của giỏ', 'Số khối <div class="cart-item"> và chữ "k sản phẩm trong giỏ"'),
    ('L2', 'cart/context_processors.py:7 (cart_item_count)', 'sum(item.quantity for item in request.user.cart.items.all())', 'Vòng lặp đơn',
     'Số dòng CartItem của giỏ', 'Số trên biểu tượng giỏ cart_item_count'),
]
LOOP_PRICES = [50000, 30000, 20000, 45000, 15000, 25000, 35000, 40000, 55000, 60000]
LOOP_CASES = [
    ('WB-LOOP-01', '0', 'Bỏ qua vòng lặp', 'Giỏ đã có bản ghi Cart nhưng rỗng', 'total_price = 0; cart_item_count = 0; hiện "Giỏ hàng của bạn đang trống"', 'test_loop_01_skip_zero_iterations'),
    ('WB-LOOP-02', '1', '1 lần', 'SP1 × 1', 'total_price = 50.000; cart_item_count = 1; 1 khối cart-item', 'test_loop_02_one_iteration'),
    ('WB-LOOP-03', '2', '2 lần', 'SP1 × 1, SP2 × 2', 'total_price = 110.000; cart_item_count = 3', 'test_loop_03_two_iterations'),
    ('WB-LOOP-04', '5', 'm lần (điển hình, 2 < m < n − 1)', 'SP1 → SP5, SPi × i', 'total_price = 425.000; cart_item_count = 15', 'test_loop_04_typical_m_iterations'),
    ('WB-LOOP-05', '9', 'n − 1 lần', 'SP1 → SP9, SPi × i', 'total_price = 1.635.000; cart_item_count = 45', 'test_loop_05_n_minus_1_iterations'),
    ('WB-LOOP-06', '10', 'n lần (tối đa)', 'SP1 → SP10, SPi × i', 'total_price = 2.235.000; cart_item_count = 55', 'test_loop_06_n_iterations'),
    ('WB-LOOP-07', '10 (thử 11)', 'n + 1 lần (thử vượt)', 'Giỏ đủ 10 SP, thêm lại SP1 qua GET /cart/add/{SP1}/',
     'Vẫn 10 dòng / 10 lần lặp; SP1 lên q = 2; total_price = 2.285.000; cart_item_count = 56', 'test_loop_07_n_plus_1_attempt'),
    ('WB-LOOP-08', '10', 'n lần, giá trị cực đại trong thân vòng lặp', 'SP1 → SP10, mỗi SP q = 2147483647',
     'total_price = 2147483647 × 375.000 = 805.306.367.625.000; cart_item_count = 21.474.836.470; không lỗi 500', 'test_loop_08_n_iterations_extreme_values'),
]

# Kết quả kiểm tra đột biến (mutation) chạy thủ công ngày 18/11/2026 trên nhánh tuan-7
MUTANTS = [
    ('M1', 'views.py:28', 'quantity < MAX  →  quantity <= MAX', 'WB-MCDC-D2-02, WB-CFG-ADD-P5', 'Bị phát hiện'),
    ('M2', 'views.py:28', 'Bỏ điều kiện A (not created and)', 'WB-MCDC-D2-03, WB-CFG-ADD-P3', 'Bị phát hiện'),
    ('M3', 'views.py:28', 'and  →  or', 'WB-MCDC-D2-02, D2-03, WB-CFG-ADD-P3, ADD-P5', 'Bị phát hiện'),
    ('M4', 'views.py:50', 'quantity < MAX  →  quantity <= MAX', 'WB-MCDC-D3-02, WB-CFG-INC-P5', 'Bị phát hiện'),
    ('M5', 'views.py:65', 'quantity <= 0  →  quantity == 0', 'Chỉ WB-MCDC-D4-03 (88 ca EP/BVA + ST + BQĐ cũ không phát hiện)', 'Bị phát hiện'),
    ('M6', 'views.py:77', 'Vòng lặp bỏ phần tử đầu', 'WB-CFG-DET-P3, WB-LOOP-02 → 08', 'Bị phát hiện'),
    ('M7', 'views.py:77', 'Vòng lặp bỏ phần tử cuối', 'WB-CFG-DET-P3, WB-LOOP-02 → 08', 'Bị phát hiện'),
    ('M8', 'context_processors.py:7', 'Đếm số dòng thay vì cộng quantity', 'WB-CFG-CIC-P4, WB-LOOP-03 → 08, WB-MCDC-D5-02', 'Bị phát hiện'),
    ('M9', 'context_processors.py:4', 'Đảo điều kiện is_authenticated', 'WB-CFG-CIC-P1, P4, WB-MCDC-D5-01, D5-02, WB-LOOP-02 → 08', 'Bị phát hiện'),
]


# ---------------------------------------------------------------------------
# 1. Thu thập kết quả test (chạy trong tiến trình con, dưới coverage)
# ---------------------------------------------------------------------------
def collect(out_path):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.test.runner import DiscoverRunner

    runner = DiscoverRunner(verbosity=0)
    runner.setup_test_environment()
    suite = runner.build_suite(['cart.tests_whitebox'])

    def flatten(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                yield from flatten(t)
            else:
                yield t

    # Lấy danh sách test TRƯỚC khi chạy: TestSuite tự xóa test khỏi suite sau khi chạy xong
    status = {getattr(t, '_testMethodName', str(t)): 'PASS' for t in flatten(suite)}
    old = runner.setup_databases()
    result = unittest.TestResult()
    suite.run(result)
    runner.teardown_databases(old)
    runner.teardown_test_environment()
    if result.testsRun != len(status):
        raise SystemExit(f'Số test chạy ({result.testsRun}) khác số test thu thập ({len(status)})')
    messages = {}
    for kind, items in (('FAIL', result.failures), ('ERROR', result.errors)):
        for test, tb in items:
            name = getattr(test, '_testMethodName', str(test))
            status[name] = kind
            messages[name] = tb.strip().splitlines()[-1][:300]
    from cart.tests_whitebox import OBSERVED
    Path(out_path).write_text(json.dumps({'status': status, 'observed': OBSERVED, 'messages': messages,
                                          'ran': result.testsRun}, ensure_ascii=False), encoding='utf-8')


def run_coverage(tmp):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    py = sys.executable

    def cov(cov_file, args):
        e = dict(env, COVERAGE_FILE=str(cov_file))
        p = subprocess.run([py, '-m', 'coverage', 'run', '--branch', '--source=cart', f'--omit={OMIT}', *args],
                           cwd=ROOT, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace')
        json_path = Path(str(cov_file) + '.json')
        subprocess.run([py, '-m', 'coverage', 'json', '-q', '-o', str(json_path)], cwd=ROOT, env=e, check=True)
        return p, json.loads(json_path.read_text(encoding='utf-8'))

    res_path = Path(tmp) / 'results.json'
    _, cov_wb = cov(Path(tmp) / '.cov_wb', [str(Path(__file__).resolve()), '--collect', str(res_path)])
    results = json.loads(res_path.read_text(encoding='utf-8'))

    p, cov_all = cov(Path(tmp) / '.cov_all', ['manage.py', 'test', 'cart'])
    out = p.stdout + p.stderr
    ran = int(re.search(r'Ran (\d+) tests?', out).group(1))
    fails = [re.sub(r'^test_st_(\d+)_.*', r'ST-\1', name) for name in re.findall(r'^(?:FAIL|ERROR): (\w+)', out, re.M)]
    return results, cov_wb, {'ran': ran, 'fails': fails, 'cov': cov_all}


# ---------------------------------------------------------------------------
# 2. Vẽ CFG
# ---------------------------------------------------------------------------
UX, UY, MARGIN, HEAD, FOOT = 125, 82, 55, 70, 70
R_NODE, R_DIAMOND = 19, 25
COL = {'line': (55, 71, 79), 'green': (46, 125, 50), 'red': (198, 40, 40), 'grey': (110, 110, 110)}
FILL = {'stmt': ((232, 245, 233), (46, 125, 50)), 'dec': ((255, 242, 204), (183, 121, 31)),
        'imp': ((245, 245, 245), (96, 125, 139)), 'exit': ((255, 255, 255), (55, 71, 79))}


def load_font(size, bold=False):
    from PIL import ImageFont
    names = (['arialbd.ttf', 'DejaVuSans-Bold.ttf'] if bold else ['arial.ttf', 'DejaVuSans.ttf'])
    for name in names:
        for folder in ('C:/Windows/Fonts', '/usr/share/fonts/truetype/dejavu', ''):
            try:
                return ImageFont.truetype(str(Path(folder) / name) if folder else name, size)
            except OSError:
                continue
    return ImageFont.load_default()


def graph_numbers(spec):
    nodes = len(spec['nodes'])
    edges = len(spec['edges'])
    outs = {}
    for a, *_ in spec['edges']:
        outs[a] = outs.get(a, 0) + 1
    preds = sum(1 for v in outs.values() if v >= 2)
    return nodes, edges, preds, edges - nodes + 2


def dashed_polygon(draw, pts, color, width=2, dash=7, gap=5):
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        length = math.hypot(x2 - x1, y2 - y1)
        pos = 0
        while pos < length:
            end = min(pos + dash, length)
            draw.line([(x1 + (x2 - x1) * pos / length, y1 + (y2 - y1) * pos / length),
                       (x1 + (x2 - x1) * end / length, y1 + (y2 - y1) * end / length)], fill=color, width=width)
            pos += dash + gap


def draw_cfg(spec, path):
    from PIL import Image, ImageDraw
    f_title, f_sub, f_node, f_cap, f_lab = load_font(17, True), load_font(14), load_font(15, True), load_font(12), load_font(13, True)
    nodes = {n[0]: n for n in spec['nodes']}
    xs = [n[2][0] for n in spec['nodes']] + [w[0] for e in spec['edges'] for w in e[3]]
    ys = [n[2][1] for n in spec['nodes']]
    width = max(int(max(xs) * UX) + 2 * MARGIN + 70, 560)
    height = int(max(ys) * UY) + 2 * MARGIN + HEAD + FOOT
    img = Image.new('RGB', (width, height), 'white')
    d = ImageDraw.Draw(img)

    def px(pos):
        return MARGIN + pos[0] * UX, MARGIN + HEAD + pos[1] * UY

    def radius(node_id):
        kind = nodes[node_id][1]
        return R_DIAMOND if kind in ('dec', 'imp') else (R_NODE + 4 if kind == 'exit' else R_NODE)

    n, e, p, v = graph_numbers(spec)
    d.text((MARGIN - 30, 14), f"CFG - {spec['func']}  ({spec['loc']})", font=f_title, fill=(46, 125, 50))
    d.text((MARGIN - 30, 40), f"N = {n} nút, E = {e} cạnh, P = {p} nút quyết định  →  V(G) = E − N + 2 = P + 1 = {v}",
           font=f_sub, fill=COL['grey'])

    # Cạnh
    for a, b, label, waypoints in spec['edges']:
        pts = [px(nodes[a][2])] + [px(w) for w in waypoints] + [px(nodes[b][2])]
        (x0, y0), (x1, y1) = pts[0], pts[1]
        dist = math.hypot(x1 - x0, y1 - y0)
        pts[0] = (x0 + (x1 - x0) * radius(a) / dist, y0 + (y1 - y0) * radius(a) / dist)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        dist = math.hypot(x1 - x0, y1 - y0)
        tip = (x1 - (x1 - x0) * radius(b) / dist, y1 - (y1 - y0) * radius(b) / dist)
        pts[-1] = tip
        d.line(pts, fill=COL['line'], width=2, joint='curve')
        ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
        d.polygon([tip, (tip[0] - 11 * ux + 5 * uy, tip[1] - 11 * uy - 5 * ux),
                   (tip[0] - 11 * ux - 5 * uy, tip[1] - 11 * uy + 5 * ux)], fill=COL['line'])
        if label:
            (sx, sy), (nx, ny) = pts[0], pts[1]
            dist = math.hypot(nx - sx, ny - sy)
            ux, uy = (nx - sx) / dist, (ny - sy) / dist
            lx, ly = sx + ux * 16 + uy * 10 - 4, sy + uy * 16 - ux * 10 - 8
            d.text((lx, ly), label, font=f_lab, fill=COL['green'] if label == 'T' else COL['red'])

    # Nút
    for node_id, kind, pos, caption, *_ in spec['nodes']:
        cx, cy = px(pos)
        fill, outline = FILL[kind]
        if kind in ('dec', 'imp'):
            pts = [(cx, cy - R_DIAMOND), (cx + R_DIAMOND, cy), (cx, cy + R_DIAMOND), (cx - R_DIAMOND, cy)]
            d.polygon(pts, fill=fill)
            if kind == 'dec':
                d.polygon(pts, outline=outline, width=2)
            else:
                dashed_polygon(d, pts, outline)
        else:
            r = R_NODE
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=2)
            if kind == 'exit':
                d.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], outline=outline, width=2)
        d.text((cx, cy), node_id, font=f_node, fill=(0, 0, 0), anchor='mm')
        if caption:
            # Mặc định nhãn ở trên-phải; tiền tố '<' = trên-trái, 'v' = dưới-phải (tránh cạnh đè lên nhãn)
            if caption[0] == '<':
                text = caption[1:]
                d.text((cx - 22 - d.textlength(text, font=f_cap), cy - 34), text, font=f_cap, fill=COL['grey'])
            elif caption[0] == 'v':
                d.text((cx + 24, cy + 12), caption[1:], font=f_cap, fill=COL['grey'])
            else:
                d.text((cx + 22, cy - 34), caption, font=f_cap, fill=COL['grey'])

    # Chú thích
    y = height - FOOT + 18
    x = MARGIN - 30
    d.ellipse([x, y - 9, x + 18, y + 9], fill=FILL['stmt'][0], outline=FILL['stmt'][1], width=2)
    d.text((x + 24, y), 'Khối lệnh', font=f_cap, fill=COL['grey'], anchor='lm')
    x += 105
    d.polygon([(x + 10, y - 11), (x + 21, y), (x + 10, y + 11), (x - 1, y)], fill=FILL['dec'][0], outline=FILL['dec'][1], width=2)
    d.text((x + 26, y), 'Quyết định', font=f_cap, fill=COL['grey'], anchor='lm')
    x += 110
    pts = [(x + 10, y - 11), (x + 21, y), (x + 10, y + 11), (x - 1, y)]
    d.polygon(pts, fill=FILL['imp'][0])
    dashed_polygon(d, pts, FILL['imp'][1], dash=4, gap=3)
    d.text((x + 26, y), 'Quyết định ẩn (Django)', font=f_cap, fill=COL['grey'], anchor='lm')
    y += 24
    x = MARGIN - 30
    d.text((x, y), 'T', font=f_lab, fill=COL['green'], anchor='lm')
    d.text((x + 12, y), '= Đúng', font=f_cap, fill=COL['grey'], anchor='lm')
    d.text((x + 70, y), 'F', font=f_lab, fill=COL['red'], anchor='lm')
    d.text((x + 82, y), '= Sai', font=f_cap, fill=COL['grey'], anchor='lm')
    d.text((x + 135, y), 'E = nút ra; nhãn xám = dòng code', font=f_cap, fill=COL['grey'], anchor='lm')

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img.size


# ---------------------------------------------------------------------------
# 3. Ghi sheet
# ---------------------------------------------------------------------------
GREEN, GREEN_DARK, WHITE = 'FF2E7D32', 'FF1B5E20', 'FFFFFFFF'
LIGHT, BAND, GREY_TEXT = 'FFE8F5E9', 'FFF6FAF6', 'FF555555'
OK_FILL, OK_TEXT, BAD_FILL, BAD_TEXT, WARN_FILL, WARN_TEXT = 'FFC6EFCE', 'FF1B5E20', 'FFFFC7CE', 'FF9C0006', 'FFFFF2CC', 'FF7F6000'
# Cột A → I: Mã TC | Đường đi | Điều kiện | Dữ liệu vào | Mong đợi | Thực tế | KQ | Hàm test | Ca hộp đen / ghi chú
WIDTHS = {'A': 17, 'B': 23, 'C': 21, 'D': 26, 'E': 27, 'F': 30, 'G': 8, 'H': 31, 'I': 22, 'J': 2}
LAST_COL = 9
IMG_COL = 'K'
IMG_WIDTH = 360          # px
LINE_PT = 14.5           # chiều cao 1 dòng chữ cỡ 11


def short_input(text):
    """Bỏ tiền tố đăng nhập lặp lại ở mọi dòng (đã ghi 1 lần trong phần quy ước)."""
    return text.replace(f'{LOGIN}, ', '').replace(LOGIN, 'Đã đăng nhập')


def build_sheet(results, cov_wb, full, images):
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    thin = Side(style='thin', color='FFBDBDBD')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fill = lambda c: PatternFill('solid', fgColor=c)
    status, observed, messages = results['status'], results['observed'], results['messages']

    wb = openpyxl.load_workbook(REPORT)
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    # Đặt ngay sau các sheet Phong_* khác (nếu có), không thì cuối file
    phong = [i for i, name in enumerate(wb.sheetnames) if name.startswith('Phong_')]
    ws = wb.create_sheet(SHEET, phong[-1] + 1 if phong else None)
    for col, w in WIDTHS.items():
        ws.column_dimensions[col].width = w
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90
    ws.freeze_panes = 'A3'
    ws.sheet_properties.tabColor = '2E7D32'
    col_w = [WIDTHS[c] for c in 'ABCDEFGHI']

    st = {'row': 1}
    anchors = {}

    def lines_needed(text, width_chars, size=11, bold=False):
        """Ước lượng số dòng khi Excel tự xuống dòng: ngắt ở dấu cách, từ dài hơn 1 dòng thì bị cắt giữa từ."""
        if text in (None, ''):
            return 1
        per_line = max((width_chars - 1.5) * (11 / size) / (1.1 if bold else 1.0), 4)
        total = 0
        for paragraph in str(text).split('\n'):
            lines, current = 1, 0
            for word in paragraph.split(' '):
                n = len(word)
                if current and current + 1 + n <= per_line:
                    current += 1 + n
                    continue
                if current:
                    lines += 1
                while n > per_line:            # từ quá dài (URL, tên hàm) bị cắt sang dòng sau
                    lines += 1
                    n -= per_line
                current = n
            total += lines
        return total

    def set_height(row, lines, size=11):
        ws.row_dimensions[row].height = round(max(lines, 1) * LINE_PT * size / 11 + 4, 1)

    def spacer(pt=8):
        ws.row_dimensions[st['row']].height = pt
        st['row'] += 1

    def line(text, size=11, bold=False, color='FF000000', italic=False, band=None, anchor=None):
        r = st['row']
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=LAST_COL)
        c = ws.cell(r, 1, text)
        c.font = Font(size=size, bold=bold, color=color, italic=italic)
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='left', indent=0 if not band else 1)
        if band:
            for k in range(1, LAST_COL + 1):
                ws.cell(r, k).fill = fill(band)
        set_height(r, lines_needed(text, sum(col_w), size, bold), size)
        if anchor:
            anchors[anchor] = r
        st['row'] += 1

    def part(title, anchor):
        spacer(12)
        line(title, size=12, bold=True, color=WHITE, band=GREEN, anchor=anchor)
        spacer(6)

    def sub(title):
        line(title, bold=True, color=GREEN_DARK)

    def result_of(method):
        return status.get(method, 'CHƯA CHẠY')

    def actual_of(tc_id, method):
        res = result_of(method)
        return observed.get(tc_id, 'Đúng như mong đợi') if res == 'PASS' else messages.get(method, res)

    def style_status(c, value):
        ok = value in ('PASS', 'Đạt', 'Bị phát hiện') or (isinstance(value, str) and value.endswith('PASS') and 'FAIL' not in value)
        bad = value in ('FAIL', 'ERROR', 'Chưa đạt', 'Sống sót', 'CHƯA CHẠY') or (isinstance(value, str) and 'FAIL' in value and not value.startswith('0'))
        if ok or bad:
            c.font = Font(bold=True, color=OK_TEXT if ok else BAD_TEXT)
            c.fill = fill(OK_FILL if ok else BAD_FILL)

    def table(headers, rows, spans=None, status_cols=(), center_cols=(), first_bold=True, total_last=False, small_cols=()):
        spans = spans or [1] * len(headers)

        def write(values, header=False, band=None, is_total=False):
            r, col, lines = st['row'], 1, 1
            for i, (value, span) in enumerate(zip(values, spans)):
                if span > 1:
                    ws.merge_cells(start_row=r, start_column=col, end_row=r, end_column=col + span - 1)
                width = sum(col_w[col - 1:col - 1 + span])
                for k in range(span):
                    cell = ws.cell(r, col + k)
                    cell.border = border
                    if header:
                        cell.fill = fill(GREEN)
                    elif is_total:
                        cell.fill = fill(LIGHT)
                    elif band:
                        cell.fill = fill(band)
                c = ws.cell(r, col, value)
                centered = header or i in center_cols or i in status_cols
                c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center' if centered else 'left')
                size = 10 if (i in small_cols and not header) else 11
                if header:
                    c.font = Font(bold=True, color=WHITE, size=10.5)
                else:
                    c.font = Font(bold=(i == 0 and first_bold) or is_total, size=size,
                                  color=GREY_TEXT if i in small_cols else 'FF000000')
                    if i in status_cols:
                        style_status(c, value)
                    if isinstance(value, float) and 0 <= value <= 1:
                        c.number_format = '0.0%'
                text = f'{value:.1%}' if isinstance(value, float) else value
                lines = max(lines, lines_needed(text, width, size, header or (i == 0 and first_bold)))
                col += span
            set_height(r, lines)
            st['row'] += 1

        write(headers, header=True)
        for k, values in enumerate(rows):
            last = total_last and k == len(rows) - 1
            write(values, band=None if k % 2 == 0 else BAND, is_total=last)

    def kpis(items):
        """Dải tóm tắt: hàng nhãn + hàng giá trị, mỗi ô 1 chỉ số."""
        r = st['row']
        for k, (label, value) in enumerate(items, start=1):
            top, bottom = ws.cell(r, k, label), ws.cell(r + 1, k, value)
            top.font = Font(size=9, color=GREY_TEXT)
            bottom.font = Font(size=13, bold=True, color=GREEN_DARK)
            for c in (top, bottom):
                c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                c.fill = fill(LIGHT)
                c.border = Border(left=Side(style='thin', color='FFFFFFFF'), right=Side(style='thin', color='FFFFFFFF'))
        ws.row_dimensions[r].height = 26
        ws.row_dimensions[r + 1].height = 24
        st['row'] += 2

    def place_image(key, start_row):
        """Đặt ảnh CFG ở cột K từ start_row; thêm dòng đệm nếu bảng thấp hơn ảnh."""
        img_path, (w, h) = images[key]
        pic = XLImage(str(img_path))
        pic.width, pic.height = IMG_WIDTH, int(h * IMG_WIDTH / w)
        ws.add_image(pic, f'{IMG_COL}{start_row}')
        used_px = sum((ws.row_dimensions[r].height or 15) * 4 / 3 for r in range(start_row, st['row']))
        while used_px < pic.height + 6:
            ws.row_dimensions[st['row']].height = 15
            used_px += 20
            st['row'] += 1

    # ======================= ĐẦU SHEET =======================
    today = datetime.date.today().strftime('%d/%m/%Y')
    branch = subprocess.run(['git', 'branch', '--show-current'], cwd=ROOT, capture_output=True, text=True).stdout.strip() or '—'
    import coverage as coverage_mod
    total_wb = len(status)
    pass_wb = sum(1 for v in status.values() if v == 'PASS')
    summary = []
    for spec in CFGS:
        n, e, p, v = graph_numbers(spec)
        passed = sum(1 for path in spec['paths'] if result_of(path[5]) == 'PASS')
        summary.append((spec['func'], spec['loc'], n, e, p, v, len(spec['paths']), passed))
    for tc, fn, loc, *_, m in MODEL_PATHS:
        summary.append((fn, loc, 2, 1, 0, 1, 1, int(result_of(m) == 'PASS')))
    total_v = sum(r[5] for r in summary)
    total_paths = sum(r[6] for r in summary)
    total_pass = sum(r[7] for r in summary)
    loop_pass = sum(1 for *_, m in LOOP_CASES if result_of(m) == 'PASS')
    wb_pct = cov_wb['totals']['percent_covered']

    line('KIỂM THỬ HỘP TRẮNG – GIỎ HÀNG (FR3): CFG · PHỦ ĐIỀU KIỆN / MC/DC · VÒNG LẶP', size=15, bold=True, color=GREEN)
    line(f'Người thực hiện: Lê Bá Hoài Phong · Ngày chạy: {today} · Nhánh: {branch} · Công cụ: Django TestCase, '
         f'coverage.py {coverage_mod.__version__} (--branch) · Mã test: cart/tests_whitebox.py', size=10, italic=True, color=GREY_TEXT)
    spacer(6)
    kpis([
        ('Test hộp trắng', f'{pass_wb}/{total_wb} PASS'),
        ('Tổng V(G) / đường cơ sở', f'{total_v} / {total_pass} PASS'),
        ('MC/DC', 'Đạt'),
        ('Ca vòng lặp', f'{loop_pass}/{len(LOOP_CASES)} PASS'),
        ('Độ phủ dòng + nhánh', f'{wb_pct:.0f}%'),
        ('Đột biến bị phát hiện', f'{len(MUTANTS)}/{len(MUTANTS)}'),
    ])
    toc_row = st['row']
    spacer(20)

    # ======================= PHẦN 1 =======================
    part('PHẦN 1 – ĐỒ THỊ LUỒNG ĐIỀU KHIỂN (CFG) & ĐƯỜNG CƠ SỞ', 'p1')
    line('Quy ước: ○ khối lệnh · ◇ quyết định · ◇ nét đứt = quyết định ẩn của Django (@login_required, get_object_or_404, '
         'ngoại lệ DoesNotExist) vì chúng tạo đường ra 302/404 riêng · E = nút ra · V(G) = E − N + 2 = P + 1 (P = số nút quyết định). '
         'Mỗi đường cơ sở có 1 test riêng. Các ca không ghi "Khách" đều đã đăng nhập bằng user cartuser; A = SP "Bình nước tre" 50.000đ.',
         size=10, color=GREY_TEXT)
    spacer(6)
    sub('1.1 Tổng hợp độ phức tạp Cyclomatic')
    table(['Hàm', 'Vị trí', 'N', 'E', 'P', 'V(G)', 'Đường', 'KQ'],
          [(f, loc, n, e, p, v, k, f'{ok}/{k} PASS') for f, loc, n, e, p, v, k, ok in summary]
          + [('TỔNG CỘNG', f'{len(summary)} hàm', '', '', '', total_v, total_paths, f'{total_pass}/{total_paths} PASS')],
          spans=[2, 1, 1, 1, 1, 1, 1, 1], center_cols=(2, 3, 4, 5, 6), status_cols=(7,), total_last=True)

    path_headers = ['Mã test case', 'Đường đi', 'Điều kiện', 'Dữ liệu vào', 'Kết quả mong đợi', 'Kết quả thực tế',
                    'KQ', 'Hàm test', 'Ca hộp đen cùng đường']
    for idx, spec in enumerate(CFGS, start=2):
        n, e, p, v = graph_numbers(spec)
        spacer(10)
        start = st['row']
        sub(f"1.{idx} {spec['func']}  ·  {spec['loc']}  ·  N = {n}, E = {e}, P = {p}  →  V(G) = {v}  →  {len(spec['paths'])} đường cơ sở")
        table(['Nút', 'Dòng', 'Câu lệnh / điều kiện', 'Loại nút'],
              [(nd[0], nd[4], nd[5], nd[6]) for nd in spec['nodes']], spans=[1, 1, 4, 3], center_cols=(0, 1))
        spacer(6)
        table(path_headers,
              [(tc, seq, cond, short_input(inp), exp, actual_of(tc, m), result_of(m), m, old)
               for tc, seq, cond, inp, exp, m, old in spec['paths']], status_cols=(6,), small_cols=(7,))
        place_image(spec['key'], start)

    spacer(10)
    sub(f'1.{len(CFGS) + 2} Hàm 1 đường trong cart/models.py (V(G) = 1, đường 1 → E)')
    table(['Mã test case', 'Hàm', 'Vị trí', 'Dữ liệu vào', 'Kết quả mong đợi', 'Kết quả thực tế', 'KQ', 'Hàm test'],
          [(tc, fn, loc, inp, exp, actual_of(tc, m), result_of(m), m) for tc, fn, loc, inp, exp, m in MODEL_PATHS],
          spans=[1, 1, 1, 1, 1, 1, 1, 2], status_cols=(6,), small_cols=(7,))

    # ======================= PHẦN 2 =======================
    part('PHẦN 2 – PHỦ ĐIỀU KIỆN / MC/DC', 'p2')
    sub('2.1 Các quyết định và ca phủ giá trị Đúng (T) / Sai (F)')
    cases = {}
    for tc, dec, val, inp, exp, m, note in SINGLE_MCDC:
        extra = val[1:].strip(' ()')
        cases.setdefault(dec, {'T': [], 'F': []})[val[0]].append((f'{tc} ({extra})' if extra else tc, m))
    cases['D2'] = {'T': [], 'F': []}
    for no, a, b, res, tc, inp, m, role in D2_TRUTH:
        cases['D2']['T' if res == 'T' else 'F'].append((f'#{no} {tc}', m))
    dec_rows = []
    for code, loc, expr, n_cond, kind, struct in DECISIONS:
        t_cases, f_cases = cases[code]['T'], cases[code]['F']
        methods = [m for _, m in t_cases + f_cases]
        ok = all(result_of(m) == 'PASS' for m in methods)
        note = '2 điều kiện – xem bảng 2.2' if code == 'D2' else (f'{kind}; {struct}' if kind != 'Tường minh' else struct)
        dec_rows.append((code, loc, expr, '\n'.join(t for t, _ in t_cases), '\n'.join(t for t, _ in f_cases),
                         'PASS' if ok else 'FAIL', note))
    table(['Mã', 'Vị trí', 'Biểu thức quyết định', 'Ca cho giá trị T', 'Ca cho giá trị F', 'KQ', 'Ghi chú'],
          dec_rows, spans=[1, 1, 2, 1, 1, 1, 2], status_cols=(5,), center_cols=(0,), small_cols=(3, 4))
    spacer(10)
    sub('2.2 MC/DC cho quyết định kép D2 – views.py:28: not created and cart_item.quantity < MAX_QUANTITY')
    table(['# · Mã test case', 'A: not created', 'B: quantity < MAX', 'A and B', 'Dữ liệu vào → mong đợi',
           'Kết quả thực tế', 'KQ', 'Hàm test', 'Vai trò MC/DC'],
          [(f'#{no} · {tc}', a, b, res, short_input(inp), actual_of(tc, m), result_of(m), m, role)
           for no, a, b, res, tc, inp, m, role in D2_TRUTH],
          center_cols=(1, 2, 3), status_cols=(6,), small_cols=(7,))
    line('A độc lập: cặp (#1, #3) – B giữ T, A đổi thì kết quả đổi. B độc lập: cặp (#1, #2) – A giữ T, B đổi thì kết quả đổi. '
         'Tập tối thiểu {#1, #2, #3} = n + 1 = 3 ca; #1b thử đúng biên MAX − 1; #4 chứng minh tổ hợp (F, F) không khả thi.',
         size=10, color=GREY_TEXT)
    spacer(10)
    sub('2.3 Chi tiết các ca MC/DC mới (các ca còn lại dùng lại ca CFG / vòng lặp ở bảng 2.1)')
    new_cases = [row for row in SINGLE_MCDC if row[0].startswith('WB-MCDC-')]
    table(['Mã test case', 'Quyết định', 'Giá trị', 'Dữ liệu vào', 'Kết quả mong đợi', 'Kết quả thực tế', 'KQ', 'Hàm test', 'Ghi chú'],
          [(tc, dec, val, short_input(inp), exp, actual_of(tc, m), result_of(m), m, note)
           for tc, dec, val, inp, exp, m, note in new_cases], status_cols=(6,), center_cols=(1,), small_cols=(7,))
    spacer(10)
    sub('2.4 Tổng hợp tiêu chí')
    table(['Tiêu chí', 'Yêu cầu', 'Phạm vi', 'Kết quả', 'Ghi chú'],
          [(a, b, c, d, e) for a, b, c, d, e in COVERAGE_CRITERIA], spans=[2, 1, 2, 2, 2], status_cols=(3,), center_cols=(3,))

    # ======================= PHẦN 3 =======================
    part('PHẦN 3 – KIỂM THỬ VÒNG LẶP', 'p3')
    sub('3.1 Các vòng lặp (đều là vòng lặp đơn, không có vòng lồng nhau / nối tiếp)')
    table(['Mã', 'Vị trí', 'Mã nguồn', 'Số lần lặp', 'Giá trị quan sát'],
          [(code, loc, src, var, obs) for code, loc, src, kind, var, obs in LOOPS], spans=[1, 2, 2, 2, 2], center_cols=(0,))
    prices = ', '.join(str(p // 1000) for p in LOOP_PRICES)
    total_price = f'{sum(LOOP_PRICES):,}'.replace(',', '.')
    line(f'Cận trên n = số sản phẩm trong hệ thống (CartItem có unique_together (cart, product)). Dữ liệu test: n = 10 SP, '
         f'giá SP1 → SP10 = {prices} nghìn đồng (tổng {total_price}đ); SP thứ i có q = i. '
         f"Mỗi GET /cart/ kiểm tra cùng lúc L1, L1' và L2.", size=10, color=GREY_TEXT)
    spacer(10)
    sub('3.2 Test case vòng lặp đơn: 0, 1, 2, m, n − 1, n, n + 1 lần')
    table(['Mã test case', 'Số lần lặp', 'Mức', 'Dữ liệu vào', 'Kết quả mong đợi', 'Kết quả thực tế', 'KQ', 'Hàm test'],
          [(tc, k, lvl, inp, exp, actual_of(tc, m), result_of(m), m) for tc, k, lvl, inp, exp, m in LOOP_CASES],
          spans=[1, 1, 1, 1, 1, 1, 1, 2], status_cols=(6,), center_cols=(1,), small_cols=(7,))

    # ======================= PHẦN 4 =======================
    part('PHẦN 4 – ĐỘ PHỦ MÃ NGUỒN & KIỂM TRA ĐỘT BIẾN', 'p4')
    sub('4.1 Độ phủ dòng + nhánh (coverage.py --branch, app cart, bỏ qua tests / migrations / management)')

    def cov_row(label, cases_, outcome, data):
        t = data['totals']
        missing = '; '.join(f"{Path(k).name}: {', '.join(map(str, v['missing_lines']))}"
                            for k, v in data['files'].items() if v['missing_lines']) or '—'
        return (label, cases_, outcome, f"{t['num_statements'] - t['missing_lines']}/{t['num_statements']}",
                f"{t['num_branches'] - t['missing_branches']}/{t['num_branches']}", t['percent_covered'] / 100, missing)

    full_pass = full['ran'] - len(full['fails'])
    fail_text = f"{full_pass} PASS, {len(full['fails'])} FAIL" + (f" ({', '.join(full['fails'])})" if full['fails'] else '')
    table(['Phạm vi chạy', 'Số ca', 'Kết quả', 'Dòng đã phủ', 'Nhánh đã phủ', 'Độ phủ', 'Chưa phủ'],
          [('Chỉ 33 ca EP/BVA (sheet Phong_BQD_Do_phu_BVA)', '33', '33 PASS', '78/83', '9/10', 0.9354838709677419,
            'context_processors.py: 9-11; models.py: 11, 23'),
           ('88 ca EP/BVA + Chuyển trạng thái + BQĐ', '88', '86 PASS, 2 FAIL (ST-21, ST-22)', '81/83', '10/10', 0.9784946236559139,
            'models.py: 11, 23'),
           cov_row('Chỉ bộ hộp trắng (cart/tests_whitebox.py)', str(total_wb), f'{pass_wb} PASS', cov_wb),
           cov_row('Toàn bộ app cart (hộp đen + hộp trắng)', str(full['ran']), fail_text, full['cov'])],
          spans=[2, 1, 2, 1, 1, 1, 1], center_cols=(1, 3, 4, 5), first_bold=False)
    files = sorted(cov_wb['files'].items())
    full_files = [k for k, v in files if v['summary']['percent_covered'] == 100]
    detail = ', '.join(f"{Path(k).name} {v['summary']['num_statements']} dòng/{v['summary']['num_branches']} nhánh"
                       for k, v in files if v['summary']['num_statements'])
    line(f'Theo từng tệp (chỉ bộ hộp trắng): {len(full_files)}/{len(files)} tệp đạt 100% – {detail}.', size=10, color=GREY_TEXT)
    spacer(10)
    sub('4.2 Kiểm tra đột biến (mutation): sửa sai 1 chỗ trong code rồi chạy lại bộ hộp trắng – phải có ít nhất 1 ca FAIL '
        '(chạy 18/11/2026, code được khôi phục sau mỗi lần)')
    table(['Mã', 'Vị trí', 'Thay đổi', 'Ca phát hiện (FAIL)', 'Kết quả'],
          MUTANTS, spans=[1, 1, 2, 4, 1], status_cols=(4,), center_cols=(0,))

    # ======================= PHẦN 5 =======================
    part('PHẦN 5 – NHẬN XÉT & CÁCH CHẠY', 'p5')
    notes = [
        f'• CFG cho {len(summary)} hàm, tổng V(G) = {total_v} → {total_paths} đường cơ sở, mỗi đường 1 test: {total_pass}/{total_paths} PASS. '
        'Quyết định ẩn của Django được đưa vào CFG nên số kết quả quyết định lớn hơn số nhánh coverage.py báo (10).',
        '• D2 (views.py:28) là quyết định kép duy nhất: 3 ca đạt MC/DC, tổ hợp (F, F) không khả thi vì SP vừa tạo luôn có q = 1.',
        '• WB-MCDC-D4-03 (q = 0) là ca duy nhất phân biệt "<= 0" với "== 0" ở views.py:65: đột biến M5 qua mặt toàn bộ 88 ca hộp đen cũ.',
        '• Vòng lặp chạy 0, 1, 2, 5, 9, 10 lần và thử 11 lần; không thể vượt n = 10 vì unique_together. Tổng tiền và số trên biểu tượng '
        'giỏ vẫn đúng khi mọi dòng có q = 2147483647.',
        f'• Bộ hộp trắng đạt {wb_pct:.0f}% dòng + nhánh (2 ca models.__str__ phủ nốt phần hộp đen còn thiếu). Chạy toàn bộ '
        f'{full["ran"]} ca của app cart: {len(full["fails"])} FAIL là ST-21, ST-22 của BUG-CART-02 (đã ghi nhận), không do bộ hộp trắng.',
    ]
    for note in notes:
        line(note, size=10.5)
    spacer(8)
    table(['Việc', 'Lệnh (chạy ở thư mục gốc dự án)'],
          [('Chạy test hộp trắng', r'.venv\Scripts\python.exe manage.py test cart.tests_whitebox -v 2'),
           ('Đo độ phủ', r'.venv\Scripts\python.exe -m coverage run --branch --source=cart '
                         r'--omit="cart/tests*,cart/migrations/*,cart/management/*" manage.py test cart.tests_whitebox'
                         r'  →  .venv\Scripts\python.exe -m coverage report -m'),
           ('Tạo lại sheet + ảnh CFG', r'.venv\Scripts\python.exe tools/build_cart_whitebox_report.py  (đóng Report.xlsx trước)')],
          spans=[2, 7])

    # Mục lục có link nhảy tới từng phần
    toc = [('Mục lục:', None), ('1. CFG', 'p1'), ('2. MC/DC', 'p2'), ('3. Vòng lặp', 'p3'), ('4. Độ phủ & đột biến', 'p4'),
           ('5. Nhận xét', 'p5')]
    for k, (text, key) in enumerate(toc, start=1):
        c = ws.cell(toc_row, k, text)
        c.alignment = Alignment(horizontal='left' if k == 1 else 'center', vertical='center')
        if key:
            c.hyperlink = f"#'{SHEET}'!A{anchors[key]}"
            c.font = Font(size=10, color='FF1565C0', underline='single')
        else:
            c.font = Font(size=10, bold=True, color=GREY_TEXT)

    wb.save(REPORT)
    return pass_wb, total_wb


def main():
    if sys.argv[1:2] == ['--collect']:
        collect(sys.argv[2])
        return
    with tempfile.TemporaryDirectory() as tmp:
        print('Chạy test hộp trắng và đo độ phủ...')
        results, cov_wb, full = run_coverage(tmp)
    images = {}
    for spec in CFGS:
        path = IMG_DIR / f"cfg_{spec['func']}.png"
        images[spec['key']] = (path, draw_cfg(spec, path))
        print('Đã vẽ', path.relative_to(ROOT))
    passed, total = build_sheet(results, cov_wb, full, images)
    print(f'Đã ghi sheet {SHEET} vào {REPORT.relative_to(ROOT)}: {passed}/{total} PASS; '
          f'độ phủ hộp trắng {cov_wb["totals"]["percent_covered"]:.1f}%; toàn bộ {full["ran"]} ca, FAIL: {full["fails"]}')


if __name__ == '__main__':
    main()
