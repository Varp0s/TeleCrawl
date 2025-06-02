from django.core.management.base import BaseCommand
from crawler.models import MessageKeyword

class Command(BaseCommand):
    help = 'Populate default keywords'
    def handle(self, *args, **options):
        MessageKeyword.populate_default_keywords()
        keywords = MessageKeyword.objects.all()
        self.stdout.write(f"Total {keywords.count()} keywords added:")
        for kw in keywords:
            status = "Active" if kw.is_active else "Inactive"
            self.stdout.write(f"- {kw.keyword} ({kw.get_keyword_type_display()}) - {status}")
        self.stdout.write(
            self.style.SUCCESS('Keywords successfully loaded!')
        )
