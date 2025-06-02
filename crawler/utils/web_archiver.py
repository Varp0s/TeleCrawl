import asyncio
import random
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class WebArchiver:
    def __init__(self, proxy_file=None, headless=True):
        self.proxy_list = []
        self.proxy_index = 0
        self.headless = headless
        if proxy_file is None:
            import os
            proxy_file = os.path.join(os.getcwd(), "proxies.txt")
            logger.info(f"Using default proxy file: {proxy_file}")
        self.load_proxies(proxy_file)
    
    def load_proxies(self, file_path):
        try:
            with open(file_path, "r") as file:
                self.proxy_list = [line.strip() for line in file.readlines()]
            if not self.proxy_list:
                logger.warning("Proxy list is empty, direct connection will be used")
                self.proxy_list = ["direct"]
        except FileNotFoundError:
            logger.warning(f"Proxy file not found: {file_path}, using direct connection")
            self.proxy_list = ["direct"]
    
    def get_next_proxy(self):
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def setup_selenium(self, proxy=None):
        chrome_options = Options()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--max_old_space_size=4096')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-gpu-logging')
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--log-level=3')
        
        if proxy and proxy != "direct":
            chrome_options.add_argument(f'--proxy-server={proxy}')
        service = Service(ChromeDriverManager().install())
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            raise
    
    async def archive_url(self, url):
        driver = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} - Archiving URL: {url}")
                proxy = self.get_next_proxy()
                logger.info(f"Using proxy: {proxy}")
                driver = self.setup_selenium(proxy)
                logger.info("Navigating to archive.org...")
                driver.get("https://web.archive.org/save/")
                wait = WebDriverWait(driver, 30)
                logger.info("Waiting for input field...")
                wait.until(EC.presence_of_element_located((By.ID, "web-save-url-input")))
                await asyncio.sleep(random.randint(3, 8))
                logger.info("Finding input element...")
                input_element = wait.until(EC.element_to_be_clickable((By.ID, "web-save-url-input")))
                input_element.clear()
                logger.info(f"Typing URL: {url}")
                for char in url:
                    input_element.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                logger.info("Submitting form...")
                input_element.send_keys(Keys.RETURN)
                random_delay = random.randint(80, 120)
                logger.info(f"Waiting {random_delay} seconds for archiving to complete...")
                check_interval = 10
                total_waited = 0
                
                while total_waited < random_delay:
                    await asyncio.sleep(check_interval)
                    total_waited += check_interval
                    try:
                        current_url = driver.current_url
                        logger.info(f"Current URL: {current_url}")
                        if "web.archive.org/web/" in current_url:
                            logger.info(f"URL archived successfully: {current_url}")
                            return {'success': True, 'archive_url': current_url}
                        done_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Done!') or contains(text(), 'Success')]")
                        if done_elements:
                            current_url = driver.current_url
                            logger.info(f"Archiving completed - Done! found: {current_url}")
                            return {'success': True, 'archive_url': current_url}
                        error_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Error') or contains(text(), 'Failed') or contains(text(), 'problem')]")
                        if error_elements:
                            error_text = error_elements[0].text
                            logger.warning(f"Archive error detected: {error_text}")
                            if attempt < max_retries - 1:
                                break
                            else:
                                return {'success': False, 'error': f'Archiving failed: {error_text}'}
                    except WebDriverException as e:
                        logger.warning(f"WebDriver exception during status check: {e}")
                        continue
                current_url = driver.current_url
                if "web.archive.org/web/" in current_url:
                    logger.info(f"URL archived successfully after full wait: {current_url}")
                    return {'success': True, 'archive_url': current_url}
                else:
                    logger.warning(f"Archiving may have failed - final URL: {current_url}")
                    if attempt < max_retries - 1:
                        if driver:
                            driver.quit()
                        await asyncio.sleep(random.randint(10, 20))
                        continue
                    else:
                        return {'success': False, 'error': 'Archiving failed - timeout or redirect issue'}
                
            except Exception as e:
                logger.error(f"URL archiving error on attempt {attempt + 1}: {url} - {e}")
                if attempt < max_retries - 1:
                    if driver:
                        driver.quit()
                    await asyncio.sleep(random.randint(10, 20))
                    continue
                else:
                    return {'success': False, 'error': str(e)}
            finally:
                if driver and attempt == max_retries - 1:
                    driver.quit()
        return {'success': False, 'error': 'Max retries exceeded'}

    async def archive_multiple_urls(self, urls, max_concurrent=1):
        semaphore = asyncio.Semaphore(max_concurrent)
        async def archive_with_semaphore(url):
            async with semaphore:
                return await self.archive_url(url)
        tasks = [archive_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return dict(zip(urls, results))
