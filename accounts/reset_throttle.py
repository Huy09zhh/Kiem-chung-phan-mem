"""SCRUM-55: Giới hạn số yêu cầu đặt lại mật khẩu theo email và theo IP.

Đếm theo cửa sổ cố định PASSWORD_RESET_WINDOW_SECONDS giây, tính từ yêu cầu đầu tiên.
Đếm cả email không tồn tại trong hệ thống, để thông báo vượt ngưỡng không
tiết lộ email nào đã đăng ký.
"""
from django.conf import settings
from django.core.cache import cache

MAX_PER_EMAIL = getattr(settings, 'PASSWORD_RESET_MAX_PER_EMAIL', 3)
MAX_PER_IP = getattr(settings, 'PASSWORD_RESET_MAX_PER_IP', 10)
WINDOW_SECONDS = getattr(settings, 'PASSWORD_RESET_WINDOW_SECONDS', 15 * 60)


def _keys(request, email):
    ip = request.META.get('REMOTE_ADDR', '') if request is not None else ''
    return ('pw_reset:email:%s' % (email or '').strip().lower(),
            'pw_reset:ip:%s' % ip)


def is_limited(request, email):
    email_key, ip_key = _keys(request, email)
    return (cache.get(email_key, 0) >= MAX_PER_EMAIL
            or cache.get(ip_key, 0) >= MAX_PER_IP)


def register_request(request, email):
    for key in _keys(request, email):
        cache.add(key, 0, WINDOW_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, WINDOW_SECONDS)


def window_minutes():
    return max(1, WINDOW_SECONDS // 60)
