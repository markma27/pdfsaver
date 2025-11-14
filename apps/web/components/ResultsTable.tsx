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
}

export function ResultsTable({
  files,
  onFilenameChange,
  onDownload,
  onOCRRequest,
  onRemove
}: ResultsTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  
  const handleEditStart = (file: ProcessedFile) => {
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
  
  if (files.length === 0) {
    return null;
  }
  
  return (
    <div className="mt-8">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Original Filename
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Suggested Filename
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {files.map(file => (
            <tr key={file.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <div className="max-w-xs truncate" title={file.originalName}>
                  {file.originalName}
                </div>
              </td>
              <td className="px-6 py-4 text-sm text-left align-top">
                {editingId === file.id ? (
                  <div className="flex items-start gap-2">
                    <input
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      onBlur={() => handleEditSave(file.id)}
                      onKeyDown={e => handleKeyDown(e, file.id)}
                      className="flex-1 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-left"
                      autoFocus
                    />
                    <button
                      onClick={() => handleEditCancel()}
                      className="text-gray-500 hover:text-gray-700 text-xs px-2 py-1 whitespace-nowrap"
                    >
                      Cancel
                    </button>
                  </div>
                ) : file.status === 'processing' || file.status === 'ocr-processing' ? (
                  <span className="text-gray-400 italic text-left">pending...</span>
                ) : file.status === 'ready' || file.status === 'needs-review' ? (
                  <div className="flex items-start gap-2">
                    <button
                      onClick={() => onDownload && onDownload(file.id)}
                      className="text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded break-words max-w-md text-left"
                      title="Click to download file"
                    >
                      <span className="break-all text-left">{file.editedFilename}</span>
                    </button>
                    <button
                      onClick={() => handleEditStart(file)}
                      className="text-gray-400 hover:text-gray-600 text-xs px-2 py-1 whitespace-nowrap"
                      title="Click to edit filename"
                    >
                      Edit
                    </button>
                  </div>
                ) : (
                  <span className="text-gray-400 break-all max-w-md text-left">{file.editedFilename}</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={file.status} />
                {file.error && (
                  <div className="text-xs text-red-600 mt-1">{file.error}</div>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <div className="flex space-x-2">
                  {file.status === 'needs-ocr' && onOCRRequest && (
                    <button
                      onClick={() => onOCRRequest(file.id)}
                      className="text-purple-600 hover:text-purple-800 focus:outline-none focus:ring-2 focus:ring-purple-500 rounded px-2 py-1"
                    >
                      Process OCR
                    </button>
                  )}
                  {onRemove && (
                    <button
                      onClick={() => onRemove(file.id)}
                      className="text-red-600 hover:text-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 rounded px-2 py-1"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

