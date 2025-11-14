import { DetectedFields } from './classify';

/**
 * Convert string to URL-friendly slug
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
 * Format: YYYY-MM-DD_{issuer_slug}_{doc_type}.pdf
 */
export function buildFilename(fields: DetectedFields): string {
  const parts: string[] = [];
  
  // Date (required)
  if (fields.date_iso) {
    parts.push(fields.date_iso);
  } else {
    parts.push('YYYY-MM-DD');
  }
  
  // Issuer slug
  const issuerSlug = slugify(fields.issuer);
  parts.push(issuerSlug);
  
  // Document type
  const docTypeSlug = fields.doc_type
    ? slugify(fields.doc_type.replace(/([A-Z])/g, '-$1').toLowerCase())
    : 'unknown';
  parts.push(docTypeSlug);
  
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

