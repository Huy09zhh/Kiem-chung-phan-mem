from django.db import migrations


def normalize_emails(apps, schema_editor):
    Sub = apps.get_model('contact', 'NewsletterSubscriber')
    groups = {}
    for s in Sub.objects.order_by('id'):
        groups.setdefault(s.email.strip().lower(), []).append(s)
    for email, subs in groups.items():
        keep = subs[0]
        if any(x.is_confirmed for x in subs):
            keep.is_confirmed = True
        for extra in subs[1:]:
            extra.delete()          
        keep.email = email
        keep.save()


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0003_newslettersubscriber_is_confirmed'),
    ]

    operations = [
        migrations.RunPython(normalize_emails, migrations.RunPython.noop),
    ]