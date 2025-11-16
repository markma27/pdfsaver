FROM python:3.11-slim

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    ocrmypdf \
    ghostscript \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY llm_helper.py .

# Expose port
EXPOSE 8123

# Run the application
# Use environment variables for configuration
# Default to 8123 if PORT not set
# Use shell form to allow environment variable substitution
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8123}"]

