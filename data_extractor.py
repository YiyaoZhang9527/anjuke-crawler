"""
数据提取模块 - 最终修正版
使用最简单直接的JavaScript提取，避免正则表达式问题
"""

import re
from datetime import datetime
from typing import Dict, Optional
from playwright.async_api import Page
from logger import logger
from config import config
from utils import handle_errors


class DataExtractor:
    """数据提取器 - 基于JavaScript的精确数据提取"""

    def __init__(self):
        self.csv_fields = [
            "房源编号", "标题", "租赁方式", "是否官方核验", "是否安选",
            "价格", "押金", "房屋面积", "户型", "小区", "详情链接",
            "楼层", "朝向", "装修", "联系方式", "个人姓名", "公司名称",
            "经纪人信息", "房源概况", "房屋设施", "卧室设施", "公共设施",
            "更新时间", "爬取时间"
        ]

    async def extract_formatted_data(self, page: Page, url: str) -> Dict:
        """直接提取格式化数据 - JavaScript直接返回最终CSV格式，消除多层转换"""
        js_code = f"""
            () => {{
                const now = new Date();
                const timestamp = now.getFullYear() + '-' +
                    String(now.getMonth() + 1).padStart(2, '0') + '-' +
                    String(now.getDate()).padStart(2, '0') + ' ' +
                    String(now.getHours()).padStart(2, '0') + ':' +
                    String(now.getMinutes()).padStart(2, '0') + ':' +
                    String(now.getSeconds()).padStart(2, '0');

                // 初始化结果对象
                const result = {{
                    "房源编号": '',
                    "标题": '',
                    "租赁方式": '',
                    "是否官方核验": '',
                    "是否安选": '',
                    "价格": '',
                    "押金": '',
                    "房屋面积": '',
                    "户型": '',
                    "小区": '',
                    "详情链接": '{url}',
                    "楼层": '',
                    "朝向": '',
                    "装修": '',
                    "联系方式": '',
                    "个人姓名": '',
                    "公司名称": '',
                    "经纪人信息": '',
                    "房源概况": '',
                    "房屋设施": '',
                    "卧室设施": '',
                    "公共设施": '',
                    "更新时间": '',
                    "爬取时间": timestamp
                }};

                const allText = document.body.innerText;

                // 1. 标题
                const h1Element = document.querySelector('h1');
                result["标题"] = h1Element ? h1Element.textContent.trim() : '';

                // 2. 价格 - 查找3-4位数字
                const strongElements = document.querySelectorAll('strong, em');
                strongElements.forEach(el => {{
                    const text = el.textContent.trim();
                    if (/^\\d{{3,4}}$/.test(text)) {{
                        result["价格"] = text + '元/月';
                    }}
                }});

                // 3. 基本信息 - 从li元素提取
                const liElements = document.querySelectorAll('li');
                liElements.forEach(li => {{
                    const text = li.textContent.trim();
                    if (text.includes('户型：')) {{
                        result["户型"] = text.replace('户型：', '').trim();
                    }} else if (text.includes('面积：')) {{
                        result["房屋面积"] = text.replace('面积：', '').trim();
                    }} else if (text.includes('楼层：')) {{
                        result["楼层"] = text.replace('楼层：', '').trim();
                    }} else if (text.includes('朝向：')) {{
                        result["朝向"] = text.replace('朝向：', '').trim();
                    }} else if (text.includes('装修：')) {{
                        result["装修"] = text.replace('装修：', '').trim();
                    }}
                }});

                // 4. 小区名称
                const communityLink = document.querySelector('a[href*="/community/view/"]');
                result["小区"] = communityLink ? communityLink.textContent.trim() : '';

                // 5. 房屋编码和更新时间 - 从房屋信息描述中提取
                const allElements = document.querySelectorAll('div, p, span');
                allElements.forEach(el => {{
                    const text = el.textContent;
                    if (text.includes('房屋编码：')) {{
                        const houseCodeMatch = text.match(/房屋编码：(\\d+)/);
                        if (houseCodeMatch) {{
                            result["房源编号"] = houseCodeMatch[1];
                        }}
                        // 同时从同一个元素中提取更新时间
                        const updateTimeMatch = text.match(/更新时间：(\\d{{4}}年\\d{{1,2}}月\\d{{1,2}}日)/);
                        if (updateTimeMatch) {{
                            result["更新时间"] = updateTimeMatch[1];
                        }}
                    }}
                }});

                // 6. 租赁方式 - 精确定位到页面中的租赁方式标识
                let rentType = '合租'; // 默认值

                // 重用之前查询的liElements，避免重复声明
                for (let li of liElements) {{
                    const text = li.textContent.trim();
                    if (text === '合租' || text === '整租') {{
                        rentType = text;
                        break;
                    }}
                }}

                result["租赁方式"] = rentType;

                // 7. 房源概况 - 使用DOM结构定位为主，关键词匹配为辅
                let houseOverviewText = '';

                // 方法1：通过DOM结构定位（最可靠）
                const overviewHeading = Array.from(document.querySelectorAll('h2')).find(h2 =>
                    h2.textContent && h2.textContent.includes('房源概况')
                );

                if (overviewHeading) {{
                    const parentDiv = overviewHeading.parentElement;
                    if (parentDiv && parentDiv.nextElementSibling) {{
                        const contentDiv = parentDiv.nextElementSibling;
                        if (contentDiv.tagName === 'DIV' && contentDiv.textContent.trim().length > 10) {{
                            houseOverviewText = contentDiv.textContent.trim();
                        }}
                    }}
                }}

                // 方法2：如果DOM结构定位失败，使用关键词搜索
                if (!houseOverviewText || houseOverviewText.length < 10) {{
                    const elements = document.querySelectorAll('*');
                    for (let element of elements) {{
                        const text = element.textContent || '';
                        // 放宽关键词条件，只要包含常见的房源描述词汇即可
                        if ((text.includes('小区') || text.includes('南北') || text.includes('采光') ||
                             text.includes('装修') || text.includes('交通') || text.includes('周边') ||
                             text.includes('拎包') || text.includes('舒适') || text.includes('性价比') ||
                             text.includes('空间') || text.includes('格局') || text.includes('楼层')) &&
                            text.length > 30 && text.length < 2000 &&
                            !text.includes('猜你喜欢') && !text.includes('相似房源') &&
                            !text.includes('附近房源') && !text.includes('小区问答') &&
                            !text.includes('看了又看')) {{
                            houseOverviewText = text.trim();
                            break;
                        }}
                    }}
                }}

                // 方法3：如果前两种方法都失败，查找包含"房源概况"的区域的下一个div
                if (!houseOverviewText || houseOverviewText.length < 10) {{
                    const allHeadings = document.querySelectorAll('h2, h3');
                    for (let heading of allHeadings) {{
                        if (heading.textContent && heading.textContent.includes('房源概况')) {{
                            let nextElement = heading.nextElementSibling;
                            while (nextElement) {{
                                if (nextElement.tagName === 'DIV' && nextElement.textContent.trim().length > 10) {{
                                    houseOverviewText = nextElement.textContent.trim();
                                    break;
                                }}
                                nextElement = nextElement.nextElementSibling;
                            }}
                            if (houseOverviewText) break;
                        }}
                    }}
                }}

                // 清理房源概况内容
                if (houseOverviewText && houseOverviewText.length > 10) {{
                    const cleanOverview = houseOverviewText
                        .replace(/猜你喜欢.*$/g, '')
                        .replace(/相似房源.*$/g, '')
                        .replace(/附近房源.*$/g, '')
                        .replace(/专家解读.*$/g, '')
                        .replace(/小区问答.*$/g, '')
                        .replace(/出租要求.*$/g, '')
                        .replace(/看了又看.*$/g, '')
                        .replace(/\\s+/g, ' ')
                        .trim();

                    if (cleanOverview && cleanOverview.length > 10) {{
                        result["房源概况"] = cleanOverview;
                    }}
                }}

                // 8. 设施提取 - 支持两种真实模式：统一模式（整租）和分分类模式（合租）
                result["房屋设施"] = '';
                result["卧室设施"] = '';
                result["公共设施"] = '';

                // 优先级1：检查分分类模式（卧室设施+公共设施）
                const bedroomSection = Array.from(document.querySelectorAll('div, h2')).find(el =>
                    el.textContent?.trim() === '卧室设施'
                );

                if (bedroomSection) {{
                    // 查找卧室设施列表
                    let bedroomElement = bedroomSection.nextElementSibling;
                    while (bedroomElement && bedroomElement.tagName !== 'UL' && bedroomElement.tagName !== 'OL') {{
                        bedroomElement = bedroomElement.nextElementSibling;
                    }}

                    // 查找公共设施
                    const publicSection = Array.from(document.querySelectorAll('div, h2')).find(el =>
                        el.textContent?.trim() === '公共设施'
                    );

                    let publicElement = null;
                    if (publicSection) {{
                        publicElement = publicSection.nextElementSibling;
                        while (publicElement && publicElement.tagName !== 'UL' && publicElement.tagName !== 'OL') {{
                            publicElement = publicElement.nextElementSibling;
                        }}
                    }}

                    // 提取分分类设施的has项
                    const bedroomFacilities = bedroomElement ?
                        Array.from(bedroomElement.querySelectorAll('li'))
                            .filter(li => li.textContent?.trim() && li.classList.contains('has'))
                            .map(li => li.textContent.trim()) : [];

                    const publicFacilities = publicElement ?
                        Array.from(publicElement.querySelectorAll('li'))
                            .filter(li => li.textContent?.trim() && li.classList.contains('has'))
                            .map(li => li.textContent.trim()) : [];

                    if (bedroomFacilities.length > 0 || publicFacilities.length > 0) {{
                        result["卧室设施"] = bedroomFacilities.join('、');
                        result["公共设施"] = publicFacilities.join('、');
                    }}
                }}

                // 优先级2：如果没有分分类，检查统一模式（房屋配套）
                if (!result["卧室设施"] && !result["公共设施"]) {{
                    // 查找包含peitao-item.has的UL元素（兼容性更好的方法）
                    let facilityList = null;
                    const allULs = document.querySelectorAll('ul');

                    for (let ul of allULs) {{
                        const hasItems = ul.querySelectorAll('li.peitao-item.has');
                        if (hasItems.length > 0) {{
                            facilityList = ul;
                            break;
                        }}
                    }}

                    if (facilityList) {{
                        const houseFacilities = Array.from(facilityList.querySelectorAll('li.peitao-item.has'))
                            .map(li => li.textContent?.trim() || '')
                            .filter(text => text);

                        if (houseFacilities.length > 0) {{
                            result["房屋设施"] = houseFacilities.join('、');
                        }}
                    }}
                }}

                // 9. 是否安选
                result["是否安选"] = allText.includes('安选') ? '是' : '否';

                // 10. 是否官方核验
                result["是否官方核验"] = allText.includes('核验码') ? '是' : '否';

                // 11. 押金 - 支持"付x押x"和"面议"两种格式
                let deposit = '';

                // 首先查找"付x押x"格式
                const depositRegex = /付(\\d+)押(\\d+)/;
                const depositMatch = allText.match(depositRegex);
                if (depositMatch) {{
                    deposit = `付${{depositMatch[1]}}押${{depositMatch[2]}}`;
                }} else if (allText.includes('面议')) {{
                    // 如果没有"付x押x"，查找"面议"
                    deposit = '面议';
                }}

                result["押金"] = deposit;

                // 12. 联系方式 - 查找手机号
                const phoneRegex = /1[3-9]\\d{{9}}/g;
                const phoneMatch = allText.match(phoneRegex);
                if (phoneMatch && phoneMatch.length > 0) {{
                    result["联系方式"] = phoneMatch[0];
                }}

                // 13. 公司名称 - 查找公司信息
                const companyRegex = /公司：([^\\.\\.\\.\\n]+)/;
                const companyMatch = allText.match(companyRegex);
                if (companyMatch) {{
                    result["公司名称"] = companyMatch[1].trim();
                }}

                // 14. 个人姓名 - 简单查找中文姓名h2
                let brokerName = '';
                const h2Elements = document.querySelectorAll('h2');

                for (let h2Element of h2Elements) {{
                    const text = h2Element.textContent.trim();
                    // 检查是否是中文姓名（2-3个中文字符）
                    if (/^[\\u4e00-\\u9fa5]{{2,3}}$/.test(text) &&
                        !text.includes('小区') &&
                        !text.includes('房源') &&
                        !text.includes('看了又看') &&
                        !text.includes('专家') &&
                        !text.includes('相似房源')) {{
                        brokerName = text;
                        break;
                    }}
                }}

                result["个人姓名"] = brokerName;
                result["经纪人信息"] = brokerName ? `${{brokerName}} - 房产经纪人` : '';

                return result;
            }}
        """
        return await page.evaluate(js_code)

    @handle_errors(default_return=False, operation_name="数据验证")
    def validate_data(self, formatted_data: Dict) -> bool:
        """验证数据 - 单一职责：只负责数据验证逻辑"""
        try:
            # 提取价格数字
            price_str = formatted_data.get('价格', '')
            if price_str:
                price_match = re.search(r'(\d+)', price_str.replace(',', ''))
                if price_match:
                    price = int(price_match.group(1))
                    if price < config.min_price or price > config.max_price:
                        logger.warning(f"价格超出范围: {price}元")
                        return False
                else:
                    logger.warning(f"无法解析价格: {price_str}")
                    return False

            # 提取面积数字
            area_str = formatted_data.get('房屋面积', '')
            if area_str:
                area_match = re.search(r'(\d+(?:\.\d+)?)', area_str)
                if area_match:
                    area = float(area_match.group(1))
                    if area < config.min_area or area > config.max_area:
                        logger.warning(f"面积超出范围: {area}㎡")
                        return False
                else:
                    logger.warning(f"无法解析面积: {area_str}")
                    return False

            return True
        except Exception as e:
            logger.error(f"数据验证异常: {e}")
            return False

    @handle_errors(default_return=None, operation_name="数据提取")
    async def extract_data(self, page: Page, url: str) -> Optional[Dict]:
        """提取数据主入口 - 优化后的单步提取"""
        logger.info("开始JavaScript数据提取")

        # 确保页面完全渲染完成，防止动态内容未加载
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
            await page.wait_for_timeout(2000)  # 额外2秒确保JavaScript完全执行
        except:
            logger.warning("页面渲染等待超时，继续执行")

        # 直接提取格式化数据，消除多层转换
        formatted_data = await self.extract_formatted_data(page, url)

        logger.success("数据提取完成")

        # 详细的数据预览日志
        non_empty_fields = {k: v for k, v in formatted_data.items() if v and v.strip()}
        empty_fields = [k for k, v in formatted_data.items() if not v or not v.strip()]

        logger.info(f"🔍 提取统计: 共{len(self.csv_fields)}个字段，有数据{len(non_empty_fields)}个，空数据{len(empty_fields)}个")

        # 显示关键字段的数据预览
        key_fields = ['标题', '价格', '房源概况', '更新时间', '押金', '房屋面积', '户型', '小区']
        logger.info("📊 关键字段数据预览:")
        for field in key_fields:
            value = formatted_data.get(field, '')
            if value:
                # 截断过长的内容用于日志显示
                display_value = value[:50] + "..." if len(value) > 50 else value
                logger.info(f"   ✅ {field}: {display_value}")
            else:
                logger.warning(f"   ❌ {field}: [空]")

        # 显示空字段列表（便于调试）
        if empty_fields:
            logger.debug(f"🔍 空字段详情: {', '.join(empty_fields)}")

        logger.data_extracted(len(non_empty_fields))

        # 验证数据（如果启用）
        if config.validate_data:
            if not self.validate_data(formatted_data):
                logger.warning(f"数据验证失败: {formatted_data.get('标题', 'Unknown')}")
                return None

        return formatted_data

    

# 全局数据提取器实例
data_extractor = DataExtractor()