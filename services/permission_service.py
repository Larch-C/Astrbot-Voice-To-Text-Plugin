"""
权限检查服务 - 统一处理群聊权限逻辑
"""
from calendar import c
from typing import Dict, List
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform.message_type import MessageType

from ..config import PluginConfig
from ..exceptions import PermissionError
from ..utils.decorators import cache_result

class PermissionService:
    """权限检查服务 - 专门处理群聊权限验证"""
    
    def __init__(self, config: Dict = None):
        """
        初始化权限服务
        
        Args:
            config: 原始配置字典，包含群聊设置
        """
        self.config = config or {}
        
        # 群聊权限配置
        group_settings = self.config.get("Group_Chat_Settings", {})
        self.enable_group_voice_recognition = group_settings.get("Enable_Group_Voice_Recognition", True)
        self.enable_group_voice_reply = group_settings.get("Enable_Group_Voice_Reply", True) # 修改默认值为True
        self.group_recognition_whitelist = set(group_settings.get("Group_Recognition_Whitelist", []))
        self.group_reply_whitelist = set(group_settings.get("Group_Reply_Whitelist", []))
        self.group_recognition_blacklist = set(group_settings.get("Group_Recognition_Blacklist", []))
        self.group_reply_blacklist = set(group_settings.get("Group_Reply_Blacklist", []))
        
        logger.info(f"权限检查服务初始化完成，Group_Chat_Permission: {self.group_reply_whitelist}") # 添加日志输出
    
    async def can_process_voice(self, event: AstrMessageEvent) -> bool:
        """检查是否可以处理语音消息"""
        try:
            message_type = event.get_message_type()
            
            # 私聊消息总是允许处理
            if message_type == MessageType.FRIEND_MESSAGE:
                logger.debug("私聊消息，允许语音识别")
                return True
            
            # 群聊消息需要检查权限
            if message_type == MessageType.GROUP_MESSAGE:
                group_id = event.get_group_id()
                return await self._check_group_permission(group_id, "recognition")
            
            # 其他消息类型不处理
            logger.debug(f"未知消息类型，不处理: {message_type}")
            return False
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False
    
    async def can_generate_reply(self, event: AstrMessageEvent) -> bool:
        """检查是否可以生成智能回复"""
        try:
            message_type = event.get_message_type()
            
            # 私聊消息总是允许回复
            if message_type == MessageType.FRIEND_MESSAGE:
                logger.debug("私聊消息，允许智能回复")
                return True
            
            # 群聊消息需要检查回复权限
            if message_type == MessageType.GROUP_MESSAGE:
                group_id = event.get_group_id()
                can_reply = await self._check_group_permission(group_id, "reply")
                return can_reply
            
            # 其他消息类型不回复
            logger.debug(f"未知消息类型，不生成回复: {message_type}")
            return False
            
        except Exception as e:
            logger.error(f"回复权限检查失败: {e}")
            return False
            
    @cache_result(ttl_seconds=60)  # 缓存1分钟
    async def _check_group_permission(self, group_id: str, action: str) -> bool:
        """
        检查群聊权限 - 优化版本
        
        Args:
            group_id: 群聊ID
            action: 操作类型 ("recognition" 或 "reply")
        
        Returns:
            bool: 是否允许操作
        """
        if not group_id:
            logger.debug("群聊ID为空，拒绝处理")
            return False
        
        # 根据操作类型获取配置
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
        
        # 权限检查逻辑
        if not enabled:
            logger.debug(f"群聊ID: {group_id} - 语音{action}功能已禁用")
            return False
        
        # 黑名单检查（优先级最高）
        if group_id in blacklist:
            logger.debug(f"群聊ID: {group_id} - 在{action}黑名单中")
            return False

        # 白名单检查
        if whitelist: # 如果白名单不为空，则只允许白名单中的群聊
            if group_id not in whitelist:
                logger.info(f"群聊ID: {group_id} - 不在{action}白名单中")
                return False
            else:
                logger.info(f"群聊ID: {group_id} - 在{action}白名单中")
                logger.debug(f"群聊ID: {group_id} - 语音{action}权限检查通过")
                return True
        else: # 如果白名单为空，则对所有群聊生效（在黑名单中除外）
            logger.info(f"群聊ID: {group_id} - {action}白名单为空，对所有群聊生效")
            logger.debug(f"群聊ID: {group_id} - 语音{action}权限检查通过")
            return True
        return False
    
    async def get_permission_status(self, group_id: str = None) -> Dict:
        """获取权限状态信息"""
        status = {
            'group_voice_recognition_enabled': self.enable_group_voice_recognition,
            'group_voice_reply_enabled': self.enable_group_voice_reply,
            'recognition_whitelist_count': len(self.group_recognition_whitelist),
            'reply_whitelist_count': len(self.group_reply_whitelist),
            'recognition_blacklist_count': len(self.group_recognition_blacklist),
            'reply_blacklist_count': len(self.group_reply_blacklist)
        }
        
        # 如果提供了群ID，返回该群的权限状态
        if group_id:
            status.update({
                'current_group_id': group_id,
                'can_recognize': await self._check_group_permission(group_id, "recognition"),
                'can_reply': await self._check_group_permission(group_id, "reply")
            })
        
        return status
    
    def update_group_permission(self, group_id: str, action: str, permission_type: str, allowed: bool):
        """动态更新群聊权限"""
        try:
            if action == "recognition":
                blacklist = self.group_recognition_blacklist
                whitelist = self.group_recognition_whitelist
            elif action == "reply":
                blacklist = self.group_reply_blacklist  
                whitelist = self.group_reply_whitelist
            else:
                raise ValueError(f"未知操作类型: {action}")
            
            if permission_type == "blacklist":
                if allowed:
                    blacklist.discard(group_id)  # 从黑名单移除
                else:
                    blacklist.add(group_id)  # 添加到黑名单
                    whitelist.discard(group_id)  # 从白名单移除（如果存在）
            elif permission_type == "whitelist":
                if allowed:
                    whitelist.add(group_id)  # 添加到白名单
                    blacklist.discard(group_id)  # 从黑名单移除（如果存在）
                else:
                    whitelist.discard(group_id)  # 从白名单移除
            else:
                raise ValueError(f"未知权限类型: {permission_type}")
            
            logger.info(f"更新群聊权限成功: {group_id} - {action} - {permission_type} - {allowed}")
            
        except Exception as e:
            logger.error(f"更新群聊权限失败: {e}")
            raise PermissionError(f"权限更新失败: {str(e)}")
