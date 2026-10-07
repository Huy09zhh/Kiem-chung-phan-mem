from django.shortcuts import render, redirect
from products.models import Category
from .forms import ContactForm, FeedbackForm


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