📋 Mục lục

Tính năng chính
Công nghệ sử dụng
Cài đặt
Cấu trúc dự án
Hướng dẫn sử dụng
API Endpoints
Workflow dịch thuật
Database Schema
Troubleshooting


✨ Tính năng chính
1. Quản lý Novel

✅ Tạo/sửa/xóa Novel, Volume, Chapter
✅ Import/Export YAML (định dạng chuẩn với segments)
✅ Hỗ trợ nhiều ngôn ngữ: Trung, Anh, Nhật, Hàn
✅ Tùy chỉnh phong cách dịch cho từng novel

2. Dịch thuật thông minh

🤖 Dịch tự động bằng Gemini API (gemini-2.5-pro)
📊 Chia chapter thành segments ~3000 từ để tối ưu context
📖 Tham khảo chapters trước để giữ nhất quán
🔄 Dịch lại chapter/segment khi cần
✨ Hỗ trợ phong cách dịch tùy chỉnh (cổ trang, hiện đại, v.v.)

3. Glossary tự động

🧠 Tạo glossary tự động từ nội dung (tên riêng, thuật ngữ)
💾 Checkpoint system - tiếp tục từ nơi dừng lại
🔍 Tìm kiếm, chỉnh sửa inline
📤 Export/Import TXT

4. Phát hiện lỗi

🚨 Foreign Character Detector - cảnh báo ký tự Hán/Nhật/Hàn/Thái trong bản dịch
🎨 Highlight ký tự ngoại ngữ trực quan
⚠️ Cảnh báo theo mức độ nghiêm trọng (low/medium/high)

5. Review chất lượng

🧐 Review AI tự động cho điểm 0-100%
📈 Thống kê chất lượng dịch theo chapter/volume/novel
📝 Nhận xét chi tiết từ AI

6. API Key Management

🔑 Quản lý nhiều Gemini API keys trong database
🔄 Auto-rotation mỗi 1 tiếng để tránh rate limit
📊 Theo dõi usage count và last used time


🛠 Công nghệ sử dụng

Backend: Django 5.2+
Database: SQLite (có thể chuyển sang PostgreSQL)
AI Provider: Google Gemini API (2.5-pro & 2.5-flash)
Cache: Django Database Cache
Frontend: HTML/CSS/JavaScript (vanilla)
Data Format: YAML


📦 Cài đặt
1. Clone repository
bashgit clone <your-repo-url>
cd novel_translator
2. Tạo virtual environment
bashpython -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
3. Cài đặt dependencies
bashpip install -r requirements.txt
4. Migrate database
bashpython manage.py migrate
python manage.py createcachetable  # Tạo cache table cho key rotation
5. Thêm Gemini API Keys
bashpython manage.py shell
pythonfrom core.models import APIKey

# Thêm key đầu tiên
APIKey.objects.create(
    provider='gemini',
    key='YOUR_GEMINI_API_KEY_1',
    name='Key 1',
    is_active=True
)

# Thêm key thứ hai (optional, để rotation)
APIKey.objects.create(
    provider='gemini',
    key='YOUR_GEMINI_API_KEY_2',
    name='Key 2',
    is_active=True
)
6. Chạy server
bashpython manage.py runserver
```

Truy cập: `http://localhost:8000`

---

## 📁 Cấu trúc dự án
```
novel_translator/
├── core/
│   ├── models.py              # Novel, Volume, Chapter, Segment, Glossary, APIKey
│   ├── views.py               # Dashboard, CRUD, Translation, Review views
│   ├── urls.py                # URL routing
│   ├── admin.py               # Django admin interface
│   ├── forms.py               # Upload YAML form
│   ├── templates/
│   │   └── core/
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── novel_detail.html
│   │       ├── volume_detail.html
│   │       ├── chapter_detail.html
│   │       ├── glossary_list.html
│   │       └── ... (CRUD forms)
│   ├── utils/
│   │   ├── gemini_client.py            # Gemini API + Key Rotation
│   │   ├── ai_client.py                # AI abstraction layer
│   │   ├── segment_processor.py        # Chia segments ~3000 từ
│   │   ├── glossary_generator.py       # Tạo glossary tự động
│   │   ├── foreign_char_detector.py    # Phát hiện ký tự ngoại ngữ
│   │   └── yaml_io.py                  # Import/Export YAML
│   └── templatetags/
│       └── custom_filters.py           # Template filters
├── novel_translator/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md

📖 Hướng dẫn sử dụng
1. Import Novel từ YAML
Format YAML:
yaml- id: Volume_1_Chapter_1_Segment_1
  title: "第一章"
  content: "原文内容..."
  title_translation: "Chương 1"
  translation: "Bản dịch..."

- id: Volume_1_Chapter_1_Segment_2
  title: "第一章"
  content: "..."
  translation: ""
```

**Các bước:**
1. Vào **Import YAML**
2. Chọn file `.yaml` hoặc `.yml`
3. Hệ thống tự động tạo Novel → Volume → Chapter → Segment

### 2. Tạo Novel thủ công

1. Dashboard → **Tạo Novel Mới**
2. Nhập: Tên truyện, Tác giả, Mô tả, Ngôn ngữ, **Phong cách dịch**
3. Tạo Volume → Tạo Chapter → Nhập content_raw

### 3. Dịch Chapter

**Workflow:**
```
Chapter (content_raw) 
  → Chia Segments (~3000 từ)
  → Dịch từng Segment (với context + glossary + style)
  → Merge thành chapter.translation
```

**Các bước:**
1. Mở Chapter Detail
2. Nhấn **"Chia Segments"** (nếu chưa có)
3. Nhấn **"Dịch Toàn Bộ"** hoặc dịch từng segment
4. Hệ thống tự động:
   - Lấy glossary từ novel
   - Lấy 3 chapters trước làm context
   - Áp dụng phong cách dịch (nếu có)
   - Phát hiện ký tự ngoại ngữ

### 4. Tạo Glossary tự động

1. Vào Novel Detail → Tab **Glossary**
2. Nhấn **"Tạo Tự Động"**
3. Hệ thống:
   - Chia chapters thành batches ~80k từ
   - Gọi Gemini để trích xuất tên riêng, thuật ngữ
   - Lưu checkpoint để tiếp tục lần sau
4. Có thể **Reset Checkpoint** để xử lý lại từ đầu

**Format Glossary:**
```
李明 = Li Minh
剑圣 = Kiếm Thánh
天元城 = Thiên Nguyên Thành
```

### 5. Phát hiện lỗi ký tự ngoại ngữ

- Sau khi dịch, hệ thống **tự động phát hiện** ký tự Hán/Nhật/Hàn/Thái
- Hiển thị **cảnh báo đỏ** ở đầu chapter
- Nhấn **"🔍 Highlight ký tự lạ"** để xem trực quan
- Dùng **"Dịch lại"** để fix

### 6. Review chất lượng

1. Chapter Detail → **"Review AI"**
2. Hệ thống:
   - Review từng segment (so sánh với bản gốc)
   - Cho điểm 0-100% (với phạt -20% nếu còn ký tự ngoại ngữ)
   - Hiển thị nhận xét

---

## 🔌 API Endpoints

### Novel & Navigation
```
GET  /                                     # Dashboard
GET  /novel/<novel_id>/                    # Novel detail
GET  /volume/<volume_id>/                  # Volume detail
GET  /chapter/<chapter_id>/                # Chapter detail
```

### Translation
```
POST /chapter/<chapter_id>/prepare/        # Chia segments
POST /chapter/<chapter_id>/translate/      # Dịch toàn bộ chapter
POST /chapter/<chapter_id>/retranslate/    # Dịch lại chapter
POST /segment/<segment_id>/translate/      # Dịch 1 segment
POST /segment/<segment_id>/retranslate/    # Dịch lại segment
```

### Translation Style
```
POST /novel/<novel_id>/update-translation-style/  # Cập nhật phong cách dịch
```

### Glossary
```
GET  /novel/<novel_id>/glossary/                   # Xem glossary (with pagination)
GET  /novel/<novel_id>/glossary/list/              # API list (AJAX)
POST /novel/<novel_id>/glossary/generate/          # Tạo tự động
POST /novel/<novel_id>/glossary/reset/             # Reset checkpoint
POST /novel/<novel_id>/glossary/add/               # Thêm term
POST /novel/<novel_id>/glossary/update/<term_id>/  # Cập nhật term
POST /glossary/<term_id>/delete/                   # Xóa term
```

### Review
```
POST /chapter/<chapter_id>/review/         # Review chapter
GET  /novel/<novel_id>/review/stats/       # Thống kê review
POST /novel/<novel_id>/review/all/         # Review tất cả chapters
POST /volume/<volume_id>/review/           # Review volume
```

### Foreign Character Detection
```
GET  /segment/<segment_id>/highlight-foreign/  # Lấy bản highlight
```

### Import/Export
```
GET  /import_yaml/                             # Import YAML form
POST /import_yaml/                             # Process import
GET  /novel/<novel_id>/export/yaml/            # Export novel
GET  /novel/<novel_id>/glossary/export/        # Export glossary TXT
POST /novel/<novel_id>/glossary/import/        # Import glossary TXT
```

### CRUD Endpoints
```
# Novel
POST /novel/create/
POST /novel/<novel_id>/edit/
POST /novel/<novel_id>/delete/

# Volume
POST /novel/<novel_id>/volume/create/
POST /volume/<volume_id>/edit/
POST /volume/<volume_id>/delete/

# Chapter
POST /volume/<volume_id>/chapter/create/
POST /chapter/<chapter_id>/edit/
POST /chapter/<chapter_id>/delete/

🔄 Workflow dịch thuật
mermaidgraph TD
    A[Chapter với content_raw] --> B{Có segments?}
    B -->|Không| C[Chia segments ~3000 từ]
    B -->|Có| D[Lấy Glossary]
    C --> D
    D --> E[Lấy 3 chapters trước]
    E --> F[Lấy phong cách dịch]
    F --> G[Dịch từng segment]
    G --> H[Phát hiện ký tự ngoại ngữ]
    H --> I{Có ký tự lạ?}
    I -->|Có| J[Lưu warning vào segment]
    I -->|Không| K[Lưu translation]
    J --> K
    K --> L{Đã dịch hết?}
    L -->|Chưa| G
    L -->|Rồi| M[Merge thành chapter.translation]
    M --> N[Tổng hợp warnings vào chapter]

🔑 API Key Rotation
Cơ chế hoạt động:

Database Cache: Lưu trữ current_key_index và last_switch_time
Auto-rotation: Sau mỗi 1 tiếng (3600 giây), tự động chuyển sang key tiếp theo
Round-robin: new_index = (current_index + 1) % total_keys
Usage tracking: Mỗi lần dùng key, tăng usage_count và cập nhật last_used

Sử dụng:
pythonfrom core.utils.gemini_client import get_gemini_client

# Tự động lấy key hiện tại (và rotate nếu đã quá 1 tiếng)
client = get_gemini_client()

# Hoặc dùng manager trực tiếp
from core.utils.gemini_client import GeminiClientManager
manager = GeminiClientManager()
client, key_id = manager.get_client()

# Force rotate ngay (nếu bị rate limit)
manager.force_rotate()

🎨 Foreign Character Detector
Phát hiện:

🇨🇳 Chữ Hán: [\u4e00-\u9fff]
🇰🇷 Chữ Hàn: [\uac00-\ud7af]
🇯🇵 Chữ Nhật: [\u3040-\u30ff]
🇹🇭 Chữ Thái: [\u0e00-\u0e7f]

Severity Levels:

low: < 5 ký tự hoặc < 5% văn bản
medium: 5-10% hoặc 5+ ký tự
high: > 10% văn bản

API:
pythonfrom core.utils.foreign_char_detector import ForeignCharDetector

# Phát hiện
result = ForeignCharDetector.detect(text)
# → {'has_foreign': bool, 'chinese_count': int, 'warning_message': str, ...}

# Highlight HTML
highlighted = ForeignCharDetector.highlight_html(text)

# Kiểm tra có nên cảnh báo
should_warn = ForeignCharDetector.should_warn(text, threshold=3)

🐛 Troubleshooting
1. Lỗi "No API key found"
Nguyên nhân: Chưa thêm Gemini API key vào database
Giải pháp:
bashpython manage.py shell
pythonfrom core.models import APIKey
APIKey.objects.create(provider='gemini', key='YOUR_KEY', is_active=True)
2. Lỗi "Rate limit exceeded"
Nguyên nhân: Gemini API bị rate limit
Giải pháp:

Thêm nhiều API keys để rotation tự động
Giảm tần suất request
Nâng cấp Gemini tier

3. Segment quá dài (> 3000 từ)
Nguyên nhân: Câu văn quá dài không thể chia nhỏ
Giải pháp: SegmentProcessor tự động xử lý - câu quá dài sẽ tách riêng thành 1 segment
4. Glossary không được áp dụng
Nguyên nhân:

Glossary chưa được tạo
Term không khớp với nội dung

Giải pháp:

Chạy "Tạo Tự Động" glossary
Kiểm tra term_cn có chính xác không

5. Foreign char detector không hoạt động
Nguyên nhân: Unicode range không đúng
Giải pháp: Kiểm tra lại pattern trong foreign_char_detector.py
6. Cache không hoạt động (key rotation fail)
Nguyên nhân: Chưa tạo cache table
Giải pháp:
bashpython manage.py createcachetable
```

---

## 📝 Phong cách dịch (Translation Style)

Mỗi novel có thể có hướng dẫn phong cách dịch riêng, ví dụ:
```
Văn phong cổ trang, trang trọng
Giữ nguyên xưng hô: Tiểu tử, Lão phu, Ta, Ngươi
Tên riêng dùng Hán Việt
Thuật ngữ võ công giữ nguyên: Thiên Tàm Công, Cửu Dương Thần Công
```

AI sẽ tuân theo các hướng dẫn này khi dịch.

---

📄 License
MIT License

👨‍💻 Author
Akira

🙏 Credits

Gemini API by Google
Django Framework
PyYAML


Happy Translating! 📚✨