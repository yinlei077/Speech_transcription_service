"""MCP 服务配置"""
from typing import Dict, Any
from pydantic import BaseSettings, Field

class MCPServiceConfig(BaseSettings):
    """MCP 服务配置类"""
    
    # 服务基本信息
    SERVICE_NAME: str = "voice-transcription-service"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_DESCRIPTION: str = "基于腾讯云的语音转写服务"
    
    # MCP 服务器配置
    MCP_HOST: str = Field(default="0.0.0.0", env="MCP_HOST")
    MCP_PORT: int = Field(default=8080, env="MCP_PORT")
    MCP_WORKERS: int = Field(default=4, env="MCP_WORKERS")
    MCP_TIMEOUT: int = Field(default=300, env="MCP_TIMEOUT")  # 5分钟超时
    
    # API 限流配置
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")  # 每分钟请求数
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # 时间窗口（秒）
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 监控配置
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PATH: str = "/metrics"
    
    # 健康检查配置
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")  # 秒
    
    # 缓存配置
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 缓存时间（秒）
    
    # 安全配置
    CORS_ORIGINS: list = Field(default=["*"], env="CORS_ORIGINS")
    CORS_METHODS: list = Field(default=["*"], env="CORS_METHODS")
    CORS_HEADERS: list = Field(default=["*"], env="CORS_HEADERS")
    
    # 任务队列配置
    TASK_QUEUE_SIZE: int = Field(default=100, env="TASK_QUEUE_SIZE")
    TASK_RESULT_TTL: int = Field(default=3600, env="TASK_RESULT_TTL")  # 结果保留时间（秒）
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """获取 MCP 服务器配置"""
        return {
            "host": self.MCP_HOST,
            "port": self.MCP_PORT,
            "workers": self.MCP_WORKERS,
            "timeout": self.MCP_TIMEOUT,
            "log_level": self.LOG_LEVEL,
            "enable_metrics": self.ENABLE_METRICS,
            "metrics_path": self.METRICS_PATH,
            "health_check_interval": self.HEALTH_CHECK_INTERVAL,
        }
    
    def get_service_info(self) -> Dict[str, str]:
        """获取服务信息"""
        return {
            "name": self.SERVICE_NAME,
            "version": self.SERVICE_VERSION,
            "description": self.SERVICE_DESCRIPTION
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """获取限流配置"""
        return {
            "enabled": self.RATE_LIMIT_ENABLED,
            "requests": self.RATE_LIMIT_REQUESTS,
            "period": self.RATE_LIMIT_PERIOD
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建配置实例
mcp_config = MCPServiceConfig()
