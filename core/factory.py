"""
组件工厂 - 使用工厂模式管理复杂的依赖关系
"""
from typing import Optional, Dict, Any
from astrbot.api import logger
from ..config import PluginConfig


class ComponentFactory:
    """
    组件工厂类 - 负责创建和管理核心组件
    """
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def create_audio_converter(cls, config: Optional[PluginConfig] = None):
        """
        创建音频转换器实例
        
        Args:
            config: 插件配置，如果为None则使用默认配置
            
        Returns:
            AudioConverter: 音频转换器实例
        """
        try:
            from .audio_converter import AudioConverter
            instance = AudioConverter(config)
            logger.debug("工厂创建音频转换器成功")
            return instance
        except Exception as e:
            logger.error(f"工厂创建音频转换器失败: {e}")
            raise
    
    @classmethod
    def create_conversion_strategy_manager(cls, config: Optional[PluginConfig] = None):
        """
        创建转换策略管理器实例
        
        Args:
            config: 插件配置
            
        Returns:
            ConversionStrategyManager: 策略管理器实例
        """
        try:
            from .conversion_strategies import ConversionStrategyManager
            audio_config = config.audio if config else None
            instance = ConversionStrategyManager(audio_config)
            logger.debug("工厂创建策略管理器成功")
            return instance
        except Exception as e:
            logger.error(f"工厂创建策略管理器失败: {e}")
            raise
    
    @classmethod
    def create_format_detector(cls, config: Optional[PluginConfig] = None):
        """
        创建音频格式检测器实例
        
        Args:
            config: 插件配置
            
        Returns:
            AudioFormatDetector: 格式检测器实例
        """
        try:
            from .audio_format_detector import AudioFormatDetector
            audio_config = config.audio if config else None
            instance = AudioFormatDetector(audio_config)
            logger.debug("工厂创建格式检测器成功")
            return instance
        except Exception as e:
            logger.error(f"工厂创建格式检测器失败: {e}")
            raise
    
    @classmethod
    def create_temp_file_manager(cls, config: Optional[PluginConfig] = None):
        """
        创建临时文件管理器实例
        
        Args:
            config: 插件配置
            
        Returns:
            TempFileManager: 临时文件管理器实例
        """
        try:
            from .temp_file_manager import TempFileManager
            temp_config = config.temp_file if config else None
            instance = TempFileManager(temp_config)
            logger.debug("工厂创建临时文件管理器成功")
            return instance
        except Exception as e:
            logger.error(f"工厂创建临时文件管理器失败: {e}")
            raise
    
    @classmethod
    def create_ffmpeg_manager(cls):
        """
        创建FFmpeg管理器实例
        
        Returns:
            FFmpegManager: FFmpeg管理器实例
        """
        try:
            from .ffmpeg_manager import FFmpegManager
            instance = FFmpegManager()
            logger.debug("工厂创建FFmpeg管理器成功")
            return instance
        except Exception as e:
            logger.error(f"工厂创建FFmpeg管理器失败: {e}")
            raise
    
    @classmethod
    def create_emotion_service(cls):
        """
        创建情绪分析服务实例
        
        Returns:
            EmotionService: 情绪分析服务实例
        """
        try:
            from ..services.emotion_service import EmotionService
            instance = EmotionService()
            logger.debug("工厂创建情绪分析服务成功")
            return instance
        except Exception as e:
            logger.error(f"工厂创建情绪分析服务失败: {e}")
            raise
    
    @classmethod
    def create_complete_audio_processor(cls, config: Optional[PluginConfig] = None):
        """
        创建完整的音频处理器（包含所有依赖）
        
        Args:
            config: 插件配置
            
        Returns:
            dict: 包含所有音频处理组件的字典
        """
        try:
            logger.info("开始创建完整的音频处理器组件集合")
            
            components = {
                'audio_converter': cls.create_audio_converter(config),
                'strategy_manager': cls.create_conversion_strategy_manager(config),
                'format_detector': cls.create_format_detector(config),
                'temp_manager': cls.create_temp_file_manager(config),
                'ffmpeg_manager': cls.create_ffmpeg_manager()
            }
            
            logger.info("完整音频处理器创建成功")
            return components
            
        except Exception as e:
            logger.error(f"创建完整音频处理器失败: {e}")
            raise
    
    @classmethod
    def get_singleton_instance(cls, component_name: str, config: Optional[PluginConfig] = None):
        """
        获取单例模式的组件实例
        
        Args:
            component_name: 组件名称
            config: 插件配置
            
        Returns:
            组件实例
        """
        if component_name not in cls._instances:
            if component_name == 'audio_converter':
                cls._instances[component_name] = cls.create_audio_converter(config)
            elif component_name == 'strategy_manager':
                cls._instances[component_name] = cls.create_conversion_strategy_manager(config)
            elif component_name == 'format_detector':
                cls._instances[component_name] = cls.create_format_detector(config)
            elif component_name == 'temp_manager':
                cls._instances[component_name] = cls.create_temp_file_manager(config)
            elif component_name == 'ffmpeg_manager':
                cls._instances[component_name] = cls.create_ffmpeg_manager()
            elif component_name == 'emotion_service':
                cls._instances[component_name] = cls.create_emotion_service()
            else:
                raise ValueError(f"未知的组件名称: {component_name}")
                
            logger.debug(f"创建单例组件: {component_name}")
        
        return cls._instances[component_name]
    
    @classmethod
    def clear_instances(cls):
        """清理所有单例实例"""
        cls._instances.clear()
        logger.debug("已清理所有工厂单例实例")
    
    @classmethod
    def get_factory_status(cls) -> dict:
        """获取工厂状态信息"""
        return {
            'singleton_instances': list(cls._instances.keys()),
            'total_instances': len(cls._instances),
            'available_components': [
                'audio_converter',
                'strategy_manager', 
                'format_detector',
                'temp_manager',
                'ffmpeg_manager',
                'emotion_service'
            ]
        }


# 便利函数，提供更简洁的接口
def create_audio_converter(config: Optional[PluginConfig] = None):
    """便利函数：创建音频转换器"""
    return ComponentFactory.create_audio_converter(config)

def create_strategy_manager(config: Optional[PluginConfig] = None):
    """便利函数：创建策略管理器"""
    return ComponentFactory.create_conversion_strategy_manager(config)

def create_format_detector(config: Optional[PluginConfig] = None):
    """便利函数：创建格式检测器"""
    return ComponentFactory.create_format_detector(config)

def create_temp_manager(config: Optional[PluginConfig] = None):
    """便利函数：创建临时文件管理器"""
    return ComponentFactory.create_temp_file_manager(config)

def create_ffmpeg_manager():
    """便利函数：创建FFmpeg管理器"""
    return ComponentFactory.create_ffmpeg_manager()

def create_complete_processor(config: Optional[PluginConfig] = None):
    """便利函数：创建完整音频处理器"""
    return ComponentFactory.create_complete_audio_processor(config)
