"""
重构后的音频转换器 - 使用工厂模式彻底解决循环导入
"""
import os
from typing import Optional
from astrbot.api import logger
from ..config import PluginConfig
from ..exceptions import AudioConversionError, FileValidationError
from ..utils.decorators import async_operation_handler
from .audio_format_detector import AudioFormatDetector
from .temp_file_manager import TempFileManager

class AudioConverter:
    """重构后的音频转换器 - 使用工厂模式避免直接依赖"""
    
    def __init__(self, config: PluginConfig = None):
        self.config = config or PluginConfig.create_default()
        
        # 初始化各个组件
        self.format_detector = AudioFormatDetector(self.config.audio)
        self.temp_manager = TempFileManager(self.config.temp_file)
        
        # 在初始化时创建并缓存策略管理器
        from .factory import ComponentFactory
        self._strategy_manager = ComponentFactory.create_conversion_strategy_manager(self.config)
        
        logger.info("音频转换器重构版本初始化完成")
    
    def _get_strategy_manager(self):
        """使用工厂方法获取策略管理器，完全避免循环导入"""
        if self._strategy_manager is None:
            # 动态导入工厂类并创建组件
            from .factory import ComponentFactory
            return ComponentFactory.create_conversion_strategy_manager(self.config)
        
        return self._strategy_manager
    
    @async_operation_handler("音频文件验证", log_performance=False)
    async def validate_audio_file(self, file_path: str) -> bool:
        """验证音频文件"""
        return self.format_detector.validate_file(file_path)
    
    @async_operation_handler("音频格式检测")
    async def detect_format(self, file_path: str) -> str:
        """检测音频格式"""
        return await self.format_detector.detect_format(file_path)
    
    @async_operation_handler("音频格式转换")
    async def convert_to_supported_format(self, input_path: str, 
                                        output_path: str = None) -> Optional[str]:
        """
        将音频转换为STT支持的格式 - 修复版本（避免文件被过早清理）
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径，如果为None则自动生成
            
        Returns:
            str: 转换后的文件路径，如果不需要转换则返回原路径
        """
        try:
            # 1. 检测格式
            input_format = await self.detect_format(input_path)
            
            if input_format == 'invalid':
                raise FileValidationError("输入文件无效")
            
            # 2. 检查是否需要转换
            if self.format_detector.is_supported_format(input_format):
                logger.info(f"音频格式 {input_format} 已支持，无需转换")
                return input_path
            
            # 3. 生成输出路径 - 修复版本：不使用context manager避免过早清理
            if output_path is None:
                # 创建持久化的临时文件，不自动清理
                output_path = self.temp_manager.create_temp_file('.mp3', 'converted_')
                logger.info(f"生成转换输出路径: {output_path}")
            
            # 4. 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"确保输出目录存在: {output_dir}")
            
            # 5. 执行转换
            strategy_manager = self._get_strategy_manager()
            success = await strategy_manager.convert_audio(
                input_path, output_path, input_format, 'mp3'
            )
            
            if success:
                # 验证转换结果
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"✅ 音频转换成功: {input_path} -> {output_path}")
                    logger.info(f"输出文件大小: {os.path.getsize(output_path)} bytes")
                    return output_path
                else:
                    logger.error(f"❌ 转换后文件无效: {output_path}")
                    # 清理无效文件
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
                    raise AudioConversionError("转换成功但输出文件无效")
            else:
                logger.error("❌ 音频转换策略执行失败")
                raise AudioConversionError("转换失败")
                
        except Exception as e:
            logger.error(f"音频转换失败: {e}")
            raise
    
    def get_format_info(self, file_path: str) -> dict:
        """获取音频文件格式信息"""
        return self.format_detector.get_format_info(file_path)
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        self.temp_manager.cleanup_all()
    
    def get_status(self) -> dict:
        """获取转换器状态"""
        strategy_manager = self._get_strategy_manager()
        return {
            'available_strategies': strategy_manager.get_available_strategies(),
            'temp_files_count': self.temp_manager.get_managed_files_count(),
            'temp_dir': self.temp_manager.get_temp_dir(),
            'supported_formats': self.config.audio.SUPPORTED_FORMATS
        }
