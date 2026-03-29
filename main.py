#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选推送主程序
"""

import os
import sys
import logging
from datetime import datetime

from news_fetcher import NewsFetcher
from push_notification import ServerChanPusher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info(f"每日精选推送 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # 检查环境变量
    if not os.getenv('SERVERCHAN_SENDKEY'):
        logger.error("SERVERCHAN_SENDKEY 未设置")
        sys.exit(1)
    
    try:
        # 1. 抓取
        logger.info("📥 开始抓取...")
        fetcher = NewsFetcher()
        categorized = fetcher.fetch_all()
        
        # 统计
        total = sum(len(items) for items in categorized.values())
        logger.info(f"📊 精选 {total} 条内容")
        for cat, items in categorized.items():
            logger.info(f"  {cat}: {len(items)}条")
        
        if total == 0:
            logger.warning("无内容可推送")
            sys.exit(0)
        
        # 2. 推送
        logger.info("📤 开始推送...")
        pusher = ServerChanPusher()
        success = pusher.push(categorized)
        
        if success:
            logger.info("✅ 任务完成!")
        else:
            logger.error("❌ 推送失败")
            sys.exit(1)
    
    except Exception as e:
        logger.exception(f"执行出错: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
