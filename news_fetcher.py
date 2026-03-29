#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选工具/项目推送模块
抓取国内AI工具、GitHub热门项目、自动化脚本、开源项目等
"""

import os
import re
import json
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ToolItem:
    """工具/项目条目"""
    name: str                    # 名称
    category: str                # 分类: ai_tool, github_project, automation, startup, open_source
    source: str                  # 来源
    link: str                    # 链接
    description: str             # 描述
    stars: int = 0               # GitHub stars (如适用)
    quality_score: int = 0       # 价值评分
    practical_use: str = ""      # 实际用途
    tags: List[str] = field(default_factory=list)


# ============ 数据源配置 ============

# 国内AI工具/模型（扩展列表）
CN_AI_TOOLS = [
    # ===== 大模型 =====
    {"name": "DeepSeek", "url": "https://www.deepseek.com/", "desc": "国产大模型，API便宜，编程能力强，支持深度思考", "tags": ["大模型", "API", "编程"]},
    {"name": "Kimi", "url": "https://kimi.moonshot.cn/", "desc": "长文本处理强，支持20万字上下文，免费", "tags": ["大模型", "长文本", "免费"]},
    {"name": "通义千问", "url": "https://tongyi.aliyun.com/", "desc": "阿里大模型，文档处理强，有免费额度", "tags": ["大模型", "文档"]},
    {"name": "智谱清言", "url": "https://chatglm.cn/", "desc": "清华系大模型，GLM开源，有API", "tags": ["大模型", "开源"]},
    {"name": "豆包", "url": "https://www.doubao.com/", "desc": "字节跳动大模型，免费，对话体验好", "tags": ["大模型", "免费"]},
    {"name": "文心一言", "url": "https://yiyan.baidu.com/", "desc": "百度大模型，中文理解强", "tags": ["大模型", "中文"]},
    {"name": "讯飞星火", "url": "https://xinghuo.xfyun.cn/", "desc": "科大讯飞大模型，语音交互强", "tags": ["大模型", "语音"]},
    {"name": "腾讯混元", "url": "https://hunyuan.tencent.com/", "desc": "腾讯大模型，微信生态集成", "tags": ["大模型", "微信"]},
    {"name": "百川大模型", "url": "https://www.baichuan-ai.com/", "desc": "开源大模型，可私有化部署", "tags": ["大模型", "开源", "部署"]},
    {"name": "MiniMax", "url": "https://www.minimaxi.com/", "desc": "AI对话+语音合成，有免费额度", "tags": ["大模型", "语音"]},
    
    # ===== AI编程工具 =====
    {"name": "iFlow CLI", "url": "https://github.com/iflow-ai/iflow-cli", "desc": "国产AI编程助手，心流编程体验", "tags": ["编程工具", "AI助手", "开源"]},
    {"name": "Cursor", "url": "https://cursor.com/", "desc": "AI编程编辑器，自动补全代码", "tags": ["编程工具", "IDE"]},
    {"name": "Trae", "url": "https://www.trae.ai/", "desc": "字节AI编程工具，国产版Cursor", "tags": ["编程工具", "IDE"]},
    {"name": "通义灵码", "url": "https://tongyi.aliyun.com/lingma", "desc": "阿里AI编程助手，VSCode插件", "tags": ["编程工具", "插件"]},
    {"name": "CodeGeeX", "url": "https://codegeex.cn/", "desc": "清华开源AI编程助手，多语言支持", "tags": ["编程工具", "开源"]},
    {"name": "Baidu Comate", "url": "https://comate.baidu.com/", "desc": "百度AI编程助手，企业可用", "tags": ["编程工具", "企业"]},
    
    # ===== AI应用搭建 =====
    {"name": "扣子Coze", "url": "https://www.coze.cn/", "desc": "字节AI应用搭建平台，无代码创建Bot", "tags": ["无代码", "AI应用"]},
    {"name": "Dify", "url": "https://dify.ai/", "desc": "开源LLM应用开发平台，可私有化部署", "tags": ["开源", "AI应用", "部署"]},
    {"name": "FastGPT", "url": "https://fastgpt.in/", "desc": "开源知识库问答系统，基于大模型", "tags": ["开源", "知识库", "RAG"]},
    {"name": "Cherry Studio", "url": "https://github.com/kangfenmao/cherry-studio", "desc": "国产AI客户端，支持多模型，美观易用", "tags": ["客户端", "开源"]},
    {"name": "LobeChat", "url": "https://github.com/lobehub/lobe-chat", "desc": "开源AI对话平台，支持多模型插件", "tags": ["开源", "客户端"]},
    {"name": "NextChat", "url": "https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web", "desc": "开源ChatGPT客户端，一键部署", "tags": ["开源", "部署"]},
    {"name": "GPT Academic", "url": "https://github.com/binary-husky/gpt_academic", "desc": "学术写作AI工具，论文润色翻译", "tags": ["学术", "开源"]},
    
    # ===== AI绘画/视频 =====
    {"name": "即梦", "url": "https://jimeng.jianying.com/", "desc": "字节AI绘画工具，免费生成图片", "tags": ["AI绘画", "免费"]},
    {"name": "可灵AI", "url": "https://klingai.kuaishou.com/", "desc": "快手AI视频生成，效果惊艳", "tags": ["AI视频", "创作"]},
    {"name": "LiblibAI", "url": "https://www.liblib.ai/", "desc": "AI绘画模型分享平台，大量免费模型", "tags": ["AI绘画", "模型库"]},
    {"name": "堆友", "url": "https://d.design/", "desc": "阿里AI设计平台，电商设计神器", "tags": ["AI设计", "电商"]},
    {"name": "通义万相", "url": "https://tongyi.aliyun.com/wanxiang/", "desc": "阿里AI绘画，中文提示词友好", "tags": ["AI绘画"]},
    {"name": "Vidu", "url": "https://www.vidu.studio/", "desc": "国产AI视频生成，高质量输出", "tags": ["AI视频", "创作"]},
    
    # ===== 效率工具 =====
    {"name": "飞书", "url": "https://www.feishu.cn/", "desc": "协作办公，有飞书多维表格自动化", "tags": ["办公", "自动化"]},
    {"name": "Notion", "url": "https://www.notion.so/", "desc": "笔记+数据库+AI，个人知识管理首选", "tags": ["笔记", "知识管理"]},
    {"name": "RayLink", "url": "https://www.raylink.live/", "desc": "免费远程控制软件，流畅稳定", "tags": ["远程控制", "免费"]},
    {"name": "Trello", "url": "https://trello.com/", "desc": "看板式任务管理，团队协作", "tags": ["任务管理", "协作"]},
    {"name": "语雀", "url": "https://www.yuque.com/", "desc": "阿里文档平台，知识库管理", "tags": ["文档", "知识库"]},
    
    # ===== 开发者工具 =====
    {"name": "Apifox", "url": "https://www.apifox.cn/", "desc": "API设计调试测试一体化工具", "tags": ["API", "开发"]},
    {"name": "Hoppscotch", "url": "https://hoppscotch.io/", "desc": "开源API调试工具，Postman替代", "tags": ["API", "开源"]},
    {"name": "RSSHub", "url": "https://docs.rsshub.app/", "desc": "开源RSS生成器，万物皆可RSS", "tags": ["RSS", "开源"]},
    {"name": "n8n", "url": "https://n8n.io/", "desc": "开源自动化工作流平台", "tags": ["自动化", "开源"]},
    {"name": "Huginn", "url": "https://github.com/huginn/huginn", "desc": "开源自动化代理，定时抓取推送", "tags": ["自动化", "开源"]},
]

# GitHub Trending API (通过RSSHub)
GITHUB_TRENDING_URLS = [
    ("https://rsshub.app/github/trending/daily/any?limit=50", "GitHub全站"),
    ("https://rsshub.app/github/trending/daily/python?limit=30", "Python"),
    ("https://rsshub.app/github/trending/daily/javascript?limit=30", "JavaScript"),
    ("https://rsshub.app/github/trending/daily/typescript?limit=30", "TypeScript"),
    ("https://rsshub.app/github/trending/daily/go?limit=20", "Go"),
    ("https://rsshub.app/github/trending/daily/rust?limit=20", "Rust"),
]

# RSS源配置
RSS_FEEDS = [
    # 技术资讯
    ("https://www.v2ex.com/api/topics/hot.json", "V2EX热门", "json"),
    ("https://rsshub.app/hackernews/best", "Hacker News", "rss"),
    ("https://rsshub.app/github/trending/daily", "GitHub Trending", "rss"),
    # 国内资讯
    ("https://www.36kr.com/feed", "36氪", "rss"),
    ("https://sspai.com/feed", "少数派", "rss"),
    ("https://rsshub.app/zhihu/hotlist", "知乎热榜", "rss"),
    ("https://rsshub.app/toutiao/today", "今日头条", "rss"),
    # 产品/创业
    ("https://rsshub.app/producthunt/today", "Product Hunt", "rss"),
    ("https://rsshub.app/indiehackers/posts/popular", "Indie Hackers", "rss"),
    # 技术博客
    ("https://rsshub.app/juejin/trending/all/monthly", "掘金热门", "rss"),
    ("https://rsshub.app/ruanyifeng/open_source_weekly", "阮一峰开源周刊", "rss"),
    ("https://rsshub.app/hellogithub/weekly", "HelloGitHub", "rss"),
]

# 自动化/实用项目关键词
AUTOMATION_KEYWORDS = [
    'automation', 'automate', '自动化', 'script', '脚本',
    'bot', '机器人', 'crawler', '爬虫', 'scraper',
    'tool', '工具', 'utility', 'helper', 'assistant',
    'workflow', '工作流', 'task', '任务', 'scheduler',
    'notification', '推送', '提醒', 'alert', '消息',
    'backup', '备份', 'sync', '同步', 'mirror',
    'download', '下载', 'converter', '转换', '格式',
    'github-actions', 'action', 'ci/cd', 'pipeline',
    'cli', 'command-line', 'terminal', 'shell',
    'api', 'wrapper', 'sdk', 'client', '接口',
    'spider', '监控', 'monitor', 'watch', 'alert',
    'rss', 'feed', '订阅', 'reader',
    'email', '邮件', 'sms', '消息推送',
    'ocr', '识别', 'extract', '解析',
    'pdf', 'word', 'excel', '文档',
    'image', '图片', 'video', '视频', '音频',
    'proxy', '代理', 'vpn', '网络',
    'password', '密码', '加密', 'encrypt',
    'database', '数据库', 'sql', 'redis',
]

# AI/大模型关键词
AI_KEYWORDS = [
    'ai', 'artificial-intelligence', '人工智能', 
    'llm', '大模型', 'gpt', 'chatgpt', 'claude',
    'deepseek', 'kimi', '通义', '文心', '智谱', '豆包',
    'agent', '智能体', 'prompt', '提示词', 'langchain',
    'rag', '知识库', 'embedding', '向量', 'pinecone',
    'chatbot', '对话', 'assistant', 'assistant',
    'generative', '生成式', 'aigc', 'content',
    'stable-diffusion', 'midjourney', '绘图', '绘画',
    'voice', '语音', 'tts', 'speech', 'whisper',
    'translation', '翻译', 'nlp', '自然语言',
    'vision', '视觉', '图像识别', 'ocr',
]

# 创业/赚钱关键词
STARTUP_KEYWORDS = [
    'startup', '创业', 'saas', '订阅', 'subscription',
    'monetize', '变现', 'revenue', '收入', 'profit',
    'side-project', '副业', 'indie', '独立开发',
    'landing-page', '落地页', 'marketing', '营销',
    'product', '产品', 'mvp', '最小可行',
    'business', '商业', '赚钱', '盈利',
    'freelance', '自由职业', '远程', 'remote',
]

# 开源/开发者关键词
DEV_KEYWORDS = [
    'open-source', '开源', 'free', '免费',
    'developer', '开发', 'programming', '编程',
    'framework', '框架', 'library', '库',
    'template', '模板', 'starter', 'boilerplate',
    'tutorial', '教程', 'learn', '学习',
]


class NewsFetcher:
    """信息抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, application/rss+xml, */*',
        })
        self.timeout = 30
    
    def fetch_all(self) -> List[ToolItem]:
        """获取所有信息"""
        items = []
        
        # 1. 国内AI工具
        logger.info("获取国内AI工具列表...")
        items.extend(self._get_cn_ai_tools())
        
        # 2. GitHub热门项目（多语言）
        logger.info("获取GitHub热门项目...")
        items.extend(self._fetch_github_trending())
        
        # 3. RSS资讯
        logger.info("获取RSS资讯...")
        items.extend(self._fetch_rss_feeds())
        
        # 4. V2EX热门
        logger.info("获取V2EX热门...")
        items.extend(self._fetch_v2ex_hot())
        
        # 5. HelloGitHub开源项目
        logger.info("获取HelloGitHub...")
        items.extend(self._fetch_hello_github())
        
        return items
    
    def _get_cn_ai_tools(self) -> List[ToolItem]:
        """获取国内AI工具列表"""
        items = []
        for tool in CN_AI_TOOLS:
            item = ToolItem(
                name=tool["name"],
                category="ai_tool",
                source="国内AI工具",
                link=tool["url"],
                description=tool["desc"],
                tags=tool.get("tags", []),
                quality_score=7
            )
            items.append(item)
        return items
    
    def _fetch_github_trending(self) -> List[ToolItem]:
        """获取GitHub Trending（多语言）"""
        items = []
        
        for url, lang_name in GITHUB_TRENDING_URLS:
            try:
                logger.info(f"获取 GitHub {lang_name} Trending...")
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    
                    for entry in feed.entries[:30]:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        summary = entry.get('summary', '') or entry.get('description', '')
                        
                        # 提取项目名
                        name_match = re.search(r'([^/]+/[^/\s]+)', title)
                        name = name_match.group(1) if name_match else title
                        
                        # 提取stars
                        stars = 0
                        star_match = re.search(r'(\d+,?\d*)\s*stars?', summary, re.I)
                        if star_match:
                            stars = int(star_match.group(1).replace(',', ''))
                        
                        # 提取描述
                        desc = re.sub(r'<[^>]+>', '', summary)
                        desc = desc[:200].strip()
                        
                        # 去重
                        if any(i.name == name for i in items):
                            continue
                        
                        item = ToolItem(
                            name=name,
                            category="github_project",
                            source=f"GitHub {lang_name}",
                            link=link,
                            description=desc,
                            stars=stars,
                        )
                        items.append(item)
                        
            except Exception as e:
                logger.error(f"GitHub {lang_name} 获取失败: {e}")
        
        logger.info(f"GitHub项目共获取 {len(items)} 条")
        return items
    
    def _fetch_rss_feeds(self) -> List[ToolItem]:
        """获取RSS资讯"""
        items = []
        
        for feed_url, source_name, feed_type in RSS_FEEDS:
            if feed_type == "json":
                continue
            
            try:
                logger.info(f"获取RSS: {source_name}")
                response = self.session.get(feed_url, timeout=self.timeout)
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    
                    for entry in feed.entries[:15]:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        summary = entry.get('summary', '') or entry.get('description', '')
                        summary = re.sub(r'<[^>]+>', '', summary)[:200]
                        
                        # 判断分类
                        if 'github' in feed_url.lower():
                            category = "github_project"
                        elif 'product' in feed_url.lower() or 'indie' in feed_url.lower():
                            category = "startup"
                        elif 'hellogithub' in feed_url.lower() or '开源' in source_name:
                            category = "open_source"
                        else:
                            category = "automation"
                        
                        item = ToolItem(
                            name=title[:60],
                            category=category,
                            source=source_name,
                            link=link,
                            description=summary,
                        )
                        items.append(item)
                        
            except Exception as e:
                logger.error(f"RSS {source_name} 获取失败: {e}")
        
        return items
    
    def _fetch_v2ex_hot(self) -> List[ToolItem]:
        """获取V2EX热门话题"""
        items = []
        
        try:
            url = "https://www.v2ex.com/api/topics/hot.json"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                for topic in data[:15]:
                    title = topic.get('title', '')
                    link = topic.get('url', '')
                    content = topic.get('content', '')[:200]
                    node = topic.get('node', {}).get('name', '')
                    
                    item = ToolItem(
                        name=title,
                        category="automation",
                        source=f"V2EX/{node}",
                        link=link,
                        description=content,
                    )
                    items.append(item)
                    
        except Exception as e:
            logger.error(f"V2EX获取失败: {e}")
        
        return items
    
    def _fetch_hello_github(self) -> List[ToolItem]:
        """获取HelloGitHub开源项目"""
        items = []
        
        try:
            url = "https://rsshub.app/hellogithub/weekly"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:20]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    summary = re.sub(r'<[^>]+>', '', summary)[:200]
                    
                    item = ToolItem(
                        name=title[:60],
                        category="open_source",
                        source="HelloGitHub",
                        link=link,
                        description=summary,
                    )
                    items.append(item)
                    
        except Exception as e:
            logger.error(f"HelloGitHub获取失败: {e}")
        
        return items
    
    def calculate_value_score(self, item: ToolItem) -> int:
        """计算价值评分 (0-10)"""
        score = 5
        text = f"{item.name} {item.description}".lower()
        
        # 自动化/实用工具 +3分
        if any(kw.lower() in text for kw in AUTOMATION_KEYWORDS):
            score += 3
        
        # AI相关 +2分
        if any(kw.lower() in text for kw in AI_KEYWORDS):
            score += 2
        
        # 创业/赚钱 +2分
        if any(kw.lower() in text for kw in STARTUP_KEYWORDS):
            score += 2
        
        # 开源/开发者 +1分
        if any(kw.lower() in text for kw in DEV_KEYWORDS):
            score += 1
        
        # GitHub stars加分
        if item.stars > 20000:
            score += 2
        elif item.stars > 10000:
            score += 1
        elif item.stars > 5000:
            score += 1
        
        # 国内AI工具加分
        if item.category == "ai_tool":
            score += 1
        
        # 开源项目加分
        if item.category == "open_source":
            score += 1
        
        # 过滤低价值
        low_value = ['广告', '推广', '优惠', '促销', '抽奖', '赞助', '广告位']
        if any(kw in text for kw in low_value):
            score -= 2
        
        return max(0, min(10, score))
    
    def generate_practical_use(self, item: ToolItem) -> str:
        """生成实际用途说明"""
        text = f"{item.name} {item.description}".lower()
        
        # 根据关键词给出建议
        suggestions = [
            (['cli', 'command', '终端', '命令'], "命令行工具，提升开发效率"),
            (['bot', '机器人', 'chatbot'], "自动化消息处理，节省人力"),
            (['crawler', '爬虫', 'scraper', 'spider'], "数据采集工具，信息监控利器"),
            (['automation', '自动化', 'workflow', 'n8n'], "自动化工具，替代重复劳动"),
            (['api', 'sdk', 'wrapper'], "开发接口，可集成到自己的项目"),
            (['notion', 'obsidian', '笔记', '知识库'], "知识管理工具，提升信息组织效率"),
            (['download', '下载'], "下载工具，可能节省会员费用"),
            (['backup', '同步', 'sync'], "数据备份工具，防止数据丢失"),
            (['大模型', 'llm', 'gpt', 'ai', 'chatgpt'], "AI能力，提升工作效率或开发AI应用"),
            (['saas', '订阅', '变现', 'revenue'], "商业模式参考，学习变现思路"),
            (['template', '模板', 'starter', 'boilerplate'], "项目模板，快速启动新项目"),
            (['rss', 'feed', '订阅'], "信息聚合工具，自动获取更新"),
            (['监控', 'monitor', 'alert'], "监控工具，及时发现问题"),
            (['ocr', '识别', 'extract'], "识别提取工具，自动化数据处理"),
            (['pdf', 'word', 'excel', '文档'], "文档处理工具，提升办公效率"),
            (['image', '图片', '绘画', 'diffusion'], "AI图像工具，创作效率提升"),
            (['video', '视频'], "视频处理工具，内容创作利器"),
            (['翻译', 'translation'], "翻译工具，跨语言沟通"),
            (['加密', 'encrypt', 'password'], "安全工具，保护数据安全"),
            (['代理', 'proxy', 'vpn'], "网络工具，访问更自由"),
        ]
        
        for keywords, suggestion in suggestions:
            if any(kw in text for kw in keywords):
                return suggestion
        
        return "值得关注，可能有实用价值"
    
    def filter_and_rank(self, items: List[ToolItem], top_n: int = 20) -> List[ToolItem]:
        """筛选并排序"""
        # 计算分数
        for item in items:
            item.quality_score = self.calculate_value_score(item)
            item.practical_use = self.generate_practical_use(item)
        
        # 过滤低分
        filtered = [i for i in items if i.quality_score >= 6]
        logger.info(f"筛选: {len(items)} -> {len(filtered)} 条 (>=6分)")
        
        # 按分数排序
        sorted_items = sorted(filtered, key=lambda x: (x.quality_score, x.stars), reverse=True)
        
        # 去重
        seen = set()
        unique = []
        for item in sorted_items:
            key = re.sub(r'\s+', '', item.name.lower())
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique[:top_n]


if __name__ == '__main__':
    # 测试
    fetcher = NewsFetcher()
    all_items = fetcher.fetch_all()
    top_items = fetcher.filter_and_rank(all_items, 25)
    
    print(f"\n今日精选 (共{len(all_items)}条，精选{len(top_items)}条):\n")
    
    for i, item in enumerate(top_items, 1):
        stars_str = f" ⭐{item.stars:,}" if item.stars > 0 else ""
        print(f"{i}. [{item.quality_score}分]{stars_str} {item.name}")
        print(f"   分类: {item.category} | 来源: {item.source}")
        print(f"   用途: {item.practical_use}")
        print()