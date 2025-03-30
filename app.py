import os
import sys
import time
import random
import json
import logging
import importlib.util
import re
import openai
import streamlit as st
from packaging.version import Version as PackagingVersion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ai_commenter.log")
    ]
)
logger = logging.getLogger(__name__)

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
    
    def __lt__(self, other):
        if isinstance(other, MyLooseVersion):
            if self.parsed and other.parsed:
                return self.parsed < other.parsed
        return str(self) < str(other)

def patch_undetected_in_memory():
    """
    In-memory patch: override undetected_chromedriver.patcher.LooseVersion
    with our custom MyLooseVersion.
    """
    try:
        import undetected_chromedriver.patcher as patcher
        patcher.LooseVersion = MyLooseVersion
        logger.info("Patched undetected_chromedriver.patcher in memory with MyLooseVersion.")
    except Exception as e:
        logger.error(f"Error patching undetected_chromedriver in memory: {e}")

# Apply patches
patch_undetected_in_memory()

# --- Import the automation modules ---
try:
    from quora_automation import quora_login_and_post
    from reddit_automation import reddit_login_and_post
    from tripadvisor_automation import tripadvisor_login_and_post
    from automation_utils import (
        search_google,
        extract_thread_content,
        choose_money_site,
        generate_ai_response,
        solve_captcha_if_present,
        get_next_tor_identity,
        test_proxy_connection
    )
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# --- Configure OpenAI API Key from Environment Variables or Streamlit Secrets ---
if "openai" in st.secrets:
    openai.api_key = st.secrets["openai"]["api_key"]
else:
    openai.api_key = os.environ.get("OPENAI_API_KEY", "")

if not openai.api_key:
    logger.warning("No OpenAI API key found! AI responses won't work.")

#############################################
# Streamlit UI Setup
#############################################
st.set_page_config(page_title="AI Commenter for Forums", layout="wide")
st.title("AI Multi-Platform Commenter")
st.markdown(
    """
    This tool automates the process of finding and commenting on relevant threads across Quora, Reddit, and TripAdvisor. 
    It uses AI to generate helpful, natural responses that include subtle references to your websites.
    
    **Features:**
    - Advanced bot detection avoidance
    - IP rotation with Tor integration
    - Human-like typing and behavior patterns
    - Automatic CAPTCHA solving
    - Smart website referencing
    """
)

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Configuration", "Content Strategy", "Automation", "Logs"])

with tab1:
    st.header("System Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        display_mode = st.radio("Browser Mode", options=["Headless", "Headful"], index=0,
                                help="Headless mode runs invisibly, while Headful shows the browser for debugging")
        os.environ["CHROME_HEADLESS"] = "true" if display_mode == "Headless" else "false"
        
        use_tor = st.checkbox("Use Tor for IP rotation", value=True, 
                              help="Rotate your IP address between requests using Tor network")
        
        if use_tor:
            # Test Tor connection if enabled
            if st.button("Test Tor Connection"):
                with st.spinner("Testing Tor connection..."):
                    current_ip = test_proxy_connection("socks5://127.0.0.1:9050")
                    if current_ip:
                        st.success(f"Tor connected successfully! Current IP: {current_ip}")
                    else:
                        st.error("Tor connection failed. Please check if Tor service is running.")
    
    with col2:
        proxy = st.text_input("Custom Proxy (optional)", 
                              help="e.g., http://user:pass@host:port (overrides Tor if both are enabled)")
        
        captcha_api_key = st.text_input("2Captcha API Key", 
                                      value=os.environ.get("CAPTCHA_API_KEY", ""), 
                                      type="password",
                                      help="API key for automatic CAPTCHA solving (highly recommended)")
        if captcha_api_key:
            os.environ["CAPTCHA_API_KEY"] = captcha_api_key
        
        use_residential_proxies = st.checkbox("Use Residential Proxies", value=False,
                                            help="Enable if you have access to a residential proxy service (higher success rate)")
        if use_residential_proxies:
            st.info("When using residential proxies, add them in the 'Custom Proxy' field above.")

    # Initialize session state
    if "log_records" not in st.session_state:
        st.session_state.log_records = []
        
    if "queue" not in st.session_state:
        st.session_state.queue = []
        
    if "websites" not in st.session_state:
        st.session_state.websites = []

    #############################################
    # Account Credentials Input
    #############################################
    st.header("Account Configuration")
    
    platforms = ["quora", "reddit", "tripadvisor"]
    account_expanders = {}
    platform_credentials = {}
    
    for platform in platforms:
        account_expanders[platform] = st.expander(f"{platform.capitalize()} Accounts")
        
        with account_expanders[platform]:
            num_accounts = st.number_input(f"Number of {platform.capitalize()} Accounts", 
                                         min_value=1, max_value=10, value=1, key=f"num_{platform}")
            
            accounts = []
            for i in range(int(num_accounts)):
                cols = st.columns(2)
                with cols[0]:
                site_name = st.text_input(f"Website {i+1} Name", value=f"Site {i+1}", key=f"site_name_{i}")
            with cols[1]:
                site_url = st.text_input(f"Website {i+1} URL", value=f"https://example{i+1}.com", key=f"site_url_{i}")
            with cols[2]:
                site_desc = st.text_input(f"Website {i+1} Description", value="Your site description", key=f"site_desc_{i}")
            
            if site_name and site_url and site_desc:
                websites.append({
                    "name": site_name,
                    "url": site_url,
                    "description": site_desc,
                    "keywords": [word.lower() for word in site_name.split() + site_desc.lower().split() if len(word) > 3]
                })
        
        st.session_state.websites = websites
        
        st.subheader("Response Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            response_tone = st.select_slider(
                "Response Tone",
                options=["Professional", "Conversational", "Helpful", "Enthusiastic", "Expert"],
                value="Helpful"
            )
        
        with col2:
            response_length = st.select_slider(
                "Response Length",
                options=["Very Short", "Short", "Medium", "Long", "Very Long"],
                value="Medium"
            )
        
        # Map response length to token counts
        token_map = {
            "Very Short": 100,
            "Short": 150, 
            "Medium": 250,
            "Long": 350,
            "Very Long": 500
        }
        max_tokens = token_map[response_length]
        
        # Instructions for the AI based on selected tone
        tone_instructions = {
            "Professional": "Write in a formal, authoritative tone with precise language.",
            "Conversational": "Write in a casual, friendly tone like you're talking to a friend.",
            "Helpful": "Focus on being supportive and providing valuable information.",
            "Enthusiastic": "Show excitement and passion about the topic.",
            "Expert": "Demonstrate deep knowledge with specific terminology and insights."
        }
        
        response_instructions = st.text_area(
            "AI Response Instructions",
            value=f"""Provide a {response_tone.lower()}, informative response that directly addresses the question.
{tone_instructions[response_tone]}
Include a subtle, natural reference to ONE of our websites near the end of your response.
Make the reference helpful and contextually relevant, not promotional.
Keep your response brief and focused.""",
            height=150
        )
        
        reference_style = st.radio(
            "Website Reference Style",
            options=["Natural mention", "Helpful resource", "Personal experience", "Statistical reference"],
            help="How to integrate your website reference into the response"
        )
        
        reference_examples = {
            "Natural mention": "I've found some great information about this on [website].",
            "Helpful resource": "If you want more details, [website] has a comprehensive guide on this topic.",
            "Personal experience": "I had a similar situation and the advice from [website] really helped me.",
            "Statistical reference": "According to research from [website], about 75% of people in this situation..."
        }
        
        st.info(f"Example reference style: {reference_examples[reference_style]}")

with tab3:
    st.header("Automation Settings")
    
    auto_sites = st.multiselect(
        "Select platforms to post on",
        options=platforms,
        default=platforms,
        help="Select all platforms you want to search and post to"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        root_keyword = st.text_input("Root Keyword(s)", "property investment thailand", 
                                     help="Enter the search keyword(s)")
    with col2:
        time_between_platforms = st.number_input("Minutes between platforms", 
                                               min_value=5, max_value=120, value=15,
                                               help="Time to wait between posting on different platforms")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        max_results = st.number_input("Max Results per Platform", 
                                    min_value=1, max_value=20, value=3,
                                    help="Maximum number of threads to process on each platform")
    with col2:
        delay_between = st.number_input("Delay between threads (seconds)", 
                                      min_value=30, max_value=300, value=60,
                                      help="Time to wait between processing different threads")
    with col3:
        max_daily_posts = st.number_input("Max Daily Posts", 
                                       min_value=1, max_value=100, value=10,
                                       help="Maximum number of posts to make per day")
    
    avoid_detection_options = st.expander("Advanced Anti-Detection Settings")
    with avoid_detection_options:
        col1, col2 = st.columns(2)
        with col1:
            random_delays = st.checkbox("Use random delays between actions", value=True, 
                                       help="Add unpredictable timing between actions to appear more human-like")
            
            human_typing = st.checkbox("Simulate human typing patterns", value=True,
                                     help="Type characters at variable speeds with occasional pauses")
            
            rotate_user_agents = st.checkbox("Rotate user agent strings", value=True,
                                          help="Use different browser identifiers for each session")
        
        with col2:
            scrolling_behavior = st.checkbox("Add realistic scrolling behavior", value=True,
                                          help="Scroll through content before interacting with elements")
            
            mouse_movement = st.checkbox("Simulate mouse movements", value=True,
                                      help="Move mouse pointer in natural patterns before clicking")
            
            stealth_mode = st.checkbox("Use stealth mode browser settings", value=True,
                                     help="Apply advanced browser settings to avoid detection")
        
        detection_level = st.slider("Anti-Detection Thoroughness", min_value=1, max_value=5, value=3,
                                  help="Higher levels apply more anti-detection techniques but may slow down the process")
        
        if detection_level >= 4:
            st.warning("High anti-detection levels may significantly reduce automation speed.")
    
    queue_col, status_col = st.columns(2)
    with queue_col:
        if st.button("Search for Threads", use_container_width=True):
            if not st.session_state.websites:
                st.error("Please add at least one website in the Content Strategy tab.")
            elif not auto_sites:
                st.error("Please select at least one platform to post on.")
            else:
                st.session_state.queue = []
                progress_bar = st.progress(0)
                
                for idx, site in enumerate(auto_sites):
                    if not platform_credentials.get(site) or not platform_credentials[site]:
                        st.error(f"No accounts configured for {site}. Please add account details.")
                        continue
                    
                    site_name = site.capitalize()
                    st.write(f"🔍 Searching for threads on {site_name}...")
                    
                    # Update progress
                    progress_bar.progress((idx / len(auto_sites)) * 0.5)
                        
                    try:
                        domain_map = {"quora": "quora.com", "reddit": "reddit.com", "tripadvisor": "tripadvisor.com"}
                        domain = domain_map[site]
                        query = f'site:{domain} "{root_keyword}"'
                        
                        thread_urls = search_google(query, max_results)
                        
                        if not thread_urls:
                            st.warning(f"No threads found on {site_name} for '{root_keyword}'")
                        else:
                            st.success(f"Found {len(thread_urls)} threads on {site_name}")
                            
                            # Add threads to the queue
                            for url in thread_urls:
                                st.session_state.queue.append({
                                    "platform": site,
                                    "url": url,
                                    "status": "pending",
                                    "timestamp": None,
                                    "content": None
                                })
                        
                    except Exception as e:
                        st.error(f"Error searching {site_name}: {str(e)}")
                    
                    # Update progress
                    progress_bar.progress(0.5 + (idx / len(auto_sites)) * 0.5)
                    
                progress_bar.progress(1.0)
                st.success(f"Added {len(st.session_state.queue)} threads to the queue")
    
    with status_col:
        # Display current queue status
        if st.session_state.queue:
            st.write(f"Queue Status: {len([i for i in st.session_state.queue if i['status'] == 'pending'])} pending, "
                    f"{len([i for i in st.session_state.queue if i['status'] == 'completed'])} completed, "
                    f"{len([i for i in st.session_state.queue if i['status'] == 'failed'])} failed")
            
            if st.button("Process Queue", use_container_width=True):
                if not st.session_state.websites:
                    st.error("Please add at least one website in the Content Strategy tab.")
                else:
                    progress_bar = st.progress(0)
                    pending_items = [i for i in st.session_state.queue if i["status"] == "pending"]
                    
                    for i, item in enumerate(pending_items):
                        # Update progress bar
                        progress_bar.progress(i / len(pending_items))
                        
                        platform = item["platform"]
                        url = item["url"]
                        
                        if not platform_credentials.get(platform) or not platform_credentials[platform]:
                            st.error(f"No account available for {platform}. Skipping {url}.")
                            item["status"] = "failed"
                            continue
                        
                        # Select a random account for this platform
                        account = random.choice(platform_credentials[platform])
                        username, password = account["username"], account["password"]
                        
                        st.write(f"Processing {platform} thread: {url}")
                        
                        try:
                            # Extract thread content
                            question_text = extract_thread_content(url)
                            if not question_text or len(question_text) < 10:
                                st.write("❌ Could not extract thread content")
                                item["status"] = "failed"
                                continue
                            
                            st.write(f"📝 Extracted content: {question_text[:100]}...")
                            
                            # Generate AI response
                            if use_chatgpt:
                                # Choose a random website to reference based on relevance
                                site_name, site_details, complexity = choose_money_site(question_text, st.session_state.websites)
                                
                                # Prepare the prompt for AI
                                site_reference = f"You can reference this site in your answer if relevant: {site_details['name']} - {site_details['url']} - {site_details['description']}"
                                
                                reference_example = reference_examples[reference_style].replace("[website]", site_details["name"])
                                
                                full_prompt = f"""
                                {response_instructions}
                                
                                Website to reference: {site_details['name']} ({site_details['url']})
                                Website description: {site_details['description']}
                                Reference style example: {reference_example}
                                
                                Question/Topic: {question_text}
                                """
                                
                                final_answer = generate_ai_response(
                                    question_text=full_prompt,
                                    additional_prompt="",
                                    use_chatgpt=True,
                                    model=ai_model,
                                    max_tokens=max_tokens
                                )
                                
                                st.write(f"🤖 Generated response: {final_answer[:100]}...")
                                
                            else:
                                # Manual response template with website reference
                                site = random.choice(st.session_state.websites)
                                final_answer = f"This is a helpful response to: {question_text[:50]}... For more information, check out {site['name']} at {site['url']}."
                                st.write(f"📄 Using template response")
                            
                            # Store the generated content
                            item["content"] = final_answer
                            
                            # Use Tor for IP rotation if enabled
                            current_proxy = proxy
                            if use_tor and not proxy:
                                # Rotate Tor identity between platforms
                                get_next_tor_identity()
                                current_proxy = "socks5://127.0.0.1:9050"
                                st.write("🔄 Rotated Tor identity for new IP address")
                            
                            # Post the content
                            if platform == "quora":
                                st.write("🔹 Posting to Quora...")
                                res = quora_login_and_post(username, password, final_answer, question_url=url, proxy=current_proxy)
                            elif platform == "reddit":
                                st.write("🔹 Posting to Reddit...")
                                # Extract post ID from URL for Reddit
                                post_id = url.split("/")[-2] if "/comments/" in url else None
                                if post_id:
                                    res = reddit_login_and_post(username, password, final_answer, comment_mode=True, post_id=post_id, proxy=current_proxy)
                                else:
                                    st.write("❌ Could not extract post ID from Reddit URL")
                                    res = False
                            else:  # tripadvisor
                                st.write("🔹 Posting to TripAdvisor...")
                                res = tripadvisor_login_and_post(username, password, final_answer, thread_url=url, proxy=current_proxy)
                            
                            if res:
                                st.write(f"✅ Successfully posted to {platform}")
                                item["status"] = "completed"
                                item["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Add to log records
                                st.session_state.log_records.append({
                                    "Timestamp": item["timestamp"],
                                    "Platform": platform,
                                    "Thread URL": url,
                                    "Status": "Success",
                                    "Content": final_answer[:100] + "..."
                                })
                            else:
                                st.write(f"❌ Failed to post to {platform}")
                                item["status"] = "failed"
                                
                                # Add to log records
                                st.session_state.log_records.append({
                                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "Platform": platform,
                                    "Thread URL": url,
                                    "Status": "Failed",
                                    "Content": final_answer[:100] + "..." if final_answer else "N/A"
                                })
                            
                            # Delay between threads
                            if i < len(pending_items) - 1:
                                st.write(f"⏱️ Waiting {delay_between} seconds before next thread...")
                                time.sleep(delay_between)
                                
                        except Exception as e:
                            st.error(f"Error processing {url}: {str(e)}")
                            item["status"] = "failed"
                            
                            # Add to log records
                            st.session_state.log_records.append({
                                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "Platform": platform,
                                "Thread URL": url,
                                "Status": f"Error: {str(e)}",
                                "Content": "N/A"
                            })
                    
                    progress_bar.progress(1.0)
                    st.success("Queue processing completed")
        else:
            st.info("Queue is empty. Search for threads first.")

with tab4:
    st.header("Activity Logs")
    
    # Display queue status
    if st.session_state.queue:
        st.subheader("Current Queue")
        queue_df = []
        for item in st.session_state.queue:
            queue_df.append({
                "Platform": item["platform"].capitalize(),
                "URL": item["url"],
                "Status": item["status"].capitalize(),
                "Timestamp": item["timestamp"] or "N/A"
            })
        st.table(queue_df)
    
    # Display log records
    if st.session_state.log_records:
        st.subheader("Activity History")
        st.table(st.session_state.log_records)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export Logs (JSON)", use_container_width=True):
                log_json = json.dumps(st.session_state.log_records, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=log_json,
                    file_name="ai_commenter_logs.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("Export Logs (CSV)", use_container_width=True):
                import pandas as pd
                import io
                
                df = pd.DataFrame(st.session_state.log_records)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="ai_commenter_logs.csv",
                    mime="text/csv"
                )
    else:
        st.info("No activity logs yet.")

# --- Run Streamlit with the proper port ---
if __name__ == '__main__':
    # Get the port from the environment variable, default to 10000 if not set
    port = os.environ.get("PORT", 10000)
    try:
        # Import the Streamlit CLI module and run the app with the specified port
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", "main.py", "--server.port", str(port)]
        sys.exit(stcli.main())
    except Exception as e:
        logger.error(f"Error starting Streamlit: {e}")

                    username = st.text_input(f"{platform.capitalize()} Username {i+1}", 
                                           key=f"{platform}_user_{i}",
                                           type="default")
                with cols[1]:
                    password = st.text_input(f"{platform.capitalize()} Password {i+1}", 
                                           key=f"{platform}_pass_{i}",
                                           type="password")
                
                if username and password:
                    accounts.append({
                        "username": username,
                        "password": password
                    })
            
            platform_credentials[platform] = accounts
            
            st.info(f"Added {len(accounts)} {platform.capitalize()} accounts.")

with tab2:
    st.header("Content Strategy")
    
    use_chatgpt = st.checkbox("Generate responses with ChatGPT", value=True)
    
    if use_chatgpt:
        ai_model = st.selectbox(
            "AI Model",
            ["gpt-3.5-turbo", "gpt-4"],
            index=0,
            help="GPT-4 provides higher quality responses but costs more"
        )
        
        st.subheader("Your Websites")
        
        # Allow user to add their websites
        col1, col2 = st.columns(2)
        with col1:
            num_sites = st.number_input("Number of websites", min_value=1, max_value=10, value=3)
        
        websites = []
        for i in range(int(num_sites)):
            cols = st.columns(3)
            with cols[0]:
