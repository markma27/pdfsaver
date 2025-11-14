# PDFsaver Web Application

Next.js 14 frontend application for bulk uploading PDF files and auto-renaming.

## Features

- 📄 Bulk upload PDF files (drag & drop supported)
- 🔍 Client-side text extraction (using pdfjs-dist)
- 🤖 Auto-classify document types (dividend, buy/sell contracts, holdings, tax, etc.)
- 🏢 Identify issuers (Computershare, Link Market Services, etc.)
- 📅 Extract dates and account information
- ✏️ Inline edit suggested filenames
- 📦 Bulk download as ZIP file (includes manifest.csv)
- 🔐 Strict CSP security policy
- 🔄 Optional OCR Worker integration (for scanned PDFs)

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **PDF Processing**: pdfjs-dist
- **ZIP Generation**: jszip
- **Date Handling**: dayjs
- **Styling**: Tailwind CSS

## Quick Start

### Install Dependencies

```bash
pnpm install
# or
npm install
# or
yarn install
```

### Environment Variables

Create `.env.local` file and configure:

```bash
NEXT_PUBLIC_APP_ORIGIN=http://localhost:3000
NEXT_PUBLIC_OCR_URL=http://127.0.0.1:8123/v1/ocr-extract
NEXT_PUBLIC_OCR_TOKEN=your-ocr-worker-token  # Optional, if OCR Worker requires authentication
```

Note: `NEXT_PUBLIC_OCR_TOKEN` will be exposed in frontend code, only for development. Production environments should use server-side proxy.

### Development Mode

```bash
pnpm dev
```

Application will start at http://localhost:3000

### Build for Production

```bash
pnpm build
pnpm start
```

## Project Structure

```
apps/web/
├── app/                 # Next.js App Router
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Main page
│   └── globals.css      # Global styles
├── components/          # React components
│   ├── Dropzone.tsx     # File upload area
│   ├── ResultsTable.tsx # Results table
│   └── StatusBadge.tsx  # Status badge
├── lib/                 # Utility functions
│   └── pdf/
│       ├── extractText.ts  # PDF text extraction
│       ├── classify.ts     # Document classification
│       ├── filename.ts     # Filename generation
│       └── rules.ts        # Rules loading
├── pages/
│   └── api/
│       └── health.ts    # Health check endpoint
└── rules.yaml           # Classification rules configuration
```

## Usage

1. **Upload Files**: Drag and drop PDF files to the upload area, or click to select files
2. **Auto Processing**: System will automatically extract text and classify documents
3. **Edit Filename**: Click on suggested filename to edit
4. **OCR Processing**: For scanned PDFs, click "Process OCR" button (requires OCR Worker configuration)
5. **Download**: Click "Download All" button to generate ZIP file

## Security Features

- All processing done client-side, files are not uploaded to Vercel servers
- Strict Content Security Policy (CSP)
- OCR requests sent directly to configured OCR Worker (bypassing Vercel limits)

## Limitations

- Maximum 25MB per PDF file
- Default concurrent processing of 5 files
- Only extracts first 3 pages for text analysis
- PDFs requiring OCR need OCR Worker configuration

## Testing

Project includes test PDF stub folder path (actual PDF files are not committed):

```
test-pdfs/
  ├── dividend-statement.pdf
  ├── buy-contract.pdf
  └── scanned-document.pdf
```

## Deploy to Vercel

1. Push code to GitHub repository
2. Import project in Vercel
3. Configure environment variables:
   - `NEXT_PUBLIC_APP_ORIGIN`: Your Vercel app URL
   - `NEXT_PUBLIC_OCR_URL`: OCR Worker URL (optional)

## License

MIT License
