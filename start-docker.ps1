# PDFsaver Docker 快速启动脚本 (PowerShell)

Write-Host "🚀 PDFsaver Docker 部署脚本" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# 检查 Docker 是否安装
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ 错误: Docker 未安装。请先安装 Docker Desktop。" -ForegroundColor Red
    exit 1
}

# 检查 Docker Compose 是否安装
try {
    docker compose version | Out-Null
} catch {
    Write-Host "❌ 错误: Docker Compose 未安装。请先安装 Docker Desktop。" -ForegroundColor Red
    exit 1
}

# 检查 .env 文件
if (-not (Test-Path .env)) {
    Write-Host "⚠️  警告: .env 文件不存在。" -ForegroundColor Yellow
    Write-Host "正在创建 .env 文件..." -ForegroundColor Yellow
    
    # 生成随机 Token
    $token = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    @"
# OCR Worker Configuration
OCR_TOKEN=$token

# LLM Configuration (Optional)
USE_LLM=false
LLM_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3
"@ | Out-File -FilePath .env -Encoding utf8
    
    Write-Host "✅ 已创建 .env 文件，Token 已自动生成。" -ForegroundColor Green
    Write-Host "⚠️  请检查 .env 文件并根据需要修改配置。" -ForegroundColor Yellow
    Read-Host "按 Enter 继续"
}

# 构建镜像
Write-Host ""
Write-Host "📦 构建 Docker 镜像..." -ForegroundColor Cyan
docker compose build

# 启动服务
Write-Host ""
Write-Host "🚀 启动服务..." -ForegroundColor Cyan
docker compose up -d

# 等待服务就绪
Write-Host ""
Write-Host "⏳ 等待服务启动..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# 检查服务状态
Write-Host ""
Write-Host "📊 服务状态:" -ForegroundColor Cyan
docker compose ps

# 显示访问信息
Write-Host ""
Write-Host "✅ 部署完成！" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Cyan
Write-Host "  - 前端: http://localhost:3000" -ForegroundColor White
Write-Host "  - OCR Worker Health: http://localhost:8123/healthz" -ForegroundColor White
Write-Host ""
Write-Host "查看日志:" -ForegroundColor Cyan
Write-Host "  docker compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "停止服务:" -ForegroundColor Cyan
Write-Host "  docker compose down" -ForegroundColor White
Write-Host ""

