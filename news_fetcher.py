#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高价值信息筛选模块
优先使用 NewsData.io API，失败时使用 RSS 备选
"""

import os
import re
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    source: str
    link: str
    summary: str
    published: Optional[datetime] = None
    quality_score: int = 0
    one_line_summary: str = ""
    practical_value: str = ""  # 实际意义


# ============ 高价值信息筛选关键词 ============

# AI相关关键词 (大模型、工具、应用) +3分
AI_KEYWORDS = [
    'ai', 'artificial intelligence', '人工智能', 'gpt', 'chatgpt', 'openai',
    'llm', '大模型', 'deepseek', 'claude', 'gemini', 'copilot',
    'machine learning', 'deep learning', '机器学习', '深度学习',
    'generative ai', '生成式ai', 'aigc', 'midjourney', 'stable diffusion',
    'agent', '智能体', 'prompt', '提示词', 'ai工具'
]

# 芯片相关关键词 (NVIDIA、算力、半导体) +3分
CHIP_KEYWORDS = [
    'nvidia', '英伟达', 'gpu', '芯片', 'chip', 'semiconductor', '半导体',
    '算力', 'computing power', 'tsmc', '台积电', 'intel', 'amd',
    'cuda', 'h100', 'a100', 'h200', 'blackwell', '数据中心',
    'datacenter', '训练', 'inference', '推理'
]

# 互联网商业相关关键词 (融资、产品发布) +2分
BUSINESS_KEYWORDS = [
    '融资', 'funding', 'fundraising', 'ipo', '上市',
    '收购', 'acquire', 'acquisition', 'merger', '合并',
    '产品发布', 'launch', 'release', '发布', '推出',
    'startup', '创业', '独角兽', 'unicorn',
    '融资轮', 'series a', 'series b', '种子轮', '天使轮'
]

# 赚钱机会相关关键词 (副业、工具变现) +3分
MONEY_KEYWORDS = [
    '副业', 'side hustle', '变现', 'monetize', '赚钱',
    '被动收入', 'passive income', '自由职业', 'freelance',
    '远程工作', 'remote work', '数字游民', 'digital nomad',
    '工具变现', 'api付费', '订阅制', 'subscription', 'saas',
    '知识付费', '课程', 'course', '付费专栏'
]

# 大公司关键词 +2分
BIG_COMPANY_KEYWORDS = [
    'openai', 'google', 'google deepmind', 'microsoft', 'apple',
    'nvidia', 'meta', 'amazon', 'tesla', 'spacex',
    'anthropic', '字节跳动', 'bytedance', '腾讯', 'tencent',
    '阿里巴巴', 'alibaba', '百度', 'baidu'
]

# 普通无价值关键词 -3分
LOW_VALUE_KEYWORDS = [
    '广告', '推广', '优惠', '折扣', '促销', 'advertisement', 'promo',
    '标题党', '震惊', '必看', '速看', '疯传', '刷屏',
    '转发', '抽奖', '福利', '免费领取', '限时',
    '点击', '优惠码', '优惠券', '抢购', '秒杀'
]


class NewsFetcher:
    """新闻抓取器"""
    
    def __init__(self):
        self.newsdata_api_key = os.getenv('NEWSDATA_API_KEY', '')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_all(self) -> List[NewsItem]:
        """获取所有新闻，优先API，失败则使用RSS"""
        news_list = []
        
        # 尝试 NewsData.io API
        if self.newsdata_api_key:
            logger.info("尝试使用 NewsData.io API...")
            news_list = self._fetch_from_newsdata()
            if news_list:
                logger.info(f"NewsData.io API 获取到 {len(news_list)} 条新闻")
                return news_list
        
        # 备选: 使用 RSS 源
        logger.info("使用 RSS 备选方案...")
        news_list = self._fetch_from_rss()
        logger.info(f"RSS 获取到 {len(news_list)} 条新闻")
        
        return news_list
    
    def _fetch_from_newsdata(self) -> List[NewsItem]:
        """从 NewsData.io API 获取新闻"""
        news_list = []
        
        try:
            url = "https://newsdata.io/api/1/news"
            params = {
                'apikey': self.newsdata_api_key,
                'q': 'technology OR AI OR chip OR startup OR funding',
                'category': 'technology',
                'language': 'en,zh',
                'size': 50
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success' and data.get('results'):
                for item in data['results']:
                    published = None
                    if item.get('pubDate'):
                        try:
                            published = datetime.fromisoformat(item['pubDate'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    news = NewsItem(
                        title=item.get('title', ''),
                        source=item.get('source_id', 'Unknown'),
                        link=item.get('link', ''),
                        summary=item.get('description', '') or (item.get('content', '')[:300] if item.get('content') else ''),
                        published=published
                    )
                    news_list.append(news)
        
        except Exception as e:
            logger.error(f"NewsData.io API 错误: {e}")
        
        return news_list
    
    def _fetch_from_rss(self) -> List[NewsItem]:
        """从 RSS 源获取新闻"""
        rss_feeds = [
            # 科技媒体 RSS
            ('https://feeds.arstechnica.com/arstechnica/technology-lab', 'Ars Technica'),
            ('https://www.theverge.com/rss/index.xml', 'The Verge'),
            ('https://techcrunch.com/feed/', 'TechCrunch'),
            ('https://www.wired.com/feed/rss', 'Wired'),
            ('https://feeds.bbci.co.uk/news/technology/rss.xml', 'BBC Tech'),
            ('https://www.36kr.com/feed', '36氪'),
            ('https://www.ifanr.com/feed', '爱范儿'),
            ('https://sspai.com/feed', '少数派'),
            ('https://hackernews.betacat.io/feed', 'Hacker News 中文'),
        ]
        
        news_list = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for feed_url, source_name in rss_feeds:
            try:
                logger.info(f"获取 RSS: {source_name}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:20]:
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6])
                        except:
                            pass
                    
                    # 过滤24小时内的新闻
                    if published and published.replace(tzinfo=None) < cutoff_time.replace(tzinfo=None):
                        continue
                    
                    summary = ''
                    if hasattr(entry, 'summary'):
                        summary = re.sub(r'<[^>]+>', '', entry.summary)
                        summary = summary[:300]
                    
                    news = NewsItem(
                        title=entry.get('title', ''),
                        source=source_name,
                        link=entry.get('link', ''),
                        summary=summary,
                        published=published
                    )
                    news_list.append(news)
            
            except Exception as e:
                logger.error(f"RSS {source_name} 错误: {e}")
                continue
        
        return news_list
    
    def calculate_value_score(self, news: NewsItem) -> int:
        """
        计算高价值分数 (0-10分制)
        只保留评分 >= 6 的新闻
        """
        score = 5  # 基础分5分
        
        text = f"{news.title} {news.summary}".lower()
        
        # AI相关关键词 +3分
        for keyword in AI_KEYWORDS:
            if keyword.lower() in text:
                score += 3
                break  # 只加一次
        
        # 芯片相关关键词 +3分
        for keyword in CHIP_KEYWORDS:
            if keyword.lower() in text:
                score += 3
                break
        
        # 赚钱机会关键词 +3分
        for keyword in MONEY_KEYWORDS:
            if keyword.lower() in text:
                score += 3
                break
        
        # 大公司关键词 +2分
        for keyword in BIG_COMPANY_KEYWORDS:
            if keyword.lower() in text:
                score += 2
                break
        
        # 商业/发布类信息 +2分
        for keyword in BUSINESS_KEYWORDS:
            if keyword.lower() in text:
                score += 2
                break
        
        # 普通无价值新闻 -3分
        for keyword in LOW_VALUE_KEYWORDS:
            if keyword.lower() in text:
                score -= 3
                break
        
        return max(0, min(10, score))
    
    def generate_one_line_summary(self, news: NewsItem) -> str:
        """生成一句话总结"""
        title = news.title
        text = f"{title} {news.summary}".lower()
        
        # 根据内容类型添加emoji前缀
        if any(k in text for k in AI_KEYWORDS[:10]):
            prefix = "🤖 AI"
        elif any(k in text for k in CHIP_KEYWORDS[:8]):
            prefix = "🔬 芯片"
        elif any(k in text for k in MONEY_KEYWORDS[:6]):
            prefix = "💰 赚钱"
        elif any(k in text for k in BUSINESS_KEYWORDS[:8]):
            prefix = "📊 商业"
        else:
            prefix = "📰 科技"
        
        # 截取标题前40字符
        short_title = title[:40] + "..." if len(title) > 40 else title
        return f"{prefix}: {short_title}"
    
    def generate_practical_value(self, news: NewsItem) -> str:
        """
        生成实际意义说明
        重点：说明对赚钱/趋势的影响
        """
        text = f"{news.title} {news.summary}".lower()
        insights = []
        
        # AI相关洞察
        if any(k in text for k in AI_KEYWORDS):
            if 'gpt' in text or 'chatgpt' in text or 'claude' in text or 'deepseek' in text:
                insights.append("大模型能力升级，可关注相关API调用成本变化")
            if 'agent' in text or '智能体' in text:
                insights.append("AI Agent赛道升温，可探索自动化工具开发机会")
            if 'prompt' in text or '提示词' in text:
                insights.append("提示词工程仍是热点，可考虑Prompt优化服务")
            if not insights:
                insights.append("AI领域持续演进，关注可落地的应用场景")
        
        # 芯片相关洞察
        if any(k in text for k in CHIP_KEYWORDS):
            if 'nvidia' in text or '英伟达' in text:
                insights.append("算力需求持续增长，关注GPU云服务价格趋势")
            if 'gpu' in text:
                insights.append("硬件升级带来AI应用成本下降红利")
            if not insights:
                insights.append("半导体供应链变化可能影响AI产品成本")
        
        # 赚钱机会相关洞察
        if any(k in text for k in MONEY_KEYWORDS):
            if '副业' in text or 'side' in text:
                insights.append("副业方法论更新，可参考新模式")
            if '变现' in text or 'monetize' in text:
                insights.append("工具变现新思路，值得研究借鉴")
            if '订阅' in text or 'subscription' in text:
                insights.append("订阅模式验证成功，可考虑复制到垂直领域")
            if not insights:
                insights.append("赚钱机会值得关注，结合自身技能评估可行性")
        
        # 商业相关洞察
        if any(k in text for k in BUSINESS_KEYWORDS):
            if '融资' in text or 'funding' in text:
                insights.append("资本看好该赛道，可关注同类产品机会")
            if '发布' in text or 'launch' in text:
                insights.append("新品发布意味着市场验证，可学习产品设计思路")
            if '收购' in text or 'acquire' in text:
                insights.append("并购活跃，该领域可能存在整合红利")
            if not insights:
                insights.append("商业动向值得关注，把握行业趋势")
        
        # 默认洞察
        if not insights:
            insights.append("关注行业动态，寻找差异化机会")
        
        return insights[0] if insights else "关注发展趋势，把握潜在机会"
    
    def filter_and_rank(self, news_list: List[NewsItem], top_n: int = 10) -> List[NewsItem]:
        """
        筛选并排序新闻
        只保留评分 >= 6 的高价值新闻
        """
        # 计算价值分数
        for news in news_list:
            news.quality_score = self.calculate_value_score(news)
            news.one_line_summary = self.generate_one_line_summary(news)
            news.practical_value = self.generate_practical_value(news)
        
        # 过滤：只保留评分 >= 6 的新闻
        filtered = [n for n in news_list if n.quality_score >= 6]
        logger.info(f"评分筛选: {len(news_list)} -> {len(filtered)} 条 (>=6分)")
        
        # 按分数排序
        sorted_news = sorted(filtered, key=lambda x: x.quality_score, reverse=True)
        
        # 去重 (相同标题只保留一个)
        seen_titles = set()
        unique_news = []
        for news in sorted_news:
            title_key = re.sub(r'\s+', '', news.title.lower())
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_news.append(news)
        
        return unique_news[:top_n]


if __name__ == '__main__':
    # 测试
    fetcher = NewsFetcher()
    all_news = fetcher.fetch_all()
    top_news = fetcher.filter_and_rank(all_news, 10)
    
    if not top_news:
        print("\n今日无高价值科技信息")
    else:
        for i, news in enumerate(top_news, 1):
            print(f"\n{i}. [{news.quality_score}分] {news.title}")
            print(f"   来源: {news.source}")
            print(f"   一句话: {news.one_line_summary}")
            print(f"   实际意义: {news.practical_value}")