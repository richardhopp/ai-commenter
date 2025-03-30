"success": False,
                            "error": str(e)
                        })

# Scheduling page
elif page == "Scheduling":
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
                        post_id = schedule_post(schedule_platform, content_to_schedule, schedule_datetime)
                        
                        if "scheduled_posts" not in st.session_state:
                            st.session_state.scheduled_posts = []
                        
                        # Add to scheduled posts
                        st.session_state.scheduled_posts.append({
                            "id": post_id,
                            "platform": schedule_platform,
                            "content": content_to_schedule,
                            "scheduled_time": schedule_datetime,
                            "platform_data": platform_data,
                            "status": "scheduled"
                        })
                        
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

# Analytics page
elif page == "Analytics":
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
        engagement_plot = create_engagement_plot(metric_dfs)
        st.plotly_chart(engagement_plot, use_container_width=True)
        
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

# Settings page
elif page == "Settings":
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

# Initialize session state for first run
if "generated_contents" not in st.session_state:
    st.session_state.generated_contents = []

if "post_logs" not in st.session_state:
    st.session_state.post_logs = []

if "scheduled_posts" not in st.session_state:
    st.session_state.scheduled_posts = []

if "content_library" not in st.session_state:
    st.session_state.content_library = []

# Main function for running the app
if __name__ == "__main__":
    # This is executed when the script is run directly
    pass
