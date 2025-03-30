import re
import time
import random
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

def init_driver():
    logging.info('[init_driver] Initializing driver...')
    try:
        # Checking browser binaries
        for browser in ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']:
            import shutil
            path = shutil.which(browser)
            logging.info(f'[init_driver] Checking {browser}: {path}')
        
        # Checking chromedriver binaries
        for driver in ['chromedriver', 'chromium-driver']:
            import shutil
            path = shutil.which(driver)
            logging.info(f'[init_driver] Checking {driver}: {path}')
        
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Set binary location explicitly for containerized environments
        chrome_binary_path = '/usr/bin/google-chrome-stable'
        options.binary_location = chrome_binary_path
        
        logging.info('[init_driver] Setting up driver with options...')
        driver = uc.Chrome(options=options)
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
