# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create templates directory
RUN mkdir -p templates

# Expose port
EXPOSE 5002

# Set environment variables
ENV FLASK_APP=otp_app_backend.py
ENV FLASK_ENV=production

# Run the application
CMD ["python", "otp_app_backend.py"] 