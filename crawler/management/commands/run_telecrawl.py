from django.core.management.base import BaseCommand
from django.conf import settings
from telethon.sync import TelegramClient
from crawler.models import TelegramChannel, TelegramMessage, DeletedMessage, ArchivedGithubUrl, CrawlerSettings, CrawlerStatus, CrawlerLog
from crawler.utils.message_parser import MessageParser
from crawler.utils.web_archiver import WebArchiver
from asgiref.sync import sync_to_async
import asyncio
import logging
import time
import os

logger = logging.getLogger('crawler.telecrawl')

class Command(BaseCommand):
    help = 'Telegram crawler starting'

    async def log_to_db(self, level, message, module='telecrawl'):
        """Log message to database asynchronously"""
        try:
            await sync_to_async(CrawlerLog.objects.create)(
                level=level,
                module=module,
                message=message
            )
        except Exception as e:
            print(f"Log writing error: {e}")

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='one time run without waiting'
        )

    def handle(self, *args, **options):
        if os.name == 'nt':  
            os.system('chcp 65001 > nul')
        
        self.once = options['once']
        asyncio.run(self.run_crawler())

    async def run_crawler(self):
        api_id = await sync_to_async(CrawlerSettings.get_setting)('TELEGRAM_API_ID')
        api_hash = await sync_to_async(CrawlerSettings.get_setting)('TELEGRAM_API_HASH')
        phone = await sync_to_async(CrawlerSettings.get_setting)('TELEGRAM_PHONE')
        
        if not all([api_id, api_hash, phone]):
            error_msg = "Telegram API settings are missing! Please enter the settings from the web interface."
            logger.error(error_msg)
            await self.log_to_db('ERROR', error_msg)
            return

        # Update crawler status
        crawler_status = await sync_to_async(CrawlerStatus.get_current_status)()
        crawler_status.status = 'starting'
        await sync_to_async(crawler_status.save)()

        await self.log_to_db('INFO', 'Crawler starting...')

        client = TelegramClient(
            'telegramcrawler',
            api_id,
            api_hash
        )
        parser = MessageParser()
        archiver = WebArchiver()

        while True:
            try:
                crawler_status.status = 'running'
                await sync_to_async(crawler_status.save)()
                async with client:
                    channel_count = crawler_status.channels_processed or 0
                    message_count = crawler_status.messages_processed or 0
                    start_msg = f"Crawler starting. Current status - Messages: {message_count}, Channels: {channel_count}"
                    logger.info(start_msg)
                    await self.log_to_db('INFO', start_msg)
                    
                    async for dialog in client.iter_dialogs():
                        if dialog.is_channel:
                            try:
                                channel_msg = f"Processing channel: {dialog.name}"
                                logger.info(channel_msg)
                                await self.log_to_db('INFO', channel_msg)
                                processed_messages = await self.process_channel(client, dialog, parser, archiver)
                                message_count += processed_messages
                                channel_count += 1
                                crawler_status.messages_processed = message_count
                                crawler_status.channels_processed = channel_count
                                crawler_status.last_message = f"Processed channel: {dialog.name} - {processed_messages} messages"
                                await sync_to_async(crawler_status.save)()
                                complete_msg = f"Channel completed: {dialog.name} - {processed_messages} new messages. Total: {message_count} messages, {channel_count} channels"
                                logger.info(complete_msg)
                                await self.log_to_db('INFO', complete_msg)
                            except Exception as e:
                                error_msg = f"Error processing channel: {dialog.name} - {e}"
                                logger.error(error_msg)
                                await self.log_to_db('ERROR', error_msg)
                                crawler_status.error_message = f"Channel error: {dialog.name} - {str(e)}"
                                await sync_to_async(crawler_status.save)()

                complete_final_msg = f"Data collection from all channels completed. Total: {message_count} messages, {channel_count} channels. Waiting for 1 hour..."
                logger.info(complete_final_msg)
                await self.log_to_db('INFO', complete_final_msg)
                
                if self.once:
                    final_msg = f"One-time run completed. Total: {message_count} messages, {channel_count} channels processed."
                    await self.log_to_db('INFO', final_msg)
                    break

                crawler_status.status = 'waiting'
                crawler_status.last_message = f"All channels processed - {message_count} messages, {channel_count} channels. Waiting for 1 hour..."
                await sync_to_async(crawler_status.save)()
                time.sleep(3600)

            except Exception as e:
                error_msg = f"General crawler error: {e}"
                logger.error(error_msg)
                await self.log_to_db('ERROR', error_msg)
                crawler_status.status = 'error'
                crawler_status.error_message = str(e)
                await sync_to_async(crawler_status.save)()
                
                if not self.once:
                    time.sleep(60)
                else:
                    break

    async def process_channel(self, client, dialog, parser, archiver):
        processed_count = 0
        channel, created = await sync_to_async(TelegramChannel.objects.get_or_create)(
            channel_id=dialog.id,
            defaults={
                'channel_name': dialog.name,
                'username': getattr(dialog.entity, 'username', None),
            }
        )
        if created:
            new_channel_msg = f"New channel added: {channel.channel_name}"
            logger.info(new_channel_msg)
            await self.log_to_db('INFO', new_channel_msg)
        deleted_message_ids = set(
            await sync_to_async(list)(
                DeletedMessage.objects.filter(channel=channel)
                .values_list('message_id', flat=True)
            )
        )
        existing_message_ids = set(
            await sync_to_async(list)(
                TelegramMessage.objects.filter(channel=channel)
                .values_list('message_id', flat=True)
            )
        )
        async for message in client.iter_messages(dialog, limit=4000):
            if not message.text:
                continue
            if (message.id in deleted_message_ids or 
                message.id in existing_message_ids):
                continue

            classification = parser.classify_message(message.text)
            github_urls = parser.extract_github_url(message.text)
            other_links = parser.extract_links(message.text)
            telegram_message = await sync_to_async(TelegramMessage.objects.create)(
                message_id=message.id,
                channel=channel,
                message_text=message.text,
                classification=classification,
                timestamp=message.date,
                extracted_links=other_links,
                extracted_github_url=github_urls
            )

            processed_count += 1
            logger.info(f"New message saved: {message.id} - {channel.channel_name}")
            if processed_count % 10 == 0:
                batch_msg = f"{channel.channel_name}: {processed_count} messages processed"
                await self.log_to_db('INFO', batch_msg)
            if github_urls:
                logger.info(f"GitHub URLs found: {github_urls}")
                try:
                    await self.archive_github_urls(github_urls, telegram_message, archiver)
                except Exception as archive_error:
                    logger.error(f"Error during archiving: {archive_error}")
            else:
                logger.debug(f"No GitHub URL found in message: {message.id}")

        channel_final_msg = f"Channel processed: {channel.channel_name} - {processed_count} new messages"
        logger.info(channel_final_msg)
        await self.log_to_db('INFO', channel_final_msg)
        return processed_count

    async def archive_github_urls(self, github_urls, telegram_message, archiver):
        for url in github_urls:
            try:
                existing_archive = await sync_to_async(
                    ArchivedGithubUrl.objects.filter(url=url, message=telegram_message).first
                )()
                
                if existing_archive:
                    logger.info(f"URL already archived: {url}")
                    continue

                logger.info(f"Archiving GitHub URL: {url}")
                result = await archiver.archive_url(url)
                await sync_to_async(ArchivedGithubUrl.objects.create)(
                    url=url,
                    message=telegram_message,
                    is_archived=result.get('success', False),
                    archive_url=result.get('archive_url', None),
                    error_message=result.get('error', None) if not result.get('success', False) else None
                )
                
                if result.get('success', False):
                    logger.info(f"GitHub URL successfully archived: {url} -> {result.get('archive_url')}")
                else:
                    logger.error(f"GitHub URL archiving failed: {url} - {result.get('error')}")

            except Exception as e:
                logger.error(f"GitHub URL archiving error: {url} - {e}")
                try:
                    await sync_to_async(ArchivedGithubUrl.objects.create)(
                        url=url,
                        message=telegram_message,
                        is_archived=False,
                        error_message=str(e)
                    )
                except Exception as db_error:
                    logger.error(f"Archive error could not be logged: {db_error}")
