# Railway Dockerfile 找不到 - 详细排查指南

## 错误信息

```
Dockerfile `Dockerfile` does not exist
```

## 当前配置（从错误信息看）

- **Path**: `/apps/ocr-worker` ✅
- **Builder**: `Dockerfile` ✅
- **Dockerfile path**: `Dockerfile` ✅
- **Root Directory**: 应该设置为 `apps/ocr-worker`

## 排查步骤

### 步骤 1: 验证 GitHub 仓库中的文件

1. **访问 GitHub 仓库**
   - 打开：https://github.com/markma27/pdfsaver
   - 导航到：`apps/ocr-worker/Dockerfile`
   - **确认文件存在且可见**

2. **如果文件不存在**
   ```bash
   # 在项目根目录
   git add apps/ocr-worker/Dockerfile
   git commit -m "Add Dockerfile for Railway deployment"
   git push
   ```

### 步骤 2: 检查 Railway Root Directory 设置

1. **进入 Railway 项目设置**
   - Railway Dashboard → 你的项目 → Settings

2. **检查 Root Directory**
   - 应该设置为：`apps/ocr-worker`
   - **不要**使用：`/apps/ocr-worker` 或 `apps\ocr-worker`

3. **如果设置不正确**
   - 清空 Root Directory（留空）
   - 保存
   - 重新设置为：`apps/ocr-worker`
   - 保存

### 步骤 3: 尝试不同的 Root Directory 配置

如果 `apps/ocr-worker` 不工作，尝试：

**选项 A: 清空 Root Directory**
- 在 Railway Settings 中
- 将 Root Directory 设置为空（留空）
- 在 "Dockerfile path" 中设置为：`apps/ocr-worker/Dockerfile`

**选项 B: 使用相对路径**
- Root Directory: 留空
- Dockerfile path: `apps/ocr-worker/Dockerfile`

**选项 C: 检查 Railway 服务配置**
- 在 Railway Dashboard 中
- 选择你的服务
- 点击 "Settings"
- 检查 "Source" 部分
- 确认 "Root Directory" 设置

### 步骤 4: 清除 Railway 缓存

1. **删除并重新创建服务**（如果其他方法都不行）
   - 在 Railway Dashboard 中
   - 删除现有服务
   - 创建新服务
   - 重新连接 GitHub 仓库
   - 设置 Root Directory 为 `apps/ocr-worker`

### 步骤 5: 使用 Railway CLI 验证

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在项目根目录
cd apps/ocr-worker

# 初始化并链接项目
railway init
railway link

# 检查配置
railway status

# 查看文件
railway logs
```

### 步骤 6: 验证文件结构

在本地验证文件结构：

```bash
# 在项目根目录
ls -la apps/ocr-worker/Dockerfile
cat apps/ocr-worker/Dockerfile  # 应该能看到内容
```

### 步骤 7: 检查 .dockerignore

如果存在 `.dockerignore` 文件，确保它没有排除 Dockerfile：

```bash
# 检查是否有 .dockerignore
cat apps/ocr-worker/.dockerignore
```

## 快速修复尝试

### 方法 1: 重新设置 Root Directory

1. 在 Railway Settings 中
2. 将 Root Directory **清空**（删除所有内容）
3. 保存
4. 重新设置为：`apps/ocr-worker`
5. 保存
6. 触发重新部署

### 方法 2: 使用完整路径

1. 在 Railway Settings 中
2. Root Directory: 留空
3. 在 Build 设置中，Dockerfile path: `apps/ocr-worker/Dockerfile`

### 方法 3: 检查服务配置

从错误信息看，配置显示：
- Path: `/apps/ocr-worker` - 这看起来像是绝对路径
- 尝试改为相对路径：`apps/ocr-worker`（不带前导斜杠）

## 验证 GitHub 仓库

访问以下 URL 确认文件存在：

```
https://github.com/markma27/pdfsaver/blob/main/apps/ocr-worker/Dockerfile
```

如果返回 404，说明文件不在 GitHub 上，需要提交并推送。

## 如果所有方法都失败

1. **创建新的 Railway 服务**
   - 删除现有服务
   - 创建新服务
   - 重新连接 GitHub
   - 在创建时直接设置 Root Directory

2. **使用 Railway 模板**
   - 选择 "Deploy from GitHub repo"
   - 在配置界面直接设置 Root Directory
   - 不要依赖自动检测

3. **联系 Railway 支持**
   - 提供部署 ID
   - 提供错误日志
   - 说明已尝试的步骤

