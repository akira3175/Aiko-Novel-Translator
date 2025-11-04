import yaml
import re
from core.models import Novel, Volume, Chapter, Segment


def import_yaml_file(uploaded_file, novel_title="Chưa đặt tên"):
    """
    Nhập YAML theo dạng:
    - id: Volume_1_Chapter_2_Segment_3
      title: ...
      content: ...
      translation: ...
    """
    data = yaml.safe_load(uploaded_file.read())
    novel, _ = Novel.objects.create(title=novel_title)

    imported_segments = 0
    imported_chapters = 0

    for item in data:
        id_ = item.get("id", "")
        if not id_:
            continue

        # ✅ Tách volume / chapter / segment
        match = re.match(r"Volume_(\d+)_Chapter_(\d+)(?:_Segment_(\d+))?", id_)
        if not match:
            continue
        vol_idx, chap_idx, seg_idx = match.groups()
        vol_idx, chap_idx = int(vol_idx), int(chap_idx)
        seg_idx = int(seg_idx) if seg_idx else None

        # ✅ Tạo hoặc lấy Volume
        volume, _ = Volume.objects.get_or_create(
            novel=novel, index=vol_idx,
            defaults={"title": f"Tập {vol_idx}"}
        )

        # ✅ Tạo hoặc lấy Chapter
        chapter, _ = Chapter.objects.get_or_create(
            volume=volume, index=chap_idx,
            defaults={
                "title": item.get("title", ""),
                "title_translation": item.get("title_translation", ""),
                "content_raw": item.get("content", ""),
                "translation": item.get("translation", "")
            }
        )

        # ✅ Nếu có Segment (chia nhỏ)
        if seg_idx is not None:
            Segment.objects.update_or_create(
                chapter=chapter,
                index=seg_idx,
                defaults={
                    "content_raw": item.get("content", ""),
                    "translation": item.get("translation", "")
                }
            )
            imported_segments += 1
        else:
            imported_chapters += 1

    return {
        "chapters": imported_chapters,
        "segments": imported_segments,
    }
