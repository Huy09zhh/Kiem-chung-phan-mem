from django import forms
from .models import ContactMessage, Feedback


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Họ và tên'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Số điện thoại'
            }),
            'subject': forms.Select(attrs={
                'class': 'contact-input'
            }),
            'message': forms.Textarea(attrs={
                'class': 'contact-input contact-textarea',
                'placeholder': 'Nhập nội dung liên hệ của bạn...',
                'rows': 5
            }),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'category', 'satisfaction', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Họ và tên'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Email (không bắt buộc)'
            }),
            'category': forms.Select(attrs={
                'class': 'contact-input'
            }),
            'satisfaction': forms.Select(attrs={
                'class': 'contact-input'
            }),
            'message': forms.Textarea(attrs={
                'class': 'contact-input contact-textarea',
                'placeholder': 'Chia sẻ trải nghiệm hoặc góp ý của bạn...',
                'rows': 4
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email or ''