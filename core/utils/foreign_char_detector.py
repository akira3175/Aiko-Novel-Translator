"""
Phát hiện ký tự ngoại ngữ (Hán, Hàn, Nhật, Thái) trong văn bản tiếng Việt
Được tích hợp vào quá trình dịch để cảnh báo người dùng
"""
import re
from typing import Dict, List, Tuple


class ForeignCharDetector:
    """Phát hiện và thống kê ký tự ngoại ngữ trong bản dịch"""
    
    # Unicode ranges cho các ngôn ngữ
    CHINESE_PATTERN = r'[\u4e00-\u9fff\u3400-\u4dbf]'  # Hán tự
    KOREAN_PATTERN = r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]'  # Chữ Hàn
    JAPANESE_PATTERN = r'[\u3040-\u309f\u30a0-\u30ff]'  # Hiragana, Katakana
    THAI_PATTERN = r'[\u0e00-\u0e7f]'  # Chữ Thái
    
    @classmethod
    def detect(cls, text: str) -> Dict[str, any]:
        """
        Phát hiện ký tự ngoại ngữ trong văn bản
        
        Returns:
            Dict với thông tin chi tiết về ký tự ngoại ngữ
        """
        if not text:
            return cls._empty_result()
        
        chinese = list(set(re.findall(cls.CHINESE_PATTERN, text)))
        korean = list(set(re.findall(cls.KOREAN_PATTERN, text)))
        japanese = list(set(re.findall(cls.JAPANESE_PATTERN, text)))
        thai = list(set(re.findall(cls.THAI_PATTERN, text)))
        
        total = len(chinese) + len(korean) + len(japanese) + len(thai)
        
        # Tạo cảnh báo
        warnings = []
        if chinese:
            sample = ' '.join(chinese[:10])
            warnings.append(f"🇨🇳 {len(chinese)} chữ Hán: {sample}")
        if korean:
            sample = ' '.join(korean[:10])
            warnings.append(f"🇰🇷 {len(korean)} chữ Hàn: {sample}")
        if japanese:
            sample = ' '.join(japanese[:10])
            warnings.append(f"🇯🇵 {len(japanese)} chữ Nhật: {sample}")
        if thai:
            sample = ' '.join(thai[:10])
            warnings.append(f"🇹🇭 {len(thai)} chữ Thái: {sample}")
        
        warning_msg = "\n".join(warnings) if warnings else ""
        severity = cls._calculate_severity(total, len(text))
        
        return {
            'has_foreign': total > 0,
            'chinese_count': len(chinese),
            'korean_count': len(korean),
            'japanese_count': len(japanese),
            'thai_count': len(thai),
            'total_count': total,
            'warning_message': warning_msg,
            'severity': severity,
            'all_chars': chinese + korean + japanese + thai
        }
    
    @classmethod
    def _empty_result(cls) -> Dict:
        """Kết quả rỗng khi không có text"""
        return {
            'has_foreign': False,
            'chinese_count': 0,
            'korean_count': 0,
            'japanese_count': 0,
            'thai_count': 0,
            'total_count': 0,
            'warning_message': '',
            'severity': 'none',
            'all_chars': []
        }
    
    @classmethod
    def _calculate_severity(cls, foreign_count: int, total_length: int) -> str:
        """
        Tính mức độ nghiêm trọng
        Returns: 'none', 'low', 'medium', 'high'
        """
        if foreign_count == 0:
            return 'none'
        
        if total_length == 0:
            return 'high'
        
        ratio = foreign_count / total_length
        
        if ratio > 0.1:  # Trên 10%
            return 'high'
        elif ratio > 0.05:  # 5-10%
            return 'medium'
        elif foreign_count > 5:  # Nhiều hơn 5 ký tự
            return 'medium'
        else:
            return 'low'
    
    @classmethod
    def highlight_html(cls, text: str) -> str:
        """
        Highlight ký tự ngoại ngữ bằng HTML cho hiển thị trên web
        """
        if not text:
            return text
        
        # Highlight Chinese (đỏ)
        text = re.sub(
            cls.CHINESE_PATTERN,
            r'<mark style="background: #fee2e2; color: #991b1b; font-weight: 600;">\g<0></mark>',
            text
        )
        # Highlight Korean (vàng)
        text = re.sub(
            cls.KOREAN_PATTERN,
            r'<mark style="background: #fef3c7; color: #92400e; font-weight: 600;">\g<0></mark>',
            text
        )
        # Highlight Japanese (xanh lá)
        text = re.sub(
            cls.JAPANESE_PATTERN,
            r'<mark style="background: #d1fae5; color: #065f46; font-weight: 600;">\g<0></mark>',
            text
        )
        # Highlight Thai (tím)
        text = re.sub(
            cls.THAI_PATTERN,
            r'<mark style="background: #e9d5ff; color: #6b21a8; font-weight: 600;">\g<0></mark>',
            text
        )
        
        return text
    
    @classmethod
    def should_warn(cls, text: str, threshold: int = 3) -> bool:
        """
        Kiểm tra có nên hiển thị cảnh báo không
        Args:
            threshold: Số ký tự ngoại ngữ tối thiểu để cảnh báo
        """
        result = cls.detect(text)
        return result['total_count'] >= threshold
    
    @classmethod
    def get_warning_badge(cls, severity: str) -> str:
        """Lấy HTML badge cho severity level"""
        badges = {
            'none': '',
            'low': '<span class="badge badge-warning">⚠️ Có ít ký tự ngoại ngữ</span>',
            'medium': '<span class="badge badge-warning">⚠️ Nhiều ký tự ngoại ngữ</span>',
            'high': '<span class="badge badge-danger">🚨 Rất nhiều ký tự ngoại ngữ - Cần dịch lại!</span>'
        }
        return badges.get(severity, '')