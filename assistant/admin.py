from django.contrib import admin

from .models import FAQ, ErrorCode, HelpArticle


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer", "keywords")


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "created_at")
    search_fields = ("code", "title", "description")


@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    search_fields = ("title", "keywords", "content")
