import os
import asyncio
import time
import tempfile
import uuid
from astrbot.api.message_components import Record
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.event import filter
import astrbot.api.star as star
from astrbot.api.star import register, Context
from astrbot.api import logger, AstrBotConfig
from .covert import AudioConverter  # 导入音频转换工具类

@register("voice_to_text", "NickMo", "语音转文字智能回复插件", "1.0.0", "")
class VoiceToTextPlugin(star.Star):
    """语音转文字智能回复插件 - 集成音频转换功能"""

    def __init__(self, context: Context, config: AstrBotConfig = None) -> None:
        super().__init__(context)
        self.context = context
        self.config = config or {}

        # 基础配置项
        self.enable_chat_reply = self.config.get("enable_chat_reply", True)
        self.console_output = self.config.get("console_output", True)
        self.enable_audio_conversion = self.config.get("enable_audio_conversion", True)
        self.max_audio_size_mb = self.config.get("max_audio_size_mb", 25)
        
        # 群聊相关配置
        group_settings = self.config.get("Group_Chat_Settings", {})
        self.enable_group_voice_recognition = group_settings.get("Enable_Group_Voice_Recognition", True)
        self.enable_group_voice_reply = group_settings.get("Enable_Group_Voice_Reply", False)
        self.group_recognition_whitelist = group_settings.get("Group_Recognition_Whitelist", [])
        self.group_reply_whitelist = group_settings.get("Group_Reply_Whitelist", [])
        self.group_recognition_blacklist = group_settings.get("Group_Recognition_Blacklist", [])
        self.group_reply_blacklist = group_settings.get("Group_Reply_Blacklist", [])

        # 初始化音频转换器
        self.audio_converter = AudioConverter()

        logger.info("语音转文字插件已加载 - 支持群聊语音识别功能")

    def should_process_voice(self, event: AstrMessageEvent) -> bool:
        """检查是否应该处理语音消息"""
        from astrbot.core.platform.message_type import MessageType
        
        message_type = event.get_message_type()
        group_id = event.get_group_id()
        
        # 私聊消息总是处理
        if message_type == MessageType.FRIEND_MESSAGE:
            logger.debug("私聊消息，允许语音识别")
            return True
            
        # 群聊消息需要检查权限
        if message_type == MessageType.GROUP_MESSAGE:
            return self.check_group_voice_permission(group_id, "recognition")
            
        # 其他类型消息不处理
        logger.debug(f"未知消息类型: {message_type}")
        return False

    def check_group_voice_permission(self, group_id: str, action: str) -> bool:
        """检查群聊语音权限
        
        Args:
            group_id: 群聊ID
            action: 操作类型 ("recognition" 或 "reply")
        
        Returns:
            bool: 是否允许操作
        """
        # 详细的调试日志
        logger.debug(f"开始检查群聊权限 - group_id: {group_id}, action: {action}")
        
        if not group_id:
            logger.debug("群聊ID为空，拒绝处理")
            return False
            
        if action == "recognition":
            logger.debug(f"检查语音识别权限 - 启用状态: {self.enable_group_voice_recognition}")
            
            # 检查是否启用群聊语音识别
            if not self.enable_group_voice_recognition:
                logger.debug(f"群聊语音识别已禁用: {group_id}")
                return False
                
            # 检查黑名单
            logger.debug(f"检查识别黑名单 - 黑名单: {self.group_recognition_blacklist}")
            if group_id in self.group_recognition_blacklist:
                logger.debug(f"群聊在语音识别黑名单中: {group_id}")
                return False
                
            # 检查白名单（如果白名单不为空）
            logger.debug(f"检查识别白名单 - 白名单: {self.group_recognition_whitelist}, 是否为空: {not bool(self.group_recognition_whitelist)}")
            if self.group_recognition_whitelist:
                if group_id not in self.group_recognition_whitelist:
                    logger.debug(f"群聊不在语音识别白名单中: {group_id}")
                    return False
                else:
                    logger.debug(f"群聊在语音识别白名单中: {group_id}")
            else:
                logger.debug(f"语音识别白名单为空，允许所有群聊: {group_id}")
                    
        elif action == "reply":
            logger.debug(f"检查语音回复权限 - 启用状态: {self.enable_group_voice_reply}")
            
            # 检查是否启用群聊语音回复
            if not self.enable_group_voice_reply:
                logger.debug(f"群聊语音回复已禁用: {group_id}")
                return False
                
            # 检查黑名单
            logger.debug(f"检查回复黑名单 - 黑名单: {self.group_reply_blacklist}")
            if group_id in self.group_reply_blacklist:
                logger.debug(f"群聊在语音回复黑名单中: {group_id}")
                return False
                
            # 检查白名单（如果白名单不为空）
            logger.debug(f"检查回复白名单 - 白名单: {self.group_reply_whitelist}, 是否为空: {not bool(self.group_reply_whitelist)}")
            if self.group_reply_whitelist:
                if group_id not in self.group_reply_whitelist:
                    logger.debug(f"群聊不在语音回复白名单中: {group_id}")
                    return False
                else:
                    logger.debug(f"群聊在语音回复白名单中: {group_id}")
            else:
                logger.debug(f"语音回复白名单为空，允许所有群聊: {group_id}")
        
        logger.debug(f"群聊语音{action}权限检查通过: {group_id}")
        return True

    def should_generate_reply(self, event: AstrMessageEvent) -> bool:
        """检查是否应该生成智能回复"""
        from astrbot.core.platform.message_type import MessageType
        
        message_type = event.get_message_type()
        group_id = event.get_group_id()
        
        # 私聊消息总是回复
        if message_type == MessageType.FRIEND_MESSAGE:
            logger.debug("私聊消息，允许智能回复")
            return True
            
        # 群聊消息需要检查回复权限
        if message_type == MessageType.GROUP_MESSAGE:
            return self.check_group_voice_permission(group_id, "reply")
            
        # 其他类型消息不回复
        logger.debug(f"未知消息类型，不生成回复: {message_type}")
        return False

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent, context=None):
        """监听所有消息,处理语音消息"""
        for comp in event.message_obj.message:
            if isinstance(comp, Record):
                # 检查是否应该处理此语音消息
                if self.should_process_voice(event):
                    async for result in self.process_voice(event, comp):
                        yield result
                else:
                    logger.debug(f"跳过语音处理 - 群聊权限检查未通过: {event.get_group_id()}")

    async def process_voice(self, event: AstrMessageEvent, voice: Record):
        """处理语音消息的完整流程 - 增强错误处理"""
        converted_file_path = None
        try:
            logger.info(f"收到来自 {event.get_sender_name()} 的语音消息")
            logger.debug(f"语音文件信息: file={voice.file}, url={voice.url}, path={getattr(voice, 'path', None)}")

            # 获取语音文件路径 - 增强错误处理
            try:
                original_file_path = await voice.convert_to_file_path()
            except Exception as e:
                logger.error(f"语音文件路径转换失败: {e}")
                logger.debug(f"尝试其他方式获取文件路径...")
                
                # 尝试备用方法获取文件路径
                original_file_path = await self.get_voice_file_path_fallback(voice)
                
                if not original_file_path:
                    yield event.plain_result("无法获取语音文件，请重新发送")
                    return

            # 增强文件验证
            if not original_file_path or not os.path.exists(original_file_path):
                logger.error(f"语音文件不存在: {original_file_path}")
                yield event.plain_result("语音文件下载失败或路径无效")
                return

            # 验证文件完整性
            if not self.audio_converter.validate_file(original_file_path):
                yield event.plain_result("语音文件损坏或格式无效")
                return

            file_size = os.path.getsize(original_file_path)
            logger.info(f"原始语音文件: {original_file_path}, 大小: {file_size} 字节")

            # 检查文件大小
            if file_size > self.max_audio_size_mb * 1024 * 1024:
                logger.error(f"语音文件过大，请发送小于{self.max_audio_size_mb}MB的文件")
                return

            if file_size < 100:  # 小于100字节认为无效
                logger.error("语音文件太小，可能损坏")
                return

            # 发送处理提示
            logger.info("正在处理语音文件...")

            # 检测音频格式
            audio_format = self.audio_converter.detect_audio_format(original_file_path)
            logger.info(f"检测到音频格式: {audio_format}")

            if audio_format == 'invalid':
                logger.error("音频文件格式无效或损坏")
                return

            # 检查音频格式是否被STT服务支持
            whisper_supported_formats = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']
            needs_conversion = audio_format not in whisper_supported_formats and audio_format not in ['mp3', 'wav']
            
            # 音频格式转换 - 确保转换为STT支持的格式
            if self.enable_audio_conversion and needs_conversion:
                try:
                    logger.info(f"正在转换{audio_format.upper()}格式为MP3...")
                    converted_file_path = await self.convert_audio_file_with_retry(original_file_path)

                    if not converted_file_path:
                        logger.error("音频格式转换失败")
                        return  # 如果转换失败，直接返回，不再尝试识别
                    else:
                        final_file_path = converted_file_path
                        logger.info(f"音频转换成功: {final_file_path}")
                        
                        # 验证转换后的文件格式
                        converted_format = self.audio_converter.detect_audio_format(final_file_path)
                        if converted_format not in whisper_supported_formats:
                            logger.error(f"转换后格式({converted_format})仍不被STT支持")
                            return

                except Exception as e:
                    logger.error(f"音频转换出错: {e}")
                    logger.error("音频格式转换失败，无法进行语音识别")
                    return  # 转换失败就不再继续
            else:
                final_file_path = original_file_path
                
                # 如果不需要转换，但格式仍然不被支持，提醒用户
                if audio_format not in whisper_supported_formats:
                    logger.error(f"检测到{audio_format.upper()}格式，可能不被STT服务支持")

            # 语音识别
            logger.info("正在识别语音内容...")
            transcribed_text = await self.call_official_stt(final_file_path)

            if not transcribed_text:
                logger.error("语音识别失败，请检查文件格式或重试")
                return

            # 输出识别结果
            if self.console_output:
                logger.info(f"语音识别结果: {transcribed_text}")

            # 显示识别结果
            logger.info(f"语音识别结果:\n{transcribed_text}")

            # 生成智能回复 - 检查群聊回复权限
            if self.enable_chat_reply and self.should_generate_reply(event):
                async for reply in self.call_official_chatllm(event, transcribed_text):
                    yield reply

        except Exception as e:
            logger.error(f"处理语音消息出错: {e}")
            logger.error(f"处理语音消息时出错: {str(e)}")
        finally:
            # 清理临时文件
            if converted_file_path and converted_file_path != original_file_path:
                self.audio_converter.cleanup_temp_files(converted_file_path)

    async def get_voice_file_path_fallback(self, voice: Record) -> str:
        """全面的语音文件路径获取方法 - 使用AstrBot提供的所有方法"""
        logger.info("开始尝试AstrBot的所有语音资源获取方法")
        
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
        
        # 方法列表：按优先级排序，每个方法都会被尝试
        methods = [
            ("官方convert_to_file_path", self._try_convert_to_file_path),
            ("Base64转换方法", self._try_base64_conversion),
            ("文件服务注册方法", self._try_file_service_registration), 
            ("Path属性直接访问", self._try_path_attribute),
            ("URL属性下载", self._try_url_download),
            ("File属性处理", self._try_file_attribute),
            ("相对路径搜索", self._try_relative_path_search),
            ("临时目录搜索", self._try_temp_directory_search),
            ("系统默认目录搜索", self._try_system_directory_search),
            ("文件名模式匹配", self._try_filename_pattern_matching)
        ]
        
        # 逐一尝试所有方法
        for method_name, method_func in methods:
            try:
                logger.info(f"尝试方法: {method_name}")
                result = await method_func(voice)
                if result and os.path.exists(result):
                    logger.info(f"方法 '{method_name}' 成功获取文件: {result}")
                    return result
                else:
                    logger.debug(f"方法 '{method_name}' 未获取到有效文件")
            except Exception as e:
                logger.warning(f"方法 '{method_name}' 执行失败: {e}")
                continue
        
        logger.error("所有语音资源获取方法都已尝试，均未成功")
        return None

    async def _try_convert_to_file_path(self, voice: Record) -> str:
        """尝试使用官方convert_to_file_path方法 - 增强版本"""
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
                    return possible_paths
            
            raise original_error
            
    async def _search_file_in_astrbot_dirs(self, filename: str) -> list:
        """在AstrBot相关目录中搜索文件"""
        import glob
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path
        
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
            
        return search_paths

    async def _try_base64_conversion(self, voice: Record) -> str:
        """尝试使用base64转换后保存为临时文件"""
        try:
            base64_data = await voice.convert_to_base64()
            if base64_data:
                # 解码base64并保存为临时文件
                import tempfile
                import uuid
                from astrbot.core.utils.astrbot_path import get_astrbot_data_path
                
                # 尝试检测文件扩展名
                file_extension = self._detect_audio_extension_from_base64(base64_data)
                temp_dir = os.path.join(get_astrbot_data_path(), "temp") 
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_file = os.path.join(temp_dir, f"voice_{uuid.uuid4().hex}{file_extension}")
                
                # 解码并写入文件
                import base64
                audio_bytes = base64.b64decode(base64_data)
                with open(temp_file, 'wb') as f:
                    f.write(audio_bytes)
                
                logger.info(f"Base64转换成功，临时文件: {temp_file}")
                return temp_file
        except Exception as e:
            logger.debug(f"Base64转换失败: {e}")
            return None

    async def _try_file_service_registration(self, voice: Record) -> str:
        """尝试使用文件服务注册方法"""
        try:
            # 先尝试注册到文件服务，然后下载
            file_service_url = await voice.register_to_file_service()
            if file_service_url:
                # 从文件服务URL下载文件
                from astrbot.core.utils.io import download_image_by_url
                downloaded_path = await download_image_by_url(file_service_url)
                logger.info(f"文件服务注册并下载成功: {downloaded_path}")
                return downloaded_path
        except Exception as e:
            logger.debug(f"文件服务注册失败: {e}")
            return None

    async def _try_path_attribute(self, voice: Record) -> str:
        """尝试直接使用path属性"""
        if hasattr(voice, 'path') and voice.path:
            if os.path.exists(voice.path):
                logger.info(f"Path属性直接命中: {voice.path}")
                return voice.path
            else:
                logger.debug(f"Path属性文件不存在: {voice.path}")
        return None

    async def _try_url_download(self, voice: Record) -> str:
        """尝试从URL下载"""
        if hasattr(voice, 'url') and voice.url:
            try:
                # 使用自定义音频下载函数，而不是download_image_by_url
                downloaded_path = await self._download_audio_file(voice.url)
                logger.info(f"URL下载成功: {downloaded_path}")
                return downloaded_path
            except Exception as e:
                logger.debug(f"URL下载失败: {e}")
        return None

    async def _download_audio_file(self, url: str) -> str:
        """专用的音频文件下载函数，正确处理文件扩展名 - Windows兼容性增强"""
        try:
            import aiohttp
            import ssl
            import certifi
            import uuid
            import os
            from astrbot.core.utils.astrbot_path import get_astrbot_data_path
            
            # 创建临时目录 - Windows路径规范化
            temp_dir = os.path.normpath(os.path.join(get_astrbot_data_path(), "temp"))
            os.makedirs(temp_dir, exist_ok=True)
            
            # 从URL推测文件扩展名
            file_extension = self._guess_audio_extension_from_url(url)
            
            # 生成临时文件路径 - Windows文件名安全处理
            timestamp = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
            # 确保文件名在Windows系统上是安全的
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
                            # 如果检测到的格式与URL推测的不同，使用检测到的格式
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

    async def _try_file_attribute(self, voice: Record) -> str:
        """尝试处理file属性的各种情况"""
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
                from astrbot.core.utils.io import download_image_by_url
                downloaded_path = await download_image_by_url(voice.file)
                logger.info(f"File URL下载成功: {downloaded_path}")
                return downloaded_path
            except Exception as e:
                logger.debug(f"File URL下载失败: {e}")
                
        # 情况4: base64 数据
        if voice.file.startswith("base64://"):
            try:
                base64_data = voice.file[9:]  # 去掉 base64://
                import base64
                import uuid
                from astrbot.core.utils.astrbot_path import get_astrbot_data_path
                
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

    async def _try_relative_path_search(self, voice: Record) -> str:
        """尝试相对路径搜索"""
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

    async def _try_temp_directory_search(self, voice: Record) -> str:
        """尝试在临时目录中搜索"""
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
            from astrbot.core.utils.astrbot_path import get_astrbot_data_path
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

    async def _try_system_directory_search(self, voice: Record) -> str:
        """尝试在系统默认目录中搜索"""
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

    async def _try_filename_pattern_matching(self, voice: Record) -> str:
        """尝试文件名模式匹配"""
        if not voice.file:
            return None
            
        import glob
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path
        
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

    def _detect_audio_extension_from_base64(self, base64_data: str) -> str:
        """从base64数据中检测音频文件扩展名"""
        try:
            import base64
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

    async def convert_audio_file_with_retry(self, original_file_path: str, max_retries: int = 2) -> str:
        """带重试机制的音频转换"""
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"音频转换尝试 {attempt + 1}/{max_retries + 1}")
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.audio_converter.convert_to_mp3, original_file_path
                )
                return result
            except Exception as e:
                logger.warning(f"转换尝试 {attempt + 1} 失败: {e}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(1)  # 重试前等待1秒
        return None

    async def convert_audio_file(self, original_file_path: str) -> str:
        """转换音频文件格式"""
        try:
            # 检测音频格式
            audio_format = self.audio_converter.detect_audio_format(original_file_path)
            logger.info(f"检测到音频格式: {audio_format}")

            # 如果已经是支持的格式，直接返回
            if audio_format in ['mp3', 'wav']:
                logger.info("音频格式已支持，无需转换")
                return original_file_path

            # 执行格式转换
            if audio_format == 'amr':
                logger.info("正在转换AMR格式到MP3...")
                converted_path = self.audio_converter.amr_to_mp3(original_file_path)
            elif audio_format == 'silk':
                logger.info("正在转换SILK格式到MP3...")
                converted_path = self.audio_converter.silk_to_mp3(original_file_path)
            else:
                logger.info("正在进行通用音频格式转换...")
                converted_path = self.audio_converter.convert_to_mp3(original_file_path)

            if os.path.exists(converted_path):
                logger.info(f"音频转换成功: {converted_path}")
                return converted_path
            else:
                logger.error("音频转换失败: 输出文件不存在")
                return None

        except Exception as e:
            logger.error(f"音频转换失败: {e}")
            return None

    async def call_official_stt(self, audio_file_path: str) -> str:
        """直接调用官方AstrBot STT接口"""
        try:
            # 获取官方STT提供商
            stt_provider = self.context.get_using_stt_provider()

            if not stt_provider:
                logger.error("未配置官方STT提供商")
                return ""

            logger.info(f"使用官方STT提供商: {type(stt_provider).__name__}")

            # 直接调用官方STT接口
            result = await stt_provider.get_text(audio_file_path)

            if result:
                logger.info("官方STT识别成功")
                return result
            else:
                logger.warning("官方STT返回空结果")
                return ""

        except Exception as e:
            logger.error(f"调用官方STT接口失败: {e}")
            return ""

    async def call_official_chatllm(self, event: AstrMessageEvent, text: str):
        """直接调用官方AstrBot ChatLLM接口"""
        try:
            # 获取官方LLM提供商
            llm_provider = self.context.get_using_provider()

            if not llm_provider:
                logger.error("未配置官方聊天服务提供商，无法生成智能回复")
                return

            logger.info(f"使用官方LLM提供商: {type(llm_provider).__name__}")
            logger.info(f"正在生成对语音内容的智能回复: {text}")

            # 发送处理提示
            logger.info("正在生成智能回复...")

            # 获取当前对话ID和上下文
            curr_cid = await self.context.conversation_manager.get_curr_conversation_id(
                event.unified_msg_origin
            )
            conversation = None
            context = []

            if curr_cid:
                conversation = await self.context.conversation_manager.get_conversation(
                    event.unified_msg_origin, curr_cid
                )
                if conversation:
                    import json
                    try:
                        context = json.loads(conversation.history)
                    except json.JSONDecodeError:
                        context = []

            # 构造提示词 - 移除自定义system_prompt，让框架使用配置的人格
            prompt = f"用户通过语音说了: {text}\n请自然地回应用户的语音内容。"

            # 直接调用官方LLM接口生成回复 - 不传递system_prompt，使用框架人格
            yield event.request_llm(
                prompt=prompt,
                session_id=curr_cid,
                contexts=context,
                conversation=conversation
            )

        except Exception as e:
            logger.error(f"调用官方ChatLLM接口失败: {e}")
            logger.error(f"生成智能回复时出错: {str(e)}")

    @filter.command("voice_status")
    async def voice_status_command(self, event: AstrMessageEvent):
        """查看语音转文字插件状态"""
        try:
            # 检查STT提供商状态
            stt_provider = self.context.get_using_stt_provider()
            stt_status = "✅ 已配置" if stt_provider else "❌ 未配置"
            stt_name = type(stt_provider).__name__ if stt_provider else "无"

            # 检查LLM提供商状态
            llm_provider = self.context.get_using_provider()
            llm_status = "✅ 已配置" if llm_provider else "❌ 未配置"
            llm_name = type(llm_provider).__name__ if llm_provider else "无"

            # 群聊配置信息
            group_recognition_status = "✅ 启用" if self.enable_group_voice_recognition else "❌ 禁用"
            group_reply_status = "✅ 启用" if self.enable_group_voice_reply else "❌ 禁用"
            
            status_info = f"""🎙️ 语音转文字插件状态:

                📡 官方STT接口: {stt_status}
                提供商: {stt_name}

                🤖 官方ChatLLM接口: {llm_status}
                提供商: {llm_name}

                🔄 音频转换: {'✅ 启用' if self.enable_audio_conversion else '❌ 禁用'}

                ⚙️ 基础配置:
                - 智能回复: {'✅ 启用' if self.enable_chat_reply else '❌ 禁用'}
                - 控制台输出: {'✅ 启用' if self.console_output else '❌ 禁用'}
                - 文件大小限制: {self.max_audio_size_mb}MB

                👥 群聊配置:
                - 群聊语音识别: {group_recognition_status}
                - 群聊语音回复: {group_reply_status}
                - 识别白名单群数: {len(self.group_recognition_whitelist)}
                - 回复白名单群数: {len(self.group_reply_whitelist)}
                - 识别黑名单群数: {len(self.group_recognition_blacklist)}
                - 回复黑名单群数: {len(self.group_reply_blacklist)}

                💡 支持格式: AMR, SILK, MP3, WAV等
                💡 使用方法: 直接发送语音消息即可"""
            
            yield event.plain_result(status_info.strip())

        except Exception as e:
            logger.error(f"获取状态信息失败: {e}")
            logger.error(f"获取状态失败: {str(e)}")

    @filter.command("voice_test")
    async def voice_test_command(self, event: AstrMessageEvent):
        """测试官方接口连接和音频转换功能"""
        try:
            logger.info("🔍 正在测试插件功能...")

            # 测试STT提供商
            stt_provider = self.context.get_using_stt_provider()
            if stt_provider:
                logger.info(f"✅ STT提供商连接正常: {type(stt_provider).__name__}")
            else:
                logger.error("❌ STT提供商未配置")

            # 测试LLM提供商
            llm_provider = self.context.get_using_provider()
            if llm_provider:
                logger.info(f"✅ LLM提供商连接正常: {type(llm_provider).__name__}")
            else:
                logger.error("❌ LLM提供商未配置")

            # 测试音频转换器
            if self.audio_converter:
                logger.info("✅ 音频转换器初始化正常")
                logger.info("📁 支持格式: AMR, SILK, MP3, WAV")
            else:
                logger.error("❌ 音频转换器初始化失败")

            logger.info("🎯 功能测试完成")

        except Exception as e:
            logger.error(f"测试功能失败: {e}")
            logger.error(f"功能测试失败: {str(e)}")

    @filter.command("voice_debug")
    async def voice_debug_command(self, event: AstrMessageEvent):
        """调试群聊权限配置"""
        try:
            # 获取当前群聊ID用于测试
            group_id = event.get_group_id()
            message_type = event.get_message_type()
            
            debug_info = f"""🔍 语音插件调试信息:

📱 当前消息类型: {message_type}
👥 当前群聊ID: {group_id}

⚙️ 群聊配置详情:
- 启用群聊语音识别: {self.enable_group_voice_recognition}
- 启用群聊语音回复: {self.enable_group_voice_reply}

📋 白名单配置:
- 识别白名单: {self.group_recognition_whitelist}
- 识别白名单长度: {len(self.group_recognition_whitelist)}
- 识别白名单为空: {not bool(self.group_recognition_whitelist)}
- 回复白名单: {self.group_reply_whitelist} 
- 回复白名单长度: {len(self.group_reply_whitelist)}
- 回复白名单为空: {not bool(self.group_reply_whitelist)}

🚫 黑名单配置:
- 识别黑名单: {self.group_recognition_blacklist}
- 回复黑名单: {self.group_reply_blacklist}

🔧 原始配置对象:
- Group_Chat_Settings: {self.config.get("Group_Chat_Settings", {})}

🎯 权限测试结果:"""

            # 如果是群聊消息，测试权限检查
            if group_id:
                recognition_result = self.check_group_voice_permission(group_id, "recognition")
                reply_result = self.check_group_voice_permission(group_id, "reply")
                debug_info += f"""
- 当前群聊语音识别权限: {recognition_result}
- 当前群聊语音回复权限: {reply_result}"""
            else:
                debug_info += f"""
- 非群聊消息，跳过权限测试"""

            yield event.plain_result(debug_info.strip())

        except Exception as e:
            logger.error(f"调试命令失败: {e}")
            yield event.plain_result(f"调试失败: {str(e)}")

    async def terminate(self):
        """插件卸载时的清理工作"""
        logger.info("语音转文字插件已卸载")
