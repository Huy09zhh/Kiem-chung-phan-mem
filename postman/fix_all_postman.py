import os
import json

base_dir = "postman/collections/Green Shop - Orders"

prereq_script = """const sid = pm.cookies.get('sessionid');
const csrf = pm.cookies.get('csrftoken');
let cookieHdr = '';
if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
if (csrf) { 
  cookieHdr += 'csrftoken=' + csrf; 
  pm.collectionVariables.set('csrf_token', csrf);
}
pm.sendRequest({
  url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
  method: 'GET',
  header: { 'Cookie': cookieHdr }
}, function (err, res) {});"""

def update_all_requests():
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if not f.endswith('.request.yaml'):
                continue
            fpath = os.path.join(root, f)
            with open(fpath, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()

            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check beforeRequest with cart/add
                if line.strip() == '- type: beforeRequest':
                    new_lines.append(line)
                    i += 1
                    if i < len(lines) and 'code: |-' in lines[i]:
                        new_lines.append(lines[i])
                        i += 1
                        # Skip old beforeRequest code lines until language:
                        has_cart_add = False
                        old_code_block = []
                        while i < len(lines) and not lines[i].strip().startswith('language:'):
                            if '/cart/add/' in lines[i]:
                                has_cart_add = True
                            old_code_block.append(lines[i])
                            i += 1
                        if has_cart_add:
                            for pline in prereq_script.splitlines():
                                new_lines.append(f"      {pline}\n")
                        else:
                            for oline in old_code_block:
                                new_lines.append(oline)
                        if i < len(lines):
                            new_lines.append(lines[i]) # language:
                    continue

                # Check variable extract lines in afterResponse
                # Old pattern:
                # const loc = pm.response.headers.get("Location") || "";
                # const match = loc.match(/\/(\d+)\//);
                # if (match) { pm.collectionVariables.set("<var>", match[1]); }
                if 'pm.response.headers.get("Location")' in line:
                    # Look ahead to see if it sets a variable
                    block = [line]
                    i += 1
                    var_found = None
                    while i < len(lines) and not lines[i].strip().startswith('language:') and not lines[i].strip().startswith('order:') and not lines[i].strip().startswith('settings:'):
                        block.append(lines[i])
                        if 'pm.collectionVariables.set(' in lines[i]:
                            for v in ['dt_cod_order_id', 'dt_qr_order_id', 'dt_mock_order_id', 'st_order_cod_id', 'st_order_qr_id', 'st_cancel_qr_id', 'st_order_mock_id', 'st_order_mock_success_id']:
                                if f'"{v}"' in lines[i] or f"'{v}'" in lines[i]:
                                    var_found = v
                                    break
                        i += 1
                    if var_found:
                        new_lines.append(f"""      let orderId = null;
      const loc = pm.response.headers.get("Location") || "";
      const mLoc = loc.match(/\\/(\\d+)\\//);
      if (mLoc) {{ orderId = mLoc[1]; }}
      else {{
        const text = pm.response.text();
        const mHtml = text.match(/\\/orders\\/(?:qr|mock|success)\\/(\\d+)/) || text.match(/action=["'][^"']*\\/orders\\/(?:qr\\/)?(\\d+)\\//) || text.match(/[Đđ]ơn hàng #(\\d+)/) || text.match(/#(\\d+)/);
        if (mHtml) {{ orderId = mHtml[1]; }}
      }}
      if (orderId) {{ pm.collectionVariables.set("{var_found}", orderId); }}
      const c = pm.cookies.get('csrftoken');
      if (c) {{ pm.collectionVariables.set('csrf_token', c); }}
""")
                    else:
                        for bl in block:
                            new_lines.append(bl)
                    if i < len(lines):
                        new_lines.append(lines[i])
                    continue

                # Special fix for 00.1, 00.2, 00.3
                if '00.1' in f and 'const t = pm.cookies.get' in line:
                    new_lines.append("""      const m = pm.response.text().match(/name=["']csrfmiddlewaretoken["']\\s+value=["']([^"']+)["']/);
      if (m) { pm.collectionVariables.set('csrf_token', m[1]); }
      const c = pm.cookies.get('csrftoken');
      if (c) { pm.collectionVariables.set('csrf_token', c); }
""")
                    i += 1
                    continue

                if '00.2' in f and 'pm.test' in line:
                    new_lines.append(line)
                    new_lines.append("""      const c = pm.cookies.get('csrftoken');
      if (c) { pm.collectionVariables.set('csrf_token', c); }
""")
                    i += 1
                    continue

                new_lines.append(line)
                i += 1

            with open(fpath, 'w', encoding='utf-8') as fp:
                fp.writelines(new_lines)

    print("Updated all request yaml files successfully!")

def parse_yaml_manual(text):
    data = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith('#'):
            i += 1
            continue
        
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
                elif sline.strip().startswith('code:'):
                    in_code = False
                    code_str = sline.strip().split('code:', 1)[1].strip()
                    code_lines = [code_str]
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
        
    clean_path = url_str.replace('{{base_url}}', '').strip('/')
    path_segments = [p for p in clean_path.split('/') if p]
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
    if 'TC-EG-07' not in req_name:
        headers.append({"key": "X-CSRFToken", "value": "{{csrf_token}}", "type": "text"})
    
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
            
    item = {
        "name": req_name,
        "event": events,
        "protocolProfileBehavior": {
            "followRedirects": False
        },
        "request": request_obj,
        "response": []
    }
    return item

def rebuild_json_collection():
    folders = [
        ("00. Chuẩn bị (chạy đầu tiên)", "Các bước chuẩn bị: lấy CSRF cookie, đăng nhập user test, thêm sản phẩm vào giỏ hàng"),
        ("01_EP_and_BVA", "Phân hoạch lớp tương đương & Phân tích giá trị biên (Standard + Robustness) cho API Đặt hàng"),
        ("02_Decision_Table", "Bảng quyết định: Kiểm thử toàn bộ các luật R1-R4 tiền điều kiện, thanh toán và VietQR confirm"),
        ("03_State_Transition", "Kiểm thử chuyển đổi trạng thái đơn hàng & thanh toán (Valid lifecycle + Negative blocked transitions)"),
        ("04_Error_Guessing", "Đoán lỗi dựa trên kinh nghiệm: Idempotency trùng lặp, thiếu CSRF, sai kiểu dữ liệu, giỏ rỗng")
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
            yaml_data = parse_yaml_manual(text)
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
            {"key": "st_order_cod_id", "value": "1", "type": "string"},
            {"key": "st_order_qr_id", "value": "1", "type": "string"},
            {"key": "st_cancel_qr_id", "value": "1", "type": "string"},
            {"key": "st_order_mock_id", "value": "1", "type": "string"},
            {"key": "st_order_mock_success_id", "value": "1", "type": "string"},
            {"key": "dt_cod_order_id", "value": "1", "type": "string"},
            {"key": "dt_qr_order_id", "value": "1", "type": "string"},
            {"key": "dt_mock_order_id", "value": "1", "type": "string"}
        ]
    }
    
    out_json = "postman/Green_Shop_Orders_Payment_FR4.postman_collection.json"
    with open(out_json, 'w', encoding='utf-8') as fp:
        json.dump(collection, fp, ensure_ascii=False, indent=2)
        
    print(f"Rebuilt {out_json} successfully!")

if __name__ == '__main__':
    update_all_requests()
    rebuild_json_collection()
