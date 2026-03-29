#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选工具/项目推送模块
抓取国内AI工具、GitHub热门项目、自动化脚本等
"""

import os
import re
import json
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ToolItem:
    """工具/项目条目"""
    name: str                    # 名称
    category: str                # 分类: ai_tool, github_project, automation, startup
    source: str                  # 来源
    link: str                    # 链接
    description: str             # 描述
    stars: int = 0               # GitHub stars (如适用)
    quality_score: int = 0       # 价值评分
    practical_use: str = ""      # 实际用途
    tags: List[str] = field(default_factory=list)


# ============ 数据源配置 ============

# 国内AI工具/模型
CN_AI_TOOLS = [
    # 大模型
    {"name": "DeepSeek", "url": "https://www.deepseek.com/", "desc": "国产大模型，API便宜，编程能力强", "tags": ["大模型", "API", "编程"]},
    {"name": "Kimi", "url": "https://kimi.moonshot.cn/", "desc": "长文本处理强，支持20万字上下文", "tags": ["大模型", "长文本"]},
    {"name": "通义千问", "url": "https://tongyi.aliyun.com/", "desc": "阿里大模型，文档处理强，有免费额度", "tags": ["大模型", "文档"]},
    {"name": "智谱清言", "url": "https://chatglm.cn/", "desc": "清华系大模型，GLM开源，有API", "tags": ["大模型", "开源"]},
    {"name": "豆包", "url": "https://www.doubao.com/", "desc": "字节跳动大模型，免费，对话体验好", "tags": ["大模型", "免费"]},
    {"name": "文心一言", "url": "https://yiyan.baidu.com/", "desc": "百度大模型，中文理解强", "tags": ["大模型", "中文"]},
    # AI工具
    {"name": "iFlow CLI", "url": "https://github.com/iflow-ai/iflow-cli", "desc": "国产AI编程助手，心流编程体验", "tags": ["编程工具", "AI助手"]},
    {"name": "Cursor中国版", "url": "https://cursor.com/", "desc": "AI编程编辑器，自动补全代码", "tags": ["编程工具", "IDE"]},
    {"name": "扣子Coze", "url": "https://www.coze.cn/", "desc": "字节AI应用搭建平台，无代码创建Bot", "tags": ["无代码", "AI应用"]},
    {"name": "Dify", "url": "https://dify.ai/", "desc": "开源LLM应用开发平台，可私有化部署", "tags": ["开源", "AI应用", "部署"]},
    {"name": "FastGPT", "url": "https://fastgpt.in/", "desc": "开源知识库问答系统，基于大模型", "tags": ["开源", "知识库", "RAG"]},
    {"name": "Cherry Studio", "url": "https://github.com/kangfenmao/cherry-studio", "desc": "国产AI客户端，支持多模型，美观易用", "tags": ["客户端", "开源"]},
    # AI绘画/视频
    {"name": "即梦", "url": "https://jimeng.jianying.com/", "desc": "字节AI绘画工具，免费生成图片", "tags": ["AI绘画", "免费"]},
    {"name": "可灵AI", "url": "https://klingai.kuaishou.com/", "desc": "快手AI视频生成，效果惊艳", "tags": ["AI视频", "创作"]},
    {"name": "LiblibAI", "url": "https://www.liblib.ai/", "desc": "AI绘画模型分享平台，大量免费模型", "tags": ["AI绘画", "模型库"]},
    # 效率工具
    {"name": "飞书", "url": "https://www.feishu.cn/", "desc": "协作办公，有飞书多维表格自动化", "tags": ["办公", "自动化"]},
    {"name": "Notion", "url": "https://www.notion.so/", "desc": "笔记+数据库+AI，个人知识管理首选", "tags": ["笔记", "知识管理"]},
    {"name": "RayLink", "url": "https://www.raylink.live/", "desc": "免费远程控制软件，流畅稳定", "tags": ["远程控制", "免费"]},
]

# GitHub Trending RSS (非官方但可用)
GITHUB_TRENDING_RSS = "https://mshibanami.github.io/GitHubTrendingRSS/daily.xml"

# 热门RSS源
RSS_FEEDS = [
    # 技术资讯
    ("https://www.v2ex.com/api/topics/hot.json", "V2EX热门", "json"),
    ("https://rsshub.app/hackernews/best", "Hacker News", "rss"),
    ("https://rsshub.app/github/trending/daily", "GitHub Trending", "rss"),
    # 国内资讯
    ("https://www.36kr.com/feed", "36氪", "rss"),
    ("https://sspai.com/feed", "少数派", "rss"),
    ("https://rsshub.app/zhihu/hotlist", "知乎热榜", "rss"),
    # Product Hunt
    ("https://rsshub.app/producthunt/today", "Product Hunt", "rss"),
]

# 自动化/实用项目关键词 (用于筛选GitHub项目)
AUTOMATION_KEYWORDS = [
    'automation', 'automate', '自动化', 'script', '脚本',
    'bot', '机器人', 'crawler', '爬虫', 'scraper',
    'tool', '工具', 'utility', 'helper', 'assistant',
    'workflow', '工作流', 'task', '任务', 'scheduler',
    'notification', '推送', '提醒', 'alert',
    'backup', '备份', 'sync', '同步',
    'download', '下载', 'converter', '转换',
    'github-actions', 'action', 'ci/cd',
    'cli', 'command-line', 'terminal',
    'api', 'wrapper', 'sdk', 'client',
    'spider', '监控', 'monitor',
]

# AI/大模型关键词
AI_KEYWORDS = [
    'ai', 'artificial-intelligence', '人工智能', 
    'llm', '大模型', 'gpt', 'chatgpt', 'claude',
    'deepseek', 'kimi', '通义', '文心', '智谱',
    'agent', '智能体', 'prompt', '提示词',
    'rag', '知识库', 'embedding', '向量',
    'chatbot', '对话', 'assistant',
    'generative', '生成式', 'aigc',
    'stable-diffusion', 'midjourney', '绘图',
]

# 创业/赚钱关键词
STARTUP_KEYWORDS = [
    'startup', '创业', 'saas', '订阅', 'subscription',
    'monetize', '变现', 'revenue', '收入',
    'side-project', '副业', 'indie', '独立开发',
    'landing-page', '落地页', 'marketing', '营销',
    'product', '产品', 'mvp', '最小可行',
]


class NewsFetcher:
    """信息抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, application/rss+xml, */*',
        })
    
    def fetch_all(self) -> List[ToolItem]:
        """获取所有信息"""
        items = []
        
        # 1. 获取国内AI工具 (静态列表 + 动态更新检查)
        logger.info("获取国内AI工具列表...")
        items.extend(self._get_cn_ai_tools())
        
        # 2. 获取GitHub热门项目
        logger.info("获取GitHub热门项目...")
        items.extend(self._fetch_github_trending())
        
        # 3. 获取RSS资讯
        logger.info("获取RSS资讯...")
        items.extend(self._fetch_rss_feeds())
        
        # 4. 获取V2EX热门
        logger.info("获取V2EX热门...")
        items.extend(self._fetch_v2ex_hot())
        
        return items
    
    def _get_cn_ai_tools(self) -> List[ToolItem]:
        """获取国内AI工具列表 (可扩展为动态检查更新)"""
        items = []
        for tool in CN_AI_TOOLS:
            item = ToolItem(
                name=tool["name"],
                category="ai_tool",
                source="国内AI工具",
                link=tool["url"],
                description=tool["desc"],
                tags=tool.get("tags", []),
                quality_score=7  # 基础分
            )
            items.append(item)
        return items
    
    def _fetch_github_trending(self) -> List[ToolItem]:
        """获取GitHub Trending"""
        items = []
        
        try:
            # 使用RSSHub的GitHub Trending
            url = "https://rsshub.app/github/trending/daily/any?limit=30"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:30]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
                    # 提取项目名
                    name_match = re.search(r'([^/]+/[^/\s]+)', title)
                    name = name_match.group(1) if name_match else title
                    
                    # 提取stars
                    stars = 0
                    star_match = re.search(r'(\d+,?\d*)\s*stars?', summary, re.I)
                    if star_match:
                        stars = int(star_match.group(1).replace(',', ''))
                    
                    # 提取描述
                    desc = re.sub(r'<[^>]+>', '', summary)
                    desc = desc[:200].strip()
                    
                    item = ToolItem(
                        name=name,
                        category="github_project",
                        source="GitHub Trending",
                        link=link,
                        description=desc,
                        stars=stars,
                    )
                    items.append(item)
                    
        except Exception as e:
            logger.error(f"GitHub Trending 获取失败: {e}")
        
        return items
    
    def _fetch_rss_feeds(self) -> List[ToolItem]:
        """获取RSS资讯"""
        items = []
        
        for feed_url, source_name, feed_type in RSS_FEEDS:
            if feed_type == "json":
                continue  # V2EX单独处理
            
            try:
                logger.info(f"获取RSS: {source_name}")
                response = self.session.get(feed_url, timeout=30)
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    
                    for entry in feed.entries[:15]:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        summary = entry.get('summary', '') or entry.get('description', '')
                        summary = re.sub(r'<[^>]+>', '', summary)[:200]
                        
                        # 根据来源判断分类
                        if 'github' in feed_url.lower():
                            category = "github_project"
                        elif 'product' in feed_url.lower():
                            category = "startup"
                        else:
                            category = "automation"
                        
                        item = ToolItem(
                            name=title[:50],
                            category=category,
                            source=source_name,
                            link=link,
                            description=summary,
                        )
                        items.append(item)
                        
            except Exception as e:
                logger.error(f"RSS {source_name} 获取失败: {e}")
        
        return items
    
    def _fetch_v2ex_hot(self) -> List[ToolItem]:
        """获取V2EX热门话题"""
        items = []
        
        try:
            url = "https://www.v2ex.com/api/topics/hot.json"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                for topic in data[:10]:
                    title = topic.get('title', '')
                    link = topic.get('url', '')
                    content = topic.get('content', '')[:200]
                    node = topic.get('node', {}).get('name', '')
                    
                    item = ToolItem(
                        name=title,
                        category="automation",
                        source=f"V2EX/{node}",
                        link=link,
                        description=content,
                    )
                    items.append(item)
                    
        except Exception as e:
            logger.error(f"V2EX获取失败: {e}")
        
        return items
    
    def calculate_value_score(self, item: ToolItem) -> int:
        """
        计算价值评分 (0-10)
        重点: 对普通人/创业者的实用价值
        """
        score = 5  # 基础分
        text = f"{item.name} {item.description}".lower()
        
        # 自动化/实用工具 +3分
        for kw in AUTOMATION_KEYWORDS:
            if kw.lower() in text:
                score += 3
                break
        
        # AI相关 +2分
        for kw in AI_KEYWORDS:
            if kw.lower() in text:
                score += 2
                break
        
        # 创业/赚钱 +2分
        for kw in STARTUP_KEYWORDS:
            if kw.lower() in text:
                score += 2
                break
        
        # GitHub stars加分
        if item.stars > 10000:
            score += 2
        elif item.stars > 5000:
            score += 1
        
        # 国内AI工具加分
        if item.category == "ai_tool":
            score += 1
        
        # 过滤低价值内容
        low_value = ['广告', '推广', '优惠', '促销', '抽奖']
        for kw in low_value:
            if kw in text:
                score -= 2
                break
        
        return max(0, min(10, score))
    
    def generate_practical_use(self, item: ToolItem) -> str:
        """生成实际用途说明"""
        text = f"{item.name} {item.description}".lower()
        
        # 根据关键词给出建议
        if any(kw in text for kw in ['cli', 'command', '终端', '命令']):
            return "命令行工具，可提升开发效率"
        elif any(kw in text for kw in ['bot', '机器人', 'chatbot']):
            return "可自动化处理消息/任务，节省人力"
        elif any(kw in text for kw in ['crawler', '爬虫', 'scraper']):
            return "数据采集工具，可用于信息监控"
        elif any(kw in text for kw in ['automation', '自动化', 'workflow']):
            return "自动化工具，可替代重复劳动"
        elif any(kw in text for kw in ['api', 'sdk']):
            return "开发接口，可集成到自己的项目"
        elif any(kw in text for kw in ['notion', 'obsidian', '笔记']):
            return "知识管理工具，提升信息组织效率"
        elif any(kw in text for kw in ['download', '下载']):
            return "下载工具，可能节省会员费用"
        elif any(kw in text for kw in ['backup', '同步', 'sync']):
            return "数据备份工具，防止数据丢失"
        elif any(kw in text for kw in ['大模型', 'llm', 'gpt', 'ai']):
            return "AI能力，可用于提升工作效率或开发AI应用"
        elif any(kw in text for kw in ['saas', '订阅', '变现']):
            return "商业模式参考，可学习变现思路"
        elif any(kw in text for kw in ['template', '模板', 'starter']):
            return "项目模板，可快速启动新项目"
        
        return "值得关注，可能有实用价值"
    
    def filter_and_rank(self, items: List[ToolItem], top_n: int = 15) -> List[ToolItem]:
        """筛选并排序"""
        # 计算分数
        for item in items:
            item.quality_score = self.calculate_value_score(item)
            item.practical_use = self.generate_practical_use(item)
        
        # 过滤低分
        filtered = [i for i in items if i.quality_score >= 6]
        logger.info(f"筛选: {len(items)} -> {len(filtered)} 条 (>=6分)")
        
        # 按分数排序
        sorted_items = sorted(filtered, key=lambda x: x.quality_score, reverse=True)
        
        # 去重
        seen = set()
        unique = []
        for item in sorted_items:
            key = re.sub(r'\s+', '', item.name.lower())
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique[:top_n]


if __name__ == '__main__':
    # 测试
    fetcher = NewsFetcher()
    all_items = fetcher.fetch_all()
    top_items = fetcher.filter_and_rank(all_items, 20)
    
    print(f"\n今日精选 ({len(top_items)}条):\n")
    
    for i, item in enumerate(top_items, 1):
        print(f"{i}. [{item.quality_score}分] {item.name}")
        print(f"   分类: {item.category} | 来源: {item.source}")
        print(f"   用途: {item.practical_use}")
        print(f"   链接: {item.link}")
        print()
