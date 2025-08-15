import os
import json
import time
import requests
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.asr.v20190614 import asr_client, models
from qcloud_cos import CosConfig, CosS3Client

class TencentASRService:
    def __init__(self, secret_id, secret_key, cos_bucket="yl-308-1303870015", cos_region="ap-nanjing"):
        """
        初始化腾讯云ASR服务
        :param secret_id: 腾讯云 SecretId
        :param secret_key: 腾讯云 SecretKey
        :param cos_bucket: COS存储桶名称
        :param cos_region: COS存储桶区域
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.cos_bucket = cos_bucket
        self.cos_region = cos_region
        self.cred = credential.Credential(secret_id, secret_key)

    def upload_to_cos(self, file_path):
        """
        上传文件到COS并返回URL
        :param file_path: 本地文件路径
        :return: 文件的公网访问URL
        """
        try:
            config = CosConfig(Region=self.cos_region, SecretId=self.secret_id, SecretKey=self.secret_key)
            client = CosS3Client(config)
            
            file_name = os.path.basename(file_path)
            
            # 上传文件
            response = client.upload_file(
                Bucket=self.cos_bucket,
                LocalFilePath=file_path,
                Key=file_name,
                PartSize=10,
                MAXThread=10,
                EnableMD5=False
            )
            
            # 检查上传是否成功并验证URL
            if response:
                url = f'https://{self.cos_bucket}.cos.{self.cos_region}.myqcloud.com/{file_name}'
                response = requests.head(url)
                if response.status_code == 200:
                    return url
                else:
                    raise Exception(f"无法访问文件URL，状态码: {response.status_code}")
            else:
                raise Exception("文件上传失败")
                
        except Exception as e:
            raise Exception(f"上传文件到COS失败: {str(e)}")

    def transcribe_audio(self, audio_file_path, save_result=True):
        """
        将音频文件转写为文本
        :param audio_file_path: 音频文件路径
        :param save_result: 是否保存结果到文件
        :return: 转写结果和状态信息的字典
        """
        try:
            # 1. 上传文件到COS
            audio_url = self.upload_to_cos(audio_file_path)
            
            # 2. 配置ASR客户端
            http_profile = HttpProfile()
            http_profile.endpoint = "asr.tencentcloudapi.com"
            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            client = asr_client.AsrClient(self.cred, "ap-nanjing", client_profile)
            
            # 3. 创建识别任务
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
            
            # 4. 发送请求并获取任务ID
            resp = client.CreateRecTask(req)
            resp_data = json.loads(resp.to_json_string())
            task_id = resp_data["Data"]["TaskId"]
            
            # 5. 轮询任务状态
            status_req = models.DescribeTaskStatusRequest()
            status_req.TaskId = task_id
            
            max_attempts = 60  # 最大尝试次数（约2分钟）
            wait_seconds = 2  # 每次等待秒数
            
            for attempt in range(max_attempts):
                status_resp = client.DescribeTaskStatus(status_req)
                status_data = json.loads(status_resp.to_json_string())
                status = status_data["Data"]["Status"]
                
                if status == 2:  # 成功
                    result = status_data["Data"]["Result"]
                    
                    # 保存结果到文件（如果需要）
                    if save_result:
                        output_file = os.path.splitext(audio_file_path)[0] + "_result.txt"
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(result)
                    
                    return {
                        "status": "success",
                        "result": result,
                        "task_id": task_id,
                        "output_file": output_file if save_result else None
                    }
                    
                elif status == 3:  # 失败
                    error_msg = status_data["Data"]["ErrorMsg"]
                    return {
                        "status": "error",
                        "error": error_msg,
                        "task_id": task_id
                    }
                    
                else:  # 继续等待
                    time.sleep(wait_seconds)
            
            return {
                "status": "timeout",
                "task_id": task_id,
                "message": "任务处理超时，请稍后手动查询结果"
            }
            
        except TencentCloudSDKException as err:
            return {
                "status": "error",
                "error": f"腾讯云SDK错误: {str(err)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"处理过程出错: {str(e)}"
            }

def transcribe_audio_file(secret_id, secret_key, audio_file_path, save_result=True):
    """
    便捷函数：直接调用音频转写服务
    :param secret_id: 腾讯云 SecretId
    :param secret_key: 腾讯云 SecretKey
    :param audio_file_path: 音频文件路径
    :param save_result: 是否保存结果到文件
    :return: 转写结果和状态信息的字典
    """
    service = TencentASRService(secret_id, secret_key)
    return service.transcribe_audio(audio_file_path, save_result)
