"""
LLM Helper for PDFsaver OCR Worker
Supports Ollama (local), DeepSeek API, and OpenAI/GPT-5 Nano API for document classification and field extraction
"""

import os
import json
import httpx  # type: ignore
from typing import Optional, Dict, Any, List

# LLM Provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # "ollama", "deepseek", or "openai"
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Default model

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # Default model

# OpenAI/GPT-5 Nano API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")  # Default model


def check_llm_available() -> bool:
    """Check if LLM is available (Ollama, DeepSeek, or OpenAI)"""
    if not USE_LLM:
        return False
    
    if LLM_PROVIDER == "deepseek":
        # Check if DeepSeek API key is configured
        return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.strip())
    elif LLM_PROVIDER == "openai":
        # Check if OpenAI API key is configured
        return bool(OPENAI_API_KEY and OPENAI_API_KEY.strip())
    else:
        # Check if Ollama is available
        try:
            response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2.0)
            return response.status_code == 200
        except:
            return False


def check_ollama_available() -> bool:
    """Check if Ollama is available (for backward compatibility)"""
    return check_llm_available() if LLM_PROVIDER == "ollama" else False


def _call_llm_api(prompt: str, max_tokens: int = 200) -> Optional[str]:
    """
    Internal function to call LLM API (Ollama, DeepSeek, or OpenAI)
    Returns the response text or None if failed
    """
    if LLM_PROVIDER == "deepseek":
        # DeepSeek API call (OpenAI-compatible)
        try:
            response = httpx.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                    "X-Data-Usage-Opt-Out": "true"  # Opt out of data retention and training
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": max_tokens
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                print(f"DeepSeek API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"DeepSeek API call error: {e}")
            return None
    elif LLM_PROVIDER == "openai":
        # OpenAI/GPT-5 Nano API call
        try:
            # GPT-5 Nano uses max_completion_tokens instead of max_tokens
            # GPT-5 Nano only supports temperature=1 (default), not 0.1
            api_payload = {
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            # Check if model is GPT-5 Nano (uses max_completion_tokens and only supports temperature=1)
            if "gpt-5" in OPENAI_MODEL.lower() or "nano" in OPENAI_MODEL.lower():
                api_payload["max_completion_tokens"] = max_tokens
                # GPT-5 Nano only supports temperature=1 (default), so don't set it
            else:
                api_payload["max_tokens"] = max_tokens
                api_payload["temperature"] = 0.1  # Other OpenAI models can use lower temperature
            
            response = httpx.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=api_payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"OpenAI API full response: {result}")
                choices = result.get("choices", [])
                print(f"OpenAI API choices count: {len(choices)}")
                if choices:
                    message = choices[0].get("message", {})
                    print(f"OpenAI API message: {message}")
                    content = message.get("content", "").strip()
                    print(f"OpenAI API response received, content length: {len(content)}")
                    if content:
                        print(f"OpenAI API response preview: {content[:200]}")
                    else:
                        print(f"OpenAI API response is empty! Full result: {result}")
                    return content
                else:
                    print(f"OpenAI API no choices in response: {result}")
                    return None
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"OpenAI API call error: {e}")
            return None
    else:
        # Ollama API call
        try:
            response = httpx.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": max_tokens
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"Ollama API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Ollama API call error: {e}")
            return None


def extract_with_llm(text: str, max_chars: int = 2000) -> Optional[Dict[str, Any]]:
    """
    Use LLM to extract document fields from text
    Returns dict with doc_type, issuer, date_iso, or None if LLM unavailable
    """
    if not USE_LLM or not check_llm_available():
        return None
    
    # Truncate text to avoid token limits
    text_sample = text[:max_chars] if len(text) > max_chars else text
    
    prompt = f"""You are analysing OCR text from an Australian financial document.

Your job: 
1. Classify the document.
2. Extract key fields.

Always follow the rules below EXACTLY.

------------------------------------------
TOP PRIORITY RULES (READ AND OBEY FIRST)
------------------------------------------
1. BuyContract: If the document contains "has bought", "bought for you", "bought for", or BOTH "CONFIRMATION" and "BUY", it is ALWAYS a BuyContract. No exceptions.
   - Look for: "BUY CONFIRMATION", "CONFIRMATION" + "BUY" box, "has bought", "bought for you", "bought for", "We have bought"
   - Example: Document with "BUY" box and "MIDSEC PTY LTD has bought for you" → ALWAYS BuyContract
   - CRITICAL: The phrase "has bought" indicates BuyContract. If you see "has bought", it is BuyContract, NOT SellContract.
2. SellContract: If the document contains "has sold", "sold for you", "sold for", or BOTH "CONFIRMATION" and "SELL" (or "Buy/Sell: SELL"), it is ALWAYS a SellContract. No exceptions.
   - Look for: "SELL CONFIRMATION", "CONFIRMATION" + "SELL" box, "has sold", "sold for you", "sold for", "We have sold"
   - CRITICAL: The phrase "has sold" indicates SellContract. If you see "has sold", it is SellContract, NOT BuyContract.
   - CRITICAL: If document says "has bought" or "bought for you" or any variation of "bought", it is BuyContract, NOT SellContract
3. NEVER use investor names, broker names, or service provider names (CommSec, JBWere, Ord Minnett, Morgan Stanley Fund Services, Computershare, Link Market Services, etc.) as issuer.
4. For Share Summary/HoldingStatement documents: Extract the ACTUAL FUND NAME from the document title (e.g., "Highwest Global Offshore Fund, Ltd."), NOT the service provider name (e.g., "Morgan Stanley Fund Services").
5. For BuyContract/SellContract: ALWAYS use "Trade Date" or "Confirmation Date" for date_iso. NEVER use "Settlement Date" - it is a FUTURE date (usually 5-7 days after trade date).
6. Only use information found IN THIS document. Ignore any previous documents.
7. Output MUST be valid JSON. No explanation, no markdown, no backticks.

------------------------------------------
OUTPUT FORMAT (EXTRACTION MODE)
------------------------------------------
Return ONLY this JSON object:

{{
  "doc_type": "DividendStatement|DistributionStatement|CapitalCallStatement|CallAndDistributionStatement|PeriodicStatement|BankStatement|BuyContract|SellContract|HoldingStatement|TaxStatement|NetAssetSummaryStatement|FinancialStatement|Other|null",
  "issuer": "fund/product/company name or null",
  "date_iso": "YYYY-MM-DD or null"
}}

------------------------------------------
DOCUMENT CLASSIFICATION RULES
------------------------------------------

BuyContract
- CRITICAL: If document contains ANY of these, it is ALWAYS BuyContract:
  * "BUY CONFIRMATION" or "CONFIRMATION" + "BUY" (in title, header, or box)
  * "has bought" or "has bought for you" or "bought for you" or "bought for"
  * "We have bought" or "We have bought for you" or "We have bought for"
  * "MIDSEC PTY LTD has bought for you" or similar broker name + "has bought"
  * "COMPANY:" field with "has bought" text nearby
  * Any phrase containing "bought" in the context of a transaction
- Keywords: "CONFIRMATION" + "BUY", "We have bought", "Contract Note", "Brokerage", "Consideration"
- Securities may include "FUND" or "ETF" — still a BuyContract if confirmation + buy exists
- If you see "CONFIRMATION" AND "BUY", it is ALWAYS BuyContract, NEVER DistributionStatement, NEVER SellContract
- CRITICAL: The phrase "has bought" indicates BuyContract. If you see "has bought", it is BuyContract, NOT SellContract.
- Examples:
  * Document with "BUY" box and "MIDSEC PTY LTD has bought for you" → BuyContract
  * Document with "BUY CONFIRMATION" title → BuyContract
  * Document with "CONFIRMATION" and "has bought" text → BuyContract
  * Document with "MIDSEC PTY LTD has bought for you" and "COMPANY: DEXUS" → BuyContract
  * Document with "MIDSEC PTY LTD has bought for you" and "MUNRO GLOBAL GROWTH FUND COMPLEX ETF" → BuyContract

SellContract
- CRITICAL: If document contains ANY of these, it is ALWAYS SellContract:
  * "SELL CONFIRMATION" or "CONFIRMATION" + "SELL" (in title, header, or box)
  * "has sold" or "has sold for you" or "sold for you" or "sold for"
  * "We have sold" or "We have sold for you" or "We have sold for"
  * "Buy/Sell: SELL" or "Buy/Sell:SELL"
  * "We confirm your SALE" or "confirm your sale"
- Keywords: "CONFIRMATION" + "SELL", "Buy/Sell: SELL", "We have sold", "We confirm your SALE", "Contract Note"
- If you see "TRADE CONFIRMATION" AND "SELL", it is ALWAYS SellContract
- CRITICAL: The phrase "has sold" indicates SellContract. If you see "has sold", it is SellContract, NOT BuyContract.
- CRITICAL: If document says "has bought" or "bought for you" or any variation of "bought", it is BuyContract, NOT SellContract
- Examples:
  * Document with "SELL" box and "We have sold" → SellContract
  * Document with "SELL CONFIRMATION" title → SellContract
  * Document with "CONFIRMATION" and "has sold" text → SellContract
  * Document with "has bought" → BuyContract (NOT SellContract, even if filename says "Sell")

DividendStatement
- Keywords: "Dividend Statement", "Dividend Payment", "Record Date", "Payment Date"

DistributionStatement
- Keywords: "Distribution Statement/Advice", "Distribution Payment", "Net Distribution"
- NOT a DistributionStatement if the document contains BUY CONFIRMATION keywords

CapitalCallStatement
- Keywords: "Capital Call", "Notice of Capital Call", "Amount Due"
- ONLY if there is NO "Distribution" content

CallAndDistributionStatement
- Document includes BOTH Capital Call AND Distribution information

HoldingStatement
- Keywords: "CHESS", "HIN", "SRN", "Holdings", "Portfolio Summary", "Shareholding Statement"
- NOT valid if trade confirmation keywords appear

BankStatement
- Keywords: "Bank Statement", account summary, BSB
- NOT a bank statement if "confirmation", "contract note", "buy", "sell", "brokerage", "consideration" appear

TaxStatement
- Keywords: "Tax Statement", "AMIT", "AMMA", "Tax Summary", "NAV & Taxation Statement"

NetAssetSummaryStatement
- Keywords: "Net Asset Summary", "NAV Summary", "Fund Performance"
- If NAV + tax info are both present → TaxStatement

FinancialStatement
- Keywords: "Financial Statements", "Financial Statement", "Directors' Report", "Directors Report", "Annual Report", "Audited Financial Statements", "Consolidated Financial Statements"
- Look for patterns like: "DIRECTORS' REPORT AND FINANCIAL STATEMENTS", "FOR THE YEAR ENDED", "Financial Statements for the year ended"
- This is a formal financial reporting document, NOT a periodic statement
- If document contains "Financial Statements" or "Directors' Report" → FinancialStatement, NOT PeriodicStatement

Other
- Everything else

------------------------------------------
ISSUER EXTRACTION RULES
------------------------------------------
Issuer must be the FUND/PRODUCT/COMPANY from THIS document.

For BuyContract/SellContract:
- CRITICAL: You MUST extract the issuer/investment name. Returning null is NOT acceptable unless the document truly has no security information.
- Extract the INVESTMENT/SECURITY name being bought/sold
- Prioritise fields in THIS ORDER:
  1. "COMPANY:" - HIGHEST PRIORITY (e.g., "COMPANY: CLEO DIAGNOSTICS LTD" → "CLEO DIAGNOSTICS LTD")
  2. "Stock Description:" - HIGH PRIORITY for trade confirmations (e.g., "Stock Description: RUSSELL 2000 INDEX ISHARES" → "RUSSELL 2000 INDEX ISHARES")
  3. "Security Description:" - PRIMARY field - Look for this in:
     * Direct format: "Security Description: PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
     * Table format: After "WE HAVE BOUGHT/SOLD THE FOLLOWING SECURITIES FOR YOU", find the table row with "Security Description" column
     * Table row example: "Quantity 25,682 Security Code CRED Security Description BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF Price 23.4603"
       → Extract "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF"
     * Table row example: "Quantity 39,260 Security Code DIFF Security Description PERPETUAL DIVERSIFIED INCOME ACTIVE ETF Price 10.1300"
       → Extract "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
     * Extract the FULL name including "ETF", "FUND", "INDEX", "ISHARES" (e.g., "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF", "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF")
     * The Security Description is usually the longest text in the table row (not Quantity, not Price, not Code)
  4. Look for security name in table rows - find the row that contains quantity, security code, and a long name (usually the investment name)
  5. "Investment:", "Security:", "Code:" followed by security name
- Remove unnecessary descriptors: "ORDINARY FULLY PAID", "FRN", "Callable", coupon details
- BUT preserve ETF/index names: Keep "INDEX", "ISHARES", "ETF", "FUND" if present (e.g., "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF" should remain complete)
- DO NOT use broker names (CommSec, JBWere, Ord Minnett, Morgan Stanley, Equity & Super, EquitySuper) or investor names
- CRITICAL: Do NOT extract legal disclaimers. If extracted name is very long (>100 chars) or contains phrases like "In Australia", "Liability", "Members", "Unless Otherwise Stated", reject it and look for actual investment name
- CRITICAL: Do NOT extract "Quantity" or other table column headers - extract the actual investment name
- CRITICAL: If you see a table with columns like "Quantity", "Security Code", "Security Description", "Price", "Consideration" - the investment name is in the "Security Description" column value

For HoldingStatement/Share Summary/NetAssetSummaryStatement:
- Extract the FUND name from the document TITLE (usually at the top of the document)
- Look for patterns like: "FUND NAME Share Summary", "FUND NAME, Ltd. Share Summary", "FUND NAME NAV Statement"
- Examples:
  * "Highwest Global Offshore Fund, Ltd. Share Summary" → "Highwest Global Offshore Fund, Ltd."
  * "ABC Investment Fund Share Summary" → "ABC Investment Fund"
  * "XYZ Fund NAV Statement" → "XYZ Fund"
- CRITICAL: Extract the ACTUAL FUND NAME, NOT the service provider name
- DO NOT use service provider names like "Morgan Stanley Fund Services", "Computershare", "Link Market Services" - these are NOT the fund name
- The fund name is usually the FIRST prominent name in the document title, before words like "Share Summary", "Statement", "NAV", etc.

For DistributionStatement/Distribution Advice:
- CRITICAL: Extract the ACTUAL FUND NAME, NOT the issuer/trustee/registry name
- Look for fund name in THIS PRIORITY ORDER:
  1. "Fund:" field - HIGHEST PRIORITY (e.g., "Fund: Ares Diversified Credit Fund - Class I" → "Ares Diversified Credit Fund - Class I")
  2. Document title/header - Look for patterns like:
     * "FUND NAME Distribution Statement"
     * "FUND NAME Distribution Advice"
     * "FUND NAME | ABN: ..." (fund name before ABN)
  3. After "Distribution Statement" or "Distribution Advice" title, look for fund name in the same section
  4. Look for fund name near "APIR Code" or fund identifiers
- Examples of CORRECT extraction:
  * "Ares Diversified Credit Fund - Class I" → "Ares Diversified Credit Fund - Class I"
  * "Causeway Wholesale Private Debt Income Fund" → "Causeway Wholesale Private Debt Income Fund"
  * "Fidante" or "AMAL CAUSEWAY TRUSTEES" → These are WRONG (these are issuers/trustees, not fund names)
- DO NOT use:
  * Issuer/Trustee names: "Fidante", "AMAL CAUSEWAY TRUSTEES", "Automic", "Computershare", "Link Market Services"
  * Registry service names: "OIF Registry Services", "Automic Registry Services"
  * Investor/recipient names
  * Document labels: "Distribution Statement", "Distribution Advice"

For DividendStatement:
- Extract the fund/product/company name from document title or main content
- Look for fund names in document headers or titles
- Look for company name near "Dividend Statement" title
- DO NOT use service provider or registry names - use the actual fund/company name

For FinancialStatement:
- Extract the COMPANY name from the document title/header
- Look for patterns like: "COMPANY NAME DIRECTORS' REPORT AND FINANCIAL STATEMENTS"
- Examples:
  * "BIOSCEPTRE INTERNATIONAL LIMITED DIRECTORS' REPORT AND FINANCIAL STATEMENTS" → "BIOSCEPTRE INTERNATIONAL LIMITED"
  * "ABC COMPANY LIMITED Financial Statements" → "ABC COMPANY LIMITED"
- Extract the FULL company name including "LIMITED", "PTY LTD", etc. (do NOT remove suffixes for Financial Statements)
- The company name is usually the FIRST prominent name in the document title, before "DIRECTORS' REPORT", "FINANCIAL STATEMENTS", etc.

For other document types:
- Extract the fund/product/company name from document title or main content
- Look for fund names in document headers or titles
- DO NOT use service provider or registry names - use the actual fund/company name

------------------------------------------
DATE EXTRACTION RULES
------------------------------------------
Output must be YYYY-MM-DD.
Document dates use AU format (DD/MM/YYYY) - CRITICAL: Day comes FIRST, then month, then year.
When you see "11/07/2025", this means: Day=11, Month=07 (July), Year=2025 → Output "2025-07-11"
DO NOT confuse with MM/DD/YYYY format - in Australian documents, the FIRST number is always the DAY.

Priority:

DividendStatement:
  Payment Date → Record Date → Statement Date

DistributionStatement:
  Payment Date → Record Date → Distribution Date

BuyContract/SellContract:
  CRITICAL: Use Trade Date or Confirmation Date, NOT Settlement Date
  Priority order:
  1. "Trade Date" - HIGHEST PRIORITY (e.g., "Trade Date: 09 May 2025" → "2025-05-09")
  2. "Confirmation Date" - HIGH PRIORITY (e.g., "Confirmation Date: 11/07/2025" → "2025-07-11")
  3. "Transaction Date" - MEDIUM PRIORITY
  4. "Date" field in confirmation section
  CRITICAL - DO NOT use:
  - "Settlement Date" - This is a FUTURE date (usually 5-7 days after trade date)
  - "ASX Settlement Date" - This is also a FUTURE date
  - "Payment Date" - Wrong field
  - Any date that is AFTER the trade/confirmation date
  CRITICAL - Date Format Conversion:
  - Australian dates are DD/MM/YYYY format (day first, month second)
  - "11/07/2025" means 11th day of July (month 07), year 2025 → "2025-07-11"
  - "15/07/2025" means 15th day of July (month 07), year 2025 → "2025-07-15"
  - DO NOT confuse DD/MM/YYYY with MM/DD/YYYY - in Australia, day comes FIRST
  Examples:
  - Document shows "Confirmation date: 11/07/2025" and "Settlement date: 15/07/2025" → Use "2025-07-11" (Confirmation Date, NOT Settlement Date)
  - Document shows "Trade Date: 09 May 2025" and "Settlement Date: 16 May 2025" → Use "2025-05-09" (Trade Date)
  - Document shows "Confirmation Date: 13 Nov 2025" and "Settlement Date: 17 Nov 2025" → Use "2025-11-13" (Confirmation Date)

FinancialStatement:
  Year End Date → "FOR THE YEAR ENDED" date → Statement Date
  Look for patterns like "FOR THE YEAR ENDED 30 JUNE 2025" → extract "2025-06-30"
  Australian date format: DD/MM/YYYY or DD MMMM YYYY (e.g., "30 June 2025" → "2025-06-30")

All others:
  Statement Date or main document date

------------------------------------------
RETURN FORMAT
------------------------------------------
Return ONLY the JSON object.

Do NOT include:
- markdown
- backticks
- commentary
- explanation
- reasoning
- extra text before or after the JSON

Document text:
{text_sample}

JSON:"""

    # GPT-5 Nano uses reasoning tokens, need more tokens for actual content
    response_text = _call_llm_api(prompt, max_tokens=2000)
    if not response_text:
        return None
    
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
            "date_iso": extracted.get("date_iso") if extracted.get("date_iso") != "null" else None
        }
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract fields manually
        print(f"LLM JSON parsing failed: {response_text[:200]}")
        return None


def extract_and_suggest_filename_with_llm(text: str, max_chars: int = 4000) -> Optional[Dict[str, Any]]:
    """
    Combined LLM call: Extract fields AND suggest filename in one request
    This reduces HTTP overhead and improves speed
    Returns dict with fields and suggested_filename, or None if LLM unavailable
    """
    if not USE_LLM or not check_llm_available():
        return None
    
    # Truncate text to avoid token limits
    text_sample = text[:max_chars] if len(text) > max_chars else text
    
    prompt = f"""You are analysing OCR text from an Australian financial document.

Your job: 
1. Classify the document.
2. Extract key fields.
3. Suggest a filename.

Always follow the rules below EXACTLY.

------------------------------------------
TOP PRIORITY RULES (READ AND OBEY FIRST)
------------------------------------------
1. BuyContract: If the document contains "has bought", "bought for you", "bought for", or BOTH "CONFIRMATION" and "BUY", it is ALWAYS a BuyContract. No exceptions.
   - Look for: "BUY CONFIRMATION", "CONFIRMATION" + "BUY" box, "has bought", "bought for you", "bought for", "We have bought"
   - Example: Document with "BUY" box and "MIDSEC PTY LTD has bought for you" → ALWAYS BuyContract
   - CRITICAL: The phrase "has bought" indicates BuyContract. If you see "has bought", it is BuyContract, NOT SellContract.
2. SellContract: If the document contains "has sold", "sold for you", "sold for", or BOTH "CONFIRMATION" and "SELL" (or "Buy/Sell: SELL"), it is ALWAYS a SellContract. No exceptions.
   - Look for: "SELL CONFIRMATION", "CONFIRMATION" + "SELL" box, "has sold", "sold for you", "sold for", "We have sold"
   - CRITICAL: The phrase "has sold" indicates SellContract. If you see "has sold", it is SellContract, NOT BuyContract.
   - CRITICAL: If document says "has bought" or "bought for you" or any variation of "bought", it is BuyContract, NOT SellContract
3. NEVER use investor names, broker names, or service provider names (CommSec, JBWere, Ord Minnett, Morgan Stanley Fund Services, Computershare, Link Market Services, etc.) as issuer.
4. For Share Summary/HoldingStatement documents: Extract the ACTUAL FUND NAME from the document title (e.g., "Highwest Global Offshore Fund, Ltd."), NOT the service provider name (e.g., "Morgan Stanley Fund Services").
5. For BuyContract/SellContract: ALWAYS use "Trade Date" or "Confirmation Date" for date_iso. NEVER use "Settlement Date" - it is a FUTURE date (usually 5-7 days after trade date).
6. Only use information found IN THIS document. Ignore any previous documents.
7. Output MUST be valid JSON. No explanation, no markdown, no backticks.

------------------------------------------
OUTPUT FORMAT (EXTRACTION + FILENAME MODE)
------------------------------------------
Return ONLY this JSON object:

{{
  "doc_type": "DividendStatement|DistributionStatement|CapitalCallStatement|CallAndDistributionStatement|PeriodicStatement|BankStatement|BuyContract|SellContract|HoldingStatement|TaxStatement|NetAssetSummaryStatement|FinancialStatement|Other|null",
  "issuer": "fund/product/company name or null",
  "date_iso": "YYYY-MM-DD or null",
  "suggested_filename": "YYYYMMDD - [doc-type-tag] - [issuer].pdf or null"
}}

------------------------------------------
DOCUMENT CLASSIFICATION RULES
------------------------------------------

BuyContract
- CRITICAL: If document contains ANY of these, it is ALWAYS BuyContract:
  * "BUY CONFIRMATION" or "CONFIRMATION" + "BUY" (in title, header, or box)
  * "has bought" or "has bought for you" or "bought for you" or "bought for"
  * "We have bought" or "We have bought for you" or "We have bought for"
  * "MIDSEC PTY LTD has bought for you" or similar broker name + "has bought"
  * "COMPANY:" field with "has bought" text nearby
  * Any phrase containing "bought" in the context of a transaction
- Keywords: "CONFIRMATION" + "BUY", "We have bought", "Contract Note", "Brokerage", "Consideration"
- Securities may include "FUND" or "ETF" — still a BuyContract if confirmation + buy exists
- If you see "CONFIRMATION" AND "BUY", it is ALWAYS BuyContract, NEVER DistributionStatement, NEVER SellContract
- CRITICAL: The phrase "has bought" indicates BuyContract. If you see "has bought", it is BuyContract, NOT SellContract.
- Examples:
  * Document with "BUY" box and "MIDSEC PTY LTD has bought for you" → BuyContract
  * Document with "BUY CONFIRMATION" title → BuyContract
  * Document with "CONFIRMATION" and "has bought" text → BuyContract
  * Document with "MIDSEC PTY LTD has bought for you" and "COMPANY: DEXUS" → BuyContract
  * Document with "MIDSEC PTY LTD has bought for you" and "MUNRO GLOBAL GROWTH FUND COMPLEX ETF" → BuyContract

SellContract
- CRITICAL: If document contains ANY of these, it is ALWAYS SellContract:
  * "SELL CONFIRMATION" or "CONFIRMATION" + "SELL" (in title, header, or box)
  * "has sold" or "has sold for you" or "sold for you" or "sold for"
  * "We have sold" or "We have sold for you" or "We have sold for"
  * "Buy/Sell: SELL" or "Buy/Sell:SELL"
  * "We confirm your SALE" or "confirm your sale"
- Keywords: "CONFIRMATION" + "SELL", "Buy/Sell: SELL", "We have sold", "We confirm your SALE", "Contract Note"
- If you see "TRADE CONFIRMATION" AND "SELL", it is ALWAYS SellContract
- CRITICAL: The phrase "has sold" indicates SellContract. If you see "has sold", it is SellContract, NOT BuyContract.
- CRITICAL: If document says "has bought" or "bought for you" or any variation of "bought", it is BuyContract, NOT SellContract
- Examples:
  * Document with "SELL" box and "We have sold" → SellContract
  * Document with "SELL CONFIRMATION" title → SellContract
  * Document with "CONFIRMATION" and "has sold" text → SellContract
  * Document with "has bought" → BuyContract (NOT SellContract, even if filename says "Sell")

DividendStatement
- Keywords: "Dividend Statement", "Dividend Payment", "Record Date", "Payment Date"

DistributionStatement
- Keywords: "Distribution Statement/Advice", "Distribution Payment", "Net Distribution"
- NOT a DistributionStatement if the document contains BUY CONFIRMATION keywords

CapitalCallStatement
- Keywords: "Capital Call", "Notice of Capital Call", "Amount Due"
- ONLY if there is NO "Distribution" content

CallAndDistributionStatement
- Document includes BOTH Capital Call AND Distribution information

HoldingStatement
- Keywords: "CHESS", "HIN", "SRN", "Holdings", "Portfolio Summary", "Shareholding Statement"
- NOT valid if trade confirmation keywords appear

BankStatement
- Keywords: "Bank Statement", account summary, BSB
- NOT a bank statement if "confirmation", "contract note", "buy", "sell", "brokerage", "consideration" appear

TaxStatement
- Keywords: "Tax Statement", "AMIT", "AMMA", "Tax Summary", "NAV & Taxation Statement"

NetAssetSummaryStatement
- Keywords: "Net Asset Summary", "NAV Summary", "Fund Performance"
- If NAV + tax info are both present → TaxStatement

FinancialStatement
- Keywords: "Financial Statements", "Financial Statement", "Directors' Report", "Directors Report", "Annual Report", "Audited Financial Statements", "Consolidated Financial Statements"
- Look for patterns like: "DIRECTORS' REPORT AND FINANCIAL STATEMENTS", "FOR THE YEAR ENDED", "Financial Statements for the year ended"
- This is a formal financial reporting document, NOT a periodic statement
- If document contains "Financial Statements" or "Directors' Report" → FinancialStatement, NOT PeriodicStatement

Other
- Everything else

------------------------------------------
ISSUER EXTRACTION RULES
------------------------------------------
Issuer must be the FUND/PRODUCT/COMPANY from THIS document.

For BuyContract/SellContract:
- CRITICAL: You MUST extract the issuer/investment name. Returning null is NOT acceptable unless the document truly has no security information.
- Extract the INVESTMENT/SECURITY name being bought/sold
- Prioritise fields in THIS ORDER:
  1. "COMPANY:" - HIGHEST PRIORITY (e.g., "COMPANY: CLEO DIAGNOSTICS LTD" → "CLEO DIAGNOSTICS LTD")
  2. "Stock Description:" - HIGH PRIORITY for trade confirmations (e.g., "Stock Description: RUSSELL 2000 INDEX ISHARES" → "RUSSELL 2000 INDEX ISHARES")
  3. "Security Description:" - PRIMARY field - Look for this in:
     * Direct format: "Security Description: PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
     * Table format: After "WE HAVE BOUGHT/SOLD THE FOLLOWING SECURITIES FOR YOU", find the table row with "Security Description" column
     * Table row example: "Quantity 25,682 Security Code CRED Security Description BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF Price 23.4603"
       → Extract "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF"
     * Table row example: "Quantity 39,260 Security Code DIFF Security Description PERPETUAL DIVERSIFIED INCOME ACTIVE ETF Price 10.1300"
       → Extract "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
     * Extract the FULL name including "ETF", "FUND", "INDEX", "ISHARES" (e.g., "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF", "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF")
     * The Security Description is usually the longest text in the table row (not Quantity, not Price, not Code)
  4. Look for security name in table rows - find the row that contains quantity, security code, and a long name (usually the investment name)
  5. "Investment:", "Security:", "Code:" followed by security name
- Remove unnecessary descriptors: "ORDINARY FULLY PAID", "FRN", "Callable", coupon details
- BUT preserve ETF/index names: Keep "INDEX", "ISHARES", "ETF", "FUND" if present (e.g., "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF" should remain complete)
- DO NOT use broker names (CommSec, JBWere, Ord Minnett, Morgan Stanley, Equity & Super, EquitySuper) or investor names
- CRITICAL: Do NOT extract legal disclaimers. If extracted name is very long (>100 chars) or contains phrases like "In Australia", "Liability", "Members", "Unless Otherwise Stated", reject it and look for actual investment name
- CRITICAL: Do NOT extract "Quantity" or other table column headers - extract the actual investment name
- CRITICAL: If you see a table with columns like "Quantity", "Security Code", "Security Description", "Price", "Consideration" - the investment name is in the "Security Description" column value

For HoldingStatement/Share Summary/NetAssetSummaryStatement:
- Extract the FUND name from the document TITLE (usually at the top of the document)
- Look for patterns like: "FUND NAME Share Summary", "FUND NAME, Ltd. Share Summary", "FUND NAME NAV Statement"
- Examples:
  * "Highwest Global Offshore Fund, Ltd. Share Summary" → "Highwest Global Offshore Fund, Ltd."
  * "ABC Investment Fund Share Summary" → "ABC Investment Fund"
  * "XYZ Fund NAV Statement" → "XYZ Fund"
- CRITICAL: Extract the ACTUAL FUND NAME, NOT the service provider name
- DO NOT use service provider names like "Morgan Stanley Fund Services", "Computershare", "Link Market Services" - these are NOT the fund name
- The fund name is usually the FIRST prominent name in the document title, before words like "Share Summary", "Statement", "NAV", etc.

For DistributionStatement/Distribution Advice:
- CRITICAL: Extract the ACTUAL FUND NAME, NOT the issuer/trustee/registry name
- Look for fund name in THIS PRIORITY ORDER:
  1. "Fund:" field - HIGHEST PRIORITY (e.g., "Fund: Ares Diversified Credit Fund - Class I" → "Ares Diversified Credit Fund - Class I")
  2. Document title/header - Look for patterns like:
     * "FUND NAME Distribution Statement"
     * "FUND NAME Distribution Advice"
     * "FUND NAME | ABN: ..." (fund name before ABN)
  3. After "Distribution Statement" or "Distribution Advice" title, look for fund name in the same section
  4. Look for fund name near "APIR Code" or fund identifiers
- Examples of CORRECT extraction:
  * "Ares Diversified Credit Fund - Class I" → "Ares Diversified Credit Fund - Class I"
  * "Causeway Wholesale Private Debt Income Fund" → "Causeway Wholesale Private Debt Income Fund"
  * "Fidante" or "AMAL CAUSEWAY TRUSTEES" → These are WRONG (these are issuers/trustees, not fund names)
- DO NOT use:
  * Issuer/Trustee names: "Fidante", "AMAL CAUSEWAY TRUSTEES", "Automic", "Computershare", "Link Market Services"
  * Registry service names: "OIF Registry Services", "Automic Registry Services"
  * Investor/recipient names
  * Document labels: "Distribution Statement", "Distribution Advice"

For DividendStatement:
- Extract the fund/product/company name from document title or main content
- Look for fund names in document headers or titles
- Look for company name near "Dividend Statement" title
- DO NOT use service provider or registry names - use the actual fund/company name

For FinancialStatement:
- Extract the COMPANY name from the document title/header
- Look for patterns like: "COMPANY NAME DIRECTORS' REPORT AND FINANCIAL STATEMENTS"
- Examples:
  * "BIOSCEPTRE INTERNATIONAL LIMITED DIRECTORS' REPORT AND FINANCIAL STATEMENTS" → "BIOSCEPTRE INTERNATIONAL LIMITED"
  * "ABC COMPANY LIMITED Financial Statements" → "ABC COMPANY LIMITED"
- Extract the FULL company name including "LIMITED", "PTY LTD", etc. (do NOT remove suffixes for Financial Statements)
- The company name is usually the FIRST prominent name in the document title, before "DIRECTORS' REPORT", "FINANCIAL STATEMENTS", etc.

For other document types:
- Extract the fund/product/company name from document title or main content
- Look for fund names in document headers or titles
- DO NOT use service provider or registry names - use the actual fund/company name

------------------------------------------
DATE EXTRACTION RULES
------------------------------------------
Output must be YYYY-MM-DD.
Document dates use AU format (DD/MM/YYYY) - CRITICAL: Day comes FIRST, then month, then year.
When you see "11/07/2025", this means: Day=11, Month=07 (July), Year=2025 → Output "2025-07-11"
DO NOT confuse with MM/DD/YYYY format - in Australian documents, the FIRST number is always the DAY.

Priority:

DividendStatement:
  Payment Date → Record Date → Statement Date

DistributionStatement:
  Payment Date → Record Date → Distribution Date

BuyContract/SellContract:
  CRITICAL: Use Trade Date or Confirmation Date, NOT Settlement Date
  Priority order:
  1. "Trade Date" - HIGHEST PRIORITY (e.g., "Trade Date: 09 May 2025" → "2025-05-09")
  2. "Confirmation Date" - HIGH PRIORITY (e.g., "Confirmation Date: 11/07/2025" → "2025-07-11")
  3. "Transaction Date" - MEDIUM PRIORITY
  4. "Date" field in confirmation section
  CRITICAL - DO NOT use:
  - "Settlement Date" - This is a FUTURE date (usually 5-7 days after trade date)
  - "ASX Settlement Date" - This is also a FUTURE date
  - "Payment Date" - Wrong field
  - Any date that is AFTER the trade/confirmation date
  CRITICAL - Date Format Conversion:
  - Australian dates are DD/MM/YYYY format (day first, month second)
  - "11/07/2025" means 11th day of July (month 07), year 2025 → "2025-07-11"
  - "15/07/2025" means 15th day of July (month 07), year 2025 → "2025-07-15"
  - DO NOT confuse DD/MM/YYYY with MM/DD/YYYY - in Australia, day comes FIRST
  Examples:
  - Document shows "Confirmation date: 11/07/2025" and "Settlement date: 15/07/2025" → Use "2025-07-11" (Confirmation Date, NOT Settlement Date)
  - Document shows "Trade Date: 09 May 2025" and "Settlement Date: 16 May 2025" → Use "2025-05-09" (Trade Date)
  - Document shows "Confirmation Date: 13 Nov 2025" and "Settlement Date: 17 Nov 2025" → Use "2025-11-13" (Confirmation Date)

FinancialStatement:
  Year End Date → "FOR THE YEAR ENDED" date → Statement Date
  Look for patterns like "FOR THE YEAR ENDED 30 JUNE 2025" → extract "2025-06-30"
  Australian date format: DD/MM/YYYY or DD MMMM YYYY (e.g., "30 June 2025" → "2025-06-30")

All others:
  Statement Date or main document date

------------------------------------------
FILENAME RULES
------------------------------------------
Filename format: YYYYMMDD - [doc-type-tag] - [issuer].pdf

Date format: YYYYMMDD (no hyphens, no separators)
- Convert YYYY-MM-DD to YYYYMMDD (e.g., "2025-11-13" → "20251113")

Issuer rules:
- Keep original capitalization and spaces
- Remove suffixes (Pty Ltd, Pty. Ltd., Limited, Ltd) if present
- for Buy/Sell: use the SECURITY name
- do NOT include investor names
- do NOT use broker names
- Use dashes with spaces ( - ) to separate date, doc-type-tag, and issuer

doc-type-tag mapping (use proper capitalization - first letter of each word):
DividendStatement → Dividend Statement
DistributionStatement → Dist Statement
CapitalCallStatement → Cap Call
CallAndDistributionStatement → Dist And Cap Call
PeriodicStatement → Periodic Statement
BankStatement → Bank Statement
BuyContract → Buy Contract
SellContract → Sell Contract
HoldingStatement → Holding Statement
TaxStatement → Tax Statement
NetAssetSummaryStatement → Net Asset Summary Statement
FinancialStatement → Financial Statement

------------------------------------------
RETURN FORMAT
------------------------------------------
Return ONLY the JSON object.

Do NOT include:
- markdown
- backticks
- commentary
- explanation
- reasoning
- extra text before or after the JSON

Document text:
{text_sample}

JSON:"""

    # GPT-5 Nano uses reasoning tokens, need more tokens for actual content
    response_text = _call_llm_api(prompt, max_tokens=1000)
    if not response_text:
        print("extract_and_suggest_filename_with_llm: No response from LLM API")
        return None
    print(f"extract_and_suggest_filename_with_llm: Received response, length={len(response_text)}")
    
    # Extract JSON from response (handle markdown code blocks)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    # Try to parse JSON
    try:
        extracted = json.loads(response_text)
        print(f"extract_and_suggest_filename_with_llm: Successfully parsed JSON")
        # Validate and clean extracted data
        result = {
            "doc_type": extracted.get("doc_type") if extracted.get("doc_type") != "null" else None,
            "issuer": extracted.get("issuer") if extracted.get("issuer") != "null" else None,
            "date_iso": extracted.get("date_iso") if extracted.get("date_iso") != "null" else None,
            "suggested_filename": extracted.get("suggested_filename") if extracted.get("suggested_filename") != "null" else None
        }
        print(f"extract_and_suggest_filename_with_llm: Extracted result: {result}")
        return result
    except json.JSONDecodeError as e:
        print(f"LLM JSON parsing failed: {e}")
        print(f"Response text (first 500 chars): {response_text[:500]}")
        return None


def suggest_filename_with_llm(fields: Dict[str, Optional[str]], text_sample: str = "") -> Optional[str]:
    """
    Use LLM to suggest a better filename based on document context
    LLM extracts everything directly from document text - ignores potentially incorrect fields
    """
    if not USE_LLM or not check_llm_available():
        return None
    
    # Use more context from text for better filename generation (increase to 4000 chars to capture fund names)
    context_sample = text_sample[:4000] if text_sample else ""
    
    prompt = f"""You are helping to rename a financial document PDF file.

IMPORTANT: Extract ALL information directly from the document text below. Do NOT rely on any pre-extracted fields - they may be incorrect.

FULL Document Context (read carefully and extract from here):
{context_sample}

------------------------------------------
TOP PRIORITY RULES
------------------------------------------
1. Determine document type. If document contains "has bought", "bought for you", or "CONFIRMATION" + "BUY", it is BuyContract. If it contains "has sold", "sold for you", or "CONFIRMATION" + "SELL", it is SellContract.
2. Extract the ACTUAL fund/product/investment name from THIS document's context
3. For BuyContract/SellContract: Use INVESTMENT/SECURITY name, NOT broker name
4. Return ONLY the filename. No explanation, no markdown, no backticks.

------------------------------------------
OUTPUT FORMAT (FILENAME MODE)
------------------------------------------
Return ONLY the filename in this format:

YYYYMMDD - [doc-type-tag] - [issuer].pdf

Date format: YYYYMMDD (no hyphens, no separators)
- Convert YYYY-MM-DD to YYYYMMDD (e.g., "2025-11-13" → "20251113")

Where:
- issuer = keep original capitalization and spaces, remove "Pty Ltd", "Ltd", "Limited", "Pty. Ltd.", etc.
- Use dashes with spaces ( - ) to separate date, doc-type-tag, and issuer
- do NOT include investor/broker names
- for BuyContract/SellContract: use INVESTMENT/SECURITY name (not broker)

doc-type-tag mapping (use proper capitalization - first letter of each word):
DividendStatement → Dividend Statement
DistributionStatement → Dist Statement
CapitalCallStatement → Cap Call
CallAndDistributionStatement → Dist And Cap Call
PeriodicStatement → Periodic Statement
BankStatement → Bank Statement
BuyContract → Buy Contract
SellContract → Sell Contract
HoldingStatement → Holding Statement
TaxStatement → Tax Statement
NetAssetSummaryStatement → Net Asset Summary Statement
FinancialStatement → Financial Statement

------------------------------------------
INVESTMENT NAME EXTRACTION (BuyContract/SellContract)
------------------------------------------
CRITICAL: Extract the INVESTMENT/SECURITY name being bought/sold from the document text.

CRITICAL: You MUST extract the investment name. Returning null or "Unknown" is NOT acceptable unless the document truly has no security information.

Look for fields in THIS PRIORITY ORDER:
1. "COMPANY:" - HIGHEST PRIORITY (e.g., "COMPANY: CLEO DIAGNOSTICS LTD" → "CLEO DIAGNOSTICS")
2. "Stock Description:" - HIGH PRIORITY (e.g., "Stock Description: RUSSELL 2000 INDEX ISHARES" → "RUSSELL 2000 INDEX ISHARES")
3. "Security Description:" - PRIMARY field - Look in tables after "WE HAVE BOUGHT/SOLD THE FOLLOWING SECURITIES FOR YOU"
   * Direct format: "Security Description: PERPETUAL DIVERSIFIED INCOME ACTIVE ETF" → "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
   * Table format: Look for table rows with columns: Quantity, Security Code, Security Description, Price, Consideration
   * Table row example: "Quantity 25,682 Security Code CRED Security Description BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF Price 23.4603"
     → Extract "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF"
   * Table row example: "Quantity 39,260 Security Code DIFF Security Description PERPETUAL DIVERSIFIED INCOME ACTIVE ETF Price 10.1300"
     → Extract "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
   * Extract the FULL name including "ETF", "FUND", "INDEX", "ISHARES"
   * The Security Description is usually the longest text in the table row (not Quantity, not Price, not Code)
4. Look for security name patterns in transaction details tables
5. "Investment:", "Code:" followed by security name

Examples of CORRECT extraction:
- "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF" → "BETASHARES AUS INVESTMENT GRADE CORPORATE BOND ETF"
- "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF" → "PERPETUAL DIVERSIFIED INCOME ACTIVE ETF"
- "VANECK AUSTRALIAN SUBORDINATED DEBT ETF" → "VANECK AUSTRALIAN SUBORDINATED DEBT ETF"
- "CLEO DIAGNOSTICS LTD" → "CLEO DIAGNOSTICS" (remove Ltd)
- "RUSSELL 2000 INDEX ISHARES" → "RUSSELL 2000 INDEX ISHARES"
- "BRAMBLES LIMITED" → "BRAMBLES" (remove Limited)

CRITICAL - DO NOT use (these are WRONG):
- Broker names: "Equity & Super", "EquitySuper", "CommSec", "JBWere", "Ord Minnett", "Morgan Stanley"
- Investor names: "GENLIM PTY LTD", "D&M- SIMON CUNNINGTON", "DmSimonCunnington", "Simon Cunnington"
- Document labels: "BUY CONFIRMATION", "SELL CONFIRMATION", "TAX INVOICE", "BuyConfirmation", "SellConfirmation", "TaxInvoice"
- Document instructions: "Retain for taxation purposes", "RetainForTaxationPurposes"
- Table column headers: "Quantity", "Currency", "Price", "Consideration", "Brokerage"
- Transaction details: "Account No", "Confirmation No", "Trade Date", "Settlement Date", "Market", "Order Status", "HIN", "Adviser Name"
- Legal disclaimers: Any text >100 chars or containing "In Australia", "Liability", etc.
- ANY text that is NOT the actual investment/security name from the "Security Description" field

If you see text like "DmSimonCunningtonBuyConfirmationTaxInvoiceRetainForTaxationPurposesEquitySuper", 
this is WRONG - it's a mix of investor name, document labels, and broker name. 
You MUST extract ONLY the investment name from "Security Description" field instead.

------------------------------------------
FUND NAME EXTRACTION (Other Document Types)
------------------------------------------
For DistributionStatement/Distribution Advice:
- CRITICAL: Extract the ACTUAL FUND NAME, NOT the issuer/trustee/registry name
- Look for fund name in THIS PRIORITY ORDER:
  1. "Fund:" field - HIGHEST PRIORITY (e.g., "Fund: Ares Diversified Credit Fund - Class I" → "Ares Diversified Credit Fund Class I")
  2. Document title/header - Look for patterns like:
     * "FUND NAME Distribution Statement" → extract FUND NAME
     * "FUND NAME Distribution Advice" → extract FUND NAME
     * "FUND NAME | ABN: ..." → extract FUND NAME (before ABN)
  3. After "Distribution Statement" or "Distribution Advice" title, look for fund name in the same section
  4. Look for fund name near "APIR Code" or fund identifiers
- Examples of CORRECT extraction:
  * "Ares Diversified Credit Fund - Class I" → "Ares Diversified Credit Fund Class I" (replace hyphens with spaces)
  * "Causeway Wholesale Private Debt Income Fund" → "Causeway Wholesale Private Debt Income Fund"
  * "Fidante" or "AMAL CAUSEWAY TRUSTEES" → These are WRONG (these are issuers/trustees, not fund names)
- DO NOT use:
  * Issuer/Trustee names: "Fidante", "AMAL CAUSEWAY TRUSTEES", "Automic", "Computershare", "Link Market Services"
  * Registry service names: "OIF Registry Services", "Automic Registry Services"
  * Investor/recipient names
  * Document labels: "Distribution Statement", "Distribution Advice"

For CapitalCallStatement/CallAndDistributionStatement:
- Extract the FUND/PRODUCT name from document title FIRST
- Look for patterns like "FUND NAME - CAPITAL CALL NOTICE" or "FUND NAME - DISTRIBUTION STATEMENT"
- Extract the FULL fund name including "Fund", "Ventures", "Partnership", etc.
- Do NOT use registry service names (e.g., "OIF Registry Services") - use the actual fund name

For HoldingStatement/Share Summary/NetAssetSummaryStatement:
- Extract the FUND name from the document TITLE (usually at the top of the document)
- Look for patterns like: "FUND NAME Share Summary", "FUND NAME, Ltd. Share Summary", "FUND NAME NAV Statement"
- Examples:
  * "Highwest Global Offshore Fund, Ltd. Share Summary" → "Highwest Global Offshore Fund" (remove Ltd)
  * "ABC Investment Fund Share Summary" → "ABC Investment Fund"
  * "XYZ Fund NAV Statement" → "XYZ Fund"
- CRITICAL: Extract the ACTUAL FUND NAME, NOT the service provider name
- DO NOT use service provider names like "Morgan Stanley Fund Services", "Computershare", "Link Market Services" - these are NOT the fund name
- The fund name is usually the FIRST prominent name in the document title, before words like "Share Summary", "Statement", "NAV", etc.
- Remove suffixes like "Ltd.", "Limited", "Inc." when creating the slug, but keep the main fund name

For FinancialStatement:
- Extract the COMPANY name from the document title/header
- Look for patterns like: "COMPANY NAME DIRECTORS' REPORT AND FINANCIAL STATEMENTS"
- Examples:
  * "BIOSCEPTRE INTERNATIONAL LIMITED DIRECTORS' REPORT AND FINANCIAL STATEMENTS" → "BIOSCEPTRE INTERNATIONAL LIMITED"
  * "ABC COMPANY LIMITED Financial Statements" → "ABC COMPANY LIMITED"
- Extract the FULL company name including "LIMITED", "PTY LTD", etc. (do NOT remove suffixes for Financial Statements)
- The company name is usually the FIRST prominent name in the document title, before "DIRECTORS' REPORT", "FINANCIAL STATEMENTS", etc.

For other document types:
- Fund names after "Fund:", "Product:", "ETF:", or in document titles
------------------------------------------
DATE EXTRACTION
------------------------------------------
Extract from document context using these priorities:

BuyContract/SellContract:
  CRITICAL: Use Trade Date or Confirmation Date, NOT Settlement Date
  Priority order:
  1. "Trade Date" - HIGHEST PRIORITY (e.g., "Trade Date: 09 May 2025" → "2025-05-09")
  2. "Confirmation Date" - HIGH PRIORITY (e.g., "Confirmation Date: 11/07/2025" → "2025-07-11")
  3. "Transaction Date" - MEDIUM PRIORITY
  4. "Date" field in confirmation section
  CRITICAL - DO NOT use:
  - "Settlement Date" - This is a FUTURE date (usually 5-7 days after trade date)
  - "ASX Settlement Date" - This is also a FUTURE date
  - "Payment Date" - Wrong field
  - Any date that is AFTER the trade/confirmation date
  CRITICAL - Date Format Conversion:
  - Australian dates are DD/MM/YYYY format (day first, month second)
  - "11/07/2025" means 11th day of July (month 07), year 2025 → "2025-07-11"
  - "15/07/2025" means 15th day of July (month 07), year 2025 → "2025-07-15"
  - DO NOT confuse DD/MM/YYYY with MM/DD/YYYY - in Australia, day comes FIRST
  Examples:
  - Document shows "Confirmation date: 11/07/2025" and "Settlement date: 15/07/2025" → Use "2025-07-11" (Confirmation Date, NOT Settlement Date)
  - Document shows "Trade Date: 09 May 2025" and "Settlement Date: 16 May 2025" → Use "2025-05-09" (Trade Date)
  - Document shows "Confirmation Date: 13 Nov 2025" and "Settlement Date: 17 Nov 2025" → Use "2025-11-13" (Confirmation Date)

FinancialStatement:
  Year End Date → "FOR THE YEAR ENDED" date → Statement Date
  Look for patterns like "FOR THE YEAR ENDED 30 JUNE 2025" → extract "2025-06-30"
  Australian date format: DD/MM/YYYY or DD MMMM YYYY (e.g., "30 June 2025" → "2025-06-30")

DividendStatement:
  Payment Date → Record Date → Statement Date

DistributionStatement:
  Payment Date → Record Date → Distribution Date

All others:
  Statement Date or document date

Format for date_iso field: YYYY-MM-DD
CRITICAL: Australian dates are DD/MM/YYYY format - Day comes FIRST, then month, then year.
When you see "11/07/2025", this means: Day=11, Month=07 (July), Year=2025 → Output "2025-07-11"
DO NOT confuse with MM/DD/YYYY format - in Australian documents, the FIRST number is always the DAY.
Format for filename: YYYYMMDD (convert YYYY-MM-DD to YYYYMMDD, e.g., "2025-11-13" → "20251113")

------------------------------------------
RETURN FORMAT
------------------------------------------
Return ONLY the filename.

Do NOT include:
- markdown
- backticks
- commentary
- explanation
- reasoning
- extra text before or after the filename

Filename:"""

    # GPT-5 Nano uses reasoning tokens, need more tokens for actual content
    response_text = _call_llm_api(prompt, max_tokens=1000)
    if not response_text:
        return None
    
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
    
    return None

