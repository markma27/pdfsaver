import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PDFsaver - PDF File Auto-Renaming Tool',
  description: 'Bulk upload PDF files, automatically extract key information and rename'
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

