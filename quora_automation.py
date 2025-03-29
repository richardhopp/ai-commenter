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
            try:
                answer_btn = driver.find_element(By.XPATH, "//*[contains(text(),'Answer')]")
                answer_btn.click()
            except:
                pass
            time.sleep(3)
            try:
                answer_box = driver.find_element(By.CSS_SELECTOR, "[contenteditable='true']")
            except:
                answer_box = driver.find_element(By.TAG_NAME, "textarea")
            answer_box.send_keys(content)
            try:
                submit_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Submit') or contains(text(),'Answer')]")
                submit_btn.click()
            except:
                answer_box.send_keys(Keys.CONTROL + Keys.ENTER)
            time.sleep(5)
        else:
            driver.get("https://www.quora.com/")
            time.sleep(3)
            try:
                add_btn = driver.find_element(By.CSS_SELECTOR, "[data-functional-selector='add-question-button']")
                add_btn.click()
            except:
                add_btn = driver.find_element(By.XPATH, "//*[contains(text(),'Add Question')]")
                add_btn.click()
            time.sleep(3)
            try:
                q_input = driver.find_element(By.CSS_SELECTOR, "[contenteditable='true']")
            except:
                q_input = driver.find_element(By.TAG_NAME, "textarea")
            q_input.send_keys(content)
            try:
                post_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Add Question' or normalize-space()='Submit']")
                post_btn.click()
            except:
                q_input.send_keys(Keys.CONTROL + Keys.ENTER)
            time.sleep(5)
        return True
    finally:
        driver.quit()
