import os
import time
import random
import logging
import traceback
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try importing various required libraries
try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        NoSuchElementException, 
        ElementClickInterceptedException,
        StaleElementReferenceException,
        WebDriverException
    )
    import openai
    from dotenv import load_dotenv
except ImportError as e:
    logger.error(f"Failed to import necessary libraries: {str(e)}")
    logger.error("Please make sure all required packages are installed.")
    raise

# Load environment variables
load_dotenv()

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.warning("OPENAI_API_KEY environment variable not found.")

# Constants
DEFAULT_TIMEOUT = 20  # seconds
MAX_RETRIES = 3
TYPING_SPEED_MIN = 0.05  # seconds per character (fast typing)
TYPING_SPEED_MAX = 0.15  # seconds per character (slow typing)
HUMAN_DELAY_MIN = 0.5  # minimum delay between actions
HUMAN_DELAY_MAX = 2.0  # maximum delay between actions

def init_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Initialize and return a Chrome webdriver with appropriate options.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        
    Returns:
        webdriver.Chrome: Initialized Chrome webdriver
    """
    try:
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument("--headless")
        
        # Add common options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36")
        
        # Create and return the webdriver
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(60)
        
        logger.info("Chrome WebDriver initialized successfully")
        return driver
    
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
        traceback.print_exc()
        raise

def simulate_human_behavior(driver: webdriver.Chrome, min_delay: float = None, max_delay: float = None) -> None:
    """
    Simulate human-like behavior by waiting a random amount of time.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        min_delay (float, optional): Minimum delay in seconds
        max_delay (float, optional): Maximum delay in seconds
    """
    min_delay = min_delay or HUMAN_DELAY_MIN
    max_delay = max_delay or HUMAN_DELAY_MAX
    time.sleep(random.uniform(min_delay, max_delay))

def randomize_typing_speed(text: str, min_speed: float = None, max_speed: float = None) -> None:
    """
    Simulate human typing by introducing random delays between keypresses.
    
    Args:
        text (str): The text being typed
        min_speed (float, optional): Minimum time per character in seconds
        max_speed (float, optional): Maximum time per character in seconds
    """
    min_speed = min_speed or TYPING_SPEED_MIN
    max_speed = max_speed or TYPING_SPEED_MAX
    
    for char in text:
        yield char
        time.sleep(random.uniform(min_speed, max_speed))

def safe_click(driver: webdriver.Chrome, element, retries: int = 3) -> bool:
    """
    Safely click an element with retries to handle common exceptions.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        element: The element to click
        retries (int): Number of retries before giving up
        
    Returns:
        bool: True if successful, False otherwise
    """
    attempt = 0
    while attempt < retries:
        try:
            # Scroll element into view before clicking
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            simulate_human_behavior(driver, 0.3, 0.7)
            element.click()
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException) as e:
            attempt += 1
            logger.warning(f"Click attempt {attempt} failed: {str(e)}")
            simulate_human_behavior(driver, 1.0, 2.0)
            # If element is stale, try to find it again
            if isinstance(e, StaleElementReferenceException) and hasattr(element, 'by') and hasattr(element, 'value'):
                try:
                    element = driver.find_element(element.by, element.value)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Unexpected error during click: {str(e)}")
            return False
    
    logger.error(f"Failed to click element after {retries} attempts")
    return False

def wait_for_element(driver: webdriver.Chrome, by: By, value: str, timeout: int = DEFAULT_TIMEOUT, visible: bool = True) -> Optional[Any]:
    """
    Wait for an element to be present and optionally visible.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        by (By): The locator method
        value (str): The locator value
        timeout (int): Maximum time to wait in seconds
        visible (bool): Whether to wait for visibility or just presence
        
    Returns:
        The element if found, None otherwise
    """
    try:
        wait = WebDriverWait(driver, timeout)
        condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
        element = wait.until(condition((by, value)))
        return element
    except TimeoutException:
        logger.warning(f"Timed out waiting for element: {by}={value}")
        return None
    except Exception as e:
        logger.error(f"Error waiting for element {by}={value}: {str(e)}")
        return None

def wait_for_elements(driver: webdriver.Chrome, by: By, value: str, timeout: int = DEFAULT_TIMEOUT, visible: bool = True) -> List[Any]:
    """
    Wait for elements to be present and optionally visible.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        by (By): The locator method
        value (str): The locator value
        timeout (int): Maximum time to wait in seconds
        visible (bool): Whether to wait for visibility or just presence
        
    Returns:
        List of elements if found, empty list otherwise
    """
    try:
        wait = WebDriverWait(driver, timeout)
        condition = EC.visibility_of_all_elements_located if visible else EC.presence_of_all_elements_located
        elements = wait.until(condition((by, value)))
        return elements
    except TimeoutException:
        logger.warning(f"Timed out waiting for elements: {by}={value}")
        return []
    except Exception as e:
        logger.error(f"Error waiting for elements {by}={value}: {str(e)}")
        return []

def fill_text_field(driver: webdriver.Chrome, element, text: str, clear_first: bool = True, human_like: bool = True) -> bool:
    """
    Fill a text field with optional human-like typing.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        element: The input element
        text (str): Text to enter
        clear_first (bool): Whether to clear the field first
        human_like (bool): Whether to simulate human typing
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if clear_first:
            element.clear()
            simulate_human_behavior(driver, 0.2, 0.5)
        
        if human_like:
            for char in randomize_typing_speed(text):
                element.send_keys(char)
        else:
            element.send_keys(text)
        
        return True
    except Exception as e:
        logger.error(f"Error filling text field: {str(e)}")
        return False

def solve_captcha_if_present(driver: webdriver.Chrome) -> bool:
    """
    Detect and handle CAPTCHA if present on the page.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        
    Returns:
        bool: True if CAPTCHA was handled or not present, False if failed to handle
    """
    # Check for common CAPTCHA identifiers
    captcha_identifiers = [
        (By.ID, "captcha"),
        (By.XPATH, "//iframe[contains(@src, 'recaptcha')]"),
        (By.XPATH, "//iframe[contains(@src, 'hcaptcha')]"),
        (By.XPATH, "//*[contains(text(), 'CAPTCHA')]"),
        (By.XPATH, "//*[contains(text(), 'captcha')]"),
        (By.XPATH, "//*[contains(text(), 'I am not a robot')]")
    ]
    
    for by, value in captcha_identifiers:
        try:
            element = driver.find_element(by, value)
            if element.is_displayed():
                logger.warning("CAPTCHA detected! Automated solving not implemented.")
                # In a real application, you might integrate a CAPTCHA solving service here
                # For now, we'll just wait to give time for manual intervention
                logger.info("Waiting 30 seconds for manual CAPTCHA resolution...")
                time.sleep(30)
                return True
        except NoSuchElementException:
            continue
        except Exception as e:
            logger.error(f"Error while checking for CAPTCHA: {str(e)}")
    
    return True  # No CAPTCHA detected or handled successfully

def take_screenshot(driver: webdriver.Chrome, filename: str = None) -> str:
    """
    Take a screenshot for debugging purposes.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        filename (str, optional): The filename to save the screenshot as
        
    Returns:
        str: Path to the saved screenshot
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
    
    try:
        # Ensure the screenshots directory exists
        os.makedirs("screenshots", exist_ok=True)
        filepath = os.path.join("screenshots", filename)
        
        driver.save_screenshot(filepath)
        logger.info(f"Screenshot saved to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to take screenshot: {str(e)}")
        return ""

def scroll_to_bottom(driver: webdriver.Chrome, scroll_pause_time: float = 1.0) -> None:
    """
    Scroll to the bottom of the page gradually.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        scroll_pause_time (float): Time to pause between scrolls
    """
    try:
        # Get scroll height
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
            
            # Wait to load page
            time.sleep(scroll_pause_time)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    except Exception as e:
        logger.error(f"Error scrolling to bottom: {str(e)}")

def scroll_into_view(driver: webdriver.Chrome, element) -> None:
    """
    Scroll element into the center of the viewport.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        element: The element to scroll to
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)  # Short pause after scrolling
    except Exception as e:
        logger.error(f"Error scrolling element into view: {str(e)}")

def check_for_errors(driver: webdriver.Chrome) -> Tuple[bool, str]:
    """
    Check the page for common error messages.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        
    Returns:
        Tuple[bool, str]: (error_found, error_message)
    """
    error_patterns = [
        (By.XPATH, "//*[contains(text(), 'error')]"),
        (By.XPATH, "//*[contains(text(), 'Error')]"),
        (By.XPATH, "//*[contains(text(), 'not found')]"),
        (By.XPATH, "//*[contains(text(), '404')]"),
        (By.XPATH, "//*[contains(text(), 'failed')]")
    ]
    
    for by, value in error_patterns:
        try:
            elements = driver.find_elements(by, value)
            for element in elements:
                if element.is_displayed():
                    error_msg = element.text.strip()
                    if error_msg:
                        return True, error_msg
        except Exception:
            continue
    
    return False, ""

def check_login_status(driver: webdriver.Chrome, logged_in_indicator: Tuple[By, str], 
                      logged_out_indicator: Tuple[By, str]) -> bool:
    """
    Check if user is logged in.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        logged_in_indicator: Tuple of (By, selector) that indicates logged in state
        logged_out_indicator: Tuple of (By, selector) that indicates logged out state
        
    Returns:
        bool: True if logged in, False otherwise
    """
    try:
        # Check for logged in indicator
        in_by, in_selector = logged_in_indicator
        try:
            logged_in_elem = driver.find_element(in_by, in_selector)
            if logged_in_elem.is_displayed():
                return True
        except NoSuchElementException:
            pass
        
        # Check for logged out indicator
        out_by, out_selector = logged_out_indicator
        try:
            logged_out_elem = driver.find_element(out_by, out_selector)
            if logged_out_elem.is_displayed():
                return False
        except NoSuchElementException:
            pass
        
        # If neither found, default to logged out
        return False
    except Exception as e:
        logger.error(f"Error checking login status: {str(e)}")
        return False

def parse_page_data(driver: webdriver.Chrome, parsers: Dict[str, Tuple[By, str]]) -> Dict[str, Any]:
    """
    Parse data from the current page using provided selectors.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        parsers: Dictionary mapping data keys to (By, selector) tuples
        
    Returns:
        Dict[str, Any]: Parsed data
    """
    result = {}
    
    for key, (by, selector) in parsers.items():
        try:
            elements = driver.find_elements(by, selector)
            if elements:
                if len(elements) == 1:
                    result[key] = elements[0].text.strip()
                else:
                    result[key] = [elem.text.strip() for elem in elements]
            else:
                result[key] = None
        except Exception as e:
            logger.error(f"Error parsing {key}: {str(e)}")
            result[key] = None
    
    return result

def save_cookies(driver: webdriver.Chrome, filename: str = "cookies.json") -> bool:
    """
    Save current browser cookies to a file.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        filename (str): File to save cookies to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cookies = driver.get_cookies()
        with open(filename, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"Cookies saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save cookies: {str(e)}")
        return False

def load_cookies(driver: webdriver.Chrome, filename: str = "cookies.json") -> bool:
    """
    Load cookies from a file into the browser.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        filename (str): File to load cookies from
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not os.path.exists(filename):
            logger.warning(f"Cookie file {filename} not found")
            return False
            
        with open(filename, 'r') as f:
            cookies = json.load(f)
            
        for cookie in cookies:
            # Some cookies can't be loaded properly, so we need to handle exceptions
            try:
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Error adding cookie: {str(e)}")
                
        logger.info(f"Cookies loaded from {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies: {str(e)}")
        return False

def safe_get(driver: webdriver.Chrome, url: str, max_retries: int = 3) -> bool:
    """
    Safely navigate to a URL with retries and error handling.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance
        url (str): URL to navigate to
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        bool: True if successful, False otherwise
    """
    attempt = 0
    while attempt < max_retries:
        try:
            driver.get(url)
            # Check if page loaded successfully
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except Exception as e:
            attempt += 1
            logger.warning(f"Attempt {attempt} to load {url} failed: {str(e)}")
            if attempt >= max_retries:
                logger.error(f"Failed to load {url} after {max_retries} attempts")
                return False
            time.sleep(2 * attempt)  # Exponential backoff

def generate_content_with_openai(
    user_prompt: str, 
    system_prompt: str = "You are a helpful assistant.", 
    model: str = "gpt-3.5-turbo", 
    max_tokens: int = 500, 
    temperature: float = 0.7,
    fallback_response: str = None
) -> str:
    """
    Generate content using OpenAI's API.
    
    Args:
        user_prompt (str): The user prompt
        system_prompt (str): The system prompt that sets the AI behavior
        model (str): The OpenAI model to use
        max_tokens (int): Maximum tokens in the response
        temperature (float): Randomness of the output (0.0-1.0)
        fallback_response (str): Response to return if API call fails
        
    Returns:
        str: Generated content
    """
    if not openai.api_key:
        logger.error("OpenAI API key not set")
        return fallback_response if fallback_response else "API key not configured."
    
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
            presence_penalty=0.1
        )
        return response.choices[0].message["content"]
    except Exception as e:
        logger.error(f"Error generating content with OpenAI: {str(e)}")
        return fallback_response if fallback_response else "I couldn't generate appropriate content at this time."

def cleanup_driver(driver: webdriver.Chrome) -> None:
    """
    Safely close and clean up the webdriver.
    
    Args:
        driver (webdriver.Chrome): The webdriver instance to clean up
    """
    try:
        driver.quit()
        logger.info("WebDriver closed successfully")
    except Exception as e:
        logger.error(f"Error closing WebDriver: {str(e)}")

# Add any additional utility functions as needed
