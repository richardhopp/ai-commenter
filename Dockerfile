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
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install google-chrome-stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

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
EXPOSE 8501 5900

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
