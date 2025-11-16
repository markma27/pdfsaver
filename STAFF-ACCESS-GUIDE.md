# Staff Access Guide

This document explains how to access the PDFsaver application from your computer.

## Quick Access

### Method 1: Direct IP Access (Simplest)

1. Open your browser (Chrome, Edge, Firefox, etc.)
2. Enter in the address bar: `http://[server-IP]:3000`
   - Example: `http://192.168.1.100:3000`
3. Press Enter to access

**Note:** Please contact IT department to obtain the server IP address.

### Method 2: Using Domain Name Access (Recommended)

If an internal domain name has been configured, you can use a friendlier address:

1. **Initial Setup (one-time only)**

   **Windows Users:**
   - Press `Win + R`, type `notepad`
   - Right-click Notepad and select "Run as administrator"
   - Open file: `C:\Windows\System32\drivers\etc\hosts`
   - Add a line at the end:
     ```
     [server-IP]  pdfsaver.internal
     ```
     Example: `192.168.1.100  pdfsaver.internal`
   - Save the file (may require administrator privileges)

   **Mac Users:**
   ```bash
   sudo nano /etc/hosts
   # Add: 192.168.1.100  pdfsaver.internal
   # Press Ctrl+X, then Y, then Enter to save
   ```

   **Linux Users:**
   ```bash
   sudo nano /etc/hosts
   # Add: 192.168.1.100  pdfsaver.internal
   # Press Ctrl+X, then Y, then Enter to save
   ```

2. **Access Application**
   - Open browser
   - Visit: `http://pdfsaver.internal:3000` or `http://pdfsaver.internal`

## Usage Instructions

### Upload Files

1. Click the upload area or drag and drop PDF files
2. Supports bulk upload of multiple files
3. Files will be automatically processed and new filenames generated

### Edit Filenames

- Click on filename to edit
- Click download after confirmation

### Download Files

- Single download: Click on filename
- Bulk download: Click "Download All" button

## Frequently Asked Questions

### Q: Cannot access the application?

**Check:**
1. Confirm you and the server are on the same internal network
2. Check if the server IP address is correct
3. Contact IT department to confirm service is running

### Q: CORS error displayed?

**Solution:**
1. Clear browser cache
2. Try using a different browser
3. Contact IT department to check configuration

### Q: File upload failed?

**Check:**
1. Is the file in PDF format?
2. Is the file size within limit (usually 25MB)?
3. Is the network connection normal?

### Q: Processing is slow?

**Possible reasons:**
1. Large files or files containing scanned content
2. High server load
3. Slow network speed

## Technical Support

If you encounter issues, please contact:
- IT Department: [Contact Information]
- Technical Support Email: [Email Address]

---

**Last Updated**: 2025-01-XX
