#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选推送模块
分类：AI动态、自动化脚本、GitHub热门、热门科技
"""

import os
import re
import json
import requests
import feedparser
from datetime import datetime
from typing import List
from dataclasses import dataclass, field
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


# ============ 国内AI工具精选 ============
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
    {"name": "Trae - 字节AI编程工具", "url": "https://www.trae.ai/", "desc": "国产版Cursor，免费使用"},
]

# ============ 数据源 ============
RSS_SOURCES = {
    # AI动态源
    "ai_news": [
        ("https://rsshub.app/hackernews/best", "Hacker News"),
        ("https://rsshub.app/openai/blog", "OpenAI官方"),
        ("https://rsshub.app/anthropic/news", "Anthropic"),
        ("https://rsshub.app/deepseek/blog", "DeepSeek"),
        ("https://rsshub.app/36kr/newsflashes", "36氪快讯"),
    ],
    # GitHub热门
    "github": [
        ("https://rsshub.app/github/trending/daily/any?limit=40", "全站"),
        ("https://rsshub.app/github/trending/daily/python?limit=25", "Python"),
        ("https://rsshub.app/github/trending/daily/javascript?limit=20", "JavaScript"),
        ("https://rsshub.app/github/trending/daily/typescript?limit=15", "TypeScript"),
        ("https://rsshub.app/github/trending/daily/go?limit=15", "Go"),
    ],
    # 科技资讯
    "tech_news": [
        ("https://rsshub.app/zhihu/hotlist", "知乎热榜"),
        ("https://sspai.com/feed", "少数派"),
        ("https://rsshub.app/juejin/trending/all/monthly", "掘金热门"),
        ("https://rsshub.app/hellogithub/weekly", "HelloGitHub"),
    ],
    # V2EX
    "v2ex": [
        ("https://www.v2ex.com/api/topics/hot.json", "V2EX热门", "json"),
    ],
}


class NewsFetcher:
    """信息抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.timeout = 25
    
    def fetch_all(self) -> List[ToolItem]:
        """获取所有内容"""
        items = []
        
        # 1. 国内AI工具
        logger.info("🤖 获取国内AI工具...")
        items.extend(self._get_cn_ai_tools())
        
        # 2. AI动态
        logger.info("📢 获取AI动态...")
        items.extend(self._fetch_ai_news())
        
        # 3. GitHub热门
        logger.info("🔥 获取GitHub热门...")
        items.extend(self._fetch_github())
        
        # 4. 自动化脚本(从GitHub筛选)
        logger.info("⚡ 获取自动化脚本...")
        items.extend(self._fetch_automation_scripts())
        
        # 5. 科技资讯
        logger.info("📰 获取科技资讯...")
        items.extend(self._fetch_tech_news())
        
        # 6. V2EX
        logger.info("💬 获取V2EX...")
        items.extend(self._fetch_v2ex())
        
        return items
    
    def _get_cn_ai_tools(self) -> List[ToolItem]:
        """国内AI工具"""
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
            items.append(item)
        return items
    
    def _fetch_ai_news(self) -> List[ToolItem]:
        """AI动态"""
        items = []
        ai_keywords = ['ai', 'gpt', 'llm', 'chatgpt', 'claude', 'deepseek', 'openai', 
                      'anthropic', 'model', 'gemini', '人工智能', '大模型', '智能体', 
                      'agent', 'sora', 'diffusion', 'stable', 'midjourney']
        
        for url, source in RSS_SOURCES["ai_news"]:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    text = title.lower()
                    
                    # AI相关内容才保留
                    if not any(kw in text for kw in ai_keywords):
                        continue
                    
                    item = ToolItem(
                        name=self._clean_title(title),
                        category="AI动态",
                        source=source,
                        link=entry.get('link', ''),
                        description=self._clean_summary(entry.get('summary', '')),
                        quality_score=7
                    )
                    items.append(item)
            except Exception as e:
                logger.error(f"{source} AI新闻错误: {e}")
        
        return items
    
    def _fetch_github(self) -> List[ToolItem]:
        """GitHub热门"""
        items = []
        seen = set()
        
        for url, lang in RSS_SOURCES["github"]:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:25]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
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
                    
                    # 生成精炼标题
                    desc = self._clean_summary(summary, 60)
                    display_name = f"{name}"
                    if desc:
                        display_name = f"{name}: {desc}"
                    
                    item = ToolItem(
                        name=display_name[:60],
                        category="GitHub热门",
                        source=f"GitHub {lang}",
                        link=link,
                        description=self._clean_summary(summary),
                        stars=stars,
                        quality_score=7
                    )
                    items.append(item)
            except Exception as e:
                logger.error(f"GitHub {lang} 错误: {e}")
        
        return items
    
    def _fetch_automation_scripts(self) -> List[ToolItem]:
        """自动化脚本(从GitHub筛选)"""
        items = []
        automation_keywords = [
            'automation', 'automate', '自动化', 'script', '脚本', 'bot',
            'crawler', '爬虫', 'scraper', 'tool', '工具', 'helper',
            'workflow', '工作流', 'task', '任务', 'scheduler', '定时',
            'notification', '推送', '提醒', 'backup', '备份',
            'download', '下载', 'sync', '同步', 'cli', '命令行',
            'spider', '监控', 'monitor', 'rss', 'email', '消息',
        ]
        
        try:
            url = "https://rsshub.app/github/trending/daily/any?limit=50"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                for entry in feed.entries:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '') or ''
                    text = f"{title} {summary}".lower()
                    
                    # 筛选自动化相关
                    if not any(kw in text for kw in automation_keywords):
                        continue
                    
                    match = re.search(r'([^/]+/[^/\s]+)', title)
                    name = match.group(1) if match else title
                    
                    stars = 0
                    star_match = re.search(r'(\d+,?\d*)\s*star', summary, re.I)
                    if star_match:
                        stars = int(star_match.group(1).replace(',', ''))
                    
                    item = ToolItem(
                        name=f"{name}: {self._clean_summary(summary, 50)}",
                        category="自动化脚本",
                        source="GitHub",
                        link=entry.get('link', ''),
                        description=self._clean_summary(summary),
                        stars=stars,
                        quality_score=8
                    )
                    items.append(item)
                    
                    if len(items) >= 10:
                        break
        except Exception as e:
            logger.error(f"自动化脚本错误: {e}")
        
        return items
    
    def _fetch_tech_news(self) -> List[ToolItem]:
        """科技资讯"""
        items = []
        
        for url, source in RSS_SOURCES["tech_news"]:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue
                
                if "zhihu" in url:
                    feed = feedparser.parse(response.content)
                    for entry in feed.entries[:10]:
                        item = ToolItem(
                            name=self._clean_title(entry.get('title', '')),
                            category="科技资讯",
                            source=source,
                            link=entry.get('link', ''),
                            description=self._clean_summary(entry.get('summary', '')),
                            quality_score=6
                        )
                        items.append(item)
                else:
                    feed = feedparser.parse(response.content)
                    for entry in feed.entries[:12]:
                        item = ToolItem(
                            name=self._clean_title(entry.get('title', '')),
                            category="科技资讯",
                            source=source,
                            link=entry.get('link', ''),
                            description=self._clean_summary(entry.get('summary', '')),
                            quality_score=6
                        )
                        items.append(item)
            except Exception as e:
                logger.error(f"{source} 科技资讯错误: {e}")
        
        return items
    
    def _fetch_v2ex(self) -> List[ToolItem]:
        """V2EX热门"""
        items = []
        
        try:
            url = "https://www.v2ex.com/api/topics/hot.json"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                for topic in data[:10]:
                    node = topic.get('node', {}).get('name', '')
                    item = ToolItem(
                        name=self._clean_title(topic.get('title', '')),
                        category="科技资讯",
                        source=f"V2EX/{node}",
                        link=topic.get('url', ''),
                        description=topic.get('content', '')[:80],
                        quality_score=6
                    )
                    items.append(item)
        except Exception as e:
            logger.error(f"V2EX错误: {e}")
        
        return items
    
    def _clean_title(self, title: str) -> str:
        """清理标题"""
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title[:50] + "..." if len(title) > 50 else title
    
    def _clean_summary(self, summary: str, max_len: int = 80) -> str:
        """清理摘要"""
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = re.sub(r'\s+', ' ', summary).strip()
        return summary[:max_len] + "..." if len(summary) > max_len else summary
    
    def generate_practical_use(self, item: ToolItem) -> str:
        """生成实用建议"""
        text = f"{item.name} {item.description}".lower()
        
        if any(kw in text for kw in ['免费', 'free']):
            return "免费可用"
        elif any(kw in text for kw in ['开源', 'open-source']):
            return "开源可部署"
        elif any(kw in text for kw in ['自动化', 'automation', '脚本', 'script']):
            return "自动化效率工具"
        elif any(kw in text for kw in ['api', 'sdk']):
            return "开发接口可用"
        elif any(kw in text for kw in ['cli', '命令行']):
            return "命令行工具"
        elif any(kw in text for kw in ['ai', 'gpt', 'llm', '大模型']):
            return "AI能力可用"
        elif any(kw in text for kw in ['爬虫', 'crawler', 'scraper']):
            return "数据采集工具"
        return "值得关注"
    
    def filter_by_category(self, items: List[ToolItem]) -> dict:
        """按分类筛选"""
        result = {
            "国内AI工具": [],
            "AI动态": [],
            "GitHub热门": [],
            "自动化脚本": [],
            "科技资讯": [],
        }
        
        seen = set()
        
        for item in items:
            item.practical_use = self.generate_practical_use(item)
            
            key = re.sub(r'\s+', '', item.name.lower())
            if key in seen:
                continue
            seen.add(key)
            
            cat = item.category
            if cat in result:
                result[cat].append(item)
        
        # 限制每个分类数量
        limits = {
            "国内AI工具": 8,
            "AI动态": 6,
            "GitHub热门": 6,
            "自动化脚本": 5,
            "科技资讯": 6,
        }
        
        for cat in result:
            result[cat] = result[cat][:limits[cat]]
        
        return result


if __name__ == '__main__':
    fetcher = NewsFetcher()
    all_items = fetcher.fetch_all()
    categorized = fetcher.filter_by_category(all_items)
    
    print(f"\n📊 总计获取 {len(all_items)} 条\n")
    
    for cat, items in categorized.items():
        print(f"\n【{cat}】({len(items)}条)")
        print("-" * 40)
        for i, item in enumerate(items, 1):
            stars = f" ⭐{item.stars:,}" if item.stars > 0 else ""
            print(f"{i}. {item.name}{stars}")
            print(f"   {item.practical_use} | {item.source}")
