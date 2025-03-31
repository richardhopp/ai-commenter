# search_respond_ui.py
# Integration module for the search and response system into the Streamlit UI

import streamlit as st
import pandas as pd
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import our modules
from search_module import SearchResult, search_for_threads, analyze_thread_relevance, cached_search_for_threads
from smart_funnel import MoneySiteDatabase, initialize_money_site_database, create_smart_funnel_for_thread
from response_generator import generate_platform_tailored_response

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def render_search_and_respond_page():
    """Render the Search & Respond page in the Streamlit UI"""
    st.title("Search & Respond")
    
    # Initialize money site database if not already in session state
    if "money_site_db" not in st.session_state:
        st.session_state.money_site_db = initialize_money_site_database()
    
    # Initialize search results if not in session state
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    
    # Initialize selected results if not in session state
    if "selected_results" not in st.session_state:
        st.session_state.selected_results = []
    
    # Initialize responses if not in session state
    if "generated_responses" not in st.session_state:
        st.session_state.generated_responses = {}
    
    # Create tabs for different functionalities
    search_tab, money_sites_tab, respond_tab, batch_tab = st.tabs([
        "Search Threads", "Money Sites", "Generate Responses", "Batch Processing"
    ])
    
    # Search Threads Tab
    with search_tab:
        st.header("Search for Relevant Threads")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input("Search Query", placeholder="Enter keywords to search for relevant threads...")
        
        with col2:
            # Platform filter
            platforms = st.multiselect(
                "Platforms",
                options=["quora", "reddit", "stackexchange", "tripadvisor"],
                default=["quora", "reddit"]
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_results = st.slider("Max Results", min_value=5, max_value=50, value=10)
        
        with col2:
            relevance_threshold = st.slider("Relevance Threshold", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
        
        with col3:
            use_cache = st.checkbox("Use Cache", value=True)
        
        # Search button
        if st.button("Search for Threads"):
            if search_query:
                with st.spinner(f"Searching for '{search_query}'..."):
                    # Perform the search
                    results = cached_search_for_threads(
                        query=search_query,
                        platforms=platforms,
                        max_results=max_results,
                        use_cache=use_cache
                    )
                    
                    # Filter by relevance
                    if relevance_threshold > 0:
                        results = analyze_thread_relevance(results, search_query, relevance_threshold)
                    
                    # Store in session state
                    st.session_state.search_results = results
                    
                    # Clear selected results
                    st.session_state.selected_results = []
                    
                    st.success(f"Found {len(results)} relevant threads")
            else:
                st.error("Please enter a search query")
        
        # Display search results if available
        if st.session_state.search_results:
            st.subheader(f"Search Results ({len(st.session_state.search_results)})")
            
            # Convert to DataFrame for better display
            results_data = []
            for i, result in enumerate(st.session_state.search_results):
                results_data.append({
                    "Select": i,  # Index for selection
                    "Title": result.title,
                    "Platform": result.platform.capitalize(),
                    "Relevance": f"{result.relevance_score:.2f}",
                    "URL": result.url
                })
            
            results_df = pd.DataFrame(results_data)
            
            # Display as a table with selection capability
            selected_indices = st.multiselect(
                "Select threads to process",
                options=results_df["Select"].tolist(),
                format_func=lambda x: f"{results_df.iloc[x]['Title']} ({results_df.iloc[x]['Platform']})"
            )
            
            # Save selected results
            st.session_state.selected_results = [
                st.session_state.search_results[i] for i in selected_indices
            ]
            
            # Display the full table of results
            st.dataframe(results_df[["Title", "Platform", "Relevance", "URL"]], use_container_width=True)
            
            # Button to add selected threads to processing
            if selected_indices and st.button("Analyze Selected Threads"):
                st.session_state.tab_index = 2  # Switch to the Respond tab
                st.rerun()
    
    # Money Sites Tab
    with money_sites_tab:
        st.header("Money Site Management")
        
        # Display current money sites
        if st.session_state.money_site_db and st.session_state.money_site_db.sites:
            st.subheader("Registered Money Sites")
            
          # Display sites in an expandable format
            for site in st.session_state.money_site_db.sites:
                with st.expander(f"{site.name} - {site.primary_url}"):
                    st.write(f"**Categories:** {', '.join(site.categories)}")
                    st.write(f"**Target Audience:** {', '.join(site.target_audience)}")
                    st.write(f"**Number of Pages:** {len(site.pages)}")
                    
                    # Display subpages in a table
                    if site.pages:
                        pages_data = []
                        for page in site.pages:
                            pages_data.append({
                                "Title": page.title,
                                "URL": page.url,
                                "Categories": ', '.join(page.categories)
                            })
                        
                        st.dataframe(pd.DataFrame(pages_data), use_container_width=True)
        else:
            st.info("No money sites registered yet. Add a new site or import from a file.")
        
        # Add new money site form
        with st.expander("Add New Money Site"):
            with st.form("add_money_site_form"):
                site_name = st.text_input("Site Name", placeholder="Living Abroad Guide")
                site_url = st.text_input("Primary URL", placeholder="https://example.com")
                site_categories = st.text_input("Categories (comma-separated)", placeholder="Expat, Living Abroad, International Living")
                site_audience = st.text_input("Target Audience (comma-separated)", placeholder="Expats, Digital Nomads, Retirees")
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_button = st.form_submit_button("Add Money Site")
                
                with col2:
                    reset_button = st.form_submit_button("Clear Form")
            
            if submit_button and site_name and site_url:
                from smart_funnel import MoneySite
                
                # Create new money site
                new_site = MoneySite(
                    name=site_name,
                    primary_url=site_url,
                    categories=[cat.strip() for cat in site_categories.split(',')] if site_categories else [],
                    target_audience=[aud.strip() for aud in site_audience.split(',')] if site_audience else []
                )
                
                # Add to database
                st.session_state.money_site_db.add_site(new_site)
                
                st.success(f"Added new money site: {site_name}")
        
        # Add subpage to existing site
        with st.expander("Add Subpage to Existing Site"):
            if st.session_state.money_site_db and st.session_state.money_site_db.sites:
                with st.form("add_subpage_form"):
                    # Select site
                    site_options = [site.name for site in st.session_state.money_site_db.sites]
                    selected_site = st.selectbox("Select Money Site", options=site_options)
                    
                    # Subpage details
                    page_title = st.text_input("Page Title", placeholder="Complete Guide to Tokyo Neighborhoods")
                    page_url = st.text_input("Page URL", placeholder="https://example.com/tokyo-neighborhoods/")
                    page_categories = st.text_input("Categories (comma-separated)", placeholder="Japan, Tokyo, Housing")
                    page_keywords = st.text_input("Keywords (comma-separated)", placeholder="tokyo neighborhoods, best places to live in tokyo")
                    page_summary = st.text_area("Content Summary", placeholder="Detailed guide to Tokyo's neighborhoods...")
                    
                    add_page_button = st.form_submit_button("Add Subpage")
                
                if add_page_button and selected_site and page_title and page_url:
                    from smart_funnel import SubPage
                    
                    # Find the selected site
                    site = st.session_state.money_site_db.get_site_by_name(selected_site)
                    if site:
                        # Create and add new subpage
                        new_page = SubPage(
                            url=page_url,
                            title=page_title,
                            categories=[cat.strip() for cat in page_categories.split(',')] if page_categories else [],
                            keywords=[kw.strip() for kw in page_keywords.split(',')] if page_keywords else [],
                            content_summary=page_summary
                        )
                        
                        site.add_page(new_page)
                        st.success(f"Added new subpage to {selected_site}: {page_title}")
            else:
                st.warning("No money sites available. Please add a money site first.")
        
        # Import/Export
        with st.expander("Import/Export Money Site Database"):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Export Database to File"):
                    # Save to file
                    import json
                    
                    # Get data as JSON
                    db_data = st.session_state.money_site_db.to_dict()
                    json_data = json.dumps(db_data, indent=2)
                    
                    # Offer for download
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"money_sites_{timestamp}.json"
                    
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=filename,
                        mime="application/json"
                    )
            
            with col2:
                uploaded_file = st.file_uploader("Import Database from JSON", type=["json"])
                
                if uploaded_file is not None:
                    try:
                        # Read the file
                        import json
                        json_data = json.loads(uploaded_file.getvalue().decode())
                        
                        # Create new database
                        from smart_funnel import MoneySiteDatabase
                        st.session_state.money_site_db = MoneySiteDatabase.from_dict(json_data)
                        
                        st.success("Successfully imported money site database")
                    except Exception as e:
                        st.error(f"Error importing database: {str(e)}")
    
    # Generate Responses Tab
    with respond_tab:
        st.header("Generate Responses")
        
        # Check if we have selected results
        if not st.session_state.selected_results:
            st.warning("No threads selected. Please go to the Search Threads tab to select threads.")
        else:
            st.subheader(f"Selected Threads ({len(st.session_state.selected_results)})")
            
            # Display selected threads with funnel analysis
            for i, result in enumerate(st.session_state.selected_results):
                with st.expander(f"{i+1}. {result.title} ({result.platform.capitalize()})"):
                    st.write(f"**URL:** {result.url}")
                    st.write(f"**Relevance Score:** {result.relevance_score:.2f}")
                    
                    # Create or retrieve smart funnel for this thread
                    if result.url not in st.session_state.get("thread_strategies", {}):
                        with st.spinner("Analyzing thread content..."):
                            # Create smart funnel
                            strategy = create_smart_funnel_for_thread(result, st.session_state.money_site_db)
                            
                            # Store in session state
                            if "thread_strategies" not in st.session_state:
                                st.session_state.thread_strategies = {}
                            
                            st.session_state.thread_strategies[result.url] = strategy
                    else:
                        strategy = st.session_state.thread_strategies[result.url]
                    
                    # Display funnel info if available
                    if strategy:
                        st.write("### Smart Funnel")
                        st.write(f"**Money Site:** {strategy.money_site.name}")
                        st.write(f"**Target Page:** {strategy.target_page.title}")
                        st.write(f"**URL:** {strategy.target_page.url}")
                        st.write(f"**Reference Type:** {strategy.reference_type}")
                        st.write(f"**Reference Position:** {strategy.reference_position}")
                        
                        # Generate response button
                        if st.button(f"Generate Response for Thread #{i+1}", key=f"gen_resp_{i}"):
                            with st.spinner("Generating response..."):
                                # Generate response
                                response = generate_platform_tailored_response(
                                    question=result.question_text or result.title,
                                    strategy=strategy
                                )
                                
                                # Store in session state
                                if "generated_responses" not in st.session_state:
                                    st.session_state.generated_responses = {}
                                
                                st.session_state.generated_responses[result.url] = response
                                
                                st.success("Response generated!")
                        
                        # Display response if available
                        if result.url in st.session_state.generated_responses:
                            st.markdown("### Generated Response")
                            st.text_area(
                                "Response",
                                value=st.session_state.generated_responses[result.url],
                                height=300
                            )
                            
                            # Copy to clipboard button
                            copy_text = st.session_state.generated_responses[result.url]
                            st.button(
                                "Copy to Clipboard",
                                key=f"copy_{i}",
                                on_click=lambda: st.session_state.update({"clipboard": copy_text})
                            )
                    else:
                        st.warning("Could not create a smart funnel for this thread. The content may not match any money site topics.")
            
            # Generate all responses button
            if st.button("Generate All Responses"):
                with st.spinner("Generating responses for all selected threads..."):
                    for result in st.session_state.selected_results:
                        # Skip if already generated
                        if result.url in st.session_state.generated_responses:
                            continue
                        
                        # Get or create strategy
                        if result.url not in st.session_state.get("thread_strategies", {}):
                            strategy = create_smart_funnel_for_thread(result, st.session_state.money_site_db)
                            
                            if "thread_strategies" not in st.session_state:
                                st.session_state.thread_strategies = {}
                            
                            st.session_state.thread_strategies[result.url] = strategy
                        else:
                            strategy = st.session_state.thread_strategies[result.url]
                        
                        # Generate response if strategy exists
                        if strategy:
                            response = generate_platform_tailored_response(
                                question=result.question_text or result.title,
                                strategy=strategy
                            )
                            
                            if "generated_responses" not in st.session_state:
                                st.session_state.generated_responses = {}
                            
                            st.session_state.generated_responses[result.url] = response
                    
                    st.success(f"Generated responses for {len(st.session_state.generated_responses)} threads!")
    
    # Batch Processing Tab
    with batch_tab:
        st.header("Batch Processing")
        st.subheader("Automatic Search and Respond")
        
        with st.form("batch_processing_form"):
            batch_query = st.text_input("Search Query", placeholder="Enter keywords to search for relevant threads...")
            
            col1, col2 = st.columns(2)
            
            with col1:
                batch_platforms = st.multiselect(
                    "Platforms",
                    options=["quora", "reddit", "stackexchange", "tripadvisor"],
                    default=["quora", "reddit"]
                )
            
            with col2:
                batch_max_results = st.slider("Max Results", min_value=5, max_value=50, value=20)
            
            col1, col2 = st.columns(2)
            
            with col1:
                batch_relevance_threshold = st.slider(
                    "Relevance Threshold", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.6, 
                    step=0.05
                )
            
            with col2:
                batch_complexity_threshold = st.slider(
                    "Min Complexity",
                    min_value=1,
                    max_value=5,
                    value=2
                )
            
            batch_process_button = st.form_submit_button("Run Batch Process")
        
        if batch_process_button and batch_query:
            # Track progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize batch results if not in session state
            if "batch_results" not in st.session_state:
                st.session_state.batch_results = []
            
            # Step 1: Search for threads
            status_text.text("Searching for threads...")
            progress_bar.progress(10)
            
            search_results = cached_search_for_threads(
                query=batch_query,
                platforms=batch_platforms,
                max_results=batch_max_results,
                use_cache=True
            )
            
            # Step 2: Filter by relevance
            status_text.text("Filtering by relevance...")
            progress_bar.progress(20)
            
            filtered_results = analyze_thread_relevance(search_results, batch_query, batch_relevance_threshold)
            
            # Step 3: Create smart funnels for each thread
            status_text.text("Creating smart funnels...")
            progress_bar.progress(30)
            
            batch_strategies = {}
            valid_results = []
            
            for i, result in enumerate(filtered_results):
                # Update progress
                progress_percent = 30 + (40 * (i / len(filtered_results)))
                progress_bar.progress(int(progress_percent))
                status_text.text(f"Analyzing thread {i+1}/{len(filtered_results)}...")
                
                # Create smart funnel
                strategy = create_smart_funnel_for_thread(result, st.session_state.money_site_db)
                
                # Keep only valid strategies and results
                if strategy and result.complexity >= batch_complexity_threshold:
                    batch_strategies[result.url] = strategy
                    valid_results.append(result)
            
            # Step 4: Generate responses
            status_text.text("Generating responses...")
            progress_bar.progress(70)
            
            batch_responses = {}
            
            for i, result in enumerate(valid_results):
                # Update progress
                progress_percent = 70 + (30 * (i / len(valid_results)))
                progress_bar.progress(int(progress_percent))
                status_text.text(f"Generating response {i+1}/{len(valid_results)}...")
                
                # Get strategy
                strategy = batch_strategies[result.url]
                
                # Generate response
                response = generate_platform_tailored_response(
                    question=result.question_text or result.title,
                    strategy=strategy
                )
                
                batch_responses[result.url] = response
            
            # Complete
            progress_bar.progress(100)
            status_text.text(f"Batch processing complete! Found {len(valid_results)} relevant threads.")
            
            # Store results
            st.session_state.batch_results = [
                {
                    "result": result,
                    "strategy": batch_strategies[result.url],
                    "response": batch_responses[result.url]
                }
                for result in valid_results
            ]
            
            # Display summary
            st.subheader("Batch Processing Results")
            st.write(f"Found {len(filtered_results)} relevant threads, generated responses for {len(valid_results)} threads.")
        
        # Display batch results if available
        if st.session_state.get("batch_results"):
            st.subheader(f"Processed Threads ({len(st.session_state.batch_results)})")
            
            for i, item in enumerate(st.session_state.batch_results):
                result = item["result"]
                strategy = item["strategy"]
                response = item["response"]
                
                with st.expander(f"{i+1}. {result.title} ({result.platform.capitalize()})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**URL:** {result.url}")
                        st.write(f"**Relevance:** {result.relevance_score:.2f}")
                        st.write(f"**Complexity:** {result.complexity}")
                    
                    with col2:
                        st.write(f"**Money Site:** {strategy.money_site.name}")
                        st.write(f"**Target Page:** {strategy.target_page.title}")
                        st.write(f"**Reference Type:** {strategy.reference_type}")
                    
                    st.markdown("### Response")
                    st.text_area(
                        f"Response for #{i+1}",
                        value=response,
                        height=200
                    )
                    
                    # Add to selected results button
                    if st.button(f"Add to Selected Threads", key=f"add_selected_{i}"):
                        if result not in st.session_state.selected_results:
                            st.session_state.selected_results.append(result)
                            st.session_state.thread_strategies[result.url] = strategy
                            st.session_state.generated_responses[result.url] = response
                            st.success(f"Added thread to selected threads")


def add_search_respond_to_app():
    """Add the search and respond page to the main application"""
    # Check if we're using the new or old UI structure
    if "page" in st.session_state:
        # New UI with render_sidebar function
        current_page = st.session_state.page
        
        if current_page == "Search & Respond":
            render_search_and_respond_page()
    else:
        # Default to just rendering the page directly
        render_search_and_respond_page()


# When run directly, show the page
if __name__ == "__main__":
    render_search_and_respond_page()
