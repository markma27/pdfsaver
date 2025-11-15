# Railway LLM 调试指南

## 问题：LLM API 没有被调用

如果文件名显示为 "00 YYYYMMDD - Unknown - Unknown.pdf"，说明 LLM 没有被调用或返回了空结果。

## 检查步骤

### 1. 检查 Railway 环境变量

在 Railway Dashboard 中，确认以下环境变量已设置：

**必需的环境变量：**
```
USE_LLM=true
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_MODEL=deepseek-chat
```

**重要：**
- `USE_LLM` 必须是 `true`（小写），不是 `True` 或 `TRUE`
- `LLM_PROVIDER` 必须是 `deepseek`、`openai` 或 `ollama`（小写）

### 2. 检查 Railway 日志

在 Railway Dashboard → Deploy Logs 中，查找以下日志：

**如果看到：**
```
LLM available check: False, USE_LLM=None, LLM_PROVIDER=ollama
```
说明 `USE_LLM` 环境变量未设置。

**如果看到：**
```
LLM available check: False, USE_LLM=true, LLM_PROVIDER=deepseek
```
说明 API key 可能未设置或无效。

**如果看到：**
```
LLM not available for filename.pdf. USE_LLM=true, LLM_PROVIDER=deepseek
```
说明 `check_llm_available()` 返回 False，可能是 API key 问题。

**如果看到：**
```
Calling LLM for filename.pdf...
LLM result: None
```
说明 LLM API 调用失败，返回了 None。

### 3. 验证环境变量

在 Railway Dashboard → Variables 中，确认：
- ✅ `USE_LLM` = `true`（小写）
- ✅ `LLM_PROVIDER` = `deepseek`（小写）
- ✅ `DEEPSEEK_API_KEY` 已设置且不为空
- ✅ `DEEPSEEK_MODEL` = `deepseek-chat`（或你使用的模型）

### 4. 测试健康检查端点

访问：`https://your-railway-url.railway.app/healthz`

应该返回：
```json
{
  "status": "ok",
  "llm_available": true,
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat"
}
```

如果 `llm_available` 是 `false`，说明配置有问题。

### 5. 常见问题

#### 问题 1: `USE_LLM` 未设置或值不正确

**症状：** 日志显示 `USE_LLM=None` 或 `USE_LLM=false`

**解决：** 在 Railway Variables 中设置 `USE_LLM=true`（小写）

#### 问题 2: API Key 未设置

**症状：** 日志显示 `LLM available check: False`，但 `USE_LLM=true`

**解决：** 在 Railway Variables 中设置 `DEEPSEEK_API_KEY=your-actual-api-key`

#### 问题 3: LLM Provider 不匹配

**症状：** 设置了 `DEEPSEEK_API_KEY`，但 `LLM_PROVIDER=ollama`

**解决：** 设置 `LLM_PROVIDER=deepseek`（小写）

#### 问题 4: LLM API 调用失败

**症状：** 日志显示 `Calling LLM...` 但 `LLM result: None`

**可能原因：**
- API key 无效
- API URL 错误
- 网络问题
- API 配额用完

**解决：** 检查 Railway Deploy Logs 中的详细错误信息

### 6. 重新部署

修改环境变量后，Railway 会自动重新部署。如果没有，可以手动触发：
1. Railway Dashboard → Deployments
2. 点击 "Redeploy"

### 7. 查看详细日志

在 Railway Dashboard → Deploy Logs 中，查找包含以下关键词的日志：
- `LLM available check`
- `Calling LLM`
- `LLM result`
- `Using fallback filename`

这些日志会帮助你诊断问题。

