"""
Django management command để tạo glossary từ command line
Usage: python manage.py generate_glossary --novel-id 1
"""
from django.core.management.base import BaseCommand, CommandError
from core.models import Novel
from core.utils.glossary_generator import GlossaryGenerator


class Command(BaseCommand):
    help = 'Tạo glossary tự động từ chapters của novel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--novel-id',
            type=int,
            required=True,
            help='ID của novel cần tạo glossary'
        )
        parser.add_argument(
            '--from-start',
            action='store_true',
            help='Bắt đầu từ đầu, không dùng checkpoint'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=20000,
            help='Số từ tối đa mỗi batch (default: 20000)'
        )

    def handle(self, *args, **options):
        novel_id = options['novel_id']
        from_checkpoint = not options['from_start']
        
        try:
            novel = Novel.objects.get(pk=novel_id)
        except Novel.DoesNotExist:
            raise CommandError(f'Novel với ID {novel_id} không tồn tại')
        
        self.stdout.write(self.style.SUCCESS(f'📚 Novel: {novel.title}'))
        
        # Khởi tạo generator
        generator = GlossaryGenerator(novel)
        generator.MAX_WORDS_PER_BATCH = options['batch_size']
        
        if from_checkpoint:
            checkpoint = generator.get_checkpoint()
            self.stdout.write(f'📍 Tiếp tục từ checkpoint: Chapter {checkpoint}')
        else:
            self.stdout.write('🔄 Bắt đầu từ đầu (ignore checkpoint)')
        
        # Chạy generation
        try:
            summary = generator.generate(start_from_checkpoint=from_checkpoint)
            
            self.stdout.write(self.style.SUCCESS('\n🎉 Hoàn tất!'))
            self.stdout.write(f'📊 Tổng kết:')
            self.stdout.write(f'   - Batches: {summary["total_batches"]}')
            self.stdout.write(f'   - Chapters: {summary["processed_chapters"]}')
            self.stdout.write(f'   - Terms mới: {summary["new_terms"]}')
            self.stdout.write(f'   - Tổng terms: {summary["total_terms"]}')
            self.stdout.write(f'   - Checkpoint: {summary["checkpoint"]}')
            
        except Exception as e:
            raise CommandError(f'Lỗi khi tạo glossary: {str(e)}')