
"""
AI Client cho việc dịch và review translation
Sử dụng Gemini API với rotation key tự động
"""
from typing import Tuple
from .gemini_client import translate_with_gemini, review_with_gemini, get_gemini_client


def translate_text(source_text: str, glossary_context: str = "", pre_chapters: str = "") -> str:
    """
    Dịch văn bản từ tiếng Trung sang tiếng Việt bằng Gemini
    
    Args:
        source_text: Văn bản gốc cần dịch
        glossary_context: Glossary thuật ngữ để dịch chính xác
        pre_chapters: Các chương đã dịch trước đó để tham khảo
    
    Returns:
        Bản dịch tiếng Việt (chỉ content, không có title)
    """
    try:
        title_trans, content_trans = translate_with_gemini(
            source_text=source_text,
            glossary_context=glossary_context,
            pre_chapters=pre_chapters
        )
        # Trả về content, hoặc cả title+content nếu cần
        return content_trans if content_trans else title_trans
    except Exception as e:
        raise Exception(f"Lỗi khi dịch: {str(e)}")


def review_translation(source_text: str, translated_text: str) -> Tuple[float, str]:
    """
    Review chất lượng bản dịch và cho điểm bằng Gemini
    
    Args:
        source_text: Văn bản gốc (tiếng Trung)
        translated_text: Bản dịch (tiếng Việt)
    
    Returns:
        Tuple of (score: float 0-100, review_report: str)
    """
    try:
        score, report = review_with_gemini(source_text, translated_text)
        return score, report
    except Exception as e:
        return 0.0, f"Lỗi khi review: {str(e)}"