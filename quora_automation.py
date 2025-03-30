import os
import random
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from automation_utils import init_driver, solve_captcha_if_present, simulate_human_behavior, _randomize_typing_speed

logger = logging.getLogger(__name__)

def find_answer_field(driver, timeout=15):
    """
    Try multiple selectors to find the answer input field.
    Uses a variety of selectors to improve reliability.
    """
    selectors = [
        (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']"),
        (By.CSS_SELECTOR, "div[role='textbox']"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
        (By.CSS_SELECTOR, "div.q-box div[contenteditable='true']"),
        (By.XPATH, "//div[@data-placeholder='Write your answer']"),
        (By.TAG_NAME, "textarea"),
        (By.XPATH, "//*[contains(@placeholder, 'Write your answer')]")
    ]
    
    for by, selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            
            # First scroll the element into view
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(random.uniform(0.5, 1))
            
            # Simulate human behavior before clicking
            simulate_human_behavior(driver, element)
            
            # Try clicking with JavaScript if regular click fails
            try:
                element.click()  # Regular click
            except ElementClickInterceptedException:
                # If regular click fails, try JavaScript click
                driver.execute_script("arguments[0].click();", element)
                
            logger.info(f"[quora] Found answer field using selector: {selector}")
            
            # Small pause after focusing the element
            time.sleep(random.uniform(0.5, 1.5))
            return element
        except Exception as e:
            logger.debug(f"[quora] Answer field not found with selector {selector}: {e}")
    
    raise Exception("[quora] Unable to locate an answer input field using any known selector.")

def quora_login_and_post(username=None, password=None, content="", question_url=None, proxy=None):
    """
    Log in to Quora and either:
    1. Answer an existing question (when question_url is provided)
    2. Create a new question (when question_url is None)
    
    Enhanced with anti-detection measures and human-like behavior
    """
    # If credentials are not passed in, load them from environment variables.
    if not username:
        username = os.environ.get("QUORA_USER1", "")
    if not password:
        password = os.environ.get("QUORA_PASS1", "")
    
    logger.info(f"[quora] Initializing Quora automation for {'answer' if question_url else 'question'}")
    
    driver = init_driver(proxy)
    try:
        driver.set_page_load_timeout(40)
        
        # Start with the Quora homepage then navigate to login for a more natural flow
        driver.get("https://www.quora.com")
        time.sleep(random.uniform(2, 4))
        
        # Check for cookie notice and handle if present
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Accept') or contains(text(), 'I agree')]"))
            )
            simulate_human_behavior(driver, cookie_btn)
            cookie_btn.click()
            time.sleep(random.uniform(0.5, 1.5))
        except (TimeoutException, NoSuchElementException):
            logger.info("[quora] No cookie notice found or already accepted")
        
        # Find and click login link if we're not already on the login page
        if "login" not in driver.current_url:
            login_selectors = [
                (By.XPATH, "//a[contains(text(), 'Login')]"),
                (By.XPATH, "//a[contains(text(), 'Log In')]"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
                (By.XPATH, "//button[contains(text(), 'Log In')]")
            ]
            
            for selector_type, selector in login_selectors:
                try:
                    login_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    simulate_human_behavior(driver, login_btn)
                    login_btn.click()
                    logger.info(f"[quora] Clicked login button with selector: {selector}")
                    time.sleep(random.uniform(1, 2))
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
        
        # If we're still not on the login page, navigate directly
        if "login" not in driver.current_url:
            driver.get("https://www.quora.com/login")
            time.sleep(random.uniform(2, 3))
        
        # Find email and password fields
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "email")))
        email_field = driver.find_element(By.NAME, "email")
        pwd_field = driver.find_element(By.NAME, "password")
        
        # Clear fields and type with human-like delays
        email_field.clear()
        simulate_human_behavior(driver, email_field)
        
        # Type email with random delays
        for char, delay in _randomize_typing_speed(username):
            email_field.send_keys(char)
            time.sleep(delay)
        
        # Pause between fields
        time.sleep(random.uniform(0.8, 1.5))
        
        # Clear password field and type with human-like delays
        pwd_field.clear()
        simulate_human_behavior(driver, pwd_field)
        
        # Type password with random delays
        for char, delay in _randomize_typing_speed(password):
            pwd_field.send_keys(char)
            time.sleep(delay)
        
        # Random pause before submission
        time.sleep(random.uniform(0.8, 2.0))
        
        # Find and click the login button instead of pressing Enter
        login_button_selectors = [
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Log In')]"),
            (By.CSS_SELECTOR, "button[type='submit']")
        ]
        
        login_clicked = False
        for selector_type, selector in login_button_selectors:
            try:
                login_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                simulate_human_behavior(driver, login_btn)
                login_btn.click()
                login_clicked = True
                logger.info(f"[quora] Clicked login button with selector: {selector}")
                break
            except (TimeoutException, NoSuchElementException):
                continue
        
        # If no login button found, use Enter key
        if not login_clicked:
            pwd_field.send_keys(Keys.ENTER)
            logger.info("[quora] Used Enter key to submit login form")
        
        # Wait for login to complete
        time.sleep(5)
        
        # Confirm login was successful by checking for user-specific elements
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, 
                    "//a[contains(@href, '/profile') or contains(@href, '/notifications') or contains(text(),'Home')]"))
            )
            logger.info("[quora] User successfully logged in")
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"[quora] Login confirmation element not found: {e}")
            
            # Check if we're still on the login page and try CAPTCHA solution
            if "login" in driver.current_url.lower():
                if solve_captcha_if_present(driver):
                    logger.info("[quora] CAPTCHA detected and solved, retrying login")
                    pwd_field = driver.find_element(By.NAME, "password")
                    pwd_field.send_keys(Keys.ENTER)
                    time.sleep(5)
        
        # ANSWER EXISTING QUESTION
        if question_url:
            # Navigate to the question
            driver.get(question_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Scroll down a bit and pause to simulate reading
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(3, 7))
            
            # Try clicking the "Answer" button using multiple selectors
            answer_clicked = False
            answer_selectors = [
                (By.XPATH, "//button[text()='Answer' or text()='Write answer']"),
                (By.XPATH, "//button[contains(text(), 'Answer')]"),
                (By.XPATH, "//a[contains(text(), 'Answer')]"),
                (By.CSS_SELECTOR, "button.q-write-btn")
            ]
            
            for selector_type, selector in answer_selectors:
                try:
                    answer_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    # Scroll to button and simulate human behavior
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", answer_btn)
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    simulate_human_behavior(driver, answer_btn)
                    answer_btn.click()
                    answer_clicked = True
                    logger.info(f"[quora] Clicked Answer button using selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"[quora] Answer button not found with selector {selector}: {e}")
            
            if not answer_clicked:
                logger.info("[quora] No clickable Answer button found; proceeding assuming editor is already open")
            
            # Give the answer editor time to load
            time.sleep(random.uniform(2, 4))
            
            # Locate the answer input field using the helper function
            try:
                answer_box = find_answer_field(driver, timeout=15)
            except Exception as e:
                raise Exception(f"[quora] Unable to locate answer input field: {e}")
            
            # Type content with human-like delays
            for char, delay in _randomize_typing_speed(content, min_delay=0.02, max_delay=0.15):
                answer_box.send_keys(char)
                time.sleep(delay)
            
            # Random pause after typing
            time.sleep(random.uniform(2, 4))
            
            # Attempt to click the submit button with multiple possible selectors
            submit_selectors = [
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//button[contains(text(), 'Post')]"),
                (By.XPATH, "//button[contains(text(), 'Answer')]"),
                (By.CSS_SELECTOR, "button.submit_button")
            ]
            
            submit_clicked = False
            for selector_type, selector in submit_selectors:
                try:
                    submit_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_btn)
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    simulate_human_behavior(driver, submit_btn)
                    submit_btn.click()
                    submit_clicked = True
                    logger.info(f"[quora] Clicked Submit button using selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"[quora] Submit button not found with selector {selector}: {e}")
            
            if not submit_clicked:
                logger.warning("[quora] Submit button not found; using keyboard shortcut")
                # Use keyboard shortcut as fallback
                answer_box.send_keys(Keys.CONTROL + Keys.ENTER)
                logger.info("[quora] Used Ctrl+Enter to submit answer")
            
            # Wait for the submission to complete
            time.sleep(random.uniform(5, 7))
            
        # CREATE NEW QUESTION
        else:
            # Navigate to the homepage
            driver.get("https://www.quora.com/")
            time.sleep(random.uniform(3, 5))
            
            # Try to find and click the "Add Question" button
            add_question_clicked = False
            add_question_selectors = [
                (By.CSS_SELECTOR, "[data-functional-selector='add-question-button']"),
                (By.XPATH, "//button[contains(text(), 'Add Question')]"),
                (By.XPATH, "//a[contains(text(), 'Add Question')]"),
                (By.XPATH, "//span[contains(text(), 'Add Question')]/parent::button"),
                (By.XPATH, "//div[contains(@class, 'selector_add_question')]")
            ]
            
            for selector_type, selector in add_question_selectors:
                try:
                    add_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    simulate_human_behavior(driver, add_btn)
                    add_btn.click()
                    add_question_clicked = True
                    logger.info(f"[quora] Clicked Add Question button using selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"[quora] Add Question button not found with selector {selector}: {e}")
            
            if not add_question_clicked:
                logger.error("[quora] Could not find Add Question button")
                return False
            
            # Wait for the question dialog to open
            time.sleep(random.uniform(2, 3))
            
            # Find the question input field
            question_input_selectors = [
                (By.CSS_SELECTOR, "[contenteditable='true']"),
                (By.XPATH, "//div[@contenteditable='true']"),
                (By.TAG_NAME, "textarea"),
                (By.XPATH, "//div[contains(@class, 'question_modal')]//div[@contenteditable='true']")
            ]
            
            question_input = None
            for selector_type, selector in question_input_selectors:
                try:
                    question_input = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    simulate_human_behavior(driver, question_input)
                    question_input.click()
                    logger.info(f"[quora] Found question input field using selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"[quora] Question input not found with selector {selector}: {e}")
            
            if not question_input:
                logger.error("[quora] Could not find question input field")
                return False
            
            # Type question content with human-like delays
            for char, delay in _randomize_typing_speed(content, min_delay=0.03, max_delay=0.15):
                question_input.send_keys(char)
                time.sleep(delay)
            
            # Random pause before submission
            time.sleep(random.uniform(2, 4))
            
            # Try to find and click the submit button
            post_selectors = [
                (By.XPATH, "//button[normalize-space()='Add Question' or normalize-space()='Submit']"),
                (By.XPATH, "//button[contains(text(), 'Add Question')]"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.CSS_SELECTOR, "button.submit_button")
            ]
            
            post_clicked = False
            for selector_type, selector in post_selectors:
                try:
                    post_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    simulate_human_behavior(driver, post_btn)
                    post_btn.click()
                    post_clicked = True
                    logger.info(f"[quora] Clicked post button using selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"[quora] Post button not found with selector {selector}: {e}")
            
            if not post_clicked:
                logger.warning("[quora] Post button not found; using keyboard shortcut")
                # Use keyboard shortcut as fallback
                question_input.send_keys(Keys.CONTROL + Keys.ENTER)
                logger.info("[quora] Used Ctrl+Enter to submit question")
            
            # Wait for submission to complete
            time.sleep(random.uniform(4, 6))
        
        # Take a screenshot for verification purposes
        try:
            debug_dir = "debug_screenshots"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            driver.save_screenshot(f"{debug_dir}/quora_{timestamp}.png")
            logger.info(f"[quora] Saved verification screenshot to {debug_dir}/quora_{timestamp}.png")
        except Exception as e:
            logger.error(f"[quora] Failed to save verification screenshot: {e}")
        
        return True
    except Exception as e:
        logger.error(f"[quora] Error during Quora automation: {e}")
        return False
    finally:
        driver.quit()
