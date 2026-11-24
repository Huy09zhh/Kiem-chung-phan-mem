"""Sinh lại collection BVA: mỗi case 3 request (chuẩn bị, biên, kiểm chứng), dùng thư viện bva_lib."""
import json, copy, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.dirname(HERE)   # thư mục postman/ (bva_generator nằm trong postman/)
SRC = os.path.join(PM, "Green Shop - Account & Auth - BVA.postman_collection.json")
old = json.load(open(SRC, encoding="utf-8"))   # mô tả case và thông tin folder lấy từ chính collection hiện tại
lib = open(os.path.join(HERE, "lib.js"), encoding="utf-8").read()

RX = {
    "req": "required|bắt buộc",
    "u150": "at most 150|(?:quá|đa) 150|150 (?:characters|ký tự)",
    "p8": "too short|at least 8|ít nhất 8",
    "p128": "at most 128|(?:quá|đa) 128|128 (?:characters|ký tự)",
    "eshort": "valid email|email hợp lệ",
    "e254": "at most 254|(?:quá|đa) 254|254 (?:characters|ký tự)",
}
# (folder index trong collection cũ, kind, field, [(len, ok, rx|None)], fields)
SPEC = [
    (1, "reg", "username", [(0, 0, "req"), (1, 1, None), (2, 1, None), (76, 1, None), (149, 1, None), (150, 1, None), (151, 0, "u150")], ["username"]),
    (2, "reg", "password", [(7, 0, "p8"), (8, 1, None), (9, 1, None), (68, 1, None), (127, 1, None), (128, 1, None), (129, 0, "p128")], ["password1", "password2"]),
    (3, "reg", "email", [(5, 0, "eshort"), (6, 1, None), (7, 1, None), (130, 1, None), (253, 1, None), (254, 1, None), (255, 0, "e254")], ["email"]),
    (4, "pro", "first_name", [(0, 1, None), (1, 1, None), (2, 1, None), (75, 1, None), (149, 1, None), (150, 1, None), (151, 0, "u150")], ["first_name"]),
    (5, "pro", "last_name", [(0, 1, None), (1, 1, None), (2, 1, None), (75, 1, None), (149, 1, None), (150, 1, None), (151, 0, "u150")], ["last_name"]),
    (6, "pro", "email", [(5, 0, "eshort"), (6, 1, None), (7, 1, None), (130, 1, None), (253, 1, None), (254, 1, None), (255, 0, "e254")], ["email"]),
    (7, "chg", "password", [(7, 0, "p8"), (8, 1, None), (9, 1, None), (68, 1, None), (127, 1, None), (128, 1, None), (129, 0, "p128")], ["new_password1", "new_password2"]),
    (8, "rst", "password", [(7, 0, "p8"), (8, 1, None), (9, 1, None), (68, 1, None), (127, 1, None), (128, 1, None), (129, 0, "p128")], ["new_password1", "new_password2"]),
]
PFX = {1: "regusr", 2: "regpwd", 3: "regmail", 4: "profirst", 5: "prolast", 6: "promail", 7: "chgpwd", 8: "rstpwd"}
PREFIX = {1: "REG-USER", 2: "REG-PWD", 3: "REG-EMAIL", 4: "PRO-FIRST", 5: "PRO-LAST", 6: "PRO-EMAIL", 7: "CHANGE-PWD", 8: "RESET-PWD"}


def form(fields):
    return {"mode": "urlencoded", "urlencoded": [{"key": k, "value": v, "type": "text"} for k, v in fields]}


def url(raw):
    path = raw.replace("{{base_url}}", "").strip("/")
    return {"raw": raw, "host": ["{{base_url}}"], "path": (path.split("/") if path else []) + [""]}


def script(cfg, fn):
    return {"listen": "prerequest" if fn.startswith("pre") else "test", "script": {"type": "text/javascript", "exec": [
        "const B = eval(pm.collectionVariables.get('bva_lib'));   // thư viện dùng chung, xem biến bva_lib",
        "const CFG = " + json.dumps(cfg, ensure_ascii=False) + ";",
        "B." + fn + "(CFG);"]}}


def req(name, method, raw, body, cfg, events):
    r = {"name": name, "protocolProfileBehavior": {"followRedirects": False},
         "event": [script(cfg, e) for e in events],
         "request": {"method": method, "header": [], "url": url(raw)}, "response": []}
    if body is not None:
        r["request"]["body"] = body
    return r


CSRF = ("csrfmiddlewaretoken", "{{bva_csrf}}")
REG_BODY = form([CSRF, ("username", "{{bva_user}}"), ("email", "{{bva_email}}"), ("password1", "{{bva_password}}"), ("password2", "{{bva_password}}")])
LOGIN_BODY = form([CSRF, ("username", "{{bva_user}}"), ("password", "{{bva_login_pw}}")])


def case_request(cfg, desc):
    k = cfg["kind"]; name = "%s | %s" % (cfg["id"], "Accept" if cfg["ok"] else "Reject")
    if k == "reg":
        m, raw, body = "POST", "{{base_url}}/accounts/register/", REG_BODY
    elif k == "pro":
        m, raw, body = "POST", "{{base_url}}/accounts/profile/edit/", form([CSRF, ("first_name", "{{bva_post_first}}"), ("last_name", "{{bva_post_last}}"), ("email", "{{bva_post_email}}")])
    elif k == "chg":
        m, raw, body = "POST", "{{base_url}}/accounts/password/change/", form([CSRF, ("old_password", "{{old_password}}"), ("new_password1", "{{bva_new_password}}"), ("new_password2", "{{bva_new_password}}")])
    else:
        m, raw, body = "POST", "{{base_url}}/accounts/password/reset/{{reset_uid}}/set-password/", form([CSRF, ("new_password1", "{{bva_new_password}}"), ("new_password2", "{{bva_new_password}}")])
    r = req(name, m, raw, body, cfg, ["pre", "test"])
    if desc: r["request"]["description"] = desc
    return r


new = copy.deepcopy(old)
new["item"] = [copy.deepcopy(old["item"][0])]
for fi, kind, field, vals, fields in SPEC:
    fo = copy.deepcopy(old["item"][fi]); fo["item"] = []
    olds = {x["name"].split(" | ")[0]: x for x in old["item"][fi]["item"]}
    def desc_of(x): return x["request"].get("description") if "request" in x else x.get("description")
    for ln, ok, rx in vals:
        pre = PREFIX[fi]
        cid = "BVA-AA-%s-L%03d" % (pre, ln)
        cfg = {"id": cid, "pfx": PFX[fi], "tag": "L%03d" % ln, "kind": kind, "field": field, "len": ln, "ok": bool(ok), "fields": fields}
        if rx: cfg["rx"] = RX[rx]
        fo["item"].append(case_request(cfg, desc_of(olds[cid]) if cid in olds else None))
    new["item"].append(fo)

# biến collection: thêm thư viện và tài khoản superuser cho hộp thư dev (folder 08)
have = {v["key"] for v in new["variable"]}
extra = {"bva_lib": lib, "bva_login_pw": "", "bva_post_first": "", "bva_post_last": "", "bva_post_email": "",
         "bva_code_letters": "4", "bva_run_code": "", "bva_mailbox_admin_user": "admin", "bva_mailbox_admin_password": "Admin@12345"}
for k, v in extra.items():
    if k in have:
        for x in new["variable"]:
            if x["key"] == k: x["value"] = v
    else:
        new["variable"].append({"key": k, "value": v, "type": "default"} if True else None)
new["info"]["description"] = (old["info"]["description"].split("Giữ nguyên các nhóm")[0].split(chr(10) + chr(10) + "Cấu trúc mới")[0].rstrip() +
    "\n\nCấu trúc mới (cập nhật 24/11/2026): mỗi case là đúng 1 request (request giá trị biên). Script trước request chuẩn bị dữ liệu, script sau request kiểm chứng. "
    "Các việc phụ (CSRF, đăng xuất, tạo tài khoản, đọc hộp thư dev, dọn dẹp) chạy ngầm bằng pm.sendRequest trong script, dùng thư viện biến bva_lib. "
    "Mỗi biến có đúng 7 giá trị (min-, min, min+, nom, max-, max, max+); với first_name/last_name min- không áp dụng nên dùng độ dài 2 làm giá trị thứ 7. "
    "Nhóm 08 cần tài khoản superuser đọc hộp thư dev: mặc định lấy từ biến collection bva_mailbox_admin_user / bva_mailbox_admin_password (có thể ghi đè bằng Environment) và backend email filebased (EMAIL_HOST_USER rỗng).\n\nPhạm vi: 00–08.")
out = sys.argv[1] if len(sys.argv) > 1 else SRC
open(out, "w", encoding="utf-8").write(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
n = sum(len(f["item"]) for f in new["item"][1:]); cs = n
print("cases", cs, "requests", n, "+", len(new["item"][0]["item"]), "->", out)
