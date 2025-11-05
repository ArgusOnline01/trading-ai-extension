# Dockerfile for Visual Trade Copilot Backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8765

# Run the application
# Use --reload for development (hot reload on code changes)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8765", "--reload"]

