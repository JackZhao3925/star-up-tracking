# 🌟 GitHub Star 增长追踪系统

自动追踪 GitHub 上 Star 增长最快的仓库，每周自动生成报告。

## 📊 功能特性

- ✅ **每周自动追踪** - 每周日 16:00（北京时间）自动运行
- ✅ **Star 增长排行** - 自动计算并排序 Star 增长最快的前十名仓库
- ✅ **历史数据保存** - 保存每周的追踪数据，方便后续分析
- ✅ **自动生成报告** - 每周生成 Markdown 格式的追踪报告
- ✅ **月度汇总** - 自动生成月度汇总报告

## 📁 项目结构

```
star-up-tracking/
├── .github/
│   └── workflows/
│       └── weekly-star-tracker.yml      # GitHub Actions 工作流
├── scripts/
│   ├── track_stars.py                   # 主追踪脚本
│   └── generate_monthly_report.py       # 月度报告生成脚本
├── data/                                # 追踪数据存储目录
│   └── stars_week_*.json               # 每周的追踪数据
├── reports/                             # 报告存储目录
│   ├── weekly_report_*.md              # 每周报告
│   └── monthly_report_*.md             # 每月报告
└── README.md
```

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/JackZhao3925/star-up-tracking.git
cd star-up-tracking
```

### 2. 手动运行追踪
```bash
python scripts/track_stars.py
```

### 3. 查看报告
追踪完成后，查看 `reports/` 目录中的 Markdown 报告文件。

## ⚙️ 配置说明

### GitHub Actions 工作流

工作流配置在 `.github/workflows/weekly-star-tracker.yml` 中：

- **运行时间**: 每周日 08:00 UTC（北京时间周日 16:00）
- **手动触发**: 点击 GitHub Actions 标签页中的 "Run workflow" 按钮

### 修改追踪周期

如需修改运行频率，编辑 `.github/workflows/weekly-star-tracker.yml`：

```yaml
schedule:
  # 每周日运行
  - cron: '0 8 * * 0'
  
  # 或每日运行
  # - cron: '0 8 * * *'
  
  # 或每月运行
  # - cron: '0 8 1 * *'
```

参考 [Cron 表达式文档](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#schedule)

## 📈 数据输出示例

### 周度报告示例

```markdown
# Star 增长最快的前十名 (近 7 天)

**更新时间**: 2026-06-24 16:00:00 UTC

| 排名 | 仓库名称 | 总 Star | 本周增长 | 描述 |
|------|---------|--------|---------|------|
| 1 | [headroom](https://github.com/...) | 50,000 | 14,000 | AI Token 压缩工具 |
| 2 | [hermes-agent](https://github.com/...) | 190,000 | 11,400 | 通用 AI 智能体平台 |
| ... | ... | ... | ... | ... |
```

### 月度报告示例

```markdown
# GitHub Star 增长月度汇总

**统计周期**: 2026-06

| 排名 | 仓库 | 总 Star | 月度增长 | 出现次数 |
|------|------|--------|---------|---------|
| 1 | [项目名](链接) | 100,000 | 50,000 | 4 |
| ... | ... | ... | ... | ... |
```

## 📊 查看追踪结果

### 在线查看

1. 访问本仓库的 GitHub Pages（如已启用）
2. 或在本仓库中查看 `reports/` 目录中的 Markdown 文件

### 本地查看

```bash
# 查看最新周报
cat reports/weekly_report_*.md | tail -1

# 查看所有数据
ls -la data/
ls -la reports/
```

## 🔧 自定义追踪

### 修改追踪范围

编辑 `scripts/track_stars.py` 中的 `search_trending_repos()` 方法：

```python
def search_trending_repos(self, days=7):
    """可调整 days 参数："""
    # days=7    # 追踪最近7天
    # days=30   # 追踪最近30天
    # days=365  # 追踪最近一年
```

### 修改筛选条件

```python
queries = [
    f'stars:>100000 pushed:>{since_date}',  # 100K+ stars
    f'stars:50000..100000 pushed:>{since_date}',  # 50K-100K stars
    f'stars:10000..50000 pushed:>{since_date}',   # 10K-50K stars
]
```

### 修改返回数量

```python
# 修改此行以改变返回的 Top N 数量
return sorted(...)[: 10]  # 改为其他数字
```

## 📚 依赖项

- Python 3.11+
- `requests` - HTTP 库
- `pandas` - 数据处理
- `python-dateutil` - 日期处理

自动安装（在 GitHub Actions 中）或手动安装：

```bash
pip install -r requirements.txt
```

## 🔑 必要权限

- `GITHUB_TOKEN` - 自动提供（GitHub Actions）
- 或手动设置环境变量 `GITHUB_TOKEN` 以使用更高的 API 速率限制

## 📝 日志和调试

### 查看工作流运行日志

1. 访问仓库的 "Actions" 标签
2. 选择 "Weekly Star Growth Tracker" 工作流
3. 点击最新的运行记录
4. 查看"Track star growth"步骤的输出

### 本地调试

```bash
export GITHUB_TOKEN=your_token_here
python scripts/track_stars.py
```

## 📊 API 限制说明

GitHub API 限制：
- 未认证请求: 60 请求/小时
- 认证请求: 5,000 请求/小时

本脚本使用 GitHub Token 认证，使用配额约为 50-100 请求/周

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 💡 建议和改进

如有任何建议或发现问题，请提交 Issue。

---

**更新于**: 2026-06-24

**下一次自动运行**: 2026-06-30 08:00 UTC（周日）
