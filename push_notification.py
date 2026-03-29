#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server酱Turbo推送模块 - 每日精选工具推送
"""

import os
import requests
from typing import List
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ServerChanPusher:
    """Server酱Turbo 推送器"""
    
    def __init__(self):
        self.sendkey = os.getenv('SERVERCHAN_SENDKEY', '')
        if not self.sendkey:
            raise ValueError("SERVERCHAN_SENDKEY 环境变量未设置")
        
        self.api_url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
    
    def format_tools_message(self, items: List, total_count: int) -> tuple:
        """格式化工具推送消息"""
        today = datetime.now().strftime('%Y-%m-%d')
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        weekday = datetime.now().weekday()
        
        title = f"每日精选 ({len(items)}条高价值内容)"
        
        content_lines = []
        content_lines.append(f"## 🎯 每日精选推送\n")
        content_lines.append(f"> **日期**: {today} 星期{weekday_names[weekday]}")
        content_lines.append(f"> **筛选**: 从 {total_count} 条中精选 {len(items)} 条\n")
        content_lines.append("---\n")
        
        # 1. 国内AI工具推荐 (取前6个)
        ai_items = [i for i in items if i.category == 'ai_tool'][:6]
        if ai_items:
            content_lines.append("### 🤖 国内AI工具\n")
            for i, item in enumerate(ai_items, 1):
                content_lines.append(f"**{i}. {item.name}**")
                content_lines.append(f"```\n{item.description}\n```")
                if item.tags:
                    tags_str = ' '.join(['#' + t for t in item.tags[:3]])
                    content_lines.append(f"{tags_str}")
                content_lines.append(f"🔗 [访问链接]({item.link})\n")
            content_lines.append("---\n")
        
        # 2. GitHub热门项目 (取前8个)
        github_items = [i for i in items if i.category == 'github_project'][:8]
        if github_items:
            content_lines.append("### 📦 GitHub热门项目\n")
            for i, item in enumerate(github_items, 1):
                star_str = f"⭐{item.stars:,}" if item.stars > 0 else ""
                content_lines.append(f"**{i}. {item.name}** {star_str}")
                content_lines.append(f"💡 {item.practical_use}")
                content_lines.append(f"🔗 [查看项目]({item.link})\n")
            content_lines.append("---\n")
        
        # 3. 开源项目推荐
        open_items = [i for i in items if i.category == 'open_source'][:4]
        if open_items:
            content_lines.append("### 🌟 开源推荐\n")
            for i, item in enumerate(open_items, 1):
                content_lines.append(f"**{i}. {item.name}**")
                content_lines.append(f"💡 {item.practical_use}")
                content_lines.append(f"🔗 [查看详情]({item.link})\n")
            content_lines.append("---\n")
        
        # 4. 其他精选
        other_items = [i for i in items if i.category in ['automation', 'startup']][:4]
        if other_items:
            content_lines.append("### 📰 精选资讯\n")
            for i, item in enumerate(other_items, 1):
                content_lines.append(f"**{i}. {item.name}**")
                content_lines.append(f"📚 {item.source}")
                content_lines.append(f"💡 {item.practical_use}")
                content_lines.append(f"🔗 [查看详情]({item.link})\n")
            content_lines.append("---\n")
        
        # 底部提示
        content_lines.append("\n### 💡 今日建议")
        content_lines.append("- 🤖 AI工具大部分有免费额度，可以先试用")
        content_lines.append("- 📦 GitHub项目可以直接使用或学习源码")
        content_lines.append("- 🔧 自动化工具可以减少重复劳动")
        content_lines.append("- 💰 关注创业项目，学习变现思路\n")
        
        content_lines.append("\n---\n📱 *每日精选推送系统*")
        
        content = "\n".join(content_lines)
        return title, content
    
    def push_tools(self, items: List, total_count: int) -> bool:
        """推送工具列表到微信"""
        if not items:
            logger.warning("无内容可推送")
            return False
        
        title, content = self.format_tools_message(items, total_count)
        
        payload = {
            'title': title,
            'desp': content
        }
        
        try:
            logger.info("正在推送到微信...")
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
