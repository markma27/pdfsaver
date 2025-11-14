# PowerShell script to start OCR Worker with LLM enabled

Write-Host "Building PDFsaver OCR Worker Docker image..." -ForegroundColor Cyan
docker build -t pdfsaver-ocr-worker .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nStopping existing container (if any)..." -ForegroundColor Yellow
docker stop pdfsaver-ocr 2>$null
docker rm pdfsaver-ocr 2>$null

Write-Host "`nChecking Ollama..." -ForegroundColor Cyan
try {
    $ollamaCheck = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Ollama is not running. Please start Ollama first!" -ForegroundColor Red
    Write-Host "  Start Ollama from Start Menu or run: ollama serve" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nStarting OCR Worker with LLM enabled..." -ForegroundColor Green
Write-Host "Model: gemma3:1b" -ForegroundColor Cyan

docker run -d `
    -p 8123:8123 `
    -e OCR_TOKEN=change-me-please `
    -e ALLOW_ORIGIN=http://localhost:3000 `
    -e USE_LLM=true `
    -e OLLAMA_URL=http://host.docker.internal:11434 `
    -e OLLAMA_MODEL=gemma3:1b `
    --name pdfsaver-ocr `
    pdfsaver-ocr-worker

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nOCR Worker started successfully!" -ForegroundColor Green
    Write-Host "Container name: pdfsaver-ocr" -ForegroundColor Cyan
    Write-Host "Port: 8123" -ForegroundColor Cyan
    Write-Host "LLM: gemma3:1b" -ForegroundColor Cyan
    Write-Host "`nTo view logs: docker logs -f pdfsaver-ocr" -ForegroundColor Yellow
    Write-Host "To stop: docker stop pdfsaver-ocr" -ForegroundColor Yellow
    Write-Host "`nWaiting for container to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    
    Write-Host "Testing health endpoint..." -ForegroundColor Cyan
    $maxRetries = 10
    $retryCount = 0
    $success = $false
    
    while ($retryCount -lt $maxRetries -and -not $success) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8123/healthz" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                $healthData = $response.Content | ConvertFrom-Json
                Write-Host "Health check passed! OCR Worker is ready." -ForegroundColor Green
                Write-Host "Status: $($healthData.status)" -ForegroundColor Green
                if ($healthData.llm_available) {
                    Write-Host "LLM: Available ($($healthData.llm_model))" -ForegroundColor Green
                } else {
                    Write-Host "LLM: Not available (check Ollama connection)" -ForegroundColor Yellow
                }
                $success = $true
            }
        } catch {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Host "Waiting for service to start... ($retryCount/$maxRetries)" -ForegroundColor Yellow
                Start-Sleep -Seconds 2
            } else {
                Write-Host "`nHealth check failed. Checking container logs..." -ForegroundColor Red
                docker logs pdfsaver-ocr --tail 30
            }
        }
    }
} else {
    Write-Host "Failed to start container!" -ForegroundColor Red
    exit 1
}

