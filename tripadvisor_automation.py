import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from automation_utils import init_driver, solve_captcha_if_present

def tripadvisor_login_and_post(username, password, content, thread_url, proxy=None):
    driver = init_driver(proxy)
    try:
        driver.set_page_load_timeout(30)
        driver.get("https://www.tripadvisor.com/")
        time.sleep(5)
        
        # Accept cookie/consent if present
        try:
            consent_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            consent_btn.click()
        except Exception as e:
            print("Consent button not found:", e)
        
        # Click the "Sign in" link
        try:
            sign_in_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Sign in"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", sign_in_link)
            sign_in_link.click()
        except Exception:
            try:
                sign_in_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in') or contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'log in')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", sign_in_link)
                sign_in_link.click()
            except Exception as e:
                print("Sign in link not found:", e)
        time.sleep(5)
        
        # Switch into login iframe if one exists
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                src = frame.get_attribute("src")
                if src and ("login" in src or "RegistrationController" in src):
                    driver.switch_to.frame(frame)
                    print("Switched to login iframe.")
                    break
        except Exception as e:
            print("Error switching to login iframe:", e)
        
        # Locate email field using multiple selectors
        email_field = None
        for sel in [(By.NAME, "email"), (By.ID, "email")]:
            try:
                email_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(sel)
                )
                if email_field.is_displayed():
                    break
            except Exception:
                continue
        
        # Locate password field using multiple selectors
        pass_field = None
        for sel in [(By.NAME, "password"), (By.ID, "password")]:
            try:
                pass_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(sel)
                )
                if pass_field.is_displayed():
                    break
            except Exception:
                continue
        
        if email_field and pass_field:
            email_field.clear()
            email_field.send_keys(username)
            pass_field.clear()
            pass_field.send_keys(password)
            pass_field.send_keys(Keys.ENTER)
        time.sleep(5)
        
        # If still on login page, try solving CAPTCHA and re-submit
        if "Sign in" in driver.title or "Log in" in driver.title:
            if solve_captcha_if_present(driver):
                pass_field = driver.find_element(By.NAME, "password")
                pass_field.send_keys(Keys.ENTER)
            time.sleep(5)
        
        # Switch back to default content
        try:
            driver.switch_to.default_content()
        except Exception as e:
            print("Error switching back to default content:", e)
        
        # Navigate to the target TripAdvisor thread URL
        driver.get(thread_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        
        # Click the "Reply" toggle using a union XPath (tries both button and link)
        try:
            reply_toggle = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "(//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reply')] | //a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reply')])"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", reply_toggle)
            reply_toggle.click()
            time.sleep(2)
        except Exception as e:
            print("Reply toggle not found:", e)
        
        # Locate the reply input field using multiple strategies
        reply_box = None
        field_selectors = [
            (By.TAG_NAME, "textarea"),
            (By.CSS_SELECTOR, "[contenteditable='true']"),
            (By.XPATH, "//*[contains(@placeholder, 'Write your reply')]")
        ]
        for by, selector in field_selectors:
            try:
                reply_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", reply_box)
                reply_box.click()
                break
            except Exception as e:
                print("Reply box not found with selector", selector, ":", e)
        if not reply_box:
            raise Exception("Unable to locate the reply input field.")
        
        # Clear and enter your reply content
        try:
            reply_box.clear()
        except Exception:
            pass
        reply_box.send_keys(content)
        time.sleep(1)
        
        # Locate the Post/Submit button using multiple strategies
        post_btn = None
        post_selectors = [
            (By.XPATH, "(//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'post') and contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reply')])"),
            (By.XPATH, "//input[@type='submit' and contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'post')]")
        ]
        for sel in post_selectors:
            try:
                post_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(sel))
                driver.execute_script("arguments[0].scrollIntoView(true);", post_btn)
                post_btn.click()
                break
            except Exception as e:
                print("Post button not found with selector", sel, ":", e)
        if not post_btn:
            print("Post button not found; using CTRL+ENTER as fallback.")
            reply_box.send_keys(Keys.CONTROL + Keys.ENTER)
        
        time.sleep(5)
        return True
    finally:
        driver.quit()
