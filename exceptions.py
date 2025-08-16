"""
插件专用异常类定义
"""

class VoiceToTextError(Exception):
    """语音转文字插件基础异常"""
    pass

class AudioConversionError(VoiceToTextError):
    """音频转换异常"""
    pass

class AudioFormatError(VoiceToTextError):
    """音频格式异常"""
    pass

class FileNotFoundError(VoiceToTextError):
    """文件未找到异常"""
    pass

class FileValidationError(VoiceToTextError):
    """文件验证异常"""
    pass

class STTProviderError(VoiceToTextError):
    """STT提供商异常"""
    pass

class PermissionError(VoiceToTextError):
    """权限检查异常"""
    pass

class ConfigurationError(VoiceToTextError):
    """配置异常"""
    pass

class FFmpegNotFoundError(AudioConversionError):
    """FFmpeg未找到异常"""
    pass

class ConversionTimeoutError(AudioConversionError):
    """转换超时异常"""
    pass
