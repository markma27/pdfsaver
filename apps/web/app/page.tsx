'use client';

import React, { useState, useCallback, useRef } from 'react';
import { Dropzone } from '@/components/Dropzone';
import { ResultsTable, ProcessedFile } from '@/components/ResultsTable';
import { PDFPreview } from '@/components/PDFPreview';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Status } from '@/components/StatusBadge';
import { extractText, needsOCR } from '@/lib/pdf/extractText';
import { classify, DetectedFields } from '@/lib/pdf/classify';
import { buildFilename, generateFileHash } from '@/lib/pdf/filename';

const MAX_CONCURRENT = 10; // Increased from 5 to 10 for better throughput

export default function Home() {
  const [files, setFiles] = useState<ProcessedFile[]>([]);
  const [processing, setProcessing] = useState(false);
  const [processingCount, setProcessingCount] = useState(0);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const fileHashesRef = useRef<Set<string>>(new Set());
  
  const processFile = useCallback(
    async (
      file: File,
      id: string
    ): Promise<Omit<ProcessedFile, 'id' | 'originalFile' | 'originalName'>> => {
      try {
        // Check for duplicates
        const hash = await generateFileHash(file);
        if (fileHashesRef.current.has(hash)) {
          return {
            status: 'error' as Status,
            fields: {} as DetectedFields,
            suggestedFilename: file.name,
            editedFilename: file.name,
            error: 'Duplicate file (already processed)'
          };
        }
        fileHashesRef.current.add(hash);
        
        // Extract text
        let extractResult;
        try {
          extractResult = await extractText(file, 3);
        } catch (extractError) {
          console.error('Text extraction failed:', extractError);
          // If extraction fails, mark as needs OCR
          return {
            status: 'needs-ocr' as Status,
            fields: {} as DetectedFields,
            suggestedFilename: file.name,
            editedFilename: file.name
          };
        }
        
        // Always send to OCR Worker for processing (OCR + LLM)
        // Skip local classification and send directly to OCR
        if (process.env.NEXT_PUBLIC_OCR_URL) {
          return {
            status: 'needs-ocr' as Status,
            fields: {} as DetectedFields,
            suggestedFilename: file.name,
            editedFilename: file.name
          };
        }
        
        // Fallback: Only use local processing if OCR URL not configured
        if (needsOCR(extractResult.text)) {
          return {
            status: 'needs-ocr' as Status,
            fields: {} as DetectedFields,
            suggestedFilename: file.name,
            editedFilename: file.name
          };
        }
        
        // Classify - wrap in try-catch to handle regex errors
        let classification;
        try {
          classification = await classify(extractResult.text);
        } catch (classifyError) {
          console.error('Classification failed:', classifyError);
          // If classification fails due to regex errors, mark as needs OCR
          if (process.env.NEXT_PUBLIC_OCR_URL) {
            return {
              status: 'needs-ocr' as Status,
              fields: {} as DetectedFields,
              suggestedFilename: file.name,
              editedFilename: file.name
            };
          } else {
            return {
              status: 'error' as Status,
              fields: {} as DetectedFields,
              suggestedFilename: file.name,
              editedFilename: file.name,
              error: 'Classification failed. Please use OCR or check file format.'
            };
          }
        }
        
        const suggestedFilename = buildFilename(classification);
        
        return {
          status: classification.needsReview
            ? ('needs-review' as Status)
            : ('ready' as Status),
          fields: {
            doc_type: classification.doc_type,
            issuer: classification.issuer,
            date_iso: classification.date_iso,
            account_last4: classification.account_last4
          },
          suggestedFilename,
          editedFilename: suggestedFilename,
          confidence: classification.confidence
        };
      } catch (error) {
        console.error('Error processing file:', error);
        // On any error, if OCR is available, suggest using it
        if (process.env.NEXT_PUBLIC_OCR_URL) {
          return {
            status: 'needs-ocr' as Status,
            fields: {} as DetectedFields,
            suggestedFilename: file.name,
            editedFilename: file.name
          };
        }
        return {
          status: 'error' as Status,
          fields: {} as DetectedFields,
          suggestedFilename: file.name,
          editedFilename: file.name,
          error: error instanceof Error ? error.message : 'Processing failed'
        };
      }
    },
    []
  );
  
  const handleOCRRequest = useCallback(
    async (id: string, fileOverride?: File) => {
      const targetFile =
        fileOverride ?? files.find(f => f.id === id)?.originalFile;
      
      if (!targetFile || !process.env.NEXT_PUBLIC_OCR_URL) {
        return;
      }
      
      setFiles(prev =>
        prev.map(f =>
          f.id === id ? { ...f, status: 'processing' } : f
        )
      );
      
      try {
        const formData = new FormData();
        formData.append('file', targetFile);
        
        const response = await fetch(process.env.NEXT_PUBLIC_OCR_URL, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_OCR_TOKEN || ''}`
          },
          body: formData
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          const errorMessage = errorText || response.statusText;
          throw new Error(`OCR request failed: ${response.status} ${response.statusText}. ${errorMessage}`);
        }
        
        const result = await response.json();
        
        if (result.fields && result.suggested_filename) {
          setFiles(prev =>
            prev.map(f =>
              f.id === id
                ? {
                    ...f,
                    status: 'ready' as Status,
                    fields: result.fields,
                    suggestedFilename: result.suggested_filename,
                    editedFilename: result.suggested_filename
                  }
                : f
            )
          );
        } else {
          throw new Error('Invalid OCR response format');
        }
      } catch (error) {
        console.error('OCR error:', error);
        setFiles(prev =>
          prev.map(f =>
            f.id === id
              ? {
                  ...f,
                  status: 'error' as Status,
                  error: error instanceof Error ? error.message : 'OCR processing failed'
                }
              : f
          )
        );
      }
    },
    [files]
  );

  const processFilesWithConcurrency = useCallback(
    async (newFiles: File[]) => {
      setProcessing(true);
      const newProcessedFiles: ProcessedFile[] = [];
      
      // If OCR URL is configured, send all files directly to OCR Worker
      if (process.env.NEXT_PUBLIC_OCR_URL) {
        for (const file of newFiles) {
          const id = `${Date.now()}-${Math.random()}`;
          newProcessedFiles.push({
            id,
            originalFile: file,
            originalName: file.name,
            status: 'processing' as Status,
            fields: {} as DetectedFields,
            suggestedFilename: file.name,
            editedFilename: file.name
          });
        }
        
        setFiles(prev => [...prev, ...newProcessedFiles]);
        
        // Process all files through OCR Worker
        const processQueue = [...newProcessedFiles];
        const activePromises: Promise<void>[] = [];
        
        const processNext = async () => {
          if (processQueue.length === 0) return;
          
          const fileData = processQueue.shift()!;
          setProcessingCount(prev => prev + 1);
          
          const promise = handleOCRRequest(
            fileData.id,
            fileData.originalFile
          ).then(() => {
            setProcessingCount(prev => prev - 1);
            if (processQueue.length > 0) {
              return processNext();
            }
          });
          
          activePromises.push(promise);
          
          if (activePromises.length < MAX_CONCURRENT && processQueue.length > 0) {
            await processNext();
          }
        };
        
        // Start initial batch
        const initialBatch = Math.min(MAX_CONCURRENT, processQueue.length);
        for (let i = 0; i < initialBatch; i++) {
          processNext();
        }
        
        // Wait for all to complete
        await Promise.all(activePromises);
        setProcessing(false);
        setProcessingCount(0);
        return;
      }
      
      // Fallback: Local processing if OCR URL not configured
      // Create initial entries
      for (const file of newFiles) {
        const id = `${Date.now()}-${Math.random()}`;
        newProcessedFiles.push({
          id,
          originalFile: file,
          originalName: file.name,
          status: 'processing' as Status,
          fields: {} as DetectedFields,
          suggestedFilename: file.name,
          editedFilename: file.name
        });
      }
      
      setFiles(prev => [...prev, ...newProcessedFiles]);
      
      // Process with concurrency limit
      const processQueue = [...newProcessedFiles];
      const activePromises: Promise<void>[] = [];
      
      const processNext = async () => {
        if (processQueue.length === 0) return;
        
        const fileData = processQueue.shift()!;
        setProcessingCount(prev => prev + 1);
        
        const promise = processFile(fileData.originalFile, fileData.id).then(
          result => {
            setFiles(prev =>
              prev.map(f =>
                f.id === fileData.id
                  ? { ...f, ...result }
                  : f
              )
            );
            setProcessingCount(prev => prev - 1);
            
            // Process next in queue
            if (processQueue.length > 0) {
              return processNext();
            }
          }
        );
        
        activePromises.push(promise);
        
        if (activePromises.length < MAX_CONCURRENT && processQueue.length > 0) {
          await processNext();
        }
      };
      
      // Start initial batch
      const initialBatch = Math.min(MAX_CONCURRENT, processQueue.length);
      for (let i = 0; i < initialBatch; i++) {
        processNext();
      }
      
      // Wait for all to complete
      await Promise.all(activePromises);
      setProcessing(false);
      setProcessingCount(0);
    },
    [processFile, handleOCRRequest]
  );
  
  const handleFilesSelected = useCallback(
    (selectedFiles: File[]) => {
      processFilesWithConcurrency(selectedFiles);
    },
    [processFilesWithConcurrency]
  );
  
  const handleFilenameChange = useCallback((id: string, newFilename: string) => {
    // Update local state
    setFiles(prev =>
      prev.map(f =>
        f.id === id ? { ...f, editedFilename: newFilename } : f
      )
    );
  }, []);
  
  
  const handleDownloadFile = useCallback(async (id: string) => {
    const file = files.find(f => f.id === id);
    if (!file || (file.status !== 'ready' && file.status !== 'needs-review')) {
      return;
    }
    
    try {
      const arrayBuffer = await file.originalFile.arrayBuffer();
      const blob = new Blob([arrayBuffer], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.editedFilename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
      alert('Download failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  }, [files]);

  const handleDownloadAll = useCallback(async () => {
    const readyFiles = files.filter(
      f => f.status === 'ready' || f.status === 'needs-review'
    );
    
    if (readyFiles.length === 0) {
      alert('No files available for download');
      return;
    }
    
    try {
      // Download each file individually
      for (const file of readyFiles) {
        const arrayBuffer = await file.originalFile.arrayBuffer();
        const blob = new Blob([arrayBuffer], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.editedFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // Small delay between downloads to avoid browser blocking multiple downloads
        if (readyFiles.length > 1) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
    } catch (error) {
      console.error('Download error:', error);
      alert('Download failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  }, [files]);

  const handleClearAll = useCallback(() => {
    if (files.length === 0) {
      return;
    }
    setShowConfirmDialog(true);
  }, [files]);

  const handleConfirmClearAll = useCallback(() => {
    setFiles([]);
    setPreviewFile(null);
    setSelectedFileId(null);
    fileHashesRef.current.clear();
    setShowConfirmDialog(false);
  }, []);

  const handleCancelClearAll = useCallback(() => {
    setShowConfirmDialog(false);
  }, []);

  const handlePreview = useCallback((file: ProcessedFile) => {
    setPreviewFile(file.originalFile);
    setSelectedFileId(file.id);
  }, []);

  const handleRemove = useCallback((id: string) => {
    setFiles(prev => {
      const updated = prev.filter(f => f.id !== id);
      // Clear preview if removed file was being previewed
      if (selectedFileId === id) {
        setPreviewFile(null);
        setSelectedFileId(null);
      }
      return updated;
    });
  }, [selectedFileId]);
  
  const readyCount = files.filter(
    f => f.status === 'ready' || f.status === 'needs-review'
  ).length;
  
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="max-w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* Header with Logo, Title, and Buttons */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4">
            {/* Left: Logo */}
            <div className="flex items-end flex-shrink-0">
              <img
                src="/pg-logo.svg"
                alt="PG Logo"
                className="h-16 sm:h-20 md:h-24 lg:h-28 w-auto"
              />
            </div>
            
            {/* Middle: Title and Subtitle - Centered */}
            <div className="flex-1 min-w-0 flex flex-col items-center justify-end">
              <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-3 tracking-tight text-center">PDFsaver</h1>
              <p className="text-base sm:text-lg text-slate-600 font-medium text-center">
                Bulk upload PDF files, automatically extract key information and rename
              </p>
            </div>
            
            {/* Right: Action Buttons - Always visible, bottom aligned with logo */}
            <div className="flex items-center gap-3 flex-shrink-0">
              <button
                onClick={handleDownloadAll}
                disabled={readyCount === 0}
                className={`font-semibold py-2.5 px-5 rounded-lg shadow-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 active:scale-95 text-sm sm:text-base ${
                  readyCount > 0
                    ? 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-md focus:ring-blue-500 cursor-pointer'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed opacity-60'
                }`}
              >
                Download ({readyCount} file{readyCount !== 1 ? 's' : ''})
              </button>
              <button
                onClick={handleClearAll}
                disabled={files.length === 0}
                className={`font-semibold py-2.5 px-5 rounded-lg shadow-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 active:scale-95 text-sm sm:text-base ${
                  files.length > 0
                    ? 'bg-slate-500 hover:bg-slate-600 text-white hover:shadow-md focus:ring-slate-500 cursor-pointer'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed opacity-60'
                }`}
              >
                Clear All ({files.length} file{files.length !== 1 ? 's' : ''})
              </button>
            </div>
          </div>
        </div>

        {/* Main Layout - Left/Right Split */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-250px)]">
          {/* Left Column */}
          <div className="flex flex-col space-y-4 min-h-0">
            {/* Dropzone */}
            <div className="flex-shrink-0">
              <Dropzone
                onFilesSelected={handleFilesSelected}
              />
            </div>
            
            {/* Processing Status */}
            {processing && (
              <div className="text-sm text-slate-600 font-medium bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5">
                <span className="inline-block w-2 h-2 bg-blue-600 rounded-full mr-2 animate-pulse"></span>
                Processing {processingCount} file{processingCount !== 1 ? 's' : ''}...
              </div>
            )}
            
            {/* File List */}
            <div className="flex-1 overflow-y-auto min-h-0">
              <ResultsTable
                files={files}
                onFilenameChange={handleFilenameChange}
                onDownload={handleDownloadFile}
                onOCRRequest={
                  process.env.NEXT_PUBLIC_OCR_URL ? handleOCRRequest : undefined
                }
                onRemove={handleRemove}
                onPreview={handlePreview}
                selectedFileId={selectedFileId}
              />
            </div>
          </div>

          {/* Right Column - PDF Preview */}
          <div className="min-h-0">
            <PDFPreview file={previewFile} />
          </div>
        </div>
      </div>

      {/* Confirm Dialog */}
      <ConfirmDialog
        isOpen={showConfirmDialog}
        title="Remove All Files"
        message={`Are you sure you want to remove all ${files.length} file${files.length !== 1 ? 's' : ''}? This action cannot be undone.`}
        confirmText="Remove All"
        cancelText="Cancel"
        onConfirm={handleConfirmClearAll}
        onCancel={handleCancelClearAll}
        variant="danger"
      />
    </main>
  );
}

