from django.core.management.base import BaseCommand
from core.models import Novel, Volume, Chapter
from core.utils.yaml_io import import_yaml_file

class Command(BaseCommand):
    help = "Import truyện từ file YAML dạng flat list (theo id Volume_x_Chapter_y)."

    def add_arguments(self, parser):
        parser.add_argument('yaml_path', type=str, help='Đường dẫn đến file YAML')

    def handle(self, *args, **options):
        yaml_path = options['yaml_path']
        data = import_yaml_file(yaml_path)

        novel, _ = Novel.objects.get_or_create(title=data['title'])

        for vol_data in data['volumes']:
            volume, _ = Volume.objects.get_or_create(
                novel=novel,
                title=vol_data['title']
            )

            for chap_data in vol_data['chapters']:
                Chapter.objects.update_or_create(
                    volume=volume,
                    title=chap_data['title_translation'] or chap_data['title'],
                    defaults={
                        'content_raw': chap_data['content_raw'],
                        'translation': chap_data.get('translation', ''),
                        'status': 'imported'
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"✅ Import thành công: {novel.title}"))
