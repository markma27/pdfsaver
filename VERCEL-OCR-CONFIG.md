# Vercel OCR Worker 配置指南

## 问题：Failed to fetch

当前端显示 "Failed to fetch" 错误时，通常是因为：

1. **Vercel 环境变量未配置**：`NEXT_PUBLIC_OCR_URL` 未设置或设置错误
2. **Railway OCR Worker 未运行**：后端服务未部署或部署失败
3. **CORS 配置问题**：OCR Worker 的 CORS 设置不允许 Vercel 域名访问

## 解决步骤

### 步骤 1: 确认 Railway OCR Worker 已部署

1. **检查 Railway 部署状态**
   - 访问 [Railway Dashboard](https://railway.app/dashboard)
   - 确认 OCR Worker 服务状态为 "Active"
   - 检查构建日志，确认没有错误

2. **获取 Railway OCR Worker URL**
   - 在 Railway 服务中，找到 "Networking" 或 "Settings"
   - 找到 "Public Domain" 或 "Generate Domain"
   - 复制完整的 URL，例如：`https://your-app.railway.app`

3. **测试 OCR Worker 健康检查**
   - 访问：`https://your-app.railway.app/healthz`
   - 应该返回 JSON 响应：
     ```json
     {
       "status": "ok",
       "llm_available": true,
       "llm_provider": "deepseek",
       "llm_model": "deepseek-chat"
     }
     ```

### 步骤 2: 在 Vercel 中配置环境变量

1. **进入 Vercel 项目设置**
   - 访问 [Vercel Dashboard](https://vercel.com/dashboard)
   - 选择你的项目（pdfsaver）
   - 点击 "Settings"
   - 点击 "Environment Variables"

2. **添加以下环境变量**

   ```
   NEXT_PUBLIC_OCR_URL=https://your-railway-url.railway.app/v1/ocr-extract
   NEXT_PUBLIC_OCR_TOKEN=change-me
   ```

   **重要**：
   - 将 `your-railway-url.railway.app` 替换为你的实际 Railway URL
   - URL 必须以 `/v1/ocr-extract` 结尾
   - 如果 OCR Worker 使用默认 token "change-me"，则 `NEXT_PUBLIC_OCR_TOKEN` 可以设置为 "change-me" 或留空

3. **保存并重新部署**
   - 点击 "Save"
   - 进入 "Deployments" 标签
   - 点击最新的部署，然后点击 "Redeploy"

### 步骤 3: 配置 Railway OCR Worker 的 CORS

确保 Railway OCR Worker 允许 Vercel 域名访问：

1. **在 Railway 环境变量中添加**：
   ```
   ALLOW_ORIGINS=https://pdfsaver.vercel.app,https://your-vercel-url.vercel.app
   ```

   或者允许所有来源（仅用于开发）：
   ```
   ALLOW_ORIGINS=*
   ```

2. **重新部署 Railway 服务**

### 步骤 4: 验证配置

1. **检查浏览器控制台**
   - 打开浏览器开发者工具（F12）
   - 查看 Console 标签
   - 查看 Network 标签，找到失败的请求
   - 检查错误信息

2. **常见错误和解决方案**

   - **"Failed to fetch"**：
     - 检查 `NEXT_PUBLIC_OCR_URL` 是否正确
     - 检查 Railway 服务是否运行
     - 检查 CORS 配置

   - **"403 Forbidden"**：
     - 检查 `NEXT_PUBLIC_OCR_TOKEN` 是否正确
     - 检查 Railway 的 `OCR_TOKEN` 环境变量

   - **"CORS error"**：
     - 检查 Railway 的 `ALLOW_ORIGINS` 环境变量
     - 确保包含 Vercel 域名

## 快速检查清单

- [ ] Railway OCR Worker 服务状态为 "Active"
- [ ] Railway OCR Worker URL 可以访问 `/healthz` 端点
- [ ] Vercel 环境变量 `NEXT_PUBLIC_OCR_URL` 已设置且正确
- [ ] Vercel 环境变量 `NEXT_PUBLIC_OCR_TOKEN` 已设置（如果需要）
- [ ] Railway 环境变量 `ALLOW_ORIGINS` 包含 Vercel 域名
- [ ] 已重新部署 Vercel 和 Railway 服务

## 测试步骤

1. 访问 Vercel 部署的网站
2. 上传一个 PDF 文件
3. 检查是否成功处理（不应该显示 "Failed to fetch"）
4. 如果仍然失败，检查浏览器控制台的错误信息

## 如果仍然失败

1. **检查 Railway 日志**
   - 在 Railway Dashboard 查看服务日志
   - 查找错误信息

2. **检查 Vercel 构建日志**
   - 在 Vercel Dashboard 查看部署日志
   - 确认环境变量已正确注入

3. **测试 OCR Worker API 直接调用**
   ```bash
   curl -X POST https://your-railway-url.railway.app/v1/ocr-extract \
     -H "Authorization: Bearer change-me" \
     -F "file=@test.pdf"
   ```

