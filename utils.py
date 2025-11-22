"""
通用工具模块 - 错误处理装饰器和重试机制
遵循函数单一职责原则，每个函数只做一件事
"""

import asyncio
import functools
from typing import Optional, Any, Callable
from logger import logger


def handle_errors(default_return: Any = None, operation_name: str = None):
    """统一错误处理装饰器 - 消除重复的try/catch逻辑"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                op_name = operation_name or func.__name__
                logger.error(f"{op_name} 失败: {e}")
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                op_name = operation_name or func.__name__
                logger.error(f"{op_name} 失败: {e}")
                return default_return

        # 根据函数类型返回对应的装饰器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry(max_times: int = 3, delay: float = 1.0, operation_name: str = None):
    """通用重试装饰器 - 消除重复的重试逻辑"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            op_name = operation_name or func.__name__

            for attempt in range(max_times):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_times - 1:
                        logger.warning(f"{op_name} 第{attempt + 1}次尝试失败，{delay}秒后重试")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"{op_name} 重试{max_times}次后仍然失败")
                        raise
            return None

        return wrapper
    return decorator


class StatisticsTracker:
    """统计信息跟踪器 - 单一职责：只负责计数"""

    def __init__(self):
        self.success_count = 0
        self.failed_count = 0

    def record_success(self):
        """记录成功"""
        self.success_count += 1

    def record_failure(self):
        """记录失败"""
        self.failed_count += 1

    def get_stats(self) -> dict:
        """获取统计信息"""
        total = self.success_count + self.failed_count
        success_rate = self.success_count / total if total > 0 else 0
        return {
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'success_rate': success_rate
        }

    def reset(self):
        """重置统计"""
        self.success_count = 0
        self.failed_count = 0