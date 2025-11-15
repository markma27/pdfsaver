# 前端本地部署启动脚本
# 使用方法: .\start-local-deploy.ps1

param(
    [string]$LocalIP = "",
    [string]$OcrUrl = "",
    [string]$OcrToken = "change-me"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PDFsaver Frontend - 本地部署启动" -ForegroundColor Cyan
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

# 配置 OCR URL（如果未提供）
if ([string]::IsNullOrEmpty($OcrUrl)) {
    $OcrUrl = "http://$LocalIP:8123/v1/ocr-extract"
}

# 检查 .env.local 文件
$envFile = ".env.local"
$envContent = @"
NEXT_PUBLIC_APP_ORIGIN=http://$LocalIP:3000
NEXT_PUBLIC_OCR_URL=$OcrUrl
NEXT_PUBLIC_OCR_TOKEN=$OcrToken
"@

if (Test-Path $envFile) {
    Write-Host "发现现有 .env.local 文件" -ForegroundColor Yellow
    $overwrite = Read-Host "是否覆盖? (y/n)"
    if ($overwrite -eq "y" -or $overwrite -eq "Y") {
        Set-Content -Path $envFile -Value $envContent
        Write-Host ".env.local 已更新" -ForegroundColor Green
    } else {
        Write-Host "使用现有 .env.local 配置" -ForegroundColor Gray
    }
} else {
    Set-Content -Path $envFile -Value $envContent
    Write-Host ".env.local 文件已创建" -ForegroundColor Green
}

# 检查 Node.js
Write-Host "`n检查 Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "Node.js 版本: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未找到 Node.js，请先安装 Node.js" -ForegroundColor Red
    exit 1
}

# 检查依赖
if (-not (Test-Path "node_modules")) {
    Write-Host "`n安装依赖..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问信息:" -ForegroundColor Cyan
Write-Host "  本地访问: http://localhost:3000" -ForegroundColor White
Write-Host "  内网访问: http://$LocalIP:3000" -ForegroundColor White
Write-Host ""
Write-Host "OCR Worker:" -ForegroundColor Cyan
Write-Host "  $OcrUrl" -ForegroundColor White
Write-Host ""
Write-Host "启动开发服务器..." -ForegroundColor Yellow
Write-Host ""

# 启动开发服务器
npm run dev

