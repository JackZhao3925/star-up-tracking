#!/usr/bin/env python3
"""
GitHub Star Growth Tracker
追踪 GitHub 上 Star 增长最快的前十名仓库
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path


class GitHubStarTracker:
    def __init__(self, token=None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.api_url = "https://api.github.com"
        
    def search_trending_repos(self, days=7):
        """
        搜索最近指定天数内 Star 增长最快的仓库
        
        Args:
            days: 追踪天数（默认7天=1周）
            
        Returns:
            list: 仓库列表
        """
        # 计算指定天数前的日期
        since_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # GitHub 搜索查询：找出最近创建或更新的高 Star 仓库
        # 使用多个查询合并，获取不同热度等级的仓库
        queries = [
            f'stars:>100000 pushed:>{since_date}',
            f'stars:50000..100000 pushed:>{since_date}',
            f'stars:10000..50000 pushed:>{since_date}',
        ]
        
        all_repos = []
        
        for query in queries:
            try:
                response = requests.get(
                    f"{self.api_url}/search/repositories",
                    headers=self.headers,
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 50
                    }
                )
                response.raise_for_status()
                data = response.json()
                all_repos.extend(data.get("items", []))
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching repos with query '{query}': {e}")
                continue
        
        return all_repos
    
    def calculate_star_growth(self, current_repos, previous_data=None):
        """
        计算 Star 增长情况
        
        Args:
            current_repos: 当前仓库数据
            previous_data: 上次追踪数据（用于计算增长量）
            
        Returns:
            list: 按增长量排序的仓库列表
        """
        if not previous_data:
            # 首次运行，直接返回 Top 10
            return sorted(
                current_repos,
                key=lambda x: x["stargazers_count"],
                reverse=True
            )[:10]
        
        # 建立仓库映射
        previous_map = {repo["id"]: repo for repo in previous_data}
        
        repos_with_growth = []
        for repo in current_repos:
            repo_id = repo["id"]
            current_stars = repo["stargazers_count"]
            previous_stars = previous_map.get(repo_id, {}).get("stargazers_count", 0)
            growth = current_stars - previous_stars
            
            repo["star_growth"] = growth
            repos_with_growth.append(repo)
        
        # 按增长量排序
        return sorted(
            repos_with_growth,
            key=lambda x: x["star_growth"],
            reverse=True
        )[:10]
    
    def format_report(self, repos, title="Star 增长最快的前十名仓库"):
        """格式化报告"""
        report = f"# {title}\n\n"
        report += f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        report += "| 排名 | 仓库名称 | 总 Star | 本周增长 | 描述 |\n"
        report += "|------|---------|--------|---------|------|\n"
        
        for idx, repo in enumerate(repos, 1):
            name = repo["full_name"]
            stars = repo["stargazers_count"]
            growth = repo.get("star_growth", "-")
            description = repo.get("description", "N/A")[:50] if repo.get("description") else "N/A"
            url = repo["html_url"]
            
            report += f"| {idx} | [{name}]({url}) | {stars:,} | {growth:,} | {description} |\n"
        
        return report
    
    def save_tracking_data(self, repos, week_num=None):
        """保存追踪数据"""
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        if week_num is None:
            week_num = datetime.now().isocalendar()[1]
        
        filename = data_dir / f"stars_week_{week_num}_{datetime.now().year}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(repos, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def run(self, days=7):
        """执行追踪"""
        print(f"[*] 开始追踪最近 {days} 天的 Star 增长...")
        
        # 获取当前仓库数据
        current_repos = self.search_trending_repos(days=days)
        print(f"[+] 获取到 {len(current_repos)} 个仓库")
        
        # 读取历史数据（如果存在）
        previous_data = None
        data_dir = Path("data")
        if data_dir.exists():
            files = sorted(data_dir.glob("*.json"), reverse=True)
            if files:
                try:
                    with open(files[0], "r", encoding="utf-8") as f:
                        previous_data = json.load(f)
                        print(f"[+] 加载历史数据: {files[0].name}")
                except Exception as e:
                    print(f"[-] 无法加载历史数据: {e}")
        
        # 计算增长
        top_repos = self.calculate_star_growth(current_repos, previous_data)
        
        # 生成报告
        report = self.format_report(top_repos, f"Star 增长最快的前十名 (近 {days} 天)")
        
        # 保存报告
        report_path = Path(f"reports/weekly_report_{datetime.now().strftime('%Y-W%W')}.md")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[+] 报告已保存: {report_path}")
        
        # 更新 README
        self.update_readme(top_repos)
        
        # 保存数据
        self.save_tracking_data(top_repos)
        print("[+] 追踪完成！")
    
    def update_readme(self, repos):
        """更新 README 文件"""
        readme_path = Path("README.md")
        
        report = "## 📊 最新一周 Star 增长最快的前十名\n\n"
        report += f"**更新于**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        report += "| 排名 | 仓库 | 总 Star | 本周增长 | 描述 |\n"
        report += "|------|------|--------|---------|------|\n"
        
        for idx, repo in enumerate(repos[:10], 1):
            name = repo["full_name"]
            stars = repo["stargazers_count"]
            growth = repo.get("star_growth", "-")
            description = repo.get("description", "N/A")[:40] if repo.get("description") else "N/A"
            url = repo["html_url"]
            
            report += f"| {idx} | [{name}]({url}) | {stars:,} | {growth:,} | {description} |\n"
        
        # 更新或创建 README
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 替换或添加表格部分
            if "## 📊 最新一周" in content:
                # 替换存在的部分
                start = content.find("## 📊 最新一周")
                end = content.find("\n## ", start + 1)
                if end == -1:
                    end = len(content)
                content = content[:start] + report + content[end:]
            else:
                # 添加到文件顶部（在第一个 ## 之后）
                first_section = content.find("\n## ")
                if first_section != -1:
                    content = content[:first_section + 1] + report + "\n" + content[first_section + 1:]
                else:
                    content = report + "\n\n" + content
        else:
            content = f"# GitHub Star 增长追踪\n\n{report}"
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] README 已更新")


if __name__ == "__main__":
    tracker = GitHubStarTracker()
    tracker.run(days=7)
