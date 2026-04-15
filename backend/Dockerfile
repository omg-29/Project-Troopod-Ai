# Use official Python image as parent
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its system dependencies
# This is the critical part for Render: it installs Chromium + all required libaries
RUN playwright install --with-deps chromium

# Copy project files
COPY . .

# Expose the port
EXPOSE 8000

# Start the application
# We use 0.0.0.0 to bind to all interfaces in the container
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
