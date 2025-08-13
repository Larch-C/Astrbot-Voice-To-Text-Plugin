import os
import asyncio
import time
import tempfile
import uuid
import glob
import base64
import aiohttp
import ssl
import certifi
from astrbot.api.message_components import Record
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.core.utils.io import download_image_by_url


class VoiceFileResolver:
    """语音文件路径解析器 - 封装所有文件获取策略"""
    
    def __init__(self):
        """初始化语音文件解析器"""
        logger.debug("初始化VoiceFileResolver")
        
    async def resolve_voice_file_path(self, voice: Record) -> str:
        """
        解析语音文件路径的主入口方法
        
        Args:
            voice: AstrBot语音消息对象
            
        Returns:
            str: 解析后的文件路径，如果失败返回None
        """
        logger.info("开始尝试所有语音资源获取方法")
        
        # 记录Voice对象的所有属性，用于调试
        voice_attrs = {
            'file': getattr(voice, 'file', None),
            'url': getattr(voice, 'url', None), 
            'path': getattr(voice, 'path', None),
            'magic': getattr(voice, 'magic', None),
            'cache': getattr(voice, 'cache', None),
            'proxy': getattr(voice, 'proxy', None),
            'timeout': getattr(voice, 'timeout', None)
        }
        logger.debug(f"Voice对象属性: {voice_attrs}")
        
        # 解析策略列表：按优先级排序
        strategies = [
            ("官方convert_to_file_path", self._strategy_official_convert),
            ("Base64转换方法", self._strategy_base64_conversion),
            ("文件服务注册方法", self._strategy_file_service_registration), 
            ("Path属性直接访问", self._strategy_path_attribute),
            ("URL属性下载", self._strategy_url_download),
            ("File属性处理", self._strategy_file_attribute),
            ("相对路径搜索", self._strategy_relative_path_search),
            ("临时目录搜索", self._strategy_temp_directory_search),
            ("系统默认目录搜索", self._strategy_system_directory_search),
            ("文件名模式匹配", self._strategy_filename_pattern_matching)
        ]
        
        # 逐一尝试所有策略
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"尝试策略: {strategy_name}")
                result = await strategy_func(voice)
                if result and os.path.exists(result):
                    logger.info(f"策略 '{strategy_name}' 成功获取文件: {result}")
                    return result
                else:
                    logger.debug(f"策略 '{strategy_name}' 未获取到有效文件")
            except Exception as e:
                logger.warning(f"策略 '{strategy_name}' 执行失败: {e}")
                continue
        
        logger.error("所有语音资源获取策略都已尝试，均未成功")
        return None

    async def _strategy_official_convert(self, voice: Record) -> str:
        """策略1: 使用官方convert_to_file_path方法"""
        try:
            return await voice.convert_to_file_path()
        except Exception as original_error:
            logger.debug(f"官方convert_to_file_path失败: {original_error}")
            
            # 如果是"not a valid file"错误，尝试修复文件路径
            if "not a valid file" in str(original_error) and voice.file:
                # 尝试在AstrBot数据目录中查找文件
                possible_paths = await self._search_file_in_astrbot_dirs(voice.file)
                if possible_paths:
                    logger.info(f"在AstrBot目录中找到文件: {possible_paths}")
                    return possible_paths[0]  # 修复：返回第一个匹配项而不是整个列表

            
            raise original_error

    async def _strategy_base64_conversion(self, voice: Record) -> str:
        """策略2: Base64数据转换"""
        try:
            base64_data = await voice.convert_to_base64()
            if base64_data:
                # 解码base64并保存为临时文件
                file_extension = self._detect_audio_extension_from_base64(base64_data)
                temp_dir = os.path.join(get_astrbot_data_path(), "temp") 
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_file = os.path.join(temp_dir, f"voice_{uuid.uuid4().hex}{file_extension}")
                
                # 解码并写入文件
                audio_bytes = base64.b64decode(base64_data)
                with open(temp_file, 'wb') as f:
                    f.write(audio_bytes)
                
                logger.info(f"Base64转换成功，临时文件: {temp_file}")
                return temp_file
        except Exception as e:
            logger.debug(f"Base64转换失败: {e}")
            return None

    async def _strategy_file_service_registration(self, voice: Record) -> str:
        """策略3: 文件服务注册"""
        try:
            # 先尝试注册到文件服务，然后下载
            file_service_url = await voice.register_to_file_service()
            if file_service_url:
                # 从文件服务URL下载文件
                downloaded_path = await download_image_by_url(file_service_url)
                logger.info(f"文件服务注册并下载成功: {downloaded_path}")
                return downloaded_path
        except Exception as e:
            logger.debug(f"文件服务注册失败: {e}")
            return None

    async def _strategy_path_attribute(self, voice: Record) -> str:
        """策略4: 直接使用path属性"""
        if hasattr(voice, 'path') and voice.path:
            if os.path.exists(voice.path):
                logger.info(f"Path属性直接命中: {voice.path}")
                return voice.path
            else:
                logger.debug(f"Path属性文件不存在: {voice.path}")
        return None

    async def _strategy_url_download(self, voice: Record) -> str:
        """策略5: URL下载"""
        if hasattr(voice, 'url') and voice.url:
            try:
                # 使用自定义音频下载函数
                downloaded_path = await self._download_audio_file(voice.url)
                logger.info(f"URL下载成功: {downloaded_path}")
                return downloaded_path
            except Exception as e:
                logger.debug(f"URL下载失败: {e}")
        return None

    async def _strategy_file_attribute(self, voice: Record) -> str:
        """策略6: 处理file属性的各种情况"""
        if not voice.file:
            return None
            
        # 情况1: 文件直接存在
        if os.path.exists(voice.file):
            logger.info(f"File属性直接命中: {voice.file}")
            return os.path.abspath(voice.file)
            
        # 情况2: file:// 协议处理
        if voice.file.startswith("file:///"):
            file_path = voice.file[8:]  # 去掉 file:///
            if os.path.exists(file_path):
                logger.info(f"File协议解析成功: {file_path}")
                return file_path
                
        # 情况3: HTTP/HTTPS URL
        if voice.file.startswith(("http://", "https://")):
            try:
                downloaded_path = await download_image_by_url(voice.file)
                logger.info(f"File URL下载成功: {downloaded_path}")
                return downloaded_path
            except Exception as e:
                logger.debug(f"File URL下载失败: {e}")
                
        # 情况4: base64 数据
        if voice.file.startswith("base64://"):
            try:
                base64_data = voice.file[9:]  # 去掉 base64://
                temp_dir = os.path.join(get_astrbot_data_path(), "temp")
                os.makedirs(temp_dir, exist_ok=True)
                
                file_extension = self._detect_audio_extension_from_base64(base64_data)
                temp_file = os.path.join(temp_dir, f"voice_{uuid.uuid4().hex}{file_extension}")
                
                audio_bytes = base64.b64decode(base64_data)
                with open(temp_file, 'wb') as f:
                    f.write(audio_bytes)
                    
                logger.info(f"File base64解码成功: {temp_file}")
                return temp_file
            except Exception as e:
                logger.debug(f"File base64解码失败: {e}")
                
        return None

    async def _strategy_relative_path_search(self, voice: Record) -> str:
        """策略7: 相对路径搜索"""
        if not voice.file or voice.file.startswith(('file:///', 'http', 'base64://')):
            return None
            
        # 在当前目录及子目录中搜索
        search_dirs = [
            os.getcwd(),
            os.path.join(os.getcwd(), "data"),
            os.path.join(os.getcwd(), "temp"),
            os.path.join(os.getcwd(), "cache"),
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                full_path = os.path.join(search_dir, voice.file)
                if os.path.exists(full_path):
                    logger.info(f"相对路径搜索成功: {full_path}")
                    return full_path
        return None

    async def _strategy_temp_directory_search(self, voice: Record) -> str:
        """策略8: 临时目录搜索"""
        if not voice.file:
            return None
            
        temp_dirs = [
            tempfile.gettempdir(),
            "/tmp",
            "C:\\Windows\\Temp" if os.name == 'nt' else None,
            os.path.expanduser("~/tmp"),
        ]
        
        # 添加AstrBot的临时目录
        try:
            temp_dirs.append(os.path.join(get_astrbot_data_path(), "temp"))
        except:
            pass
            
        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                full_path = os.path.join(temp_dir, voice.file)
                if os.path.exists(full_path):
                    logger.info(f"临时目录搜索成功: {full_path}")
                    return full_path
        return None

    async def _strategy_system_directory_search(self, voice: Record) -> str:
        """策略9: 系统默认目录搜索"""
        if not voice.file:
            return None
            
        system_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop"),
            "/var/tmp" if os.name != 'nt' else None,
            "C:\\Users\\Public\\Downloads" if os.name == 'nt' else None,
        ]
        
        for sys_dir in system_dirs:
            if sys_dir and os.path.exists(sys_dir):
                full_path = os.path.join(sys_dir, voice.file)
                if os.path.exists(full_path):
                    logger.info(f"系统目录搜索成功: {full_path}")
                    return full_path
        return None

    async def _strategy_filename_pattern_matching(self, voice: Record) -> str:
        """策略10: 文件名模式匹配"""
        if not voice.file:
            return None
            
        # 搜索模式：在各种目录下查找类似的文件名
        search_patterns = [
            os.path.join(get_astrbot_data_path(), "**", voice.file),
            os.path.join(get_astrbot_data_path(), "**", f"*{voice.file}*"),
            os.path.join(tempfile.gettempdir(), f"*{voice.file}*"),
            os.path.join(os.getcwd(), "**", f"*{voice.file}*"),
        ]
        
        for pattern in search_patterns:
            try:
                matches = glob.glob(pattern, recursive=True)
                for match in matches:
                    if os.path.isfile(match):
                        logger.info(f"模式匹配成功: {match}")
                        return match
            except Exception as e:
                logger.debug(f"模式匹配失败 {pattern}: {e}")
                continue
        
        return None

    # 辅助方法
    async def _search_file_in_astrbot_dirs(self, filename: str) -> str:
        """在AstrBot相关目录中搜索文件"""
        search_paths = []
        try:
            astrbot_data_path = get_astrbot_data_path()
            search_locations = [
                os.path.join(astrbot_data_path, "**", filename),
                os.path.join(astrbot_data_path, "temp", "**", filename),
                os.path.join("/tmp", "**", filename),
                os.path.join(tempfile.gettempdir(), "**", filename),
                # 搜索任何包含该文件名的文件
                os.path.join(astrbot_data_path, "**", f"*{filename}*"),
            ]
            
            for search_pattern in search_locations:
                try:
                    matches = glob.glob(search_pattern, recursive=True)
                    for match in matches:
                        if os.path.isfile(match) and os.path.getsize(match) > 0:
                            search_paths.append(os.path.abspath(match))
                except Exception as e:
                    logger.debug(f"搜索模式失败 {search_pattern}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"AstrBot目录搜索失败: {e}")
            
        return search_paths if search_paths else None

    async def _download_audio_file(self, url: str) -> str:
        """专用的音频文件下载函数，正确处理文件扩展名"""
        try:
            # 创建临时目录
            temp_dir = os.path.normpath(os.path.join(get_astrbot_data_path(), "temp"))
            os.makedirs(temp_dir, exist_ok=True)
            
            # 从URL推测文件扩展名
            file_extension = self._guess_audio_extension_from_url(url)
            
            # 生成临时文件路径
            timestamp = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
            safe_filename = f"{timestamp}{file_extension}".replace(":", "_").replace("/", "_").replace("\\", "_")
            temp_file_path = os.path.normpath(os.path.join(temp_dir, safe_filename))
            
            # 下载文件
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(trust_env=True, connector=connector) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # 根据实际内容检测格式
                        actual_extension = self._detect_audio_extension_from_content(content)
                        if actual_extension and actual_extension != file_extension:
                            final_file_path = os.path.join(temp_dir, f"{timestamp}{actual_extension}")
                        else:
                            final_file_path = temp_file_path
                        
                        with open(final_file_path, 'wb') as f:
                            f.write(content)
                        
                        logger.info(f"音频文件下载成功: {final_file_path}")
                        return final_file_path
                    else:
                        raise Exception(f"下载失败，HTTP状态码: {response.status}")
                        
        except Exception as e:
            logger.error(f"音频文件下载失败: {e}")
            raise

    def _guess_audio_extension_from_url(self, url: str) -> str:
        """从URL推测音频文件扩展名"""
        url_lower = url.lower()
        if '.amr' in url_lower:
            return '.amr'
        elif '.mp3' in url_lower:
            return '.mp3'
        elif '.wav' in url_lower:
            return '.wav'
        elif '.ogg' in url_lower:
            return '.ogg'
        elif '.silk' in url_lower:
            return '.silk'
        elif '.m4a' in url_lower:
            return '.m4a'
        elif '.flac' in url_lower:
            return '.flac'
        else:
            return '.audio'  # 默认扩展名

    def _detect_audio_extension_from_content(self, content: bytes) -> str:
        """从文件内容检测音频文件扩展名"""
        try:
            if content.startswith(b'#!AMR'):
                return '.amr'
            elif content.startswith(b'RIFF') and b'WAVE' in content[:20]:
                return '.wav'
            elif content.startswith(b'ID3') or content[0:2] in [b'\xff\xfb', b'\xff\xf3']:
                return '.mp3'
            elif content.startswith(b'OggS'):
                return '.ogg'
            elif content.startswith(b'\x02#!SILK_V3'):
                return '.silk'
            else:
                return None  # 无法确定格式
        except:
            return None

    def _detect_audio_extension_from_base64(self, base64_data: str) -> str:
        """从base64数据中检测音频文件扩展名"""
        try:
            # 解码前几个字节来检测文件类型
            decoded_header = base64.b64decode(base64_data[:50])
            
            if decoded_header.startswith(b'#!AMR'):
                return '.amr'
            elif decoded_header.startswith(b'RIFF'):
                return '.wav'
            elif decoded_header.startswith(b'ID3') or decoded_header[0:2] in [b'\xff\xfb', b'\xff\xf3']:
                return '.mp3'
            elif decoded_header.startswith(b'OggS'):
                return '.ogg'
            elif decoded_header.startswith(b'\x02#!SILK_V3'):
                return '.silk'
            else:
                return '.audio'  # 默认扩展名
        except:
            return '.audio'
