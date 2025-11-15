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
        check_ollama_available
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    extract_with_llm = None
    suggest_filename_with_llm = None
    extract_and_suggest_filename_with_llm = None
    check_ollama_available = lambda: False

# Learning store
try:
    from learning_store import get_learning_store
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    get_learning_store = None

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


class EditFeedbackRequest(BaseModel):
    original_filename: str
    edited_filename: str
    fields: Dict[str, Optional[str]]
    text_sample: Optional[str] = ""


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


def build_fallback_filename(fields: Dict[str, Optional[str]]) -> str:
    """
    Build a simple fallback filename if LLM is not available
    Format: YYYY-MM-DD_Unknown_Unknown.pdf
    """
    date = fields.get("date_iso") or "YYYY-MM-DD"
    issuer = fields.get("issuer") or "Unknown"
    doc_type = fields.get("doc_type") or "Unknown"
    
    # Simple slugify
    issuer_slug = issuer.lower().replace(" ", "-").replace("_", "-")
    doc_type_slug = doc_type.lower().replace(" ", "-").replace("_", "-")
    
    return f"{date}_{issuer_slug}_{doc_type_slug}.pdf"


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    status = {"status": "ok"}
    if LLM_AVAILABLE:
        status["llm_available"] = check_ollama_available()
        if status["llm_available"]:
            status["llm_model"] = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
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
    # Verify token
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
            return OCRResponse(
                has_text=has_text,
                ocred=ocred,
                pages_used=2,
                fields=cached_result["fields"],
                suggested_filename=cached_result["suggested_filename"]
            )
        
        # Initialize fields
        fields = {
            "doc_type": None,
            "issuer": None,
            "asx_code": None,
            "date_iso": None,
            "account_last4": None
        }
        suggested_filename = None
        
        # Get learning examples if available
        learning_examples = []
        if LEARNING_AVAILABLE and get_learning_store:
            learning_store = get_learning_store()
            learning_examples = learning_store.find_similar_edits(fields, text_content, max_examples=3)
            if learning_examples:
                print(f"Found {len(learning_examples)} similar edit examples for learning")
        
        # Use LLM for extraction and filename generation
        if LLM_AVAILABLE and extract_and_suggest_filename_with_llm:
            # Try combined LLM call first (faster - single HTTP request)
            combined_result = extract_and_suggest_filename_with_llm(text_content, max_chars=4000, learning_examples=learning_examples)
            if combined_result:
                fields.update({
                    "doc_type": combined_result.get("doc_type"),
                    "issuer": combined_result.get("issuer"),
                    "asx_code": combined_result.get("asx_code"),
                    "date_iso": combined_result.get("date_iso"),
                    "account_last4": combined_result.get("account_last4")
                })
                suggested_filename = combined_result.get("suggested_filename")
                print(f"LLM combined extraction successful for {file.filename}")
        
        # Fallback: Use separate LLM calls if combined call not available or failed
        if not suggested_filename and LLM_AVAILABLE:
            if extract_with_llm:
                llm_fields = extract_with_llm(text_content, max_chars=4000)
                if llm_fields:
                    fields.update(llm_fields)
                    print(f"LLM field extraction successful for {file.filename}")
            
            if suggest_filename_with_llm:
                llm_filename = suggest_filename_with_llm(fields, text_content[:4000], learning_examples=learning_examples)
                if llm_filename:
                    suggested_filename = llm_filename
                    print(f"LLM filename generation successful for {file.filename}")
        
        # Final fallback: Build simple filename if LLM not available or failed
        if not suggested_filename:
            suggested_filename = build_fallback_filename(fields)
            print(f"Using fallback filename for {file.filename}")
        
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


@app.post("/v1/learn-edit")
async def learn_edit(
    request: EditFeedbackRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Learn from user filename edits
    Stores the edit pattern for future similar documents
    """
    # Verify token
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
    
    if not LEARNING_AVAILABLE or not get_learning_store:
        raise HTTPException(status_code=503, detail="Learning store not available")
    
    try:
        learning_store = get_learning_store()
        learning_store.add_edit(
            original_filename=request.original_filename,
            edited_filename=request.edited_filename,
            fields=request.fields,
            text_sample=request.text_sample or ""
        )
        return {"status": "success", "message": "Edit pattern learned"}
    except Exception as e:
        print(f"Learning store error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to learn edit: {str(e)}")


if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8123)
