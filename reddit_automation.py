import os
import random
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from automation_utils import init_driver, solve_captcha_if_present, simulate_human_behavior, randomize_typing_speed

logger = logging.getLogger(__name__)

def reddit_login_and_post(username=None, password=None, content="", subreddit="", post_title="", proxy=None, comment_mode=False, post_id=None):
    """
    Log in to Reddit and either:
    1. Create a new post (when comment_mode=False)
    2. Comment on an existing post (when comment_mode=True, post_id required)
    
    Args:
        username: Reddit username
        password: Reddit password
        content: The text to post/comment
        subreddit: Subreddit name without r/ prefix (for new posts)
        post_title: Post title (for new posts)
        proxy: Optional proxy to use
        comment_mode: Whether to comment instead of creating a post
        post_id: Post ID when in comment mode
    
    Returns:
        Boolean indicating success
    """
    # Load credentials from environment variables if not provided.
    if not username:
        username = os.environ.get("REDDIT_USER1", "")
    if not password:
        password = os.environ.get("REDDIT_PASS1", "")
    
    logger.info(f"[reddit] Initializing Reddit {'comment' if comment_mode else 'post'} automation")
    
    driver = init_driver(proxy)
    try:
        driver.set_page_load_timeout(30)
        
        # Start with the Reddit homepage instead of directly going to the login page
        # This more closely mimics human behavior
        driver.get("https://www.reddit.com")
        time.sleep(random.uniform(2, 4))
        
        # Check for cookie banner and accept it if present
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Agree')]"))
            )
            simulate_human_behavior(driver, cookie_button)
            cookie_button.click()
            time.sleep(random.uniform(1, 2))
        except (TimeoutException, NoSuchElementException):
            logger.info("[reddit] No cookie banner found or already accepted")
        
        # Look for login button
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Log In')]"))
            )
            simulate_human_behavior(driver, login_button)
            login_button.click()
            time.sleep(random.uniform(2, 3))
        except (TimeoutException, NoSuchElementException):
            logger.info("[reddit] No login button found, trying direct login URL")
            driver.get("https://www.reddit.com/login")
            time.sleep(random.uniform(2, 3))
        
        # Wait for the login fields to appear
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "loginUsername")))
        
        # Type username and password with human-like delays
        user_field = driver.find_element(By.ID, "loginUsername")
        pass_field = driver.find_element(By.ID, "loginPassword")
        
        # Clear fields
        user_field.clear()
        pass_field.clear()
        
        # Type username with random delays
        simulate_human_behavior(driver, user_field)
        for char, delay in _randomize_typing_speed(username):
            user_field.send_keys(char)
            time.sleep(delay)
        
        # Pause between fields
        time.sleep(random.uniform(0.5, 1.5))
        
        # Type password with random delays
        simulate_human_behavior(driver, pass_field)
        for char, delay in _randomize_typing_speed(password):
            pass_field.send_keys(char)
            time.sleep(delay)
        
        # Click login button instead of pressing Enter
        try:
            login_submit = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log In')]"))
            )
            simulate_human_behavior(driver, login_submit)
            login_submit.click()
        except (TimeoutException, NoSuchElementException):
            # Fallback to Enter key
            pass_field.send_keys(Keys.ENTER)
        
        # Wait until login is complete: URL should no longer contain "login"
        WebDriverWait(driver, 15).until(
            lambda d: "reddit.com" in d.current_url.lower() and "login" not in d.current_url.lower()
        )
        logger.info("[reddit] User logged in successfully")
        
        # Small delay after login
        time.sleep(random.uniform(2, 4))
        
        # Check for CAPTCHA on login page and solve if present
        if "login" in driver.current_url.lower():
            if solve_captcha_if_present(driver):
                # Try login again after solving CAPTCHA
                pass_field = driver.find_element(By.ID, "loginPassword")
                pass_field.send_keys(Keys.ENTER)
                WebDriverWait(driver, 15).until(
                    lambda d: "reddit.com" in d.current_url.lower() and "login" not in d.current_url.lower()
                )
                logger.info("[reddit] User logged in after CAPTCHA resolution")
            else:
                logger.error("[reddit] Login failed, still on login page")
                return False
        
        # COMMENT MODE: Comment on an existing post
        if comment_mode and post_id:
            # Navigate to the post
            post_url = f"https://www.reddit.com/comments/{post_id}"
            logger.info(f"[reddit] Navigating to post: {post_url}")
            driver.get(post_url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(random.uniform(3, 5))
            
            # Simulate reading the post
            simulate_human_behavior(driver)
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(2, 5))
            
            # Find the comment box using multiple possible selectors
            comment_box = None
            selectors = [
                (By.CSS_SELECTOR, "div[data-test-id='comment-submission-form-richtext'] div[contenteditable='true']"),
                (By.XPATH, "//div[contains(@data-test-id, 'comment-submission-form')]//*[@contenteditable='true']"),
                (By.CSS_SELECTOR, "textarea[data-test-id='comment-submission-form-textarea']"),
                (By.CSS_SELECTOR, "textarea.commentbox-textarea"),
                (By.XPATH, "//textarea[contains(@placeholder, 'What are your thoughts')]")
            ]
            
            for selector_type, selector in selectors:
                try:
                    comment_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    if comment_box.is_displayed():
                        simulate_human_behavior(driver, comment_box)
                        comment_box.click()
                        logger.info(f"[reddit] Found comment box with selector: {selector}")
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not comment_box:
                logger.error("[reddit] Could not find comment box")
                return False
            
            # Type the comment with human-like delays
            for char, delay in _randomize_typing_speed(content, min_delay=0.01, max_delay=0.15):
                comment_box.send_keys(char)
                time.sleep(delay)
            
            # Wait a bit before submitting
            time.sleep(random.uniform(1, 3))
            
            # Find and click the comment button
            submit_selectors = [
                (By.XPATH, "//button[contains(text(), 'Comment')]"),
                (By.CSS_SELECTOR, "button[data-test-id='comment-submission-form-submit']"),
                (By.XPATH, "//button[contains(@class, 'comment-submission')]")
            ]
            
            submit_btn = None
            for selector_type, selector in submit_selectors:
                try:
                    submit_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector))
                    )
                    if submit_btn.is_displayed():
                        simulate_human_behavior(driver, submit_btn)
                        submit_btn.click()
                        logger.info("[reddit] Clicked comment button")
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not submit_btn:
                logger.warning("[reddit] Could not find submit button, trying shortcut")
                # Try using keyboard shortcut as fallback
                comment_box.send_keys(Keys.CONTROL + Keys.ENTER)
            
            # Wait for comment to appear
            time.sleep(random.uniform(3, 5))
            success = True
            
        # POST MODE: Create a new post
        else:
            # Navigate to the submission page on old Reddit (more reliable interface)
            submit_url = f"https://old.reddit.com/r/{subreddit}/submit"
            logger.info(f"[reddit] Navigating to submission page: {submit_url}")
            driver.get(submit_url)
            
            # Wait for the page to load
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "title")))
            time.sleep(random.uniform(1, 2))
            
            # Select "Text" post type if available
            try:
                choice = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "choice_self")))
                simulate_human_behavior(driver, choice)
                choice.click()
                time.sleep(random.uniform(0.5, 1))
            except (TimeoutException, NoSuchElementException):
                logger.info("[reddit] Self post choice not clickable or not found")
            
            # Wait for the title and text fields
            title_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "title")))
            text_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "text")))
            
            # Clear fields
            simulate_human_behavior(driver, title_input)
            title_input.clear()
            
            # Type title with random delays
            for char, delay in _randomize_typing_speed(post_title):
                title_input.send_keys(char)
                time.sleep(delay)
            
            # Switch to text field
            time.sleep(random.uniform(0.8, 1.5))
            simulate_human_behavior(driver, text_input)
            text_input.clear()
            
            # Type content with random delays
            for char, delay in _randomize_typing_speed(content):
                text_input.send_keys(char)
                time.sleep(delay)
            
            # Small delay before submission
            time.sleep(random.uniform(1, 3))
            
            # Use an XPath with case-insensitive search for "submit"
            submit_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]")
                )
            )
            simulate_human_behavior(driver, submit_btn)
            submit_btn.click()
            
            # Wait for submission to complete
            time.sleep(random.uniform(3, 5))
            success = True
        
        # Final status
        if success:
            logger.info("[reddit] Content successfully posted")
            return True
        else:
            logger.error("[reddit] Failed to post content")
            return False
            
    except Exception as e:
        logger.error(f"[reddit] Error during Reddit automation: {e}")
        return False
    finally:
        # Take a screenshot for debugging in case of issues
        try:
            debug_dir = "debug_screenshots"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            driver.save_screenshot(f"{debug_dir}/reddit_{timestamp}.png")
        except Exception as screenshot_error:
            logger.error(f"[reddit] Error taking debug screenshot: {screenshot_error}")
            
        driver.quit()
