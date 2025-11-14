# PDFsaver — Product Requirements Document (PRD)
**Version:** v1.0  
**Author:** Mark Ma (Jaquillard Minns)  
**Date:** YYYY-MM-DD

---

## 1. Overview
PDFsaver automates the manual task of downloading, renaming, and organizing investment-related PDF documents (dividend statements, contract notes, holding statements, tax statements, etc.).  
The goal is to let users drag and drop documents (or forward them via email in later versions), automatically extract key fields, and produce consistently named files ready for download or upload to SharePoint.

The MVP focuses on **automated renaming of digital (text) PDFs** entirely in the browser for privacy and speed, with an **optional OCR worker** to handle scanned documents.

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
| Accountant / Admin | I can drag and drop multiple PDF statements to the web app and receive renamed versions following firm naming conventions. |
| Accountant | If a file is scanned (no text layer), the app tells me it needs OCR and optionally processes it via the OCR worker. |
| Manager | I can bulk download all renamed PDFs as a single ZIP archive. |
| IT Admin | I can deploy a local OCR worker VM (FastAPI) to process scanned PDFs privately. |
| Future (SaaS) | I can forward emails with attachments to a unique inbox, and documents automatically appear in the portal ready for review. |

---

## 4. Scope

### In Scope (MVP)
- Web app (Next.js on Vercel) for local PDF text extraction, renaming, and ZIP download.
- Bulk upload of PDFs (10–50 files typical, up to 25 MB each).
- Filename convention engine using regex + keyword rules:
  ```
  {date}_{issuer}_{doc_type}_{account_last4}.pdf
  ```
- Client-side text parsing (pdf.js) for digital PDFs.
- Detection of scanned PDFs (no text layer).
- Integration with external OCR worker via API for scanned files.
- Download renamed files individually or as ZIP.

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
   ├─ Detect: text found → rename locally
   └─ No text → POST file → [OCR Worker VM]

[OCR Worker VM]
   ├─ FastAPI + Tesseract + OCRmyPDF
   ├─ Extract text from scanned PDFs
   ├─ Apply same rules → suggest filename
   ├─ Return JSON { fields, suggested_filename }
   └─ (Optional) /v1/ocr-pdf endpoint returns OCR’d PDF

[Vercel Hosting]
   ├─ Static Next.js site (no file storage)
   ├─ Environment vars for OCR endpoint
   └─ Optional tiny API for pre-signed tokens or short-lived auth
```

---

## 6. Functional Requirements

### 6.1 File Processing
- Allow drag-drop or file picker upload (multiple PDFs).
- For each file:
  1. Read first 1–3 pages using `pdfjs-dist`.
  2. Extract text; determine if it has a text layer.
  3. Run classification rules:
     - **Doc type**: DividendStatement, BuyContract, SellContract, HoldingStatement, TaxStatement.
     - **Issuer**: from dictionary (Computershare, Link Market Services, Automic, etc.).
     - **Date**: via labeled or unlabeled regex.
     - **Account last4**: via HIN/SRN/Account regex.
  4. Build filename: `YYYY-MM-DD_Issuer_DocType_XXXX.pdf`
  5. Show results in table with edit-inline filename.

### 6.2 Bulk Download
- “Download All” → generate ZIP (JSZip).
- Include optional `manifest.csv` mapping original → new name.

### 6.3 OCR Integration
- For files with no text:
  - Option A: Mark as “Needs OCR”.
  - Option B: If user enables OCR, POST file to worker:
    ```
    POST /v1/ocr-extract
    Headers: Authorization: Bearer <token>
    Body: multipart/form-data { file }
    ```
  - Worker returns:
    ```json
    {
      "ocred": true,
      "fields": {...},
      "suggested_filename": "2025-03-31_Computershare_DividendStatement_1234.pdf"
    }
    ```
- Show progress + result inline.

### 6.4 Configurable Rules
Rules defined in a YAML file (`rules.yaml`):
```yaml
types:
  DividendStatement: ["Dividend statement","Distribution statement"]
  BuyContract: ["CONTRACT NOTE","BUY"]
  SellContract: ["CONTRACT NOTE","SELL"]
  HoldingStatement: ["CHESS","Issuer Sponsored","HIN","SRN"]
  TaxStatement: ["Annual Tax Statement","Tax Summary","AMMA","AMIT"]
issuers:
  - Computershare
  - Link Market Services
  - Automic
  - BoardRoom
  - CommSec
  - CMC Markets
  - nabtrade
  - Bell Potter
  - Vanguard
  - iShares
  - Betashares
  - Magellan
```

### 6.5 Naming Logic
```
filename = {date_iso}_{slug(issuer)}_{doc_type}_{account_last4}.pdf
```
`slug()` → replace spaces/punctuation with “-”, lowercase optional.

---

## 7. Non-Functional Requirements
| Category | Requirement |
|-----------|-------------|
| **Performance** | < 2 s for digital PDFs (local); < 15 s via OCR worker. |
| **File size** | Up to 25 MB per PDF; no upload to Vercel. |
| **Security** | No files stored on Vercel; HTTPS between browser and worker. |
| **Scalability** | OCR worker horizontal scaling via Docker/VMs. |
| **Privacy** | No persistent file storage; temp files deleted after processing. |
| **Compatibility** | Chrome, Edge, Firefox (latest); desktop focus. |
| **Extensibility** | Easy to plug in SharePoint upload or new issuer rules. |

---

## 8. Deployment Plan

### Frontend (Vercel)
- **Framework:** Next.js 14 (App Router)
- **Storage:** none
- **Libraries:** pdfjs-dist, jszip, dayjs
- **Env vars:**
  - `NEXT_PUBLIC_OCR_URL=https://ocr.pdfsaver.com/v1/ocr-extract`
- **Limits:** Vercel body size limit bypassed (browser → worker direct)

### OCR Worker VM
- **Stack:** Ubuntu 22.04 + Python + FastAPI + Tesseract + OCRmyPDF
- **Ports:** 8123 (HTTP), optional 443 via Nginx/Caddy
- **Auth:** Bearer token (short-lived or static)
- **CORS:** allow `https://pdfsaver.vercel.app`
- **Docker (optional):** build + run instructions
- **File size limit:** 200 MB (`client_max_body_size 200m`)
- **Auto-start:** systemd service `pdfsaver.service`

### Domains
- Frontend: `https://pdfsaver.vercel.app`
- Worker: `https://ocr.pdfsaver.com`

---

## 9. Future Roadmap
| Version | Feature | Description |
|----------|----------|-------------|
| v1.1 | OCR worker streaming back full OCR’d PDF | Allow downloading the searchable PDF. |
| v1.2 | Email-in workflow | Users forward dividend/tax statements to unique address. |
| v1.3 | SharePoint upload | Direct browser → SharePoint folder. |
| v1.4 | Admin portal | List, review, edit, export processed documents. |
| v2.0 | SaaS multi-tenant | Auth, billing, team management, analytics. |

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
- 90% of investment-related PDFs renamed correctly without manual edits.
- > 80% of user time saved vs manual renaming.
- < 2 s processing latency for digital PDFs.
- < 15 s OCR latency per scanned PDF.
- Zero PDF content persisted on servers.

---

## 12. Deliverables
| Component | Description | Owner |
|------------|--------------|--------|
| Next.js frontend | Bulk upload, rename, ZIP download | Frontend dev |
| YAML rules file | Issuer & type detection patterns | Accounting SME |
| OCR worker (FastAPI) | OCR & text extraction API | Backend dev |
| VM setup scripts | Ubuntu + Python + systemd deployment | DevOps |
| Nginx/Caddy config | Reverse proxy + TLS | DevOps |

---

## 13. Acceptance Criteria
- ✅ Upload multiple PDFs and auto-generate filenames per rules.
- ✅ Download all renamed PDFs as ZIP within browser.
- ✅ No files uploaded to Vercel.
- ✅ OCR worker processes scanned PDFs correctly when invoked.
- ✅ Temporary files deleted after processing.
- ✅ Secure communication via HTTPS and Bearer auth.
- ✅ Editable filenames before download.

---

## 14. Appendix

### Example Filenames
| Original | New Filename |
|-----------|---------------|
| `COMPUTERSHARE_31MAR2025.pdf` | `2025-03-31_Computershare_DividendStatement_1234.pdf` |
| `ContractNote_Trade1234.pdf` | `2025-04-02_CommSec_BuyContract_5678.pdf` |
| `Holding.pdf` | `2025-03-31_LinkMarketServices_HoldingStatement_4321.pdf` |

### Example Worker Response
```json
{
  "ocred": true,
  "fields": {
    "doc_type": "TaxStatement",
    "issuer": "Vanguard",
    "date_iso": "2025-07-31",
    "account_last4": "9123"
  },
  "suggested_filename": "2025-07-31_Vanguard_TaxStatement_9123.pdf"
}
```
