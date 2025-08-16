"""
临时文件管理器 - 统一管理临时文件的创建和清理
"""
import os
import time
import uuid
import tempfile
from contextlib import contextmanager
from typing import List, Optional
from pathlib import Path
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from ..config import TempFileConfig
from ..exceptions import FileValidationError

class TempFileManager:
    """临时文件管理器"""
    
    def __init__(self, config: TempFileConfig = None):
        self.config = config or TempFileConfig()
        self._temp_files: List[str] = []
        self._temp_dir: Optional[str] = None
        self._last_cleanup = time.time()
        self._initialize_temp_directory()
    
    def _initialize_temp_directory(self):
        """初始化临时目录"""
        try:
            # 优先使用AstrBot数据目录
            base_dir = get_astrbot_data_path()
            self._temp_dir = os.path.join(base_dir, self.config.TEMP_DIR_NAME)
        except Exception:
            # 备用系统临时目录
            self._temp_dir = os.path.join(tempfile.gettempdir(), self.config.TEMP_DIR_NAME)
        
        # 确保目录存在
        os.makedirs(self._temp_dir, exist_ok=True)
        
        # 测试目录写入权限
        try:
            test_file = os.path.join(self._temp_dir, f"test_{os.getpid()}.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            logger.warning(f"临时目录权限测试失败: {e}")
            # 使用系统默认临时目录
            self._temp_dir = tempfile.mkdtemp(prefix="astrbot_voice_")
        
        logger.info(f"临时文件管理器初始化完成 - 目录: {self._temp_dir}")
    
    @contextmanager
    def temp_file(self, extension: str = '.tmp', prefix: str = 'voice_'):
        """创建临时文件的上下文管理器"""
        temp_path = None
        try:
            # 生成唯一文件名
            filename = f"{prefix}{uuid.uuid4().hex}{extension}"
            temp_path = os.path.join(self._temp_dir, filename)
            
            # 记录临时文件
            self._temp_files.append(temp_path)
            logger.debug(f"创建临时文件: {temp_path}")
            
            yield temp_path
            
        finally:
            # 清理临时文件
            if temp_path:
                self.cleanup_file(temp_path)
                if temp_path in self._temp_files:
                    self._temp_files.remove(temp_path)
    
    def create_temp_file(self, extension: str = '.tmp', prefix: str = 'voice_') -> str:
        """创建临时文件（非上下文管理器版本）"""
        filename = f"{prefix}{uuid.uuid4().hex}{extension}"
        temp_path = os.path.join(self._temp_dir, filename)
        
        # 创建空文件
        with open(temp_path, 'w') as f:
            pass
        
        self._temp_files.append(temp_path)
        logger.debug(f"创建临时文件: {temp_path}")
        
        # 检查是否需要清理
        self._check_and_cleanup()
        
        return temp_path
    
    def cleanup_file(self, file_path: str):
        """清理单个临时文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"清理临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败 {file_path}: {e}")
    
    def cleanup_all(self):
        """清理所有管理的临时文件"""
        for file_path in self._temp_files[:]:  # 复制列表以避免修改时的迭代问题
            self.cleanup_file(file_path)
            self._temp_files.remove(file_path)
        logger.info("清理所有临时文件完成")
    
    def _check_and_cleanup(self):
        """检查并执行定期清理"""
        current_time = time.time()
        
        # 检查文件数量限制
        if len(self._temp_files) > self.config.MAX_TEMP_FILES:
            logger.warning(f"临时文件数量超过限制 ({len(self._temp_files)} > {self.config.MAX_TEMP_FILES})")
            self._cleanup_old_files()
        
        # 检查定期清理时间
        if current_time - self._last_cleanup > self.config.CLEANUP_INTERVAL_MINUTES * 60:
            self._cleanup_old_files()
            self._last_cleanup = current_time
    
    def _cleanup_old_files(self):
        """清理老旧的临时文件"""
        cleaned_count = 0
        for file_path in self._temp_files[:]:
            try:
                if os.path.exists(file_path):
                    # 检查文件创建时间
                    file_age = time.time() - os.path.getctime(file_path)
                    if file_age > self.config.CLEANUP_INTERVAL_MINUTES * 60:
                        self.cleanup_file(file_path)
                        self._temp_files.remove(file_path)
                        cleaned_count += 1
                else:
                    # 文件已不存在，从列表中移除
                    self._temp_files.remove(file_path)
            except Exception as e:
                logger.warning(f"清理老旧文件失败 {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个老旧临时文件")
    
    def get_temp_dir(self) -> str:
        """获取临时目录路径"""
        return self._temp_dir
    
    def get_managed_files_count(self) -> int:
        """获取当前管理的临时文件数量"""
        return len(self._temp_files)
    
    def __del__(self):
        """析构时清理所有临时文件"""
        if self.config.AUTO_CLEANUP:
            self.cleanup_all()
