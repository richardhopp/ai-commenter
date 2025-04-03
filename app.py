import os
import streamlit as st
import time
import logging
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional, Tuple, Union
from search_respond_ui import render_search_and_respond_page

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Social Media Content Automation",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Try importing required modules
try:
    import openai
    from dotenv import load_dotenv
    
    # Import automation modules
    try:
        from quora_automation import quora_login_and_post
        from reddit_automation import reddit_login_and_post
        from tripadvisor_automation import tripadvisor_login_and_post
        AUTOMATION_AVAILABLE = True
        logger.info("Automation modules loaded successfully")
    except ImportError as e:
        logger.error(f"Failed to import automation modules: {str(e)}")
        AUTOMATION_AVAILABLE = False
        
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    st.error(f"Failed to import required modules: {str(e)}")

# Load environment variables
load_dotenv()

# Define styles
COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#4ECDC4",
    "accent": "#FFE66D",
    "success": "#6BFF8A",
    "error": "#FF6B6B",
    "warning": "#FFD166",
    "info": "#6BBCFF"
}

# Define platform-specific constants
PLATFORM_INFO = {
    "Quora": {
        "icon": "❓",
        "color": "#AA2200",
        "content_type": "question",
        "min_length": 10,
        "max_length": 300
    },
    "Reddit": {
        "icon": "🔍",
        "color": "#FF4500",
        "content_type": "post",
        "min_length": 20,
        "max_length": 40000
    },
    "TripAdvisor": {
        "icon": "🏨",
        "color": "#00AF87",
        "content_type": "review",
        "min_length": 100,
        "max_length": 2000
    }
}

# Use environment variables instead of st.secrets
# API Keys
openai_api_key = os.environ.get("OPENAI_API_KEY")
captcha_api_key = os.environ.get("CAPTCHA_API_KEY")

# Configure OpenAI
if openai_api_key:
    openai.api_key = openai_api_key
    logger.info("OpenAI API key configured successfully")
else:
    logger.warning("OpenAI API key not found in environment variables")

# Platform credentials
platform_credentials = {
    "quora": {
        "username": os.environ.get("QUORA_USER1"),
        "password": os.environ.get("QUORA_PASS1")
    },
    "reddit": {
        "username": os.environ.get("REDDIT_USER1"),
        "password": os.environ.get("REDDIT_PASS1")
    },
    "tripadvisor": {
        "username": os.environ.get("TRIPADVISOR_USER1"),
        "password": os.environ.get("TRIPADVISOR_PASS1")
    }
}

# Check if credentials are properly configured
for platform, creds in platform_credentials.items():
    if creds["username"] and creds["password"]:
        logger.info(f"{platform.capitalize()} credentials configured")
    else:
        logger.warning(f"{platform.capitalize()} credentials not fully configured")

# Utility Functions
def generate_content(topic: str, content_type: str, platform: str, tone: str, length: str = "medium") -> Tuple[Optional[str], Optional[str]]:
    """
    Generate content using OpenAI based on parameters.
    
    Args:
        topic: Main topic or keyword for the content
        content_type: Type of content (Question, Blog Post, etc.)
        platform: Target platform (Quora, Reddit, TripAdvisor)
        tone: Tone of the content (Professional, Casual, etc.)
        length: Length of content (short, medium, long)
        
    Returns:
        Tuple of (generated_content, error_message)
    """
    if not openai_api_key:
        return None, "OpenAI API key is required for content generation."
    
    try:
        # Determine word count range based on length
        length_words = {
            "short": "50-100",
            "medium": "100-200",
            "long": "200-400"
        }.get(length.lower(), "100-200")
        
        # Create system prompt based on platform and content type
        system_prompt = f"You are an expert content creator specialized in creating engaging {content_type.lower()}s for {platform}."
        
        # Create user prompt with specifics
        user_prompt = f"""
        Create a {tone.lower()} {content_type.lower()} about {topic} for {platform}.
        
        The content should be:
        - Engaging and natural-sounding
        - Appropriate for the platform
        - Between {length_words} words
        - Free of promotional language
        
        For Quora: Make sure it's in question format and ends with a question mark.
        For Reddit: Make it conversational and suited for the platform's community.
        For TripAdvisor: Focus on descriptive experience sharing.
        """
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        
        # Extract and return generated content
        generated_content = response.choices[0].message["content"].strip()
        return generated_content, None
    
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        return None, f"Error generating content: {str(e)}"

def generate_hashtags(topic: str, platform: str, count: int = 5) -> Tuple[List[str], Optional[str]]:
    """
    Generate relevant hashtags for a topic and platform.
    
    Args:
        topic: The main topic or keyword
        platform: Target platform
        count: Number of hashtags to generate
        
    Returns:
        Tuple of (hashtags_list, error_message)
    """
    if not openai_api_key:
        return [], "OpenAI API key is required for hashtag generation."
    
    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a social media expert who creates effective hashtags."},
                {"role": "user", "content": f"Generate {count} relevant hashtags for a post about '{topic}' on {platform}. Return only the hashtags in a comma-separated format without any explanation or commentary."}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        # Process and format the hashtags
        hashtag_text = response.choices[0].message["content"].strip()
        hashtags = [tag.strip().replace("#", "") for tag in hashtag_text.split(",")]
        hashtags = [f"#{tag}" if not tag.startswith("#") else tag for tag in hashtags]
        
        return hashtags, None
    
    except Exception as e:
        logger.error(f"Error generating hashtags: {str(e)}")
        return [], f"Error generating hashtags: {str(e)}"

def analyze_engagement_potential(content: str, platform: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Analyze the engagement potential of content.
    
    Args:
        content: The content to analyze
        platform: Target platform
        
    Returns:
        Tuple of (analysis_data, error_message)
    """
    if not openai_api_key:
        return None, "OpenAI API key is required for engagement analysis."
    
    try:
        # Call OpenAI API for analysis
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert social media analyst who evaluates content engagement potential."
                },
                {
                    "role": "user", 
                    "content": f"""
                    Analyze this content for {platform} and provide:
                    
                    1. Engagement score (0-100)
                    2. Brief explanation of strengths
                    3. Brief explanation of weaknesses
                    4. Suggestions for improvement
                    
                    Format your response as a JSON object with the following keys:
                    "score", "strengths", "weaknesses", "suggestions"
                    
                    Content to analyze:
                    
                    {content}
                    """
                }
            ],
            max_tokens=500,
            temperature=0.5
        )
        
        # Parse and extract the JSON response
        analysis_text = response.choices[0].message["content"].strip()
        
        try:
            import re
            json_match = re.search(r'({.*})', analysis_text, re.DOTALL)
            if json_match:
                analysis_json = json.loads(json_match.group(1))
            else:
                # Fallback if not in JSON format
                analysis_json = {
                    "score": 70,
                    "strengths": "Content seems well-formulated.",
                    "weaknesses": "Unable to extract detailed analysis.",
                    "suggestions": "Consider making the content more engaging and platform-specific."
                }
            return analysis_json, None
        
        except Exception as json_error:
            logger.error(f"Error parsing analysis JSON: {str(json_error)}")
            return {
                "score": 65,
                "strengths": "Content appears to be well-structured.",
                "weaknesses": "Could not perform detailed analysis.",
                "suggestions": "Consider reviewing for platform-specific optimization."
            }, None
    
    except Exception as e:
        logger.error(f"Error analyzing engagement potential: {str(e)}")
        return None, f"Error analyzing engagement potential: {str(e)}"

def schedule_post(platform: str, content: str, schedule_time: datetime, 
                  platform_data: Dict[str, Any] = None) -> str:
    """
    Schedule a post for future publication.
    
    Args:
        platform: Target platform
        content: Content to post
        schedule_time: When to publish
        platform_data: Additional platform-specific data
        
    Returns:
        Post ID for reference
    """
    # Initialize scheduled posts in session state if not exists
    if "scheduled_posts" not in st.session_state:
        st.session_state.scheduled_posts = []
    
    # Generate unique post ID
    post_id = f"post_{len(st.session_state.scheduled_posts) + 1}_{int(time.time())}"
    
    # Add to scheduled posts
    st.session_state.scheduled_posts.append({
        "id": post_id,
        "platform": platform,
        "content": content,
        "scheduled_time": schedule_time,
        "platform_data": platform_data or {},
        "status": "scheduled"
    })
    
    logger.info(f"Scheduled post {post_id} for {schedule_time.strftime('%Y-%m-%d %H:%M')}")
    return post_id

def simulate_post_metrics(days: int = 30) -> Dict[str, pd.DataFrame]:
    """
    Simulate metrics for posts to demonstrate analytics functionality.
    
    Args:
        days: Number of days of data to generate
        
    Returns:
        Dictionary of DataFrames with metrics by platform
    """
    # Generate dates
    dates = [datetime.now() - timedelta(days=i) for i in range(days)]
    dates.reverse()
    
    # Simulate engagement patterns for each platform
    metrics = {
        "Quora": {
            "views": [int(100 * (1 + 0.5 * np.sin(i/5) + 0.2 * random.random())) for i in range(days)],
            "upvotes": [int(20 * (1 + 0.5 * np.sin(i/5) + 0.3 * random.random())) for i in range(days)],
            "comments": [int(5 * (1 + 0.3 * np.sin(i/5) + 0.5 * random.random())) for i in range(days)]
        },
        "Reddit": {
            "views": [int(200 * (1 + 0.3 * np.sin(i/7) + 0.4 * random.random())) for i in range(days)],
            "upvotes": [int(50 * (1 + 0.4 * np.sin(i/7) + 0.3 * random.random())) for i in range(days)],
            "comments": [int(15 * (1 + 0.6 * np.sin(i/7) + 0.2 * random.random())) for i in range(days)]
        },
        "TripAdvisor": {
            "views": [int(80 * (1 + 0.2 * np.sin(i/6) + 0.3 * random.random())) for i in range(days)],
            "upvotes": [int(10 * (1 + 0.3 * np.sin(i/6) + 0.4 * random.random())) for i in range(days)],
            "comments": [int(3 * (1 + 0.2 * np.sin(i/6) + 0.6 * random.random())) for i in range(days)]
        }
    }
    
    # Create dataframes for each platform
    platform_dfs = {}
    for platform, platform_metrics in metrics.items():
        data = {"date": dates}
        data.update(platform_metrics)
        platform_dfs[platform] = pd.DataFrame(data)
    
    return platform_dfs

# Sidebar Navigation
def render_sidebar():
    """Render the navigation sidebar"""
    with st.sidebar:
        st.title("Content Automation")
        
        page = st.radio(
            "Navigation",
            ["Dashboard", "Content Creation", "Platform Posting", "Scheduling", "Analytics", "Search & Respond", "Settings"]
        )
        
        st.markdown("---")
        
        # Quick status indicators
        st.markdown("### System Status")
        
        openai_status = "✅ Connected" if openai_api_key else "❌ Not Connected"
        captcha_status = "✅ Connected" if captcha_api_key else "❌ Not Connected"
        automation_status = "✅ Available" if AUTOMATION_AVAILABLE else "❌ Not Available"
        
        st.markdown(f"OpenAI API: {openai_status}")
        st.markdown(f"CAPTCHA API: {captcha_status}")
        st.markdown(f"Automation: {automation_status}")
        
        # Platform status
        st.markdown("### Platform Status")
        
        for platform, creds in platform_credentials.items():
            platform_status = "✅ Ready" if creds["username"] and creds["password"] else "❌ Not Configured"
            st.markdown(f"{platform.capitalize()}: {platform_status}")
        
        st.markdown("---")
        st.markdown("© 2025 Content Automation Dashboard")
        
    return page

# Page Components
def render_dashboard():
    """Render the dashboard page"""
    st.title("Content Automation Dashboard")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        content_count = len(st.session_state.get("generated_contents", []))
        st.metric(label="Contents Generated", value=content_count)
    
    with col2:
        posts_count = len(st.session_state.get("post_logs", []))
        st.metric(label="Posts Published", value=posts_count)
    
    with col3:
        scheduled_count = len([p for p in st.session_state.get("scheduled_posts", []) if p["status"] == "scheduled"])
        st.metric(label="Scheduled Posts", value=scheduled_count)
    
    with col4:
        platforms_used = set([p["platform"] for p in st.session_state.get("post_logs", [])])
        platforms_count = len(platforms_used) if platforms_used else 0
        st.metric(label="Platforms Used", value=platforms_count)
    
    # Recent activity
    st.markdown("## Recent Activity")
    
    tab1, tab2 = st.tabs(["Recent Posts", "Recent Content"])
    
    with tab1:
        if "post_logs" in st.session_state and st.session_state.post_logs:
            for i, log in enumerate(list(reversed(st.session_state.post_logs))[:5]):
                status = "✅ Success" if log['success'] else f"❌ Failed: {log.get('error', 'Unknown error')}"
                with st.expander(f"{log['timestamp']} - {log['platform']} - {status}"):
                    st.write(f"Content snippet: {log['content']}")
                    if log['success'] and log.get('url'):
                        st.markdown(f"[View post]({log['url']})")
        else:
            st.info("No posting activity yet.")
    
    with tab2:
        if "generated_contents" in st.session_state and st.session_state.generated_contents:
            for i, log in enumerate(list(reversed(st.session_state.generated_contents))[:5]):
                with st.expander(f"{log['timestamp']} - {log['topic']} ({log['type']} for {log['platform']})"):
                    st.text_area(f"Content {i+1}", log['content'], height=100, disabled=True)
        else:
            st.info("No content generation logs yet.")
    
    # Engagement metrics
    st.markdown("## Engagement Metrics")
    
    # Simulate metrics for demonstration
    metric_dfs = simulate_post_metrics(30)
    
    # Create engagement plot
    fig = go.Figure()
    
    colors = {
        "Quora": "#aa2200",
        "Reddit": "#ff4500",
        "TripAdvisor": "#00af87"
    }
    
    for platform, df in metric_dfs.items():
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["views"],
            mode='lines',
            name=f"{platform} Views",
            line=dict(color=colors[platform]),
            hovertemplate='%{y} views<extra></extra>'
        ))
    
    fig.update_layout(
        title="Platform Engagement Over Time",
        xaxis_title="Date",
        yaxis_title="Views",
        hovermode="x unified",
        legend_title="Platform",
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Platform specific metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Quora Performance")
        quora_df = metric_dfs["Quora"]
        
        # Calculate averages
        avg_views = int(quora_df["views"].mean())
        avg_upvotes = int(quora_df["upvotes"].mean())
        avg_comments = int(quora_df["comments"].mean())
        
        st.metric("Avg. Views", avg_views)
        st.metric("Avg. Upvotes", avg_upvotes)
        st.metric("Avg. Comments", avg_comments)
    
    with col2:
        st.markdown("### Reddit Performance")
        reddit_df = metric_dfs["Reddit"]
        
        # Calculate averages
        avg_views = int(reddit_df["views"].mean())
        avg_upvotes = int(reddit_df["upvotes"].mean())
        avg_comments = int(reddit_df["comments"].mean())
        
        st.metric("Avg. Views", avg_views)
        st.metric("Avg. Upvotes", avg_upvotes)
        st.metric("Avg. Comments", avg_comments)
    
    with col3:
        st.markdown("### TripAdvisor Performance")
        tripadvisor_df = metric_dfs["TripAdvisor"]
        
        # Calculate averages
        avg_views = int(tripadvisor_df["views"].mean())
        avg_upvotes = int(tripadvisor_df["upvotes"].mean())
        avg_comments = int(tripadvisor_df["comments"].mean())
        
        st.metric("Avg. Views", avg_views)
        st.metric("Avg. Upvotes", avg_upvotes)
        st.metric("Avg. Comments", avg_comments)

def render_content_creation():
    """Render the content creation page"""
    st.title("Content Creation")
    
    # Content generation form
    with st.form("content_generation_form"):
        topic = st.text_input("Topic or keyword")
        
        col1, col2 = st.columns(2)
        with col1:
            content_type = st.selectbox("Content type", ["Question", "Blog Post", "Review", "Social Media Post"])
        
        with col2:
            platform = st.selectbox("Target platform", ["Quora", "Reddit", "TripAdvisor", "Multiple"])
        
        col1, col2 = st.columns(2)
        with col1:
            tone = st.selectbox("Tone", ["Neutral", "Professional", "Casual", "Enthusiastic", "Critical"])
        
        with col2:
            length = st.selectbox("Length", ["Short", "Medium", "Long"])
        
        generate_button = st.form_submit_button("Generate Content")
    
    if generate_button and topic:
        if not openai_api_key:
            st.error("OpenAI API key is required for content generation.")
        else:
            with st.spinner("Generating content..."):
                generated_content, error = generate_content(topic, content_type, platform, tone, length.lower())
                
                if error:
                    st.error(error)
                else:
                    # Display the generated content
                    st.subheader("Generated Content")
                    st.write(generated_content)
                    
                    # Generate hashtags
                    with st.spinner("Generating related hashtags..."):
                        hashtags, hashtag_error = generate_hashtags(topic, platform)
                        
                        if not hashtag_error and hashtags:
                            st.markdown("### Suggested Hashtags")
                            st.write(" ".join(hashtags))
                    
                    # Analyze engagement potential
                    with st.spinner("Analyzing engagement potential..."):
                        analysis, analysis_error = analyze_engagement_potential(generated_content, platform)
                        
                        if not analysis_error and analysis:
                            st.markdown("### Engagement Analysis")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Create a gauge chart for the score
                                fig = go.Figure(go.Indicator(
                                    mode = "gauge+number",
                                    value = analysis["score"],
                                    domain = {'x': [0, 1], 'y': [0, 1]},
                                    title = {'text': "Engagement Score"},
                                    gauge = {
                                        'axis': {'range': [0, 100]},
                                        'bar': {'color': "darkblue"},
                                        'steps': [
                                            {'range': [0, 50], 'color': "lightgray"},
                                            {'range': [50, 75], 'color': "gray"},
                                            {'range': [75, 100], 'color': "darkgray"}
                                        ]
                                    }
                                ))
                                
                                fig.update_layout(height=300)
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with col2:
                                st.markdown("#### Analysis Details")
                                st.markdown(f"**Strengths:** {analysis['strengths']}")
                                st.markdown(f"**Weaknesses:** {analysis['weaknesses']}")
                                st.markdown(f"**Suggestions:** {analysis['suggestions']}")
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Post Now"):
                            st.session_state.content_to_post = generated_content
                            st.session_state.selected_platform = platform
                            st.session_state.selected_content_type = content_type
                            st.rerun()
                    
                    with col2:
                        if st.button("Schedule Post"):
                            st.session_state.content_to_schedule = generated_content
                            st.session_state.schedule_platform = platform
                            st.session_state.schedule_content_type = content_type
                            st.rerun()
                    
                    with col3:
                        if st.button("Save to Library"):
                            if "content_library" not in st.session_state:
                                st.session_state.content_library = []
                            
                            st.session_state.content_library.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "topic": topic,
                                "type": content_type,
                                "platform": platform,
                                "tone": tone,
                                "content": generated_content,
                                "hashtags": hashtags if 'hashtags' in locals() else []
                            })

def render_scheduling():
    """Render the scheduling page"""
    st.title("Post Scheduling")
    
    # Check if we came from content generation
    content_to_schedule = st.session_state.get("content_to_schedule", "")
    schedule_platform = st.session_state.get("schedule_platform", "Quora")
    
    # Create tabs for scheduling and viewing scheduled posts
    tab1, tab2 = st.tabs(["Schedule New Post", "View Scheduled Posts"])
    
    with tab1:
        if not content_to_schedule:
            # Content selection
            content_options = []
            
            # Add from generated content
            if "generated_contents" in st.session_state and st.session_state.generated_contents:
                content_options.extend([
                    f"{item['timestamp']} - {item['topic']} ({item['type']} for {item['platform']})"
                    for item in st.session_state.generated_contents
                ])
            
            # Add from content library
            if "content_library" in st.session_state and st.session_state.content_library:
                content_options.extend([
                    f"Library: {item['timestamp']} - {item['topic']} ({item['type']})"
                    for item in st.session_state.content_library
                ])
            
            content_options.append("Use custom content")
            
            if content_options:
                selected_content_option = st.selectbox("Select content to schedule", content_options)
                
                # Custom content input if selected
                if selected_content_option == "Use custom content":
                    content_to_schedule = st.text_area("Enter your content", height=200)
                    schedule_platform = st.selectbox("Select platform", ["Quora", "Reddit", "TripAdvisor"])
                else:
                    # Get the selected content from session state
                    if selected_content_option.startswith("Library:"):
                        # Extract from content library
                        library_index = content_options.index(selected_content_option) - len(st.session_state.get("generated_contents", []))
                        if library_index < len(st.session_state.content_library):
                            item = st.session_state.content_library[library_index]
                            content_to_schedule = item["content"]
                            schedule_platform = item["platform"]
                    else:
                        # Extract from generated contents
                        generated_index = content_options.index(selected_content_option)
                        if generated_index < len(st.session_state.generated_contents):
                            item = st.session_state.generated_contents[generated_index]
                            content_to_schedule = item["content"]
                            schedule_platform = item["platform"]
                    
                    st.text_area("Content to schedule", content_to_schedule, height=200, disabled=True)
                    st.info(f"Platform: {schedule_platform}")
            else:
                st.info("No content available for scheduling. Generate content first.")
                content_to_schedule = st.text_area("Or enter custom content", height=200)
                schedule_platform = st.selectbox("Select platform", ["Quora", "Reddit", "TripAdvisor"])
        else:
            st.text_area("Content to schedule", content_to_schedule, height=200, disabled=True)
            st.info(f"Platform: {schedule_platform}")
        
        # Platform-specific fields
        if schedule_platform == "Reddit" and content_to_schedule:
            # For Reddit, we need subreddit and title
            subreddit = st.text_input("Subreddit (without r/)")
            post_title = st.text_input("Post title")
        
        elif schedule_platform == "TripAdvisor" and content_to_schedule:
            # For TripAdvisor, we need location/hotel/restaurant
            location_name = st.text_input("Location/Hotel/Restaurant name")
            rating = st.slider("Rating (1-5)", 1, 5, 4)
        
        # Scheduling options
        if content_to_schedule:
            st.markdown("### Scheduling Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                schedule_date = st.date_input("Date", datetime.now() + timedelta(days=1))
            
            with col2:
                schedule_time = st.time_input("Time", datetime.now().time())
            
            schedule_datetime = datetime.combine(schedule_date, schedule_time)
            
            if schedule_datetime <= datetime.now():
                st.warning("Scheduled time must be in the future.")
            
            # Schedule button
            schedule_button = st.button("Schedule Post")
            
            if schedule_button:
                if schedule_datetime <= datetime.now():
                    st.error("Cannot schedule posts in the past. Please select a future date and time.")
                else:
                    # Additional data needed for specific platforms
                    platform_data = {}
                    
                    if schedule_platform == "Reddit":
                        if not subreddit or not post_title:
                            st.error("Subreddit and post title are required for Reddit posts.")
                        else:
                            platform_data = {
                                "subreddit": subreddit,
                                "title": post_title
                            }
                    
                    elif schedule_platform == "TripAdvisor":
                        if not location_name:
                            st.error("Location name is required for TripAdvisor reviews.")
                        else:
                            platform_data = {
                                "location_name": location_name,
                                "rating": rating
                            }
                    
                    if (schedule_platform == "Quora" or 
                        (schedule_platform == "Reddit" and subreddit and post_title) or
                        (schedule_platform == "TripAdvisor" and location_name)):
                        
                        # Schedule the post
                        post_id = schedule_post(schedule_platform, content_to_schedule, schedule_datetime, platform_data)
                        
                        st.success(f"Post scheduled for {schedule_datetime.strftime('%Y-%m-%d %H:%M')}!")
                        
                        # Clear the content_to_schedule if we came from content generation
                        if "content_to_schedule" in st.session_state:
                            del st.session_state.content_to_schedule
    
    with tab2:
        if "scheduled_posts" in st.session_state and st.session_state.scheduled_posts:
            st.markdown("### Scheduled Posts")
            
            # Create a table of scheduled posts
            scheduled_data = []
            for post in st.session_state.scheduled_posts:
                scheduled_data.append({
                    "ID": post["id"],
                    "Platform": post["platform"],
                    "Content Preview": post["content"][:50] + "..." if len(post["content"]) > 50 else post["content"],
                    "Scheduled Time": post["scheduled_time"].strftime("%Y-%m-%d %H:%M"),
                    "Status": post["status"].capitalize()
                })
            
            scheduled_df = pd.DataFrame(scheduled_data)
            st.dataframe(scheduled_df, use_container_width=True)
            
            # Allow editing or canceling scheduled posts
            st.markdown("### Manage Scheduled Posts")
            
            post_to_manage = st.selectbox(
                "Select a post to manage",
                options=[f"{post['id']} - {post['platform']} - {post['scheduled_time'].strftime('%Y-%m-%d %H:%M')}" 
                        for post in st.session_state.scheduled_posts]
            )
            
            if post_to_manage:
                post_id = post_to_manage.split(" - ")[0]
                
                # Find the post in session state
                selected_post = next((post for post in st.session_state.scheduled_posts if post["id"] == post_id), None)
                
                if selected_post:
                    st.text_area("Content", selected_post["content"], height=150, disabled=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Cancel Scheduled Post"):
                            # Remove the post from scheduled posts
                            st.session_state.scheduled_posts = [
                                post for post in st.session_state.scheduled_posts if post["id"] != post_id
                            ]
                            st.success("Scheduled post canceled!")
                            st.rerun()
                    
                    with col2:
                        if selected_post["status"] == "scheduled" and st.button("Post Now"):
                            # Change status to "posting"
                            for post in st.session_state.scheduled_posts:
                                if post["id"] == post_id:
                                    post["status"] = "posting"
                            
                            st.success("Post will be published immediately!")
                            st.rerun()
        else:
            st.info("No scheduled posts available.")

def render_analytics():
    """Render the analytics page"""
    st.title("Content Analytics")
    
    # Performance overview
    st.markdown("## Performance Overview")
    
    # Simulate metrics for demonstration
    metric_dfs = simulate_post_metrics(30)
    
    # Platform selection for detailed analysis
    platform_for_analysis = st.selectbox(
        "Select platform for detailed analysis",
        ["All Platforms", "Quora", "Reddit", "TripAdvisor"]
    )
    
    if platform_for_analysis == "All Platforms":
        # Combined engagement plot for all platforms
        fig = go.Figure()
        
        colors = {
            "Quora": "#aa2200",
            "Reddit": "#ff4500",
            "TripAdvisor": "#00af87"
        }
        
        for platform, df in metric_dfs.items():
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["views"],
                mode='lines',
                name=f"{platform} Views",
                line=dict(color=colors[platform]),
                hovertemplate='%{y} views<extra></extra>'
            ))
        
        fig.update_layout(
            title="Platform Engagement Over Time",
            xaxis_title="Date",
            yaxis_title="Views",
            hovermode="x unified",
            legend_title="Platform",
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary metrics for all platforms
        st.markdown("### Summary Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Posts", len(st.session_state.get("post_logs", [])))
        
        with col2:
            avg_views = sum([df["views"].mean() for df in metric_dfs.values()]) / len(metric_dfs)
            st.metric("Avg. Views Per Post", f"{int(avg_views)}")
        
        with col3:
            avg_engagement = sum([df["comments"].mean() / df["views"].mean() * 100 for df in metric_dfs.values()]) / len(metric_dfs)
            st.metric("Avg. Engagement Rate", f"{avg_engagement:.1f}%")
    else:
        # Detailed analysis for a specific platform
        st.markdown(f"### {platform_for_analysis} Performance Analysis")
        
        platform_df = metric_dfs[platform_for_analysis]
        
        # Create detailed engagement plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=platform_df["date"],
            y=platform_df["views"],
            mode='lines+markers',
            name='Views',
            line=dict(color='blue'),
            hovertemplate='%{y} views<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=platform_df["date"],
            y=platform_df["upvotes"],
            mode='lines+markers',
            name='Upvotes',
            line=dict(color='green'),
            hovertemplate='%{y} upvotes<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=platform_df["date"],
            y=platform_df["comments"],
            mode='lines+markers',
            name='Comments',
            line=dict(color='red'),
            hovertemplate='%{y} comments<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"{platform_for_analysis} Engagement Metrics",
            xaxis_title="Date",
            yaxis_title="Count",
            hovermode="x unified",
            legend_title="Metric",
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Key metrics
        st.markdown("### Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Calculate metrics for the platform
            avg_views = int(platform_df["views"].mean())
            st.metric("Avg. Views", avg_views)
        
        with col2:
            avg_upvotes = int(platform_df["upvotes"].mean())
            st.metric("Avg. Upvotes", avg_upvotes)
        
        with col3:
            avg_comments = int(platform_df["comments"].mean())
            st.metric("Avg. Comments", avg_comments)
        
        with col4:
            engagement_rate = avg_comments / avg_views * 100 if avg_views > 0 else 0
            st.metric("Engagement Rate", f"{engagement_rate:.1f}%")
        
        # Content performance
        st.markdown("### Content Performance Analysis")
        
        # Get posts for this platform from logs
        platform_posts = [
            post for post in st.session_state.get("post_logs", [])
            if post["platform"] == platform_for_analysis and post["success"]
        ]
        
        if platform_posts:
            # Create a simulated performance dataframe
            performance_data = []
            
            for post in platform_posts:
                # Simulate performance metrics for each post
                performance_data.append({
                    "Post Date": post["timestamp"],
                    "Content Preview": post["content"][:50] + "..." if len(post["content"]) > 50 else post["content"],
                    "Views": random.randint(50, 500),
                    "Upvotes": random.randint(5, 50),
                    "Comments": random.randint(1, 20),
                    "Engagement Rate": random.uniform(1.0, 8.0)
                })
            
            performance_df = pd.DataFrame(performance_data)
            st.dataframe(performance_df, use_container_width=True)
            
            # Best performing content
            if len(performance_df) > 0:
                st.markdown("### Top Performing Content")
                
                # Get the best performing post by engagement rate
                best_post = performance_df.loc[performance_df["Engagement Rate"].idxmax()]
                
                st.markdown(f"**Post Date:** {best_post['Post Date']}")
                st.markdown(f"**Content:** {best_post['Content Preview']}")
                st.markdown(f"**Views:** {best_post['Views']}")
                st.markdown(f"**Upvotes:** {best_post['Upvotes']}")
                st.markdown(f"**Comments:** {best_post['Comments']}")
                st.markdown(f"**Engagement Rate:** {best_post['Engagement Rate']:.1f}%")
        else:
            st.info(f"No posts for {platform_for_analysis} found in logs.")

def render_settings():
    """Render the settings page"""
    st.title("Settings")
    
    # API Configuration
    st.markdown("## API Configuration")
    st.info("API keys and credentials are managed through environment variables for security. To update these, please modify your environment configuration.")
    
    # Environment variables status
    st.markdown("### Environment Variables Status")
    
    env_vars = {
        "OPENAI_API_KEY": openai_api_key,
        "CAPTCHA_API_KEY": captcha_api_key,
        "QUORA_USER1": platform_credentials["quora"]["username"],
        "QUORA_PASS1": platform_credentials["quora"]["password"],
        "REDDIT_USER1": platform_credentials["reddit"]["username"],
        "REDDIT_PASS1": platform_credentials["reddit"]["password"],
        "TRIPADVISOR_USER1": platform_credentials["tripadvisor"]["username"],
        "TRIPADVISOR_PASS1": platform_credentials["tripadvisor"]["password"]
    }
    
    env_status = pd.DataFrame({
        "Variable": list(env_vars.keys()),
        "Status": ["✅ Set" if val else "❌ Not Set" for val in env_vars.values()]
    })
    
    st.dataframe(env_status, use_container_width=True, hide_index=True)
    
    # Content Generation Settings
    st.markdown("## Content Generation Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_model = st.selectbox(
            "Default GPT Model",
            ["gpt-3.5-turbo", "gpt-4"],
            index=0
        )
    
    with col2:
        default_temperature = st.slider(
            "Default Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
    
    # Save settings button
    if st.button("Save Settings"):
        st.session_state.default_model = default_model
        st.session_state.default_temperature = default_temperature
        st.success("Settings saved!")
    
    # Automation Settings
    st.markdown("## Automation Settings")
    
    headless_default = st.checkbox("Run browsers in headless mode by default", value=True)
    
    retry_count = st.slider(
        "Default retry count for actions",
        min_value=1,
        max_value=10,
        value=3
    )
    
    # Save automation settings
    if st.button("Save Automation Settings"):
        st.session_state.headless_default = headless_default
        st.session_state.retry_count = retry_count
        st.success("Automation settings saved!")
    
    # Data Management
    st.markdown("## Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear Generated Content History"):
            if "generated_contents" in st.session_state:
                st.session_state.generated_contents = []
            st.success("Generated content history cleared!")
    
    with col2:
        if st.button("Clear Post Logs"):
            if "post_logs" in st.session_state:
                st.session_state.post_logs = []
            st.success("Post logs cleared!")
    
    if st.button("Reset All Data", type="primary"):
        for key in ['generated_contents', 'post_logs', 'scheduled_posts', 'content_library']:
            if key in st.session_state:
                del st.session_state[key]
        st.success("All data has been reset!")

# Main App Logic
def main():
    """Main application logic"""
    # Initialize session state for first run
    if "generated_contents" not in st.session_state:
        st.session_state.generated_contents = []

    if "post_logs" not in st.session_state:
        st.session_state.post_logs = []

    if "scheduled_posts" not in st.session_state:
        st.session_state.scheduled_posts = []

    if "content_library" not in st.session_state:
        st.session_state.content_library = []
    
    # Render sidebar and get current page
    current_page = render_sidebar()
    
    # Store current page in session state
    st.session_state.page = current_page
    
    # Render the selected page
    if current_page == "Dashboard":
        render_dashboard()
    elif current_page == "Content Creation":
        render_content_creation()
    elif current_page == "Platform Posting":
        render_platform_posting()
    elif current_page == "Scheduling":
        render_scheduling()
    elif current_page == "Analytics":
        render_analytics()
    elif current_page == "Search & Respond":
        render_search_and_respond_page()
    elif current_page == "Settings":
        render_settings()

# Run the app
if __name__ == "__main__":
    main()

    st.success("Content saved to library!")

    # Save to session state
    if "generated_contents" not in st.session_state:
        st.session_state.generated_contents = []

    st.session_state.generated_contents.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic if 'topic' in locals() else "Default Topic",
        "type": content_type,
        "platform": platform,
        "tone": tone,
        "content": generated_content
    })

def render_platform_posting():
    """Render the platform posting page"""
    st.title("Platform Posting")
    
    if not AUTOMATION_AVAILABLE:
        st.error("Automation modules are not available. Cannot proceed with posting.")
    else:
        # Check if we came from content generation
        content_to_post = st.session_state.get("content_to_post", "")
        selected_platform = st.session_state.get("selected_platform", "Quora")
        
        # Platform selection
        if not content_to_post:
            platform_for_posting = st.selectbox(
                "Select platform for posting",
                ["Quora", "Reddit", "TripAdvisor"]
            )
        else:
            platform_for_posting = selected_platform
            st.info(f"Content ready for posting to {platform_for_posting}")
        
        # Content selection
        if not content_to_post:
            content_options = []
            
            # Add from generated content
            if "generated_contents" in st.session_state and st.session_state.generated_contents:
                content_options.extend([
                    f"{item['timestamp']} - {item['topic']} ({item['type']} for {item['platform']})"
                    for item in st.session_state.generated_contents
                ])
            
            # Add from content library
            if "content_library" in st.session_state and st.session_state.content_library:
                content_options.extend([
                    f"Library: {item['timestamp']} - {item['topic']} ({item['type']})"
                    for item in st.session_state.content_library
                ])
            
            content_options.append("Use custom content")
            
            selected_content_option = st.selectbox("Select content", content_options)
            
            # Custom content input if selected
            if selected_content_option == "Use custom content":
                content_to_post = st.text_area("Enter your content", height=200)
            else:
                # Get the selected content from session state
                if selected_content_option.startswith("Library:"):
                    # Extract from content library
                    library_index = content_options.index(selected_content_option) - len(st.session_state.get("generated_contents", []))
                    if library_index < len(st.session_state.content_library):
                        content_to_post = st.session_state.content_library[library_index]["content"]
                else:
                    # Extract from generated contents
                    generated_index = content_options.index(selected_content_option)
                    if generated_index < len(st.session_state.generated_contents):
                        content_to_post = st.session_state.generated_contents[generated_index]["content"]
                
                st.text_area("Content to post", content_to_post, height=200, disabled=True)
        else:
            st.text_area("Content to post", content_to_post, height=200, disabled=True)
        
        # Get username and password for the selected platform
        platform_key = platform_for_posting.lower()
        username = platform_credentials.get(platform_key, {}).get("username", "")
        password = platform_credentials.get(platform_key, {}).get("password", "")
        
        # Platform-specific fields
        if platform_for_posting == "Quora":
            # For Quora, we need question format
            if content_to_post and not content_to_post.endswith("?"):
                st.warning("Content for Quora should be in question format and end with a question mark.")
        
        elif platform_for_posting == "Reddit":
            # For Reddit, we need subreddit and title
            subreddit = st.text_input("Subreddit (without r/)")
            post_title = st.text_input("Post title")
        
        elif platform_for_posting == "TripAdvisor":
            # For TripAdvisor, we need location/hotel/restaurant
            location_name = st.text_input("Location/Hotel/Restaurant name")
            rating = st.slider("Rating (1-5)", 1, 5, 4)
        
        # Post button
        col1, col2 = st.columns(2)
        
        with col1:
            post_button = st.button("Post Content")
        
        with col2:
            headless_mode = st.checkbox("Run in headless mode", value=True)
        
        if post_button:
            if not content_to_post:
                st.error("Please select or enter content to post.")
            elif not username or not password:
                st.error(f"Credentials for {platform_for_posting} are not configured.")
            else:
                with st.spinner(f"Posting to {platform_for_posting}..."):
                    try:
                        result = None
                        
                        if platform_for_posting == "Quora":
                            result = quora_login_and_post(
                                email=username,
                                password=password,
                                question=content_to_post,
                                headless=headless_mode
                            )
                        
                        elif platform_for_posting == "Reddit":
                            if not subreddit or not post_title:
                                st.error("Subreddit and post title are required for Reddit posts.")
                            else:
                                result = reddit_login_and_post(
                                    username=username,
                                    password=password,
                                    subreddit=subreddit,
                                    title=post_title,
                                    content=content_to_post,
                                    headless=headless_mode
                                )
                        
                        elif platform_for_posting == "TripAdvisor":
                            if not location_name:
                                st.error("Location name is required for TripAdvisor reviews.")
                            else:
                                result = tripadvisor_login_and_post(
                                    username=username,
                                    password=password,
                                    location_name=location_name,
                                    rating=rating,
                                    review_text=content_to_post,
                                    headless=headless_mode
                                )
                        
                        # Display result
                        if result and result.get("success"):
                            st.success(f"Successfully posted to {platform_for_posting}!")
                            if result.get("url"):
                                st.markdown(f"[View your post]({result['url']})")
                            
                            # Log the successful post
                            if "post_logs" not in st.session_state:
                                st.session_state.post_logs = []
                            
                            st.session_state.post_logs.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "platform": platform_for_posting,
                                "content": content_to_post[:100] + "..." if len(content_to_post) > 100 else content_to_post,
                                "success": True,
                                "url": result.get("url", "")
                            })
                            
                            # Clear the content_to_post if we came from content generation
                            if "content_to_post" in st.session_state:
                                del st.session_state.content_to_post
                        else:
                            error_msg = result.get("error", "Unknown error") if result else "Failed to post"
                            st.error(f"Failed to post: {error_msg}")
                            
                            # Log the failed post
                            if "post_logs" not in st.session_state:
                                st.session_state.post_logs = []
                            
                            st.session_state.post_logs.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "platform": platform_for_posting,
                                "content": content_to_post[:100] + "..." if len(content_to_post) > 100 else content_to_post,
                                "success": False,
                                "error": error_msg
                            })
                    
                    except Exception as e:
                        st.error(f"Error during posting: {str(e)}")
                        
                        # Log the exception
                        if "post_logs" not in st.session_state:
                            st.session_state.post_logs = []
                        
                        st.session_state.post_logs.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "platform": platform_for_posting,
                            "content": content_to_post[:100] + "..." if len(content_to_post) > 100 else content_to_post,
                            "success": False,
                            "error": str(e)
                        })
