# GitHub Star 增长追踪系统

每周从 GitHub Trending 页面抓取 star 增长最快的仓库，生成报告并通过邮件发送。

## 功能
- 每周自动追踪（每周日 08:00 UTC，北京时间 16:00）
- **Star 增长排行**（前十，直接从 GitHub Trending 页面抓取）
- 报告发布到 GitHub Pages（docs/index.md）
- 邮件通知（SMTP 发送到指定邮箱）

## 快速开始
```bash
git clone https://github.com/JackZhao3925/star-up-tracking.git
cd star-up-tracking
pip install -r requirements.txt
python scripts/track_stars.py
```

## 目录结构
```
.
├── scripts/
│   └── track_stars.py          # 主追踪脚本
├── docs/                       # GitHub Pages 发布目录
├── data/                       # 本地数据存档（gitignored）
├── reports/                    # 周度报告（gitignored）
└── requirements.txt
```

## GitHub Actions
工作流位于 `.github/workflows/weekly-star-tracker.yml`。

## GitHub Pages
在仓库设置 → Pages 中将 Source 设为 branch: main, folder: /docs。

## 环境变量 / Secrets
在 GitHub Settings → Secrets and variables → Actions 中配置：

| Secret | 说明 |
|--------|------|
| `SMTP_HOST` | 发件邮箱 SMTP 服务器，如 `smtp.163.com` |
| `SMTP_USER` | 发件邮箱地址 |
| `SMTP_PASS` | 发件邮箱的 SMTP 授权码 |
| `EMAIL_RECIPIENT` | 收件人邮箱（默认 `jackzhao3925@163.com`） |
