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

def tripadvisor_login_and_post(username=None, password=None, content="", thread_url="", proxy=None):
    """
    Log in to TripAdvisor and post a reply to a thread.
    
    Enhanced with anti-detection measures and human-like behavior
    """
    # Load credentials from environment variables if not provided
    if not username:
        username = os.environ.get("TRIPADVISOR_USER1", "")
    if not password:
        password = os.environ.get("TRIPADVISOR_PASS1", "")
    
    logger.info(f"[tripadvisor] Initializing TripAdvisor automation")
    
    driver = init_driver(proxy)
    try:
        driver.set_page_load_timeout(40)
        
        # Start with the homepage for a more natural browsing pattern
        driver.get("https://www.tripadvisor.com/")
        time.sleep(random.uniform(3, 5))
        
        # Accept cookies if the banner appears
        try:
            cookie_selectors = [
                (By.ID, "onetrust-accept-btn-handler"),
                (By.XPATH, "//button[contains(text(), 'Accept All')]"),
                (By.XPATH, "//button[contains(text(), 'Accept')]"),
                (By.XPATH, "//button[contains(text(), 'I Accept')]")
            ]
            
            for selector_type, selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    simulate_human_behavior(driver, cookie_btn)
                    cookie_btn.click()
                    logger.info(f"[tripadvisor] Accepted cookies using selector: {selector}")
                    time.sleep(random.uniform(1, 2))
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
        except Exception as e:
            logger.info(f"[tripadvisor] No cookie banner found or error: {e}")
        
        # Simulate looking around the site a bit
        random_scrolls = random.randint(1, 3)
        for _ in range(random_scrolls):
            scroll_amount = random.randint(300, 700)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(1, 3))
        
        # Click sign in using multiple potential selectors
        sign_in_selectors = [
            (By.LINK_TEXT, "Sign in"),
            (By.XPATH, "//a[contains(text(), 'Sign in') or contains(text(), 'Log in')]"),
            (By.CSS_SELECTOR, ".login a"),
            (By.CSS_SELECTOR, "a.sign-in"),
            (By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'Log in')]"),
            (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'log in')]")
        ]
        
        sign_in_clicked = False
        for selector_type, selector in sign_in_selectors:
            try:
                sign_in_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                simulate_human_behavior(driver, sign_in_link)
                sign_in_link.click()
                sign_in_clicked = True
                logger.info(f"[tripadvisor] Clicked sign-in using selector: {selector}")
                time.sleep(random.uniform(2, 3))
                break
            except Exception as e:
                logger.debug(f"[tripadvisor] Sign-in element not found with selector {selector}: {e}")
        
        if not sign_in_clicked:
            logger.warning("[tripadvisor] Could not find sign-in link, trying profile menu workaround")
            # Try clicking on profile icon first
            try:
                profile_icon = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".menu-avatar, .prof_avatar, .ui_avatar"))
                )
                simulate_human_behavior(driver, profile_icon)
                profile_icon.click()
                time.sleep(random.uniform(1, 2))
                
                # Now look for sign in option in dropdown
                sign_in_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')]"))
                )
                simulate_human_behavior(driver, sign_in_menu)
                sign_in_menu.click()
                time.sleep(random.uniform(2, 3))
                sign_in_clicked = True
                logger.info("[tripadvisor] Used profile menu workaround to access sign-in")
            except Exception as e:
                logger.error(f"[tripadvisor] Profile menu workaround failed: {e}")
        
        # If we still couldn't sign in via UI, go directly to the login page
        if not sign_in_clicked:
            logger.warning("[tripadvisor] Using direct login URL as fallback")
            driver.get("https://www.tripadvisor.com/Login")
            time.sleep(random.uniform(2, 3))
        
        # Check for and switch to login iframe if one exists
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            iframe_switched = False
            
            for frame in iframes:
                try:
                    src = frame.get_attribute("src")
                    if src and ("login" in src.lower() or "registration" in src.lower()):
                        driver.switch_to.frame(frame)
                        iframe_switched = True
                        logger.info(f"[tripadvisor] Switched to login iframe: {src}")
                        time.sleep(random.uniform(1, 2))
                        break
                except Exception as iframe_err:
                    logger.debug(f"[tripadvisor] Error checking iframe: {iframe_err}")
            
            if not iframe_switched and len(iframes) > 0:
                # If we couldn't identify the right iframe but there are iframes, try the first one
                driver.switch_to.frame(iframes[0])
                logger.info("[tripadvisor] Switched to first iframe as fallback")
                time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.info(f"[tripadvisor] No iframes found or error switching: {e}")
        
        # Locate email field using multiple selectors
        email_field = None
        email_selectors = [
            (By.NAME, "email"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
            (By.XPATH, "//input[@name='email' or @id='email' or contains(@placeholder, 'email')]")
        ]
        
        for selector_type, selector in email_selectors:
            try:
                email_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((selector_type, selector))
                )
                if email_field.is_displayed():
                    simulate_human_behavior(driver, email_field)
                    email_field.clear()
                    logger.info(f"[tripadvisor] Found email field using selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"[tripadvisor] Email field not found with selector {selector}: {e}")
        
        # Locate password field using multiple selectors
        pass_field = None
        pass_selectors = [
            (By.NAME, "password"),
            (By.ID, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@name='password' or @id='password' or @type='password']")
        ]
        
        for selector_type, selector in pass_selectors:
            try:
                pass_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((selector_type, selector))
                )
                if pass_field.is_displayed():
                    logger.info(f"[tripadvisor] Found password field using selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"[tripadvisor] Password field not found with selector {selector}: {e}")
        
        # Enter login credentials if both fields were found
        if email_field and pass_field:
            # Type email with random delays
            for char, delay in _randomize_typing_speed(username):
                email_field.send_keys(char)
                time.sleep(delay)
            
            # Pause between fields
            time.sleep(random.uniform(0.8, 1.5))
            
            # Click and clear password field
            simulate_human_behavior(driver, pass_field)
            pass_field.clear()
            
            # Type password with random delays
            for char, delay in _randomize_typing_speed(password):
                pass_field.send_keys(char)
                time.sleep(delay)
            
            # Random pause before submission
            time.sleep(random.uniform(1, 2))
            
            # Look for sign-in/login button
            login_button_selectors = [
                (By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'Log in')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//a[contains(text(), 'Sign in') and contains(@class, 'button')]")
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
                    logger.info(f"[tripadvisor] Clicked login button using selector: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"[tripadvisor] Login button not found with selector {selector}: {e}")
            
            # If no button found, try pressing Enter
            if not login_clicked:
                logger.info("[tripadvisor] No login button found, using Enter key")
                pass_field.send_keys(Keys.ENTER)
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if CAPTCHA appeared and try to solve it
            if "Sign in" in driver.title or "Log in" in driver.title:
                if solve_captcha_if_present(driver):
                    logger.info("[tripadvisor] CAPTCHA detected and solved, submitting form again")
                    pass_field = driver.find_element(By.NAME, "password")
                    pass_field.send_keys(Keys.ENTER)
                    time.sleep(5)
        else:
            logger.error("[tripadvisor] Could not find email or password fields")
            return False
        
        # Switch back to default content
        try:
            driver.switch_to.default_content()
            logger.info("[tripadvisor] Switched back to default content after login")
        except Exception as e:
            logger.info(f"[tripadvisor] Error switching back to default content: {e}")
        
        # Navigate to the target thread
        logger.info(f"[tripadvisor] Navigating to thread URL: {thread_url}")
        driver.get(thread_url)
        
        # Wait for the page to load
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(2, 4))
        
        # Scroll down to read the thread content
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(200, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(1, 3))
        
        # Click the "Reply" button using multiple potential selectors
        reply_selectors = [
            (By.XPATH, "//button[contains(text(), 'Reply')]"),
            (By.XPATH, "//a[contains(text(), 'Reply')]"),
            (By.CSS_SELECTOR, "button.reply-button"),
            (By.CSS_SELECTOR, "a.reply-button"),
            (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reply')]"),
            (By.XPATH, "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reply')]")
        ]
        
        reply_clicked = False
        for selector_type, selector in reply_selectors:
            try:
                reply_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                # Scroll to button for better visibility
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", reply_btn)
                time.sleep(random.uniform(0.5, 1.5))
                
                simulate_human_behavior(driver, reply_btn)
                reply_btn.click()
                reply_clicked = True
                logger.info(f"[tripadvisor] Clicked reply button using selector: {selector}")
                time.sleep(random.uniform(1, 2))
                break
            except Exception as e:
                logger.debug(f"[tripadvisor] Reply button not found with selector {selector}: {e}")
        
        if not reply_clicked:
            logger.error("[tripadvisor] Could not find reply button")
            return False
        
        # Look for the reply input field
        reply_box = None
        input_selectors = [
            (By.TAG_NAME, "textarea"),
            (By.CSS_SELECTOR, "[contenteditable='true']"),
            (By.XPATH, "//*[contains(@placeholder, 'Write your reply')]"),
            (By.CSS_SELECTOR, "div.reply-box textarea"),
            (By.CSS_SELECTOR, "div.reply-area textarea")
        ]
        
        for selector_type, selector in input_selectors:
            try:
                reply_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                simulate_human_behavior(driver, reply_box)
                try:
                    reply_box.clear()
                except:
                    pass  # Some editors can't be cleared
                
                reply_box.click()
                logger.info(f"[tripadvisor] Found reply box using selector: {selector}")
                break
            except Exception as e:
                logger.debug(f"[tripadvisor] Reply box not found with selector {selector}: {e}")
        
        if not reply_box:
            logger.error("[tripadvisor] Could not find reply input field")
            return False
        
        # Type reply with human-like delays
        for char, delay in _randomize_typing_speed(content, min_delay=0.03, max_delay=0.15):
            reply_box.send_keys(char)
            time.sleep(delay)
        
        # Random pause before posting
        time.sleep(random.uniform(2, 4))
        
        # Find and click the post/submit button
        post_selectors = [
            (By.XPATH, "//button[contains(text(), 'Post') and contains(text(), 'Reply')]"),
            (By.XPATH, "//button[contains(text(), 'Post')]"),
            (By.XPATH, "//button[contains(text(), 'Submit')]"),
            (By.XPATH, "//input[@type='submit' and contains(@value, 'Post')]"),
            (By.CSS_SELECTOR, "button.submit")
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
                logger.info(f"[tripadvisor] Clicked post button using selector: {selector}")
                break
            except Exception as e:
                logger.debug(f"[tripadvisor] Post button not found with selector {selector}: {e}")
        
        if not post_clicked:
            logger.warning("[tripadvisor] Post button not found; using keyboard shortcut")
            reply_box.send_keys(Keys.CONTROL + Keys.ENTER)
            logger.info("[tripadvisor] Used Ctrl+Enter to submit reply")
        
        # Wait for post to process
        time.sleep(random.uniform(4, 6))
        
        # Take a verification screenshot
        try:
            debug_dir = "debug_screenshots"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            driver.save_screenshot(f"{debug_dir}/tripadvisor_{timestamp}.png")
            logger.info(f"[tripadvisor] Saved verification screenshot to {debug_dir}/tripadvisor_{timestamp}.png")
        except Exception as e:
            logger.error(f"[tripadvisor] Failed to save verification screenshot: {e}")
        
        return True
    except Exception as e:
        logger.error(f"[tripadvisor] Error during TripAdvisor automation: {e}")
        return False
    finally:
        driver.quit()
