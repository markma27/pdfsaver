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
    from llm_helper import extract_with_llm, suggest_filename_with_llm, extract_and_suggest_filename_with_llm, check_ollama_available
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    extract_with_llm = None
    suggest_filename_with_llm = None
    extract_and_suggest_filename_with_llm = None
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
        "must": ["Distribution statement", "Distribution Advice", "Distribution Payment", "DISTRIBUTION STATEMENT"],
        "hints": ["Distribution", "Payment date", "Record date", "ETF", "Managed Fund", "Distribution Rate", "Holding Balance", "Gross Distribution", "Net Distribution"]
    },
    "CallAndDistributionStatement": {
        "must": ["Call and Distribution Statement", "CALL AND DISTRIBUTION STATEMENT", "Call & Distribution Statement", "Dist and Capital Call", "DIST AND CAPITAL CALL", "Distribution and Capital Call", "DISTRIBUTION AND CAPITAL CALL"],
        "hints": ["Capital Call", "Call", "Distribution", "Net Cash Distribution", "Notional Capital Call", "Called Capital", "Uncalled Committed Capital", "Dist & Capital Call"]
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
        "must": ["BUY CONFIRMATION", "BUY", "We have bought"],
        "hints": ["Buy Confirmation", "Trade Confirmation", "Purchase", "Acquisition", "Buy Order", "CONTRACT NOTE", "We confirm the following transaction", "Transaction Type: BUY", "Consideration", "Brokerage"]
    },
    "SellContract": {
        "must": ["SELL"],
        "hints": ["Sell Confirmation", "Trade Confirmation", "Sale", "Disposal", "Sell Order", "CONTRACT NOTE", "We have sold", "We confirm the following transaction", "Transaction Type: SELL"]
    },
    "HoldingStatement": {
        "must": ["CHESS", "Issuer Sponsored", "SRN", "HIN"],
        "hints": ["Holder Identification Number", "Statement Date", "Holdings", "Portfolio"]
    },
    "TaxStatement": {
        "must": ["Annual Tax Statement", "Tax Summary", "AMMA", "AMIT", "NAV & Taxation Statement", "NAV AND TAXATION STATEMENT", "Taxation Statement", "TAXATION STATEMENT", "NAV and Taxation", "NAV AND TAXATION"],
        "hints": ["Tax Year", "Assessable Income", "Tax Return", "Taxation", "Tax Withheld", "Tax Payable"]
    },
    "NetAssetSummaryStatement": {
        "must": ["Net Asset Summary", "NET ASSET SUMMARY", "NAV Summary", "NAV SUMMARY", "Net Asset Value Summary"],
        "hints": ["Net Asset Value", "NAV", "Unit Price", "Asset Summary", "Asset Value", "Unit Balance", "Total Assets", "Total Liabilities"]
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
    "CallAndDistributionStatement": ["Statement Date", "Date"],
    "PeriodicStatement": ["Statement Date", "Period End", "Date"],
    "BankStatement": ["Statement Date", "Period End", "Date"],
    "BuyContract": ["Confirmation Date", "Transaction Date", "Trade Date", "Settlement Date", "As at Date", "Date"],
    "SellContract": ["Confirmation Date", "Transaction Date", "Trade Date", "Settlement Date", "As at Date", "Date"],
    "HoldingStatement": ["Statement Date", "Date"],
    "TaxStatement": ["Statement Date", "Tax Year", "Date"],
    "NetAssetSummaryStatement": ["Statement Date", "As at Date", "Date"]
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
    
    # Special handling: Check for "Call and Distribution Statement" FIRST (highest priority)
    # This is more specific than just "Distribution Statement"
    # Check for various forms: "Call and Distribution", "Dist and Capital Call", etc.
    is_call_and_dist = (
        "CALL AND DISTRIBUTION STATEMENT" in upper_text or 
        "CALL & DISTRIBUTION STATEMENT" in upper_text or
        "DIST AND CAPITAL CALL" in upper_text or
        "DISTRIBUTION AND CAPITAL CALL" in upper_text or
        ("CAPITAL CALL" in upper_text and "DISTRIBUTION" in upper_text and "STATEMENT" in upper_text)
    )
    if is_call_and_dist:
        call_distribution_hints = ["CAPITAL CALL", "CALL", "DISTRIBUTION", "NET CASH DISTRIBUTION", "NOTIONAL CAPITAL CALL", "CALLED CAPITAL", "UNCALLED COMMITTED CAPITAL", "DIST & CAPITAL CALL"]
        hint_count = sum(1 for hint in call_distribution_hints if hint in upper_text)
        call_distribution_score = 95 + hint_count * 5
        if call_distribution_score > best_score:
            best_match = "CallAndDistributionStatement"
            best_score = call_distribution_score
    
    # Special handling: Check for Distribution Statement (lower priority than Call and Distribution)
    # to avoid false positives with BuyContract when "BUY" appears in other contexts
    if ("DISTRIBUTION STATEMENT" in upper_text or "DISTRIBUTION ADVICE" in upper_text or "DISTRIBUTION PAYMENT" in upper_text) and best_match != "CallAndDistributionStatement":
        # Strong indicator of DistributionStatement
        distribution_hints = ["DISTRIBUTION", "PAYMENT DATE", "RECORD DATE", "DISTRIBUTION RATE", "HOLDING BALANCE", "GROSS DISTRIBUTION", "NET DISTRIBUTION"]
        hint_count = sum(1 for hint in distribution_hints if hint in upper_text)
        distribution_score = 90 + hint_count * 5
        if distribution_score > best_score:
            best_match = "DistributionStatement"
            best_score = distribution_score
    
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        # Skip if we already found CallAndDistributionStatement or DistributionStatement with high confidence
        if (best_match == "CallAndDistributionStatement" and best_score >= 95) or (best_match == "DistributionStatement" and best_score >= 90):
            continue
            
        score = 0
        must_matches = [m for m in patterns["must"] if m.upper() in upper_text]
        hint_matches = [h for h in patterns["hints"] if h.upper() in upper_text]
        
        # For BuyContract, require more specific indicators to avoid false positives
        if doc_type == "BuyContract":
            # Require at least one of: "BUY CONFIRMATION", "We have bought", or multiple strong hints
            has_buy_confirmation = "BUY CONFIRMATION" in upper_text or "WE HAVE BOUGHT" in upper_text
            strong_hints = ["BUY CONFIRMATION", "TRADE CONFIRMATION", "CONSIDERATION", "BROKERAGE", "TRANSACTION TYPE: BUY"]
            strong_hint_count = sum(1 for hint in strong_hints if hint in upper_text)
            
            if has_buy_confirmation:
                score = 85 + len(hint_matches) * 5
            elif "BUY" in upper_text and strong_hint_count >= 2:
                score = 70 + len(hint_matches) * 5
            elif "BUY" in upper_text:
                score = 40 + len(hint_matches) * 3  # Lower score for just "BUY"
        else:
            # Standard scoring for other document types
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
    # More flexible pattern to match various date formats after the label
    # Matches: "Payment Date: 15/05/2024", "Record Date 02/04/2024", etc.
    patterns = [
        rf"(?i){re.escape(label)}[:\s]+(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{4}})",  # DD/MM/YYYY or DD-MM-YYYY
        rf"(?i){re.escape(label)}[:\s]+(\d{{4}}[/-]\d{{1,2}}[/-]\d{{1,2}})",  # YYYY-MM-DD
        rf"(?i){re.escape(label)}[:\s]+(\d{{1,2}}\s+\w+\s+\d{{4}})",  # DD Month YYYY
        rf"(?i){re.escape(label)}[:\s]+(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2}})",  # DD/MM/YY (2-digit year)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed
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
    """Parse date string to ISO format (YYYY-MM-DD)
    Prioritizes Australian date format (DD/MM/YYYY) over US format (MM/DD/YYYY)
    """
    # Clean up the date string
    date_str = date_str.strip()
    
    # Try Australian format first (DD/MM/YYYY or DD-MM-YYYY) - most common in Australian financial docs
    formats = [
        "%d/%m/%Y",      # 15/05/2024 -> 2024-05-15
        "%d-%m-%Y",      # 15-05-2024 -> 2024-05-15
        "%d/%m/%y",      # 15/05/24 -> 2024-05-15 (assume 20xx for 2-digit years)
        "%d %B %Y",      # 15 May 2024 -> 2024-05-15
        "%d %b %Y",      # 15 May 2024 -> 2024-05-15
        "%Y-%m-%d",      # 2024-05-15 -> 2024-05-15 (ISO format)
        "%Y/%m/%d",      # 2024/05/15 -> 2024-05-15
        # US formats (lower priority, but included for compatibility)
        "%m/%d/%Y",      # 05/15/2024 -> 2024-05-15
        "%m-%d-%Y",      # 05-15-2024 -> 2024-05-15
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Handle 2-digit years: assume 20xx for years < 50, 19xx for years >= 50
            if fmt == "%d/%m/%y" or fmt == "%d-%m-%y":
                year = dt.year
                if year < 1950:
                    dt = dt.replace(year=year + 100)
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


def title_case(text: Optional[str]) -> str:
    """Convert string to Title Case without dashes (e.g., 'Anacacia Capital' -> 'AnacaciaCapital')"""
    if not text:
        return "Unknown"
    
    # Remove company suffixes (Pty Ltd, Limited, etc.)
    # Common variations: Pty Ltd, Pty. Ltd., PTY LTD, Limited, Ltd, Ltd.
    text = re.sub(r'\b(?:Pty\.?\s*Ltd\.?|PTY\.?\s*LTD\.?|Limited|Ltd\.?)\b', '', text, flags=re.IGNORECASE)
    
    # Clean up: remove special characters except spaces, hyphens, and alphanumeric
    text = re.sub(r"[^\w\s-]", "", text)
    
    # Split by spaces and hyphens, then capitalize each word
    words = re.split(r'[\s-]+', text)
    title_words = []
    for word in words:
        if word:
            # Capitalize first letter, lowercase the rest
            title_words.append(word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper())
    
    # Join without separators (remove dashes)
    result = ''.join(title_words)
    
    return result if result else "Unknown"


def slugify(text: Optional[str]) -> str:
    """Convert string to URL-friendly slug (kept for backward compatibility)"""
    if not text:
        return "unknown"
    
    # Remove company suffixes (Pty Ltd, Limited, etc.)
    # Common variations: Pty Ltd, Pty. Ltd., PTY LTD, Limited, Ltd, Ltd.
    text = re.sub(r'\b(?:Pty\.?\s*Ltd\.?|PTY\.?\s*LTD\.?|Limited|Ltd\.?)\b', '', text, flags=re.IGNORECASE)
    
    # Clean up and convert to slug
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = text.replace(" ", "-").replace("-+", "-").strip("-")
    
    # Remove multiple consecutive hyphens
    text = re.sub(r"-+", "-", text)
    
    return text if text else "unknown"


def build_filename(fields: Dict[str, Optional[str]]) -> str:
    """Build suggested filename from detected fields"""
    parts = []
    
    # Date
    if fields.get("date_iso"):
        parts.append(fields["date_iso"])
    else:
        parts.append("YYYY-MM-DD")
    
    # Issuer in Title Case (no dashes)
    issuer_title = title_case(fields.get("issuer"))
    parts.append(issuer_title)
    
    # Document type in Title Case (no dashes)
    doc_type = fields.get("doc_type", "unknown")
    
    # Special handling for CallAndDistributionStatement
    if doc_type == "CallAndDistributionStatement":
        doc_type_title = "DistributionAndCapitalCallStatement"
    elif doc_type == "DistributionStatement":
        doc_type_title = "DistributionStatement"
    elif doc_type == "DividendStatement":
        doc_type_title = "DividendStatement"
    elif doc_type == "BuyContract":
        doc_type_title = "BuyContract"
    elif doc_type == "SellContract":
        doc_type_title = "SellContract"
    elif doc_type == "HoldingStatement":
        doc_type_title = "HoldingStatement"
    elif doc_type == "TaxStatement":
        doc_type_title = "TaxStatement"
    elif doc_type == "BankStatement":
        doc_type_title = "BankStatement"
    elif doc_type == "PeriodicStatement":
        doc_type_title = "PeriodicStatement"
    elif doc_type == "NetAssetSummaryStatement":
        doc_type_title = "NetAssetSummaryStatement"
    else:
        # For unknown types, convert to Title Case
        doc_type_title = title_case(doc_type.replace("Statement", "").replace("Contract", ""))
    
    parts.append(doc_type_title)
    
    # Do NOT include account last 4 digits
    
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
    
    # Check file extension (case-insensitive)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_dir = tempfile.mkdtemp()
    temp_input = os.path.join(temp_dir, "input.pdf")
    temp_output = os.path.join(temp_dir, "output.pdf")
    
    try:
        # Save uploaded file
        with open(temp_input, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Smart OCR: Check if PDF has text layer first, only OCR if needed
        pages_to_check = min(2, len(fitz.open(temp_input)))  # Reduced from 3 to 2 pages
        fitz.open(temp_input).close()
        
        ocred = False
        text_content = ""
        
        # Check if PDF has sufficient text layer
        doc_initial = fitz.open(temp_input)
        has_text_layer = False
        initial_text = ""
        for page_num in range(pages_to_check):
            page = doc_initial[page_num]
            page_text = page.get_text()
            initial_text += page_text + "\n"
            if len(page_text.strip()) > 100:  # Has sufficient text
                has_text_layer = True
        doc_initial.close()
        
        if has_text_layer:
            # PDF already has text layer, skip OCR for speed
            print(f"PDF has text layer, skipping OCR for {file.filename}")
            text_content = initial_text
        else:
            # No text layer or insufficient text, run OCR
            print(f"PDF lacks text layer, running OCR for {file.filename}")
            try:
                ocrmypdf.ocr(
                    temp_input,
                    temp_output,
                    rotate_pages=True,
                    deskew=True,
                    clean=True,
                    optimize=1,  # Reduced from 3 to 1 for faster processing
                    language="eng",
                    force_ocr=True
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
                text_content = initial_text
        
        # Check if we got text (for has_text flag)
        has_text_layer = len(text_content.strip()) >= 50
        
        # Generate file hash for caching
        file_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()[:16]
        
        # Check cache first, but validate cached result
        if file_hash in _file_cache:
            cached_result = _file_cache[file_hash]
            cached_doc_type = cached_result["fields"].get("doc_type")
            cached_filename = cached_result.get("suggested_filename", "")
            
            # Validate cached result - check if CallAndDistributionStatement/DistributionStatement was incorrectly cached as BuyContract
            upper_text_check = text_content.upper()
            is_call_and_distribution_check = ("CALL AND DISTRIBUTION STATEMENT" in upper_text_check or 
                                             "CALL & DISTRIBUTION STATEMENT" in upper_text_check)
            is_distribution_statement_check = (("DISTRIBUTION STATEMENT" in upper_text_check or 
                                               "DISTRIBUTION ADVICE" in upper_text_check or 
                                               "DISTRIBUTION PAYMENT" in upper_text_check) and not is_call_and_distribution_check)
            
            if (is_call_and_distribution_check or is_distribution_statement_check) and cached_doc_type == "BuyContract":
                # Cache has wrong classification, invalidate and reprocess
                doc_type_name = "CallAndDistributionStatement" if is_call_and_distribution_check else "DistributionStatement"
                print(f"Cache invalidated - {doc_type_name} was incorrectly cached as BuyContract for {file.filename}")
                del _file_cache[file_hash]
            elif (is_call_and_distribution_check or is_distribution_statement_check) and "buy-contract" in cached_filename.lower():
                # Filename is wrong even if doc_type is correct, invalidate cache
                print(f"Cache invalidated - filename contains wrong document type for {file.filename}")
                del _file_cache[file_hash]
            else:
                # Cache is valid
                print(f"Cache hit for {file.filename}")
                return OCRResponse(
                    has_text=has_text_layer,
                    ocred=ocred,
                    pages_used=pages_to_check,
                    fields=cached_result["fields"],
                    suggested_filename=cached_result["suggested_filename"]
                )
        
        # Always use LLM for classification and extraction if available
        fields = {
            "doc_type": None,
            "issuer": None,
            "asx_code": None,
            "date_iso": None,
            "account_last4": None
        }
        suggested_filename = None
        
        # CRITICAL: Check for Call and Distribution Statement and Distribution Statement FIRST before LLM processing
        # This ensures we catch it early and prevent LLM from misclassifying
        upper_text = text_content.upper()
        is_call_and_distribution = ("CALL AND DISTRIBUTION STATEMENT" in upper_text or 
                                    "CALL & DISTRIBUTION STATEMENT" in upper_text)
        is_distribution_statement = (("DISTRIBUTION STATEMENT" in upper_text or 
                                     "DISTRIBUTION ADVICE" in upper_text or 
                                     "DISTRIBUTION PAYMENT" in upper_text) and not is_call_and_distribution)
        
        # Always use LLM for classification and extraction if available
        fields = {
            "doc_type": None,
            "issuer": None,
            "asx_code": None,
            "date_iso": None,
            "account_last4": None
        }
        suggested_filename = None
        
        # Try combined LLM call first (faster - single HTTP request)
        if LLM_AVAILABLE and extract_and_suggest_filename_with_llm:
            combined_result = extract_and_suggest_filename_with_llm(text_content, max_chars=4000)
            if combined_result:
                fields.update({
                    "doc_type": combined_result.get("doc_type"),
                    "issuer": combined_result.get("issuer"),
                    "asx_code": combined_result.get("asx_code"),
                    "date_iso": combined_result.get("date_iso"),
                    "account_last4": combined_result.get("account_last4")
                })
                suggested_filename = combined_result.get("suggested_filename")
                
                # IMMEDIATE CORRECTION: If this is clearly a Call and Distribution Statement or Distribution Statement, override LLM
                if is_call_and_distribution:
                    if fields.get("doc_type") != "CallAndDistributionStatement":
                        print(f"IMMEDIATE CORRECTION: LLM returned {fields.get('doc_type')}, forcing CallAndDistributionStatement for {file.filename}")
                    fields["doc_type"] = "CallAndDistributionStatement"
                    # Regenerate filename if it's wrong
                    if suggested_filename and ("buy-contract" in suggested_filename.lower() or "sell-contract" in suggested_filename.lower()):
                        suggested_filename = None  # Force regeneration
                elif is_distribution_statement:
                    if fields.get("doc_type") != "DistributionStatement":
                        print(f"IMMEDIATE CORRECTION: LLM returned {fields.get('doc_type')}, forcing DistributionStatement for {file.filename}")
                    fields["doc_type"] = "DistributionStatement"
                    # Regenerate filename if it's wrong
                    if suggested_filename and ("buy-contract" in suggested_filename.lower() or "sell-contract" in suggested_filename.lower()):
                        suggested_filename = None  # Force regeneration
        
        # Fallback: Use separate LLM calls if combined call not available or failed
        if not suggested_filename and LLM_AVAILABLE and extract_with_llm:
            llm_fields = extract_with_llm(text_content)
            if llm_fields:
                fields.update(llm_fields)
                # IMMEDIATE CORRECTION: If this is clearly a Call and Distribution Statement or Distribution Statement, override LLM
                if is_call_and_distribution:
                    if fields.get("doc_type") != "CallAndDistributionStatement":
                        print(f"IMMEDIATE CORRECTION: LLM returned {fields.get('doc_type')}, forcing CallAndDistributionStatement for {file.filename}")
                    fields["doc_type"] = "CallAndDistributionStatement"
                elif is_distribution_statement:
                    if fields.get("doc_type") != "DistributionStatement":
                        print(f"IMMEDIATE CORRECTION: LLM returned {fields.get('doc_type')}, forcing DistributionStatement for {file.filename}")
                    fields["doc_type"] = "DistributionStatement"
        
        # Fallback: Use rule-based approach if LLM not available or failed
        # Also re-extract date using rules if LLM date seems incorrect or missing
        doc_type, confidence = classify_doc_type(text_content)
        issuer = detect_issuer(text_content)
        rule_based_date = extract_date(text_content, doc_type or fields.get("doc_type"))
        account_last4 = extract_account_last4(text_content)
        
        # CRITICAL: Force CallAndDistributionStatement or DistributionStatement if rule-based classification detects it
        # This overrides any incorrect LLM classification
        if is_call_and_distribution:
            if doc_type == "CallAndDistributionStatement":
                # Force CallAndDistributionStatement - override LLM if it was wrong
                if fields.get("doc_type") != "CallAndDistributionStatement":
                    print(f"Force corrected doc_type from {fields.get('doc_type')} to CallAndDistributionStatement for {file.filename}")
                fields["doc_type"] = "CallAndDistributionStatement"
        elif is_distribution_statement:
            if doc_type == "DistributionStatement":
                # Force DistributionStatement - override LLM if it was wrong
                if fields.get("doc_type") != "DistributionStatement":
                    print(f"Force corrected doc_type from {fields.get('doc_type')} to DistributionStatement for {file.filename}")
                fields["doc_type"] = "DistributionStatement"
        
        # Extract ASX code from text if not provided by LLM
        if not fields["asx_code"]:
            asx_match = re.search(r'\b(?:ASX\s+Code|Code)[:\s]+([A-Z]{3,6})\b', text_content, re.IGNORECASE)
            if asx_match:
                fields["asx_code"] = asx_match.group(1).upper()
        
        # Fill in missing fields from rule-based extraction
        # But prioritize rule-based CallAndDistributionStatement/DistributionStatement over LLM BuyContract
        if not fields["doc_type"]:
            fields["doc_type"] = doc_type
        elif fields.get("doc_type") == "BuyContract" and (doc_type == "CallAndDistributionStatement" or is_call_and_distribution):
            # Rule-based says CallAndDistributionStatement, but LLM said BuyContract - trust rules
            fields["doc_type"] = "CallAndDistributionStatement"
            print(f"Corrected LLM BuyContract to CallAndDistributionStatement for {file.filename}")
            # Invalidate suggested filename if it contains wrong document type
            if suggested_filename and "buy-contract" in suggested_filename.lower():
                suggested_filename = None
        elif fields.get("doc_type") == "BuyContract" and (doc_type == "DistributionStatement" or is_distribution_statement):
            # Rule-based says DistributionStatement, but LLM said BuyContract - trust rules
            fields["doc_type"] = "DistributionStatement"
            print(f"Corrected LLM BuyContract to DistributionStatement for {file.filename}")
            # Invalidate suggested filename if it contains wrong document type
            if suggested_filename and "buy-contract" in suggested_filename.lower():
                suggested_filename = None
        elif is_call_and_distribution:
            # Final safety check: if text clearly says Call and Distribution Statement, force it
            fields["doc_type"] = "CallAndDistributionStatement"
            if suggested_filename and ("buy-contract" in suggested_filename.lower() or "sell-contract" in suggested_filename.lower()):
                suggested_filename = None
        elif is_distribution_statement:
            # Final safety check: if text clearly says Distribution Statement, force it
            fields["doc_type"] = "DistributionStatement"
            if suggested_filename and ("buy-contract" in suggested_filename.lower() or "sell-contract" in suggested_filename.lower()):
                suggested_filename = None
        
        if not fields["issuer"]:
            fields["issuer"] = issuer
        if not fields["account_last4"]:
            fields["account_last4"] = account_last4
        
        # For date: prefer rule-based extraction if LLM date is missing or seems incorrect
        # Rule-based extraction prioritizes Payment Date/Record Date which are more reliable
        if rule_based_date:
            # If LLM didn't provide a date, or if rule-based date is more recent (likely more accurate),
            # use rule-based date. For dividend statements, Payment Date is usually more relevant.
            if not fields["date_iso"]:
                fields["date_iso"] = rule_based_date
            elif fields.get("doc_type") == "DividendStatement" or fields.get("doc_type") == "DistributionStatement" or fields.get("doc_type") == "CallAndDistributionStatement" or fields.get("doc_type") == "NetAssetSummaryStatement":
                # For dividend/distribution/call-and-distribution/net-asset-summary statements, prefer rule-based date (which prioritizes Payment Date)
                fields["date_iso"] = rule_based_date
            # Otherwise, keep LLM date if it exists
        
        # Build filename
        # CRITICAL: Prioritize LLM for filename generation, but ensure Title Case format (no dashes)
        # LLM is smarter at determining document types and names, so we trust it more
        if not suggested_filename:
            # Try LLM first for all document types (LLM is smart enough)
            if LLM_AVAILABLE and suggest_filename_with_llm:
                print(f"Using LLM for filename generation: {file.filename}")
                llm_filename = suggest_filename_with_llm(fields, text_content[:4000])
                if llm_filename:
                    suggested_filename = llm_filename
        
        # Convert LLM filename to Title Case format if needed (remove dashes, ensure proper capitalization)
        if suggested_filename:
            # Check if filename needs conversion to Title Case format
            filename_no_ext = suggested_filename.replace(".pdf", "")
            needs_conversion = False
            
            # Check for old format indicators
            if " " in filename_no_ext:  # Has spaces instead of underscores
                needs_conversion = True
            elif "_" in filename_no_ext:
                parts = filename_no_ext.split("_")
                # Check if any part (except date) has dashes or is lowercase
                for i, part in enumerate(parts):
                    if i > 0:  # Skip date part (index 0)
                        if "-" in part or (part and part[0].islower()):
                            needs_conversion = True
                            break
            
            if needs_conversion:
                print(f"Converting LLM filename '{suggested_filename}' to Title Case format for {file.filename}")
                suggested_filename = build_filename(fields)
        
        # Final fallback to rule-based filename
        if not suggested_filename:
            suggested_filename = build_filename(fields)
        
        # Ensure filename is in Title Case format (no dashes except in date, use underscores not spaces)
        # Check if filename contains dashes or spaces in issuer or doc_type parts (not date)
        if suggested_filename:
            # Normalize: replace spaces with underscores first
            if " " in suggested_filename:
                suggested_filename = suggested_filename.replace(" ", "_")
            
            # Check for old format (dashes in non-date parts)
            parts = suggested_filename.replace(".pdf", "").split("_")
            needs_regeneration = False
            
            if len(parts) >= 2:
                # Check issuer part (second part) - should not have dashes
                if "-" in parts[1]:
                    print(f"Converting issuer part '{parts[1]}' (contains dashes) to Title Case format for {file.filename}")
                    needs_regeneration = True
                # Check doc_type part (third part if exists) - should not have dashes
                elif len(parts) >= 3 and "-" in parts[2]:
                    print(f"Converting doc_type part '{parts[2]}' (contains dashes) to Title Case format for {file.filename}")
                    needs_regeneration = True
            
            if needs_regeneration:
                suggested_filename = build_filename(fields)
        
        # Final safety check: if filename contains wrong document type or old format (with dashes), regenerate using rule-based
        # Also convert any LLM-generated filenames to Title Case format (no dashes)
        if suggested_filename:
            # Check for dashes in non-date parts (date starts with YYYY or 20XX)
            filename_no_ext = suggested_filename.replace(".pdf", "")
            if "_" in filename_no_ext:
                parts = filename_no_ext.split("_")
                # Check parts after date (issuer and doc_type should not have dashes)
                for i, part in enumerate(parts):
                    if i > 0 and "-" in part:  # Skip date part (index 0)
                        print(f"FINAL SAFETY CHECK: Filename '{suggested_filename}' contains dashes in part '{part}' (old format), regenerating with Title Case format for {file.filename}")
                        suggested_filename = build_filename(fields)
                        break
        
        if fields.get("doc_type") == "CallAndDistributionStatement":
            if suggested_filename and ("BuyContract" in suggested_filename or "SellContract" in suggested_filename or "buy-contract" in suggested_filename.lower() or "sell-contract" in suggested_filename.lower()):
                print(f"FINAL SAFETY CHECK: Regenerating filename - detected wrong document type '{suggested_filename}' for CallAndDistributionStatement in {file.filename}")
                suggested_filename = build_filename(fields)
            # Double check - ensure filename contains DistributionAndCapitalCallStatement (new format)
            elif suggested_filename and "DistributionAndCapitalCallStatement" not in suggested_filename:
                # If doc_type is CallAndDistributionStatement but filename doesn't match, regenerate
                print(f"FINAL SAFETY CHECK: Filename '{suggested_filename}' doesn't contain 'DistributionAndCapitalCallStatement', regenerating for {file.filename}")
                suggested_filename = build_filename(fields)
        elif fields.get("doc_type") == "DistributionStatement":
            if suggested_filename and ("BuyContract" in suggested_filename or "SellContract" in suggested_filename or "buy-contract" in suggested_filename.lower() or "sell-contract" in suggested_filename.lower()):
                print(f"FINAL SAFETY CHECK: Regenerating filename - detected wrong document type '{suggested_filename}' for DistributionStatement in {file.filename}")
                suggested_filename = build_filename(fields)
            # Double check - ensure filename contains DistributionStatement (new format, no dashes)
            elif suggested_filename and "DistributionStatement" not in suggested_filename:
                # If doc_type is DistributionStatement but filename doesn't match, regenerate
                print(f"FINAL SAFETY CHECK: Filename '{suggested_filename}' doesn't contain 'DistributionStatement', regenerating for {file.filename}")
                suggested_filename = build_filename(fields)
        
        # Cache the result
        _file_cache[file_hash] = {
            "fields": {
                "doc_type": fields.get("doc_type"),
                "issuer": fields.get("issuer"),
                "date_iso": fields.get("date_iso"),
                "account_last4": fields.get("account_last4"),
                "asx_code": fields.get("asx_code")
            },
            "suggested_filename": suggested_filename
        }
        
        # Limit cache size to prevent memory issues (keep last 100 entries)
        if len(_file_cache) > 100:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(_file_cache))
            del _file_cache[oldest_key]
        
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
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"OCR processing error: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8123)

