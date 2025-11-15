# Railway 快速修复 - Dockerfile 找不到

## 确认信息

✅ Dockerfile 在 git 中的路径：`apps/ocr-worker/Dockerfile`  
✅ 文件已提交到 GitHub  
❌ Railway 仍然找不到文件

## 立即尝试的解决方案

### 方案 1: 重新设置 Root Directory（最可能有效）

1. **进入 Railway 项目设置**
   - Railway Dashboard → 你的项目 → Settings

2. **清除并重新设置 Root Directory**
   - 找到 "Root Directory" 字段
   - **完全删除**现有值（如果有）
   - 保存
   - 重新输入：`apps/ocr-worker`（注意：不要有前导斜杠 `/`）
   - 保存

3. **触发重新部署**
   - 点击 "Deployments"
   - 点击 "Redeploy" 或推送新代码到 GitHub

### 方案 2: 检查服务配置中的 Source 设置

1. **进入服务设置**
   - Railway Dashboard → 你的服务 → Settings
   - 找到 "Source" 部分

2. **检查配置**
   - Repository: `markma27/pdfsaver`
   - Branch: `main`
   - **Root Directory**: 应该是 `apps/ocr-worker`

3. **如果 Root Directory 显示为 `/apps/ocr-worker`**
   - 删除前导斜杠，改为 `apps/ocr-worker`
   - 保存

### 方案 3: 删除并重新创建服务

如果上述方法都不行：

1. **删除现有服务**
   - Railway Dashboard → 你的服务 → Settings
   - 滚动到底部
   - 点击 "Delete Service"

2. **创建新服务**
   - 点击 "New" → "GitHub Repo"
   - 选择 `markma27/pdfsaver`
   - 在配置界面：
     - **Root Directory**: `apps/ocr-worker`
     - **Framework**: Docker
   - 创建服务

3. **配置环境变量**
   - 重新添加所有环境变量

### 方案 4: 使用 Railway CLI 强制重新部署

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在项目根目录
cd apps/ocr-worker

# 链接到项目
railway link

# 强制重新部署
railway up --detach
```

## 验证 GitHub 仓库

访问以下 URL 确认文件存在：

```
https://github.com/markma27/pdfsaver/tree/main/apps/ocr-worker
```

应该能看到：
- ✅ Dockerfile
- ✅ railway.json
- ✅ main.py
- ✅ llm_helper.py
- ✅ requirements.txt

## 如果文件不在 GitHub

如果 GitHub 上看不到 Dockerfile，需要提交：

```bash
# 在项目根目录
git add apps/ocr-worker/Dockerfile
git add apps/ocr-worker/railway.json
git commit -m "Add Dockerfile and railway.json for Railway"
git push
```

## 检查 Railway 构建日志

在 Railway Dashboard 中查看构建日志，查找：

1. **克隆阶段**
   - 应该显示：`Cloning github.com/markma27/pdfsaver`
   - 检查是否有错误

2. **文件检测阶段**
   - Railway 应该检测到 Dockerfile
   - 如果显示 "No Dockerfile found"，说明 Root Directory 设置有问题

3. **构建阶段**
   - 如果找到 Dockerfile，应该显示 "Building Docker image..."

## 常见错误配置

❌ **错误**: Root Directory = `/apps/ocr-worker`（有前导斜杠）  
✅ **正确**: Root Directory = `apps/ocr-worker`（无前导斜杠）

❌ **错误**: Root Directory = `apps\ocr-worker`（Windows 路径分隔符）  
✅ **正确**: Root Directory = `apps/ocr-worker`（Unix 路径分隔符）

❌ **错误**: Root Directory = `apps/ocr-worker/`（有尾随斜杠）  
✅ **正确**: Root Directory = `apps/ocr-worker`（无尾随斜杠）

## 最终检查清单

在 Railway 重新部署前，确认：

- [ ] GitHub 仓库中有 `apps/ocr-worker/Dockerfile`
- [ ] GitHub 仓库中有 `apps/ocr-worker/railway.json`
- [ ] Railway Root Directory 设置为 `apps/ocr-worker`（无斜杠）
- [ ] Railway Builder 设置为 `Dockerfile`
- [ ] Railway Dockerfile path 设置为 `Dockerfile`（相对路径）

