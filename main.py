#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选推送主程序 - 增强版

目标：只推高价值、尽量不重复
保证：每个分类都有内容
"""

import os
import sys
import traceback
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_fetcher import NewsFetcher
from push_notification import ServerChanPusher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info(f"每日精选推送 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    if not os.getenv('SERVERCHAN_SENDKEY'):
        logger.error("❌ SERVERCHAN_SENDKEY 未设置")
        sys.exit(1)
    
    pusher = None
    try:
        pusher = ServerChanPusher()
        
        logger.info("📥 开始抓取...")
        fetcher = NewsFetcher()
        result = fetcher.fetch_all()
        
        stats = result.get("统计面板", {})
        category_counts = stats.get("各分类数", {})
        total = sum(category_counts.values())
        
        logger.info(f"📊 分类统计:")
        for cat, count in category_counts.items():
            logger.info(f"   {cat}: {count}条")
        logger.info(f"   总计: {total}条")
        
        if total == 0:
            logger.warning("⚠️ 无内容可推送")
            sys.exit(0)
        
        logger.info("📤 开始推送...")
        success = pusher.push(result)
        
        if success:
            logger.info("✅ 任务完成!")
        else:
            logger.error("❌ 推送失败")
            pusher.push_alert("消息推送", "推送API调用失败")
            sys.exit(1)
    
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.exception(f"❌ 执行出错: {e}")
        
        if pusher:
            pusher.push_alert("主程序执行", error_trace[-500:])
        else:
            try:
                pusher = ServerChanPusher()
                pusher.push_alert("主程序执行", error_trace[-500:])
            except:
                pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()