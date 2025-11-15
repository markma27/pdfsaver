# Railway 部署指南

本指南说明如何在 Railway 上部署 OCR Worker。

## 问题排查

如果遇到 "Error creating build plan with Railpack" 错误，请按照以下步骤操作：

## 方法 1: 使用 railway.json 配置文件（推荐）

1. **确保 railway.json 文件存在**
   - 文件位置：`apps/ocr-worker/railway.json`
   - 这个文件已经创建，告诉 Railway 使用 Dockerfile 构建

2. **在 Railway 中配置项目**
   - 创建新项目，选择 "Deploy from GitHub repo"
   - **重要**: 在项目设置中，设置 **Root Directory** 为 `apps/ocr-worker`
   - Railway 会自动检测 `railway.json` 和 `Dockerfile`

## 方法 2: 手动配置 Railway 设置

如果方法 1 不工作，在 Railway 项目设置中手动配置：

1. 进入项目设置 (Settings)
2. 找到 "Root Directory" 设置
3. 设置为：`apps/ocr-worker`
4. 找到 "Build Command" 设置
5. 留空（Railway 会使用 Dockerfile）
6. 找到 "Start Command" 设置
7. 设置为：`uvicorn main:app --host 0.0.0.0 --port $PORT`

## 方法 3: 使用 Railway CLI

如果 Web 界面有问题，可以使用 Railway CLI：

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在 apps/ocr-worker 目录下初始化项目
cd apps/ocr-worker
railway init

# 链接到现有项目或创建新项目
railway link

# 设置环境变量
railway variables set USE_LLM=true
railway variables set LLM_PROVIDER=deepseek
railway variables set DEEPSEEK_API_KEY=your-api-key
railway variables set DEEPSEEK_MODEL=deepseek-chat
railway variables set OCR_TOKEN=change-me

# 部署
railway up
```

## 环境变量配置

在 Railway 项目设置中添加以下环境变量：

```
USE_LLM=true
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-chat
OCR_TOKEN=change-me
ALLOW_ORIGINS=https://your-frontend-url.vercel.app
PORT=8000
```

**注意**: Railway 会自动设置 `PORT` 环境变量，应用会从 `$PORT` 读取端口。

## 验证部署

1. **检查构建日志**
   - 在 Railway Dashboard 查看构建日志
   - 确认 Dockerfile 被正确识别

2. **检查服务状态**
   - 服务应该显示为 "Active"
   - 点击服务查看日志

3. **测试健康检查**
   - Railway 会提供一个 URL，例如：`https://your-app.railway.app`
   - 访问 `https://your-app.railway.app/healthz`
   - 应该返回 JSON 响应

## 常见问题

### 问题 1: "Error creating build plan with Railpack"

**原因**: Railway 无法检测项目类型或找不到 Dockerfile

**解决方案**:
1. 确保 `railway.json` 文件存在于 `apps/ocr-worker` 目录
2. 在 Railway 项目设置中设置 Root Directory 为 `apps/ocr-worker`
3. 确保 Dockerfile 存在于 `apps/ocr-worker` 目录

### 问题 2: 构建失败 - "Dockerfile not found"

**原因**: Railway 在错误的目录查找 Dockerfile

**解决方案**:
- 在 Railway 项目设置中设置 Root Directory 为 `apps/ocr-worker`

### 问题 3: 服务启动失败

**原因**: 端口配置错误或依赖缺失

**解决方案**:
1. 确保使用 `$PORT` 环境变量（Railway 自动提供）
2. 检查 Dockerfile 中的 CMD 命令是否正确
3. 查看 Railway 日志了解具体错误

### 问题 4: 环境变量未生效

**解决方案**:
1. 在 Railway 项目设置中添加环境变量
2. 重新部署服务
3. 环境变量更改后需要重新部署才能生效

## 更新 Dockerfile 以支持 Railway

如果 Railway 仍然无法识别，可以更新 Dockerfile 的 CMD 命令：

```dockerfile
# 使用环境变量 PORT（Railway 自动提供）
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

但当前的 Dockerfile 已经使用固定端口 8000，Railway 会自动映射到 `$PORT`。

## 下一步

部署成功后：
1. 获取 Railway 提供的 URL
2. 在 Vercel 环境变量中设置 `NEXT_PUBLIC_OCR_URL`
3. 测试前端和后端的连接

