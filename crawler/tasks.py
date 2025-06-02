from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from crawler.models import TelegramMessage, DeletedMessage
import logging

logger = logging.getLogger(__name__)

@shared_task
def clean_irrelevant_messages(days=1):
    cutoff_time = timezone.now() - timedelta(days=days)
    irrelevant_messages = TelegramMessage.objects.filter(
        classification='irrelevant',
        timestamp__lt=cutoff_time
    )
    count = irrelevant_messages.count()
    if count == 0:
        logger.info('No irrelevant messages found to delete')
        return f'No irrelevant messages found to delete'
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
    logger.info(f'Irrelevant message cleanup completed: {deleted_count} messages deleted')
    return f'{deleted_count} irrelevant messages successfully deleted'

@shared_task
def archive_github_urls(limit=10):
    """Archive GitHub URLs"""
    from crawler.models import ArchivedGithubUrl
    from crawler.utils.web_archiver import WebArchiver
    from asgiref.sync import sync_to_async
    import asyncio
    
    messages = TelegramMessage.objects.filter(
        classification='relevant',
        extracted_github_url__isnull=False
    ).exclude(
        id__in=ArchivedGithubUrl.objects.values_list('message_id', flat=True)
    )[:limit]
    
    if not messages:
        logger.info("No GitHub URLs found to process")
        return "No GitHub URLs found to process"
    archiver = WebArchiver()
    processed_count = 0
    success_count = 0
    
    async def process_message(message):
        nonlocal processed_count, success_count
        github_urls = message.extracted_github_url or []
        for url in github_urls:
            clean_url = url.split(")")[0] if ")" in url else url
            try:
                result = await archiver.archive_url(clean_url)
                await sync_to_async(ArchivedGithubUrl.objects.create)(
                    url=clean_url,
                    message=message,
                    is_archived=result['success'],
                    archive_url=result.get('archive_url'),
                    error_message=result.get('error')
                )              
                processed_count += 1
                if result['success']:
                    success_count += 1
                    logger.info(f"URL successfully archived: {clean_url}")
                else:
                    logger.warning(f"URL could not be archived: {clean_url} - {result.get('error')}")
                    
            except Exception as e:
                await sync_to_async(ArchivedGithubUrl.objects.create)(
                    url=clean_url,
                    message=message,
                    is_archived=False,
                    error_message=str(e)
                )
                processed_count += 1
                logger.error(f"Error processing URL: {clean_url} - {e}")
    
    async def run_archiving():
        tasks = [process_message(message) for message in messages]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    asyncio.run(run_archiving())
    result_message = f'{processed_count} URLs processed, {success_count} successful'
    logger.info(result_message)
    return result_message
