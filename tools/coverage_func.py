"""
Đọc coverage.json (do `coverage json` tạo ra) và in độ phủ DÒNG + NHÁNH
chỉ riêng hàm admin_order_list trong admin_panel/views.py.

Cách dùng (xem hướng dẫn đầy đủ trong file Excel / tin nhắn):
  coverage run --branch --source=admin_panel manage.py runserver --noreload
  (chạy CodeceptJS ở terminal khác, xong thì Ctrl+C dừng server)
  coverage json -o coverage.json
  python tools/coverage_func.py coverage.json [tên_hàm]
  (mặc định đo admin_order_list; thêm tên hàm để đo hàm khác trong admin_panel/views.py)
"""
import ast
import json
import sys
from pathlib import Path

FUNC = sys.argv[2] if len(sys.argv) > 2 else "admin_order_list"   # ví dụ: admin_order_update_status
data = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else "coverage.json").read_text(encoding="utf-8"))
key = next(k for k in data["files"] if k.replace("\\", "/").endswith("admin_panel/views.py"))
f = data["files"][key]

tree = ast.parse(Path("admin_panel/views.py").read_text(encoding="utf-8"))
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == FUNC)
lo, hi = fn.body[0].lineno, fn.end_lineno          # bỏ dòng def/decorator
inside = lambda n: lo <= n <= hi

ex = [n for n in f["executed_lines"] if inside(n)]
ms = [n for n in f["missing_lines"] if inside(n)]
exb = [b for b in f.get("executed_branches", []) if inside(b[0])]
msb = [b for b in f.get("missing_branches", []) if inside(b[0])]

tl, tb = len(ex) + len(ms), len(exb) + len(msb)
print(f"Hàm {FUNC} (dòng {lo}-{hi})")
print(f"Độ phủ dòng : {len(ex)}/{tl} = {len(ex)*100/tl:.1f}%")
if tb:
    print(f"Độ phủ nhánh: {len(exb)}/{tb} = {len(exb)*100/tb:.1f}%")
print("Dòng chưa chạy :", sorted(ms))
print("Nhánh chưa chạy:", sorted(msb))
