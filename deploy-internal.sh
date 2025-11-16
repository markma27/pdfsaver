#!/bin/bash

# 内部网络部署脚本

set -e

echo "🚀 PDFsaver 内部网络部署脚本"
echo "================================"

# 获取服务器 IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "检测到服务器 IP: $SERVER_IP"

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cat > .env << EOF
# 服务器配置
SERVER_IP=$SERVER_IP
WEB_PORT=3000

# OCR Worker 配置
OCR_TOKEN=$(openssl rand -hex 32)

# 允许的来源（内部网络）
# 更新为您的实际访问地址
ALLOW_ORIGIN=http://$SERVER_IP:3000
ALLOW_ORIGINS=http://$SERVER_IP:3000,http://localhost:3000,http://127.0.0.1:3000

# 前端配置
NEXT_PUBLIC_APP_ORIGIN=http://$SERVER_IP:3000

# LLM 配置（可选）
USE_LLM=false
LLM_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3
EOF
    echo "✅ .env 文件已创建"
    echo ""
    echo "⚠️  请编辑 .env 文件，更新以下配置："
    echo "   - ALLOW_ORIGINS: 添加员工访问的 URL（如：http://pdfsaver.internal:3000）"
    echo "   - NEXT_PUBLIC_APP_ORIGIN: 更新为实际访问地址"
    echo ""
    read -p "按 Enter 继续..."
fi

# 检查防火墙
echo ""
echo "检查防火墙配置..."
if command -v ufw &> /dev/null; then
    echo "检测到 UFW 防火墙"
    if ! sudo ufw status | grep -q "3000/tcp"; then
        echo "⚠️  端口 3000 未在防火墙中开放"
        read -p "是否现在开放端口 3000？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ufw allow 3000/tcp
            echo "✅ 已开放端口 3000"
        fi
    fi
elif command -v firewall-cmd &> /dev/null; then
    echo "检测到 firewalld"
    if ! sudo firewall-cmd --list-ports | grep -q "3000/tcp"; then
        echo "⚠️  端口 3000 未在防火墙中开放"
        read -p "是否现在开放端口 3000？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo firewall-cmd --permanent --add-port=3000/tcp
            sudo firewall-cmd --reload
            echo "✅ 已开放端口 3000"
        fi
    fi
fi

# 构建和启动
echo ""
echo "📦 构建 Docker 镜像..."
docker-compose build

echo ""
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
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
echo "访问信息:"
echo "  - 服务器 IP: $SERVER_IP"
echo "  - 前端访问: http://$SERVER_IP:3000"
echo "  - OCR Worker Health: http://$SERVER_IP:8123/healthz"
echo ""
echo "员工访问方式:"
echo "  1. 直接访问: http://$SERVER_IP:3000"
echo "  2. 配置 hosts 文件后访问: http://pdfsaver.internal:3000"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""

