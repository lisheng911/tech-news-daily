#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强智教务系统课表爬取模块
支持验证码自动识别
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

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
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        self.token = None
    
    def get_current_week(self) -> int:
        """计算当前是第几周"""
        today = datetime.now()
        # 计算从开学第一天到今天的天数
        days = (today - FIRST_DAY).days
        # 开学第一天是周五，所以第一周从那天开始
        # 第几周 = (天数 // 7) + 1
        week = (days // 7) + 1
        return max(1, week)
    
    def get_today_weekday(self) -> int:
        """获取今天是星期几 (1-7, 1=周一)"""
        return datetime.now().weekday() + 1
    
    def try_login_without_captcha(self) -> bool:
        """尝试无验证码登录 (app.do 接口)"""
        login_url = f"{BASE_URL}/app.do"
        params = {
            'method': 'authUser',
            'xh': self.student_id,
            'pwd': self.password
        }
        
        try:
            logger.info("尝试无验证码登录 (app.do)...")
            response = self.session.post(login_url, params=params, timeout=15)
            data = response.json()
            
            # 检查登录成功标志
            if data.get('success') or data.get('flag') == '1' or data.get('token'):
                self.token = data.get('token', data.get('accessToken'))
                logger.info(f"登录成功! Token: {self.token[:20]}..." if self.token else "登录成功!")
                return True
            else:
                msg = data.get('msg', data.get('message', '未知错误'))
                logger.warning(f"登录失败: {msg}")
                return False
        
        except Exception as e:
            logger.error(f"无验证码登录异常: {e}")
            return False
    
    def try_login_ashx(self) -> bool:
        """尝试 app.ashx 接口登录"""
        login_url = f"{BASE_URL}/app/app.ashx"
        params = {
            'method': 'authUser',
            'xh': self.student_id,
            'pwd': self.password
        }
        
        try:
            logger.info("尝试 app.ashx 接口登录...")
            response = self.session.post(login_url, params=params, timeout=15)
            data = response.json()
            
            if data.get('success') or data.get('flag') == '1' or data.get('token'):
                self.token = data.get('token', data.get('accessToken'))
                logger.info(f"app.ashx 登录成功!")
                return True
            return False
        
        except Exception as e:
            logger.error(f"app.ashx 登录异常: {e}")
            return False
    
    def login_with_captcha(self) -> bool:
        """带验证码的登录流程"""
        try:
            # 尝试导入验证码识别库
            import ddddocr
        except ImportError:
            logger.warning("ddddocr 未安装，无法识别验证码")
            logger.info("请在 requirements.txt 中添加: ddddocr")
            return False
        
        try:
            import ddddocr
            
            # 1. 获取验证码图片
            captcha_urls = [
                f"{BASE_URL}/verifycode.servlet",
                f"{BASE_URL}/CheckCode.aspx",
                f"{BASE_URL}/jsxsd/verifycode.servlet",
                f"{BASE_URL}/app/verifycode.servlet",
            ]
            
            captcha_img = None
            for url in captcha_urls:
                try:
                    logger.info(f"尝试获取验证码: {url}")
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200 and len(response.content) > 100:
                        captcha_img = response.content
                        break
                except:
                    continue
            
            if not captcha_img:
                logger.error("无法获取验证码图片")
                return False
            
            # 2. 识别验证码
            ocr = ddddocr.DdddOcr(show_ad=False)
            captcha_code = ocr.classification(captcha_img)
            logger.info(f"验证码识别结果: {captcha_code}")
            
            # 3. 提交登录
            login_url = f"{BASE_URL}/studentportal.php/Home/Login"
            data = {
                'xh': self.student_id,
                'pwd': self.password,
                'verifycode': captcha_code,
            }
            
            response = self.session.post(login_url, data=data, timeout=15)
            
            # 检查是否登录成功
            if '登录成功' in response.text or 'success' in response.text.lower():
                logger.info("验证码登录成功!")
                return True
            else:
                logger.error("验证码登录失败")
                return False
        
        except Exception as e:
            logger.error(f"验证码登录异常: {e}")
            return False
    
    def login(self) -> bool:
        """尝试多种方式登录"""
        if not self.student_id or not self.password:
            logger.error("STUDENT_ID 或 STUDENT_PASSWORD 环境变量未设置")
            return False
        
        # 尝试不同的登录方式
        methods = [
            self.try_login_without_captcha,
            self.try_login_ashx,
            self.login_with_captcha,
        ]
        
        for method in methods:
            if method():
                return True
        
        logger.error("所有登录方式均失败")
        return False
    
    def fetch_schedule(self, week: int = None) -> List[Dict]:
        """获取指定周次的课表"""
        if week is None:
            week = self.get_current_week()
        
        if not self.token:
            logger.error("未登录，无法获取课表")
            return []
        
        # 尝试不同的API端点
        api_urls = [
            f"{BASE_URL}/app.do",
            f"{BASE_URL}/app/app.ashx",
        ]
        
        for api_url in api_urls:
            try:
                params = {
                    'method': 'getKbcxAzc',
                    'xh': self.student_id,
                    'xnxqid': SEMESTER,
                    'zc': str(week)
                }
                headers = {'token': self.token} if self.token else {}
                
                logger.info(f"获取第 {week} 周课表...")
                response = self.session.get(api_url, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        logger.info(f"获取到 {len(data)} 条课程记录")
                        return data
                    elif data.get('token') == '-1':
                        logger.warning("Token已过期，需要重新登录")
                        continue
            except Exception as e:
                logger.error(f"获取课表异常 ({api_url}): {e}")
                continue
        
        return []
    
    def parse_schedule(self, raw_data: List[Dict]) -> List[CourseItem]:
        """解析课表数据"""
        courses = []
        
        for item in raw_data:
            try:
                # 解析课程时间字段 kcsj (格式: x0a0b, 表示星期x的第a,b节)
                kcsj = item.get('kcsj', '00000')
                weekday = int(kcsj[0]) if len(kcsj) > 0 else 0
                sections = kcsj[1:] if len(kcsj) > 1 else ''
                
                # 解析周次信息
                kkzc = item.get('kkzc', '')
                is_single = item.get('sjbz') == '1'
                is_double = item.get('sjbz') == '2'
                
                course = CourseItem(
                    name=item.get('kcmc', '未知课程'),
                    teacher=item.get('jsxm', ''),
                    classroom=item.get('jsmc', ''),
                    start_time=item.get('kssj', ''),
                    end_time=item.get('jssj', ''),
                    weekday=weekday,
                    sections=sections,
                    weeks=kkzc,
                    is_single=is_single,
                    is_double=is_double
                )
                courses.append(course)
            
            except Exception as e:
                logger.warning(f"解析课程失败: {e}")
                continue
        
        return courses
    
    def get_today_courses(self, courses: List[CourseItem] = None) -> List[CourseItem]:
        """获取今日课程"""
        if courses is None:
            if not self.login():
                return []
            raw_data = self.fetch_schedule()
            courses = self.parse_schedule(raw_data)
        
        today_weekday = self.get_today_weekday()
        current_week = self.get_current_week()
        
        today_courses = []
        for course in courses:
            if course.weekday != today_weekday:
                continue
            
            # 检查周次
            if course.is_single and current_week % 2 == 0:
                continue  # 单周课，但当前是双周
            if course.is_double and current_week % 2 == 1:
                continue  # 双周课，但当前是单周
            
            # 检查是否在当前周
            if course.weeks:
                try:
                    # 处理不同格式的周次: "1-16", "1,3,5", "1-8,10-16"
                    weeks_str = course.weeks
                    week_nums = set()
                    
                    # 解析 "1-16" 格式
                    range_match = re.findall(r'(\d+)-(\d+)', weeks_str)
                    for start, end in range_match:
                        week_nums.update(range(int(start), int(end) + 1))
                    
                    # 解析 "1,3,5" 格式
                    single_nums = re.findall(r'(?<!\d)(\d+)(?!\d)', weeks_str)
                    for num in single_nums:
                        week_nums.add(int(num))
                    
                    if current_week not in week_nums:
                        continue
                except:
                    pass
            
            today_courses.append(course)
        
        # 按开始时间排序
        today_courses.sort(key=lambda c: c.start_time if c.start_time else '00:00')
        
        return today_courses
    
    def fetch_all(self) -> List[CourseItem]:
        """主入口：获取今日课表"""
        if not self.login():
            logger.error("登录失败，无法获取课表")
            return []
        
        raw_data = self.fetch_schedule()
        if not raw_data:
            logger.warning("未获取到课表数据")
            return []
        
        courses = self.parse_schedule(raw_data)
        today_courses = self.get_today_courses(courses)
        
        logger.info(f"今日共有 {len(today_courses)} 节课")
        return today_courses


def format_time_display(time_str: str) -> str:
    """格式化时间显示"""
    if not time_str or time_str == '00:00':
        return ''
    return time_str


def get_section_time(section: str) -> Tuple[str, str]:
    """根据节次获取上课时间"""
    # 常见的时间安排
    time_map = {
        '1': ('08:00', '08:45'),
        '2': ('08:55', '09:40'),
        '3': ('10:00', '10:45'),
        '4': ('10:55', '11:40'),
        '5': ('11:50', '12:35'),
        '6': ('14:00', '14:45'),
        '7': ('14:55', '15:40'),
        '8': ('16:00', '16:45'),
        '9': ('16:55', '17:40'),
        '10': ('19:00', '19:45'),
        '11': ('19:55', '20:40'),
        '12': ('20:50', '21:35'),
    }
    
    if not section:
        return ('', '')
    
    # 提取第一个数字
    match = re.search(r'(\d+)', section)
    if match:
        sec_num = match.group(1)
        return time_map.get(sec_num, ('', ''))
    
    return ('', '')


if __name__ == '__main__':
    # 测试
    fetcher = ScheduleFetcher()
    print(f"当前周次: 第 {fetcher.get_current_week()} 周")
    print(f"今天: 星期 {fetcher.get_today_weekday()}")
    
    courses = fetcher.fetch_all()
    
    if not courses:
        print("\n今日无课")
    else:
        print(f"\n今日课程 ({len(courses)} 节):")
        print("-" * 50)
        for course in courses:
            print(f"📚 {course.name}")
            print(f"   👨‍🏫 {course.teacher}")
            print(f"   📍 {course.classroom}")
            print(f"   🕐 {course.start_time} - {course.end_time}")
            print("-" * 50)
