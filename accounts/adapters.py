"""SCRUM-53: Dự án chỉ đăng ký qua /accounts/register/ (RegisterForm, FR1.1).
allauth chỉ dùng cho đăng nhập Google, không cho đăng ký tài khoản thường."""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class NoLocalSignupAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        # Đóng form đăng ký mặc định của allauth (/accounts/signup/)
        return False


class GoogleSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        # Vẫn cho tạo tài khoản lần đầu khi đăng nhập bằng Google
        return True
