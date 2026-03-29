#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选推送模块
确保每个分类都有足够内容
"""

import os
import re
import json
import requests
import feedparser
from datetime import datetime
from typing import List
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ToolItem:
    """内容条目"""
    name: str
    category: str
    source: str
    link: str
    description: str
    stars: int = 0
    quality_score: int = 0
    practical_use: str = ""


# ============ 国内AI工具精选（静态，保证数量） ============
CN_AI_TOOLS = [
    {"name": "DeepSeek R1 - 深度思考免费模型", "url": "https://www.deepseek.com/", "desc": "国产最强推理模型，免费开放，API超便宜"},
    {"name": "Kimi - 20万字长文本AI", "url": "https://kimi.moonshot.cn/", "desc": "支持超长文本，文件解析强，完全免费"},
    {"name": "通义千问 - 阿里大模型", "url": "https://tongyi.aliyun.com/", "desc": "文档处理强，有免费API额度"},
    {"name": "智谱清言 - 清华GLM", "url": "https://chatglm.cn/", "desc": "开源模型，可私有部署，有API"},
    {"name": "豆包 - 字节免费AI", "url": "https://www.doubao.com/", "desc": "完全免费，对话体验好"},
    {"name": "即梦AI - 免费AI绘画", "url": "https://jimeng.jianying.com/", "desc": "字节出品，免费生成图片"},
    {"name": "可灵AI - AI视频生成", "url": "https://klingai.kuaishou.com/", "desc": "快手出品，视频生成效果好"},
    {"name": "Coze扣子 - 无代码AI应用", "url": "https://www.coze.cn/", "desc": "无代码搭建AI机器人，免费托管"},
    {"name": "Dify - 开源AI应用平台", "url": "https://dify.ai/", "desc": "可私有部署的LLM应用开发平台"},
    {"name": "Cursor - AI编程神器", "url": "https://cursor.com/", "desc": "AI自动写代码，程序员必备"},
]


class NewsFetcher:
    """信息抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.timeout = 25
    
    def fetch_all(self) -> dict:
        """直接按分类获取，确保每个分类都有内容"""
        result = {
            "国内AI工具": [],
            "AI动态": [],
            "GitHub热门": [],
            "自动化脚本": [],
            "科技资讯": [],
        }
        
        # 1. 国内AI工具（静态数据，保证10条）
        logger.info("🤖 获取国内AI工具...")
        result["国内AI工具"] = self._get_cn_ai_tools()
        
        # 2. AI动态（不筛选，直接取科技新闻）
        logger.info("📢 获取AI动态...")
        result["AI动态"] = self._fetch_ai_news()
        
        # 3. GitHub热门（不筛选，直接取热门）
        logger.info("🔥 获取GitHub热门...")
        result["GitHub热门"] = self._fetch_github_trending()
        
        # 4. 自动化脚本（从GitHub筛选工具类项目）
        logger.info("⚡ 获取自动化脚本...")
        result["自动化脚本"] = self._fetch_automation_scripts()
        
        # 5. 科技资讯（知乎、少数派等）
        logger.info("📰 获取科技资讯...")
        result["科技资讯"] = self._fetch_tech_news()
        
        return result
    
    def _get_cn_ai_tools(self) -> List[ToolItem]:
        """国内AI工具（静态数据）"""
        items = []
        for tool in CN_AI_TOOLS:
            item = ToolItem(
                name=tool["name"],
                category="国内AI工具",
                source="精选",
                link=tool["url"],
                description=tool["desc"],
                quality_score=8
            )
            item.practical_use = self._get_practical_use(item)
            items.append(item)
        return items
    
    def _fetch_ai_news(self) -> List[ToolItem]:
        """AI动态 - 不筛选关键词，直接取科技资讯"""
        items = []
        
        # 数据源：Hacker News + 36氪 + IT之家
        sources = [
            ("https://rsshub.app/hackernews/best", "Hacker News"),
            ("https://rsshub.app/36kr/newsflashes", "36氪"),
            ("https://rsshub.app/ithome/ranking", "IT之家"),
        ]
        
        seen_titles = set()
        
        for url, source in sources:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    
                    # 去重
                    title_key = re.sub(r'\s+', '', title.lower())[:30]
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)
                    
                    item = ToolItem(
                        name=self._clean_title(title),
                        category="AI动态",
                        source=source,
                        link=entry.get('link', ''),
                        description=self._clean_summary(entry.get('summary', '')),
                        quality_score=7
                    )
                    item.practical_use = self._get_practical_use(item)
                    items.append(item)
                    
                    if len(items) >= 10:
                        break
                        
                if len(items) >= 10:
                    break
            except Exception as e:
                logger.error(f"{source} 错误: {e}")
        
        return items
    
    def _fetch_github_trending(self) -> List[ToolItem]:
        """GitHub热门 - 直接取热门项目，不筛选"""
        items = []
        seen = set()
        
        url = "https://rsshub.app/github/trending/daily/any?limit=30"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                for entry in feed.entries:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or ''
                    
                    # 提取项目名
                    match = re.search(r'([^/]+/[^/\s]+)', title)
                    name = match.group(1) if match else title
                    
                    if name in seen:
                        continue
                    seen.add(name)
                    
                    # 提取stars
                    stars = 0
                    star_match = re.search(r'(\d+,?\d*)\s*star', summary, re.I)
                    if star_match:
                        stars = int(star_match.group(1).replace(',', ''))
                    
                    item = ToolItem(
                        name=name,
                        category="GitHub热门",
                        source="GitHub",
                        link=link,
                        description=self._clean_summary(summary, 60),
                        stars=stars,
                        quality_score=7
                    )
                    item.practical_use = self._get_practical_use(item)
                    items.append(item)
                    
                    if len(items) >= 10:
                        break
        except Exception as e:
            logger.error(f"GitHub热门错误: {e}")
        
        return items
    
    def _fetch_automation_scripts(self) -> List[ToolItem]:
        """自动化脚本 - 从GitHub筛选工具类项目"""
        items = []
        seen = set()
        
        # 工具类关键词
        tool_keywords = [
            'tool', 'tools', 'cli', 'script', 'scripts', 'bot', 'helper',
            'automation', 'util', 'utility', 'downloader', 'crawler',
            'scraper', 'monitor', 'backup', 'sync', 'converter',
            'scheduler', 'notification', 'rss', 'email', 'api',
            'workflow', 'task', 'runner', 'manager', 'generator',
        ]
        
        # 从多个语言热门中筛选
        urls = [
            "https://rsshub.app/github/trending/daily/python?limit=30",
            "https://rsshub.app/github/trending/daily/javascript?limit=25",
            "https://rsshub.app/github/trending/daily/go?limit=20",
            "https://rsshub.app/github/trending/daily/rust?limit=15",
        ]
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                
                feed = feedparser.parse(response.content)
                for entry in feed.entries:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '') or ''
                    text = f"{title} {summary}".lower()
                    
                    # 提取项目名
                    match = re.search(r'([^/]+/[^/\s]+)', title)
                    name = match.group(1) if match else title
                    
                    if name in seen:
                        continue
                    
                    # 筛选工具类项目
                    if not any(kw in text for kw in tool_keywords):
                        continue
                    
                    seen.add(name)
                    
                    # 提取stars
                    stars = 0
                    star_match = re.search(r'(\d+,?\d*)\s*star', summary, re.I)
                    if star_match:
                        stars = int(star_match.group(1).replace(',', ''))
                    
                    item = ToolItem(
                        name=name,
                        category="自动化脚本",
                        source="GitHub",
                        link=entry.get('link', ''),
                        description=self._clean_summary(summary, 50),
                        stars=stars,
                        quality_score=8
                    )
                    item.practical_use = self._get_practical_use(item)
                    items.append(item)
                    
                    if len(items) >= 10:
                        break
                        
                if len(items) >= 10:
                    break
            except Exception as e:
                logger.error(f"自动化脚本错误: {e}")
        
        return items
    
    def _fetch_tech_news(self) -> List[ToolItem]:
        """科技资讯 - 知乎、少数派、掘金"""
        items = []
        seen_titles = set()
        
        sources = [
            ("https://rsshub.app/zhihu/hotlist", "知乎"),
            ("https://sspai.com/feed", "少数派"),
            ("https://rsshub.app/juejin/trending/all/monthly", "掘金"),
            ("https://www.v2ex.com/api/topics/hot.json", "V2EX"),
        ]
        
        for url, source in sources:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                
                # V2EX是JSON格式
                if "v2ex" in url:
                    data = response.json()
                    for topic in data[:8]:
                        title = topic.get('title', '')
                        title_key = re.sub(r'\s+', '', title.lower())[:30]
                        if title_key in seen_titles:
                            continue
                        seen_titles.add(title_key)
                        
                        node = topic.get('node', {}).get('name', '')
                        item = ToolItem(
                            name=self._clean_title(title),
                            category="科技资讯",
                            source=f"V2EX/{node}",
                            link=topic.get('url', ''),
                            description="",
                            quality_score=6
                        )
                        item.practical_use = "值得关注"
                        items.append(item)
                else:
                    feed = feedparser.parse(response.content)
                    for entry in feed.entries[:10]:
                        title = entry.get('title', '')
                        title_key = re.sub(r'\s+', '', title.lower())[:30]
                        if title_key in seen_titles:
                            continue
                        seen_titles.add(title_key)
                        
                        item = ToolItem(
                            name=self._clean_title(title),
                            category="科技资讯",
                            source=source,
                            link=entry.get('link', ''),
                            description=self._clean_summary(entry.get('summary', '')),
                            quality_score=6
                        )
                        item.practical_use = "值得关注"
                        items.append(item)
                        
                if len(items) >= 12:
                    break
            except Exception as e:
                logger.error(f"{source} 科技资讯错误: {e}")
        
        return items
    
    def _clean_title(self, title: str) -> str:
        """清理标题"""
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title[:50] + "..." if len(title) > 50 else title
    
    def _clean_summary(self, summary: str, max_len: int = 60) -> str:
        """清理摘要"""
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = re.sub(r'\s+', ' ', summary).strip()
        return summary[:max_len] + "..." if len(summary) > max_len else summary
    
    def _get_practical_use(self, item: ToolItem) -> str:
        """生成实用建议"""
        text = f"{item.name} {item.description}".lower()
        
        if '免费' in text or 'free' in text:
            return "免费可用"
        elif '开源' in text or 'open-source' in text:
            return "开源可部署"
        elif 'automation' in text or '自动化' in text or 'script' in text or '脚本' in text:
            return "自动化工具"
        elif 'api' in text or 'sdk' in text:
            return "开发接口"
        elif 'cli' in text or '命令行' in text:
            return "命令行工具"
        elif 'ai' in text or 'gpt' in text or 'llm' in text or '大模型' in text:
            return "AI能力"
        elif 'crawler' in text or '爬虫' in text or 'scraper' in text:
            return "数据采集"
        return "值得关注"


if __name__ == '__main__':
    fetcher = NewsFetcher()
    result = fetcher.fetch_all()
    
    print("\n" + "=" * 50)
    print("📊 抓取结果统计")
    print("=" * 50)
    
    total = 0
    for cat, items in result.items():
        print(f"\n【{cat}】{len(items)}条")
        print("-" * 40)
        for i, item in enumerate(items[:5], 1):
            stars = f" ⭐{item.stars:,}" if item.stars > 0 else ""
            print(f"{i}. {item.name}{stars}")
        if len(items) > 5:
            print(f"... 还有 {len(items)-5} 条")
        total += len(items)
    
    print(f"\n📊 总计: {total} 条")
