from django.db import models
from django.utils import timezone

class TelegramChannel(models.Model):
    channel_id = models.BigIntegerField(unique=True)
    channel_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'telegram_channels'
        verbose_name = 'Telegram Channel'
        verbose_name_plural = 'Telegram Channels'
    
    def __str__(self):
        return f"{self.channel_name} ({self.channel_id})"


class TelegramMessage(models.Model):
    CLASSIFICATION_CHOICES = [
        ('relevant', 'Relevant'),
        ('irrelevant', 'Irrelevant'),
    ]
    
    message_id = models.BigIntegerField()
    channel = models.ForeignKey(TelegramChannel, on_delete=models.CASCADE, related_name='messages')
    message_text = models.TextField()
    classification = models.CharField(max_length=255, choices=CLASSIFICATION_CHOICES)  # Increased max_length to 255
    timestamp = models.DateTimeField()
    extracted_links = models.JSONField(null=True, blank=True)
    extracted_github_url = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'telegram_messages'
        verbose_name = 'Telegram Message'
        verbose_name_plural = 'Telegram Messages'
        unique_together = ['message_id', 'channel']
        indexes = [
            models.Index(fields=['classification']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['message_id']),
        ]
    def __str__(self):
        return f"Message {self.message_id} from {self.channel.channel_name}"

class DeletedMessage(models.Model):
    message_id = models.BigIntegerField()
    channel = models.ForeignKey(TelegramChannel, on_delete=models.CASCADE, related_name='deleted_messages')
    deleted_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, default='irrelevant')
    class Meta:
        db_table = 'deleted_messages'
        verbose_name = 'Deleted Message'
        verbose_name_plural = 'Deleted Messages'
        unique_together = ['message_id', 'channel']
    def __str__(self):
        return f"Deleted Message {self.message_id} from {self.channel.channel_name}"

class ArchivedGithubUrl(models.Model):
    url = models.URLField()
    message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name='archived_urls')
    processed_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)
    archive_url = models.URLField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    class Meta:
        db_table = 'archived_github_urls'
        verbose_name = 'Archived GitHub URL'
        verbose_name_plural = 'Archived GitHub URLs'
        unique_together = ['url', 'message']
    def __str__(self):
        return f"Archived: {self.url}"

class CrawlerLog(models.Model):
    LOG_LEVELS = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('DEBUG', 'Debug'),
    ]
    
    level = models.CharField(max_length=10, choices=LOG_LEVELS)
    message = models.TextField()
    module = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    extra_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'crawler_logs'
        verbose_name = 'Crawler Log'
        verbose_name_plural = 'Crawler Logs'
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['module']),
        ]
    def __str__(self):
        return f"[{self.level}] {self.module}: {self.message[:50]}..."

class CrawlerSettings(models.Model):
    name = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crawler_settings'
        verbose_name = 'Crawler Setting'
        verbose_name_plural = 'Crawler Settings'
    
    def __str__(self):
        return f"{self.name}: {self.value[:50]}..."
    @classmethod
    def get_setting(cls, name, default=None):
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT value FROM crawler_settings WHERE name = %s",[name])
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            print(f"Error getting setting '{name}': {e}")
            return default

    @classmethod
    def set_setting(cls, name, value, description=""):
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM crawler_settings WHERE name = %s", [name])
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        "UPDATE crawler_settings SET value = %s, description = %s, updated_at = NOW() WHERE name = %s",
                        [value, description, name]
                    )
                else:
                    cursor.execute(
                        "INSERT INTO crawler_settings (name, value, description, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW())",
                        [name, value, description]
                    )
                connection.commit()
                return True
        except Exception as e:
            print(f"Error setting setting '{name}': {e}")
            return False

class CrawlerStatus(models.Model):
    """Model for crawler running status"""
    STATUS_CHOICES = [
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('error', 'Error'),
    ]
    
    is_running = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='stopped')
    process_id = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    last_message = models.TextField(blank=True, null=True)  # Added null=True
    error_message = models.TextField(blank=True, null=True)  # Added null=True
    messages_processed = models.IntegerField(default=0)
    channels_processed = models.IntegerField(default=0)
    class Meta:
        db_table = 'crawler_status'
        verbose_name = 'Crawler Status'
        verbose_name_plural = 'Crawler Statuses'
    
    def __str__(self):
        return f"Crawler Status: {self.status}"
    @classmethod
    def get_current_status(cls):
        """Get or create current status"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT is_running, status, process_id, started_at, stopped_at, last_message, error_message, messages_processed, channels_processed FROM crawler_status WHERE id = %s",
                    [1]
                )
                row = cursor.fetchone()
                if row:
                    class StatusObj:
                        def __init__(self, data):
                            self.id = 1
                            self.is_running = data[0]
                            self.status = data[1]
                            self.process_id = data[2]
                            self.started_at = data[3]
                            self.stopped_at = data[4]
                            self.last_message = data[5]
                            self.error_message = data[6]
                            self.messages_processed = data[7]
                            self.channels_processed = data[8]
                        def save(self):
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    """UPDATE crawler_status SET 
                                       is_running = %s, status = %s, process_id = %s, 
                                       started_at = %s, stopped_at = %s, last_message = %s, 
                                       error_message = %s, messages_processed = %s, channels_processed = %s 
                                       WHERE id = %s""",
                                    [self.is_running, self.status, self.process_id, 
                                     self.started_at, self.stopped_at, self.last_message,
                                     self.error_message, self.messages_processed, self.channels_processed, 1]
                                )
                                connection.commit()
                    return StatusObj(row)
                else:
                    cursor.execute(
                        "INSERT INTO crawler_status (id, is_running, status, last_message, error_message, messages_processed, channels_processed) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        [1, False, 'stopped', '', '', 0, 0]  
                    )
                    connection.commit()
                    class StatusObj:
                        def __init__(self):
                            self.id = 1
                            self.is_running = False
                            self.status = 'stopped'
                            self.process_id = None
                            self.started_at = None
                            self.stopped_at = None
                            self.last_message = ''
                            self.error_message = ''
                            self.messages_processed = 0
                            self.channels_processed = 0
                        
                        def save(self):
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    """UPDATE crawler_status SET 
                                       is_running = %s, status = %s, process_id = %s, 
                                       started_at = %s, stopped_at = %s, last_message = %s, 
                                       error_message = %s, messages_processed = %s, channels_processed = %s 
                                       WHERE id = %s""",
                                    [self.is_running, self.status, self.process_id, 
                                     self.started_at, self.stopped_at, self.last_message,
                                     self.error_message, self.messages_processed, self.channels_processed, 1]
                                )
                                connection.commit()
                    return StatusObj()
                    
        except Exception as e:
            print(f"Error getting status: {e}")
            class StatusObj:
                def __init__(self):
                    self.id = 1
                    self.is_running = False
                    self.status = 'stopped'
                    self.process_id = None
                    self.started_at = None
                    self.stopped_at = None
                    self.last_message = ''
                    self.error_message = ''
                    self.messages_processed = 0
                    self.channels_processed = 0
                def save(self):
                    pass
            return StatusObj()

class MessageKeyword(models.Model):
    KEYWORD_TYPES = [
        ('security', 'Security'),
        ('vulnerability', 'Vulnerability'),
        ('exploit', 'Exploit'),
        ('domain', 'Domain'),
        ('other', 'Other'),
    ]
    
    keyword = models.CharField(max_length=255, unique=True)
    keyword_type = models.CharField(max_length=20, choices=KEYWORD_TYPES, default='other')
    case_sensitive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'message_keywords'
        verbose_name = 'Message Keyword'
        verbose_name_plural = 'Message Keywords'
        indexes = [
            models.Index(fields=['keyword_type']),
            models.Index(fields=['is_active']),
        ]
    def __str__(self):
        return f"{self.keyword} ({self.get_keyword_type_display()})"
    
    @classmethod
    def get_active_keywords(cls, keyword_type=None):
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                if keyword_type:
                    cursor.execute(
                        "SELECT keyword FROM message_keywords WHERE is_active = %s AND keyword_type = %s",
                        [True, keyword_type]
                    )
                else:
                    cursor.execute(
                        "SELECT keyword FROM message_keywords WHERE is_active = %s",
                        [True]
                    )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Could not get keywords from database: {e}")
            return []
    
    @classmethod
    def populate_default_keywords(cls):
        default_keywords = [
            {'keyword': 'poc', 'keyword_type': 'exploit', 'description': 'Proof of Concept'},
            {'keyword': 'exploit', 'keyword_type': 'exploit', 'description': 'Exploit code'},
            {'keyword': 'vulnerability', 'keyword_type': 'vulnerability', 'description': 'Vulnerability reference'},
            {'keyword': 'RCE vulnerability', 'keyword_type': 'vulnerability', 'description': 'Remote Code Execution vulnerability'},
            {'keyword': '0-day', 'keyword_type': 'vulnerability', 'description': 'Zero-day vulnerability'},
            {'keyword': 'PoC', 'keyword_type': 'exploit', 'description': 'Proof of Concept (uppercase)'},
            {'keyword': 'p0c', 'keyword_type': 'exploit', 'description': 'PoC variant'},
            {'keyword': 'P0C', 'keyword_type': 'exploit', 'description': 'PoC variant (uppercase)'},
            {'keyword': 'RCE', 'keyword_type': 'vulnerability', 'description': 'Remote Code Execution'},
            {'keyword': 'payload', 'keyword_type': 'exploit', 'description': 'Exploit payload'},
            {'keyword': '.gov.tr', 'keyword_type': 'domain', 'description': 'Turkish government domain'},
            {'keyword': '@com.tr', 'keyword_type': 'domain', 'description': 'Turkish commercial domain'},
        ]
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                for kw_data in default_keywords:
                    cursor.execute("SELECT id FROM message_keywords WHERE keyword = %s", [kw_data['keyword']])
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO message_keywords (keyword, keyword_type, description, case_sensitive, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
                            [kw_data['keyword'], kw_data['keyword_type'], kw_data['description'], False, True]
                        )
                connection.commit()
        except Exception as e:
            print(f"Error populating keywords: {e}")
