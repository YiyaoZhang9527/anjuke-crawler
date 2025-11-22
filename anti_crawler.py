"""
反爬虫处理模块
包含验证码处理、延时控制、浏览器伪装等反爬虫应对策略
"""

import asyncio
import random
import time
from typing import Optional
from playwright.async_api import Page
from config import config
from logger import logger
from utils import retry, handle_errors


class AntiCrawler:
    """反爬虫处理器 - 专注核心功能，避免过度工程"""

    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]

    async def setup_browser_stealth(self, page: Page):
        """设置浏览器隐身模式"""
        if not config.enable_stealth_mode:
            return

        # 设置随机User-Agent
        await page.set_extra_http_headers({
            'User-Agent': random.choice(self.user_agents)
        })

        # 设置视口大小
        await page.set_viewport_size({
            'width': random.choice([1920, 1366, 1440]),
            'height': random.choice([1080, 768, 900])
        })

        # 注入反检测脚本
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            window.chrome = {
                runtime: {}
            };
        """)

    async def smart_delay(self, base_delay: Optional[float] = None):
        """智能延时 - 避免被检测的随机延时"""
        delay = base_delay or config.crawl_delay
        random_delay = delay + random.uniform(0, delay * 0.3)
        await asyncio.sleep(random_delay)

    async def simulate_human_behavior(self, page: Page):
        """模拟人类行为 - 随机滑动页面"""
        # 随机滚动
        scroll_distance = random.randint(100, 500)
        await page.mouse.wheel(0, scroll_distance)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # 随机滚动回来
        await page.mouse.wheel(0, -scroll_distance // 2)
        await asyncio.sleep(random.uniform(0.3, 0.8))

    async def handle_verification(self, page: Page) -> bool:
        """处理验证码 - 支持自动和手动验证"""
        if not config.enable_auto_verification:
            return True

        try:
            # 检查是否出现反爬验证页面 - 安居客特有的验证界面
            await page.wait_for_timeout(3000)

            # 检查页面标题和内容特征
            page_title = await page.title()
            page_content = await page.content()

            verification_indicators = [
                lambda: "验证码" in page_title,
                lambda: "访问过于频繁" in page_title,
                lambda: "点击按钮进行验证" in page_content,
                lambda: "callback.58.com/antibot/verifycode" in page.url
            ]

            verification_found = False
            for indicator in verification_indicators:
                try:
                    if await indicator():
                        verification_found = True
                        break
                except:
                    continue

            if verification_found:
                logger.verification_detected()

                # 尝试自动点击验证按钮
                verification_success = False
                max_attempts = 3

                for attempt in range(max_attempts):
                    try:
                        # 安居客验证按钮的特征
                        verify_button_selectors = [
                            'button:has-text("点击按钮进行验证")',
                            'button:has-text("点击按钮完成验证")',
                            'text="点击按钮进行验证"',  # 直接文本按钮
                            'text="点击按钮完成验证"'
                        ]

                        button_clicked = False
                        for selector in verify_button_selectors:
                            try:
                                # 先尝试通过文本查找按钮
                                if selector.startswith('text='):
                                    button_text = selector.replace('text=', '').strip('"')
                                    button = await page.locator(f'button:has-text("{button_text}")').first
                                else:
                                    button = await page.locator(selector).first

                                if button:
                                    await button.click()
                                    button_clicked = True
                                    logger.info(f"已点击验证按钮 (尝试 {attempt + 1}/{max_attempts})")
                                    break
                            except:
                                continue

                        if button_clicked:
                            # 等待页面跳转（验证需要时间）
                            await page.wait_for_timeout(5000 + (attempt * 2000))

                            # 检查是否验证成功 - 通过检查页面特征
                            current_url = page.url
                            page_title = await page.title()

                            # 验证成功的标志：URL不再包含verifycode，或页面内容变为房源详情
                            verification_success = (
                                'verifycode' not in current_url and
                                '验证码' not in page_title and
                                ('fangyuan' in current_url or '房源' in await page.content())
                            )

                            if verification_success:
                                logger.verification_success()
                                return True
                            else:
                                logger.warning(f"验证未成功，继续尝试 ({attempt + 1}/{max_attempts})")
                                continue

                    except Exception as e:
                        logger.warning(f"验证尝试 {attempt + 1} 失败: {e}")
                        continue

                if not verification_success:
                    logger.verification_failed()
                    return False
            else:
                return True

        except Exception as e:
            logger.exception("验证码处理异常", e)
            return True  # 异常时假设验证成功，避免阻塞

    @handle_errors(default_return=False, operation_name="页面导航")
    async def navigate_to_page(self, page: Page, url: str) -> bool:
        """简单导航 - 单一职责：只负责页面导航"""
        response = await page.goto(
            url,
            timeout=config.browser_timeout,
            wait_until='domcontentloaded'
        )
        return response.status == 200

    @handle_errors(default_return=False, operation_name="页面加载后处理")
    async def post_load_actions(self, page: Page) -> bool:
        """页面加载后的处理 - 单一职责：只负责加载后操作"""
        # 页面加载后延时
        await page.wait_for_timeout(config.page_load_delay * 1000)

        # 处理验证码
        if not await self.handle_verification(page):
            return False

        # 模拟人类行为
        await self.simulate_human_behavior(page)
        return True

    @retry(max_times=3, delay=1.0, operation_name="安全导航")
    @handle_errors(default_return=False, operation_name="安全导航")
    async def safe_navigate(self, page: Page, url: str) -> bool:
        """安全导航 - 简化后的组合函数"""
        logger.url_start(url)

        # 1. 导航到页面
        if not await self.navigate_to_page(page, url):
            logger.warning("页面导航失败")
            return False

        # 2. 加载后处理
        if not await self.post_load_actions(page):
            logger.warning("页面加载后处理失败")
            return False

        logger.success("页面加载成功")
        return True

    async def wait_for_page_load(self, page: Page, timeout: int = 10000):
        """等待页面完全加载"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
            await page.wait_for_timeout(1000)
        except:
            logger.warning("页面加载超时，继续执行")


# 全局反爬虫实例
anti_crawler = AntiCrawler()