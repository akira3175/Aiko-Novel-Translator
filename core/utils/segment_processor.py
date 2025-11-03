import re
from typing import List, Tuple
from ..models import Chapter, Segment


class SegmentProcessor:
    """Chia chapter thành segments ~3000 từ và quản lý việc dịch"""
    
    MAX_WORDS = 3000
    
    @staticmethod
    def count_words(text: str) -> int:
        """Đếm số từ trong văn bản (hỗ trợ cả tiếng Trung và tiếng Việt)"""
        # Với tiếng Trung, mỗi ký tự là 1 từ
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # Với các ngôn ngữ khác, tách bằng khoảng trắng
        other_words = len(re.findall(r'\b\w+\b', text))
        return chinese_chars + other_words
    
    @staticmethod
    def split_by_sentences(text: str) -> List[str]:
        """Tách văn bản thành các câu"""
        # Pattern cho tiếng Trung và tiếng Việt
        sentences = re.split(r'([。！？\.!?]+[\s]*)', text)
        result = []
        for i in range(0, len(sentences)-1, 2):
            if i+1 < len(sentences):
                result.append(sentences[i] + sentences[i+1])
            else:
                result.append(sentences[i])
        if sentences and not result:
            result = [text]
        return [s.strip() for s in result if s.strip()]
    
    @classmethod
    def create_segments(cls, chapter: Chapter) -> int:
        """
        Chia chapter thành các segments ~3000 từ
        Returns: số lượng segments được tạo
        """
        if not chapter.content_raw:
            return 0
        
        # Xóa segments cũ nếu có
        chapter.segments.all().delete()
        
        sentences = cls.split_by_sentences(chapter.content_raw)
        segments = []
        current_segment = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_words = cls.count_words(sentence)
            
            # Nếu câu hiện tại quá dài, tách riêng
            if sentence_words > cls.MAX_WORDS:
                if current_segment:
                    segments.append('\n'.join(current_segment))
                    current_segment = []
                    current_word_count = 0
                segments.append(sentence)
                continue
            
            # Nếu thêm câu này vượt quá giới hạn, lưu segment hiện tại
            if current_word_count + sentence_words > cls.MAX_WORDS and current_segment:
                segments.append('\n'.join(current_segment))
                current_segment = [sentence]
                current_word_count = sentence_words
            else:
                current_segment.append(sentence)
                current_word_count += sentence_words
        
        # Thêm segment cuối cùng
        if current_segment:
            segments.append('\n'.join(current_segment))
        
        # Tạo Segment objects
        for idx, content in enumerate(segments, start=1):
            Segment.objects.create(
                chapter=chapter,
                index=idx,
                content_raw=content
            )
        
        return len(segments)
    
    @classmethod
    def get_translation_progress(cls, chapter: Chapter) -> dict:
        """Lấy thông tin tiến độ dịch của chapter"""
        segments = chapter.segments.all()
        total = segments.count()
        translated = segments.filter(translation__isnull=False).exclude(translation='').count()
        
        return {
            'total': total,
            'translated': translated,
            'remaining': total - translated,
            'progress_percent': (translated / total * 100) if total > 0 else 0
        }
    
    @classmethod
    def merge_translations(cls, chapter: Chapter) -> str:
        """Gộp tất cả translations của segments thành bản dịch hoàn chỉnh"""
        segments = chapter.segments.order_by('index')
        translations = []
        
        for segment in segments:
            if segment.translation:
                translations.append(segment.translation.strip())
        
        return '\n\n'.join(translations)
    
    @classmethod
    def get_next_untranslated_segment(cls, chapter: Chapter):
        """Lấy segment tiếp theo chưa dịch"""
        return chapter.segments.filter(
            translation__isnull=True
        ).order_by('index').first() or chapter.segments.filter(
            translation=''
        ).order_by('index').first()