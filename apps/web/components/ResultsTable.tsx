'use client';

import React, { useState } from 'react';
import { StatusBadge, Status } from './StatusBadge';
import { DetectedFields } from '@/lib/pdf/classify';

export interface ProcessedFile {
  id: string;
  originalFile: File;
  originalName: string;
  status: Status;
  fields: DetectedFields;
  suggestedFilename: string;
  editedFilename: string;
  confidence?: number;
  error?: string;
}

interface ResultsTableProps {
  files: ProcessedFile[];
  onFilenameChange: (id: string, newFilename: string) => void;
  onDownload?: (id: string) => void;
  onOCRRequest?: (id: string) => void;
  onRemove?: (id: string) => void;
  onPreview?: (file: ProcessedFile) => void;
  selectedFileId?: string | null;
}

export function ResultsTable({
  files,
  onFilenameChange,
  onDownload,
  onOCRRequest,
  onRemove,
  onPreview,
  selectedFileId
}: ResultsTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  
  const handleEditStart = (file: ProcessedFile, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(file.id);
    setEditValue(file.editedFilename);
  };
  
  const handleEditSave = (id: string) => {
    if (editValue.trim()) {
      onFilenameChange(id, editValue.trim());
    }
    setEditingId(null);
    setEditValue('');
  };
  
  const handleEditCancel = () => {
    setEditingId(null);
    setEditValue('');
  };
  
  const handleKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === 'Enter') {
      handleEditSave(id);
    } else if (e.key === 'Escape') {
      handleEditCancel();
    }
  };

  const handleFileClick = (file: ProcessedFile) => {
    if (onPreview && editingId !== file.id) {
      onPreview(file);
    }
  };
  
  if (files.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        <p>No files uploaded yet</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-2">
      {files.map(file => (
        <div
          key={file.id}
          onClick={() => handleFileClick(file)}
          className={`
            p-4 border rounded-lg cursor-pointer transition-colors
            ${selectedFileId === file.id 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
            }
          `}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge status={file.status} />
                {file.error && (
                  <span className="text-xs text-red-600">{file.error}</span>
                )}
              </div>
              
              <div className="text-sm font-medium text-gray-900 mb-1 truncate" title={file.originalName}>
                {file.originalName}
              </div>
              
              <div className="text-sm text-gray-600">
                {editingId === file.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      onBlur={() => handleEditSave(file.id)}
                      onKeyDown={e => handleKeyDown(e, file.id)}
                      onClick={e => e.stopPropagation()}
                      className="flex-1 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        handleEditCancel();
                      }}
                      className="text-gray-500 hover:text-gray-700 text-xs px-2 py-1"
                    >
                      Cancel
                    </button>
                  </div>
                ) : file.status === 'processing' || file.status === 'ocr-processing' ? (
                  <span className="text-gray-400 italic">pending...</span>
                ) : file.status === 'ready' || file.status === 'needs-review' ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        onDownload && onDownload(file.id);
                      }}
                      className="text-blue-600 hover:text-blue-800 underline break-words text-left"
                      title="Click to download file"
                    >
                      {file.editedFilename}
                    </button>
                    <button
                      onClick={e => handleEditStart(file, e)}
                      className="text-gray-400 hover:text-gray-600 text-xs px-2 py-1"
                      title="Click to edit filename"
                    >
                      Edit
                    </button>
                  </div>
                ) : (
                  <span className="text-gray-400 break-words">{file.editedFilename}</span>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              {file.status === 'needs-ocr' && onOCRRequest && (
                <button
                  onClick={e => {
                    e.stopPropagation();
                    onOCRRequest(file.id);
                  }}
                  className="text-xs text-purple-600 hover:text-purple-800 px-2 py-1 rounded hover:bg-purple-50"
                >
                  Process OCR
                </button>
              )}
              {onRemove && (
                <button
                  onClick={e => {
                    e.stopPropagation();
                    onRemove(file.id);
                  }}
                  className="text-xs text-red-600 hover:text-red-800 px-2 py-1 rounded hover:bg-red-50"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

