import hashlib

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from products.models import Category
from .forms import ContactForm, FeedbackForm
from .models import NewsletterSubscriber

NEWSLETTER_SALT = 'newsletter-confirm'
NEWSLETTER_TOKEN_MAX_AGE = 60 * 60 * 48      
NEWSLETTER_IP_LIMIT = 5                      
NEWSLETTER_IP_WINDOW = 60 * 10               
NEWSLETTER_EMAIL_COOLDOWN = 60 * 10          


def contact_page(request):
    categories = Category.objects.all()
    contact_form = ContactForm()
    feedback_form = FeedbackForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'contact':
            contact_form = ContactForm(request.POST)
            feedback_form = FeedbackForm()

            if contact_form.is_valid():
                contact_form.save()
                return redirect('/contact/?contact_success=1')

        elif form_type == 'feedback':
            feedback_form = FeedbackForm(request.POST)
            contact_form = ContactForm()

            if feedback_form.is_valid():
                feedback_form.save()
                return redirect('/contact/?feedback_success=1')

    return render(request, 'contact/contact.html', {
        'categories': categories,
        'contact_form': contact_form,
        'feedback_form': feedback_form,
        'contact_success': request.GET.get('contact_success') == '1',
        'feedback_success': request.GET.get('feedback_success') == '1',
    })


def _safe_next(request):
    next_url = request.POST.get('next') or '/'
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = '/'
    return next_url.split('?')[0].split('#')[0]


def _back(next_url, result):
    return redirect(f'{next_url}?newsletter={result}#newsletter')


@require_POST
def newsletter_subscribe(request):
    next_url = _safe_next(request)
    email = (request.POST.get('email') or '').strip().lower()

    try:
        validate_email(email)
    except ValidationError:
        return _back(next_url, 'invalid')

    ip = request.META.get('REMOTE_ADDR', 'unknown')
    ip_key = f'newsletter_ip_{ip}'
    cache.add(ip_key, 0, NEWSLETTER_IP_WINDOW)
    try:
        count = cache.incr(ip_key)
    except ValueError:
        cache.set(ip_key, 1, NEWSLETTER_IP_WINDOW)
        count = 1
    if count > NEWSLETTER_IP_LIMIT:
        return _back(next_url, 'limited')

    already = NewsletterSubscriber.objects.filter(email=email, is_confirmed=True).exists()
    email_key = 'newsletter_mail_' + hashlib.sha256(email.encode()).hexdigest()
    if not already and cache.add(email_key, 1, NEWSLETTER_EMAIL_COOLDOWN):
        token = signing.dumps(email, salt=NEWSLETTER_SALT)
        link = request.build_absolute_uri(reverse('newsletter_confirm', args=[token]))
        send_mail(
            'Xác nhận đăng ký nhận tin Green Shop',
            'Cảm ơn bạn đã quan tâm đến Green Shop.\n\n'
            f'Vui lòng bấm vào liên kết sau để xác nhận đăng ký (hiệu lực 48 giờ):\n{link}\n\n'
            'Nếu bạn không thực hiện đăng ký này, hãy bỏ qua email.',
            getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            [email],
            fail_silently=True,
        )
    return _back(next_url, 'pending')


def newsletter_confirm(request, token):
    try:
        email = signing.loads(token, salt=NEWSLETTER_SALT, max_age=NEWSLETTER_TOKEN_MAX_AGE)
    except signing.BadSignature:
        return _back('/', 'confirm_invalid')
    sub, _ = NewsletterSubscriber.objects.get_or_create(email=email)
    if not sub.is_confirmed:
        sub.is_confirmed = True
        sub.save(update_fields=['is_confirmed'])
    return _back('/', 'confirmed')