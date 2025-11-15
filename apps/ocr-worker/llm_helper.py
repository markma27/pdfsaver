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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")  # Default model
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
  "doc_type": "DividendStatement|DistributionStatement|CallAndDistributionStatement|PeriodicStatement|BankStatement|BuyContract|SellContract|HoldingStatement|TaxStatement|NetAssetSummaryStatement|Other|null",
  "issuer": "fund/product/company name (NOT investor name) or null",
  "asx_code": "ASX code (e.g., BAOR, AAA) or null",
  "date_iso": "YYYY-MM-DD or null",
  "account_last4": "last 4 digits or null"
}}

CRITICAL: Extract information ONLY from THIS document. Do NOT use information from previous documents.

Important:
- "issuer" should be the FUND/PRODUCT/COMPANY name from THIS document (extract from document text)
  * For BuyContract/SellContract: CRITICAL - Extract the INVESTMENT/SECURITY name being bought/sold. Look for fields like:
    - "Security Description:", "Investment:", "Security:", "Code:", "Description:", "Name:"
    - The main investment/security name in transaction details (e.g., "Insurance Australia Group Ltd", "Scentre Group Trust 1", "BRAMBLES LIMITED", "BGF EUPN SPEC SI")
    - Extract the COMPANY/TRUST/FUND name, NOT the broker name (e.g., "JBWere", "CommSec") or investor name
    - Remove technical details like "FRN", "Callable", "Matures" dates, coupon rates unless essential
    - Use the main company/trust name (e.g., "Insurance Australia Group" not "Insurance Australia Group Ltd FRN 3MBBSW...")
  * For other document types: Extract the fund/product/company name
- Do NOT use investor/account holder names
- Do NOT use broker names for BuyContract/SellContract
- "asx_code" is the ASX stock code if available in THIS document (e.g., "BXB", "XRO", "REA")
- For bank statements, "issuer" is the bank name
- "date_iso" should be extracted from THIS document using these priorities:
  * For DividendStatement: Use "Payment Date" first, then "Record Date", then "Statement Date"
  * For DistributionStatement: Use "Payment Date" first, then "Record Date", then "Distribution Date"
  * For BuyContract/SellContract: Use "Confirmation Date" first (e.g., "Confirmation date: 11/07/2025" → "2025-07-11"), then "Transaction Date", then "Trade Date", then "Settlement Date", then "As at Date"
  * For other types: Use "Statement Date" or document date
  * Format: YYYY-MM-DD (e.g., if you see "15/05/2024" or "15 May 2024", convert to "2024-05-15")
  * IMPORTANT: Dates in DD/MM/YYYY format (Australian format) - day is first, month is second
- "account_last4" should be the investor number or account last 4 digits from THIS document

Document types:
- DividendStatement: Dividend payment statements
- DistributionStatement: Distribution advice/payment statements (ETFs, managed funds). Look for "DISTRIBUTION STATEMENT", "Distribution Statement", "Distribution Advice", "Distribution Payment", "Distribution Rate", "Holding Balance", "Gross Distribution", "Net Distribution". CRITICAL: Do NOT confuse with BuyContract - Distribution Statements are about fund distributions/payments, NOT purchases. If you see "CONFIRMATION" + "BUY", it is ALWAYS BuyContract, NEVER DistributionStatement, even if the investment name contains "FUND" or "ETF"
- PeriodicStatement: Periodic statements showing transactions, balances, fees (managed funds)
- BankStatement: Bank account statements from banks showing account balances, transactions, deposits, withdrawals. Look for "Bank Statement" in the title. CRITICAL: Do NOT classify as BankStatement if you see "CONFIRMATION", "CONTRACT NOTE", "BUY", "SELL", "Trade", "Brokerage", or "Consideration" - these indicate trade confirmations, NOT bank statements
- BuyContract: Buy confirmations, trade confirmations for purchases, contract notes showing BUY transactions. Look for "CONFIRMATION" (most common), "BUY CONFIRMATION", "CONTRACT NOTE", "We have bought", "Transaction Type: BUY", "Consideration", "Brokerage", "Trade Date", "Settlement Date", "Confirmation Date". CRITICAL: Documents with "CONFIRMATION" in the title AND "BUY" are ALWAYS BuyContract, NOT BankStatement. Even if they mention "Account" or "Account Number", if it's a confirmation document with BUY, it's a BuyContract
- SellContract: Sell confirmations, trade confirmations for sales, contract notes showing SELL transactions. Look for "SELL CONFIRMATION", "Sell Confirmation", "Trade Confirmation", "We have sold", "Transaction Type: SELL"
- HoldingStatement: Shareholding statements showing holdings/portfolio (CHESS, HIN, SRN, Portfolio Summary, Holdings Summary). Look for "CHESS", "HIN", "SRN", "Holdings", "Portfolio", "Shareholding Statement", "NAV statement", "Fund Performance", "Shareholder Value", "Shareholder Activity". CRITICAL: Do NOT classify as HoldingStatement if you see "CONFIRMATION", "CONTRACT NOTE", "BUY", "SELL", "Trade", "Brokerage", or "Consideration" - these indicate trade confirmations (BuyContract/SellContract), NOT holding statements
- TaxStatement: Tax-related statements. Look for "Tax Statement", "Tax Summary", "AMMA", "AMIT", "Taxation Statement", "NAV & Taxation Statement", "Tax Year", "Assessable Income", "Tax Return", "Tax Withheld", "Tax Payable". IMPORTANT: "NAV & Taxation Statement" is a TaxStatement, NOT a HoldingStatement or NetAssetSummaryStatement
- NetAssetSummaryStatement: Net Asset Value (NAV) summaries showing asset values, unit prices, net asset values WITHOUT tax information. Look for "Net Asset Summary", "NAV Summary", "NAV statement", "NAV Statement", "Net Asset Value", "Unit Price", "Asset Summary", "Fund Performance", "Shareholder Value", "Shareholder Activity", "Opening Balance", "Closing Balance". CRITICAL: Documents with "NAV statement" or "Fund Performance" are ALWAYS NetAssetSummaryStatement or HoldingStatement, NEVER BankStatement. IMPORTANT: This is different from "NAV & Taxation Statement" which is a TaxStatement. If the document shows both NAV and tax information, it's a TaxStatement. If it only shows NAV/asset values without tax details, it's a NetAssetSummaryStatement
- CallAndDistributionStatement: Call and Distribution Statements combining capital calls with distributions. Look for "Call and Distribution Statement", "Dist and Capital Call", "Distribution and Capital Call", "Capital Call", "Notional Capital Call", "Called Capital", "Uncalled Committed Capital" combined with distribution information
- Other: Other financial documents

CRITICAL: When classifying documents (PRIORITY ORDER):
1. **BuyContract has HIGHEST PRIORITY** - If you see "CONFIRMATION" (or "CONTRACT NOTE") AND "BUY" (or "We have bought" or "Has bought"), it is ALWAYS a BuyContract, regardless of other keywords like "FUND", "ETF", "Distribution", etc.
   - BuyContract documents often contain investment names with "FUND" or "ETF" (e.g., "AORIS INT FUND", "ETF"), but these are the SECURITIES being bought, NOT distribution statements
   - BuyContract documents may mention "Account No." but these refer to trading accounts, NOT bank accounts
   - BuyContract requires clear purchase/transaction indicators: "CONFIRMATION" + "BUY", "We have bought", "Has bought", "Consideration", "Brokerage"
   - CRITICAL: Even if the investment name contains "FUND" or "ETF", if the document says "CONFIRMATION" + "BUY", it is ALWAYS BuyContract, NEVER DistributionStatement
2. **CallAndDistributionStatement** - "Call and Distribution Statement" or "Dist and Capital Call" combined with distribution information
3. **DistributionStatement** - "DISTRIBUTION STATEMENT" in the title, but ONLY if NOT a BuyContract (no "CONFIRMATION" + "BUY")
   - Do NOT classify as DistributionStatement if you see "CONFIRMATION" + "BUY" - that's a BuyContract
   - Distribution Statements are about fund distributions/payments, NOT purchases
4. Other types follow normal rules

Additional rules:
- Do NOT classify as BuyContract just because the word "BUY" appears in other contexts (e.g., "Buy-Sell Spread" in fund statements)
- Do NOT classify as HoldingStatement if you see "CONFIRMATION", "CONTRACT NOTE", "BUY", "SELL", "Trade", "Brokerage", or "Consideration" - these indicate BuyContract/SellContract
- BankStatement requires "Bank Statement" in the title AND bank-specific indicators like "BSB", "Bank Account", "Banking"
- If you see "CONFIRMATION", "CONTRACT NOTE", "Brokerage", or "Consideration", it is NEVER a BankStatement
- If you see "NAV statement", "NAV Statement", "Fund Performance", "Shareholder Value", or "Shareholder Activity", it is ALWAYS NetAssetSummaryStatement or HoldingStatement, NEVER BankStatement
- "Net Asset Summary" or "NAV Summary" WITHOUT tax information = NetAssetSummaryStatement
- "NAV & Taxation Statement" or documents with both NAV and tax information = TaxStatement

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


def extract_and_suggest_filename_with_llm(text: str, max_chars: int = 4000) -> Optional[Dict[str, Any]]:
    """
    Combined LLM call: Extract fields AND suggest filename in one request
    This reduces HTTP overhead and improves speed
    Returns dict with fields and suggested_filename, or None if LLM unavailable
    """
    if not USE_LLM or not check_ollama_available():
        return None
    
    # Truncate text to avoid token limits
    text_sample = text[:max_chars] if len(text) > max_chars else text
    
    prompt = f"""Analyze this Australian financial document text and extract key information AND suggest a filename. Return ONLY a valid JSON object with these exact fields:
{{
  "doc_type": "DividendStatement|DistributionStatement|CallAndDistributionStatement|PeriodicStatement|BankStatement|BuyContract|SellContract|HoldingStatement|TaxStatement|NetAssetSummaryStatement|Other|null",
  "issuer": "fund/product/company name (NOT investor name) or null",
  "asx_code": "ASX code (e.g., BAOR, AAA) or null",
  "date_iso": "YYYY-MM-DD or null",
  "account_last4": "last 4 digits or null",
  "suggested_filename": "YYYY-MM-DD_[fund-product-slug]_document-type.pdf or null"
}}

CRITICAL: Extract information ONLY from THIS document. Do NOT use information from previous documents.

Important:
- "issuer" should be the FUND/PRODUCT/COMPANY name from THIS document (extract from document text)
  * For BuyContract/SellContract: CRITICAL - Extract the INVESTMENT/SECURITY name being bought/sold. Look for fields like:
    - "Security Description:", "Investment:", "Security:", "Code:", "Description:", "Name:"
    - The main investment/security name in transaction details (e.g., "Insurance Australia Group Ltd", "Scentre Group Trust 1", "BRAMBLES LIMITED", "BGF EUPN SPEC SI")
    - Extract the COMPANY/TRUST/FUND name, NOT the broker name (e.g., "JBWere", "CommSec") or investor name
    - Remove technical details like "FRN", "Callable", "Matures" dates, coupon rates unless essential
    - Use the main company/trust name (e.g., "Insurance Australia Group" not "Insurance Australia Group Ltd FRN 3MBBSW...")
  * For other document types: Extract the fund/product/company name
- Do NOT use investor/account holder names
- Do NOT use broker names for BuyContract/SellContract
- "asx_code" is the ASX stock code if available in THIS document (e.g., "BXB", "XRO", "REA")
- For bank statements, "issuer" is the bank name
- "date_iso" should be extracted from THIS document using these priorities:
  * For DividendStatement: Use "Payment Date" first, then "Record Date", then "Statement Date"
  * For DistributionStatement: Use "Payment Date" first, then "Record Date", then "Distribution Date"
  * For BuyContract/SellContract: Use "Confirmation Date" first (e.g., "Confirmation date: 11/07/2025" → "2025-07-11"), then "Transaction Date", then "Trade Date", then "Settlement Date", then "As at Date"
  * For other types: Use "Statement Date" or document date
  * Format: YYYY-MM-DD (e.g., if you see "15/05/2024" or "15 May 2024", convert to "2024-05-15")
  * IMPORTANT: Dates in DD/MM/YYYY format (Australian format) - day is first, month is second
- "account_last4" should be the investor number or account last 4 digits from THIS document
- "suggested_filename": Generate filename in format YYYY-MM-DD_[fund-product-slug]_document-type.pdf
  * Remove company suffixes: "Pty Ltd", "Limited", "Ltd" (and all variations)
  * For BuyContract/SellContract: Use investment/security name, NOT broker name
  * Do NOT include account numbers or identifiers
  * Document type: "dividend-statement", "distribution-statement", "buy-contract", "sell-contract", etc.

Document types:
- DividendStatement: Dividend payment statements
- DistributionStatement: Distribution advice/payment statements (ETFs, managed funds). Look for "DISTRIBUTION STATEMENT", "Distribution Statement", "Distribution Advice", "Distribution Payment", "Distribution Rate", "Holding Balance", "Gross Distribution", "Net Distribution". CRITICAL: Do NOT confuse with BuyContract - Distribution Statements are about fund distributions/payments, NOT purchases. If you see "CONFIRMATION" + "BUY", it is ALWAYS BuyContract, NEVER DistributionStatement, even if the investment name contains "FUND" or "ETF"
- PeriodicStatement: Periodic statements showing transactions, balances, fees (managed funds)
- BankStatement: Bank account statements from banks showing account balances, transactions, deposits, withdrawals. Look for "Bank Statement" in the title. CRITICAL: Do NOT classify as BankStatement if you see "CONFIRMATION", "CONTRACT NOTE", "BUY", "SELL", "Trade", "Brokerage", or "Consideration" - these indicate trade confirmations, NOT bank statements
- BuyContract: Buy confirmations, trade confirmations for purchases, contract notes showing BUY transactions. Look for "CONFIRMATION" (most common), "BUY CONFIRMATION", "CONTRACT NOTE", "We have bought", "Transaction Type: BUY", "Consideration", "Brokerage", "Trade Date", "Settlement Date", "Confirmation Date". CRITICAL: Documents with "CONFIRMATION" in the title AND "BUY" are ALWAYS BuyContract, NOT BankStatement. Even if they mention "Account" or "Account Number", if it's a confirmation document with BUY, it's a BuyContract
- SellContract: Sell confirmations, trade confirmations for sales, contract notes showing SELL transactions. Look for "SELL CONFIRMATION", "Sell Confirmation", "Trade Confirmation", "We have sold", "Transaction Type: SELL"
- HoldingStatement: Shareholding statements showing holdings/portfolio (CHESS, HIN, SRN, Portfolio Summary, Holdings Summary). Look for "CHESS", "HIN", "SRN", "Holdings", "Portfolio", "Shareholding Statement", "NAV statement", "Fund Performance", "Shareholder Value", "Shareholder Activity". CRITICAL: Do NOT classify as HoldingStatement if you see "CONFIRMATION", "CONTRACT NOTE", "BUY", "SELL", "Trade", "Brokerage", or "Consideration" - these indicate trade confirmations (BuyContract/SellContract), NOT holding statements
- TaxStatement: Tax-related statements. Look for "Tax Statement", "Tax Summary", "AMMA", "AMIT", "Taxation Statement", "NAV & Taxation Statement", "Tax Year", "Assessable Income", "Tax Return", "Tax Withheld", "Tax Payable". IMPORTANT: "NAV & Taxation Statement" is a TaxStatement, NOT a HoldingStatement or NetAssetSummaryStatement
- NetAssetSummaryStatement: Net Asset Value (NAV) summaries showing asset values, unit prices, net asset values WITHOUT tax information. Look for "Net Asset Summary", "NAV Summary", "NAV statement", "NAV Statement", "Net Asset Value", "Unit Price", "Asset Summary", "Fund Performance", "Shareholder Value", "Shareholder Activity", "Opening Balance", "Closing Balance". CRITICAL: Documents with "NAV statement" or "Fund Performance" are ALWAYS NetAssetSummaryStatement or HoldingStatement, NEVER BankStatement. IMPORTANT: This is different from "NAV & Taxation Statement" which is a TaxStatement. If the document shows both NAV and tax information, it's a TaxStatement. If it only shows NAV/asset values without tax details, it's a NetAssetSummaryStatement
- CallAndDistributionStatement: Call and Distribution Statements combining capital calls with distributions. Look for "Call and Distribution Statement", "Dist and Capital Call", "Distribution and Capital Call", "Capital Call", "Notional Capital Call", "Called Capital", "Uncalled Committed Capital" combined with distribution information
- Other: Other financial documents

CRITICAL: When classifying documents (PRIORITY ORDER):
1. **BuyContract has HIGHEST PRIORITY** - If you see "CONFIRMATION" (or "CONTRACT NOTE") AND "BUY" (or "We have bought" or "Has bought"), it is ALWAYS a BuyContract, regardless of other keywords like "FUND", "ETF", "Distribution", etc.
   - BuyContract documents often contain investment names with "FUND" or "ETF" (e.g., "AORIS INT FUND", "ETF"), but these are the SECURITIES being bought, NOT distribution statements
   - BuyContract documents may mention "Account No." but these refer to trading accounts, NOT bank accounts
   - BuyContract requires clear purchase/transaction indicators: "CONFIRMATION" + "BUY", "We have bought", "Has bought", "Consideration", "Brokerage"
   - CRITICAL: Even if the investment name contains "FUND" or "ETF", if the document says "CONFIRMATION" + "BUY", it is ALWAYS BuyContract, NEVER DistributionStatement
2. **CallAndDistributionStatement** - "Call and Distribution Statement" or "Dist and Capital Call" combined with distribution information
3. **DistributionStatement** - "DISTRIBUTION STATEMENT" in the title, but ONLY if NOT a BuyContract (no "CONFIRMATION" + "BUY")
   - Do NOT classify as DistributionStatement if you see "CONFIRMATION" + "BUY" - that's a BuyContract
   - Distribution Statements are about fund distributions/payments, NOT purchases
4. Other types follow normal rules

Additional rules:
- Do NOT classify as BuyContract just because the word "BUY" appears in other contexts (e.g., "Buy-Sell Spread" in fund statements)
- Do NOT classify as HoldingStatement if you see "CONFIRMATION", "CONTRACT NOTE", "BUY", "SELL", "Trade", "Brokerage", or "Consideration" - these indicate BuyContract/SellContract
- BankStatement requires "Bank Statement" in the title AND bank-specific indicators like "BSB", "Bank Account", "Banking"
- If you see "CONFIRMATION", "CONTRACT NOTE", "Brokerage", or "Consideration", it is NEVER a BankStatement
- If you see "NAV statement", "NAV Statement", "Fund Performance", "Shareholder Value", or "Shareholder Activity", it is ALWAYS NetAssetSummaryStatement or HoldingStatement, NEVER BankStatement
- "Net Asset Summary" or "NAV Summary" WITHOUT tax information = NetAssetSummaryStatement
- "NAV & Taxation Statement" or documents with both NAV and tax information = TaxStatement

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
                    "temperature": 0.1,
                    "num_predict": 300  # Increased to accommodate filename
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
                    "account_last4": extracted.get("account_last4") if extracted.get("account_last4") != "null" else None,
                    "suggested_filename": extracted.get("suggested_filename") if extracted.get("suggested_filename") != "null" else None
                }
            except json.JSONDecodeError:
                print(f"LLM JSON parsing failed: {response_text[:200]}")
                return None
    except Exception as e:
        print(f"LLM combined extraction error: {e}")
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
1. **READ THE DOCUMENT CONTEXT ABOVE CAREFULLY** - The fund/product/investment name is IN THE TEXT
2. **Extract the ACTUAL fund/product/investment name from the document context** - Look for:
   - For BuyContract/SellContract: Extract the INVESTMENT/SECURITY name being bought/sold. Look for fields like "Investment:", "Security Description:", "Code:", or the main investment name in the transaction details. Examples: "Insurance Australia Group Ltd FRN 3MBBSW...", "Scentre Group Trust 1 FRN...", "BRAMBLES LIMITED". Do NOT use broker names (e.g., "JBWere") or investor names
   - For other document types: Fund names after "Fund:", "Product:", "ETF:", or in document titles
   - The name is usually in the main transaction/investment section
   - Extract a MEANINGFUL name - for complex investments, use the main company/trust name (e.g., "Insurance Australia Group" not the full FRN description)
   - Remove technical details like "FRN", "Callable", "Matures" dates, coupon rates unless they are essential to identify the investment
3. **ALWAYS include the date** - Extract from document context using these priorities:
   - For DividendStatement: Look for "Payment Date" first (e.g., "Payment Date: 15/05/2024" → "2024-05-15"), then "Record Date", then "Statement Date"
   - For DistributionStatement: Look for "Payment Date" first, then "Record Date", then "Distribution Date"
   - For BuyContract/SellContract: Look for "Confirmation Date" first (e.g., "Confirmation date: 11/07/2025" → "2025-07-11"), then "Transaction Date", then "Trade Date", then "Settlement Date"
   - For other types: Look for "Statement Date" or document date
   - Format: YYYY-MM-DD
   - CRITICAL: Australian dates are DD/MM/YYYY format - day comes first, month second (e.g., "15/05/2024" = May 15, 2024 = "2024-05-15")
   - If date is Unknown, use "YYYY-MM-DD" as placeholder
4. **Format**: YYYY-MM-DD_[fund-product-slug]_document-type.pdf
   - Do NOT include account numbers or identifiers in the filename
5. **Convert fund name to slug**: lowercase, replace spaces with hyphens, remove special characters
   - Example: "ABC Fund Class X" → "abc-fund-class-x"
   - Remove parentheses and their contents if they are just qualifiers, but keep important class/type information
   - Remove company suffixes: "Pty Ltd", "Pty. Ltd.", "PTY LTD", "Limited", "Ltd", "Ltd." (and all variations)
   - Example: "ABC Fund Pty Ltd" → "abc-fund", "XYZ Company Pty. Ltd." → "xyz-company"
6. **Document type** (lowercase, hyphenated):
   - "dividend-statement", "distribution-statement", "periodic-statement", "bank-statement", "buy-contract", "sell-contract", "holding-statement", "tax-statement"

IMPORTANT: 
- Extract the SPECIFIC fund/product/investment name from THIS document's context - each document is different
- For BuyContract/SellContract: Use the investment/security name (e.g., "Insurance Australia Group", "Scentre Group Trust 1", "BRAMBLES LIMITED"), NOT the broker name
- Do NOT use generic company names - use the FULL fund/product/investment name
- Do NOT use investor/account holder names
- Do NOT use broker names (e.g., "JBWere", "CommSec") for BuyContract/SellContract
- Do NOT use ASX codes unless fund/investment name is completely unavailable
- Read the document context carefully to find the actual fund/product/investment name
- If the extracted fields are incomplete or incorrect, use your best judgment from the document context to generate a meaningful filename

CRITICAL: Return ONLY the filename. Do NOT include any explanation, reasoning, or additional text. Just the filename.

Example of correct response:
2025-07-25_abc-fund-class-x_distribution-statement.pdf

Example of INCORRECT response (do NOT do this):
Based on the document context, I extracted the following information: * Fund/Product Name: ABC Fund Class X * Date: 2025-07-25 Using the formatting rules, the filename should be: 2025-07-25_abc-fund-class-x_distribution-statement.pdf

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

