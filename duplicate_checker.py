"""
房源去重检查模块 - 极简设计
从现有CSV加载房源ID，避免重复处理
"""

import csv
import os
from typing import Set, Optional
from logger import logger


class DuplicateChecker:
    """房源去重检查器 - 只加载不保存，极简设计"""

    def __init__(self, csv_file: Optional[str] = None):
        self.crawled_ids: Set[str] = set()
        self.enabled = True
        self.csv_file = csv_file
        self._load_existing_ids()

    def _load_existing_ids(self):
        """从现有CSV加载已爬取的房源ID"""
        try:
            # 如果没有指定CSV文件，尝试从.env读取
            if not self.csv_file:
                csv_file = 'anjuke_houses.csv'
                if os.path.exists('.env'):
                    with open('.env', 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                if key.strip() == 'CSV_FILENAME':
                                    csv_file = value.split('#')[0].strip()
                                    break
                self.csv_file = csv_file

            if os.path.exists(self.csv_file):
                with open(self.csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        house_id = row.get('房源编号', '').strip()
                        if house_id:
                            self.crawled_ids.add(house_id)
                logger.info(f"加载去重数据: {len(self.crawled_ids)}个已爬取房源ID")
        except Exception as e:
            logger.warning(f"加载去重数据失败: {e}")
            self.crawled_ids = set()

    def is_duplicate(self, house_id: str) -> bool:
        """检查是否重复 - 核心方法，只做判断"""
        if not self.enabled or not house_id:
            return False

        is_dup = house_id in self.crawled_ids
        if is_dup:
            logger.info(f"跳过重复房源: {house_id}")
        return is_dup

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_crawled': len(self.crawled_ids),
            'csv_file': self.csv_file,
            'enabled': self.enabled
        }

    def enable(self, enabled: bool = True):
        """启用/禁用去重检查"""
        self.enabled = enabled
        logger.info(f"去重检查: {'启用' if enabled else '禁用'}")


# 全局实例
duplicate_checker = DuplicateChecker()