import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'PDFsaver - PDF File Auto-Renaming Tool',
  description: 'Bulk upload PDF files, automatically extract key information and rename',
  icons: {
    icon: '/icon.svg',
  },
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body className="font-sans">{children}</body>
    </html>
  );
}

