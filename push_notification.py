#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server酱推送模块 - 增强版

特性：
- 决策面板摘要
- 内容截断（推送是入口，不是本体）
- 失败告警
"""

import os
import requests
from typing import Dict, List
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ServerChanPusher:
    """Server酱推送器"""
    
    # 推送内容截断配置
    MAX_TITLE_LEN = 40
    MAX_DESC_LEN = 50
    MAX_ITEMS_PER_CATEGORY = 5  # 每分类最多显示条数
    
    def __init__(self):
        self.sendkey = os.getenv('SERVERCHAN_SENDKEY', '')
        if not self.sendkey:
            raise ValueError("SERVERCHAN_SENDKEY 环境变量未设置")
        self.api_url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
    
    def format_message(self, categorized: Dict) -> tuple:
        """格式化推送消息"""
        today = datetime.now().strftime('%Y-%m-%d')
        weekday = ['一', '二', '三', '四', '五', '六', '日'][datetime.now().weekday()]
        
        stats = categorized.get("统计面板", {})
        category_counts = stats.get("各分类数", {})
        
        # 计算总数
        total_new = sum(category_counts.values())
        
        # 决策面板状态标签
        if total_new >= 10:
            status_label = "✅ 丰富"
        elif total_new >= 5:
            status_label = "📊 正常"
        elif total_new > 0:
            status_label = "⚠️ 较少"
        else:
            status_label = "🆘 兜底"
        
        title = f"[{status_label}] 每日精选 ({total_new}条)"
        
        lines = []
        lines.append(f"## 📅 {today} 星期{weekday}\n")
        
        # 决策面板 - 核心统计
        lines.append("### 📊 决策面板\n")
        lines.append(f"| 分类 | 数量 |")
        lines.append(f"|:---:|:---:|")
        
        categories = ["GitHub热门", "自动化脚本", "AI新功能", "新模型咨询", "好用的工具"]
        for cat in categories:
            count = category_counts.get(cat, 0)
            lines.append(f"| {cat} | **{count}** |")
        
        lines.append(f"|:---:|:---:|")
        lines.append(f"| 📥 抓取总数 | {stats.get('抓取总数', 0)} |")
        lines.append(f"| ⏰ 过期过滤 | {stats.get('过滤过期', 0)} |")
        lines.append(f"| 🚫 黑名单过滤 | {stats.get('过滤黑名单', 0)} |")
        lines.append(f"| 🚫 压制过滤 | {stats.get('过滤压制', 0)} |")
        lines.append("\n")
        
        # 各分类内容
        for cat in categories:
            items = categorized.get(cat, [])
            if items:
                lines.append(f"### {self._get_category_emoji(cat)} {cat}\n")
                self._format_items(lines, items[:self.MAX_ITEMS_PER_CATEGORY])
        
        lines.append("---\n")
        lines.append("### 💡 说明\n")
        lines.append("- 每个分类保证有内容（动态+保底）")
        lines.append("- 点击链接查看完整内容\n")
        lines.append("\n📱 *每日精选推送*")
        
        return title, "\n".join(lines)
    
    def _get_category_emoji(self, cat: str) -> str:
        """获取分类图标"""
        emojis = {
            "GitHub热门": "🔥",
            "自动化脚本": "🤖",
            "AI新功能": "🧠",
            "新模型咨询": "🆕",
            "好用的工具": "🛠️",
        }
        return emojis.get(cat, "📌")
    
    def _format_items(self, lines: List, items: List):
        """格式化条目 - 截断版"""
        for i, item in enumerate(items, 1):
            # 标题截断
            title = item.title[:self.MAX_TITLE_LEN]
            if len(item.title) > self.MAX_TITLE_LEN:
                title += "..."
            
            stars = f"⭐{item.stars:,} " if item.stars > 0 else ""
            status = f"[{item.status}]" if item.status not in ('new', 'static') else ""
            
            lines.append(f"**{i}. {title}** {stars}{status}")
            
            # 描述截断
            if item.description:
                desc = item.description[:self.MAX_DESC_LEN]
                lines.append(f"   > {desc}")
            
            # 链接
            lines.append(f"   🔗 [查看详情]({item.link})\n")
    
    def push(self, categorized: Dict) -> bool:
        """推送消息"""
        title, content = self.format_message(categorized)
        
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
    
    def push_alert(self, step: str, error_msg: str) -> bool:
        """失败告警推送"""
        title = f"[❌ 失败告警] 每日精选执行失败"
        
        content = f"""## ⚠️ 执行失败告警

**失败步骤**: {step}

**错误摘要**:
```
{error_msg[:500]}
```

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
*请检查 GitHub Actions 日志获取详细信息*
"""
        
        try:
            logger.info("发送失败告警...")
            response = requests.post(
                self.api_url,
                data={'title': title, 'desp': content},
                timeout=30
            )
            result = response.json()
            return result.get('code') == 0
        except Exception as e:
            logger.error(f"告警推送失败: {e}")
            return False
