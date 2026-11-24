import json
import os
import re

base_dir = "postman/collections/Green Shop - Orders"

def parse_simple_yaml(text):
    data = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith('#'):
            i += 1
            continue
        
        # Check scripts block
        if line.startswith('scripts:'):
            scripts = []
            i += 1
            cur_script = None
            in_code = False
            code_lines = []
            while i < len(lines):
                sline = lines[i]
                if sline and not sline.startswith(' ') and not sline.startswith('\t'):
                    break
                if sline.strip().startswith('- type:'):
                    if cur_script:
                        cur_script['code'] = '\n'.join(code_lines)
                        scripts.append(cur_script)
                    stype = sline.strip().split(':', 1)[1].strip()
                    cur_script = {'type': stype}
                    in_code = False
                    code_lines = []
                elif 'code: |-' in sline or 'code: |' in sline:
                    in_code = True
                    code_lines = []
                elif sline.strip().startswith('language:'):
                    in_code = False
                elif in_code:
                    code_lines.append(sline[4:] if sline.startswith('    ') else sline.strip())
                i += 1
            if cur_script:
                cur_script['code'] = '\n'.join(code_lines)
                scripts.append(cur_script)
            data['scripts'] = scripts
            continue

        # Check body block
        if line.startswith('body:'):
            body = {'content': {}}
            i += 1
            in_content = False
            while i < len(lines):
                bline = lines[i]
                if bline and not bline.startswith(' ') and not bline.startswith('\t'):
                    break
                if bline.strip().startswith('type:'):
                    body['type'] = bline.strip().split(':', 1)[1].strip()
                elif bline.strip().startswith('content:'):
                    in_content = True
                elif in_content and ':' in bline:
                    k, v = bline.strip().split(':', 1)
                    v = v.strip().strip('"').strip("'")
                    body['content'][k.strip()] = v
                i += 1
            data['body'] = body
            continue

        # Check settings block
        if line.startswith('settings:'):
            settings = {}
            i += 1
            while i < len(lines):
                sline = lines[i]
                if sline and not sline.startswith(' ') and not sline.startswith('\t'):
                    break
                if ':' in sline:
                    k, v = sline.strip().split(':', 1)
                    val = v.strip().lower()
                    settings[k.strip()] = False if val == 'false' else (True if val == 'true' else val)
                i += 1
            data['settings'] = settings
            continue

        # Simple key-value
        if ':' in line:
            k, v = line.split(':', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            data[k] = v
        i += 1
    return data

def build_postman_request(yaml_data, req_name):
    url_str = yaml_data.get('url', '{{base_url}}/orders/checkout/')
    if not url_str.endswith('/') and '?' not in url_str:
        url_str += '/'
        
    clean_path = url_str.replace('{{base_url}}', '')
    if clean_path.startswith('/'):
        clean_path = clean_path[1:]
    parts = clean_path.split('/')
    path_segments = [p for p in parts if p]
    if url_str.endswith('/'):
        path_segments.append("")
    
    events = []
    for sc in yaml_data.get('scripts', []):
        listen_type = 'prerequest' if sc.get('type') == 'beforeRequest' else 'test'
        events.append({
            "listen": listen_type,
            "script": {
                "type": "text/javascript",
                "exec": sc.get('code', '').splitlines()
            }
        })
    
    headers = []
    # Only omit CSRF header for TC-EG-07 which specifically tests missing CSRF
    if 'TC-EG-07' not in req_name and '00.1' not in req_name:
        headers.append({
            "key": "X-CSRFToken",
            "value": "{{csrf_token}}",
            "type": "text"
        })
    
    request_obj = {
        "method": yaml_data.get('method', 'GET'),
        "header": headers,
        "url": {
            "raw": url_str,
            "host": ["{{base_url}}"],
            "path": path_segments
        }
    }
    
    body_data = yaml_data.get('body')
    if body_data:
        btype = body_data.get('type')
        if btype == 'urlencoded':
            urlencoded_items = []
            for k, v in body_data.get('content', {}).items():
                urlencoded_items.append({
                    "key": k,
                    "value": str(v),
                    "type": "text"
                })
            request_obj["body"] = {
                "mode": "urlencoded",
                "urlencoded": urlencoded_items
            }
            request_obj["header"].append({
                "key": "Content-Type",
                "value": "application/x-www-form-urlencoded"
            })
        elif btype == 'json':
            request_obj["body"] = {
                "mode": "raw",
                "raw": json.dumps(body_data.get('content', {}), indent=2)
            }
            request_obj["header"].append({
                "key": "Content-Type",
                "value": "application/json"
            })
            
    # Explicitly set followRedirects to false so 302 responses and Location headers are preserved
    settings = yaml_data.get('settings', {})
    follow_redirects = settings.get('followRedirects', False)
    
    item = {
        "name": req_name,
        "event": events,
        "protocolProfileBehavior": {
            "followRedirects": follow_redirects
        },
        "request": request_obj,
        "response": []
    }
    return item

def main():
    folders = [
        ("00. Chuẩn bị (chạy đầu tiên)", "Các bước chuẩn bị: lấy CSRF cookie, đăng nhập user test, thêm sản phẩm vào giỏ hàng"),
        ("01_EP_and_BVA", "Phân hoạch lớp tương đương & Phân tích giá trị biên (Standard + Robustness) cho API Đặt hàng"),
        ("02_Decision_Table", "Bảng quyết định: Kiểm thử toàn bộ các luật R1-R4 tiền điều kiện, thanh toán và VietQR confirm"),
        ("03_State_Transition", "Kiểm thử chuyển đổi trạng thái đơn hàng & thanh toán (Valid lifecycle + Negative blocked transitions)"),
        ("04_Error_Guessing", "Đoán lỗi dựa trên kinh nghiệm: Idempotency trùng lặp, thiếu CSRF, sai kiểu dữ liệu, giỏ rỗng"),
        ("05_White_Box_Coverage", "Kiểm thử Hộp trắng (White-box Coverage): Phủ toàn diện CFG, câu lệnh (Statement 100%), nhánh quyết định (Branch 100%), biểu thức ghép MC/DC và nhánh ngoại lệ")
    ]
    
    collection_items = []
    
    for folder_name, folder_desc in folders:
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.exists(folder_path):
            continue
        
        req_files = [f for f in os.listdir(folder_path) if f.endswith('.request.yaml')]
        req_files.sort()
        
        folder_requests = []
        for rf in req_files:
            file_path = os.path.join(folder_path, rf)
            with open(file_path, 'r', encoding='utf-8') as fp:
                text = fp.read()
            yaml_data = parse_simple_yaml(text)
            req_name = rf.replace('.request.yaml', '')
            postman_req = build_postman_request(yaml_data, req_name)
            folder_requests.append(postman_req)
            
        collection_items.append({
            "name": folder_name,
            "description": folder_desc,
            "item": folder_requests
        })
        
    collection = {
        "info": {
            "_postman_id": "c1f7b89d-4e2a-49a0-9c2e-8e8f81023456",
            "name": "Green Shop - Orders & Payment (FR4)",
            "description": "Bộ Postman Collection kiểm thử toàn diện phân hệ Đặt hàng & Thanh toán (FR4) theo chuẩn 4 kỹ thuật Chương 4: EP & BVA, Bảng quyết định (Decision Table), Chuyển đổi trạng thái (State Transition), và Đoán lỗi (Error Guessing).",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": collection_items,
        "variable": [
            {"key": "base_url", "value": "http://127.0.0.1:8000", "type": "string"},
            {"key": "username", "value": "khach_test", "type": "string"},
            {"key": "password", "value": "DoiMatKhauCuaBan@123", "type": "string"},
            {"key": "product_id", "value": "1", "type": "string"},
            {"key": "csrf_token", "value": "", "type": "string"},
            {"key": "st_order_cod_id", "value": "", "type": "string"},
            {"key": "st_order_qr_id", "value": "", "type": "string"},
            {"key": "st_cancel_qr_id", "value": "", "type": "string"},
            {"key": "st_order_mock_id", "value": "", "type": "string"},
            {"key": "st_order_mock_success_id", "value": "", "type": "string"},
            {"key": "dt_cod_order_id", "value": "", "type": "string"},
            {"key": "dt_qr_order_id", "value": "", "type": "string"},
            {"key": "dt_mock_order_id", "value": "", "type": "string"},
            {"key": "wb_order_cod_id", "value": "", "type": "string"},
            {"key": "wb_order_qr_id", "value": "", "type": "string"},
            {"key": "wb_order_mock_id", "value": "", "type": "string"}
        ]
    }
    
    out_json = "postman/Green_Shop_Orders_Payment_FR4.postman_collection.json"
    with open(out_json, 'w', encoding='utf-8') as fp:
        json.dump(collection, fp, ensure_ascii=False, indent=2)
        
    print(f"Generated {out_json} successfully with {len(collection_items)} folders and total requests:")
    total = 0
    for fold in collection_items:
        cnt = len(fold['item'])
        total += cnt
        print(f" - {fold['name']}: {cnt} requests")
    print(f"Total: {total} requests.")

if __name__ == '__main__':
    main()
