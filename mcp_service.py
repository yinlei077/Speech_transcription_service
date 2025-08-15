from fastmcp import FastMCP, BaseRequest, BaseResponse
from fastmcp.types import File
from typing import Optional, Dict, List
from datetime import datetime
import asyncio
from asr_service_async import AsyncTencentASRService, ASRResult
from config import settings

from mcp_config import mcp_config

# 创建 FastMCP 应用实例
app = FastMCP(
    service_name=mcp_config.SERVICE_NAME,
    service_version=mcp_config.SERVICE_VERSION,
    service_description=mcp_config.SERVICE_DESCRIPTION,
    **mcp_config.get_mcp_config()
)

class TranscribeRequest(BaseRequest):
    """转写请求"""
    file: File
    secret_id: Optional[str] = None
    secret_key: Optional[str] = None
    cos_bucket: Optional[str] = None
    cos_region: Optional[str] = None

class TranscribeResponse(BaseResponse):
    """转写响应"""
    task_id: str
    status: str
    message: str
    results: Optional[List[Dict]] = None
    error: Optional[str] = None

# 用于存储任务状态
task_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)
active_tasks: Dict[str, dict] = {}

@app.mcp_endpoint("/transcribe")
async def transcribe_audio(request: TranscribeRequest) -> TranscribeResponse:
    """音频转写服务"""
    try:
        # 验证文件大小
        file_size = len(request.file.content)
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            return TranscribeResponse(
                task_id="",
                status="error",
                message=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # 使用环境变量或请求参数
        final_secret_id = request.secret_id or settings.TENCENT_SECRET_ID
        final_secret_key = request.secret_key or settings.TENCENT_SECRET_KEY
        final_cos_bucket = request.cos_bucket or settings.COS_BUCKET
        final_cos_region = request.cos_region or settings.COS_REGION
        
        # 验证必要参数
        if not all([final_secret_id, final_secret_key, final_cos_bucket, final_cos_region]):
            return TranscribeResponse(
                task_id="",
                status="error",
                message="Missing required credentials"
            )
        
        # 生成任务ID
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
        
        # 保存文件
        file_name = f"{task_id}_{request.file.filename}"
        file_path = os.path.join(settings.TEMP_FILE_DIR, file_name)
        with open(file_path, "wb") as f:
            f.write(request.file.content)
        
        # 创建ASR服务实例
        service = AsyncTencentASRService(
            secret_id=final_secret_id,
            secret_key=final_secret_key,
            cos_bucket=final_cos_bucket,
            cos_region=final_cos_region
        )
        
        async with task_semaphore:
            active_tasks[task_id] = {"status": "started", "start_time": datetime.now()}
            
            try:
                # 上传到COS
                audio_url = await service.upload_to_cos(file_path)
                
                # 创建识别任务
                asr_task_id = await service.create_asr_task(audio_url)
                
                # 等待结果
                status_data = await service.wait_for_completion(asr_task_id)
                
                if status_data["Data"]["Status"] == 2:  # 成功
                    result = status_data["Data"]["Result"]
                    parsed_results = service.result_parser.parse_raw_result(result)
                    
                    # 格式化结果
                    formatted_results = []
                    for res in parsed_results:
                        formatted_results.append({
                            'text': res.text,
                            'start_time': res.start_time,
                            'end_time': res.end_time,
                            'speaker_id': res.speaker_id,
                            'emotion': res.emotion,
                            'emotion_score': res.emotion_score
                        })
                    
                    return TranscribeResponse(
                        task_id=task_id,
                        status="completed",
                        message="识别完成",
                        results=formatted_results
                    )
                else:
                    error_msg = status_data["Data"].get("ErrorMsg", "Unknown error")
                    return TranscribeResponse(
                        task_id=task_id,
                        status="error",
                        message=f"识别失败: {error_msg}"
                    )
                    
            except Exception as e:
                return TranscribeResponse(
                    task_id=task_id,
                    status="error",
                    message=str(e)
                )
            
            finally:
                # 清理资源
                if task_id in active_tasks:
                    del active_tasks[task_id]
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                    
    except Exception as e:
        return TranscribeResponse(
            task_id="",
            status="error",
            message=str(e)
        )

@app.mcp_endpoint("/tasks")
async def get_tasks() -> Dict:
    """获取当前任务状态"""
    return {
        "active_tasks": len(active_tasks),
        "max_tasks": settings.MAX_CONCURRENT_TASKS,
        "tasks": active_tasks
    }

@app.mcp_endpoint("/health")
async def health_check() -> Dict:
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(active_tasks),
        "max_tasks": settings.MAX_CONCURRENT_TASKS
    }

if __name__ == "__main__":
    app.run()
