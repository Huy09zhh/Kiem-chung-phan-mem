from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Nhập tài khoản'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Nhập email'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Nhập mật khẩu'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Nhập lại mật khẩu'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Nhập tài khoản'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Nhập mật khẩu'})
    )


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Tên đăng nhập'})
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Họ'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Tên'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email'})

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email


class UserProfileUpdateForm(forms.ModelForm):
    """SCRUM-30: Form cập nhật hồ sơ dành cho người dùng thông thường.

    Trường username bị loại khỏi form hoàn toàn — không nhận, không xử lý,
    không lưu username từ dữ liệu POST của người dùng thường.
    Chỉ cho phép cập nhật: first_name, last_name, email.
    """

    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Họ'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Tên'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email'})

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'placeholder': 'Mật khẩu hiện tại'})
        self.fields['new_password1'].widget.attrs.update({'placeholder': 'Mật khẩu mới'})
        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Nhập lại mật khẩu mới'})

class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'placeholder': 'Nhập email của bạn'})

    def save(self, *args, **kwargs):
        # Dùng domain người dùng đang truy cập thay cho Site mặc định ("example.com"),
        # để liên kết đặt lại mật khẩu trong email mở được.
        request = kwargs.get('request')
        if request is not None and not kwargs.get('domain_override'):
            kwargs['domain_override'] = request.get_host()
        return super().save(*args, **kwargs)
