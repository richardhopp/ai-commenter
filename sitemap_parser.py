# sitemap_parser.py

import requests
import logging
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SitemapPage:
    """Class representing a page from a sitemap"""
    
    def __init__(self, url: str, lastmod: Optional[datetime] = None, 
                 priority: Optional[float] = None, changefreq: Optional[str] = None):
        self.url = url
        self.lastmod = lastmod
        self.priority = priority
        self.changefreq = changefreq
        self.title = ""
        self.content_snippet = ""
        self.categories = []
        self.tags = []
    
    def __str__(self):
        return f"{self.url} - {self.title}"


class SitemapParser:
    """Class for parsing XML sitemaps and extracting page data"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.sitemap_index_url = f"{base_url.rstrip('/')}/sitemap_index.xml"
        self.pages = []
        self.post_pages = []
        self.blog_pages = []
        self.page_pages = []
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xml",
            "Accept-Language": "en-US,en;q=0.9"
        }
    
    def fetch_sitemap(self, url: str) -> Optional[str]:
        """Fetch sitemap XML content from URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching sitemap {url}: {str(e)}")
            return None
    
    def parse_sitemap_index(self) -> List[str]:
        """Parse sitemap index and extract links to individual sitemaps"""
        try:
            sitemap_content = self.fetch_sitemap(self.sitemap_index_url)
            if not sitemap_content:
                logger.warning(f"Could not fetch sitemap index from {self.sitemap_index_url}")
                # Fallback to direct sitemaps
                return [
                    f"{self.base_url.rstrip('/')}/post-sitemap.xml",
                    f"{self.base_url.rstrip('/')}/page-sitemap.xml"
                ]
            
            # Parse XML
            root = ET.fromstring(sitemap_content)
            
            # Extract sitemap URLs
            # Need to handle namespaces in XML
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            sitemap_urls = []
            
            for sitemap in root.findall(".//sm:sitemap", namespaces) or root.findall(".//sitemap"):
                loc_element = sitemap.find(".//sm:loc", namespaces) or sitemap.find("loc")
                if loc_element is not None and loc_element.text:
                    sitemap_url = loc_element.text.strip()
                    
                    # Only include post and page sitemaps as requested
                    if "post-sitemap.xml" in sitemap_url or "page-sitemap.xml" in sitemap_url:
                        sitemap_urls.append(sitemap_url)
            
            if not sitemap_urls:
                logger.warning("No post or page sitemaps found in sitemap index")
                # Fallback to direct sitemaps
                return [
                    f"{self.base_url.rstrip('/')}/post-sitemap.xml",
                    f"{self.base_url.rstrip('/')}/page-sitemap.xml"
                ]
            
            return sitemap_urls
        
        except Exception as e:
            logger.error(f"Error parsing sitemap index: {str(e)}")
            # Fallback to direct sitemaps
            return [
                f"{self.base_url.rstrip('/')}/post-sitemap.xml",
                f"{self.base_url.rstrip('/')}/page-sitemap.xml"
            ]
    
    def parse_sitemap(self, sitemap_url: str) -> List[SitemapPage]:
        """Parse a single sitemap and extract page data"""
        try:
            sitemap_content = self.fetch_sitemap(sitemap_url)
            if not sitemap_content:
                logger.warning(f"Could not fetch sitemap from {sitemap_url}")
                return []
            
            # Parse XML
            root = ET.fromstring(sitemap_content)
            
            # Extract page URLs
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            pages = []
            
            for url in root.findall(".//sm:url", namespaces) or root.findall(".//url"):
                loc_element = url.find(".//sm:loc", namespaces) or url.find("loc")
                lastmod_element = url.find(".//sm:lastmod", namespaces) or url.find("lastmod")
                priority_element = url.find(".//sm:priority", namespaces) or url.find("priority")
                changefreq_element = url.find(".//sm:changefreq", namespaces) or url.find("changefreq")
                
                if loc_element is not None and loc_element.text:
                    page_url = loc_element.text.strip()
                    
                    # Try to parse lastmod date if present
                    lastmod = None
                    if lastmod_element is not None and lastmod_element.text:
                        try:
                            lastmod_str = lastmod_element.text.strip()
                            lastmod = datetime.fromisoformat(lastmod_str.replace('Z', '+00:00'))
                        except ValueError:
                            pass
                    
                    # Try to parse priority if present
                    priority = None
                    if priority_element is not None and priority_element.text:
                        try:
                            priority = float(priority_element.text.strip())
                        except ValueError:
                            pass
                    
                    # Get changefreq if present
                    changefreq = None
                    if changefreq_element is not None and changefreq_element.text:
                        changefreq = changefreq_element.text.strip()
                    
                    # Create page object
                    page = SitemapPage(
                        url=page_url,
                        lastmod=lastmod,
                        priority=priority,
                        changefreq=changefreq
                    )
                    
                    pages.append(page)
            
            return pages
        
        except Exception as e:
            logger.error(f"Error parsing sitemap {sitemap_url}: {str(e)}")
            return []
    
    def extract_page_metadata(self, pages: List[SitemapPage], fetch_limit: int = 10) -> None:
        """
        Fetch page content and extract metadata like title, description, categories.
        Limit the number of pages to fetch to avoid excessive requests.
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Limit the number of pages to fetch
            pages_to_fetch = pages[:min(fetch_limit, len(pages))]
            
            for page in pages_to_fetch:
                try:
                    response = requests.get(page.url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('title')
                    if title_tag:
                        page.title = title_tag.text.strip()
                    
                    # Extract meta description
                    description_tag = soup.find('meta', attrs={'name': 'description'})
                    if description_tag:
                        page.content_snippet = description_tag.get('content', '').strip()
                    
                    # Extract categories and tags (WordPress-specific)
                    categories_links = soup.select('.cat-links a, .category-links a, .categories a')
                    for cat_link in categories_links:
                        category = cat_link.text.strip()
                        if category:
                            page.categories.append(category)
                    
                    tags_links = soup.select('.tag-links a, .tags-links a, .tags a')
                    for tag_link in tags_links:
                        tag = tag_link.text.strip()
                        if tag:
                            page.tags.append(tag)
                    
                    # If we didn't find categories/tags, try to extract from URL structure
                    if not page.categories:
                        # Try to extract categories from URL path
                        path = urlparse(page.url).path
                        segments = [seg for seg in path.split('/') if seg]
                        
                        # If URL has structure like /category/subcategory/page-name
                        if len(segments) >= 2:
                            # Add potential category segments
                            for segment in segments[:-1]:  # Exclude the last segment (page name)
                                category = segment.replace('-', ' ').replace('_', ' ').title()
                                page.categories.append(category)
                
                except Exception as page_err:
                    logger.warning(f"Error fetching metadata for {page.url}: {str(page_err)}")
                    continue
        
        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping metadata extraction")
    
    def categorize_pages(self, all_pages: List[SitemapPage]) -> None:
        """Categorize pages into posts, blog posts, and regular pages"""
        for page in all_pages:
            if "/post/" in page.url or "/posts/" in page.url or "/blog/" in page.url:
                self.blog_pages.append(page)
            elif "/page/" in page.url or "/pages/" in page.url:
                self.page_pages.append(page)
            else:
                # Check URL patterns to determine type
                url_path = urlparse(page.url).path
                
                # If ends with typical post slug pattern (year/month/slug or category/slug)
                if re.search(r'/\d{4}/\d{2}/[\w-]+/?$', url_path) or re.search(r'/[\w-]+/[\w-]+/?$', url_path):
                    self.post_pages.append(page)
                else:
                    self.page_pages.append(page)
    
    def fetch_and_parse_all(self, fetch_metadata: bool = True, metadata_limit: int = 10) -> List[SitemapPage]:
        """Fetch and parse all sitemaps, returning all pages"""
        try:
            # Get sitemap URLs
            sitemap_urls = self.parse_sitemap_index()
            
            # Parse each sitemap
            all_pages = []
            for sitemap_url in sitemap_urls:
                pages = self.parse_sitemap(sitemap_url)
                all_pages.extend(pages)
            
            # Store all pages
            self.pages = all_pages
            
            # Categorize pages
            self.categorize_pages(all_pages)
            
            # Fetch metadata if requested
            if fetch_metadata and all_pages:
                self.extract_page_metadata(all_pages, fetch_limit=metadata_limit)
            
            return all_pages
        
        except Exception as e:
            logger.error(f"Error fetching and parsing sitemaps: {str(e)}")
            return []
    
    def get_post_pages(self) -> List[SitemapPage]:
        """Get all blog/post pages"""
        return self.blog_pages + self.post_pages
    
    def get_page_pages(self) -> List[SitemapPage]:
        """Get all regular pages"""
        return self.page_pages
    
    def get_relevant_pages(self, query: str, limit: int = 10) -> List[SitemapPage]:
        """Find pages relevant to a search query"""
        query = query.lower()
        query_terms = set(query.split())
        
        scored_pages = []
        
        for page in self.pages:
            score = 0
            
            # Score based on title
            title = page.title.lower()
            for term in query_terms:
                if term in title:
                    score += 10
            
            # Exact phrase matches are worth more
            if query in title:
                score += 20
            
            # Score based on URL (weighted less than title)
            url = page.url.lower()
            for term in query_terms:
                if term in url:
                    score += 5
            
            # Score based on categories and tags
            for category in page.categories:
                for term in query_terms:
                    if term in category.lower():
                        score += 3
            
            for tag in page.tags:
                for term in query_terms:
                    if term in tag.lower():
                        score += 3
            
            # Score based on content snippet
            content = page.content_snippet.lower()
            for term in query_terms:
                if term in content:
                    score += 2
            
            if score > 0:
                scored_pages.append((page, score))
        
        # Sort by score and limit results
        scored_pages.sort(key=lambda x: x[1], reverse=True)
        
        return [page for page, score in scored_pages[:limit]]


def create_sitemaps_for_money_sites(money_sites: List[str]) -> Dict[str, List[SitemapPage]]:
    """
    Create sitemap parsers for all money sites.
    
    Args:
        money_sites: List of money site URLs
        
    Returns:
        Dictionary mapping site URLs to their pages
    """
    site_pages = {}
    
    for site_url in money_sites:
        try:
            # Clean the URL
            if not site_url.startswith(('http://', 'https://')):
                site_url = 'https://' + site_url
            
            # Create parser
            parser = SitemapParser(site_url)
            
            # Fetch and parse
            pages = parser.fetch_and_parse_all(fetch_metadata=True, metadata_limit=20)
            
            # Store pages
            site_pages[site_url] = {
                'parser': parser,
                'pages': pages,
                'post_pages': parser.get_post_pages(),
                'page_pages': parser.get_page_pages()
            }
            
            logger.info(f"Fetched {len(pages)} pages from {site_url}")
            
        except Exception as e:
            logger.error(f"Error processing sitemap for {site_url}: {str(e)}")
    
    return site_pages


if __name__ == "__main__":
    # Test with a real site
    test_url = "https://aparthotel.com"
    parser = SitemapParser(test_url)
    pages = parser.fetch_and_parse_all()
    
    print(f"Found {len(pages)} pages total")
    print(f"Post pages: {len(parser.get_post_pages())}")
    print(f"Page pages: {len(parser.get_page_pages())}")
    
    # Test relevance matching
    query = "tokyo apartments monthly stay"
    relevant = parser.get_relevant_pages(query, limit=5)
    
    print(f"\nTop 5 pages for '{query}':")
    for page in relevant:
        print(f"- {page.title}: {page.url}")
