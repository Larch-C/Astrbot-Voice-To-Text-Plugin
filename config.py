"""
配置管理模块 - 统一管理所有配置项
"""
from dataclasses import dataclass
from typing import List, Dict, Any
import os

@dataclass
class AudioProcessingConfig:
    """音频处理配置"""
    MAX_FILE_SIZE_MB: int = 25
    MIN_FILE_SIZE_BYTES: int = 100
    CONVERSION_TIMEOUT_SECONDS: int = 60
    RETRY_COUNT: int = 2
    RETRY_DELAY_SECONDS: float = 1.0
    SUPPORTED_FORMATS: List[str] = None
    
    def __post_init__(self):
        if self.SUPPORTED_FORMATS is None:
            self.SUPPORTED_FORMATS = [
                'flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 
                'oga', 'ogg', 'wav', 'webm'
            ]

@dataclass 
class TempFileConfig:
    """临时文件配置"""
    TEMP_DIR_NAME: str = "astrbot_voice_temp"
    AUTO_CLEANUP: bool = True
    MAX_TEMP_FILES: int = 100
    CLEANUP_INTERVAL_MINUTES: int = 30

@dataclass
class FFmpegConfig:
    """FFmpeg配置"""
    SEARCH_CACHE_TIMEOUT_SECONDS: int = 3600  # 1小时缓存
    CONVERSION_TIMEOUT_SECONDS: int = 20  # 转换超时时间
    RETRY_COUNT: int = 2  # 重试次数
    RETRY_DELAY_SECONDS: float = 1.0  # 重试延迟
    COMMON_PATHS: List[str] = None
    
    def __post_init__(self):
        if self.COMMON_PATHS is None:
            if os.name == 'nt':  # Windows
                self.COMMON_PATHS = [
                    r'C:\ffmpeg\bin\ffmpeg.exe',
                    r'C:\Program Files\FFmpeg\bin\ffmpeg.exe',
                    os.path.expanduser(r'~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe'),
                ]
            else:  # Unix/Linux/Mac
                self.COMMON_PATHS = [
                    '/usr/bin/ffmpeg',
                    '/usr/local/bin/ffmpeg',
                    '/opt/homebrew/bin/ffmpeg',
                ]

@dataclass
class LoggingConfig:
    """日志配置"""
    ENABLE_DEBUG: bool = False
    ENABLE_PERFORMANCE_LOGGING: bool = True
    LOG_CONVERSION_DETAILS: bool = True

@dataclass
class PluginConfig:
    """插件总配置"""
    audio: AudioProcessingConfig
    temp_file: TempFileConfig  
    ffmpeg: FFmpegConfig
    logging: LoggingConfig
    
    @classmethod
    def create_default(cls) -> 'PluginConfig':
        """创建默认配置"""
        return cls(
            audio=AudioProcessingConfig(),
            temp_file=TempFileConfig(),
            ffmpeg=FFmpegConfig(),
            logging=LoggingConfig()
        )
