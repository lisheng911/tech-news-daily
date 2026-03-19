#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科技新闻自动推送主程序
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
    logger.info(f"科技新闻推送任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # 检查环境变量
    newsdata_key = os.getenv('NEWSDATA_API_KEY', '')
    serverchan_key = os.getenv('SERVERCHAN_SENDKEY', '')
    
    if not serverchan_key:
        logger.error("SERVERCHAN_SENDKEY 环境变量未设置，无法推送")
        sys.exit(1)
    
    if not newsdata_key:
        logger.warning("NEWSDATA_API_KEY 未设置，将使用RSS作为数据源")
    
    try:
        # 1. 抓取新闻
        logger.info("步骤1: 抓取新闻...")
        fetcher = NewsFetcher()
        all_news = fetcher.fetch_all()
        logger.info(f"共获取 {len(all_news)} 条原始新闻")
        
        if not all_news:
            logger.warning("未获取到任何新闻")
            sys.exit(0)
        
        # 2. 筛选排序
        logger.info("步骤2: 筛选和排序...")
        top_news = fetcher.filter_and_rank(all_news, top_n=10)
        logger.info(f"筛选后保留 {len(top_news)} 条高质量新闻")
        
        # 3. 推送
        logger.info("步骤3: 推送到微信...")
        pusher = ServerChanPusher()
        success = pusher.push(top_news)
        
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
