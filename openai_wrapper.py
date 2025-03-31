"""
OpenAI API wrapper with proper configuration handling.
This module ensures OpenAI API is properly configured using our centralized config.
"""

import logging
import openai
from config import get_config

logger = logging.getLogger(__name__)

def configure_openai():
    """Configure the OpenAI API with the API key from config"""
    config = get_config()
    api_key = config.get("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("OpenAI API key not found in configuration")
        return False
    
    openai.api_key = api_key
    logger.info("OpenAI API configured successfully")
    return True

def is_openai_configured():
    """Check if OpenAI API is configured"""
    return bool(openai.api_key)

def generate_content(
    user_prompt: str, 
    system_prompt: str = "You are a helpful assistant.", 
    model: str = "gpt-3.5-turbo", 
    max_tokens: int = 500, 
    temperature: float = 0.7,
    fallback_response: str = None
) -> str:
    """
    Generate content using OpenAI's API with proper error handling.
    
    Args:
        user_prompt: The user prompt
        system_prompt: The system prompt that sets the AI behavior
        model: The OpenAI model to use
        max_tokens: Maximum tokens in the response
        temperature: Randomness of the output (0.0-1.0)
        fallback_response: Response to return if API call fails
        
    Returns:
        str: Generated content
    """
    if not is_openai_configured():
        if not configure_openai():
            logger.error("OpenAI API key not configured")
            return fallback_response if fallback_response else "API key not configured."
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=1,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        return response.choices[0].message["content"]
    except openai.error.AuthenticationError:
        logger.error("OpenAI API authentication failed")
        return fallback_response if fallback_response else "Authentication with the OpenAI API failed. Please check your API key."
    except openai.error.RateLimitError:
        logger.error("OpenAI API rate limit exceeded")
        return fallback_response if fallback_response else "OpenAI API rate limit exceeded. Please try again later."
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return fallback_response if fallback_response else "An error occurred with the OpenAI API."
    except Exception as e:
        logger.error(f"Error generating content with OpenAI: {str(e)}")
        return fallback_response if fallback_response else "I couldn't generate appropriate content at this time."
