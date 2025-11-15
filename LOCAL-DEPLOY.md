# 本地部署指南 - 让员工通过 URL 访问

本指南说明如何在本地部署 PDFsaver，并让员工通过 URL 访问。

## 架构说明

- **前端 (Next.js)**: 运行在本地，通过内网 IP 或内网穿透工具暴露
- **OCR Worker (FastAPI)**: 运行在本地 Docker 容器中

## 方案选择

### 方案 A: 内网访问（推荐，如果员工在同一网络）

如果员工都在同一个局域网（办公室网络），可以直接使用内网 IP 访问。

### 方案 B: 内网穿透（如果员工不在同一网络）

如果员工需要从外部网络访问，需要使用内网穿透工具（如 ngrok、frp、ZeroTier 等）。

## 步骤 1: 部署 OCR Worker

### 1.1 启动 OCR Worker Docker 容器

```powershell
# 在项目根目录
cd apps/ocr-worker

# 构建并启动容器
docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=deepseek `
  -e DEEPSEEK_API_KEY=your-deepseek-api-key `
  -e DEEPSEEK_MODEL=deepseek-chat `
  -e OCR_TOKEN=change-me `
  -e ALLOW_ORIGINS=http://localhost:3000,http://your-local-ip:3000 `
  pdfsaver-ocr:latest
```

### 1.2 获取本地 IP 地址

**Windows:**
```powershell
ipconfig
# 查找 "IPv4 地址"，例如：192.168.1.100
```

**Mac/Linux:**
```bash
ifconfig
# 或
ip addr show
```

### 1.3 测试 OCR Worker

在浏览器访问：`http://localhost:8123/healthz`

应该看到 JSON 响应，确认服务正常运行。

## 步骤 2: 部署前端

### 2.1 安装依赖

```powershell
cd apps/web
npm install
# 或
pnpm install
```

### 2.2 配置环境变量

创建 `apps/web/.env.local` 文件：

```bash
# 本地 IP 地址（替换为你的实际 IP）
NEXT_PUBLIC_APP_ORIGIN=http://192.168.1.100:3000

# OCR Worker URL（使用本地 IP）
NEXT_PUBLIC_OCR_URL=http://192.168.1.100:8123/v1/ocr-extract

# OCR Token（如果设置了）
NEXT_PUBLIC_OCR_TOKEN=change-me
```

**重要**: 将 `192.168.1.100` 替换为你的实际本地 IP 地址。

### 2.3 启动前端

```powershell
cd apps/web
npm run dev
# 或
pnpm dev
```

前端将在 `http://localhost:3000` 启动。

### 2.4 更新 OCR Worker CORS 配置

如果使用内网 IP 访问，需要更新 OCR Worker 的 `ALLOW_ORIGINS`：

```powershell
# 停止并删除现有容器
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

# 重新启动，添加内网 IP 到 ALLOW_ORIGINS
docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=deepseek `
  -e DEEPSEEK_API_KEY=your-deepseek-api-key `
  -e DEEPSEEK_MODEL=deepseek-chat `
  -e OCR_TOKEN=change-me `
  -e ALLOW_ORIGINS=http://localhost:3000,http://192.168.1.100:3000 `
  pdfsaver-ocr:latest
```

## 步骤 3: 让员工访问

### 方案 A: 内网访问（员工在同一网络）

1. **获取你的本地 IP 地址**（见步骤 1.2）
2. **确保防火墙允许端口 3000 和 8123**
3. **告诉员工访问**: `http://你的IP:3000`
   - 例如：`http://192.168.1.100:3000`

**Windows 防火墙配置:**
```powershell
# 允许端口 3000 (前端)
New-NetFirewallRule -DisplayName "PDFsaver Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# 允许端口 8123 (OCR Worker)
New-NetFirewallRule -DisplayName "PDFsaver OCR Worker" -Direction Inbound -LocalPort 8123 -Protocol TCP -Action Allow
```

### 方案 B: 内网穿透（员工不在同一网络）

#### 选项 1: 使用 ngrok（最简单）

1. **安装 ngrok**
   - 访问 https://ngrok.com/
   - 注册账号并下载 ngrok
   - 获取 authtoken

2. **启动 ngrok**
```powershell
# 为前端创建隧道
ngrok http 3000

# 会显示类似：
# Forwarding  https://abc123.ngrok.io -> http://localhost:3000
```

3. **更新环境变量**
   - 在 `apps/web/.env.local` 中更新 `NEXT_PUBLIC_APP_ORIGIN` 为 ngrok URL
   - 更新 OCR Worker 的 `ALLOW_ORIGINS` 包含 ngrok URL

4. **为 OCR Worker 创建另一个隧道**（如果需要）
```powershell
# 新开一个终端
ngrok http 8123
```

5. **告诉员工访问**: ngrok 提供的 URL（例如：`https://abc123.ngrok.io`）

**注意**: ngrok 免费版每次重启 URL 会变化。付费版可以固定域名。

#### 选项 2: 使用 Cloudflare Tunnel（免费，稳定）

1. **安装 cloudflared**
   - 访问 https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
   - 下载并安装

2. **创建隧道**
```powershell
# 登录 Cloudflare
cloudflared tunnel login

# 创建隧道
cloudflared tunnel create pdfsaver

# 运行隧道（前端）
cloudflared tunnel --url http://localhost:3000
```

3. **配置路由**（可选，用于固定域名）
   - 在 Cloudflare Dashboard 配置 DNS 和路由

#### 选项 3: 使用 frp（自建服务器）

如果你有自己的服务器，可以使用 frp 进行内网穿透。

## 步骤 4: 验证部署

1. **本地测试**
   - 访问 `http://localhost:3000`
   - 上传一个 PDF 文件测试

2. **内网测试**
   - 在同一网络的另一台设备访问 `http://你的IP:3000`
   - 测试上传和处理功能

3. **检查 OCR Worker**
   - 访问 `http://你的IP:8123/healthz`
   - 确认返回健康状态

## 常见问题

### 端口被占用

如果端口 3000 或 8123 被占用，可以修改：

**前端端口:**
```powershell
# 修改 package.json 中的 dev 脚本
"dev": "next dev -p 3001"
```

**OCR Worker 端口:**
```powershell
# 修改 Docker 端口映射
docker run -d --name pdfsaver-ocr -p 8124:8000 ...
```

### CORS 错误

确保 OCR Worker 的 `ALLOW_ORIGINS` 包含：
- 前端访问的 URL（包括 IP 地址和域名）
- 如果使用 ngrok，包含 ngrok URL

### 防火墙阻止访问

**Windows:**
```powershell
# 检查防火墙规则
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*PDFsaver*"}

# 如果规则不存在，创建规则（见步骤 3）
```

**Mac:**
- 系统设置 > 网络 > 防火墙 > 选项
- 允许 Node.js 和 Docker 的入站连接

### IP 地址变化

如果使用 DHCP，IP 地址可能会变化。解决方案：

1. **设置静态 IP**（推荐）
   - 在路由器或系统网络设置中配置静态 IP

2. **使用域名**
   - 在内网 DNS 服务器配置域名指向你的 IP
   - 或使用 mDNS（.local 域名）

3. **使用内网穿透工具**
   - ngrok、Cloudflare Tunnel 等提供固定域名

## 性能优化

### 使用生产模式

前端可以使用生产模式提高性能：

```powershell
cd apps/web
npm run build
npm start
```

生产模式需要设置 `NODE_ENV=production`。

### 限制并发

如果多员工同时使用，可能需要：
- 增加 OCR Worker 的资源限制
- 使用负载均衡（多个 OCR Worker 实例）
- 限制前端并发处理数量

## 安全建议

1. **使用强密码**
   - 设置 `OCR_TOKEN` 为强密码，不要使用 "change-me"

2. **限制访问**
   - 使用防火墙限制只允许特定 IP 访问
   - 或使用 VPN 让员工连接

3. **HTTPS**
   - 如果使用内网穿透工具，确保使用 HTTPS
   - 本地部署可以使用自签名证书

4. **定期更新**
   - 定期更新依赖和 Docker 镜像
   - 关注安全公告

## 维护

### 查看日志

**OCR Worker:**
```powershell
docker logs pdfsaver-ocr
docker logs -f pdfsaver-ocr  # 实时查看
```

**前端:**
- 查看终端输出
- 或使用 PM2 等进程管理器

### 重启服务

**OCR Worker:**
```powershell
docker restart pdfsaver-ocr
```

**前端:**
- 停止并重新运行 `npm run dev`

### 更新代码

1. 拉取最新代码
2. 重新构建 Docker 镜像（如果 OCR Worker 有更新）
3. 重启服务

## 下一步

部署完成后：
1. 测试所有功能
2. 告诉员工访问 URL
3. 收集反馈
4. 根据需要优化配置

