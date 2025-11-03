from django.db import models
from django.utils import timezone


class Novel(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=8, default='zh')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    
    def to_yaml_dict(self):
        """Export novel data to YAML-compatible dict"""
        segments_data = []
        
        for volume in self.volumes.all().order_by('index'):
            for chapter in volume.chapters.all().order_by('index'):
                for segment in chapter.segments.all().order_by('index'):
                    segments_data.append({
                        'id': f'Volume_{volume.index}_Chapter_{chapter.index}_Segment_{segment.index}',
                        'title': chapter.title,
                        'content': segment.content_raw,
                        'title_translation': chapter.title_translation or '',
                        'translation': segment.translation or '',
                    })
        
        return segments_data


class Volume(models.Model):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='volumes')
    index = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('novel', 'index')
        ordering = ['index']

    def __str__(self):
        return f"{self.novel.title} - Vol {self.index}"


class Chapter(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, related_name='chapters')
    index = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=512, blank=True)
    content_raw = models.TextField(blank=True, null=True)
    translation = models.TextField(blank=True, null=True)
    title_translation = models.TextField(blank=True, null=True)
    match_percent = models.FloatField(default=0)
    status = models.CharField(max_length=32, default='imported')
    review = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    foreign_char_warning = models.TextField(
        blank=True, 
        null=True, 
        help_text='Tổng hợp cảnh báo ký tự ngoại ngữ từ tất cả segments'
    )

    class Meta:
        unique_together = ('volume', 'index')
        ordering = ['index']

    def __str__(self):
        return f"Vol{self.volume.index}-Chap{self.index}"


class Segment(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='segments')
    index = models.PositiveIntegerField(default=1)
    content_raw = models.TextField(blank=True)
    translation = models.TextField(blank=True, null=True)
    match_percent = models.FloatField(default=0)
    review = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    foreign_char_warning = models.TextField(
        blank=True, 
        null=True, 
        help_text='Cảnh báo ký tự ngoại ngữ trong bản dịch segment này'
    )

    class Meta:
        unique_together = ('chapter', 'index')
        ordering = ['index']

    def __str__(self):
        return f"{self.chapter} - Seg{self.index}"


class Glossary(models.Model):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='glossaries')
    term_cn = models.CharField(max_length=128)
    term_vi = models.CharField(max_length=128)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('novel', 'term_cn')

    def __str__(self):
        return f"{self.term_cn} = {self.term_vi}"


class APIKey(models.Model):
    """Quản lý Gemini API Keys"""
    
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic Claude'),
    ]
    
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='gemini')
    key = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=100, blank=True, help_text="Tên gợi nhớ, VD: Key 1, Key Production")
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0, help_text="Số lần sử dụng")
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
    
    def __str__(self):
        masked_key = f"{self.key[:8]}...{self.key[-4:]}" if len(self.key) > 12 else "***"
        return f"{self.name or self.provider} ({masked_key})"
    
    def mark_used(self):
        """Đánh dấu key đã được sử dụng"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])