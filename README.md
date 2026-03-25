# 每日课表推送系统

自动获取教务系统课表并推送到微信。

## 功能特点

- 自动登录教务系统（支持验证码自动识别）
- 获取当日课程安排
- 每天早上 7:30 自动推送到微信

## 配置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 |
|------------|------|
| `STUDENT_ID` | 学号 |
| `STUDENT_PASSWORD` | 教务系统密码 |
| `SERVERCHAN_SENDKEY` | Server酱Turbo SendKey（从 https://sct.ftqq.com/ 获取）|

## 手动触发

在 GitHub Actions 页面点击 "Run workflow" 可手动触发。

## 定时执行

每天东京时间早上 7:30 自动执行。

## 自定义配置

如需修改学期或开学日期，请编辑 `schedule_fetcher.py` 文件中的以下配置：

```python
SEMESTER = "2025-2026-2"          # 学期
FIRST_DAY = datetime(2026, 3, 6)  # 开学第一周周一
```

## 支持的教务系统

- 强智教务系统（智慧校园平台）
