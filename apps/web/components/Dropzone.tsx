'use client';

import React, { useCallback, useState } from 'react';

interface DropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function Dropzone({ onFilesSelected, disabled = false }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (disabled) return;
    
    const files = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    );
    
    if (files.length > 0) {
      onFilesSelected(files);
    }
  }, [onFilesSelected, disabled]);
  
  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled) return;
    
    const files = Array.from(e.target.files || []).filter(
      file => file.type === 'application/pdf'
    );
    
    if (files.length > 0) {
      onFilesSelected(files);
    }
    
    // Reset input
    e.target.value = '';
  }, [onFilesSelected, disabled]);
  
  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center transition-colors
        ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-gray-400'}
      `}
    >
      <input
        type="file"
        id="file-input"
        multiple
        accept=".pdf,application/pdf"
        onChange={handleFileInput}
        disabled={disabled}
        className="hidden"
      />
      <label
        htmlFor="file-input"
        className={`cursor-pointer ${disabled ? 'pointer-events-none' : ''}`}
      >
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <div className="mt-4">
          <p className="text-sm text-gray-600">
            <span className="font-semibold">Click to select files</span> or drag and drop PDF files here
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Supports bulk upload (PDF format only)
          </p>
        </div>
      </label>
    </div>
  );
}

