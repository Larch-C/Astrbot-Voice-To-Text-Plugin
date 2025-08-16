"""
FFmpeg管理器 - 专门管理FFmpeg可执行文件的搜索和调用
"""
import os
import time
import shutil
import subprocess
import asyncio
from typing import Optional, List
from astrbot.api import logger
from ..config import FFmpegConfig
from ..exceptions import FFmpegNotFoundError, ConversionTimeoutError
from ..utils.decorators import cache_result, async_operation_handler

class FFmpegManager:
    """FFmpeg管理器 - 缓存FFmpeg路径并提供统一的调用接口"""
    
    def __init__(self, config: FFmpegConfig = None):
        self.config = config or FFmpegConfig()
        self._ffmpeg_path: Optional[str] = None
        self._search_attempted: bool = False
        self._last_search_time: float = 0
    
    @property
    def ffmpeg_path(self) -> Optional[str]:
        """获取FFmpeg可执行文件路径，带缓存机制"""
        current_time = time.time()
        
        # 检查缓存是否过期
        if (self._search_attempted and 
            current_time - self._last_search_time < self.config.SEARCH_CACHE_TIMEOUT_SECONDS):
            return self._ffmpeg_path
        
        # 重新搜索FFmpeg
        self._ffmpeg_path = self._find_ffmpeg_executable()
        self._search_attempted = True
        self._last_search_time = current_time
        
        if self._ffmpeg_path:
            logger.info(f"FFmpeg路径已缓存: {self._ffmpeg_path}")
        else:
            logger.error("未找到FFmpeg可执行文件")
            
        return self._ffmpeg_path
    
    def is_available(self) -> bool:
        """检查FFmpeg是否可用"""
        return self.ffmpeg_path is not None
    
    def _find_ffmpeg_executable(self) -> Optional[str]:
        """搜索FFmpeg可执行文件 - 健壮版本（借鉴旧版本）"""
        logger.debug("开始搜索FFmpeg可执行文件")
        
        # 1. 首先检查PATH中的标准命令
        standard_commands = ['ffmpeg']
        if os.name == 'nt':  # Windows
            standard_commands.append('ffmpeg.exe')
            
        for cmd in standard_commands:
            path = shutil.which(cmd)
            if path:
                logger.info(f"在PATH中找到FFmpeg: {path}")
                return cmd  # 返回命令名而不是完整路径，让系统自动解析
        
        logger.debug("未在PATH中找到FFmpeg，尝试搜索常见安装位置...")
        
        # 2. 搜索常见的安装路径（扩展版）
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
                '/root/.pyffmpeg/bin/ffmpeg',  # 特殊处理
                
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
        
        # 3. 使用系统命令进一步搜索
        additional_path = self._search_using_system_commands()
        if additional_path:
            return additional_path
        
        # 4. 检查环境变量中可能指定的FFmpeg路径
        ffmpeg_env_paths = [
            os.environ.get('FFMPEG_PATH'),
            os.environ.get('FFMPEG_BINARY'),
            os.environ.get('FFMPEG_EXECUTABLE'),
        ]
        
        for env_path in ffmpeg_env_paths:
            if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
                logger.info(f"通过环境变量找到FFmpeg: {env_path}")
                return env_path
        
        # 5. 最后尝试递归搜索一些目录（限制深度避免性能问题）
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
                            paths = result.stdout.strip().split('\n')
                            for path in paths:
                                if os.path.isfile(path) and os.access(path, os.X_OK):
                                    logger.info(f"通过递归搜索找到FFmpeg: {path}")
                                    return path
                    except Exception as e:
                        logger.debug(f"递归搜索{search_dir}失败: {e}")
                        continue
        
        logger.error("在所有搜索位置都未找到FFmpeg")
        self._log_detailed_search_info()
        return None
    
    def _is_valid_ffmpeg(self, path: str) -> bool:
        """验证FFmpeg路径是否有效"""
        try:
            return os.path.isfile(path) and os.access(path, os.X_OK)
        except Exception:
            return False
    
    def _search_using_system_commands(self) -> Optional[str]:
        """使用系统命令搜索FFmpeg"""
        if os.name == 'nt':  # Windows
            return None  # Windows下已经通过shutil.which搜索了
        
        # Unix系统下使用whereis和which命令
        search_commands = [
            ['whereis', 'ffmpeg'],
            ['which', 'ffmpeg'],
        ]
        
        for cmd in search_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    # 解析输出
                    paths = result.stdout.strip().split()
                    for path in paths:
                        if ('ffmpeg' in path and 
                            'man' not in path and 
                            self._is_valid_ffmpeg(path)):
                            logger.info(f"通过{' '.join(cmd)}找到FFmpeg: {path}")
                            return path
            except Exception as e:
                logger.debug(f"系统命令搜索失败 {' '.join(cmd)}: {e}")
        
        return None
    
    @async_operation_handler("FFmpeg音频转换")
    async def convert_audio_async(self, input_path: str, output_path: str, 
                                 format_options: dict = None) -> bool:
        """异步执行FFmpeg音频转换"""
        if not self.is_available():
            raise FFmpegNotFoundError("FFmpeg未安装或无法找到")
        
        # 构建FFmpeg命令
        cmd = self._build_conversion_command(input_path, output_path, format_options)
        
        try:
            # 使用异步子进程
            if os.name == 'nt':
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            # 等待进程完成，带超时控制
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self.config.CONVERSION_TIMEOUT_SECONDS
                )
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')[:500]
                    raise subprocess.SubprocessError(f"FFmpeg转换失败: {error_msg}")
                
                logger.debug(f"FFmpeg转换成功: {input_path} -> {output_path}")
                return True
                
            except asyncio.TimeoutError:
                # 超时处理
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                raise ConversionTimeoutError("FFmpeg转换超时")
                
        except Exception as e:
            logger.error(f"FFmpeg异步转换失败: {e}")
            raise
    
    def convert_audio_sync(self, input_path: str, output_path: str, 
                          format_options: dict = None) -> bool:
        """同步执行FFmpeg音频转换（向后兼容）"""
        if not self.is_available():
            raise FFmpegNotFoundError("FFmpeg未安装或无法找到")
        
        cmd = self._build_conversion_command(input_path, output_path, format_options)
        
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.config.CONVERSION_TIMEOUT_SECONDS,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.config.CONVERSION_TIMEOUT_SECONDS
                )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')[:500]
                raise subprocess.SubprocessError(f"FFmpeg转换失败: {error_msg}")
            
            logger.debug(f"FFmpeg同步转换成功: {input_path} -> {output_path}")
            return True
            
        except subprocess.TimeoutExpired:
            raise ConversionTimeoutError("FFmpeg转换超时")
        except Exception as e:
            logger.error(f"FFmpeg同步转换失败: {e}")
            raise
    
    def _build_conversion_command(self, input_path: str, output_path: str, 
                                 format_options: dict = None) -> List[str]:
        """构建FFmpeg转换命令"""
        cmd = [self.ffmpeg_path, '-i', os.path.normpath(input_path)]
        
        # 默认转换选项
        default_options = {
            'acodec': 'libmp3lame',
            'ab': '128k',
            'ar': '24000',  # 采样率
            'ac': '1',      # 单声道
        }
        
        # 合并用户选项
        options = {**default_options, **(format_options or {})}
        
        # 添加选项到命令
        for key, value in options.items():
            cmd.extend([f'-{key}', str(value)])
        
        # 添加输出文件和覆盖选项
        cmd.extend(['-y', os.path.normpath(output_path)])
        
        logger.debug(f"FFmpeg命令: {' '.join(cmd)}")
        return cmd
    
    def get_version(self) -> Optional[str]:
        """获取FFmpeg版本信息"""
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 解析版本信息
                lines = result.stdout.split('\n')
                if lines:
                    version_line = lines
                    if 'ffmpeg version' in version_line:
                        return version_line.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"获取FFmpeg版本失败: {e}")
            return None
    
    def clear_cache(self):
        """清理缓存，强制重新搜索FFmpeg"""
        self._ffmpeg_path = None
        self._search_attempted = False
        self._last_search_time = 0
        logger.info("FFmpeg缓存已清理")
    
    def _log_detailed_search_info(self):
        """输出详细的搜索信息和安装建议"""
        logger.info("FFmpeg搜索详情:")
        logger.info(f"- 操作系统: {os.name}")
        logger.info(f"- PATH环境变量: {os.environ.get('PATH', 'Not found')}")
        
        # 检查环境变量
        env_vars = ['FFMPEG_PATH', 'FFMPEG_BINARY', 'FFMPEG_EXECUTABLE']
        for env_var in env_vars:
            value = os.environ.get(env_var)
            logger.info(f"- {env_var}: {value or '未设置'}")
        
        logger.info("- 建议解决方案:")
        if os.name == 'nt':
            logger.info("  Windows: 从 https://ffmpeg.org/download.html 下载并添加到PATH")
            logger.info("  或使用包管理器: choco install ffmpeg 或 scoop install ffmpeg")
        else:
            logger.info("  Mac: brew install ffmpeg")
            logger.info("  Ubuntu/Debian: apt-get install ffmpeg")
            logger.info("  CentOS/RHEL: yum install ffmpeg 或 dnf install ffmpeg")
            logger.info("  Docker: 在Dockerfile中添加 RUN apt-get update && apt-get install -y ffmpeg")
        
        logger.info("- 或设置环境变量 FFMPEG_PATH 指向FFmpeg可执行文件")

    def get_status(self) -> dict:
        """获取FFmpeg管理器状态信息"""
        return {
            'is_available': self.is_available(),
            'ffmpeg_path': self._ffmpeg_path,
            'search_attempted': self._search_attempted,
            'last_search_time': self._last_search_time,
            'cache_valid': (time.time() - self._last_search_time < self.config.SEARCH_CACHE_TIMEOUT_SECONDS),
            'version': self.get_version()
        }
