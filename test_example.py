"""
安居客爬虫测试示例
测试爬虫的基本功能
"""

import asyncio
from anjuke_crawler import crawl_anjuke_single

# 测试URL - 请替换为实际的安居客租房页面URL
TEST_URLS = [
    # 整租测试URL
    "https://hf.zu.anjuke.com/fangyuan/1299356733",
    # 合租测试URL
    "https://hf.zu.anjuke.com/fangyuan/1299356733"
]

async def test_crawler():
    """测试爬虫功能"""
    from logger import logger
    logger.info("开始测试安居客爬虫...")

    # 测试单个URL爬取
    test_url = TEST_URLS[0]  # 使用第一个URL进行测试
    logger.info(f"测试URL: {test_url}")

    try:
        data = await crawl_anjuke_single(test_url)

        if data:
            logger.success("测试成功! 提取到的数据:")
            for key, value in data.items():
                if value:  # 只显示有值的字段
                    logger.info(f"  {key}: {value}")
        else:
            logger.error("测试失败 - 未能提取到数据")

    except Exception as e:
        logger.exception("测试异常", e)

if __name__ == "__main__":
    from logger import logger
    logger.warning("请确保已正确配置.env文件中的代理设置")
    logger.warning("请将TEST_URLS替换为实际的安居客租房页面URL")

    # 运行测试
    asyncio.run(test_crawler())