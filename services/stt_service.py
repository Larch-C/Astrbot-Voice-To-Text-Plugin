"""
STT服务层 - 统一处理语音转文字的业务逻辑
"""
from typing import Optional
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..config import PluginConfig
from ..exceptions import STTProviderError
from ..utils.decorators import async_operation_handler, retry_on_failure
from ..stt_providers import STTProviderManager, get_provider_default_config

class STTService:
    """STT服务 - 专门处理语音转文字调用"""
    
    def __init__(self, config: dict, context=None):
        """
        初始化STT服务
        
        Args:
            config: 原始配置字典
            context: AstrBot上下文对象
        """
        self.config = config
        self.context = context
        
        # 语音识别配置
        voice_recognition = self.config.get("Voice_Recognition", {})
        self.stt_source = voice_recognition.get("STT_Source", "framework")
        self.framework_stt_provider_name = voice_recognition.get("Framework_STT_Provider_Name", "")
        self.enable_voice_processing = voice_recognition.get("Enable_Voice_Processing", True)
        
        # 初始化插件STT管理器（如果使用plugin模式）
        self.stt_manager = None
        if self.stt_source == "plugin":
            self._initialize_plugin_stt()
        
        logger.info(f"STT服务初始化完成，使用来源: {self.stt_source}")
    
    def _initialize_plugin_stt(self):
        """初始化插件STT管理器"""
        try:
            stt_api_config = self.config.get("STT_API_Config", {})
            api_key = stt_api_config.get("API_Key", "")
            api_base_url = stt_api_config.get("API_Base_URL", "")
            model = stt_api_config.get("Model", "")
            provider_type = stt_api_config.get("Provider_Type", "openai")
            custom_headers = stt_api_config.get("Custom_Headers", {})
            
            # 获取"other"类型的自定义配置
            custom_kwargs = {}
            if provider_type == "other":
                custom_kwargs = {
                    "custom_request_body": stt_api_config.get("Custom_Request_Body", {}),
                    "custom_endpoint": stt_api_config.get("Custom_Endpoint", "/audio/transcriptions"),
                    "custom_request_method": stt_api_config.get("Custom_Request_Method", "POST"),
                    "custom_content_type": stt_api_config.get("Custom_Content_Type", "multipart/form-data"),
                    "custom_response_path": stt_api_config.get("Custom_Response_Path", "text")
                }
            
            # 获取提供商默认配置
            default_config = get_provider_default_config(provider_type)
            
            # 使用默认配置补充空值
            if not api_base_url:
                api_base_url = default_config["api_base_url"]
            if not model:
                model = default_config["default_model"]
            
            # 初始化STT提供商管理器
            self.stt_manager = STTProviderManager(
                provider_type=provider_type,
                api_key=api_key,
                api_base_url=api_base_url,
                model=model,
                custom_headers=custom_headers,
                **custom_kwargs
            )
            
            logger.info(f"插件STT提供商管理器初始化成功: {provider_type}")
            
        except Exception as e:
            logger.error(f"插件STT提供商管理器初始化失败: {e}")
            self.stt_manager = None
    
    @async_operation_handler("语音转文字")
    @retry_on_failure(max_retries=2)
    async def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """
        转录音频文件为文字
        
        Args:
            audio_file_path: 音频文件路径
            
        Returns:
            str: 转录的文本，如果失败返回None
        """
        if not self.enable_voice_processing:
            logger.warning("语音处理已禁用")
            return None
        
        if self.stt_source == "framework":
            return await self._call_framework_stt(audio_file_path)
        elif self.stt_source == "plugin":
            return await self._call_plugin_stt(audio_file_path)
        else:
            raise STTProviderError(f"未知的STT服务来源: {self.stt_source}")
    
    @async_operation_handler("框架STT调用")
    async def _call_framework_stt(self, audio_file_path: str) -> Optional[str]:
        """调用AstrBot框架STT接口"""
        if not self.context:
            raise STTProviderError("缺少AstrBot上下文对象")
        
        try:
            # 如果指定了特定的框架STT提供商名字，尝试查找并使用
            if self.framework_stt_provider_name:
                all_stt_providers = self.context.get_all_stt_providers()
                
                # 查找指定名字的提供商
                target_provider = None
                for provider in all_stt_providers:
                    provider_meta = provider.meta()
                    if provider_meta.id == self.framework_stt_provider_name:
                        target_provider = provider
                        break
                
                if target_provider:
                    logger.info(f"使用指定的框架STT提供商: {self.framework_stt_provider_name}")
                    result = await target_provider.get_text(audio_file_path)
                    
                    if result:
                        logger.info("指定框架STT提供商识别成功")
                        return result
                    else:
                        logger.warning("指定框架STT提供商返回空结果")
                        return None
                else:
                    logger.warning(f"未找到指定的框架STT提供商: {self.framework_stt_provider_name}，使用默认提供商")
            
            # 使用默认的框架STT提供商
            stt_provider = self.context.get_using_stt_provider()
            
            if not stt_provider:
                raise STTProviderError("未配置AstrBot框架STT提供商")
            
            logger.info(f"使用AstrBot框架默认STT提供商: {type(stt_provider).__name__}")
            result = await stt_provider.get_text(audio_file_path)
            
            if result:
                logger.info("AstrBot框架STT识别成功")
                return result
            else:
                logger.warning("AstrBot框架STT返回空结果")
                return None
                
        except Exception as e:
            logger.error(f"调用AstrBot框架STT接口失败: {e}")
            raise STTProviderError(f"框架STT调用失败: {str(e)}") from e
    
    @async_operation_handler("插件STT调用")
    async def _call_plugin_stt(self, audio_file_path: str) -> Optional[str]:
        """调用插件独立STT API"""
        if not self.stt_manager:
            raise STTProviderError("插件STT提供商管理器未初始化")
        
        try:
            logger.info(f"使用STT提供商管理器进行语音转录")
            result = await self.stt_manager.transcribe_audio(audio_file_path)
            
            if result:
                logger.info("STT提供商管理器转录成功")
                return result
            else:
                logger.warning("STT提供商管理器返回空结果")
                return None
                
        except Exception as e:
            logger.error(f"STT提供商管理器转录失败: {e}")
            raise STTProviderError(f"插件STT调用失败: {str(e)}") from e
    
    def get_stt_status(self) -> dict:
        """获取STT服务状态"""
        status = {
            'stt_source': self.stt_source,
            'voice_processing_enabled': self.enable_voice_processing,
        }
        
        if self.stt_source == "framework":
            if self.context:
                stt_provider = self.context.get_using_stt_provider()
                status.update({
                    'framework_provider_available': stt_provider is not None,
                    'framework_provider_name': type(stt_provider).__name__ if stt_provider else None,
                    'specified_provider_name': self.framework_stt_provider_name or "默认"
                })
            else:
                status.update({
                    'framework_provider_available': False,
                    'error': '缺少AstrBot上下文对象'
                })
        
        elif self.stt_source == "plugin":
            status.update({
                'plugin_manager_available': self.stt_manager is not None,
                'plugin_provider_info': self.stt_manager.get_provider_info() if self.stt_manager else None
            })
        
        return status
    
    def is_available(self) -> bool:
        """检查STT服务是否可用"""
        if not self.enable_voice_processing:
            return False
        
        if self.stt_source == "framework":
            return self.context and self.context.get_using_stt_provider() is not None
        elif self.stt_source == "plugin":
            return self.stt_manager is not None
        
        return False
