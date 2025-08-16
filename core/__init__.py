"""
核心模块 - 语音转文字插件的核心音频处理组件
使用工厂模式完全避免循环导入问题
"""

# 只导入基础组件，避免循环导入
from .audio_format_detector import AudioFormatDetector
from .temp_file_manager import TempFileManager
from .ffmpeg_manager import FFmpegManager

# 导入工厂模块 - 这是唯一的高级导入
from .factory import ComponentFactory

# 提供便利的工厂函数
def create_audio_converter(config=None):
    """工厂函数：创建音频转换器实例"""
    return ComponentFactory.create_audio_converter(config)

def create_strategy_manager(config=None):
    """工厂函数：创建策略管理器实例"""  
    return ComponentFactory.create_conversion_strategy_manager(config)

def create_format_detector(config=None):
    """工厂函数：创建格式检测器实例"""
    return ComponentFactory.create_format_detector(config)

def create_complete_processor(config=None):
    """工厂函数：创建完整音频处理器"""
    return ComponentFactory.create_complete_audio_processor(config)

# 只导出基础组件和工厂
__all__ = [
    # 基础组件
    'AudioFormatDetector',
    'TempFileManager', 
    'FFmpegManager',
    # 工厂类和函数
    'ComponentFactory',
    'create_audio_converter',
    'create_strategy_manager',
    'create_format_detector',
    'create_complete_processor'
]

# 版本信息
__version__ = "1.0.2"
