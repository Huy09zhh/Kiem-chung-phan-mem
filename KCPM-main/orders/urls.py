from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('qr/<int:order_id>/', views.order_qr, name='order_qr'),
    path('qr/<int:order_id>/confirm/', views.confirm_qr_paid, name='confirm_qr_paid'),
    path('mock/<int:order_id>/', views.mock_payment, name='mock_payment'),
    path('mock/<int:order_id>/success/', views.mock_payment_success, name='mock_payment_success'),
    path('mock/<int:order_id>/fail/', views.mock_payment_fail, name='mock_payment_fail'),
]