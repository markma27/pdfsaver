import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import { loadRules, RulesConfig } from './rules';

dayjs.extend(customParseFormat);

export type DocType =
  | 'DividendStatement'
  | 'DistributionStatement'
  | 'BankStatement'
  | 'BuyContract'
  | 'SellContract'
  | 'HoldingStatement'
  | 'TaxStatement';

export interface DetectedFields {
  doc_type: DocType | null;
  issuer: string | null;
  date_iso: string | null;
  account_last4: string | null;
}

export interface ClassificationResult extends DetectedFields {
  confidence: number;
  needsReview: boolean;
}

/**
 * Classify document type based on text content
 */
export async function classifyDocType(
  text: string,
  rules: RulesConfig
): Promise<{ type: DocType | null; confidence: number }> {
  const upperText = text.toUpperCase();
  let bestMatch: { type: DocType; score: number } | null = null;
  
  for (const [type, patterns] of Object.entries(rules.types)) {
    let score = 0;
    const mustMatches = patterns.must.filter(must =>
      upperText.includes(must.toUpperCase())
    );
    const hintMatches = patterns.hints.filter(hint =>
      upperText.includes(hint.toUpperCase())
    );
    
    // Must patterns are required
    if (mustMatches.length === patterns.must.length) {
      score = 80 + hintMatches.length * 5;
    } else if (mustMatches.length > 0) {
      score = 50 + hintMatches.length * 5;
    } else if (hintMatches.length > 0) {
      score = 30 + hintMatches.length * 5;
    }
    
    if (score > 0 && (!bestMatch || score > bestMatch.score)) {
      bestMatch = { type: type as DocType, score };
    }
  }
  
  return {
    type: bestMatch?.type || null,
    confidence: bestMatch?.score || 0
  };
}

/**
 * Detect issuer from text
 */
export function detectIssuer(
  text: string,
  rules: RulesConfig
): string | null {
  const upperText = text.toUpperCase();
  
  // Check normalized variants first
  for (const [variant, canonical] of Object.entries(rules.issuers.normalize)) {
    if (upperText.includes(variant.toUpperCase())) {
      return canonical;
    }
  }
  
  // Check canonical names
  for (const issuer of rules.issuers.canonical) {
    if (upperText.includes(issuer.toUpperCase())) {
      return issuer;
    }
  }
  
  return null;
}

/**
 * Extract date from text based on document type priorities
 */
export function extractDate(
  text: string,
  docType: DocType | null,
  rules: RulesConfig
): string | null {
  if (!docType) {
    // Try generic date extraction
    return extractGenericDate(text);
  }
  
  const priorities = rules.date_priorities[docType] || ['Date'];
  
  // Try labeled dates first
  for (const label of priorities) {
    const date = extractLabeledDate(text, label);
    if (date) return date;
  }
  
  // Fallback to generic extraction
  return extractGenericDate(text);
}

/**
 * Extract date with a specific label
 */
function extractLabeledDate(text: string, label: string): string | null {
  // Escape special regex characters in the label
  const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  
  // Date patterns: DD/MM/YYYY, YYYY-MM-DD, DD Month YYYY
  const datePatterns = [
    `\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}`,  // DD/MM/YYYY or DD-MM-YYYY
    `\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}`,  // YYYY-MM-DD or YYYY/MM/DD
    `\\d{1,2}\\s+\\w+\\s+\\d{4}`        // DD Month YYYY
  ];
  
  // Try each pattern separately to avoid regex group issues
  for (const pattern of datePatterns) {
    const labelRegex = new RegExp(
      `${escapedLabel}[:\\s]+(${pattern})`,
      'i'
    );
    
    const match = text.match(labelRegex);
    if (match && match[1]) {
      const parsed = parseDate(match[1]);
      if (parsed) return parsed;
    }
  }
  
  return null;
}

/**
 * Extract generic date from text (various formats)
 */
function extractGenericDate(text: string): string | null {
  // Common date patterns
  const patterns = [
    /\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b/,
    /\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b/,
    /\b(\d{1,2}\s+\w+\s+\d{4})\b/i
  ];
  
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const parsed = parseDate(match[1]);
      if (parsed) return parsed;
    }
  }
  
  return null;
}

/**
 * Parse date string to ISO format (YYYY-MM-DD)
 */
function parseDate(dateStr: string): string | null {
  // Clean up the date string
  const cleaned = dateStr.trim();
  
  const formats = [
    'YYYY-MM-DD',
    'DD-MM-YYYY',
    'MM/DD/YYYY',
    'DD/MM/YYYY',
    'D MMMM YYYY',
    'DD MMMM YYYY',
    'D MMM YYYY',
    'DD MMM YYYY',
    'D MMMM YYYY',  // e.g., "16 July 2025"
    'DD MMMM YYYY'  // e.g., "02 July 2025"
  ];
  
  for (const format of formats) {
    const parsed = dayjs(cleaned, format, true);
    if (parsed.isValid()) {
      return parsed.format('YYYY-MM-DD');
    }
  }
  
  return null;
}

/**
 * Extract account number (last 4 digits)
 */
export function extractAccountLast4(
  text: string,
  rules: RulesConfig
): string | null {
  // Safe account patterns (avoid complex regex that might fail)
  const safePatterns = [
    /(?:HIN|SRN|Account|Holder\s+ID?)[:\s]+([A-Z0-9-]{6,})/i,
    /(?:Account\s+Number|Account\s+No\.?)[:\s]+([A-Z0-9-]{6,})/i,
    /BSB[:\s]+\d{3}-\d{3}[:\s]+ACC[:\s]+[*]*(\d{4})/i,
    /Account[:\s]+[*]*(\d{4})/i
  ];
  
  for (const pattern of safePatterns) {
    try {
      const match = text.match(pattern);
      if (match && match[1]) {
        const account = match[1].replace(/[^A-Z0-9]/g, '');
        if (account.length >= 4) {
          return account.slice(-4);
        }
      }
    } catch (error) {
      // Skip invalid patterns
      continue;
    }
  }
  
  return null;
}

/**
 * Main classification function
 */
export async function classify(
  text: string
): Promise<ClassificationResult> {
  const rules = await loadRules();
  
  const { type: doc_type, confidence: typeConfidence } =
    await classifyDocType(text, rules);
  const issuer = detectIssuer(text, rules);
  const date_iso = extractDate(text, doc_type, rules);
  const account_last4 = extractAccountLast4(text, rules);
  
  // Calculate overall confidence
  let confidence = typeConfidence;
  if (issuer) confidence += 10;
  if (date_iso) confidence += 10;
  if (account_last4) confidence += 10;
  
  confidence = Math.min(confidence, 100);
  
  return {
    doc_type,
    issuer,
    date_iso,
    account_last4,
    confidence,
    needsReview: confidence < 90
  };
}

