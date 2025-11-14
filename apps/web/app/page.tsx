'use client';

import React, { useState, useCallback, useRef } from 'react';
import { Dropzone } from '@/components/Dropzone';
import { ResultsTable, ProcessedFile } from '@/components/ResultsTable';
import { Status } from '@/components/StatusBadge';
import { extractText, needsOCR } from '@/lib/pdf/extractText';
import { classify, DetectedFields } from '@/lib/pdf/classify';
import { buildFilename, generateFileHash } from '@/lib/pdf/filename';

const MAX_CONCURRENT = 5;

export default function Home() {
  const [files, setFiles] = useState<ProcessedFile[]>([]);
  const [processing, setProcessing] = useState(false);
  const [processingCount, setProcessingCount] = useState(0);
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
          throw new Error(`OCR request failed: ${response.statusText}`);
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
    setFiles(prev =>
      prev.map(f =>
        f.id === id ? { ...f, editedFilename: newFilename } : f
      )
    );
  }, []);
  
  const handleRemove = useCallback((id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
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
    if (confirm(`Are you sure you want to remove all ${files.length} file(s)?`)) {
      setFiles([]);
      fileHashesRef.current.clear();
    }
  }, [files]);
  
  const readyCount = files.filter(
    f => f.status === 'ready' || f.status === 'needs-review'
  ).length;
  
  return (
    <main className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">PDFsaver</h1>
          <p className="text-lg text-gray-600">
            Bulk upload PDF files, automatically extract key information and rename
          </p>
        </div>
        
        <Dropzone
          onFilesSelected={handleFilesSelected}
        />
        
        {processing && (
          <div className="mt-4 text-center text-sm text-gray-600">
            Processing {processingCount} file{processingCount !== 1 ? 's' : ''}...
          </div>
        )}
        
        <ResultsTable
          files={files}
          onFilenameChange={handleFilenameChange}
          onDownload={handleDownloadFile}
          onOCRRequest={
            process.env.NEXT_PUBLIC_OCR_URL ? handleOCRRequest : undefined
          }
          onRemove={handleRemove}
        />
        
        {files.length > 0 && (
          <div className="mt-8 text-center flex justify-center gap-4">
            {readyCount > 0 && (
              <button
                onClick={handleDownloadAll}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg shadow-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Download ({readyCount} file{readyCount !== 1 ? 's' : ''})
              </button>
            )}
            <button
              onClick={handleClearAll}
              className="bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg shadow-md transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              Clear All ({files.length} file{files.length !== 1 ? 's' : ''})
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

