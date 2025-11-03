"""
Quản lý Gemini API client với rotation key từ database
"""
import time
import re
from typing import Optional
from google import genai
from google.genai import types
from django.core.cache import cache
from django.utils import timezone
from ..models import APIKey


class GeminiClientManager:
    """Quản lý Gemini client với rotation API key mỗi 1 tiếng từ database"""
    
    CACHE_KEY_INDEX = 'gemini_current_key_index'
    CACHE_KEY_TIME = 'gemini_last_switch_time'
    ROTATION_INTERVAL = 3600  # 1 tiếng (3600 giây)
    
    def __init__(self):
        self.api_keys = self._load_api_keys_from_db()
        if not self.api_keys:
            raise ValueError("⚠️ Không có API key nào active trong database!")
    
    def _load_api_keys_from_db(self) -> list:
        """Load API keys từ database (chỉ lấy key active)"""
        keys = APIKey.objects.filter(
            provider='gemini',
            is_active=True
        ).order_by('id').values_list('id', 'key')
        
        return [(key_id, key) for key_id, key in keys]
    
    def _get_current_index(self) -> int:
        """Lấy index hiện tại từ cache"""
        index = cache.get(self.CACHE_KEY_INDEX)
        if index is None:
            cache.set(self.CACHE_KEY_INDEX, 0, timeout=None)
            return 0
        return int(index)
    
    def _get_last_switch_time(self) -> float:
        """Lấy thời gian switch cuối từ cache"""
        last_time = cache.get(self.CACHE_KEY_TIME)
        if last_time is None:
            now = time.time()
            cache.set(self.CACHE_KEY_TIME, now, timeout=None)
            return now
        return float(last_time)
    
    def _rotate_key(self):
        """Đổi sang API key tiếp theo"""
        current_index = self._get_current_index()
        new_index = (current_index + 1) % len(self.api_keys)
        cache.set(self.CACHE_KEY_INDEX, new_index, timeout=None)
        cache.set(self.CACHE_KEY_TIME, time.time(), timeout=None)
        print(f"🔄 Đã đổi API key sang key số {new_index + 1}/{len(self.api_keys)}")
    
    def _mark_key_used(self, key_id: int):
        """Cập nhật usage count cho key"""
        try:
            api_key = APIKey.objects.get(id=key_id)
            api_key.mark_used()
        except APIKey.DoesNotExist:
            pass
    
    def get_client(self) -> tuple[genai.Client, int]:
        """
        Trả về Gemini client với API key hiện tại
        Tự động rotate sau mỗi 1 tiếng
        
        Returns:
            Tuple (client, key_id)
        """
        now = time.time()
        last_switch = self._get_last_switch_time()
        
        # Kiểm tra xem đã đủ 1 tiếng chưa
        if now - last_switch >= self.ROTATION_INTERVAL:
            self._rotate_key()
        
        current_index = self._get_current_index()
        key_id, api_key = self.api_keys[current_index]
        
        # Đánh dấu key đã được sử dụng
        self._mark_key_used(key_id)
        
        return genai.Client(api_key=api_key), key_id
    
    def force_rotate(self):
        """Ép buộc đổi key ngay lập tức (dùng khi bị rate limit)"""
        self._rotate_key()
        return self.get_client()


# Singleton instance
_manager = None

def get_gemini_client() -> genai.Client:
    """
    Helper function để lấy Gemini client
    Usage: client = get_gemini_client()
    """
    global _manager
    if _manager is None:
        _manager = GeminiClientManager()
    client, _ = _manager.get_client()
    return client


def translate_with_gemini(
    source_text: str,
    glossary_context: str = "",
    pre_chapters: str = "",
    model: str = "gemini-2.5-pro"
) -> tuple[str, str]:
    """
    Dịch văn bản bằng Gemini
    
    Args:
        source_text: Văn bản gốc cần dịch
        glossary_context: Bảng thuật ngữ
        pre_chapters: Các chương đã dịch trước đó
        model: Model Gemini sử dụng
    
    Returns:
        Tuple (title_translation, content_translation)
    """
    client = get_gemini_client()
    
    prompt = f"""
# 🌸 Vai trò
Bạn là một **biên tập viên dịch thuật tài hoa**, với trái tim dành trọn cho từng con chữ.  
Hãy gìn giữ nguyên vẹn **tinh hoa của từng dòng thơ, từng câu văn** — như những báu vật thiêng liêng của tác phẩm gốc.  
Sau đó, bằng bàn tay khéo léo và hơi thở của nghệ sĩ, **hãy mài giũa ngôn từ cho long lanh hơn**, khơi dậy linh hồn sâu lắng,  
để văn bản không chỉ truyền tải mà còn **lay động trái tim người đọc**, như dòng sông quê hương êm đềm mà cuốn cuộn sóng ngầm cảm xúc.

---

# 🎯 Nhiệm vụ
Dịch **cả tiêu đề (title)** lẫn **nội dung (content)** sang **tiếng Việt**,  
giữ **văn phong mượt mà, nhất quán**.  
Đọc **các chương trước** để tham khảo xương hồi và ngữ cảnh để chương này được mạch lạc.  
Dịch **đúng theo bảng thuật ngữ tên riêng bên dưới**.

---

## 📜 Dữ liệu đầu vào

### Các chương trước (tham khảo ngữ cảnh):
{pre_chapters if pre_chapters else "Không có"}

### Dịch đúng theo bảng thuật ngữ tên riêng:
{glossary_context if glossary_context else "Không có glossary"}

### Nội dung gốc cần dịch:
{source_text}

---

# ⚠️ Yêu cầu xuất kết quả
Chỉ xuất đúng theo định dạng sau, **không thêm bất kỳ lời giải thích nào khác**:

###TITLE###
<tiêu đề dịch>

###CONTENT###
<nội dung dịch>
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                ]
            )
        )
        
        text = response.text.strip()
        
        # Parse kết quả
        title_trans, content_trans = "", ""
        if "###TITLE###" in text and "###CONTENT###" in text:
            parts = text.split("###CONTENT###")
            title_part = parts[0].replace("###TITLE###", "").strip()
            content_part = parts[1].strip()
            title_trans = title_part
            content_trans = content_part
        else:
            # Fallback: nếu không có format chuẩn, lấy toàn bộ text
            content_trans = text
        
        return title_trans, content_trans
        
    except Exception as e:
        raise Exception(f"Lỗi khi dịch với Gemini: {str(e)}")


def review_with_gemini(
    source_text: str,
    translated_text: str,
    model: str = "gemini-2.5-flash"
) -> tuple[float, str]:
    """
    Review chất lượng bản dịch bằng Gemini
    
    Args:
        source_text: Văn bản gốc
        translated_text: Bản dịch
        model: Model Gemini sử dụng
    
    Returns:
        Tuple (score: float 0-100, review_report: str)
    """
    client = get_gemini_client()
    
    prompt = f"""
Bạn là biên tập viên kiểm định chất lượng bản dịch song ngữ Trung–Việt.

Nhiệm vụ:
1. So sánh bản gốc và bản dịch để đánh giá mức độ trung thành về nội dung, ngữ khí.
2. Đặc biệt chú ý giữ nguyên các tên riêng (nhân vật, địa danh, chiêu thức). Lỗi sai tên riêng là lỗi nghiêm trọng.
3. Đánh giá và cho điểm phần trăm độ khớp (0-100%).
4. Nếu còn xuất hiện bất kỳ ký tự thuộc các ngôn ngữ khác ngoài ngôn ngữ đích (tiếng Trung, Hàn, Nhật...), trừ 20%.

Yêu cầu định dạng output (chỉ trả về đúng format này):
Độ khớp: xx%
<Nhận xét ngắn gọn từ 3-6 dòng về chất lượng bản dịch. Nếu có lỗi, chỉ ra cụ thể.>

---
原文：
{source_text[:40000]}  

---
译文：
{translated_text[:40000]}
"""
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.OFF,
                    ),
                ]
            )
        )
        
        print(prompt)
        print("⚡ Gemini review response received.", response)
        review_text = response.text.strip()
        
        # Extract score
        match = re.search(r'(\d{1,3}(?:\.\d+)?)\s*%', review_text)
        score = 0.0
        if match:
            try:
                score = float(match.group(1))
                score = min(max(score, 0.0), 100.0)
            except ValueError:
                score = 0.0
        
        return score, review_text
        
    except Exception as e:
        return 0.0, f"Lỗi khi review: {str(e)}"


def fix_translation_with_gemini(
    original_title: str,
    original_content: str,
    translated_title: str,
    translated_content: str,
    glossary_context: str = "",
    model: str = "gemini-2.0-flash"
) -> tuple[str, str]:
    """
    Sửa bản dịch còn sót ký tự ngoại ngữ
    
    Returns:
        Tuple (fixed_title, fixed_content)
    """
    client = get_gemini_client()
    
    prompt = f"""
Bạn là dịch giả tiểu thuyết chuyên nghiệp.
Bản dịch dưới đây vẫn còn sót chữ Hán hoặc các ký tự ngoại ngữ.
Hãy dịch lại thành bản hoàn chỉnh 100% tiếng Việt, giữ nguyên phong cách và nội dung.

Glossary (ưu tiên sử dụng):
{glossary_context if glossary_context else "Không có"}

---
Tiêu đề gốc: {original_title}
Tiêu đề dịch hiện tại: {translated_title}

Nội dung gốc:
{original_content[:40000]}

Nội dung dịch hiện tại:
{translated_content[:40000]}

---
⚠️ Xuất kết quả theo định dạng:

###TITLE###
<tiêu đề dịch hoàn chỉnh>

###CONTENT###
<nội dung dịch hoàn chỉnh>
"""
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        
        text = response.text.strip()
        
        title_new, content_new = translated_title, translated_content
        if "###TITLE###" in text and "###CONTENT###" in text:
            parts = text.split("###CONTENT###")
            title_new = parts[0].replace("###TITLE###", "").strip()
            content_new = parts[1].strip()
        
        return title_new, content_new
        
    except Exception as e:
        print(f"⚠️ Lỗi khi fix translation: {e}")
        return translated_title, translated_content