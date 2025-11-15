'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// Set worker source
if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
}

interface PDFPreviewProps {
  file: File | null;
}

export function PDFPreview({ file }: PDFPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfRef = useRef<pdfjsLib.PDFDocumentProxy | null>(null);
  const loadingTaskRef = useRef<pdfjsLib.PDFDocumentLoadingTask | null>(null);
  const fileIdRef = useRef<string | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1.25); // 125% default zoom

  // Generate a unique ID for the file based on name and size
  const getFileId = (file: File | null): string | null => {
    if (!file) return null;
    return `${file.name}-${file.size}-${file.lastModified}`;
  };

  // Load PDF when file changes
  useEffect(() => {
    const currentFileId = getFileId(file);
    
    // If same file, don't reload
    if (currentFileId === fileIdRef.current && pdfRef.current) {
      return;
    }

    // Cleanup previous loading task
    if (loadingTaskRef.current) {
      loadingTaskRef.current.destroy();
      loadingTaskRef.current = null;
    }

    if (!file) {
      fileIdRef.current = null;
      pdfRef.current = null;
      setPageNum(1);
      setNumPages(0);
      setError(null);
      setLoading(false);
      return;
    }

    const loadPDF = async () => {
      setLoading(true);
      setError(null);
      fileIdRef.current = currentFileId;
      
      try {
        const arrayBuffer = await file.arrayBuffer();
        const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
        loadingTaskRef.current = loadingTask;
        
        const pdf = await loadingTask.promise;
        pdfRef.current = pdf;
        const totalPages = pdf.numPages;
        setNumPages(totalPages);
        setPageNum(1);
        
        // Don't render here - let the render effect handle it
      } catch (err) {
        console.error('Error loading PDF:', err);
        setError(err instanceof Error ? err.message : 'Failed to load PDF');
        pdfRef.current = null;
        fileIdRef.current = null;
      } finally {
        setLoading(false);
        loadingTaskRef.current = null;
      }
    };

    loadPDF();

    // Cleanup function
    return () => {
      if (loadingTaskRef.current) {
        loadingTaskRef.current.destroy();
        loadingTaskRef.current = null;
      }
    };
  }, [file]);

  // Render page when pageNum, scale, or numPages changes (after PDF is loaded)
  useEffect(() => {
    // Don't render if PDF is not loaded, loading, or invalid page number
    if (!pdfRef.current || loading || pageNum < 1 || pageNum > numPages || numPages === 0) {
      return;
    }

    const renderCurrentPage = async () => {
      try {
        const page = await pdfRef.current!.getPage(pageNum);
        await renderPage(page, scale);
        // Clear any previous errors on successful render
        setError(null);
      } catch (err) {
        console.error('Error rendering page:', err);
        setError(err instanceof Error ? err.message : 'Failed to render page');
      }
    };

    // Small delay to ensure canvas is mounted
    const timeoutId = setTimeout(() => {
      renderCurrentPage();
    }, 50);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [pageNum, scale, numPages, loading]);

  const renderPage = async (page: pdfjsLib.PDFPageProxy, currentScale: number, retryCount = 0) => {
    if (!canvasRef.current) {
      // Retry up to 5 times if canvas is not ready
      if (retryCount < 5) {
        setTimeout(() => {
          renderPage(page, currentScale, retryCount + 1);
        }, 100);
      } else {
        console.error('Canvas not available after retries');
        setError('Failed to initialize canvas');
      }
      return;
    }

    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    if (!context) {
      console.error('Failed to get canvas context');
      setError('Failed to get canvas context');
      return;
    }

    try {
      const viewport = page.getViewport({ scale: currentScale });
      canvas.height = viewport.height;
      canvas.width = viewport.width;

      const renderContext = {
        canvasContext: context,
        viewport: viewport
      };

      await page.render(renderContext).promise;
    } catch (err) {
      console.error('Error rendering page to canvas:', err);
      setError(err instanceof Error ? err.message : 'Failed to render page');
    }
  };

  const handlePrevPage = () => {
    if (pageNum > 1) {
      setPageNum(pageNum - 1);
    }
  };

  const handleNextPage = () => {
    if (pageNum < numPages) {
      setPageNum(pageNum + 1);
    }
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  };

  if (!file) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl">
        <div className="text-center text-slate-400">
          <svg
            className="mx-auto h-16 w-16 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
          <p className="text-lg font-medium">Select a file to preview</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white border border-slate-200 rounded-xl shadow-sm">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3.5 border-b border-slate-200 bg-slate-50/50 rounded-t-xl">
        <div className="flex items-center gap-2.5">
          <button
            onClick={handlePrevPage}
            disabled={pageNum <= 1}
            className="px-3.5 py-1.5 text-sm font-medium bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-700"
          >
            ← Prev
          </button>
          <span className="text-sm text-slate-600 font-medium px-2">
            Page {pageNum} of {numPages}
          </span>
          <button
            onClick={handleNextPage}
            disabled={pageNum >= numPages}
            className="px-3.5 py-1.5 text-sm font-medium bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-700"
          >
            Next →
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="px-3.5 py-1.5 text-sm font-medium bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors text-slate-700"
          >
            −
          </button>
          <span className="text-sm text-slate-600 w-16 text-center font-medium">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="px-3.5 py-1.5 text-sm font-medium bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors text-slate-700"
          >
            +
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto p-4 bg-slate-100">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-slate-500 font-medium">Loading PDF...</div>
          </div>
        )}
        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-red-600 font-medium">Error: {error}</div>
          </div>
        )}
        {!loading && !error && (
          <div className="flex justify-center">
            <canvas ref={canvasRef} className="shadow-xl rounded-lg" />
          </div>
        )}
      </div>
    </div>
  );
}

