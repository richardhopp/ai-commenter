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
    proxychains4 \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install google-chrome-stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && google-chrome --version  # Verify Chrome installation

# Install Chrome driver - get the version matching your Chrome
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && echo "Chrome version: $CHROME_VERSION" \
    && CHROMEDRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
    && echo "Chromedriver version: $CHROMEDRIVER_VERSION" \
    && wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip \
    && chromedriver --version  # Verify Chromedriver installation

# Create a symbolic link to ensure Chrome can be found in the standard location
RUN ln -sf /usr/bin/google-chrome-stable /usr/bin/chrome \
    && ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome

# Configure ProxyChains for proxy integration
RUN echo "strict_chain" > /etc/proxychains4.conf \
    && echo "proxy_dns" >> /etc/proxychains4.conf \
    && echo "remote_dns_subnet 224" >> /etc/proxychains4.conf \
    && echo "tcp_read_time_out 15000" >> /etc/proxychains4.conf \
    && echo "tcp_connect_time_out 8000" >> /etc/proxychains4.conf \
    && echo "[ProxyList]" >> /etc/proxychains4.conf \
    && echo "# Add your proxies here" >> /etc/proxychains4.conf \
    && echo "# Example: http 11.22.33.44 3128" >> /etc/proxychains4.conf

# Set environment variables
ENV DISPLAY=:99
ENV CHROME_HEADLESS=true
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Create data directory for persistent storage
RUN mkdir -p /app/data/debug_screenshots /app/.streamlit

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create patch for undetected-chromedriver
COPY patch_undetected.py /app/patch_undetected.py
RUN python -c "from patch_undetected import patch_undetected; patch_undetected()"

# Copy the rest of your application code
COPY . /app

# Add alias for randomize_typing_speed function
RUN echo '\n# Add alias for backward compatibility\n_randomize_typing_speed = randomize_typing_speed' >> /app/automation_utils.py

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
command=streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n" > /etc/supervisor/conf.d/supervisord.conf

# Expose ports: 10000 for Streamlit UI, 5900 for VNC, 8501 backup port
EXPOSE 10000 5900 8501

# Print verification information at the end of the build
RUN echo "Chrome path: $(which google-chrome-stable)" \
    && echo "Chrome version: $(google-chrome --version)" \
    && echo "Chromedriver path: $(which chromedriver)" \
    && echo "Chromedriver version: $(chromedriver --version)"

# Make supervisord the entrypoint
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
