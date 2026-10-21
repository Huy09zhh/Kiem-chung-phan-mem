from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from products.models import Product


def home(request):
    products = Product.objects.all()

    flash_sale_qs = Product.objects.filter(is_flash_sale=True)
    flash_sale_paginator = Paginator(flash_sale_qs, 4)
    flash_sale_page = request.GET.get('flash_page')
    flash_sale_products = flash_sale_paginator.get_page(flash_sale_page)

    featured_qs = Product.objects.filter(is_featured=True)
    featured_paginator = Paginator(featured_qs, 4)
    featured_page = request.GET.get('featured_page')
    featured_products = featured_paginator.get_page(featured_page)

    shop_products_qs = Product.objects.all()
    shop_paginator = Paginator(shop_products_qs, 12)
    shop_page = request.GET.get('page')
    shop_products = shop_paginator.get_page(shop_page)

    context = {
        'products': products,
        'flash_sale_products': flash_sale_products,
        'featured_products': featured_products,
        'shop_products': shop_products,
    }

    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')


POLICIES = {
    'doi-tra': {
        'title': 'Chính sách đổi trả và hoàn tiền',
        'intro': 'Green Shop cam kết mang đến thực phẩm tươi sạch. Nếu sản phẩm bạn nhận được chưa đạt kỳ vọng, chúng tôi sẽ hỗ trợ đổi trả nhanh chóng, minh bạch và không gây phiền hà.',
        'sections': [
            {'heading': '1. Phạm vi áp dụng', 'items': [
                'Chính sách áp dụng cho tất cả đơn hàng đặt qua website Green Shop.',
                'Áp dụng cho cả hình thức thanh toán khi nhận hàng (COD), chuyển khoản QR và thanh toán trực tuyến.',
                'Các chương trình khuyến mãi, flash sale vẫn được đổi trả theo đúng chính sách này, trừ khi có thông báo riêng trên trang sản phẩm.']},
            {'heading': '2. Trường hợp được đổi trả', 'items': [
                'Sản phẩm bị dập nát, héo úa, hư hỏng hoặc có dấu hiệu biến chất khi nhận hàng.',
                'Sản phẩm giao sai chủng loại, sai quy cách hoặc sai số lượng so với đơn đặt hàng.',
                'Sản phẩm không đạt chất lượng như mô tả trên website (độ tươi, kích thước, xuất xứ).',
                'Sản phẩm bị thiếu so với đơn hàng, hoặc bao bì bị rách, hở làm ảnh hưởng đến chất lượng bên trong.',
                'Sản phẩm đã hết hạn sử dụng hoặc cận hạn không đủ thời gian dùng như cam kết.']},
            {'heading': '3. Trường hợp không áp dụng đổi trả', 'items': [
                'Sản phẩm đã qua sử dụng, chế biến hoặc bảo quản không đúng hướng dẫn sau khi nhận hàng.',
                'Yêu cầu được gửi sau thời hạn quy định tại mục 4.',
                'Sản phẩm không còn nguyên trạng do lỗi của khách hàng trong quá trình bảo quản.',
                'Khách hàng đổi ý, không còn nhu cầu mà sản phẩm không có lỗi (trừ khi Green Shop có chính sách hỗ trợ riêng).',
                'Không cung cấp được hình ảnh, video hoặc thông tin đơn hàng để đối chiếu.']},
            {'heading': '4. Thời hạn gửi yêu cầu', 'items': [
                'Rau củ quả và thực phẩm tươi: trong vòng 24 giờ kể từ khi nhận hàng.',
                'Thực phẩm đóng gói, khô và sản phẩm khác: trong vòng 3 ngày kể từ khi nhận hàng.',
                'Yêu cầu gửi trễ hơn thời hạn trên sẽ được xem xét tùy từng trường hợp cụ thể.']},
            {'heading': '5. Quy trình đổi trả', 'items': [
                'Bước 1: Liên hệ Green Shop qua hotline 1900 29 29 62 hoặc gửi yêu cầu tại trang Liên hệ, kèm mã đơn hàng.',
                'Bước 2: Cung cấp hình ảnh hoặc video rõ ràng thể hiện tình trạng sản phẩm và bao bì.',
                'Bước 3: Green Shop xác nhận yêu cầu trong vòng 24 giờ làm việc và thông báo hướng xử lý.',
                'Bước 4: Giao sản phẩm đổi hoặc hoàn tiền theo phương án đã thống nhất.']},
            {'heading': '6. Hình thức xử lý', 'items': [
                'Đổi sản phẩm mới cùng loại và giá trị, miễn phí vận chuyển chiều đổi.',
                'Hoàn tiền toàn bộ hoặc một phần giá trị sản phẩm lỗi nếu sản phẩm đổi không còn hàng.',
                'Tặng mã giảm giá cho lần mua sau trong trường hợp khách hàng đồng ý.']},
            {'heading': '7. Chính sách hoàn tiền', 'items': [
                'Đơn thanh toán khi nhận hàng: hoàn tiền qua chuyển khoản ngân hàng theo thông tin khách hàng cung cấp.',
                'Đơn đã thanh toán qua chuyển khoản hoặc cổng thanh toán: hoàn về đúng tài khoản đã thanh toán.',
                'Thời gian hoàn tiền từ 3 đến 7 ngày làm việc kể từ khi yêu cầu được xác nhận, tùy ngân hàng.',
                'Đơn hàng bị hủy trước khi giao sẽ được hoàn lại toàn bộ số tiền đã thanh toán.']},
            {'heading': '8. Lưu ý', 'items': [
                'Vui lòng kiểm tra hàng ngay khi nhận và quay video mở hàng để việc xử lý nhanh hơn.',
                'Green Shop có quyền từ chối yêu cầu nếu phát hiện thông tin không trung thực.',
                'Chính sách có thể được cập nhật theo từng thời kỳ và có hiệu lực từ khi đăng tải trên website.']},
        ],
    },
    'van-chuyen': {
        'title': 'Chính sách vận chuyển và giao nhận',
        'intro': 'Green Shop giao hàng tận nơi, ưu tiên nhanh và giữ độ tươi của sản phẩm. Dưới đây là thông tin chi tiết về phạm vi, thời gian, phí giao hàng và các lưu ý khi nhận hàng.',
        'sections': [
            {'heading': '1. Phạm vi giao hàng', 'items': [
                'Giao hàng nội thành TP. Hồ Chí Minh và các khu vực lân cận theo danh sách hiển thị khi đặt hàng.',
                'Các tỉnh thành khác được giao qua đơn vị vận chuyển đối tác, áp dụng với sản phẩm có thể bảo quản.',
                'Một số sản phẩm tươi sống chỉ giao trong nội thành để đảm bảo chất lượng.']},
            {'heading': '2. Thời gian giao hàng', 'items': [
                'Nội thành: giao trong ngày với đơn đặt trước 15:00, hoặc trong vòng 24 giờ.',
                'Ngoại thành: từ 1 đến 2 ngày làm việc.',
                'Tỉnh thành khác: từ 2 đến 5 ngày làm việc tùy khu vực.',
                'Thời gian có thể kéo dài hơn vào dịp lễ, Tết, thời tiết xấu hoặc khi lượng đơn tăng cao.']},
            {'heading': '3. Phí vận chuyển', 'items': [
                'Phí giao hàng được tính theo khoảng cách và khối lượng đơn hàng, hiển thị rõ khi thanh toán.',
                'Miễn phí vận chuyển cho đơn hàng đạt giá trị tối thiểu theo chương trình đang áp dụng.',
                'Đơn hàng giao nhanh hoặc giao theo khung giờ chỉ định có thể phát sinh phụ phí, được báo trước khi xác nhận.']},
            {'heading': '4. Theo dõi đơn hàng', 'items': [
                'Sau khi đặt hàng, bạn nhận được trang xác nhận kèm mã đơn hàng.',
                'Trạng thái đơn (chờ xử lý, đã xác nhận, đang giao, hoàn thành) được cập nhật bởi Green Shop.',
                'Nhân viên giao hàng sẽ liên hệ qua số điện thoại bạn đã cung cấp trước khi giao.']},
            {'heading': '5. Kiểm tra hàng khi nhận', 'items': [
                'Vui lòng kiểm tra số lượng, chủng loại và tình trạng sản phẩm ngay khi nhận hàng.',
                'Nên quay video lúc mở gói hàng để làm căn cứ khi cần đổi trả.',
                'Nếu phát hiện sai lệch, hãy liên hệ ngay hotline để được hỗ trợ trong thời hạn quy định.']},
            {'heading': '6. Giao hàng không thành công', 'items': [
                'Nếu không liên lạc được người nhận sau nhiều lần, đơn hàng có thể bị hoàn về cửa hàng.',
                'Với đơn thanh toán khi nhận hàng bị từ chối nhận, Green Shop có thể giới hạn các đơn COD sau đó.',
                'Khi giao lại, phí vận chuyển có thể được tính thêm tùy trường hợp.']},
            {'heading': '7. Bảo quản trong quá trình vận chuyển', 'items': [
                'Rau củ quả được đóng gói bằng bao bì thân thiện môi trường, hạn chế dập nát.',
                'Sản phẩm cần giữ lạnh được đóng kèm túi giữ nhiệt hoặc đá khô theo từng loại.',
                'Vui lòng bảo quản sản phẩm đúng hướng dẫn ngay sau khi nhận để giữ độ tươi.']},
        ],
    },
    'bao-hanh': {
        'title': 'Chính sách bảo hành và cam kết chất lượng',
        'intro': 'Green Shop chịu trách nhiệm về chất lượng sản phẩm mình cung cấp. Chính sách này nêu rõ phạm vi cam kết, điều kiện và cách tiếp nhận khi sản phẩm gặp vấn đề.',
        'sections': [
            {'heading': '1. Cam kết chất lượng', 'items': [
                'Sản phẩm có nguồn gốc rõ ràng, được tuyển chọn từ các nhà cung cấp và nông trại uy tín.',
                'Thực phẩm tươi được kiểm tra trước khi đóng gói và giao đến khách hàng.',
                'Thông tin hạn sử dụng, xuất xứ và thành phần được thể hiện trên bao bì hoặc trang sản phẩm.']},
            {'heading': '2. Phạm vi bảo hành', 'items': [
                'Sản phẩm lỗi do nhà cung cấp hoặc phát sinh trong quá trình đóng gói, vận chuyển.',
                'Sản phẩm hư hỏng, biến chất trong thời hạn sử dụng khi đã được bảo quản đúng hướng dẫn.',
                'Dụng cụ, phụ kiện đi kèm (nếu có) được bảo hành theo thời hạn của nhà sản xuất.']},
            {'heading': '3. Thời hạn bảo hành', 'items': [
                'Thực phẩm tươi: trong vòng 24 giờ kể từ khi nhận hàng.',
                'Thực phẩm đóng gói: đến hết hạn sử dụng ghi trên bao bì, với điều kiện bao bì còn nguyên vẹn.',
                'Dụng cụ, phụ kiện: từ 3 đến 12 tháng tùy sản phẩm, theo phiếu bảo hành đi kèm.']},
            {'heading': '4. Điều kiện bảo hành', 'items': [
                'Sản phẩm còn trong thời hạn bảo hành và có thông tin đơn hàng tại Green Shop.',
                'Khách hàng cung cấp hình ảnh hoặc video thể hiện lỗi của sản phẩm.',
                'Sản phẩm được bảo quản đúng theo hướng dẫn in trên bao bì hoặc trang sản phẩm.']},
            {'heading': '5. Trường hợp không được bảo hành', 'items': [
                'Hư hỏng do bảo quản, sử dụng hoặc chế biến không đúng hướng dẫn.',
                'Sản phẩm đã quá thời hạn sử dụng hoặc quá thời hạn bảo hành.',
                'Hư hỏng do tác động bên ngoài như va đập, ngấm nước, côn trùng sau khi nhận hàng.',
                'Sản phẩm bị can thiệp, sửa chữa hoặc mở bao bì bởi bên thứ ba.']},
            {'heading': '6. Quy trình tiếp nhận bảo hành', 'items': [
                'Bước 1: Liên hệ hotline 1900 29 29 62 hoặc gửi yêu cầu tại trang Liên hệ, kèm mã đơn hàng.',
                'Bước 2: Cung cấp hình ảnh hoặc video thể hiện tình trạng lỗi.',
                'Bước 3: Green Shop kiểm tra thông tin và phản hồi trong vòng 24 giờ làm việc.',
                'Bước 4: Đổi sản phẩm mới, sửa chữa hoặc hoàn tiền theo phương án được thống nhất.']},
            {'heading': '7. Trách nhiệm của các bên', 'items': [
                'Green Shop chịu trách nhiệm về chất lượng sản phẩm tại thời điểm giao cho khách hàng.',
                'Khách hàng chịu trách nhiệm bảo quản sản phẩm đúng cách sau khi nhận hàng.',
                'Hai bên cùng trao đổi thiện chí để giải quyết khiếu nại một cách nhanh chóng và công bằng.']},
        ],
    },
}


def policy(request, slug):
    data = POLICIES.get(slug)
    if data is None:
        raise Http404
    return render(request, 'core/policy.html', {'policy': data})