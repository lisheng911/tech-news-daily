#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server酱Turbo推送模块
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
        
        # Server酱Turbo API
        self.api_url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
    
    def format_schedule_message(self, courses: List, current_week: int, weekday: int) -> tuple:
        """格式化课表为推送消息"""
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not courses:
            title = f"📭 今日无课"
            content = f"""## 🎉 今日无课

**📅 日期**: {today}  
**📆 第 {current_week} 周 星期{weekday_names[weekday-1]}**

---

> 今天没有安排课程，可以自由安排时间！

📱 *每日课表推送系统*"""
            return title, content
        
        # 有课的情况
        title = f"📚 今日课表 ({len(courses)}节课)"
        
        content_lines = []
        content_lines.append(f"## 📅 今日课表\n")
        content_lines.append(f"> **日期**: {today}")
        content_lines.append(f"> **周次**: 第 {current_week} 周 星期{weekday_names[weekday-1]}\n")
        
        # 时间轴样式
        content_lines.append("---\n")
        content_lines.append("### 🕐 今日安排\n")
        
        for i, course in enumerate(courses, 1):
            # 课程卡片
            time_str = f"{course.start_time} - {course.end_time}" if course.start_time else "时间待定"
            
            # 单双周标记
            week_note = ""
            if course.is_single:
                week_note = " (单周)"
            elif course.is_double:
                week_note = " (双周)"
            
            content_lines.append(f"\n#### {i}. {course.name}{week_note}\n")
            content_lines.append(f"| 项目 | 内容 |\n|------|------|\n")
            content_lines.append(f"| 🕐 时间 | {time_str} |\n")
            
            if course.teacher:
                content_lines.append(f"| 👨‍🏫 教师 | {course.teacher} |\n")
            
            if course.classroom and course.classroom != '无':
                content_lines.append(f"| 📍 教室 | {course.classroom} |\n")
            
            content_lines.append("\n---\n")
        
        # 添加底部提示
        content_lines.append("\n💡 **温馨提示**")
        content_lines.append("- 请提前准备好教材和文具")
        content_lines.append("- 注意上课时间和教室位置")
        content_lines.append("- 如有调课请及时关注通知\n")
        
        content_lines.append("\n📱 *每日课表推送系统*")
        
        content = "\n".join(content_lines)
        return title, content
    
    def push_schedule(self, courses: List, current_week: int, weekday: int) -> bool:
        """推送课表到微信"""
        title, content = self.format_schedule_message(courses, current_week, weekday)
        
        payload = {
            'title': title,
            'desp': content
        }
        
        try:
            logger.info("正在推送课表到微信...")
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
    from schedule_fetcher import CourseItem
    
    test_courses = [
        CourseItem(
            name="Python程序设计",
            teacher="张老师",
            classroom="教学楼A301",
            start_time="08:00",
            end_time="09:40",
            weekday=1,
            sections="12",
            weeks="1-16"
        ),
        CourseItem(
            name="数据结构",
            teacher="李老师",
            classroom="教学楼B202",
            start_time="10:00",
            end_time="11:40",
            weekday=1,
            sections="34",
            weeks="1-16"
        )
    ]
    
    pusher = ServerChanPusher()
    pusher.push_schedule(test_courses, 3, 1)
