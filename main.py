#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选工具推送主程序
自动抓取国内AI工具、GitHub热门项目、自动化脚本等
"""

import os
import sys
import logging
from datetime import datetime

from news_fetcher import NewsFetcher
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
    logger.info(f"每日精选推送任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # 检查环境变量
    serverchan_key = os.getenv('SERVERCHAN_SENDKEY', '')
    
    if not serverchan_key:
        logger.error("SERVERCHAN_SENDKEY 环境变量未设置，无法推送")
        sys.exit(1)
    
    try:
        # 1. 抓取内容
        logger.info("步骤1: 抓取内容...")
        fetcher = NewsFetcher()
        all_items = fetcher.fetch_all()
        logger.info(f"共获取 {len(all_items)} 条内容")
        
        # 2. 筛选高价值内容
        logger.info("步骤2: 筛选高价值内容...")
        top_items = fetcher.filter_and_rank(all_items, top_n=22)
        logger.info(f"筛选后 {len(top_items)} 条高价值内容")
        
        if not top_items:
            logger.warning("无高价值内容可推送")
            sys.exit(0)
        
        # 打印筛选结果
        logger.info("-" * 30)
        for i, item in enumerate(top_items, 1):
            logger.info(f"{i}. [{item.quality_score}分] {item.name} ({item.category})")
        logger.info("-" * 30)
        
        # 3. 推送
        logger.info("步骤3: 推送到微信...")
        pusher = ServerChanPusher()
        success = pusher.push_tools(top_items, len(all_items))
        
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
