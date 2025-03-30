# Use a lightweight Python 3.12 image
FROM python:3.12-slim

# Install system dependencies, including tools for GUI and VNC
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    fluxbox \
    x11vnc \
    supervisor \
    net-tools \
    unzip \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install google-chrome-stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

# Install Chrome driver - get the version matching your Chrome
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && CHROMEDRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
    && wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Set environment variable for display and headless mode (set to false for visible browser)
ENV DISPLAY=:99
ENV CHROME_HEADLESS=false

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app

# Create supervisor configuration to launch Xvfb, fluxbox, x11vnc, and your Streamlit app
RUN mkdir -p /etc/supervisor/conf.d
RUN echo "[supervisord]\nnodaemon=true\n\n\
[program:xvfb]\n\
command=Xvfb :99 -screen 0 1920x1080x24\n\
autorestart=true\n\n\
[program:fluxbox]\n\
command=fluxbox\n\
autorestart=true\n\n\
[program:x11vnc]\n\
command=x11vnc -display :99 -forever -nopw -listen 0.0.0.0 -xkb\n\
autorestart=true\n\n\
[program:streamlit]\n\
command=streamlit run app.py --server.port=8501 --server.address=0.0.0.0\n\
autorestart=true\n" > /etc/supervisor/conf.d/supervisord.conf

# Expose ports: 8501 for Streamlit UI, 5900 for VNC
EXPOSE 8501 5900 10000

# Make sure port 10000 is used for the CMD in render.com
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
