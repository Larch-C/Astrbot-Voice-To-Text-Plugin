"""
音频转换策略模块 - 使用策略模式实现不同的转换方法
"""
from abc import ABC, abstractmethod
import os
import asyncio
from typing import Optional
from astrbot.api import logger
from pydub import AudioSegment
import uuid

# 可选导入pilk库
try:
    import pilk
    PILK_AVAILABLE = True
except ImportError:
    PILK_AVAILABLE = False
    logger.warning("pilk库未安装，SILK格式转换功能将不可用")

from ..config import AudioProcessingConfig
from ..exceptions import AudioConversionError, FFmpegNotFoundError
from ..utils.decorators import async_operation_handler, retry_on_failure
from .ffmpeg_manager import FFmpegManager
from .temp_file_manager import TempFileManager
from ..covert import AudioConverter # 导入 covert.py 中的 AudioConverter
import os # 确保os模块已导入


class ConversionStrategy(ABC):
    """音频转换策略抽象基类"""
    
    def __init__(self, config: AudioProcessingConfig = None):
        self.config = config or AudioProcessingConfig()
    
    @abstractmethod
    async def can_handle(self, input_format: str, output_format: str) -> bool:
        """检查策略是否能处理指定的转换"""
        pass
    
    @abstractmethod
    async def convert(self, input_path: str, output_path: str) -> bool:
        """执行转换"""
        pass
    
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass


class PyDubStrategy(ConversionStrategy):
    """使用PyDub进行音频转换的策略"""
    
    def __init__(self, config: AudioProcessingConfig = None):
        super().__init__(config)
        self._ffmpeg_available = None
        self._check_attempted = False
    
    @property
    def strategy_name(self) -> str:
        return "PyDub转换策略"
    
    async def can_handle(self, input_format: str, output_format: str) -> bool:
        """检查PyDub是否能处理该格式转换"""
        # 检查FFmpeg可用性
        if not await self._check_ffmpeg_availability():
            logger.debug("FFmpeg不可用，PyDub策略跳过需要FFmpeg的格式")
            # 只处理不需要FFmpeg的基础格式
            basic_formats = ['wav']
            return input_format in basic_formats and output_format in basic_formats
        
        # FFmpeg可用时支持更多格式
        supported_formats = ['mp3', 'wav', 'ogg', 'flac', 'amr']
        return input_format in supported_formats and output_format in supported_formats
    
    async def _check_ffmpeg_availability(self) -> bool:
        """检查FFmpeg可用性，带缓存"""
        if not self._check_attempted:
            try:
                import subprocess
                result = subprocess.run(['ffprobe', '-version'], 
                                      capture_output=True, timeout=5)
                self._ffmpeg_available = result.returncode == 0
            except Exception:
                self._ffmpeg_available = False
            self._check_attempted = True
            
            if self._ffmpeg_available:
                logger.info("FFmpeg可用，PyDub策略支持完整格式")
            else:
                logger.warning("FFmpeg不可用，PyDub策略仅支持基础格式")
        
        return self._ffmpeg_available
    
    @async_operation_handler("PyDub音频转换")
    @retry_on_failure(max_retries=2)
    async def convert(self, input_path: str, output_path: str) -> bool:
        """使用PyDub进行转换"""
        try:
            # 在线程池中执行CPU密集型操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._convert_sync, input_path, output_path)
            return True
        except Exception as e:
            # 如果是FFmpeg相关错误，提供更好的错误信息
            error_msg = str(e)
            if 'ffprobe' in error_msg or 'ffmpeg' in error_msg:
                logger.warning(f"PyDub转换失败(FFmpeg相关) - 尝试下一种策略: {error_msg}")
                return False # FFmpeg相关错误时返回False，不抛出异常
            else:
                logger.error(f"PyDub转换失败: {error_msg}")
                raise AudioConversionError(f"PyDub转换失败: {error_msg}") from e
    
    def _convert_sync(self, input_path: str, output_path: str):
        """同步执行PyDub转换"""
        try:
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format="mp3", bitrate="128k")
        except Exception as e:
            # 如果失败，尝试基础的WAV处理
            if 'ffprobe' in str(e) or 'ffmpeg' in str(e):
                logger.debug("尝试基础WAV处理...")
                audio = AudioSegment.from_wav(input_path)
                audio.export(output_path, format="mp3", bitrate="128k")
            else:
                raise


class FFmpegStrategy(ConversionStrategy):
    """使用FFmpeg进行音频转换的策略"""
    
    def __init__(self, config: AudioProcessingConfig = None):
        super().__init__(config)
        self.ffmpeg_manager = FFmpegManager()
    
    @property
    def strategy_name(self) -> str:
        return "FFmpeg转换策略"
    
    async def can_handle(self, input_format: str, output_format: str) -> bool:
        """检查FFmpeg是否可用且能处理该格式"""
        if not self.ffmpeg_manager.is_available():
            return False
        
        # FFmpeg几乎支持所有格式
        supported_formats = ['amr', 'silk', 'mp3', 'wav', 'ogg', 'flac', 'm4a', 'mp4']
        return input_format in supported_formats and output_format in supported_formats
    
    @async_operation_handler("FFmpeg音频转换")
    async def convert(self, input_path: str, output_path: str) -> bool:
        """使用FFmpeg进行转换"""
        try:
            await self.ffmpeg_manager.convert_audio_async(input_path, output_path)
            return True
        except Exception as e:
            logger.info(f"FFmpeg转换失败 - 尝试下一种策略: {e}")
            # raise AudioConversionError(f"FFmpeg转换失败: {str(e)}") from e
            return False

class SilkDecoderExeStrategy(ConversionStrategy):
    """
    使用 silk_v3_decoder.exe 将 SILK 转换为 PCM，再用 FFmpeg 转换为 MP3 的策略。
    仅在 Windows 系统下可用。
    """
    def __init__(self, config: AudioProcessingConfig = None):
        super().__init__(config)
        self.audio_converter_instance = AudioConverter() # 使用 covert.py 中的 AudioConverter
    
    @property
    def strategy_name(self) -> str:
        return "silk_v3_decoder.exe转换策略"
    
    async def can_handle(self, input_format: str, output_format: str) -> bool:
        """检查是否能处理SILK转换，并确保是Windows系统且exe存在"""
        if os.name != 'nt':
            return False
        
        if input_format == 'silk' and output_format == 'mp3':
            # 检查 silk_v3_decoder.exe 是否存在
            try:
                self.audio_converter_instance._find_silk_decoder_executable()
                return True
            except Exception:
                return False
        return False
    
    @async_operation_handler("silk_v3_decoder.exe音频转换")
    @retry_on_failure(max_retries=1) # 外部exe调用，重试次数少一点
    async def convert(self, input_path: str, output_path: str) -> bool:
        """使用 silk_v3_decoder.exe 进行转换"""
        try:
            # 直接调用 covert.py 中实现的 _convert_silk_with_exe 方法
            converted_path = await asyncio.to_thread(
                self.audio_converter_instance._convert_silk_with_exe, 
                input_path, 
                output_path
            )
            return converted_path == output_path
        except Exception as e:
            logger.error(f"silk_v3_decoder.exe 转换失败: {e}")
            raise AudioConversionError(f"silk_v3_decoder.exe 转换失败: {str(e)}") from e


class SilkStrategy(ConversionStrategy):
    """专门处理SILK格式的转换策略 (使用pilk库)"""
    
    def __init__(self, config: AudioProcessingConfig = None):
        super().__init__(config)
        self.temp_manager = TempFileManager()
    
    @property
    def strategy_name(self) -> str:
        return "SILK转换策略 (pilk)"
    
    async def can_handle(self, input_format: str, output_format: str) -> bool:
        """检查是否能处理SILK转换"""
        if not PILK_AVAILABLE:
            return False
        return input_format == 'silk' and output_format == 'mp3'
    
    @async_operation_handler("SILK音频转换 (pilk)")
    @retry_on_failure(max_retries=2)
    async def convert(self, input_path: str, output_path: str) -> bool:
        """转换SILK为MP3"""
        try:
            # 使用pilk库解码SILK为PCM
            with self.temp_manager.temp_file('.pcm', 'silk_') as pcm_temp:
                await self._decode_silk_to_pcm(input_path, pcm_temp)
                await self._convert_pcm_to_mp3(pcm_temp, output_path)
            return True
        except Exception as e:
            logger.error(f"SILK转换失败 (pilk): {e}")
            raise AudioConversionError(f"SILK转换失败 (pilk): {str(e)}") from e
    
    async def _decode_silk_to_pcm(self, silk_path: str, pcm_path: str):
        """使用pilk解码SILK为PCM"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, pilk.decode, silk_path, pcm_path)
    
    async def _convert_pcm_to_mp3(self, pcm_path: str, mp3_path: str):
        """将PCM转换为MP3"""
        # 尝试多个采样率
        sample_rates = [24000, 16000, 12000, 8000]
        
        for sample_rate in sample_rates:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    self._pcm_to_mp3_sync, 
                    pcm_path, mp3_path, sample_rate
                )
                logger.info(f"SILK转换成功，采样率: {sample_rate}Hz")
                return
            except Exception as e:
                logger.debug(f"采样率 {sample_rate}Hz 转换失败: {e}")
                continue
        
        raise AudioConversionError("所有采样率转换都失败")
    
    def _pcm_to_mp3_sync(self, pcm_path: str, mp3_path: str, sample_rate: int):
        """同步执行PCM到MP3转换"""
        audio = AudioSegment.from_raw(
            pcm_path,
            frame_rate=sample_rate,
            channels=1,
            sample_width=2
        )
        audio.export(mp3_path, format="mp3", bitrate="128k")


class FallbackStrategy(ConversionStrategy):
    """备用转换策略 - 基于旧版本的成功方法"""
    
    @property
    def strategy_name(self) -> str:
        return "备用转换策略"
    
    async def can_handle(self, input_format: str, output_format: str) -> bool:
        """备用策略总是可以尝试"""
        return True
    
    def _validate_file(self, file_path: str) -> bool:
        """验证文件是否存在且可读 - 来自旧版本"""
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

            # 检查文件是否可读
            with open(file_path, 'rb') as f:
                header = f.read(10)

            if len(header) < 5:
                logger.error(f"文件头过短: {file_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return False
    
    @async_operation_handler("备用音频转换")
    async def convert(self, input_path: str, output_path: str) -> bool:
        """使用多种备用方法尝试转换 - 基于旧版本的成功策略"""
        # 首先验证文件
        if not self._validate_file(input_path):
            raise AudioConversionError(f"输入文件无效: {input_path}")
        
        # 按优先级排序的备用方法
        fallback_methods = [
            ("通用格式转换", self._try_generic_format),
            ("WAV格式转换", self._try_as_wav), 
            ("多采样率原始音频", self._try_raw_audio_multi_rates),
            ("AMR格式转换", self._try_as_amr),
            ("最大兼容性转换", self._try_maximum_compatibility)
        ]
        
        logger.info(f"开始备用转换，尝试 {len(fallback_methods)} 种方法")
        
        for method_name, method in fallback_methods:
            try:
                logger.info(f"尝试备用方法: {method_name}")
                await method(input_path, output_path)
                
                # 验证输出文件
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"备用方法 '{method_name}' 成功")
                    return True
                else:
                    logger.warning(f"备用方法 '{method_name}' 生成了无效文件")
                    
            except Exception as e:
                logger.debug(f"备用方法 '{method_name}' 失败: {e}")
                # 清理可能的无效输出文件
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                continue
        
        raise AudioConversionError("所有备用转换方法都失败")
    
    async def _try_generic_format(self, input_path: str, output_path: str):
        """通用格式转换 - 让PyDub自动检测"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._generic_convert_sync, input_path, output_path)
    
    def _generic_convert_sync(self, input_path: str, output_path: str):
        """同步通用转换"""
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="mp3", bitrate="128k")
        logger.debug("通用格式转换成功")
    
    async def _try_as_wav(self, input_path: str, output_path: str):
        """尝试作为WAV格式处理"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._wav_convert_sync, input_path, output_path)
    
    def _wav_convert_sync(self, input_path: str, output_path: str):
        """同步WAV转换"""
        audio = AudioSegment.from_wav(input_path)
        audio.export(output_path, format="mp3", bitrate="128k")
        logger.debug("WAV格式转换成功")
    
    async def _try_as_amr(self, input_path: str, output_path: str):
        """尝试作为AMR格式处理"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._amr_convert_sync, input_path, output_path)
    
    def _amr_convert_sync(self, input_path: str, output_path: str):
        """同步AMR转换"""
        audio = AudioSegment.from_file(input_path, format="amr")
        audio.export(output_path, format="mp3", bitrate="128k")
        logger.debug("AMR格式转换成功")
    
    async def _try_raw_audio_multi_rates(self, input_path: str, output_path: str):
        """尝试多种采样率的原始音频转换 - 基于旧版本"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._raw_multi_rates_sync, input_path, output_path)
    
    def _raw_multi_rates_sync(self, input_path: str, output_path: str):
        """同步多采样率原始音频转换"""
        # 常见的音频采样率，按优先级排序
        sample_rates = [24000, 16000, 8000, 12000, 22050, 44100]
        channels_options = [1, 2]  # 单声道和立体声[1]
        sample_widths = [1, 2]     # 16位和8位[1]
        
        with open(input_path, 'rb') as f:
            raw_data = f.read()
        
        for sample_rate in sample_rates:
            for channels in channels_options:
                for sample_width in sample_widths:
                    try:
                        audio = AudioSegment.from_raw(
                            raw_data,
                            frame_rate=sample_rate,
                            channels=channels,
                            sample_width=sample_width
                        )
                        # 尝试导出，如果成功就返回
                        audio.export(output_path, format="mp3", bitrate="128k")
                        logger.debug(f"原始音频转换成功: {sample_rate}Hz, {channels}ch, {sample_width*8}bit")
                        return
                    except Exception as e:
                        logger.debug(f"尝试参数失败 {sample_rate}Hz/{channels}ch/{sample_width*8}bit: {e}")
                        continue
        
        raise Exception("所有原始音频参数组合都失败")
    
    async def _try_maximum_compatibility(self, input_path: str, output_path: str):
        """最大兼容性转换 - 最后的尝试"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._maximum_compatibility_sync, input_path, output_path)
    
    def _maximum_compatibility_sync(self, input_path: str, output_path: str):
        """最大兼容性同步转换"""
        # 方法1: 尝试不同的文件扩展名
        extensions_to_try = ['.wav', '.mp3', '.amr', '.ogg', '.flac']
        
        for ext in extensions_to_try:
            try:
                if ext == '.wav':
                    audio = AudioSegment.from_wav(input_path)
                elif ext == '.mp3':
                    audio = AudioSegment.from_mp3(input_path)
                elif ext == '.amr':
                    audio = AudioSegment.from_file(input_path, format="amr")
                else:
                    audio = AudioSegment.from_file(input_path)
                    
                audio.export(output_path, format="mp3", bitrate="128k")
                logger.debug(f"最大兼容性转换成功，作为{ext}格式处理")
                return
            except Exception as e:
                logger.debug(f"作为{ext}格式处理失败: {e}")
                continue
        
        # 方法2: 如果上述都失败，尝试直接复制文件内容并添加简单头部
        try:
            with open(input_path, 'rb') as src:
                data = src.read()
            
            # 创建一个最小的WAV头部，然后转换
            import struct
            sample_rate = 8000
            channels = 1
            bits_per_sample = 16
            
            # 简化的WAV头部
            wav_header = b'RIFF'
            wav_header += struct.pack('<I', len(data) + 36)
            wav_header += b'WAVE'
            wav_header += b'fmt '
            wav_header += struct.pack('<I', 16)
            wav_header += struct.pack('<H', 1)  # PCM
            wav_header += struct.pack('<H', channels)
            wav_header += struct.pack('<I', sample_rate)
            wav_header += struct.pack('<I', sample_rate * channels * bits_per_sample // 8)
            wav_header += struct.pack('<H', channels * bits_per_sample // 8)
            wav_header += struct.pack('<H', bits_per_sample)
            wav_header += b'data'
            wav_header += struct.pack('<I', len(data))
            
            # 创建临时WAV文件
            temp_wav = input_path + '.temp.wav'
            with open(temp_wav, 'wb') as f:
                f.write(wav_header + data)
            
            try:
                audio = AudioSegment.from_wav(temp_wav)
                audio.export(output_path, format="mp3", bitrate="128k")
                logger.debug("最大兼容性转换成功，使用自制WAV头部")
            finally:
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                    
        except Exception as e:
            logger.debug(f"最大兼容性转换失败: {e}")


class ConversionStrategyManager:
    """音频转换策略管理器 - 统一管理所有转换策略"""
    
    def __init__(self, config: AudioProcessingConfig = None):
        self.config = config or AudioProcessingConfig()
        
        # 初始化所有策略
        self.strategies = [
            SilkDecoderExeStrategy(self.config), # Windows系统下优先使用 silk_v3_decoder.exe
            FFmpegStrategy(self.config),
            PyDubStrategy(self.config),
            SilkStrategy(self.config),
            FallbackStrategy(self.config)
        ]
        
        logger.info("转换策略管理器初始化完成")
    
    async def convert_audio(self, input_path: str, output_path: str, 
                          input_format: str, output_format: str) -> bool:
        """
        使用合适的策略转换音频 - 修复版本（按顺序执行，不并发）
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            input_format: 输入格式
            output_format: 输出格式
            
        Returns:
            bool: 转换是否成功
        """
        logger.info(f"开始音频转换: {input_format} -> {output_format}")
        logger.info(f"输入文件: {input_path}")
        logger.info(f"输出文件: {output_path}")
        
        # 按优先级尝试每个策略，确保顺序执行
        for i, strategy in enumerate(self.strategies, 1):
            try:
                # 检查策略是否能处理该转换
                can_handle = await strategy.can_handle(input_format, output_format)
                if not can_handle:
                    logger.debug(f"策略 {strategy.strategy_name} 不支持 {input_format}->{output_format}，跳过")
                    continue
                
                logger.info(f"尝试策略 {i}/{len(self.strategies)}: {strategy.strategy_name}")
                
                # 清理可能存在的旧输出文件
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                        logger.debug(f"清理旧输出文件: {output_path}")
                    except Exception as e:
                        logger.warning(f"清理旧文件失败: {e}")
                
                # 执行转换
                success = await strategy.convert(input_path, output_path)
                
                # 验证转换结果
                if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"✅ 转换成功: {strategy.strategy_name}")
                    logger.info(f"输出文件大小: {os.path.getsize(output_path)} bytes")
                    return True
                else:
                    if success:
                        logger.warning(f"❌ 策略 {strategy.strategy_name} 返回成功但输出文件无效")
                    else:
                        logger.warning(f"❌ 策略 {strategy.strategy_name} 转换失败")
                    
                    # 清理无效的输出文件
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
                            
            except Exception as e:
                logger.error(f"❌ 策略 {strategy.strategy_name} 出现异常: {e}")
                # 清理可能的无效输出文件
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                continue
        
        logger.error("🚨 所有转换策略都失败")
        return False
    
    def get_available_strategies(self) -> list:
        """获取可用策略列表"""
        return [strategy.strategy_name for strategy in self.strategies]
    
    async def get_strategy_capabilities(self) -> dict:
        """获取各策略的能力信息"""
        capabilities = {}
        for strategy in self.strategies:
            capabilities[strategy.strategy_name] = {
                'can_handle_silk': await strategy.can_handle('silk', 'mp3'),
                'can_handle_amr': await strategy.can_handle('amr', 'mp3'),
                'can_handle_wav': await strategy.can_handle('wav', 'mp3'),
                'can_handle_mp3': await strategy.can_handle('mp3', 'mp3')
            }
        return capabilities
