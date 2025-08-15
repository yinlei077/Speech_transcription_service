import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 腾讯云配置
    TENCENT_SECRET_ID: Optional[str] = None
    TENCENT_SECRET_KEY: Optional[str] = None
    COS_BUCKET: Optional[str] = None
    COS_REGION: Optional[str] = None

    # API访问控制
    API_TOKEN: str = ""

    # 并发控制
    MAX_CONCURRENT_TASKS: int = 4
    CURRENT_TASKS: int = 0

    # 临时文件配置
    TEMP_FILE_DIR: str = "temp_uploads"
    MAX_FILE_SIZE_MB: int = 512

    class Config:
        env_file = ".env"

settings = Settings()

# 创建临时文件目录
os.makedirs(settings.TEMP_FILE_DIR, exist_ok=True)
