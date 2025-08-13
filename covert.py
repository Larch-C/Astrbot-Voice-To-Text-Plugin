import os
import subprocess
import tempfile
import shutil
import asyncio
from pathlib import Path
from pydub import AudioSegment
from astrbot.api import logger
import pilk
import uuid
# import silk  # 已弃用: SILK库转换已被FFmpeg替代

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
        将SILK文件转换为MP3格式（用于 QQ 语音）- 使用FFmpeg实现

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

            # 使用FFmpeg直接转换SILK为MP3
            logger.info(f"开始使用FFmpeg转换SILK格式: {silk_path} -> {output_path}")
            
            # 尝试FFmpeg转换SILK
            try:
                self._convert_silk_with_ffmpeg(silk_path, output_path)
                logger.info(f"SILK转MP3成功: {silk_path} -> {output_path}")
                return output_path
            except Exception as ffmpeg_error:
                logger.warning(f"FFmpeg转换SILK失败: {ffmpeg_error}")
                
                # 如果FFmpeg失败，尝试备用方法
                logger.info("尝试备用SILK转换方法...")
                try:
                    return self._convert_silk_fallback(silk_path, output_path)
                except Exception as fallback_error:
                    logger.error(f"备用SILK转换方法也失败: {fallback_error}")
                    raise Exception(f"所有SILK转换方法都失败: FFmpeg错误={ffmpeg_error}, 备用方法错误={fallback_error}")

            # 注释：原有的silk库转换方法已被FFmpeg方法替代
            # 以下是原有使用silk-python库的转换代码（已注释）：
            # ================================================================
            # # 先将SILK转为WAV，再转为MP3
            # wav_temp = os.path.join(self.temp_dir, f"{Path(silk_path).stem}_temp.wav")
            # 
            # try:
            #     import silk  # silk-python库
            #     silk.decode(silk_path, wav_temp, 24000)  # 24kHz采样率
            # 
            #     # 将WAV转为MP3
            #     audio = AudioSegment.from_wav(wav_temp)
            #     audio.export(output_path, format="mp3", bitrate="128k")
            # 
            #     # 清理临时文件
            #     if os.path.exists(wav_temp):
            #         os.remove(wav_temp)
            # 
            #     logger.info(f"SILK转MP3成功: {silk_path} -> {output_path}")
            #     return output_path
            # 
            # except ImportError:
            #     logger.error("silk-python库未安装，无法处理SILK格式")
            #     raise
            # ================================================================

        except Exception as e:
            logger.error(f"SILK转MP3失败: {e}")
            raise

    def _convert_amr_with_pydub(self, amr_path: str, output_path: str):
        """使用pydub转换AMR"""
        audio = AudioSegment.from_file(amr_path, format="amr")
        audio.export(output_path, format="mp3", bitrate="128k")
        logger.info("使用pydub转换成功")

    async def _convert_amr_with_ffmpeg_async(self, amr_path: str, output_path: str):
        """使用FFmpeg异步转换AMR - 真正的异步实现"""
        # 检查FFmpeg是否可用 - 跨平台兼容性增强
        ffmpeg_cmd = self._find_ffmpeg_executable()
        if not ffmpeg_cmd:
            raise Exception("FFmpeg未安装或不在PATH中。请参考README.md安装FFmpeg")
            
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

        try:
            # 使用异步子进程，不阻塞事件循环
            if os.name == 'nt':
                # Windows系统异步子进程创建
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Unix系统异步子进程创建
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            try:
                # 异步等待进程完成，设置超时
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=60.0
                )
                
                if process.returncode != 0:
                    # 解码字节串并限制错误信息长度
                    stdout_str = stdout.decode('utf-8', errors='ignore')[:1000] if stdout else ""
                    stderr_str = stderr.decode('utf-8', errors='ignore')[:1000] if stderr else ""
                    error_msg = stderr_str or stdout_str or "未知错误"
                    raise Exception(f"FFmpeg转换失败: {error_msg}")
                    
            except asyncio.TimeoutError:
                # 异步超时处理
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                raise Exception("FFmpeg转换超时")
        
        except Exception as e:
            logger.error(f"异步FFmpeg转换失败: {e}")
            raise
        
        logger.info(f"使用异步FFmpeg转换成功: {ffmpeg_cmd}")

    def _convert_amr_with_ffmpeg(self, amr_path: str, output_path: str):
        """使用FFmpeg转换AMR - 同步包装器，保持向后兼容"""
        # 检查是否在异步上下文中
        try:
            loop = asyncio.get_running_loop()
            # 在异步上下文中，抛出异常提示使用异步版本
            raise RuntimeError("在异步上下文中请直接使用 _convert_amr_with_ffmpeg_async 方法")
        except RuntimeError:
            # 不在异步上下文中，使用 asyncio.run 运行异步版本
            return asyncio.run(self._convert_amr_with_ffmpeg_async(amr_path, output_path))

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

    async def _convert_silk_with_ffmpeg_async(self, silk_path: str, output_path: str):
        """使用FFmpeg异步转换SILK格式 - 真正的异步实现"""
        # 检查FFmpeg是否可用 - 跨平台兼容性增强
        ffmpeg_cmd = self._find_ffmpeg_executable()
        if not ffmpeg_cmd:
            raise Exception("FFmpeg未安装或不在PATH中。请参考README.md安装FFmpeg")
        
        # 确保路径正确处理
        silk_path = os.path.normpath(silk_path)
        output_path = os.path.normpath(output_path)
        
        # FFmpeg转换SILK的命令
        cmd = [
            ffmpeg_cmd, '-i', silk_path,
            '-acodec', 'libmp3lame',
            '-ar', '24000',  # 设置采样率为24kHz（SILK常用采样率）
            '-ab', '128k',   # 设置比特率
            '-ac', '1',      # 单声道
            '-y',            # 覆盖输出文件
            output_path
        ]

        try:
            # 使用异步子进程，不阻塞事件循环
            if os.name == 'nt':
                # Windows系统异步子进程创建
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Unix系统异步子进程创建
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            try:
                # 异步等待进程完成，设置超时
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=60.0
                )
                
                if process.returncode != 0:
                    # 解码字节串并限制错误信息长度
                    stdout_str = stdout.decode('utf-8', errors='ignore')[:1000] if stdout else ""
                    stderr_str = stderr.decode('utf-8', errors='ignore')[:1000] if stderr else ""
                    error_msg = stderr_str or stdout_str or "未知错误"
                    raise Exception(f"FFmpeg转换SILK失败: {error_msg}")
                    
            except asyncio.TimeoutError:
                # 异步超时处理
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                raise Exception("FFmpeg转换SILK超时")
        
        except Exception as e:
            logger.error(f"异步FFmpeg转换SILK失败: {e}")
            raise
        
        logger.info(f"使用异步FFmpeg转换SILK成功: {ffmpeg_cmd}")

    def _convert_silk_with_ffmpeg(self, silk_path: str, output_path: str):
        """使用FFmpeg转换SILK格式 - 同步包装器，保持向后兼容"""
        # 检查是否在异步上下文中
        try:
            loop = asyncio.get_running_loop()
            # 在异步上下文中，抛出异常提示使用异步版本
            raise RuntimeError("在异步上下文中请直接使用 _convert_silk_with_ffmpeg_async 方法")
        except RuntimeError:
            # 不在异步上下文中，使用 asyncio.run 运行异步版本
            return asyncio.run(self._convert_silk_with_ffmpeg_async(silk_path, output_path))

    def _convert_silk_fallback(self, silk_path: str, output_path: str) -> str:
        """SILK格式备用转换方法 - 使用pilk库"""
        try:
            # 方法1: 使用pilk库进行SILK解码（推荐方法）
            try:
                logger.info("尝试使用pilk库解码SILK格式")
                return self._convert_silk_with_pilk(silk_path, output_path)
            except Exception as e:
                logger.debug(f"pilk解码失败: {e}")
                
            # 方法2: 尝试使用PyDub的通用解码器
            try:
                audio = AudioSegment.from_file(silk_path)
                audio.export(output_path, format="mp3", bitrate="128k")
                logger.info("使用PyDub通用解码器转换SILK成功")
                return output_path
            except Exception as e:
                logger.debug(f"PyDub通用解码器失败: {e}")
                
            # 方法3: 尝试作为原始音频数据处理
            try:
                # 跳过SILK文件头，尝试解码音频数据
                with open(silk_path, 'rb') as f:
                    # 跳过SILK文件头（通常前几个字节是标识符）
                    header = f.read(10)
                    if header.startswith(b'\x02#!SILK_V3'):
                        # 跳过SILK V3标识符
                        f.seek(10)
                    else:
                        f.seek(0)
                    
                    raw_data = f.read()
                    
                # 尝试将原始数据作为PCM处理
                audio = AudioSegment.from_raw(
                    raw_data,
                    frame_rate=24000,  # SILK常用采样率
                    channels=1,        # 单声道
                    sample_width=2     # 16位
                )
                audio.export(output_path, format="mp3", bitrate="128k")
                logger.info("使用原始数据方法转换SILK成功")
                return output_path
                
            except Exception as e:
                logger.debug(f"原始数据方法失败: {e}")
                
            # 如果所有备用方法都失败
            raise Exception("所有SILK备用转换方法都失败")
            
        except Exception as e:
            logger.error(f"SILK备用转换失败: {e}")
            raise

    def _convert_silk_with_pilk(self, silk_path: str, output_path: str) -> str:
        """使用pilk库转换SILK格式"""
        try:
            
            # 生成临时PCM文件路径
            pcm_temp = os.path.join(self.temp_dir, f"temp_silk_{uuid.uuid4().hex}.pcm")
            
            try:
                # 使用pilk解码SILK为PCM
                logger.info(f"使用pilk解码SILK: {silk_path} -> {pcm_temp}")
                duration = pilk.decode(silk_path, pcm_temp)
                logger.info(f"SILK解码成功，音频时长: {duration}ms")
                
                # 验证PCM文件是否生成
                if not os.path.exists(pcm_temp) or os.path.getsize(pcm_temp) == 0:
                    raise Exception("pilk解码生成的PCM文件无效")
                
                # 使用pydub将PCM转换为MP3
                # pilk默认输出16-bit, 单声道, 采样率根据原SILK文件确定
                # 常见的SILK采样率: 8000, 12000, 16000, 24000
                sample_rates = [24000, 16000, 12000, 8000]  # 正确的列表语法 按优先级排序
                
                conversion_success = False
                for sample_rate in sample_rates:
                    try:
                        logger.info(f"尝试使用采样率 {sample_rate}Hz 转换PCM到MP3")
                        audio = AudioSegment.from_raw(
                            pcm_temp,
                            frame_rate=sample_rate,
                            channels=1,
                            sample_width=2  # 16-bit = 2 bytes
                        )
                        audio.export(output_path, format="mp3", bitrate="128k")
                        logger.info(f"pilk转换SILK成功: {silk_path} -> {output_path}")
                        conversion_success = True
                        break
                    except Exception as e:
                        logger.debug(f"采样率 {sample_rate}Hz 转换失败: {e}")
                        continue
                
                if not conversion_success:
                    raise Exception("所有采样率都转换失败")
                    
                return output_path
                
            finally:
                # 清理临时PCM文件
                if os.path.exists(pcm_temp):
                    try:
                        os.remove(pcm_temp)
                        logger.debug(f"清理临时PCM文件: {pcm_temp}")
                    except Exception as e:
                        logger.warning(f"清理临时PCM文件失败: {e}")
                
        except ImportError:
            logger.error("pilk库未安装，无法使用pilk解码SILK格式")
            raise Exception("pilk库未安装，请运行: pip install pilk")
        except Exception as e:
            logger.error(f"pilk转换SILK失败: {e}")
            raise

    def _find_ffmpeg_executable(self) -> str:
        """
        跨平台查找FFmpeg可执行文件 - 支持Windows/Mac/Linux/Docker环境
        
        Returns:
            str: FFmpeg可执行文件的完整路径，如果未找到则返回None
        """
        # 1. 首先尝试在PATH中查找标准命令
        standard_commands = ['ffmpeg']
        if os.name == 'nt':  # Windows
            standard_commands.append('ffmpeg.exe')
            
        for cmd in standard_commands:
            if shutil.which(cmd):
                logger.info(f"在PATH中找到FFmpeg: {shutil.which(cmd)}")
                return cmd
                
        logger.debug("未在PATH中找到FFmpeg，尝试搜索常见安装位置...")
        
        # 2. 搜索常见的安装路径
        search_paths = []
        
        if os.name == 'nt':  # Windows
            search_paths = [
                r'C:\ffmpeg\bin\ffmpeg.exe',
                r'C:\Program Files\FFmpeg\bin\ffmpeg.exe', 
                r'C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe',
                os.path.expanduser(r'~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe'),
                os.path.expanduser(r'~\AppData\Local\Microsoft\WindowsApps\ffmpeg.exe'),
                r'C:\ProgramData\chocolatey\bin\ffmpeg.exe',
            ]
        else:  # Mac/Linux/Docker
            search_paths = [
                # 标准Linux路径
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/bin/ffmpeg',
                '/sbin/ffmpeg',
                
                # Docker常见路径
                '/usr/lib/ffmpeg/ffmpeg',
                '/opt/ffmpeg/bin/ffmpeg',
                '/app/ffmpeg',
                
                # Mac常见路径 (Homebrew等)
                '/opt/homebrew/bin/ffmpeg',  # Apple Silicon Mac (M1/M2)
                '/usr/local/Cellar/ffmpeg/*/bin/ffmpeg',  # Intel Mac
                '/opt/local/bin/ffmpeg',  # MacPorts

                '/root/.pyffmpeg/bin/ffmpeg', # 特殊处理
                
                # 用户目录路径
                os.path.expanduser('~/bin/ffmpeg'),
                os.path.expanduser('~/.local/bin/ffmpeg'),
                
                # 其他可能的路径
                '/snap/bin/ffmpeg',  # Snap包
                '/var/lib/snapd/snap/bin/ffmpeg',
            ]
            
        # 搜索所有可能的路径
        for path in search_paths:
            # 处理通配符路径（如Homebrew的版本化路径）
            if '*' in path:
                import glob
                matches = glob.glob(path)
                for match in matches:
                    if os.path.isfile(match) and os.access(match, os.X_OK):
                        logger.info(f"在通配符路径中找到FFmpeg: {match}")
                        return match
            else:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    logger.info(f"在固定路径中找到FFmpeg: {path}")
                    return path
                    
        # 3. 尝试使用whereis命令（Linux/Mac）
        if os.name != 'nt':
            try:
                result = subprocess.run(['whereis', 'ffmpeg'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # whereis输出格式: "ffmpeg: /usr/bin/ffmpeg /usr/share/man/man1/ffmpeg.1"
                    paths = result.stdout.split()[1:]  # 跳过命令名
                    for path in paths:
                        if os.path.isfile(path) and os.access(path, os.X_OK) and 'man' not in path:
                            logger.info(f"通过whereis找到FFmpeg: {path}")
                            return path
            except Exception as e:
                logger.debug(f"whereis命令失败: {e}")
                
        # 4. 尝试使用which命令的变体（适用于某些Docker环境）
        if os.name != 'nt':
            try:
                for which_cmd in ['which', '/usr/bin/which', '/bin/which']:
                    if os.path.exists(which_cmd) or shutil.which(which_cmd.split('/')[-1]):
                        result = subprocess.run([which_cmd, 'ffmpeg'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0 and result.stdout.strip():
                            paths = result.stdout.strip().split('\n')  # 得到路径列表
                            for path in paths:  # 遍历列表
                                if os.path.isfile(path) and os.access(path, os.X_OK):  # 正确：逐一检查每个路径
                                    logger.info(f"通过{which_cmd}找到FFmpeg: {path}")
                                    return path 
            except Exception as e:
                logger.debug(f"which命令搜索失败: {e}")
                
        # 5. 检查环境变量中可能指定的FFmpeg路径
        ffmpeg_env_paths = [
            os.environ.get('FFMPEG_PATH'),
            os.environ.get('FFMPEG_BINARY'),
            os.environ.get('FFMPEG_EXECUTABLE'),
        ]
        
        for env_path in ffmpeg_env_paths:
            if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
                logger.info(f"通过环境变量找到FFmpeg: {env_path}")
                return env_path
                
        # 6. 最后尝试递归搜索一些目录（限制深度避免性能问题）
        if os.name != 'nt':  # 只在Unix系统上进行递归搜索
            search_dirs = ['/usr', '/opt', '/app']
            for search_dir in search_dirs:
                if os.path.isdir(search_dir):
                    try:
                        # 使用find命令进行有限深度搜索
                        result = subprocess.run(['find', search_dir, '-name', 'ffmpeg', 
                                               '-type', 'f', '-executable', '-maxdepth', '3'], 
                                              capture_output=True, text=True, timeout=30)
                        if result.returncode == 0 and result.stdout.strip():
                            paths = result.stdout.strip().split('\n')  # 得到路径列表
                            for path in paths:  # 遍历列表
                                if os.path.isfile(path) and os.access(path, os.X_OK):
                                    logger.info(f"通过递归搜索找到FFmpeg: {path}")
                                    return path
                    except Exception as e:
                        logger.debug(f"递归搜索{search_dir}失败: {e}")
                        continue
        
        logger.error("在所有可能的位置都未找到FFmpeg可执行文件")
        logger.info("FFmpeg搜索详情:")
        logger.info(f"- 操作系统: {os.name}")
        logger.info(f"- PATH环境变量: {os.environ.get('PATH', 'Not found')}")
        logger.info("- 建议解决方案:")
        if os.name == 'nt':
            logger.info("  Windows: 从 https://ffmpeg.org/download.html 下载并添加到PATH")
        else:
            logger.info("  Mac: brew install ffmpeg")
            logger.info("  Ubuntu/Debian: apt-get install ffmpeg")
            logger.info("  CentOS/RHEL: yum install ffmpeg 或 dnf install ffmpeg")
            logger.info("  Docker: 在Dockerfile中添加 RUN apt-get update && apt-get install -y ffmpeg")
            
        return None
