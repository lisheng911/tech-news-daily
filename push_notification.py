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
        
        # 分类统计
        ai_count = len([i for i in items if i.category == 'ai_tool'])
        github_count = len([i for i in items if i.category == 'github_project'])
        
        content_lines = []
        content_lines.append(f"## 🎯 每日精选推送\n")
        content_lines.append(f"> **日期**: {today} 星期{weekday_names[weekday]}")
        content_lines.append(f"> **筛选**: 从 {total_count} 条中精选 {len(items)} 条\n")
        
        # 分类展示
        content_lines.append("---\n")
        
        # 1. 国内AI工具推荐
        ai_items = [i for i in items if i.category == 'ai_tool'][:5]
        if ai_items:
            content_lines.append("### 🤖 国内AI工具\n")
            for i, item in enumerate(ai_items, 1):
                content_lines.append(f"**{i}. {item.name}**")
                content_lines.append(f"- 描述: {item.description}")
                if item.tags:
                    content_lines.append(f"- 标签: {' '.join(['`' + t + '`' for t in item.tags[:3]])}")
                content_lines.append(f"- 链接: [点击访问]({item.link})\n")
            content_lines.append("---\n")
        
        # 2. GitHub热门项目
        github_items = [i for i in items if i.category == 'github_project'][:6]
        if github_items:
            content_lines.append("### 📦 GitHub热门项目\n")
            for i, item in enumerate(github_items, 1):
                star_str = f" ⭐{item.stars:,}" if item.stars > 0 else ""
                content_lines.append(f"**{i}. {item.name}**{star_str}")
                content_lines.append(f"- 用途: {item.practical_use}")
                content_lines.append(f"- 描述: {item.description[:80]}...")
                content_lines.append(f"- 链接: [查看项目]({item.link})\n")
            content_lines.append("---\n")
        
        # 3. 其他精选内容
        other_items = [i for i in items if i.category not in ['ai_tool', 'github_project']][:4]
        if other_items:
            content_lines.append("### 📰 其他精选\n")
            for i, item in enumerate(other_items, 1):
                content_lines.append(f"**{i}. {item.name}**")
                content_lines.append(f"- 来源: {item.source}")
                content_lines.append(f"- 用途: {item.practical_use}")
                content_lines.append(f"- 链接: [查看详情]({item.link})\n")
            content_lines.append("---\n")
        
        # 底部提示
        content_lines.append("\n### 💡 使用建议")
        content_lines.append("- AI工具可提升工作效率，大部分有免费额度")
        content_lines.append("- GitHub项目可直接使用或学习源码")
        content_lines.append("- 关注自动化工具，减少重复劳动\n")
        
        content_lines.append("\n📱 *每日精选推送系统*")
        
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


if __name__ == '__main__':
    # 测试
    from dataclasses import dataclass, field
    from typing import List
    
    @dataclass
    class TestItem:
        name: str
        category: str
        source: str
        link: str
        description: str
        stars: int = 0
        quality_score: int = 0
        practical_use: str = ""
        tags: List[str] = field(default_factory=list)
    
    test_items = [
        TestItem(
            name="DeepSeek",
            category="ai_tool",
            source="国内AI工具",
            link="https://www.deepseek.com/",
            description="国产大模型，API便宜，编程能力强",
            tags=["大模型", "API", "编程"],
            quality_score=8,
            practical_use="AI能力，可用于提升工作效率或开发AI应用"
        ),
        TestItem(
            name="microsoft/semantic-kernel",
            category="github_project",
            source="GitHub Trending",
            link="https://github.com/microsoft/semantic-kernel",
            description="Integrate cutting-edge LLM technology into your apps",
            stars=21000,
            quality_score=8,
            practical_use="开发接口，可集成到自己的项目"
        ),
    ]
    
    pusher = ServerChanPusher()
    pusher.push_tools(test_items, 100)