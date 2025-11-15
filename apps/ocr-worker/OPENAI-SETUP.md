# OpenAI / GPT-5 Nano API 配置指南

本指南将帮助你配置 OCR Worker 以使用 OpenAI 的 GPT-5 Nano API。

## 前置要求

1. 一个有效的 OpenAI API 密钥
2. Docker 已安装并运行

## 步骤 1: 获取 OpenAI API 密钥

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册或登录你的账户
3. 前往 API Keys 页面
4. 创建新的 API 密钥
5. 复制并保存你的 API 密钥（格式：`sk-...`）

## 步骤 2: 配置环境变量

在启动 Docker 容器时，设置以下环境变量：

- `USE_LLM=true` - 启用 LLM 功能
- `LLM_PROVIDER=openai` - 使用 OpenAI 作为 LLM 提供商
- `OPENAI_API_KEY` - 你的 OpenAI API 密钥
- `OPENAI_MODEL` - 模型名称（默认：`gpt-5-nano`）
- `OPENAI_API_URL` - API 端点（默认：`https://api.openai.com/v1/chat/completions`）

## 步骤 3: 启动 Docker 容器

### 使用 PowerShell (Windows)

```powershell
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=openai `
  -e OPENAI_API_KEY=your-api-key-here `
  -e OPENAI_MODEL=gpt-5-nano `
  -e OCR_TOKEN=change-me `
  pdfsaver-ocr:latest
```

### 使用 Bash (Linux/Mac)

```bash
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

docker run -d \
  --name pdfsaver-ocr \
  -p 8123:8000 \
  -e USE_LLM=true \
  -e LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=your-api-key-here \
  -e OPENAI_MODEL=gpt-5-nano \
  -e OCR_TOKEN=change-me \
  pdfsaver-ocr:latest
```

## 步骤 4: 验证配置

检查 OCR Worker 是否正常运行：

```powershell
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:8123/healthz" -UseBasicParsing | ConvertFrom-Json
```

```bash
# Linux/Mac
curl http://localhost:8123/healthz | jq
```

你应该看到类似以下的响应：

```json
{
  "status": "ok",
  "llm_available": true,
  "llm_provider": "openai",
  "llm_model": "gpt-5-nano"
}
```

## 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `USE_LLM` | 是 | `false` | 设置为 `true` 以启用 LLM 功能 |
| `LLM_PROVIDER` | 是 | `ollama` | 设置为 `openai` 以使用 OpenAI API |
| `OPENAI_API_KEY` | 是 | - | 你的 OpenAI API 密钥 |
| `OPENAI_MODEL` | 否 | `gpt-5-nano` | 要使用的模型名称 |
| `OPENAI_API_URL` | 否 | `https://api.openai.com/v1/chat/completions` | OpenAI API 端点 |

## 切换回其他 LLM 提供商

### 切换到 Ollama（本地）

```powershell
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=ollama `
  -e OLLAMA_MODEL=llama3 `
  -e OCR_TOKEN=change-me `
  pdfsaver-ocr:latest
```

### 切换到 DeepSeek

```powershell
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=deepseek `
  -e DEEPSEEK_API_KEY=your-deepseek-key `
  -e DEEPSEEK_MODEL=deepseek-chat `
  -e OCR_TOKEN=change-me `
  pdfsaver-ocr:latest
```

## 注意事项

⚠️ **隐私提示**：
- 使用 OpenAI API 时，文档内容会发送到 OpenAI 服务器
- OpenAI 可能会使用你的数据进行模型训练（除非你使用企业版或特定的隐私设置）
- 如果处理敏感文档，建议使用本地 Ollama 或查看 OpenAI 的企业隐私选项

💰 **费用**：
- OpenAI API 按使用量计费
- GPT-5 Nano 是较新的模型，请查看 OpenAI 官网了解最新定价
- 建议设置使用限额以避免意外费用

## 故障排除

### LLM 不可用

如果 `llm_available` 为 `false`：

1. 检查 `USE_LLM` 是否设置为 `true`
2. 检查 `OPENAI_API_KEY` 是否正确设置
3. 检查 API 密钥是否有效
4. 查看容器日志：`docker logs pdfsaver-ocr`

### API 错误

如果遇到 API 错误：

1. 检查你的 API 密钥是否有效
2. 检查你的账户是否有足够的余额
3. 检查模型名称是否正确（`gpt-5-nano`）
4. 查看容器日志获取详细错误信息

