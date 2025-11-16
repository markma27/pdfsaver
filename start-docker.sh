#!/bin/bash

# PDFsaver Docker 快速启动脚本

set -e

echo "🚀 PDFsaver Docker 部署脚本"
echo "================================"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装。请先安装 Docker。"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装。请先安装 Docker Compose。"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  警告: .env 文件不存在。"
    echo "正在创建 .env 文件..."
    cat > .env << EOF
# OCR Worker Configuration
OCR_TOKEN=$(openssl rand -hex 32)

# LLM Configuration (Optional)
USE_LLM=false
LLM_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3
EOF
    echo "✅ 已创建 .env 文件，Token 已自动生成。"
    echo "⚠️  请检查 .env 文件并根据需要修改配置。"
    read -p "按 Enter 继续..."
fi

# 构建镜像
echo ""
echo "📦 构建 Docker 镜像..."
docker-compose build

# 启动服务
echo ""
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务就绪
echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

# 显示访问信息
echo ""
echo "✅ 部署完成！"
echo ""
echo "访问地址:"
echo "  - 前端: http://localhost:3000"
echo "  - OCR Worker Health: http://localhost:8123/healthz"
echo ""
echo "查看日志:"
echo "  docker-compose logs -f"
echo ""
echo "停止服务:"
echo "  docker-compose down"
echo ""

