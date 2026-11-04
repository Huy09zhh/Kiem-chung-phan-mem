import email
import re
from email import policy
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import include, path

from . import dev_mailbox


class MailboxTestURLs:
    # Include both endpoints even when startup settings disable the feature,
    # so tests also exercise the checks inside the views.
    urlpatterns = [
        path('dev/mailbox/', dev_mailbox.mailbox_view, name='dev_mailbox'),
        path('dev/mailbox/clear/', dev_mailbox.mailbox_clear_view, name='dev_mailbox_clear'),
        path('', include('config.urls')),
    ]


@override_settings(ROOT_URLCONF=MailboxTestURLs, DEBUG=True, DEV_MAILBOX_ENABLED=True,
                   EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend',
                   ALLOWED_HOSTS=['testserver'])
class DevMailboxSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('mail_customer', 'customer@example.test', 'Old7!Password#42')
        cls.staff = User.objects.create_user('mail_staff', 'staff@example.test', 'Staff7!Password#42', is_staff=True)
        cls.superuser = User.objects.create_superuser('mail_admin', 'admin@example.test', 'Admin7!Password#42')

    def setUp(self):
        self.folder = TemporaryDirectory(prefix='scrum42-mail-')
        self.addCleanup(self.folder.cleanup)
        override = override_settings(EMAIL_FILE_PATH=self.folder.name)
        override.enable()
        self.addCleanup(override.disable)
        # Generate a real reset email for another user, including a usable token.
        response = self.client.post('/accounts/password/reset/', {'email': self.customer.email})
        self.assertEqual(response.status_code, 302)
        self.logs = list(Path(self.folder.name).glob('*.log'))
        self.assertTrue(self.logs)
        message = email.message_from_bytes(self.logs[0].read_bytes().split(dev_mailbox.SEPARATOR)[0], policy=policy.default)
        body = message.get_body(preferencelist=('plain', 'html')).get_content()
        self.token_url = re.search(r'https?://[^\s<>]+/accounts/password/reset/[^\s<>]+', body).group(0)

    def assert_hidden(self, response):
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, self.token_url, status_code=404)
        self.assertNotContains(response, self.customer.email, status_code=404)
        self.assertNotContains(response, self.folder.name, status_code=404)
        self.assertIn('no-store', response.get('Cache-Control', ''))

    def csrf_client(self, user=None):
        client = Client(enforce_csrf_checks=True)
        if user is not None:
            client.force_login(user)
        client.get('/accounts/password/reset/')
        return client, client.cookies['csrftoken'].value

    def test_anonymous_cannot_read_reset_email(self):
        self.assert_hidden(self.client.get('/dev/mailbox/'))

    def test_customer_cannot_read_reset_email(self):
        self.client.force_login(self.customer)
        self.assert_hidden(self.client.get('/dev/mailbox/'))

    def test_staff_without_superuser_cannot_read_reset_email(self):
        self.client.force_login(self.staff)
        self.assert_hidden(self.client.get('/dev/mailbox/'))

    def test_inactive_superuser_cannot_read_reset_email(self):
        self.superuser.is_active = False
        self.superuser.save(update_fields=['is_active'])
        self.client.force_login(self.superuser)
        self.assert_hidden(self.client.get('/dev/mailbox/'))

    def test_superuser_can_read_dev_email_without_caching(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/dev/mailbox/')
        self.assertContains(response, self.customer.email)
        self.assertContains(response, self.token_url)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('private', response['Cache-Control'])

    def test_anonymous_cannot_clear_mail_even_with_csrf(self):
        client, token = self.csrf_client()
        self.assert_hidden(client.post('/dev/mailbox/clear/', {'csrfmiddlewaretoken': token}))
        self.assertTrue(self.logs[0].exists())

    def test_customer_cannot_clear_mail_even_with_csrf(self):
        client, token = self.csrf_client(self.customer)
        self.assert_hidden(client.post('/dev/mailbox/clear/', {'csrfmiddlewaretoken': token}))
        self.assertTrue(self.logs[0].exists())

    def test_staff_cannot_clear_mail_even_with_csrf(self):
        client, token = self.csrf_client(self.staff)
        self.assert_hidden(client.post('/dev/mailbox/clear/', {'csrfmiddlewaretoken': token}))
        self.assertTrue(self.logs[0].exists())

    def test_superuser_can_clear_only_mail_logs_with_csrf(self):
        other_file = Path(self.folder.name) / 'keep.txt'
        other_file.write_text('keep', encoding='utf-8')
        client, token = self.csrf_client(self.superuser)
        response = client.post('/dev/mailbox/clear/', {'csrfmiddlewaretoken': token})
        self.assertRedirects(response, '/dev/mailbox/')
        self.assertFalse(list(Path(self.folder.name).glob('*.log')))
        self.assertTrue(other_file.exists())
        self.assertIn('no-store', response['Cache-Control'])

    def test_superuser_clear_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.superuser)
        self.assertEqual(client.post('/dev/mailbox/clear/').status_code, 403)
        self.assertTrue(self.logs[0].exists())

    def test_get_cannot_clear_mail(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get('/dev/mailbox/clear/').status_code, 405)
        self.assertTrue(self.logs[0].exists())

    def test_disabled_feature_denies_both_endpoints_to_superuser(self):
        self.client.force_login(self.superuser)
        with override_settings(DEV_MAILBOX_ENABLED=False):
            self.assert_hidden(self.client.get('/dev/mailbox/'))
            self.assert_hidden(self.client.post('/dev/mailbox/clear/'))
        self.assertTrue(self.logs[0].exists())

    def test_debug_false_denies_both_endpoints_even_if_flag_true(self):
        self.client.force_login(self.superuser)
        with override_settings(DEBUG=False):
            self.assert_hidden(self.client.get('/dev/mailbox/'))
            self.assert_hidden(self.client.post('/dev/mailbox/clear/'))
        self.assertTrue(self.logs[0].exists())

    def test_reset_done_hides_mailbox_link_for_anonymous_and_non_superusers(self):
        self.assertNotContains(self.client.get('/accounts/password/reset/done/'), '/dev/mailbox/')
        for user in (self.customer, self.staff):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertNotContains(self.client.get('/accounts/password/reset/done/'), '/dev/mailbox/')

    def test_reset_done_shows_mailbox_link_for_superuser_in_dev(self):
        self.client.force_login(self.superuser)
        self.assertContains(self.client.get('/accounts/password/reset/done/'), '/dev/mailbox/')

    def test_reset_token_still_works_for_email_recipient(self):
        # The token is obtained from the private test email file, not from a
        # publicly accessible mailbox; legitimate password reset must still work.
        response = self.client.get(urlsplit(self.token_url).path)
        self.assertEqual(response.status_code, 302)
        reset_path = response['Location']
        new_password = 'New8!Password#42'
        response = self.client.post(reset_path, {'new_password1': new_password, 'new_password2': new_password})
        self.assertRedirects(response, '/accounts/password/reset/complete/')
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(new_password))
