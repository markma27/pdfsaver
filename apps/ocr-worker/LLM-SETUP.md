# LLM Setup Guide for OCR Worker

This guide explains how to set up a local LLM (Large Language Model) to enhance document classification and field extraction in the OCR Worker.

## Why Use LLM?

- **Better Classification**: LLM can understand context better than regex patterns
- **Handles Variations**: Works with documents that don't match exact patterns
- **Improved Accuracy**: Especially useful for OCR'd text with errors
- **Privacy**: All processing happens locally, no data sent to external APIs

## Option 1: Using Ollama (Recommended)

Ollama is the easiest way to run LLMs locally.

### Installation

1. **Install Ollama**:
   - Windows: Download from https://ollama.com/download
   - Or use: `winget install Ollama.Ollama`
   - Mac/Linux: `curl https://ollama.com/install.sh | sh`

2. **Pull a small, fast model**:
   ```bash
   # Small model (~1.3GB, fast)
   ollama pull llama3.2:1b
   
   # Or slightly larger but better quality (~2GB)
   ollama pull llama3.2:3b
   
   # Or even better quality (~4.7GB)
   ollama pull llama3.1:8b
   ```

3. **Start Ollama** (usually runs automatically):
   ```bash
   ollama serve
   ```
   Default URL: http://localhost:11434

### Configuration

Set environment variables in your OCR Worker:

```bash
# Enable LLM
USE_LLM=true

# Ollama URL (default: http://localhost:11434)
OLLAMA_URL=http://localhost:11434

# Model name (default: llama3.2:1b)
OLLAMA_MODEL=llama3.2:1b
```

### Docker Setup

If using Docker, you need to:

1. **Run Ollama separately** (not in Docker container):
   ```bash
   ollama serve
   ```

2. **Update Docker run command** to use host network or expose Ollama:
   ```bash
   docker run -d \
     -p 8123:8123 \
     --network host \
     -e OCR_TOKEN=your-token \
     -e ALLOW_ORIGIN=http://localhost:3000 \
     -e USE_LLM=true \
     -e OLLAMA_URL=http://host.docker.internal:11434 \
     -e OLLAMA_MODEL=llama3.2:1b \
     --name pdfsaver-ocr \
     pdfsaver-ocr-worker
   ```

   Or use host.docker.internal on Windows/Mac, or host network on Linux.

## Option 2: Using llama.cpp Python Bindings

For more control, you can use llama-cpp-python directly:

```bash
pip install llama-cpp-python
```

Then modify `llm_helper.py` to use llama-cpp-python instead of Ollama API.

## How It Works

1. **Rule-based extraction first**: Tries regex patterns and rules
2. **LLM enhancement**: If confidence is low (<70%) or fields missing, uses LLM
3. **LLM filename suggestion**: Uses LLM to suggest better filenames
4. **Fallback**: If LLM unavailable, uses rule-based approach

## Performance

- **Small model (1b)**: ~1-2 seconds per document
- **Medium model (3b)**: ~2-4 seconds per document  
- **Large model (8b)**: ~5-10 seconds per document

## Testing

Test if Ollama is working:

```bash
curl http://localhost:11434/api/tags
```

Test LLM extraction:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "Say hello",
  "stream": false
}'
```

## Troubleshooting

### LLM not responding
- Check Ollama is running: `ollama list`
- Verify URL: `curl http://localhost:11434/api/tags`
- Check model is downloaded: `ollama list`

### Slow processing
- Use a smaller model (1b or 3b)
- Reduce text sample size in `llm_helper.py`
- Consider using LLM only when rule-based fails

### Docker connection issues
- Use `host.docker.internal:11434` on Windows/Mac
- Use `--network host` on Linux
- Or run Ollama in a separate container and connect via Docker network

## Disabling LLM

To disable LLM and use only rule-based extraction:

```bash
USE_LLM=false
```

Or simply don't set the environment variable.

