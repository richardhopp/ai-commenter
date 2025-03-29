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
        try:
            consent_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            consent_btn.click()
        except:
            pass
        try:
            sign_in_link = driver.find_element(By.LINK_TEXT, "Sign in")
            sign_in_link.click()
        except:
            sign_in_link = driver.find_element(By.XPATH, "//*[contains(text(),'Sign in') or contains(text(),'Log in')]")
            sign_in_link.click()
        time.sleep(5)
        try:
            login_iframe = None
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                src = frame.get_attribute("src")
                if src and ("login" in src or "RegistrationController" in src):
                    login_iframe = frame
                    break
            if login_iframe:
                driver.switch_to.frame(login_iframe)
        except:
            pass
        possible_email_selectors = [(By.NAME, "email"), (By.ID, "email")]
        email_field = None
        for sel in possible_email_selectors:
            try:
                email_field = driver.find_element(*sel)
                if email_field.is_displayed():
                    break
            except:
                continue
        possible_pass_selectors = [(By.NAME, "password"), (By.ID, "password")]
        pass_field = None
        for sel in possible_pass_selectors:
            try:
                pass_field = driver.find_element(*sel)
                if pass_field.is_displayed():
                    break
            except:
                continue
        if email_field and pass_field:
            email_field.clear()
            email_field.send_keys(username)
            pass_field.clear()
            pass_field.send_keys(password)
            pass_field.send_keys(Keys.ENTER)
        time.sleep(5)
        if "Sign in" in driver.title or "Log in" in driver.title:
            if solve_captcha_if_present(driver):
                if pass_field:
                    pass_field.send_keys(Keys.ENTER)
            time.sleep(5)
        try:
            driver.switch_to.default_content()
        except:
            pass
        driver.get(thread_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        try:
            reply_toggle = driver.find_element(By.XPATH, "//button[contains(text(),'Reply') or //a[contains(text(),'Reply')]]")
            if reply_toggle.is_displayed():
                reply_toggle.click()
                time.sleep(2)
        except:
            pass
        reply_box = None
        try:
            reply_box = driver.find_element(By.TAG_NAME, "textarea")
        except:
            try:
                reply_box = driver.find_element(By.CSS_SELECTOR, "[contenteditable='true']")
            except:
                pass
        if reply_box:
            reply_box.clear()
            reply_box.send_keys(content)
        try:
            post_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Post') and contains(text(),'reply')]")
        except:
            try:
                post_btn = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Post your reply']")
            except:
                post_btn = None
        if post_btn:
            post_btn.click()
        else:
            if reply_box:
                reply_box.send_keys(Keys.CONTROL + Keys.ENTER)
        time.sleep(5)
        return True
    finally:
        driver.quit()
