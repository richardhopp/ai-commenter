import undetected_chromedriver as uc
import random
import time
import itertools
import requests
import openai
from packaging.version import Version as LooseVersion
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
        "Living Abroad - Aparthotels": {
            "url": "https://aparthotel.com",
            "description": "Discover global aparthotels and rental options with in-depth local living guides.",
            "count": random.randint(0, 5)
        },
        "Crypto Rentals": {
            "url": "https://cryptoapartments.com",
            "description": "Modern rental platform accepting cryptocurrency with travel and lifestyle insights.",
            "count": random.randint(0, 5)
        },
        "Serviced Apartments": {
            "url": "https://servicedapartments.net",
            "description": "Curated listings of serviced apartments featuring travel tips and local renting rules.",
            "count": random.randint(0, 5)
        },
        "Furnished Apartments": {
            "url": "https://furnishedapartments.net",
            "description": "Immediate living solutions with organized listings and analyses of local living conditions.",
            "count": random.randint(0, 5)
        },
        "Real Estate Abroad": {
            "url": "https://realestateabroad.com",
            "description": "International property developments and investment insights with market analysis.",
            "count": random.randint(0, 5)
        },
        "Property Developments": {
            "url": "https://propertydevelopments.com",
            "description": "Latest new property projects with detailed buying guides and financing options.",
            "count": random.randint(0, 5)
        },
        "Property Investment": {
            "url": "https://propertyinvestment.net",
            "description": "Dedicated to property investment—offering how-to articles, financing guides, and yield analysis.",
            "count": random.randint(0, 5)
        },
        "Golden Visa Opportunities": {
            "url": "https://golden-visa.com",
            "description": "Exclusive insights on Golden Visa properties and investment immigration for the global elite.",
            "count": random.randint(0, 5)
        },
        "Residence by Investment": {
            "url": "https://residence-by-investment.com",
            "description": "Guidance on securing residency through property investments, featuring country-specific strategies.",
            "count": random.randint(0, 5)
        },
        "Citizenship by Investment": {
            "url": "https://citizenship-by-investment.net",
            "description": "Comprehensive information on citizenship-by-investment programs and securing your wealth globally.",
            "count": random.randint(0, 5)
        }
    }
    selected_site = min(sites.items(), key=lambda item: item[1]["count"])
    return selected_site[0], selected_site[1], complexity

def generate_ai_response(question_text, additional_prompt, use_chatgpt=True):
    if not use_chatgpt:
        return "Default answer: " + question_text[:100] + "..."
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
            max_tokens=250 if complexity == "detailed" else 100,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error generating answer: {e}"

def solve_captcha_if_present(driver):
    """
    Checks for a CAPTCHA on the page and uses 2Captcha to solve it if found.
    Returns True if a CAPTCHA was solved, else False.
    """
    # Look for a data-sitekey in the page source
    page_html = driver.page_source
    captcha_type = None
    site_key = None
    if "data-sitekey" in page_html:
        start = page_html.find('data-sitekey="') + len('data-sitekey="')
        end = page_html.find('"', start)
        site_key = page_html[start:end]
        captcha_type = "recaptcha"
    if not site_key:
        # Try checking for an iframe with a src containing "sitekey=" or "k="
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and ("sitekey=" in src or "k=" in src):
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(src).query)
                site_key = qs.get("sitekey", qs.get("k", [None]))[0]
                captcha_type = "recaptcha"
                break
    if not site_key or not captcha_type:
        return False
    api_key = ""
    try:
        api_key = driver.execute_script("return window.streamlit_secrets.captcha.api_key")
    except Exception:
        # Fallback to st.secrets (if accessible) or environment variable
        try:
            api_key = st.secrets["captcha"]["api_key"]
        except Exception:
            api_key = ""
    if not api_key:
        print("2Captcha API key not found.")
        return False

    # Submit CAPTCHA solving request to 2Captcha
    data = {
        "key": api_key,
        "method": "userrecaptcha",
        "googlekey": site_key,
        "pageurl": driver.current_url,
        "json": 1
    }
    try:
        resp = requests.post("https://2captcha.com/in.php", data=data).json()
    except Exception as e:
        print("Error sending CAPTCHA request:", e)
        return False

    if resp.get("status") != 1:
        print("Error from 2Captcha:", resp.get("request"))
        return False

    captcha_id = resp.get("request")
    token = None
    for _ in range(20):
        time.sleep(5)
        try:
            r = requests.get(f"https://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1").json()
        except Exception as e:
            print("Error polling 2Captcha:", e)
            continue
        if r.get("status") == 1:
            token = r.get("request")
            break
        elif r.get("request") != "CAPCHA_NOT_READY":
            print("2Captcha error:", r.get("request"))
            break

    if not token:
        return False

    # Inject the token into the CAPTCHA response field (for reCAPTCHA)
    driver.execute_script("""
        document.querySelectorAll('[name="g-recaptcha-response"]').forEach(el => {
            el.style.display = 'block';
            el.value = arguments[0];
        });
    """, token)
    return True
