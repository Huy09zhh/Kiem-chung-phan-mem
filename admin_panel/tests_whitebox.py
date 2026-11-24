"""
Kiểm thử hộp trắng (Chương 4, IV.4 – Control Flow Testing) cho 2 chức năng đã kiểm thử hộp đen.

Phân hệ 6: Admin Orders & Analytics.
  1. Tìm kiếm đơn hàng      : admin_panel.views.admin_order_list
     27 câu lệnh, 8 quyết định (16 nhánh), V(G) = 9
  2. Cập nhật trạng thái đơn: admin_panel.views.admin_order_update_status
     12 câu lệnh, 2 quyết định (4 nhánh), V(G) = 3

Mã test case trong report (sheet PH6_Quân_HopTrang): test_wb_s1 → TC-AOA-WB-S1, test_wb_b3 → TC-AOA-WB-B3,
test_c1_... của OrderListConditionTests → TC-AOA-WB-C1..C4, test_wb_u1/u2 → TC-AOA-WB-U1/U2,
test_c1_... của UpdateStatusConditionTests → TC-AOA-WB-UC1..UC3.

Mỗi class là một bộ test trả lời câu hỏi "tối thiểu bao nhiêu test case để bao phủ 100%":
  OrderListStatementTests     : 2 test -> bao phủ câu lệnh 100% (nhánh mới 11/16)
  OrderListBranchTests        : 4 test -> bao phủ nhánh 100% (16/16)
  OrderListConditionTests     : 4 test -> bao phủ tổ hợp điều kiện của D6 (startswith('#') and isdigit())
  UpdateStatusStatementTests  : 2 test -> bao phủ câu lệnh 100% và nhánh 100% (4/4)
  UpdateStatusConditionTests  : 3 test -> bao phủ nhánh – điều kiện / tổ hợp điều kiện của D1 (A and B)

Chạy tất cả:   python manage.py test admin_panel.tests_whitebox -v 2
Đo độ phủ một bộ (ví dụ bộ phủ câu lệnh):
  coverage erase
  coverage run --branch --source=admin_panel manage.py test admin_panel.tests_whitebox.OrderListStatementTests
  coverage json -o coverage.json
  python tools/coverage_func.py coverage.json admin_order_list
"""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

ROW_ID = re.compile(r'<td>#(\d+)</td>')


class OrderListBase(TestCase):
    """Dữ liệu chung: 3 đơn khác nhau về tên, SĐT, trạng thái, phương thức thanh toán."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('wb_admin', password='pw-12345', is_staff=True)
        customer = User.objects.create_user('wb_customer', password='pw-12345')

        def mk(name, phone, status, method):
            return Order.objects.create(
                user=customer, full_name=name, phone=phone, address='1 Duong Test',
                total_price=100000, status=status, payment_method=method,
            )

        cls.o_an = mk('Nguyen Van An', '0911111111', 'paid', 'qr')
        cls.o_binh = mk('Tran Thi Binh', '0922222222', 'pending', 'cod')
        cls.o_ngoc = mk('Le Ngoc', '0933123456', 'shipping', 'mock')

    def setUp(self):
        self.client.force_login(self.admin)

    def ids(self, **params):
        resp = self.client.get(reverse('admin_order_list'), params)
        self.assertEqual(resp.status_code, 200)
        return {int(x) for x in ROW_ID.findall(resp.content.decode())}

    def all_ids(self):
        return {self.o_an.pk, self.o_binh.pk, self.o_ngoc.pk}


# ---------------------------------------------------------------------------
# 1. TÌM KIẾM ĐƠN HÀNG (admin_order_list)
#    D1 status_filter rỗng?          D2 status hợp lệ?
#    D3 payment_filter rỗng?         D4 payment hợp lệ?
#    D5 keyword rỗng?                D6 keyword dạng "#số"?
#    D7 len(keyword) >= 6?           D8 keyword toàn chữ số?
# ---------------------------------------------------------------------------
class OrderListStatementTests(OrderListBase):
    """Tối thiểu 2 test để bao phủ 100% câu lệnh. Nhánh False của D1, D3, D5, D7, D8 chưa chạy (11/16 nhánh)."""

    def test_wb_s1_status_hop_le_payment_hop_le_keyword_ma_don(self):
        # D1 T, D2 T, D3 T, D4 T, D5 T, D6 T
        got = self.ids(status='paid', payment_method='qr', keyword=f'#{self.o_an.pk}')
        self.assertEqual(got, {self.o_an.pk})

    def test_wb_s2_status_sai_payment_sai_keyword_6_chu_so(self):
        # D1 T, D2 F, D3 T, D4 F, D5 T, D6 F, D7 T, D8 T
        got = self.ids(status='hacked', payment_method='hacked', keyword='123456')
        self.assertEqual(got, set())


class OrderListBranchTests(OrderListStatementTests):
    """Tối thiểu 4 test để bao phủ 100% nhánh (2 test kế thừa ở trên + 2 test dưới)."""

    def test_wb_b3_chi_keyword_ngan_khong_phai_so(self):
        # D1 F, D3 F, D5 T, D6 F, D7 F, D8 F
        self.assertEqual(self.ids(keyword='Ng'), {self.o_an.pk, self.o_ngoc.pk})

    def test_wb_b4_khong_tham_so(self):
        # D1 F, D3 F, D5 F
        self.assertEqual(self.ids(), self.all_ids())


class OrderListConditionTests(OrderListBase):
    """Tổ hợp điều kiện của D6: C1 = keyword bắt đầu bằng '#', C2 = phần sau '#' toàn chữ số."""

    def test_c1_dung_c2_dung(self):          # '#<mã>'  -> lọc đúng mã đơn (nhánh True)
        self.assertEqual(self.ids(keyword=f'#{self.o_binh.pk}'), {self.o_binh.pk})

    def test_c1_dung_c2_sai(self):           # '#abc'   -> nhánh False, không đơn nào khớp
        self.assertEqual(self.ids(keyword='#abc'), set())

    def test_c1_sai_c2_dung(self):           # '<mã>'   -> nhánh False, tìm theo mã đơn ở D8
        self.assertEqual(self.ids(keyword=str(self.o_binh.pk)), {self.o_binh.pk})

    def test_c1_sai_c2_sai(self):            # 'Ng'     -> nhánh False, tìm theo tên
        self.assertEqual(self.ids(keyword='Ng'), {self.o_an.pk, self.o_ngoc.pk})


# ---------------------------------------------------------------------------
# 2. CẬP NHẬT TRẠNG THÁI ĐƠN (admin_order_update_status)
#    D1: new_status hợp lệ (A) VÀ chuyển được từ trạng thái hiện tại (B)?
#    D2: next == 'detail'?
# ---------------------------------------------------------------------------
class UpdateStatusBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('wb_admin2', password='pw-12345', is_staff=True)
        cls.customer = User.objects.create_user('wb_customer2', password='pw-12345')

    def setUp(self):
        self.client.force_login(self.admin)

    def make(self, status='pending'):
        return Order.objects.create(
            user=self.customer, full_name='Khach Test', phone='0912345678',
            address='1 Duong Test', total_price=100000, status=status,
        )

    def post(self, order, status, next_url=None):
        data = {'status': status}
        if next_url is not None:
            data['next'] = next_url
        return self.client.post(reverse('admin_order_update_status', args=[order.pk]), data)

    def check(self, resp, order, expected_status, expected_url):
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], expected_url)
        order.refresh_from_db()
        self.assertEqual(order.status, expected_status)


class UpdateStatusStatementTests(UpdateStatusBase):
    """Tối thiểu 2 test: bao phủ 100% câu lệnh, đồng thời 100% nhánh."""

    def test_wb_u1_hop_le_ve_trang_chi_tiet(self):          # D1 T, D2 T
        o = self.make('pending')
        self.check(self.post(o, 'confirmed', 'detail'), o, 'confirmed',
                   reverse('admin_order_detail', args=[o.pk]))

    def test_wb_u2_khong_hop_le_ve_danh_sach(self):         # D1 F, D2 F
        o = self.make('pending')
        self.check(self.post(o, 'hacked'), o, 'pending', reverse('admin_order_list'))


class UpdateStatusConditionTests(UpdateStatusBase):
    """D1 = A and B (A: trạng thái có trong danh sách, B: chuyển được từ trạng thái hiện tại).
    3 test phủ nhánh – điều kiện và mọi tổ hợp khả thi (A sai, B đúng là không thể xảy ra)."""

    def test_c1_a_dung_b_dung(self):        # A T, B T -> chấp nhận
        o = self.make('pending')
        self.check(self.post(o, 'paid', 'detail'), o, 'paid', reverse('admin_order_detail', args=[o.pk]))

    def test_c2_a_sai(self):                # A F (B không được xét) -> từ chối
        o = self.make('pending')
        self.check(self.post(o, 'hacked', 'detail'), o, 'pending', reverse('admin_order_detail', args=[o.pk]))

    def test_c3_a_dung_b_sai(self):         # A T, B F (đổi ngược) -> từ chối
        o = self.make('shipping')
        self.check(self.post(o, 'pending', 'detail'), o, 'shipping', reverse('admin_order_detail', args=[o.pk]))