"""Hộp thư dev: hiển thị các email đã "gửi" khi chưa cấu hình SMTP (filebased backend).

Chỉ bật khi settings.DEV_MAILBOX_ENABLED (DEBUG=True và chưa có EMAIL_HOST_USER).
"""
import email
import re
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

SEPARATOR = b'-' * 79
URL_RE = re.compile(r'(https?://[^\s<]+)')


def _mailbox_dir():
    return Path(settings.EMAIL_FILE_PATH)


def _read_messages():
    messages = []
    folder = _mailbox_dir()
    if not folder.exists():
        return messages

    for log_file in folder.glob('*.log'):
        for chunk in log_file.read_bytes().split(SEPARATOR):
            chunk = chunk.strip()
            if not chunk:
                continue
            msg = email.message_from_bytes(chunk, policy=policy.default)
            part = msg.get_body(preferencelist=('plain', 'html'))
            body = part.get_content() if part else ''
            try:
                sent_at = parsedate_to_datetime(msg['Date'])
            except (TypeError, ValueError):
                sent_at = None
            messages.append({
                'from': msg['From'],
                'to': msg['To'],
                'subject': msg['Subject'],
                'sent_at': sent_at,
                'body': mark_safe(URL_RE.sub(r'<a href="\1">\1</a>', escape(body))),
            })

    messages.sort(key=lambda m: m['sent_at'].timestamp() if m['sent_at'] else 0, reverse=True)
    return messages


def _ensure_enabled():
    if not getattr(settings, 'DEV_MAILBOX_ENABLED', False):
        raise Http404


def mailbox_view(request):
    _ensure_enabled()
    return render(request, 'core/dev_mailbox.html', {
        'messages_list': _read_messages(),
        'mailbox_dir': _mailbox_dir(),
    })


@require_POST
def mailbox_clear_view(request):
    _ensure_enabled()
    for log_file in _mailbox_dir().glob('*.log'):
        log_file.unlink(missing_ok=True)
    return redirect('dev_mailbox')
