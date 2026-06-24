# 🌟 GitHub Star 增长追踪系统

自动追踪 GitHub 上 Star 增长最快的仓库，每周自动生成报告并发布到 GitHub Pages（docs/）。

## 功能
- 每周自动追踪（每周日 08:00 UTC）
- Star 增长排行（前十）
- 历史数据保存（data/）
- 周度报告保存在 reports/，并发布到 pages（docs/index.md）

## 快速开始
git clone https://github.com/JackZhao3925/star-up-tracking.git
cd star-up-tracking
pip install -r requirements.txt
python scripts/track_stars.py

## GitHub Actions
工作流位于 .github/workflows/weekly-star-tracker.yml（自动在 main/docs 更新报告以供 Pages 使用）。

## GitHub Pages
在仓库设置 → Pages 中将 Source 设为 branch: main, folder: /docs，然后保存。Pages URL 通常为:
https://<your-username>.github.io/star-up-tracking/
