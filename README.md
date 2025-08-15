# 语音转写 MCP 服务

基于腾讯云的语音转写服务，使用 FastMCP 框架实现，支持说话人分离和情感识别。

## 功能特点

- 基于 FastMCP 框架
- 支持多种音频格式（mp3, wav, ogg, flac）
- 说话人分离
- 情感识别
- 并发控制
- 完整的错误处理
- 可配置的服务参数
- API 限流
- 监控指标
- 健康检查

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

### 2. 本地测试

```python
from modelscope.mcp import MCPClient

async def test_transcribe():
    client = MCPClient()
    
    # 调用服务
    response = await client.invoke(
        "voice-transcription-service",
        "/transcribe",
        files={"file": open("audio.mp3", "rb")},
        data={
            "secret_id": "your_secret_id",
            "secret_key": "your_secret_key",
            "cos_bucket": "your_bucket",
            "cos_region": "ap-nanjing"
        }
    )
    
    print(response)
```

### 3. 部署到 ModelScope

```bash
# 安装 ModelScope CLI
pip install modelscope-cli

# 登录
modelscope login

# 部署服务
modelscope deploy mcp_service.py
```

## MCP 服务器配置

### 基本配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 服务名称 | SERVICE_NAME | voice-transcription-service | 服务标识 |
| 服务版本 | SERVICE_VERSION | 1.0.0 | 服务版本号 |
| 监听地址 | MCP_HOST | 0.0.0.0 | 服务监听地址 |
| 端口 | MCP_PORT | 8080 | 服务端口 |
| 工作进程数 | MCP_WORKERS | 4 | 并发工作进程数 |
| 超时时间 | MCP_TIMEOUT | 300 | 请求超时时间(秒) |

### 限流配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 启用限流 | RATE_LIMIT_ENABLED | true | 是否启用 API 限流 |
| 请求限制 | RATE_LIMIT_REQUESTS | 100 | 每时间窗口最大请求数 |
| 时间窗口 | RATE_LIMIT_PERIOD | 60 | 限流时间窗口(秒) |

### 监控和日志

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 日志级别 | LOG_LEVEL | INFO | 日志记录级别 |
| 启用监控 | ENABLE_METRICS | true | 是否启用监控指标 |
| 监控路径 | METRICS_PATH | /metrics | 监控指标访问路径 |
| 健康检查间隔 | HEALTH_CHECK_INTERVAL | 30 | 健康检查间隔(秒) |

### 缓存配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 启用缓存 | CACHE_ENABLED | true | 是否启用缓存 |
| 缓存时间 | CACHE_TTL | 3600 | 缓存有效期(秒) |

### 任务队列配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 队列大小 | TASK_QUEUE_SIZE | 100 | 任务队列容量 |
| 结果保留时间 | TASK_RESULT_TTL | 3600 | 结果保留时间(秒) |

## API 说明

### 1. 转写接口

**端点**: `/transcribe`

**请求参数**:
- `file`: 音频文件（必需）
- `secret_id`: 腾讯云 SecretId（可选，如环境变量已设置）
- `secret_key`: 腾讯云 SecretKey（可选，如环境变量已设置）
- `cos_bucket`: COS 存储桶名称（可选，如环境变量已设置）
- `cos_region`: COS 存储桶地域（可选，如环境变量已设置）

**响应格式**:
```json
{
    "task_id": "任务ID",
    "status": "completed",
    "message": "识别完成",
    "results": [
        {
            "text": "转写文本",
            "start_time": 0.0,
            "end_time": 1.0,
            "speaker_id": 1,
            "emotion": "neutral",
            "emotion_score": 0.95
        }
    ]
}
```

### 2. 任务状态查询

**端点**: `/tasks`

**响应格式**:
```json
{
    "active_tasks": 1,
    "max_tasks": 4,
    "tasks": {
        "task_id": {
            "status": "started",
            "start_time": "2024-01-01T12:00:00"
        }
    }
}
```

### 3. 健康检查

**端点**: `/health`

**响应格式**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "active_tasks": 1,
    "max_tasks": 4
}
```

## 项目结构

```
.
├── README.md           # 项目文档
├── mcp_service.py     # MCP 服务主文件
├── mcp_config.py      # MCP 服务器配置
├── asr_service_async.py # ASR 服务模块
├── config.py          # 配置管理
├── requirements.txt   # 依赖管理
├── .env.example       # 环境变量示例
├── .gitignore        # Git 忽略配置
└── modelscope.yaml   # ModelScope 配置
```

## 监控和指标

服务提供以下监控指标：
- 请求计数和延迟
- 任务队列状态
- 资源使用情况
- 错误率统计

访问 `/metrics` 获取详细监控指标。

## 最佳实践

### 1. 配置管理
- 使用环境变量管理敏感信息
- 根据实际负载调整工作进程数
- 设置合适的限流参数
- 配置适当的超时时间

### 2. 性能优化
- 启用缓存减少重复计算
- 调整任务队列大小
- 配置合理的并发数
- 设置适当的结果保留时间

### 3. 监控和维护
- 定期检查监控指标
- 及时处理错误日志
- 清理过期数据
- 更新服务配置

### 4. 安全建议
- 使用 HTTPS
- 启用 API 限流
- 配置访问控制
- 定期更新密钥

## 故障排除

1. **服务无法启动**
   - 检查端口占用
   - 验证配置文件
   - 查看错误日志

2. **请求被限流**
   - 检查限流配置
   - 调整请求频率
   - 增加限流阈值

3. **任务处理超时**
   - 检查超时配置
   - 优化处理逻辑
   - 增加工作进程

## 贡献指南

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License