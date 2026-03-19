#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科技新闻抓取模块
优先使用 NewsData.io API，失败时使用 RSS 备选
"""

import os
import re
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
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

# 关键词权重 - AI、芯片、互联网商业优先
KEYWORD_WEIGHTS = {
    # AI 相关 (权重 10)
    'ai': 10, 'artificial intelligence': 10, '人工智能': 10, 'gpt': 10, 'chatgpt': 10,
    'openai': 10, 'llm': 10, '大模型': 10, 'deepseek': 10, 'claude': 10, 'gemini': 10,
    'machine learning': 9, 'deep learning': 9, '机器学习': 9, '深度学习': 9,
    'nvidia': 9, '英伟达': 9, 'gpu': 8, '芯片': 8, 'chip': 8, 'semiconductor': 8,
    
    # 互联网商业 (权重 7-8)
    'alibaba': 7, '阿里巴巴': 7, '腾讯': 7, 'tencent': 7, '字节跳动': 7, 'bytedance': 7,
    '美团': 7, 'meituan': 7, '京东': 6, 'jd.com': 6, '拼多多': 6, 'pinduoduo': 6,
    'apple': 6, 'google': 6, 'microsoft': 6, '亚马逊': 6, 'amazon': 6, 'meta': 6,
    'tesla': 7, '特斯拉': 7, 'spacex': 7, 'elon musk': 7,
    'startup': 6, '融资': 6, 'funding': 6, 'ipo': 7, '收购': 6, 'acquisition': 6,
    
    # 科技新闻通用 (权重 4-5)
    'tech': 5, '科技': 5, '创新': 4, 'innovation': 4,
    '5g': 5, 'quantum': 6, '量子': 6, 'blockchain': 5, '区块链': 5,
    'cybersecurity': 5, '网络安全': 5, 'data': 4, '数据': 4,
    'cloud': 5, '云': 5, 'software': 4, '软件': 4,
}

# 低质量关键词 (扣分)
LOW_QUALITY_KEYWORDS = [
    '广告', '推广', '优惠', '折扣', '促销', 'advertisement', 'promo',
    '标题党', '震惊', '必看', '速看', '疯传', '刷屏',
    '转发', '抽奖', '福利', '免费领取'
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
                'q': 'technology OR AI OR chip OR startup',
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
                        summary=item.get('description', '') or item.get('content', '')[:300] if item.get('content') else '',
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
    
    def calculate_quality_score(self, news: NewsItem) -> int:
        """计算新闻质量分数"""
        score = 50  # 基础分
        
        text = f"{news.title} {news.summary}".lower()
        
        # 正向关键词加分
        for keyword, weight in KEYWORD_WEIGHTS.items():
            if keyword in text:
                score += weight
        
        # 低质量关键词扣分
        for keyword in LOW_QUALITY_KEYWORDS:
            if keyword in text:
                score -= 20
        
        # 标题长度合理性
        if 20 <= len(news.title) <= 100:
            score += 5
        
        # 有摘要加分
        if news.summary and len(news.summary) > 50:
            score += 10
        
        # 有发布时间加分
        if news.published:
            score += 5
        
        return max(0, min(100, score))
    
    def generate_one_line_summary(self, news: NewsItem) -> str:
        """生成一句话总结"""
        title = news.title
        summary = news.summary
        
        # 提取关键信息
        combined = f"{title}。{summary}" if summary else title
        
        # 简单提取关键点
        if '发布' in combined or 'launch' in combined.lower():
            prefix = "🚀 发布: "
        elif '收购' in combined or 'acquire' in combined.lower() or 'merger' in combined.lower():
            prefix = "💼 收购: "
        elif '融资' in combined or 'fund' in combined.lower() or 'raise' in combined.lower():
            prefix = "💰 融资: "
        elif 'ai' in combined.lower() or '人工智能' in combined:
            prefix = "🤖 AI: "
        elif 'chip' in combined.lower() or '芯片' in combined:
            prefix = "🔬 芯片: "
        else:
            prefix = "📰 "
        
        # 截取标题前50字符作为简短总结
        short_title = title[:50] + "..." if len(title) > 50 else title
        return prefix + short_title
    
    def filter_and_rank(self, news_list: List[NewsItem], top_n: int = 10) -> List[NewsItem]:
        """筛选并排序新闻"""
        # 计算质量分数
        for news in news_list:
            news.quality_score = self.calculate_quality_score(news)
            news.one_line_summary = self.generate_one_line_summary(news)
        
        # 过滤低质量新闻
        filtered = [n for n in news_list if n.quality_score >= 40]
        
        # 按质量分数排序
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
    
    for i, news in enumerate(top_news, 1):
        print(f"\n{i}. [{news.quality_score}分] {news.title}")
        print(f"   来源: {news.source}")
        print(f"   一句话: {news.one_line_summary}")
