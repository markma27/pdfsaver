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
      e.preventDefault();
      e.stopPropagation();
      handleEditSave(id);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
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
    <div className="space-y-3">
      {files.map(file => (
        <div
          key={file.id}
          onClick={() => handleFileClick(file)}
          className={`
            p-4 border rounded-xl cursor-pointer transition-all duration-200 bg-white
            ${selectedFileId === file.id 
              ? 'border-blue-500 bg-blue-50/50 shadow-md ring-2 ring-blue-200' 
              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 hover:shadow-sm'
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
              
              <div className="text-sm font-semibold text-slate-900 mb-1.5 truncate" title={file.originalName}>
                {file.originalName}
              </div>
              
              <div className="text-sm text-slate-600">
                {editingId === file.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      onKeyDown={e => {
                        e.stopPropagation();
                        handleKeyDown(e, file.id);
                      }}
                      onClick={e => e.stopPropagation()}
                      onBlur={e => {
                        // Don't save on blur if clicking Save/Cancel buttons
                        const relatedTarget = e.relatedTarget as HTMLElement;
                        if (relatedTarget && (relatedTarget.closest('button') || relatedTarget.closest('input'))) {
                          return;
                        }
                        // Small delay to allow button clicks to process first
                        setTimeout(() => {
                          if (editingId === file.id) {
                            handleEditSave(file.id);
                          }
                        }, 200);
                      }}
                      className="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-900 font-medium"
                      autoFocus
                    />
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        e.preventDefault();
                        handleEditSave(file.id);
                      }}
                      className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 text-xs px-3 py-1.5 rounded-md font-medium transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        e.preventDefault();
                        handleEditCancel();
                      }}
                      className="text-slate-500 hover:text-slate-700 text-xs px-3 py-1.5 rounded-md hover:bg-slate-100 font-medium transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : file.status === 'processing' || file.status === 'ocr-processing' ? (
                  <span className="text-slate-400 italic font-medium">pending...</span>
                ) : file.status === 'ready' || file.status === 'needs-review' ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        onDownload && onDownload(file.id);
                      }}
                      className="text-blue-600 hover:text-blue-700 underline break-words text-left font-medium hover:no-underline"
                      title="Click to download file"
                    >
                      {file.editedFilename}
                    </button>
                    <button
                      onClick={e => handleEditStart(file, e)}
                      className="text-slate-400 hover:text-slate-600 text-xs px-2 py-1 rounded-md hover:bg-slate-100 font-medium"
                      title="Click to edit filename"
                    >
                      Edit
                    </button>
                  </div>
                ) : (
                  <span className="text-slate-400 break-words font-medium">{file.editedFilename}</span>
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
                  className="text-xs text-purple-600 hover:text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-50 font-semibold transition-colors"
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
                  className="text-xs text-red-600 hover:text-red-700 px-3 py-1.5 rounded-lg hover:bg-red-50 font-semibold transition-colors"
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

