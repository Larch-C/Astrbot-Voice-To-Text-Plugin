"""
服务层模块 - 语音转文字插件的业务逻辑服务
"""

# 导出服务类，便于外部导入
from .voice_processing_service import VoiceProcessingService
from .permission_service import PermissionService
from .stt_service import STTService

__all__ = [
    'VoiceProcessingService',
    'PermissionService', 
    'STTService'
]

# 版本信息
__version__ = "1.0.0"
