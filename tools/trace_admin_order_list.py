"""
Đo độ phủ DÒNG và NHÁNH của hàm admin_order_list khi chạy bộ test BVA,
KHÔNG cần cài Django hay coverage.

Cách làm: lấy nguyên mã nguồn hàm admin_order_list từ admin_panel/views.py,
chạy nó với các đối tượng giả (Order, Q, render) để không cần cơ sở dữ liệu,
ghi lại từng dòng được thực thi (sys.settrace), rồi tính:
  - độ phủ dòng  = số câu lệnh được chạy / tổng số câu lệnh trong hàm
  - độ phủ nhánh = số nhánh (True/False của mỗi if) được chạy / tổng số nhánh

Chạy:  python tools/trace_admin_order_list.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIEWS = ROOT / "admin_panel" / "views.py"
FUNC = "admin_order_list"

# ---------- Đối tượng giả ----------
class Q:
    def __init__(self, **kw): self.kw = kw
    def __or__(self, other): return self
    __ior__ = __or__

class _QS:
    def __getattr__(self, name):
        return lambda *a, **k: self
    def filter(self, *a, **k): return self
    def none(self): return self

class Order:
    STATUS_CHOICES = (("pending", "Chờ xử lý"), ("awaiting_transfer", "Chờ chuyển khoản"),
        ("paid", "Đã thanh toán"), ("failed", "Thanh toán thất bại"), ("confirmed", "Đã xác nhận"),
        ("shipping", "Đang giao"), ("completed", "Hoàn thành"), ("cancelled", "Đã hủy"))
    PAYMENT_METHOD_CHOICES = (("cod", "COD"), ("qr", "QR"), ("mock", "Mock"))
    objects = _QS()

class Request:
    def __init__(self, params): self.GET = params

def render(request, template, context): return context

# ---------- Lấy nguyên hàm từ views.py ----------
src = VIEWS.read_text(encoding="utf-8")
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == FUNC)
fn.decorator_list = []                      # bỏ @admin_required (cần DB/đăng nhập)
code = compile(ast.Module(body=[fn], type_ignores=[]), str(VIEWS), "exec")
ns = {"Order": Order, "Q": Q, "render": render}
exec(code, ns)
view = ns[FUNC]

# ---------- Cấu trúc câu lệnh / nhánh ----------
stmts = [n for n in ast.walk(fn) if isinstance(n, ast.stmt) and n is not fn]
stmt_lines = sorted({n.lineno for n in stmts})
def stmt_of(line):
    best = None
    for n in stmts:
        if n.lineno <= line <= (n.end_lineno or n.lineno):
            if best is None or n.lineno >= best.lineno: best = n
    return best.lineno if best else None
ifs = [n for n in ast.walk(fn) if isinstance(n, ast.If)]

# ---------- Chạy và ghi vết ----------
events = []          # dãy dòng đã chạy theo thứ tự, mỗi lần gọi hàm một đoạn
def run(params):
    seq = []
    def tracer(frame, event, arg):
        if frame.f_code.co_filename != str(VIEWS): return tracer
        if event == "line":
            s = stmt_of(frame.f_lineno)
            if s: seq.append(s)
        return tracer
    sys.settrace(tracer)
    try: view(Request(params))
    finally: sys.settrace(None)
    events.append(seq)

def report(title, cases):
    events.clear()
    for p in cases: run(p)
    hit = {l for seq in events for l in seq}
    br_hit, br_all = set(), []
    for n in ifs:
        body_first = n.body[0].lineno
        else_first = n.orelse[0].lineno if n.orelse else None
        br_all += [(n.lineno, "True"), (n.lineno, "False")]
        for seq in events:
            for i, l in enumerate(seq):
                if l != n.lineno: continue
                nxt = seq[i + 1] if i + 1 < len(seq) else None
                if nxt == body_first: br_hit.add((n.lineno, "True"))
                else: br_hit.add((n.lineno, "False"))
    nl, nh = len(stmt_lines), len(hit & set(stmt_lines))
    nb, nbh = len(br_all), len(br_hit)
    print(f"\n== {title} ==")
    print(f"Độ phủ dòng : {nh}/{nl} = {nh*100/nl:.1f}%")
    print(f"Độ phủ nhánh: {nbh}/{nb} = {nbh*100/nb:.1f}%")
    miss = [l for l in stmt_lines if l not in hit]
    print("Dòng chưa chạy :", miss)
    print("Nhánh chưa chạy:", [f"dòng {l} ({b})" for l, b in br_all if (l, b) not in br_hit])
    return nh, nl, nbh, nb

def branches_of(params):
    """Trả về (tập dòng, tập nhánh) mà RIÊNG test case này thực thi."""
    events.clear(); run(params)
    seq = events[0]
    lines = set(seq)
    brs = set()
    for n in ifs:
        body_first = n.body[0].lineno
        for i, l in enumerate(seq):
            if l == n.lineno:
                nxt = seq[i + 1] if i + 1 < len(seq) else None
                brs.add((n.lineno, "True" if nxt == body_first else "False"))
    return lines, brs

# 14 test case BVA (mỗi ca chỉ đổi từ khóa, không có bộ lọc trạng thái / thanh toán)
PHONE = "09123456781234567890"
BVA = [{"keyword": PHONE[:n]} for n in (10, 5, 6, 7, 19, 20, 21)] + \
      [{"keyword": str(k)} for k in (0, 1, 2, 4, 8, 9, 10)]

# Các test case bổ sung từ bảng quyết định (lọc và từ khóa dạng #id)
EXTRA = [{"keyword": "#5"}, {"keyword": "Nguyen"}, {"keyword": "Ng"},
         {"status": "paid"}, {"status": "hacked"}, {"payment_method": "qr"},
         {"payment_method": "hacked"}]

if __name__ == "__main__":
    print("Hàm:", FUNC, "trong", VIEWS.name)
    report("Chỉ 14 TC BVA tìm kiếm", BVA)
    report("14 TC BVA + 7 TC bổ sung từ bảng quyết định", BVA + EXTRA)
