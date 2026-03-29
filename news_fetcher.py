#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日精选推送模块 - 增强版

核心原则：
- 只推高价值、尽量不重复
- 空推可接受，重复推送不接受
- 每个分类必须有内容

增强特性：
- 抓取隔离层：单源故障不影响全局
- 去噪黑名单：过滤垃圾内容
- 冷启动保护：连续空推放宽阈值
- 结构化历史：数据资产化
- 模糊去重：标题相似度检测
- 评分软上限：防止评分爆炸
"""

import os
import re
import json
import hashlib
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============ 模糊去重工具函数 ============
def normalize_title(title: str) -> str:
    """标准化标题：去标点、小写、去空格"""
    # 去除标点符号
    title = re.sub(r'[^\w\s\u4e00-\u9fff]', '', title)
    # 小写
    title = title.lower()
    # 合并空格
    title = re.sub(r'\s+', '', title)
    return title


def extract_keywords(title: str) -> Set[str]:
    """提取标题关键词（简单分词）"""
    norm = normalize_title(title)
    # 中文按字符切分（2字以上）
    keywords = set()
    # 提取英文单词
    en_words = re.findall(r'[a-z]{2,}', norm)
    keywords.update(en_words)
    # 提取中文词组（2-4字）
    for i in range(len(norm)):
        for length in [4, 3, 2]:
            if i + length <= len(norm):
                word = norm[i:i+length]
                if re.match(r'^[\u4e00-\u9fff]+$', word):
                    keywords.add(word)
    return keywords


def title_similarity(title1: str, title2: str) -> float:
    """
    计算标题相似度（0-1）
    
    方法：关键词重合度
    """
    kw1 = extract_keywords(title1)
    kw2 = extract_keywords(title2)
    
    if not kw1 or not kw2:
        return 0.0
    
    intersection = kw1 & kw2
    union = kw1 | kw2
    
    return len(intersection) / len(union) if union else 0.0


# ============ 去噪关键词黑名单 ============
BLACKLIST_KEYWORDS = [
    "速看", "震惊", "发布会", "盘点", "汇总", "必看", "重磅",
    "刚刚", "突发", "紧急", "惊呆", "疯了", "泪目", "破防",
    "官宣", "首发", "独家", "揭秘", "曝光", "涉嫌"
]

# ============ 静态资源库（长期工具） ============
STATIC_RESOURCES = {
    "GitHub热门": [
        {"name": "yt-dlp - 视频下载神器", "url": "https://github.com/yt-dlp/yt-dlp", "desc": "支持上千网站", "stars": 75000},
        {"name": "AutoGPT - 自主AI代理", "url": "https://github.com/Significant-Gravitas/AutoGPT", "desc": "AI自动化先锋", "stars": 160000},
        {"name": "LangChain - LLM应用框架", "url": "https://github.com/langchain-ai/langchain", "desc": "构建AI应用", "stars": 90000},
        {"name": "ComfyUI - Stable Diffusion GUI", "url": "https://github.com/comfyanonymous/ComfyUI", "desc": "AI绘画节点式界面", "stars": 50000},
        {"name": "transformers - HuggingFace核心库", "url": "https://github.com/huggingface/transformers", "desc": "预训练模型库", "stars": 130000},
    ],
    "自动化脚本": [
        {"name": "n8n - 工作流自动化", "url": "https://github.com/n8n-io/n8n", "desc": "可视化自动化平台", "stars": 40000},
        {"name": "huginn - 自动化代理", "url": "https://github.com/huginn/huginn", "desc": "构建自定义代理", "stars": 42000},
        {"name": "AutoHotkey - Windows自动化", "url": "https://www.autohotkey.com/", "desc": "脚本自动化工具"},
        {"name": "Playwright - 浏览器自动化", "url": "https://github.com/microsoft/playwright", "desc": "跨浏览器自动化", "stars": 65000},
        {"name": "Puppeteer - Node.js浏览器控制", "url": "https://github.com/puppeteer/puppeteer", "desc": "Headless Chrome", "stars": 88000},
    ],
    "AI新功能": [
        {"name": "DeepSeek R1 - 深度思考模型", "url": "https://www.deepseek.com/", "desc": "国产推理模型，免费开放"},
        {"name": "Kimi - 长文本AI", "url": "https://kimi.moonshot.cn/", "desc": "20万字长文本，完全免费"},
        {"name": "Claude - Anthropic AI助手", "url": "https://claude.ai/", "desc": "安全可靠的AI对话"},
        {"name": "Perplexity - AI搜索引擎", "url": "https://www.perplexity.ai/", "desc": "AI驱动搜索"},
        {"name": "Midjourney - AI绘画", "url": "https://www.midjourney.com/", "desc": "高质量AI图像生成"},
    ],
    "新模型咨询": [
        {"name": "Hugging Face - 模型社区", "url": "https://huggingface.co/models", "desc": "最新开源模型集合"},
        {"name": "OpenRouter - API聚合", "url": "https://openrouter.ai/", "desc": "多模型统一接口"},
        {"name": "Ollama - 本地运行LLM", "url": "https://ollama.ai/", "desc": "本地大模型运行"},
        {"name": "ModelScope - 阿里模型库", "url": "https://modelscope.cn/", "desc": "国产模型社区"},
        {"name": "Papers With Code - 论文+代码", "url": "https://paperswithcode.com/", "desc": "最新AI论文追踪"},
    ],
    "好用的工具": [
        {"name": "Cursor - AI编程助手", "url": "https://cursor.sh/", "desc": "AI代码编辑器"},
        {"name": "Raycast - Mac效率工具", "url": "https://www.raycast.com/", "desc": "快捷启动器"},
        {"name": "Obsidian - 知识管理", "url": "https://obsidian.md/", "desc": "双向链接笔记"},
        {"name": "Notion - 全能协作平台", "url": "https://www.notion.so/", "desc": "笔记+数据库+协作"},
        {"name": "VS Code - 代码编辑器", "url": "https://code.visualstudio.com/", "desc": "免费强大的IDE"},
        {"name": "Docker - 容器化平台", "url": "https://www.docker.com/", "desc": "应用容器化部署"},
        {"name": "Figma - 设计协作", "url": "https://www.figma.com/", "desc": "在线UI设计工具"},
    ],
}


@dataclass
class ContentItem:
    """内容条目"""
    title: str
    link: str
    source: str
    publish_time: str = ""
    category: str = "未分类"
    description: str = ""
    stars: int = 0
    quality_score: int = 5
    status: str = "new"
    content_hash: str = ""
    duplicate_days: int = 0


@dataclass
class SourceStatus:
    """源状态追踪"""
    fail_count: int = 0
    last_success: Optional[datetime] = None
    is_degraded: bool = False


class HistoryManager:
    """
    历史记录管理器 - 结构化存储
    
    history.json 结构：
    {
        "records": {
            "content_hash": {
                "first_seen": "2024-01-01T00:00:00",
                "last_pushed": "2024-01-02T00:00:00",
                "push_count": 2,
                "last_score": 8,
                "title": "...",
                "source": "..."
            }
        },
        "consecutive_empty": 0
    }
    """
    
    # 历史记录最大条数
    MAX_HISTORY_SIZE = 2000
    
    def __init__(self, history_file: str = "history.json"):
        self.history_file = history_file
        self.history: Dict[str, dict] = {}
        self.consecutive_empty = 0  # 连续空推计数
        self._load()
    
    def _load(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 兼容旧格式
                    self.history = data.get("records", data)
                    self.consecutive_empty = data.get("consecutive_empty", 0)
                logger.info(f"📂 加载历史记录: {len(self.history)} 条, 连续空推: {self.consecutive_empty}")
            except:
                self.history = {}
    
    def save(self):
        try:
            # 清理超出的历史记录
            self._cleanup_history()
            
            data = {
                "records": self.history,
                "consecutive_empty": self.consecutive_empty,
                "last_update": datetime.now().isoformat()
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 保存历史记录: {len(self.history)} 条")
        except Exception as e:
            logger.error(f"保存历史失败: {e}")
    
    def _cleanup_history(self):
        """清理超出限制的历史记录"""
        if len(self.history) > self.MAX_HISTORY_SIZE:
            # 按 last_pushed 排序，删除最旧的
            sorted_items = sorted(
                self.history.items(),
                key=lambda x: x[1].get('last_pushed', '2000-01-01'),
                reverse=True
            )
            # 保留最新的 MAX_HISTORY_SIZE 条
            self.history = dict(sorted_items[:self.MAX_HISTORY_SIZE])
            removed = len(sorted_items) - self.MAX_HISTORY_SIZE
            logger.info(f"🧹 清理历史记录: 删除 {removed} 条旧记录")
    
    def _hash(self, title: str, link: str, source: str) -> str:
        """生成内容hash - 三元组去重"""
        title_norm = re.sub(r'\s+', '', title.lower())
        link_norm = link.strip().lower()
        source_norm = source.strip().lower()
        return hashlib.md5(f"{title_norm}|{link_norm}|{source_norm}".encode()).hexdigest()[:16]
    
    def check_duplicate(self, item: ContentItem) -> Tuple[bool, int]:
        """
        检查是否重复 - 精确匹配 + 模糊匹配
        
        策略：
        1. 精确匹配：title + url + source hash
        2. 模糊匹配：标题相似度 > 0.8
        """
        content_hash = self._hash(item.title, item.link, item.source)
        item.content_hash = content_hash
        
        # 1. 精确匹配
        if content_hash in self.history:
            record = self.history[content_hash]
            try:
                last_date = datetime.fromisoformat(record.get('last_pushed', '2000-01-01'))
                days_ago = (datetime.now() - last_date).days
                return True, days_ago
            except:
                return True, 0
        
        # 2. 模糊匹配：遍历历史记录查找相似标题
        SIMILARITY_THRESHOLD = 0.8
        for hash_key, record in self.history.items():
            stored_title = record.get('title', '')
            if not stored_title:
                continue
            
            similarity = title_similarity(item.title, stored_title)
            if similarity > SIMILARITY_THRESHOLD:
                logger.info(f"🔍 模糊匹配命中: '{item.title[:30]}...' ≈ '{stored_title[:30]}...' (相似度: {similarity:.2f})")
                try:
                    last_date = datetime.fromisoformat(record.get('last_pushed', '2000-01-01'))
                    days_ago = (datetime.now() - last_date).days
                    return True, days_ago
                except:
                    return True, 0
        
        return False, 0
    
    def is_cold_start(self) -> bool:
        """
        冷启动检测：连续2天空推
        
        返回 True 表示需要放宽策略（不是降低阈值）
        """
        return self.consecutive_empty >= 2
    
    def record_empty_push(self):
        """记录空推"""
        self.consecutive_empty += 1
    
    def record_successful_push(self, count: int):
        """记录成功推送"""
        if count > 0:
            self.consecutive_empty = 0
    
    def classify(self, item: ContentItem) -> str:
        """分类重复内容"""
        is_dup, days_ago = self.check_duplicate(item)
        item.duplicate_days = days_ago
        
        if not is_dup:
            item.status = 'new'
            return 'new'
        
        # 阈值底线不动，保持6分
        threshold = 6
        
        if days_ago <= 1:
            return 'suppress'
        elif days_ago <= 7:
            if item.quality_score >= threshold:
                item.status = 'repeat'
                return 'remind'
            return 'suppress'
        else:
            item.status = 'new'
            return 'new'
    
    def mark_pushed(self, item: ContentItem):
        """标记为已推送 - 结构化存储"""
        content_hash = item.content_hash or self._hash(item.title, item.link, item.source)
        now = datetime.now().isoformat()
        
        if content_hash in self.history:
            # 更新现有记录
            record = self.history[content_hash]
            record['last_pushed'] = now
            record['push_count'] = record.get('push_count', 1) + 1
            record['last_score'] = item.quality_score
        else:
            # 新记录
            self.history[content_hash] = {
                'first_seen': now,
                'last_pushed': now,
                'push_count': 1,
                'last_score': item.quality_score,
                'title': item.title[:50],
                'source': item.source
            }


class SourceHealthTracker:
    """
    源健康追踪器 - 抓取隔离层
    
    功能：
    - 每个源独立超时（5秒）
    - 失败计数
    - degraded标记（连续3次失败）
    """
    
    def __init__(self):
        self.sources: Dict[str, SourceStatus] = {}
        self.source_timeout = 5  # 单源超时5秒
        self.degrade_threshold = 3  # 连续3次失败标记为degraded
    
    def get_status(self, source: str) -> SourceStatus:
        if source not in self.sources:
            self.sources[source] = SourceStatus()
        return self.sources[source]
    
    def is_available(self, source: str) -> bool:
        """检查源是否可用"""
        status = self.get_status(source)
        return not status.is_degraded
    
    def record_success(self, source: str):
        """记录成功"""
        status = self.get_status(source)
        status.fail_count = 0
        status.last_success = datetime.now()
        status.is_degraded = False
    
    def record_failure(self, source: str):
        """记录失败"""
        status = self.get_status(source)
        status.fail_count += 1
        if status.fail_count >= self.degrade_threshold:
            status.is_degraded = True
            logger.warning(f"⚠️ 源 {source} 已标记为 degraded（连续失败{status.fail_count}次）")


class NewsFetcher:
    """
    信息抓取器 - 增强版
    
    增强特性：
    - 抓取隔离层
    - 去噪黑名单
    - 冷启动保护
    - 分类保底
    """
    
    # 分类定义（确保每个分类都有内容）
    CATEGORIES = ["GitHub热门", "自动化脚本", "AI新功能", "新模型咨询", "好用的工具"]
    
    # 来源权重
    SOURCE_WEIGHTS = {
        "GitHub": 1.5, "Hacker News": 1.3, "知乎": 1.0,
        "少数派": 1.0, "V2EX": 0.9, "IT之家": 0.8, "36氪": 0.8,
    }
    
    # 内容过期时间（小时）
    EXPIRE_HOURS = 48
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.history = HistoryManager()
        self.health = SourceHealthTracker()
    
    def fetch_all(self) -> dict:
        """获取所有内容"""
        result = {
            "GitHub热门": [],
            "自动化脚本": [],
            "AI新功能": [],
            "新模型咨询": [],
            "好用的工具": [],
            "统计面板": {
                "抓取总数": 0,
                "过滤过期": 0,
                "过滤黑名单": 0,
                "过滤压制": 0,
                "各分类数": {},
            }
        }
        
        # 第一步：动态抓取（带隔离）
        logger.info("📡 开始动态抓取...")
        all_items = []
        all_items.extend(self._fetch_github_trending())
        all_items.extend(self._fetch_ai_news())
        all_items.extend(self._fetch_automation_news())
        all_items.extend(self._fetch_tech_news())
        
        result["统计面板"]["抓取总数"] = len(all_items)
        logger.info(f"📊 抓取到 {len(all_items)} 条动态内容")
        
        # 第二步：过期过滤
        valid_items = []
        for item in all_items:
            if self._is_expired(item):
                result["统计面板"]["过滤过期"] += 1
                continue
            valid_items.append(item)
        
        # 第三步：分类 + 去重 + 黑名单过滤（黑名单需要评分）
        suppress_count = 0
        blacklisted = 0
        for item in valid_items:
            status = self.history.classify(item)
            if status == 'suppress':
                suppress_count += 1
                continue
            elif status == 'remind':
                item.quality_score = self._calc_score(
                    item.title, item.stars, item.source, item.publish_time, is_repeat=True
                )
            else:
                item.quality_score = self._calc_score(
                    item.title, item.stars, item.source, item.publish_time
                )
            
            # 黑名单过滤（需要评分）
            if self._is_blacklisted(item):
                blacklisted += 1
                continue
            
            # 添加到分类
            cat = item.category
            if cat in result:
                result[cat].append(item)
        
        result["统计面板"]["过滤压制"] = suppress_count
        result["统计面板"]["过滤黑名单"] = blacklisted
        if blacklisted > 0:
            logger.info(f"🚫 黑名单过滤: {blacklisted} 条")
        
        # 第四步：排序并确保每个分类都有内容
        for cat in self.CATEGORIES:
            # 排序
            result[cat] = sorted(result[cat], key=lambda x: x.quality_score, reverse=True)
            # 保底：如果分类为空，从静态资源补充
            if not result[cat]:
                logger.info(f"📚 {cat} 无内容，启用静态保底...")
                result[cat] = self._get_static_for_category(cat)
            result["统计面板"]["各分类数"][cat] = len(result[cat])
        
        # 第五步：记录历史
        total_pushed = sum(len(result[cat]) for cat in self.CATEGORIES)
        if total_pushed == 0:
            self.history.record_empty_push()
        else:
            self.history.record_successful_push(total_pushed)
            for cat in self.CATEGORIES:
                for item in result[cat]:
                    if item.status != 'static':
                        self.history.mark_pushed(item)
        
        self.history.save()
        
        return result
    
    def _is_blacklisted(self, item: ContentItem) -> bool:
        """
        检查黑名单 - 与评分联动
        
        原则：黑名单不单独生效，与评分联动
        只有 score < 5 且命中黑名单才过滤
        """
        title_lower = item.title.lower()
        for keyword in BLACKLIST_KEYWORDS:
            if keyword in title_lower:
                # 命中黑名单，检查评分
                # 如果评分已经很低才过滤
                if item.quality_score < 5:
                    return True
        return False
    
    def _is_expired(self, item: ContentItem) -> bool:
        """检查过期"""
        if not item.publish_time:
            return False
        try:
            pub_time = datetime.fromisoformat(item.publish_time.replace('Z', '+00:00'))
            if pub_time.tzinfo:
                pub_time = pub_time.replace(tzinfo=None)
            hours_ago = (datetime.now() - pub_time).total_seconds() / 3600
            return hours_ago > self.EXPIRE_HOURS
        except:
            return False
    
    def _get_static_for_category(self, category: str) -> List[ContentItem]:
        """获取分类的静态保底内容"""
        items = []
        resources = STATIC_RESOURCES.get(category, [])
        for tool in resources[:2]:  # 每个分类最多2条保底
            item = ContentItem(
                title=tool["name"],
                category=category,
                source="精选",
                link=tool["url"],
                description=tool.get("desc", ""),
                stars=tool.get("stars", 0),
                quality_score=7,
                status="static"
            )
            items.append(item)
        return items
    
    def _fetch_source(self, url: str, source: str) -> Optional[bytes]:
        """
        抓取单个源 - 带隔离保护
        """
        if not self.health.is_available(source):
            logger.warning(f"⏭️ 跳过 degraded 源: {source}")
            return None
        
        try:
            response = self.session.get(url, timeout=self.health.source_timeout)
            if response.status_code == 200:
                self.health.record_success(source)
                return response.content
            else:
                self.health.record_failure(source)
                return None
        except Exception as e:
            self.health.record_failure(source)
            logger.error(f"❌ {source} 错误: {e}")
            return None
    
    def _fetch_github_trending(self) -> List[ContentItem]:
        """GitHub热门"""
        items = []
        source = "GitHub"
        content = self._fetch_source("https://rsshub.app/github/trending/daily/any?limit=50", source)
        
        if content:
            feed = feedparser.parse(content)
            seen = set()
            for entry in feed.entries[:25]:
                title = entry.get('title', '')
                match = re.search(r'([^/]+/[^/\s]+)', title)
                name = match.group(1) if match else title
                
                if name in seen:
                    continue
                seen.add(name)
                
                summary = entry.get('summary', '') or ''
                stars = 0
                star_match = re.search(r'(\d+,?\d*)\s*star', summary, re.I)
                if star_match:
                    stars = int(star_match.group(1).replace(',', ''))
                
                # 分类判断
                category = "GitHub热门"
                name_lower = name.lower()
                if any(kw in name_lower for kw in ['auto', 'bot', 'automation', 'workflow', 'n8n', 'huginn']):
                    category = "自动化脚本"
                elif any(kw in name_lower for kw in ['ai', 'gpt', 'llm', 'chat', 'model', 'transformer']):
                    category = "AI新功能"
                elif any(kw in name_lower for kw in ['tool', 'util', 'helper', 'cli', 'app']):
                    category = "好用的工具"
                
                item = ContentItem(
                    title=name,
                    category=category,
                    source=source,
                    link=entry.get('link', ''),
                    description=self._clean(summary, 60),
                    stars=stars,
                    quality_score=self._calc_score(name, stars, source)
                )
                items.append(item)
        
        return items
    
    def _fetch_ai_news(self) -> List[ContentItem]:
        """AI动态 + 新模型咨询"""
        items = []
        sources = [
            ("https://rsshub.app/hackernews/best", "Hacker News"),
            ("https://rsshub.app/36kr/newsflashes", "36氪"),
        ]
        seen = set()
        
        for url, source in sources:
            content = self._fetch_source(url, source)
            if not content:
                continue
            
            feed = feedparser.parse(content)
            for entry in feed.entries[:20]:
                title = entry.get('title', '')
                key = re.sub(r'\s+', '', title.lower())[:30]
                if key in seen:
                    continue
                seen.add(key)
                
                pub_time = ""
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_time = datetime(*entry.published_parsed[:6]).isoformat()
                    except:
                        pass
                
                # 分类判断
                title_lower = title.lower()
                if any(kw in title_lower for kw in ['model', 'llm', 'gpt', 'release', '发布', '模型']):
                    category = "新模型咨询"
                else:
                    category = "AI新功能"
                
                item = ContentItem(
                    title=self._clean(title, 50),
                    category=category,
                    source=source,
                    link=entry.get('link', ''),
                    description=self._clean(entry.get('summary', ''), 60),
                    publish_time=pub_time,
                    quality_score=self._calc_score(title, 0, source, pub_time)
                )
                items.append(item)
        
        return items
    
    def _fetch_automation_news(self) -> List[ContentItem]:
        """自动化脚本"""
        items = []
        source = "Hacker News"
        content = self._fetch_source("https://rsshub.app/hackernews/best", source)
        
        if content:
            feed = feedparser.parse(content)
            seen = set()
            for entry in feed.entries[:20]:
                title = entry.get('title', '')
                title_lower = title.lower()
                
                # 只保留自动化相关
                if not any(kw in title_lower for kw in ['script', 'automation', 'tool', 'cli', 'api', 'workflow', 'bot']):
                    continue
                
                key = re.sub(r'\s+', '', title.lower())[:30]
                if key in seen:
                    continue
                seen.add(key)
                
                pub_time = ""
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_time = datetime(*entry.published_parsed[:6]).isoformat()
                    except:
                        pass
                
                item = ContentItem(
                    title=self._clean(title, 50),
                    category="自动化脚本",
                    source=source,
                    link=entry.get('link', ''),
                    description=self._clean(entry.get('summary', ''), 60),
                    publish_time=pub_time,
                    quality_score=self._calc_score(title, 0, source, pub_time)
                )
                items.append(item)
        
        return items
    
    def _fetch_tech_news(self) -> List[ContentItem]:
        """科技资讯 + 工具"""
        items = []
        sources = [
            ("https://rsshub.app/zhihu/hotlist", "知乎"),
            ("https://sspai.com/feed", "少数派"),
            ("https://www.v2ex.com/api/topics/hot.json", "V2EX"),
            ("https://rsshub.app/ithome/ranking", "IT之家"),
            ("https://rsshub.app/producthunt/today", "ProductHunt"),
        ]
        seen = set()
        
        for url, source in sources:
            content = self._fetch_source(url, source)
            if not content:
                continue
            
            if "v2ex" in url:
                try:
                    data = json.loads(content)
                    for topic in data[:15]:
                        title = topic.get('title', '')
                        key = re.sub(r'\s+', '', title.lower())[:30]
                        if key in seen:
                            continue
                        seen.add(key)
                        
                        created = topic.get('created', 0)
                        pub_time = datetime.fromtimestamp(created).isoformat() if created else ""
                        
                        title_lower = title.lower()
                        if any(kw in title_lower for kw in ['工具', 'tool', '推荐', '好用']):
                            category = "好用的工具"
                        else:
                            category = "AI新功能"
                        
                        item = ContentItem(
                            title=self._clean(title, 50),
                            category=category,
                            source=f"V2EX",
                            link=topic.get('url', ''),
                            publish_time=pub_time,
                            quality_score=self._calc_score(title, 0, "V2EX", pub_time)
                        )
                        items.append(item)
                except:
                    pass
            else:
                feed = feedparser.parse(content)
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    key = re.sub(r'\s+', '', title.lower())[:30]
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    pub_time = ""
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            pub_time = datetime(*entry.published_parsed[:6]).isoformat()
                        except:
                            pass
                    
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ['工具', 'tool', '推荐', '好用', 'app']):
                        category = "好用的工具"
                    else:
                        category = "AI新功能"
                    
                    item = ContentItem(
                        title=self._clean(title, 50),
                        category=category,
                        source=source,
                        link=entry.get('link', ''),
                        description=self._clean(entry.get('summary', ''), 60),
                        publish_time=pub_time,
                        quality_score=self._calc_score(title, 0, source, pub_time)
                    )
                    items.append(item)
        
        return items
    
    def _calc_score(self, title: str, stars: int = 0, source: str = "", 
                     publish_time: str = "", is_repeat: bool = False) -> int:
        """
        计算质量分数
        
        公式：基础分 + 关键词分 + 来源权重 + Stars加成 - 时间衰减 - 重复惩罚
        
        冷启动放宽策略（连续2天空推）：
        - 关键词加分增强：+3（原+2）
        - 时间衰减减半
        - 阈值底线不动，策略可以动
        
        软上限：防止评分爆炸，拉开中高分区区分度
        """
        score = 5.0
        text = title.lower()
        
        # 冷启动检测
        is_cold_start = self.history.is_cold_start()
        if is_cold_start:
            logger.info(f"⚠️ 冷启动放宽策略激活（连续空推{self.history.consecutive_empty}天）")
        
        # 关键词加分（冷启动时增强）
        keyword_bonus = 3 if is_cold_start else 2
        if any(kw in text for kw in ['ai', 'gpt', 'llm', '免费', 'free', '开源', 'open']):
            score += keyword_bonus
        if any(kw in text for kw in ['automation', '自动化', 'script', '脚本', 'tool', '工具']):
            score += keyword_bonus
        if any(kw in text for kw in ['api', 'sdk', 'cli']):
            score += 1
        
        # 来源权重
        source_weight = self.SOURCE_WEIGHTS.get(source, 1.0)
        score *= source_weight
        
        # Stars加成
        if stars > 10000:
            score += 2
        elif stars > 5000:
            score += 1
        
        # 时间衰减（冷启动时减半）
        if publish_time:
            try:
                pub_time = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
                if pub_time.tzinfo:
                    pub_time = pub_time.replace(tzinfo=None)
                hours_ago = (datetime.now() - pub_time).total_seconds() / 3600
                if hours_ago > 24:
                    decay = min(3.0, (hours_ago - 24) / 12 * 0.5)
                    if is_cold_start:
                        decay *= 0.5  # 冷启动时衰减减半
                    score -= decay
            except:
                pass
        
        # 重复惩罚
        if is_repeat:
            score -= 2
        
        # ===== 软上限：防止评分爆炸 =====
        # 原始分数上限为10，但高分区间压缩
        # 9分以上：只保留30%的超出部分
        if score > 9:
            score = 9 + (score - 9) * 0.3
        # 最终硬上限
        score = min(10, score)
        
        return max(1, int(score))
    
    def _clean(self, text: str, max_len: int = 60) -> str:
        """清理文本"""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_len] + "..." if len(text) > max_len else text


if __name__ == '__main__':
    fetcher = NewsFetcher()
    result = fetcher.fetch_all()
    
    print("\n" + "=" * 60)
    print("📊 分类结果")
    print("=" * 60)
    
    for cat in NewsFetcher.CATEGORIES:
        items = result.get(cat, [])
        print(f"\n【{cat}】{len(items)}条")
        for i, item in enumerate(items[:3], 1):
            status_tag = f"[{item.status}]" if item.status != 'new' else ""
            stars = f"⭐{item.stars:,}" if item.stars > 0 else ""
            print(f"  {i}. {item.title} {stars} {status_tag}")
    
    print(f"\n📈 统计面板:")
    for k, v in result["统计面板"].items():
        print(f"   {k}: {v}")
