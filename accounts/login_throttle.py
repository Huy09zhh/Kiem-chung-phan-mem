"""SCRUM-54: Khóa tạm đăng nhập sau nhiều lần nhập sai liên tiếp.

Đếm số lần sai theo tên đăng nhập và theo địa chỉ IP (lưu trong cache).
Đạt ngưỡng thì khóa trong LOGIN_LOCKOUT_SECONDS giây, kể cả khi nhập đúng mật khẩu.
"""
from django.conf import settings
from django.core.cache import cache

MAX_FAILED_PER_USER = getattr(settings, 'LOGIN_MAX_FAILED_ATTEMPTS', 5)
MAX_FAILED_PER_IP = getattr(settings, 'LOGIN_IP_MAX_FAILED_ATTEMPTS', 20)
LOCKOUT_SECONDS = getattr(settings, 'LOGIN_LOCKOUT_SECONDS', 15 * 60)


def _client_ip(request):
    # Không tin X-Forwarded-For vì người dùng tự gửi được header này
    return request.META.get('REMOTE_ADDR', '') if request is not None else ''


def _keys(request, username):
    user_key = 'login_fail:user:%s' % (username or '').strip().lower()
    ip_key = 'login_fail:ip:%s' % _client_ip(request)
    return user_key, ip_key


def is_locked(request, username):
    user_key, ip_key = _keys(request, username)
    return (cache.get(user_key, 0) >= MAX_FAILED_PER_USER
            or cache.get(ip_key, 0) >= MAX_FAILED_PER_IP)


def register_failure(request, username):
    for key in _keys(request, username):
        # add() chỉ đặt hạn khóa ở lần sai đầu tiên; incr() giữ nguyên hạn đó
        cache.add(key, 0, LOCKOUT_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, LOCKOUT_SECONDS)


def reset_user(request, username):
    user_key, _ = _keys(request, username)
    cache.delete(user_key)


def lockout_minutes():
    return max(1, LOCKOUT_SECONDS // 60)
