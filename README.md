# 🌟 GitHub Star 增长追踪系统

自动追踪 GitHub 上 Star 增长最快的仓库，每周自动生成报告并发布到 GitHub Pages（docs/）。

## 功能
- 每周自动追踪（每周日 08:00 UTC）
- **Star 增长排行**（前十，按增长量排序而非总星数）
- 历史数据保存（data/）
- 周度报告保存在 reports/，并发布到 pages（docs/index.md）
- **自动归档机制**：超过 3 个月的报告自动移至 reports/history/

## 核心改进

### ✅ 修复的问题
1. **本周增长数据** - 现在正确计算与上周数据的对比
2. **排序逻辑** - 改为按 Star 增长量排序（而非总星数）
3. **双语描述** - 描述字段同时包含英文和中文对照
4. **历史管理** - 超过 90 天的报告自动归档到 history/ 文件夹

### 📊 数据格式示例

| 排名 | 仓库名称 | 总 Star | 本周增长 | 描述 |
|------|---------|--------|---------|------|
| 1 | owner/repo | 10,000 | 500 | English description / 中文描述 |

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
├── data/                       # 追踪数据存档
├── reports/                    # 周度报告
│   └── history/               # 超过3个月的历史报告
├── docs/                       # GitHub Pages 发布目录
└── requirements.txt
```

## GitHub Actions
工作流位于 `.github/workflows/weekly-star-tracker.yml`（自动在 main/docs 更新报告以供 Pages 使用）。

## GitHub Pages
在仓库设置 → Pages 中将 Source 设为 branch: main, folder: /docs，然后保存。Pages URL 通常为:
https://<your-username>.github.io/star-up-tracking/

## 环境变量
- `GITHUB_TOKEN` (可选) - GitHub API Token，用于增加请求限制
