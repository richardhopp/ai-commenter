import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from automation_utils import init_driver, solve_captcha_if_present

def reddit_login_and_post(username, password, content, subreddit, title, proxy=None):
    driver = init_driver(proxy)
    try:
        driver.set_page_load_timeout(30)
        driver.get("https://www.reddit.com/login")
        
        # Wait for the login fields to appear
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "loginUsername")))
        user_field = driver.find_element(By.ID, "loginUsername")
        pass_field = driver.find_element(By.ID, "loginPassword")
        user_field.clear()
        user_field.send_keys(username)
        pass_field.clear()
        pass_field.send_keys(password)
        pass_field.send_keys(Keys.ENTER)
        
        # Wait until login is complete (URL no longer contains 'login')
        WebDriverWait(driver, 15).until(
            lambda d: "reddit.com" in d.current_url.lower() and "login" not in d.current_url.lower()
        )
        time.sleep(3)
        
        # If still on login page, try solving CAPTCHA and re-submit
        if "login" in driver.current_url.lower():
            if solve_captcha_if_present(driver):
                pass_field = driver.find_element(By.ID, "loginPassword")
                pass_field.send_keys(Keys.ENTER)
                WebDriverWait(driver, 15).until(
                    lambda d: "reddit.com" in d.current_url.lower() and "login" not in d.current_url.lower()
                )
                time.sleep(3)
        
        # Navigate to the submission page on old Reddit
        submit_url = f"https://old.reddit.com/r/{subreddit}/submit"
        driver.get(submit_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "title")))
        
        # For self posts, try clicking the "self" choice if available
        try:
            choice = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "choice_self")))
            driver.execute_script("arguments[0].scrollIntoView(true);", choice)
            choice.click()
        except Exception as e:
            print("Self post choice not clickable or not found:", e)
        
        # Wait for the title and text fields
        title_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "title")))
        text_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "text")))
        driver.execute_script("arguments[0].scrollIntoView(true);", title_input)
        title_input.clear()
        title_input.send_keys(title)
        driver.execute_script("arguments[0].scrollIntoView(true);", text_input)
        text_input.clear()
        text_input.send_keys(content)
        
        time.sleep(random.uniform(1, 3))
        
        # Use an XPath that performs a case-insensitive match for "submit"
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        submit_btn.click()
        time.sleep(5)
        return True
    finally:
        driver.quit()
