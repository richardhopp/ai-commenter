# search_module.py

import os
import re
import json
import random
import logging
import time
import requests
from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import concurrent.futures

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Constants for search configuration
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

PLATFORM_DOMAINS = {
    "quora": ["quora.com"],
    "reddit": ["reddit.com"],
    "tripadvisor": ["tripadvisor.com", "tripadvisor.co.uk", "tripadvisor.ca"],
    "stackexchange": ["stackoverflow.com", "superuser.com", "askubuntu.com", "stackexchange.com"],
    "medium": ["medium.com"],
    "twitter": ["twitter.com", "x.com"],
    "linkedin": ["linkedin.com"],
    "facebook": ["facebook.com"],
    "discord": ["discord.com"],
    "youtube": ["youtube.com", "youtu.be"]
}

class SearchResult:
    """Class to represent a search result with relevant thread data"""
    
    def __init__(self, title, url, snippet, platform=None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.platform = platform or self._detect_platform()
        self.relevance_score = 0.0
        self.complexity = 0
        self.topics = []
        self.keywords = []
        self.engagement_metrics = {}
        self.question_text = ""
        self.thread_content = ""
        self.date_posted = None
    
    def _detect_platform(self) -> str:
        """Detect which platform the URL belongs to"""
        domain = urlparse(self.url).netloc
        
        for platform, domains in PLATFORM_DOMAINS.items():
            if any(d in domain for d in domains):
                return platform
        
        return "unknown"
    
    def __str__(self):
        return f"{self.title} | {self.platform} | Score: {self.relevance_score:.2f}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "platform": self.platform,
            "relevance_score": self.relevance_score,
            "complexity": self.complexity,
            "topics": self.topics,
            "keywords": self.keywords,
            "question_text": self.question_text,
            "engagement_metrics": self.engagement_metrics
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        """Create from dictionary"""
        result = cls(data["title"], data["url"], data["snippet"])
        result.platform = data["platform"]
        result.relevance_score = data["relevance_score"]
        result.complexity = data["complexity"]
        result.topics = data["topics"]
        result.keywords = data["keywords"]
        result.question_text = data.get("question_text", "")
        result.engagement_metrics = data.get("engagement_metrics", {})
        return result


def search_google(query: str, site: str = None, max_results: int = 10, lang: str = "en", 
                  country: str = "us", start: int = 0) -> List[dict]:
    """
    Perform a Google search using scraping (or SerpAPI if available).
    
    Args:
        query: The search query
        site: Site restriction (e.g., "site:reddit.com")
        max_results: Maximum number of results to return
        lang: Language code
        country: Country code
        start: Start index for pagination
        
    Returns:
        List of search result dictionaries
    """
    # Use SerpAPI if API key is available
    serpapi_key = os.environ.get("SERPAPI_KEY")
    if serpapi_key:
        return _search_with_serpapi(query, site, max_results, lang, country, start)
    
    # Fallback to scraping
    return _search_with_scraping(query, site, max_results, lang, country, start)


def _search_with_serpapi(query: str, site: str = None, max_results: int = 10, 
                         lang: str = "en", country: str = "us", start: int = 0) -> List[dict]:
    """Use SerpAPI to perform a search (more reliable but costs money)"""
    try:
        from serpapi import GoogleSearch
        
        search_query = query
        if site:
            search_query = f"{search_query} {site}"
        
        params = {
            "api_key": os.environ.get("SERPAPI_KEY"),
            "engine": "google",
            "q": search_query,
            "google_domain": f"google.{country}",
            "gl": country,
            "hl": lang,
            "num": min(max_results, 100),  # SerpAPI limits
            "start": start
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Process organic results
        if "organic_results" not in results:
            logger.warning("No organic results found in SerpAPI response")
            return []
        
        parsed_results = []
        for result in results["organic_results"][:max_results]:
            parsed_results.append({
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", "")
            })
            
        return parsed_results
    
    except Exception as e:
        logger.error(f"Error using SerpAPI: {str(e)}")
        logger.info("Falling back to scraping method")
        return _search_with_scraping(query, site, max_results, lang, country, start)


def _search_with_scraping(query: str, site: str = None, max_results: int = 10, 
                         lang: str = "en", country: str = "us", start: int = 0) -> List[dict]:
    """Use web scraping to perform a Google search (free but less reliable)"""
    try:
        # Build the search URL
        search_query = query
        if site:
            search_query = f"{search_query} {site}"
        
        search_url = (
            f"https://www.google.com/search"
            f"?q={requests.utils.quote(search_query)}"
            f"&hl={lang}"
            f"&gl={country}"
            f"&start={start}"
            f"&num={min(max_results, 100)}"  # Google typically limits to 100 max
        )
        
        # Get the search results page
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": f"{lang};q=0.8,en-US;q=0.5,en;q=0.3",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the results
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        result_blocks = soup.select("div.g")
        
        for block in result_blocks[:max_results]:
            try:
                title_element = block.select_one("h3")
                link_element = block.select_one("a")
                snippet_element = block.select_one("div.VwiC3b")
                
                if title_element and link_element:
                    title = title_element.text.strip()
                    url = link_element.get("href", "")
                    
                    # Google URLs are often redirects - extract the actual URL
                    if url.startswith("/url?"):
                        url = parse_qs(urlparse(url).query).get("q", [""])[0]
                    
                    snippet = snippet_element.text.strip() if snippet_element else ""
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            except Exception as e:
                logger.warning(f"Error parsing search result: {str(e)}")
                continue
        
        return results
    
    except Exception as e:
        logger.error(f"Error scraping Google search: {str(e)}")
        return []


def search_for_threads(query: str, platforms: List[str] = None, max_results: int = 10) -> List[SearchResult]:
    """
    Search for relevant threads using Google site: search across platforms.
    
    Args:
        query: The search query
        platforms: List of platforms to search (None for all supported platforms)
        max_results: Maximum results to return
        
    Returns:
        List of SearchResult objects with thread data
    """
    results = []
    platforms_to_search = platforms or list(PLATFORM_DOMAINS.keys())
    
    # Limit to supported platforms
    platforms_to_search = [p for p in platforms_to_search if p in PLATFORM_DOMAINS]
    
    # Calculate max results per platform
    results_per_platform = max(1, max_results // len(platforms_to_search))
    
    for platform in platforms_to_search:
        # Create site restriction string for this platform
        site_restrictions = []
        for domain in PLATFORM_DOMAINS[platform]:
            site_restrictions.append(f"site:{domain}")
        
        site_str = " OR ".join(site_restrictions)
        
        # Add extra platform-specific qualifiers to find question threads
        platform_qualifiers = ""
        if platform == "quora":
            platform_qualifiers = "?"  # Questions typically have question marks
        elif platform == "reddit":
            platform_qualifiers = "thread"
        elif platform == "stackexchange":
            platform_qualifiers = "question"
        
        # Perform the search
        platform_results = search_google(
            f"{query} {platform_qualifiers}",
            site=site_str,
            max_results=results_per_platform
        )
        
        # Convert to SearchResult objects
        for result in platform_results:
            search_result = SearchResult(
                title=result["title"],
                url=result["url"],
                snippet=result["snippet"],
                platform=platform
            )
            results.append(search_result)
    
    # Add additional metadata and score the results
    enrich_search_results(results, query)
    
    # Sort by relevance score
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    return results[:max_results]


def fetch_thread_content(search_result: SearchResult) -> Optional[str]:
    """
    Fetch the actual content of a thread from its URL.
    
    Args:
        search_result: The SearchResult object with the URL
        
    Returns:
        String of thread content or None if retrieval failed
    """
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = requests.get(search_result.url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse the content based on the platform
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if search_result.platform == "quora":
            # Extract Quora question and details
            question_elem = soup.select_one("div.q-box.qu-borderAll")
            content = ""
            
            if question_elem:
                content = question_elem.text.strip()
            
            # Fallback to title-based question
            if not content and search_result.title:
                content = search_result.title
                
            # Extract any additional context
            details_elem = soup.select_one("div.q-text")
            if details_elem:
                content += "\n\n" + details_elem.text.strip()
                
            search_result.question_text = content
                
        elif search_result.platform == "reddit":
            # Extract Reddit post content
            post_content = soup.select_one("div[data-test-id='post-content']")
            if post_content:
                content = post_content.text.strip()
                search_result.question_text = search_result.title
                search_result.thread_content = content
            else:
                # Old Reddit fallback
                post_content = soup.select_one("div.usertext-body")
                if post_content:
                    content = post_content.text.strip()
                    search_result.question_text = search_result.title
                    search_result.thread_content = content
        
        elif search_result.platform == "stackexchange":
            # Extract Stack Exchange question
            question_elem = soup.select_one("div.question")
            if question_elem:
                title_elem = question_elem.select_one("h1")
                body_elem = question_elem.select_one("div.s-prose")
                
                question_title = title_elem.text.strip() if title_elem else search_result.title
                question_body = body_elem.text.strip() if body_elem else ""
                
                search_result.question_text = question_title
                search_result.thread_content = question_body
                
        else:
            # Generic extraction for other platforms
            # Extract title if available
            title_elem = soup.select_one("h1") or soup.select_one("title")
            if title_elem:
                search_result.question_text = title_elem.text.strip()
            
            # Extract main content
            main_content = None
            for selector in ["article", "main", ".content", "#content", ".post", ".thread"]:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if main_content:
                search_result.thread_content = main_content.text.strip()
            else:
                # Fallback to body text
                search_result.thread_content = soup.get_text()
        
        # If we couldn't extract specific content, use the full page text
        if not search_result.question_text and not search_result.thread_content:
            page_text = soup.get_text()
            # Limit to reasonable size
            search_result.thread_content = page_text[:10000]
        
        # Extract engagement metrics if available
        extract_engagement_metrics(search_result, soup)
        
        # Extract date if available
        extract_date(search_result, soup)
        
        return search_result.thread_content
    
    except Exception as e:
        logger.error(f"Error fetching thread content from {search_result.url}: {str(e)}")
        return None


def extract_engagement_metrics(search_result: SearchResult, soup: BeautifulSoup) -> None:
    """Extract engagement metrics (upvotes, comments, views) from the page"""
    metrics = {}
    
    if search_result.platform == "quora":
        # Extract Quora metrics
        try:
            # Try to find answer count
            answer_count_elem = soup.select_one("div.q-text.qu-medium")
            if answer_count_elem and "answer" in answer_count_elem.text.lower():
                answer_text = answer_count_elem.text.lower()
                answer_count = re.search(r'(\d+)\s+answer', answer_text)
                if answer_count:
                    metrics["answers"] = int(answer_count.group(1))
                    
            # Try to find view count
            view_count_elem = soup.select_one("div.q-text.qu-color--gray")
            if view_count_elem and "view" in view_count_elem.text.lower():
                view_text = view_count_elem.text.lower()
                view_count = re.search(r'(\d+(?:,\d+)*)\s+view', view_text)
                if view_count:
                    metrics["views"] = int(view_count.group(1).replace(',', ''))
        except Exception as e:
            logger.debug(f"Error extracting Quora metrics: {str(e)}")
    
    elif search_result.platform == "reddit":
        # Extract Reddit metrics
        try:
            # Try to find upvotes
            upvote_elem = soup.select_one("div[data-test-id='post-content'] button[aria-label*='upvote']")
            if upvote_elem:
                upvote_text = upvote_elem.text.strip()
                if upvote_text and upvote_text.isdigit():
                    metrics["upvotes"] = int(upvote_text)
                    
            # Try to find comment count
            comment_elem = soup.select_one("span:contains('comments')")
            if comment_elem:
                comment_text = comment_elem.text.strip()
                comment_count = re.search(r'(\d+)\s+comments', comment_text)
                if comment_count:
                    metrics["comments"] = int(comment_count.group(1))
        except Exception as e:
            logger.debug(f"Error extracting Reddit metrics: {str(e)}")
    
    # Store the metrics
    search_result.engagement_metrics = metrics


def extract_date(search_result: SearchResult, soup: BeautifulSoup) -> None:
    """Extract the posting date from the page"""
    try:
        # Look for time elements or common date formats
        date_elem = soup.select_one("time") or soup.select_one("[datetime]")
        
        if date_elem:
            datetime_attr = date_elem.get("datetime")
            if datetime_attr:
                from datetime import datetime
                try:
                    search_result.date_posted = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                except Exception:
                    # Try to parse from text
                    search_result.date_posted = date_elem.text.strip()
        
        # Platform-specific date extraction fallbacks
        if not search_result.date_posted:
            if search_result.platform == "quora":
                date_elem = soup.select_one("span.q-text.qu-color--gray")
                if date_elem and ("answered" in date_elem.text.lower() or "asked" in date_elem.text.lower()):
                    search_result.date_posted = date_elem.text.strip()
            
            elif search_result.platform == "reddit":
                date_elem = soup.select_one("a[data-testid='post-timestamp']")
                if date_elem:
                    search_result.date_posted = date_elem.text.strip()
    
    except Exception as e:
        logger.debug(f"Error extracting date: {str(e)}")


def enrich_search_results(results: List[SearchResult], query: str) -> None:
    """
    Enrich search results with additional data and relevance scores.
    
    Args:
        results: List of SearchResult objects
        query: Original search query for relevance scoring
    """
    # Use concurrent.futures to fetch content in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit thread content fetch tasks
        future_to_result = {executor.submit(fetch_thread_content, result): result for result in results}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_result):
            result = future_to_result[future]
            try:
                # The future.result() contains the thread content or None
                _ = future.result()
            except Exception as e:
                logger.error(f"Error enriching result {result.url}: {str(e)}")
    
    # Add relevance scoring after content is fetched
    for result in results:
        result.relevance_score = calculate_relevance_score(result, query)


def calculate_relevance_score(result: SearchResult, query: str) -> float:
    """
    Calculate a relevance score for a search result based on multiple factors.
    
    Args:
        result: SearchResult object
        query: Original search query
        
    Returns:
        Relevance score between 0 and 1
    """
    # Start with base score
    score = 0.5
    
    # Split query into keywords
    query_keywords = set(query.lower().split())
    
    # Check title relevance
    title_words = set(result.title.lower().split())
    title_match_ratio = len(query_keywords.intersection(title_words)) / max(1, len(query_keywords))
    score += title_match_ratio * 0.2
    
    # Check question/content relevance
    content_text = (result.question_text + " " + result.thread_content).lower()
    
    # Count keyword occurrences in content
    keyword_occurrences = sum(content_text.count(keyword) for keyword in query_keywords)
    content_relevance = min(1.0, keyword_occurrences / (10 * max(1, len(query_keywords))))
    score += content_relevance * 0.2
    
    # Check if it's a question format
    if result.question_text and ('?' in result.question_text or any(question_word in result.question_text.lower() for question_word in ['how', 'what', 'why', 'when', 'where', 'which', 'who'])):
        score += 0.1
    
    # Recent content bonus (if date available)
    if result.date_posted:
        # If date is a string, just use it as a basic signal
        if isinstance(result.date_posted, str):
            recency_terms = ['hour', 'day', 'week', 'today', 'yesterday']
            if any(term in result.date_posted.lower() for term in recency_terms):
                score += 0.1
        else:
            # If it's a datetime, calculate actual recency
            from datetime import datetime, timedelta
            if datetime.now() - result.date_posted < timedelta(days=30):
                score += 0.1
            elif datetime.now() - result.date_posted < timedelta(days=180):
                score += 0.05
    
    # Engagement metrics bonus
    if result.engagement_metrics:
        # Answers or comments - shows active discussion
        answers = result.engagement_metrics.get('answers', 0) or result.engagement_metrics.get('comments', 0)
        if answers > 0:
            answer_bonus = min(0.15, answers / 20 * 0.1)
            score += answer_bonus
        
        # Views - shows interest level
        views = result.engagement_metrics.get('views', 0)
        if views > 0:
            view_bonus = min(0.1, views / 1000 * 0.05)
            score += view_bonus
    
    # Platform quality adjustment (some platforms have better content for different queries)
    platform_quality = {
        "quora": 0.05,
        "reddit": 0.05,
        "stackexchange": 0.1,
        "medium": 0.03,
        "unknown": -0.05
    }
    score += platform_quality.get(result.platform, 0)
    
    # Normalize the score to 0-1 range
    normalized_score = max(0.0, min(1.0, score))
    return normalized_score


def analyze_thread_relevance(results: List[SearchResult], query: str, threshold: float = 0.5) -> List[SearchResult]:
    """
    Filter search results by relevance score threshold.
    
    Args:
        results: List of SearchResult objects
        query: Original search query
        threshold: Minimum relevance score (0-1)
        
    Returns:
        Filtered list of SearchResult objects
    """
    # Ensure we've calculated relevance scores
    for result in results:
        if result.relevance_score == 0:
            result.relevance_score = calculate_relevance_score(result, query)
    
    # Filter by threshold
    filtered_results = [r for r in results if r.relevance_score >= threshold]
    
    # Sort by relevance score
    filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    return filtered_results


# Cache for search results to avoid redundant searches
_search_cache = {}

def cached_search_for_threads(query: str, platforms: List[str] = None, max_results: int = 10, 
                            use_cache: bool = True, cache_duration_hours: int = 24) -> List[SearchResult]:
    """
    Search for threads with caching to avoid redundant searches.
    
    Args:
        query: The search query
        platforms: List of platforms to search
        max_results: Maximum results to return
        use_cache: Whether to use the cache
        cache_duration_hours: How long to keep cached results valid
        
    Returns:
        List of SearchResult objects
    """
    global _search_cache
    
    # Create a cache key from the query and platforms
    cache_key = f"{query}_{','.join(sorted(platforms)) if platforms else 'all'}_{max_results}"
    
    # Check if we have a valid cached result
    if use_cache and cache_key in _search_cache:
        cached_entry = _search_cache[cache_key]
        cache_time, cache_results = cached_entry
        
        # Check if cache is still valid
        from datetime import datetime, timedelta
        if datetime.now() - cache_time < timedelta(hours=cache_duration_hours):
            logger.info(f"Using cached search results for '{query}'")
            return cache_results
    
    # Perform the search
    results = search_for_threads(query, platforms, max_results)
    
    # Cache the results
    if use_cache:
        from datetime import datetime
        _search_cache[cache_key] = (datetime.now(), results)
        
        # Clean up old cache entries
        current_time = datetime.now()
        expired_keys = [k for k, v in _search_cache.items() 
                       if current_time - v[0] > timedelta(hours=cache_duration_hours)]
        
        for key in expired_keys:
            del _search_cache[key]
    
    return results


# Function to save search results to a file
def save_search_results(results: List[SearchResult], filename: str) -> bool:
    """
    Save search results to a JSON file.
    
    Args:
        results: List of SearchResult objects
        filename: Path to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in results]
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_dicts, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(results)} search results to {filename}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving search results: {str(e)}")
        return False


# Function to load search results from a file
def load_search_results(filename: str) -> List[SearchResult]:
    """
    Load search results from a JSON file.
    
    Args:
        filename: Path to the file
        
    Returns:
        List of SearchResult objects
    """
    try:
        # Load from file
        with open(filename, 'r', encoding='utf-8') as f:
            result_dicts = json.load(f)
        
        # Convert dictionaries to SearchResult objects
        results = [SearchResult.from_dict(d) for d in result_dicts]
        
        logger.info(f"Loaded {len(results)} search results from {filename}")
        return results
    
    except Exception as e:
        logger.error(f"Error loading search results: {str(e)}")
        return []


if __name__ == "__main__":
    # Simple test of the search module
    query = "best restaurants in tokyo"
    results = search_for_threads(query, platforms=["quora", "reddit"], max_results=5)
    
    print(f"Search results for '{query}':")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title} ({result.platform}) - Score: {result.relevance_score:.2f}")
        print(f"   URL: {result.url}")
        print(f"   Snippet: {result.snippet[:100]}...")
        print()
    
    # Save results for testing
    save_search_results(results, "test_search_results.json")
