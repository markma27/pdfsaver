# PDFsaver OCR Worker

FastAPI service for OCR processing and text extraction of scanned PDFs.

## Features

- 🔍 Automatically detect if PDF has text layer
- 📝 OCR processing for scanned PDFs (using OCRmyPDF + Tesseract)
- 🎯 Extract document fields (type, issuer, date)
- 🔐 Bearer Token authentication
- 🌐 CORS support
- 🐳 Docker support

## Tech Stack

- **Framework**: FastAPI
- **OCR Engine**: OCRmyPDF + Tesseract OCR
- **PDF Processing**: PyMuPDF (fitz)
- **Python Version**: 3.11+

## Quick Start

### System Requirements

- Ubuntu 22.04+ or similar Linux distribution
- Python 3.11+
- Tesseract OCR
- Ghostscript
- Poppler utils

### Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    ocrmypdf \
    ghostscript \
    poppler-utils
```

### Install Python Dependencies

```bash
cd apps/ocr-worker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create `.env` file:

```bash
OCR_TOKEN=your-secure-token-here
ALLOW_ORIGIN=https://pdfsaver.vercel.app
```

### Run Service

```bash
uvicorn main:app --host 0.0.0.0 --port 8123
```

Service will start at http://0.0.0.0:8123

### Health Check

```bash
curl http://localhost:8123/healthz
```

## Docker Deployment

### Build Image

```bash
docker build -t pdfsaver-ocr-worker .
```

### Run Container

```bash
docker run -d \
  -p 8123:8123 \
  -e OCR_TOKEN=your-token \
  -e ALLOW_ORIGIN=https://pdfsaver.vercel.app \
  --name pdfsaver-ocr \
  pdfsaver-ocr-worker
```

## API Endpoints

### GET /healthz

Health check endpoint

**Response**:
```json
{
  "status": "ok"
}
```

### POST /v1/ocr-extract

Process PDF file and extract fields

**Headers**:
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Body**:
- `file`: PDF file (multipart/form-data)

**Response**:
```json
{
  "has_text": false,
  "ocred": true,
  "pages_used": 3,
  "fields": {
    "doc_type": "DividendStatement",
    "issuer": "Computershare",
    "date_iso": "2025-03-31"
  },
  "suggested_filename": "2025-03-31_Computershare_DividendStatement_1234.pdf"
}
```

## System Service Deployment

### Using systemd

1. Copy service file:
```bash
sudo cp deploy/systemd/pdfsaver.service /etc/systemd/system/
```

2. Edit service file, update paths and user

3. Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pdfsaver
sudo systemctl start pdfsaver
sudo systemctl status pdfsaver
```

### Nginx Reverse Proxy

1. Copy Nginx configuration:
```bash
sudo cp deploy/nginx/pdfsaver.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/pdfsaver.conf /etc/nginx/sites-enabled/
```

2. Test configuration:
```bash
sudo nginx -t
```

3. Reload Nginx:
```bash
sudo systemctl reload nginx
```

## Performance Optimization

- OCR processing may take 10-15 seconds per file
- Recommend using multi-core CPU and sufficient memory
- For high load, consider horizontal scaling with multiple Worker instances

## Security Recommendations

1. **Change Default Token**: Use strong random token
2. **HTTPS**: Use HTTPS in production (configure SSL certificates)
3. **Firewall**: Restrict access IP ranges
4. **Regular Updates**: Keep dependencies updated

## Troubleshooting

### OCR Fails

- Check if Tesseract is correctly installed: `tesseract --version`
- Check OCRmyPDF: `ocrmypdf --version`
- View logs: `journalctl -u pdfsaver -f`

### Insufficient Memory

- Increase system swap space
- Limit concurrent request count
- Use larger VM instance

### CORS Errors

- Check `ALLOW_ORIGIN` environment variable
- Ensure frontend URL exactly matches (including protocol and port)

## License

MIT License
