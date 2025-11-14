"""
PDFsaver OCR Worker
FastAPI service for OCR processing of scanned PDFs
"""

import os
import re
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import fitz  # PyMuPDF
import ocrmypdf
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# LLM helper (optional)
try:
    from llm_helper import extract_with_llm, suggest_filename_with_llm, check_ollama_available
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    extract_with_llm = None
    suggest_filename_with_llm = None
    check_ollama_available = lambda: False

app = FastAPI(title="PDFsaver OCR Worker", version="1.0.0")

# CORS configuration
ALLOW_ORIGIN = os.getenv("ALLOW_ORIGIN", "http://localhost:3000")
OCR_TOKEN = os.getenv("OCR_TOKEN", "change-me")

# CORS middleware - allow all origins in development
# We still require a Bearer token for auth, so origins are not security-critical here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (dev-friendly)
    allow_credentials=False,  # we don't use cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Pydantic models
class OCRResponse(BaseModel):
    has_text: bool
    ocred: bool
    pages_used: int
    fields: Dict[str, Optional[str]]
    suggested_filename: str


class HealthResponse(BaseModel):
    status: str


# Auth dependency
async def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        if token != OCR_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    return token


# Rules (mirroring TypeScript rules)
DOC_TYPE_PATTERNS = {
    "DividendStatement": {
        "must": ["Dividend statement"],
        "hints": ["Record Date", "Payment Date", "DRP", "Dividend Reinvestment", "Dividend"]
    },
    "DistributionStatement": {
        "must": ["Distribution statement", "Distribution Advice", "Distribution Payment"],
        "hints": ["Distribution", "Payment date", "Record date", "ETF", "Managed Fund"]
    },
    "PeriodicStatement": {
        "must": ["Periodic Statement"],
        "hints": ["Transactions", "Unit Balance", "Redemption Price", "Buy-Sell Spread", "Fees and Costs"]
    },
    "BankStatement": {
        "must": ["Bank Statement", "Account Statement", "Statement of Account"],
        "hints": ["Account Number", "BSB", "Transaction", "Balance", "Bank"]
    },
    "BuyContract": {
        "must": ["CONTRACT NOTE", "BUY"],
        "hints": ["Purchase", "Acquisition", "Buy Order"]
    },
    "SellContract": {
        "must": ["CONTRACT NOTE", "SELL"],
        "hints": ["Sale", "Disposal", "Sell Order"]
    },
    "HoldingStatement": {
        "must": ["CHESS", "Issuer Sponsored", "SRN", "HIN"],
        "hints": ["Holder Identification Number", "Statement Date", "Holdings", "Portfolio"]
    },
    "TaxStatement": {
        "must": ["Annual Tax Statement", "Tax Summary", "AMMA", "AMIT"],
        "hints": ["Tax Year", "Assessable Income", "Tax Return"]
    }
}

ISSUERS = {
    "canonical": [
        "Computershare",
        "Link Market Services",
        "Automic",
        "BoardRoom",
        "CommSec",
        "CMC Markets",
        "nabtrade",
        "Bell Potter",
        "Vanguard",
        "iShares",
        "BlackRock",
        "Betashares",
        "Magellan"
    ],
    "normalize": {
        "Computershare Limited": "Computershare",
        "Link Market Services Limited": "Link Market Services",
        "CMC Markets Stockbroking": "CMC Markets",
        "Bell Potter Securities": "Bell Potter",
        "BlackRock Investment Management": "BlackRock",
        "iShares by BlackRock": "iShares"
    }
}

DATE_PRIORITIES = {
    "DividendStatement": ["Payment Date", "Record Date", "Statement Date", "Date"],
    "DistributionStatement": ["Payment Date", "Record Date", "Distribution Date", "Statement Date", "Date"],
    "PeriodicStatement": ["Statement Date", "Period End", "Date"],
    "BankStatement": ["Statement Date", "Period End", "Date"],
    "BuyContract": ["Trade Date", "Settlement Date", "Statement Date", "Date"],
    "SellContract": ["Trade Date", "Settlement Date", "Statement Date", "Date"],
    "HoldingStatement": ["Statement Date", "Date"],
    "TaxStatement": ["Statement Date", "Tax Year", "Date"]
}

ACCOUNT_PATTERNS = [
    r"(?i)(?:HIN|SRN|Account|Holder(?:\s+ID)?)[:\s]*([A-Z0-9-]{6,})",
    r"(?i)(?:Account\s+Number|Account\s+No\.?)[:\s]*([A-Z0-9-]{6,})"
]


def classify_doc_type(text: str) -> Tuple[Optional[str], int]:
    """Classify document type and return confidence score"""
    upper_text = text.upper()
    best_match = None
    best_score = 0
    
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        score = 0
        must_matches = [m for m in patterns["must"] if m.upper() in upper_text]
        hint_matches = [h for h in patterns["hints"] if h.upper() in upper_text]
        
        if len(must_matches) == len(patterns["must"]):
            score = 80 + len(hint_matches) * 5
        elif len(must_matches) > 0:
            score = 50 + len(hint_matches) * 5
        elif len(hint_matches) > 0:
            score = 30 + len(hint_matches) * 5
        
        if score > 0 and score > best_score:
            best_match = doc_type
            best_score = score
    
    return best_match, best_score


def detect_issuer(text: str) -> Optional[str]:
    """Detect issuer from text"""
    upper_text = text.upper()
    
    # Check normalized variants
    for variant, canonical in ISSUERS["normalize"].items():
        if variant.upper() in upper_text:
            return canonical
    
    # Check canonical names
    for issuer in ISSUERS["canonical"]:
        if issuer.upper() in upper_text:
            return issuer
    
    return None


def extract_date(text: str, doc_type: Optional[str]) -> Optional[str]:
    """Extract date from text"""
    if not doc_type:
        return extract_generic_date(text)
    
    priorities = DATE_PRIORITIES.get(doc_type, ["Date"])
    
    for label in priorities:
        date = extract_labeled_date(text, label)
        if date:
            return date
    
    return extract_generic_date(text)


def extract_labeled_date(text: str, label: str) -> Optional[str]:
    """Extract date with specific label"""
    pattern = rf"(?i){re.escape(label)}[:\s]+(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}|\d{{4}}[/-]\d{{1,2}}[/-]\d{{1,2}}|\d{{1,2}}\s+\w+\s+\d{{4}})"
    match = re.search(pattern, text)
    if match:
        return parse_date(match.group(1))
    return None


def extract_generic_date(text: str) -> Optional[str]:
    """Extract generic date from text"""
    patterns = [
        r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
        r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b",
        r"\b(\d{1,2}\s+\w+\s+\d{4})\b"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed
    
    return None


def parse_date(date_str: str) -> Optional[str]:
    """Parse date string to ISO format (YYYY-MM-DD)"""
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%d %b %Y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def extract_account_last4(text: str) -> Optional[str]:
    """Extract account number (last 4 digits)"""
    for pattern in ACCOUNT_PATTERNS:
        match = re.search(pattern, text)
        if match and match.group(1):
            account = re.sub(r"[^A-Z0-9]", "", match.group(1))
            if len(account) >= 4:
                return account[-4:]
    return None


def slugify(text: Optional[str]) -> str:
    """Convert string to URL-friendly slug"""
    if not text:
        return "unknown"
    return re.sub(r"[^\w\s-]", "", text.lower()).replace(" ", "-").replace("-+", "-").strip("-")


def build_filename(fields: Dict[str, Optional[str]]) -> str:
    """Build suggested filename from detected fields"""
    parts = []
    
    # Date
    if fields.get("date_iso"):
        parts.append(fields["date_iso"])
    else:
        parts.append("YYYY-MM-DD")
    
    # Issuer slug
    issuer_slug = slugify(fields.get("issuer"))
    parts.append(issuer_slug)
    
    # Document type
    doc_type = fields.get("doc_type", "unknown")
    doc_type_slug = slugify(doc_type.replace("Statement", "").replace("Contract", ""))
    parts.append(doc_type_slug)
    
    # Account last 4
    if fields.get("account_last4"):
        parts.append(fields["account_last4"])
    else:
        parts.append("XXXX")
    
    return f"{'_'.join(parts)}.pdf"


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    status = {"status": "ok"}
    if LLM_AVAILABLE:
        status["llm_available"] = check_ollama_available()
        if status["llm_available"]:
            status["llm_model"] = os.getenv("OLLAMA_MODEL", "llama3")
    return status


@app.post("/v1/ocr-extract", response_model=OCRResponse)
async def ocr_extract(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    Process PDF file with OCR if needed
    Returns extracted fields and suggested filename
    """
    # Manual token verification
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        if token != OCR_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_dir = tempfile.mkdtemp()
    temp_input = os.path.join(temp_dir, "input.pdf")
    temp_output = os.path.join(temp_dir, "output.pdf")
    
    try:
        # Save uploaded file
        with open(temp_input, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Always run OCR for all PDFs (force OCR and LLM processing)
        pages_to_check = min(3, len(fitz.open(temp_input)))
        fitz.open(temp_input).close()
        
        ocred = False
        text_content = ""
        
        # Always run OCR on all PDFs
        try:
            ocrmypdf.ocr(
                temp_input,
                temp_output,
                rotate_pages=True,
                deskew=True,
                clean=True,
                optimize=3,
                language="eng",
                force_ocr=True  # Force OCR even if text layer exists
            )
            ocred = True
            
            # Extract text from OCR'd PDF
            doc = fitz.open(temp_output)
            for page_num in range(pages_to_check):
                page = doc[page_num]
                text_content += page.get_text() + "\n"
            doc.close()
        except Exception as e:
            # If OCR fails, try to extract what we can from original
            print(f"OCR failed, trying original text: {e}")
            doc = fitz.open(temp_input)
            for page_num in range(pages_to_check):
                page = doc[page_num]
                text_content += page.get_text() + "\n"
            doc.close()
        
        # Check if we got text (for has_text flag)
        has_text_layer = len(text_content.strip()) >= 50
        
        # Always use LLM for classification and extraction if available
        fields = {
            "doc_type": None,
            "issuer": None,
            "asx_code": None,
            "date_iso": None,
            "account_last4": None
        }
        
        # Primary: Use LLM for all PDFs if available
        if LLM_AVAILABLE and extract_with_llm:
            llm_fields = extract_with_llm(text_content)
            if llm_fields:
                fields.update(llm_fields)
        
        # Fallback: Use rule-based approach if LLM not available or failed
        if not fields["doc_type"] or not fields["issuer"]:
            doc_type, confidence = classify_doc_type(text_content)
            issuer = detect_issuer(text_content)
            date_iso = extract_date(text_content, doc_type)
            account_last4 = extract_account_last4(text_content)
            
            # Extract ASX code from text if not provided by LLM
            if not fields["asx_code"]:
                asx_match = re.search(r'\b(?:ASX\s+Code|Code)[:\s]+([A-Z]{3,6})\b', text_content, re.IGNORECASE)
                if asx_match:
                    fields["asx_code"] = asx_match.group(1).upper()
            
            # Fill in missing fields from rule-based extraction
            if not fields["doc_type"]:
                fields["doc_type"] = doc_type
            if not fields["issuer"]:
                fields["issuer"] = issuer
            if not fields["date_iso"]:
                fields["date_iso"] = date_iso
            if not fields["account_last4"]:
                fields["account_last4"] = account_last4
        
        # Build filename - always try LLM first if available (with full text context)
        suggested_filename = None
        if LLM_AVAILABLE and suggest_filename_with_llm:
            # Pass more context to LLM for better filename generation (use more text to capture fund names)
            # Use first 5000 chars to ensure we capture fund names that might be further down in the document
            suggested_filename = suggest_filename_with_llm(fields, text_content[:5000])
        
        # Fallback to rule-based filename if LLM didn't provide one
        if not suggested_filename:
            suggested_filename = build_filename(fields)
        
        # Ensure response only includes expected fields (remove asx_code from response if needed)
        response_fields = {
            "doc_type": fields.get("doc_type"),
            "issuer": fields.get("issuer"),
            "date_iso": fields.get("date_iso"),
            "account_last4": fields.get("account_last4"),
            "asx_code": fields.get("asx_code")  # Include ASX code in response
        }
        
        return OCRResponse(
            has_text=has_text_layer,
            ocred=ocred,
            pages_used=pages_to_check,
            fields=response_fields,
            suggested_filename=suggested_filename
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8123)

