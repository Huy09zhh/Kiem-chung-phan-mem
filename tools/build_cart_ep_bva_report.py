"""
Tạo sheet TC_EP_BVA_GioHang_Phong trong docs/Report.xlsx: kiểm thử phân hoạch tương đương (EP) và giá trị
biên (BVA) cho FR3 – Giỏ hàng, trình bày giống sheet TC_Tim_kiem_don_hang_Quân
(I. Lớp tương đương → II. Giá trị biên → III. Test case).

- Mã TC, tag (V1–V10, I1–I6) và số liệu lấy đúng theo docs/TestCase_FR3_Cart_EP_BVA.md.
- Cột "Trạng thái" lấy từ lần chạy thật cart/tests.py (Django TestCase).
- Cột Postman / CodeceptJS lấy từ postman/GreenShop-ShoppingCart-EP-BVA.postman_collection.json
  và tests/cart_ep_bva_test.js.
- Cuối cùng script kiểm tra mọi mã EP/BVA mà sheet Phong_BQD_Do_phu_BVA và WhiteBox_Phong nhắc tới
  đều có trong sheet này.

Cách dùng (đóng Report.xlsx trước khi chạy):
  python tools/build_cart_ep_bva_report.py
  python tools/build_cart_ep_bva_report.py --report <file.xlsx>    # ghi vào file khác để xem trước
"""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cart_whitebox_report import SheetWriter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs' / 'Report.xlsx'
TEST_FILE = ROOT / 'cart' / 'tests.py'
POSTMAN = ROOT / 'postman' / 'GreenShop-ShoppingCart-EP-BVA.postman_collection.json'
CODECEPT = ROOT / 'tests' / 'cart_ep_bva_test.js'
SHEET = 'TC_EP_BVA_GioHang_Phong'
PLACE_BEFORE = 'TC_Chuyen_TT_GioHang_Phong'          # thứ tự: EP/BVA → chuyển trạng thái → BQĐ → hộp trắng
CROSS_CHECK = ['Phong_BQD_Do_phu_BVA', 'WhiteBox_Phong']

WIDTHS = {'A': 28, 'B': 46, 'C': 28, 'D': 36, 'E': 46, 'F': 46, 'G': 10, 'H': 14, 'I': 26, 'J': 34}
GREEN, RED = 'C6EFCE', 'FFC7CE'
MAX, MAX_1 = '2.147.483.647', '2.147.483.646'

TITLE = ('Chức năng: Quản lý giỏ hàng – thêm, xem, tăng, giảm, xóa sản phẩm (/cart/) | Phân hệ FR3: Giỏ hàng | '
         'Người thực hiện: Lê Bá Hoài Phong')

# I. Lớp tương đương (theo mục 3 của tài liệu EP/BVA): (biến, lớp hợp lệ, tag, lớp không hợp lệ, tag)
EP = [
    ('Trạng thái đăng nhập', 'Đã đăng nhập', 'V1', 'Chưa đăng nhập (khách) → chuyển /accounts/login/', 'I1'),
    ('product_id', 'Số nguyên dương, sản phẩm tồn tại', 'V2', '(a) Số nguyên dương, sản phẩm không tồn tại → 404', 'I2'),
    ('', '', '', '(b) Số âm (−1) → 404', 'I3'),
    ('', '', '', '(c) Không phải số (abc) → 404', 'I4'),
    ('SP đã có trong giỏ khi thêm', 'Chưa có → tạo mới, quantity = 1', 'V3', '–', ''),
    ('', 'Đã có → quantity + 1', 'V4', '', ''),
    ('SP có trong giỏ khi tăng / giảm', 'Có trong giỏ', 'V5', 'Không có trong giỏ → 404', 'I5'),
    ('SP có trong giỏ khi xóa', 'Có → xóa hẳn', 'V6', '–', ''),
    ('', 'Không có → 302, không lỗi', 'V7', '', ''),
    ('Số SP trong giỏ', '= 0 → thông báo giỏ trống', 'V8', '–', ''),
    ('', '≥ 1 → hiển thị tổng tiền', 'V9', '', ''),
    ('Chủ sở hữu giỏ', 'Đúng user', 'V10', 'User khác → không thấy, tăng bị 404', 'I6'),
]

# II. Giá trị biên: (biến, min−, min, min+, nominal, max−, max, max+) – kèm mã TC kiểm tra giá trị đó
BVA = [
    ('product_id', '0 (BVA-01)', 'min_id (BVA-02)', 'min_id + 1 (BVA-14)', '–', 'max_id − 1 (BVA-15)',
     'max_id (BVA-03)', 'max_id + 1 (BVA-04)'),
    ('product_id theo kiểu BIGINT', '–', '–', '–', '–', '–', '2⁶³ − 1 (BVA-05)', '2⁶³ (BVA-06)'),
    ('quantity khi giảm', '–', '1 → xóa khỏi giỏ (BVA-07)', '2 (BVA-08)', '3 (BVA-09)', '–', '–', '–'),
    ('quantity khi tăng / thêm', '–', '1 (BVA-10)', '2 (EP-09)', '–', f'{MAX_1} (BVA-16)',
     f'{MAX} (BVA-17, BVA-18)', '–'),
    ('Số SP trong giỏ', '–', '0 (EP-14, BVA-13)', '1 (BVA-11)', '2 (BVA-12)', '–', '–', '–'),
]

FIX_NOTE = f'Giữ {MAX}, không lỗi 500 (sau khi sửa BUG-CART-01; trước khi sửa lưu 2.147.483.648)'

# III. Test case: (mã, tên, tiền điều kiện, input, kết quả mong đợi, tag, hợp lệ?, thực tế khi PASS nếu khác mong đợi)
EP_CASES = [
    ('EP-01', 'Khách thêm SP – chuyển login kèm next', 'Chưa đăng nhập', 'GET /cart/add/{A}/',
     '302 → /accounts/login/?next=/cart/add/{A}/, không tạo CartItem', 'I1, V2', False),
    ('EP-02', 'Khách xem giỏ – chuyển login', 'Chưa đăng nhập', 'GET /cart/', '302 → trang đăng nhập', 'I1', False),
    ('EP-03', 'Khách tăng số lượng – chuyển login', 'Chưa đăng nhập', 'GET /cart/increase/{A}/',
     '302 → trang đăng nhập', 'I1', False),
    ('EP-04', 'Thêm SP chưa có trong giỏ', 'Đăng nhập; giỏ rỗng', 'GET /cart/add/{A}/',
     '302 → /cart/, A có quantity = 1', 'V1, V2, V3', True),
    ('EP-05', 'Thêm SP đã có trong giỏ', 'Đăng nhập; giỏ có A × 1', 'GET /cart/add/{A}/',
     'A có quantity = 2, vẫn 1 dòng', 'V1, V2, V4', True),
    ('EP-06', 'Thêm SP không tồn tại', 'Đăng nhập', 'GET /cart/add/{max_id + 100}/', '404, không tạo CartItem',
     'I2', False),
    ('EP-07', 'product_id âm', 'Đăng nhập', 'GET /cart/add/-1/', '404', 'I3', False),
    ('EP-08', 'product_id không phải số', 'Đăng nhập', 'GET /cart/add/abc/', '404', 'I4', False),
    ('EP-09', 'Tăng SP có trong giỏ', 'Đăng nhập; giỏ có A × 2', 'GET /cart/increase/{A}/', 'A có quantity = 3',
     'V5', True),
    ('EP-10', 'Tăng SP không có trong giỏ', 'Đăng nhập; giỏ rỗng', 'GET /cart/increase/{A}/', '404', 'I5', False),
    ('EP-11', 'Giảm SP không có trong giỏ', 'Đăng nhập; giỏ rỗng', 'GET /cart/decrease/{A}/', '404', 'I5', False),
    ('EP-12', 'Xóa SP có trong giỏ', 'Đăng nhập; giỏ có A × 5', 'GET /cart/remove/{A}/',
     '302, A bị xóa hẳn (không phụ thuộc số lượng)', 'V6', True),
    ('EP-13', 'Xóa SP không có trong giỏ', 'Đăng nhập; giỏ rỗng', 'GET /cart/remove/{A}/', '302 → /cart/, không lỗi',
     'V7', True),
    ('EP-14', 'Xem giỏ trống', 'Đăng nhập; giỏ rỗng', 'GET /cart/',
     '200, có "Giỏ hàng của bạn đang trống", không có nút đặt hàng', 'V8', True),
    ('EP-15', 'Giỏ tách biệt theo user', 'user1 có A × 1; đăng nhập user2', 'GET /cart/, GET /cart/increase/{A}/',
     'user2 không thấy A; increase → 404; A của user1 vẫn = 1', 'I6, V10', False),
]
BVA_CASES = [
    ('BVA-01', 'product_id = 0 (min−)', 'Đăng nhập', 'GET /cart/add/0/', '404', 'I2', False),
    ('BVA-02', 'product_id = min_id (min)', 'Đăng nhập; giỏ rỗng', 'GET /cart/add/{min_id}/',
     'Thêm thành công, quantity = 1', 'V1, V2, V3', True),
    ('BVA-03', 'product_id = max_id (max)', 'Đăng nhập; giỏ rỗng', 'GET /cart/add/{max_id}/',
     'Thêm thành công, quantity = 1', 'V1, V2, V3', True),
    ('BVA-04', 'product_id = max_id + 1 (max+)', 'Đăng nhập', 'GET /cart/add/{max_id + 1}/', '404', 'I2', False),
    ('BVA-05', 'product_id = 2⁶³ − 1 (biên kiểu BIGINT)', 'Đăng nhập', 'GET /cart/add/9223372036854775807/', '404',
     'I2', False),
    ('BVA-06', 'product_id = 2⁶³ (vượt BIGINT) trên 4 endpoint', 'Đăng nhập',
     'GET add / increase / decrease / remove với 9223372036854775808', '404 cả 4 endpoint, không lỗi 500', 'I2', False),
    ('BVA-07', 'Giảm khi quantity = 1 (min)', 'Đăng nhập; giỏ có A × 1', 'GET /cart/decrease/{A}/',
     'A bị xóa khỏi giỏ', 'V1, V5', True),
    ('BVA-08', 'Giảm khi quantity = 2 (min+)', 'Đăng nhập; giỏ có A × 2', 'GET /cart/decrease/{A}/',
     'quantity = 1, còn trong giỏ', 'V1, V5', True),
    ('BVA-09', 'Giảm khi quantity = 3 (nominal)', 'Đăng nhập; giỏ có A × 3', 'GET /cart/decrease/{A}/',
     'quantity = 2', 'V1, V5', True),
    ('BVA-10', 'Tăng khi quantity = 1 (min)', 'Đăng nhập; giỏ có A × 1', 'GET /cart/increase/{A}/', 'quantity = 2',
     'V1, V5', True),
    ('BVA-11', 'Giỏ có 1 sản phẩm', 'Đăng nhập; giỏ có A × 1', 'GET /cart/', 'Tổng tiền = 50.000', 'V1, V9', True),
    ('BVA-12', 'Giỏ có 2 sản phẩm', 'Đăng nhập; giỏ có A × 2, B × 1', 'GET /cart/', 'Tổng tiền = 130.000', 'V1, V9',
     True),
    ('BVA-13', 'Xóa SP cuối cùng: 1 SP → 0 SP', 'Đăng nhập; giỏ có A × 1', 'GET /cart/remove/{A}/, rồi GET /cart/',
     'Hiện "Giỏ hàng của bạn đang trống"', 'V1, V6, V8', True),
    ('BVA-14', 'product_id = min_id + 1 (min+)', 'Đăng nhập; giỏ rỗng', 'GET /cart/add/{min_id + 1}/',
     'Thêm thành công, quantity = 1', 'V1, V2, V3', True),
    ('BVA-15', 'product_id = max_id − 1 (max−)', 'Đăng nhập; giỏ rỗng', 'GET /cart/add/{max_id − 1}/',
     'Thêm thành công, quantity = 1', 'V1, V2, V3', True),
    ('BVA-16', f'Tăng khi quantity = {MAX_1} (max−)', f'Đăng nhập; giỏ có A × {MAX_1}', 'GET /cart/increase/{A}/',
     f'quantity = {MAX}', 'V1, V5', True),
    ('BVA-17', f'Tăng khi quantity = {MAX} (max)', f'Đăng nhập; giỏ có A × {MAX}', 'GET /cart/increase/{A}/',
     f'Không vượt {MAX}, không lỗi 500', 'V1, V5', False, FIX_NOTE),
    ('BVA-18', f'Thêm SP khi quantity = {MAX} (max)', f'Đăng nhập; giỏ có A × {MAX}', 'GET /cart/add/{A}/',
     f'Không vượt {MAX}, không lỗi 500', 'V1, V2, V4', False, FIX_NOTE),
]


def unit_results():
    """Chạy cart/tests.py; trả về {mã TC: 'PASS'/'FAIL'} theo docstring 'TC-CART-...' của từng hàm test."""
    source = TEST_FILE.read_text(encoding='utf-8')
    fn_of = {tc: fn for fn, tc in re.findall(r'def (test_\w+)\(self\):\s+"""(TC-CART-[A-Z]+-\d+)', source)}
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    proc = subprocess.run([sys.executable, 'manage.py', 'test', 'cart.tests', '--noinput'], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = proc.stdout + proc.stderr
    ran = re.search(r'^Ran (\d+) tests?', out, re.M)
    if not ran:
        print(out)
        sys.exit('Không chạy được cart.tests.')
    failed = set(re.findall(r'^(?:FAIL|ERROR): (test_\w+) ', out, re.M))
    return int(ran.group(1)), {tc: ('FAIL' if fn in failed else 'PASS') for tc, fn in fn_of.items()}


def postman_ids():
    names = []

    def walk(items):
        for it in items:
            if 'item' in it:
                walk(it['item'])
            else:
                names.append(it['name'])
    walk(json.loads(POSTMAN.read_text(encoding='utf-8'))['item'])
    found = {}
    for n in names:
        m = re.match(r'(TC-CART-(?:EP|BVA)-\d+)(\.\d+)?', n)
        if m:
            found.setdefault(m.group(1), []).append(m.group(2) or '')
    return {tc: tc + (f' ({", ".join(s for s in subs if s)})' if any(subs) else '') for tc, subs in found.items()}


def codecept_ids():
    return set(re.findall(r'TC-CART-(?:EP|BVA)-\d+', CODECEPT.read_text(encoding='utf-8')))


CASE_COLS = [('STT', 'A', 'center'), ('Tên test case', 'B', 'left'), ('Tiền điều kiện', 'C', 'left'),
             ('Input', 'D', 'left'), ('Kết quả mong đợi', 'E', 'left'), ('Kết quả thực tế', 'F', 'left'),
             ('Trạng thái', 'G', 'center'), ('Tag được bao phủ', 'H', 'center'), ('Mã TC Postman', 'I', 'left'),
             ('Mã scenario CodeceptJS', 'J', 'left')]


def case_rows(cases, start, results, pm, cj):
    rows = []
    for i, (code, name, pre, inp, exp, tags, valid, *actual) in enumerate(cases, start):
        tc = f'TC-CART-{code}'
        res = results.get(tc, 'FAIL')
        color = GREEN if valid else RED
        real = (actual[0] if actual else exp) if res == 'PASS' else 'Không đúng như mong đợi (xem log test)'
        rows.append([
            (str(i), 'A', 'center'), (f'{tc} – {name}', 'B', 'left'), (pre, 'C', 'left'), (inp, 'D', 'left'),
            (exp, 'E', 'left', color), (real, 'F', 'left', color),
            (res, 'G', 'center', GREEN if res == 'PASS' else RED), (tags, 'H', 'center'),
            (pm.get(tc, '– (không có trong Postman)'), 'I', 'left'),
            (f'{tc} (cart_ep_bva_test.js)' if tc in cj else '–', 'J', 'left'),
        ])
    return rows


def cross_check(wb, all_ids):
    """Mã EP/BVA được nhắc trong sheet BQĐ và hộp trắng phải có trong sheet này."""
    report = {}
    for name in CROSS_CHECK:
        if name not in wb.sheetnames:
            report[name] = None
            continue
        refs = set()
        for row in wb[name].iter_rows(values_only=True):
            for v in row:
                if isinstance(v, str):
                    refs |= {f'TC-CART-{k}-{n}' for k, n in re.findall(r'\b(EP|BVA)-(\d{2})\b', v)}
                    # dải "BVA-01 → 06" cũng tính đủ các mã ở giữa
                    for k, a, b in re.findall(r'\b(EP|BVA)-(\d{2}) → (\d{2})\b', v):
                        refs |= {f'TC-CART-{k}-{n:02d}' for n in range(int(a), int(b) + 1)}
        report[name] = (sorted(refs), sorted(refs - all_ids))
    return report


def build(results, ran):
    import openpyxl

    pm, cj = postman_ids(), codecept_ids()
    all_cases = EP_CASES + BVA_CASES
    all_ids = {f'TC-CART-{c[0]}' for c in all_cases}
    missing_unit = sorted(all_ids - set(results))
    if missing_unit:
        sys.exit(f'Không tìm thấy unit test cho: {missing_unit}')

    wb = openpyxl.load_workbook(REPORT)
    if SHEET in wb.sheetnames:
        index = wb.sheetnames.index(SHEET)
        wb.remove(wb[SHEET])
    elif PLACE_BEFORE in wb.sheetnames:
        index = wb.sheetnames.index(PLACE_BEFORE)
    else:
        phong = [i for i, n in enumerate(wb.sheetnames) if 'Phong' in n]
        index = phong[0] if phong else len(wb.sheetnames)
    ws = wb.create_sheet(SHEET, index)
    w = SheetWriter(ws, WIDTHS, text_span='A:J')
    today = datetime.date.today().strftime('%d/%m/%Y')

    w.text(TITLE, title=True, gap=1)
    w.text('I. LỚP TƯƠNG ĐƯƠNG', bold=True)
    w.table([('Biến đầu vào', 'A', 'left'), ('Lớp hợp lệ', 'B', 'left'), ('Tag', 'C', 'center'),
             ('Lớp không hợp lệ', 'D:E', 'left'), ('Tag', 'F', 'center')], [list(r) for r in EP])
    w.gap()

    w.text('II. GIÁ TRỊ BIÊN (trong ngoặc là mã TC kiểm tra giá trị đó)', bold=True)
    w.table([('Biến đầu vào', 'A', 'left'), ('min−', 'B', 'center'), ('min', 'C', 'center'), ('min+', 'D', 'center'),
             ('nominal', 'E', 'center'), ('max−', 'F', 'center'), ('max', 'G:H', 'center'), ('max+', 'I:J', 'center')],
            [list(r) for r in BVA])
    w.text('Ghi chú: dữ liệu test có 4 sản phẩm; min_id, max_id là id nhỏ nhất / lớn nhất đang có. SP A "Bình nước tre" '
           '= 50.000đ, SP B "Túi vải canvas" = 30.000đ. product_id = 0 đi qua URL nhưng không có sản phẩm nên thuộc lớp I2. '
           '2⁶³ − 1 = 9223372036854775807 (giới hạn kiểu BIGINT), 2⁶³ = 9223372036854775808.')
    w.text(f'SRS không quy định số lượng tối đa của 1 sản phẩm trong giỏ, nên biên trên của quantity lấy theo kiểu '
           f'PositiveIntegerField: {MAX}. Tăng hoặc thêm khi đang ở {MAX} sẽ ra 2.147.483.648, hệ thống phải giữ nguyên '
           '(BUG-CART-01, đã sửa).')
    w.gap()

    w.text('III. TEST CASE', bold=True)
    w.text(f'1. Phân hoạch tương đương ({len(EP_CASES)} ca)', bold=True)
    w.table(CASE_COLS, case_rows(EP_CASES, 1, results, pm, cj))
    w.gap()
    w.text(f'2. Giá trị biên ({len(BVA_CASES)} ca)', bold=True)
    w.table(CASE_COLS, case_rows(BVA_CASES, len(EP_CASES) + 1, results, pm, cj))

    res = [results[f'TC-CART-{c[0]}'] for c in all_cases]
    defined = {r[2] for r in EP if r[2]} | {r[4] for r in EP if r[4]}
    covered = {t.strip() for c in all_cases for t in c[5].split(',')}
    w.text(f'Tổng kết: {len(all_cases)} ca, {res.count("PASS")} PASS, {len(res) - res.count("PASS")} FAIL '
           f'(chạy unit test cart/tests.py ngày {today}). '
           + (f'Bao phủ đủ {len(defined)}/{len(defined)} tag.' if defined <= covered
              else f'Tag chưa bao phủ: {", ".join(sorted(defined - covered))}.')
           + ' Kiểm thử giá trị biên phát hiện BUG-CART-01 (BVA-17, BVA-18 FAIL trước khi sửa, PASS sau khi sửa).')
    w.text('Các mã TC ở sheet này cũng được dùng ở sheet Phong_BQD_Do_phu_BVA (phần 2: độ phủ mã nguồn của ca hộp đen) '
           'và WhiteBox_Phong (TC-CART-EP-01, EP-04, BVA-07, BVA-08 làm ví dụ phủ câu lệnh / nhánh; BVA-18 là trường hợp '
           'A T – B F của BUG-CART-01).')
    w.gap()

    w.text('CÁCH CHẠY', bold=True)
    for line in ('python manage.py test cart.tests -v 2',
                 'newman run postman/GreenShop-ShoppingCart-EP-BVA.postman_collection.json',
                 'npx codeceptjs run tests/cart_ep_bva_test.js --steps      (chạy python manage.py seed_cart_test trước)',
                 'python tools/build_cart_ep_bva_report.py      (tạo lại sheet này; đóng Report.xlsx trước khi chạy)'):
        w.text(line)

    checks = cross_check(wb, all_ids)
    try:
        wb.save(REPORT)
    except PermissionError:
        sys.exit(f'Không ghi được {REPORT}: hãy đóng file Excel rồi chạy lại.')
    return len(all_cases), res.count('PASS'), defined <= covered, checks


def main():
    global REPORT
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 3 and sys.argv[1] == '--report':
        REPORT = Path(sys.argv[2]).resolve()
    os.chdir(ROOT)
    print('Đang chạy cart.tests ...')
    ran, results = unit_results()
    print(f'Ran {ran} tests')
    n, passed, all_tags, checks = build(results, ran)
    print(f'Đã ghi sheet {SHEET}: {n} ca, {passed} PASS; bao phủ đủ tag: {all_tags}')
    for name, value in checks.items():
        if value is None:
            print(f'  {name}: không có sheet này')
        else:
            refs, missing = value
            print(f'  {name}: nhắc {len(refs)} mã EP/BVA, mã không có trong sheet EP/BVA: {missing or "không có"}')


if __name__ == '__main__':
    main()
