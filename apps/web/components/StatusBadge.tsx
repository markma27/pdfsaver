'use client';

import React from 'react';

export type Status = 'processing' | 'ready' | 'needs-ocr' | 'ocr-processing' | 'error' | 'needs-review';

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

const statusConfig: Record<Status, { label: string; color: string }> = {
  processing: { label: 'Processing', color: 'bg-blue-100 text-blue-700 border border-blue-200' },
  ready: { label: 'Ready', color: 'bg-green-100 text-green-700 border border-green-200' },
  'needs-ocr': { label: 'Needs OCR', color: 'bg-yellow-100 text-yellow-700 border border-yellow-200' },
  'ocr-processing': { label: 'OCR Processing', color: 'bg-purple-100 text-purple-700 border border-purple-200' },
  error: { label: 'Error', color: 'bg-red-100 text-red-700 border border-red-200' },
  'needs-review': { label: 'Needs Review', color: 'bg-orange-100 text-orange-700 border border-orange-200' }
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${config.color} ${className}`}
    >
      {config.label}
    </span>
  );
}

