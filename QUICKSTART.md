# PDFsaver Quick Start Guide

## Prerequisites

- Node.js 18+ and pnpm/npm/yarn
- Python 3.11+ (OCR Worker only)
- Tesseract OCR (OCR Worker only)

## 1. Frontend Application Setup

```bash
# Navigate to frontend directory
cd apps/web

# Install dependencies
pnpm install
# or npm install / yarn install

# Create environment variables file
# Windows PowerShell:
New-Item -ItemType File -Path .env.local
# Linux/Mac:
touch .env.local

# Edit .env.local, add:
# NEXT_PUBLIC_APP_ORIGIN=http://localhost:3000
# NEXT_PUBLIC_OCR_URL=http://127.0.0.1:8123/v1/ocr-extract
# NEXT_PUBLIC_OCR_TOKEN=your-token  # Optional

# Start development server
pnpm dev
```

Visit http://localhost:3000

## 2. OCR Worker Setup (Optional)

### Method A: Python Virtual Environment

```bash
# Navigate to OCR Worker directory
cd apps/ocr-worker

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng ocrmypdf ghostscript poppler-utils

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export OCR_TOKEN=your-secure-token
export ALLOW_ORIGIN=http://localhost:3000

# Start service
uvicorn main:app --host 0.0.0.0 --port 8123
```

### Method B: Docker

```bash
cd apps/ocr-worker

# Build image
docker build -t pdfsaver-ocr-worker .

# Run container
docker run -d \
  -p 8123:8123 \
  -e OCR_TOKEN=your-token \
  -e ALLOW_ORIGIN=http://localhost:3000 \
  --name pdfsaver-ocr \
  pdfsaver-ocr-worker
```

## 3. Testing

1. Open browser and visit http://localhost:3000
2. Drag and drop or select PDF files
3. Wait for processing to complete
4. Edit filenames (if needed)
5. Click "Download All" to generate ZIP file

## 4. Common Issues

### PDF Processing Fails
- Ensure PDF files are not corrupted
- Check browser console for error messages
- For scanned PDFs, ensure OCR Worker is running

### OCR Worker Connection Fails
- Check if OCR Worker is running: `curl http://localhost:8123/healthz`
- Check CORS settings: `ALLOW_ORIGIN` must match frontend URL
- Verify token is correct

### Styles Not Displaying
- Ensure Tailwind CSS dependencies are installed: `pnpm install`
- Check that `tailwind.config.js` and `postcss.config.js` exist

## 5. Production Deployment

### Vercel Deployment (Frontend)

1. Push code to GitHub
2. Import project in Vercel
3. Configure environment variables:
   - `NEXT_PUBLIC_APP_ORIGIN`: Your Vercel app URL
   - `NEXT_PUBLIC_OCR_URL`: OCR Worker URL (optional)

### OCR Worker Deployment

Refer to `apps/ocr-worker/README.md` for detailed deployment instructions.

## Next Steps

- Read the full [README.md](README.md)
- Review [PRD.md](PRD.md) to understand project requirements
- Customize `apps/web/rules.yaml` to add new document types or issuers
