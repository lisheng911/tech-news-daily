#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选推送模块
每个分类都有静态备用数据，确保网络失败也能推送
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


# ============ 静态备用数据（网络失败时使用） ============

# 国内AI工具（静态主数据）
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

# AI动态备用数据
AI_NEWS_BACKUP = [
    {"name": "OpenAI发布GPT-4.5", "url": "https://openai.com/", "desc": "最新大模型，能力更强"},
    {"name": "DeepSeek R1开源发布", "url": "https://www.deepseek.com/", "desc": "国产推理模型，媲美o1"},
    {"name": "Claude 3.5 Sonnet更新", "url": "https://anthropic.com/", "desc": "编程能力大幅提升"},
    {"name": "Gemini 2.0发布", "url": "https://deepmind.google/", "desc": "谷歌最新多模态模型"},
    {"name": "Llama 3.3开源", "url": "https://ai.meta.com/", "desc": "Meta开源大模型"},
    {"name": "AI编程工具Trae发布", "url": "https://www.trae.ai/", "desc": "字节AI编程工具"},
    {"name": "Sora视频生成开放", "url": "https://openai.com/sora", "desc": "OpenAI视频生成"},
    {"name": "Midjourney V7发布", "url": "https://midjourney.com/", "desc": "AI绘画新版本"},
]

# GitHub热门备用数据
GITHUB_BACKUP = [
    {"name": "microsoft/semantic-kernel", "url": "https://github.com/microsoft/semantic-kernel", "desc": "AI应用开发框架", "stars": 22000},
    {"name": "openai/whisper", "url": "https://github.com/openai/whisper", "desc": "语音识别模型", "stars": 60000},
    {"name": "langchain-ai/langchain", "url": "https://github.com/langchain-ai/langchain", "desc": "LLM应用框架", "stars": 90000},
    {"name": "lobehub/lobe-chat", "url": "https://github.com/lobehub/lobe-chat", "desc": "开源AI聊天客户端", "stars": 35000},
    {"name": "hpcaitech/Open-Sora", "url": "https://github.com/hpcaitech/Open-Sora", "desc": "开源视频生成", "stars": 20000},
    {"name": "comfyanonymous/ComfyUI", "url": "https://github.com/comfyanonymous/ComfyUI", "desc": "Stable Diffusion界面", "stars": 45000},
    {"name": "AutomaApp/automa", "url": "https://github.com/AutomaApp/automa", "desc": "浏览器自动化", "stars": 10000},
    {"name": "denoland/deno", "url": "https://github.com/denoland/deno", "desc": "JavaScript运行时", "stars": 95000},
    {"name": "rustdesk/rustdesk", "url": "https://github.com/rustdesk/rustdesk", "desc": "远程桌面软件", "stars": 70000},
    {"name": "usebruno/bruno", "url": "https://github.com/usebruno/bruno", "desc": "API测试工具", "stars": 25000},
]

# 自动化脚必备用数据
AUTOMATION_BACKUP = [
    {"name": "yt-dlp/yt-dlp", "url": "https://github.com/yt-dlp/yt-dlp", "desc": "视频下载工具", "stars": 75000},
    {"name": "huginn/huginn", "url": "https://github.com/huginn/huginn", "desc": "自动化代理系统", "stars": 42000},
    {"name": "n8n-io/n8n", "url": "https://github.com/n8n-io/n8n", "desc": "工作流自动化", "stars": 45000},
    {"name": "ArchiveBox/ArchiveBox", "url": "https://github.com/ArchiveBox/ArchiveBox", "desc": "网页归档工具", "stars": 20000},
    {"name": "pwndbg/pwndbg", "url": "https://github.com/pwndbg/pwndbg", "desc": "调试工具", "stars": 7000},
    {"name": "sherlock-project/sherlock", "url": "https://github.com/sherlock-project/sherlock", "desc": "用户名搜索工具", "stars": 55000},
    {"name": "InstaPy/InstaPy", "url": "https://github.com/InstaPy/InstaPy", "desc": "Instagram自动化", "stars": 16000},
    {"name": "github/hub", "url": "https://github.com/github/hub", "desc": "GitHub命令行工具", "stars": 22000},
    {"name": "scrapy/scrapy", "url": "https://github.com/scrapy/scrapy", "desc": "爬虫框架", "stars": 52000},
    {"name": "puppeteer/puppeteer", "url": "https://github.com/puppeteer/puppeteer", "desc": "浏览器自动化", "stars": 88000},
]

# 科技资讯备用数据
TECH_NEWS_BACKUP = [
    {"name": "AI大模型最新进展汇总", "url": "https://www.36kr.com/", "source": "36氪"},
    {"name": "程序员必备工具推荐", "url": "https://sspai.com/", "source": "少数派"},
    {"name": "开源项目精选推荐", "url": "https://github.com/", "source": "GitHub"},
    {"name": "科技行业热点解读", "url": "https://www.zhihu.com/", "source": "知乎"},
    {"name": "开发者效率工具分享", "url": "https://juejin.cn/", "source": "掘金"},
    {"name": "AI编程工具对比评测", "url": "https://www.v2ex.com/", "source": "V2EX"},
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
        """获取所有内容，网络失败时使用备用数据"""
        result = {
            "国内AI工具": [],
            "AI动态": [],
            "GitHub热门": [],
            "自动化脚本": [],
            "科技资讯": [],
        }
        
        # 1. 国内AI工具（静态数据，100%保证）
        logger.info("🤖 获取国内AI工具...")
        result["国内AI工具"] = self._get_cn_ai_tools()
        
        # 2. AI动态
        logger.info("📢 获取AI动态...")
        result["AI动态"] = self._fetch_ai_news()
        if len(result["AI动态"]) < 5:
            logger.warning("AI动态数据不足，使用备用数据")
            result["AI动态"] = self._get_ai_news_backup()
        
        # 3. GitHub热门
        logger.info("🔥 获取GitHub热门...")
        result["GitHub热门"] = self._fetch_github_trending()
        if len(result["GitHub热门"]) < 5:
            logger.warning("GitHub热门数据不足，使用备用数据")
            result["GitHub热门"] = self._get_github_backup()
        
        # 4. 自动化脚本
        logger.info("⚡ 获取自动化脚本...")
        result["自动化脚本"] = self._fetch_automation_scripts()
        if len(result["自动化脚本"]) < 5:
            logger.warning("自动化脚本数据不足，使用备用数据")
            result["自动化脚本"] = self._get_automation_backup()
        
        # 5. 科技资讯
        logger.info("📰 获取科技资讯...")
        result["科技资讯"] = self._fetch_tech_news()
        if len(result["科技资讯"]) < 5:
            logger.warning("科技资讯数据不足，使用备用数据")
            result["科技资讯"] = self._get_tech_news_backup()
        
        return result
    
    # ============ 静态备用数据方法 ============
    
    def _get_cn_ai_tools(self) -> List[ToolItem]:
        """国内AI工具（静态）"""
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
    
    def _get_ai_news_backup(self) -> List[ToolItem]:
        """AI动态备用数据"""
        items = []
        for news in AI_NEWS_BACKUP:
            item = ToolItem(
                name=news["name"],
                category="AI动态",
                source="精选",
                link=news["url"],
                description=news["desc"],
                quality_score=7
            )
            item.practical_use = "AI动态"
            items.append(item)
        return items
    
    def _get_github_backup(self) -> List[ToolItem]:
        """GitHub热门备用数据"""
        items = []
        for proj in GITHUB_BACKUP:
            item = ToolItem(
                name=proj["name"],
                category="GitHub热门",
                source="GitHub",
                link=proj["url"],
                description=proj["desc"],
                stars=proj.get("stars", 0),
                quality_score=7
            )
            item.practical_use = self._get_practical_use(item)
            items.append(item)
        return items
    
    def _get_automation_backup(self) -> List[ToolItem]:
        """自动化脚必备用数据"""
        items = []
        for proj in AUTOMATION_BACKUP:
            item = ToolItem(
                name=proj["name"],
                category="自动化脚本",
                source="GitHub",
                link=proj["url"],
                description=proj["desc"],
                stars=proj.get("stars", 0),
                quality_score=8
            )
            item.practical_use = "自动化工具"
            items.append(item)
        return items
    
    def _get_tech_news_backup(self) -> List[ToolItem]:
        """科技资讯备用数据"""
        items = []
        for news in TECH_NEWS_BACKUP:
            item = ToolItem(
                name=news["name"],
                category="科技资讯",
                source=news["source"],
                link=news["url"],
                description="",
                quality_score=6
            )
            item.practical_use = "值得关注"
            items.append(item)
        return items
    
    # ============ 网络抓取方法 ============
    
    def _fetch_ai_news(self) -> List[ToolItem]:
        """AI动态 - 抓取网络数据"""
        items = []
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
        """GitHub热门 - 抓取网络数据"""
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
                    
                    match = re.search(r'([^/]+/[^/\s]+)', title)
                    name = match.group(1) if match else title
                    
                    if name in seen:
                        continue
                    seen.add(name)
                    
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
        """自动化脚本 - 抓取网络数据"""
        items = []
        seen = set()
        
        tool_keywords = [
            'tool', 'tools', 'cli', 'script', 'scripts', 'bot', 'helper',
            'automation', 'util', 'utility', 'downloader', 'crawler',
            'scraper', 'monitor', 'backup', 'sync', 'converter',
            'scheduler', 'notification', 'rss', 'email', 'api',
            'workflow', 'task', 'runner', 'manager', 'generator',
        ]
        
        urls = [
            "https://rsshub.app/github/trending/daily/python?limit=30",
            "https://rsshub.app/github/trending/daily/javascript?limit=25",
            "https://rsshub.app/github/trending/daily/go?limit=20",
            "https://rsshub.app/github/trending/daily/typescript?limit=20",
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
                    
                    match = re.search(r'([^/]+/[^/\s]+)', title)
                    name = match.group(1) if match else title
                    
                    if name in seen:
                        continue
                    seen.add(name)
                    
                    stars = 0
                    star_match = re.search(r'(\d+,?\d*)\s*star', summary, re.I)
                    if star_match:
                        stars = int(star_match.group(1).replace(',', ''))
                    
                    is_tool = any(kw in text for kw in tool_keywords)
                    
                    item = ToolItem(
                        name=name,
                        category="自动化脚本",
                        source="GitHub",
                        link=entry.get('link', ''),
                        description=self._clean_summary(summary, 50),
                        stars=stars,
                        quality_score=8 if is_tool else 6
                    )
                    item.practical_use = self._get_practical_use(item)
                    
                    if is_tool:
                        items.insert(len([i for i in items if i.quality_score >= 8]), item)
                    elif len(items) < 10:
                        items.append(item)
                    
                    if len(items) >= 10:
                        break
                        
                if len(items) >= 10:
                    break
            except Exception as e:
                logger.error(f"自动化脚本错误: {e}")
        
        return items[:10]
    
    def _fetch_tech_news(self) -> List[ToolItem]:
        """科技资讯 - 抓取网络数据"""
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
    
    # ============ 工具方法 ============
    
    def _clean_title(self, title: str) -> str:
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title[:50] + "..." if len(title) > 50 else title
    
    def _clean_summary(self, summary: str, max_len: int = 60) -> str:
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = re.sub(r'\s+', ' ', summary).strip()
        return summary[:max_len] + "..." if len(summary) > max_len else summary
    
    def _get_practical_use(self, item: ToolItem) -> str:
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