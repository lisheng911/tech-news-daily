#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server酱Turbo推送模块
"""

import os
import requests
from typing import List
import logging
from news_fetcher import NewsItem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ServerChanPusher:
    """Server酱Turbo 推送器"""
    
    def __init__(self):
        self.sendkey = os.getenv('SERVERCHAN_SENDKEY', '')
        if not self.sendkey:
            raise ValueError("SERVERCHAN_SENDKEY 环境变量未设置")
        
        # Server酱Turbo API
        self.api_url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
    
    def format_news_message(self, news_list: List[NewsItem]) -> tuple:
        """格式化新闻为推送消息"""
        if not news_list:
            return "今日高价值科技信息", "## 📭 今日无高价值科技信息\n\n> 经过筛选，今日暂无符合标准的高价值科技新闻。\n\n---\n📱 *高价值信息筛选系统*"
        
        # 标题
        title = f"💎 高价值信息精选 ({len(news_list)}条)"
        
        # Markdown 内容
        content_lines = []
        content_lines.append("## 🔥 高价值科技信息\n")
        content_lines.append("> 过去24小时最有价值的科技动态\n")
        
        for i, news in enumerate(news_list, 1):
            score_display = "⭐" * min(news.quality_score // 2, 5)  # 星级显示
            content_lines.append(f"\n### {i}. {news.one_line_summary}\n")
            content_lines.append(f"> 价值评分: {score_display} ({news.quality_score}/10)\n\n")
            content_lines.append(f"**📰 标题**: {news.title}\n")
            content_lines.append(f"**📌 来源**: {news.source}\n")
            content_lines.append(f"**🔗 链接**: [点击查看]({news.link})\n")
            
            if news.summary:
                short_summary = news.summary[:120] + "..." if len(news.summary) > 120 else news.summary
                content_lines.append(f"\n**📝 摘要**: {short_summary}\n")
            
            # 实际意义 (核心价值)
            if news.practical_value:
                content_lines.append(f"\n**💡 实际意义**: {news.practical_value}\n")
            
            content_lines.append("\n---")
        
        # 添加底部信息
        content_lines.append("\n\n📱 *由高价值信息筛选系统生成*\n")
        content_lines.append("🎯 *只筛选真正有价值的信息*\n")
        
        content = "\n".join(content_lines)
        return title, content
    
    def push(self, news_list: List[NewsItem]) -> bool:
        """推送新闻到微信"""
        title, content = self.format_news_message(news_list)
        
        payload = {
            'title': title,
            'desp': content
        }
        
        try:
            logger.info("正在推送消息到微信...")
            response = requests.post(self.api_url, data=payload, timeout=30)
            result = response.json()
            
            if result.get('code') == 0:
                logger.info("推送成功!")
                return True
            else:
                logger.error(f"推送失败: {result.get('message', '未知错误')}")
                return False
        
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求错误: {e}")
            return False
        except Exception as e:
            logger.error(f"推送异常: {e}")
            return False


if __name__ == '__main__':
    # 测试推送
    test_news = [
        NewsItem(
            title="OpenAI发布GPT-5，性能大幅提升",
            source="TechCrunch",
            link="https://example.com/news1",
            summary="OpenAI今天发布了最新的GPT-5模型，在多项基准测试中取得了突破性进展。",
            one_line_summary="🤖 AI: OpenAI发布GPT-5，性能大幅提升",
            practical_value="大模型能力升级，可关注相关API调用成本变化，探索新的应用场景",
            quality_score=8
        )
    ]
    
    pusher = ServerChanPusher()
    pusher.push(test_news)
