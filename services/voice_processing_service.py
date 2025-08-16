"""
语音处理服务 - 统一处理语音消息的业务逻辑
"""
import os
from typing import Optional, AsyncGenerator
from astrbot.api import logger
from astrbot.api.message_components import Record
from astrbot.api.event import AstrMessageEvent

from ..config import PluginConfig
from ..exceptions import VoiceToTextError, FileNotFoundError
from ..utils.decorators import async_operation_handler
from ..core.factory import ComponentFactory
from ..voice_file_resolver import VoiceFileResolver

class VoiceProcessingService:
    """语音处理服务 - 专注于语音消息处理流程"""
    
    def __init__(self, config: PluginConfig = None):
        self.config = config or PluginConfig.create_default()
        # 使用工厂模式创建音频处理组件，避免循环导入
        self.audio_converter = ComponentFactory.create_audio_converter(self.config)
        self.file_resolver = VoiceFileResolver()
        
        # 为命令直接访问创建FFmpeg管理器实例
        self.ffmpeg_manager = ComponentFactory.create_ffmpeg_manager()
        
        logger.info("语音处理服务初始化完成")
    
    @async_operation_handler("语音文件处理")
    async def process_voice_file(self, voice: Record) -> Optional[str]:
        """
        处理语音文件，返回可用于STT的文件路径
        
        Args:
            voice: 语音消息对象
            
        Returns:
            str: 处理后的音频文件路径，如果失败返回None
        """
        try:
            # 1. 获取语音文件路径
            original_path = await self._get_voice_file_path(voice)
            if not original_path:
                raise FileNotFoundError("无法获取语音文件路径")
            
            # 2. 验证文件
            if not await self.audio_converter.validate_audio_file(original_path):
                raise VoiceToTextError("语音文件验证失败")
            
            # 3. 检查文件大小
            file_size = os.path.getsize(original_path)
            if file_size > self.config.audio.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise VoiceToTextError(f"文件过大，超过{self.config.audio.MAX_FILE_SIZE_MB}MB限制")
            
            # 4. 转换为支持的格式
            processed_path = await self.audio_converter.convert_to_supported_format(original_path)
            
            logger.info(f"语音文件处理成功: {processed_path}")
            return processed_path
            
        except Exception as e:
            logger.error(f"语音文件处理失败: {e}")
            raise
    
    async def _get_voice_file_path(self, voice: Record) -> Optional[str]:
        """获取语音文件路径 - 集成多种策略"""
        try:
            # 首先尝试官方方法
            path = await voice.convert_to_file_path()
            if path and os.path.exists(path):
                return path
        except Exception as e:
            logger.debug(f"官方方法获取路径失败: {e}")
        
        # 使用备用解析器
        return await self.file_resolver.resolve_voice_file_path(voice)
    
    def cleanup_resources(self):
        """清理资源"""
        self.audio_converter.cleanup_temp_files()
        
    def get_processing_status(self) -> dict:
        """获取处理状态"""
        return {
            'audio_converter_status': self.audio_converter.get_status(),
            'config': {
                'max_file_size_mb': self.config.audio.MAX_FILE_SIZE_MB,
                'supported_formats': self.config.audio.SUPPORTED_FORMATS,
                'conversion_timeout': self.config.audio.CONVERSION_TIMEOUT_SECONDS
            }
        }
