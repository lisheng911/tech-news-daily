#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server酱推送模块 - 按分类推送
"""

import os
import requests
from typing import List, Dict
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ServerChanPusher:
    """Server酱推送器"""
    
    def __init__(self):
        self.sendkey = os.getenv('SERVERCHAN_SENDKEY', '')
        if not self.sendkey:
            raise ValueError("SERVERCHAN_SENDKEY 环境变量未设置")
        self.api_url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
    
    def format_message(self, categorized: Dict, total_count: int) -> tuple:
        """格式化推送消息"""
        today = datetime.now().strftime('%Y-%m-%d')
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        weekday = datetime.now().weekday()
        
        # 计算精选数量
        selected_count = sum(len(items) for items in categorized.values())
        title = f"每日精选 ({selected_count}条)"
        
        lines = []
        lines.append(f"## 📅 {today} 星期{weekday_names[weekday]}\n")
        lines.append(f"> 从 {total_count} 条中精选 {selected_count} 条\n")
        lines.append("---\n")
        
        # 1. 国内AI工具
        items = categorized.get("国内AI工具", [])
        if items:
            lines.append("### 🤖 国内AI工具\n")
            for i, item in enumerate(items, 1):
                lines.append(f"**{i}. {item.name}**")
                lines.append(f"> {item.description}")
                lines.append(f"🔗 [访问]({item.link})\n")
            lines.append("---\n")
        
        # 2. AI动态
        items = categorized.get("AI动态", [])
        if items:
            lines.append("### 📢 AI动态\n")
            for i, item in enumerate(items, 1):
                lines.append(f"**{i}. {item.name}**")
                lines.append(f"> 来源: {item.source}")
                lines.append(f"🔗 [查看]({item.link})\n")
            lines.append("---\n")
        
        # 3. 自动化脚本
        items = categorized.get("自动化脚本", [])
        if items:
            lines.append("### ⚡ 自动化脚本\n")
            for i, item in enumerate(items, 1):
                stars = f"⭐{item.stars:,} " if item.stars > 0 else ""
                lines.append(f"**{i}. {item.name}**")
                lines.append(f"> {stars}{item.practical_use}")
                lines.append(f"🔗 [查看]({item.link})\n")
            lines.append("---\n")
        
        # 4. GitHub热门
        items = categorized.get("GitHub热门", [])
        if items:
            lines.append("### 🔥 GitHub热门\n")
            for i, item in enumerate(items, 1):
                stars = f"⭐{item.stars:,} " if item.stars > 0 else ""
                lines.append(f"**{i}. {item.name}**")
                lines.append(f"> {stars}{item.practical_use}")
                lines.append(f"🔗 [查看]({item.link})\n")
            lines.append("---\n")
        
        # 5. 科技资讯
        items = categorized.get("科技资讯", [])
        if items:
            lines.append("### 📰 科技资讯\n")
            for i, item in enumerate(items, 1):
                lines.append(f"**{i}. {item.name}**")
                lines.append(f"> 来源: {item.source}")
                lines.append(f"🔗 [查看]({item.link})\n")
            lines.append("---\n")
        
        # 底部
        lines.append("\n### 💡 使用建议")
        lines.append("- 🤖 国内AI工具大多免费，建议试用")
        lines.append("- ⚡ 自动化脚本可节省重复劳动")
        lines.append("- 🔥 GitHub热门项目可学习或直接使用")
        lines.append("- 📢 AI动态关注最新能力变化\n")
        
        lines.append("\n📱 *每日精选推送*")
        
        return title, "\n".join(lines)
    
    def push(self, categorized: Dict, total_count: int) -> bool:
        """推送"""
        title, content = self.format_message(categorized, total_count)
        
        try:
            logger.info("正在推送...")
            response = requests.post(
                self.api_url,
                data={'title': title, 'desp': content},
                timeout=30
            )
            result = response.json()
            
            if result.get('code') == 0:
                logger.info("✅ 推送成功!")
                return True
            else:
                logger.error(f"❌ 推送失败: {result.get('message')}")
                return False
        except Exception as e:
            logger.error(f"推送异常: {e}")
            return False