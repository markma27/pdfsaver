# Next Steps - OCR Worker is Running! ✅

## Current Status
- ✅ OCR Worker is running on http://localhost:8123
- ✅ Health check passed: `{"status":"ok"}`

## Step 1: Configure Frontend

Make sure your frontend has OCR Worker configured in `apps/web/.env.local`:

```bash
NEXT_PUBLIC_APP_ORIGIN=http://localhost:3000
NEXT_PUBLIC_OCR_URL=http://localhost:8123/v1/ocr-extract
NEXT_PUBLIC_OCR_TOKEN=change-me-please
```

**Note:** The token must match what you set in Docker (currently `change-me-please`)

## Step 2: Verify Frontend is Running

Open a new terminal and check if the frontend is running:

```powershell
# Check if Next.js is running
curl http://localhost:3000
```

If not running, start it:
```powershell
cd apps\web
pnpm dev
```

## Step 3: Test the Application

1. **Open browser**: http://localhost:3000
2. **Upload a PDF file** (drag & drop or click to select)
3. **For text PDFs**: Should extract and classify automatically
4. **For scanned PDFs**: Will show "Needs OCR" → Click "Process OCR" button

## Step 4: Monitor OCR Processing

Watch OCR Worker logs in real-time:
```powershell
docker logs -f pdfsaver-ocr
```

## Troubleshooting

### Frontend can't connect to OCR Worker
- Verify OCR Worker is running: `curl http://localhost:8123/healthz`
- Check token matches in both `.env.local` and Docker container
- Check CORS: `ALLOW_ORIGIN` in Docker should match frontend URL

### OCR processing fails
- Check logs: `docker logs pdfsaver-ocr`
- Verify PDF file is not corrupted
- Check file size (max 200MB)

### Stop OCR Worker
```powershell
docker stop pdfsaver-ocr
```

### Restart OCR Worker
```powershell
cd apps\ocr-worker
.\start-docker.ps1
```

## Success Indicators

✅ PDF uploaded successfully
✅ Text extracted (or "Needs OCR" shown)
✅ Fields detected (type, issuer, date, account)
✅ Suggested filename generated
✅ Can edit filename inline
✅ Can download ZIP with all files

