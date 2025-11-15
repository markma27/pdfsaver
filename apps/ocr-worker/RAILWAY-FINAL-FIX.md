# Railway Dockerfile 找不到 - 最终解决方案

## 问题确认

Railway 错误：`Dockerfile 'Dockerfile' does not exist`

即使：
- ✅ Dockerfile 在 GitHub: `apps/ocr-worker/Dockerfile`
- ✅ Root Directory 设置为: `apps/ocr-worker`
- ✅ railway.json 配置正确

## 根本原因

Railway 的 Root Directory 设置可能：
1. 格式不正确（有前导/尾随斜杠）
2. 在错误的位置设置（项目级别 vs 服务级别）
3. 缓存问题

## 解决方案（按顺序尝试）

### 方案 1: 在服务级别设置 Root Directory（最重要！）

**关键**：Root Directory 必须在**服务级别**设置，不是项目级别！

1. **进入 Railway Dashboard**
   - https://railway.app/dashboard
   - 选择你的**项目**
   - 选择你的**服务**（不是项目设置）

2. **进入服务设置**
   - 点击服务名称
   - 点击 "Settings" 标签
   - **不是**项目级别的 Settings

3. **找到 Source 部分**
   - 在 Settings 页面
   - 找到 "Source" 或 "Repository" 部分
   - 找到 "Root Directory" 字段

4. **清除并重新设置**
   - **完全删除** Root Directory 字段中的所有内容
   - 点击 "Save" 或按 Enter
   - **等待 5 秒**
   - 重新输入：`apps/ocr-worker`
   - **确保**：没有前导斜杠 `/`，没有尾随斜杠 `/`
   - 点击 "Save"

5. **触发重新部署**
   - 点击 "Deployments" 标签
   - 点击 "Redeploy" 按钮

### 方案 2: 删除并重新创建服务（如果方案 1 失败）

这是最可靠的方法：

1. **删除现有服务**
   - Railway Dashboard → 你的服务 → Settings
   - 滚动到底部
   - 点击 "Delete Service"
   - 确认删除

2. **创建新服务**
   - 在项目中点击 "New" 或 "+"
   - 选择 "GitHub Repo"
   - 选择 `markma27/pdfsaver` 仓库
   - 在出现的配置界面中：
     - **Root Directory**: 输入 `apps/ocr-worker`
     - **Framework**: 选择 "Docker" 或让 Railway 自动检测
   - 点击 "Deploy"

3. **配置环境变量**
   - 进入新服务的 Settings
   - 找到 "Variables" 部分
   - 添加以下环境变量：
     ```
     USE_LLM=true
     LLM_PROVIDER=deepseek
     DEEPSEEK_API_KEY=sk-b3de873d6f124918888e73f6f7f87e3b
     DEEPSEEK_MODEL=deepseek-chat
     OCR_TOKEN=change-me
     ALLOW_ORIGINS=https://your-vercel-url.vercel.app
     ```

### 方案 3: 使用 Railway CLI（如果 Web 界面有问题）

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在项目根目录
cd apps/ocr-worker

# 初始化项目
railway init

# 链接到现有项目
railway link

# 检查配置
railway status

# 查看文件列表
railway logs

# 强制重新部署
railway up --detach
```

## 验证步骤

### 1. 验证 GitHub 仓库

访问并确认文件存在：
```
https://github.com/markma27/pdfsaver/tree/main/apps/ocr-worker
```

应该能看到：
- ✅ Dockerfile
- ✅ railway.json
- ✅ main.py
- ✅ llm_helper.py
- ✅ requirements.txt

### 2. 验证 Railway 配置

在 Railway Dashboard 中检查：

1. **服务级别的 Settings**
   - Source → Root Directory: `apps/ocr-worker`
   - Build → Builder: `Dockerfile`
   - Build → Dockerfile Path: `Dockerfile`（或留空）

2. **构建日志**
   - 应该显示 "Building Docker image..."
   - 不应该有 "Dockerfile does not exist" 错误

## 常见错误配置

❌ **错误**: Root Directory = `/apps/ocr-worker`（有前导斜杠）  
✅ **正确**: Root Directory = `apps/ocr-worker`（无前导斜杠）

❌ **错误**: Root Directory = `apps\ocr-worker`（Windows 路径）  
✅ **正确**: Root Directory = `apps/ocr-worker`（Unix 路径）

❌ **错误**: Root Directory = `apps/ocr-worker/`（有尾随斜杠）  
✅ **正确**: Root Directory = `apps/ocr-worker`（无尾随斜杠）

❌ **错误**: 在项目级别设置 Root Directory  
✅ **正确**: 在**服务级别**设置 Root Directory

## 如果所有方法都失败

1. **检查 Railway 服务日志**
   - 查看完整的构建日志
   - 查找具体的错误信息

2. **尝试其他平台**
   - Render.com（类似 Railway）
   - Fly.io
   - 或使用本地部署（见 LOCAL-DEPLOY.md）

3. **联系 Railway 支持**
   - 提供部署 ID
   - 提供错误日志截图
   - 说明已尝试的步骤

## 调试技巧

在 Railway 构建日志中查找：

1. **克隆阶段**
   ```
   Cloning github.com/markma27/pdfsaver
   ```
   - 确认仓库克隆成功

2. **文件检测阶段**
   ```
   Detected Dockerfile
   ```
   - 如果看到这个，说明找到了文件

3. **构建阶段**
   ```
   Building Docker image...
   ```
   - 如果看到这个，说明构建开始

如果看到 "Dockerfile does not exist"，说明：
- Root Directory 设置不正确
- 或文件不在 GitHub 上
- 或 Railway 缓存问题

