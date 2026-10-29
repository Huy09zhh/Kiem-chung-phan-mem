from django.core.exceptions import ValidationError

MAX_PASSWORD_LENGTH = 128


class MaximumLengthValidator:
    """Giới hạn độ dài tối đa của mật khẩu (mặc định 128 ký tự)."""

    def __init__(self, max_length=MAX_PASSWORD_LENGTH):
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) > self.max_length:
            raise ValidationError(
                'Mật khẩu không được dài quá %(max_length)d ký tự.',
                code='password_too_long',
                params={'max_length': self.max_length},
            )

    def get_help_text(self):
        return 'Mật khẩu không được dài quá %d ký tự.' % self.max_length