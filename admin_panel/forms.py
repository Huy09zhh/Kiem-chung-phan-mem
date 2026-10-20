from django import forms
from accounts.forms import ProfileUpdateForm


class AdminProfileForm(ProfileUpdateForm):
    """Form sửa thông tin tài khoản dùng trong Admin Panel."""

    class Meta(ProfileUpdateForm.Meta):
        labels = {
            'username': 'Tên đăng nhập',
            'first_name': 'Họ',
            'last_name': 'Tên',
            'email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class AdminUserForm(AdminProfileForm):
    """Admin chỉnh sửa tài khoản người dùng, có thêm trạng thái hoạt động."""

    class Meta(AdminProfileForm.Meta):
        fields = ProfileUpdateForm.Meta.fields + ['is_active']
        labels = dict(AdminProfileForm.Meta.labels, is_active='Tài khoản đang hoạt động')