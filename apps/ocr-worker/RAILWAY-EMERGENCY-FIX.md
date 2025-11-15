# Railway 紧急修复 - Dockerfile 找不到

## 快速诊断

### 步骤 1: 验证 GitHub 仓库

访问以下 URL 确认文件存在：

```
https://github.com/markma27/pdfsaver/blob/main/apps/ocr-worker/Dockerfile
```

**如果返回 404**：
- Dockerfile 没有提交到 GitHub
- 需要执行：
  ```bash
  git add apps/ocr-worker/Dockerfile
  git commit -m "Add Dockerfile for Railway"
  git push
  ```

**如果文件存在**：
- 继续步骤 2

### 步骤 2: Railway 配置修复（按顺序执行）

#### 方法 A: 清除并重新设置 Root Directory

1. **进入 Railway Dashboard**
   - https://railway.app/dashboard
   - 选择你的项目 → 选择服务

2. **进入服务设置**
   - 点击服务名称
   - 点击 "Settings" 标签

3. **清除 Root Directory**
   - 找到 "Source" 部分
   - 找到 "Root Directory" 字段
   - **完全删除**所有内容（留空）
   - 点击 "Save" 或按 Enter

4. **等待几秒钟**

5. **重新设置 Root Directory**
   - 在同一个字段中
   - 输入：`apps/ocr-worker`
   - **不要**使用 `/apps/ocr-worker` 或 `apps\ocr-worker`
   - 点击 "Save"

6. **触发重新部署**
   - 点击 "Deployments" 标签
   - 点击 "Redeploy" 按钮

#### 方法 B: 删除并重新创建服务（如果方法 A 失败）

1. **删除现有服务**
   - Railway Dashboard → 你的服务 → Settings
   - 滚动到底部
   - 点击 "Delete Service"
   - 确认删除

2. **创建新服务**
   - 在项目中点击 "New"
   - 选择 "GitHub Repo"
   - 选择 `markma27/pdfsaver` 仓库
   - 在配置界面：
     - **Root Directory**: 输入 `apps/ocr-worker`
     - **Framework**: 选择 "Docker" 或让 Railway 自动检测
   - 点击 "Deploy"

3. **配置环境变量**
   - 重新添加所有环境变量：
     ```
     USE_LLM=true
     LLM_PROVIDER=deepseek
     DEEPSEEK_API_KEY=sk-b3de873d6f124918888e73f6f7f87e3b
     DEEPSEEK_MODEL=deepseek-chat
     OCR_TOKEN=change-me
     ALLOW_ORIGINS=https://your-vercel-url.vercel.app
     ```

### 步骤 3: 使用 Railway CLI（如果 Web 界面有问题）

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在项目根目录
cd apps/ocr-worker

# 初始化项目
railway init

# 链接到现有项目（或创建新项目）
railway link

# 检查配置
railway status

# 查看文件
railway logs

# 强制重新部署
railway up
```

## 验证配置

部署成功后，检查：

1. **构建日志**
   - 应该显示 "Building Docker image..."
   - 不应该有 "Dockerfile does not exist" 错误

2. **服务状态**
   - 服务应该显示为 "Active"

3. **健康检查**
   - 访问：`https://your-app.railway.app/healthz`
   - 应该返回 JSON 响应

## 常见错误配置

❌ **错误 1**: Root Directory = `/apps/ocr-worker`（有前导斜杠）  
✅ **正确**: Root Directory = `apps/ocr-worker`（无前导斜杠）

❌ **错误 2**: Root Directory = `apps\ocr-worker`（Windows 路径）  
✅ **正确**: Root Directory = `apps/ocr-worker`（Unix 路径）

❌ **错误 3**: Root Directory = `apps/ocr-worker/`（有尾随斜杠）  
✅ **正确**: Root Directory = `apps/ocr-worker`（无尾随斜杠）

❌ **错误 4**: Root Directory 在项目级别设置，但服务级别没有设置  
✅ **正确**: 在**服务级别**的 Settings 中设置 Root Directory

## 如果所有方法都失败

1. **检查 Railway 服务日志**
   - 查看完整的构建日志
   - 查找具体的错误信息

2. **联系 Railway 支持**
   - 提供部署 ID
   - 提供错误日志截图
   - 说明已尝试的步骤

3. **临时解决方案**
   - 使用其他平台（Render、Fly.io 等）
   - 或使用本地部署（见 LOCAL-DEPLOY.md）

