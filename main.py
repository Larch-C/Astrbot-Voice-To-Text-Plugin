"""
重构后的语音转文字插件主文件 - 使用服务层架构
"""
import os
import time
from astrbot.api.message_components import Record
from astrbot.api.event import AstrMessageEvent
from astrbot.api.event import filter
import astrbot.api.star as star
from astrbot.api.star import register, Context
from astrbot.api import logger, AstrBotConfig

from .config import PluginConfig
from .exceptions import VoiceToTextError, STTProviderError
from .utils.decorators import async_operation_handler
from .services.voice_processing_service import VoiceProcessingService
from .services.permission_service import PermissionService
from .services.stt_service import STTService

@register("voice_to_text", "NickMo", "语音转文字智能回复插件", "1.2.0", "")
class VoiceToTextPlugin(star.Star):
    """重构后的语音转文字插件 - 使用服务层架构"""

    def __init__(self, context: Context, config: AstrBotConfig = None) -> None:
        super().__init__(context)
        self.context = context
        self.config = config or {}
        
        # 初始化插件配置
        self.plugin_config = PluginConfig.create_default()
        
        # 基础配置
        chat_reply_settings = self.config.get("Chat_Reply", {})
        self.enable_chat_reply = chat_reply_settings.get("Enable_Chat_Reply", True)
        self.console_output = self.config.get("Output_Settings", {}).get("Console_Output", True) # 修正console_output的获取路径
        
        # 权限服务
        logger.info(f"回复配置: {self.enable_chat_reply}")
        logger.info(f"输出配置: {self.console_output}")

        # 初始化服务层
        self._initialize_services()
        
        logger.info("重构版语音转文字插件初始化完成")
    
    def _initialize_services(self):
        """初始化所有服务层组件"""
        try:
            # 初始化权限服务
            self.permission_service = PermissionService(self.config)
            
            # 初始化语音处理服务
            self.voice_processing_service = VoiceProcessingService(self.plugin_config)
            
            # 初始化STT服务
            self.stt_service = STTService(self.config, self.context)
            
            logger.info("所有服务层组件初始化完成")
            
        except Exception as e:
            logger.error(f"服务层初始化失败: {e}")
            raise VoiceToTextError(f"插件初始化失败: {str(e)}") from e
    
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent, context=None):
        """监听所有消息，处理语音消息 - 重构版本"""
        # 使用框架提供的 API 方法获取消息链，而不是直接访问内部属性
        messages = event.get_messages()
        for comp in messages:
            if isinstance(comp, Record):
                # 检查权限
                if await self.permission_service.can_process_voice(event):
                    async for result in self._process_voice_message(event, comp):
                        yield result
                else:
                    logger.debug(f"权限检查未通过，跳过语音处理: {event.get_group_id()}")
    
    @async_operation_handler("语音消息处理")
    async def _process_voice_message(self, event: AstrMessageEvent, voice: Record):
        """处理语音消息的完整流程 - 重构版本"""
        try:
            logger.info(f"收到来自 {event.get_sender_name()} 的语音消息")
            
            # 1. 语音文件处理
            processed_file_path = await self._process_voice_file(voice)
            if not processed_file_path:
                return
            
            # 2. 语音识别
            transcribed_text = await self._transcribe_voice(processed_file_path)
            if not transcribed_text:
                return
            
            # 3. 输出识别结果
            if self.console_output:
                logger.info(f"语音识别结果: {transcribed_text}")
            
            # 4. 生成智能回复
            if self.enable_chat_reply and await self.permission_service.can_generate_reply(event):
                async for reply in self._generate_intelligent_reply(event, transcribed_text):
                    yield reply
                    
        except VoiceToTextError as e:
            logger.error(f"语音处理业务逻辑错误: {e}")
        except Exception as e:
            logger.error(f"语音处理未知错误: {e}")
        finally:
            # 清理资源
            await self._cleanup_resources()
    
    async def _process_voice_file(self, voice: Record) -> str:
        """处理语音文件"""
        try:
            return await self.voice_processing_service.process_voice_file(voice)
        except Exception as e:
            logger.error(f"语音文件处理失败: {e}")
            return None
    
    async def _transcribe_voice(self, audio_file_path: str) -> str:
        """语音转文字"""
        try:
            return await self.stt_service.transcribe_audio(audio_file_path)
        except STTProviderError as e:
            logger.error(f"STT服务错误: {e}")
            return None
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return None
    
    async def _generate_intelligent_reply(self, event: AstrMessageEvent, text: str):
        """生成智能回复"""
        try:
            # 获取LLM提供商
            llm_provider = self.context.get_using_provider()
            if not llm_provider:
                logger.error("未配置LLM提供商，无法生成智能回复")
                return
            
            logger.info(f"使用LLM提供商: {type(llm_provider).__name__}")
            logger.info("正在生成智能回复...")
            
            # 获取对话上下文
            curr_cid = await self.context.conversation_manager.get_curr_conversation_id(
                event.unified_msg_origin
            )
            conversation = None
            
            if curr_cid:
                conversation = await self.context.conversation_manager.get_conversation(
                    event.unified_msg_origin, curr_cid
                )
            
            # 构造提示词
            prompt = f"用户通过语音说了: {text}"
            
            # 调用框架LLM接口
            yield event.request_llm(
                prompt=prompt,
                session_id=curr_cid,
                conversation=conversation
            )
            
        except Exception as e:
            logger.error(f"生成智能回复失败: {e}")
    
    async def _cleanup_resources(self):
        """清理资源"""
        try:
            self.voice_processing_service.cleanup_resources()
        except Exception as e:
            logger.warning(f"资源清理失败: {e}")
    
    @filter.command("voice_status")
    async def voice_status_command(self, event: AstrMessageEvent):
        """查看插件状态 - 重构版本"""
        try:
            # 获取各服务状态
            stt_status = self.stt_service.get_stt_status()
            permission_status = await self.permission_service.get_permission_status(event.get_group_id())
            processing_status = self.voice_processing_service.get_processing_status()
            
            # 构建状态信息
            status_info = f"""🎙️ 语音转文字插件状态:

                📡 STT服务状态:
                - 服务来源: {stt_status.get('stt_source', '未知')}
                - 语音处理: {'✅ 启用' if stt_status.get('voice_processing_enabled') else '❌ 禁用'}
                - 服务可用: {'✅ 是' if self.stt_service.is_available() else '❌ 否'}

                🤖 LLM接口状态:
                - 提供商: {'✅ 已配置' if self.context.get_using_provider() else '❌ 未配置'}

                👥 权限状态:
                - 群聊语音识别: {'✅ 启用' if permission_status.get('group_voice_recognition_enabled') else '❌ 禁用'}
                - 群聊语音回复: {'✅ 启用' if permission_status.get('group_voice_reply_enabled') else '❌ 禁用'}

                ⚙️ 处理配置:
                - 智能回复: {'✅ 启用' if self.enable_chat_reply else '❌ 禁用'}
                - 控制台输出: {'✅ 启用' if self.console_output else '❌ 禁用'}
                - 最大文件大小: {processing_status['config']['max_file_size_mb']}MB

                🔧 架构信息:
                - 使用重构后的服务层架构
                - 模块化组件设计
                - 统一异常处理
                - 性能优化装饰器

                💡 使用方法: 直接发送语音消息即可"""

            yield event.plain_result(status_info.strip())
            
        except Exception as e:
            logger.error(f"获取状态信息失败: {e}")
            yield event.plain_result(f"状态查询失败: {str(e)}")
    
    @filter.command("voice_test")
    async def voice_test_command(self, event: AstrMessageEvent):
        """测试插件功能 - 重构版本"""
        try:
            logger.info("🔍 正在测试重构版插件功能...")
            
            test_results = []
            
            # 测试STT服务
            if self.stt_service.is_available():
                test_results.append("✅ STT服务可用")
            else:
                test_results.append("❌ STT服务不可用")
            
            # 测试LLM服务
            llm_provider = self.context.get_using_provider()
            if llm_provider:
                test_results.append(f"✅ LLM服务可用: {type(llm_provider).__name__}")
            else:
                test_results.append("❌ LLM服务不可用")
            
            # 测试语音处理服务
            processing_status = self.voice_processing_service.get_processing_status()
            if processing_status:
                test_results.append("✅ 语音处理服务正常")
            else:
                test_results.append("❌ 语音处理服务异常")
            
            # 测试权限服务
            group_id = event.get_group_id()
            if group_id:
                can_process = await self.permission_service.can_process_voice(event)
                can_reply = await self.permission_service.can_generate_reply(event)
                test_results.append(f"✅ 权限检查: 识别={can_process}, 回复={can_reply}")
            else:
                test_results.append("✅ 权限检查: 私聊消息")
            
            result_text = "🧪 重构版插件功能测试结果:\n\n" + "\n".join(test_results)
            result_text += "\n\n🏗️ 架构优势:\n- 模块化设计\n- 服务层解耦\n- 统一错误处理\n- 性能优化"
            
            yield event.plain_result(result_text)
            
        except Exception as e:
            logger.error(f"功能测试失败: {e}")
            yield event.plain_result(f"测试失败: {str(e)}")
    
    @filter.command("voice_debug")
    async def voice_debug_command(self, event: AstrMessageEvent):
        """调试信息 - 重构版本"""
        try:
            group_id = event.get_group_id()
            
            debug_info = f"""🔍 插件调试信息:

                📱 消息信息:
                - 消息类型: {event.get_message_type()}
                - 群聊ID: {group_id or '私聊'}
                - 发送者: {event.get_sender_name()}

                🏗️ 架构状态:
                - 服务层初始化: ✅ 完成
                - 权限服务: {'✅ 正常' if hasattr(self, 'permission_service') else '❌ 异常'}
                - 语音处理服务: {'✅ 正常' if hasattr(self, 'voice_processing_service') else '❌ 异常'}
                - STT服务: {'✅ 正常' if hasattr(self, 'stt_service') else '❌ 异常'}

                📊 服务详情:
                - STT源: {self.stt_service.stt_source if hasattr(self, 'stt_service') else '未知'}
                - 权限状态: {await self.permission_service.get_permission_status(group_id) if hasattr(self, 'permission_service') else '未知'}

                🔧 重构改进:
                - ✅ 单一职责原则
                - ✅ 依赖注入
                - ✅ 服务层架构
                - ✅ 统一异常处理
                - ✅ 性能优化装饰器
                - ✅ 配置统一管理"""

            yield event.plain_result(debug_info.strip())
            
        except Exception as e:
            logger.error(f"调试命令失败: {e}")
            yield event.plain_result(f"调试失败: {str(e)}")
    
    
    async def terminate(self):
        """插件卸载时的清理工作 - 重构版本"""
        try:
            await self._cleanup_resources()
            logger.info("重构版语音转文字插件已卸载")
        except Exception as e:
            logger.error(f"插件卸载清理失败: {e}")
