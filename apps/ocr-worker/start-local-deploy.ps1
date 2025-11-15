# 本地部署启动脚本 - 支持内网访问
# 使用方法: .\start-local-deploy.ps1

param(
    [string]$LocalIP = "",
    [string]$DeepSeekApiKey = "",
    [string]$OcrToken = "change-me"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PDFsaver OCR Worker - 本地部署启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取本地 IP 地址（如果未提供）
if ([string]::IsNullOrEmpty($LocalIP)) {
    Write-Host "正在获取本地 IP 地址..." -ForegroundColor Yellow
    $networkAdapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.IPAddress -notlike "127.*" -and 
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual"
    }
    
    if ($networkAdapters) {
        $LocalIP = $networkAdapters[0].IPAddress
        Write-Host "检测到本地 IP: $LocalIP" -ForegroundColor Green
    } else {
        Write-Host "无法自动检测 IP 地址，请手动输入:" -ForegroundColor Red
        $LocalIP = Read-Host "本地 IP 地址"
    }
}

# 检查 DeepSeek API Key
if ([string]::IsNullOrEmpty($DeepSeekApiKey)) {
    $DeepSeekApiKey = $env:DEEPSEEK_API_KEY
    if ([string]::IsNullOrEmpty($DeepSeekApiKey)) {
        Write-Host "请输入 DeepSeek API Key:" -ForegroundColor Yellow
        $DeepSeekApiKey = Read-Host "DeepSeek API Key"
    }
}

# 检查 Docker 是否运行
Write-Host "`n检查 Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "Docker 正在运行" -ForegroundColor Green
} catch {
    Write-Host "错误: Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 停止并删除现有容器
Write-Host "`n清理现有容器..." -ForegroundColor Yellow
docker stop pdfsaver-ocr 2>$null
docker rm pdfsaver-ocr 2>$null

# 构建镜像（如果需要）
Write-Host "`n检查 Docker 镜像..." -ForegroundColor Yellow
$imageExists = docker images -q pdfsaver-ocr:latest
if (-not $imageExists) {
    Write-Host "构建 Docker 镜像..." -ForegroundColor Yellow
    docker build -t pdfsaver-ocr:latest .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: Docker 镜像构建失败" -ForegroundColor Red
        exit 1
    }
}

# 配置 CORS - 允许本地和内网访问
$allowOrigins = "http://localhost:3000,http://$LocalIP:3000"

Write-Host "`n配置信息:" -ForegroundColor Cyan
Write-Host "  本地 IP: $LocalIP" -ForegroundColor White
Write-Host "  前端 URL: http://$LocalIP:3000" -ForegroundColor White
Write-Host "  OCR Worker URL: http://$LocalIP:8123/v1/ocr-extract" -ForegroundColor White
Write-Host "  允许的来源: $allowOrigins" -ForegroundColor White
Write-Host ""

# 启动容器
Write-Host "启动 OCR Worker 容器..." -ForegroundColor Yellow
docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=deepseek `
  -e DEEPSEEK_API_KEY=$DeepSeekApiKey `
  -e DEEPSEEK_MODEL=deepseek-chat `
  -e OCR_TOKEN=$OcrToken `
  -e ALLOW_ORIGINS=$allowOrigins `
  pdfsaver-ocr:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "OCR Worker 启动成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "访问信息:" -ForegroundColor Cyan
    Write-Host "  健康检查: http://$LocalIP:8123/healthz" -ForegroundColor White
    Write-Host "  API 端点: http://$LocalIP:8123/v1/ocr-extract" -ForegroundColor White
    Write-Host ""
    Write-Host "前端配置 (.env.local):" -ForegroundColor Cyan
    Write-Host "  NEXT_PUBLIC_APP_ORIGIN=http://$LocalIP:3000" -ForegroundColor Yellow
    Write-Host "  NEXT_PUBLIC_OCR_URL=http://$LocalIP:8123/v1/ocr-extract" -ForegroundColor Yellow
    Write-Host "  NEXT_PUBLIC_OCR_TOKEN=$OcrToken" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "员工访问 URL: http://$LocalIP:3000" -ForegroundColor Green
    Write-Host ""
    Write-Host "查看日志: docker logs -f pdfsaver-ocr" -ForegroundColor Gray
    Write-Host "停止服务: docker stop pdfsaver-ocr" -ForegroundColor Gray
} else {
    Write-Host "`n错误: 容器启动失败" -ForegroundColor Red
    Write-Host "查看日志: docker logs pdfsaver-ocr" -ForegroundColor Yellow
    exit 1
}

