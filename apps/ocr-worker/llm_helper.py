"""
LLM Helper for PDFsaver OCR Worker
Uses Ollama for local LLM inference to improve document classification and field extraction
"""

import os
import json
import httpx
from typing import Optional, Dict, Any

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Default model
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"


def check_ollama_available() -> bool:
    """Check if Ollama is available"""
    if not USE_LLM:
        return False
    
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2.0)
        return response.status_code == 200
    except:
        return False


def extract_with_llm(text: str, max_chars: int = 2000) -> Optional[Dict[str, Any]]:
    """
    Use LLM to extract document fields from text
    Returns dict with doc_type, issuer, date_iso, account_last4, or None if LLM unavailable
    """
    if not USE_LLM or not check_ollama_available():
        return None
    
    # Truncate text to avoid token limits
    text_sample = text[:max_chars] if len(text) > max_chars else text
    
    prompt = f"""Analyze this Australian financial document text and extract key information. Return ONLY a valid JSON object with these exact fields:
{{
  "doc_type": "DividendStatement|DistributionStatement|PeriodicStatement|BankStatement|BuyContract|SellContract|HoldingStatement|TaxStatement|Other|null",
  "issuer": "fund/product/company name (NOT investor name) or null",
  "asx_code": "ASX code (e.g., BAOR, AAA) or null",
  "date_iso": "YYYY-MM-DD or null",
  "account_last4": "last 4 digits or null"
}}

CRITICAL: Extract information ONLY from THIS document. Do NOT use information from previous documents.

Important:
- "issuer" should be the FUND/PRODUCT/COMPANY name from THIS document (extract from document text)
- Do NOT use investor/account holder names
- "asx_code" is the ASX stock code if available in THIS document
- For bank statements, "issuer" is the bank name
- "date_iso" should be the statement date or payment date from THIS document (format: YYYY-MM-DD)
- "account_last4" should be the investor number or account last 4 digits from THIS document

Document types:
- DividendStatement: Dividend payment statements
- DistributionStatement: Distribution advice/payment statements (ETFs, managed funds)
- PeriodicStatement: Periodic statements showing transactions, balances, fees (managed funds)
- BankStatement: Bank account statements
- BuyContract: Share purchase contract notes
- SellContract: Share sale contract notes
- HoldingStatement: Shareholding statements (CHESS, HIN, SRN)
- TaxStatement: Tax statements (AMMA, AMIT, annual tax)
- Other: Other financial documents

Document text:
{text_sample}

JSON:"""

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent output
                    "num_predict": 200   # Limit response length
                }
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Try to parse JSON
            try:
                extracted = json.loads(response_text)
                # Validate and clean extracted data
                return {
                    "doc_type": extracted.get("doc_type") if extracted.get("doc_type") != "null" else None,
                    "issuer": extracted.get("issuer") if extracted.get("issuer") != "null" else None,
                    "asx_code": extracted.get("asx_code") if extracted.get("asx_code") != "null" else None,
                    "date_iso": extracted.get("date_iso") if extracted.get("date_iso") != "null" else None,
                    "account_last4": extracted.get("account_last4") if extracted.get("account_last4") != "null" else None
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract fields manually
                return None
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return None
    
    return None


def suggest_filename_with_llm(fields: Dict[str, Optional[str]], text_sample: str = "") -> Optional[str]:
    """
    Use LLM to suggest a better filename based on extracted fields and document context
    LLM has full flexibility to determine the best filename format based on document content
    """
    if not USE_LLM or not check_ollama_available():
        return None
    
    # Use more context from text for better filename generation (increase to 4000 chars to capture fund names)
    context_sample = text_sample[:4000] if text_sample else ""
    
    prompt = f"""You are helping to rename a financial document PDF file. You MUST analyze the document context below to extract the ACTUAL fund/product name from THIS specific document.

Extracted Fields (may be incomplete - verify against document context):
- Document Type: {fields.get('doc_type', 'Unknown')}
- Fund/Product/Issuer: {fields.get('issuer', 'Unknown')}
- ASX Code: {fields.get('asx_code', 'Unknown')}
- Date: {fields.get('date_iso', 'Unknown')}
- Account (last 4): {fields.get('account_last4', 'Unknown')}

FULL Document Context (read carefully):
{context_sample}

CRITICAL INSTRUCTIONS:
1. **READ THE DOCUMENT CONTEXT ABOVE CAREFULLY** - The fund/product name is IN THE TEXT
2. **Extract the ACTUAL fund/product name from the document context** - Look for:
   - Fund names after "Fund:", "Product:", "ETF:", or in document titles
   - The fund name is usually near the top of the document or in a title
   - Extract the COMPLETE fund/product name, not just the company name
   - For example, if you see "Company Name ABC Fund Class X", extract "Company Name ABC Fund Class X", not just "Company Name"
3. **ALWAYS include the date** - Extract from document context (statement date, payment date, document date)
   - Format: YYYY-MM-DD
   - If date is Unknown, use "YYYY-MM-DD" as placeholder
4. **Format**: YYYY-MM-DD_[fund-product-slug]_document-type_account-last4.pdf
5. **Convert fund name to slug**: lowercase, replace spaces with hyphens, remove special characters
   - Example: "ABC Fund Class X" → "abc-fund-class-x"
   - Remove parentheses and their contents if they are just qualifiers, but keep important class/type information
6. **Document type** (lowercase, hyphenated):
   - "dividend-statement", "distribution-statement", "periodic-statement", "bank-statement", "buy-contract", "sell-contract", "holding-statement", "tax-statement"
7. **Account**: Use last 4 digits from document, or "XXXX" if unknown

IMPORTANT: 
- Extract the SPECIFIC fund/product name from THIS document's context - each document is different
- Do NOT use generic company names - use the FULL fund/product name
- Do NOT use investor/account holder names
- Do NOT use ASX codes unless fund name is completely unavailable
- Read the document context carefully to find the actual fund/product name

CRITICAL: Return ONLY the filename. Do NOT include any explanation, reasoning, or additional text. Just the filename.

Example of correct response:
2025-07-25_abc-fund-class-x_distribution-statement_1234.pdf

Example of INCORRECT response (do NOT do this):
Based on the document context, I extracted the following information: * Fund/Product Name: ABC Fund Class X * Date: 2025-07-25 Using the formatting rules, the filename should be: 2025-07-25_abc-fund-class-x_distribution-statement_1234.pdf

Return ONLY the filename, nothing else."""

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for more focused output
                    "num_predict": 150   # Increase slightly to ensure we get the full filename
                }
            },
            timeout=15.0
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            
            # Extract filename from response - LLM might return explanation text
            # Look for the actual filename pattern: YYYY-MM-DD_*.pdf or similar
            import re
            
            # Try to find filename pattern in the response
            filename_pattern = r'(\d{4}-\d{2}-\d{2}_[^\s]+\.pdf)'
            match = re.search(filename_pattern, response_text)
            
            if match:
                filename = match.group(1)
            else:
                # If no pattern found, try to extract last line or text before common phrases
                # Remove common explanation prefixes
                filename = response_text
                # Remove explanation prefixes
                for prefix in [
                    "Based on the document context",
                    "The filename should be",
                    "Here is the filename",
                    "Filename:",
                    "The suggested filename is",
                    "I extracted",
                    "Using the format"
                ]:
                    if prefix.lower() in filename.lower():
                        # Extract text after the prefix
                        parts = filename.split(prefix, 1)
                        if len(parts) > 1:
                            filename = parts[1].strip()
                            # Remove any leading punctuation or bullets
                            filename = re.sub(r'^[:\-\*\s]+', '', filename)
                            break
                
                # Take first line if multiple lines
                filename = filename.split('\n')[0].strip()
                
                # Remove quotes and clean up
                filename = filename.replace('"', '').replace("'", "").strip()
                
                # Remove any trailing explanation text (look for common phrases)
                explanation_markers = [
                    " based on",
                    " extracted from",
                    " using the",
                    " following the",
                    " according to"
                ]
                for marker in explanation_markers:
                    idx = filename.lower().find(marker.lower())
                    if idx > 0:
                        filename = filename[:idx].strip()
                        break
            
            # Final cleanup
            filename = filename.strip()
            
            # Validate and return
            if filename.endswith('.pdf'):
                return filename
            elif '.' not in filename and len(filename) > 0:
                return f"{filename}.pdf"
            elif len(filename) == 0:
                return None
    except Exception as e:
        print(f"LLM filename suggestion error: {e}")
    
    return None

