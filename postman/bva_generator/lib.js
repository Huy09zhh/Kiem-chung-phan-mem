(function () {
  // Thư viện dùng chung cho BVA (3 request mỗi case): chuẩn bị, kiểm tra biên, kiểm chứng.
  // Mọi việc phụ (CSRF, đăng xuất, dọn dẹp) chạy ngầm bằng pm.sendRequest, không hiện thành request trong Runner.
  var cv = pm.collectionVariables;
  var N = { username: 76, password: 68, email: 130, first_name: 75, last_name: 75 };
  var B = {};

  B.base = function () { return pm.variables.replaceIn('{{base_url}}'); };
  B.fail = function (what, e) { pm.test('Gọi được ' + what, function () { throw (e || new Error('không có phản hồi')); }); };
  B.get = function (path, cb) {
    pm.sendRequest({ url: B.base() + path, method: 'GET' }, function (e, r) { if (e || !r) { B.fail(path, e); return; } cb(r); });
  };
  B.post = function (path, fields, cb) {
    var body = Object.keys(fields).map(function (k) { return { key: k, value: String(fields[k]) }; });
    pm.sendRequest({ url: B.base() + path, method: 'POST', body: { mode: 'urlencoded', urlencoded: body } }, function (e, r) { if (e || !r) { B.fail(path, e); return; } cb(r); });
  };

  // ---------- phân tích HTML ----------
  function decode(v) { return String(v).replace(/&#x([0-9a-f]+);/gi, function (_, n) { return String.fromCodePoint(parseInt(n, 16)); }).replace(/&#([0-9]+);/g, function (_, n) { return String.fromCodePoint(Number(n)); }).replace(/&quot;/g, '"').replace(/&#x27;|&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); }
  function attr(tag, key) { var m = tag.match(new RegExp('(?:^|\\s)' + key + '=["\']([^"\']*)["\']', 'i')); return m ? decode(m[1]) : null; }
  function inputs(html) { return html.match(/<input\b[^>]*>/gi) || []; }
  function input(html, name) { return inputs(html).find(function (t) { return attr(t, 'name') === name; }) || null; }
  function value(html, name) { var t = input(html, name); return t ? (attr(t, 'value') || '') : null; }
  function shownUser(html) { var t = inputs(html).find(function (x) { return attr(x, 'id') === 'id_username_display'; }); return t ? attr(t, 'value') : null; }
  function fieldError(html, name) {
    var tag = input(html, name); if (!tag) { return ''; }
    var id = 'id_' + name + '_error';
    var blocks = html.match(/<(?:ul|small|span)\b[^>]*(?:errorlist|auth-error)[^>]*>[\s\S]*?<\/(?:ul|small|span)>/gi) || [];
    var own = blocks.find(function (b) { return b.indexOf(id) !== -1; });
    if (own) { return decode(own.replace(/<[^>]*>/g, ' ')); }
    var after = html.slice(html.indexOf(tag) + tag.length).split(/<\/(?:div|p)>/i)[0];
    var error = after.match(/<(?:small|span|ul)\b[^>]*(?:auth-error|errorlist|color:\s*red)[^>]*>[\s\S]*?<\/(?:small|span|ul)>/i);
    return error ? decode(error[0].replace(/<[^>]*>/g, ' ')) : '';
  }
  B.tokenOf = function (html) { var m = html.match(/name=["']csrfmiddlewaretoken["'][^>]*value=["']([^"']+)["']/); return m ? m[1] : ''; };
  function locationPath() { var loc = pm.response.headers.get('Location') || ''; return loc.replace(/^https?:\/\/[^/]+/i, '').split('?')[0]; }

  // ---------- phiên làm việc ----------
  B.token = function (path, cb) { B.get(path, function (r) { cv.set('bva_csrf', B.tokenOf(r.text())); if (cb) { cb(r); } }); };
  // đưa phiên về Guest (đăng xuất), rồi lấy CSRF của trang path (nếu có)
  B.guest = function (path, cb) {
    B.get('/accounts/password/change/', function (r) {
      B.post('/accounts/logout/', { csrfmiddlewaretoken: B.tokenOf(r.text()) }, function () {
        if (path) { B.token(path, cb); } else if (cb) { cb(); }
      });
    });
  };
  B.login = function (user, pass, cb) {
    B.guest('/accounts/login/', function () {
      B.post('/accounts/login/', { csrfmiddlewaretoken: cv.get('bva_csrf'), username: user, password: pass }, cb);
    });
  };
  function adminCreds() {
    return { u: pm.environment.get('bva_mailbox_admin_user') || cv.get('bva_mailbox_admin_user'), p: pm.environment.get('bva_mailbox_admin_password') || cv.get('bva_mailbox_admin_password') };
  }

  // ---------- dữ liệu theo độ dài ----------
  // Quy tắc đặt tên: <phần đầu theo case>_<mã lượt chạy>_<đệm 0123456789 cho đủ độ dài>
  // Mã lượt chạy: các chữ cái tăng dần, mỗi chữ theo sau là số thứ tự của nó (a1b2c3d4, D4E5G7K11), lấy theo phút chạy.
  function binom(n, k) { if (k < 0 || k > n) { return 0; } var r = 1; for (var i = 1; i <= k; i++) { r = r * (n - k + i) / i; } return Math.round(r); }
  function unrank(idx, n, k) {
    var out = [], start = 0;
    for (var i = 0; i < k; i++) {
      for (var c = start; c < n; c++) { var cnt = binom(n - c - 1, k - i - 1); if (idx < cnt) { out.push(c); start = c + 1; break; } idx -= cnt; }
    }
    return out;
  }
  // Số chữ cái mặc định 4; chỉnh bằng biến collection bva_code_letters (3 = ngắn hơn nhưng dễ trùng, 5 = dài hơn, ít trùng)
  function runCode() {
    var K = parseInt(cv.get('bva_code_letters'), 10) || 4, total = binom(26, K), m = Math.floor(Date.now() / 60000);
    var upper = Math.floor(m / total) % 2 === 1;
    return unrank(m % total, 26, K).map(function (c) { var L = String.fromCharCode(97 + c); return (upper ? L.toUpperCase() : L) + (c + 1); }).join('');
  }
  function fill(head, n) { var need = n - head.length; if (need <= 0) { return head.slice(0, n); } return head + '0123456789'.repeat(Math.ceil(need / 10)).slice(0, need); }
  function rep(word, n) { return n ? word.repeat(Math.ceil(n / word.length)).slice(0, n) : ''; }
  function password(n, variant) { return rep(variant === 'new' ? 'Newp@456' : 'Pass@123', n); }
  function username(n, head) { if (!n) { return ''; } if (n < 3) { return Array.from({ length: n }, function () { return String.fromCodePoint(0x4e00 + Math.floor(Math.random() * 16000)); }).join(''); } return fill(head + '_', n); }
  function email(n, head) {
    if (!n) { return ''; } if (n === 5) { return 'a@b.c'; }
    if (n < 70) { var pick = function () { return String.fromCharCode(97 + Math.floor(Math.random() * 26)); }; if (n < 8) { return pick().repeat(n - 5) + '@' + pick() + '.' + pick() + pick(); } return fill(head + '_', n - 13) + '@example.test'; }
    var local = fill(head + '_', 64), remaining = n - 65 - 5, labels = [];
    while (remaining > 0) { var take = Math.min(63, remaining); if (remaining - take === 1) { take--; } labels.push(fill('d', take)); remaining -= take; if (remaining > 0) { remaining--; } }
    var res = local + '@' + labels.join('.') + '.test'; if (res.length !== n) { throw new Error('Email length mismatch'); } return res;
  }
  // tạo toàn bộ dữ liệu của case: các biến khác giữ nominal, chỉ biến đang xét đổi độ dài
  B.prepare = function (cfg) {
    var code = runCode(), head = cfg.pfx + '_' + cfg.tag + '_' + code;
    var L = { username: N.username, password: N.password, email: N.email };
    if (cfg.kind === 'reg') { L[cfg.field] = cfg.len; }
    cv.set('bva_run_code', code);
    cv.set('bva_user', username(L.username, head));
    cv.set('bva_email', email(L.email, head));
    cv.set('bva_password', password(L.password));
    cv.set('old_password', cv.get('bva_password'));
    cv.set('bva_first_name', rep('FirstName', N.first_name));
    cv.set('bva_last_name', rep('LastName', N.last_name));
    cv.set('bva_post_first', cfg.field === 'first_name' ? rep('FirstName', cfg.len) : cv.get('bva_first_name'));
    cv.set('bva_post_last', cfg.field === 'last_name' ? rep('LastName', cfg.len) : cv.get('bva_last_name'));
    cv.set('bva_post_email', cfg.kind === 'pro' && cfg.field === 'email' ? email(cfg.len, head + '_new') : cv.get('bva_email'));
    cv.set('bva_new_password', (cfg.kind === 'chg' || cfg.kind === 'rst') ? password(cfg.len, 'new') : '');
    cv.set('bva_login_pw', cfg.kind === 'reg' ? cv.get('bva_password') : (cfg.ok ? cv.get('bva_new_password') : cv.get('old_password')));
    cv.set('bva_case', cfg.id);
    var checks = { username: cv.get('bva_user').length === L.username, email: cv.get('bva_email').length === L.email, password: cv.get('bva_password').length === L.password };
    Object.keys(checks).forEach(function (k) { if (!checks[k]) { throw new Error('Sai độ dài dữ liệu: ' + k); } });
  };

  // ---------- kiểm tra chung ----------
  function expectOk(loc) { pm.test('HTTP 302', function () { pm.response.to.have.status(302); }); pm.test('Đúng trang chuyển hướng', function () { pm.expect(locationPath()).to.eql(loc); }); }
  function expectReject(cfg) {
    pm.test('HTTP 200', function () { pm.response.to.have.status(200); });
    pm.test('Lỗi đúng trường và đúng nguyên nhân', function () {
      var html = pm.response.text();
      var messages = cfg.fields.map(function (f) { return fieldError(html, f); }).filter(Boolean);
      pm.expect(messages, 'Không có lỗi gắn với trường đang kiểm tra').to.not.be.empty;
      pm.expect(messages.join(' ')).to.match(new RegExp(cfg.rx, 'i'));
    });
  }
  function hasSession(html, user) { return shownUser(html) === user; }
  function noSession(r, what) {
    pm.test(what || 'Không có phiên đăng nhập', function () { var h = r.text(); pm.expect(shownUser(h)).to.eql(null); pm.expect(input(h, 'password')).to.not.eql(null); });
  }
  // sau khi đăng nhập thành công: kiểm tra đúng tài khoản; sau đó chạy tiếp cb
  function checkSession(cfg, cb) {
    B.get('/accounts/profile/edit/', function (r) {
      pm.test('Đúng tài khoản (phiên đăng nhập)', function () { pm.expect(r.code).to.eql(200); pm.expect(hasSession(r.text(), cv.get('bva_user'))).to.eql(true); });
      if (cfg.kind === 'reg') { pm.test('Lưu đúng email', function () { pm.expect(value(r.text(), 'email')).to.eql(cv.get('bva_email')); }); }
      cb(r);
    });
  }
  // đăng nhập thử bằng mật khẩu bị từ chối: phải thất bại và không có phiên
  function rejectedLogin(pass, what, cb) {
    B.guest('/accounts/login/', function () {
      B.post('/accounts/login/', { csrfmiddlewaretoken: cv.get('bva_csrf'), username: cv.get('bva_user'), password: pass }, function (r) {
        pm.test(what, function () { pm.expect(r.code).to.eql(200); pm.expect(r.text()).to.match(/auth-error(?:-box)?|errorlist/); });
        B.get('/accounts/profile/edit/', function (r2) { noSession(r2); cb(); });
      });
    });
  }

  // ---------- chuẩn bị (chạy trong script trước request) ----------
  var SLOG = [];
  function log(name, ok, detail) { SLOG.push({ n: name, ok: !!ok, d: detail || '' }); cv.set('bva_setup_log', JSON.stringify(SLOG)); }
  function registerNominal(cb) {
    B.guest('/accounts/register/', function () {
      B.post('/accounts/register/', { csrfmiddlewaretoken: cv.get('bva_csrf'), username: cv.get('bva_user'), email: cv.get('bva_email'), password1: cv.get('bva_password'), password2: cv.get('bva_password') }, cb);
    });
  }
  B.pre = function (cfg) {
    SLOG = []; cv.set('bva_setup_log', '[]');
    B.prepare(cfg);
    cv.set('reset_uid', 'chua-co-lien-ket');   // giá trị tạm để URL luôn hợp lệ nếu bước chuẩn bị lỗi
    var k = cfg.kind;
    if (k === 'reg') {
      B.guest('/accounts/register/', function (r) { var h = r.text(); log('SETUP: đúng form đăng ký (username, password1)', input(h, 'username') !== null && input(h, 'password1') !== null); });
    } else if (k === 'pro') {
      registerNominal(function () {
        B.get('/accounts/profile/edit/', function (r) {
          log('SETUP: tài khoản test đã đăng ký và đăng nhập', shownUser(r.text()) === cv.get('bva_user'));
          B.post('/accounts/profile/edit/', { csrfmiddlewaretoken: B.tokenOf(r.text()), first_name: cv.get('bva_first_name'), last_name: cv.get('bva_last_name'), email: cv.get('bva_email') }, function () {
            B.get('/accounts/profile/edit/', function (r2) {
              var h = r2.text(); cv.set('bva_csrf', B.tokenOf(h));
              log('SETUP: hồ sơ nominal đã được lưu', value(h, 'first_name') === cv.get('bva_first_name') && value(h, 'last_name') === cv.get('bva_last_name') && value(h, 'email') === cv.get('bva_email'));
            });
          });
        });
      });
    } else if (k === 'chg') {
      registerNominal(function () {
        B.get('/accounts/password/change/', function (r) { cv.set('bva_csrf', B.tokenOf(r.text())); log('SETUP: đã đăng nhập, có form đổi mật khẩu', input(r.text(), 'old_password') !== null); });
      });
    } else { // rst: tạo tài khoản, gửi email đặt lại, đọc hộp thư dev bằng superuser, mở form mật khẩu mới
      var a = adminCreds(), email = cv.get('bva_email');
      log('SETUP 08: có tài khoản superuser để đọc hộp thư dev', a.u && a.p, 'thiếu bva_mailbox_admin_user / bva_mailbox_admin_password');
      registerNominal(function () {
        B.guest('/accounts/password/reset/', function () {
          B.post('/accounts/password/reset/', { csrfmiddlewaretoken: cv.get('bva_csrf'), email: email }, function () {
            B.login(a.u, a.p, function () {
              B.get('/dev/mailbox/', function (r) {
                log('SETUP 08: hộp thư dev chỉ đọc được bằng superuser', r.code === 200);
                var hit = null;
                r.text().split('<details').forEach(function (b) {
                  if (!hit && b.indexOf(email) !== -1) { var m = b.match(/\/accounts\/password\/reset\/([^\/\s"<]+)\/([^\/\s"<]+)\//); if (m) { hit = { uid: m[1], token: m[2] }; } }
                });
                log('SETUP 08: reset URL thuộc đúng email của testcase', hit !== null);
                if (!hit) { return; }
                cv.set('reset_uid', hit.uid);
                B.guest(null, function () {
                  B.get('/accounts/password/reset/' + hit.uid + '/' + hit.token + '/', function (r2) {
                    var h = r2.text(); cv.set('bva_csrf', B.tokenOf(h));
                    log('SETUP 08: token reset được chấp nhận, đúng form set-password', r2.code === 200 && input(h, 'new_password1') !== null);
                  });
                });
              });
            });
          });
        });
      });
    }
  };

  // ---------- kiểm chứng (chạy trong script sau request) ----------
  var OK_LOC = { reg: '/', pro: '/accounts/profile/', chg: '/accounts/profile/', rst: '/accounts/password/reset/complete/' };
  function verify(cfg) {
    var k = cfg.kind;
    if (k === 'pro') {
      B.get('/accounts/profile/edit/', function (r) {
        var h = r.text();
        pm.test(cfg.ok ? 'Lưu đúng giá trị mới' : 'Hồ sơ giữ nguyên giá trị cũ', function () {
          pm.expect(value(h, 'first_name')).to.eql(cfg.ok ? cv.get('bva_post_first') : cv.get('bva_first_name'));
          pm.expect(value(h, 'last_name')).to.eql(cfg.ok ? cv.get('bva_post_last') : cv.get('bva_last_name'));
          pm.expect(value(h, 'email')).to.eql(cfg.ok ? cv.get('bva_post_email') : cv.get('bva_email'));
        });
        B.guest(null);
      });
      return;
    }
    var pw = cv.get('bva_login_pw');
    B.guest('/accounts/login/', function () {
      B.post('/accounts/login/', { csrfmiddlewaretoken: cv.get('bva_csrf'), username: cv.get('bva_user'), password: pw }, function (lr) {
        if (k === 'reg' && !cfg.ok) {
          pm.test('Không đăng nhập bằng dữ liệu bị từ chối', function () { pm.expect(lr.code).to.eql(200); pm.expect(lr.text()).to.match(/auth-error(?:-box)?|errorlist/); });
          B.get('/accounts/profile/edit/', function (r) { noSession(r); B.guest(null); });
          return;
        }
        B.get('/accounts/profile/edit/', function (r) {
          var what = k === 'reg' ? 'Đăng nhập được bằng tài khoản vừa đăng ký' : (cfg.ok ? 'Đăng nhập được bằng mật khẩu mới' : 'Mật khẩu cũ vẫn đăng nhập được (đổi mật khẩu bị từ chối)');
          pm.test(what, function () { pm.expect(r.code).to.eql(200); pm.expect(hasSession(r.text(), cv.get('bva_user'))).to.eql(true); });
          if (k === 'reg') { pm.test('Lưu đúng email', function () { pm.expect(value(r.text(), 'email')).to.eql(cv.get('bva_email')); }); }
          if (cfg.ok && (k === 'chg' || k === 'rst')) { rejectedLogin(cv.get('old_password'), 'Mật khẩu cũ không còn đăng nhập được', function () { B.guest(null); }); }
          else { B.guest(null); }
        });
      });
    });
  }

  // ---------- test của request giá trị biên ----------
  B.test = function (cfg) {
    JSON.parse(cv.get('bva_setup_log') || '[]').forEach(function (x) { pm.test(x.n, function () { pm.expect(x.ok, x.d || x.n).to.eql(true); }); });
    if (cfg.ok) { expectOk(OK_LOC[cfg.kind]); } else { expectReject(cfg); }
    verify(cfg);
  };

  return B;
})()
