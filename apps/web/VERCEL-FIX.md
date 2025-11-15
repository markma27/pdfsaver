# Vercel 部署修复指南

## 问题

错误信息：`sh: line 1: cd: apps/web: No such file or directory`

**原因**: Vercel 项目设置中的 Root Directory 没有正确配置，导致 Vercel 在错误的目录执行命令。

## 解决方案

### 方法 1: 在 Vercel 项目设置中配置 Root Directory（推荐）

1. **进入 Vercel 项目设置**
   - 访问 [Vercel Dashboard](https://vercel.com/dashboard)
   - 选择你的项目
   - 点击 "Settings"（设置）

2. **配置 General 设置**
   - 找到 "Root Directory" 选项
   - 点击 "Edit"
   - 设置为：`apps/web`
   - 点击 "Save"

3. **配置 Build & Development Settings**
   - 找到 "Build Command"
   - 设置为：`npm run build`（或 `pnpm build`）
   - 找到 "Output Directory"
   - 设置为：`.next`
   - 找到 "Install Command"
   - 设置为：`npm install`（或 `pnpm install`）

4. **重新部署**
   - 点击 "Deployments"
   - 找到失败的部署
   - 点击 "Redeploy" 或等待自动重新部署

### 方法 2: 使用简化的 vercel.json（已更新）

我已经更新了 `vercel.json` 文件，移除了 `cd apps/web` 命令。现在需要：

1. **在 Vercel 项目设置中设置 Root Directory**
   - 这是**必须**的步骤
   - 设置为：`apps/web`

2. **提交并推送代码**
   ```bash
   git add apps/web/vercel.json
   git commit -m "Fix Vercel deployment configuration"
   git push
   ```

3. **Vercel 会自动重新部署**

## 验证配置

部署成功后，检查：

1. **构建日志**
   - 应该显示在 `apps/web` 目录下执行命令
   - 不应该有 "No such file or directory" 错误

2. **部署状态**
   - 应该显示 "Ready" 状态
   - 可以访问部署的 URL

## 环境变量配置

确保在 Vercel 项目设置中添加了以下环境变量：

```
NEXT_PUBLIC_APP_ORIGIN=https://your-app.vercel.app
NEXT_PUBLIC_OCR_URL=https://your-ocr-worker-url.com/v1/ocr-extract
NEXT_PUBLIC_OCR_TOKEN=change-me
```

## 如果仍然失败

1. **检查 Root Directory 设置**
   - 确认设置为 `apps/web`（不是 `/apps/web` 或 `apps\web`）

2. **检查文件结构**
   - 确认 GitHub 仓库中有 `apps/web/package.json`
   - 确认 `apps/web/vercel.json` 存在

3. **查看详细日志**
   - 在 Vercel Dashboard 查看完整的构建日志
   - 查找具体的错误信息

4. **尝试手动构建**
   - 在本地测试：`cd apps/web && npm install && npm run build`
   - 确认本地构建成功

## 常见错误

### 错误 1: "No such file or directory"
- **原因**: Root Directory 未设置或设置错误
- **解决**: 在 Vercel 设置中设置 Root Directory 为 `apps/web`

### 错误 2: "Module not found"
- **原因**: 依赖未安装
- **解决**: 确认 `package.json` 存在且依赖正确

### 错误 3: "Build failed"
- **原因**: 代码错误或配置问题
- **解决**: 查看构建日志中的具体错误信息

