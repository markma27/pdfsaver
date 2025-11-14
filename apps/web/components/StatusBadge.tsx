'use client';

import React from 'react';

export type Status = 'processing' | 'ready' | 'needs-ocr' | 'ocr-processing' | 'error' | 'needs-review';

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

const statusConfig: Record<Status, { label: string; color: string }> = {
  processing: { label: 'Processing', color: 'bg-blue-100 text-blue-800' },
  ready: { label: 'Ready', color: 'bg-green-100 text-green-800' },
  'needs-ocr': { label: 'Needs OCR', color: 'bg-yellow-100 text-yellow-800' },
  'ocr-processing': { label: 'OCR Processing', color: 'bg-purple-100 text-purple-800' },
  error: { label: 'Error', color: 'bg-red-100 text-red-800' },
  'needs-review': { label: 'Needs Review', color: 'bg-orange-100 text-orange-800' }
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color} ${className}`}
    >
      {config.label}
    </span>
  );
}

