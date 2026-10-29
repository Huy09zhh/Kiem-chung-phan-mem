from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import NewsletterSubscriber
from .views import NEWSLETTER_SALT


class NewsletterSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('newsletter_subscribe')

    def _post(self, email):
        return self.client.post(self.url, {'email': email, 'next': '/'})

    def test_email_moi_va_email_da_dang_ky_cung_mot_thong_bao(self):
        NewsletterSubscriber.objects.create(email='old@example.com', is_confirmed=True)
        r1 = self._post('new@example.com')
        r2 = self._post('old@example.com')
        self.assertEqual(r1['Location'], r2['Location'])
        self.assertIn('newsletter=pending', r1['Location'])

    def test_chua_xac_nhan_thi_chua_vao_danh_sach(self):
        self._post('new@example.com')
        self.assertFalse(NewsletterSubscriber.objects.filter(email='new@example.com').exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_bam_link_xac_nhan_moi_duoc_dang_ky(self):
        token = signing.dumps('new@example.com', salt=NEWSLETTER_SALT)
        r = self.client.get(reverse('newsletter_confirm', args=[token]))
        self.assertIn('newsletter=confirmed', r['Location'])
        self.assertTrue(NewsletterSubscriber.objects.get(email='new@example.com').is_confirmed)

    def test_token_gia_bi_tu_choi(self):
        r = self.client.get(reverse('newsletter_confirm', args=['token-gia']))
        self.assertIn('newsletter=confirm_invalid', r['Location'])
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    def test_gioi_han_so_lan_gui(self):
        for i in range(5):
            self.assertIn('pending', self._post(f'u{i}@example.com')['Location'])
        self.assertIn('newsletter=limited', self._post('u6@example.com')['Location'])