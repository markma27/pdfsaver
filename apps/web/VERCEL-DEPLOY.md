# 部署到 Vercel 指南

本指南说明如何将 PDFsaver 前端部署到 Vercel，并配置 OCR Worker 后端。

## 架构说明

- **前端 (Next.js)**: 部署到 Vercel
- **OCR Worker (FastAPI)**: 需要单独部署到其他平台（Railway、Render、VPS 等）

## 步骤 1: 部署前端到 Vercel

### 1.1 准备代码

确保代码已推送到 GitHub 仓库。

### 1.2 在 Vercel 创建项目

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 "Add New Project"
3. 导入你的 GitHub 仓库
4. 配置项目设置：
   - **Framework Preset**: Next.js
   - **Root Directory**: `apps/web` (重要！)
   - **Build Command**: `npm run build` (或 `pnpm build`)
   - **Output Directory**: `.next`

### 1.3 配置环境变量

在 Vercel 项目设置中添加以下环境变量：

```
NEXT_PUBLIC_APP_ORIGIN=https://your-app.vercel.app
NEXT_PUBLIC_OCR_URL=https://your-ocr-worker-url.com/v1/ocr-extract
NEXT_PUBLIC_OCR_TOKEN=your-ocr-worker-token
```

**重要说明**：
- `NEXT_PUBLIC_OCR_URL`: OCR Worker 的完整 URL（需要先部署 OCR Worker）
- `NEXT_PUBLIC_OCR_TOKEN`: 如果 OCR Worker 设置了 token 验证，需要提供（如果使用默认 "change-me" 则不需要）

### 1.4 部署

点击 "Deploy" 按钮，Vercel 会自动构建并部署。

## 步骤 2: 部署 OCR Worker

OCR Worker 需要部署到支持 Python/Docker 的平台。推荐选项：

### 选项 A: Railway (推荐，最简单)

1. 访问 [Railway](https://railway.app/)
2. 创建新项目，选择 "Deploy from GitHub repo"
3. 选择 `apps/ocr-worker` 目录
4. Railway 会自动检测 Dockerfile
5. 配置环境变量：
   ```
   USE_LLM=true
   LLM_PROVIDER=deepseek
   DEEPSEEK_API_KEY=your-deepseek-api-key
   DEEPSEEK_MODEL=deepseek-chat
   OCR_TOKEN=change-me  # 或设置一个安全的 token
   ```
6. Railway 会自动分配一个 URL，例如：`https://your-app.railway.app`
7. 在 Vercel 环境变量中设置 `NEXT_PUBLIC_OCR_URL=https://your-app.railway.app/v1/ocr-extract`

### 选项 B: Render

1. 访问 [Render](https://render.com/)
2. 创建新的 "Web Service"
3. 连接 GitHub 仓库
4. 配置：
   - **Root Directory**: `apps/ocr-worker`
   - **Environment**: Docker
   - **Dockerfile Path**: `apps/ocr-worker/Dockerfile`
5. 配置环境变量（同 Railway）
6. Render 会分配 URL，更新 Vercel 环境变量

### 选项 C: VPS (自己的服务器)

参考 `apps/ocr-worker/deploy/` 目录下的部署文档。

## 步骤 3: 验证部署

1. 访问 Vercel 部署的 URL
2. 上传一个 PDF 文件测试
3. 检查浏览器控制台是否有错误
4. 如果 OCR Worker 连接失败，检查：
   - OCR Worker URL 是否正确
   - CORS 配置是否正确
   - 环境变量是否已设置

## 常见问题

### CORS 错误

如果遇到 CORS 错误，在 OCR Worker 的环境变量中设置 `ALLOW_ORIGINS`：

```
ALLOW_ORIGINS=https://your-app.vercel.app,https://your-app-git-main.vercel.app
```

或者如果使用 Railway/Render，可以在环境变量中设置多个域名（用逗号分隔）。

**注意**: 如果 `ALLOW_ORIGINS` 未设置，OCR Worker 默认允许所有来源（`*`），这在开发环境可以，但生产环境建议限制域名。

### 环境变量未生效

- Vercel 环境变量需要以 `NEXT_PUBLIC_` 开头才能在客户端使用
- 修改环境变量后需要重新部署

### OCR Worker 连接失败

1. 检查 OCR Worker 是否正常运行
2. 访问 `https://your-ocr-worker-url.com/healthz` 检查健康状态
3. 检查网络连接和防火墙设置

## 更新部署

### 更新前端

代码推送到 GitHub 后，Vercel 会自动重新部署。

### 更新 OCR Worker

根据部署平台的不同，更新方式也不同：
- **Railway/Render**: 推送代码后自动更新
- **VPS**: 需要手动拉取代码并重启服务

## 成本估算

- **Vercel**: 免费计划支持个人项目，有使用限制
- **Railway**: 免费计划有 $5 额度，超出后按使用付费
- **Render**: 免费计划有使用限制，可能需要升级

## 安全建议

1. **OCR Token**: 生产环境建议设置强密码，不要使用 "change-me"
2. **API Keys**: 确保 DeepSeek API Key 等敏感信息只存储在环境变量中
3. **HTTPS**: 确保所有服务都使用 HTTPS
4. **CORS**: 限制允许的域名，不要使用 `*`

