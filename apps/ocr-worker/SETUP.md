# OCR Worker Setup Guide

## Option 1: Using Docker (Recommended - No Python Installation Required)

### Prerequisites
- Docker Desktop installed on Windows

### Steps

1. **Build the Docker image:**
   ```powershell
   cd apps\ocr-worker
   docker build -t pdfsaver-ocr-worker .
   ```

2. **Run the container:**
   ```powershell
   docker run -d `
     -p 8123:8123 `
     -e OCR_TOKEN=your-secure-token-here `
     -e ALLOW_ORIGIN=http://localhost:3000 `
     --name pdfsaver-ocr `
     pdfsaver-ocr-worker
   ```

3. **Verify it's running:**
   ```powershell
   curl http://localhost:8123/healthz
   ```

4. **View logs:**
   ```powershell
   docker logs pdfsaver-ocr
   ```

## Option 2: Local Python Setup

### Prerequisites
- Python 3.11+ installed
- Add Python to PATH during installation

### Steps

1. **Install Python 3.11+**
   - Download from https://www.python.org/downloads/
   - **Important:** Check "Add Python to PATH" during installation

2. **Create virtual environment:**
   ```powershell
   cd apps\ocr-worker
   python -m venv venv
   ```

3. **Activate virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   
   If you get an execution policy error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
   
   **Note:** On Windows, you'll also need to install system dependencies:
   - Tesseract OCR: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Add Tesseract to PATH (usually `C:\Program Files\Tesseract-OCR`)
   - OCRmyPDF and Ghostscript will be installed via pip

5. **Set environment variables:**
   ```powershell
   $env:OCR_TOKEN="your-secure-token-here"
   $env:ALLOW_ORIGIN="http://localhost:3000"
   ```

6. **Start the server:**
   ```powershell
   uvicorn main:app --host 0.0.0.0 --port 8123
   ```

## Configuration

Update your frontend `.env.local` file:
```
NEXT_PUBLIC_OCR_URL=http://localhost:8123/v1/ocr-extract
NEXT_PUBLIC_OCR_TOKEN=your-secure-token-here
```

## Troubleshooting

### Docker Issues
- Make sure Docker Desktop is running
- Check if port 8123 is already in use: `netstat -ano | findstr :8123`

### Python Issues
- Verify Python is installed: `python --version`
- If not found, reinstall Python and check "Add to PATH"
- For Tesseract issues, ensure it's in your system PATH

### Connection Issues
- Verify OCR Worker is running: `curl http://localhost:8123/healthz`
- Check CORS settings match your frontend URL
- Verify the token matches in both frontend and worker

