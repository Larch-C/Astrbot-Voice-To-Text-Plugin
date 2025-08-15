import os
import asyncio
import json
from astrbot.api.message_components import Record
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.event import filter
import astrbot.api.star as star
from astrbot.api.star import register, Context
from astrbot.api import logger, AstrBotConfig
from astrbot.core.platform.message_type import MessageType
from .covert import AudioConverter  # 导入音频转换工具类
from .voice_file_resolver import VoiceFileResolver  # 导入语音文件解析器
from .stt_providers import STTProviderManager, get_provider_default_config, PROVIDER_DISPLAY_CONFIGS  # 导入STT提供商管理器

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
        
        # 语音识别配置
        voice_recognition = self.config.get("Voice_Recognition", {})
        self.stt_source = voice_recognition.get("STT_Source", "framework")
        self.framework_stt_provider_name = voice_recognition.get("Framework_STT_Provider_Name", "")
        self.enable_voice_processing = voice_recognition.get("Enable_Voice_Processing", True)
        
        # STT API配置（仅在选择plugin时使用）
        if self.stt_source == "plugin":
            stt_api_config = self.config.get("STT_API_Config", {})
            self.api_key = stt_api_config.get("API_Key", "")
            self.api_base_url = stt_api_config.get("API_Base_URL", "")
            self.model = stt_api_config.get("Model", "")
            self.provider_type = stt_api_config.get("Provider_Type", "openai")
            self.custom_headers = stt_api_config.get("Custom_Headers", {})
            
            # 获取"other"类型的自定义配置
            custom_kwargs = {}
            if self.provider_type == "other":
                custom_kwargs = {
                    "custom_request_body": stt_api_config.get("Custom_Request_Body", {}),
                    "custom_endpoint": stt_api_config.get("Custom_Endpoint", "/audio/transcriptions"),
                    "custom_request_method": stt_api_config.get("Custom_Request_Method", "POST"),
                    "custom_content_type": stt_api_config.get("Custom_Content_Type", "multipart/form-data"),
                    "custom_response_path": stt_api_config.get("Custom_Response_Path", "text")
                }
            
            # 初始化STT提供商管理器
            try:
                # 获取提供商默认配置
                default_config = get_provider_default_config(self.provider_type)
                
                # 使用默认配置补充空值
                if not self.api_base_url:
                    self.api_base_url = default_config["api_base_url"]
                if not self.model:
                    self.model = default_config["default_model"]
                
                # 初始化STT提供商管理器（支持other类型的自定义参数）
                self.stt_manager = STTProviderManager(
                    provider_type=self.provider_type,
                    api_key=self.api_key,
                    api_base_url=self.api_base_url,
                    model=self.model,
                    custom_headers=self.custom_headers,
                    **custom_kwargs
                )
                
                logger.info(f"STT提供商管理器初始化成功: {self.provider_type}")
                logger.debug(f"配置详情: {self.stt_manager.get_provider_info()}")
                
            except Exception as e:
                logger.error(f"STT提供商管理器初始化失败: {e}")
                self.stt_manager = None
        
        # 群聊相关配置
        group_settings = self.config.get("Group_Chat_Settings", {})
        self.enable_group_voice_recognition = group_settings.get("Enable_Group_Voice_Recognition", True)
        self.enable_group_voice_reply = group_settings.get("Enable_Group_Voice_Reply", False)
        self.group_recognition_whitelist = group_settings.get("Group_Recognition_Whitelist", [])
        self.group_reply_whitelist = group_settings.get("Group_Reply_Whitelist", [])
        self.group_recognition_blacklist = group_settings.get("Group_Recognition_Blacklist", [])
        self.group_reply_blacklist = group_settings.get("Group_Reply_Blacklist", [])

        # 初始化音频转换器和文件解析器
        self.audio_converter = AudioConverter()
        self.voice_file_resolver = VoiceFileResolver()

        logger.info("语音转文字插件已加载 - 支持群聊语音识别功能")

    def should_process_voice(self, event: AstrMessageEvent) -> bool:
        """检查是否应该处理语音消息"""
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
        """检查群聊语音权限 - 简化版本
        
        Args:
            group_id: 群聊ID
            action: 操作类型 ("recognition" 或 "reply")
        
        Returns:
            bool: 是否允许操作
        """
        logger.debug(f"检查群聊权限 - group_id: {group_id}, action: {action}")
        
        if not group_id:
            logger.debug("群聊ID为空，拒绝处理")
            return False
        
        # 根据操作类型获取相应的配置
        if action == "recognition":
            enabled = self.enable_group_voice_recognition
            blacklist = self.group_recognition_blacklist
            whitelist = self.group_recognition_whitelist
        elif action == "reply":
            enabled = self.enable_group_voice_reply
            blacklist = self.group_reply_blacklist
            whitelist = self.group_reply_whitelist
        else:
            logger.warning(f"未知的操作类型: {action}")
            return False
        
        # 简化的权限检查逻辑
        if not enabled:
            logger.debug(f"群聊语音{action}已禁用: {group_id}")
            return False
            
        if group_id in blacklist:
            logger.debug(f"群聊在{action}黑名单中: {group_id}")
            return False
            
        if whitelist and group_id not in whitelist:
            logger.debug(f"群聊不在{action}白名单中: {group_id}")
            return False
        
        logger.debug(f"群聊语音{action}权限检查通过: {group_id}")
        return True

    def should_generate_reply(self, event: AstrMessageEvent) -> bool:
        """检查是否应该生成智能回复"""
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

            # 获取语音文件路径 - 使用专用解析器
            try:
                original_file_path = await voice.convert_to_file_path()
            except Exception as e:
                logger.error(f"语音文件路径转换失败: {e}")
                logger.debug(f"尝试其他方式获取文件路径...")
                
                # 使用VoiceFileResolver进行文件路径解析
                original_file_path = await self.voice_file_resolver.resolve_voice_file_path(voice)
                
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
            needs_conversion = audio_format not in whisper_supported_formats
            
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
                    logger.error(f"音频格式转换失败: {e}")
                    return
            else:
                final_file_path = original_file_path
                
                # 如果不需要转换，但格式仍然不被支持，提醒用户
                if audio_format not in whisper_supported_formats:
                    logger.error(f"检测到{audio_format.upper()}格式，可能不被STT服务支持")

            # 语音识别
            logger.info("正在识别语音内容...")
            transcribed_text = await self.call_stt_service(final_file_path)

            if not transcribed_text:
                logger.error("语音识别失败，请检查文件格式或重试")
                return

            # 输出识别结果
            logger.info(f"语音识别结果: {transcribed_text}")

            # 生成智能回复 - 检查群聊回复权限
            if self.enable_chat_reply and self.should_generate_reply(event):
                async for reply in self.call_official_chatllm(event, transcribed_text):
                    yield reply

        except Exception as e:
            logger.error(f"处理语音消息失败: {e}")
        finally:
            # 清理临时文件
            if converted_file_path and converted_file_path != original_file_path:
                self.audio_converter.cleanup_temp_files(converted_file_path)



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


    async def call_stt_service(self, audio_file_path: str) -> str:
        """根据配置选择调用框架STT或插件独立STT"""
        if self.stt_source == "framework":
            return await self.call_framework_stt(audio_file_path)
        elif self.stt_source == "plugin":
            return await self.call_plugin_stt(audio_file_path)
        else:
            logger.error(f"未知的STT服务来源: {self.stt_source}")
            return ""

    async def call_framework_stt(self, audio_file_path: str) -> str:
        """调用AstrBot框架STT接口"""
        try:
            # 如果指定了特定的框架STT提供商名字，尝试查找并使用
            if self.framework_stt_provider_name:
                # 获取所有可用的STT提供商
                all_stt_providers = self.context.get_all_stt_providers()
                
                # 查找指定名字的提供商
                target_provider = None
                for provider in all_stt_providers:
                    provider_meta = provider.meta()
                    if provider_meta.id == self.framework_stt_provider_name:
                        target_provider = provider
                        break
                
                if target_provider:
                    logger.info(f"使用指定的框架STT提供商: {self.framework_stt_provider_name} ({type(target_provider).__name__})")
                    
                    # 调用指定的STT提供商
                    result = await target_provider.get_text(audio_file_path)
                    
                    if result:
                        logger.info(f"指定框架STT提供商识别成功: {self.framework_stt_provider_name}")
                        return result
                    else:
                        logger.warning(f"指定框架STT提供商返回空结果: {self.framework_stt_provider_name}")
                        return ""
                else:
                    logger.warning(f"未找到指定的框架STT提供商: {self.framework_stt_provider_name}，使用默认提供商")
            
            # 获取默认的框架STT提供商
            stt_provider = self.context.get_using_stt_provider()

            if not stt_provider:
                logger.error("未配置AstrBot框架STT提供商")
                return ""

            logger.info(f"使用AstrBot框架默认STT提供商: {type(stt_provider).__name__}")

            # 直接调用官方STT接口
            result = await stt_provider.get_text(audio_file_path)

            if result:
                logger.info("AstrBot框架STT识别成功")
                return result
            else:
                logger.warning("AstrBot框架STT返回空结果")
                return ""

        except Exception as e:
            logger.error(f"调用AstrBot框架STT接口失败: {e}")
            return ""

    async def call_plugin_stt(self, audio_file_path: str) -> str:
        """调用插件独立STT API - 使用新的提供商管理系统"""
        try:
            if not hasattr(self, 'stt_manager') or self.stt_manager is None:
                logger.error("STT提供商管理器未初始化")
                return ""

            logger.info(f"使用STT提供商管理器进行语音转录: {self.provider_type}")
            
            # 使用STT提供商管理器进行转录
            result = await self.stt_manager.transcribe_audio(audio_file_path)
            
            if result:
                logger.info(f"STT提供商管理器转录成功: {self.provider_type}")
                return result
            else:
                logger.warning(f"STT提供商管理器返回空结果: {self.provider_type}")
                return ""

        except Exception as e:
            logger.error(f"STT提供商管理器转录失败: {e}")
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
            prompt = f"用户通过语音说了: {text}\n"

            # 直接调用官方LLM接口生成回复 - 完全使用框架人格和对话上下文
            yield event.request_llm(
                prompt=prompt,
                session_id=curr_cid,
                conversation=conversation  # 只传递conversation，让框架处理上下文和人格
            )

        except Exception as e:
            logger.error(f"调用官方ChatLLM接口失败: {e}")

    @filter.command("voice_status")
    async def voice_status_command(self, event: AstrMessageEvent):
        """查看语音转文字插件状态"""
        try:
            # STT服务来源和状态
            stt_source_text = "🔧 AstrBot框架STT" if self.stt_source == "framework" else "🔌 插件独立STT"
            
            if self.stt_source == "framework":
                # 检查框架STT提供商状态
                stt_provider = self.context.get_using_stt_provider()
                stt_status = "✅ 已配置" if stt_provider else "❌ 未配置"
                stt_name = type(stt_provider).__name__ if stt_provider else "无"
                
                # 显示具体配置信息
                if self.framework_stt_provider_name:
                    stt_detail = f"指定提供商: {self.framework_stt_provider_name}\n提供商类: {stt_name}"
                else:
                    provider_id = stt_provider.meta().id if stt_provider else "无"
                    stt_detail = f"默认提供商: {provider_id}\n提供商类: {stt_name}"
            else:
                # 检查插件STT配置状态
                stt_status = "✅ 已配置" if hasattr(self, 'api_key') and self.api_key else "❌ 未配置"
                stt_detail = f"提供商: {getattr(self, 'provider_type', 'unknown')}"
                if hasattr(self, 'api_base_url'):
                    stt_detail += f"\nAPI地址: {self.api_base_url}"
                if hasattr(self, 'model'):
                    stt_detail += f"\n模型: {self.model}"

            # 检查LLM提供商状态
            llm_provider = self.context.get_using_provider()
            llm_status = "✅ 已配置" if llm_provider else "❌ 未配置"
            llm_name = type(llm_provider).__name__ if llm_provider else "无"

            # 群聊配置信息
            group_recognition_status = "✅ 启用" if self.enable_group_voice_recognition else "❌ 禁用"
            group_reply_status = "✅ 启用" if self.enable_group_voice_reply else "❌ 禁用"
            
            status_info = f"""🎙️ 语音转文字插件状态:

                📡 STT服务来源: {stt_source_text}
                状态: {stt_status}
                {stt_detail}

                🤖 ChatLLM接口: {llm_status}
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
                💡 使用方法: 直接发送语音消息即可
                💡 配置说明: 在插件配置中选择STT服务来源"""
            
            yield event.plain_result(status_info.strip())

        except Exception as e:
            logger.error(f"获取状态信息失败: {e}")

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
            logger.error(f"功能测试失败: {e}")

    @filter.command("voice_providers")
    async def voice_providers_command(self, event: AstrMessageEvent):
        """查看所有支持的STT提供商"""
        try:
            provider_info = "🎙️ 支持的STT提供商列表:\n\n"
            
            for provider_key, provider_data in PROVIDER_DISPLAY_CONFIGS.items():
                # 获取提供商的技术配置
                tech_config = get_provider_default_config(provider_key)
                
                provider_info += f"🔹 **{provider_data['name']}** (`{provider_key}`)\n"
                provider_info += f"   📝 {provider_data['description']}\n"
                provider_info += f"   💰 定价: {provider_data['pricing']}\n"
                provider_info += f"   🌟 特性: {', '.join(provider_data['features'])}\n"
                provider_info += f"   🔗 默认API: {tech_config['api_base_url']}\n"
                provider_info += f"   🤖 默认模型: {tech_config['default_model']}\n"
                provider_info += f"   📋 支持模型: {', '.join(tech_config['supported_models'])}\n\n"
            
            provider_info += """💡 使用说明:
                1. 在插件配置中选择 STT_Source 为 'plugin'
                2. 选择具体的 Provider_Type (提供商类型)
                3. 配置相应的 API_Key 和其他参数
                4. 发送语音消息即可使用指定提供商进行识别

                🎯 推荐选择:
                - **OpenAI**: 官方服务，准确度最高
                - **Groq**: 免费额度，响应速度最快  
                - **SiliconFlow**: 国内服务，中文优化
                - **Deepgram**: 专业服务，实时转录"""

            yield event.plain_result(provider_info.strip())

        except Exception as e:
            logger.error(f"获取提供商信息失败: {e}")
            yield event.plain_result(f"获取提供商信息失败: {str(e)}")

    @filter.command("voice_framework_providers")
    async def voice_framework_providers_command(self, event: AstrMessageEvent):
        """查看所有可用的框架STT提供商"""
        try:
            # 获取所有框架STT提供商
            all_stt_providers = self.context.get_all_stt_providers()
            
            if not all_stt_providers:
                provider_info = "❌ 当前没有可用的框架STT提供商\n\n请在AstrBot配置中添加STT提供商配置"
            else:
                provider_info = "🔧 可用的AstrBot框架STT提供商列表:\n\n"
                
                # 获取当前使用的默认提供商
                current_stt_provider = self.context.get_using_stt_provider()
                current_provider_id = ""
                if current_stt_provider:
                    current_provider_id = current_stt_provider.meta().id
                
                for idx, provider in enumerate(all_stt_providers, 1):
                    provider_meta = provider.meta()
                    provider_id = provider_meta.id
                    provider_type = provider_meta.type
                    provider_model = provider_meta.model
                    
                    # 标记当前默认提供商
                    is_current = provider_id == current_provider_id
                    status_icon = "⭐" if is_current else "🔹"
                    status_text = " (当前默认)" if is_current else ""
                    
                    provider_info += f"{status_icon} **{provider_id}**{status_text}\n"
                    provider_info += f"   📝 类型: {provider_type}\n"
                    provider_info += f"   🤖 模型: {provider_model}\n"
                    provider_info += f"   🔧 提供商类: {type(provider).__name__}\n\n"
                
                provider_info += """💡 使用说明:
                    1. 在插件配置中选择 STT_Source 为 'framework'
                    2. 在 Framework_STT_Provider_Name 中填入上述提供商ID
                    3. 留空则使用当前默认的STT提供商
                    4. 发送语音消息即可使用指定的框架STT提供商

                    🔧 配置示例:
                    - Framework_STT_Provider_Name: "openai_whisper_1" (使用指定提供商)
                    - Framework_STT_Provider_Name: "" (使用默认提供商)"""

            yield event.plain_result(provider_info.strip())

        except Exception as e:
            logger.error(f"获取框架STT提供商信息失败: {e}")
            yield event.plain_result(f"获取框架STT提供商信息失败: {str(e)}")

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
