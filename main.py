#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日课表推送主程序
"""

import os
import sys
import logging
from datetime import datetime

from schedule_fetcher import ScheduleFetcher
from push_notification import ServerChanPusher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info(f"每日课表推送任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # 检查环境变量
    student_id = os.getenv('STUDENT_ID', '')
    student_password = os.getenv('STUDENT_PASSWORD', '')
    serverchan_key = os.getenv('SERVERCHAN_SENDKEY', '')
    
    if not serverchan_key:
        logger.error("SERVERCHAN_SENDKEY 环境变量未设置，无法推送")
        sys.exit(1)
    
    if not student_id or not student_password:
        logger.error("STUDENT_ID 或 STUDENT_PASSWORD 环境变量未设置")
        sys.exit(1)
    
    try:
        # 1. 登录并获取课表
        logger.info("步骤1: 登录教务系统并获取课表...")
        fetcher = ScheduleFetcher()
        
        current_week = fetcher.get_current_week()
        weekday = fetcher.get_today_weekday()
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        
        logger.info(f"当前: 第 {current_week} 周 星期{weekday_names[weekday-1]}")
        
        courses = fetcher.fetch_all()
        logger.info(f"今日共 {len(courses)} 节课")
        
        # 2. 推送课表
        logger.info("步骤2: 推送课表到微信...")
        pusher = ServerChanPusher()
        success = pusher.push_schedule(courses, current_week, weekday)
        
        if success:
            logger.info("✅ 任务完成!")
        else:
            logger.error("❌ 推送失败")
            sys.exit(1)
    
    except Exception as e:
        logger.exception(f"任务执行出错: {e}")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info(f"任务结束 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)


if __name__ == '__main__':
    main()