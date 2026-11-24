"""
Tạo sheet TC_Chuyen_TT_GioHang_Phong trong docs/Report.xlsx: kiểm thử chuyển đổi trạng thái FR3 – Giỏ hàng,
trình bày giống sheet TC_Chuyen_TT_don_Quân (I. Lớp tương đương → II. Bảng chuyển trạng thái → III. Test case).

Script chạy cart/tests_state_transition.py rồi lấy kết quả PASS/FAIL thật của từng hàm test (và từng subTest
của ST-01) để điền cột "Trạng thái". Sheet này thay cho sheet cũ Phong_test_trandition.

Cách dùng (đóng Report.xlsx trước khi chạy):
  python tools/build_cart_state_transition_report.py
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cart_whitebox_report import SheetWriter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs' / 'Report.xlsx'
TEST_FILE = ROOT / 'cart' / 'tests_state_transition.py'
MODULE = 'cart.tests_state_transition'
SHEET = 'TC_Chuyen_TT_GioHang_Phong'
OLD_SHEETS = ['Phong_test_trandition', SHEET]

WIDTHS = {'A': 24, 'B': 56, 'C': 30, 'D': 34, 'E': 56, 'F': 56, 'G': 10, 'H': 14, 'I': 56}
GREEN, RED = 'C6EFCE', 'FFC7CE'
MAX = '2.147.483.647'
MAX_1 = '2.147.483.646'

TITLE = ('Chức năng: Quản lý giỏ hàng – thêm, tăng, giảm, xóa sản phẩm và dọn giỏ khi đặt hàng (/cart/) | '
         'Phân hệ FR3: Giỏ hàng | Người thực hiện: Lê Bá Hoài Phong')

# I. Lớp tương đương: (biến đầu vào, lớp hợp lệ, tag, lớp không hợp lệ, tag)
EP = [
    ('Người thực hiện thao tác', 'Chủ giỏ hàng đã đăng nhập', 'V1',
     '(a) Khách chưa đăng nhập', 'X1'),
    ('', '', '',
     '(b) Người dùng khác (chỉ được đổi giỏ của chính họ)', 'X2'),
    ('Thao tác trên một sản phẩm', 'add, remove ở mọi trạng thái; increase, decrease khi sản phẩm đã có trong giỏ',
     'V2', '(a) increase, decrease khi sản phẩm chưa có trong giỏ', 'X3'),
    ('', 'Admin xóa sản phẩm khỏi hệ thống', 'V3',
     f'(b) add, increase khi sản phẩm đã ở số lượng tối đa ({MAX})', 'X4'),
    ('Thao tác trên cả giỏ', 'Đặt hàng / thanh toán khi giỏ có sản phẩm (COD, QR, Mock; hủy đơn QR; Mock thất bại)',
     'V4', '(a) Đặt hàng khi giỏ trống', 'X5'),
    ('', '', '',
     '(b) Xác nhận lại đơn QR đã thanh toán hoặc đã hủy', 'X6'),
]

# II. Bảng chuyển trạng thái: (trạng thái, ký hiệu – điều kiện, loại, chuyển được sang)
ITEM_STATES = [
    ('Chưa có trong giỏ', 'ABSENT – không có CartItem', 'Bắt đầu / kết thúc', 'ONE (add)'),
    ('Có 1 sản phẩm', 'ONE – q = 1', 'Trung gian', 'MANY (add, increase); ABSENT (decrease, remove, admin xóa SP)'),
    ('Nhiều sản phẩm', f'MANY – 2 ≤ q ≤ {MAX_1}', 'Trung gian',
     'MANY (add, increase, decrease); AT_MAX (add, increase khi q = MAX − 1); ONE (decrease khi q = 2); '
     'ABSENT (remove, admin xóa SP)'),
    ('Đạt số lượng tối đa', f'AT_MAX – q = {MAX}', 'Biên trên (chặn tăng)',
     'MANY (decrease); ABSENT (remove, admin xóa SP). add, increase giữ nguyên AT_MAX'),
]
CART_STATES = [
    ('Giỏ trống', 'EMPTY – không có CartItem nào', 'Bắt đầu / kết thúc',
     'NOT_EMPTY (add). Đặt hàng bị chặn, quay về /cart/'),
    ('Giỏ có hàng', 'NOT_EMPTY – có ít nhất 1 CartItem', 'Trung gian',
     'EMPTY (xóa SP cuối, đặt COD, xác nhận QR, Mock thành công); giữ NOT_EMPTY (xóa SP chưa phải SP cuối, '
     'đặt QR hoặc Mock, hủy đơn QR, Mock thất bại)'),
]

ST01 = 'CartItemStateTransitionTests.test_st_01_all_state_event_pairs_follow_table'
ITEM_T = 'CartItemStateTransitionTests.'
CART_T = 'CartLevelStateTransitionTests.'
FAIL_BUG02 = 'B bị xóa khỏi giỏ (BUG-CART-02, chưa sửa)'
PASS_BUG02 = ('Chỉ xóa A, B còn trong giỏ, q = 1 (PASS sau khi sửa BUG-CART-02 ở commit a318c9a – SCRUM-56; '
              'trước khi sửa, B bị xóa)')


def ok(text):
    return 'Chấp nhận – ' + text


def no(text):
    return 'Từ chối – ' + text


def st01(n, start, event, end, expected, tags, accepted=True):
    """Một ô trong bảng 4 trạng thái × 4 sự kiện (subTest của ST-01)."""
    arrow = f'{start.split(" ")[0]} → {end}'
    name = f'ST-01.{n:02d} – {arrow} ({event})' if accepted else f'ST-01.{n:02d} – {start.split(" ")[0]} + {event}'
    return dict(name=name, start=start, event=event, expected=expected, tags=tags, accepted=accepted,
                test=ST01, sub={'state': start.split(' ')[0], 'event': event})


# III. Test case: name, start, event, expected, tags, accepted (tô xanh/đỏ), test (hàm test), fail (thực tế nếu FAIL)
ITEM_CASES = [
    st01(1, 'ABSENT', 'add', 'ONE', ok('302 về giỏ, q = 1 → ONE'), 'V1, V2'),
    st01(2, 'ABSENT', 'increase', 'ABSENT', no('404, không tạo CartItem, giữ ABSENT'), 'X3', False),
    st01(3, 'ABSENT', 'decrease', 'ABSENT', no('404, giữ ABSENT'), 'X3', False),
    st01(4, 'ABSENT', 'remove', 'ABSENT', ok('302 về giỏ, không lỗi, giữ ABSENT'), 'V1, V2'),
    st01(5, 'ONE', 'add', 'MANY', ok('q = 2 → MANY'), 'V1, V2'),
    st01(6, 'ONE', 'increase', 'MANY', ok('q = 2 → MANY'), 'V1, V2'),
    st01(7, 'ONE', 'decrease', 'ABSENT', ok('xóa CartItem → ABSENT'), 'V1, V2'),
    st01(8, 'ONE', 'remove', 'ABSENT', ok('xóa CartItem → ABSENT'), 'V1, V2'),
    st01(9, 'MANY (q = 5)', 'add', 'MANY', ok('q = 6, vẫn MANY'), 'V1, V2'),
    st01(10, 'MANY (q = 5)', 'increase', 'MANY', ok('q = 6, vẫn MANY'), 'V1, V2'),
    st01(11, 'MANY (q = 5)', 'decrease', 'MANY', ok('q = 4, vẫn MANY'), 'V1, V2'),
    st01(12, 'MANY (q = 5)', 'remove', 'ABSENT', ok('xóa CartItem → ABSENT'), 'V1, V2'),
    st01(13, 'AT_MAX', 'add', 'AT_MAX', no(f'giữ q = {MAX}, không lỗi 500'), 'X4', False),
    st01(14, 'AT_MAX', 'increase', 'AT_MAX', no(f'giữ q = {MAX}, không lỗi 500'), 'X4', False),
    st01(15, 'AT_MAX', 'decrease', 'MANY', ok(f'q = {MAX_1} → MANY'), 'V1, V2'),
    st01(16, 'AT_MAX', 'remove', 'ABSENT', ok('xóa CartItem → ABSENT'), 'V1, V2'),
    dict(name='ST-02 – MANY → ONE (decrease tại biên q = 2)', start='MANY (q = 2)', event='decrease',
         expected=ok('q = 1 → ONE'), tags='V1, V2', test=ITEM_T + 'test_st_02_decrease_from_2_moves_many_to_one'),
] + [
    dict(name=f'ST-03.0{i} – MANY → AT_MAX ({ev} tại biên q = MAX − 1)', start=f'MANY (q = {MAX_1})', event=ev,
         expected=ok(f'q = {MAX} → AT_MAX'), tags='V1, V2',
         test=ITEM_T + 'test_st_03_add_or_increase_from_max_minus_1_moves_to_at_max')
    for i, ev in ((1, 'add'), (2, 'increase'))
] + [
    dict(name=f'ST-04.0{i} – Chuỗi lên rồi xuống, bước {i}/6: {s.split(" ")[0]} → {e}', start=s, event=ev,
         expected=ok(x), tags='V1, V2', test=ITEM_T + 'test_st_04_full_path_up_then_down_to_absent')
    for i, s, ev, e, x in (
        (1, 'ABSENT', 'add', 'ONE', 'q = 1 → ONE'),
        (2, 'ONE', 'increase', 'MANY', 'q = 2 → MANY'),
        (3, 'MANY (q = 2)', 'add', 'MANY', 'q = 3, vẫn MANY'),
        (4, 'MANY (q = 3)', 'decrease', 'MANY', 'q = 2, vẫn MANY'),
        (5, 'MANY (q = 2)', 'decrease', 'ONE', 'q = 1 → ONE'),
        (6, 'ONE', 'decrease', 'ABSENT', 'xóa CartItem → ABSENT'),
    )
] + [
    dict(name=f'ST-05.0{i} – Chuỗi qua AT_MAX, bước {i}/5: {s.split(" ")[0]} → {e}', start=s, event=ev,
         expected=x, tags=t, accepted=a, test=ITEM_T + 'test_st_05_path_through_at_max')
    for i, s, ev, e, x, t, a in (
        (1, f'MANY (q = {MAX_1})', 'increase', 'AT_MAX', ok(f'q = {MAX} → AT_MAX'), 'V1, V2', True),
        (2, 'AT_MAX', 'add', 'AT_MAX', no(f'giữ q = {MAX}'), 'X4', False),
        (3, 'AT_MAX', 'decrease', 'MANY', ok(f'q = {MAX_1} → MANY'), 'V1, V2', True),
        (4, f'MANY (q = {MAX_1})', 'add', 'AT_MAX', ok(f'q = {MAX} → AT_MAX'), 'V1, V2', True),
        (5, 'AT_MAX', 'remove', 'ABSENT', ok('xóa CartItem → ABSENT'), 'V1, V2', True),
    )
] + [
    dict(name='ST-06 – Xóa rồi thêm lại: MANY → ABSENT → ONE', start='MANY (q = 5)', event='remove, rồi add',
         expected=ok('q = 1 → ONE, không giữ số lượng cũ'), tags='V1, V2',
         test=ITEM_T + 'test_st_06_absent_is_reachable_again_after_remove'),
] + [
    dict(name=f'ST-07.0{i} – {ev} trên A không đổi sản phẩm B', start='A: MANY (q = 2); B: q = 3', event=f'{ev} trên A',
         expected=ok('A đổi theo sự kiện; B vẫn q = 3'), tags='V1, V2',
         test=ITEM_T + 'test_st_07_event_only_changes_target_product')
    for i, ev in enumerate(('add', 'increase', 'decrease', 'remove'), 1)
] + [
    dict(name=f'ST-08.0{i} – Khách {ev}', start='MANY (q = 2), đã đăng xuất', event=ev,
         expected=no('302 về /accounts/login/, giữ q = 2 (MANY)'), tags='X1', accepted=False,
         test=ITEM_T + 'test_st_08_guest_events_do_not_change_state')
    for i, ev in enumerate(('add', 'increase', 'decrease', 'remove'), 1)
] + [
    dict(name='ST-09 – Khách thêm SP → đăng nhập → quay lại: ABSENT → ONE', start='ABSENT, khách',
         event='add → đăng nhập → quay lại URL next', expected=ok('sau đăng nhập về URL next, q = 1 → ONE'),
         tags='X1, V1, V2', test=ITEM_T + 'test_st_09_guest_add_then_login_reaches_one'),
] + [
    dict(name=f'ST-16.0{i} – Người dùng khác {ev} cùng sản phẩm', start='MANY (q = 2) của user 1',
         event=f'User 2 {ev}', expected=no('giỏ user 1 vẫn q = 2 (MANY)'), tags='X2', accepted=False,
         test=ITEM_T + 'test_st_16_other_user_events_do_not_change_state')
    for i, ev in enumerate(('add', 'increase', 'decrease', 'remove'), 1)
] + [
    dict(name=f'ST-17.0{i} – Admin xóa sản phẩm: {s.split(" ")[0]} → ABSENT', start=s, event='Admin xóa sản phẩm',
         expected=ok('CartItem bị xóa → ABSENT, /cart/ vẫn trả 200'), tags='V3',
         test=ITEM_T + 'test_st_17_deleting_product_moves_item_to_absent')
    for i, s in enumerate(('ONE', 'MANY (q = 5)', f'AT_MAX (q = {MAX})'), 1)
]

CART_CASES = [
    dict(name='ST-10 – Xóa dần về giỏ trống: NOT_EMPTY → EMPTY', start='NOT_EMPTY (A × 1, B × 1)',
         event='remove A, rồi decrease B',
         expected=ok('sau bước 1 còn B; sau bước 2 hiện "Giỏ hàng của bạn đang trống" → EMPTY'), tags='V1, V2',
         test=CART_T + 'test_st_10_removing_last_item_returns_to_empty'),
    dict(name='ST-11 – Đặt hàng khi giỏ trống', start='EMPTY', event='POST /orders/checkout/',
         expected=no('302 về /cart/, không tạo đơn, giữ EMPTY'), tags='X5', accepted=False,
         test=CART_T + 'test_st_11_checkout_on_empty_cart_stays_empty'),
    dict(name='ST-12 – Đặt COD: NOT_EMPTY → EMPTY', start='NOT_EMPTY (A × 2)', event='Đặt hàng COD',
         expected=ok('tạo đơn, xóa hết CartItem → EMPTY'), tags='V4',
         test=CART_T + 'test_st_12_cod_order_empties_cart'),
    dict(name='ST-13 – Đặt QR rồi xác nhận chuyển khoản: NOT_EMPTY → EMPTY', start='NOT_EMPTY (A × 2)',
         event='Đặt QR, rồi xác nhận đã chuyển khoản',
         expected=ok('sau bước 1 giỏ còn nguyên; sau bước 2 → EMPTY'), tags='V4',
         test=CART_T + 'test_st_13_qr_keeps_cart_until_payment_confirmed'),
    dict(name='ST-14 – Đặt Mock rồi thanh toán thành công: NOT_EMPTY → EMPTY', start='NOT_EMPTY (A × 2)',
         event='Đặt Mock, rồi thanh toán thành công',
         expected=ok('sau bước 1 giỏ còn nguyên; sau bước 2 → EMPTY'), tags='V4',
         test=CART_T + 'test_st_14_mock_success_empties_cart'),
    dict(name='ST-15 – Đặt Mock rồi thanh toán thất bại: giữ NOT_EMPTY', start='NOT_EMPTY (A × 2)',
         event='Đặt Mock, rồi thanh toán thất bại', expected=ok('giỏ giữ A × 2 (NOT_EMPTY)'), tags='V4',
         test=CART_T + 'test_st_15_mock_failure_keeps_cart'),
    dict(name='ST-18 – Hủy đơn QR: giữ NOT_EMPTY', start='NOT_EMPTY (A × 2), đơn QR đang chờ',
         event='POST /orders/<id>/cancel/', expected=ok('302 về /cart/, đơn cancelled, giỏ giữ A × 2'), tags='V4',
         test=CART_T + 'test_st_18_cancel_qr_order_keeps_cart'),
    dict(name='ST-19 – Xác nhận lại đơn QR đã thanh toán', start='NOT_EMPTY (B × 1), đơn QR đã paid',
         event='Xác nhận lại đơn QR', expected=no('không xóa giỏ mới, giữ B × 1'), tags='X6', accepted=False,
         test=CART_T + 'test_st_19_confirm_paid_qr_again_keeps_new_cart'),
    dict(name='ST-20 – Xác nhận đơn QR đã hủy', start='NOT_EMPTY (A × 2), đơn QR đã cancelled',
         event='Xác nhận đơn QR', expected=no('đơn vẫn cancelled, giỏ giữ A × 2'), tags='X6', accepted=False,
         test=CART_T + 'test_st_20_confirm_cancelled_qr_changes_nothing'),
    dict(name='ST-21 – Thêm SP khi đơn QR đang chờ, rồi xác nhận', start='NOT_EMPTY (A × 2), đơn QR chờ; sau đó thêm B',
         event='Xác nhận đơn QR', expected=ok('chỉ xóa A (có trong đơn), B còn trong giỏ, q = 1'), tags='V4',
         test=CART_T + 'test_st_21_qr_confirm_keeps_product_added_after_order', fail=FAIL_BUG02, passed=PASS_BUG02),
    dict(name='ST-22 – Thêm SP khi đơn Mock đang chờ, rồi thanh toán thành công',
         start='NOT_EMPTY (A × 2), đơn Mock chờ; sau đó thêm B', event='Mock thanh toán thành công',
         expected=ok('chỉ xóa A (có trong đơn), B còn trong giỏ, q = 1'), tags='V4',
         test=CART_T + 'test_st_22_mock_success_keeps_product_added_after_order', fail=FAIL_BUG02, passed=PASS_BUG02),
]


def run_tests():
    """Chạy tests_state_transition, trả về {(tên hàm, subTest hoặc None)} của các ca FAIL/ERROR."""
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    proc = subprocess.run([sys.executable, 'manage.py', 'test', MODULE, '-v', '2', '--noinput'], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = proc.stdout + proc.stderr
    ran = re.search(r'^Ran (\d+) tests?', out, re.M)
    if not ran:
        print(out)
        sys.exit('Không chạy được test.')
    failed = set()
    for m in re.finditer(r'^(?:FAIL|ERROR): (test_\w+) \(([\w.]+)\)(?: \((.*)\))?\s*$', out, re.M):
        cls = m.group(2).split('.')[-2]
        sub = frozenset(re.findall(r"(\w+)='([^']*)'", m.group(3) or ''))
        failed.add((f'{cls}.{m.group(1)}', sub or None))
    return int(ran.group(1)), failed


def result(case, failed):
    if (case['test'], None) in failed:
        return 'FAIL'
    if case.get('sub') and (case['test'], frozenset(case['sub'].items())) in failed:
        return 'FAIL'
    return 'PASS'


def check_tests_exist(cases):
    source = TEST_FILE.read_text(encoding='utf-8')
    missing = {c['test'] for c in cases if f'def {c["test"].split(".")[-1]}(' not in source}
    if missing:
        sys.exit(f'Không tìm thấy hàm test: {sorted(missing)}')


CASE_COLS = [('STT', 'A', 'center'), ('Tên test case', 'B', 'left'), ('Trạng thái hiện tại', 'C', 'left'),
             ('Sự kiện (input)', 'D', 'left'), ('Kết quả mong đợi', 'E', 'left'), ('Kết quả thực tế', 'F', 'left'),
             ('Trạng thái', 'G', 'center'), ('Tag được bao phủ', 'H', 'center'),
             ('Hàm test (cart/tests_state_transition.py)', 'I', 'left')]


def case_rows(cases, failed, start_no):
    rows = []
    for i, c in enumerate(cases, start_no):
        res = result(c, failed)
        color = GREEN if c.get('accepted', True) else RED
        actual = c.get('passed', c['expected']) if res == 'PASS' else c.get('fail', 'Không đúng như mong đợi (xem log test)')
        rows.append([
            (str(i), 'A', 'center'), (c['name'], 'B', 'left'), (c['start'], 'C', 'left', color),
            (c['event'], 'D', 'left', color), (c['expected'], 'E', 'left', color), (actual, 'F', 'left'),
            (res, 'G', 'center', RED if res != 'PASS' else None), (c['tags'], 'H', 'center'),
            (c['test'].split('.')[-1], 'I', 'left'),
        ])
    return rows


def build(ran, failed):
    import openpyxl

    cases = ITEM_CASES + CART_CASES
    check_tests_exist(cases)
    wb = openpyxl.load_workbook(REPORT)
    index = None
    for name in OLD_SHEETS:
        if name in wb.sheetnames:
            index = wb.sheetnames.index(name) if index is None else index
            wb.remove(wb[name])
    if index is None:
        index = len(wb.sheetnames)
    ws = wb.create_sheet(SHEET, index)
    w = SheetWriter(ws, WIDTHS, text_span='A:I')

    w.text(TITLE, title=True, gap=1)

    w.text('I. LỚP TƯƠNG ĐƯƠNG', bold=True)
    w.table([('Biến đầu vào', 'A', 'left'), ('Lớp hợp lệ', 'B', 'left'), ('Tag', 'C', 'center'),
             ('Lớp không hợp lệ', 'D:E', 'left'), ('Tag', 'F', 'center')], [list(r) for r in EP])
    w.gap()

    w.text('II. BẢNG CHUYỂN TRẠNG THÁI (suy ra từ cart/views.py và orders/views.py; q = CartItem.quantity, '
           f'MAX = {MAX})', bold=True)
    state_cols = [('Trạng thái', 'A', 'left'), ('Ký hiệu – điều kiện', 'B', 'left'), ('Loại', 'C', 'left'),
                  ('Chuyển được sang (sự kiện)', 'D:F', 'left')]
    w.text('1. Trạng thái của một sản phẩm trong giỏ', bold=True)
    w.table(state_cols, [list(r) for r in ITEM_STATES])
    w.text('Ghi chú: increase, decrease khi sản phẩm chưa có trong giỏ trả 404 và giữ ABSENT. Khách chưa đăng nhập '
           'bị chuyển về trang đăng nhập, giỏ không đổi. Thao tác trên sản phẩm A không làm đổi sản phẩm khác trong '
           'giỏ, và không làm đổi giỏ của người dùng khác.')
    w.gap()
    w.text('2. Trạng thái của cả giỏ hàng (khi đặt hàng và thanh toán – FR3.5)', bold=True)
    w.table(state_cols, [list(r) for r in CART_STATES])
    w.text('Ghi chú: theo FR3.5, khi thanh toán xong chỉ được xóa những sản phẩm có trong đơn. Luồng QR theo hành vi '
           'sau SCRUM-43: giỏ chỉ được dọn khi xác nhận đã chuyển khoản.')
    w.gap()

    w.text('III. TEST CASE (mỗi ca là một lần chuyển trạng thái)', bold=True)
    w.text('1. Một sản phẩm trong giỏ', bold=True)
    w.table(CASE_COLS, case_rows(ITEM_CASES, failed, 1))
    w.gap()
    w.text('2. Cả giỏ hàng', bold=True)
    w.table(CASE_COLS, case_rows(CART_CASES, failed, len(ITEM_CASES) + 1))

    results = [result(c, failed) for c in cases]
    fails = [c['name'].split(' – ')[0] for c, r in zip(cases, results) if r != 'PASS']
    defined = {r[2] for r in EP if r[2]} | {r[4] for r in EP if r[4]}
    covered = {t.strip() for c in cases for t in c['tags'].split(',')}
    summary = (f'Tổng kết: {len(cases)} ca, {results.count("PASS")} PASS, {len(fails)} FAIL'
               + (f' ({", ".join(fails)} – BUG-CART-02: thanh toán đơn QR/Mock xóa cả sản phẩm không có trong đơn, '
                  'chưa sửa)' if fails else '') + '. ')
    if 'FAIL' not in [result(c, failed) for c in CART_CASES if c.get('passed')]:
        summary += ('ST-21, ST-22 phát hiện BUG-CART-02 (thanh toán đơn QR/Mock xóa cả sản phẩm không có trong đơn): '
                    'FAIL trước khi sửa, PASS sau commit a318c9a – SCRUM-56. ')
    summary += (f'Bao phủ đủ {len(defined)}/{len(defined)} tag ({", ".join(sorted(defined))}).'
                if defined <= covered else f'Tag chưa bao phủ: {", ".join(sorted(defined - covered))}.')
    w.text(summary)
    w.gap()

    w.text('CÁCH CHẠY', bold=True)
    w.text('python manage.py test cart.tests_state_transition -v 2')
    w.text('python tools/build_cart_state_transition_report.py      '
           '(tạo lại sheet này; đóng Report.xlsx trước khi chạy)')

    try:
        wb.save(REPORT)
    except PermissionError:
        sys.exit(f'Không ghi được {REPORT}: hãy đóng file Excel rồi chạy lại.')
    return len(cases), results.count('PASS'), fails, covered >= defined


def main():
    global REPORT
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 3 and sys.argv[1] == '--report':      # ghi vào file khác để xem trước
        REPORT = Path(sys.argv[2]).resolve()
    os.chdir(ROOT)
    print(f'Đang chạy {MODULE} ...')
    ran, failed = run_tests()
    print(f'Ran {ran} tests, FAIL/ERROR: {sorted(t for t, _ in failed) or "không có"}')
    n, passed, fails, all_tags = build(ran, failed)
    print(f'Đã ghi sheet {SHEET}: {n} ca, {passed} PASS, FAIL: {fails or "không có"}; '
          f'bao phủ đủ tag: {all_tags}')


if __name__ == '__main__':
    main()
