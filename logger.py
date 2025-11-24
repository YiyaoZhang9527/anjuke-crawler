"""
日志模块
提供彩色控制台输出和文件日志记录功能
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            original_levelname = record.levelname
            record.levelname = f"{self.COLORS[original_levelname]}{original_levelname}{self.COLORS['RESET']}"
            formatted = super().format(record)
            record.levelname = original_levelname  # 恢复原始levelname
            return formatted
        return super().format(record)


class Logger:
    """日志管理器 - 简单、高效、彩色输出"""

    def __init__(self, name: str = 'AnjukeCrawler'):
        self.name = name
        self.logger = self._setup_logger()
        # 验证码日志组件
        self.verification_log_file = None
        self.verification_enabled = True
        self._init_verification_log()

    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        # 直接读取.env文件
        log_level = 'INFO'
        log_filename = 'anjuke_crawler.log'
        show_progress = True

        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.split('#')[0].strip()  # 移除行内注释

                        if key == 'LOG_LEVEL':
                            log_level = value
                        elif key == 'LOG_FILENAME':
                            log_filename = value
                        elif key == 'SHOW_PROGRESS':
                            show_progress = value.lower() == 'true'
                        elif key == 'ENABLE_VERIFICATION_LOG':
                            self.verification_enabled = value.lower() == 'true'
                        elif key == 'VERIFICATION_LOG_FILE':
                            self.verification_log_file = value

        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # 清除现有处理器
        logger.handlers.clear()

        # 控制台处理器（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 控制台格式
        console_format = ColoredFormatter(
            '%(asctime)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # 文件处理器（详细日志）
        if log_filename:
            file_handler = logging.FileHandler(
                log_filename,
                mode='a',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

            # 文件格式（无颜色）
            file_format = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

        return logger

    def debug(self, message: str, **kwargs):
        """调试信息"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """信息输出"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """警告信息"""
        self.logger.warning(f"⚠️ {message}", **kwargs)

    def error(self, message: str, **kwargs):
        """错误信息"""
        self.logger.error(f"❌ {message}", **kwargs)

    def critical(self, message: str, **kwargs):
        """严重错误"""
        self.logger.critical(f"🔥 {message}", **kwargs)

    def success(self, message: str, **kwargs):
        """成功信息"""
        self.logger.info(f"✅ {message}", **kwargs)

    def progress(self, message: str, **kwargs):
        """进度信息"""
        # 重新读取show_progress设置
        show_progress = True
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.split('#')[0].strip()
                        if key == 'SHOW_PROGRESS':
                            show_progress = value.lower() == 'true'
                            break

        if show_progress:
            self.logger.info(f"📊 {message}", **kwargs)

    def crawler_start(self):
        """爬虫启动"""
        self.info("🚀 启动安居客爬虫...")

    def crawler_stop(self, stats: dict):
        """爬虫停止"""
        # 读取CSV文件名
        csv_filename = 'anjuke_houses.csv'
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.split('#')[0].strip()
                        if key == 'CSV_FILENAME':
                            csv_filename = value
                            break

        self.info(f"📈 爬取完成! 成功: {stats['success_count']}, 失败: {stats['failed_count']}")
        self.info(f"📁 数据已保存到: {csv_filename}")

    def url_start(self, url: str, attempt: int = 1, max_attempts: int = 3):
        """开始处理URL"""
        self.progress(f"处理URL: {url} (尝试 {attempt}/{max_attempts})")

    def url_success(self, title: str = None):
        """URL处理成功"""
        msg = "数据提取成功"
        if title:
            msg += f": {title}"
        self.success(msg)

    def url_failed(self, reason: str = "处理失败"):
        """URL处理失败"""
        self.error(reason)

    def data_extracted(self, data_count: int):
        """数据提取统计"""
        self.info(f"🔍 提取到 {data_count} 个字段")

    def browser_start(self):
        """浏览器启动"""
        self.info("🌐 启动浏览器...")

    def browser_ready(self):
        """浏览器就绪"""
        self.success("浏览器启动成功")

    def browser_close(self):
        """浏览器关闭"""
        self.info("🔚 浏览器已关闭")

    def verification_detected(self):
        """检测到验证码"""
        self.info("🔍 检测到验证码，正在处理...")

    def verification_success(self):
        """验证码处理成功"""
        self.success("验证成功")

    def verification_failed(self):
        """验证码处理失败"""
        self.error("验证码处理失败")

    def csv_created(self, filename: str):
        """CSV文件创建"""
        self.info(f"📝 创建新CSV文件: {filename}")

    def csv_appended(self, filename: str):
        """CSV文件追加"""
        self.info(f"📝 追加到现有CSV文件: {filename}")

    def config_loaded(self):
        """配置加载完成"""
        self.debug(f"配置加载完成 - 日志级别: {config.log_level}")

    def exception(self, message: str, exception: Exception = None):
        """异常信息"""
        if exception:
            self.error(f"{message}: {str(exception)}")
        else:
            self.error(message)

    def _init_verification_log(self):
        """初始化验证码日志"""
        if not self.verification_log_file:
            self.verification_log_file = 'verification_log.csv'

        # 确保日志文件存在
        if not os.path.exists(self.verification_log_file):
            with open(self.verification_log_file, 'w', encoding='utf-8') as f:
                f.write("timestamp,url,result,attempts,duration_seconds\n")

    def log_verification(self, url: str, result: str, attempts: int = 1, duration: float = 0.0):
        """记录验证码处理结果"""
        if not self.verification_enabled:
            return

        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp},{url},{result},{attempts},{duration:.2f}\n"

            with open(self.verification_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception:
            # 静默失败，不影响主程序
            pass

    def log_verification_success(self, url: str, attempts: int = 1, duration: float = 0.0):
        """记录验证成功"""
        self.log_verification(url, "SUCCESS", attempts, duration)

    def log_verification_failure(self, url: str, attempts: int = 1, duration: float = 0.0):
        """记录验证失败"""
        self.log_verification(url, "FAILED", attempts, duration)

    def log_verification_skip(self, url: str):
        """记录跳过验证"""
        self.log_verification(url, "SKIPPED", 0, 0.0)


# 全局日志实例
logger = Logger()


def get_logger(name: Optional[str] = None) -> Logger:
    """获取日志实例"""
    if name:
        return Logger(name)
    return logger