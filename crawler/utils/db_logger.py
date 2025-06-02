import logging
from django.conf import settings
from asgiref.sync import sync_to_async

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        try:
            import asyncio
            if hasattr(asyncio, 'current_task') and asyncio.current_task():
                asyncio.create_task(self._async_emit(record))
            else:
                self._sync_emit(record)
        except Exception:
            pass
    
    def _sync_emit(self, record):
        try:
            from crawler.models import CrawlerLog
            CrawlerLog.objects.create(
                level=record.levelname,
                message=self.format(record),
                module=record.module,
                extra_data={
                    'funcName': record.funcName,
                    'lineno': record.lineno,
                    'pathname': record.pathname
                }
            )
        except Exception:
            pass
    
    async def _async_emit(self, record):
        try:
            from crawler.models import CrawlerLog
            await sync_to_async(CrawlerLog.objects.create)(
                level=record.levelname,
                message=self.format(record),
                module=record.module,
                extra_data={
                    'funcName': record.funcName,
                    'lineno': record.lineno,
                    'pathname': record.pathname
                }
            )
        except Exception:
            pass
