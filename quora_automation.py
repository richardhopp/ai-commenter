import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from automation_utils import init_driver, solve_captcha_if_present

def quora_login_and_post(username, password, content, question_url=None, proxy=None):
    driver = init_driver(proxy)
    try:
        driver.set_page_load_timeout(30)
        driver.get("https://www.quora.com/login")
        
        # Wait for login fields and submit credentials
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "email")))
        email_field = driver.find_element(By.NAME, "email")
        pwd_field = driver.find_element(By.NAME, "password")
        email_field.send_keys(username)
        pwd_field.send_keys(password)
        pwd_field.send_keys(Keys.ENTER)
        time.sleep(5)
        
        # If still on login page, try to solve CAPTCHA if present
        if "login" in driver.current_url.lower():
            if solve_captcha_if_present(driver):
                pwd_field = driver.find_element(By.NAME, "password")
                pwd_field.send_keys(Keys.ENTER)
                time.sleep(5)
        
        if question_url:
            # Navigate to the target question page
            driver.get(question_url)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # Try clicking the "Answer" button
            try:
                answer_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Answer')]"))
                )
                answer_btn.click()
            except Exception as e:
                print("Answer button not found; proceeding without clicking it:", e)
            time.sleep(3)
            
            # Try to locate the answer field using multiple selectors
            try:
                # First, try a contenteditable element
                answer_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true']"))
                )
            except Exception as e:
                print("Contenteditable answer box not found, trying textarea:", e)
                answer_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
                )
            answer_box.click()  # ensure focus
            answer_box.send_keys(content)
            
            # Try to click the Submit button
            try:
                submit_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit') or contains(text(),'Answer')]"))
                )
                submit_btn.click()
            except Exception as e:
                print("Submit button not found or not clickable; using keyboard shortcut:", e)
                answer_box.send_keys(Keys.CONTROL + Keys.ENTER)
            time.sleep(5)
        else:
            # New Question flow (if needed; for posting a question rather than an answer)
            driver.get("https://www.quora.com/")
            time.sleep(3)
            try:
                add_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-functional-selector='add-question-button']"))
                )
                add_btn.click()
            except Exception:
                add_btn = driver.find_element(By.XPATH, "//*[contains(text(),'Add Question')]")
                add_btn.click()
            time.sleep(3)
            try:
                q_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[contenteditable='true']"))
                )
            except Exception:
                q_input = driver.find_element(By.TAG_NAME, "textarea")
            q_input.send_keys(content)
            try:
                post_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Add Question' or normalize-space()='Submit']"))
                )
                post_btn.click()
            except Exception:
                q_input.send_keys(Keys.CONTROL + Keys.ENTER)
            time.sleep(5)
        return True
    finally:
        driver.quit()
