# app.py

#############################################
# Monkey-Patching Section
#############################################

import sys
import importlib.util
import re
import streamlit as st
import time
import random
import openai

# Import PackagingVersion from packaging
from packaging.version import Version as PackagingVersion

class MyLooseVersion:
    """
    A custom version class to emulate distutils.version.LooseVersion.
    This version attempts to parse the input string using packaging.version.Version.
    If parsing fails (e.g. for "real estate tokyo"), it falls back to storing the entire
    string in a list so that .version exists.
    """
    def __init__(self, version):
        try:
            parsed = PackagingVersion(version)
            self.parsed = parsed
            # Create a list of tokens from the parsed version string.
            self.version = str(parsed).split(".")
        except Exception:
            self.parsed = None
            # Fallback: store the original string as a single-element list.
            self.version = [version]

    def __str__(self):
        if self.parsed:
            return str(self.parsed)
        else:
            return "".join(self.version)

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
    with our custom MyLooseVersion, so that any call to LooseVersion(...).version 
    will not fail even if the input isn't a valid version string.
    """
    try:
        import undetected_chromedriver.patcher as patcher
        patcher.LooseVersion = MyLooseVersion
        print("Patched undetected_chromedriver.patcher in memory with MyLooseVersion.")
    except Exception as e:
        print("Error patching undetected_chromedriver in memory:", e)

# Apply patches early to avoid import issues
patch_setuptools()
patch_undetected_in_memory()

#############################################
# Now Import the Rest
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

#############################################
# Streamlit UI Setup
#############################################

st.set_page_config(page_title="Stealth Multi-Platform Poster", layout="centered")
st.title("Stealth Multi-Platform Poster with Custom LooseVersion")
st.markdown(
    "This tool automatically searches for threads, analyzes questions using ChatGPT, and posts tailored answers on "
    "Quora, Reddit, and TripAdvisor. You can choose Manual mode to post to one platform, or Auto mode to search for "
    "threads across multiple sites. A log report of processed URLs and statuses is maintained below."
)

# Initialize a log report list in session state
if "log_records" not in st.session_state:
    st.session_state.log_records = []

#############################################
# Account Credentials
#############################################

def load_accounts(platform):
    accounts = []
    if platform in st.secrets:
        config = st.secrets[platform]
        i = 1
        while f"user{i}" in config and f"pass{i}" in config:
            accounts.append((f"Account {i} - {config[f'user{i}']}", config[f"user{i}"], config[f"pass{i}"]))
            i += 1
    return accounts

#############################################
# Mode Selection
#############################################

platform_choice = st.selectbox("Select Mode", ["quora", "reddit", "tripadvisor", "auto"])

if platform_choice != "auto":
    # Manual Mode: Use credentials for the selected platform.
    accounts = load_accounts(platform_choice)
    if not accounts:
        st.error(f"No accounts configured for {platform_choice}. Please add them via Streamlit Cloud Secrets.")
        st.stop()
    selected_account = st.selectbox("Choose Account", [acc[0] for acc in accounts])
    account = next(acc for acc in accounts if acc[0] == selected_account)
    username, password = account[1], account[2]

    proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")

    if platform_choice == "quora":
        target_url = st.text_input("Quora question URL (optional)", help="Paste URL to answer; leave empty to post new question.")
        content = st.text_area("Content to post", height=150)
    elif platform_choice == "reddit":
        subreddit = st.text_input("Subreddit (without r/)", help="Enter the subreddit to post in.")
        post_title = st.text_input("Post Title", help="Enter a title for the Reddit post.")
        content = st.text_area("Content to post", height=150)
    elif platform_choice == "tripadvisor":
        target_url = st.text_input("TripAdvisor thread URL", help="Enter the URL of the forum thread.")
        content = st.text_area("Content to post", height=150)

    # ChatGPT integration
    use_chatgpt = st.checkbox("Generate answer with ChatGPT", value=True)
    if use_chatgpt:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt_for_analysis = st.text_area("Additional instructions (optional)", "Provide a concise, clear answer.", height=80)

    if st.button("Post Content Manually"):
        st.info(f"Posting manually on {platform_choice}...")
        try:
            final_content = content
            if use_chatgpt:
                final_content = generate_ai_response(content, prompt_for_analysis, use_chatgpt=True)
            if platform_choice == "quora":
                res = quora_login_and_post(username, password, final_content, question_url=target_url, proxy=proxy)
                log_url = target_url if target_url else "New Question"
            elif platform_choice == "reddit":
                res = reddit_login_and_post(username, password, final_content, subreddit, post_title, proxy=proxy)
                log_url = f"r/{subreddit}"
            elif platform_choice == "tripadvisor":
                res = tripadvisor_login_and_post(username, password, final_content, thread_url=target_url, proxy=proxy)
                log_url = target_url
            st.session_state.log_records.append({
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Platform": platform_choice,
                "Thread URL": log_url,
                "Status": "Success" if res else "Failed"
            })
            st.success("Content posted successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

else:
    # Auto Mode: Allow selection of target sites
    st.subheader("Auto Mode: Multi-Site Search & Post")
    auto_sites = st.multiselect(
        "Select target sites for auto mode",
        options=["quora", "reddit", "tripadvisor"],
        default=["quora", "reddit", "tripadvisor"],
        help="Select all sites you want to search and post from."
    )
    root_keyword = st.text_input("Root Keyword(s)", "real estate tokyo", help="Enter keywords for thread search.")
    max_results = st.number_input("Max Results per Site", min_value=1, max_value=20, value=3)
    delay_between = st.number_input("Delay between threads (seconds)", min_value=5, max_value=60, value=10)
    
    # Use a base account from Quora for auto mode (you can expand this to select per site if desired)
    accounts = load_accounts("quora")
    if not accounts:
        st.error("No Quora accounts configured (required for auto mode).")
        st.stop()
    selected_account = st.selectbox("Choose Base Account (Auto Mode)", [acc[0] for acc in accounts])
    account = next(acc for acc in accounts if acc[0] == selected_account)
    username, password = account[1], account[2]
    proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")
    
    use_chatgpt = st.checkbox("Generate answer with ChatGPT", value=True)
    if use_chatgpt:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt_for_analysis = st.text_area("Additional instructions (optional)", "Provide a concise, clear answer.", height=80)
    
    if st.button("Run Auto Process"):
        st.info("Starting auto process: Searching for threads and generating responses...")
        for site in auto_sites:
            domain = {"quora": "quora.com", "reddit": "reddit.com", "tripadvisor": "tripadvisor.com"}[site]
            query = f'site:{domain} "{root_keyword}"'
            st.write(f"Searching for threads on {site} with query: {query}")
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
                            # For Reddit auto mode, use default subreddit "test" and post title "Auto Post"
                            res = reddit_login_and_post(username, password, final_answer, subreddit="test", post_title="Auto Post", proxy=proxy)
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
