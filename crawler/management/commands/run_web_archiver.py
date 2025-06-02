from django.core.management.base import BaseCommand
from crawler.models import TelegramMessage, ArchivedGithubUrl
from crawler.utils.web_archiver import WebArchiver
import asyncio
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'GitHub URL\'lerini web.archive.org\'a arşivler'
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Her seferde kaç URL işlensin (varsayılan: 10)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Sadece bir kez çalıştır'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        once = options['once']
        asyncio.run(self.run_archiver(limit, once))

    async def run_archiver(self, limit, once):
        archiver = WebArchiver()
        while True:
            try:
                urls_to_process = await self.get_unprocessed_urls(limit)
                if not urls_to_process:
                    logger.info("İşlenecek yeni URL bulunamadı")
                    if once:
                        break
                    await asyncio.sleep(3600)  
                    continue
                for url_data in urls_to_process:
                    try:
                        await self.process_url(archiver, url_data)
                    except Exception as e:
                        logger.error(f"URL işlenirken hata: {url_data['url']} - {e}")
                if once:
                    break
                await asyncio.sleep(300) 
                
            except Exception as e:
                logger.error(f"Arşivleme döngüsü hatası: {e}")
                if once:
                    break
                await asyncio.sleep(60)

    async def get_unprocessed_urls(self, limit):
        messages = TelegramMessage.objects.filter(
            classification='relevant',
            extracted_github_url__isnull=False
        ).exclude(
            id__in=ArchivedGithubUrl.objects.values_list('message_id', flat=True)
        )[:limit]
        
        urls_to_process = []
        for message in messages:
            github_urls = message.extracted_github_url or []
            for url in github_urls:
                clean_url = url.split(")")[0] if ")" in url else url
                urls_to_process.append({
                    'url': clean_url,
                    'message': message
                })
        return urls_to_process

    async def process_url(self, archiver, url_data):
        url = url_data['url']
        message = url_data['message']
        try:
            archive_result = await archiver.archive_url(url)
            ArchivedGithubUrl.objects.create(
                url=url,
                message=message,
                is_archived=archive_result['success'],
                archive_url=archive_result.get('archive_url'),
                error_message=archive_result.get('error')
            )
            if archive_result['success']:
                logger.info(f"URL başarıyla arşivlendi: {url}")
            else:
                logger.warning(f"URL arşivlenemedi: {url} - {archive_result.get('error')}")
        except Exception as e:
            ArchivedGithubUrl.objects.create(
                url=url,
                message=message,
                is_archived=False,
                error_message=str(e)
            )
            raise
