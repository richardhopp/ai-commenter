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
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "loginUsername")))
        user_field = driver.find_element(By.ID, "loginUsername")
        pass_field = driver.find_element(By.ID, "loginPassword")
        user_field.send_keys(username)
        pass_field.send_keys(password)
        pass_field.send_keys(Keys.ENTER)
        time.sleep(5)
        if "login" in driver.current_url.lower():
            if solve_captcha_if_present(driver):
                pass_field = driver.find_element(By.ID, "loginPassword")
                pass_field.send_keys(Keys.ENTER)
                time.sleep(5)
        submit_url = f"https://old.reddit.com/r/{subreddit}/submit"
        driver.get(submit_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "title")))
        try:
            choice = driver.find_element(By.ID, "choice_self")
            if choice.is_displayed():
                choice.click()
        except:
            pass
        title_input = driver.find_element(By.NAME, "title")
        text_input = driver.find_element(By.NAME, "text")
        title_input.clear()
        title_input.send_keys(title)
        text_input.clear()
        text_input.send_keys(content)
        time.sleep(random.uniform(1,3))
        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(),'submit') or contains(text(),'Submit')]")
        submit_btn.click()
        time.sleep(5)
        return True
    finally:
        driver.quit()
