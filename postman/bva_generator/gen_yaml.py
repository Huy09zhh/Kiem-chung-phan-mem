import json, os, shutil, yaml, re
PM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # thư mục postman/
J = os.path.join(PM, "Green Shop - Account & Auth - BVA.postman_collection.json")
D = os.path.join(PM, "collections", "Green Shop - Account & Auth - BVA")
c = json.load(open(J, encoding="utf-8"))

class L(str): pass
def lit(dumper, data): return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
yaml.add_representer(L, lit, Dumper=yaml.SafeDumper)
def S(x): return L(x) if isinstance(x, str) and "\n" in x else x
def dump(d): return yaml.dump(d, Dumper=yaml.SafeDumper, allow_unicode=True, sort_keys=False, width=100000, default_flow_style=False)
def fname(n): return re.sub(r'[<>:"/\|?*]', "-", n.replace(" | ", "  -  "))

# giữ name của collection trong YAML hiện có, thay mô tả + biến
old_root = yaml.safe_load(open(os.path.join(D, ".resources", "definition.yaml"), encoding="utf-8"))
root = {"$kind": "collection", "name": old_root.get("name", c["info"]["name"]), "description": S(c["info"]["description"]),
        "variables": {v["key"]: v.get("value", "") for v in c["variable"]}}
shutil.rmtree(D)
os.makedirs(os.path.join(D, ".resources"))
open(os.path.join(D, ".resources", "definition.yaml"), "w", encoding="utf-8", newline="\n").write(dump({**root, "description": S(root["description"])}))

n_req = 0
for fi, fo in enumerate(c["item"]):
    fd = os.path.join(D, fname(fo["name"])); os.makedirs(os.path.join(fd, ".resources"))
    meta = {"$kind": "collection"}
    if fo.get("description"): meta["description"] = S(fo["description"])
    meta["order"] = (fi + 1) * 1000
    open(os.path.join(fd, ".resources", "definition.yaml"), "w", encoding="utf-8", newline="\n").write(dump(meta))
    for ri, r in enumerate(fo["item"]):
        q = r["request"]; u = q["url"]["raw"] if isinstance(q["url"], dict) else q["url"]
        y = {"$kind": "http-request", "url": u, "method": q["method"]}
        if q.get("description"): y["description"] = S(q["description"])
        b = q.get("body")
        if b and b.get("mode") == "urlencoded":
            y["body"] = {"type": "urlencoded", "content": {f["key"]: f["value"] for f in b["urlencoded"]}}
        sc = []
        for e in r.get("event", []):
            sc.append({"type": "beforeRequest" if e["listen"] == "prerequest" else "afterResponse", "code": S("\n".join(e["script"]["exec"]))})
        if sc: y["scripts"] = sc
        if r.get("protocolProfileBehavior", {}).get("followRedirects") is False: y["settings"] = {"followRedirects": False}
        y["order"] = (ri + 1) * 1000
        open(os.path.join(fd, fname(r["name"]) + ".request.yaml"), "w", encoding="utf-8", newline="\n").write(dump(y)); n_req += 1
print("đã ghi", n_req, "request yaml")
# kiểm tra đọc lại
cnt = 0; bad = 0
for dp, dn, fn in os.walk(D):
    for f in fn:
        if f.endswith(".yaml"):
            try: yaml.safe_load(open(os.path.join(dp, f), encoding="utf-8")); cnt += 1
            except Exception as e: bad += 1; print("LỖI", f, str(e)[:80])
print("yaml đọc được:", cnt, "lỗi:", bad)
