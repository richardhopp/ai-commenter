# app.py

import sys
import importlib.util
import re
import streamlit as st
import time
import random
import openai

from packaging.version import Version as PackagingVersion

#############################################
# Custom MyLooseVersion
#############################################
class MyLooseVersion(PackagingVersion):
    """
    A custom version class to emulate distutils.version.LooseVersion,
    providing both .version and .vstring attributes.
    """
    def __init__(self, version):
        self.vstring = version  # distutils' LooseVersion stored the raw string in .vstring
        try:
            super().__init__(version)
            # distutils LooseVersion used .version as a list of string tokens
            self.version = str(self).split(".")
        except:
            # If parse fails, store a fallback
            self._version = None
            self.version = [version]

    def __str__(self):
        if self._version is not None:
            return super().__str__()
        else:
            return self.vstring

    def __repr__(self):
        return f"<MyLooseVersion {str(self)}>"

#############################################
# Patch setuptools & undetected in memory
#############################################
def patch_setuptools():
    spec = importlib.util.find_spec("setuptools")
    if spec is None:
        print("Warning: setuptools not found. Please ensure it's installed.")
    else:
        print("setuptools found.")

def patch_undetected_in_memory():
    """
    In-memory patch: override undetected_chromedriver.patcher.LooseVersion 
    with MyLooseVersion so references to .vstring or .version won't break.
    """
    try:
        import undetected_chromedriver.patcher as patcher
        patcher.LooseVersion = MyLooseVersion
        print("Patched undetected_chromedriver in memory with MyLooseVersion.")
    except Exception as e:
        print("Error patching undetected_chromedriver in memory:", e)

patch_setuptools()
patch_undetected_in_memory()

#############################################
# Now import the rest
#############################################

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

st.set_page_config(page_title="Stealth Multi-Platform Poster", layout="centered")
st.title("Stealth Multi-Platform Poster with Full Auto & Custom LooseVersion")
st.markdown(
    "This tool can post on Quora, Reddit, TripAdvisor in **Manual mode** (one site at a time), "
    "or do **Auto mode** (multiple sites, multiple accounts) searching Google for threads and posting answers. "
    "We've patched undetected_chromedriver to handle any string (like 'tokyo') as a version."
)

# Session-based log
if "log_records" not in st.session_state:
    st.session_state.log_records = []

#############################################
# Load account credentials from secrets
#############################################
def load_accounts(platform):
    """Return a list of (display_name, username, password) for the given platform."""
    accounts = []
    if platform in st.secrets:
        config = st.secrets[platform]
        i = 1
        while f"user{i}" in config and f"pass{i}" in config:
            disp = f"Account {i} - {config[f'user{i}']}"
            usr = config[f"user{i}"]
            pwd = config[f"pass{i}"]
            accounts.append((disp, usr, pwd))
            i += 1
    return accounts

#############################################
# Manual or Auto Mode
#############################################
mode_choice = st.selectbox("Select Mode", ["quora", "reddit", "tripadvisor", "auto"])

############################
# Manual Mode
############################
if mode_choice != "auto":
    # Load accounts for the chosen platform
    accounts = load_accounts(mode_choice)
    if not accounts:
        st.error(f"No accounts configured for {mode_choice}. Please add them to secrets.")
        st.stop()
    selected_account = st.selectbox(f"Choose {mode_choice} Account", [a[0] for a in accounts])
    account = next(a for a in accounts if a[0] == selected_account)
    username, password = account[1], account[2]

    proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")

    if mode_choice == "quora":
        target_url = st.text_input("Quora question URL (optional)", help="Leave blank to post a new question.")
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
        openai.api_key = st.secrets["openai"]["api_key"]
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

    # Choose sites
    auto_sites = st.multiselect(
        "Select target sites for auto mode",
        ["quora", "reddit", "tripadvisor"],
        default=["quora", "reddit", "tripadvisor"]
    )
    # For each chosen site, pick an account
    site_account_map = {}
    for site in auto_sites:
        site_accounts = load_accounts(site)
        if not site_accounts:
            st.warning(f"No accounts found for {site}. Please add them in secrets.")
        sel_acc = st.selectbox(f"Choose {site} Account", [a[0] for a in site_accounts], key=f"auto_{site}")
        site_account_map[site] = next(a for a in site_accounts if a[0] == sel_acc)

    root_keyword = st.text_input("Root Keyword(s)", "tokyo", help="Enter the search keyword(s).")
    max_results = st.number_input("Max Results per Site", min_value=1, max_value=20, value=3)
    delay_between = st.number_input("Delay between threads (seconds)", min_value=5, max_value=60, value=10)
    proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")

    use_chatgpt = st.checkbox("Generate answer with ChatGPT", value=True)
    if use_chatgpt:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt_for_analysis = st.text_area("Additional instructions (optional)", "Provide a concise, clear answer.", height=80)

    if st.button("Run Auto Process"):
        st.info("Starting auto process: Searching for threads and generating responses...")
        for site in auto_sites:
            # domain mapping
            domain_map = {"quora": "quora.com", "reddit": "reddit.com", "tripadvisor": "tripadvisor.com"}
            if site not in domain_map:
                st.error(f"Unknown site: {site}. Skipping.")
                continue
            domain = domain_map[site]
            query = f'site:{domain} "{root_keyword}"'
            st.write(f"Searching for threads on {site} with query: {query}")

            # get account credentials
            selected_acc = site_account_map[site]
            username, password = selected_acc[1], selected_acc[2]

            # search
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
                        # Post to the site
                        if site == "quora":
                            res = quora_login_and_post(username, password, final_answer, question_url=url, proxy=proxy)
                            posted_platform = "auto/quora"
                        elif site == "reddit":
                            # For reddit auto mode, use default subreddit 'test' and post title 'Auto Post'
                            res = reddit_login_and_post(username, password, final_answer, "test", "Auto Post", proxy=proxy)
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

############################
# Log Report
############################
st.header("Log Report")
if st.session_state.log_records:
    st.table(st.session_state.log_records)
else:
    st.write("No log records yet.")
