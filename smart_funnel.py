import os
import re
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from difflib import SequenceMatcher
from urllib.parse import urlparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try to import sitemap parser, create a minimal fallback if missing
try:
    from sitemap_parser import SitemapParser, SitemapPage
except ImportError:
    logger.warning("sitemap_parser module not found. Using fallback page class.")
    
    class SitemapPage:
        """Fallback class if sitemap_parser module is missing"""
        def __init__(self, url, title="", content_snippet=""):
            self.url = url
            self.title = title
            self.content_snippet = content_snippet
            self.categories = []
            self.tags = []

# Try to import OpenAI for content analysis
try:
    import openai
except ImportError:
    logger.warning("OpenAI library not found. Some content analysis features will be limited.")

# Classes for money site database structure
class SubPage:
    """Represents a subpage within a money site"""
    
    def __init__(self, url: str, title: str, categories: List[str] = None, 
                 keywords: List[str] = None, content_summary: str = ""):
        self.url = url
        self.title = title
        self.categories = categories or []
        self.keywords = keywords or []
        self.content_summary = content_summary
        self.relevance_score = 0.0
    
    def __str__(self):
        return f"{self.title} - {self.url}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "url": self.url,
            "title": self.title,
            "categories": self.categories,
            "keywords": self.keywords,
            "content_summary": self.content_summary
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SubPage":
        """Create from dictionary"""
        return cls(
            url=data["url"],
            title=data["title"],
            categories=data.get("categories", []),
            keywords=data.get("keywords", []),
            content_summary=data.get("content_summary", "")
        )
    
    @classmethod
    def from_sitemap_page(cls, sitemap_page: SitemapPage) -> "SubPage":
        """Create from a SitemapPage"""
        return cls(
            url=sitemap_page.url,
            title=sitemap_page.title or cls._extract_title_from_url(sitemap_page.url),
            categories=sitemap_page.categories or [],
            keywords=sitemap_page.tags or [],
            content_summary=sitemap_page.content_snippet or ""
        )
    
    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """Extract a title from the URL if no title is available"""
        parsed_url = urlparse(url)
        path = parsed_url.path
        segments = [s for s in path.split('/') if s]
        if segments:
            title = segments[-1].replace('-', ' ').replace('_', ' ').title()
            return title
        return parsed_url.netloc.replace('www.', '')


class MoneySite:
    """Represents a money site with multiple pages"""
    
    def __init__(self, name: str, primary_url: str, categories: List[str] = None,
                 target_audience: List[str] = None, pages: List[SubPage] = None):
        self.name = name
        self.primary_url = primary_url
        self.categories = categories or []
        self.target_audience = target_audience or []
        self.pages = pages or []
        self.parser = None  # Will hold SitemapParser if available
        self.relevance_score = 0.0
    
    def __str__(self):
        return f"{self.name} - {self.primary_url} ({len(self.pages)} pages)"
    
    def add_page(self, page: SubPage) -> None:
        """Add a subpage to the money site"""
        self.pages.append(page)
    
    def get_subpage_by_url(self, url: str) -> Optional[SubPage]:
        """Get a subpage by its URL"""
        for page in self.pages:
            if page.url == url:
                return page
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "primary_url": self.primary_url,
            "categories": self.categories,
            "target_audience": self.target_audience,
            "pages": [page.to_dict() for page in self.pages]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MoneySite":
        """Create from dictionary"""
        site = cls(
            name=data["name"],
            primary_url=data["primary_url"],
            categories=data.get("categories", []),
            target_audience=data.get("target_audience", [])
        )
        
        # Add pages
        for page_data in data.get("pages", []):
            site.add_page(SubPage.from_dict(page_data))
        
        return site
    
    def load_pages_from_sitemap(self, fetch_metadata: bool = True, metadata_limit: int = 20) -> bool:
        """Load pages from the site's sitemap"""
        try:
            # Import here to avoid circular imports
            from sitemap_parser import SitemapParser
            
            self.parser = SitemapParser(self.primary_url)
            sitemap_pages = self.parser.fetch_and_parse_all(
                fetch_metadata=fetch_metadata, 
                metadata_limit=metadata_limit
            )
            
            # Convert SitemapPage objects to SubPage objects
            for sitemap_page in sitemap_pages:
                # Create and add the subpage
                subpage = SubPage.from_sitemap_page(sitemap_page)
                
                # If categories are empty, use site categories as fallback
                if not subpage.categories:
                    subpage.categories = self.categories.copy()
                
                self.pages.append(subpage)
            
            logger.info(f"Loaded {len(self.pages)} pages from {self.primary_url}")
            return True
        
        except ImportError:
            logger.warning("SitemapParser not available. Cannot load real pages.")
            return False
        except Exception as e:
            logger.error(f"Error loading pages from {self.primary_url}: {str(e)}")
            return False
    
    def find_relevant_pages(self, query: str, limit: int = 5) -> List[Tuple[SubPage, float]]:
        """Find pages relevant to a query, with relevance scores"""
        # Try to use the parser's relevance function if available
        if self.parser:
            try:
                relevant_sitemap_pages = self.parser.get_relevant_pages(query, limit=limit)
                
                # Match with our SubPage objects and calculate scores
                scored_pages = []
                
                for sitemap_page in relevant_sitemap_pages:
                    # Find matching SubPage
                    matching_page = None
                    for subpage in self.pages:
                        if subpage.url == sitemap_page.url:
                            matching_page = subpage
                            break
                    
                    if matching_page:
                        # Calculate relevance score (0-1 scale)
                        query_terms = set(query.lower().split())
                        
                        # Count matches in title, URL, categories, keywords
                        matches = 0
                        total_terms = len(query_terms)
                        
                        title = matching_page.title.lower()
                        url = matching_page.url.lower()
                        cats = ' '.join(matching_page.categories).lower()
                        keys = ' '.join(matching_page.keywords).lower()
                        
                        for term in query_terms:
                            if term in title:
                                matches += 1
                            if term in url:
                                matches += 0.5
                            if term in cats:
                                matches += 0.7
                            if term in keys:
                                matches += 0.7
                        
                        # Normalize to 0-1
                        score = min(1.0, matches / (total_terms * 1.5))
                        
                        scored_pages.append((matching_page, score))
                
                # Sort by score
                scored_pages.sort(key=lambda x: x[1], reverse=True)
                
                return scored_pages
            
            except Exception as e:
                logger.warning(f"Error using parser relevance: {str(e)}")
                # Fall through to backup method
        
        # Backup method: basic matching
        query = query.lower()
        query_terms = set(query.split())
        
        # Score each page
        scored_pages = []
        
        for page in self.pages:
            score = 0.0
            
            # Title matching (most important)
            title = page.title.lower()
            for term in query_terms:
                if term in title:
                    score += 0.3
            
            # Exact phrase matches are worth more
            if query in title:
                score += 0.4
            
            # URL matching (less important)
            url = page.url.lower()
            for term in query_terms:
                if term in url:
                    score += 0.15
            
            # Category matching
            for category in page.categories:
                category = category.lower()
                for term in query_terms:
                    if term in category:
                        score += 0.1
            
            # Keyword matching
            for keyword in page.keywords:
                keyword = keyword.lower()
                for term in query_terms:
                    if term in keyword:
                        score += 0.1
            
            # Content summary matching
            content = page.content_summary.lower()
            for term in query_terms:
                if term in content:
                    score += 0.05
            
            # Only include pages with some relevance
            if score > 0:
                scored_pages.append((page, min(1.0, score)))
        
        # Sort by score
        scored_pages.sort(key=lambda x: x[1], reverse=True)
        
        return scored_pages[:limit]


class MoneySiteDatabase:
    """Database of money sites and their pages"""
    
    def __init__(self):
        self.sites: List[MoneySite] = []
    
    def add_site(self, site: MoneySite) -> None:
        """Add a money site to the database"""
        self.sites.append(site)
    
    def get_site_by_name(self, name: str) -> Optional[MoneySite]:
        """Get a site by its name"""
        for site in self.sites:
            if site.name.lower() == name.lower():
                return site
        return None
    
    def get_site_by_url(self, url: str) -> Optional[MoneySite]:
        """Get a site by checking if url belongs to it"""
        url_domain = self._extract_domain(url)
        
        for site in self.sites:
            site_domain = self._extract_domain(site.primary_url)
            if site_domain == url_domain:
                return site
        
        return None
    
    def get_all_subpages(self) -> List[SubPage]:
        """Get all subpages from all sites"""
        all_pages = []
        for site in self.sites:
            all_pages.extend(site.pages)
        return all_pages
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        url = url.lower()
        if url.startswith(('http://', 'https://')):
            url = url.split('://', 1)[1]
        
        domain = url.split('/', 1)[0]
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "sites": [site.to_dict() for site in self.sites]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MoneySiteDatabase":
        """Create from dictionary"""
        db = cls()
        
        # Add sites
        for site_data in data.get("sites", []):
            db.add_site(MoneySite.from_dict(site_data))
        
        return db
    
    def save_to_file(self, filename: str) -> bool:
        """Save database to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved money site database to {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving money site database: {str(e)}")
            return False
    
    @classmethod
    def load_from_file(cls, filename: str) -> Optional["MoneySiteDatabase"]:
        """Load database from a JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            db = cls.from_dict(data)
            logger.info(f"Loaded money site database from {filename} ({len(db.sites)} sites)")
            return db
        
        except Exception as e:
            logger.error(f"Error loading money site database: {str(e)}")
            return None


class ReferenceStrategy:
    """Strategy for referencing a money site in a response"""
    
    TYPE_DIRECT = "direct"           # Direct link with clear call to action
    TYPE_INDIRECT = "indirect"       # Mention of site without explicit call to action
    TYPE_INFORMATIONAL = "info"      # Reference as an information source
    TYPE_CONTEXTUAL = "contextual"   # Natural mention within context
    
    POSITION_EARLY = "early"         # In the first paragraph
    POSITION_MIDDLE = "middle"       # In the middle of the response
    POSITION_CONCLUSION = "conclusion"  # At the end as a conclusion or additional resource
    
    def __init__(self, thread, money_site: MoneySite, target_page: SubPage):
        self.thread = thread
        self.money_site = money_site
        self.target_page = target_page
        self.reference_type = self.TYPE_INFORMATIONAL
        self.reference_position = self.POSITION_CONCLUSION
        self.tone = "helpful"
        self.word_count = 150
        self.platform_customizations = {}
    
    def __str__(self):
        return (f"Reference Strategy: {self.reference_type} reference to {self.target_page.title} "
                f"({self.reference_position} position)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "reference_type": self.reference_type,
            "reference_position": self.reference_position,
            "tone": self.tone,
            "word_count": self.word_count,
            "platform_customizations": self.platform_customizations,
            "money_site_name": self.money_site.name,
            "target_page_url": self.target_page.url,
            "target_page_title": self.target_page.title
        }


# Main functions for the smart funnel module

def initialize_money_site_database(filename: str = None) -> MoneySiteDatabase:
    """
    Initialize and return the money site database.
    
    Args:
        filename: Optional file to load an existing database from
        
    Returns:
        Initialized MoneySiteDatabase
    """
    # Try to load from file if provided
    if filename and os.path.exists(filename):
        db = MoneySiteDatabase.load_from_file(filename)
        if db:
            return db
    
    # Create a new database
    db = MoneySiteDatabase()
    
    # Create money sites with real URLs
    create_money_sites(db)
    
    return db


def create_money_sites(db: MoneySiteDatabase) -> None:
    """Create money sites based on real websites"""
    
    # Define real money sites
    sites = [
        ("Living Abroad - Aparthotels", "https://aparthotel.com", 
         ["Aparthotels", "Rental Options", "Travel", "Living Abroad", "Local Living"],
         ["Expats", "Digital Nomads", "Business Travelers", "Long-term Travelers"]),
        
        ("Crypto Rentals", "https://cryptoapartments.com", 
         ["Cryptocurrency", "Rentals", "Digital Assets", "Travel", "Lifestyle"],
         ["Crypto Investors", "Digital Nomads", "Tech Enthusiasts", "Travelers"]),
        
        ("Serviced Apartments", "https://servicedapartments.net", 
         ["Serviced Apartments", "Corporate Housing", "Executive Stays", "Travel", "Relocation"],
         ["Business Travelers", "Executives", "Relocating Professionals", "Expat Families"]),
        
        ("Furnished Apartments", "https://furnishedapartments.net", 
         ["Furnished Rentals", "Turnkey Housing", "Temporary Housing", "Relocation"],
         ["Relocating Professionals", "Students", "Temporary Workers", "Transitional Housing Seekers"]),
        
        ("Real Estate Abroad", "https://realestateabroad.com", 
         ["International Property", "Property Investment", "Overseas Real Estate", "Foreign Markets"],
         ["Property Investors", "Retirees", "Second Home Buyers", "Expats"]),
        
        ("Property Developments", "https://propertydevelopments.com", 
         ["New Developments", "Off-Plan Properties", "Real Estate Projects", "Pre-Construction"],
         ["Investors", "First-time Buyers", "Property Flippers", "Developers"]),
        
        ("Property Investment", "https://propertyinvestment.net", 
         ["Property Investment", "Real Estate Strategy", "Rental Yields", "Portfolio Building"],
         ["Property Investors", "Portfolio Builders", "Buy-to-Let Owners", "Investment Strategists"]),
        
        ("Golden Visa Opportunities", "https://golden-visa.com", 
         ["Golden Visa", "Investment Immigration", "Residence by Investment", "Investor Visas"],
         ["High Net Worth Individuals", "Investors", "Immigration Planners", "Global Citizens"]),
        
        ("Residence by Investment", "https://residence-by-investment.com", 
         ["Residence Programs", "Investment Immigration", "Global Residency", "Second Residency"],
         ["Investors", "Global Mobility Seekers", "Tax Planners", "Business Owners"]),
        
        ("Citizenship by Investment", "https://citizenship-by-investment.net", 
         ["Citizenship Programs", "Passport Investment", "Economic Citizenship", "Dual Nationality"],
         ["Ultra High Net Worth Individuals", "Global Investors", "Travel Freedom Seekers", "Political Stability Seekers"])
    ]
    
    # Create and add each site
    for name, url, categories, audience in sites:
        site = MoneySite(
            name=name,
            primary_url=url,
            categories=categories,
            target_audience=audience
        )
        
        # Try to load pages from real sitemap
        try:
            success = site.load_pages_from_sitemap()
            if not success:
                # If loading from sitemap fails, create sample pages
                create_sample_pages_for_site(site)
        except:
            # Fallback to sample pages
            create_sample_pages_for_site(site)
        
        # Add to database
        db.add_site(site)


def create_sample_pages_for_site(site: MoneySite) -> None:
    """Create sample pages for a site when real sitemap loading fails"""
    logger.info(f"Creating sample pages for {site.name}")
    
    # Generic pages for all sites
    site.add_page(SubPage(
        url=f"{site.primary_url}/",
        title=f"{site.name} - Home",
        categories=site.categories,
        keywords=[],
        content_summary=f"Homepage for {site.name} featuring top destinations and investment opportunities."
    ))
    
    site.add_page(SubPage(
        url=f"{site.primary_url}/about/",
        title=f"About {site.name}",
        categories=site.categories,
        keywords=[],
        content_summary=f"About {site.name} and our mission to help you find the best opportunities."
    ))
    
    site.add_page(SubPage(
        url=f"{site.primary_url}/blog/",
        title=f"{site.name} Blog",
        categories=site.categories,
        keywords=[],
        content_summary=f"Latest articles and guides from {site.name}."
    ))
    
    # Generate specific sample pages based on site type
    if "Apartments" in site.name or "Aparthotels" in site.name:
        # Apartment/accommodation related sites
        locations = ["Tokyo", "Bangkok", "Singapore", "Dubai", "London", "New York", "Paris"]
        
        for location in locations:
            site.add_page(SubPage(
                url=f"{site.primary_url}/{location.lower()}/",
                title=f"{location} {site.name.split('-')[0].strip()}",
                categories=[location, "Accommodation", "Housing"],
                keywords=[f"{location.lower()} apartments", f"{location.lower()} accommodation", "expat housing"],
                content_summary=f"Complete guide to {site.name.split('-')[0].strip()} in {location} including neighborhoods, pricing, and amenities for long-term stays."
            ))
    
    elif "Investment" in site.name or "Real Estate" in site.name:
        # Real estate/investment related sites
        markets = ["Japan", "Thailand", "Portugal", "Spain", "Dubai", "Malaysia", "Greece"]
        
        for market in markets:
            site.add_page(SubPage(
                url=f"{site.primary_url}/markets/{market.lower()}/",
                title=f"{market} {site.name} Guide",
                categories=[market, "Investment", "Real Estate"],
                keywords=[f"{market.lower()} property", f"{market.lower()} real estate", f"{market.lower()} investment"],
                content_summary=f"Comprehensive guide to {site.name} opportunities in {market} with market analysis, legal requirements, and ROI projections."
            ))
    
    elif "Visa" in site.name or "Citizenship" in site.name:
        # Visa/citizenship related sites
        countries = ["Portugal", "Spain", "Greece", "Cyprus", "Turkey", "Malta", "Caribbean", "Vanuatu"]
        
        for country in countries:
            site.add_page(SubPage(
                url=f"{site.primary_url}/programs/{country.lower()}/",
                title=f"{country} {site.name} Program",
                categories=[country, "Investment Migration", "Residence Program"],
                keywords=[f"{country.lower()} golden visa", f"{country.lower()} citizenship", f"{country.lower()} residency"],
                content_summary=f"Detailed guide to {country}'s {site.name} program including investment options, application process, and pathway to citizenship."
            ))


def analyze_question_complexity(question_text: str) -> int:
    """
    Analyze the complexity of a question to determine appropriate response strategy.
    
    Args:
        question_text: The question text
        
    Returns:
        Complexity score from 1 (simple) to 5 (complex)
    """
    # Default complexity
    complexity = 3
    
    # Length factor (longer questions are often more complex)
    words = question_text.split()
    if len(words) < 8:
        complexity -= 1
    elif len(words) > 20:
        complexity += 1
    
    # Multi-part questions
    if question_text.count('?') > 1:
        complexity += 1
    
    # Complexity indicators
    complex_indicators = [
        'compare', 'difference', 'analysis', 'implications',
        'complex', 'complicated', 'detailed', 'comprehensive',
        'explain', 'why', 'how', 'implications', 'factors'
    ]
    
    # Simple indicators
    simple_indicators = [
        'best', 'top', 'list', 'simple', 'easy',
        'quick', 'basic', 'beginner', 'start'
    ]
    
    # Check for indicators
    question_lower = question_text.lower()
    for indicator in complex_indicators:
        if indicator in question_lower:
            complexity += 1
            break
    
    for indicator in simple_indicators:
        if indicator in question_lower:
            complexity -= 1
            break
    
    # Ensure within range
    return max(1, min(5, complexity))


def match_question_to_money_site(question_text: str, search_result, 
                                money_site_db: MoneySiteDatabase) -> List[Tuple[MoneySite, float]]:
    """
    Match a question to the most relevant money sites.
    
    Args:
        question_text: The question text
        search_result: SearchResult object with additional context
        money_site_db: Money site database
        
    Returns:
        List of (MoneySite, relevance_score) tuples, sorted by relevance
    """
    # Get all sites from the database
    all_sites = money_site_db.sites
    
    # Calculate text for relevance matching
    matching_text = f"{question_text} {search_result.title} {search_result.thread_content}"
    
    # Score each site for relevance
    site_scores = []
    
    for site in all_sites:
        # Find relevant pages for this site
        relevant_pages = site.find_relevant_pages(matching_text, limit=3)
        
        # Skip sites with no relevant pages
        if not relevant_pages:
            continue
        
        # Use the best page's score as the site's score
        best_page_score = relevant_pages[0][1] if relevant_pages else 0
        
        # Boost score based on category and audience matches
        query_terms = set(matching_text.lower().split())
        
        category_match = 0
        for category in site.categories:
            category_words = set(category.lower().split())
            matches = len(query_terms.intersection(category_words))
            category_match = max(category_match, matches / max(1, len(category_words)))
        
        audience_match = 0
        for audience in site.target_audience:
            audience_words = set(audience.lower().split())
            matches = len(query_terms.intersection(audience_words))
            audience_match = max(audience_match, matches / max(1, len(audience_words)))
        
        # Calculate final score with weights
        final_score = (
            best_page_score * 0.6 +  # Page relevance is most important
            category_match * 0.25 +  # Category match is next
            audience_match * 0.15    # Audience match is least important
        )
        
        site_scores.append((site, final_score))
    
    # If no relevant sites found, fall back to basic matching
    if not site_scores:
        for site in all_sites:
            # Simple matching against site name and categories
            site_text = f"{site.name} {' '.join(site.categories)} {' '.join(site.target_audience)}"
            site_text = site_text.lower()
            
            # Calculate basic similarity
            similarity = SequenceMatcher(None, matching_text.lower(), site_text).ratio()
            site_scores.append((site, similarity * 0.5))  # Lower base score for fallback method
    
    # Sort by score in descending order
    site_scores.sort(key=lambda x: x[1], reverse=True)
    
    return site_scores


def find_best_subpage(site: MoneySite, question_text: str, search_result) -> List[Tuple[SubPage, float]]:
    """
    Find the most relevant subpages within a money site.
    
    Args:
        site: Money site to search within
        question_text: The question text
        search_result: SearchResult with additional context
        
    Returns:
        List of (SubPage, relevance_score) tuples, sorted by relevance
    """
    # Calculate text for relevance matching
    matching_text = f"{question_text} {search_result.title} {search_result.thread_content}"
    
    # Use the site's relevance function if available
    return site.find_relevant_pages(matching_text, limit=5)


def generate_reference_strategy(thread, money_site: MoneySite, target_page: SubPage,
                              question_complexity: int, platform: str, 
                              subpage_relevance: float) -> ReferenceStrategy:
    """
    Generate a strategy for referencing the money site in the response.
    
    Args:
        question_complexity: Complexity score (1-5)
        platform: Target platform
        subpage_relevance: Relevance score of the subpage
        
    Returns:
        ReferenceStrategy object with appropriate settings
    """
    strategy = ReferenceStrategy(thread, money_site, target_page)
    
    # Set reference type based on relevance and complexity
    if subpage_relevance >= 0.8:
        # Highly relevant - can be more direct
        if question_complexity >= 4:
            strategy.reference_type = ReferenceStrategy.TYPE_INFORMATIONAL
        else:
            strategy.reference_type = ReferenceStrategy.TYPE_DIRECT
    elif subpage_relevance >= 0.6:
        # Moderately relevant
        if question_complexity >= 3:
            strategy.reference_type = ReferenceStrategy.TYPE_INFORMATIONAL
        else:
            strategy.reference_type = ReferenceStrategy.TYPE_INDIRECT
    else:
        # Less relevant - be more subtle
        strategy.reference_type = ReferenceStrategy.TYPE_CONTEXTUAL
    
    # Set position based on platform and complexity
    if platform == "quora":
        if question_complexity >= 4:
            # Complex questions benefit from providing context first
            strategy.reference_position = ReferenceStrategy.POSITION_MIDDLE
        else:
            strategy.reference_position = ReferenceStrategy.POSITION_CONCLUSION
    
    elif platform == "reddit":
        # Reddit users often prefer information first, then sources
        strategy.reference_position = ReferenceStrategy.POSITION_CONCLUSION
        
        # For highly relevant content on a complex question, can use earlier positioning
        if subpage_relevance >= 0.8 and question_complexity >= 4:
            strategy.reference_position = ReferenceStrategy.POSITION_MIDDLE
    
    elif platform == "stackexchange":
        # Stack Exchange values information upfront with references
        strategy.reference_position = ReferenceStrategy.POSITION_EARLY
    
    else:
        # Default positioning
        strategy.reference_position = ReferenceStrategy.POSITION_CONCLUSION
    
    # Set word count based on complexity
    if question_complexity <= 2:
        strategy.word_count = 100
    elif question_complexity <= 3:
        strategy.word_count = 150
    elif question_complexity <= 4:
        strategy.word_count = 250
    else:
        strategy.word_count = 350
    
    # Set tone based on platform
    if platform == "reddit":
        strategy.tone = "conversational"
    elif platform == "stackexchange":
        strategy.tone = "professional"
    elif platform == "quora":
        strategy.tone = "authoritative"
    else:
        strategy.tone = "helpful"
    
    # Add platform-specific customizations
    if platform == "reddit":
        strategy.platform_customizations = {
            "use_markdown": True,
            "avoid_self_promotion": True,
            "include_tldr": question_complexity >= 4
        }
    elif platform == "quora":
        strategy.platform_customizations = {
            "include_credentials": True,
            "use_paragraphs": True
        }
    elif platform == "stackexchange":
        strategy.platform_customizations = {
            "include_code_examples": "tech" in question_text.lower(),
            "reference_documentation": True
        }
    
    return strategy


def generate_reference_text(strategy: ReferenceStrategy) -> str:
    """
    Generate text for referencing the money site based on the provided strategy.
    
    Args:
        strategy: ReferenceStrategy to use
        
    Returns:
        Generated reference text
    """
    site = strategy.money_site
    page = strategy.target_page
    
    # Base template based on reference type
    if strategy.reference_type == ReferenceStrategy.TYPE_DIRECT:
        # Direct reference with call to action
        templates = [
            f"For detailed information on this topic, check out {page.title} on {site.name} ({page.url}).",
            f"If you want to learn more, {site.name} has a great guide on this: {page.title} ({page.url}).",
            f"I recommend reading the comprehensive guide on {page.title} available at {site.name} ({page.url}).",
            f"For a step-by-step approach, you might find {page.title} from {site.name} helpful ({page.url})."
        ]
    
    elif strategy.reference_type == ReferenceStrategy.TYPE_INDIRECT:
        # Indirect mention without explicit call to action
        templates = [
            f"There's some good information about this on {site.name} in their article about {page.title}.",
            f"{site.name} explores this topic in depth through their resource on {page.title}.",
            f"The team at {site.name} has written about {page.title}, which covers similar concepts.",
            f"I've found the material on {page.title} from {site.name} to be quite informative on this subject."
        ]
    
    elif strategy.reference_type == ReferenceStrategy.TYPE_INFORMATIONAL:
        # Reference as information source
        templates = [
            f"According to {site.name}'s guide on {page.title}, the key factors to consider are...",
            f"Based on information from {site.name}'s article on {page.title}, it appears that...",
            f"Research from {site.name} on {page.title} suggests that...",
            f"As outlined in {site.name}'s resource on {page.title}, the general approach involves..."
        ]
    
    else:  # TYPE_CONTEXTUAL
        # Natural mention within context
        templates = [
            f"This reminds me of a point made in an article about {page.title} I read on {site.name}.",
            f"When looking into this previously, I came across some insights on {site.name} related to {page.title}.",
            f"There's an interesting perspective on this in {site.name}'s coverage of {page.title}.",
            f"This approach is similar to what's discussed in {site.name}'s take on {page.title}."
        ]
    
    # Select a template based on thread context to avoid repetition
    # For simplicity, just use random selection here
    import random
    reference_text = random.choice(templates)
    
    # Apply platform-specific customizations
    if strategy.platform_customizations.get("use_markdown", False):
        # Convert URL to markdown format
        reference_text = reference_text.replace(
            f"({page.url})",
            f"[{page.title}]({page.url})"
        )
    
    if strategy.platform_customizations.get("include_credentials", False):
        # Add expertise signal if appropriate
        if "Investment" in site.name or "Real Estate" in site.name:
            reference_text += " Their team includes real estate investment specialists with market experience."
        elif "Visa" in site.name or "Citizenship" in site.name:
            reference_text += " They work with immigration lawyers who specialize in investment programs."
        elif "Apartments" in site.name or "Aparthotels" in site.name:
            reference_text += " They have a network of accommodation partners across major global cities."
    
    return reference_text


def process_question(question_text: str, thread=None, platform: str = "general") -> Dict[str, Any]:
    """
    Process a question to identify relevant money sites and generate response strategy.
    
    Args:
        question_text: Question text to process
        thread: Optional thread context
        platform: Platform the question is from (e.g., "reddit", "quora")
        
    Returns:
        Dictionary with processing results including reference strategy
    """
    # Initialize result dictionary
    result = {
        "question": question_text,
        "platform": platform,
        "has_relevant_site": False,
        "reference_strategy": None,
        "money_site": None,
        "target_page": None
    }
    
    # Load money site database
    db_path = os.path.join(os.path.dirname(__file__), "money_sites.json")
    money_site_db = initialize_money_site_database(db_path)
    
    # Create a mock search result if no thread provided
    # In a real implementation, this would extract context from the thread
    class MockSearchResult:
        def __init__(self, title="", thread_content=""):
            self.title = title
            self.thread_content = thread_content
    
    search_result = MockSearchResult()
    if thread:
        # Extract context from thread
        search_result.title = getattr(thread, "title", "")
        search_result.thread_content = getattr(thread, "content", "")
    
    # Analyze question complexity
    complexity = analyze_question_complexity(question_text)
    result["question_complexity"] = complexity
    
    # Match question to money sites
    site_matches = match_question_to_money_site(question_text, search_result, money_site_db)
    
    # Check if we have relevant matches
    if site_matches and site_matches[0][1] >= 0.4:  # Minimum relevance threshold
        best_site_match = site_matches[0]
        site = best_site_match[0]
        site_relevance = best_site_match[1]
        
        # Find best subpage
        subpage_matches = find_best_subpage(site, question_text, search_result)
        
        if subpage_matches:
            best_subpage_match = subpage_matches[0]
            target_page = best_subpage_match[0]
            subpage_relevance = best_subpage_match[1]
            
            # Generate reference strategy
            strategy = generate_reference_strategy(
                thread, site, target_page,
                complexity, platform, subpage_relevance
            )
            
            # Generate reference text
            reference_text = generate_reference_text(strategy)
            
            # Update result
            result["has_relevant_site"] = True
            result["money_site"] = site
            result["target_page"] = target_page
            result["reference_strategy"] = strategy
            result["reference_text"] = reference_text
            result["site_relevance"] = site_relevance
            result["subpage_relevance"] = subpage_relevance
    
    return result


def generate_response_with_reference(question_text: str, reference_result: Dict[str, Any]) -> str:
    """
    Generate a complete response with the reference integrated according to the strategy.
    
    Args:
        question_text: Question text
        reference_result: Result from process_question function
        
    Returns:
        Complete response text with integrated reference
    """
    # If no relevant money site was found, return a simple response
    if not reference_result.get("has_relevant_site", False):
        return generate_generic_response(question_text, reference_result["question_complexity"])
    
    # Get key information
    strategy = reference_result["reference_strategy"]
    reference_text = reference_result["reference_text"]
    complexity = reference_result["question_complexity"]
    
    # Generate response based on complexity
    if complexity <= 2:
        # Simple, direct response
        main_response = generate_simple_response(question_text)
    elif complexity <= 3:
        # Moderate complexity
        main_response = generate_moderate_response(question_text)
    else:
        # Complex response
        main_response = generate_complex_response(question_text)
    
    # Adjust response length to strategy word count
    target_words = strategy.word_count
    current_words = len(main_response.split())
    
    if current_words > target_words * 1.2:
        # Response is too long, trim it
        main_response = " ".join(main_response.split()[:target_words])
        # Ensure we don't cut mid-sentence
        if not main_response.endswith((".", "!", "?")):
            main_response = main_response.rsplit(".", 1)[0] + "."
    
    # Position the reference according to strategy
    if strategy.reference_position == ReferenceStrategy.POSITION_EARLY:
        # Place reference at the beginning
        response = f"{reference_text}\n\n{main_response}"
    
    elif strategy.reference_position == ReferenceStrategy.POSITION_MIDDLE:
        # Split response and place reference in the middle
        sentences = main_response.split(". ")
        midpoint = len(sentences) // 2
        
        first_half = ". ".join(sentences[:midpoint]) + "."
        second_half = ". ".join(sentences[midpoint:])
        
        response = f"{first_half}\n\n{reference_text}\n\n{second_half}"
    
    else:  # POSITION_CONCLUSION
        # Place reference at the end
        response = f"{main_response}\n\n{reference_text}"
    
    # Apply platform customizations
    if strategy.platform_customizations.get("include_tldr", False):
        # Add a TL;DR at the beginning for longer responses
        words = question_text.split()
        topic = " ".join(words[:min(5, len(words))])
        response = f"TL;DR: {topic} - {reference_result['target_page'].title}\n\n{response}"
    
    return response


def generate_generic_response(question_text: str, complexity: int) -> str:
    """
    Generate a generic response when no relevant money site is found.
    
    Args:
        question_text: Question text
        complexity: Question complexity score
        
    Returns:
        Generic response
    """
    # Very basic response generator
    # In a real implementation, this would use more sophisticated NLP
    
    # Extract key terms for personalization
    terms = question_text.lower().split()
    topic = next((term for term in terms if term in [
        "investment", "property", "real estate", "apartment", "rental",
        "visa", "residence", "citizenship", "living abroad", "expat"
    ]), "this topic")
    
    if complexity <= 2:
        return f"Regarding {topic}, there are several key factors to consider. " \
               f"First, it's important to research the specific requirements and options available. " \
               f"Second, consulting with a specialist can provide valuable insights tailored to your situation. " \
               f"Finally, take time to compare different approaches before making a decision."
    
    elif complexity <= 3:
        return f"When it comes to {topic}, the answer depends on several factors including your specific goals, " \
               f"timeline, and budget constraints. Generally, it's advisable to begin with thorough research on " \
               f"the current market conditions and regulatory environment. Many people find success by working " \
               f"with established professionals who specialize in this area and can provide personalized guidance. " \
               f"Consider also joining relevant online communities where you can learn from others' experiences."
    
    else:
        return f"Addressing your question about {topic} requires a nuanced approach. Various factors come into play, " \
               f"including current market trends, regulatory frameworks, and your individual circumstances. " \
               f"From a strategic perspective, it's worth considering both short-term advantages and long-term implications. " \
               f"Many experts in this field recommend starting with a comprehensive assessment of your objectives, followed by " \
               f"systematic research into available options. This typically includes evaluating cost-benefit ratios, " \
               f"understanding legal requirements, and identifying potential obstacles. " \
               f"For optimal results, consider consulting with specialists who can provide tailored advice based on " \
               f"your specific situation and goals."


def generate_simple_response(question_text: str) -> str:
    """Generate a simple response for low complexity questions"""
    # In a real implementation, this would use templates or NLP models
    return generate_generic_response(question_text, 1)


def generate_moderate_response(question_text: str) -> str:
    """Generate a moderate response for medium complexity questions"""
    return generate_generic_response(question_text, 3)


def generate_complex_response(question_text: str) -> str:
    """Generate a complex response for high complexity questions"""
    return generate_generic_response(question_text, 5)


# Main entry point for using the module
def handle_question(question_text: str, thread=None, platform: str = "general") -> str:
    """
    Main function to handle a question and generate a response with money site reference.
    
    Args:
        question_text: Question text
        thread: Optional thread context
        platform: Platform the question is from
        
    Returns:
        Complete response with money site reference if relevant
    """
    try:
        # Process the question
        result = process_question(question_text, thread, platform)
        
        # Generate response with reference
        response = generate_response_with_reference(question_text, result)
        
        # Log processing details
        if result.get("has_relevant_site", False):
            logger.info(
                f"Generated response for question with reference to {result['money_site'].name} "
                f"(relevance: {result.get('site_relevance', 0):.2f})"
            )
        else:
            logger.info("Generated generic response (no relevant money site found)")
        
        return response
    
    except Exception as e:
        logger.error(f"Error handling question: {str(e)}")
        # Fallback to very simple response in case of errors
        return "I apologize, but I'm having trouble processing your question. Could you please rephrase or provide more details?"


# If the module is run directly, provide a simple CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Funnel for Q&A platforms")
    parser.add_argument("--question", "-q", type=str, help="Question to process")
    parser.add_argument("--platform", "-p", type=str, default="general", 
                        choices=["general", "reddit", "quora", "stackexchange"],
                        help="Platform the question is from")
    parser.add_argument("--init-db", action="store_true", help="Initialize money site database")
    
    args = parser.parse_args()
    
    if args.init_db:
        db = initialize_money_site_database()
        db.save_to_file("money_sites.json")
        print(f"Initialized money site database with {len(db.sites)} sites")
    
    elif args.question:
        response = handle_question(args.question, platform=args.platform)
        print("\nQuestion:", args.question)
        print("\nResponse:", response)
    
    else:
        print("Interactive mode. Type 'exit' to quit.")
        platform = args.platform
        
        while True:
            question = input("\nEnter question: ")
            if question.lower() in ["exit", "quit"]:
                break
            
            response = handle_question(question, platform=platform)
            print("\nResponse:", response)

def create_smart_funnel_for_thread(thread, money_site_db):
    """
    Create a smart funnel reference strategy for a thread.
    
    Args:
        thread: The search result or thread to analyze
        money_site_db: The money site database
        
    Returns:
        ReferenceStrategy object or None if no match found
    """
    question_text = thread.question_text or thread.title
    
    # Process the question to find relevant money site and strategy
    result = process_question(question_text, thread, thread.platform)
    
    if result["has_relevant_site"]:
        return result["reference_strategy"]
    
    return None
