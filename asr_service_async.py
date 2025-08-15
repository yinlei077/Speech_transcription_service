import os
import json
import time
import asyncio
import aiohttp
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.asr.v20190614 import asr_client, models
from qcloud_cos import CosConfig, CosS3Client

@dataclass
class ASRResult:
    """语音识别结果数据类"""
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[int] = None
    emotion: Optional[str] = None
    emotion_score: Optional[float] = None

@dataclass
class TranscriptionResult:
    """转写结果数据类"""
    status: str
    task_id: str
    file_name: str
    creation_time: datetime
    completion_time: Optional[datetime] = None
    results: List[ASRResult] = None
    error: Optional[str] = None
    output_file: Optional[str] = None

class ResultParser:
    """结果解析器"""
    @staticmethod
    def parse_raw_result(raw_result: str) -> List[ASRResult]:
        """解析原始识别结果"""
        try:
            results = []
            
            # 如果结果已经是列表，直接使用
            if isinstance(raw_result, list):
                segments = raw_result
            else:
                # 尝试解析 JSON 字符串
                try:
                    segments = json.loads(raw_result)
                except json.JSONDecodeError as e:
                    # 如果 JSON 解析失败，尝试其他格式
                    print(f"JSON 解析失败: {e}")
                    print(f"原始结果: {raw_result}")
                    
                    # 尝试处理可能的文本格式
                    if isinstance(raw_result, str):
                        # 如果是纯文本，创建一个简单的结果
                        return [ASRResult(
                            text=raw_result,
                            start_time=0.0,
                            end_time=0.0,
                            speaker_id=None,
                            emotion=None,
                            emotion_score=None
                        )]
                    else:
                        raise Exception(f"无法解析的结果格式: {type(raw_result)}")
            
            # 确保 segments 是列表
            if not isinstance(segments, list):
                segments = [segments]
            
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                    
                # 基础信息
                text = segment.get('FinalSentence', '')
                if not text:
                    text = segment.get('Text', '')  # 尝试其他可能的字段名
                
                start_time = segment.get('StartMs', 0)
                if start_time:
                    start_time = start_time / 1000
                else:
                    start_time = segment.get('StartTime', 0.0)
                
                end_time = segment.get('EndMs', 0)
                if end_time:
                    end_time = end_time / 1000
                else:
                    end_time = segment.get('EndTime', 0.0)
                
                # 说话人信息
                speaker_id = None
                speech_segment = segment.get('SpeechSegment', {})
                if isinstance(speech_segment, dict):
                    speaker_id = speech_segment.get('SpeakerId')
                
                # 情感信息
                emotion = None
                emotion_score = None
                emotion_info = segment.get('EmotionInfo', {})
                if isinstance(emotion_info, dict):
                    emotion = emotion_info.get('EmotionType')
                    emotion_score = emotion_info.get('EmotionScore')
                
                result = ASRResult(
                    text=text,
                    start_time=start_time,
                    end_time=end_time,
                    speaker_id=speaker_id,
                    emotion=emotion,
                    emotion_score=emotion_score
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"解析结果时出错: {e}")
            print(f"原始结果类型: {type(raw_result)}")
            print(f"原始结果内容: {raw_result}")
            raise Exception(f"解析结果失败: {str(e)}")

class AsyncTencentASRService:
    """异步腾讯云ASR服务"""
    def __init__(self, secret_id: str, secret_key: str, cos_bucket: str, 
                 cos_region: str = "ap-nanjing", max_retries: int = 3, retry_delay: int = 5):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.cos_bucket = cos_bucket
        self.cos_region = cos_region
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cred = credential.Credential(secret_id, secret_key)
        self.result_parser = ResultParser()

    async def upload_to_cos(self, file_path: str) -> str:
        """异步上传文件到COS"""
        try:
            config = CosConfig(Region=self.cos_region, SecretId=self.secret_id, SecretKey=self.secret_key)
            client = CosS3Client(config)
            
            file_name = os.path.basename(file_path)
            
            # 上传文件（由于COS SDK不支持异步，这里使用线程池）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.upload_file(
                    Bucket=self.cos_bucket,
                    LocalFilePath=file_path,
                    Key=file_name,
                    PartSize=10,
                    MAXThread=10,
                    EnableMD5=False
                )
            )
            
            # 构建URL
            url = f'https://{self.cos_bucket}.cos.{self.cos_region}.myqcloud.com/{file_name}'
            
            # 异步验证URL可访问性
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    if response.status == 200:
                        return url
                    else:
                        raise Exception(f"无法访问文件URL，状态码: {response.status}")
                        
        except Exception as e:
            raise Exception(f"上传文件到COS失败: {str(e)}")

    async def create_asr_task(self, audio_url: str) -> str:
        """创建ASR任务"""
        try:
            http_profile = HttpProfile()
            http_profile.endpoint = "asr.tencentcloudapi.com"
            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            client = asr_client.AsrClient(self.cred, "ap-nanjing", client_profile)
            
            req = models.CreateRecTaskRequest()
            params = {
                "EngineModelType": "16k_zh",
                "ChannelNum": 1,
                "ResTextFormat": 5,
                "SourceType": 0,
                "Url": audio_url,
                "SpeakerDiarization": 1,
                "SpeakerNumber": 0,
                "EmotionRecognition": 1,
                "EmotionalEnergy": 1,
                "ConvertNumMode": 1,
                "FilterDirty": 0,
                "FilterPunc": 0,
                "FilterModal": 0,
                "SentenceMaxLength": 0
            }
            req.from_json_string(json.dumps(params))
            
            # 使用线程池执行同步API调用
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, client.CreateRecTask, req)
            resp_data = json.loads(resp.to_json_string())
            
            return resp_data["Data"]["TaskId"]
            
        except Exception as e:
            raise Exception(f"创建ASR任务失败: {str(e)}")

    async def check_task_status(self, task_id: str) -> Dict:
        """检查任务状态"""
        try:
            http_profile = HttpProfile()
            http_profile.endpoint = "asr.tencentcloudapi.com"
            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            client = asr_client.AsrClient(self.cred, "ap-nanjing", client_profile)
            
            req = models.DescribeTaskStatusRequest()
            req.TaskId = task_id
            
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, client.DescribeTaskStatus, req)
            return json.loads(resp.to_json_string())
            
        except Exception as e:
            raise Exception(f"检查任务状态失败: {str(e)}")

    async def wait_for_completion(self, task_id: str, polling_interval: int = 2) -> Dict:
        """等待任务完成"""
        while True:
            status_data = await self.check_task_status(task_id)
            status = status_data["Data"]["Status"]
            
            if status == 2:  # 成功
                return status_data
            elif status == 3:  # 失败
                raise Exception(f"ASR任务失败: {status_data['Data']['ErrorMsg']}")
            
            await asyncio.sleep(polling_interval)

    async def transcribe_audio(self, audio_file_path: str, save_result: bool = True) -> TranscriptionResult:
        """转写单个音频文件"""
        try:
            file_name = os.path.basename(audio_file_path)
            creation_time = datetime.now()
            
            # 上传文件
            audio_url = await self.upload_to_cos(audio_file_path)
            
            # 创建任务
            task_id = await self.create_asr_task(audio_url)
            
            # 等待完成
            status_data = await self.wait_for_completion(task_id)
            
            # 解析结果
            raw_result = status_data["Data"]["Result"]
            results = self.result_parser.parse_raw_result(raw_result)
            
            # 保存结果
            output_file = None
            if save_result:
                output_file = os.path.splitext(audio_file_path)[0] + "_result.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    # 保存格式化的结果
                    f.write("转写结果摘要:\n")
                    f.write("-" * 50 + "\n")
                    for result in results:
                        f.write(f"时间: {result.start_time:.2f}s - {result.end_time:.2f}s\n")
                        if result.speaker_id is not None:
                            f.write(f"说话人: {result.speaker_id}\n")
                        if result.emotion:
                            f.write(f"情感: {result.emotion} (置信度: {result.emotion_score:.2f})\n")
                        f.write(f"内容: {result.text}\n")
                        f.write("-" * 50 + "\n")
            
            return TranscriptionResult(
                status="success",
                task_id=task_id,
                file_name=file_name,
                creation_time=creation_time,
                completion_time=datetime.now(),
                results=results,
                output_file=output_file
            )
            
        except Exception as e:
            return TranscriptionResult(
                status="error",
                task_id=task_id if 'task_id' in locals() else "",
                file_name=file_name,
                creation_time=creation_time,
                error=str(e)
            )

    async def batch_transcribe(self, audio_files: List[str], 
                             max_concurrent: int = 5, 
                             save_results: bool = True) -> List[TranscriptionResult]:
        """批量转写音频文件"""
        async def process_file(file_path: str) -> TranscriptionResult:
            for attempt in range(self.max_retries):
                try:
                    return await self.transcribe_audio(file_path, save_results)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return TranscriptionResult(
                            status="error",
                            task_id="",
                            file_name=os.path.basename(file_path),
                            creation_time=datetime.now(),
                            error=f"重试{self.max_retries}次后失败: {str(e)}"
                        )
                    await asyncio.sleep(self.retry_delay)

        # 使用信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_process(file_path: str) -> TranscriptionResult:
            async with semaphore:
                return await process_file(file_path)

        # 并发处理所有文件
        tasks = [bounded_process(file_path) for file_path in audio_files]
        return await asyncio.gather(*tasks)

# 便捷函数
async def transcribe_audio_file(secret_id: str, secret_key: str, 
                              cos_bucket: str, cos_region: str,
                              audio_file_path: str, 
                              save_result: bool = True) -> TranscriptionResult:
    """异步转写单个音频文件的便捷函数"""
    service = AsyncTencentASRService(
        secret_id=secret_id,
        secret_key=secret_key,
        cos_bucket=cos_bucket,
        cos_region=cos_region
    )
    return await service.transcribe_audio(audio_file_path, save_result)

async def batch_transcribe_files(secret_id: str, secret_key: str,
                               cos_bucket: str, cos_region: str,
                               audio_files: List[str],
                               max_concurrent: int = 5,
                               save_results: bool = True) -> List[TranscriptionResult]:
    """异步批量转写音频文件的便捷函数"""
    service = AsyncTencentASRService(
        secret_id=secret_id,
        secret_key=secret_key,
        cos_bucket=cos_bucket,
        cos_region=cos_region
    )
    return await service.batch_transcribe(audio_files, max_concurrent, save_results)
