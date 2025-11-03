from django.contrib import admin
from .models import Novel, Volume, Chapter, Glossary, Segment, APIKey


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('novel', 'index', 'title')


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('volume', 'index', 'title', 'updated_at')

@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'index', 'updated_at')

@admin.register(Glossary)
class GlossaryAdmin(admin.ModelAdmin):
    list_display = ('novel', 'term_cn', 'term_vi')

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')