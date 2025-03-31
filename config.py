"""
Centralized configuration management for the Content Automation app.
This module handles environment variables and Streamlit secrets uniformly.
"""

import os
import logging
import streamlit as st

logger = logging.getLogger(__name__)

class Config:
    """
    Centralized configuration that prioritizes environment variables,
    then falls back to Streamlit secrets if available.
    """
    
    def __init__(self):
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables and Streamlit secrets"""
        # API Keys
        self._config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
        self._config["CAPTCHA_API_KEY"] = os.environ.get("CAPTCHA_API_KEY", "")
        
        # Platform Credentials
        # Quora
        self._config["QUORA_USER1"] = os.environ.get("QUORA_USER1", "")
        self._config["QUORA_PASS1"] = os.environ.get("QUORA_PASS1", "")
        
        # Reddit
        self._config["REDDIT_USER1"] = os.environ.get("REDDIT_USER1", "")
        self._config["REDDIT_PASS1"] = os.environ.get("REDDIT_PASS1", "")
        
        # TripAdvisor
        self._config["TRIPADVISOR_USER1"] = os.environ.get("TRIPADVISOR_USER1", "")
        self._config["TRIPADVISOR_PASS1"] = os.environ.get("TRIPADVISOR_PASS1", "")
        
        # Try to load from Streamlit secrets if empty
        if hasattr(st, "secrets"):
            # API Keys
            if not self._config["OPENAI_API_KEY"] and "openai" in st.secrets and "api_key" in st.secrets["openai"]:
                self._config["OPENAI_API_KEY"] = st.secrets["openai"]["api_key"]
            
            if not self._config["CAPTCHA_API_KEY"] and "captcha" in st.secrets and "api_key" in st.secrets["captcha"]:
                self._config["CAPTCHA_API_KEY"] = st.secrets["captcha"]["api_key"]
            
            # Quora
            if not self._config["QUORA_USER1"] and "quora" in st.secrets and "user1" in st.secrets["quora"]:
                self._config["QUORA_USER1"] = st.secrets["quora"]["user1"]
            
            if not self._config["QUORA_PASS1"] and "quora" in st.secrets and "pass1" in st.secrets["quora"]:
                self._config["QUORA_PASS1"] = st.secrets["quora"]["pass1"]
            
            # Reddit
            if not self._config["REDDIT_USER1"] and "reddit" in st.secrets and "user1" in st.secrets["reddit"]:
                self._config["REDDIT_USER1"] = st.secrets["reddit"]["user1"]
            
            if not self._config["REDDIT_PASS1"] and "reddit" in st.secrets and "pass1" in st.secrets["reddit"]:
                self._config["REDDIT_PASS1"] = st.secrets["reddit"]["pass1"]
            
            # TripAdvisor
            if not self._config["TRIPADVISOR_USER1"] and "tripadvisor" in st.secrets and "user1" in st.secrets["tripadvisor"]:
                self._config["TRIPADVISOR_USER1"] = st.secrets["tripadvisor"]["user1"]
            
            if not self._config["TRIPADVISOR_PASS1"] and "tripadvisor" in st.secrets and "pass1" in st.secrets["tripadvisor"]:
                self._config["TRIPADVISOR_PASS1"] = st.secrets["tripadvisor"]["pass1"]
        
        # Log configuration status
        logger.info("Configuration loaded")
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self._config.get(key, default)
    
    def is_configured(self, service):
        """Check if a service is properly configured"""
        if service == "openai":
            return bool(self._config.get("OPENAI_API_KEY"))
        elif service == "captcha":
            return bool(self._config.get("CAPTCHA_API_KEY"))
        elif service == "quora":
            return bool(self._config.get("QUORA_USER1")) and bool(self._config.get("QUORA_PASS1"))
        elif service == "reddit":
            return bool(self._config.get("REDDIT_USER1")) and bool(self._config.get("REDDIT_PASS1"))
        elif service == "tripadvisor":
            return bool(self._config.get("TRIPADVISOR_USER1")) and bool(self._config.get("TRIPADVISOR_PASS1"))
        return False
    
    def get_platform_credentials(self, platform):
        """Get credentials for a specific platform"""
        if platform == "quora":
            return {
                "username": self._config.get("QUORA_USER1", ""),
                "password": self._config.get("QUORA_PASS1", "")
            }
        elif platform == "reddit":
            return {
                "username": self._config.get("REDDIT_USER1", ""),
                "password": self._config.get("REDDIT_PASS1", "")
            }
        elif platform == "tripadvisor":
            return {
                "username": self._config.get("TRIPADVISOR_USER1", ""),
                "password": self._config.get("TRIPADVISOR_PASS1", "")
            }
        return {"username": "", "password": ""}


# Create a singleton instance
config = Config()

# Function to get the configuration instance
def get_config():
    return config
