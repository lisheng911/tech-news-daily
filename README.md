# 每日精选推送系统

自动抓取国内AI工具、GitHub热门项目、自动化脚本等高价值内容，每天推送到微信。

## 功能特点

- 🤖 国内AI工具推荐（DeepSeek、Kimi、iFlow CLI等）
- 📦 GitHub热门项目（自动筛选实用工具）
- 📰 技术资讯精选（V2EX、少数派、Hacker News等）
- 💡 智能评分筛选，只推送高价值内容

## 配置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 |
|------------|------|
| `SERVERCHAN_SENDKEY` | Server酱Turbo SendKey（从 https://sct.ftqq.com/ 获取）|

## 手动触发

在 GitHub Actions 页面点击 "Run workflow" 可手动触发。

## 定时执行

每天北京时间早上 8:00 自动执行。

## 筛选规则

系统会自动评分并筛选高价值内容：

- ✅ 自动化脚本、CLI工具 (+3分)
- ✅ AI/大模型相关 (+2分)
- ✅ 创业/副业相关 (+2分)
- ✅ 高Stars项目 (+1~2分)
- ❌ 广告、推广内容 (-2分)

只推送评分 ≥6 分的内容。

## 数据来源

- 国内AI工具（静态列表）
- GitHub Trending（RSSHub）
- V2EX热门话题
- 少数派、36氪、知乎热榜
- Hacker News、Product Hunt