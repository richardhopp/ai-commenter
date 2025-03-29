import undetected_chromedriver as uc
import random
import time
import itertools
import requests
import openai
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# List of User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
]

def _rotate_user_agent():
    return random.choice(USER_AGENTS)

def init_driver(proxy_address=None):
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    ua = _rotate_user_agent()
    options.add_argument(f"--user-agent={ua}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if proxy_address:
        options.add_argument(f"--proxy-server={proxy_address}")
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(30)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def search_google(query, max_results=5):
    driver = init_driver()
    driver.get(f"https://www.google.com/search?q={query}")
    time.sleep(random.uniform(2, 4))
    results = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        for element in elements[:max_results]:
            results.append(element.get_attribute("href"))
    except Exception:
        pass
    driver.quit()
    return results

def extract_thread_content(url):
    driver = init_driver()
    driver.get(url)
    time.sleep(random.uniform(3,6))
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")
    question_element = soup.find("div", {"class": "question_text"})
    if question_element:
        return question_element.get_text(strip=True)
    paragraphs = soup.find_all("p")
    if paragraphs:
        return " ".join(p.get_text(strip=True) for p in paragraphs)
    return ""

def choose_money_site(question_text):
    word_count = len(question_text.split())
    complexity = "simple" if word_count < 20 else "detailed"
    sites = {
        "Living Abroad": {"url": "https://aparthotel.com", "description": "Monthly rentals & aparthotels worldwide", "count": random.randint(0,5)},
        "Real Estate Abroad": {"url": "https://realestateabroad.com", "description": "New build properties and real estate investments", "count": random.randint(0,5)},
        "Investment Visas": {"url": "https://investmentvisa.com", "description": "Guidance on investment visas and residency solutions", "count": random.randint(0,5)}
    }
    selected_site = min(sites.items(), key=lambda item: item[1]["count"])
    return selected_site[0], selected_site[1], complexity

def generate_ai_response(question_text, additional_prompt, use_chatgpt=True):
    if not use_chatgpt:
        return "Default answer: " + question_text[:100] + "..."
    # Smart prompt including a plug for a money site from the smart funnel
    site_name, site_details, complexity = choose_money_site(question_text)
    plug = f"Click here for more details: {site_details['url']}. {site_details['description']}."
    prompt = (
        f"Analyze the following question and provide a clear, concise answer. "
        f"Include a subtle reference to our service: {plug}\n\n"
        f"Question: {question_text}\nAdditional instructions: {additional_prompt}\n\nAnswer:"
    )
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=250 if complexity=="detailed" else 100,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error generating answer: {e}"
