from django.shortcuts import render, redirect
from products.models import Category
from .forms import ContactForm, FeedbackForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import NewsletterSubscriber

# validate_email của Django cho phép email dài tới 320 ký tự, nên tự chặn theo
# max_length của model (254) và giới hạn phần trước @ của RFC 5321 (64).
NEWSLETTER_EMAIL_MAX_LENGTH = NewsletterSubscriber._meta.get_field('email').max_length
EMAIL_LOCAL_PART_MAX_LENGTH = 64

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

@require_POST
def newsletter_subscribe(request):
    email = (request.POST.get('email') or '').strip().lower()
 
    next_url = request.POST.get('next') or '/'
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = '/'
    next_url = next_url.split('?')[0].split('#')[0]
 
    try:
        validate_email(email)
        if (len(email) > NEWSLETTER_EMAIL_MAX_LENGTH
                or len(email.rsplit('@', 1)[0]) > EMAIL_LOCAL_PART_MAX_LENGTH):
            raise ValidationError('Email vượt quá độ dài cho phép.')
    except ValidationError:
        result = 'invalid'
    else:
        _, created = NewsletterSubscriber.objects.get_or_create(email=email)
        result = 'success' if created else 'exists'
 
    return redirect(f'{next_url}?newsletter={result}#newsletter')
 