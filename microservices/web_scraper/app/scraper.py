
import requests
from bs4 import BeautifulSoup
import time
import hashlib
import os
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WebScraper:
    def __init__(self):
        self.user_agent = os.getenv("SCRAPER_USER_AGENT", "DocumentRouter/1.0")
        self.delay = float(os.getenv("SCRAPER_DELAY", "1"))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
        
        # Setup Selenium WebDriver options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument(f"--user-agent={self.user_agent}")
    
    def scrape_url(self, url: str, rules: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Scrape content from a URL using specified rules"""
        try:
            # Respect rate limiting
            time.sleep(self.delay)
            
            # Determine scraping method
            use_selenium = rules and rules.get('use_selenium', False)
            
            if use_selenium:
                return self._scrape_with_selenium(url, rules)
            else:
                return self._scrape_with_requests(url, rules)
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    def _scrape_with_requests(self, url: str, rules: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Scrape using requests and BeautifulSoup"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic information
            title = self._extract_title(soup, rules)
            content = self._extract_content(soup, rules)
            metadata = self._extract_metadata(soup, url, rules)
            
            # Generate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'content_hash': content_hash,
                'metadata': metadata,
                'scraping_method': 'requests'
            }
            
        except requests.RequestException as e:
            print(f"Request error for {url}: {e}")
            return None
    
    def _scrape_with_selenium(self, url: str, rules: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Scrape using Selenium WebDriver for JavaScript-heavy sites"""
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(url)
            
            # Wait for page to load
            wait_time = rules.get('wait_time', 5) if rules else 5
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            if rules and rules.get('dynamic_wait'):
                time.sleep(rules.get('dynamic_wait', 2))
            
            # Get page source after JavaScript execution
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract information
            title = self._extract_title(soup, rules)
            content = self._extract_content(soup, rules)
            metadata = self._extract_metadata(soup, url, rules)
            
            # Generate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'content_hash': content_hash,
                'metadata': metadata,
                'scraping_method': 'selenium'
            }
            
        except Exception as e:
            print(f"Selenium error for {url}: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _extract_title(self, soup: BeautifulSoup, rules: Dict[str, Any] = None) -> str:
        """Extract page title"""
        if rules and 'title_selector' in rules:
            # Use custom selector
            title_element = soup.select_one(rules['title_selector'])
            if title_element:
                return title_element.get_text(strip=True)
        
        # Default title extraction
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Fallback to h1
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return "No title found"
    
    def _extract_content(self, soup: BeautifulSoup, rules: Dict[str, Any] = None) -> str:
        """Extract main content from page"""
        content_text = ""
        
        if rules and 'content_selectors' in rules:
            # Use custom selectors
            for selector in rules['content_selectors']:
                elements = soup.select(selector)
                for element in elements:
                    content_text += element.get_text(strip=True) + "\n"
        else:
            # Default content extraction strategy
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Try common content selectors
            content_selectors = [
                'article',
                '.content',
                '#content',
                '.post-content',
                '.entry-content',
                'main',
                '.main'
            ]
            
            content_found = False
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        content_text += element.get_text(strip=True) + "\n"
                    content_found = True
                    break
            
            # Fallback: extract all paragraphs
            if not content_found:
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    content_text += p.get_text(strip=True) + "\n"
        
        # Clean up content
        content_text = re.sub(r'\n\s*\n', '\n', content_text)  # Remove empty lines
        content_text = content_text.strip()
        
        return content_text
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str, rules: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract metadata from page"""
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc
        }
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            if name and content:
                metadata[name] = content
        
        # Extract structured data (JSON-LD)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        structured_data = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except json.JSONDecodeError:
                pass
        
        if structured_data:
            metadata['structured_data'] = structured_data
        
        # Extract links
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            if href and text:
                absolute_url = urljoin(url, href)
                links.append({'url': absolute_url, 'text': text})
        
        metadata['links'] = links[:20]  # Limit to first 20 links
        
        # Custom metadata extraction from rules
        if rules and 'metadata_selectors' in rules:
            for key, selector in rules['metadata_selectors'].items():
                element = soup.select_one(selector)
                if element:
                    metadata[key] = element.get_text(strip=True)
        
        return metadata
    
    def scrape_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract URLs from XML sitemap"""
        try:
            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            urls = []
            
            # Handle regular sitemap
            for loc in soup.find_all('loc'):
                urls.append(loc.get_text(strip=True))
            
            # Handle sitemap index
            for sitemap in soup.find_all('sitemap'):
                loc = sitemap.find('loc')
                if loc:
                    urls.append(loc.get_text(strip=True))
            
            return urls
            
        except Exception as e:
            print(f"Error scraping sitemap {sitemap_url}: {e}")
            return []
    
    def discover_documents(self, url: str, file_extensions: List[str] = None) -> List[str]:
        """Discover document links on a page"""
        if file_extensions is None:
            file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        
        try:
            scraped_data = self._scrape_with_requests(url)
            if not scraped_data or 'metadata' not in scraped_data:
                return []
            
            document_urls = []
            links = scraped_data['metadata'].get('links', [])
            
            for link in links:
                link_url = link['url']
                # Check if link points to a document
                for ext in file_extensions:
                    if link_url.lower().endswith(ext):
                        document_urls.append(link_url)
                        break
            
            return document_urls
            
        except Exception as e:
            print(f"Error discovering documents from {url}: {e}")
            return []
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is accessible"""
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except:
            return False
