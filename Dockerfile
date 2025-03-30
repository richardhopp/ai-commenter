# Use a lightweight Python 3.12 image
FROM python:3.12-slim

# Install system dependencies, including Chromium, its driver, and GUI tools
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    xvfb \
    fluxbox \
    x11vnc \
    supervisor \
    wget \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for display
ENV DISPLAY=:99

# Copy requirements and install Python packages
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
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

# Expose the Streamlit port and the VNC port
EXPOSE 8501 5900

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
