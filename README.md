# PDFsaver

PDF file auto-renaming tool - Bulk upload PDF files, automatically extract key information and rename.

## Project Overview

PDFsaver is a full-stack application for automating the renaming task of investment-related PDF documents. The MVP version focuses on processing digital PDFs in the browser, with an optional OCR Worker for handling scanned PDFs.

### Core Features

- 📄 **Bulk Upload**: Support drag & drop or file picker to upload multiple PDF files
- 🔍 **Text Extraction**: Client-side PDF text extraction (first 1-3 pages)
- 🤖 **Auto Classification**: Identify document types (dividend, buy/sell contracts, holdings, tax, etc.)
- 🏢 **Issuer Identification**: Identify issuers from predefined list
- 📅 **Date Extraction**: Extract dates based on document type priorities
- 🔢 **Account Identification**: Extract last 4 digits of HIN/SRN/Account numbers
- ✏️ **Inline Editing**: Edit suggested filenames
- 📦 **Bulk Download**: Download all renamed files as ZIP (includes manifest.csv)
- 🔐 **Privacy Protection**: All processing done client-side, files not uploaded to Vercel

## Project Structure

```
pdfsaver/
├── apps/
│   ├── web/                 # Next.js frontend application
│   │   ├── app/             # Next.js App Router
│   │   ├── components/      # React components
│   │   ├── lib/             # Utility functions
│   │   └── rules.yaml       # Classification rules
│   └── ocr-worker/          # Python FastAPI OCR Worker
│       ├── main.py          # FastAPI application
│       ├── requirements.txt # Python dependencies
│       ├── Dockerfile       # Docker image
│       └── deploy/          # Deployment configuration
│           ├── systemd/     # systemd service files
│           └── nginx/       # Nginx configuration
├── .gitignore
└── LICENSE
```

## Quick Start

### Frontend Application (Web)

```bash
cd apps/web
pnpm install
# Create .env.local file and configure environment variables
pnpm dev
```

Visit http://localhost:3000

### OCR Worker

```bash
cd apps/ocr-worker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export OCR_TOKEN=your-secure-token
export ALLOW_ORIGIN=http://localhost:3000

uvicorn main:app --host 0.0.0.0 --port 8123
```

## Tech Stack

### Frontend
- Next.js 14 (App Router)
- TypeScript
- React 18
- pdfjs-dist (PDF text extraction)
- jszip (ZIP generation)
- dayjs (Date handling)
- Tailwind CSS

### OCR Worker
- FastAPI
- PyMuPDF (PDF processing)
- OCRmyPDF (OCR engine)
- Tesseract OCR
- Python 3.11+

## Supported Document Types

- **DividendStatement**: Dividend/Distribution statements
- **BuyContract**: Buy contracts
- **SellContract**: Sell contracts
- **HoldingStatement**: Holding statements
- **TaxStatement**: Tax statements

## Supported Issuers

- Computershare
- Link Market Services
- Automic
- BoardRoom
- CommSec
- CMC Markets
- nabtrade
- Bell Potter
- Vanguard
- iShares / BlackRock
- Betashares
- Magellan

## Filename Format

```
YYYY-MM-DD_{issuer_slug}_{doc_type}_{account_last4}.pdf
```

Examples:
- `2025-03-31_Computershare_DividendStatement_1234.pdf`
- `2025-04-02_CommSec_BuyContract_5678.pdf`

## Deployment

### Vercel Deployment (Frontend)

1. Connect GitHub repository to Vercel
2. Configure environment variables:
   - `NEXT_PUBLIC_APP_ORIGIN`: Vercel app URL
   - `NEXT_PUBLIC_OCR_URL`: OCR Worker URL (optional)

### OCR Worker Deployment

#### Docker Method

```bash
cd apps/ocr-worker
docker build -t pdfsaver-ocr-worker .
docker run -d -p 8123:8123 \
  -e OCR_TOKEN=your-token \
  -e ALLOW_ORIGIN=https://pdfsaver.vercel.app \
  pdfsaver-ocr-worker
```

#### System Service Method

Refer to `apps/ocr-worker/README.md` for detailed systemd and Nginx configuration instructions.

## Security Features

- ✅ Client-side processing (files not uploaded to Vercel)
- ✅ Strict Content Security Policy
- ✅ Bearer Token authentication (OCR Worker)
- ✅ CORS restrictions
- ✅ No persistent storage

## Limitations

- Maximum 25MB per PDF file
- Default concurrent processing of 5 files
- Only analyzes first 3 pages of text
- OCR processing requires separate Worker deployment

## Development

### Adding New Document Types

Edit `apps/web/rules.yaml` to add new document type patterns.

### Adding New Issuers

Add to `apps/web/rules.yaml` in the `issuers.canonical` list.

### Testing

Project includes test PDF stub folder path (actual PDFs are not committed):

```
test-pdfs/
  ├── dividend-statement.pdf
  ├── buy-contract.pdf
  └── scanned-document.pdf
```

## License

MIT License - See [LICENSE](LICENSE) file for details

## Contributing

Issues and Pull Requests are welcome!

## Roadmap

- [ ] v1.1: OCR Worker returns full OCR'd PDF
- [ ] v1.2: Email-in workflow
- [ ] v1.3: SharePoint direct upload
- [ ] v1.4: Admin portal
- [ ] v2.0: SaaS multi-tenant version
