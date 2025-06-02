from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from crawler.models import TelegramMessage, DeletedMessage
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleans irrelevant messages'
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Delete messages older than this many days (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not delete anything, just show what would be deleted'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_time = timezone.now() - timedelta(days=days)
        irrelevant_messages = TelegramMessage.objects.filter(
            classification='irrelevant',
            timestamp__lt=cutoff_time
        )
        count = irrelevant_messages.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: {count} irrelevant messages will be deleted'
                )
            )
            return
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No irrelevant messages found to delete')
            )
            return
        deleted_records = []
        for message in irrelevant_messages:
            deleted_records.append(
                DeletedMessage(
                    message_id=message.message_id,
                    channel=message.channel,
                    reason='irrelevant'
                )
            )
        DeletedMessage.objects.bulk_create(deleted_records, ignore_conflicts=True)
        deleted_count = irrelevant_messages.delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'{deleted_count} irrelevant messages successfully deleted'
            )
        )
        logger.info(f'Irrelevant message cleanup completed: {deleted_count} messages deleted')
