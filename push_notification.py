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
            return "今日科技新闻", "今日暂无高质量科技新闻"
        
        # 标题
        title = f"📡 今日科技新闻精选 ({len(news_list)}条)"
        
        # Markdown 内容
        content_lines = []
        content_lines.append("## 🔥 科技要闻精选\n")
        content_lines.append("> 过去24小时最值得关注的科技新闻\n")
        
        for i, news in enumerate(news_list, 1):
            content_lines.append(f"\n### {i}. {news.one_line_summary}\n")
            content_lines.append(f"**标题**: {news.title}\n")
            content_lines.append(f"**来源**: {news.source}\n")
            content_lines.append(f"**链接**: [点击查看]({news.link})\n")
            
            if news.summary:
                short_summary = news.summary[:150] + "..." if len(news.summary) > 150 else news.summary
                content_lines.append(f"\n**摘要**: {short_summary}\n")
            
            content_lines.append("---")
        
        # 添加底部信息
        content_lines.append("\n---\n")
        content_lines.append("📱 *由自动新闻推送系统生成*\n")
        content_lines.append("⏰ *每日早8点(东京时间)推送*\n")
        
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
            one_line_summary="🤖 AI: OpenAI发布GPT-5，性能大幅提升"
        )
    ]
    
    pusher = ServerChanPusher()
    pusher.push(test_news)