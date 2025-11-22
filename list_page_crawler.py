"""
房源列表页爬取器
从安居客房源列表页提取房源详情链接
"""

from typing import List
from playwright.async_api import Page
from logger import logger
from config import config
from utils import handle_errors


class ListPageCrawler:
    """房源列表页爬取器"""

    def __init__(self):
        # 使用配置中的BASE_URL
        self.base_url = config.base_url

    @handle_errors(default_return=[], operation_name="房源链接提取")
    async def extract_house_links(self, page: Page, url: str, max_houses: int = 60) -> List[str]:
        """从房源列表页提取房源详情链接"""
        logger.info(f"开始提取房源链接: {url}")

        # 导航到房源列表页
        response = await page.goto(url, wait_until='domcontentloaded')
        if response.status != 200:
            logger.error(f"页面访问失败，状态码: {response.status}")
            return []

        # 等待页面加载
        await page.wait_for_timeout(3000)

        # 使用JavaScript提取房源链接
        house_links = await page.evaluate("""
                () => {
                    const links = [];

                    // 方法1: 查找包含房源链接的a标签
                    const allLinks = document.querySelectorAll('a[href*="/fangyuan/"]');
                    for (const link of allLinks) {
                        const href = link.href;
                        // 确保是完整的房源详情页URL
                        if (href.includes('anjuke.com') &&
                            href.includes('/fangyuan/') &&
                            href.match(/\\/fangyuan\\/\\d+$/)) {
                            links.push(href);
                        }
                    }

                    // 方法2: 如果方法1失败，尝试查找可能的链接模式
                    if (links.length === 0) {
                        const allAs = document.querySelectorAll('a');
                        for (const a of allAs) {
                            const href = a.href;
                            if (href &&
                                href.includes('anjuke.com') &&
                                href.match(/fangyuan\\/\\d+/)) {
                                links.push(href);
                            }
                        }
                    }

                    // 去重并返回
                    return [...new Set(links)];
                }
            """)

            # 限制数量
        if len(house_links) > max_houses:
            house_links = house_links[:max_houses]

        logger.success(f"成功提取 {len(house_links)} 个房源链接")

        # 输出前几个链接用于调试
        for i, link in enumerate(house_links[:5]):
            logger.info(f"房源链接 {i+1}: {link}")

        return house_links

    async def generate_list_urls(self, pages: int = None) -> List[str]:
        """生成列表页URL列表 - 支持TARGET_REGIONS配置"""
        if pages is None:
            pages = config.max_pages

        urls = []

        # 如果配置了TARGET_REGIONS，为每个区域生成URL
        if config.target_regions:
            for region in config.target_regions:
                region = region.strip()
                if region:
                    # 为每个区域生成分页URL
                    for page in range(1, pages + 1):
                        if page == 1:
                            url = f"{self.base_url}/{region}/"
                        else:
                            url = f"{self.base_url}/{region}/p{page}/"
                        urls.append(url)
        else:
            # 没有配置TARGET_REGIONS，使用默认URL
            for page in range(1, pages + 1):
                if page == 1:
                    url = f"{self.base_url}/"
                else:
                    url = f"{self.base_url}/p{page}/"
                urls.append(url)

        logger.info(f"生成了 {len(urls)} 个列表页URL，覆盖 {len(config.target_regions) if config.target_regions else 1} 个区域")
        return urls


# 全局列表页爬取器实例
list_page_crawler = ListPageCrawler()