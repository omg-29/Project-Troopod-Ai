# Use the official Microsoft Playwright Python image
# This comes pre-installed with Chromium and all necessary system libraries
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We ensure the browser and its system dependencies are fully ready.
# PIN to the same version as the Playwright package.
RUN playwright install --with-deps chromium

# Copy project files
COPY . .

# Expose the port
EXPOSE 8000

# Start the application
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
