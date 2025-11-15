# DeepSeek API 配置指南

本指南说明如何在 OCR Worker 中使用 DeepSeek API 在线服务。

## 为什么使用 DeepSeek API？

- **无需本地部署**：不需要安装 Ollama 或下载模型
- **更好的性能**：DeepSeek 提供高性能的在线 API
- **易于使用**：只需配置 API Key 即可使用
- **适合生产环境**：稳定的在线服务

## 获取 DeepSeek API Key

1. 访问 [DeepSeek 官网](https://www.deepseek.com/)
2. 注册账号并登录
3. 进入 API 管理页面
4. 创建新的 API Key
5. 复制 API Key（格式类似：`sk-xxxxxxxxxxxxxxxxxxxxx`）

## 配置环境变量

### 方式 1：Docker 运行时设置

```powershell
docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=deepseek `
  -e DEEPSEEK_API_KEY=sk-your-api-key-here `
  -e DEEPSEEK_MODEL=deepseek-chat `
  -e OCR_TOKEN=change-me `
  pdfsaver-ocr:latest
```

### 方式 2：使用 PowerShell 脚本

创建或修改启动脚本，添加以下环境变量：

```powershell
$env:USE_LLM="true"
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="sk-your-api-key-here"
$env:DEEPSEEK_MODEL="deepseek-chat"
```

## 环境变量说明

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `USE_LLM` | 启用 LLM 功能 | `false` | 是 |
| `LLM_PROVIDER` | LLM 提供商：`ollama` 或 `deepseek` | `ollama` | 是 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 无 | 使用 DeepSeek 时必需 |
| `DEEPSEEK_API_URL` | DeepSeek API 端点 | `https://api.deepseek.com/v1/chat/completions` | 否 |
| `DEEPSEEK_MODEL` | DeepSeek 模型名称 | `deepseek-chat` | 否 |

## 可用的 DeepSeek 模型

- `deepseek-chat`：通用对话模型（推荐）
- `deepseek-coder`：代码专用模型
- 其他模型请参考 DeepSeek 官方文档

## 验证配置

启动容器后，检查健康状态：

```powershell
curl http://localhost:8123/healthz
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

## 从 Ollama 切换到 DeepSeek

如果之前使用 Ollama，切换到 DeepSeek 只需：

1. 停止当前容器
2. 使用新的环境变量启动容器（设置 `LLM_PROVIDER=deepseek` 和 `DEEPSEEK_API_KEY`）
3. 重启容器

## 隐私保护

✅ **数据隐私保护已启用**：
- 代码已自动添加 `X-Data-Usage-Opt-Out: true` HTTP 头
- 这确保你的文档数据不会被 DeepSeek 存储或用于模型训练
- 所有 API 请求都包含此隐私保护头

⚠️ **注意事项**：
- 使用 DeepSeek API 时，文档内容仍会发送到 DeepSeek 服务器进行处理
- 但通过 `X-Data-Usage-Opt-Out` 头，数据不会被保留或用于训练
- 如果处理高度敏感文档，建议使用本地 Ollama

💰 **费用**：
- DeepSeek API 按使用量计费
- 请查看 DeepSeek 官网了解最新定价
- 建议设置使用限额以避免意外费用

## 故障排除

### API Key 无效
- 检查 API Key 是否正确
- 确认 API Key 未过期
- 验证 API Key 有足够的权限

### 连接超时
- 检查网络连接
- 确认 DeepSeek API 服务正常
- 尝试增加超时时间

### 返回错误
- 查看容器日志：`docker logs pdfsaver-ocr`
- 检查 API 配额是否用完
- 验证模型名称是否正确

## 示例：完整的 Docker 启动命令

```powershell
docker stop pdfsaver-ocr 2>$null
docker rm pdfsaver-ocr 2>$null

docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=deepseek `
  -e DEEPSEEK_API_KEY=sk-your-actual-api-key-here `
  -e DEEPSEEK_MODEL=deepseek-chat `
  -e OCR_TOKEN=change-me `
  pdfsaver-ocr:latest
```

## 切换回 Ollama

如果想切换回本地 Ollama：

```powershell
docker stop pdfsaver-ocr
docker rm pdfsaver-ocr

docker run -d `
  --name pdfsaver-ocr `
  -p 8123:8000 `
  -e USE_LLM=true `
  -e LLM_PROVIDER=ollama `
  -e OLLAMA_URL=http://host.docker.internal:11434 `
  -e OLLAMA_MODEL=llama3 `
  -e OCR_TOKEN=change-me `
  pdfsaver-ocr:latest
```

