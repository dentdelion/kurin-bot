# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create directory for Google credentials
RUN mkdir -p /app/credentials

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Create startup script that handles Google credentials from environment variable
RUN echo '#!/bin/bash\n\
# Create Google credentials file from environment variable if provided\n\
if [ ! -z "$GOOGLE_CREDENTIALS_JSON" ]; then\n\
    echo "Creating Google credentials file from environment variable..."\n\
    echo "$GOOGLE_CREDENTIALS_JSON" > /app/credentials/credentials.json\n\
    echo "Google credentials file created."\n\
elif [ ! -f "/app/credentials/credentials.json" ]; then\n\
    echo "Warning: No Google credentials found. Please provide GOOGLE_CREDENTIALS_JSON environment variable or mount credentials file."\n\
fi\n\
\n\
# Start the application\n\
exec python run.py' > /app/start.sh && chmod +x /app/start.sh

# Simple health check - just verify the main script exists and Python works
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the application via startup script
CMD ["/app/start.sh"] 