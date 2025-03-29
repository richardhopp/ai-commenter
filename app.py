import streamlit as st
import time
import random
import openai

from quora_automation import quora_login_and_post
from reddit_automation import reddit_login_and_post
from tripadvisor_automation import tripadvisor_login_and_post
from automation_utils import search_google, extract_thread_content, choose_money_site, generate_ai_response

st.set_page_config(page_title="Stealth Multi-Platform Poster", layout="centered")
st.title("Stealth Multi-Platform Poster")
st.markdown("This tool automatically searches for threads, analyzes questions using ChatGPT, and posts tailored answers on Quora, Reddit, and TripAdvisor. A log report of processed URLs and statuses is maintained below.")

# Initialize a log report list in session state
if "log_records" not in st.session_state:
    st.session_state.log_records = []

# --- Load account credentials from Streamlit Cloud Secrets ---
def load_accounts(platform):
    accounts = []
    if platform in st.secrets:
        config = st.secrets[platform]
        i = 1
        while f"user{i}" in config and f"pass{i}" in config:
            accounts.append((f"Account {i} - {config[f'user{i}']}", config[f"user{i}"], config[f"pass{i}"]))
            i += 1
    return accounts

platform_choice = st.selectbox("Select Platform", ["quora", "reddit", "tripadvisor", "auto"])
if platform_choice != "auto":
    accounts = load_accounts(platform_choice)
    if not accounts:
        st.error(f"No accounts configured for {platform_choice}. Please add them via Streamlit Cloud Secrets.")
        st.stop()
    selected_account = st.selectbox("Choose Account", [acc[0] for acc in accounts])
    account = next(acc for acc in accounts if acc[0] == selected_account)
    username, password = account[1], account[2]
else:
    # For auto mode, we use Quora’s account as base.
    accounts = load_accounts("quora")
    if not accounts:
        st.error("No Quora accounts configured (required for auto mode).")
        st.stop()
    selected_account = st.selectbox("Choose Base Account (Auto Mode)", [acc[0] for acc in accounts])
    account = next(acc for acc in accounts if acc[0] == selected_account)
    username, password = account[1], account[2]

# Optional global proxy
proxy = st.text_input("Global Proxy (optional)", help="e.g., http://user:pass@host:port")

if platform_choice != "auto":
    if platform_choice == "quora":
        target_url = st.text_input("Quora question URL (optional)", help="Paste URL to answer; leave empty to post new question.")
    elif platform_choice == "reddit":
        subreddit = st.text_input("Subreddit (without r/)", help="Enter the subreddit to post in.")
        post_title = st.text_input("Post Title", help="Enter a title for the Reddit post.")
    elif platform_choice == "tripadvisor":
        target_url = st.text_input("TripAdvisor thread URL", help="Enter the URL of the forum thread.")
    content = st.text_area("Content to post", height=150)
else:
    root_keyword = st.text_input("Root Keyword(s)", "real estate tokyo", help="Keywords for thread search.")
    max_results = st.number_input("Max Results per Search", min_value=1, max_value=20, value=3)
    delay_between = st.number_input("Delay between threads (seconds)", min_value=5, max_value=60, value=10)

# ChatGPT integration for content generation
use_chatgpt = st.checkbox("Generate answer with ChatGPT", value=True)
if use_chatgpt:
    openai.api_key = st.secrets["openai"]["api_key"]
    prompt_for_analysis = st.text_area("Additional instructions (optional)", "Provide a concise, clear answer.", height=80)

# Posting triggers
if platform_choice != "auto":
    if st.button("Post Content Manually"):
        st.info(f"Posting manually on {platform_choice}...")
        try:
            if platform_choice == "quora":
                res = quora_login_and_post(username, password, content, question_url=target_url, proxy=proxy)
                thread_url = target_url if target_url else "New Question"
            elif platform_choice == "reddit":
                res = reddit_login_and_post(username, password, content, subreddit, post_title, proxy=proxy)
                thread_url = f"r/{subreddit}"
            elif platform_choice == "tripadvisor":
                res = tripadvisor_login_and_post(username, password, content, thread_url=target_url, proxy=proxy)
                thread_url = target_url
            # Log action
            st.session_state.log_records.append({
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Platform": platform_choice,
                "Thread URL": thread_url,
                "Status": "Success" if res else "Failed"
            })
            st.success("Content posted successfully!")
        except Exception as e:
            st.error(f"Error: {e}")
else:
    if st.button("Run Auto Process"):
        st.info("Starting auto process: Searching for threads and generating responses...")
        query = f'site:quora.com "{root_keyword}"'
        try:
            from automation_utils import search_google
            thread_urls = search_google(query, max_results)
        except Exception as e:
            st.error(f"Search error: {e}")
            thread_urls = []
        if not thread_urls:
            st.error("No threads found. Try different keywords.")
        else:
            st.success(f"Found {len(thread_urls)} threads. Processing...")
            for url in thread_urls:
                st.write(f"Processing thread: {url}")
                try:
                    from automation_utils import extract_thread_content
                    question_text = extract_thread_content(url)
                    if not question_text:
                        st.write("Could not extract question text; skipping.")
                        continue
                    generated_answer = generate_ai_response(question_text, prompt_for_analysis, use_chatgpt=use_chatgpt)
                    st.write("Generated Answer:", generated_answer)
                    from automation_utils import choose_money_site
                    site_name, site_details, complexity = choose_money_site(question_text)
                    st.write(f"Smart funnel selected: {site_name} (complexity: {complexity})")
                    res = quora_login_and_post(username, password, generated_answer, question_url=url, proxy=proxy)
                    st.session_state.log_records.append({
                        "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Platform": "auto/quora",
                        "Thread URL": url,
                        "Status": "Success" if res else "Failed"
                    })
                    st.write(f"Posted on thread: {url}")
                    time.sleep(delay_between)
                except Exception as e:
                    st.error(f"Error processing {url}: {e}")
            st.success("Auto process completed. Please verify the posts on their respective platforms.")

# Display log report
st.header("Log Report")
if st.session_state.log_records:
    st.table(st.session_state.log_records)
else:
    st.write("No log records yet.")
