from django.contrib import admin
from .models import ContactMessage, Feedback


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'is_resolved', 'created_at')
    list_filter = ('subject', 'is_resolved', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message')
    list_editable = ('is_resolved',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'category', 'satisfaction', 'is_reviewed', 'created_at')
    list_filter = ('category', 'satisfaction', 'is_reviewed', 'created_at')
    search_fields = ('name', 'email', 'message')
    list_editable = ('is_reviewed',)