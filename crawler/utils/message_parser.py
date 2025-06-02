import re
from asgiref.sync import sync_to_async

class MessageParser:
    @staticmethod
    def get_keywords():
        try:
            from crawler.models import MessageKeyword
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT keyword FROM message_keywords WHERE is_active = %s",[True])
                keywords = [row[0] for row in cursor.fetchall()]

            return keywords if keywords else ["poc", "exploit", "vulnerability", "RCE vulnerability","0-day", "PoC", "p0c", "P0C", "RCE", "payload",".gov.tr", "@com.tr"]
        except Exception as e:
            print(f"Could not get keywords from database: {e}")
            return ["poc", "exploit", "vulnerability", "RCE vulnerability","0-day", "PoC", "p0c", "P0C", "RCE", "payload",".gov.tr", "@com.tr"]
        
    @staticmethod
    async def classify_message(text):
        keywords = await sync_to_async(MessageParser.get_keywords)()
        
        for kw in keywords:
            if kw.startswith(('http://', 'https://', 'www.')):
                if kw.lower() in text.lower():
                    return "relevant"
            elif kw.startswith(('.', '@')):
                if kw.lower() in text.lower():
                    return "relevant"
            else:
                escaped_kw = re.escape(kw)
                if re.search(rf"\b{escaped_kw}\b", text, re.IGNORECASE):
                    return "relevant"
        
        return "irrelevant"
    @staticmethod
    def extract_github_url(text):
        pattern = r"(https?://github\.com/[^\s\*\[\]]+)"
        urls = re.findall(pattern, text)
        cleaned_urls = []
        for url in urls:
            cleaned_url = url.strip()
            cleaned_url = re.sub(r'[.,;:!?\)\]\}"\'*]+$', '', cleaned_url)
            if cleaned_url.endswith(')') and cleaned_url.count('(') < cleaned_url.count(')'):
                cleaned_url = cleaned_url.rstrip(')')
            cleaned_url = re.sub(r'[^\w/\-_#:?.&=]+$', '', cleaned_url)
            if cleaned_url and cleaned_url.startswith('http'):
                cleaned_urls.append(cleaned_url)
        return cleaned_urls

    @staticmethod
    def extract_links(text):
        pattern = r"(https?://[^\s\*\[\]]+)"
        all_links = re.findall(pattern, text)
        cleaned_links = []
        for link in all_links:
            cleaned_link = link.strip()
            cleaned_link = re.sub(r'[.,;:!?\)\]\}"\'*]+$', '', cleaned_link)
            if cleaned_link.endswith(')') and cleaned_link.count('(') < cleaned_link.count(')'):
                cleaned_link = cleaned_link.rstrip(')')
            cleaned_link = re.sub(r'[^\w/\-_#:?.&=]+$', '', cleaned_link)
            if cleaned_link and cleaned_link.startswith('http'):
                cleaned_links.append(cleaned_link)

        non_github_links = [
            link for link in cleaned_links
            if not re.search(r"https?://github\.com", link, re.IGNORECASE)
        ]
        return non_github_links
