"""
音频格式检测器 - 专门负责音频文件格式识别
"""
import os
from typing import Optional, Dict, Tuple
from astrbot.api import logger
from ..config import AudioProcessingConfig
from ..exceptions import AudioFormatError, FileValidationError
from ..utils.decorators import cache_result

class AudioFormatDetector:
    """音频格式检测器"""
    
    def __init__(self, config: AudioProcessingConfig = None):
        self.config = config or AudioProcessingConfig()
        
        # 音频格式签名映射
        self.format_signatures = {
            b'#!AMR\n': 'amr',
            b'#!AMR': 'amr',
            b'\x02#!SILK_V3': 'silk',
            b'ID3': 'mp3',
            b'\xff\xfb': 'mp3',
            b'\xff\xf3': 'mp3',
            b'RIFF': 'wav',  # 需要进一步检查WAVE标识
            b'OggS': 'ogg',
            b'fLaC': 'flac',
        }
    
    def validate_file(self, file_path: str) -> bool:
        """验证文件是否存在且可读"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return False

            if not os.path.isfile(file_path):
                logger.error(f"路径不是文件: {file_path}")
                return False

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"文件为空: {file_path}")
                return False

            if file_size < self.config.MIN_FILE_SIZE_BYTES:
                logger.error(f"文件太小: {file_path} ({file_size} bytes)")
                return False

            if file_size > self.config.MAX_FILE_SIZE_MB * 1024 * 1024:
                logger.error(f"文件过大: {file_path} ({file_size} bytes)")
                return False

            # 检查文件是否可读
            with open(file_path, 'rb') as f:
                header = f.read(12)

            if len(header) < 5:
                logger.error(f"文件头过短: {file_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return False
    
    @cache_result(ttl_seconds=300)  # 缓存5分钟
    async def detect_format(self, file_path: str) -> str:
        """
        检测音频文件格式
        
        Returns:
            str: 检测到的格式名称，如果无法识别返回'unknown'，如果文件无效返回'invalid'
        """
        try:
            if not self.validate_file(file_path):
                return 'invalid'

            with open(file_path, 'rb') as f:
                header = f.read(12)

            # 检测已知格式
            detected_format = self._identify_format_by_header(header)
            
            if detected_format:
                logger.info(f"检测到音频格式: {detected_format}")
                return detected_format
            else:
                logger.warning(f"未知音频格式，文件头: {header[:10].hex()}")
                return 'unknown'

        except Exception as e:
            logger.error(f"检测音频格式失败: {e}")
            return 'invalid'
    
    def _identify_format_by_header(self, header: bytes) -> Optional[str]:
        """根据文件头识别格式"""
        # 检查固定格式签名
        for signature, format_name in self.format_signatures.items():
            if header.startswith(signature):
                # WAV格式需要额外验证WAVE标识
                if format_name == 'wav' and b'WAVE' not in header:
                    continue
                return format_name
        
        # 检查MP3的其他可能标识
        if header[0:2] in [b'\xff\xfb', b'\xff\xf3']:
            return 'mp3'
        
        return None
    
    def is_supported_format(self, format_name: str) -> bool:
        """检查格式是否被STT服务支持"""
        return format_name in self.config.SUPPORTED_FORMATS
    
    def needs_conversion(self, format_name: str) -> bool:
        """检查是否需要格式转换"""
        return not self.is_supported_format(format_name) and format_name not in ['invalid', 'unknown']
    
    async def get_format_info(self, file_path: str) -> Dict[str, any]:
        """获取音频文件的详细格式信息"""
        try:
            if not self.validate_file(file_path):
                raise FileValidationError(f"文件验证失败: {file_path}")
            
            file_size = os.path.getsize(file_path)
            
            # 检测格式
            format_name = await self.detect_format(file_path)
            
            return {
                'file_path': file_path,
                'file_size': file_size,
                'format': format_name,
                'is_supported': self.is_supported_format(format_name),
                'needs_conversion': self.needs_conversion(format_name),
                'is_valid': format_name != 'invalid'
            }
            
        except Exception as e:
            logger.error(f"获取格式信息失败: {e}")
            raise AudioFormatError(f"获取音频格式信息失败: {str(e)}") from e
    
    def detect_format_from_extension(self, file_path: str) -> Optional[str]:
        """从文件扩展名推测格式（备用方法）"""
        try:
            _, ext = os.path.splitext(file_path.lower())
            ext_to_format = {
                '.amr': 'amr',
                '.silk': 'silk', 
                '.mp3': 'mp3',
                '.wav': 'wav',
                '.ogg': 'ogg',
                '.flac': 'flac',
                '.m4a': 'm4a',
                '.mp4': 'mp4',
                '.mpeg': 'mpeg',
                '.mpga': 'mpga',
                '.oga': 'oga',
                '.webm': 'webm'
            }
            return ext_to_format.get(ext)
        except Exception:
            return None
