"""Kiểm thử chuyển trạng thái phiên đăng nhập (Account & Auth) – sheet PH1_Tiên_ChuyenTT.

Mỗi test ứng với một dòng (20–45) của bảng "III. TEST CASE", theo đúng thứ tự:
S0 = Guest, S1 = Customer (is_staff=False), S2 = Admin (is_staff=True).
"""
from datetime import timedelta

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

CUSTOMER_PW = 'CustomerPass#2026'
ADMIN_PW = 'AdminPass#2026'
NEW_PW = 'NewCustomerPass#2026'
ADMIN_DASHBOARD = '/admin-panel/dashboard/'
ACCOUNTS_ADMIN_DASHBOARD = '/accounts/admin-dashboard/'


class StateTransitionTests(TestCase):

    def setUp(self):
        cache.clear()  # bộ đếm khóa đăng nhập (login_throttle) nằm trong cache
        self.client = Client()
        self.customer = User.objects.create_user(
            username='customer_st', password=CUSTOMER_PW, email='customer_st@example.com')
        self.admin = User.objects.create_user(
            username='admin_st', password=ADMIN_PW, email='admin_st@example.com', is_staff=True)
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        self.logout_url = reverse('logout')
        self.profile_url = reverse('profile')
        # trang login/register có nút Google (allauth) nên cần SocialApp như accounts/tests.py
        app = SocialApp.objects.create(provider='google', name='Google', client_id='test', secret='test')
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            from django.contrib.sites.models import Site
            app.sites.add(Site.objects.get_current())

    # ---------- tiện ích kiểm tra trạng thái ----------

    def assertGuest(self, client=None):
        """S0: profile chuyển sang trang đăng nhập."""
        r = (client or self.client).get(self.profile_url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r['Location'].startswith(self.login_url))

    def assertLoggedIn(self, client=None):
        """S1/S2: profile trả 200."""
        self.assertEqual((client or self.client).get(self.profile_url).status_code, 200)

    def assertRedirectsToLogin(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(self.login_url))

    # ---------- Trạng thái trước: S0 (Guest) ----------

    def test_tc_aa_003_004_dang_ky_hop_le(self):
        """S0 → Đăng ký hợp lệ → S1: 302 về /; profile 200 đúng username."""
        r = self.client.post(self.register_url, {
            'username': 'newuser_st', 'email': 'newuser_st@example.com',
            'password1': 'NewUserPass#2026', 'password2': 'NewUserPass#2026'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)
        p = self.client.get(self.profile_url)
        self.assertEqual(p.status_code, 200)
        self.assertContains(p, 'newuser_st')

    def test_tc_aa_008_dang_ky_mat_khau_khong_khop(self):
        """S0 → Đăng ký, hai ô mật khẩu không khớp → S0: 200 ở form; profile 302 về login."""
        r = self.client.post(self.register_url, {
            'username': 'mismatch_st', 'email': 'mismatch_st@example.com',
            'password1': 'NewUserPass#2026', 'password2': 'OtherPass#2026'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertFalse(User.objects.filter(username='mismatch_st').exists())
        self.assertGuest()

    def test_tc_aa_021_022_dang_nhap_dung_customer(self):
        """S0 → Đăng nhập đúng Customer → S1: 302 về /; profile 200."""
        r = self.client.post(self.login_url, {'username': 'customer_st', 'password': CUSTOMER_PW})
        self.assertRedirects(r, '/', fetch_redirect_response=False)
        self.assertLoggedIn()

    def test_tc_aa_025_dang_nhap_customer_next_cart(self):
        """S0 → Đăng nhập đúng Customer kèm next=/cart/ → S1: 302 về /cart/."""
        r = self.client.post(self.login_url, {
            'username': 'customer_st', 'password': CUSTOMER_PW, 'next': '/cart/'})
        self.assertRedirects(r, '/cart/', fetch_redirect_response=False)
        self.assertLoggedIn()

    def test_tc_aa_046_047_dang_nhap_dung_admin(self):
        """S0 → Đăng nhập đúng Admin → S2: 302 về dashboard; 2 trang quản trị 200."""
        r = self.client.post(self.login_url, {'username': 'admin_st', 'password': ADMIN_PW})
        self.assertRedirects(r, reverse('admin_dashboard'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(ADMIN_DASHBOARD).status_code, 200)
        self.assertEqual(self.client.get(ACCOUNTS_ADMIN_DASHBOARD).status_code, 200)

    def test_tc_aa_014_019_dang_nhap_sai_mat_khau(self):
        """S0 → Đăng nhập sai mật khẩu → S0: 200 có khối lỗi; profile 302 về login."""
        r = self.client.post(self.login_url, {'username': 'customer_st', 'password': 'WrongPass#2026'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].non_field_errors())
        self.assertGuest()

    def test_tc_aa_043_dang_nhap_mat_khau_cu_sau_khi_doi(self):
        """S0 → Đăng nhập bằng mật khẩu cũ sau khi đã đổi → S0: 200 có khối lỗi."""
        self.customer.set_password(NEW_PW)
        self.customer.save()
        r = self.client.post(self.login_url, {'username': 'customer_st', 'password': CUSTOMER_PW})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].non_field_errors())
        self.assertGuest()

    def test_tc_aa_016_dang_nhap_de_trong(self):
        """S0 → Đăng nhập để trống → S0: 200 có thông báo lỗi bắt buộc nhập."""
        r = self.client.post(self.login_url, {'username': '', 'password': ''})
        self.assertEqual(r.status_code, 200)
        self.assertIn('username', r.context['form'].errors)
        self.assertIn('password', r.context['form'].errors)
        self.assertGuest()

    def test_tc_aa_024_dang_nhap_next_mien_ngoai(self):
        """S0 → Đăng nhập kèm next=https://evil.example/ → S1: 302, không ra miền ngoài."""
        r = self.client.post(self.login_url, {
            'username': 'customer_st', 'password': CUSTOMER_PW, 'next': 'https://evil.example/'})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('evil.example', r['Location'])
        self.assertEqual(r['Location'], '/')
        self.assertLoggedIn()

    def test_tc_aa_044_guest_vao_trang_quan_tri(self):
        """S0 → GET /admin-panel/dashboard/ → S0: 302 về login."""
        self.assertRedirectsToLogin(self.client.get(ADMIN_DASHBOARD))

    def test_tc_aa_019_031_033_guest_sua_ho_so_doi_mat_khau(self):
        """S0 → GET profile, profile/edit, password/change → S0: cả 3 đều 302 về login."""
        for url in (self.profile_url, reverse('profile_edit'), reverse('change_password')):
            with self.subTest(url=url):
                self.assertRedirectsToLogin(self.client.get(url))

    def test_tc_aa_020_guest_post_dang_xuat(self):
        """S0 → POST /accounts/logout/ khi chưa có phiên → S0: 302 về login."""
        self.assertRedirectsToLogin(self.client.post(self.logout_url))

    def test_tc_aa_012_013_dang_ky_kem_is_staff_is_superuser(self):
        """S0 → Đăng ký kèm is_staff/is_superuser=on → S1 (không S2): 302 về /; dashboard 302 về /."""
        r = self.client.post(self.register_url, {
            'username': 'mass_st', 'email': 'mass_st@example.com',
            'password1': 'NewUserPass#2026', 'password2': 'NewUserPass#2026',
            'is_staff': 'on', 'is_superuser': 'on'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)
        user = User.objects.get(username='mass_st')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertRedirects(self.client.get(ADMIN_DASHBOARD), '/', fetch_redirect_response=False)

    # ---------- Trạng thái trước: S1 (Customer) ----------

    def test_tc_aa_040_041_customer_dang_xuat_hop_le(self):
        """S1 → POST đăng xuất kèm CSRF → S0: 302 về /; profile 302 về login."""
        self.client.force_login(self.customer)
        r = self.client.post(self.logout_url)
        self.assertRedirects(r, '/', fetch_redirect_response=False)
        self.assertGuest()

    def test_tc_aa_042_customer_dang_xuat_bang_get(self):
        """S1 → GET /accounts/logout/ → S1: 405; profile vẫn 200."""
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(self.logout_url).status_code, 405)
        self.assertLoggedIn()

    def test_tc_aa_039_customer_dang_xuat_thieu_csrf(self):
        """S1 → POST đăng xuất thiếu CSRF token → S1: 403; phiên giữ nguyên."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.customer)
        self.assertEqual(client.post(self.logout_url).status_code, 403)
        self.assertLoggedIn(client)

    def test_tc_aa_027_028_customer_cap_nhat_ho_so_hop_le(self):
        """S1 → Sửa họ, tên, email hợp lệ → S1: 302 về profile; profile hiện họ tên mới."""
        self.client.force_login(self.customer)
        r = self.client.post(reverse('profile_edit'), {
            'first_name': 'Tran', 'last_name': 'Thi Moi', 'email': 'customer_new@example.com'})
        self.assertRedirects(r, self.profile_url, fetch_redirect_response=False)
        p = self.client.get(self.profile_url)
        self.assertEqual(p.status_code, 200)
        self.assertContains(p, 'Tran')
        self.assertContains(p, 'Thi Moi')

    def test_tc_aa_029_customer_cap_nhat_ho_so_email_sai(self):
        """S1 → Sửa hồ sơ với email sai định dạng → S1: 200 có thông báo lỗi, không lưu."""
        self.client.force_login(self.customer)
        r = self.client.post(reverse('profile_edit'), {
            'first_name': 'Tran', 'last_name': 'Thi Moi', 'email': 'email-sai-dinh-dang'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('email', r.context['form'].errors)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, 'customer_st@example.com')
        self.assertLoggedIn()

    def test_tc_aa_038_customer_doi_mat_khau_dung(self):
        """S1 → Đổi mật khẩu đúng → S1: 302 về profile; profile vẫn 200 (giữ phiên)."""
        self.client.force_login(self.customer)
        r = self.client.post(reverse('change_password'), {
            'old_password': CUSTOMER_PW, 'new_password1': NEW_PW, 'new_password2': NEW_PW})
        self.assertRedirects(r, self.profile_url, fetch_redirect_response=False)
        self.assertLoggedIn()
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(NEW_PW))

    def test_tc_aa_034_customer_doi_mat_khau_sai_mat_khau_cu(self):
        """S1 → Đổi mật khẩu với old_password sai → S1: 200 có lỗi."""
        self.client.force_login(self.customer)
        r = self.client.post(reverse('change_password'), {
            'old_password': 'WrongOld#2026', 'new_password1': NEW_PW, 'new_password2': NEW_PW})
        self.assertEqual(r.status_code, 200)
        self.assertIn('old_password', r.context['form'].errors)
        self.assertLoggedIn()

    def test_tc_aa_005_customer_mo_trang_dang_ky(self):
        """S1 → GET /accounts/register/ → S1: 302 về /, không tạo tài khoản."""
        self.client.force_login(self.customer)
        count = User.objects.count()
        self.assertRedirects(self.client.get(self.register_url), '/', fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), count)
        self.assertLoggedIn()

    def test_tc_aa_023_customer_mo_trang_dang_nhap(self):
        """S1 → GET /accounts/login/ → S1: 302 về /, phiên giữ nguyên."""
        self.client.force_login(self.customer)
        self.assertRedirects(self.client.get(self.login_url), '/', fetch_redirect_response=False)
        self.assertLoggedIn()

    def test_tc_aa_045_customer_vao_trang_quan_tri(self):
        """S1 → GET 2 trang quản trị → S1: cả 2 đều 302 về /, không lên S2."""
        self.client.force_login(self.customer)
        for url in (ADMIN_DASHBOARD, ACCOUNTS_ADMIN_DASHBOARD):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), '/', fetch_redirect_response=False)
        self.assertLoggedIn()

    # ---------- Trạng thái trước: S2 (Admin) ----------

    def test_tc_aa_049_050_admin_dang_xuat_hop_le(self):
        """S2 → POST đăng xuất kèm CSRF → S0: 302 về /; dashboard 302 về login."""
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(self.logout_url), '/', fetch_redirect_response=False)
        self.assertRedirectsToLogin(self.client.get(ADMIN_DASHBOARD))

    def test_tc_aa_048_admin_mo_trang_dang_nhap(self):
        """S2 → GET /accounts/login/ → S2: 302 về dashboard, phiên giữ nguyên."""
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(self.login_url), reverse('admin_dashboard'),
                             fetch_redirect_response=False)
        self.assertEqual(self.client.get(ADMIN_DASHBOARD).status_code, 200)

    # ---------- Phiên hết hạn: S1 → S0 ----------

    def test_tc_aa_059_phien_het_han(self):
        """S1 → Phiên hết hạn → S0: profile 302 về login?next=/accounts/profile/; dashboard 302 về login."""
        self.client.force_login(self.customer)
        self.assertLoggedIn()
        Session.objects.update(expire_date=timezone.now() - timedelta(days=1))
        r = self.client.get(self.profile_url)
        self.assertRedirects(r, f'{self.login_url}?next={self.profile_url}',
                             fetch_redirect_response=False)
        self.assertRedirectsToLogin(self.client.get(ADMIN_DASHBOARD))


def load_tests(loader, tests, pattern):
    """Chạy theo thứ tự dòng của sheet (unittest mặc định sắp xếp theo tên)."""
    names = [n for n in vars(StateTransitionTests) if n.startswith('test_')]
    return loader.suiteClass(StateTransitionTests(n) for n in names)
