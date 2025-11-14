import * as pdfjsLib from 'pdfjs-dist';

// Set worker source for pdfjs-dist
// pdfjs-dist v4+ uses .mjs files
if (typeof window !== 'undefined') {
  // Use local worker file from public folder
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
}

export interface ExtractTextResult {
  text: string;
  hasText: boolean;
  pagesUsed: number;
}

/**
 * Extract text from the first N pages of a PDF file
 * @param file - PDF file object
 * @param maxPages - Maximum number of pages to extract (default: 3)
 * @returns Extracted text and metadata
 */
export async function extractText(
  file: File,
  maxPages: number = 3
): Promise<ExtractTextResult> {
  const arrayBuffer = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;
  
  const totalPages = pdf.numPages;
  const pagesToExtract = Math.min(maxPages, totalPages);
  
  let fullText = '';
  let hasAnyText = false;
  
  for (let pageNum = 1; pageNum <= pagesToExtract; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();
    
    const pageText = textContent.items
      .map((item: any) => item.str)
      .join(' ')
      .trim();
    
    if (pageText.length > 0) {
      hasAnyText = true;
      fullText += pageText + '\n';
    }
  }
  
  return {
    text: fullText.trim(),
    hasText: hasAnyText,
    pagesUsed: pagesToExtract
  };
}

/**
 * Check if PDF needs OCR (has less than threshold text)
 * @param text - Extracted text
 * @param threshold - Minimum text length to consider valid (default: 50)
 * @returns true if OCR is needed
 */
export function needsOCR(text: string, threshold: number = 50): boolean {
  return text.length < threshold;
}

