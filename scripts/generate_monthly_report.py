#!/usr/bin/env python3
"""
生成每月 Star 增长汇总报告
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def generate_monthly_report():
    """生成月度报告"""
    data_dir = Path("data")
    reports_dir = Path("reports")
    
    if not data_dir.exists():
        print("[-] 数据目录不存在，无法生成报告")
        return
    
    # 收集本月的数据
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    repo_stats = defaultdict(lambda: {
        "max_stars": 0,
        "appearances": 0,
        "growth_total": 0,
        "latest_data": None
    })
    
    # 读取所有数据文件
    for data_file in sorted(data_dir.glob("*.json")):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                repos = json.load(f)
            
            for repo in repos:
                repo_id = repo["full_name"]
                stars = repo["stargazers_count"]
                growth = repo.get("star_growth", 0)
                
                stats = repo_stats[repo_id]
                stats["max_stars"] = max(stats["max_stars"], stars)
                stats["appearances"] += 1
                stats["growth_total"] += growth
                stats["latest_data"] = repo
        
        except Exception as e:
            print(f"[-] 读取文件失败 {data_file}: {e}")
            continue
    
    if not repo_stats:
        print("[-] 没有可用的追踪数据")
        return
    
    # 生成报告
    report = f"# 📈 GitHub Star 增长月度汇总\n\n"
    report += f"**统计周期**: {current_year}-{current_month:02d}\n"
    report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    
    # 按总增长量排序
    sorted_repos = sorted(
        repo_stats.items(),
        key=lambda x: x[1]["growth_total"],
        reverse=True
    )[:10]
    
    report += "## 🏆 本月 Star 增长最快的仓库\n\n"
    report += "| 排名 | 仓库 | 总 Star | 月度增长 | 出现次数 |\n"
    report += "|------|------|--------|---------|----------|\n"
    
    for idx, (repo_name, stats) in enumerate(sorted_repos, 1):
        stars = stats["max_stars"]
        growth = stats["growth_total"]
        appearances = stats["appearances"]
        latest = stats["latest_data"]
        url = latest["html_url"] if latest else "#"
        
        report += f"| {idx} | [{repo_name}]({url}) | {stars:,} | {growth:,} | {appearances} |\n"
    
    # 保存报告
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / f"monthly_report_{current_year}-{current_month:02d}.md"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"[+] 月度报告已生成: {report_file}")


if __name__ == "__main__":
    generate_monthly_report()
