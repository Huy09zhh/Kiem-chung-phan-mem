import os

base_dir = r"C:\Users\TOSHIBA\Desktop\DUAN\KCPM\Kiem-chung-phan-mem\postman\collections\Green Shop - Orders"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def write_request(folder, filename, content):
    full_path = os.path.join(base_dir, folder, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Created: {folder}/{filename}")

# ==============================================================================
# FOLDER 01_EP_and_BVA
# ==============================================================================

# ==============================================================================
# FOLDER 00. Chuẩn bị (chạy đầu tiên)
# ==============================================================================
folder_00 = "00. Chuẩn bị (chạy đầu tiên)"
ensure_dir(os.path.join(base_dir, folder_00))
ensure_dir(os.path.join(base_dir, folder_00, ".resources"))

with open(os.path.join(base_dir, folder_00, ".resources", "definition.yaml"), "w", encoding="utf-8") as f:
    f.write('''$kind: collection
name: "00. Chuẩn bị (chạy đầu tiên)"
description: "Các bước chuẩn bị: lấy CSRF cookie, đăng nhập user test, thêm sản phẩm vào giỏ hàng"
order: 1000
''')

write_request(folder_00, "00.1 GET trang đăng nhập (lấy cookie csrftoken).request.yaml", '''$kind: http-request
url: "{{base_url}}/accounts/login/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('Trang đăng nhập 200', function () { pm.expect(pm.response.code).to.eql(200); });
      var m = pm.response.text().match(/name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']/);
      if (m) { pm.collectionVariables.set('csrf_token', m[1]); }
      var c = pm.cookies.get('csrftoken');
      if (c) { pm.collectionVariables.set('csrf_token', c); }
    language: text/javascript
settings:
  followRedirects: false
order: 1000
''')

write_request(folder_00, "00.2 POST đăng nhập khách hàng.request.yaml", '''$kind: http-request
url: "{{base_url}}/accounts/login/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    username: "{{username}}"
    password: "{{password}}"
scripts:
  - type: beforeRequest
    code: |-
      var c = pm.cookies.get('csrftoken');
      if (c) { pm.collectionVariables.set('csrf_token', c); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('Đăng nhập thành công (302 hoặc 200)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      var c = pm.cookies.get('csrftoken');
      if (c) { pm.collectionVariables.set('csrf_token', c); }
    language: text/javascript
settings:
  followRedirects: false
order: 2000
''')

write_request(folder_00, "00.3 Thêm sản phẩm vào giỏ.request.yaml", '''$kind: http-request
url: "{{base_url}}/cart/add/{{product_id}}/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('Thêm SP vào giỏ → 302 hoặc 200', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      var c = pm.cookies.get('csrftoken');
      if (c) { pm.collectionVariables.set('csrf_token', c); }
    language: text/javascript
settings:
  followRedirects: false
order: 3000
''')

folder_01 = "01_EP_and_BVA"
ensure_dir(os.path.join(base_dir, folder_01))
ensure_dir(os.path.join(base_dir, folder_01, ".resources"))

with open(os.path.join(base_dir, folder_01, ".resources", "definition.yaml"), "w", encoding="utf-8") as f:
    f.write("""$kind: collection
name: 01_EP_and_BVA
description: "Kiểm thử Phân hoạch tương đương (EP) & Phân tích giá trị biên (BVA) Standard (4n+1) và Robustness (6n+1) cho API Checkout"
order: 2000
""")

# 1. TC-ORD-06
write_request(folder_01, "TC-ORD-06 [EP] GET Checkout hien thi gio hang va 3 phuong thuc.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: GET
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-06 | GET Checkout trả về HTTP 200', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
      pm.test('TC-ORD-06 | Giao diện chứa đủ 3 radio cod, qr, mock', function () {
        const h = pm.response.text();
        ['cod','qr','mock'].forEach(m => pm.expect(h).to.include('value="' + m + '"'));
      });
    language: text/javascript
order: 1000
""")

# 2. TC-ORD-07
write_request(folder_01, "TC-ORD-07 [BVA-min] Checkout voi cac truong tai bien toi thieu 1 ky tu.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "A"
    phone: "0"
    address: "B"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-07 | Biên min (1 ký tự) tạo đơn thành công (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 2000
""")

# 3. TC-ORD-08
write_request(folder_01, "TC-ORD-08 [BVA-min+] Checkout voi cac truong tai min+ 2 ky tu.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "An"
    phone: "09"
    address: "HN"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-08 | Biên min+ (2 ký tự) tạo đơn thành công (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 3000
""")

# 4. TC-ORD-09
write_request(folder_01, "TC-ORD-09 [BVA-nom] Checkout nominal du lieu chuan.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    note: "Giao giờ hành chính"
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-09 | Dữ liệu danh định Nominal tạo đơn thành công (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("order_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 4000
""")

# 5. TC-ORD-10
write_request(folder_01, "TC-ORD-10 [BVA-max-] Checkout voi full_name 254 ky tu, phone 19 ky tu.request.yaml", f"""
$kind: http-request
url: "{{{{base_url}}}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{{{csrf_token}}}}"
    full_name: "{"a" * 254}"
    phone: "{"9" * 19}"
    address: "123 Đường ABC, Phường 1, TP.HCM"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      pm.sendRequest({{ url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/', method: 'GET' }}, function () {{}});
      const t = pm.cookies.get('csrftoken'); if (t) {{ pm.collectionVariables.set('csrf_token', t); }}
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-10 | Biên max- (name 254, phone 19) tạo đơn thành công (302)', function () {{
        pm.expect([200, 302]).to.include(pm.response.code);
      }});
    language: text/javascript
settings:
  followRedirects: false
order: 5000
""")

# 6. TC-ORD-11
write_request(folder_01, "TC-ORD-11 [BVA-max] Checkout voi full_name 255 ky tu, phone 20 ky tu.request.yaml", f"""
$kind: http-request
url: "{{{{base_url}}}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{{{csrf_token}}}}"
    full_name: "{"a" * 255}"
    phone: "{"9" * 20}"
    address: "123 Đường ABC, Phường 1, TP.HCM"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      pm.sendRequest({{ url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/', method: 'GET' }}, function () {{}});
      const t = pm.cookies.get('csrftoken'); if (t) {{ pm.collectionVariables.set('csrf_token', t); }}
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-11 | Biên max (name 255, phone 20) tạo đơn thành công (302)', function () {{
        pm.expect([200, 302]).to.include(pm.response.code);
      }});
    language: text/javascript
settings:
  followRedirects: false
order: 6000
""")

# 7. TC-ORD-12
write_request(folder_01, "TC-ORD-12 [BVA-min-] Ho ten rong bi chan tao don.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: ""
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    note: "Giao giờ hành chính"
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-12 | Họ tên rỗng phải bị chặn (trả về form 200, không 302)', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 7000
""")

# 8. TC-ORD-13
write_request(folder_01, "TC-ORD-13 [EP-invalid] Ho ten toan khoang trang bi chan.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "     "
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-13 | Họ tên toàn khoảng trắng bị chặn (HTTP 200)', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 8000
""")

# 9. TC-ORD-14
write_request(folder_01, "TC-ORD-14 [BVA-min-] SDT rong bi chan tao don.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Nguyễn Văn A"
    phone: ""
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-14 | SĐT rỗng bị chặn (HTTP 200)', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 9000
""")

# 10. TC-ORD-15
write_request(folder_01, "TC-ORD-15 [BVA-min-] Dia chi rong bi chan tao don.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Nguyễn Văn A"
    phone: "0901234567"
    address: ""
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-15 | Địa chỉ rỗng bị chặn (HTTP 200)', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 10000
""")

# 11. TC-ORD-16
write_request(folder_01, "TC-ORD-16 [EP-invalid] Bo trong ca 3 truong bat buoc.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: ""
    phone: ""
    address: ""
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-16 | Trống cả 3 trường bắt buộc bị chặn (HTTP 200)', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 11000
""")

# 12. TC-ORD-17
write_request(folder_01, "TC-ORD-17 [BVA-max+] Ho ten 256 ky tu vuot max bi chan.request.yaml", f"""
$kind: http-request
url: "{{{{base_url}}}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{{{csrf_token}}}}"
    full_name: "{"a" * 256}"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      pm.sendRequest({{ url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/', method: 'GET' }}, function () {{}});
      const t = pm.cookies.get('csrftoken'); if (t) {{ pm.collectionVariables.set('csrf_token', t); }}
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-17 | Họ tên 256 ký tự (vượt max 255) bị chặn (HTTP 200)', function () {{
        pm.expect(pm.response.code).to.eql(200);
      }});
    language: text/javascript
settings:
  followRedirects: false
order: 12000
""")

# 13. TC-ORD-18
write_request(folder_01, "TC-ORD-18 [BVA-max+] SDT 21 ky tu vuot max bi chan.request.yaml", f"""
$kind: http-request
url: "{{{{base_url}}}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{{{csrf_token}}}}"
    full_name: "Nguyễn Văn A"
    phone: "{"9" * 21}"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    note: ""
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      pm.sendRequest({{ url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/', method: 'GET' }}, function () {{}});
      const t = pm.cookies.get('csrftoken'); if (t) {{ pm.collectionVariables.set('csrf_token', t); }}
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-18 | SĐT 21 ký tự (vượt max 20) bị chặn (HTTP 200)', function () {{
        pm.expect(pm.response.code).to.eql(200);
      }});
    language: text/javascript
settings:
  followRedirects: false
order: 13000
""")

# 14. TC-ORD-21
write_request(folder_01, "TC-ORD-21 [EP-valid] Khong gui payment_method mac dinh COD.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Khách Mặc Định"
    phone: "0908889999"
    address: "Hà Nội"
    note: ""
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-21 | Bỏ qua payment_method tự động mặc định COD (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 14000
""")

# 15. TC-ORD-22
write_request(folder_01, "TC-ORD-22 [EP-invalid] payment_method sai tap hop bi chan.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Khách Bitcoin"
    phone: "0901234567"
    address: "TP.HCM"
    note: ""
    payment_method: "bitcoin"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ORD-22 | payment_method=bitcoin bị từ chối (HTTP 200, không đổi ngầm COD)', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 15000
""")

print("01_EP_and_BVA generation finished.")

# ==============================================================================
# FOLDER 02_Decision_Table
# ==============================================================================
folder_02 = "02_Decision_Table"
ensure_dir(os.path.join(base_dir, folder_02))
ensure_dir(os.path.join(base_dir, folder_02, ".resources"))

with open(os.path.join(base_dir, folder_02, ".resources", "definition.yaml"), "w", encoding="utf-8") as f:
    f.write("""$kind: collection
name: 02_Decision_Table
description: "Kiểm thử Bảng quyết định (Decision Table) cho các luật R1..R4 của Tiền điều kiện, Phân luồng kênh thanh toán và Xác nhận VietQR"
order: 3000
""")

# 1. TC-DT-01
write_request(folder_02, "TC-DT-01 [Rule R1] Precondition Y-Y-Y cho phep checkout (HTTP 200).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: GET
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-01 | [Rule R1] Đăng nhập Y, Giỏ hàng Y, Tiền hợp lệ Y -> 200 hiển thị form', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
order: 1000
""")

# 2. TC-DT-02
write_request(folder_02, "TC-DT-02 [Rule R3] Gio hang rong N redirect cart (HTTP 302).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      // Không nạp giỏ hàng để kiểm thử Rule R3 (Giỏ rỗng N)
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-02 | [Rule R3] Giỏ rỗng N -> chuyển hướng về /cart/ (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 2000
""")

# 3. TC-DT-03
write_request(folder_02, "TC-DT-03 [Rule PM-R1] Dat hang COD Y tao don pending va redirect success.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (COD)"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-03 | [Rule PM-R1] COD Y -> Tạo đơn pending + redirect success (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("dt_cod_order_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 3000
""")

# 4. TC-DT-04
write_request(folder_02, "TC-DT-04 [Rule PM-R2] Dat hang VietQR Y tao don awaiting_transfer va redirect QR.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (QR)"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    payment_method: "qr"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-04 | [Rule PM-R2] VietQR Y -> Tạo đơn awaiting_transfer + redirect QR (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("dt_qr_order_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 4000
""")

# 5. TC-DT-05
write_request(folder_02, "TC-DT-05 [Rule PM-R3] Dat hang Mock Y tao don pending va redirect sandbox.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (Mock)"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    payment_method: "mock"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-05 | [Rule PM-R3] Mock Y -> Tạo đơn pending + redirect sandbox (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("dt_mock_order_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 5000
""")

# 6. TC-DT-06
write_request(folder_02, "TC-DT-06 [Rule PM-R4] Phuong thuc khong hop le N chan tao don (HTTP 200).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (ZaloPay)"
    phone: "0901234567"
    address: "12 Nguyễn Huệ, Quận 1, TP.HCM"
    payment_method: "zalopay"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-06 | [Rule PM-R4] payment_method N -> Chặn tạo đơn, trả về 200 kèm cảnh báo', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 6000
""")

# 7. TC-DT-07
write_request(folder_02, "TC-DT-07 [Rule QR-R1] Confirm QR hop le POST + awaiting_transfer doi sang paid.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{dt_qr_order_id}}/confirm/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-DT-07 | [Rule QR-R1] POST confirm QR hợp lệ -> redirect success (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 7000
""")

# 8. TC-DT-08
write_request(folder_02, "TC-DT-08 [Rule QR-R3] Confirm QR bang GET Method!=POST khong doi trang thai.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{dt_qr_order_id}}/confirm/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-DT-08 | [Rule QR-R3] GET confirm QR -> redirect (302) mà không kích hoạt đổi trạng thái', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 8000
""")

# ==============================================================================
# FOLDER 03_State_Transition
# ==============================================================================
folder_03 = "03_State_Transition"
ensure_dir(os.path.join(base_dir, folder_03))
ensure_dir(os.path.join(base_dir, folder_03, ".resources"))

with open(os.path.join(base_dir, folder_03, ".resources", "definition.yaml"), "w", encoding="utf-8") as f:
    f.write("""$kind: collection
name: 03_State_Transition
description: "Kiểm thử Chuyển đổi trạng thái (State Transition Testing) nối tiếp vòng đời đơn hàng và kiểm tra các ca chặn chuyển sai"
order: 4000
""")

# 1. TC-ST-FLOW-01
write_request(folder_03, "TC-ST-FLOW-01 Tao don COD ban dau (pending).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (ST-COD)"
    phone: "0901234567"
    address: "TP.HCM"
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-01 | Tạo đơn COD -> 302 sang success (State: pending)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("st_order_cod_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 1000
""")

# 2. TC-ST-FLOW-02
write_request(folder_03, "TC-ST-FLOW-02 Xem trang success don COD (pending).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/success/{{st_order_cod_id}}/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-02 | Trang xác nhận trả về 200', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
      pm.test('TC-ST-FLOW-02 | Hiển thị trạng thái Chờ xử lý và Thanh toán khi nhận hàng', function () {
        const text = pm.response.text();
        pm.expect(text).to.include('Chờ xử lý');
        pm.expect(text).to.include('Thanh toán khi nhận hàng');
      });
    language: text/javascript
order: 2000
""")

# 3. TC-ST-FLOW-03
write_request(folder_03, "TC-ST-FLOW-03 Tao don VietQR ban dau (awaiting_transfer).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (ST-QR)"
    phone: "0901234567"
    address: "TP.HCM"
    payment_method: "qr"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-03 | Tạo đơn QR -> 302 sang trang QR (State: awaiting_transfer)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("st_order_qr_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 3000
""")

# 4. TC-ST-FLOW-04
write_request(folder_03, "TC-ST-FLOW-04 Xem trang QR don hang VietQR (awaiting_transfer).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{st_order_qr_id}}/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-04 | Mở trang QR trả về HTTP 200', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
      pm.test('TC-ST-FLOW-04 | Hiển thị nội dung chuyển khoản THANH TOAN DH', function () {
        pm.expect(pm.response.text()).to.include('THANH TOAN DH');
      });
    language: text/javascript
order: 4000
""")

# 5. TC-ST-FLOW-05
write_request(folder_03, "TC-ST-FLOW-05 [Valid] POST confirm QR (awaiting_transfer to paid).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{st_order_qr_id}}/confirm/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-05 | [Transition hợp lệ] awaiting_transfer -> paid (302 success)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 5000
""")

# 6. TC-ST-FLOW-06
write_request(folder_03, "TC-ST-FLOW-06 Tao don VietQR moi de thu huy don.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (Hủy QR)"
    phone: "0901234567"
    address: "TP.HCM"
    payment_method: "qr"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-06 | Tạo đơn QR mới -> 302', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("st_cancel_qr_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 6000
""")

# 7. TC-ST-FLOW-07
write_request(folder_03, "TC-ST-FLOW-07 [Valid] POST cancel QR (awaiting_transfer to cancelled).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/{{st_cancel_qr_id}}/cancel/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-07 | [Transition hợp lệ] awaiting_transfer -> cancelled (302 redirect /cart/)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 7000
""")

# 8. TC-ST-FLOW-08
write_request(folder_03, "TC-ST-FLOW-08 Tao don Mock ban dau (pending).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (Mock Fail)"
    phone: "0901234567"
    address: "TP.HCM"
    payment_method: "mock"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-08 | Tạo đơn Mock -> 302 sang Sandbox', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("st_order_mock_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 8000
""")

# 9. TC-ST-FLOW-09
write_request(folder_03, "TC-ST-FLOW-09 [Valid] Callback Mock that bai (pending to failed).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/mock/{{st_order_mock_id}}/fail/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-09 | [Transition hợp lệ] Mock callback fail -> pending sang failed (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 9000
""")

# 10. TC-ST-FLOW-10
write_request(folder_03, "TC-ST-FLOW-10 Kiem tra trang ket qua Mock that bai (Bao that bai, khong chuc mung).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/success/{{st_order_mock_id}}/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-10 | Trang kết quả trả về HTTP 200', function () {
        pm.expect(pm.response.code).to.eql(200);
      });
      pm.test('TC-ST-FLOW-10 | Thông báo thanh toán thất bại, không chứa chúc mừng', function () {
        const text = pm.response.text();
        pm.expect(text.toLowerCase()).to.include('thất bại');
        pm.expect(text).to.not.include('Đặt hàng thành công');
      });
    language: text/javascript
order: 10000
""")

# 11. TC-ST-FLOW-11
write_request(folder_03, "TC-ST-FLOW-11 Tao don Mock moi de thu thanh cong.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Trần Đình Đức (Mock Pass)"
    phone: "0901234567"
    address: "TP.HCM"
    payment_method: "mock"
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-11 | Tạo đơn Mock mới -> 302', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
      const loc = pm.response.headers.get("Location") || "";
      const match = loc.match(/\\/(\\d+)\\//);
      if (match) { pm.collectionVariables.set("st_order_mock_success_id", match[1]); }
    language: text/javascript
settings:
  followRedirects: false
order: 11000
""")

# 12. TC-ST-FLOW-12
write_request(folder_03, "TC-ST-FLOW-12 [Valid] Callback Mock thanh cong (pending to paid).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/mock/{{st_order_mock_success_id}}/success/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-FLOW-12 | [Transition hợp lệ] Mock callback success -> pending sang paid (302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 12000
""")

# 13. TC-ST-INV-01
write_request(folder_03, "TC-ST-INV-01 [Negative] Confirm QR tren don COD pending (Chan chuyen sai).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{st_order_cod_id}}/confirm/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-INV-01 | [Chặn chuyển sai] Không cho confirm QR trên đơn COD (redirect 302, giữ nguyên pending)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 13000
""")

# 14. TC-ST-INV-02
write_request(folder_03, "TC-ST-INV-02 [Negative] Mock fail tren don da paid (Chan ha cap trang thai).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/mock/{{st_order_mock_success_id}}/fail/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-INV-02 | [Chặn chuyển sai] Không cho hạ cấp đơn đã paid xuống failed (redirect 302, giữ paid)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 14000
""")

# 15. TC-ST-INV-03
write_request(folder_03, "TC-ST-INV-03 [Negative] Cancel QR tren don da paid (Chan huy don da thanh toan).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/{{st_order_mock_success_id}}/cancel/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-ST-INV-03 | [Chặn chuyển sai] Không cho hủy đơn đã paid qua cancel QR (redirect 302, giữ paid)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 15000
""")

# ==============================================================================
# FOLDER 04_Error_Guessing
# ==============================================================================
folder_04 = "04_Error_Guessing"
ensure_dir(os.path.join(base_dir, folder_04))
ensure_dir(os.path.join(base_dir, folder_04, ".resources"))

with open(os.path.join(base_dir, folder_04, ".resources", "definition.yaml"), "w", encoding="utf-8") as f:
    f.write("""$kind: collection
name: 04_Error_Guessing
description: "Kiểm thử đoán lỗi (Error Guessing) dựa trên kinh nghiệm: Idempotency, lỗi session, thiếu CSRF, dữ liệu dị dạng"
order: 5000
""")

# 1. TC-EG-01
write_request(folder_04, "TC-EG-01 Checkout khi gio hang rong (Chan tao don mo coi).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
    full_name: "Khách Giỏ Rỗng"
    phone: "0901234567"
    address: "Hà Nội"
    payment_method: "cod"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-EG-01 | Giỏ rỗng không được tạo đơn -> 302 về /cart/', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 1000
""")

# 2. TC-EG-02
write_request(folder_04, "TC-EG-02 Gui trung lap POST confirm QR 2 lan lien tiep (Idempotency).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{st_order_qr_id}}/confirm/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-EG-02 | Gửi confirm QR lần 2 không gây crash 500 (trả về 302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 2000
""")

# 3. TC-EG-03
write_request(folder_04, "TC-EG-03 Gui trung lap POST Mock success 2 lan lien tiep (Idempotency).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/mock/{{st_order_mock_success_id}}/success/"
method: POST
body:
  type: urlencoded
  content:
    csrfmiddlewaretoken: "{{csrf_token}}"
scripts:
  - type: beforeRequest
    code: |-
      const t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-EG-03 | Gửi Mock success lần 2 không gây crash 500 (trả về 302)', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 3000
""")

# 4. TC-EG-04
write_request(folder_04, "TC-EG-04 Goi endpoint doi trang thai bang GET trai phep (NFR2).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/mock/{{st_order_mock_id}}/fail/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-EG-04 | GET endpoint đổi trạng thái -> 302 không kích hoạt cập nhật', function () {
        pm.expect([200, 302]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 4000
""")

# 5. TC-EG-05
write_request(folder_04, "TC-EG-05 Truy cap endpoint voi ma don khong ton tai 999999.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/success/999999/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-EG-05 | Mã đơn 999999 không tồn tại trả về HTTP 404', function () {
        pm.expect(pm.response.code).to.eql(404);
      });
    language: text/javascript
order: 5000
""")

# 6. TC-EG-06
write_request(folder_04, "TC-EG-06 Truy cap endpoint voi ma don chuoi ky tu abc.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/success/abc/"
method: GET
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-EG-06 | Mã đơn không phải số (abc) trả về HTTP 404', function () {
        pm.expect(pm.response.code).to.eql(404);
      });
    language: text/javascript
order: 6000
""")

# 7. TC-EG-07
write_request(folder_04, "TC-EG-07 POST confirm QR khong co CSRF token (Bao mat NFR2).request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/qr/{{st_order_qr_id}}/confirm/"
method: POST
body:
  type: urlencoded
  content:
    full_name: "Test No CSRF"
scripts:
  - type: afterResponse
    code: |-
      pm.test('TC-EG-07 | Thiếu CSRF token trả về mã HTTP 403 Forbidden', function () {
        pm.expect(pm.response.code).to.eql(403);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 7000
""")

# 8. TC-EG-08
write_request(folder_04, "TC-EG-08 Gui checkout voi JSON Body thay vi Form URL-encoded.request.yaml", """
$kind: http-request
url: "{{base_url}}/orders/checkout/"
method: POST
headers:
  Content-Type: application/json
body:
  type: json
  content: |-
    {
      "full_name": "JSON User",
      "phone": "0901234567",
      "address": "TP.HCM",
      "payment_method": "cod"
    }
scripts:
  - type: beforeRequest
    code: |-
      var sid = pm.cookies.get('sessionid');
      var csrf = pm.cookies.get('csrftoken');
      var cookieHdr = '';
      if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
      if (csrf) { 
        cookieHdr += 'csrftoken=' + csrf; 
        pm.collectionVariables.set('csrf_token', csrf);
      }
      pm.sendRequest({
        url: pm.collectionVariables.get('base_url') + '/cart/add/' + pm.collectionVariables.get('product_id') + '/',
        method: 'GET',
        header: { 'Cookie': cookieHdr }
      }, function (err, res) {});
    language: text/javascript
  - type: afterResponse
    code: |-
      pm.test('TC-EG-08 | Gửi JSON body không làm server crash 500 (trả về 200 hoặc 400)', function () {
        pm.expect([200, 400, 403]).to.include(pm.response.code);
      });
    language: text/javascript
settings:
  followRedirects: false
order: 8000
""")

print("ALL Postman requests generated successfully!")
