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

    async def _detect_verification_page(self, page: Page) -> bool:
        """检测是否为验证页面 - 专门优化58验证页面检测"""
        try:
            # 等待页面稳定
            await page.wait_for_timeout(2000)

            current_url = page.url

            # 1. 直接检测58验证页面URL
            if 'callback.58.com/antibot/verifycode' in current_url:
                return True

            # 2. 检查是否包含验证相关URL特征
            if 'verifycode' in current_url or 'antibot' in current_url:
                return True

            # 3. 检查页面标题
            page_title = await page.title()
            verification_titles = ['验证码', '访问过于频繁', '安全验证', '请输入验证码']
            if any(title in page_title for title in verification_titles):
                return True

            # 4. 直接查找58验证页面的特征按钮
            try:
                await page.wait_for_selector('button:has-text("点击按钮进行验证")', timeout=3000)
                return True
            except:
                pass

            # 5. 检查页面文本内容
            page_content = await page.content()
            verification_texts = ['点击按钮进行验证', '点击按钮完成验证', '访问过于频繁，本次访问做以下验证码校验']
            if any(text in page_content for text in verification_texts):
                return True

            return False
        except:
            return False

    async def _click_verification_button(self, page: Page) -> bool:
        """点击验证按钮 - 专门优化58验证页面"""
        try:
            # 58验证页面的按钮选择器 - 按优先级排序
            verification_selectors = [
                'button:has-text("点击按钮进行验证")',  # 最准确的58验证按钮
                'button:has-text("点击按钮完成验证")',
                '[role="button"]:has-text("点击按钮进行验证")',
                'text="点击按钮进行验证"',  # 直接文本匹配
                '*:has-text("点击按钮进行验证")'  # 通用选择器作为兜底
            ]

            for selector in verification_selectors:
                try:
                    logger.info(f"尝试使用选择器点击验证按钮: {selector}")

                    # 等待元素出现并可点击
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        # 确保元素可见和可点击
                        await element.wait_for_element_state('visible', timeout=2000)

                        # 滚动到元素位置
                        await element.scroll_into_view_if_needed()

                        # 点击按钮
                        await element.click()
                        logger.info(f"✅ 成功点击验证按钮，使用选择器: {selector}")
                        return True

                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue

            logger.warning("❌ 所有验证按钮选择器都失败了")
            return False

        except Exception as e:
            logger.warning(f"点击验证按钮时发生异常: {e}")
            return False

    async def _verify_success(self, page: Page) -> bool:
        """验证是否成功 - 优化检测逻辑"""
        try:
            # 等待页面变化
            await page.wait_for_timeout(3000)

            current_url = page.url
            page_title = await page.title()

            logger.info(f"验证后检查 - URL: {current_url}, 标题: {page_title}")

            # 成功标志1: URL不再包含58验证特征
            url_success = (
                'callback.58.com/antibot/verifycode' not in current_url and
                'verifycode' not in current_url and
                'antibot' not in current_url
            )

            # 成功标志2: 页面标题不再是验证页面
            title_success = all(
                title not in page_title
                for title in ['验证码', '访问过于频繁', '请输入验证码', '安全验证']
            )

            # 成功标志3: URL已经跳转到安居客房源页面
            url_target_success = 'anjuke.com' in current_url

            # 只要满足任一成功条件就认为验证成功
            success = url_success and (title_success or url_target_success)

            logger.info(f"验证结果检查 - URL成功: {url_success}, 标题成功: {title_success}, 目标成功: {url_target_success}, 总体成功: {success}")

            return success

        except Exception as e:
            logger.warning(f"验证成功检查时发生异常: {e}")
            return False

    async def handle_verification(self, page: Page) -> bool:
        """处理验证码 - 简化的主控制逻辑"""
        start_time = time.time()
        current_url = page.url

        if not config.enable_auto_verification:
            if config.enable_verification_log:
                logger.log_verification_skip(current_url)
            return True

        try:
            if not await self._detect_verification_page(page):
                return True

            logger.verification_detected()

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    if await self._click_verification_button(page):
                        logger.info(f"已点击验证按钮 (尝试 {attempt + 1}/{max_attempts})")

                        # 等待验证完成
                        await page.wait_for_timeout(5000 + (attempt * 2000))

                        if await self._verify_success(page):
                            duration = time.time() - start_time
                            logger.verification_success()
                            if config.enable_verification_log:
                                logger.log_verification_success(page.url, attempt + 1, duration)
                            return True
                        else:
                            logger.warning(f"验证未成功，继续尝试 ({attempt + 1}/{max_attempts})")

                except Exception as e:
                    logger.warning(f"验证尝试 {attempt + 1} 失败: {e}")

            duration = time.time() - start_time
            logger.verification_failed()
            if config.enable_verification_log:
                logger.log_verification_failure(current_url, max_attempts, duration)
            return False

        except Exception as e:
            logger.exception("验证码处理异常", e)
            return True

    @handle_errors(default_return=False, operation_name="页面导航")
    async def navigate_to_page(self, page: Page, url: str) -> bool:
        """简单导航 - 单一职责：只负责页面导航"""
        response = await page.goto(
            url,
            timeout=config.browser_timeout,
            wait_until='networkidle'  # 修改为networkidle确保页面完全加载
        )
        return response.status == 200

    @handle_errors(default_return=False, operation_name="页面加载后处理")
    async def post_load_actions(self, page: Page) -> bool:
        """页面加载后的处理 - 单一职责：只负责加载后操作"""
        # 确保页面完全加载，防止动态内容未渲染完成
        try:
            await self.wait_for_page_load(page, timeout=15000)
        except:
            logger.warning("页面完全加载等待超时，继续执行")

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