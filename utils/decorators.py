"""
装饰器工具模块
"""
import functools
import asyncio
import time
from typing import Any, Callable
from astrbot.api import logger
from ..exceptions import VoiceToTextError

def async_operation_handler(operation_name: str, log_performance: bool = True):
    """异步操作处理装饰器 - 统一异常处理和性能监控，支持异步生成器"""
    def decorator(func: Callable) -> Callable:
        # 检查原函数是否是异步生成器函数
        import inspect
        is_async_gen = inspect.isasyncgenfunction(func)
        
        if is_async_gen:
            # 异步生成器函数的包装器
            @functools.wraps(func)
            async def async_gen_wrapper(*args, **kwargs):
                start_time = time.time() if log_performance else None
                try:
                    logger.info(f"开始{operation_name}")
                    
                    async for item in func(*args, **kwargs):
                        yield item
                    
                    if log_performance:
                        duration = time.time() - start_time
                        logger.info(f"{operation_name}成功 - 耗时: {duration:.2f}秒")
                    else:
                        logger.info(f"{operation_name}成功")
                        
                except VoiceToTextError:
                    raise
                except Exception as e:
                    logger.error(f"{operation_name}失败: {e}")
                    raise VoiceToTextError(f"{operation_name}失败: {str(e)}") from e
            
            return async_gen_wrapper
        else:
            # 普通异步函数的包装器
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time() if log_performance else None
                try:
                    logger.info(f"开始{operation_name}")
                    result = await func(*args, **kwargs)
                    
                    if log_performance:
                        duration = time.time() - start_time
                        logger.info(f"{operation_name}成功 - 耗时: {duration:.2f}秒")
                    else:
                        logger.info(f"{operation_name}成功")
                    
                    return result
                    
                except VoiceToTextError:
                    raise
                except Exception as e:
                    logger.error(f"{operation_name}失败: {e}")
                    raise VoiceToTextError(f"{operation_name}失败: {str(e)}") from e
            
            return async_wrapper
    return decorator

def retry_on_failure(max_retries: int = 2, delay: float = 1.0, exponential_backoff: bool = True):
    """重试装饰器 - 支持指数退避"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        current_delay = delay * (2 ** attempt) if exponential_backoff else delay
                        logger.warning(f"操作失败，{current_delay:.1f}秒后重试 (第{attempt + 1}/{max_retries + 1}次): {e}")
                        await asyncio.sleep(current_delay)
                    else:
                        logger.error(f"所有重试都失败了: {e}")
            
            raise last_exception
        return wrapper
    return decorator

def validate_input(validation_func: Callable[[Any], bool], error_message: str = "输入验证失败"):
    """输入验证装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 验证第一个非self参数（通常是输入数据）
            if len(args) > 1 and not validation_func(args)[1]:
                raise VoiceToTextError(error_message)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def cache_result(cache_key_func: Callable = None, ttl_seconds: int = 300):
    """结果缓存装饰器"""
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 检查缓存
            current_time = time.time()
            if cache_key in cache:
                cached_result, cached_time = cache[cache_key]
                if current_time - cached_time < ttl_seconds:
                    logger.debug(f"使用缓存结果: {cache_key}")
                    return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            
            # 清理过期缓存
            expired_keys = [k for k, (_, t) in cache.items() if current_time - t >= ttl_seconds]
            for k in expired_keys:
                del cache[k]
                
            return result
        return wrapper
    return decorator
