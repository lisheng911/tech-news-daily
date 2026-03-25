#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强智教务系统课表爬取模块
支持多种登录方式：Base64加密登录、验证码识别
"""

import os
import re
import base64
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
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
    
    def encode_str(self, s: str) -> str:
        """Base64编码（强智系统加密方式）"""
        return base64.b64encode(s.encode('utf-8')).decode('utf-8')
    
    def login_base64(self) -> bool:
        """使用Base64加密方式登录（强智标准方式）"""
        login_url = f"{BASE_URL}/jsxsd/xk/LoginToXk"
        
        # 构造加密数据: encode(账号)%%encode(密码)=
        encoded_user = self.encode_str(self.student_id)
        encoded_pwd = self.encode_str(self.password)
        encoded_data = f"{encoded_user}%%{encoded_pwd}="
        
        form_data = {'encoded': encoded_data}
        
        try:
            logger.info("尝试 Base64 加密登录...")
            response = self.session.post(login_url, data=form_data, timeout=15, allow_redirects=True)
            
            # 检查登录是否成功
            if '学生个人中心' in response.text or 'xskb' in response.text or response.status_code == 200:
                self.logged_in = True
                logger.info("Base64 登录成功!")
                return True
            else:
                logger.warning("Base64 登录失败")
                return False
        
        except Exception as e:
            logger.error(f"Base64 登录异常: {e}")
            return False
    
    def login_studentportal(self) -> bool:
        """登录学生门户"""
        try:
            # 1. 获取登录页面
            login_page_url = f"{BASE_URL}/studentportal.php"
            response = self.session.get(login_page_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 2. 查找登录表单
            form = soup.find('form')
            if not form:
                logger.warning("未找到登录表单")
                return False
            
            action = form.get('action', '')
            if action.startswith('/'):
                login_url = f"{BASE_URL}{action}"
            elif action.startswith('http'):
                login_url = action
            else:
                login_url = f"{BASE_URL}/studentportal.php/{action}" if action else f"{BASE_URL}/studentportal.php/Home/Login"
            
            # 3. 提交登录
            logger.info(f"尝试学生门户登录: {login_url}")
            
            data = {
                'xh': self.student_id,
                'pwd': self.password,
            }
            
            # 如果有验证码，尝试识别
            captcha_img = soup.find('img', {'id': re.compile(r'verify|captcha|code', re.I)})
            if captcha_img:
                captcha_src = captcha_img.get('src', '')
                if captcha_src:
                    # 尝试识别验证码
                    captcha_result = self._recognize_captcha(captcha_src)
                    if captcha_result:
                        data['verifycode'] = captcha_result
                        data['code'] = captcha_result
            
            response = self.session.post(login_url, data=data, timeout=15, allow_redirects=True)
            
            if '登录成功' in response.text or '个人中心' in response.text or '课表' in response.text:
                self.logged_in = True
                logger.info("学生门户登录成功!")
                return True
            
            logger.warning(f"学生门户登录失败，响应长度: {len(response.text)}")
            return False
        
        except Exception as e:
            logger.error(f"学生门户登录异常: {e}")
            return False
    
    def _recognize_captcha(self, captcha_src: str) -> Optional[str]:
        """识别验证码"""
        try:
            import ddddocr
            
            # 构造完整URL
            if captcha_src.startswith('/'):
                captcha_url = f"{BASE_URL}{captcha_src}"
            elif not captcha_src.startswith('http'):
                captcha_url = f"{BASE_URL}/{captcha_src}"
            else:
                captcha_url = captcha_src
            
            logger.info(f"获取验证码: {captcha_url}")
            response = self.session.get(captcha_url, timeout=10)
            
            if response.status_code == 200 and len(response.content) > 50:
                ocr = ddddocr.DdddOcr(show_ad=False)
                code = ocr.classification(response.content)
                logger.info(f"验证码识别结果: {code}")
                return code
        
        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
        
        return None
    
    def login_with_captcha(self) -> bool:
        """带验证码的登录流程"""
        try:
            import ddddocr
        except ImportError:
            logger.warning("ddddocr 未安装")
            return False
        
        # 尝试多种验证码URL
        captcha_urls = [
            f"{BASE_URL}/verifycode.servlet",
            f"{BASE_URL}/CheckCode.aspx",
            f"{BASE_URL}/jsxsd/verifycode.servlet",
        ]
        
        for captcha_url in captcha_urls:
            try:
                logger.info(f"尝试验证码登录: {captcha_url}")
                
                # 获取验证码
                response = self.session.get(captcha_url, timeout=10)
                if response.status_code != 200 or len(response.content) < 50:
                    continue
                
                # 识别验证码
                ocr = ddddocr.DdddOcr(show_ad=False)
                captcha_code = ocr.classification(response.content)
                logger.info(f"验证码识别: {captcha_code}")
                
                # 提交登录
                login_url = f"{BASE_URL}/jsxsd/xk/LoginToXk"
                encoded_user = self.encode_str(self.student_id)
                encoded_pwd = self.encode_str(self.password)
                
                form_data = {
                    'encoded': f"{encoded_user}%%{encoded_pwd}=",
                    'RANDOMCODE': captcha_code,
                }
                
                response = self.session.post(login_url, data=form_data, timeout=15)
                
                if '学生个人中心' in response.text or response.status_code == 200:
                    self.logged_in = True
                    logger.info("验证码登录成功!")
                    return True
            
            except Exception as e:
                logger.warning(f"验证码登录尝试失败: {e}")
                continue
        
        return False
    
    def login(self) -> bool:
        """尝试多种方式登录"""
        if not self.student_id or not self.password:
            logger.error("STUDENT_ID 或 STUDENT_PASSWORD 环境变量未设置")
            return False
        
        # 尝试不同的登录方式
        methods = [
            self.login_base64,
            self.login_studentportal,
            self.login_with_captcha,
        ]
        
        for method in methods:
            if method():
                return True
            self.session.cookies.clear()
        
        logger.error("所有登录方式均失败")
        return False
    
    def fetch_schedule_html(self, week: int = None) -> str:
        """获取课表HTML页面"""
        if week is None:
            week = self.get_current_week()
        
        # 尝试多种课表URL
        schedule_urls = [
            f"{BASE_URL}/jsxsd/xskb/xskb_list.do",
            f"{BASE_URL}/jsxsd/xskb/xskb_find.jsp",
        ]
        
        for url in schedule_urls:
            try:
                params = {
                    'zc': str(week),
                    'xnxq01id': SEMESTER,
                    'sfFd': '1',
                }
                
                logger.info(f"获取第 {week} 周课表: {url}")
                response = self.session.get(url, params=params, timeout=15)
                
                if response.status_code == 200 and len(response.text) > 500:
                    return response.text
            except Exception as e:
                logger.warning(f"获取课表失败 ({url}): {e}")
        
        return ""
    
    def parse_html_schedule(self, html: str) -> List[CourseItem]:
        """解析HTML课表"""
        courses = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找课表内容
            kb_contents = soup.find_all('div', class_='kbcontent')
            
            if not kb_contents:
                # 尝试其他解析方式
                kb_contents = soup.find_all('td', class_=re.compile(r'kb|course'))
            
            weekday = 1
            section = 1
            
            for content in kb_contents:
                text = content.get_text(strip=True)
                
                if not text or text == '\xa0':
                    continue
                
                # 尝试解析课程信息
                # 格式通常是：课程名\n老师\n周次\n教室
                lines = text.split('\n')
                if lines:
                    course_name = lines[0].strip() if lines else ''
                    
                    if course_name and course_name != '\xa0':
                        # 提取老师
                        teacher = ''
                        teacher_tag = content.find('font', title='老师')
                        if teacher_tag:
                            teacher = teacher_tag.get_text(strip=True)
                        
                        # 提取教室
                        classroom = ''
                        room_tag = content.find('font', title='教室')
                        if room_tag:
                            classroom = room_tag.get_text(strip=True)
                        
                        # 提取周次
                        weeks = ''
                        week_tag = content.find('font', title='周次(节次)')
                        if week_tag:
                            weeks = week_tag.get_text(strip=True)
                        
                        course = CourseItem(
                            name=course_name,
                            teacher=teacher,
                            classroom=classroom,
                            start_time='',
                            end_time='',
                            weekday=weekday,
                            sections=str(section),
                            weeks=weeks,
                        )
                        courses.append(course)
                
                weekday += 1
                if weekday > 7:
                    weekday = 1
                    section += 1
        
        except Exception as e:
            logger.error(f"解析课表HTML失败: {e}")
        
        return courses
    
    def get_today_courses(self) -> List[CourseItem]:
        """获取今日课程"""
        today_weekday = self.get_today_weekday()
        current_week = self.get_current_week()
        
        # 获取课表HTML
        html = self.fetch_schedule_html(current_week)
        if not html:
            logger.warning("未获取到课表数据")
            return []
        
        # 解析课表
        all_courses = self.parse_html_schedule(html)
        
        # 筛选今日课程
        today_courses = [c for c in all_courses if c.weekday == today_weekday]
        
        # 按节次排序
        today_courses.sort(key=lambda c: int(c.sections) if c.sections.isdigit() else 0)
        
        return today_courses
    
    def fetch_all(self) -> List[CourseItem]:
        """主入口：获取今日课表"""
        if not self.login():
            logger.error("登录失败，无法获取课表")
            return []
        
        courses = self.get_today_courses()
        logger.info(f"今日共有 {len(courses)} 节课")
        
        return courses


if __name__ == '__main__':
    # 测试
    fetcher = ScheduleFetcher()
    print(f"当前周次: 第 {fetcher.get_current_week()} 周")
    print(f"今天: 星期 {fetcher.get_today_weekday()}")
    
    courses = fetcher.fetch_all()
    
    if not courses:
        print("\n今日无课或获取失败")
    else:
        print(f"\n今日课程 ({len(courses)} 节):")
        print("-" * 50)
        for course in courses:
            print(f"📚 {course.name}")
            print(f"   👨‍🏫 {course.teacher}")
            print(f"   📍 {course.classroom}")
            print(f"   📅 第{course.sections}节")
            print("-" * 50)
