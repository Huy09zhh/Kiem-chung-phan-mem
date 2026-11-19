from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('products/', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('contact/', include('contact.urls')),
    path('admin-panel/', include('admin_panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    from django.http import HttpResponse

    def dev_shutdown_view(request):
        import os, threading, time
        def _stop():
            time.sleep(0.5)
            try:
                import coverage
                cov = coverage.Coverage.current()
                if cov:
                    cov.stop()
                    cov.save()
            except Exception:
                pass
            os._exit(0)
        threading.Thread(target=_stop).start()
        return HttpResponse("Server shutting down and coverage saved.")

    urlpatterns += [
        path('dev/shutdown/', dev_shutdown_view, name='dev_shutdown'),
    ]

if settings.DEV_MAILBOX_ENABLED:
    from core import dev_mailbox

    urlpatterns += [
        path('dev/mailbox/', dev_mailbox.mailbox_view, name='dev_mailbox'),
        path('dev/mailbox/clear/', dev_mailbox.mailbox_clear_view, name='dev_mailbox_clear'),
    ]