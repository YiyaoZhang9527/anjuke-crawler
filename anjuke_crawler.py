"""
安居客租房信息爬虫主程序 - 真正的列表→详情批量爬虫
"""

import asyncio
import csv
import os
from playwright.async_api import async_playwright, Browser, Page
from typing import List, Optional
from datetime import datetime

from config import config
from anti_crawler import anti_crawler
from data_extractor import data_extractor
from list_page_crawler import list_page_crawler
from logger import logger
from utils import handle_errors, retry, StatisticsTracker
from duplicate_checker import duplicate_checker


class AnjukeCrawler:
    """安居客爬虫主类 - 列表页→详情页批量爬取"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.stats = StatisticsTracker()

        # 初始化新功能模块
        if config.enable_duplicate_check:
            csv_file = config.duplicate_csv_file if config.duplicate_csv_file else config.csv_filename
            self.duplicate_checker = duplicate_checker.__class__(csv_file)
            self.duplicate_checker.enable(True)
        else:
            self.duplicate_checker = None

        # 验证码日志功能已集成到logger中，无需单独初始化

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def start(self):
        """启动浏览器"""
        if self.browser:
            return

        logger.crawler_start()

        # 启动Playwright
        playwright = await async_playwright().start()

        # 配置浏览器启动选项
        launch_options = {
            'headless': config.browser_headless,
            'args': [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        }

        # 添加代理配置
        if config.proxy_list:
            proxy = config.proxy_list[0]
            launch_options['proxy'] = {'server': proxy}

        # 启动浏览器
        self.browser = await playwright.chromium.launch(**launch_options)

        # 创建新页面
        self.page = await self.browser.new_page()

        # 设置反爬虫
        await anti_crawler.setup_browser_stealth(self.page)

        logger.browser_ready()

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
            logger.browser_close()

    async def crawl_from_list_pages(self, max_pages: int = None, max_houses_per_page: int = None) -> bool:
        """从房源列表页开始逐页处理 - 加载一页列表→爬取该页所有详情"""
        if not self.page:
            raise RuntimeError("请先调用start()方法或使用async with")

        # 使用.env配置的默认值
        if max_pages is None:
            max_pages = config.max_pages
        if max_houses_per_page is None:
            max_houses_per_page = config.max_houses_per_page

        # 生成列表页URL
        list_urls = await list_page_crawler.generate_list_urls(max_pages)
        logger.info(f"准备逐页处理 {len(list_urls)} 个列表页，每页最多{max_houses_per_page}套房源")

        # 准备CSV文件
        await self._prepare_csv()

        total_processed = 0

        # 逐页处理：加载列表页→立即爬取该页的详情页
        for page_num, list_url in enumerate(list_urls, 1):
            # 检查总房源数限制
            if self.stats.success_count >= config.max_total_houses:
                logger.info(f"已达到最大房源数限制: {config.max_total_houses}")
                break
            try:
                logger.progress(f"处理列表页 {page_num}/{len(list_urls)}: {list_url}")

                # 提取当前页的房源链接
                house_links = await list_page_crawler.extract_house_links(
                    self.page, list_url, max_houses_per_page
                )

                if not house_links:
                    logger.warning(f"列表页 {page_num} 未提取到房源链接")
                    continue

                logger.info(f"列表页 {page_num} 提取到 {len(house_links)} 个房源链接，开始爬取详情")

                # 立即爬取当前页的所有房源详情
                page_success_count = await self.crawl_house_batch(house_links)

                total_processed += len(house_links)
                logger.info(f"列表页 {page_num} 处理完成，累计处理 {total_processed} 套房源")

                # 页面间延时
                if page_num < len(list_urls):
                    await anti_crawler.smart_delay(3)

            except Exception:
                continue  # 错误已被装饰器记录

        logger.crawler_stop(self.stats.get_stats())

        return self.stats.success_count > 0

    @handle_errors(default_return=False)
    async def crawl_single_house(self, url: str) -> bool:
        """爬取单个房源 - 单一职责：只处理一个房源"""
        logger.info(f"开始爬取房源: {url}")

        # 安全导航到房源页
        if not await anti_crawler.safe_navigate(self.page, url):
            return False

        # 提取数据
        data = await data_extractor.extract_data(self.page, url)
        if not data:
            return False

        # 去重检查（如果启用）
        if self.duplicate_checker:
            house_id = data.get('房源编号', '').strip()
            if self.duplicate_checker.is_duplicate(house_id):
                logger.info(f"跳过重复房源: {house_id}")
                return False

        # 保存数据
        await self._save_to_csv(data)
        logger.success(f"房源爬取成功: {data.get('标题', 'Unknown')}")
        return True

    @handle_errors(default_return=0)
    async def crawl_house_batch(self, house_links: List[str]) -> int:
        """批量爬取房源 - 单一职责：只负责批量处理逻辑"""
        success_count = 0

        for i, url in enumerate(house_links, 1):
            logger.progress(f"房源进度: {i}/{len(house_links)}")

            # 爬取单个房源
            if await self.crawl_single_house(url):
                success_count += 1
                self.stats.record_success()
            else:
                self.stats.record_failure()

            # 智能延时
            await anti_crawler.smart_delay()

        logger.info(f"批量处理完成: 成功{success_count}套，失败{len(house_links) - success_count}套")
        return success_count

    async def _crawl_detail_pages(self, house_links: List[str]) -> bool:
        """批量爬取房源详情页 - 复用批量处理逻辑"""
        logger.info(f"开始批量爬取 {len(house_links)} 个房源详情页")

        # 直接复用批量处理函数
        success_count = await self.crawl_house_batch(house_links)

        return success_count > 0

    async def _prepare_csv(self):
        """准备CSV文件"""
        file_exists = os.path.exists(config.csv_filename)

        # 如果不存在或者不是追加模式，创建新文件
        if not file_exists or not config.append_mode:
            with open(config.csv_filename, 'w', newline='', encoding=config.csv_encoding) as f:
                writer = csv.writer(f)
                writer.writerow(data_extractor.csv_fields)
            logger.csv_created(config.csv_filename)
        else:
            logger.csv_appended(config.csv_filename)

    async def _save_to_csv(self, data: dict):
        """保存数据到CSV - 带详细日志"""
        try:
            logger.info(f"💾 开始保存数据到CSV: {config.csv_filename}")

            # 统计要保存的数据
            non_empty_data = {k: v for k, v in data.items() if v and v.strip()}
            empty_data_fields = [k for k, v in data.items() if not v or not v.strip()]

            logger.info(f"📝 保存数据统计: 共{len(data)}个字段，有数据{len(non_empty_data)}个，空数据{len(empty_data_fields)}个")

            # 显示即将保存的关键数据
            key_preview = {}
            for field in ['房源编号', '标题', '价格', '房源概况', '更新时间', '押金']:
                value = data.get(field, '')
                if value:
                    key_preview[field] = value[:30] + "..." if len(value) > 30 else value
                else:
                    key_preview[field] = "[空]"

            logger.info("📋 即将保存的关键数据:")
            for field, value in key_preview.items():
                status = "✅" if value != "[空]" else "❌"
                logger.info(f"   {status} {field}: {value}")

            # 执行实际的保存操作
            with open(config.csv_filename, 'a', newline='', encoding=config.csv_encoding) as f:
                writer = csv.DictWriter(f, fieldnames=data_extractor.csv_fields)
                writer.writerow(data)

            logger.success(f"✅ 数据保存成功: {data.get('标题', 'Unknown')}")

            # 如果有空字段，显示警告
            if empty_data_fields:
                logger.warning(f"⚠️  保存的数据中有{len(empty_data_fields)}个空字段: {', '.join(empty_data_fields[:5])}{'...' if len(empty_data_fields) > 5 else ''}")

        except Exception as e:
            logger.error(f"❌ CSV保存失败: {e}")
            logger.error(f"❌ 失败的数据标题: {data.get('标题', 'Unknown')}")
            raise  # 重新抛出异常以便上层处理

    def get_stats(self) -> dict:
        """获取爬取统计信息"""
        return self.stats.get_stats()


# 便捷函数
async def crawl_anjuke_from_list(max_pages: int = None, max_houses_per_page: int = None) -> bool:
    """一键爬取安居客房源信息 - 从列表页开始，使用.env默认配置

    Args:
        max_pages: 最大爬取列表页数（可选，默认使用.env配置）
        max_houses_per_page: 每页最大房源数（可选，默认使用.env配置）

    Returns:
        bool: 爬取是否成功
    """
    async with AnjukeCrawler() as crawler:
        return await crawler.crawl_from_list_pages(max_pages, max_houses_per_page)


async def crawl_anjuke_from_urls(urls: List[str]) -> bool:
    """从给定URL列表批量爬取

    Args:
        urls: 房源详情页URL列表

    Returns:
        bool: 爬取是否成功
    """
    async with AnjukeCrawler() as crawler:
        return await crawler._crawl_detail_pages(urls)


if __name__ == "__main__":
    # 直接运行爬虫 - 从列表页开始
    from logger import logger

    logger.info("🚀 启动安居客爬虫 - 逐页处理模式")
    logger.info(f"📋 配置: 列表页数={config.max_pages}, 每页房源数={config.max_houses_per_page}")
    logger.info(f"🎯 工作模式: 加载一页房源列表→爬取该页所有详情")
    logger.info(f"⚙️  延时配置: {config.crawl_delay}秒, 超时: {config.browser_timeout}ms")
    logger.info(f"📁 输出文件: {config.csv_filename}")

    async def run_crawler():
        # 使用.env默认配置，无需传递参数
        success = await crawl_anjuke_from_list()

        if success:
            logger.success("✅ 爬虫执行成功!")
        else:
            logger.error("❌ 爬虫执行失败!")

    # 运行爬虫
    asyncio.run(run_crawler())