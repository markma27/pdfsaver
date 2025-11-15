"""
PDFsaver OCR Worker
FastAPI service for OCR processing of scanned PDFs
Uses LLM for document classification and filename generation
"""

import os
import hashlib
import tempfile
import shutil
from typing import Optional, Dict, Any, Tuple

import fitz  # PyMuPDF  # type: ignore
import ocrmypdf  # type: ignore
from fastapi import FastAPI, File, UploadFile, HTTPException, Header  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel  # type: ignore

# LLM helper
try:
    from llm_helper import (
        extract_with_llm,
        suggest_filename_with_llm,
        extract_and_suggest_filename_with_llm,
        check_llm_available,
        check_ollama_available  # For backward compatibility
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    extract_with_llm = None
    suggest_filename_with_llm = None
    extract_and_suggest_filename_with_llm = None
    check_llm_available = lambda: False
    check_ollama_available = lambda: False

app = FastAPI(title="PDFsaver OCR Worker", version="2.0.0")

# Configuration
ALLOW_ORIGIN = os.getenv("ALLOW_ORIGIN", "http://localhost:3000")
OCR_TOKEN = os.getenv("OCR_TOKEN", "change-me")

# File cache for duplicate detection (in-memory)
_file_cache: Dict[str, Dict[str, Any]] = {}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


def check_pdf_has_text(pdf_path: str, max_pages: int = 2) -> Tuple[bool, str]:
    """
    Check if PDF has sufficient text layer
    Returns (has_text, text_content)
    """
    doc = fitz.open(pdf_path)
    text_content = ""
    has_text = False
    
    pages_to_check = min(max_pages, len(doc))
    for page_num in range(pages_to_check):
        page = doc[page_num]
        page_text = page.get_text()
        text_content += page_text + "\n"
        if len(page_text.strip()) > 100:  # Has sufficient text
            has_text = True
    
    doc.close()
    return has_text, text_content


def run_ocr(input_path: str, output_path: str) -> bool:
    """
    Run OCR on PDF file
    Returns True if successful, False otherwise
    """
    try:
        ocrmypdf.ocr(
            input_path,
            output_path,
            rotate_pages=True,
            deskew=True,
            clean=True,
            optimize=1,
            language="eng",
            force_ocr=True
        )
        return True
    except Exception as e:
        print(f"OCR failed: {e}")
        return False


def extract_text_from_pdf(pdf_path: str, max_pages: int = 2) -> str:
    """
    Extract text from PDF (first few pages)
    """
    doc = fitz.open(pdf_path)
    text_content = ""
    pages_to_check = min(max_pages, len(doc))
    
    for page_num in range(pages_to_check):
        page = doc[page_num]
        text_content += page.get_text() + "\n"
    
    doc.close()
    return text_content


def get_month_num(date_iso: str) -> str:
    """
    Get the Num based on the month of the date
    Mapping: July(07)->01, Aug(08)->02, Sep(09)->03, Oct(10)->04, Nov(11)->05, Dec(12)->06,
             Jan(01)->07, Feb(02)->08, Mar(03)->09, Apr(04)->10, May(05)->11, Jun(06)->12
    """
    if not date_iso or date_iso == "YYYY-MM-DD":
        return "00"  # Default if no date
    
    # Extract month from YYYY-MM-DD or YYYYMMDD format
    if "-" in date_iso:
        # YYYY-MM-DD format
        parts = date_iso.split("-")
        if len(parts) >= 2:
            month = int(parts[1])
        else:
            return "00"
    else:
        # YYYYMMDD format
        if len(date_iso) >= 6:
            month = int(date_iso[4:6])
        else:
            return "00"
    
    # Month to Num mapping
    month_to_num = {
        7: "01",   # July
        8: "02",   # Aug
        9: "03",   # Sep
        10: "04",  # Oct
        11: "05",  # Nov
        12: "06",  # Dec
        1: "07",   # Jan
        2: "08",   # Feb
        3: "09",   # Mar
        4: "10",   # Apr
        5: "11",   # May
        6: "12"    # Jun
    }
    
    return month_to_num.get(month, "00")


def add_num_prefix(filename: str, date_iso: Optional[str]) -> str:
    """
    Add Num prefix to filename based on the month of the date
    Format: Num YYYYMMDD - [doc-type-tag] - [issuer].pdf
    """
    if not filename:
        return filename
    
    # Try to extract date from date_iso first
    date_to_use = date_iso
    
    # If date_iso is not available or invalid, try to extract from filename
    if not date_to_use or date_to_use == "YYYY-MM-DD":
        # Try to extract YYYYMMDD from filename (format: YYYYMMDD - ... or Num YYYYMMDD - ...)
        import re
        # Look for 8 consecutive digits (YYYYMMDD)
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            date_str = date_match.group(1)
            # Convert YYYYMMDD to YYYY-MM-DD format for get_month_num
            date_to_use = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    # Extract Num based on date
    num = get_month_num(date_to_use or "")
    
    # If filename already starts with a number (Num), replace it
    # Otherwise, add Num at the beginning
    parts = filename.split(" ", 1)
    if parts[0].isdigit() and len(parts[0]) == 2:
        # Already has Num prefix, replace it
        return f"{num} {parts[1]}" if len(parts) > 1 else f"{num} {filename}"
    else:
        # Add Num prefix
        return f"{num} {filename}"


def build_fallback_filename(fields: Dict[str, Optional[str]]) -> str:
    """
    Build a simple fallback filename if LLM is not available
    Format: YYYYMMDD - [doc-type] - [issuer].pdf
    """
    date_iso = fields.get("date_iso") or "YYYY-MM-DD"
    # Convert YYYY-MM-DD to YYYYMMDD
    date = date_iso.replace("-", "") if "-" in date_iso else date_iso
    
    issuer = fields.get("issuer") or "Unknown"
    # Remove common suffixes
    issuer = issuer.replace(" Pty Ltd", "").replace(" Pty. Ltd.", "").replace(" Limited", "").replace(" Ltd", "").strip()
    
    doc_type = fields.get("doc_type") or "Unknown"
    # Convert doc_type to readable format with proper capitalization
    doc_type_map = {
        "DividendStatement": "Dividend Statement",
        "DistributionStatement": "Dist Statement",
        "CapitalCallStatement": "Cap Call",
        "CallAndDistributionStatement": "Dist And Cap Call",
        "PeriodicStatement": "Periodic Statement",
        "BankStatement": "Bank Statement",
        "BuyContract": "Buy Contract",
        "SellContract": "Sell Contract",
        "HoldingStatement": "Holding Statement",
        "TaxStatement": "Tax Statement",
        "NetAssetSummaryStatement": "Net Asset Summary Statement",
        "FinancialStatement": "Financial Statement"
    }
    doc_type_tag = doc_type_map.get(doc_type, doc_type.replace("_", " ").title())
    
    filename = f"{date} - {doc_type_tag} - {issuer}.pdf"
    # Add Num prefix
    return add_num_prefix(filename, date_iso)


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    status = {"status": "ok"}
    if LLM_AVAILABLE:
        status["llm_available"] = check_llm_available()
        if status["llm_available"]:
            llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
            if llm_provider == "deepseek":
                status["llm_provider"] = "deepseek"
                status["llm_model"] = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            elif llm_provider == "openai":
                status["llm_provider"] = "openai"
                status["llm_model"] = os.getenv("OPENAI_MODEL", "gpt-5-nano")
            else:
                status["llm_provider"] = "ollama"
                status["llm_model"] = os.getenv("OLLAMA_MODEL", "llama3")
    return status


@app.post("/v1/ocr-extract", response_model=OCRResponse)
async def ocr_extract(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    Process PDF file with OCR if needed
    Uses LLM for document classification and filename generation
    """
    # Verify token (only if OCR_TOKEN is set and not default)
    if OCR_TOKEN and OCR_TOKEN != "change-me":
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
    
    # Check file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_dir = tempfile.mkdtemp()
    temp_input = os.path.join(temp_dir, "input.pdf")
    temp_output = os.path.join(temp_dir, "output.pdf")
    
    try:
        # Save uploaded file
        with open(temp_input, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Check if PDF has text layer
        has_text_layer, initial_text = check_pdf_has_text(temp_input, max_pages=2)
        
        ocred = False
        text_content = ""
        
        if has_text_layer:
            # PDF already has text layer, use it directly
            print(f"PDF has text layer, skipping OCR for {file.filename}")
            text_content = initial_text
        else:
            # No text layer, run OCR
            print(f"PDF lacks text layer, running OCR for {file.filename}")
            if run_ocr(temp_input, temp_output):
                ocred = True
                text_content = extract_text_from_pdf(temp_output, max_pages=2)
            else:
                # OCR failed, try to use what we have
                print(f"OCR failed, using original text for {file.filename}")
                text_content = initial_text
        
        # Check if we got sufficient text
        has_text = len(text_content.strip()) >= 50
        
        # Generate file hash for caching
        file_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()[:16]
        
        # Check cache
        if file_hash in _file_cache:
            cached_result = _file_cache[file_hash]
            print(f"Cache hit for {file.filename}")
            # Add Num prefix to cached filename
            cached_filename = add_num_prefix(
                cached_result["suggested_filename"],
                cached_result["fields"].get("date_iso")
            )
            return OCRResponse(
                has_text=has_text,
                ocred=ocred,
                pages_used=2,
                fields=cached_result["fields"],
                suggested_filename=cached_filename
            )
        
        # Initialize fields
        fields = {
            "doc_type": None,
            "issuer": None,
            "date_iso": None
        }
        suggested_filename = None
        
        # Use LLM for extraction and filename generation
        if LLM_AVAILABLE and extract_and_suggest_filename_with_llm:
            # Check if LLM is actually available
            llm_available = check_llm_available()
            print(f"LLM_AVAILABLE={LLM_AVAILABLE}, check_llm_available()={llm_available} for {file.filename}")
            if llm_available:
                # Try combined LLM call first (faster - single HTTP request)
                print(f"Attempting LLM extraction for {file.filename}")
                combined_result = extract_and_suggest_filename_with_llm(text_content, max_chars=4000)
                if combined_result:
                    fields.update({
                        "doc_type": combined_result.get("doc_type"),
                        "issuer": combined_result.get("issuer"),
                        "date_iso": combined_result.get("date_iso")
                    })
                    suggested_filename = combined_result.get("suggested_filename")
                    print(f"LLM combined extraction successful for {file.filename}")
        
        # Fallback: Use separate LLM calls if combined call not available or failed
        if not suggested_filename and LLM_AVAILABLE:
            llm_available = check_llm_available()
            if llm_available and extract_with_llm:
                print(f"Attempting separate LLM field extraction for {file.filename}")
                llm_fields = extract_with_llm(text_content, max_chars=4000)
            else:
                llm_fields = None
            if llm_fields:
                fields.update(llm_fields)
                print(f"LLM field extraction successful for {file.filename}")
            
            if llm_available and suggest_filename_with_llm:
                print(f"Attempting LLM filename generation for {file.filename}")
                llm_filename = suggest_filename_with_llm(fields, text_content[:4000])
                if llm_filename:
                    suggested_filename = llm_filename
                    print(f"LLM filename generation successful for {file.filename}")
        
        # Final fallback: Build simple filename if LLM not available or failed
        if not suggested_filename:
            suggested_filename = build_fallback_filename(fields)
            print(f"Using fallback filename for {file.filename}")
        
        # Add Num prefix to filename (for both LLM-generated and fallback filenames)
        suggested_filename = add_num_prefix(suggested_filename, fields.get("date_iso"))
        
        # Cache the result
        _file_cache[file_hash] = {
            "fields": {
                "doc_type": fields.get("doc_type"),
                "issuer": fields.get("issuer"),
                "date_iso": fields.get("date_iso"),
            },
            "suggested_filename": suggested_filename
        }
        
        # Limit cache size to prevent memory issues (keep last 100 entries)
        if len(_file_cache) > 100:
            oldest_key = next(iter(_file_cache))
            del _file_cache[oldest_key]
        
        return OCRResponse(
            has_text=has_text,
            ocred=ocred,
            pages_used=2,
            fields=fields,
            suggested_filename=suggested_filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
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
    import uvicorn  # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8123)
