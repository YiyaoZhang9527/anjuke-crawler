# CLAUDE.md

此文件为Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

这是一个基于Python的安居客租房信息爬虫。爬虫实现了"列表页→详情页"的架构，逐页处理租房房源列表，将全面的房源数据提取到CSV格式中。

## 开发环境设置

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

## 运行爬虫

```bash
# 运行主爬虫（使用.env配置）
python anjuke_crawler.py

# 使用虚拟环境运行
./venv/bin/python3 anjuke_crawler.py

# Python导入快速测试
python -c "
import asyncio
from anjuke_crawler import crawl_anjuke_from_list
asyncio.run(crawl_anjuke_from_list())
"
```

## 核心架构

爬虫遵循模块化设计，职责分离明确：

### 主要组件

1. **anjuke_crawler.py** - 主程序协调器，含异步上下文管理器

   - `AnjukeCrawler` 类实现列表→详情工作流程
   - 逐页处理：加载一个列表页→爬取该页所有详情页
   - 输出包含22个特定字段的CSV，包括设施提取
2. **config.py** - 配置管理（25个可配置参数）

   - 从 `.env`文件读取所有设置
   - 处理浏览器、爬取、CSV、日志、反爬虫和验证设置
   - 无硬编码值 - 完全由配置驱动
3. **list_page_crawler.py** - 列表页URL生成和链接提取

   - 通过组合 `BASE_URL`和 `TARGET_REGIONS`生成URL
   - 使用JavaScript注入提取房源详情链接
   - 支持分页和每页限制
4. **data_extractor.py** - 数据提取和验证

   - 基于JavaScript的DOM操作，提取22个CSV字段
   - 处理整租和合租的设施提取
   - 包含基于配置范围的价格/面积验证
5. **anti_crawler.py** - 反爬虫策略

   - 隐身模式配置
   - 代理支持和User-Agent轮换
   - 自动和手动验证码处理
   - 智能延时和重试机制
6. **logger.py** - 综合日志系统

   - 彩色控制台输出和文件日志
   - 可配置详细程度的进度跟踪
   - 直接读取 `.env`避免循环依赖

### 关键架构模式

- **异步上下文管理器**：`AnjukeCrawler`实现 `__aenter__`/`__aexit__`进行资源管理
- **逐页处理**：不同于批量爬虫，一次处理一个列表页以获得更好的内存管理
- **配置驱动**：所有25个 `.env`参数都被积极使用，无冗余设置
- **JavaScript注入**：使用Playwright的 `evaluate()`进行可靠的DOM操作
- **区域化URL生成**：自动为多个目标区域创建URL

### 工作流程

1. 加载 `.env`配置（25个参数）
2. 使用隐身设置初始化Playwright浏览器
3. 生成区域化URL：`BASE_URL + TARGET_REGIONS`
4. 对每个列表页：
   - 使用反爬虫措施导航
   - 提取房源详情链接（最多 `MAX_HOUSES_PER_PAGE`个）
   - 立即处理每个详情页
   - 应用数据验证（价格/面积范围）
   - 将有效数据写入CSV
5. 全程维护计数和重试逻辑

## 配置系统

所有行为通过 `.env`文件的25个参数控制：

- **浏览器配置**：`BROWSER_HEADLESS`、`BROWSER_TIMEOUT`
- **爬取配置**：`MAX_HOUSES_PER_PAGE`、`MAX_TOTAL_HOUSES`、`MAX_PAGES`、`CRAWL_DELAY`、`PAGE_LOAD_DELAY`
- **区域配置**：`BASE_URL`、`TARGET_REGIONS`（逗号分隔）
- **输出配置**：`CSV_FILENAME`、`CSV_ENCODING`、`APPEND_MODE`
- **日志配置**：`LOG_LEVEL`、`SHOW_PROGRESS`、`LOG_FILENAME`
- **反爬配置**：`ENABLE_STEALTH_MODE`、`ENABLE_AUTO_VERIFICATION`、`MAX_RETRY_TIMES`、`RETRY_DELAY`、`PROXY_LIST`
- **验证配置**：`VALIDATE_DATA`、`MIN_PRICE`、`MAX_PRICE`、`MIN_AREA`、`MAX_AREA`

## 输出文件

- **主要输出**：`anjuke_houses.csv`，包含22个字段（标题、价格、面积、设施、联系信息等）
- **日志文件**：`anjuke_crawler.log`，详细的执行跟踪
- **实时输出**：控制台进度报告，显示成功/失败计数

## 重要技术要点

- 使用Playwright + Chromium实现可靠的浏览器自动化
- JavaScript提取避免XPath/选择器的脆弱性
- 区域化URL生成支持多个目标区域
- 反爬虫包括自动和手动验证处理
- 所有数据验证可配置并可禁用
- 通过上下文管理器实现适当的异步资源清理

## ⭐ 函数单一职责原则 (最高优先级)

**绝对禁止**编写超过20行的函数。如果函数需要超过3层缩进，重新设计它。

### 强制规则
1. **函数长度限制**：任何函数不得超过20行代码
2. **单一职责**：每个函数只做一件事并做好它
3. **嵌套限制**：不得超过2层if/for嵌套
4. **参数限制**：函数参数不超过5个

### 当前需要重构的问题函数
- `anjuke_crawler.py:143-181` - `_crawl_page_detail_links` (39行，需要拆分)
- `anti_crawler.py:147-191` - `safe_navigate` (45行，过于复杂)
- `data_extractor.py:32-98` - `extract_data` (67行，职责混乱)

### 正确的函数设计示例
```python
# ❌ 错误：过长，职责混乱
async def process_page_details(self, house_links: List[str], page_num: int) -> bool:
    # 39行混合逻辑...

# ✅ 正确：单一职责，简洁
async def crawl_single_house(self, url: str) -> Optional[Dict]:
    """只做一件事：爬取单个房源"""
    if not await anti_crawler.safe_navigate(self.page, url):
        return None
    return await data_extractor.extract_data(self.page, url)

async def process_house_batch(self, house_links: List[str]) -> List[Dict]:
    """只做一件事：批量处理房源"""
    return [await self.crawl_single_house(url) for url in house_links]
```

### 重构原则
- 如果函数名包含"and"，拆分成两个函数
- 如果函数超过1个return语句，考虑拆分
- 如果try/catch占用了超过30%的函数体，使用装饰器
- 如果函数需要注释解释"这段代码做什么"，重写函数而不是写注释

**记住**：好代码不需要注释，因为它已经说清楚了一切。
