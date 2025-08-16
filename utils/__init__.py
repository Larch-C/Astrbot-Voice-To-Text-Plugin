"""
工具模块 - 语音转文字插件的通用工具和装饰器
"""

# 导出常用装饰器，便于外部导入
from .decorators import (
    async_operation_handler,
    retry_on_failure,
    validate_input,
    cache_result
)

__all__ = [
    'async_operation_handler',
    'retry_on_failure', 
    'validate_input',
    'cache_result'
]

# 版本信息
__version__ = "1.0.0"
