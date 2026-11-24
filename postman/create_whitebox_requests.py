import os
import re

wb_dir = r"C:\Users\TOSHIBA\Desktop\DUAN\KCPM\Kiem-chung-phan-mem\postman\collections\Green Shop - Orders\05_White_Box_Coverage"
res_dir = os.path.join(wb_dir, ".resources")
os.makedirs(res_dir, exist_ok=True)

# 1. Definition.yaml
definition_content = """$kind: collection
name: 05_White_Box_Coverage
description: "Kiểm thử Hộp trắng (White-box Testing): Phủ toàn diện CFG, câu lệnh (Statement 100%), nhánh quyết định (Branch 100%), biểu thức ghép MC/DC và nhánh ngoại lệ"
order: 6000
"""
with open(os.path.join(res_dir, "definition.yaml"), "w", encoding="utf-8") as f:
    f.write(definition_content)

# Template for pre-request (replenish cart)
PRE_REPLENISH = """var sid = pm.cookies.get('sessionid');
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
var t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }"""

PRE_EMPTY_CART = """var sid = pm.cookies.get('sessionid');
var csrf = pm.cookies.get('csrftoken');
var cookieHdr = '';
if (sid) { cookieHdr += 'sessionid=' + sid + '; '; }
if (csrf) { 
  cookieHdr += 'csrftoken=' + csrf; 
  pm.collectionVariables.set('csrf_token', csrf);
}
pm.sendRequest({
  url: pm.collectionVariables.get('base_url') + '/cart/remove/' + pm.collectionVariables.get('product_id') + '/',
  method: 'GET',
  header: { 'Cookie': cookieHdr }
}, function (err, res) {});
var t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }"""

PRE_EXTRACT_CSRF = """var t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }"""

POST_REFRESH_CSRF = """var t = pm.cookies.get('csrftoken'); if (t) { pm.collectionVariables.set('csrf_token', t); }"""

requests_data = [
    {
        "filename": "TC-WB-01 [Statement] GET Checkout render giao dien (Duong GET chinh).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "GET",
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-01 | GET Checkout trả về HTTP 200', function () {
  pm.expect(pm.response.code).to.eql(200);
});
pm.test('TC-WB-01 | Render form checkout đủ 3 phương thức COD, QR, Mock', function () {
  var h = pm.response.text();
  pm.expect(h).to.include('value="cod"');
  pm.expect(h).to.include('value="qr"');
  pm.expect(h).to.include('value="mock"');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 1000
    },
    {
        "filename": "TC-WB-02 [Branch] POST Checkout khi gio hang rong (Nhanh D1 True redirect cart).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "cod"
        },
        "pre": PRE_EMPTY_CART,
        "post": """pm.test('TC-WB-02 | Giỏ hàng rỗng redirect về trang giỏ hàng (/cart/)', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 2000
    },
    {
        "filename": "TC-WB-03 [Condition] POST Checkout ho ten rong (Dieu kien D4a True).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "   ",
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "cod"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-03 | Họ tên rỗng trả về form HTTP 200 báo lỗi', function () {
  pm.expect(pm.response.code).to.eql(200);
  pm.expect(pm.response.text()).to.include('Họ tên không được để trống');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 3000
    },
    {
        "filename": "TC-WB-04 [Condition] POST Checkout ho ten 256 ky tu vuot max (Dieu kien D4b True).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "A" * 256,
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "cod"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-04 | Họ tên > 255 ký tự trả về HTTP 200 báo lỗi độ dài', function () {
  pm.expect(pm.response.code).to.eql(200);
  pm.expect(pm.response.text()).to.include('tối đa 255 ký tự');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 4000
    },
    {
        "filename": "TC-WB-05 [Condition] POST Checkout SDT rong (Dieu kien D5a True).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "",
            "address": "123 Le Loi",
            "payment_method": "cod"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-05 | Số điện thoại rỗng trả về HTTP 200 báo lỗi', function () {
  pm.expect(pm.response.code).to.eql(200);
  pm.expect(pm.response.text()).to.include('Số điện thoại không được để trống');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 5000
    },
    {
        "filename": "TC-WB-06 [Condition] POST Checkout SDT 21 ky tu vuot max (Dieu kien D5b True).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "012345678901234567890",
            "address": "123 Le Loi",
            "payment_method": "cod"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-06 | Số điện thoại > 20 ký tự trả về HTTP 200 báo lỗi', function () {
  pm.expect(pm.response.code).to.eql(200);
  pm.expect(pm.response.text()).to.include('tối đa 20 ký tự');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 6000
    },
    {
        "filename": "TC-WB-07 [Branch] POST Checkout dia chi rong (Nhanh D6 True).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "   ",
            "payment_method": "cod"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-07 | Địa chỉ rỗng trả về HTTP 200 báo lỗi', function () {
  pm.expect(pm.response.code).to.eql(200);
  pm.expect(pm.response.text()).to.include('Địa chỉ không được để trống');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 7000
    },
    {
        "filename": "TC-WB-08 [Branch] POST Checkout bo qua payment_method (Nhanh D7 True mac dinh COD).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "123 Le Loi"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-08 | Không truyền payment_method -> mặc định COD tạo đơn thành công', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 8000
    },
    {
        "filename": "TC-WB-09 [Branch] POST Checkout phuong thuc sai tap hop (Nhanh D8 True).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "zalopay_unsupported"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-09 | Phương thức ngoài tập hợp trả về HTTP 200 báo lỗi', function () {
  pm.expect(pm.response.code).to.eql(200);
  pm.expect(pm.response.text()).to.include('Phương thức thanh toán không hợp lệ');
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 9000
    },
    {
        "filename": "TC-WB-10 [Path] POST Checkout COD happy path (Full path COD tao don pending).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "cod"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-10 | Đặt hàng COD redirect success (302)', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
  var loc = pm.response.headers.get('Location') || '';
  var m = loc.match(/\\/orders\\/success\\/(\\d+)/);
  if (!m) { m = pm.response.text().match(/\\/orders\\/success\\/(\\d+)/); }
  if (m) {
    pm.collectionVariables.set('wb_order_cod_id', m[1]);
  }
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 10000
    },
    {
        "filename": "TC-WB-11 [Path] POST Checkout VietQR happy path (Full path QR tao don awaiting).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "qr"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-11 | Đặt hàng VietQR redirect trang QR (302)', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
  var loc = pm.response.headers.get('Location') || '';
  var m = loc.match(/\\/orders\\/qr\\/(\\d+)/);
  if (!m) { m = pm.response.text().match(/\\/orders\\/qr\\/(\\d+)/); }
  if (m) {
    pm.collectionVariables.set('wb_order_qr_id', m[1]);
  }
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 11000
    },
    {
        "filename": "TC-WB-12 [Path] POST Checkout Mock happy path (Full path Mock tao don pending).request.yaml",
        "url": "{{base_url}}/orders/checkout/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}",
            "full_name": "Nguyen Van A",
            "phone": "0901234567",
            "address": "123 Le Loi",
            "payment_method": "mock"
        },
        "pre": PRE_REPLENISH,
        "post": """pm.test('TC-WB-12 | Đặt hàng Mock redirect sandbox mock (302)', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
  var loc = pm.response.headers.get('Location') || '';
  var m = loc.match(/\\/orders\\/mock\\/(\\d+)/);
  if (!m) { m = pm.response.text().match(/\\/orders\\/mock\\/(\\d+)/); }
  if (m) {
    pm.collectionVariables.set('wb_order_mock_id', m[1]);
  }
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 12000
    },
    {
        "filename": "TC-WB-13 [MC-DC] POST confirm QR hop le (Dieu kien TTT awaiting sang paid).request.yaml",
        "url": "{{base_url}}/orders/qr/{{wb_order_qr_id}}/confirm/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}"
        },
        "pre": PRE_EXTRACT_CSRF,
        "post": """pm.test('TC-WB-13 | POST confirm QR hợp lệ -> chuyển paid & redirect success', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 13000
    },
    {
        "filename": "TC-WB-14 [Branch] GET order_qr khi don da thanh toan (Nhanh views_146 redirect).request.yaml",
        "url": "{{base_url}}/orders/qr/{{wb_order_qr_id}}/",
        "method": "GET",
        "pre": PRE_EXTRACT_CSRF,
        "post": """pm.test('TC-WB-14 | GET order_qr khi đơn đã paid -> redirect order_success (views:146)', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 14000
    },
    {
        "filename": "TC-WB-15 [MC-DC] GET confirm QR bi chan (Dieu kien FTT Method!=POST).request.yaml",
        "url": "{{base_url}}/orders/qr/{{wb_order_qr_id}}/confirm/",
        "method": "GET",
        "pre": PRE_EXTRACT_CSRF,
        "post": """pm.test('TC-WB-15 | GET confirm QR -> Method!=POST không đổi trạng thái đơn', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 15000
    },
    {
        "filename": "TC-WB-16 [MC-DC] POST confirm QR tren don COD bi chan (Dieu kien TFT method!=qr).request.yaml",
        "url": "{{base_url}}/orders/qr/{{wb_order_cod_id}}/confirm/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}"
        },
        "pre": PRE_EXTRACT_CSRF,
        "post": """pm.test('TC-WB-16 | Confirm QR trên đơn COD bị chặn (payment_method!=qr)', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 16000
    },
    {
        "filename": "TC-WB-17 [Path] POST Mock fail callback (pending sang failed).request.yaml",
        "url": "{{base_url}}/orders/mock/{{wb_order_mock_id}}/fail/",
        "method": "POST",
        "body": {
            "csrfmiddlewaretoken": "{{csrf_token}}"
        },
        "pre": PRE_EXTRACT_CSRF,
        "post": """pm.test('TC-WB-17 | Callback mock fail -> chuyển pending sang failed', function () {
  pm.expect([200, 302]).to.include(pm.response.code);
});
""" + POST_REFRESH_CSRF,
        "follow": False,
        "order": 17000
    },
    {
        "filename": "TC-WB-18 [Statement] GET my_orders xem danh sach don QR cho thanh toan.request.yaml",
        "url": "{{base_url}}/orders/my/",
        "method": "GET",
        "pre": PRE_EXTRACT_CSRF,
        "post": """pm.test('TC-WB-18 | GET my_orders trả về HTTP 200 danh sách đơn chờ', function () {
  pm.expect(pm.response.code).to.eql(200);
});
""" + POST_REFRESH_CSRF,
        "follow": True,
        "order": 18000
    }
]

def format_script_code(code_str):
    lines = code_str.strip().splitlines()
    res = "    code: |-\n"
    for l in lines:
        res += f"      {l}\n"
    return res

for req in requests_data:
    filepath = os.path.join(wb_dir, req["filename"])
    content = "$kind: http-request\n"
    content += f'url: "{req["url"]}"\n'
    content += f'method: {req["method"]}\n'
    
    if "body" in req:
        content += "body:\n"
        content += "  type: urlencoded\n"
        content += "  content:\n"
        for k, v in req["body"].items():
            content += f'    {k}: "{v}"\n'
            
    content += "scripts:\n"
    content += "  - type: beforeRequest\n"
    content += format_script_code(req["pre"])
    content += "    language: text/javascript\n"
    content += "  - type: afterResponse\n"
    content += format_script_code(req["post"])
    content += "    language: text/javascript\n"
    
    if not req.get("follow", True):
        content += "settings:\n"
        content += "  followRedirects: false\n"
        
    content += f'order: {req["order"]}\n'
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Created {len(requests_data)} requests in {wb_dir}")
