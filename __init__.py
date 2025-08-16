"""
AstrBot 语音转文字插件 - 支持多平台的智能语音识别系统
"""

# 导入主要插件类
from .main import VoiceToTextPlugin

# 导入配置和异常处理
from .config import PluginConfig
from .exceptions import (
    VoiceToTextError,
    STTProviderError, 
    AudioConversionError,
    FileNotFoundError,
    PermissionError,
    FFmpegNotFoundError,
    ConversionTimeoutError,
    FileValidationError
)

# 导入STT提供商管理器
from .stt_providers import STTProviderManager, get_provider_default_config

# 导入语音文件解析器
from .voice_file_resolver import VoiceFileResolver

__all__ = [
    # 主插件类
    'VoiceToTextPlugin',
    
    # 配置管理
    'PluginConfig',
    
    # 异常类
    'VoiceToTextError',
    'STTProviderError',
    'AudioConversionError', 
    'FileNotFoundError',
    'PermissionError',
    'FFmpegNotFoundError',
    'ConversionTimeoutError',
    'FileValidationError',
    
    # STT管理
    'STTProviderManager',
    'get_provider_default_config',
    
    # 工具类
    'VoiceFileResolver'
]

# 插件元数据
__name__ = "astrbot_plugin_voice_to_text"
__version__ = "1.0.0"
__author__ = "NickMo"
__description__ = "语音转文字智能回复插件，支持Linux、macOS等跨平台系统"
__license__ = "MIT"

# 支持的平台
__platforms__ = ["linux", "darwin", "win32"]

# 兼容性信息
__min_python_version__ = "3.8"
__min_astrbot_version__ = "3.4.0"
