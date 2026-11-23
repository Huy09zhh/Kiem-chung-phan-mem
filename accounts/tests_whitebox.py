"""Kiểm thử hộp trắng (Control Flow Testing) cho phân hệ Account & Auth.

Mỗi test ứng với một mã WB-xx trong sheet "Whitebox_Tiên" (Report KCPM.xlsx):
    Phần 1  login_view                      WB-L1 .. WB-L6
    Phần 2  get_safe_next_url               WB-N1 .. WB-N3
    Phần 3  register_view                   WB-R1 .. WB-R4
    Phần 4  admin_required                  WB-A1 .. WB-A3
    Phần 5  CustomPasswordResetForm.save    WB-F1 .. WB-F3
    Phần 6  logout / profile / đổi mật khẩu WB-O1, WB-P1, WB-P2, WB-H1, WB-H2

Chạy:  python manage.py test accounts.tests_whitebox -v 2
Đo độ phủ: coverage run --branch --source=accounts manage.py test accounts.tests_whitebox
"""
from allauth.socialaccount.models import SocialApp
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .forms import CustomPasswordResetForm
from .views import get_safe_next_url

PW = 'WbTest#2026Aa'


def make_user(username, is_staff=False, **extra):
    return User.objects.create_user(username=username, password=PW, email=f'{username}@example.test', is_staff=is_staff, **extra)


class GoogleAppMixin:
    """Database test trống nên cần cấu hình Google OAuth giả để trang đăng nhập/đăng ký render được."""

    def setUp(self):
        super().setUp()
        app = SocialApp.objects.create(provider='google', name='Google', client_id='test', secret='test')
        app.sites.add(Site.objects.get_current())


class WhiteBoxLoginViewTests(GoogleAppMixin, TestCase):
    """Phần 1 – login_view (views.py:41). D1 đã đăng nhập, D2 is_staff, D3 POST và hợp lệ, D4 is_staff."""

    def setUp(self):
        super().setUp()
        self.customer = make_user('wb_customer')
        self.admin = make_user('wb_admin', is_staff=True)
        self.url = reverse('login')

    def test_wb_l1_logged_in_admin_redirects_to_dashboard(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse('admin_dashboard'), fetch_redirect_response=False)

    def test_wb_l2_logged_in_customer_redirects_home(self):
        self.client.force_login(self.customer)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)

    def test_wb_l3_guest_post_admin_credentials(self):
        r = self.client.post(self.url, {'username': 'wb_admin', 'password': PW})
        self.assertRedirects(r, reverse('admin_dashboard'), fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

    def test_wb_l4_guest_post_customer_credentials(self):
        r = self.client.post(self.url, {'username': 'wb_customer', 'password': PW})
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

    def test_wb_l5_guest_get_shows_form(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context['form'].is_bound)

    def test_wb_l6_guest_post_wrong_password_shows_error(self):
        r = self.client.post(self.url, {'username': 'wb_customer', 'password': 'Sai#Mat#Khau1'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)


class WhiteBoxSafeNextUrlTests(TestCase):
    """Phần 2 – get_safe_next_url (views.py:11). D1: next_url (A) và url_has_allowed_host_and_scheme (B)."""

    def setUp(self):
        self.rf = RequestFactory()

    def test_wb_n1_no_next_returns_default(self):
        request = self.rf.get('/accounts/login/')
        self.assertEqual(get_safe_next_url(request), 'home')

    def test_wb_n2_external_next_in_get_is_rejected(self):
        request = self.rf.get('/accounts/login/', {'next': 'https://evil.example/'})
        self.assertEqual(get_safe_next_url(request), 'home')

    def test_wb_n3_internal_next_in_post_is_accepted(self):
        request = self.rf.post('/accounts/login/', {'next': '/cart/'})
        self.assertEqual(get_safe_next_url(request), '/cart/')


class WhiteBoxRegisterViewTests(GoogleAppMixin, TestCase):
    """Phần 3 – register_view (views.py:23). D1 đã đăng nhập, D2 POST và hợp lệ."""

    def setUp(self):
        super().setUp()
        self.url = reverse('register')

    def test_wb_r1_logged_in_user_redirected_home(self):
        self.client.force_login(make_user('wb_logged'))
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)

    def test_wb_r2_valid_post_creates_user_and_logs_in(self):
        r = self.client.post(self.url, {'username': 'wb_new', 'email': 'wb_new@example.test', 'password1': PW, 'password2': PW})
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username='wb_new').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_wb_r3_guest_get_shows_form(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context['form'].is_bound)

    def test_wb_r4_invalid_post_shows_error_and_creates_nothing(self):
        r = self.client.post(self.url, {'username': 'wb_bad', 'email': 'wb_bad@example.test', 'password1': PW, 'password2': PW + 'X'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertFalse(User.objects.filter(username='wb_bad').exists())


class WhiteBoxAdminRequiredTests(TestCase):
    """Phần 4 – admin_required (decorators.py:3), kiểm tra qua /accounts/admin-dashboard/."""

    def setUp(self):
        self.url = '/accounts/admin-dashboard/'

    def test_wb_a1_guest_redirected_to_login(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse('login'), fetch_redirect_response=False)

    def test_wb_a2_customer_redirected_home(self):
        self.client.force_login(make_user('wb_customer'))
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)

    def test_wb_a3_admin_gets_dashboard(self):
        self.client.force_login(make_user('wb_admin', is_staff=True))
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)


class WhiteBoxPasswordResetFormTests(TestCase):
    """Phần 5 – CustomPasswordResetForm.save (forms.py:116). D: request is not None (A) và not domain_override (B)."""

    SAVE_KWARGS = dict(subject_template_name='accounts/password_reset_subject.txt',
                       email_template_name='accounts/password_reset_email.html')

    def setUp(self):
        self.user = make_user('wb_reset')
        self.rf = RequestFactory()

    def _form(self):
        form = CustomPasswordResetForm({'email': self.user.email})
        self.assertTrue(form.is_valid())
        return form

    def test_wb_f1_without_request_uses_site_domain(self):
        self._form().save(request=None, **self.SAVE_KWARGS)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('example.com', mail.outbox[0].body)
        self.assertNotIn('testserver', mail.outbox[0].body)

    def test_wb_f2_explicit_domain_override_is_kept(self):
        request = self.rf.get('/accounts/password/reset/')
        self._form().save(request=request, domain_override='custom.test', **self.SAVE_KWARGS)
        self.assertIn('custom.test', mail.outbox[0].body)
        self.assertNotIn('testserver', mail.outbox[0].body)

    def test_wb_f3_request_host_becomes_domain(self):
        r = self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertEqual(r.status_code, 302)
        self.assertIn('testserver', mail.outbox[0].body)


class WhiteBoxSimpleViewsTests(TestCase):
    """Phần 6 – logout_view, profile_update_view, change_password_view."""

    def setUp(self):
        self.user = make_user('wb_simple', first_name='An', last_name='Nguyen')
        self.client.force_login(self.user)

    def test_wb_o1_logout_post_clears_session(self):
        r = self.client.post(reverse('logout'))
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wb_p1_profile_valid_post_saves(self):
        r = self.client.post(reverse('profile_edit'), {'first_name': 'Binh', 'last_name': 'Tran', 'email': 'wb_new_mail@example.test'})
        self.assertRedirects(r, reverse('profile'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email), ('Binh', 'wb_new_mail@example.test'))

    def test_wb_p2_profile_invalid_email_shows_error(self):
        r = self.client.post(reverse('profile_edit'), {'first_name': 'Binh', 'last_name': 'Tran', 'email': 'email-sai-dinh-dang'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)

    def test_wb_h1_change_password_valid_keeps_session(self):
        new_pw = 'WbNew#2026Bb'
        r = self.client.post(reverse('change_password'), {'old_password': PW, 'new_password1': new_pw, 'new_password2': new_pw})
        self.assertRedirects(r, reverse('profile'), fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_pw))

    def test_wb_h2_change_password_wrong_old_shows_error(self):
        r = self.client.post(reverse('change_password'), {'old_password': 'Sai#Mat#Khau1', 'new_password1': 'WbNew#2026Bb', 'new_password2': 'WbNew#2026Bb'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
