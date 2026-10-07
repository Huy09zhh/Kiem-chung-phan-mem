from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('search-suggestions/', views.product_search_suggestions, name='product_search_suggestions'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
]