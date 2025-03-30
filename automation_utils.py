import undetected_chromedriver as uc
import random
import time
import requests
import openai
from packaging.version import Version as LooseVersion
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import shutil
import os
import tempfile
import logging
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# List of User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
]

def _rotate_user_agent():
    return random.choice(USER_AGENTS)

def init_driver(proxy_address=None):
    logging.info('[init_driver] Initializing driver...')
    try:
        options = uc.ChromeOptions()
        
        # Check CHROME_HEADLESS env variable (default true)
        headless = os.environ.get("CHROME_HEADLESS", "true").lower() == "true"
        if headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        ua = _rotate_user_agent()
        options.add_argument(f"--user-agent={ua}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if proxy_address:
            options.add_argument(f"--proxy-server={proxy_address}")
        
        # Attempt to find the browser binary using shutil.which
        possible_bins = ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"]
        binary_path = None
        for b in possible_bins:
            found = shutil.which(b)
            logging.info(f'[init_driver] Checking {b}: {found}')
            if found:
                binary_path = found
                break
                
        # Set binary location explicitly for containerized environments
        chrome_binary_path = '/usr/bin/google-chrome-stable'
        options.binary_location = chrome_binary_path
        
        logging.info(f'[init_driver] Using Chrome binary at: {chrome_binary_path}')
        
        # Find chromedriver and copy to a temporary location to fix permissions
        possible_drivers = ["chromedriver", "chromium-driver"]
        driver_path = None
        for p in possible_drivers:
            found = shutil.which(p)
            logging.info(f'[init_driver] Checking {p}: {found}')
            if found:
                driver_path = found
                break
        if driver_path:
            logging.info(f'[init_driver] Found chromedriver at: {driver_path}')
            try:
                tmp_dir = tempfile.gettempdir()
                tmp_driver = os.path.join(tmp_dir, "chromedriver")
                shutil.copy2(driver_path, tmp_driver)
                os.chmod(tmp_driver, 0o755)
                driver_path = tmp_driver
                logging.info(f'[init_driver] Copied chromedriver to temporary location: {driver_path}')
            except Exception as e:
                logging.warning(f'[init_driver] Warning: Failed to copy chromedriver to temporary location: {e}')
        else:
            logging.warning("[init_driver] WARNING: No chromedriver found via which().")
        
        logging.info('[init_driver] Setting up driver with options...')
        driver = uc.Chrome(options=options,
                        browser_executable_path=chrome_binary_path,
                        driver_executable_path=driver_path,
                        use_subprocess=False)
        driver.set_page_load_timeout(30)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        logging.info('[init_driver] Driver initialized successfully.')
        return driver
    except Exception as e:
        logging.error(f'[init_driver] Error initializing driver: {e}')
        logging.exception(e)
        raise

def close_driver(driver):
    logging.info('[close_driver] Closing driver...')
    try:
        driver.quit()
        logging.info('[close_driver] Driver closed successfully.')
    except Exception as e:
        logging.error(f'[close_driver] Error closing driver: {e}')
        logging.exception(e)

def search_google(query, max_results=5):
    logging.info(f'[search_google] Searching for: {query}')
    driver = init_driver()
    results = []
    try:
        driver.get(f"https://www.google.com/search?q={query}")
        time.sleep(random.uniform(2, 4))
        elements = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        for element in elements[:max_results]:
            results.append(element.get_attribute("href"))
        logging.info(f'[search_google] Found {len(results)} results')
    except Exception as e:
        logging.error(f"[search_google] Error during search: {e}")
    finally:
        close_driver(driver)
    return results

def extract_thread_content(url):
    logging.info(f'[extract_thread_content] Extracting content from: {url}')
    driver = init_driver()
    content = ""
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        question_element = soup.find("div", {"class": "question_text"})
        if question_element:
            content = question_element.get_text(strip=True)
        else:
            paragraphs = soup.find_all("p")
            if paragraphs:
                content = " ".join(p.get_text(strip=True) for p in paragraphs)
        logging.info(f'[extract_thread_content] Extracted {len(content)} characters')
    except Exception as e:
        logging.error(f"[extract_thread_content] Error extracting content: {e}")
    finally:
        close_driver(driver)
    return content

def choose_money_site(question_text):
    word_count = len(question_text.split())
    complexity = "simple" if word_count < 20 else "detailed"
    sites = {
        "Living Abroad - Aparthotels": {
            "url": "https://aparthotel.com",
            "description": "Offers aparthotels, rental options, and travel guides for local living.",
            "count": random.randint(0, 5)
        },
        "Crypto Rentals": {
            "url": "https://cryptoapartments.com",
            "description": "Modern rental platform accepting cryptocurrency with travel and lifestyle insights.",
            "count": random.randint(0, 5)
        },
        "Serviced Apartments": {
            "url": "https://servicedapartments.net",
            "description": "Specializes in serviced apartments with travel tips and local renting rules.",
            "count": random.randint(0, 5)
        },
        "Furnished Apartments": {
            "url": "https://furnishedapartments.net",
            "description": "Focuses on furnished apartments with immediate living solutions and local analysis.",
            "count": random.randint(0, 5)
        },
        "Real Estate Abroad": {
            "url": "https://realestateabroad.com",
            "description": "International property investments, buying guides, financing tips, and market analysis.",
            "count": random.randint(0, 5)
        },
        "Property Developments": {
            "url": "https://propertydevelopments.com",
            "description": "Latest new property projects with detailed buying and financing guides.",
            "count": random.randint(0, 5)
        },
        "Property Investment": {
            "url": "https://propertyinvestment.net",
            "description": "Dedicated to property investment with how-to articles, financing guides, and yield analysis.",
            "count": random.randint(0, 5)
        },
        "Golden Visa Opportunities": {
            "url": "https://golden-visa.com",
            "description": "Focuses on Golden Visa properties and investment immigration for the global elite.",
            "count": random.randint(0, 5)
        },
        "Residence by Investment": {
            "url": "https://residence-by-investment.com",
            "description": "Guides investors on obtaining residency through property investments across markets.",
            "count": random.randint(0, 5)
        },
        "Citizenship by Investment": {
            "url": "https://citizenship-by-investment.net",
            "description": "Covers citizenship-by-investment programs with global insights and investment tips.",
            "count": random.randint(0, 5)
        }
    }
    selected_site = min(sites.items(), key=lambda item: item[1]["count"])
    return selected_site[0], selected_site[1], complexity

def generate_ai_response(question_text, additional_prompt, use_chatgpt=True):
    """
    Uses OpenAI's ChatCompletion API (gpt-3.5-turbo) to generate an answer.
    """
    logging.info(f'[generate_ai_response] Generating response for question: {question_text[:50]}...')
    if not use_chatgpt:
        return "Default answer: " + question_text[:100] + "..."
    site_name, site_details, complexity = choose_money_site(question_text)
    plug = f"Click here for more details: {site_details['url']}. {site_details['description']}."
    prompt_text = (
        f"Analyze the following question and provide a clear, concise answer. "
        f"Include a subtle reference to our service: {plug}\n\n"
        f"Question: {question_text}\nAdditional instructions: {additional_prompt}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=250 if complexity == "detailed" else 100,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"[generate_ai_response] Error generating answer: {e}")
        return f"Error generating answer: {e}"

def solve_captcha_if_present(driver):
    """
    Checks for a CAPTCHA on the page and uses 2Captcha to solve it if found.
    Returns True if a CAPTCHA was solved, else False.
    """
    logging.info('[solve_captcha] Checking for CAPTCHA presence...')
    page_html = driver.page_source
    captcha_type = None
    site_key = None
    if "data-sitekey" in page_html:
        start = page_html.find('data-sitekey="') + len('data-sitekey="')
        end = page_html.find('"', start)
        site_key = page_html[start:end]
        captcha_type = "recaptcha"
    if not site_key:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and ("sitekey=" in src or "k=" in src):
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(src).query)
                site_key = qs.get("sitekey", qs.get("k", [None]))[0]
                captcha_type = "recaptcha"
                break
    if not site_key or not captcha_type:
        logging.info('[solve_captcha] No CAPTCHA detected.')
        return False
    # Load CAPTCHA API key from environment variables
    api_key = os.environ.get("CAPTCHA_API_KEY", "")
    if not api_key:
        logging.warning("2Captcha API key not found in environment variables.")
        return False
    logging.info('[solve_captcha] CAPTCHA detected. Attempting to solve...')
    data = {
        "key": api_key,
        "method": "userrecaptcha",
        "googlekey": site_key,
        "pageurl": driver.current_url,
        "json": 1
    }
    try:
        resp = requests.post("https://2captcha.com/in.php", data=data).json()
    except Exception as e:
        logging.error(f"[solve_captcha] Error sending CAPTCHA request: {e}")
        return False
    if resp.get("status") != 1:
        logging.error(f"[solve_captcha] Error from 2Captcha: {resp.get('request')}")
        return False
    captcha_id = resp.get("request")
    token = None
    for _ in range(20):
        time.sleep(5)
        try:
            r = requests.get(f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1").json()
        except Exception as e:
            logging.error(f"[solve_captcha] Error polling 2Captcha: {e}")
            continue
        if r.get("status") == 1:
            token = r.get("request")
            break
        elif r.get("request") != "CAPCHA_NOT_READY":
            logging.error(f"[solve_captcha] 2Captcha error: {r.get('request')}")
            break
    if not token:
        logging.warning("[solve_captcha] Failed to get CAPTCHA solution token.")
        return False
    driver.execute_script("""
        document.querySelectorAll('[name="g-recaptcha-response"]').forEach(el => {
            el.style.display = 'block';
            el.value = arguments[0];
        });
    """, token)
    logging.info('[solve_captcha] CAPTCHA solution applied successfully.')
    return True

def search_and_extract_text_from_quora(query, max_results=5):
    """
    Searches for a query on Quora and extracts text from the result pages.
    
    Args:
        query (str): The search query.
        max_results (int): Maximum number of results to process.
        
    Returns:
        list: A list of dictionaries containing question, answer pairs.
    """
    logging.info(f'[search_quora] Searching for: {query}')
    driver = None
    try:
        driver = init_driver()
        search_url = f"https://www.quora.com/search?q={query.replace(' ', '%20')}"
        
        logging.info(f'[search_quora] Navigating to {search_url}')
        driver.get(search_url)
        
        # Wait for search results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='q-box qu-borderBottom']"))
        )
        
        # Extract search result links
        result_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='q-box qu-borderBottom']")
        
        results = []
        processed = 0
        
        for result in result_elements:
            if processed >= max_results:
                break
                
            try:
                # Find the question link
                link_element = result.find_element(By.CSS_SELECTOR, "a[class*='q-box qu-display--block qu-cursor--pointer qu-hover--textDecoration--underline']")
                question_text = link_element.text.strip()
                link_url = link_element.get_attribute('href')
                
                if not question_text or not link_url:
                    continue
                
                logging.info(f'[search_quora] Found question: {question_text[:50]}...')
                
                # Navigate to the question page
                driver.get(link_url)
                
                # Wait for the page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='q-box spacing_log_answer_content']"))
                )
                
                # Extract answers
                answer_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='q-box spacing_log_answer_content']")
                
                if answer_elements:
                    answer_text = answer_elements[0].text.strip()  # Get the first answer
                    
                    if answer_text:
                        results.append({
                            'question': question_text,
                            'answer': answer_text,
                            'url': link_url
                        })
                        processed += 1
                        logging.info(f'[search_quora] Extracted answer ({len(answer_text)} chars)')
                
                # Go back to search results
                driver.back()
                
                # Wait for search results to reload
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='q-box qu-borderBottom']"))
                )
                
                # Re-find the elements as they become stale after navigation
                result_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='q-box qu-borderBottom']")
                
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
                logging.error(f'[search_quora] Error processing result: {str(e)}')
                continue
        
        logging.info(f'[search_quora] Extracted {len(results)} results')
        return results
        
    except Exception as e:
        logging.error(f'[search_quora] Error: {str(e)}')
        logging.exception(e)
        return []
        
    finally:
        if driver:
            close_driver(driver)

def search_and_extract_text_from_reddit(query, max_results=5, min_comments=5):
    """
    Searches for a query on Reddit and extracts text from the result pages.
    
    Args:
        query (str): The search query.
        max_results (int): Maximum number of results to process.
        min_comments (int): Minimum number of comments required.
        
    Returns:
        list: A list of dictionaries containing post and comment data.
    """
    logging.info(f'[search_reddit] Searching for: {query}')
    driver = None
    try:
        driver = init_driver()
        search_url = f"https://www.reddit.com/search/?q={query.replace(' ', '%20')}&type=link"
        
        logging.info(f'[search_reddit] Navigating to {search_url}')
        driver.get(search_url)
        
        # Wait for search results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='post-container']"))
        )
        
        time.sleep(2)  # Additional wait for all content to load
        
        # Extract search result links
        result_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='post-container']")
        
        results = []
        processed = 0
        
        for result in result_elements:
            if processed >= max_results:
                break
                
            try:
                # Check if it has enough comments
                comment_element = result.find_element(By.CSS_SELECTOR, "span[data-testid='comment-count']")
                comment_text = comment_element.text.strip()
                comment_count = int(re.search(r'\d+', comment_text).group()) if re.search(r'\d+', comment_text) else 0
                
                if comment_count < min_comments:
                    continue
                
                # Find the post title and link
                title_element = result.find_element(By.CSS_SELECTOR, "div[data-testid='post-title'] > div > a")
                post_title = title_element.text.strip()
                post_url = title_element.get_attribute('href')
                
                if not post_title or not post_url:
                    continue
                
                logging.info(f'[search_reddit] Found post: {post_title[:50]}... with {comment_count} comments')
                
                # Navigate to the post page
                driver.get(post_url)
                
                # Wait for the page to load comments
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='post-title']"))
                )
                
                # Get post content
                post_content = ""
                try:
                    # Try to find text post content
                    post_content_element = driver.find_element(By.CSS_SELECTOR, "div[data-testid='post-content'] div[data-click-id='text'] div")
                    post_content = post_content_element.text.strip()
                except NoSuchElementException:
                    # If not found, it might be an image or link post
                    try:
                        # Check for link posts
                        post_content_element = driver.find_element(By.CSS_SELECTOR, "div[data-testid='post-content'] a[data-testid='outbound-link']")
                        post_content = f"Link post: {post_content_element.get_attribute('href')}"
                    except NoSuchElementException:
                        post_content = "No text content (might be an image post)"
                
                # Extract top-level comments
                try:
                    # Wait for comments to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='comment']"))
                    )
                    
                    comment_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='comment']")
                    comments = []
                    
                    for i, comment_element in enumerate(comment_elements[:5]):  # Get up to 5 top comments
                        try:
                            comment_text = comment_element.find_element(By.CSS_SELECTOR, "div[data-testid='comment'] div[data-testid='comment'] div").text.strip()
                            if comment_text:
                                comments.append(comment_text)
                        except Exception as e:
                            logging.warning(f'[search_reddit] Error extracting comment text: {str(e)}')
                            continue
                    
                    if post_title and (post_content or comments):
                        results.append({
                            'title': post_title,
                            'content': post_content,
                            'comments': comments,
                            'url': post_url
                        })
                        processed += 1
                        logging.info(f'[search_reddit] Extracted post with {len(comments)} comments')
                    
                except (TimeoutException, NoSuchElementException) as e:
                    logging.warning(f'[search_reddit] Error loading comments: {str(e)}')
                    # Still add the post if we have content
                    if post_title and post_content:
                        results.append({
                            'title': post_title,
                            'content': post_content,
                            'comments': [],
                            'url': post_url
                        })
                        processed += 1
                        logging.info(f'[search_reddit] Extracted post with no comments')
                
                # Go back to search results
                driver.back()
                
                # Wait for search results to reload
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='post-container']"))
                )
                
                # Re-find the elements as they become stale after navigation
                result_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='post-container']")
                
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
                logging.error(f'[search_reddit] Error processing result: {str(e)}')
                continue
            except Exception as e:
                logging.error(f'[search_reddit] Unexpected error: {str(e)}')
                logging.exception(e)
                continue
        
        logging.info(f'[search_reddit] Extracted {len(results)} results')
        return results
        
    except Exception as e:
        logging.error(f'[search_reddit] Error: {str(e)}')
        logging.exception(e)
        return []
        
    finally:
        if driver:
            close_driver(driver)
