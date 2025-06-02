from django.core.management.base import BaseCommand
from crawler.models import TelegramChannel, TelegramMessage, ArchivedGithubUrl, CrawlerLog
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Show crawler status'
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Telecrawl status ===\n'))
        channel_count = TelegramChannel.objects.count()
        active_channels = TelegramChannel.objects.filter(is_active=True).count()
        self.stdout.write(f'Total Channels: {channel_count}')
        self.stdout.write(f'Active Channels: {active_channels}\n')
        total_messages = TelegramMessage.objects.count()
        relevant_messages = TelegramMessage.objects.filter(classification='relevant').count()
        last_24h = timezone.now() - timedelta(hours=24)
        recent_messages = TelegramMessage.objects.filter(created_at__gte=last_24h).count()
        self.stdout.write(f'Total Messages: {total_messages}')
        self.stdout.write(f'Relevant Messages: {relevant_messages}')
        self.stdout.write(f'Recent Messages (Last 24h): {recent_messages}\n')
        total_archives = ArchivedGithubUrl.objects.count()
        successful_archives = ArchivedGithubUrl.objects.filter(is_archived=True).count()
        failed_archives = ArchivedGithubUrl.objects.filter(is_archived=False).count()
        self.stdout.write(f'Total Archive Attempts: {total_archives}')
        self.stdout.write(f'Successful Archives: {successful_archives}')
        self.stdout.write(f'Failed Archives: {failed_archives}\n')
        total_logs = CrawlerLog.objects.count()
        error_logs = CrawlerLog.objects.filter(level='ERROR').count()
        warning_logs = CrawlerLog.objects.filter(level='WARNING').count()
        self.stdout.write(f'Total Logs: {total_logs}')
        self.stdout.write(f'Error Logs: {error_logs}')
        self.stdout.write(f'Warning Logs: {warning_logs}\n')
        if total_messages > 0:
            last_message = TelegramMessage.objects.latest('created_at')
            self.stdout.write(f'Last Message: {last_message.created_at} - {last_message.channel.channel_name}')
        if total_logs > 0:
            last_log = CrawlerLog.objects.latest('timestamp')
            self.stdout.write(f'Last Log: {last_log.timestamp} - {last_log.level} - {last_log.message[:50]}...')
        self.stdout.write(self.style.SUCCESS('\n=== STATUS REPORT COMPLETED ==='))
