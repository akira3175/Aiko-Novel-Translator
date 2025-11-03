"""
Tự động tạo glossary từ nội dung chapters
"""
import re
from typing import List, Dict, Tuple
from django.db import transaction
from ..models import Novel, Chapter, Glossary
from .gemini_client import get_gemini_client
from google.genai import types


class GlossaryGenerator:
    """Tạo glossary tự động từ chapters"""
    
    MAX_WORDS_PER_BATCH = 80000  # Mỗi batch tối đa 20k từ
    
    def __init__(self, novel: Novel):
        self.novel = novel
        self.client = get_gemini_client()
    
    @staticmethod
    def count_words(text: str) -> int:
        """Đếm số từ (ký tự Hán + từ Latin)"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_words = len(re.findall(r'\b\w+\b', text))
        return chinese_chars + other_words
    
    def get_existing_glossary(self) -> str:
        """Lấy glossary hiện có để tham khảo"""
        terms = self.novel.glossaries.all()
        if not terms:
            return ""
        
        lines = [f"{term.term_cn} = {term.term_vi}" for term in terms]
        return "\n".join(lines)
    
    def get_checkpoint(self) -> int:
        """
        Lấy vị trí checkpoint (chapter cuối cùng đã xử lý)
        Lưu trong field description của novel
        """
        # Parse checkpoint từ description (format: "checkpoint:123")
        if self.novel.description:
            match = re.search(r'checkpoint:(\d+)', self.novel.description)
            if match:
                return int(match.group(1))
        return 0
    
    def save_checkpoint(self, chapter_index: int):
        """Lưu checkpoint vào novel description"""
        if not self.novel.description:
            self.novel.description = f"checkpoint:{chapter_index}"
        else:
            # Replace existing checkpoint or append
            if 'checkpoint:' in self.novel.description:
                self.novel.description = re.sub(
                    r'checkpoint:\d+',
                    f'checkpoint:{chapter_index}',
                    self.novel.description
                )
            else:
                self.novel.description += f"\ncheckpoint:{chapter_index}"
        self.novel.save(update_fields=['description'])
    
    def batch_chapters(self, start_chapter: int = 0) -> List[List[Chapter]]:
        """
        Chia chapters thành các batch ~20k từ
        
        Args:
            start_chapter: Index chapter bắt đầu (0-based)
        
        Returns:
            List of chapter batches
        """
        all_chapters = []
        for volume in self.novel.volumes.all().order_by('index'):
            chapters = volume.chapters.filter(
                content_raw__isnull=False
            ).order_by('index')
            all_chapters.extend(chapters)
        
        # Skip đến start_chapter
        all_chapters = all_chapters[start_chapter:]
        
        batches = []
        current_batch = []
        current_word_count = 0
        
        for chapter in all_chapters:
            if not chapter.content_raw:
                continue
            
            chapter_words = self.count_words(chapter.content_raw)
            
            # Nếu thêm chapter này vượt quá limit, lưu batch hiện tại
            if current_word_count + chapter_words > self.MAX_WORDS_PER_BATCH and current_batch:
                batches.append(current_batch)
                current_batch = [chapter]
                current_word_count = chapter_words
            else:
                current_batch.append(chapter)
                current_word_count += chapter_words
        
        # Thêm batch cuối
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def extract_glossary_from_batch(
        self,
        chapters: List[Chapter],
        existing_glossary: str
    ) -> str:
        """Gọi Gemini để trích xuất glossary từ batch chapters"""
        
        # Ghép nội dung chapters
        content = "\n\n".join([
            f"=== {ch.title} ===\n{ch.content_raw}"
            for ch in chapters
            if ch.content_raw
        ])
        
        if not content.strip():
            return ""
        
        prompt = f"""
# 🧙 Vai trò
Bạn là **công cụ hỗ trợ dịch thuật chuyên cho truyện tiểu thuyết**.

---

# 🧾 Nhiệm vụ
Hãy **trích xuất và bổ sung BẢNG THUẬT NGỮ (Glossary)** từ văn bản sau:

---
{content[:75000]}  
(... và các chương tiếp theo)
---

---

# ⚙️ Yêu cầu chi tiết

1. **Trích xuất** tất cả các:
   - Thuật ngữ đặc biệt
   - Danh hiệu
   - Xưng hô
   - Tên riêng nhân vật
   - Địa danh
   - Kỹ năng, chiêu thức
   trong đoạn văn ở trên.

2. **Bỏ qua** những từ:
   - Phổ thông, vật dụng đời thường (ví dụ: 手机, 椅子, 图书馆…)
   - Nghề nghiệp chung
   - Từ đã xuất hiện trong glossary cũ bên dưới

3. **Chuyển đổi và dịch:**
   - Nếu là **tên riêng ngoại lai** (phiên âm Trung, ví dụ: 卡洛斯, 莉亚, 亚瑟), 
     hãy **chuyển về dạng La-tinh gốc** → `卡洛斯 = Carlos`
   - Nếu là **thuật ngữ, danh hiệu, địa danh**, hãy **dịch sang tiếng Việt tự nhiên**.
   - Giữ nhất quán với glossary cũ

---

## 📜 Glossary hiện có (KHÔNG trích xuất lại):
{existing_glossary if existing_glossary else "Chưa có"}

---

# ⚠️ Định dạng đầu ra
> Không thêm chú thích hay giải thích nào khác.  
> Chỉ xuất **thuần văn bản**, mỗi dòng một mục, theo dạng:
原文 = Dịch

Ví dụ:
李明 = Li Minh
剑圣 = Kiếm Thánh
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"⚠️ Lỗi khi tạo glossary: {e}")
            return ""
    
    def parse_and_save_glossary(self, glossary_text: str) -> int:
        """
        Parse glossary text và lưu vào database
        
        Returns:
            Số terms mới được thêm
        """
        if not glossary_text.strip():
            return 0
        
        lines = glossary_text.strip().split('\n')
        new_count = 0
        
        with transaction.atomic():
            for line in lines:
                line = line.strip()
                if not line or '=' not in line:
                    continue
                
                # Parse: 原文 = Dịch
                parts = line.split('=', 1)
                if len(parts) != 2:
                    continue
                
                term_cn = parts[0].strip()
                term_vi = parts[1].strip()
                
                if not term_cn or not term_vi:
                    continue
                
                # Tạo hoặc update
                _, created = Glossary.objects.get_or_create(
                    novel=self.novel,
                    term_cn=term_cn,
                    defaults={'term_vi': term_vi}
                )
                
                if created:
                    new_count += 1
        
        return new_count
    
    def generate(self, start_from_checkpoint: bool = True) -> Dict:
        """
        Chạy quy trình tạo glossary
        
        Args:
            start_from_checkpoint: Tiếp tục từ checkpoint hay bắt đầu từ đầu
        
        Returns:
            Dict với thông tin tổng kết
        """
        # Lấy checkpoint
        start_chapter = self.get_checkpoint() if start_from_checkpoint else 0
        
        print(f"📚 Bắt đầu tạo glossary cho: {self.novel.title}")
        print(f"📍 Checkpoint: Chapter {start_chapter}")
        
        # Lấy glossary hiện có
        existing_glossary = self.get_existing_glossary()
        print(f"📖 Glossary hiện có: {self.novel.glossaries.count()} terms")
        
        # Chia batches
        batches = self.batch_chapters(start_chapter)
        print(f"📦 Tổng số batches: {len(batches)}")
        
        total_new_terms = 0
        processed_chapters = 0
        
        for i, batch in enumerate(batches, 1):
            print(f"\n▶ Batch {i}/{len(batches)}: {len(batch)} chapters")
            
            # Tính word count
            word_count = sum(self.count_words(ch.content_raw or '') for ch in batch)
            print(f"   📊 ~{word_count:,} từ")
            
            # Trích xuất glossary
            glossary_text = self.extract_glossary_from_batch(batch, existing_glossary)
            
            # Parse và lưu
            new_terms = self.parse_and_save_glossary(glossary_text)
            total_new_terms += new_terms
            
            print(f"   ✅ Thêm {new_terms} terms mới")
            
            # Cập nhật existing glossary
            existing_glossary = self.get_existing_glossary()
            
            # Lưu checkpoint (chapter cuối của batch)
            last_chapter = batch[-1]
            chapter_index = self._get_chapter_global_index(last_chapter)
            self.save_checkpoint(chapter_index)
            processed_chapters += len(batch)
            
            print(f"   💾 Checkpoint saved: Chapter {chapter_index}")
        
        summary = {
            'total_batches': len(batches),
            'processed_chapters': processed_chapters,
            'new_terms': total_new_terms,
            'total_terms': self.novel.glossaries.count(),
            'checkpoint': self.get_checkpoint()
        }
        
        print(f"\n🎉 Hoàn tất!")
        print(f"📊 Tổng kết:")
        print(f"   - Đã xử lý: {processed_chapters} chapters")
        print(f"   - Terms mới: {total_new_terms}")
        print(f"   - Tổng terms: {summary['total_terms']}")
        
        return summary
    
    def _get_chapter_global_index(self, chapter: Chapter) -> int:
        """Lấy index global của chapter (qua tất cả volumes)"""
        count = 0
        for volume in self.novel.volumes.all().order_by('index'):
            if volume.index < chapter.volume.index:
                count += volume.chapters.count()
            elif volume.index == chapter.volume.index:
                count += chapter.index
                break
        return count