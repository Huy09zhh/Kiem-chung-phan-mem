"""Chạy toàn bộ Postman collection của nhóm bằng newman, một lệnh duy nhất.

Chạy từ thư mục gốc repo (đã bật .venv):
    python postman/run_all.py                 # chạy tất cả
    python postman/run_all.py --chi PH6 PH2   # chỉ chạy một số phân hệ
    python postman/run_all.py --ds            # xem danh sách các lượt chạy

Script tự làm:
  1. Cất db.sqlite3 của bạn sang thư mục báo cáo.
  2. Dựng DB mẫu: migrate DB trống + postman/seed_full.py (tài khoản, sản phẩm, 20 đơn hàng cố định).
  3. Đổi từng collection trong postman/collections (định dạng YAML của Postman) sang JSON.
  4. Mỗi lượt chạy: chép DB mẫu -> bật server -> newman -> tắt server. Lượt nào cũng bắt đầu
     từ cùng một dữ liệu, và bật lại server là xóa các bộ đếm chặn spam (khóa đăng nhập,
     giới hạn gửi mail, form liên hệ, đăng ký nhận tin).
  5. Ghi báo cáo vào output/postman_run/<thời gian>/BaoCao.html.
  6. Trả db.sqlite3 của bạn về như cũ.

    --db-hien-tai : chạy thẳng trên db.sqlite3 đang có, không dựng DB mẫu (vẫn sao lưu và trả lại).

Chạy tay trên giao diện Postman với cùng bộ dữ liệu:
    python postman/run_all.py --server
  Lệnh này cất DB của bạn, dựng DB mẫu và bật server đúng cấu hình (mail ghi ra sent_emails/,
  mở /dev/mailbox/). Trong Postman chọn environment "Green Shop - Test chung" rồi Run.
  Muốn làm mới dữ liệu giữa các collection: tạo file output/postman_db/lam_moi (server tự tắt,
  chép lại DB mẫu, bật lại), hoặc Ctrl+C rồi chạy lại lệnh. Ctrl+C là DB của bạn được trả về.
  (--dung-db / --tra-db: chỉ đổi DB, tự bật server bằng  EMAIL_HOST_USER= python manage.py runserver)

Cần: Node.js (npx tự tải newman lần đầu) và PyYAML (pip install pyyaml).
Không cần bật server trước; nếu cổng 8000 đang có server khác chạy thì tắt nó đi.
"""
import argparse
import datetime
import html
import json
import os
import shutil
import socket
import subprocess
import sys
import time

try:
    import yaml
except ImportError:
    sys.exit('Thiếu PyYAML: pip install pyyaml')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLL_DIR = os.path.join(ROOT, 'postman', 'collections')
HOST, PORT = '127.0.0.1', 8000
BASE_URL = f'http://{HOST}:{PORT}'

ADMIN = {'admin_username': 'admin', 'admin_password': 'Admin@12345'}
KHACH = {'customer_username': 'user1', 'customer_password': 'User@12345',
         'cust_username': 'user2', 'cust_password': 'User@12345'}

# Biến Environment (script đọc bằng pm.environment.get nên không đặt được ở biến collection).
# BVA nhóm 08 của Tiên đọc hộp thư dev bằng tài khoản superuser của DB mẫu.
NEWMAN_ENV = {'bva_mailbox_admin_user': 'admin', 'bva_mailbox_admin_password': 'Admin@12345'}

# (mã, thư mục collection, chạy theo từng folder?, biến ghi đè)
# Thứ tự: chỉ đọc trước, phần đăng nhập/khóa tài khoản để cuối.
PLAN = [
    ('PH2', 'Green Shop - Products & Search (TC-PS)', False, {}),
    ('PH5', 'GreenShop - Admin Catalog & Media', False, {}),
    ('PH3-GioHang', 'Green Shop - Shopping Cart (EP-BVA)', False, {}),
    ('PH3-Email', 'email_dangky', False, {}),
    ('PH4', 'Green Shop - Orders', False, {'username': 'user1', 'password': 'User@12345'}),
    ('PH6', 'PH6 - Admin Orders & Analytics', True, {**ADMIN, **KHACH}),
    ('PH1-TCAA', 'Green Shop - Account & Auth (TC-AA)', False, {}),
    # BVA chạy từng nhóm: cả bộ một lượt sẽ vượt ngưỡng khóa đăng nhập / gửi mail (SCRUM-54, 55)
    ('PH1-BVA', 'Green Shop - Account & Auth - BVA', True, {}),
]


# ---------------------------------------------------------------- YAML -> JSON

def load_yaml(path):
    # BaseLoader giữ mọi giá trị là chuỗi: 'no' không thành False, '0912...' không mất số 0
    with open(path, encoding='utf-8') as f:
        return yaml.load(f, Loader=yaml.BaseLoader) or {}


def to_order(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 1e12


def convert_scripts(scripts):
    events = []
    for s in scripts or []:
        kind = str(s.get('type', ''))
        listen = 'prerequest' if kind.endswith('beforeRequest') else 'test' if kind.endswith('afterResponse') else None
        if listen and s.get('code'):
            events.append({'listen': listen, 'script': {'type': 'text/javascript', 'exec': s['code'].split('\n')}})
    return events


def pairs(data):
    """dict hoặc list -> [(key, value)]"""
    if isinstance(data, dict):
        out = []
        for k, v in data.items():
            for item in (v if isinstance(v, list) else [v]):
                out.append((k, item))
        return out
    out = []
    for item in data or []:
        if isinstance(item, dict) and 'key' in item:
            out.append((item['key'], item.get('value', '')))
        elif isinstance(item, dict):
            out.extend(item.items())
    return out


def convert_request(path):
    y = load_yaml(path)
    name = y.get('name') or os.path.basename(path)[:-len('.request.yaml')]
    url = y.get('url', '')
    if y.get('queryParams') and '?' not in url:
        url += '?' + '&'.join(f'{k}={v}' for k, v in pairs(y['queryParams']))
    req = {
        'method': y.get('method', 'GET'),
        'header': [{'key': k, 'value': v} for k, v in pairs(y.get('headers'))],
        'url': url,
    }
    body = y.get('body')
    if body:
        btype = body.get('type')
        content = body.get('content', '')
        if btype == 'urlencoded':
            req['body'] = {'mode': 'urlencoded',
                           'urlencoded': [{'key': k, 'value': v, 'type': 'text'} for k, v in pairs(content)]}
        elif btype == 'json':
            req['body'] = {'mode': 'raw', 'raw': content, 'options': {'raw': {'language': 'json'}}}
        else:
            req['body'] = {'mode': 'raw', 'raw': content if isinstance(content, str) else json.dumps(content)}
    if y.get('auth'):
        req['auth'] = {'type': y['auth'].get('type', 'noauth')}
    item = {'name': name, 'request': req, 'event': convert_scripts(y.get('scripts'))}
    follow = (y.get('settings') or {}).get('followRedirects')
    if follow is not None:
        item['protocolProfileBehavior'] = {'followRedirects': str(follow).lower() == 'true'}
    return to_order(y.get('order')), item


def convert_folder(folder):
    entries = []
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if name.startswith('.'):
            continue
        if os.path.isdir(full):
            definition = os.path.join(full, '.resources', 'definition.yaml')
            if not os.path.exists(definition):
                continue
            d = load_yaml(definition)
            sub = {'name': d.get('name') or name, 'item': convert_folder(full)}
            if d.get('description'):
                sub['description'] = d['description']
            events = convert_scripts(d.get('scripts'))
            if events:
                sub['event'] = events
            entries.append((to_order(d.get('order')), sub['name'], sub))
        elif name.endswith('.request.yaml'):
            order, item = convert_request(full)
            entries.append((order, item['name'], item))
    entries.sort(key=lambda e: (e[0], e[1]))
    return [e[2] for e in entries]


def convert_collection(dirname, overrides):
    folder = os.path.join(COLL_DIR, dirname)
    d = load_yaml(os.path.join(folder, '.resources', 'definition.yaml'))
    variables = dict(d.get('variables') or {})
    variables.update(overrides)
    variables['base_url'] = BASE_URL
    variables['baseUrl'] = BASE_URL
    return {
        'info': {'name': d.get('name') or dirname,
                 'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
        'variable': [{'key': k, 'value': '' if v is None else str(v)} for k, v in variables.items()],
        'event': convert_scripts(d.get('scripts')),
        'item': convert_folder(folder),
    }


# ---------------------------------------------------------------- server / newman

def port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PORT)) == 0


def start_server(log):
    # EMAIL_HOST_USER rỗng: mail ghi ra sent_emails/ và mở /dev/mailbox/ (BVA nhóm 08 cần),
    # đồng thời không gửi mail thật qua Gmail khi test. Không đụng tới file .env.
    env = dict(os.environ, EMAIL_HOST_USER='')
    proc = subprocess.Popen([sys.executable, 'manage.py', 'runserver', f'{HOST}:{PORT}', '--noreload'],
                            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
    for _ in range(60):
        if port_open():
            return proc
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    proc.kill()
    sys.exit('Không bật được server, xem log trong thư mục báo cáo.')


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()
    for _ in range(20):
        if not port_open():
            return
        time.sleep(0.25)


def run_newman(json_path, report_path, folder, verbose):
    npx = shutil.which('npx') or shutil.which('npx.cmd')
    if not npx:
        sys.exit('Không tìm thấy npx, cài Node.js trước.')
    cmd = [npx, '--yes', 'newman@6', 'run', json_path,
           '--reporters', 'cli,json' if verbose else 'json',
           '--reporter-json-export', report_path, '--timeout-request', '30000']
    if folder:
        cmd += ['--folder', folder]
    for key, value in NEWMAN_ENV.items():
        cmd += ['--env-var', f'{key}={value}']
    subprocess.run(cmd, cwd=ROOT)
    try:
        with open(report_path, encoding='utf-8') as f:
            return json.load(f)['run']
    except (OSError, ValueError, KeyError):
        # newman bị ngắt giữa chừng: ghi nhận là lỗi rồi chạy tiếp lượt sau
        return {'stats': {'requests': {'total': 0, 'failed': 0}, 'assertions': {'total': 0, 'failed': 0}},
                'failures': [{'source': {'name': '(newman)'},
                              'error': {'name': 'Newman không chạy xong', 'message': 'không có file kết quả'}}]}


# ---------------------------------------------------------------- main

def build_runs(selected):
    runs = []
    for code, dirname, per_folder, overrides in PLAN:
        if selected and not any(code.upper().startswith(s.upper()) for s in selected):
            continue
        if not os.path.isdir(os.path.join(COLL_DIR, dirname)):
            print(f'!! Bỏ qua {code}: không thấy thư mục {dirname}')
            continue
        collection = convert_collection(dirname, overrides)
        if per_folder:
            for sub in collection['item']:
                if 'item' in sub:
                    runs.append((code, collection, sub['name']))
        else:
            runs.append((code, collection, None))
    return runs


def write_html(path, results, started, total_time):
    rows, details = [], []
    for i, (code, name, folder, run) in enumerate(results, 1):
        st = run['stats']
        req_fail = st['requests']['failed']
        a_total, a_fail = st['assertions']['total'], st['assertions']['failed']
        status = 'PASS' if not run['failures'] else 'FAIL'
        color = '#C6EFCE' if status == 'PASS' else '#FFC7CE'
        rows.append(f'<tr><td>{i}</td><td>{html.escape(code)}</td><td>{html.escape(name)}</td>'
                    f'<td>{html.escape(folder or "(cả collection)")}</td><td>{st["requests"]["total"]}</td>'
                    f'<td>{req_fail}</td><td>{a_total}</td><td>{a_total - a_fail}</td><td>{a_fail}</td>'
                    f'<td style="background:{color}">{status}</td></tr>')
        if run['failures']:
            items = ''.join(
                f'<li><b>{html.escape(f.get("source", {}).get("name", "?"))}</b>: '
                f'{html.escape(f.get("error", {}).get("test") or f.get("error", {}).get("name", ""))} '
                f'<i>{html.escape(str(f.get("error", {}).get("message", ""))[:300])}</i></li>'
                for f in run['failures'])
            details.append(f'<h3>{i}. {html.escape(name)} {html.escape(folder or "")}</h3><ul>{items}</ul>')
    page = f'''<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"><title>Kết quả chạy Postman</title>
<style>body{{font-family:Calibri,Arial,sans-serif;font-size:14px;margin:24px}}
table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:4px 8px}}
th{{background:#D9E1F2}}li{{margin:3px 0}}</style></head><body>
<h2>Kết quả chạy Postman toàn nhóm</h2>
<p>Bắt đầu: {started:%d/%m/%Y %H:%M} — thời gian chạy: {total_time/60:.1f} phút — server: {BASE_URL}</p>
<table><tr><th>#</th><th>Mã</th><th>Collection</th><th>Folder</th><th>Request</th><th>Request lỗi</th>
<th>Assertion</th><th>Đạt</th><th>Không đạt</th><th>Kết quả</th></tr>{''.join(rows)}</table>
<h2>Chi tiết các assertion không đạt</h2>{''.join(details) or '<p>Không có.</p>'}</body></html>'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)


def prepare_template(out_dir, db):
    """Dựng DB mẫu: DB trống -> migrate -> seed_full.py. Trả về đường dẫn file mẫu."""
    if os.path.exists(db):
        os.remove(db)
    manage = [sys.executable, 'manage.py']
    subprocess.run(manage + ['migrate', '-v', '0'], cwd=ROOT, check=True)
    subprocess.run(manage + ['shell', '-c', "exec(open('postman/seed_full.py', encoding='utf-8').read())"],
                   cwd=ROOT, check=True)
    template = os.path.join(out_dir, 'db_mau.sqlite3')
    shutil.copy2(db, template)
    return template


def main():
    ap = argparse.ArgumentParser(description='Chạy toàn bộ Postman collection của nhóm bằng newman.')
    ap.add_argument('--chi', nargs='*', default=[], help='chỉ chạy các mã này, ví dụ: --chi PH6 PH2')
    ap.add_argument('--ds', action='store_true', help='chỉ in danh sách lượt chạy rồi thoát')
    ap.add_argument('--db-hien-tai', action='store_true', help='chạy trên db.sqlite3 đang có thay vì DB mẫu')
    ap.add_argument('--chi-tiet', action='store_true', help='in kết quả từng request ra màn hình')
    ap.add_argument('--dung-db', action='store_true', help='thay db.sqlite3 bằng DB mẫu để chạy tay trên Postman')
    ap.add_argument('--tra-db', action='store_true', help='trả db.sqlite3 của bạn về sau khi chạy tay')
    ap.add_argument('--server', action='store_true',
                    help='dựng DB mẫu + bật server để chạy bằng giao diện Postman; Ctrl+C là trả DB về')
    args = ap.parse_args()

    db = os.path.join(ROOT, 'db.sqlite3')
    keep_dir = os.path.join(ROOT, 'output', 'postman_db')
    keep = os.path.join(keep_dir, 'db_cua_ban.sqlite3')
    if args.server:
        if port_open():
            sys.exit(f'Cổng {PORT} đang có server chạy. Tắt runserver đang mở rồi chạy lại.')
        os.makedirs(keep_dir, exist_ok=True)
        if not os.path.exists(keep) and os.path.exists(db):
            shutil.copy2(db, keep)
        trigger = os.path.join(keep_dir, 'lam_moi')
        log = open(os.path.join(keep_dir, 'server.log'), 'a', encoding='utf-8')
        proc = None
        try:
            template = prepare_template(keep_dir, db)
            proc = start_server(log)
            print('\n=== Server đang chạy với DB mẫu: ' + BASE_URL + '  (log: output/postman_db/server.log)')
            print('=== Postman: chọn environment "Green Shop - Test chung" rồi Run.')
            print('=== Làm mới dữ liệu: tạo file output/postman_db/lam_moi, hoặc Ctrl+C rồi chạy lại lệnh.')
            print('=== Ctrl+C là DB của bạn được trả về.\n')
            n = 0
            while True:
                time.sleep(0.5)
                if os.path.exists(trigger):
                    stop_server(proc)
                    shutil.copy2(template, db)
                    proc = start_server(log)
                    os.remove(trigger)
                    n += 1
                    print(f'[{datetime.datetime.now():%H:%M:%S}] Đã làm mới dữ liệu và bật lại server (lần {n}).')
                elif proc.poll() is not None:
                    print('Server đã dừng, xem output/postman_db/server.log')
                    break
        except KeyboardInterrupt:
            pass
        finally:
            if proc and proc.poll() is None:
                stop_server(proc)
            log.close()
            if os.path.exists(keep):
                for _ in range(20):          # Windows: chờ server nhả file DB
                    try:
                        shutil.copy2(keep, db)
                        os.remove(keep)
                        print('\nĐã trả db.sqlite3 của bạn về.')
                        break
                    except OSError:
                        time.sleep(0.5)
                else:
                    print('\nChưa trả được DB, chạy: python postman/run_all.py --tra-db')
        return

    if args.dung_db or args.tra_db:
        if port_open():
            sys.exit(f'Tắt runserver đang chạy ở cổng {PORT} trước.')
        if args.tra_db:
            if not os.path.exists(keep):
                sys.exit('Không có bản DB nào đang cất.')
            shutil.copy2(keep, db)
            os.remove(keep)
            print('Đã trả db.sqlite3 của bạn về.')
            return
        os.makedirs(keep_dir, exist_ok=True)
        if not os.path.exists(keep) and os.path.exists(db):
            shutil.copy2(db, keep)   # chỉ cất lần đầu, chạy lại --dung-db không ghi đè bản của bạn
            print(f'Đã cất DB của bạn: {keep}')
        prepare_template(keep_dir, db)
        print('db.sqlite3 giờ là DB mẫu. Bật server bằng: EMAIL_HOST_USER= python manage.py runserver')
        print('rồi chọn environment "Green Shop - Test chung" trong Postman.')
        print('Chạy xong: python postman/run_all.py --tra-db')
        return

    runs = build_runs(args.chi)
    if args.ds or not runs:
        for i, (code, coll, folder) in enumerate(runs, 1):
            print(f'{i:2}. {code:12} {coll["info"]["name"]}  {folder or ""}')
        return
    if port_open():
        sys.exit(f'Cổng {PORT} đang có server chạy. Tắt runserver đang mở rồi chạy lại.')

    if os.path.exists(keep):
        sys.exit('DB của bạn đang được cất do --dung-db. Chạy --tra-db trước rồi hẵng chạy tự động.')

    started = datetime.datetime.now()
    out_dir = os.path.join(ROOT, 'output', 'postman_run', started.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(out_dir)
    backup = os.path.join(out_dir, 'db_cua_ban.sqlite3')
    if os.path.exists(db):
        shutil.copy2(db, backup)

    results = []
    log = open(os.path.join(out_dir, 'server.log'), 'w', encoding='utf-8')
    try:
        template = None if args.db_hien_tai else prepare_template(out_dir, db)
        for i, (code, coll, folder) in enumerate(runs, 1):
            label = coll['info']['name'] + (f' / {folder}' if folder else '')
            print(f'\n[{i}/{len(runs)}] {label}')
            json_path = os.path.join(out_dir, f'{i:02d}_{code}.collection.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(coll, f, ensure_ascii=False, indent=1)
            if template:
                shutil.copy2(template, db)
            proc = start_server(log)
            try:
                run = run_newman(json_path, os.path.join(out_dir, f'{i:02d}_{code}.ketqua.json'), folder, args.chi_tiet)
            finally:
                stop_server(proc)
            st = run['stats']
            print(f'    request {st["requests"]["total"]}, assertion {st["assertions"]["total"]}, '
                  f'không đạt {st["assertions"]["failed"]}, lỗi khác {len(run["failures"]) - st["assertions"]["failed"]}')
            results.append((code, coll['info']['name'], folder, run))
    finally:
        log.close()
        if results:
            report = os.path.join(out_dir, 'BaoCao.html')
            write_html(report, results, started, (datetime.datetime.now() - started).total_seconds())
            print(f'\nBáo cáo: {report}')
        if os.path.exists(backup):
            shutil.copy2(backup, db)
            print('Đã trả db.sqlite3 của bạn về như trước khi chạy.')
        elif os.path.exists(db) and not args.db_hien_tai:
            os.remove(db)


if __name__ == '__main__':
    main()
