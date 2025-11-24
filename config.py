"""
安居客爬虫配置管理模块
读取.env配置文件，提供配置参数
"""

import os
from typing import Dict, Any


class Config:
    """配置管理类 - 简单、直接、无多余功能"""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """加载.env配置文件"""
        # 确保当前目录有.env文件
        if not os.path.exists('.env'):
            raise FileNotFoundError("缺少.env配置文件")

        # 读取.env文件
        with open('.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 解析配置项
        config_dict = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                # 移除行内注释（#后面的部分）
                value = value.split('#')[0].strip()
                config_dict[key] = value

        # 浏览器配置
        self.browser_headless = config_dict.get('BROWSER_HEADLESS', 'false').lower() == 'true'
        self.browser_timeout = int(config_dict.get('BROWSER_TIMEOUT', '30000'))
        self.base_url = config_dict.get('BASE_URL', 'https://hf.zu.anjuke.com/fangyuan')

        # 爬取配置
        self.max_houses_per_page = int(config_dict.get('MAX_HOUSES_PER_PAGE', '60'))
        self.max_total_houses = int(config_dict.get('MAX_TOTAL_HOUSES', '50000'))
        self.max_pages = int(config_dict.get('MAX_PAGES', '100'))
        self.crawl_delay = int(config_dict.get('CRAWL_DELAY', '2'))
        self.page_load_delay = int(config_dict.get('PAGE_LOAD_DELAY', '2'))

        # CSV配置
        self.csv_filename = config_dict.get('CSV_FILENAME', 'anjuke_houses.csv')
        self.csv_encoding = config_dict.get('CSV_ENCODING', 'utf-8')
        self.append_mode = config_dict.get('APPEND_MODE', 'false').lower() == 'true'

        # 日志配置
        self.log_level = config_dict.get('LOG_LEVEL', 'INFO')
        self.show_progress = config_dict.get('SHOW_PROGRESS', 'true').lower() == 'true'
        self.log_filename = config_dict.get('LOG_FILENAME', 'anjuke_crawler.log')

        # 反爬配置
        self.enable_auto_verification = config_dict.get('ENABLE_AUTO_VERIFICATION', 'true').lower() == 'true'
        self.max_retry_times = int(config_dict.get('MAX_RETRY_TIMES', '3'))
        self.retry_delay = int(config_dict.get('RETRY_DELAY', '5'))
        self.enable_stealth_mode = config_dict.get('ENABLE_STEALTH_MODE', 'true').lower() == 'true'

        # 代理配置
        proxy_str = config_dict.get('PROXY_LIST', '').strip()
        self.proxy_list = proxy_str.split(',') if proxy_str else []

        # 目标区域
        regions_str = config_dict.get('TARGET_REGIONS', '').strip()
        self.target_regions = regions_str.split(',') if regions_str else []

        # 数据验证配置
        self.validate_data = config_dict.get('VALIDATE_DATA', 'true').lower() == 'true'
        self.min_price = int(config_dict.get('MIN_PRICE', '100'))
        self.max_price = int(config_dict.get('MAX_PRICE', '50000'))
        self.min_area = int(config_dict.get('MIN_AREA', '1'))
        self.max_area = int(config_dict.get('MAX_AREA', '1000'))

        # 新增功能配置
        self.enable_duplicate_check = config_dict.get('ENABLE_DUPLICATE_CHECK', 'true').lower() == 'true'
        self.duplicate_csv_file = config_dict.get('DUPLICATE_CSV_FILE', '').strip()
        self.enable_verification_log = config_dict.get('ENABLE_VERIFICATION_LOG', 'true').lower() == 'true'
        self.verification_log_file = config_dict.get('VERIFICATION_LOG_FILE', 'verification_log.csv')

    def get_dict(self) -> Dict[str, Any]:
        """返回配置字典"""
        return {
            'browser_headless': self.browser_headless,
            'browser_timeout': self.browser_timeout,
            'base_url': self.base_url,
            'max_houses_per_page': self.max_houses_per_page,
            'max_total_houses': self.max_total_houses,
            'max_pages': self.max_pages,
            'crawl_delay': self.crawl_delay,
            'page_load_delay': self.page_load_delay,
            'csv_filename': self.csv_filename,
            'csv_encoding': self.csv_encoding,
            'append_mode': self.append_mode,
            'log_level': self.log_level,
            'show_progress': self.show_progress,
            'log_filename': self.log_filename,
            'enable_auto_verification': self.enable_auto_verification,
            'max_retry_times': self.max_retry_times,
            'retry_delay': self.retry_delay,
            'enable_stealth_mode': self.enable_stealth_mode,
            'proxy_list': self.proxy_list,
            'target_regions': self.target_regions,
            'validate_data': self.validate_data,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'min_area': self.min_area,
            'max_area': self.max_area,
            'enable_duplicate_check': self.enable_duplicate_check,
            'duplicate_csv_file': self.duplicate_csv_file,
            'enable_verification_log': self.enable_verification_log,
            'verification_log_file': self.verification_log_file
        }

    def __str__(self) -> str:
        """配置概览"""
        return f"Config(browser_headless={self.browser_headless}, csv_file='{self.csv_filename}')"


# 全局配置实例
config = Config()