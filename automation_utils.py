import undetected_chromedriver as uc
import random
import time
import requests
import openai
import subprocess
import socket
from packaging.version import Version as LooseVersion
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import shutil
import os
import tempfile
import logging
import re
import json
from stem import Signal
from stem.control import Controller
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# List of diverse and recent User-Agent strings
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # macOS Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Windows Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.83",
    # Mobile User Agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S928U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.143 Mobile Safari/537.36",
]

# Browser viewport sizes to randomize
VIEWPORT_SIZES = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
    (1680, 1050)
]

def _rotate_user_agent():
    """Return a random user agent from the list."""
    return random.choice(USER_AGENTS)

def _random_viewport_size():
    """Return a random viewport size."""
    return random.choice(VIEWPORT_SIZES)

def _randomize_typing_speed(text, min_delay=0.05, max_delay=0.2):
    """
    Returns a function that will type text with random delays between keystrokes.
    """
    delays = [random.uniform(min_delay, max_delay) for _ in range(len(text))]
    return zip(text, delays)

def simulate_human_behavior(driver, element=None):
    """
    Simulates human behavior such as random scrolling and mouse movements.
    """
    try:
        # Random scroll
        scroll_amount = random.randint(100, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))
        
        # Random mouse movements if an element is provided
        if element:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(
                element, 
                random.randint(-10, 10), 
                random.randint(-10, 10)
            )
            actions.perform()
            time.sleep(random.uniform(0.3, 0.7))
        
        # Sometimes move mouse to a random position on the page
        if random.random() < 0.3:
            x_position = random.randint(100, 700)
            y_position = random.randint(100, 500)
            driver.execute_script(f"document.elementFromPoint({x_position}, {y_position}).scrollIntoView({{behavior: 'smooth', block: 'center'}});")
            time.sleep(random.uniform(0.2, 0.8))
    except Exception as e:
        logger.debug(f"Error in human behavior simulation: {e}")

def get_next_tor_identity():
    """
    Request a new identity from the Tor network.
    """
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            logger.info("Successfully requested new Tor identity")
            time.sleep(5)  # Wait for the new identity to be established
    except Exception as e:
        logger.error(f"Error requesting new Tor identity: {e}")

def test_proxy_connection(proxy=None):
    """
    Test if the proxy connection is working.
    Returns the external IP if successful, None otherwise.
    """
    try:
        session = requests.Session()
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy
            }
        
        response = session.get("https://api.ipify.org?format=json", timeout=10)
        data = response.json()
        logger.info(f"Current external IP: {data['ip']}")
        return data['ip']
    except Exception as e:
        logger.error(f"Error testing proxy connection: {e}")
        return None

def init_driver(proxy_address=None):
    """
    Initialize a Chrome driver with anti-detection measures.
    """
    logger.info('[init_driver] Initializing driver...')
    try:
        options = uc.ChromeOptions()
        
        # Check CHROME_HEADLESS env variable (default true)
        headless = os.environ.get("CHROME_HEADLESS", "true").lower() == "true"
        if headless:
            options.add_argument("--headless=new")
        
        # Anti-detection measures
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        
        # Randomize user agent
        ua = _rotate_user_agent()
        options.add_argument(f"--user-agent={ua}")
        
        # Set random viewport size
        width, height = _random_viewport_size()
        options.add_argument(f"--window-size={width},{height}")
        
        # Additional anti-fingerprinting measures
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-site-isolation-trials")
        
        # Language and locale randomization
        locales = ["en-US", "en-GB", "en-CA", "en-AU"]
        options.add_argument(f"--lang={random.choice(locales)}")
        
        # Set proxy if provided
        if proxy_address:
            options.add_argument(f"--proxy-server={proxy_address}")
        
        # Set binary location explicitly for containerized environments
        chrome_binary_path = '/usr/bin/google-chrome-stable'
        options.binary_location = chrome_binary_path
        
        logger.info(f'[init_driver] Using Chrome binary at: {chrome_binary_path}')
        
        # Find chromedriver
        chromedriver_path = '/usr/local/bin/chromedriver'
        logger.info(f'[init_driver] Using chromedriver at: {chromedriver_path}')
        
        # Create the Chrome driver with explicit paths
        driver = uc.Chrome(
            options=options,
            browser_executable_path=chrome_binary_path,
            driver_executable_path=chromedriver_path,
            use_subprocess=False
        )
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        # Apply additional anti-detection JavaScript
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                // Overwrite the 'webdriver' property to prevent detection
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Overwrite the navigator permissions property
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Prevent detection via plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const plugins = [];
                        for (let i = 0; i < 3; i++) {
                            plugins.push({
                                name: `Plugin ${i}`,
                                description: `Description ${i}`,
                                filename: `plugin${i}.dll`,
                                length: 1
                            });
                        }
                        return plugins;
                    }
                });
                
                // Add a fake touch points function
                const originalHasTouchPoints = navigator.maxTouchPoints;
                Object.defineProperty(navigator, 'maxTouchPoints', {
                    get: () => Math.floor(Math.random() * 2) === 0 ? 0 : 1
                });
                
                // Add fake device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => Math.floor(Math.random() * 8) + 4
                });
            """
        })
        
        logger.info('[init_driver] Driver initialized successfully with anti-detection measures.')
        return driver
    except Exception as e:
        logger.error(f'[init_driver] Error initializing driver: {e}')
        logger.exception(e)
        raise

def close_driver(driver):
    """
    Safely close the browser driver.
    """
    logger.info('[close_driver] Closing driver...')
    try:
        driver.quit()
        logger.info('[close_driver] Driver closed successfully.')
    except Exception as e:
        logger.error(f'[close_driver] Error closing driver: {e}')
        logger.exception(e)

def search_google(query, max_results=5, proxy=None):
    """
    Search Google for relevant threads using the given query.
    """
    logger.info(f'[search_google] Searching for: {query}')
    driver = init_driver(proxy)
    results = []
    try:
        # Add randomization to search URL
        search_params = {
            'q': query,
            'hl': random.choice(['en', 'en-US', 'en-GB']),
            'gl': random.choice(['us', 'uk', 'ca', 'au']),
            'pws': '0'  # Disable personalized search
        }
        
        search_url = f"https://www.google.com/search?{requests.compat.urlencode(search_params)}"
        driver.get(search_url)
        
        # Simulate human behavior with random delays and scrolling
        time.sleep(random.uniform(1, 3))
        simulate_human_behavior(driver)
        
        # Look for results with different selectors
        result_selectors = [
            "div.yuRUbf a",  # Standard search results
            "div.g div.yuRUbf a",  # Alternative selector
            "div[jscontroller] a[jsname][data-ved][ping]"  # Another possible selector
        ]
        
        for selector in result_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                break
        
        for element in elements[:max_results]:
            simulate_human_behavior(driver, element)
            url = element.get_attribute("href")
            results.append(url)
        
        logger.info(f'[search_google] Found {len(results)} results')
    except Exception as e:
        logger.error(f"[search_google] Error during search: {e}")
    finally:
        close_driver(driver)
    return results

def extract_thread_content(url, proxy=None):
    """
    Extract content from a thread URL with advanced parsing.
    """
    logger.info(f'[extract_thread_content] Extracting content from: {url}')
    driver = init_driver(proxy)
    content = ""
    try:
        driver.get(url)
        
        # Simulate human behavior with random delays
        time.sleep(random.uniform(2, 4))
        simulate_human_behavior(driver)
        
        # Determine the domain to use appropriate extraction strategy
        domain = re.search(r'https?://(?:www\.)?([^/]+)', url).group(1)
        
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        if "quora.com" in domain:
            # Extract Quora question
            question_selectors = [
                "div.q-box.qu-borderAll.qu-borderRadius--small",
                "div.q-text.qu-dynamicFontSize--regular",
                "div.question-title"
            ]
            
            for selector in question_selectors:
                question_element = soup.select_one(selector)
                if question_element:
                    content = question_element.get_text(strip=True)
                    break
            
            # If no question found, try getting the h1 title
            if not content:
                h1_element = soup.find("h1")
                if h1_element:
                    content = h1_element.get_text(strip=True)
        
        elif "reddit.com" in domain:
            # Extract Reddit post
            post_title = soup.select_one("h1")
            post_content = soup.select_one("div[data-test-id='post-content']")
            
            if post_title:
                title_text = post_title.get_text(strip=True)
                content = title_text
            
            if post_content:
                text_divs = post_content.select("div > div > p")
                if text_divs:
                    content_text = " ".join(div.get_text(strip=True) for div in text_divs)
                    content = f"{content}: {content_text}" if content else content_text
        
        elif "tripadvisor.com" in domain:
            # Extract TripAdvisor post
            topic_title = soup.select_one("h1.topicTitle")
            post_text = soup.select_one("div.postBody")
            
            if topic_title:
                content = topic_title.get_text(strip=True)
            
            if post_text:
                content_text = post_text.get_text(strip=True)
                content = f"{content}: {content_text}" if content else content_text
        
        # Generic extraction as fallback
        if not content:
            # Try to get heading
            heading = soup.find(["h1", "h2"])
            heading_text = heading.get_text(strip=True) if heading else ""
            
            # Get main content paragraphs
            paragraphs = soup.find_all("p")
            paragraph_text = " ".join(p.get_text(strip=True) for p in paragraphs[:5]) if paragraphs else ""
            
            content = f"{heading_text}: {paragraph_text}" if heading_text else paragraph_text
        
        logger.info(f'[extract_thread_content] Extracted {len(content)} characters')
    except Exception as e:
        logger.error(f"[extract_thread_content] Error extracting content: {e}")
    finally:
        close_driver(driver)
    return content

def choose_money_site(question_text, websites_list=None):
    """
    Intelligently select the best website to reference based on the question content.
    """
    # Default websites if none provided
    if not websites_list:
        websites = {
            "Living Abroad - Aparthotels": {
                "url": "https://aparthotel.com",
                "description": "Offers aparthotels, rental options, and travel guides for local living.",
                "keywords": ["living", "apartment", "rental", "hotel", "accommodation"]
            },
            "Crypto Rentals": {
                "url": "https://cryptoapartments.com",
                "description": "Modern rental platform accepting cryptocurrency with travel and lifestyle insights.",
                "keywords": ["crypto", "bitcoin", "digital", "currency", "payment"]
            },
            "Serviced Apartments": {
                "url": "https://servicedapartments.net",
                "description": "Specializes in serviced apartments with travel tips and local renting rules.",
                "keywords": ["service", "apartment", "business", "travel", "corporate"]
            },
            "Furnished Apartments": {
                "url": "https://furnishedapartments.net",
                "description": "Focuses on furnished apartments with immediate living solutions and local analysis.",
                "keywords": ["furnished", "ready", "move-in", "apartment", "home"]
            },
            "Real Estate Abroad": {
                "url": "https://realestateabroad.com",
                "description": "International property investments, buying guides, financing tips, and market analysis.",
                "keywords": ["real estate", "property", "buying", "investing", "international"]
            },
            "Property Developments": {
                "url": "https://propertydevelopments.com",
                "description": "Latest new property projects with detailed buying and financing guides.",
                "keywords": ["development", "new", "project", "construction", "presale"]
            },
            "Property Investment": {
                "url": "https://propertyinvestment.net",
                "description": "Dedicated to property investment with how-to articles, financing guides, and yield analysis.",
                "keywords": ["investment", "return", "yield", "roi", "portfolio"]
            },
            "Golden Visa Opportunities": {
                "url": "https://golden-visa.com",
                "description": "Focuses on Golden Visa properties and investment immigration for the global elite.",
                "keywords": ["visa", "golden", "immigration", "citizenship", "passport"]
            },
            "Residence by Investment": {
                "url": "https://residence-by-investment.com",
                "description": "Guides investors on obtaining residency through property investments across markets.",
                "keywords": ["residence", "permanent", "residency", "immigration", "permit"]
            },
            "Citizenship by Investment": {
                "url": "https://citizenship-by-investment.net",
                "description": "Covers citizenship-by-investment programs with global insights and investment tips.",
                "keywords": ["citizenship", "passport", "naturalization", "immigration", "second"]
            }
        }
    else:
        websites = {site["name"]: {"url": site["url"], "description": site["description"], "keywords": []} for site in websites_list}
    
    # Calculate question complexity based on word count and length
    word_count = len(question_text.split())
    complexity = "simple" if word_count < 20 else "detailed" if word_count < 50 else "complex"
    
    # Score each website based on keyword relevance to the question
    site_scores = {}
    question_lower = question_text.lower()
    
    for site_name, site_data in websites.items():
        score = 0
        
        # Check for exact keyword matches
        for keyword in site_data.get("keywords", []):
            if keyword.lower() in question_lower:
                score += 10
        
        # Check for partial matches
        words = question_lower.split()
        site_name_words = site_name.lower().split()
        description_words = site_data["description"].lower().split()
        
        for word in words:
            if len(word) > 3:  # Ignore short words
                if any(word in site_word for site_word in site_name_words):
                    score += 5
                if any(word in desc_word for desc_word in description_words):
                    score += 2
        
        site_scores[site_name] = score
    
    # If all scores are 0, use a random site
    if all(score == 0 for score in site_scores.values()):
        selected_site_name = random.choice(list(websites.keys()))
    else:
        # Get the highest-scoring site
        selected_site_name = max(site_scores.items(), key=lambda x: x[1])[0]
    
    selected_site = websites[selected_site_name]
    return selected_site_name, selected_site, complexity

def generate_ai_response(question_text, additional_prompt="", use_chatgpt=True, model="gpt-3.5-turbo", max_tokens=250, temperature=0.7, websites=None):
    """
    Generate an AI response using OpenAI's API with improved context handling.
    """
    logger.info(f'[generate_ai_response] Generating response for question: {question_text[:50]}...')
    
    if not use_chatgpt:
        return "Default answer: " + question_text[:100] + "..."
    
    site_name, site_details, complexity = choose_money_site(question_text, websites)
    
    # Create a more natural site reference
    site_reference = f"{site_details['url']} - {site_details['description']}"
    
    # Adjust max tokens based on complexity if not explicitly set
    if max_tokens == 250:
        if complexity == "simple":
            max_tokens = 150
        elif complexity == "detailed":
            max_tokens = 250
        else:  # complex
            max_tokens = 350
    
    # Create a system prompt that guides the AI to be conversational and include the site reference
    system_prompt = f"""You are a helpful, conversational assistant providing value to users by answering their questions clearly and naturally.
Your goal is to provide genuinely useful information while subtly mentioning a relevant website near the end of your response.
The website to reference: {site_reference}

Guidelines:
- Be conversational and friendly in your tone
- Provide accurate, valuable information
- Include the website reference naturally, not as an obvious advertisement
- Make sure your response directly addresses the user's question
- Keep your answer concise but informative"""

    # Combine user question with any additional instructions
    user_prompt = question_text
    if additional_prompt:
        user_prompt += f"\n\nAdditional notes: {additional_prompt}"
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=1,
            frequency_penalty=0.2,
            presence
