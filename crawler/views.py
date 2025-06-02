from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.template.loader import render_to_string
import subprocess
import psutil
import os
import signal
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from .models import TelegramMessage, TelegramChannel, ArchivedGithubUrl, CrawlerLog, CrawlerSettings, CrawlerStatus, MessageKeyword

def dashboard(request):
    context = {
        'total_messages': TelegramMessage.objects.count(),
        'relevant_messages': TelegramMessage.objects.filter(classification='relevant').count(),
        'irrelevant_messages': TelegramMessage.objects.filter(classification='irrelevant').count(),
        'total_channels': TelegramChannel.objects.count(),
        'active_channels': TelegramChannel.objects.filter(is_active=True).count(),
        'archived_urls': ArchivedGithubUrl.objects.filter(is_archived=True).count(),
        'pending_urls': ArchivedGithubUrl.objects.filter(is_archived=False).count(),
        'recent_messages': TelegramMessage.objects.select_related('channel').order_by('-timestamp')[:10],
        'recent_logs': CrawlerLog.objects.order_by('-timestamp')[:10],
    }
    return render(request, 'crawler/dashboard.html', context)

def message_list(request):
    messages = TelegramMessage.objects.select_related('channel').order_by('-timestamp')
    classification = request.GET.get('classification')
    if classification:
        messages = messages.filter(classification=classification)
    
    search = request.GET.get('search')
    if search:
        messages = messages.filter(
            Q(message_text__icontains=search) |
            Q(channel__channel_name__icontains=search)        )
    
    paginator = Paginator(messages, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'classification': classification,
        'search': search,
    }
    return render(request, 'crawler/message_list.html', context)

def channel_list(request):
    channels = TelegramChannel.objects.annotate(
        message_count=Count('messages')
    ).order_by('-message_count')
    context = {
        'channels': channels,
    }
    return render(request, 'crawler/channel_list.html', context)

def archived_url_list(request):
    urls = ArchivedGithubUrl.objects.select_related('message', 'message__channel').order_by('-processed_at')
    is_archived = request.GET.get('is_archived')
    if is_archived:        urls = urls.filter(is_archived=is_archived == 'true')
    paginator = Paginator(urls, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'is_archived': is_archived,
    }
    return render(request, 'crawler/archived_url_list.html', context)

def log_list(request):
    logs = CrawlerLog.objects.order_by('-timestamp')
    level = request.GET.get('level')
    if level:
        logs = logs.filter(level=level)
    module = request.GET.get('module')
    if module:        logs = logs.filter(module=module)
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'level': level,
        'module': module,
        'available_levels': CrawlerLog.LOG_LEVELS,
        'available_modules': CrawlerLog.objects.values_list('module', flat=True).distinct(),
    }
    return render(request, 'crawler/log_list.html', context)

def settings_view(request):
    if request.method == 'POST':
        api_id = request.POST.get('api_id')
        api_hash = request.POST.get('api_hash')
        phone = request.POST.get('phone')
        
        if api_id:
            CrawlerSettings.set_setting('TELEGRAM_API_ID', api_id, 'Telegram API ID')
        if api_hash:
            CrawlerSettings.set_setting('TELEGRAM_API_HASH', api_hash, 'Telegram API Hash')
        if phone:
            CrawlerSettings.set_setting('TELEGRAM_PHONE', phone, 'Telegram Phone Number')
        messages.success(request, 'Settings saved successfully!')
        return redirect('crawler:settings')
    
    context = {
        'api_id': CrawlerSettings.get_setting('TELEGRAM_API_ID', ''),
        'api_hash': CrawlerSettings.get_setting('TELEGRAM_API_HASH', ''),
        'phone': CrawlerSettings.get_setting('TELEGRAM_PHONE', ''),
        'crawler_status': CrawlerStatus.get_current_status(),
    }
    return render(request, 'crawler/settings.html', context)

@csrf_exempt
@require_POST
def start_crawler(request):
    try:
        crawler_status = CrawlerStatus.get_current_status()
        if crawler_status.is_running:            
            return JsonResponse({'success': False,'message': 'Crawler is already running!'})

        api_id = CrawlerSettings.get_setting('TELEGRAM_API_ID')
        api_hash = CrawlerSettings.get_setting('TELEGRAM_API_HASH')
        phone = CrawlerSettings.get_setting('TELEGRAM_PHONE')
        
        if not all([api_id, api_hash, phone]):
            return JsonResponse({'success': False,'message': 'API settings missing! Please enter API information from the settings page.'})
        from django.conf import settings
        project_root = settings.BASE_DIR
        
        print(f"Debug: Project root path: {project_root}")  # For debugging
        process = subprocess.Popen([
            'python', 'manage.py', 'run_telegram_crawler'
        ], cwd=str(project_root))
        
        crawler_status.is_running = True
        crawler_status.status = 'running'
        crawler_status.process_id = process.pid
        crawler_status.started_at = timezone.now()
        crawler_status.stopped_at = None
        crawler_status.error_message = ''
        crawler_status.save()
        return JsonResponse({'success': True,'message': f'Crawler started! (PID: {process.pid})'})
        
    except Exception as e:
        return JsonResponse({'success': False,'message': f'Error: {str(e)}'})

@csrf_exempt
@require_POST  
def stop_crawler(request):
    try:
        crawler_status = CrawlerStatus.get_current_status()
        if not crawler_status.is_running:
            return JsonResponse({'success': False,'message': 'Crawler is already stopped!'})
        if crawler_status.process_id:
            try:
                process = psutil.Process(crawler_status.process_id)
                process.terminate()
                process.wait(timeout=10)
            except psutil.NoSuchProcess:
                pass  # Process already dead
            except psutil.TimeoutExpired:
                try:
                    process.kill()
                except:
                    pass
          # Update status
        crawler_status.is_running = False
        crawler_status.status = 'stopped'
        crawler_status.process_id = None
        crawler_status.stopped_at = timezone.now()
        crawler_status.save()
        CrawlerLog.log('Crawler stopped by user request', level='info', module='crawler.views')
        return JsonResponse({'success': True,'message': 'Crawler stopped!'})

    except Exception as e:
        return JsonResponse({'success': False,'message': f'Error: {str(e)}'})

def crawler_status_api(request):
    crawler_status = CrawlerStatus.get_current_status()
    if crawler_status.is_running and crawler_status.process_id:
        try:
            process = psutil.Process(crawler_status.process_id)
            if not process.is_running():
                # Process died, update status
                crawler_status.is_running = False
                crawler_status.status = 'stopped'
                crawler_status.process_id = None
                crawler_status.stopped_at = timezone.now()
                crawler_status.save()
        except psutil.NoSuchProcess:
            # Process not found, update status
            crawler_status.is_running = False
            crawler_status.status = 'stopped'
            crawler_status.process_id = None
            crawler_status.stopped_at = timezone.now()
            crawler_status.save()
    
    return JsonResponse({
        'is_running': crawler_status.is_running,
        'status': crawler_status.status,
        'process_id': crawler_status.process_id,
        'started_at': crawler_status.started_at.isoformat() if crawler_status.started_at else None,
        'stopped_at': crawler_status.stopped_at.isoformat() if crawler_status.stopped_at else None,
        'messages_processed': crawler_status.messages_processed,
        'channels_processed': crawler_status.channels_processed,
        'last_message': crawler_status.last_message,
        'error_message': crawler_status.error_message,
    })

def keywords_api(request):
    from .models import MessageKeyword
    keywords = MessageKeyword.objects.all().order_by('keyword_type', 'keyword')
    keywords_data = []
    
    for kw in keywords:
        keywords_data.append({
            'id': kw.id,
            'keyword': kw.keyword,
            'keyword_type': kw.keyword_type,
            'keyword_type_display': kw.get_keyword_type_display(),
            'is_active': kw.is_active,
            'case_sensitive': kw.case_sensitive,
            'description': kw.description,
        })
    return JsonResponse({'keywords': keywords_data,'total': len(keywords_data)})

@require_POST
def add_keyword_api(request):
    from .models import MessageKeyword
    keyword = request.POST.get('keyword', '').strip()
    keyword_type = request.POST.get('keyword_type', 'other')
    
    if not keyword:
        return JsonResponse({'success': False,'message': 'Keyword cannot be empty!'})
    
    try:
        # Check if same keyword exists
        if MessageKeyword.objects.filter(keyword=keyword).exists():
            return JsonResponse({'success': False,'message': 'This keyword already exists!'})

        new_keyword = MessageKeyword.objects.create(
            keyword=keyword,
            keyword_type=keyword_type,
            description=f'{keyword} keyword - added on {timezone.now().strftime("%d.%m.%Y %H:%M")}'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'"{keyword}" keyword successfully added!',
            'keyword': {
                'id': new_keyword.id,
                'keyword': new_keyword.keyword,
                'keyword_type': new_keyword.keyword_type,
                'is_active': new_keyword.is_active
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False,'message': f'Error occurred while adding keyword: {str(e)}'})

@require_POST
def toggle_keyword_api(request):
    from .models import MessageKeyword
    keyword_id = request.POST.get('id')
    is_active = request.POST.get('is_active', 'false').lower() == 'true'
    try:
        keyword = MessageKeyword.objects.get(id=keyword_id)
        keyword.is_active = is_active
        keyword.save()
        status = "active" if is_active else "inactive"
        return JsonResponse({'success': True,'message': f'"{keyword.keyword}" keyword has been set to {status}!'})

    except MessageKeyword.DoesNotExist:
        return JsonResponse({'success': False,'message': 'Keyword not found!'})

    except Exception as e:
        return JsonResponse({'success': False,'message': f'Error occurred: {str(e)}'})

@require_POST
def delete_keyword_api(request):
    from .models import MessageKeyword
    keyword_id = request.POST.get('id')
    try:
        keyword = MessageKeyword.objects.get(id=keyword_id)
        keyword_text = keyword.keyword
        keyword.delete()
        return JsonResponse({'success': True,'message': f'"{keyword_text}" keyword successfully deleted!'})

    except MessageKeyword.DoesNotExist:
        return JsonResponse({'success': False,'message': 'Keyword not found!'})
    except Exception as e:
        return JsonResponse({'success': False,'message': f'Error occurred: {str(e)}'})

def export_channel_messages_to_pdf(request, channel_id):
    channel = get_object_or_404(TelegramChannel, id=channel_id)
    messages = TelegramMessage.objects.filter(channel=channel).order_by('-timestamp')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{channel.channel_name}_messages.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.alignment = 1 
    elements.append(Paragraph(f"Telegram Channel: {channel.channel_name}", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    data = []
    for msg in messages:
        data.append([
            msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            msg.message_text,
        ])
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    
    table = Table(data)
    table.setStyle(table_style)
    elements.append(table)
    doc.build(elements)
    return response

def export_channel_pdf(request, channel_id):
    channel = get_object_or_404(TelegramChannel, id=channel_id)
    classification = request.GET.get('classification', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    messages = TelegramMessage.objects.filter(channel=channel).order_by('-timestamp')
    if classification != 'all':
        messages = messages.filter(classification=classification)
    if date_from:
        messages = messages.filter(timestamp__gte=date_from)
    if date_to:
        messages = messages.filter(timestamp__lte=date_to)
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"channel_{channel.channel_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
    )
    story = []
    story.append(Paragraph(f"Telegram Channel Report", title_style))
    story.append(Paragraph(f"Channel: {channel.channel_name}", subtitle_style))
    story.append(Paragraph(f"Channel ID: {channel.channel_id}", normal_style))
    if channel.username:
        story.append(Paragraph(f"Username: @{channel.username}", normal_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", normal_style))
    story.append(Paragraph(f"Total Message Count: {messages.count()}", normal_style))
    if classification != 'all':
        story.append(Paragraph(f"Filtering: {classification.title()}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    if messages.exists():
        data = [['#', 'Date', 'Classification', 'Message Content']]
        for idx, message in enumerate(messages[:500], 1):
            text = message.message_text[:200] + "..." if len(message.message_text) > 200 else message.message_text
            text = text.replace('\n', ' ').replace('\r', ' ')
            data.append([
                str(idx),
                message.timestamp.strftime('%d.%m.%Y %H:%M'),
                'Relevant' if message.classification == 'relevant' else 'Irrelevant',
                text
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(table)
        if messages.count() > 500:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(f"Note: First 500 messages are shown. Total {messages.count()} messages found.", normal_style))
    else:        
        story.append(Paragraph("No messages found matching these criteria.", normal_style))
    doc.build(story)
    return response
