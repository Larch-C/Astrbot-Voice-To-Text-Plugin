import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from pydub import AudioSegment
from astrbot.api import logger


class AudioConverter:
    """音频格式转换工具类 - Windows兼容"""

    def __init__(self):
        # 获取临时目录 - Windows兼容性优化
        self.temp_dir = tempfile.gettempdir()
        
        # Windows系统优化临时目录选择
        if os.name == 'nt':
            # 优先使用TEMP环境变量
            windows_temp = os.environ.get('TEMP') or os.environ.get('TMP')
            if windows_temp and os.path.exists(windows_temp):
                self.temp_dir = windows_temp
            
        # 确保临时目录存在且可写
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 测试写入权限
        try:
            test_file = os.path.join(self.temp_dir, f"astrbot_test_{os.getpid()}.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            logger.warning(f"临时目录写入测试失败: {e}")
            # 使用当前目录作为备用
            self.temp_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(self.temp_dir, exist_ok=True)
            
        logger.info(f"音频转换器初始化完成，临时目录: {self.temp_dir}")

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

    def detect_audio_format(self, file_path: str) -> str:
        """
        检测音频文件格式，增强版本
        """
        try:
            if not self.validate_file(file_path):
                return 'invalid'

            with open(file_path, 'rb') as f:
                header = f.read(12)

            # 检测文件头 - 更严格的验证
            if header.startswith(b'#!AMR\n'):
                logger.info("检测到标准AMR格式")
                return 'amr'
            elif header.startswith(b'#!AMR'):
                logger.info("检测到AMR格式（非标准换行符）")
                return 'amr'
            elif header.startswith(b'\x02#!SILK_V3'):
                logger.info("检测到SILK_V3格式")
                return 'silk'
            elif header.startswith(b'ID3') or header[0:2] == b'\xff\xfb' or header[0:2] == b'\xff\xf3':
                logger.info("检测到MP3格式")
                return 'mp3'
            elif header.startswith(b'RIFF') and b'WAVE' in header:
                logger.info("检测到WAV格式")
                return 'wav'
            elif header.startswith(b'OggS'):
                logger.info("检测到OGG格式")
                return 'ogg'
            else:
                logger.warning(f"未知音频格式，文件头: {header[:10].hex()}")
                return 'unknown'

        except Exception as e:
            logger.error(f"检测音频格式失败: {e}")
            return 'invalid'

    def amr_to_mp3(self, amr_path: str, output_path: str = None) -> str:
        """
        将AMR文件转换为MP3格式 - 增强错误处理版本
        """
        try:
            # 验证输入文件
            if not self.validate_file(amr_path):
                raise ValueError(f"无效的AMR文件: {amr_path}")

            # 再次验证AMR格式
            audio_format = self.detect_audio_format(amr_path)
            if audio_format not in ['amr', 'unknown']:  # 允许unknown格式尝试转换
                logger.warning(f"文件格式为 {audio_format}，但仍尝试作为AMR处理")

            # 生成输出路径
            if output_path is None:
                amr_filename = Path(amr_path).stem
                output_path = os.path.join(self.temp_dir, f"{amr_filename}_{os.getpid()}.mp3")

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            logger.info(f"开始AMR转MP3: {amr_path} -> {output_path}")

            # 尝试多种转换方法
            conversion_methods = [
                self._convert_amr_with_pydub,
                self._convert_amr_with_ffmpeg,
                self._convert_amr_with_fallback
            ]

            last_error = None
            for i, method in enumerate(conversion_methods, 1):
                try:
                    logger.debug(f"尝试转换方法 {i}/{len(conversion_methods)}")
                    method(amr_path, output_path)
                    
                    # 验证转换结果
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        logger.info(f"转换方法 {i} 成功")
                        break
                        
                except Exception as e:
                    last_error = e
                    logger.warning(f"转换方法 {i} 失败: {e}")
                    # 清理可能产生的无效文件
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
                    continue
            else:
                # 所有方法都失败了
                raise Exception(f"所有AMR转换方法都失败，最后错误: {last_error}")

            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise Exception("转换后的文件无效")

            logger.info(f"AMR转MP3成功: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"AMR转MP3失败: {e}")
            raise

    def convert_to_mp3(self, input_path: str, output_path: str = None) -> str:
        """
        智能转换音频文件为MP3格式 - 增强版本
        """
        try:
            # 首先验证文件
            if not self.validate_file(input_path):
                raise ValueError(f"输入文件无效: {input_path}")

            audio_format = self.detect_audio_format(input_path)
            logger.info(f"检测到音频格式: {audio_format}")

            if audio_format == 'invalid':
                raise ValueError("无法识别的音频格式")

            if audio_format == 'mp3':
                logger.info("文件已是MP3格式，无需转换")
                return input_path
            elif audio_format == 'amr':
                return self.amr_to_mp3(input_path, output_path)
            elif audio_format == 'silk':
                return self.silk_to_mp3(input_path, output_path)
            else:
                # 使用通用转换方法
                if output_path is None:
                    input_filename = Path(input_path).stem
                    output_path = os.path.join(self.temp_dir, f"{input_filename}_{os.getpid()}.mp3")

                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format="mp3", bitrate="128k")

                logger.info(f"通用转换成功: {input_path} -> {output_path}")
                return output_path

        except Exception as e:
            logger.error(f"音频转换失败: {e}")
            raise

    def cleanup_temp_files(self, file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path) and (self.temp_dir in file_path or "temp" in file_path):
                os.remove(file_path)
                logger.info(f"清理临时文件: {file_path}")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

    def silk_to_mp3(self, silk_path: str, output_path: str = None) -> str:
        """
        将SILK文件转换为MP3格式（用于 QQ 语音）

        Args:
            silk_path: 输入的SILK文件路径
            output_path: 输出的MP3文件路径

        Returns:
            str: 转换后的MP3文件路径
        """
        try:
            if not os.path.exists(silk_path):
                raise FileNotFoundError(f"SILK文件不存在: {silk_path}")

            if output_path is None:
                silk_filename = Path(silk_path).stem
                output_path = os.path.join(self.temp_dir, f"{silk_filename}.mp3")

            # 先将SILK转为WAV，再转为MP3
            wav_temp = os.path.join(self.temp_dir, f"{Path(silk_path).stem}_temp.wav")

            # 使用silk-python库进行转换
            if not SILK_AVAILABLE:
                logger.error("silk-python库未安装，无法处理SILK格式")
                raise ImportError("silk-python库未安装，无法处理SILK格式")
            
            try:
                silk.decode(silk_path, wav_temp, 24000)  # 24kHz采样率

                # 将WAV转为MP3
                audio = AudioSegment.from_wav(wav_temp)
                audio.export(output_path, format="mp3", bitrate="128k")

                # 清理临时文件
                if os.path.exists(wav_temp):
                    os.remove(wav_temp)

                logger.info(f"SILK转MP3成功: {silk_path} -> {output_path}")
                return output_path

            except ImportError:
                logger.error("silk-python库未安装，无法处理SILK格式")
                raise

        except Exception as e:
            logger.error(f"SILK转MP3失败: {e}")
            raise

    def _convert_amr_with_pydub(self, amr_path: str, output_path: str):
        """使用pydub转换AMR"""
        audio = AudioSegment.from_file(amr_path, format="amr")
        audio.export(output_path, format="mp3", bitrate="128k")
        logger.info("使用pydub转换成功")

    def _convert_amr_with_ffmpeg(self, amr_path: str, output_path: str):
        """使用FFmpeg转换AMR - 增强Windows兼容性"""
        # 检查FFmpeg是否可用 - Windows兼容性增强
        ffmpeg_cmd = 'ffmpeg'
        if not shutil.which(ffmpeg_cmd):
            # Windows系统尝试查找ffmpeg.exe
            if os.name == 'nt':
                ffmpeg_cmd = 'ffmpeg.exe'
                if not shutil.which(ffmpeg_cmd):
                    # 尝试常见的Windows安装路径
                    common_paths = [
                        r'C:\ffmpeg\bin\ffmpeg.exe',
                        r'C:\Program Files\FFmpeg\bin\ffmpeg.exe',
                        r'C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe',
                        os.path.expanduser(r'~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe'),
                        os.path.expanduser(r'~\AppData\Local\Microsoft\WindowsApps\ffmpeg.exe')
                    ]
                    
                    for path in common_paths:
                        if os.path.exists(path):
                            ffmpeg_cmd = path
                            break
                    else:
                        raise Exception("FFmpeg未安装或不在PATH中。请参考README.md安装FFmpeg")
            else:
                raise Exception("FFmpeg未安装或不在PATH中")
            
        # 确保路径在Windows上正确处理
        amr_path = os.path.normpath(amr_path)
        output_path = os.path.normpath(output_path)
        
        cmd = [
            ffmpeg_cmd, '-i', amr_path,
            '-acodec', 'libmp3lame',
            '-ab', '128k',
            '-y',  # 覆盖输出文件
            output_path
        ]

        # Windows系统的子进程调用优化
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            # 使用 Popen 进行流式处理，避免大量输出缓冲在内存中
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            ) as process:
                try:
                    # 设置超时并获取有限的输出
                    stdout, stderr = process.communicate(timeout=60)
                    
                    if process.returncode != 0:
                        # 只记录前1000字符的错误信息，避免内存问题
                        error_msg = (stderr[:1000] if stderr else stdout[:1000]) or "未知错误"
                        raise Exception(f"FFmpeg转换失败: {error_msg}")
                        
                except subprocess.TimeoutExpired:
                    process.kill()
                    raise Exception("FFmpeg转换超时")
        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg转换超时")
        
        logger.info(f"使用FFmpeg转换成功: {ffmpeg_cmd}")

    def _convert_amr_with_fallback(self, amr_path: str, output_path: str):
        """备用转换方法 - 尝试作为其他格式处理"""
        try:
            # 尝试作为wav格式读取
            audio = AudioSegment.from_wav(amr_path)
            audio.export(output_path, format="mp3", bitrate="128k")
            logger.info("使用WAV fallback转换成功")
        except:
            # 尝试原始音频数据读取
            with open(amr_path, 'rb') as f:
                audio = AudioSegment.from_raw(
                    f, 
                    frame_rate=8000, 
                    channels=1, 
                    sample_width=2
                )
                audio.export(output_path, format="mp3", bitrate="128k")
                logger.info("使用RAW fallback转换成功")
