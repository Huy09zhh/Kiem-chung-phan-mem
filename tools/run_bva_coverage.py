"""Kịch bản tự động hóa thực thi:
1. Seed dữ liệu BVA cho Orders
2. Khởi chạy Django server với coverage: coverage run --branch --source=orders manage.py runserver --noreload 8000
3. Chờ server sẵn sàng trên http://127.0.0.1:8000/
4. Chạy CodeceptJS E2E test cho phân hệ orders: npx codeceptjs run tests/orders_checkout_bva_test.js --steps
5. Dừng server an toàn để coverage ghi file .coverage
6. Chạy coverage report -m và phân tích chi tiết độ phủ dòng/nhánh
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = PROJECT_DIR.parent / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

print(f"[1/6] Sử dụng Python: {PYTHON_EXE}")
print(f"[1/6] Thư mục dự án: {PROJECT_DIR}")

# 1. Seed dữ liệu
print("\n[2/6] Seed dữ liệu Orders BVA...")
subprocess.run([str(PYTHON_EXE), "manage.py", "seed_orders_bva"], cwd=PROJECT_DIR, check=True)

# 2. Xóa dữ liệu coverage cũ nếu có
cov_file = PROJECT_DIR / ".coverage"
if cov_file.exists():
    cov_file.unlink()

# 3. Khởi chạy server Django với coverage
print("\n[3/6] Khởi chạy Django server với coverage run --branch --source=orders...")
server_cmd = [
    str(PYTHON_EXE),
    "-m", "coverage", "run",
    "--branch",
    "--source=orders",
    "manage.py", "runserver",
    "--noreload", "8000"
]

server_log_file = open(PROJECT_DIR / "django_server.log", "w", encoding="utf-8")
server_proc = subprocess.Popen(
    server_cmd,
    cwd=PROJECT_DIR,
    stdout=server_log_file,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
)

# Chờ server khởi động
server_ready = False
for i in range(25):
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8000/accounts/login/", timeout=2)
        if resp.status in (200, 302):
            server_ready = True
            print(f" -> Server đã sẵn sàng sau {i+1}s (HTTP {resp.status})!")
            break
    except Exception:
        time.sleep(1)

if not server_ready:
    print("❌ Lỗi: Server Django không khởi động kịp thời!")
    server_proc.kill()
    sys.exit(1)

# 4. Chạy CodeceptJS test
print("\n[4/6] Chạy kịch bản kiểm thử E2E CodeceptJS: tests/orders_checkout_bva_test.js...")
test_cmd = "npx codeceptjs run tests/orders_checkout_bva_test.js --steps"
test_proc = subprocess.run(test_cmd, cwd=PROJECT_DIR, shell=True)

# 5. Dừng server Django an toàn để coverage flush dữ liệu
print("\n[5/6] Dừng server Django và hoàn tất lưu kết quả coverage...")
try:
    urllib.request.urlopen("http://127.0.0.1:8000/dev/shutdown/", timeout=3)
except Exception:
    pass

try:
    server_proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    if sys.platform == "win32":
        server_proc.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        server_proc.send_signal(signal.SIGINT)
    try:
        server_proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        server_proc.terminate()

time.sleep(1)

# 6. Xuất báo cáo coverage
server_log_file.close()
print("\n[6/6] Xuất báo cáo coverage...")
subprocess.run([str(PYTHON_EXE), "-m", "coverage", "report", "-m"], cwd=PROJECT_DIR)
subprocess.run([str(PYTHON_EXE), "-m", "coverage", "json", "-o", "coverage_orders.json"], cwd=PROJECT_DIR)

if (PROJECT_DIR / "coverage_orders.json").exists():
    with open(PROJECT_DIR / "coverage_orders.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print("\n--- CHI TIẾT TỔNG HỢP PHÂN HỆ ORDERS ---")
    summary = data.get("totals", {})
    print(f"Tổng số dòng lệnh (Statements): {summary.get('num_statements')}")
    print(f"Số dòng đã thực thi (Covered) : {summary.get('covered_lines')}")
    print(f"Số dòng bị thiếu (Missing)   : {summary.get('missing_lines')}")
    print(f"Độ phủ dòng (Line Coverage)  : {summary.get('percent_covered'):.2f}%")
    print(f"Tổng số nhánh (Branches)     : {summary.get('num_branches', 0)}")
    print(f"Số nhánh đã phủ (Covered)    : {summary.get('covered_branches', 0)}")
    print(f"Số nhánh bị thiếu (Missing)  : {summary.get('missing_branches', 0)}")
    if summary.get('num_branches', 0) > 0:
        br_pct = summary.get('covered_branches', 0) / summary.get('num_branches', 0) * 100
        print(f"Độ phủ nhánh (Branch Coverage): {br_pct:.2f}%")

print("\nHoàn tất kịch bản đo độ phủ BVA!")
