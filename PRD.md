# PDFsaver — Product Requirements Document (PRD)
**Version:** v2.0  
**Author:** Mark Ma (Jaquillard Minns)  
**Date:** 2025-11-15  
**Last Updated:** 2025-11-15

---

## 1. Overview
PDFsaver automates the manual task of downloading, renaming, and organizing investment-related PDF documents (dividend statements, contract notes, holding statements, tax statements, etc.).  
The goal is to let users drag and drop documents (or forward them via email in later versions), automatically extract key fields, and produce consistently named files ready for download or upload to SharePoint.

The current version focuses on **automated renaming of digital (text) PDFs** entirely in the browser for privacy and speed, with an **optional OCR worker** powered by LLM (Large Language Model) to handle scanned documents and improve classification accuracy.

**Key Features:**
- Modern split-panel UI with PDF preview
- LLM-powered document classification and field extraction
- Smart OCR that skips PDFs with existing text layers
- Professional confirmation dialogs
- Brand logos (JM and PG) in header

---

## 2. Objectives
- Save time and reduce manual renaming effort for accounting/investment teams.
- Ensure consistent filename conventions across documents and issuers.
- Preserve data security: files should not leave the user’s environment unless the user explicitly uploads to a trusted OCR worker.
- Build a base for a future SaaS product similar in workflow to Dext or Hubdoc (email-in, dashboard, export).

---

## 3. Key User Stories
| Role | Story |
|------|--------|
| Accountant / Admin | I can drag and drop multiple PDF statements to the web app and receive renamed versions following firm naming conventions. I can preview each PDF in the right panel before downloading. |
| Accountant | If a file is scanned (no text layer), the app automatically detects this and processes it via the OCR worker with LLM-powered classification. |
| Accountant | I can click on any file in the list to preview it in the right panel, navigate pages, and adjust zoom level. |
| Manager | I can bulk download all renamed PDFs individually, or use "Clear All" to remove all files with a professional confirmation dialog. |
| IT Admin | I can deploy a local OCR worker VM (FastAPI + Ollama) to process scanned PDFs privately with LLM intelligence. |
| User | The UI is modern and professional with Inter font, card-based layouts, and brand logos (JM and PG) visible in the header. |
| Future (SaaS) | I can forward emails with attachments to a unique inbox, and documents automatically appear in the portal ready for review. |

---

## 4. Scope

### In Scope (v2.0)
- Web app (Next.js on Vercel) with modern split-panel UI
- Bulk upload of PDFs (10–50 files typical, up to 25 MB each)
- **LLM-powered classification** via OCR worker (Ollama llama3)
- **Smart OCR** that skips PDFs with existing text layers
- Filename convention engine:
  ```
  {date}_{TitleCase(issuer)}_{TitleCase(doc_type)}.pdf
  ```
- Client-side text parsing (pdf.js) for digital PDFs
- PDF preview panel with navigation and zoom controls
- Card-based file list with click-to-preview
- Professional confirmation dialogs
- Brand logos (JM and PG) in header
- Integration with external OCR worker via API for scanned files
- Download renamed files individually or in bulk
- Support for 8 document types including CallAndDistributionStatement and NetAssetSummaryStatement

### Future Scope
- Email-in ingestion and queueing.
- SharePoint direct upload via Graph API (MSAL PKCE flow).
- Admin portal for reviewing processed docs.
- OCR worker scaling (multiple nodes, queues).
- SaaS multi-tenant deployment and billing.

---

## 5. Architecture Overview

### 5.1 High-Level Diagram
```
[User Browser @ pdfsaver.vercel.app]
   ├─ Drag/drop PDFs
   ├─ Extract text client-side (pdf.js)
   ├─ Detect: text found → send to OCR Worker for LLM processing
   └─ No text → POST file → [OCR Worker VM]

[OCR Worker VM]
   ├─ FastAPI + Tesseract + OCRmyPDF + Ollama (LLM)
   ├─ Smart OCR: Check for existing text layer → skip OCR if found
   ├─ Extract text from scanned PDFs (if needed)
   ├─ LLM Classification (Ollama llama3):
   │   ├─ Extract doc_type, issuer, date intelligently
   │   ├─ Prioritize fund/product names over ASX codes
   │   └─ Remove company suffixes ("Pty Ltd", etc.)
   ├─ Rule-based validation and correction
   ├─ Build filename (Title Case format)
   ├─ Cache results (file hash-based)
   └─ Return JSON { fields, suggested_filename }

[Vercel Hosting]
   ├─ Static Next.js site (no file storage)
   ├─ Modern UI: Split-panel layout, PDF preview, Inter font
   ├─ Environment vars for OCR endpoint
   └─ Brand logos (JM and PG) in header
```

---

## 6. Functional Requirements

### 6.1 File Processing
- Allow drag-drop or file picker upload (multiple PDFs).
- For each file:
  1. **Smart OCR Detection**: Check if PDF has existing text layer (first 2 pages). Skip OCR if sufficient text found.
  2. Extract text using `pdfjs-dist` (first 2-3 pages).
  3. **LLM-Powered Classification** (when OCR worker configured):
     - Send extracted text to LLM (Ollama with llama3 model) for intelligent classification
     - LLM extracts: doc_type, issuer, date, account_last4
     - Falls back to rule-based classification if LLM unavailable
  4. **Rule-Based Classification** (fallback/validation):
     - **Doc types**: DividendStatement, BuyContract, SellContract, HoldingStatement, TaxStatement, PeriodicStatement, CallAndDistributionStatement, NetAssetSummaryStatement
     - **Issuer**: Prioritize actual fund/product names over ASX codes or generic company names
     - **Date**: Prioritize specific dates (e.g., "Payment Date" for dividends, "Confirmation Date" for contracts)
     - **Account last4**: Removed from filename (v2.0)
  5. Build filename: `YYYY-MM-DD_IssuerName_DocumentType.pdf` (Title Case, no dashes except in date)
  6. Show results in card-based list with PDF preview panel

### 6.2 Bulk Download & File Management
- **Individual Download**: Click suggested filename to download that file directly
- **Bulk Download**: "Download All" button → download each file individually (browser handles multiple downloads)
- **Clear All**: Remove all files with professional confirmation dialog
- **File Preview**: Click any file in the list to preview PDF in right panel
  - PDF preview supports page navigation (prev/next)
  - Zoom controls (default 125%, adjustable)
  - Canvas-based rendering using pdfjs-dist

### 6.3 OCR Integration & LLM Processing
- **Smart OCR**: Check PDF for existing text layer before processing
  - If text layer exists: Skip OCR, extract text directly
  - If no text layer: Run OCRmyPDF with optimized settings (pages_to_check=2, optimize=1)
- **LLM-Powered Extraction** (when OCR worker configured):
  - POST file to worker:
    ```
    POST /v1/ocr-extract
    Headers: Authorization: Bearer <token>
    Body: multipart/form-data { file }
    ```
  - Worker processes with LLM (Ollama llama3):
    - Extracts document fields intelligently
    - Suggests filename in correct format
    - Handles complex document types
  - Worker returns:
    ```json
    {
      "fields": {
        "doc_type": "DistributionStatement",
        "issuer": "Eley Griffiths Group Mid Cap Fund Class A",
        "date_iso": "2025-10-01"
      },
      "suggested_filename": "2025-10-01_EleyGriffithsGroupMidCapFundClassA_DistributionStatement.pdf"
    }
    ```
- **Caching**: File hash-based cache to speed up duplicate file processing
- Show progress + result inline with status badges

### 6.4 Configurable Rules & Document Types
Rules defined in code with "must" and "hint" keywords for classification:

**Document Types:**
- **DividendStatement**: Distribution statements, dividend payments
- **BuyContract**: Buy confirmation notes
- **SellContract**: Sell confirmation notes
- **HoldingStatement**: CHESS statements, issuer sponsored holdings
- **TaxStatement**: Annual tax statements, NAV & Taxation statements
- **PeriodicStatement**: Periodic account statements
- **CallAndDistributionStatement**: Combined capital call and distribution statements
- **NetAssetSummaryStatement**: Net asset summary statements

**Classification Priority:**
1. LLM classification (primary method when available)
2. Rule-based validation and correction
3. Immediate correction for known misclassifications (e.g., DistributionStatement vs BuyContract)

**Issuer Extraction:**
- Prioritize actual fund/product names over ASX codes
- Remove company suffixes ("Pty Ltd", "Limited", etc.)
- Extract from document text, not hardcoded lists

### 6.5 Naming Logic
```
filename = {date_iso}_{TitleCase(issuer)}_{TitleCase(doc_type)}.pdf
```

**Format Rules:**
- **Date**: `YYYY-MM-DD` format (ISO date)
- **Issuer**: Title Case, no dashes, spaces preserved (e.g., "EleyGriffithsGroupMidCapFundClassA")
- **Document Type**: Title Case, no dashes (e.g., "DistributionStatement", "BuyContract", "DistributionAndCapitalCallStatement")
- **Separator**: Underscore (`_`) between date, issuer, and document type
- **Account last4**: Removed (v2.0)
- **Company suffixes**: Automatically removed ("Pty Ltd", "Limited", etc.)

**Special Cases:**
- `CallAndDistributionStatement` → `DistributionAndCapitalCallStatement`
- All document types mapped to Title Case equivalents

---

## 7. Non-Functional Requirements
| Category | Requirement |
|-----------|-------------|
| **Performance** | < 2 s for digital PDFs (local); < 10 s via OCR worker with smart OCR (skips PDFs with text layers); File hash caching for duplicate files. |
| **File size** | Up to 25 MB per PDF; no upload to Vercel. |
| **Security** | No files stored on Vercel; HTTPS between browser and worker; Bearer token authentication. |
| **Scalability** | OCR worker horizontal scaling via Docker/VMs; Concurrent processing (MAX_CONCURRENT=10). |
| **Privacy** | No persistent file storage; temp files deleted after processing; File hash-based caching (in-memory only). |
| **Compatibility** | Chrome, Edge, Firefox (latest); desktop focus; Responsive design for tablet screens. |
| **Extensibility** | Easy to plug in SharePoint upload or new issuer rules; Modular component architecture. |
| **UI/UX** | Modern design with Inter font; Professional confirmation dialogs; Accessible keyboard navigation (ESC, Enter). |
| **Branding** | JM Logo and PG Logo displayed in header; Consistent visual identity. |

---

## 8. Deployment Plan

### Frontend (Vercel)
- **Framework:** Next.js 14 (App Router)
- **Storage:** none
- **Libraries:** 
  - pdfjs-dist (PDF text extraction and preview)
  - jszip (ZIP generation)
  - dayjs (date handling)
- **UI Framework:** Tailwind CSS with Inter font
- **Design System:**
  - Slate color palette
  - Card-based layouts
  - Professional confirmation dialogs
  - Split-panel UI (file list + PDF preview)
- **Branding:** JM Logo and PG Logo in header
- **Env vars:**
  - `NEXT_PUBLIC_OCR_URL=https://ocr.pdfsaver.com/v1/ocr-extract`
  - `NEXT_PUBLIC_OCR_TOKEN=<optional-bearer-token>`
- **Limits:** Vercel body size limit bypassed (browser → worker direct)

### OCR Worker VM
- **Stack:** Ubuntu 22.04 + Python + FastAPI + Tesseract + OCRmyPDF + Ollama (LLM)
- **LLM Integration:** 
  - Ollama with llama3 model (default)
  - Configurable via `OLLAMA_URL` and `OLLAMA_MODEL` environment variables
  - LLM handles document classification and field extraction
- **Ports:** 8123 (HTTP), optional 443 via Nginx/Caddy
- **Auth:** Bearer token (short-lived or static)
- **CORS:** allow `https://pdfsaver.vercel.app` or `http://localhost:3000` (dev)
- **Docker:** Fully containerized with Dockerfile
- **File size limit:** 200 MB (`client_max_body_size 200m`)
- **Performance Optimizations:**
  - Smart OCR (skip PDFs with text layers)
  - Reduced OCR parameters (pages_to_check=2, optimize=1)
  - File hash-based caching
  - Concurrent processing (MAX_CONCURRENT=10)
- **Auto-start:** systemd service `pdfsaver.service` or Docker container

### Domains
- Frontend: `https://pdfsaver.vercel.app`
- Worker: `https://ocr.pdfsaver.com`

---

## 9. Version History & Roadmap

### v2.0 (Current)
- ✅ Modern split-panel UI with PDF preview
- ✅ LLM-powered document classification (Ollama llama3)
- ✅ Smart OCR (skip PDFs with existing text layers)
- ✅ Enhanced document types (CallAndDistributionStatement, NetAssetSummaryStatement)
- ✅ Improved naming rules (Title Case, no account suffix)
- ✅ Professional confirmation dialogs
- ✅ Brand logos (JM and PG) in header
- ✅ Inter font throughout application
- ✅ Card-based file list with click-to-preview
- ✅ PDF preview with navigation and zoom controls

### Future Roadmap
| Version | Feature | Description |
|----------|----------|-------------|
| v2.1 | OCR worker streaming back full OCR'd PDF | Allow downloading the searchable PDF. |
| v2.2 | Email-in workflow | Users forward dividend/tax statements to unique address. |
| v2.3 | SharePoint upload | Direct browser → SharePoint folder. |
| v2.4 | Admin portal | List, review, edit, export processed documents. |
| v3.0 | SaaS multi-tenant | Auth, billing, team management, analytics. |

---

## 10. Risks & Mitigation
| Risk | Impact | Mitigation |
|-------|---------|-------------|
| Vercel upload size limit | Blocked uploads > 4.5 MB | Client-side parsing; direct browser → worker uploads. |
| OCR worker overload | Slow jobs | Limit concurrency, scale horizontally. |
| Incorrect naming | Confusion | Keep editable filenames + `manifest.csv`. |
| Data leakage | Privacy/legal | No persistent storage, HTTPS, firewall + token auth. |
| Provider downtime | Availability | Multi-VM setup or on-prem agent fallback. |

---

## 11. Success Metrics
- 90%+ of investment-related PDFs renamed correctly without manual edits (improved with LLM).
- > 80% of user time saved vs manual renaming.
- < 2 s processing latency for digital PDFs (local).
- < 10 s OCR latency per scanned PDF (with smart OCR skipping PDFs with text layers).
- Zero PDF content persisted on servers.
- PDF preview enables quick verification before download.
- Professional UI improves user confidence and adoption.
- LLM-powered classification reduces misclassification errors (e.g., DistributionStatement vs BuyContract).

---

## 12. Deliverables
| Component | Description | Owner |
|------------|--------------|--------|
| Next.js frontend | Modern split-panel UI with PDF preview, card-based file list, Inter font, brand logos | Frontend dev |
| PDF Preview Component | Canvas-based PDF viewer with navigation and zoom controls | Frontend dev |
| Confirm Dialog Component | Professional confirmation dialogs with keyboard support | Frontend dev |
| OCR worker (FastAPI) | OCR & LLM-powered text extraction API (Ollama llama3) | Backend dev |
| LLM Integration | Document classification and field extraction via Ollama | Backend dev |
| Smart OCR Logic | Skip PDFs with existing text layers for performance | Backend dev |
| Docker Container | Fully containerized OCR worker with Dockerfile | DevOps |
| VM setup scripts | Ubuntu + Python + Ollama + systemd deployment | DevOps |
| Nginx/Caddy config | Reverse proxy + TLS | DevOps |

---

## 13. Acceptance Criteria
- ✅ Upload multiple PDFs and auto-generate filenames per rules (Title Case format).
- ✅ Download files individually by clicking filename, or bulk download all files.
- ✅ Preview PDFs in right panel with page navigation and zoom controls (default 125%).
- ✅ No files uploaded to Vercel (direct browser → worker).
- ✅ OCR worker processes scanned PDFs correctly with LLM-powered classification.
- ✅ Smart OCR skips PDFs with existing text layers for faster processing.
- ✅ Temporary files deleted after processing.
- ✅ Secure communication via HTTPS and Bearer auth.
- ✅ Editable filenames before download (via Edit button).
- ✅ Professional confirmation dialogs for destructive actions (Clear All).
- ✅ Brand logos (JM and PG) displayed in header.
- ✅ Modern UI with Inter font, card-based layouts, and Slate color palette.
- ✅ Support for 8 document types including complex types like CallAndDistributionStatement.
- ✅ Filenames use Title Case format without dashes (except date separator).

---

## 14. Appendix

### Example Filenames
| Original | New Filename (v2.0) |
|-----------|---------------|
| `COMPUTERSHARE_31MAR2025.pdf` | `2025-03-31_Computershare_DividendStatement.pdf` |
| `ContractNote_Trade1234.pdf` | `2025-04-02_CommSec_BuyContract.pdf` |
| `Holding.pdf` | `2025-03-31_LinkMarketServices_HoldingStatement.pdf` |
| `Distribution Statement.pdf` | `2025-10-01_EleyGriffithsGroupMidCapFundClassA_DistributionStatement.pdf` |
| `Call and Distribution Statement.pdf` | `2025-09-15_FundName_DistributionAndCapitalCallStatement.pdf` |
| `NAV and Taxation Statement.pdf` | `2025-07-31_Vanguard_TaxStatement.pdf` |

### Example Worker Response
```json
{
  "fields": {
    "doc_type": "TaxStatement",
    "issuer": "Vanguard",
    "date_iso": "2025-07-31"
  },
  "suggested_filename": "2025-07-31_Vanguard_TaxStatement.pdf"
}
```

### UI Layout
```
┌─────────────────────────────────────────────────────────┐
│  PDFsaver                    [JM Logo] [PG Logo]      │
│  Bulk upload PDF files...                              │
│                                                         │
│  [Download] [Clear All]                                │
├──────────────────────┬──────────────────────────────────┤
│  左侧栏              │  右侧栏                        │
│  ┌────────────────┐ │  ┌──────────────────────────┐ │
│  │ Dropzone       │ │  │ PDF Preview              │ │
│  │ (Drag & Drop)  │ │  │ [Toolbar: Prev/Next/Zoom]│ │
│  └────────────────┘ │  │ [Canvas: PDF Content]   │ │
│  ┌────────────────┐ │  │                          │ │
│  │ File List      │ │  │                          │ │
│  │ (Card-based)   │ │  │                          │ │
│  │ ┌────────────┐ │ │  │                          │ │
│  │ │ Status     │ │ │  │                          │ │
│  │ │ Filename   │ │ │  │                          │ │
│  │ │ [Edit][X]  │ │ │  │                          │ │
│  │ └────────────┘ │ │  │                          │ │
│  │ ┌────────────┐ │ │  │                          │ │
│  │ │ File 2     │ │ │  │                          │ │
│  │ └────────────┘ │ │  │                          │ │
│  └────────────────┘ │  └──────────────────────────┘ │
└──────────────────────┴──────────────────────────────────┘
```

### UI Components
- **Header**: Title, description, and brand logos (JM and PG) in top right
- **Action Buttons**: Download All and Clear All buttons in top left (when files present)
- **Dropzone**: Large drag-and-drop area with visual feedback
- **File List**: Card-based list with:
  - Status badges (Ready, Processing, Needs OCR, etc.)
  - Original filename
  - Suggested filename (clickable to download)
  - Edit button for filename editing
  - Remove button
  - Click anywhere on card to preview PDF
- **PDF Preview Panel**: 
  - Toolbar with page navigation (Prev/Next) and zoom controls (-/+/125%)
  - Canvas-based PDF rendering
  - Empty state when no file selected
- **Confirm Dialog**: Professional modal dialog for destructive actions
  - Keyboard support (ESC to cancel, Enter to confirm)
  - Focus management
  - Backdrop blur effect
