# OCR Worker Quick Start

## Issue: Docker Desktop Not Running

If you see the error: `The system cannot find the file specified` or `dockerDesktopLinuxEngine`, Docker Desktop is not running.

### Solution 1: Start Docker Desktop (Recommended)

1. **Install Docker Desktop** (if not installed):
   - Download from: https://www.docker.com/products/docker-desktop
   - Install and restart your computer

2. **Start Docker Desktop**:
   - Open Docker Desktop from Start Menu
   - Wait until it shows "Docker Desktop is running" in the system tray
   - The whale icon should be steady (not animated)

3. **Then run the startup script again**:
   ```powershell
   cd apps\ocr-worker
   .\start-docker.ps1
   ```

### Solution 2: Install Python and Run Locally

If you prefer not to use Docker:

1. **Install Python 3.11+**:
   - Download from: https://www.python.org/downloads/
   - **IMPORTANT:** During installation, check ✅ "Add Python to PATH"
   - Verify installation: Open new PowerShell and run `python --version`

2. **Install Tesseract OCR** (Required for OCR):
   - Download Windows installer: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to default location: `C:\Program Files\Tesseract-OCR`
   - Add to PATH: Add `C:\Program Files\Tesseract-OCR` to System PATH

3. **Set up OCR Worker**:
   ```powershell
   cd apps\ocr-worker
   
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   .\venv\Scripts\Activate.ps1
   
   # If you get execution policy error, run:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

4. **Start the server**:
   ```powershell
   # Set environment variables
   $env:OCR_TOKEN="change-me-please"
   $env:ALLOW_ORIGIN="http://localhost:3000"
   
   # Start server
   uvicorn main:app --host 0.0.0.0 --port 8123
   ```

### Solution 3: Use Without OCR (Temporary)

If you just want to test the frontend without OCR:

1. The frontend will work for PDFs with text layers
2. PDFs without text will show "Needs OCR" status
3. You can manually rename those files

### Verify OCR Worker is Running

Once started (either Docker or Python), test it:
```powershell
curl http://localhost:8123/healthz
```

Should return: `{"status":"ok"}`

### Update Frontend Configuration

Make sure your `apps/web/.env.local` has:
```
NEXT_PUBLIC_OCR_URL=http://localhost:8123/v1/ocr-extract
NEXT_PUBLIC_OCR_TOKEN=change-me-please
```

