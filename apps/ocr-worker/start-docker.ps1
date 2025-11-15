# PowerShell script to start OCR Worker with Docker

Write-Host "Building PDFsaver OCR Worker Docker image..." -ForegroundColor Cyan
docker build -t pdfsaver-ocr-worker .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nStopping existing container (if any)..." -ForegroundColor Yellow
docker stop pdfsaver-ocr 2>$null
docker rm pdfsaver-ocr 2>$null

Write-Host "`nStarting OCR Worker container..." -ForegroundColor Green

# Check if LLM should be enabled
$useLLM = $env:USE_LLM -eq "true"
$ollamaUrl = $env:OLLAMA_URL
$ollamaModel = $env:OLLAMA_MODEL

if (-not $ollamaUrl) {
    $ollamaUrl = "http://host.docker.internal:11434"
}
if (-not $ollamaModel) {
    $ollamaModel = "qwen2.5:7b"
}

$dockerArgs = @(
    "-d",
    "-p", "8123:8123",
    "-e", "OCR_TOKEN=change-me-please",
    "-e", "ALLOW_ORIGIN=http://localhost:3000"
)

if ($useLLM) {
    Write-Host "LLM enabled: $ollamaModel" -ForegroundColor Cyan
    $dockerArgs += "-e", "USE_LLM=true"
    $dockerArgs += "-e", "OLLAMA_URL=$ollamaUrl"
    $dockerArgs += "-e", "OLLAMA_MODEL=$ollamaModel"
} else {
    Write-Host "LLM disabled (set USE_LLM=true to enable)" -ForegroundColor Yellow
}

$dockerArgs += "--name", "pdfsaver-ocr"
$dockerArgs += "pdfsaver-ocr-worker"

docker run @dockerArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nOCR Worker started successfully!" -ForegroundColor Green
    Write-Host "Container name: pdfsaver-ocr" -ForegroundColor Cyan
    Write-Host "Port: 8123" -ForegroundColor Cyan
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
                Write-Host "Health check passed! OCR Worker is ready." -ForegroundColor Green
                $response.Content
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

