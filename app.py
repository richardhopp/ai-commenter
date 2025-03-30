import os
import sys
import importlib.util
import re
import time
import random
import openai
import streamlit as st
from packaging.version import Version as PackagingVersion

# --- Monkey-Patching Section ---
class MyLooseVersion:
    """
    A custom version class to emulate distutils.version.LooseVersion.
    Attempts to parse the version string using packaging.version.
    Falls back to storing the raw string.
    """
    def __init__(self, version):
        self.vstring = version
        try:
            parsed = PackagingVersion(version)
            self.parsed = parsed
            self.version = str(parsed).split(".")
        except Exception:
            self.parsed = None
            self.version = [version]

    def __str__(self):
        return str(self.parsed) if self.parsed is not None else self.vstring

    def __repr__(self):
        return f"<MyLooseVersion {str(self)}>"

def patch_setuptools():
    spec = importlib.util.find_spec("setuptools")
    if spec is None:
        print("Warning: setuptools module not found. Please ensure setuptools is installed.")
    else:
        print("setuptools found.")

def patch_undetected_in_memory():
    """
    In-memory patch: override undetected_chromedriver.patcher.LooseVersion
    with our custom MyLooseVersion.
    """
    try:
        import undetected_chromedriver.patcher as patcher
        patcher.LooseVersion = MyLooseVersion
        print("Patched undetected_chromedriver.patcher in memory with MyLooseVersion.")
    except Exception as e:
        print("Error patching undetected_chromedriver in memory:", e)

patch_setuptools()
patch_undetected_in_memory()

# --- Now Import the Rest ---
from quora_automation import quora_login_and_post
from reddit_automation import reddit_login_and_post
from tripadvisor_automation import tripadvisor_login_and_post
from automation_utils import (
    search_google,
    extract_thread_content,
    choose_money_site,
    generate_ai_response,
    solve_captcha_if_present
)

# --- Configure OpenAI API Key from Environment Variables ---
openai.api_key = os.environ.get("OPENAI_API_KEY", "")

#############################################
# Streamlit UI Setup
#############################################
st.set_page_config(page_title="Stealth Multi-Platform Poster", layout="centered")
st.title("Stealth Multi-Platform Poster with Custom LooseVersion")
st.markdown(
    "This tool automatically searches for threads, analyzes questions using ChatGPT, and posts tailored answers on "
    "Quora, Reddit, and TripAdvisor. You can choose Manual mode to post to one platform or Auto mode to search for "
    "threads across multiple sites. A log report of processed URLs and statuses is maintained below."
)

# Browser Mode Toggle: Headless vs. Headful (for visible Chrome debugging)
display_mode = st.radio("Browser Mode", options=["Headless", "Headful"], index=0)
os.environ["CHROME_HEADLESS"] = "true" if display_mode == "Headless" else "false"

# Initialize session state log
if "log_records" not in st.session_state:
    st.session_state.log_records = []

#############################################
# Account Credentials Loader
#############################################
def load_accounts(platform):
    """
    Load account credentials from environment variables.
    For example, for Quora, expects variables QUORA_USER1, QUORA_PASS1, etc.
    """
    accounts = []
    idx = 1
    while True:
        user = os.environ.get(f"{platform.upper()}_USER{idx}")
        passwd = os.environ.get(f"{platform.upper()}_PASS{idx}")
        if not user or not passwd:
            break
        accounts.append((f"Account {idx} - {user}", user, passwd))
        idx += 1
    return accounts

#############################################
# Mode Selection: Manual vs. Auto
#############################################
mode_choice = st.selectbox("Select Mode", ["quora", "reddit", "tripadvisor", "auto"])

############################
# Manual Mode
############################
if mode_choice != "auto":
    accounts = load_accounts(mode_choice)
    if not accounts:
        st.error(f"No accounts configured for {mode_choice}. Please add them as environment variables.")
        st.stop()
    selected_account = st.selectbox(f"Choose {mode_choice} Account", [a[0] for a in accounts])
    account = next(a for a in accounts if a[0] == selected_account)
    username, password = account[1], account[2]

    proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")

    if mode_choice == "quora":
        target_url = st.text_input("Quora question URL (optional)", help="Paste URL to answer; leave blank to post a new question.")
        content = st.text_area("Content to post", height=150)
    elif mode_choice == "reddit":
        subreddit = st.text_input("Subreddit (without r/)", help="Enter the subreddit.")
        post_title = st.text_input("Post Title", help="Enter a title for the Reddit post.")
        content = st.text_area("Content to post", height=150)
    elif mode_choice == "tripadvisor":
        target_url = st.text_input("TripAdvisor thread URL", help="Enter the forum thread URL.")
        content = st.text_area("Content to post", height=150)

    use_chatgpt = st.checkbox("Generate answer with ChatGPT", value=True)
    if use_chatgpt:
        prompt_for_analysis = st.text_area("Additional instructions (optional)", "Provide a concise, clear answer.", height=80)

    if st.button("Post Content Manually"):
        st.info(f"Posting manually on {mode_choice}...")
        try:
            final_content = content
            if use_chatgpt:
                final_content = generate_ai_response(content, prompt_for_analysis, use_chatgpt=True)
            if mode_choice == "quora":
                res = quora_login_and_post(username, password, final_content, question_url=target_url, proxy=proxy)
                log_url = target_url if target_url else "New Question"
            elif mode_choice == "reddit":
                res = reddit_login_and_post(username, password, final_content, subreddit, post_title, proxy=proxy)
                log_url = f"r/{subreddit}"
            else:
                res = tripadvisor_login_and_post(username, password, final_content, thread_url=target_url, proxy=proxy)
                log_url = target_url

            st.session_state.log_records.append({
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Platform": mode_choice,
                "Thread URL": log_url,
                "Status": "Success" if res else "Failed"
            })
            st.success("Content posted successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

############################
# Auto Mode
############################
else:
    st.subheader("Auto Mode: Multi-Site Searching & Posting")
    auto_sites = st.multiselect(
        "Select target sites for auto mode",
        options=["quora", "reddit", "tripadvisor"],
        default=["quora", "reddit", "tripadvisor"],
        help="Select all sites you want to search and post from."
    )
    # Load accounts for each chosen site from environment variables.
    site_account_map = {}
    for site in auto_sites:
        accs = load_accounts(site)
        if not accs:
            st.warning(f"No accounts found for {site}. Please set environment variables for {site.upper()}_USER1 and {site.upper()}_PASS1.")
        else:
            sel = st.selectbox(f"Choose {site} Account", [a[0] for a in accs], key=f"auto_{site}")
            site_account_map[site] = next(a for a in accs if a[0] == sel)

    root_keyword = st.text_input("Root Keyword(s)", "real estate tokyo", help="Enter the search keyword(s).")
    max_results = st.number_input("Max Results per Site", min_value=1, max_value=20, value=3)
    delay_between = st.number_input("Delay between threads (seconds)", min_value=5, max_value=60, value=10)
    proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")

    use_chatgpt = st.checkbox("Generate answer with ChatGPT", value=True)
    if use_chatgpt:
        prompt_for_analysis = st.text_area("Additional instructions (optional)", "Provide a concise, clear answer.", height=80)

    if st.button("Run Auto Process"):
        st.info("Starting auto process: Searching for threads and generating responses...")
        domain_map = {"quora": "quora.com", "reddit": "reddit.com", "tripadvisor": "tripadvisor.com"}
        for site in auto_sites:
            site = site.strip().lower()
            if site not in domain_map:
                st.error(f"Unknown site: {site}. Skipping.")
                continue
            domain = domain_map[site]
            query = f'site:{domain} "{root_keyword}"'
            st.write(f"Searching for threads on {site} with query: {query}")

            if site in site_account_map:
                acc = site_account_map[site]
                username, password = acc[1], acc[2]
            else:
                st.error(f"No account available for {site}. Skipping.")
                continue

            try:
                thread_urls = search_google(query, max_results)
            except Exception as e:
                st.error(f"Search error on {site}: {e}")
                thread_urls = []
            if not thread_urls:
                st.error(f"No threads found on {site} for '{root_keyword}'.")
            else:
                st.success(f"Found {len(thread_urls)} threads on {site}. Processing...")
                for url in thread_urls:
                    st.write(f"Processing thread: {url}")
                    try:
                        question_text = extract_thread_content(url)
                        if not question_text:
                            st.write("Could not extract question text; skipping.")
                            continue
                        final_answer = generate_ai_response(question_text, prompt_for_analysis, use_chatgpt)
                        st.write("Generated Answer:", final_answer)
                        from automation_utils import choose_money_site
                        site_name, site_details, complexity = choose_money_site(question_text)
                        st.write(f"Smart funnel selected: {site_name} (complexity: {complexity})")
                        if site == "quora":
                            res = quora_login_and_post(username, password, final_answer, question_url=url, proxy=proxy)
                            posted_platform = "auto/quora"
                        elif site == "reddit":
                            subreddit = os.environ.get("REDDIT_SUBREDDIT", "test")
                            post_title = os.environ.get("REDDIT_POST_TITLE", "Auto Post")
                            res = reddit_login_and_post(username, password, final_answer, subreddit, post_title, proxy=proxy)
                            posted_platform = "auto/reddit"
                        else:
                            res = tripadvisor_login_and_post(username, password, final_answer, thread_url=url, proxy=proxy)
                            posted_platform = "auto/tripadvisor"
                        st.session_state.log_records.append({
                            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "Platform": posted_platform,
                            "Thread URL": url,
                            "Status": "Success" if res else "Failed"
                        })
                        st.write(f"Posted on thread: {url}")
                        time.sleep(delay_between)
                    except Exception as e:
                        st.error(f"Error processing {url}: {e}")
        st.success("Auto process completed. Please verify the posts on each site.")

#############################################
# Display Log Report
#############################################
st.header("Log Report")
if st.session_state.log_records:
    st.table(st.session_state.log_records)
else:
    st.write("No log records yet.")
