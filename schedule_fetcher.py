#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
福州软件职业技术学院教务系统课表爬取模块
登录方式：MD5加密 + 验证码识别
"""

import os
import re
import hashlib
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置
BASE_URL = "https://jw.fzrjxy.com"
SEMESTER = "2025-2026-2"
FIRST_DAY = datetime(2026, 3, 6)  # 开学第一周周五


@dataclass
class CourseItem:
    """课程条目"""
    name: str           # 课程名称
    teacher: str        # 教师姓名
    classroom: str      # 教室名称
    start_time: str     # 开始时间
    end_time: str       # 结束时间
    weekday: int        # 星期几 (1-7)
    sections: str       # 第几节
    weeks: str          # 周次
    is_single: bool = False   # 单周
    is_double: bool = False   # 双周


class ScheduleFetcher:
    """课表爬取器"""
    
    def __init__(self):
        self.student_id = os.getenv('STUDENT_ID', '')
        self.password = os.getenv('STUDENT_PASSWORD', '')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, application/xhtml+xml, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'X-Requested-With': 'XMLHttpRequest',
        })
        self.logged_in = False
    
    def get_current_week(self) -> int:
        """计算当前是第几周"""
        today = datetime.now()
        days = (today - FIRST_DAY).days
        week = (days // 7) + 1
        return max(1, week)
    
    def get_today_weekday(self) -> int:
        """获取今天是星期几 (1-7, 1=周一)"""
        return datetime.now().weekday() + 1
    
    def md5_encrypt(self, s: str) -> str:
        """MD5加密"""
        return hashlib.md5(s.encode('utf-8')).hexdigest()
    
    def get_captcha(self) -> Optional[str]:
        """获取并识别验证码"""
        try:
            import ddddocr
        except ImportError:
            logger.warning("ddddocr 未安装")
            return None
        
        captcha_url = f"{BASE_URL}/studentportal.php/Public/verify/"
        
        try:
            logger.info(f"获取验证码: {captcha_url}")
            response = self.session.get(captcha_url, timeout=10)
            
            if response.status_code == 200 and len(response.content) > 50:
                ocr = ddddocr.DdddOcr(show_ad=False)
                code = ocr.classification(response.content)
                logger.info(f"验证码识别结果: {code}")
                return code
            else:
                logger.error(f"验证码获取失败: status={response.status_code}, size={len(response.content)}")
        
        except Exception as e:
            logger.error(f"验证码识别异常: {e}")
        
        return None
    
    def login(self) -> bool:
        """登录教务系统"""
        if not self.student_id or not self.password:
            logger.error("STUDENT_ID 或 STUDENT_PASSWORD 环境变量未设置")
            return False
        
        login_url = f"{BASE_URL}/studentportal.php/Index/checkLogin"
        
        # 构造登录数据
        data = {
            'logintype': 'xsxh',           # 登录类型：学号
            'xsxh': self.student_id,       # 学号
            'dlmm': self.md5_encrypt(self.password),  # 密码MD5加密
        }
        
        # 第一次尝试（无验证码）
        try:
            logger.info("尝试登录（无验证码）...")
            response = self.session.post(login_url, data=data, timeout=15)
            result = response.json()
            
            if result.get('status') == 1:
                self.logged_in = True
                logger.info("登录成功！")
                return True
            
            # 检查是否需要验证码
            if result.get('code') == 3 or '验证码' in result.get('info', ''):
                logger.info("需要验证码，正在获取...")
                
                # 获取验证码并重试
                captcha = self.get_captcha()
                if captcha:
                    data['yzm'] = captcha
                    
                    logger.info("使用验证码重新登录...")
                    response = self.session.post(login_url, data=data, timeout=15)
                    result = response.json()
                    
                    if result.get('status') == 1:
                        self.logged_in = True
                        logger.info("验证码登录成功！")
                        return True
                    else:
                        logger.error(f"登录失败: {result.get('info', '未知错误')}")
            else:
                logger.error(f"登录失败: {result.get('info', '未知错误')}")
        
        except Exception as e:
            logger.error(f"登录异常: {e}")
        
        return False
    
    def fetch_schedule_html(self, week: int = None) -> str:
        """获取课表HTML页面"""
        if not self.logged_in:
            logger.error("未登录，无法获取课表")
            return ""
        
        if week is None:
            week = self.get_current_week()
        
        # 访问主页建立会话
        try:
            main_url = f"{BASE_URL}/studentportal.php/Main/"
            self.session.get(main_url, timeout=10)
        except:
            pass
        
        # 获取课表
        schedule_url = f"{BASE_URL}/studentportal.php/Kbcx/bkxkcb"
        
        try:
            params = {
                'zc': str(week),
                'xnxqid': SEMESTER,
            }
            
            logger.info(f"获取第 {week} 周课表...")
            response = self.session.get(schedule_url, params=params, timeout=15)
            
            if response.status_code == 200 and len(response.text) > 500:
                return response.text
        except Exception as e:
            logger.error(f"获取课表异常: {e}")
        
        # 尝试其他URL
        alt_urls = [
            f"{BASE_URL}/studentportal.php/Kbcx/xskbcx",
            f"{BASE_URL}/studentportal.php/Main/kb",
        ]
        
        for url in alt_urls:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200 and len(response.text) > 500:
                    return response.text
            except:
                continue
        
        return ""
    
    def parse_html_schedule(self, html: str) -> List[CourseItem]:
        """解析HTML课表"""
        courses = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 方式1: 查找课表内容div
            kb_contents = soup.find_all('div', class_='kbcontent')
            
            if not kb_contents:
                # 方式2: 查找课表table
                table = soup.find('table', class_=re.compile(r'kb|schedule|timetable'))
                if table:
                    kb_contents = table.find_all('td')
            
            if not kb_contents:
                # 方式3: 查找所有有课程内容的td
                kb_contents = soup.find_all('td', class_=re.compile(r'has|course'))
            
            for content in kb_contents:
                text = content.get_text(strip=True)
                
                if not text or text == '\xa0' or len(text) < 2:
                    continue
                
                # 尝试解析课程名
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines:
                    course_name = lines[0]
                    
                    if course_name and len(course_name) > 1:
                        # 提取老师
                        teacher = ''
                        teacher_tag = content.find('font', title='老师')
                        if teacher_tag:
                            teacher = teacher_tag.get_text(strip=True)
                        elif len(lines) > 1:
                            # 尝试从文本提取
                            for line in lines[1:]:
                                if '老师' in line or '教师' in line:
                                    teacher = line.replace('老师', '').replace('教师', '').strip()
                                    break
                        
                        # 提取教室
                        classroom = ''
                        room_tag = content.find('font', title='教室')
                        if room_tag:
                            classroom = room_tag.get_text(strip=True)
                        
                        # 提取周次
                        weeks = ''
                        week_tag = content.find('font', title=re.compile(r'周次|节次'))
                        if week_tag:
                            weeks = week_tag.get_text(strip=True)
                        
                        course = CourseItem(
                            name=course_name,
                            teacher=teacher,
                            classroom=classroom,
                            start_time='',
                            end_time='',
                            weekday=1,
                            sections='',
                            weeks=weeks,
                        )
                        courses.append(course)
        
        except Exception as e:
            logger.error(f"解析课表HTML失败: {e}")
        
        return courses
    
    def get_today_courses(self) -> List[CourseItem]:
        """获取今日课程"""
        today_weekday = self.get_today_weekday()
        current_week = self.get_current_week()
        
        html = self.fetch_schedule_html(current_week)
        if not html:
            logger.warning("未获取到课表数据")
            return []
        
        all_courses = self.parse_html_schedule(html)
        
        # 筛选今日课程（简化处理，返回所有课程让用户自己看）
        logger.info(f"共解析到 {len(all_courses)} 条课程记录")
        
        return all_courses
    
    def fetch_all(self) -> List[CourseItem]:
        """主入口：获取课表"""
        if not self.login():
            logger.error("登录失败，无法获取课表")
            return []
        
        courses = self.get_today_courses()
        logger.info(f"获取到 {len(courses)} 条课程信息")
        
        return courses


if __name__ == '__main__':
    fetcher = ScheduleFetcher()
    print(f"当前周次: 第 {fetcher.get_current_week()} 周")
    print(f"今天: 星期 {fetcher.get_today_weekday()}")
    
    courses = fetcher.fetch_all()
    
    if not courses:
        print("\n获取失败或无课")
    else:
        print(f"\n课程信息 ({len(courses)} 条):")
        for course in courses:
            print(f"- {course.name} | {course.teacher} | {course.classroom}")
