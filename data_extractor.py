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

                // 6. 租赁方式
                result["租赁方式"] = allText.includes('整租') ? '整租' : '合租';

                // 7. 房源概况 - 直接搜索包含房源概况关键词的元素
                let houseOverviewElement = null;
                const elements = document.querySelectorAll('*');

                // 搜索包含房源概况关键词的元素
                for (let element of elements) {{
                    const text = element.textContent || '';
                    if ((text.includes('小区环境优美') ||
                         text.includes('南北通透') ||
                         text.includes('拎包即住') ||
                         text.includes('性价比高') ||
                         text.includes('物业办事效率')) &&
                        text.length > 50 &&
                        text.length < 2000) {{
                        houseOverviewElement = element;
                        break;
                    }}
                }}

                // 如果找到房源概况元素，提取内容
                if (houseOverviewElement) {{
                    let overviewText = houseOverviewElement.textContent.trim();

                    // 清理房源概况内容，移除无关内容
                    const cleanOverview = overviewText
                        .replace(/猜你喜欢.*$/g, '')
                        .replace(/相似房源.*$/g, '')
                        .replace(/附近房源.*$/g, '')
                        .replace(/专家解读.*$/g, '')
                        .replace(/小区问答.*$/g, '')
                        .replace(/出租要求.*$/g, '')
                        .replace(/\\s+/g, ' ')
                        .trim();

                    if (cleanOverview && cleanOverview.length > 10) {{
                        result["房源概况"] = cleanOverview;
                    }}
                }}

                // 8. 设施提取 - 根据租赁方式和has类名精确提取
                const rentType = allText.includes('整租') ? '整租' : '合租';

                if (rentType === '整租') {{
                    // 整租：查找房屋配套，只提取带has类名的设施
                    let facilitySection = null;

                    // 方法1：查找包含"房屋配套"文本的所有元素
                    const allElements = Array.from(document.querySelectorAll('*'));

                    for (let element of allElements) {{
                        if (element.textContent && element.textContent.includes('房屋配套')) {{
                            // 查找下一个包含设施的列表
                            let nextElement = element.nextElementSibling;
                            while (nextElement) {{
                                if (nextElement.tagName === 'UL' || nextElement.tagName === 'OL') {{
                                    facilitySection = nextElement;
                                    break;
                                }}
                                nextElement = nextElement.nextElementSibling;
                            }}
                            if (facilitySection) break;
                        }}
                    }}

                    // 方法2：如果方法1失败，直接查找包含设施的列表
                    if (!facilitySection) {{
                        const allLists = document.querySelectorAll('ul, ol');
                        for (let list of allLists) {{
                            const items = list.querySelectorAll('li');
                            if (items.length > 5) {{ // 假设设施列表有较多项目
                                const firstItem = items[0].textContent;
                                // 检查是否包含常见的设施词汇
                                if (firstItem.includes('冰箱') || firstItem.includes('洗衣机') ||
                                    firstItem.includes('空调') || firstItem.includes('电视')) {{
                                    facilitySection = list;
                                    break;
                                }}
                            }}
                        }}
                    }}

                    if (facilitySection) {{
                        const facilityItems = facilitySection.querySelectorAll('li');
                        const facilities = [];

                        facilityItems.forEach(item => {{
                            const text = item.textContent?.trim() || '';
                            // 只提取带has类名的设施
                            if (text && item.className.includes('has')) {{
                                facilities.push(text);
                            }}
                        }});

                        result["房屋设施"] = facilities.join('、');
                        result["卧室设施"] = '';
                        result["公共设施"] = '';
                    }}
                }} else {{
                    // 合租：分别提取卧室设施和公共设施
                    let bedroomSection = null;
                    let publicSection = null;

                    // 查找卧室设施
                    const elements = Array.from(document.querySelectorAll('*'));
                    elements.forEach(el => {{
                        if (el.textContent && el.textContent.includes('卧室设施')) {{
                            let nextElement = el.nextElementSibling;
                            while (nextElement) {{
                                if (nextElement.tagName === 'UL' || nextElement.tagName === 'OL') {{
                                    bedroomSection = nextElement;
                                    break;
                                }}
                                nextElement = nextElement.nextElementSibling;
                            }}
                        }}
                        if (el.textContent && el.textContent.includes('公共设施')) {{
                            let nextElement = el.nextElementSibling;
                            while (nextElement) {{
                                if (nextElement.tagName === 'UL' || nextElement.tagName === 'OL') {{
                                    publicSection = nextElement;
                                    break;
                                }}
                                nextElement = nextElement.nextElementSibling;
                            }}
                        }}
                    }});

                    const bedroomFacilities = [];
                    const publicFacilities = [];

                    // 提取卧室设施（带has类名）
                    if (bedroomSection) {{
                        const bedroomItems = bedroomSection.querySelectorAll('li');
                        bedroomItems.forEach(item => {{
                            const text = item.textContent?.trim() || '';
                            if (text && item.className.includes('has')) {{
                                bedroomFacilities.push(text);
                            }}
                        }});
                    }}

                    // 提取公共设施（带has类名）
                    if (publicSection) {{
                        const publicItems = publicSection.querySelectorAll('li');
                        publicItems.forEach(item => {{
                            const text = item.textContent?.trim() || '';
                            if (text && item.className.includes('has')) {{
                                publicFacilities.push(text);
                            }}
                        }});
                    }}

                    result["房屋设施"] = '';
                    result["卧室设施"] = bedroomFacilities.join('、');
                    result["公共设施"] = publicFacilities.join('、');
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