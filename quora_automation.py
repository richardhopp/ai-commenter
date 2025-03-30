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
        
        # Log in
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "email")))
        email_field = driver.find_element(By.NAME, "email")
        pwd_field = driver.find_element(By.NAME, "password")
        email_field.send_keys(username)
        pwd_field.send_keys(password)
        pwd_field.send_keys(Keys.ENTER)
        time.sleep(5)
        
        if "login" in driver.current_url.lower():
            if solve_captcha_if_present(driver):
                pwd_field = driver.find_element(By.NAME, "password")
                pwd_field.send_keys(Keys.ENTER)
                time.sleep(5)
        
        if question_url:
            driver.get(question_url)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # Try clicking the "Answer" button using multiple selectors
            answer_clicked = False
            answer_selectors = [
                (By.XPATH, "//*[contains(text(),'Answer')]"),
                (By.XPATH, "//button[contains(.,'Answer')]")
            ]
            for sel in answer_selectors:
                try:
                    answer_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(sel)
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", answer_btn)
                    answer_btn.click()
                    answer_clicked = True
                    break
                except Exception as e:
                    print("Answer button not found with selector", sel, ":", e)
            if not answer_clicked:
                print("No clickable Answer button found; proceeding assuming editor is already open.")
            time.sleep(3)
            
            # Try finding the answer input field with a list of selectors
            field_selectors = [
                (By.CSS_SELECTOR, "div[contenteditable='true']"),
                (By.TAG_NAME, "textarea"),
                (By.XPATH, "//*[contains(@placeholder, 'Write your answer')]")
            ]
            answer_box = None
            for by, selector in field_selectors:
                try:
                    answer_box = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", answer_box)
                    answer_box.click()
                    break
                except Exception as e:
                    print("Answer field not found with selector", selector, ":", e)
            if not answer_box:
                raise Exception("Unable to locate an answer input field.")
            
            answer_box.send_keys(content)
            
            # Attempt to click the submit button
            try:
                submit_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit') or contains(text(),'Answer')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                submit_btn.click()
            except Exception as e:
                print("Submit button not found or not clickable; using CTRL+ENTER shortcut:", e)
                answer_box.send_keys(Keys.CONTROL + Keys.ENTER)
            time.sleep(5)
        else:
            # New Question flow (if needed)
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
