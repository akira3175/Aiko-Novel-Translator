from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from .models import Novel, Volume, Chapter, Segment, Glossary
from .utils.yaml_io import import_yaml_file
from .forms import UploadYAMLForm
from .utils.ai_client import translate_text, review_translation
from .utils.segment_processor import SegmentProcessor
from .utils.glossary_generator import GlossaryGenerator
import yaml
from django.http import HttpResponse


def dashboard(request):
    novels = Novel.objects.all()
    return render(request, 'core/dashboard.html', {'novels': novels})


def novel_detail(request, novel_id):
    novel = get_object_or_404(Novel, pk=novel_id)
    
    # Thống kê glossary
    glossary_count = novel.glossaries.count()
    glossary_terms = novel.glossaries.all()[:50]  # Lấy 50 terms đầu tiên
    
    # Lấy checkpoint
    generator = GlossaryGenerator(novel)
    checkpoint = generator.get_checkpoint()
    
    context = {
        'novel': novel,
        'glossary_count': glossary_count,
        'glossary_terms': glossary_terms,
        'checkpoint': checkpoint,
    }
    return render(request, 'core/novel_detail.html', context)


def volume_detail(request, volume_id):
    volume = get_object_or_404(Volume, pk=volume_id)
    return render(request, 'core/volume_detail.html', {'volume': volume})


def chapter_detail(request, chapter_id):
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    
    # Lấy thông tin segments
    segments = chapter.segments.all()
    progress = SegmentProcessor.get_translation_progress(chapter)
    
    context = {
        'chapter': chapter,
        'segments': segments,
        'progress': progress,
    }
    return render(request, 'core/chapter_detail.html', context)


def import_yaml_view(request):
    if request.method == "POST":
        form = UploadYAMLForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES["file"]
            try:
                result = import_yaml_file(f)
                return render(request, "core/import_yaml.html", {
                    "form": UploadYAMLForm(),
                    "success": f"✅ Nhập {result['chapters']} chương, {result['segments']} đoạn thành công!"
                })
            except Exception as e:
                return render(request, "core/import_yaml.html", {
                    "form": form,
                    "error": str(e)
                })
    else:
        form = UploadYAMLForm()
    return render(request, "core/import_yaml.html", {"form": form})


@require_POST
def prepare_chapter_view(request, chapter_id):
    """Chuẩn bị chapter bằng cách chia thành segments"""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    
    try:
        segment_count = SegmentProcessor.create_segments(chapter)
        return JsonResponse({
            'ok': True,
            'message': f'Đã chia thành {segment_count} segments',
            'segment_count': segment_count
        })
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)


@require_POST
def translate_segment_view(request, segment_id):
    """Dịch một segment"""
    segment = get_object_or_404(Segment, pk=segment_id)
    
    try:
        # Lấy glossary của novel
        glossary_terms = segment.chapter.volume.novel.glossaries.all()
        glossary_context = "\n".join([
            f"{g.term_cn} → {g.term_vi}"
            for g in glossary_terms
        ])
        
        # Dịch segment
        translated = translate_text(
            segment.content_raw,
            glossary_context=glossary_context
        )
        
        segment.translation = translated
        segment.save()
        
        # Cập nhật progress
        progress = SegmentProcessor.get_translation_progress(segment.chapter)
        
        # Nếu đã dịch xong tất cả, gộp lại
        if progress['remaining'] == 0:
            merged = SegmentProcessor.merge_translations(segment.chapter)
            segment.chapter.translation = merged
            segment.chapter.status = 'translated'
            segment.chapter.save()
        
        return JsonResponse({
            'ok': True,
            'translation': translated,
            'progress': progress
        })
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)


@require_POST
def translate_chapter_auto_view(request, chapter_id):
    """Dịch toàn bộ chapter (tự động chia segments và dịch)"""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    
    try:
        # Bước 1: Chia segments nếu chưa có
        if chapter.segments.count() == 0:
            SegmentProcessor.create_segments(chapter)
        
        # Bước 2: Dịch từng segment
        glossary_terms = chapter.volume.novel.glossaries.all()
        glossary_context = "\n".join([
            f"{g.term_cn} → {g.term_vi}"
            for g in glossary_terms
        ])
        
        translated_count = 0
        for segment in chapter.segments.all():
            if not segment.translation:
                segment.translation = translate_text(
                    segment.content_raw,
                    glossary_context=glossary_context
                )
                segment.save()
                translated_count += 1
        
        # Bước 3: Gộp translations
        merged = SegmentProcessor.merge_translations(chapter)
        chapter.translation = merged
        chapter.status = 'translated'
        chapter.save()
        
        return JsonResponse({
            'ok': True,
            'message': f'Đã dịch {translated_count} segments',
            'translation': merged
        })
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)


@require_POST
def review_chapter_view(request, chapter_id):
    """Review chất lượng dịch của chapter"""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    
    # Review từng segment
    total_score = 0
    reviews = []
    
    for segment in chapter.segments.all():
        if segment.translation:
            score, report = review_translation(
                segment.content_raw,
                segment.translation
            )
            segment.match_percent = score
            segment.review = report
            segment.save()
            
            total_score += score
            reviews.append(f"Segment {segment.index}: {score}%\n{report}")
    
    # Tính điểm trung bình
    segment_count = chapter.segments.count()
    avg_score = total_score / segment_count if segment_count > 0 else 0
    
    chapter.match_percent = avg_score
    chapter.review = "\n\n".join(reviews)
    chapter.save()
    
    return JsonResponse({'ok': True, 'avg_score': round(avg_score, 1)})


def review_chapter_results_view(request, chapter_id):
    """Lấy kết quả review của chapter"""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    
    segments = []
    for segment in chapter.segments.all():
        if segment.match_percent > 0:
            segments.append({
                'index': segment.index,
                'match_percent': segment.match_percent,
                'review': segment.review or '',
            })
    
    return JsonResponse({
        'ok': True,
        'segments': segments,
        'avg_score': chapter.match_percent,
    })


# ==================== GLOSSARY VIEWS ====================

def glossary_list_api_view(request, novel_id):
    """API endpoint để lấy glossary với pagination và search"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    page = int(request.GET.get('page', 1))
    search = request.GET.get('search', '').strip()
    per_page = 30
    
    # Query glossary
    terms_query = novel.glossaries.all()
    
    # Search filter
    if search:
        terms_query = terms_query.filter(
            Q(term_cn__icontains=search) | 
            Q(term_vi__icontains=search) |
            Q(note__icontains=search)
        )
    
    terms_query = terms_query.order_by('term_cn')
    
    # Pagination
    paginator = Paginator(terms_query, per_page)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    terms = [{
        'id': term.id,
        'term_cn': term.term_cn,
        'term_vi': term.term_vi,
        'note': term.note or '',
    } for term in page_obj]
    
    return JsonResponse({
        'ok': True,
        'terms': terms,
        'total_count': paginator.count,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
        }
    })


def glossary_list_view(request, novel_id):
    """Xem danh sách glossary của novel"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    # Pagination
    terms = novel.glossaries.all().order_by('term_cn')
    paginator = Paginator(terms, 50)  # 50 terms per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Thống kê
    generator = GlossaryGenerator(novel)
    checkpoint = generator.get_checkpoint()
    
    context = {
        'novel': novel,
        'page_obj': page_obj,
        'checkpoint': checkpoint,
        'total_terms': terms.count(),
    }
    return render(request, 'core/glossary_list.html', context)


@require_POST
def generate_glossary_view(request, novel_id):
    """Tạo glossary tự động từ chapters"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    # Lấy tham số
    from_checkpoint = request.POST.get('from_checkpoint', 'true') == 'true'
    
    try:
        generator = GlossaryGenerator(novel)
        summary = generator.generate(start_from_checkpoint=from_checkpoint)
        
        return JsonResponse({
            'ok': True,
            'summary': summary
        })
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)


@require_POST
def reset_glossary_checkpoint_view(request, novel_id):
    """Reset checkpoint về 0"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    generator = GlossaryGenerator(novel)
    generator.save_checkpoint(0)
    
    return JsonResponse({'ok': True, 'message': 'Đã reset checkpoint về 0'})


@require_POST
def delete_glossary_term_view(request, term_id):
    """Xóa một term trong glossary"""
    term = get_object_or_404(Glossary, pk=term_id)
    term.delete()
    
    return JsonResponse({'ok': True})


@require_POST
def add_glossary_term_view(request, novel_id):
    """Thêm term mới vào glossary"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    term_cn = request.POST.get('term_cn', '').strip()
    term_vi = request.POST.get('term_vi', '').strip()
    note = request.POST.get('note', '').strip()
    
    if term_cn and term_vi:
        Glossary.objects.update_or_create(
            novel=novel,
            term_cn=term_cn,
            defaults={
                'term_vi': term_vi,
                'note': note
            }
        )
        return JsonResponse({'ok': True})
    
    return JsonResponse({'ok': False, 'error': 'Missing required fields'}, status=400)


@require_POST
def update_glossary_term_view(request, novel_id, term_id):
    """Cập nhật một field của glossary term (inline editing)"""
    import json
    
    term = get_object_or_404(Glossary, pk=term_id, novel_id=novel_id)
    
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value', '').strip()
        
        if field in ['term_cn', 'term_vi', 'note']:
            setattr(term, field, value)
            term.save()
            return JsonResponse({'ok': True})
        else:
            return JsonResponse({'ok': False, 'error': 'Invalid field'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


# ==================== REVIEW VIEWS ====================

def review_stats_view(request, novel_id):
    """Lấy thống kê review của novel"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    # Lấy tất cả chapters đã dịch
    chapters = []
    for volume in novel.volumes.all().order_by('index'):
        for chapter in volume.chapters.filter(translation__isnull=False).order_by('index'):
            chapters.append({
                'id': chapter.id,
                'title': chapter.title_translation or chapter.title,
                'volume_id': volume.id,
                'volume_index': volume.index,
                'chapter_index': chapter.index,
                'match_percent': chapter.match_percent,
                'review': chapter.review,
            })
    
    # Tính thống kê
    reviewed_chapters = [ch for ch in chapters if ch['match_percent'] > 0]
    avg_score = sum(ch['match_percent'] for ch in reviewed_chapters) / len(reviewed_chapters) if reviewed_chapters else 0
    low_score_count = len([ch for ch in reviewed_chapters if ch['match_percent'] < 80])
    
    return JsonResponse({
        'ok': True,
        'chapters': chapters,
        'reviewed_count': len(reviewed_chapters),
        'avg_score': round(avg_score, 1),
        'low_score_count': low_score_count,
    })


@require_POST
def review_all_chapters_view(request, novel_id):
    """Review tất cả chapters đã dịch của novel"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    try:
        reviewed_count = 0
        total_score = 0
        
        for volume in novel.volumes.all():
            for chapter in volume.chapters.filter(translation__isnull=False):
                # Review từng segment
                segment_scores = []
                
                for segment in chapter.segments.all():
                    if segment.translation:
                        score, report = review_translation(
                            segment.content_raw,
                            segment.translation
                        )
                        segment.match_percent = score
                        segment.review = report
                        segment.save()
                        segment_scores.append(score)
                
                # Tính điểm trung bình cho chapter
                if segment_scores:
                    avg_score = sum(segment_scores) / len(segment_scores)
                    chapter.match_percent = avg_score
                    chapter.save()
                    
                    total_score += avg_score
                    reviewed_count += 1
        
        avg_score = total_score / reviewed_count if reviewed_count > 0 else 0
        
        return JsonResponse({
            'ok': True,
            'reviewed_count': reviewed_count,
            'avg_score': round(avg_score, 1)
        })
        
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)


@require_POST
def review_volume_view(request, volume_id):
    """Review tất cả chapters trong một volume"""
    volume = get_object_or_404(Volume, pk=volume_id)
    
    try:
        reviewed_count = 0
        total_score = 0
        
        for chapter in volume.chapters.filter(translation__isnull=False):
            # Review từng segment
            segment_scores = []
            
            for segment in chapter.segments.all():
                if segment.translation:
                    score, report = review_translation(
                        segment.content_raw,
                        segment.translation
                    )
                    segment.match_percent = score
                    segment.review = report
                    segment.save()
                    segment_scores.append(score)
            
            # Tính điểm trung bình cho chapter
            if segment_scores:
                avg_score = sum(segment_scores) / len(segment_scores)
                chapter.match_percent = avg_score
                chapter.save()
                
                total_score += avg_score
                reviewed_count += 1
        
        avg_score = total_score / reviewed_count if reviewed_count > 0 else 0
        
        return JsonResponse({
            'ok': True,
            'reviewed_count': reviewed_count,
            'avg_score': round(avg_score, 1)
        })
        
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)
    
#==================== EXPORT / IMPORT VIEWS ====================

def export_novel_yaml_view(request, novel_id):
    """Export novel segments to YAML file theo format chuẩn"""
    from django.http import HttpResponse
    import yaml
    
    novel = get_object_or_404(Novel, pk=novel_id)
    
    # Lấy dữ liệu segments
    segments_data = []
    
    for volume in novel.volumes.all().order_by('index'):
        for chapter in volume.chapters.all().order_by('index'):
            # Nếu có segments, export từng segment
            if chapter.segments.exists():
                for segment in chapter.segments.all().order_by('index'):
                    segments_data.append({
                        'id': f'Volume_{volume.index}_Chapter_{chapter.index}_Segment_{segment.index}',
                        'title': chapter.title,
                        'content': segment.content_raw,
                        'title_translation': chapter.title_translation or '',
                        'translation': segment.translation or '',
                    })
            else:
                # Nếu chưa chia segment, export toàn bộ chapter
                segments_data.append({
                    'id': f'Volume_{volume.index}_Chapter_{chapter.index}',
                    'title': chapter.title,
                    'content': chapter.content_raw or '',
                    'title_translation': chapter.title_translation or '',
                    'translation': chapter.translation or '',
                })
    
    # Tạo YAML với format đẹp
    yaml_content = yaml.dump(
        segments_data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
        indent=2
    )
    
    # Tạo response
    response = HttpResponse(yaml_content, content_type='text/yaml; charset=utf-8')
    safe_title = novel.title.replace(' ', '_')[:50]
    filename = f"{safe_title}_export.yaml"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def export_glossary_txt_view(request, novel_id):
    """Export glossary to TXT file"""
    from django.http import HttpResponse
    
    novel = get_object_or_404(Novel, pk=novel_id)
    terms = novel.glossaries.all().order_by('term_cn')
    
    lines = []
    for term in terms:
        lines.append(f"{term.term_cn} = {term.term_vi}")
        if term.note:
            lines.append(f"# {term.note}")
    
    txt_content = "\n".join(lines)
    response = HttpResponse(txt_content, content_type='text/plain; charset=utf-8')
    safe_title = novel.title.replace(' ', '_')[:50]
    filename = f"{safe_title}_glossary.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@require_POST
def import_glossary_txt_view(request, novel_id):
    """Import glossary from TXT file"""
    novel = get_object_or_404(Novel, pk=novel_id)
    
    if 'file' not in request.FILES:
        return JsonResponse({'ok': False, 'error': 'Không có file'}, status=400)
    
    file = request.FILES['file']
    
    try:
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        imported_count = 0
        updated_count = 0
        current_note = ''
        
        for line in lines:
            line = line.strip()
            
            if not line:
                current_note = ''
                continue
            
            if line.startswith('#'):
                current_note = line[1:].strip()
                continue
            
            if ' = ' in line:
                parts = line.split(' = ', 1)
                if len(parts) == 2:
                    term_cn = parts[0].strip()
                    term_vi = parts[1].strip()
                    
                    existing = novel.glossaries.filter(term_cn=term_cn).first()
                    
                    if existing:
                        existing.term_vi = term_vi
                        if current_note:
                            existing.note = current_note
                        existing.save()
                        updated_count += 1
                    else:
                        Glossary.objects.create(
                            novel=novel,
                            term_cn=term_cn,
                            term_vi=term_vi,
                            note=current_note
                        )
                        imported_count += 1
                    
                    current_note = ''
        
        return JsonResponse({
            'ok': True,
            'imported_count': imported_count,
            'updated_count': updated_count,
            'message': f'✅ Import thành công: {imported_count} terms mới, {updated_count} terms cập nhật'
        })
        
    except UnicodeDecodeError:
        return JsonResponse({
            'ok': False,
            'error': 'File không đúng encoding. Vui lòng dùng UTF-8'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': f'Lỗi: {str(e)}'
        }, status=400)