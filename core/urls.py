from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard & Navigation
    path('', views.dashboard, name='dashboard'),
    path('novel/<int:novel_id>/', views.novel_detail, name='novel_detail'),
    path('volume/<int:volume_id>/', views.volume_detail, name='volume_detail'),
    path('chapter/<int:chapter_id>/', views.chapter_detail, name='chapter_detail'),
    path('import_yaml/', views.import_yaml_view, name='import_yaml'),
    
    # Export/Import endpoints
    path('novel/<int:novel_id>/export/yaml/', views.export_novel_yaml_view, name='export_novel_yaml'),
    path('novel/<int:novel_id>/glossary/export/', views.export_glossary_txt_view, name='export_glossary_txt'),
    path('novel/<int:novel_id>/glossary/import/', views.import_glossary_txt_view, name='import_glossary_txt'),
    
    # Translation endpoints (với retranslate support)
    path('chapter/<int:chapter_id>/prepare/', views.prepare_chapter_view, name='prepare_chapter'),
    path('chapter/<int:chapter_id>/translate/', views.translate_chapter_auto_view, name='translate_chapter'),
    path('chapter/<int:chapter_id>/retranslate/', views.retranslate_chapter_view, name='retranslate_chapter'),
    
    path('segment/<int:segment_id>/translate/', views.translate_segment_view, name='translate_segment'),
    path('segment/<int:segment_id>/retranslate/', views.retranslate_segment_view, name='retranslate_segment'),
    path('segment/<int:segment_id>/highlight-foreign/', views.highlight_foreign_chars_view, name='highlight_foreign'),
    
    # Translation style endpoint
    path('novel/<int:novel_id>/update-translation-style/', views.update_translation_style_view, name='update_translation_style'),

    # Review endpoints
    path('chapter/<int:chapter_id>/review/', views.review_chapter_view, name='review_chapter'),
    path('chapter/<int:chapter_id>/review/results/', views.review_chapter_results_view, name='review_chapter_results'),
    
    # Glossary endpoints
    path('novel/<int:novel_id>/glossary/', views.glossary_list_view, name='glossary_list'),
    path('novel/<int:novel_id>/glossary/list/', views.glossary_list_api_view, name='glossary_list_api'),
    path('novel/<int:novel_id>/glossary/generate/', views.generate_glossary_view, name='generate_glossary'),
    path('novel/<int:novel_id>/glossary/reset/', views.reset_glossary_checkpoint_view, name='reset_glossary_checkpoint'),
    path('novel/<int:novel_id>/glossary/add/', views.add_glossary_term_view, name='add_glossary_term'),
    path('novel/<int:novel_id>/glossary/update/<int:term_id>/', views.update_glossary_term_view, name='update_glossary_term'),
    path('glossary/<int:term_id>/delete/', views.delete_glossary_term_view, name='delete_glossary_term'),
    
    # Novel-level Review endpoints
    path('novel/<int:novel_id>/review/stats/', views.review_stats_view, name='review_stats'),
    path('novel/<int:novel_id>/review/all/', views.review_all_chapters_view, name='review_all_chapters'),
    path('volume/<int:volume_id>/review/', views.review_volume_view, name='review_volume'),
]