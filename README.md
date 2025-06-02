# Telecrawl v1

A comprehensive Django-based Telegram message crawler with automated GitHub URL archiving, modern web interface, and Celery task management.

## Features

- **Telegram Message Crawling**: Automated crawling of Telegram channels and groups
- **GitHub URL Detection**: Automatic detection and archiving of GitHub repositories
- **Web Interface**: Modern Bootstrap-based dashboard with message filtering and analytics
- **Background Tasks**: Celery-powered background processing with Redis broker
- **Database Integration**: PostgreSQL database with Django ORM
- **Docker Support**: Complete containerization with Docker Compose
- **Monitoring**: Built-in logging and task monitoring
- **Admin Interface**: Django admin panel for data management

## Architecture

```
├── Django Web Application
│   ├── Dashboard & Analytics
│   ├── Message List & Filtering
│   ├── Channel Management
│   └── Admin Interface
├── Celery Background Tasks
│   ├── Message Crawling
│   ├── URL Processing
│   ├── GitHub Archiving
│   └── Periodic Cleanup
├── Database (PostgreSQL)
│   ├── Telegram Channels
│   ├── Messages
│   ├── Archived URLs
│   └── Crawler Logs
└── External Services
    ├── Redis (Celery Broker)
    ├── Telegram API
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telecrawl
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python3 telegram_session_creater.py after enter the app id and hash create telegrm sesssion file.
   ```

4. **Environment configuration**
   Copy `env/.env.example` to `env/.env` and configure:
   ```env
   # Database
   DB_NAME=telecrawl
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   
   # Redis
   REDIS_URL=redis://localhost:6379/0
   
   # Telegram
   TELEGRAM_API_ID= DO NOT FILL USE UI
   TELEGRAM_API_HASH=DO NOT FILL USE UI
   TELEGRAM_PHONE=DO NOT FILL USE UI
   
   # Django
   SECRET_KEY=your_secret_key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

5. **Database setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start services**
   ```bash
   # Terminal 1: Django
   python manage.py runserver
   
   # Terminal 2: Celery Worker
   celery -A telecrawl worker -l info
   
   # Terminal 3: Celery Beat (Scheduler)
   celery -A telecrawl beat -l info
   ```

### Docker Setup

1. **Environment configuration**
   Configure `env/.env` as described above

2. **Start all services**
   ```bash
   docker-compose up -d --build
   ```

## Usage

### Web Interface

- **Dashboard**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **Message List**: http://localhost:8000/messages/
- **Channel List**: http://localhost:8000/channels/

### Management Commands

1. **Run Telecrawl**
   ```bash
   python manage.py run_telecrawl
   ```

2. **Run Web Archiver**
   ```bash
   python manage.py run_web_archiver
   ```

3. **Clean Old Messages**
   ```bash
   python manage.py clean_messages --days 30
   ```

### API Endpoints

- `GET /api/messages/` - List messages with filtering
- `GET /api/channels/` - List monitored channels
- `GET /api/stats/` - Dashboard statistics
- `POST /api/channels/` - Add new channel

## Configuration

### Telegram Setup

1. Get API credentials from https://my.telegram.org/
2. Add credentials to `.env` file
3. Run the crawler to authenticate

### Channel Monitoring

Add channels through:
- Django Admin interface
- Web dashboard
- Direct database entry

### Task Scheduling

Configure periodic tasks in `telecrawl/celery.py`:

```python
app.conf.beat_schedule = {
    'crawl-messages': {
        'task': 'crawler.tasks.crawl_messages_task',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'archive-urls': {
        'task': 'crawler.tasks.archive_urls_task',
        'schedule': crontab(minute=30),  # Every hour at minute 30
    },
}
```

## Models

### TelegramChannel
- Channel metadata and monitoring settings
- Last crawl timestamps
- Active status

### TelegramMessage
- Message content and metadata
- Classification (link, text, media)
- Timestamps and indexing

### ArchivedGithubUrl
- GitHub repository information
- Archive status and metadata
- Processing timestamps

### CrawlerLog
- System logs and error tracking
- Performance metrics
- Debug information

## Monitoring

### Logs
- Application logs: `logs/telecrawl.log`
- Celery logs: Console output
- Docker logs: `docker-compose logs`

### Health Checks
- Database connectivity
- Redis connectivity
- Celery worker status
- Telegram API status

## Development

### Adding New Features

1. **Models**: Add to `crawler/models.py`
2. **Tasks**: Add to `crawler/tasks.py`
3. **Views**: Add to `crawler/views.py`
4. **Templates**: Add to `crawler/templates/`
5. **Tests**: Add to `crawler/tests.py`

### Testing

```bash
python manage.py test
```

### Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## Production Deployment

### Environment
- Set `DEBUG=False`
- Configure proper `SECRET_KEY`
- Set up SSL/HTTPS
- Configure static file serving

### Services
- Use PostgreSQL with connection pooling
- Use Redis with persistence
- Use Gunicorn with multiple workers
- Set up reverse proxy (Nginx)

### Monitoring
- Set up logging aggregation
- Configure health checks
- Monitor Celery queues
- Track database performance

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check PostgreSQL service
   - Verify connection credentials
   - Check network connectivity

2. **Celery Tasks Not Running**
   - Check Redis connectivity
   - Verify Celery worker is running
   - Check task queue status

3. **Telegram API Errors**
   - Verify API credentials
   - Check account status
   - Monitor rate limits

4. **Memory Issues**
   - Monitor message processing batch sizes
   - Check database query optimization
   - Review log file rotation

### Debug Commands

```bash
# Check database status
python manage.py dbshell

# Monitor Celery
celery -A telecrawl inspect stats

# Check migrations
python manage.py showmigrations

# Clear cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the logs for error details
