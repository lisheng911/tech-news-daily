# 科技新闻每日推送系统

自动抓取科技新闻并推送到微信。

## 配置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `NEWSDATA_API_KEY` | NewsData.io API密钥 | https://newsdata.io/ 注册获取 (可选，不配置则使用RSS) |
| `SERVERCHAN_SENDKEY` | Server酱Turbo SendKey | https://sct.ftqq.com/ 登录获取 |

## 手动触发

在 GitHub Actions 页面点击 "Run workflow" 可手动触发。

## 定时执行

每天东京时间早上8点自动执行。
