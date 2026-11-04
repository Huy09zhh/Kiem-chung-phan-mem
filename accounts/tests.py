from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from allauth.socialaccount.models import SocialApp


class SCRUM30UsernameProtectionTests(TestCase):
    """Kiểm thử SCRUM-30: Người dùng thường không thể thay đổi Username.

    TC01 – Username hiển thị trên trang chỉnh sửa hồ sơ.
    TC02 – Cập nhật trường hợp lệ (first_name) không làm thay đổi username.
    TC03 – Gửi username giả mạo qua POST body không làm thay đổi username trong DB.
    TC04 – Sau khi cập nhật, vẫn đăng nhập được bằng username + mật khẩu cũ.
    TC05 – Admin có thể thay đổi username người dùng qua admin panel.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='testuser@example.com',
            first_name='Nguyen',
            last_name='Van A',
        )
        self.admin = User.objects.create_user(
            username='adminuser',
            password='adminpassword123',
            email='admin@example.com',
            is_staff=True,
        )
        self.profile_edit_url = reverse('profile_edit')

    # ---------- TC01: Hiển thị username trên trang chỉnh sửa ----------

    def test_tc01_profile_edit_page_accessible(self):
        """TC01: Trang chỉnh sửa hồ sơ trả về 200 và hiển thị username."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(self.profile_edit_url)
        self.assertEqual(response.status_code, 200)
        # Username của người dùng phải xuất hiện trong nội dung trang
        self.assertContains(response, 'testuser')

    def test_tc01_username_field_not_in_form(self):
        """TC01: Form UserProfileUpdateForm không có trường username."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(self.profile_edit_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        # username không được có trong form fields
        self.assertNotIn('username', form.fields)

    # ---------- TC02: Cập nhật trường hợp lệ không đổi username ----------

    def test_tc02_update_first_name_keeps_username(self):
        """TC02: Cập nhật first_name hợp lệ, username phải giữ nguyên."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.profile_edit_url, {
            'first_name': 'Le',
            'last_name': 'Van B',
            'email': 'testuser@example.com',
        })
        # Redirect về trang profile sau khi lưu thành công
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        # first_name được cập nhật
        self.assertEqual(self.user.first_name, 'Le')
        # Username giữ nguyên
        self.assertEqual(self.user.username, 'testuser')

    def test_tc02_update_email_keeps_username(self):
        """TC02: Cập nhật email hợp lệ, username phải giữ nguyên."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.profile_edit_url, {
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'email': 'newemail@example.com',
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
        self.assertEqual(self.user.username, 'testuser')

    # ---------- TC03: Gửi username giả mạo qua POST body ----------

    def test_tc03_spoofed_username_not_saved(self):
        """TC03: Gửi username khác trong POST body — username trong DB không đổi."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.profile_edit_url, {
            'username': 'hacker_username',   # giả mạo username trong POST body
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'email': 'testuser@example.com',
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        # username KHÔNG được thay đổi
        self.assertNotEqual(self.user.username, 'hacker_username')
        self.assertEqual(self.user.username, 'testuser')

    def test_tc03_spoofed_username_other_fields_still_updated(self):
        """TC03: Khi gửi username giả mạo, các trường hợp lệ khác vẫn được lưu."""
        self.client.login(username='testuser', password='testpassword123')
        self.client.post(self.profile_edit_url, {
            'username': 'hacker_username',
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
        })
        self.user.refresh_from_db()
        # Các trường hợp lệ được cập nhật
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'updated@example.com')
        # Username vẫn không đổi
        self.assertEqual(self.user.username, 'testuser')

    # ---------- TC04: Vẫn đăng nhập được sau khi cập nhật ----------

    def test_tc04_login_with_original_username_after_update(self):
        """TC04: Sau khi cập nhật hồ sơ, đăng nhập bằng username cũ vẫn hoạt động."""
        self.client.login(username='testuser', password='testpassword123')
        # Cập nhật first_name
        self.client.post(self.profile_edit_url, {
            'first_name': 'Updated',
            'last_name': 'Van A',
            'email': 'testuser@example.com',
        })
        # Đăng xuất
        self.client.logout()
        # Đăng nhập lại bằng username và mật khẩu cũ
        logged_in = self.client.login(username='testuser', password='testpassword123')
        self.assertTrue(logged_in, 'Đăng nhập bằng username cũ sau update phải thành công.')

    def test_tc04_spoofed_username_cannot_login_after_update(self):
        """TC04: Username giả mạo do người dùng gửi không thể dùng để đăng nhập."""
        self.client.login(username='testuser', password='testpassword123')
        self.client.post(self.profile_edit_url, {
            'username': 'hacker_username',
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'email': 'testuser@example.com',
        })
        self.client.logout()
        # Thử đăng nhập bằng username giả mạo — phải thất bại
        logged_in = self.client.login(username='hacker_username', password='testpassword123')
        self.assertFalse(logged_in, 'Không được phép đăng nhập bằng username giả mạo.')

    # ---------- TC05: Admin có thể thay đổi username ----------

    def test_tc05_admin_can_change_username(self):
        """TC05: Admin dùng admin_user_update view có thể thay đổi username người dùng."""
        self.client.login(username='adminuser', password='adminpassword123')
        admin_edit_url = reverse('admin_user_update', kwargs={'pk': self.user.pk})
        response = self.client.post(admin_edit_url, {
            'username': 'changed_by_admin',
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'email': 'testuser@example.com',
            'is_active': True,
        })
        # Redirect (302) sau khi admin lưu thành công
        self.assertIn(response.status_code, [200, 302])
        self.user.refresh_from_db()
        # Username được thay đổi bởi admin
        self.assertEqual(self.user.username, 'changed_by_admin')

    # ---------- TC06: Regression — không ảnh hưởng đến form submit đúng ----------

    def test_tc06_profile_update_with_empty_optional_fields(self):
        """TC06: Gửi first_name và last_name rỗng vẫn hoạt động (optional fields)."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.profile_edit_url, {
            'first_name': '',
            'last_name': '',
            'email': 'testuser@example.com',
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')

    def test_tc06_duplicate_email_rejected(self):
        """TC06: Email trùng với người dùng khác bị từ chối."""
        other = User.objects.create_user(
            username='otheruser',
            password='pass123',
            email='other@example.com',
        )
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.profile_edit_url, {
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'email': 'other@example.com',  # email đã tồn tại
        })
        # Form không hợp lệ — không redirect, trả lại trang với lỗi
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())
        # Username vẫn không đổi
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')

    def test_tc06_unauthenticated_user_redirected(self):
        """TC06: Người dùng chưa đăng nhập bị redirect về trang login."""
        response = self.client.get(self.profile_edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])


class PasswordLengthBoundaryTests(TestCase):
    """Kiểm thử SCRUM-33: giới hạn độ dài mật khẩu tối đa 128 ký tự khi đăng ký."""

    def setUp(self):
        # Database test trống nên cần cấu hình Google OAuth giả để trang đăng ký render được
        app = SocialApp.objects.create(
            provider='google', name='Google', client_id='test', secret='test'
        )
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            from django.contrib.sites.models import Site
            app.sites.add(Site.objects.get_current())

    def _register(self, username, pw):
        return self.client.post(reverse('register'), {
            'username': username,
            'email': f'{username}@example.com',
            'password1': pw,
            'password2': pw,
        })

    def test_mat_khau_128_ky_tu_duoc_chap_nhan(self):
        pw = ('Ab1x' * 32)[:128]
        resp = self._register('pw128', pw)
        self.assertEqual(resp.status_code, 302)

    def test_mat_khau_129_ky_tu_bi_tu_choi(self):
        pw = ('Ab1x' * 33)[:129]
        resp = self._register('pw129', pw)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'không được dài quá 128')
        self.assertFalse(User.objects.filter(username='pw129').exists())

    def test_mat_khau_1_trieu_ky_tu_bi_tu_choi(self):
        resp = self._register('pwlong', 'Ab1x' * 250000)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='pwlong').exists())