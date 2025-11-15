# Railway 部署失败修复指南

## 错误信息

```
Dockerfile `Dockerfile` does not exist
```

## 原因

Railway 无法找到 Dockerfile，通常是因为 **Root Directory 没有正确设置**。

## 解决方案

### 步骤 1: 在 Railway 项目设置中设置 Root Directory（最重要！）

1. **进入 Railway Dashboard**
   - 访问 https://railway.app/dashboard
   - 选择你的项目

2. **进入项目设置**
   - 点击项目名称
   - 点击 "Settings"（设置）标签

3. **设置 Root Directory**
   - 找到 "Root Directory" 选项
   - 点击 "Edit" 或输入框
   - **设置为：`apps/ocr-worker`**
   - 点击 "Save" 或按 Enter

4. **验证设置**
   - 确认 Root Directory 显示为 `apps/ocr-worker`
   - 不是 `/apps/ocr-worker` 或 `apps\ocr-worker`

### 步骤 2: 确认 Dockerfile 已提交到 GitHub

1. **检查 GitHub 仓库**
   - 访问你的 GitHub 仓库
   - 确认 `apps/ocr-worker/Dockerfile` 文件存在
   - 如果不存在，需要提交并推送：
     ```bash
     git add apps/ocr-worker/Dockerfile
     git commit -m "Add Dockerfile for Railway deployment"
     git push
     ```

### 步骤 3: 重新部署

1. **触发重新部署**
   - 在 Railway Dashboard 中
   - 点击 "Deployments" 标签
   - 找到失败的部署
   - 点击 "Redeploy" 按钮
   - 或者推送新的代码到 GitHub（会自动触发部署）

### 步骤 4: 验证部署

部署成功后，检查：

1. **构建日志**
   - 应该显示 "Building Docker image..."
   - 不应该有 "Dockerfile does not exist" 错误

2. **服务状态**
   - 服务应该显示为 "Active"
   - 可以访问健康检查端点

## 如果仍然失败

### 检查清单

- [ ] Root Directory 设置为 `apps/ocr-worker`（不是其他值）
- [ ] Dockerfile 存在于 `apps/ocr-worker/Dockerfile`
- [ ] Dockerfile 已提交到 GitHub
- [ ] railway.json 存在于 `apps/ocr-worker/railway.json`
- [ ] 所有文件都已推送到 GitHub

### 使用 Railway CLI 验证

如果 Web 界面有问题，可以使用 Railway CLI：

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在项目根目录
cd apps/ocr-worker

# 链接到项目
railway link

# 检查配置
railway status

# 部署
railway up
```

### 手动指定 Dockerfile 路径

如果 Root Directory 设置正确但仍然失败，可以尝试：

1. 在 Railway 项目设置中
2. 找到 "Build" 设置
3. 手动指定 Dockerfile 路径：`Dockerfile`（相对路径，因为 Root Directory 已设置）

## 常见错误

### 错误 1: "Dockerfile does not exist"
- **原因**: Root Directory 未设置或设置错误
- **解决**: 设置 Root Directory 为 `apps/ocr-worker`

### 错误 2: "Build failed"
- **原因**: Dockerfile 语法错误或依赖问题
- **解决**: 查看构建日志，修复 Dockerfile 中的错误

### 错误 3: "Service failed to start"
- **原因**: 启动命令错误或端口配置问题
- **解决**: 检查 `railway.json` 中的 `startCommand` 和端口配置

## 验证配置

部署成功后，访问健康检查端点：

```
https://your-app.railway.app/healthz
```

应该返回：
```json
{
  "status": "ok",
  "llm_available": true,
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat"
}
```

## 环境变量配置

确保在 Railway 项目设置中添加了以下环境变量：

```
USE_LLM=true
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-chat
OCR_TOKEN=change-me
ALLOW_ORIGINS=https://your-frontend-url.vercel.app
```

**重要**: Railway 会自动设置 `PORT` 环境变量，应用会从 `$PORT` 读取端口。

