import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core import mail, signing
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
 
from .models import ContactMessage, Feedback, NewsletterSubscriber
from .views import NEWSLETTER_SALT


class ContactPhoneValidationTests(TestCase):
    def setUp(self):
        cache.clear()

    def post_contact(self, phone):
        return self.client.post(reverse('contact_page'), {
            'form_type': 'contact',
            'name': 'SCRUM-39 Test',
            'email': 'scrum39@example.test',
            'phone': phone,
            'subject': 'tu_van',
            'message': 'Kiem thu so dien thoai SCRUM-39',
        })

    def assert_phone_rejected(self, phone):
        response = self.post_contact(phone)
        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.context['contact_form'].errors)
        self.assertContains(response, 'Số điện thoại không hợp lệ.')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_rejects_letters_and_special_characters_without_saving(self):
        for phone in ('abc!!!@@@', '09123abc78', '091234567!', '+84-912345678'):
            with self.subTest(phone=phone):
                self.assert_phone_rejected(phone)

    def test_rejects_invalid_lengths_and_prefixes(self):
        for phone in (
            '091234567', '09123456789', '+8491234567', '+849123456789',
            '84912345678', '+840912345678', '0012345678',
        ):
            with self.subTest(phone=phone):
                self.assert_phone_rejected(phone)

    def test_rejects_non_ascii_digits_and_internal_whitespace(self):
        for phone in (
            '\uff10\uff19\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18',
            '0912 345678', '0912\t345678', '0912\n345678',
        ):
            with self.subTest(phone=phone):
                self.assert_phone_rejected(phone)

    def test_accepts_domestic_and_international_numbers(self):
        for phone in ('0912345678', '+84912345678', ' 0912345678 ', ' +84912345678 '):
            with self.subTest(phone=phone):
                response = self.post_contact(phone)
                self.assertRedirects(response, reverse('contact_page') + '?contact_success=1')
                self.assertEqual(ContactMessage.objects.first().phone, phone.strip())
        self.assertEqual(ContactMessage.objects.count(), 4)

    def test_phone_is_optional(self):
        for phone in ('', '   '):
            with self.subTest(phone=phone):
                response = self.post_contact(phone)
                self.assertRedirects(response, reverse('contact_page') + '?contact_success=1')
                self.assertEqual(ContactMessage.objects.first().phone, '')
        self.assertEqual(ContactMessage.objects.count(), 2)


class ContactSuccessMessageTests(TestCase):
    contact_success = 'Gửi liên hệ thành công. Green Shop sẽ phản hồi bạn sớm nhất.'
    feedback_success = 'Cảm ơn bạn đã gửi góp ý. Phản hồi của bạn rất quan trọng với Green Shop.'

    def setUp(self):
        cache.clear()
        self.url = reverse('contact_page')
        self.contact_data = {
            'form_type': 'contact', 'name': 'Contact test',
            'email': 'contact@example.test', 'phone': '0912345678',
            'subject': 'tu_van', 'message': 'Valid contact',
        }
        self.feedback_data = {
            'form_type': 'feedback', 'name': 'Feedback test', 'email': '',
            'category': 'website', 'satisfaction': '5', 'message': 'Valid feedback',
        }

    def assert_no_success_message(self, response):
        self.assertNotContains(response, self.contact_success)
        self.assertNotContains(response, self.feedback_success)

    def test_invalid_contact_after_success_only_shows_phone_error(self):
        success = self.client.post(self.url, self.contact_data)
        self.assertRedirects(success, self.url + '?contact_success=1')
        self.assertContains(self.client.get(success.url), self.contact_success)

        response = self.client.post(success.url, {
            **self.contact_data, 'phone': 'abc!!!@@@',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.context['contact_form'].errors)
        self.assertContains(response, 'Số điện thoại không hợp lệ.')
        self.assert_no_success_message(response)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(ContactMessage.objects.get().phone, '0912345678')

    def test_invalid_feedback_after_success_only_shows_form_error(self):
        success = self.client.post(self.url, self.feedback_data)
        self.assertRedirects(success, self.url + '?feedback_success=1')
        self.assertContains(self.client.get(success.url), self.feedback_success)

        response = self.client.post(success.url, {
            **self.feedback_data, 'message': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.context['feedback_form'].errors)
        self.assert_no_success_message(response)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_invalid_post_hides_both_stale_success_flags(self):
        response = self.client.post(
            self.url + '?contact_success=1&feedback_success=1',
            {**self.contact_data, 'phone': 'abc!!!@@@'},
        )
        self.assertIn('phone', response.context['contact_form'].errors)
        self.assert_no_success_message(response)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_valid_posts_with_stale_flags_show_only_current_success(self):
        for data, flag, message, other_message in (
            (self.contact_data, 'contact_success', self.contact_success, self.feedback_success),
            (self.feedback_data, 'feedback_success', self.feedback_success, self.contact_success),
        ):
            with self.subTest(form_type=data['form_type']):
                response = self.client.post(
                    self.url + '?contact_success=1&feedback_success=1', data,
                )
                self.assertRedirects(response, self.url + '?' + flag + '=1')
                page = self.client.get(response.url)
                self.assertContains(page, message)
                self.assertNotContains(page, other_message)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(Feedback.objects.count(), 1)


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


# ---------------------------------------------------------------------------
# SCRUM-36 - Độ dài email đăng ký nhận tin: Phân hoạch tương đương (EP) & Giá trị biên (BVA).
# Input : docs/email_dangky_testcase.xlsx (sheet "Test case")
# Output: docs/email_dangky_report.xlsx
# Chạy: python manage.py test contact -v 2

DOCS_DIR = Path(settings.BASE_DIR) / 'docs'
TESTCASE_FILE = DOCS_DIR / 'email_dangky_testcase.xlsx'
REPORT_FILE = DOCS_DIR / 'email_dangky_report.xlsx'

PENDING_MESSAGE = 'Nếu email hợp lệ, chúng tôi đã gửi thư xác nhận. Vui lòng kiểm tra hộp thư để hoàn tất đăng ký.'
INVALID_MESSAGE = 'Email không hợp lệ, vui lòng kiểm tra lại.'
CONFIRM_LINK = re.compile(r'https?://\S+/newsletter/confirm/\S+/')


def load_test_cases(path=TESTCASE_FILE):
    """Đọc sheet "Test case": dòng có ô đầu là "STT" là tiêu đề, các dòng sau là dữ liệu."""
    ws = load_workbook(path, read_only=True)['Test case']
    rows = ws.iter_rows(values_only=True)
    header = next(row for row in rows if row and row[0] == 'STT')
    cases = [dict(zip(header, row)) for row in rows if row and row[1]]
    ws.parent.close()
    return cases


def label_lengths(email):
    domain = email.rsplit('@', 1)[1]
    return ', '.join(str(len(label)) for label in domain.split('.')[:-1])


class NewsletterEmailLengthTests(TestCase):
    """Mỗi dòng trong sheet "Test case" sinh ra một test_TC_NL_xx."""

    results = []

    def setUp(self):
        # Mỗi ca độc lập với giới hạn 5 lần / 10 phút / IP của SCRUM-34
        cache.clear()
        self.client = Client(raise_request_exception=False)

    def run_case(self, case):
        email = case['Email đầu vào']
        # Bảo vệ dữ liệu thiết kế: độ dài ghi trong Excel phải khớp với email thật
        self.assertEqual(len(email), case['Tổng độ dài'], 'Sai dữ liệu: tổng độ dài')
        self.assertEqual(len(email.rsplit('@', 1)[0]), case['Độ dài phần trước @'], 'Sai dữ liệu: phần trước @')
        self.assertEqual(label_lengths(email), str(case['Độ dài nhãn tên miền']), 'Sai dữ liệu: nhãn tên miền')

        started_at = datetime.now()
        start = time.perf_counter()
        response = self.client.post(reverse('newsletter_subscribe'), {'email': email, 'next': '/'}, follow=True)
        duration_ms = (time.perf_counter() - start) * 1000
        final_url = response.redirect_chain[-1][0] if response.redirect_chain else ''
        status = parse_qs(urlparse(final_url).query).get('newsletter', [''])[0]
        content = response.content.decode()
        message = next((m for m in (PENDING_MESSAGE, INVALID_MESSAGE) if m in content), '(không có thông báo)')
        mails = [m for m in mail.outbox if email.lower() in m.to]

        # Bấm link trong thư xác nhận (nếu có) để xem email có thực sự vào DB không
        link = CONFIRM_LINK.search(mails[0].body) if mails else None
        if link:
            self.client.get(urlparse(link.group()).path)
        saved = NewsletterSubscriber.objects.filter(email=email.lower(), is_confirmed=True).exists()

        # Expected / Actual: True = hệ thống chấp nhận email (gửi thư xác nhận, bấm link thì được lưu DB)
        expected = case['Loại'] == 'Hợp lệ'
        accepted = status == 'pending' and message == PENDING_MESSAGE and len(mails) == 1 and saved
        rejected = status == 'invalid' and message == INVALID_MESSAGE and not mails and not saved
        passed = accepted if expected else rejected
        self.results.append({
            **case, 'Expected': expected, 'Actual': accepted, 'Status': 'PASS' if passed else 'FAIL',
            'Thoi_Gian_Chay': started_at.strftime('%d/%m/%Y %H:%M'), 'Thoi_Luong_ms': round(duration_ms, 3),
        })

        actual = (f'?newsletter={status or "(trống)"}, hiển thị "{message}", gửi {len(mails)} thư, '
                  f'{"email ĐƯỢC lưu vào DB" if saved else "không lưu email vào DB"}')
        self.assertTrue(passed, f'{case["Mã TC"]}: mong đợi "{case["Kết quả mong đợi"]}", thực tế {actual}')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls.results:
            write_report(sorted(cls.results, key=lambda r: r['STT']))


def make_test(case):
    def test(self):
        self.run_case(case)
    test.__doc__ = f'{case["Mã TC"]}: {case["Tên test case"]}'
    return test


for _case in load_test_cases():
    setattr(NewsletterEmailLengthTests, f'test_{_case["Mã TC"].replace("-", "_")}', make_test(_case))


# (tiêu đề cột report, cột tương ứng trong sheet "Test case" hoặc trong kết quả chạy, độ rộng)
REPORT_COLUMNS = [
    ('TC_ID', 'Mã TC', 11),
    ('Ten_Test_Case', 'Tên test case', 36),
    ('Loai', 'Loại', 13),
    ('email', 'Email đầu vào', 40),
    ('tongDoDai', 'Tổng độ dài', 11),
    ('doDaiTruocA', 'Độ dài phần trước @', 13),
    ('doDaiNhan', 'Độ dài nhãn tên miền', 15),
    ('Expected', 'Expected', 10),
    ('Actual', 'Actual', 10),
    ('Status', 'Status', 9),
    ('Tags', 'Tag được bao phủ', 26),
    ('Thoi_Gian_Chay', 'Thoi_Gian_Chay', 18),
    ('Thoi_Luong_ms', 'Thoi_Luong_ms', 15),
]


def write_report(results, columns=REPORT_COLUMNS, path=REPORT_FILE):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Report'
    ws.append([title for title, _, _ in columns])
    for r in results:
        ws.append([r[key] for _, key, _ in columns])

    for column, (title, _, width) in zip(ws.columns, columns):
        ws.column_dimensions[column[0].column_letter].width = width
        for cell in column:
            cell.alignment = Alignment(horizontal='left' if title == 'email' else 'center')
            if title == 'Thoi_Luong_ms':
                cell.number_format = '0.000'
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = 'B2'

    wb.save(path)


# ---------------------------------------------------------------------------
# SCRUM-41 - Giới hạn tần suất gửi form Liên hệ: Phân hoạch tương đương (EP) & Giá trị biên (BVA).
# Input : docs/lienhe_gioihan_testcase.xlsx (sheet "Test case")
# Output: docs/lienhe_gioihan_report.xlsx
# Chạy: python manage.py test contact.tests.ContactRateLimitTests -v 2

RATE_LIMIT_TESTCASE_FILE = DOCS_DIR / 'lienhe_gioihan_testcase.xlsx'
RATE_LIMIT_REPORT_FILE = DOCS_DIR / 'lienhe_gioihan_report.xlsx'
RATE_LIMIT_MESSAGE = 'Bạn gửi quá nhanh, vui lòng thử lại sau'

_CONTACT_DATA = {
    'form_type': 'contact', 'name': 'SCRUM-41 Test', 'email': 'scrum41@example.test',
    'phone': '0912345678', 'subject': 'tu_van', 'message': 'Kiem thu gioi han SCRUM-41',
}
RATE_LIMIT_ACTIONS = {
    'Liên hệ hợp lệ': _CONTACT_DATA,
    'Liên hệ sai dữ liệu': {**_CONTACT_DATA, 'phone': 'abc!!!@@@'},
    'Góp ý hợp lệ': {
        'form_type': 'feedback', 'name': 'SCRUM-41 Test', 'email': 'scrum41@example.test',
        'category': 'website', 'satisfaction': '5', 'message': 'Kiem thu gioi han SCRUM-41',
    },
}
# Thứ tự kiểm tra sai dữ liệu và giới hạn không được ticket quy định, nên cả hai phản hồi đều đúng
RATE_LIMIT_ALLOWED_OUTCOMES = {
    'Chấp nhận': {'Chấp nhận'},
    'Bị chặn': {'Bị chặn'},
    'Lỗi dữ liệu': {'Lỗi dữ liệu', 'Bị chặn'},
}


class ContactRateLimitTests(TestCase):
    """Mỗi dòng trong sheet "Test case" sinh ra một test_TC_LH_xx."""

    results = []

    def setUp(self):
        cache.clear()
        self.client = Client(raise_request_exception=False)
        # Đồng hồ đứng yên để thời gian chờ chính xác đến từng giây; self.elapsed là số giây đã trôi qua
        self.elapsed = 0
        base_time, base_now = time.time(), timezone.now()
        for target, clock in (
            ('time.time', lambda: base_time + self.elapsed),
            ('django.utils.timezone.now', lambda: base_now + timedelta(seconds=self.elapsed)),
        ):
            patcher = patch(target, clock)
            patcher.start()
            self.addCleanup(patcher.stop)

    def send(self, client, action, index, case, ip, **extra):
        if action == 'Mở trang (GET)':
            return client.get(reverse('contact_page'), REMOTE_ADDR=ip, **extra)
        data = RATE_LIMIT_ACTIONS[action]
        if case['Dữ liệu mỗi lần'] == 'Khác nhau':
            data = {**data, 'email': f'scrum41.{index}@example.test', 'message': f'{data["message"]} {index}'}
        return client.post(reverse('contact_page'), data, REMOTE_ADDR=ip, **extra)

    def run_case(self, case):
        for i in range(case['Số lần trước đó']):
            self.send(self.client, case['Thao tác trước đó'], i, case, case['IP trước đó'])
        self.elapsed = case['Thời gian chờ (giây)']

        action = case['Thao tác kiểm tra']
        client = Client(raise_request_exception=False) if case['Phiên kiểm tra'] == 'Phiên mới' else self.client
        extra = {'HTTP_X_FORWARDED_FOR': case['X-Forwarded-For']} if case['X-Forwarded-For'] else {}
        started_at = datetime.now()
        for i in range(case['Số lần kiểm tra']):
            start = time.perf_counter()
            response = self.send(client, action, 100 + i, case, case['IP kiểm tra'], follow=True, **extra)
            duration_ms = (time.perf_counter() - start) * 1000

        content = response.content.decode()
        success = (ContactSuccessMessageTests.feedback_success if action == 'Góp ý hợp lệ'
                   else ContactSuccessMessageTests.contact_success)
        if success in content:
            actual = 'Khác' if RATE_LIMIT_MESSAGE in content else 'Chấp nhận'
        elif RATE_LIMIT_MESSAGE in content:
            actual = 'Bị chặn'
        else:
            actual = 'Lỗi dữ liệu' if 'class="form-error"' in content else 'Khác'
        contacts, feedbacks = ContactMessage.objects.count(), Feedback.objects.count()

        expected = case['Kết quả mong đợi']
        passed = (actual in RATE_LIMIT_ALLOWED_OUTCOMES[expected]
                  and contacts == case['Liên hệ mong đợi'] and feedbacks == case['Góp ý mong đợi'])
        self.results.append({
            **case, 'Lan_Gui': case['Số lần trước đó'] + case['Số lần kiểm tra'],
            'Actual': actual, 'Lien_He_Thuc_Te': contacts, 'Gop_Y_Thuc_Te': feedbacks,
            'Status': 'PASS' if passed else 'FAIL',
            'Thoi_Gian_Chay': started_at.strftime('%d/%m/%Y %H:%M'), 'Thoi_Luong_ms': round(duration_ms, 3),
        })

        self.assertTrue(passed, f'{case["Mã TC"]}: mong đợi "{expected}" với {case["Liên hệ mong đợi"]} liên hệ, '
                                f'{case["Góp ý mong đợi"]} góp ý; thực tế "{actual}" với {contacts} liên hệ, '
                                f'{feedbacks} góp ý (HTTP {response.status_code})')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls.results:
            write_report(sorted(cls.results, key=lambda r: r['STT']),
                         RATE_LIMIT_REPORT_COLUMNS, RATE_LIMIT_REPORT_FILE)


for _case in load_test_cases(RATE_LIMIT_TESTCASE_FILE):
    setattr(ContactRateLimitTests, f'test_{_case["Mã TC"].replace("-", "_")}', make_test(_case))


# (tiêu đề cột report, cột tương ứng trong sheet "Test case" hoặc trong kết quả chạy, độ rộng)
RATE_LIMIT_REPORT_COLUMNS = [
    ('TC_ID', 'Mã TC', 11),
    ('Ten_Test_Case', 'Tên test case', 50),
    ('Tong_So_Lan', 'Lan_Gui', 12),
    ('Cho_Giay', 'Thời gian chờ (giây)', 10),
    ('Expected', 'Kết quả mong đợi', 13),
    ('Actual', 'Actual', 13),
    ('Lien_He_Mong_Doi', 'Liên hệ mong đợi', 18),
    ('Lien_He_Thuc_Te', 'Lien_He_Thuc_Te', 17),
    ('Gop_Y_Mong_Doi', 'Góp ý mong đợi', 16),
    ('Gop_Y_Thuc_Te', 'Gop_Y_Thuc_Te', 15),
    ('Status', 'Status', 9),
    ('Tags', 'Tag được bao phủ', 16),
    ('Thoi_Gian_Chay', 'Thoi_Gian_Chay', 18),
    ('Thoi_Luong_ms', 'Thoi_Luong_ms', 15),
]


class NewsletterEmailCaseTests(TestCase):
    def test_email_luon_luu_chu_thuong(self):
        s = NewsletterSubscriber.objects.create(email='An@Shop.vn')
        self.assertEqual(s.email, 'an@shop.vn')
 
    def test_khong_tao_duoc_ban_ghi_trung_khac_hoa_thuong(self):
        NewsletterSubscriber.objects.create(email='An@Shop.vn')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NewsletterSubscriber.objects.create(email='an@shop.vn')
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
 
    def test_admin_nhap_email_chu_hoa_trung_bi_bao_loi(self):
        NewsletterSubscriber.objects.create(email='an@shop.vn')
        s = NewsletterSubscriber(email='AN@Shop.vn')
        with self.assertRaises(ValidationError):
            s.full_clean()


class ContactMessageLengthValidationTests(TestCase):
    """
    Kiểm thử SCRUM-40: Giới hạn trường message (Nội dung) tối đa 2.000 ký tự.
    - Hợp lệ: ngắn (1 ký tự, bình thường), đúng 2.000 ký tự -> Lưu thành công.
    - Không hợp lệ: 2.001 ký tự, 1.000.000 ký tự -> Bị từ chối, hiển thị lỗi, không lưu DB.
    """

    def setUp(self):
        cache.clear()
        self.url = reverse('contact_page')
        self.base_data = {
            'form_type': 'contact',
            'name': 'Nguyễn Văn A',
            'email': 'nguyenvana@example.com',
            'phone': '0912345678',
            'subject': 'tu_van',
        }

    def test_message_short_valid_is_accepted(self):
        for msg in ('A', 'Xin chào shop, tôi cần tư vấn sản phẩm rau hữu cơ.'):
            with self.subTest(msg=msg):
                data = {**self.base_data, 'message': msg}
                response = self.client.post(self.url, data)
                self.assertRedirects(response, self.url + '?contact_success=1')
                self.assertTrue(ContactMessage.objects.filter(message=msg).exists())

    def test_message_boundary_exact_2000_chars_is_accepted(self):
        msg_2000 = 'A' * 2000
        data = {**self.base_data, 'message': msg_2000}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url + '?contact_success=1')
        self.assertEqual(ContactMessage.objects.filter(name='Nguyễn Văn A').count(), 1)
        saved = ContactMessage.objects.get(name='Nguyễn Văn A')
        self.assertEqual(len(saved.message), 2000)

    def test_message_boundary_2001_chars_is_rejected(self):
        msg_2001 = 'A' * 2001
        data = {**self.base_data, 'message': msg_2001}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.context['contact_form'].errors)
        self.assertContains(response, 'Nội dung không được dài quá 2000 ký tự.')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_message_1_million_chars_is_rejected(self):
        msg_1m = 'A' * 1_000_000
        data = {**self.base_data, 'message': msg_1m}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.context['contact_form'].errors)
        self.assertContains(response, 'Nội dung không được dài quá 2000 ký tự.')
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_invalid_data_not_saved_and_valid_submissions_still_work(self):
        bad_response = self.client.post(self.url, {**self.base_data, 'message': 'B' * 2500})
        self.assertEqual(bad_response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)

        good_response = self.client.post(self.url, {**self.base_data, 'message': 'Nội dung hợp lệ'})
        self.assertRedirects(good_response, self.url + '?contact_success=1')
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(ContactMessage.objects.first().message, 'Nội dung hợp lệ')
