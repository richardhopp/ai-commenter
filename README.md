# Stealth Multi-Platform Poster

## Table of Contents

1. [Features](#features)  
2. [Project Structure](#project-structure)  
3. [Installation](#installation)  
4. [Usage](#usage)  
5. [Deployment on Streamlit Cloud](#deployment-on-streamlit-cloud)  
6. [Security & Best Practices](#security--best-practices)  
7. [License](#license)

---

## Features

- **Root Keyword Search**: Enter a keyword (e.g., “real estate tokyo”) to search for relevant threads.
- **Adaptive AI Answers**: Uses OpenAI’s ChatGPT (text-davinci-003) to analyze question complexity and generate either a concise or detailed answer.
- **Smart Funnel for Money Sites**: Automatically selects the best target "money site" (e.g., Living Abroad, Real Estate Abroad, Investment Visas) based on question complexity.
- **Multi-Platform Posting**: Supports posting on Quora, Reddit, and TripAdvisor with platform-specific login and posting routines.
- **Stealth Automation**: Leverages undetected-chromedriver with headless Chromium, rotating User-Agent strings, and optional proxy support to mimic human behavior.
- **CAPTCHA Solving**: Integrates with 2Captcha to automatically solve CAPTCHAs when they appear.
- **Human Behavior Simulation**: Implements slow typing, randomized delays, scrolling, and mouse movements to appear as a real user.
- **Comprehensive Logging**: Maintains a log report of processed thread URLs, generated answers, and posting statuses.
- **Secure API Key Storage**: Uses [Streamlit’s secrets management](https://docs.streamlit.io/streamlit-cloud/get-started/share-streamlit-apps#secrets-management) to keep your keys out of the repository.

---

## Project Structure

stealth_poster/ ├── streamlit_app.py # Main Streamlit interface (UI, thread search, ChatGPT integration, logging) ├── quora_automation.py # Quora-specific login and posting automation ├── reddit_automation.py # Reddit-specific login and posting automation ├── tripadvisor_automation.py # TripAdvisor-specific login and posting automation ├── automation_utils.py # Shared utilities (driver setup, search functions, content extraction, smart funnel, ChatGPT integration) ├── requirements.txt # Python dependencies ├── packages.txt # Linux packages (Chromium and Chromium Driver) for Streamlit Cloud ├── apt.txt # Additional apt configuration (if needed)

yaml
Copy

---

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/stealth_poster.git
   cd stealth_poster
Install Dependencies:

All required Python packages are listed in requirements.txt. When deploying to Streamlit Cloud, these packages are automatically installed.

Configure Streamlit Cloud Secrets:

Instead of including a local .streamlit/secrets.toml file in the repository, add your credentials and API keys via the Streamlit Cloud Secrets settings (see the Deployment on Streamlit Cloud section for details).

Usage
Manual Mode:

Select a target platform (quora, reddit, or tripadvisor).

Choose an account from the configured credentials.

Provide any target URL (e.g., a Quora question URL, a TripAdvisor thread URL, or for Reddit, specify a subreddit and post title).

Enter the content to post.

Click "Post Content Manually" to log in and post your content.

A log report will display the thread URLs processed and their statuses.

Auto Mode:

Select "auto" mode to automatically search for threads using a root keyword.

Enter the root keyword (e.g., “real estate tokyo”) and set the maximum number of results and delay between thread processing.

Optionally, use ChatGPT to generate an answer based on each question’s complexity. Provide additional instructions if needed.

Click "Run Auto Process" to search for threads, analyze questions via ChatGPT, generate answers, and post them.

A log report is maintained with details of each processed thread.

Deployment on Streamlit Cloud
Push to GitHub:
Upload the entire stealth_poster folder to your GitHub repository.

Set Up Your Streamlit Cloud App:

Go to Streamlit Cloud and create a new app by linking your repository.

Ensure that packages.txt and apt.txt are present so that Chromium and its driver are installed.

Add your credentials and API keys via the Streamlit Cloud Secrets settings. Use the sample structure below.

Sample Secrets Structure for Streamlit Cloud:

toml
Copy
[quora]
user1 = "quora_user@example.com"
pass1 = "quora_password"
user2 = "another_quora_user@example.com"
pass2 = "another_quora_password"

[reddit]
user1 = "reddit_username"
pass1 = "reddit_password"

[tripadvisor]
user1 = "tripadvisor_user@example.com"
pass1 = "tripadvisor_password"

[captcha]
api_key = "YOUR_2CAPTCHA_API_KEY"

[openai]
api_key = "YOUR_OPENAI_API_KEY"
Deploy:
Deploy the app. Your Streamlit Cloud instance will install the necessary Linux packages from packages.txt and apt.txt and run your app.

Security & Best Practices
Credential Security:
Do not commit sensitive credentials to your repository. Use Streamlit Cloud’s Secrets management to securely store your account credentials, 2Captcha API key, and OpenAI API key.

Proxy & User-Agent Rotation:
The app rotates User-Agent strings and supports optional proxy configuration to help avoid IP-based blocking and detection.

Human Behavior Simulation:
Built-in delays, slow typing, scrolling, and mouse movements simulate human interaction to help bypass bot detection.

CAPTCHA Solving:
Integration with 2Captcha allows the app to automatically solve CAPTCHAs when encountered.

Logging:
All actions and thread processing are logged in the app’s interface. Review the log report to monitor successful and failed posts.

License
This project is licensed under the MIT License.