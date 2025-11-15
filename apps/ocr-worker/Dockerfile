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
EXPOSE 8000

# Run the application
# Use environment variables for configuration
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

