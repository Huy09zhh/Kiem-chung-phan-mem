"""
Tạo sheet WhiteBox_Phong trong docs/Report.xlsx và ảnh CFG trong docs/img/cfg/ cho phần
kiểm thử hộp trắng FR3 – Giỏ hàng (Chương 4, IV.4 – Control Flow Testing):
  PHẦN 1: cart.views.cart_add       PHẦN 2: cart.views.cart_decrease

Script chạy cart/tests_whitebox.py và cart/tests.py (hộp đen) một lần bằng coverage.py --branch, ghi
độ phủ riêng cho từng test case (dynamic context), rồi lấy đúng số đo đó điền vào sheet. Không có con
số độ phủ nào gõ tay.

Cách dùng (đóng Report.xlsx trước khi chạy):
  python tools/build_cart_whitebox_report.py
  python tools/build_cart_whitebox_report.py --measure coverage.json cart_add   # chỉ in độ phủ 1 hàm
"""
import ast
import datetime
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs' / 'Report.xlsx'
IMG_DIR = ROOT / 'docs' / 'img' / 'cfg'
VIEWS = 'cart/views.py'
SHEET = 'WhiteBox_Phong'
OLD_SHEETS = ['Phong_CFG_MCDC_Loop', SHEET]

WB = 'cart.tests_whitebox.'
BB = 'cart.tests.'
CTX = {   # mã test case -> context của coverage (tên đầy đủ của hàm test)
    'ADD-S1': WB + 'CartAddStatementTests.test_wb_add_s1_chua_dang_nhap',
    'ADD-S2': WB + 'CartAddStatementTests.test_wb_add_s2_san_pham_da_co_trong_gio',
    'ADD-B3': WB + 'CartAddBranchTests.test_wb_add_b3_gio_rong',
    'ADD-C1': WB + 'CartAddConditionTests.test_c1_a_dung_b_dung',
    'ADD-C2': WB + 'CartAddConditionTests.test_c2_a_dung_b_sai',
    'ADD-C3': WB + 'CartAddConditionTests.test_c3_a_sai',
    'DEC-S1': WB + 'CartDecreaseStatementTests.test_wb_dec_s1_so_luong_1_bi_xoa',
    'DEC-S2': WB + 'CartDecreaseStatementTests.test_wb_dec_s2_so_luong_2_con_1',
    'EP-01': BB + 'CartEquivalencePartitionTests.test_ep_01_guest_add_redirects_login',
    'EP-04': BB + 'CartEquivalencePartitionTests.test_ep_04_add_new_product_creates_item_qty_1',
    'BVA-07': BB + 'CartBoundaryValueTests.test_bva_07_decrease_from_1_removes_item',
    'BVA-08': BB + 'CartBoundaryValueTests.test_bva_08_decrease_from_2_keeps_item',
}

# Đồ thị luồng điều khiển. nodes: số nút -> (dòng code, các dòng lệnh thuộc nút, nội dung, loại nút)
CART_ADD = {
    'func': 'cart_add', 'image': 'cfg_cart_add.png',
    'nodes': {
        1: ('17', {17}, 'D1: if not request.user.is_authenticated', 'Điều kiện'),
        2: ('18', {18}, 'return redirect("/accounts/login/?next=/cart/add/<id>/")', 'Lệnh'),
        3: ('20–26', {20, 21, 23}, 'Lấy sản phẩm (404 nếu không có), lấy giỏ của user, '
                                   'get_or_create dòng giỏ → (cart_item, created)', 'Lệnh'),
        4: ('28', {28}, 'D2: if not created (A) and cart_item.quantity < MAX_QUANTITY (B)', 'Điều kiện'),
        5: ('29–30', {29, 30}, 'cart_item.quantity += 1; cart_item.save()', 'Lệnh'),
        6: ('32', {32}, "return redirect('cart_detail')", 'Lệnh'),
        7: ('–', set(), 'Kết thúc', 'Kết thúc'),
    },
    'decisions': {1: 'D1', 4: 'D2'},
    'end': 7,
    'pos': {1: (1, 0), 2: (0, 1), 3: (2, 1), 4: (2, 2), 5: (1.3, 3), 6: (2, 4), 7: (1, 5)},
    'edges': [(1, 2, 'T'), (1, 3, 'F'), (2, 7, ''), (3, 4, ''), (4, 5, 'T'), (4, 6, 'F'),
              (5, 6, ''), (6, 7, '')],
    'branches': {(17, 18): ('D1', 'T'), (17, 20): ('D1', 'F'), (28, 29): ('D2', 'T'), (28, 32): ('D2', 'F')},
}
CART_DECREASE = {
    'func': 'cart_decrease', 'image': 'cfg_cart_decrease.png',
    'nodes': {
        1: ('59–63', {59, 60, 62, 63}, 'Lấy giỏ, lấy sản phẩm và dòng giỏ (404 nếu không có); '
                                       'cart_item.quantity -= 1', 'Lệnh'),
        2: ('65', {65}, 'D1: if cart_item.quantity <= 0', 'Điều kiện'),
        3: ('66', {66}, 'cart_item.delete() – xóa sản phẩm khỏi giỏ', 'Lệnh'),
        4: ('68', {68}, 'cart_item.save() – lưu số lượng mới', 'Lệnh'),
        5: ('70', {70}, "return redirect('cart_detail')", 'Kết thúc'),
    },
    'decisions': {2: 'D1'},
    'end': 5,
    'pos': {1: (1, 0), 2: (1, 1), 3: (0.35, 2), 4: (1.65, 2), 5: (1, 3)},
    'edges': [(1, 2, ''), (2, 3, 'T'), (2, 4, 'F'), (3, 5, ''), (4, 5, '')],
    'branches': {(65, 66): ('D1', 'T'), (65, 68): ('D1', 'F')},
}


# ---------------------------------------------------------------------------
# Đo độ phủ
# ---------------------------------------------------------------------------
def func_range(name):
    tree = ast.parse((ROOT / VIEWS).read_text(encoding='utf-8'))
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    return fn.body[0].lineno, fn.end_lineno          # bỏ dòng def/decorator


def views_entry(report):
    return next(v for k, v in report['files'].items() if k.replace('\\', '/').endswith(VIEWS))


def measure_cli(json_path, name):
    """Giống tools/coverage_func.py của Quân nhưng cho cart/views.py."""
    f = views_entry(json.loads(Path(json_path).read_text(encoding='utf-8')))
    lo, hi = func_range(name)
    inside = lambda n: lo <= n <= hi
    ex = [n for n in f['executed_lines'] if inside(n)]
    ms = [n for n in f['missing_lines'] if inside(n)]
    exb = [b for b in f.get('executed_branches', []) if inside(b[0])]
    msb = [b for b in f.get('missing_branches', []) if inside(b[0])]
    tl, tb = len(ex) + len(ms), len(exb) + len(msb)
    print(f'Hàm {name} (dòng {lo}-{hi})')
    print(f'Độ phủ dòng : {len(ex)}/{tl} = {len(ex) * 100 / tl:.1f}%')
    if tb:
        print(f'Độ phủ nhánh: {len(exb)}/{tb} = {len(exb) * 100 / tb:.1f}%')
    print('Dòng chưa chạy :', sorted(ms))
    print('Nhánh chưa chạy:', sorted(msb))


class Measurement:
    """Chạy test một lần với dynamic_context = test_function, giữ lại dòng/nhánh đã chạy của từng test."""

    def __init__(self):
        from coverage import CoverageData

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            data_file, rc, js = tmp / '.coverage', tmp / 'coveragerc', tmp / 'cov.json'
            rc.write_text('[run]\nbranch = True\nsource = cart\ndynamic_context = test_function\n'
                          f'data_file = {data_file.as_posix()}\n', encoding='utf-8')
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            proc = subprocess.run(
                [sys.executable, '-m', 'coverage', 'run', f'--rcfile={rc}', 'manage.py', 'test',
                 'cart.tests_whitebox', 'cart.tests', '-v', '2', '--noinput'],
                cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
            out = proc.stdout + proc.stderr
            if 'Ran ' not in out:
                print(out)
                sys.exit('Không chạy được test.')
            self.results = {m.group(2): 'PASS' if m.group(3) == 'ok' else 'FAIL'
                            for m in re.finditer(r'^(test_\w+) \((cart\.tests_whitebox\.[\w.]+)\) \.\.\. (\w+)',
                                                 out, re.M)}
            subprocess.run([sys.executable, '-m', 'coverage', 'json', f'--rcfile={rc}', '-q', '-o', str(js)],
                           cwd=ROOT, env=env, check=True)
            f = views_entry(json.loads(js.read_text(encoding='utf-8')))
            self.stmts = set(f['executed_lines']) | set(f['missing_lines'])
            self.arcs = {tuple(b) for b in f['executed_branches'] + f['missing_branches']}

            data = CoverageData(str(data_file))
            data.read()
            path = next(p for p in data.measured_files() if p.replace('\\', '/').endswith(VIEWS))
            self.contexts = sorted(c for c in data.measured_contexts() if c)
            self.hits = {}
            for ctx in self.contexts:
                data.set_query_contexts(['^' + re.escape(ctx) + '$'])
                self.hits[ctx] = (set(data.lines(path) or []), set(data.arcs(path) or []))

    def result(self, test_id):
        return self.results.get(test_id, 'FAIL')

    def cov(self, spec, ctxs):
        lo, hi = func_range(spec['func'])
        stmts = {n for n in self.stmts if lo <= n <= hi}
        arcs = {a for a in self.arcs if lo <= a[0] <= hi}
        lines, hit_arcs = set(), set()
        for c in ctxs:
            l, a = self.hits.get(c, (set(), set()))
            lines |= l & stmts
            hit_arcs |= a & arcs
        return Cov(spec, stmts, arcs, lines, hit_arcs)


class Cov:
    def __init__(self, spec, stmts, arcs, lines, hit_arcs):
        self.spec, self.stmts, self.arcs, self.lines, self.hit_arcs = spec, stmts, arcs, lines, hit_arcs
        self.s, self.n = len(lines), len(stmts)
        self.b, self.nb = len(hit_arcs), len(arcs)

    @property
    def path(self):
        nodes = [k for k, v in self.spec['nodes'].items() if v[1] & self.lines]
        if self.spec['end'] not in nodes:
            nodes.append(self.spec['end'])
        return '-'.join(map(str, nodes))

    @property
    def missing_lines(self):
        return sorted(self.stmts - self.lines)

    def branch_list(self):
        return ', '.join(' '.join(self.spec['branches'][a]) for a in sorted(self.hit_arcs))

    def value(self, decision):
        got = [tf for a, (d, tf) in self.spec['branches'].items() if d == decision and a in self.hit_arcs]
        return '/'.join(got) or '–'

    def missing_branches(self):
        miss = sorted(self.arcs - self.hit_arcs)
        names = {'T': 'True', 'F': 'False'}
        return ', '.join(f'{a}→{b} (nhánh {names[self.spec["branches"][(a, b)][1]]} của '
                         f'{self.spec["branches"][(a, b)][0]})' for a, b in miss)


def pct(a, b):
    v = a * 100 / b
    return f'{v:.0f}%' if v == int(v) else f'{v:.1f}%'.replace('.', ',')


def frac(a, b):
    return f'{a}/{b} = {pct(a, b)}'


def cyclomatic(spec):
    e, n, p = len(spec['edges']), len(spec['nodes']), len(spec['decisions'])
    assert e - n + 2 == p + 1, f'{spec["func"]}: E − N + 2 = {e - n + 2} nhưng P + 1 = {p + 1}'
    return e, n, p, p + 1


# ---------------------------------------------------------------------------
# Vẽ CFG (nút lệnh: hình tròn, nút điều kiện: hình thoi, nút kết thúc: 2 vòng tròn)
# ---------------------------------------------------------------------------
def load_font(size):
    from PIL import ImageFont
    for name in ('arial.ttf', 'DejaVuSans.ttf', 'segoeui.ttf'):
        for base in (Path('C:/Windows/Fonts'), Path('/usr/share/fonts/truetype/dejavu'), Path('')):
            try:
                return ImageFont.truetype(str(base / name), size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_cfg(spec, path):
    from PIL import Image, ImageDraw

    k = 3                                   # vẽ to gấp 3 rồi thu nhỏ cho nét mịn
    ux, uy, margin = 80, 88, 42
    r, dw, dh = 19, 36, 28
    xs = [p[0] for p in spec['pos'].values()]
    ys = [p[1] for p in spec['pos'].values()]
    width = int((max(xs) - min(xs)) * ux + 2 * margin)
    height = int((max(ys) - min(ys)) * uy + 2 * margin)
    img = Image.new('RGB', (width * k, height * k), 'white')
    d = ImageDraw.Draw(img)
    f_node, f_label = load_font(14 * k), load_font(12 * k)

    def at(n):
        x, y = spec['pos'][n]
        return ((x - min(xs)) * ux + margin) * k, ((y - min(ys)) * uy + margin) * k

    def reach(n, vx, vy):                   # khoảng cách từ tâm tới viền theo hướng (vx, vy)
        if n in spec['decisions']:
            return k / (abs(vx) / dw + abs(vy) / dh)
        return r * k

    for a, b, label in spec['edges']:
        (x1, y1), (x2, y2) = at(a), at(b)
        length = math.hypot(x2 - x1, y2 - y1)
        vx, vy = (x2 - x1) / length, (y2 - y1) / length
        sx, sy = x1 + vx * reach(a, vx, vy), y1 + vy * reach(a, vx, vy)
        ex, ey = x2 - vx * reach(b, -vx, -vy), y2 - vy * reach(b, -vx, -vy)
        head, half = 11 * k, 4.5 * k
        bx, by = ex - vx * head, ey - vy * head
        d.line([(sx, sy), (bx, by)], fill='black', width=int(1.3 * k))
        d.polygon([(ex, ey), (bx - vy * half, by + vx * half), (bx + vy * half, by - vx * half)], fill='black')
        if label:
            px, py = (-vy, vx) if -vy > 0 or (vy == 0 and vx < 0) else (vy, -vx)
            mx, my = sx + (ex - sx) * 0.42 + px * 9 * k, sy + (ey - sy) * 0.42 + py * 9 * k
            d.text((mx, my), label, font=f_label, fill='black', anchor='mm')

    for n in spec['nodes']:
        x, y = at(n)
        if n in spec['decisions']:
            d.polygon([(x, y - dh * k), (x + dw * k, y), (x, y + dh * k), (x - dw * k, y)],
                      fill=(255, 242, 204), outline='black', width=int(1.3 * k))
            d.text((x, y - 7 * k), str(n), font=f_node, fill='black', anchor='mm')
            d.text((x, y + 8 * k), spec['decisions'][n], font=f_node, fill='black', anchor='mm')
            continue
        d.ellipse([x - r * k, y - r * k, x + r * k, y + r * k], fill='white', outline='black', width=int(1.3 * k))
        if n == spec['end']:
            ri = (r - 4) * k
            d.ellipse([x - ri, y - ri, x + ri, y + ri], outline='black', width=int(1.3 * k))
        d.text((x, y), str(n), font=f_node, fill='black', anchor='mm')

    img = img.resize((width, height), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# Ghi sheet (cùng định dạng sheet WhiteBox_Quân / WhiteBox_Huy)
# ---------------------------------------------------------------------------
WIDTHS = {'A': 14, 'B': 32, 'C': 22, 'D': 14, 'E': 36, 'F': 58, 'G': 10, 'H': 3}
IMG_COL = 'I'


class SheetWriter:
    """Ghi sheet theo định dạng chung của nhóm (Calibri 11, tiêu đề bảng nền D9E1F2, viền mảnh).
    Dùng chung cho build_cart_state_transition_report.py."""

    def __init__(self, ws, widths=None, text_span='A:G'):
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        self.ws, self.r = ws, 1
        self.widths = widths or WIDTHS
        self.text_span = text_span
        self.Alignment, self.PatternFill = Alignment, PatternFill
        self.font = Font(name='Calibri', size=11)
        self.bold = Font(name='Calibri', size=11, bold=True)
        self.title_font = Font(name='Calibri', size=12, bold=True)
        self.head_fill = PatternFill('solid', fgColor='D9E1F2')
        thin = Side(style='thin')
        self.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for col, w in self.widths.items():
            ws.column_dimensions[col].width = w

    @staticmethod
    def cols(span):
        from openpyxl.utils import column_index_from_string
        a, _, b = span.partition(':')
        return column_index_from_string(a), column_index_from_string(b or a)

    def span_width(self, span):
        from openpyxl.utils import get_column_letter
        a, b = self.cols(span)
        return sum(self.widths.get(get_column_letter(i), 8.43) for i in range(a, b + 1))

    def fit(self, cells):
        lines = 1
        for value, span in cells:
            chars = max(self.span_width(span) - 1, 4)
            n = sum(max(1, math.ceil(len(part) * 0.9 / chars)) for part in str(value).split('\n'))
            lines = max(lines, n)
        self.ws.row_dimensions[self.r].height = max(15.75, 15 * lines + 1)

    def cells(self, items, header=False, boxed=True):
        """items: [(giá trị, 'A' hoặc 'C:E', căn lề[, màu nền])]"""
        for value, span, align, *fill in items:
            a, b = self.cols(span)
            if b > a:
                self.ws.merge_cells(start_row=self.r, start_column=a, end_row=self.r, end_column=b)
            for c in range(a, b + 1):
                cell = self.ws.cell(row=self.r, column=c)
                if boxed:
                    cell.border = self.border
                if header:
                    cell.fill = self.head_fill
                elif fill and fill[0]:
                    cell.fill = self.PatternFill('solid', fgColor=fill[0])
            cell = self.ws.cell(row=self.r, column=a, value=value)
            cell.font = self.bold if header else self.font
            cell.alignment = self.Alignment(horizontal='center' if header else align, vertical='center',
                                            wrap_text=True)
        self.fit([(item[0], item[1]) for item in items])
        self.r += 1

    def text(self, value, bold=False, title=False, gap=0):
        a, b = self.cols(self.text_span)
        self.ws.merge_cells(start_row=self.r, start_column=a, end_row=self.r, end_column=b)
        cell = self.ws.cell(row=self.r, column=a, value=value)
        cell.font = self.title_font if title else self.bold if bold else self.font
        cell.alignment = self.Alignment(vertical='center', wrap_text=True)
        self.fit([(value, self.text_span)])
        self.r += 1 + gap

    def answer(self, value):
        self.text('     → ' + value)

    def table(self, columns, rows):
        """columns: [(tiêu đề, span, căn lề)]; rows: list các list giá trị, hoặc list (giá trị, span, căn lề)."""
        self.cells([(title, span, 'center') for title, span, _ in columns], header=True)
        for row in rows:
            if row and isinstance(row[0], tuple):
                self.cells(row)
            else:
                self.cells([(v, span, align) for v, (_, span, align) in zip(row, columns)])

    def gap(self, n=1):
        self.r += n

    def image(self, path, row):
        from openpyxl.drawing.image import Image as XLImage
        self.ws.add_image(XLImage(str(path)), f'{IMG_COL}{row}')


NODE_COLS = [('Nút', 'A', 'center'), ('Dòng code', 'B', 'center'), ('Nội dung', 'C:E', 'left'),
             ('Loại nút', 'F', 'center')]
VG_COLS = [('Công thức', 'A:B', 'left'), ('Thay số', 'C:E', 'left'), ('V(G)', 'F', 'center')]
END_COLS = [('Độ phức tạp Cyclomatic', 'A:B', 'center'), ('Số test nhỏ nhất: Statement coverage', 'C:D', 'center'),
            ('Số test nhỏ nhất: Branch coverage', 'E', 'center'), ('Tổ hợp điều kiện', 'F', 'center')]


def tc_cols(input_title, cover_title):
    return [('Test case', 'A', 'center'), (input_title, 'B', 'left'), ('Đường đi (nút)', 'C', 'center'),
            (cover_title, 'D', 'center'), ('Expected output', 'E', 'left'),
            ('Unit test (tests_whitebox.py)', 'F', 'left'), ('Kết quả', 'G', 'center')]


def total_row(value, note):
    return [('Tổng', 'A', 'center'), ('', 'B', 'left'), ('', 'C', 'center'), (value, 'D', 'center'),
            (note, 'E:G', 'left')]


def measured_note(today, c):
    note = f'Đo bằng coverage.py --branch ({today}): câu lệnh {frac(c.s, c.n)}, nhánh {frac(c.b, c.nb)}'
    if c.b < c.nb:
        note += f'. Nhánh chưa chạy: {c.missing_branches()}'
    return note


def write_cfg_and_vg(w, spec, image_path, note):
    w.text('I. ĐỒ THỊ LUỒNG ĐIỀU KHIỂN (hình bên phải; nút hình thoi là nút điều kiện)', bold=True)
    w.image(image_path, w.r - 1)
    w.table(NODE_COLS, [[str(n), line, content, kind] for n, (line, _, content, kind) in spec['nodes'].items()])
    w.text(note)
    w.gap()
    e, n, p, v = cyclomatic(spec)
    names = ', '.join(spec['decisions'].values())
    w.text('II. ĐỘ PHỨC TẠP CYCLOMATIC', bold=True)
    w.table(VG_COLS, [
        ['V(G) = E − N + 2', f'E = {e} cạnh, N = {n} nút → {e} − {n} + 2', str(v)],
        ['V(G) = P + 1', f'P = {p} nút điều kiện ({names}) → {p} + 1', str(v)],
        ['V(G) = R', f'R = {v - 1} miền kín + 1 miền ngoài', str(v)],
    ])
    w.gap()
    return v


def write_part1(w, m, today, img):
    s = CART_ADD
    c = {k: m.cov(s, [CTX[k]]) for k in ('ADD-S1', 'ADD-S2', 'ADD-B3', 'ADD-C1', 'ADD-C2', 'ADD-C3', 'EP-01', 'EP-04')}
    stmt_suite = m.cov(s, [CTX['ADD-S1'], CTX['ADD-S2']])
    branch_suite = m.cov(s, [CTX['ADD-S1'], CTX['ADD-S2'], CTX['ADD-B3']])
    bb =m.cov(s, [x for x in m.contexts if x.startswith(BB)])
    n_bb = len([x for x in m.contexts if x.startswith(BB)])
    assert stmt_suite.s == stmt_suite.n and stmt_suite.b < stmt_suite.nb, 'Bộ phủ câu lệnh cart_add không như phân tích'
    assert branch_suite.b == branch_suite.nb, 'Bộ phủ nhánh cart_add chưa đạt 100%'
    assert c['ADD-C1'].value('D2') == 'T' and c['ADD-C2'].value('D2') == 'F' and c['ADD-C3'].value('D2') == 'F'
    n = stmt_suite.n

    w.text('PHẦN 1 – KIỂM THỬ HỘP TRẮNG (Control Flow Testing): Thêm sản phẩm vào giỏ – cart/views.py, '
           'hàm cart_add, dòng 16–32', title=True, gap=1)
    v = write_cfg_and_vg(w, s, img, 'Ghi chú: get_object_or_404 (dòng 20) và get_or_create (dòng 23) là lời gọi '
                                    'hàm của Django, không phải lệnh if trong hàm, nên được gộp vào nút lệnh 3.')

    w.text('III. BAO PHỦ CÂU LỆNH (Statement coverage)', bold=True)
    w.text('1. Có bao nhiêu câu lệnh?', bold=True)
    w.answer(f'{n} câu lệnh: dòng {", ".join(map(str, sorted(stmt_suite.stmts)))}')
    w.text('2. Test case TC-CART-EP-04 (đã đăng nhập, giỏ rỗng, thêm A) bao phủ bao nhiêu % câu lệnh?', bold=True)
    e4 = c['EP-04']
    w.answer(f'{frac(e4.s, n)}  (đi qua nút {e4.path}; thiếu dòng {", ".join(map(str, e4.missing_lines))})')
    w.text('   Test case TC-CART-EP-01 (chưa đăng nhập, thêm A) bao phủ bao nhiêu % câu lệnh?', bold=True)
    e1 = c['EP-01']
    w.answer(f'{frac(e1.s, n)}  (đi qua nút {e1.path})')
    w.text('3. Tối thiểu bao nhiêu test case để bao phủ 100% câu lệnh?', bold=True)
    w.answer('2 test case (bảng dưới). Nhánh True của D1 kết thúc hàm ngay bằng return, nên 1 test case '
             'không thể chạy cả dòng 18 lẫn các dòng 20–32.')
    w.gap()
    cls = 'CartAddStatementTests.'
    w.table(tc_cols('Input (GET /cart/add/<id>/)', 'Câu lệnh phủ'), [
        ['WB-ADD-S1', 'Chưa đăng nhập; thêm A', c['ADD-S1'].path, f'{c["ADD-S1"].s}/{n}',
         '302 → /accounts/login/?next=/cart/add/<A>/, không tạo CartItem',
         cls + 'test_wb_add_s1_chua_dang_nhap', m.result(CTX['ADD-S1'])],
        ['WB-ADD-S2', 'Đã đăng nhập; giỏ có A × 1; thêm A', c['ADD-S2'].path, f'{c["ADD-S2"].s}/{n}',
         '302 → /cart/, A có quantity = 2', cls + 'test_wb_add_s2_san_pham_da_co_trong_gio',
         m.result(CTX['ADD-S2'])],
        total_row(frac(stmt_suite.s, n), measured_note(today, stmt_suite)),
    ])
    w.gap()

    nb = branch_suite.nb
    w.text('IV. BAO PHỦ NHÁNH (Decision/Branch coverage)', bold=True)
    w.text('1. Có bao nhiêu nhánh?', bold=True)
    w.answer(f'{nb} nhánh = {len(s["decisions"])} nút điều kiện × 2 (True, False)')
    w.text('2. Test case TC-CART-EP-04 bao phủ bao nhiêu % nhánh?', bold=True)
    w.answer(f'{frac(e4.b, nb)}  ({e4.branch_list()})')
    w.text('   Test case TC-CART-EP-01 bao phủ bao nhiêu % nhánh?', bold=True)
    w.answer(f'{frac(e1.b, nb)}  ({e1.branch_list()})')
    w.text('3. Tối thiểu bao nhiêu test case để bao phủ 100% nhánh?', bold=True)
    w.answer('3 test case. D1 T kết thúc hàm ngay nên cần 1 test riêng; khi D1 F, hai nhánh D2 T và D2 F '
             'cần 2 lần chạy khác nhau.')
    w.gap()
    ids = ['ADD-S1', 'ADD-S2', 'ADD-B3']
    w.table([('Nhánh', 'A', 'center'), ('Ý nghĩa', 'B', 'left')] +
            [(f'WB-{k}', col, 'center') for k, col in zip(ids, 'CDE')], [
        ['D1 T / D1 F', 'Chưa / đã đăng nhập'] + [c[k].value('D1') for k in ids],
        ['D2 T / D2 F', 'Tăng / không tăng số lượng'] + [c[k].value('D2') for k in ids],
        ['Số nhánh phủ', ''] + [f'{c[k].b}/{nb}' for k in ids],
    ])
    w.gap()
    cls = 'CartAddBranchTests.'
    w.table(tc_cols('Input (GET /cart/add/<id>/)', 'Nhánh phủ'), [
        ['WB-ADD-S1', 'Chưa đăng nhập; thêm A', c['ADD-S1'].path, f'{c["ADD-S1"].b}/{nb}',
         '302 → trang đăng nhập, không tạo CartItem', cls + 'test_wb_add_s1_chua_dang_nhap',
         m.result(WB + cls + 'test_wb_add_s1_chua_dang_nhap')],
        ['WB-ADD-S2', 'Đã đăng nhập; giỏ có A × 1; thêm A', c['ADD-S2'].path, f'{c["ADD-S2"].b}/{nb}',
         'A có quantity = 2', cls + 'test_wb_add_s2_san_pham_da_co_trong_gio',
         m.result(WB + cls + 'test_wb_add_s2_san_pham_da_co_trong_gio')],
        ['WB-ADD-B3', 'Đã đăng nhập; giỏ rỗng; thêm A', c['ADD-B3'].path, f'{c["ADD-B3"].b}/{nb}',
         'A được thêm với quantity = 1', cls + 'test_wb_add_b3_gio_rong', m.result(CTX['ADD-B3'])],
        total_row(frac(branch_suite.b, nb), measured_note(today, branch_suite)),
    ])
    w.gap()

    w.text('V. BAO PHỦ ĐIỀU KIỆN cho nút điều kiện ghép D2: A = not created (sản phẩm đã có trong giỏ),  '
           'B = cart_item.quantity < MAX_QUANTITY (chưa đạt 2.147.483.647)', bold=True)
    w.text('Bao phủ điều kiện: A và B đều phải nhận T và F. Chỉ cần WB-ADD-C2 (A T, B F) và WB-ADD-C3 (A F, B T) '
           'là đủ, nhưng cả hai đều cho D2 = F nên không bao phủ nhánh.')
    w.text('Bao phủ nhánh – điều kiện: thêm WB-ADD-C1 (A T, B T → D2 T) → 3 test WB-ADD-C1, C2, C3.')
    w.text('Bao phủ tổ hợp điều kiện: có 4 tổ hợp, nhưng A F – B F không xảy ra được vì dòng giỏ vừa tạo luôn có '
           'quantity = 1 < MAX. Còn 3 tổ hợp khả thi → 3 test case.')
    w.text('Bao phủ nhánh không bắt buộc thử A T – B F (sản phẩm đã ở số lượng tối đa). Đây chính là trường hợp của '
           'lỗi BUG-CART-01: trước khi sửa, thêm sản phẩm đang có 2.147.483.647 sẽ lưu 2.147.483.648.')
    w.gap()
    cols = [('Test case', 'A', 'center'), ('A', 'B', 'center'), ('B', 'C', 'center'), ('D2', 'D', 'center'),
            ('Input', 'E', 'left'), ('Expected output', 'F', 'left'), ('Kết quả', 'G', 'center')]
    w.table(cols, [
        ['WB-ADD-C1', 'T', 'T', c['ADD-C1'].value('D2'), 'Giỏ có A × 1; thêm A', 'quantity = 2',
         m.result(CTX['ADD-C1'])],
        ['WB-ADD-C2', 'T', 'F', c['ADD-C2'].value('D2'), 'Giỏ có A × 2.147.483.647; thêm A',
         'Giữ quantity = 2.147.483.647, không lỗi', m.result(CTX['ADD-C2'])],
        ['WB-ADD-C3', 'F', '(T)', c['ADD-C3'].value('D2'), 'Giỏ rỗng; thêm A',
         'A được thêm với quantity = 1', m.result(CTX['ADD-C3'])],
        ['–', 'F', 'F', '–', 'Không khả thi', '–', '–'],
    ])
    w.text('(T): Python không xét B vì A đã sai (toán tử and ngắt mạch); nếu được xét, B nhận T vì dòng mới có '
           'quantity = 1.')
    w.gap()

    w.text('VI. KẾT LUẬN', bold=True)
    w.table(END_COLS[:3] + [('Tổ hợp điều kiện (D2)', 'F', 'center')], [[str(v), '2', '3', '3 (khả thi)']])
    w.gap()
    if bb.s == bb.n and bb.b == bb.nb:
        w.text(f'So sánh: {n_bb} TC EP/BVA hộp đen (cart/tests.py) cũng đạt 100% câu lệnh và 100% nhánh của cart_add, '
               'còn bộ hộp trắng chỉ cần 3 test chọn theo nhánh để đạt cùng mức.')
    else:
        w.text(f'So sánh: {n_bb} TC EP/BVA hộp đen (cart/tests.py) chỉ đạt {frac(bb.s, bb.n)} câu lệnh và '
               f'{frac(bb.b, bb.nb)} nhánh của cart_add, còn 3 test chọn theo nhánh đã đạt 100%.')
    w.text('Độ phủ phụ thuộc cách chọn test case, không phụ thuộc số lượng. Độ bao phủ 100% cũng không có nghĩa là '
           'đã test 100%: 3 test phủ nhánh không có trường hợp A T – B F của BUG-CART-01, phải thêm bao phủ điều kiện '
           '(WB-ADD-C2) mới kiểm tra được.')


def write_part2(w, m, today, img):
    s = CART_DECREASE
    c = {k: m.cov(s, [CTX[k]]) for k in ('DEC-S1', 'DEC-S2', 'BVA-07', 'BVA-08')}
    suite = m.cov(s, [CTX['DEC-S1'], CTX['DEC-S2']])
    bva = m.cov(s, [CTX['BVA-07'], CTX['BVA-08']])
    assert suite.s == suite.n and suite.b == suite.nb, 'Bộ test cart_decrease chưa đạt 100%'
    n, nb = suite.n, suite.nb

    w.text('PHẦN 2 – KIỂM THỬ HỘP TRẮNG (Control Flow Testing): Giảm số lượng sản phẩm trong giỏ – cart/views.py, '
           'hàm cart_decrease, dòng 57–70', title=True, gap=1)
    v = write_cfg_and_vg(w, s, img, 'Ghi chú: @login_required (dòng 57) chặn khách chưa đăng nhập trước khi vào hàm, '
                                    'nên không nằm trong đồ thị của hàm.')

    w.text('III. BAO PHỦ CÂU LỆNH (Statement coverage)', bold=True)
    w.text('1. Có bao nhiêu câu lệnh?', bold=True)
    w.answer(f'{n} câu lệnh: dòng {", ".join(map(str, sorted(suite.stmts)))}')
    for key, label in (('BVA-07', 'TC-CART-BVA-07 (giỏ có A × 1, giảm A)'),
                       ('BVA-08', 'TC-CART-BVA-08 (giỏ có A × 2, giảm A)')):
        prefix = '2. ' if key == 'BVA-07' else '   '
        w.text(f'{prefix}Test case {label} bao phủ bao nhiêu % câu lệnh?', bold=True)
        x = c[key]
        w.answer(f'{frac(x.s, n)}  (đi qua nút {x.path}; thiếu dòng {", ".join(map(str, x.missing_lines))})')
    w.text('3. Tối thiểu bao nhiêu test case để bao phủ 100% câu lệnh?', bold=True)
    w.answer('2 test case (bảng dưới). Nhánh if (dòng 66) và nhánh else (dòng 68) đều có lệnh riêng nên 1 test case '
             'không đủ.')
    w.gap()
    cls = 'CartDecreaseStatementTests.'
    w.table(tc_cols('Input (GET /cart/decrease/<id>/)', 'Câu lệnh phủ'), [
        ['WB-DEC-S1', 'Đã đăng nhập; giỏ có A × 1; giảm A', c['DEC-S1'].path, f'{c["DEC-S1"].s}/{n}',
         '302 → /cart/, A bị xóa khỏi giỏ', cls + 'test_wb_dec_s1_so_luong_1_bi_xoa', m.result(CTX['DEC-S1'])],
        ['WB-DEC-S2', 'Đã đăng nhập; giỏ có A × 2; giảm A', c['DEC-S2'].path, f'{c["DEC-S2"].s}/{n}',
         '302 → /cart/, A còn quantity = 1', cls + 'test_wb_dec_s2_so_luong_2_con_1', m.result(CTX['DEC-S2'])],
        total_row(frac(suite.s, n), measured_note(today, suite)),
    ])
    w.gap()

    w.text('IV. BAO PHỦ NHÁNH (Decision/Branch coverage)', bold=True)
    w.text('1. Có bao nhiêu nhánh?', bold=True)
    w.answer(f'{nb} nhánh = {len(s["decisions"])} nút điều kiện × 2 (True, False)')
    w.text('2. Test case TC-CART-BVA-07 bao phủ bao nhiêu % nhánh?', bold=True)
    w.answer(f'{frac(c["BVA-07"].b, nb)}  ({c["BVA-07"].branch_list()})')
    w.text('3. Tối thiểu bao nhiêu test case để bao phủ 100% nhánh?', bold=True)
    w.answer(f'2 test case: WB-DEC-S1 ({c["DEC-S1"].branch_list()}) và WB-DEC-S2 ({c["DEC-S2"].branch_list()}) '
             'ở bảng trên')
    w.gap()

    w.text('V. BAO PHỦ ĐIỀU KIỆN: D1 chỉ có 1 điều kiện đơn (quantity <= 0, sau khi đã trừ 1)', bold=True)
    w.text('D1 không có điều kiện ghép nên bao phủ điều kiện, bao phủ nhánh – điều kiện và bao phủ tổ hợp điều kiện '
           'đều trùng với bao phủ nhánh: điều kiện nhận T ở WB-DEC-S1 và F ở WB-DEC-S2.')
    w.gap()
    w.table([('Test case', 'A', 'center'), ('quantity <= 0', 'B', 'center'), ('D1', 'C', 'center'),
             ('Input', 'D:E', 'left'), ('Expected output', 'F', 'left'), ('Kết quả', 'G', 'center')], [
        ['WB-DEC-S1', 'T (1 − 1 = 0)', c['DEC-S1'].value('D1'), 'Giỏ có A × 1; giảm A', 'A bị xóa khỏi giỏ',
         m.result(CTX['DEC-S1'])],
        ['WB-DEC-S2', 'F (2 − 1 = 1)', c['DEC-S2'].value('D1'), 'Giỏ có A × 2; giảm A', 'A còn quantity = 1',
         m.result(CTX['DEC-S2'])],
    ])
    w.gap()

    w.text('VI. KẾT LUẬN', bold=True)
    w.table(END_COLS[:3] + [('Tổ hợp điều kiện (D1)', 'F', 'center')], [[str(v), '2', '2', '2']])
    w.gap()
    if bva.s == bva.n and bva.b == bva.nb:
        w.text('So sánh: 2 TC BVA hộp đen TC-CART-BVA-07 và TC-CART-BVA-08 (giảm từ 1 và từ 2) đi đúng 2 nhánh của D1, '
               'nên riêng 2 TC này đã đạt 100% câu lệnh và 100% nhánh của cart_decrease.')
    else:
        w.text(f'So sánh: TC-CART-BVA-07 và TC-CART-BVA-08 đạt {frac(bva.s, bva.n)} câu lệnh và '
               f'{frac(bva.b, bva.nb)} nhánh của cart_decrease.')
    w.text('Với điều kiện đơn, chọn giá trị biên quanh điểm quyết định (quantity = 1 và 2) cũng chính là chọn test '
           'theo nhánh.')


def write_howto(w):
    w.text('CÁCH CHẠY VÀ ĐO ĐỘ PHỦ', bold=True)
    for line in ('python manage.py test cart.tests_whitebox -v 2',
                 'coverage erase',
                 'coverage run --branch --source=cart manage.py test cart.tests_whitebox.<TênClass>',
                 'coverage json -o coverage.json',
                 'python tools/build_cart_whitebox_report.py --measure coverage.json cart_add      '
                 '(hoặc cart_decrease)',
                 'python tools/build_cart_whitebox_report.py      '
                 '(tạo lại sheet WhiteBox_Phong và ảnh CFG; đóng Report.xlsx trước khi chạy)'):
        w.text(line)


def build_sheet(m):
    import openpyxl

    today = datetime.date.today().strftime('%d/%m/%Y')
    img_add = draw_cfg(CART_ADD, IMG_DIR / CART_ADD['image'])
    img_dec = draw_cfg(CART_DECREASE, IMG_DIR / CART_DECREASE['image'])

    wb = openpyxl.load_workbook(REPORT)
    index = None
    for name in OLD_SHEETS:
        if name in wb.sheetnames:
            index = wb.sheetnames.index(name) if index is None else index
            wb.remove(wb[name])
    if index is None:
        phong = [i for i, n in enumerate(wb.sheetnames) if n.startswith('Phong_')]
        index = phong[-1] + 1 if phong else len(wb.sheetnames)
    ws = wb.create_sheet(SHEET, index)

    w = SheetWriter(ws)
    write_part1(w, m, today, img_add)
    w.gap(2)
    write_part2(w, m, today, img_dec)
    w.gap(2)
    write_howto(w)
    try:
        wb.save(REPORT)
    except PermissionError:
        sys.exit(f'Không ghi được {REPORT}: hãy đóng file Excel rồi chạy lại.')
    return ws.max_row


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 4 and sys.argv[1] == '--measure':
        measure_cli(sys.argv[2], sys.argv[3])
        return
    os.chdir(ROOT)
    print('Đang chạy cart.tests_whitebox và cart.tests với coverage.py ...')
    m = Measurement()
    wb_tests = {k: v for k, v in m.results.items()}
    failed = [k for k, v in wb_tests.items() if v != 'PASS']
    print(f'Hộp trắng: {len(wb_tests) - len(failed)}/{len(wb_tests)} PASS' + (f', FAIL: {failed}' if failed else ''))
    rows = build_sheet(m)
    print(f'Đã ghi sheet {SHEET} ({rows} dòng) vào {REPORT.relative_to(ROOT)} và ảnh CFG vào '
          f'{IMG_DIR.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
