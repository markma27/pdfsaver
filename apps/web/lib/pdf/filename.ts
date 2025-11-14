import { DetectedFields } from './classify';

/**
 * Convert string to Title Case without dashes (e.g., 'Anacacia Capital' -> 'AnacaciaCapital')
 */
export function titleCase(text: string | null): string {
  if (!text) return 'Unknown';
  
  // Remove company suffixes (Pty Ltd, Limited, etc.)
  // Common variations: Pty Ltd, Pty. Ltd., PTY LTD, Limited, Ltd, Ltd.
  let cleaned = text.replace(/\b(?:Pty\.?\s*Ltd\.?|PTY\.?\s*LTD\.?|Limited|Ltd\.?)\b/gi, '');
  
  // Clean up: remove special characters except spaces, hyphens, and alphanumeric
  cleaned = cleaned.replace(/[^\w\s-]/g, '');
  
  // Split by spaces and hyphens, then capitalize each word
  const words = cleaned.split(/[\s-]+/).filter(word => word.length > 0);
  const titleWords = words.map(word => 
    word.length > 1 
      ? word[0].toUpperCase() + word.slice(1).toLowerCase()
      : word.toUpperCase()
  );
  
  // Join without separators (remove dashes)
  const result = titleWords.join('');
  
  return result || 'Unknown';
}

/**
 * Convert string to URL-friendly slug (kept for backward compatibility)
 */
export function slugify(text: string | null): string {
  if (!text) return 'unknown';
  
  // Remove company suffixes (Pty Ltd, Limited, etc.)
  // Common variations: Pty Ltd, Pty. Ltd., PTY LTD, Limited, Ltd, Ltd.
  let cleaned = text.replace(/\b(?:Pty\.?\s*Ltd\.?|PTY\.?\s*LTD\.?|Limited|Ltd\.?)\b/gi, '');
  
  // Clean up and convert to slug
  cleaned = cleaned
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
  
  return cleaned || 'unknown';
}

/**
 * Build suggested filename from detected fields
 * Format: YYYY-MM-DD_{issuer_title}_{doc_type_title}.pdf (Title Case, no dashes)
 */
export function buildFilename(fields: DetectedFields): string {
  const parts: string[] = [];
  
  // Date (required)
  if (fields.date_iso) {
    parts.push(fields.date_iso);
  } else {
    parts.push('YYYY-MM-DD');
  }
  
  // Issuer in Title Case (no dashes)
  const issuerTitle = titleCase(fields.issuer);
  parts.push(issuerTitle);
  
  // Document type in Title Case (no dashes)
  let docTypeTitle: string;
  if (fields.doc_type === 'CallAndDistributionStatement') {
    docTypeTitle = 'DistributionAndCapitalCallStatement';
  } else if (fields.doc_type === 'DistributionStatement') {
    docTypeTitle = 'DistributionStatement';
  } else if (fields.doc_type === 'DividendStatement') {
    docTypeTitle = 'DividendStatement';
  } else if (fields.doc_type === 'BuyContract') {
    docTypeTitle = 'BuyContract';
  } else if (fields.doc_type === 'SellContract') {
    docTypeTitle = 'SellContract';
  } else if (fields.doc_type === 'HoldingStatement') {
    docTypeTitle = 'HoldingStatement';
  } else if (fields.doc_type === 'TaxStatement') {
    docTypeTitle = 'TaxStatement';
  } else if (fields.doc_type === 'BankStatement') {
    docTypeTitle = 'BankStatement';
  } else if (fields.doc_type === 'PeriodicStatement') {
    docTypeTitle = 'PeriodicStatement';
  } else {
    // For unknown types, convert to Title Case
    const cleaned = fields.doc_type?.replace('Statement', '').replace('Contract', '') || 'unknown';
    docTypeTitle = titleCase(cleaned);
  }
  
  parts.push(docTypeTitle);
  
  // Do NOT include account last 4 digits
  
  return `${parts.join('_')}.pdf`;
}

/**
 * Generate a quick hash of file content (first 200KB) for duplicate detection
 */
export async function generateFileHash(file: File): Promise<string> {
  const chunk = file.slice(0, 200 * 1024); // First 200KB
  const arrayBuffer = await chunk.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

