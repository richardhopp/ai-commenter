import os
import time
import logging
import random
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import selenium components
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    StaleElementReferenceException
)

# Import automation utilities
from automation_utils import init_driver, solve_captcha_if_present, simulate_human_behavior, randomize_typing_speed
from automation_utils import wait_for_element, wait_for_elements, safe_click, fill_text_field
from automation_utils import scroll_into_view, take_screenshot, check_for_errors, generate_content_with_openai
from automation_utils import save_cookies, load_cookies, cleanup_driver

# Quora-specific constants
QUORA_URL = "https://www.quora.com"
QUORA_LOGIN_URL = "https://www.quora.com/login"
QUORA_ADD_QUESTION_URL = "https://www.quora.com/ask"

# Quora selectors
LOGIN_SELECTORS = {
    "email_input": (By.ID, "email"),
    "password_input": (By.ID, "password"),
    "login_button": (By.CSS_SELECTOR, "button[type='submit']"),
    "error_message": (By.CSS_SELECTOR, ".login_error_message"),
}

QUESTION_SELECTORS = {
    "question_input": (By.CSS_SELECTOR, "textarea.qu-borderAll"),
    "submit_button": (By.CSS_SELECTOR, "button[type='submit']"),
    "topic_input": (By.CSS_SELECTOR, "input[placeholder='Add topics']"),
    "first_topic_suggestion": (By.CSS_SELECTOR, ".qu-dynamicFontSize--small"),
}

def quora_login(driver, email: str, password: str) -> bool:
    """
    Log in to Quora with the provided credentials.
    
    Args:
        driver: The webdriver instance
        email: User's email address
        password: User's password
        
    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        logger.info("Navigating to Quora login page")
        driver.get(QUORA_LOGIN_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        # Check for CAPTCHA
        solve_captcha_if_present(driver)
        
        # Fill in email
        email_input = wait_for_element(driver, *LOGIN_SELECTORS["email_input"])
        if not email_input:
            logger.error("Email input field not found")
            take_screenshot(driver, "login_email_not_found.png")
            return False
        
        fill_text_field(driver, email_input, email)
        simulate_human_behavior(driver)
        
        # Fill in password
        password_input = wait_for_element(driver, *LOGIN_SELECTORS["password_input"])
        if not password_input:
            logger.error("Password input field not found")
            take_screenshot(driver, "login_password_not_found.png")
            return False
        
        fill_text_field(driver, password_input, password)
        simulate_human_behavior(driver)
        
        # Click login button
        login_button = wait_for_element(driver, *LOGIN_SELECTORS["login_button"])
        if not login_button:
            logger.error("Login button not found")
            take_screenshot(driver, "login_button_not_found.png")
            return False
        
        safe_click(driver, login_button)
        
        # Wait for login to complete and verify
        time.sleep(5)
        
        # Check for error messages
        try:
            error_element = driver.find_element(*LOGIN_SELECTORS["error_message"])
            if error_element.is_displayed():
                logger.error(f"Login failed: {error_element.text}")
                take_screenshot(driver, "login_error.png")
                return False
        except NoSuchElementException:
            # No error message found, which is good
            pass
        
        # Check if we're redirected to the feed or home page
        if "feed" in driver.current_url or driver.current_url == QUORA_URL:
            logger.info("Login successful")
            # Save cookies for later use
            save_cookies(driver, "quora_cookies.json")
            return True
        else:
            logger.error(f"Login might have failed. Current URL: {driver.current_url}")
            take_screenshot(driver, "login_unexpected_page.png")
            return False
            
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        take_screenshot(driver, "login_exception.png")
        return False

def add_question_to_quora(driver, question: str, topics: List[str] = None) -> bool:
    """
    Add a new question to Quora.
    
    Args:
        driver: The webdriver instance
        question: The question to post
        topics: Optional list of topics to tag
        
    Returns:
        bool: True if posting successful, False otherwise
    """
    try:
        logger.info(f"Adding question: {question}")
        driver.get(QUORA_ADD_QUESTION_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        # Fill in question
        question_input = wait_for_element(driver, *QUESTION_SELECTORS["question_input"])
        if not question_input:
            logger.error("Question input field not found")
            take_screenshot(driver, "question_input_not_found.png")
            return False
        
        fill_text_field(driver, question_input, question)
        simulate_human_behavior(driver)
        
        # Add topics if provided
        if topics and len(topics) > 0:
            topic_input = wait_for_element(driver, *QUESTION_SELECTORS["topic_input"])
            if topic_input:
                for topic in topics:
                    fill_text_field(driver, topic_input, topic)
                    simulate_human_behavior(driver, 1.0, 2.0)
                    
                    # Select first suggestion
                    suggestion = wait_for_element(driver, *QUESTION_SELECTORS["first_topic_suggestion"])
                    if suggestion:
                        safe_click(driver, suggestion)
                        simulate_human_behavior(driver)
                    else:
                        # If no suggestion found, just press Enter
                        topic_input.send_keys(Keys.ENTER)
                        simulate_human_behavior(driver)
        
        # Submit the question
        submit_button = wait_for_element(driver, *QUESTION_SELECTORS["submit_button"])
        if not submit_button:
            logger.error("Submit button not found")
            take_screenshot(driver, "submit_button_not_found.png")
            return False
        
        safe_click(driver, submit_button)
        
        # Wait for submission to complete
        time.sleep(5)
        
        # Check if we're redirected to the question page
        if "/answer/" in driver.current_url:
            logger.info("Question added successfully")
            return True
        else:
            logger.error(f"Question submission might have failed. Current URL: {driver.current_url}")
            take_screenshot(driver, "question_submission_unexpected_page.png")
            return False
            
    except Exception as e:
        logger.error(f"Error adding question: {str(e)}")
        take_screenshot(driver, "add_question_exception.png")
        return False

def generate_question(topic: str, style: str = "normal") -> str:
    """
    Generate a question for Quora using OpenAI.
    
    Args:
        topic: The topic to generate a question about
        style: The style of the question (normal, controversial, deep, etc.)
        
    Returns:
        str: Generated question
    """
    styles = {
        "normal": "a straightforward question",
        "controversial": "a thought-provoking or slightly controversial question",
        "deep": "a philosophical or deep question",
        "personal": "a personal experience question",
        "funny": "a humorous or absurd question",
        "technical": "a technical or detailed question"
    }
    
    style_prompt = styles.get(style.lower(), styles["normal"])
    
    system_prompt = """
    You are an expert at creating engaging Quora questions. 
    Create questions that are clear, specific, and likely to generate interesting answers.
    Do not include any prefixes, suffixes, or explanations in your response.
    Return only the question text itself.
    """
    
    user_prompt = f"""
    Generate {style_prompt} for Quora about {topic}.
    
    Make sure the question:
    - Is grammatically correct
    - Ends with a question mark
    - Is not too basic or easily searchable
    - Would encourage detailed responses
    - Is between 10-20 words for readability
    - Doesn't include 'Quora' in the question itself
    """
    
    question = generate_content_with_openai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=100,
        temperature=0.7,
        fallback_response=f"What are the most interesting aspects of {topic}?"
    )
    
    # Clean up the question
    question = question.strip().rstrip('.').strip()
    if not question.endswith('?'):
        question += '?'
    
    return question

def suggest_topics_for_question(question: str, num_topics: int = 3) -> List[str]:
    """
    Suggest relevant topics for a Quora question using OpenAI.
    
    Args:
        question: The question to suggest topics for
        num_topics: Number of topics to suggest
        
    Returns:
        List[str]: List of suggested topics
    """
    system_prompt = """
    You are an expert at tagging Quora questions with appropriate topics.
    Return only a comma-separated list of topics, without any prefixes, suffixes, or explanations.
    """
    
    user_prompt = f"""
    Suggest {num_topics} relevant topics for the following Quora question:
    
    "{question}"
    
    Provide only a comma-separated list of topics.
    Topics should be:
    - Short (1-3 words each)
    - Relevant to the question
    - Common topics on Quora
    - Properly capitalized
    """
    
    topics_text = generate_content_with_openai(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=100,
        temperature=0.3,
        fallback_response="Technology, Science, Education"
    )
    
    # Clean up and format the topics
    topics = [topic.strip() for topic in topics_text.split(',')]
    
    return topics

def quora_login_and_post(email: str, password: str, question: str = None, topic: str = None, headless: bool = True) -> Dict[str, Any]:
    """
    Log in to Quora and post a question.
    
    Args:
        email: Quora account email
        password: Quora account password
        question: Question to post (if None, one will be generated)
        topic: Topic to generate a question about (if question is None)
        headless: Whether to run the browser in headless mode
        
    Returns:
        Dict with status and results
    """
    result = {
        "success": False,
        "question": question,
        "url": None,
        "error": None
    }
    
    driver = None
    try:
        # Initialize the webdriver
        driver = init_driver(headless=headless)
        
        # Try to log in
        login_success = quora_login(driver, email, password)
        if not login_success:
            result["error"] = "Failed to log in to Quora"
            return result
        
        # Generate question if not provided
        if not question and topic:
            question = generate_question(topic)
            result["question"] = question
        elif not question:
            result["error"] = "Neither question nor topic provided"
            return result
        
        # Generate topics
        topics = suggest_topics_for_question(question)
        
        # Post the question
        post_success = add_question_to_quora(driver, question, topics)
        if not post_success:
            result["error"] = "Failed to post question"
            return result
        
        # Get the URL of the posted question
        result["url"] = driver.current_url
        result["success"] = True
        
        return result
    
    except Exception as e:
        logger.error(f"Error in quora_login_and_post: {str(e)}")
        result["error"] = str(e)
        if driver:
            take_screenshot(driver, "quora_automation_exception.png")
        return result
    
    finally:
        # Clean up
        if driver:
            cleanup_driver(driver)

# Main function for testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    email = os.getenv("QUORA_EMAIL")
    password = os.getenv("QUORA_PASSWORD")
    
    if not email or not password:
        logger.error("Quora credentials not found in environment variables")
    else:
        result = quora_login_and_post(
            email=email,
            password=password,
            topic="Artificial Intelligence",
            headless=False
        )
        
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Question: {result['question']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
