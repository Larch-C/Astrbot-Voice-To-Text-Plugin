"""
STT服务提供商配置和管理模块
支持多种语音转文字服务提供商的统一接口
"""

import aiohttp
import ssl
import certifi
from typing import Dict, Any, Optional
from astrbot.api import logger

class STTProviderConfig:
    """STT提供商配置类"""
    
    # 各提供商的默认配置
    PROVIDER_CONFIGS = {
        "openai": {
            "api_base_url": "https://api.openai.com/v1",
            "default_model": "whisper-1",
            "endpoint": "/audio/transcriptions",
            "format": "openai",
            "supported_models": ["whisper-1"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        },
        "groq": {
            "api_base_url": "https://api.groq.com/openai/v1", 
            "default_model": "whisper-large-v3",
            "endpoint": "/audio/transcriptions",
            "format": "openai",
            "supported_models": ["whisper-large-v3", "distil-whisper-large-v3-en"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        },
        "deepgram": {
            "api_base_url": "https://api.deepgram.com/v1",
            "default_model": "nova-2",
            "endpoint": "/listen",
            "format": "deepgram",
            "supported_models": ["nova-2", "nova", "enhanced", "base"],
            "content_type": "audio/wav",
            "auth_header": "Authorization",
            "auth_format": "Token {api_key}"
        },
        "azure": {
            "api_base_url": "https://YOUR_REGION.api.cognitive.microsoft.com/speechtotext/v3.1",
            "default_model": "whisper",
            "endpoint": "/transcriptions",
            "format": "azure",
            "supported_models": ["whisper"],
            "content_type": "multipart/form-data",
            "auth_header": "Ocp-Apim-Subscription-Key",
            "auth_format": "{api_key}"
        },
        "siliconflow": {
            "api_base_url": "https://api.siliconflow.cn/v1",
            "default_model": "FunAudioLLM/SenseVoiceSmall",
            "endpoint": "/audio/transcriptions",
            "format": "openai",
            "supported_models": ["FunAudioLLM/SenseVoiceSmall"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization", 
            "auth_format": "Bearer {api_key}"
        },
        "minimax": {
            "api_base_url": "https://api.minimax.chat/v1",
            "default_model": "speech-01",
            "endpoint": "/audio/transcriptions",
            "format": "openai",
            "supported_models": ["speech-01"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        },
        "volcengine": {
            "api_base_url": "https://openspeech.bytedance.com/api/v1",
            "default_model": "volcano-asr",
            "endpoint": "/asr",
            "format": "volcengine",
            "supported_models": ["volcano-asr"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        },
        "tencent": {
            "api_base_url": "https://asr.tencentcloudapi.com",
            "default_model": "16k_zh",
            "endpoint": "/",
            "format": "tencent",
            "supported_models": ["16k_zh", "8k_zh", "16k_en"],
            "content_type": "application/json",
            "auth_header": "Authorization", 
            "auth_format": "TC3-HMAC-SHA256 {api_key}"
        },
        "baidu": {
            "api_base_url": "https://vop.baidu.com/server_api",
            "default_model": "1537",
            "endpoint": "",
            "format": "baidu",
            "supported_models": ["1537", "1736"],
            "content_type": "audio/wav",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        },
        "custom": {
            "api_base_url": "https://api.example.com/v1",
            "default_model": "whisper-1",
            "endpoint": "/audio/transcriptions",
            "format": "openai",
            "supported_models": ["whisper-1"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        },
        "other": {
            "api_base_url": "https://api.example.com",
            "default_model": "default-model",
            "endpoint": "/audio/transcriptions",
            "format": "other",
            "supported_models": ["default-model"],
            "content_type": "multipart/form-data",
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}"
        }
    }

    @classmethod
    def get_provider_config(cls, provider_type: str) -> Dict[str, Any]:
        """获取提供商配置"""
        return cls.PROVIDER_CONFIGS.get(provider_type, cls.PROVIDER_CONFIGS["custom"])
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """获取支持的提供商列表"""
        return list(cls.PROVIDER_CONFIGS.keys())
    
    @classmethod
    def get_provider_models(cls, provider_type: str) -> list:
        """获取提供商支持的模型列表"""
        config = cls.get_provider_config(provider_type)
        return config.get("supported_models", [])

class STTProviderManager:
    """STT提供商管理器"""
    
    def __init__(self, provider_type: str, api_key: str, api_base_url: str = None, 
                 model: str = None, custom_headers: Dict[str, str] = None, **kwargs):
        self.provider_type = provider_type.lower()
        self.api_key = api_key
        self.config = STTProviderConfig.get_provider_config(self.provider_type)
        
        # 使用自定义配置覆盖默认配置
        self.api_base_url = api_base_url or self.config["api_base_url"]
        self.model = model or self.config["default_model"] 
        self.custom_headers = custom_headers or {}
        
        # "other"类型的完全自定义配置
        if self.provider_type == "other":
            self.custom_request_body = kwargs.get("custom_request_body", {})
            self.custom_endpoint = kwargs.get("custom_endpoint", "/audio/transcriptions")
            self.custom_request_method = kwargs.get("custom_request_method", "POST")
            self.custom_content_type = kwargs.get("custom_content_type", "multipart/form-data")
            self.custom_response_path = kwargs.get("custom_response_path", "text")
        
        logger.info(f"初始化STT提供商管理器: {self.provider_type}")

    async def transcribe_audio(self, audio_file_path: str) -> str:
        """
        转录音频文件 - 统一处理MP3格式
        
        Args:
            audio_file_path: 音频文件路径（应该已经是MP3格式）
            
        Returns:
            str: 转录文本
        """
        try:
            if not self.api_key:
                raise ValueError(f"{self.provider_type} API密钥未配置")

            # 根据提供商类型选择处理方法
            if self.config["format"] == "openai":
                return await self._transcribe_openai_format(audio_file_path)
            elif self.config["format"] == "deepgram":
                return await self._transcribe_deepgram_format(audio_file_path)
            elif self.config["format"] == "other":
                return await self._transcribe_other_format(audio_file_path)
            else:
                # 大部分提供商都兼容OpenAI格式
                logger.info(f"使用OpenAI兼容格式处理 {self.provider_type}")
                return await self._transcribe_openai_format(audio_file_path)
                
        except Exception as e:
            logger.error(f"音频转录失败 ({self.provider_type}): {e}")
            raise

    async def _transcribe_openai_format(self, audio_file_path: str) -> str:
        """OpenAI格式转录 (OpenAI, Groq, SiliconFlow, MiniMax, Custom)"""
        api_url = f"{self.api_base_url.rstrip('/')}{self.config['endpoint']}"
        
        # 处理自定义请求头，支持动态变量替换
        processed_custom_headers = {}
        for key, value in self.custom_headers.items():
            if isinstance(value, str):
                # 支持变量替换
                processed_value = value.format(
                    api_key=self.api_key,
                    model=self.model,
                    provider_type=self.provider_type
                )
                processed_custom_headers[key] = processed_value
            else:
                processed_custom_headers[key] = value
        
        headers = {
            self.config["auth_header"]: self.config["auth_format"].format(api_key=self.api_key),
            "User-Agent": f"AstrBot-VoiceToText-Plugin/1.0.0-{self.provider_type}",
            **processed_custom_headers
        }

        logger.info(f"使用 {self.provider_type} STT API: {api_url}")

        # 读取音频文件
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 使用multipart/form-data格式
            data = aiohttp.FormData()
            data.add_field('file', audio_data, filename='audio.mp3', content_type='audio/mpeg')
            data.add_field('model', self.model)
            data.add_field('response_format', 'json')
            
            async with session.post(api_url, headers=headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    transcript = result.get("text", "")
                    if transcript:
                        logger.info(f"{self.provider_type} STT识别成功")
                        return transcript.strip()
                    else:
                        logger.warning(f"{self.provider_type} STT返回空结果")
                        return ""
                else:
                    error_text = await response.text()
                    raise Exception(f"{self.provider_type} API请求失败: {response.status} - {error_text}")

    async def _transcribe_deepgram_format(self, audio_file_path: str) -> str:
        """Deepgram格式转录"""
        api_url = f"{self.api_base_url.rstrip('/')}{self.config['endpoint']}"
        
        # 处理自定义请求头，支持动态变量替换
        processed_custom_headers = {}
        for key, value in self.custom_headers.items():
            if isinstance(value, str):
                # 支持变量替换
                processed_value = value.format(
                    api_key=self.api_key,
                    model=self.model,
                    provider_type=self.provider_type
                )
                processed_custom_headers[key] = processed_value
            else:
                processed_custom_headers[key] = value
        
        headers = {
            self.config["auth_header"]: self.config["auth_format"].format(api_key=self.api_key),
            "Content-Type": self.config["content_type"],
            "User-Agent": f"AstrBot-VoiceToText-Plugin/1.0.0-deepgram",
            **processed_custom_headers
        }
        
        params = {"model": self.model}

        logger.info(f"使用 Deepgram STT API: {api_url}")

        # 读取音频文件
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.post(api_url, headers=headers, params=params, data=audio_data) as response:
                if response.status == 200:
                    result = await response.json()
                    # Deepgram返回格式
                    channels = result.get("results", {}).get("channels", [])
                    if channels and len(channels) > 0:
                        # channels是列表，需要取第一个元素
                        first_channel = channels[0]
                        alternatives = first_channel.get("alternatives", [])
                        if alternatives and len(alternatives) > 0:
                            # alternatives也是列表，需要取第一个元素
                            first_alternative = alternatives[0]
                            transcript = first_alternative.get("transcript", "")
                            if transcript:
                                logger.info("Deepgram STT识别成功")
                                return transcript.strip()
                    
                    logger.warning("Deepgram STT返回空结果")
                    return ""
                else:
                    error_text = await response.text()
                    raise Exception(f"Deepgram API请求失败: {response.status} - {error_text}")

    async def _transcribe_other_format(self, audio_file_path: str) -> str:
        """完全自定义格式转录 - 支持任意API格式"""
        api_url = f"{self.api_base_url.rstrip('/')}{self.custom_endpoint}"
        
        # 构建请求头
        headers = {
            "User-Agent": f"AstrBot-VoiceToText-Plugin/1.0.0-other",
            **self.custom_headers
        }
        
        # 添加认证头
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"使用完全自定义格式 STT API: {api_url}")

        # 读取音频文件
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 根据内容类型构建请求数据
            if self.custom_content_type == "multipart/form-data":
                # multipart/form-data格式
                data = aiohttp.FormData()
                data.add_field('file', audio_data, filename='audio.mp3', content_type='audio/mpeg')
                
                # 添加自定义请求体中的字段
                for key, value in self.custom_request_body.items():
                    # 支持变量替换
                    if isinstance(value, str):
                        value = value.format(
                            model=self.model,
                            api_key=self.api_key,
                            audio_base64=None  # multipart模式不需要base64
                        )
                    data.add_field(key, str(value))
                
                request_data = data
                
            elif self.custom_content_type == "application/json":
                # JSON格式 - 需要将音频转为base64
                import base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # 构建JSON请求体
                json_data = {}
                for key, value in self.custom_request_body.items():
                    if isinstance(value, str):
                        value = value.format(
                            model=self.model,
                            api_key=self.api_key,
                            audio_base64=audio_base64
                        )
                    json_data[key] = value
                
                headers["Content-Type"] = "application/json"
                request_data = json_data
                
            else:  # application/octet-stream
                # 直接发送音频数据
                headers["Content-Type"] = self.custom_content_type
                request_data = audio_data
            
            # 发送请求
            method = getattr(session, self.custom_request_method.lower())
            
            if self.custom_content_type == "application/json":
                async with method(api_url, headers=headers, json=request_data) as response:
                    response_data = await self._handle_other_response(response)
            else:
                async with method(api_url, headers=headers, data=request_data) as response:
                    response_data = await self._handle_other_response(response)
            
            return response_data

    async def _handle_other_response(self, response) -> str:
        """处理自定义格式的响应"""
        if response.status == 200:
            result = await response.json()
            
            # 根据自定义响应路径提取文本
            transcript = self._extract_text_by_path(result, self.custom_response_path)
            
            if transcript:
                logger.info("自定义格式STT识别成功")
                return transcript.strip()
            else:
                logger.warning("自定义格式STT返回空结果")
                return ""
        else:
            error_text = await response.text()
            raise Exception(f"自定义格式API请求失败: {response.status} - {error_text}")

    def _extract_text_by_path(self, data: dict, path: str) -> str:
        """根据路径从响应JSON中提取文本"""
        try:
            current = data
            for key in path.split('.'):
                if isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list) and key.isdigit():
                    current = current[int(key)]
                else:
                    return ""
            return str(current) if current is not None else ""
        except Exception as e:
            logger.warning(f"提取响应文本失败: {e}")
            return ""

    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "provider_type": self.provider_type,
            "api_base_url": self.api_base_url,
            "model": self.model,
            "format": self.config["format"]
        }

def get_provider_default_config(provider_type: str) -> Dict[str, str]:
    """
    获取指定提供商的默认配置
    用于前端动态更新配置表单
    """
    config = STTProviderConfig.get_provider_config(provider_type)
    return {
        "api_base_url": config["api_base_url"],
        "default_model": config["default_model"]
    }

# 提供商配置映射表，用于前端配置界面
PROVIDER_DISPLAY_CONFIGS = {
    "openai": {
        "name": "OpenAI Whisper",
        "description": "OpenAI官方Whisper API，准确度高，支持多语言", 
        "pricing": "按使用量计费",
        "features": ["多语言支持", "高准确度", "官方服务"]
    },
    "groq": {
        "name": "Groq",
        "description": "高速Whisper推理服务，响应速度快",
        "pricing": "免费额度 + 按使用量计费", 
        "features": ["超快速度", "Whisper模型", "免费额度"]
    },
    "deepgram": {
        "name": "Deepgram", 
        "description": "专业语音识别服务，实时转录能力强",
        "pricing": "按使用量计费",
        "features": ["实时转录", "多模型选择", "专业服务"]
    },
    "azure": {
        "name": "Azure Speech",
        "description": "微软Azure语音服务，企业级可靠性",
        "pricing": "按使用量计费",
        "features": ["企业级", "高可靠性", "全球部署"]
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "description": "硅基流动语音识别服务，支持中文优化",
        "pricing": "按使用量计费",
        "features": ["中文优化", "高性价比", "国内服务"]
    },
    "minimax": {
        "name": "MiniMax",
        "description": "海螺AI语音服务，中文效果好",
        "pricing": "按使用量计费",
        "features": ["中文优势", "AI集成", "多模态"]
    },
    "volcengine": {
        "name": "火山引擎",
        "description": "字节跳动语音识别服务，短视频场景优化",
        "pricing": "按使用量计费", 
        "features": ["短视频优化", "低延迟", "高并发"]
    },
    "tencent": {
        "name": "腾讯云",
        "description": "腾讯云语音识别，游戏社交场景优化",
        "pricing": "按使用量计费",
        "features": ["游戏优化", "社交场景", "稳定可靠"]
    },
    "baidu": {
        "name": "百度智能云",
        "description": "百度语音识别，中文语音处理强",
        "pricing": "按使用量计费",
        "features": ["中文强项", "方言支持", "本土化"]
    },
    "custom": {
        "name": "自定义服务",
        "description": "其他兼容OpenAI格式的语音服务",
        "pricing": "根据服务商而定",
        "features": ["灵活配置", "兼容性", "可扩展"]
    }
}
