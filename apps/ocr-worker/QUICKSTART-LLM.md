# Quick Start: LLM Integration

## Step 1: Install Ollama

**Windows:**
```powershell
# Download from https://ollama.com/download
# Or use winget:
winget install Ollama.Ollama
```

**Mac/Linux:**
```bash
curl https://ollama.com/install.sh | sh
```

## Step 2: Download a Model

```bash
# Small and fast (~1.3GB)
ollama pull llama3.2:1b

# Or better quality (~2GB)
ollama pull llama3.2:3b
```

## Step 3: Start Ollama

Ollama usually starts automatically. Verify it's running:

```bash
curl http://localhost:11434/api/tags
```

Should return a list of available models.

## Step 4: Update OCR Worker Environment

If running Docker:

```powershell
# Stop existing container
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

# Restart with LLM enabled
cd apps\ocr-worker
docker build -t pdfsaver-ocr-worker .

docker run -d `
  -p 8123:8123 `
  --network host `
  -e OCR_TOKEN=change-me-please `
  -e ALLOW_ORIGIN=http://localhost:3000 `
  -e USE_LLM=true `
  -e OLLAMA_URL=http://localhost:11434 `
  -e OLLAMA_MODEL=llama3.2:1b `
  --name pdfsaver-ocr `
  pdfsaver-ocr-worker
```

**Note:** On Windows/Mac, you might need to use `host.docker.internal` instead of `localhost`:

```powershell
-e OLLAMA_URL=http://host.docker.internal:11434
```

## Step 5: Verify LLM Integration

Check health endpoint:

```bash
curl http://localhost:8123/healthz
```

Should show:
```json
{
  "status": "ok",
  "llm_available": true,
  "llm_model": "llama3.2:1b"
}
```

## How It Works

1. **Rule-based extraction first** (fast, regex-based)
2. **LLM enhancement** when:
   - Confidence < 70%
   - Missing critical fields (doc_type, issuer)
3. **LLM filename suggestion** for better naming
4. **Automatic fallback** if LLM unavailable

## Performance

- **Without LLM**: ~1-2 seconds per PDF
- **With LLM (1b model)**: ~2-4 seconds per PDF
- **With LLM (3b model)**: ~3-6 seconds per PDF

## Disable LLM

To disable LLM and use only rules:

```bash
-e USE_LLM=false
```

Or simply don't set `USE_LLM` environment variable.

