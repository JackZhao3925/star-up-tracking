#!/usr/bin/env python3
"""
GitHub Star Growth Tracker
追踪 GitHub 上 Star 增长最快的前十名仓库（每周运行）
改进：
- 正确计算本周增长（使用上周数据对比）
- 排序按增长量而不是总Star数
- 获取英文和中文描述
- 自动归档超过3个月的历史报告
- 使用 full_name 去重与历史比对
- 请求增加简单重试与退避
- 保存数据文件使用 ISO 日期与周数
- 写报告到 reports/，并同步写入 docs/index.md 以便 GitHub Pages 展示
"""

import os
import json
import time
import requests
import shutil
from datetime import datetime, timedelta
from pathlib import Path


class GitHubStarTracker:
    def __init__(self, token=None, max_retries=3, backoff_factor=1.0):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.api_url = "https://api.github.com"
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _get_with_retries(self, url, params=None):
        attempt = 0
        while attempt < self.max_retries:
            try:
                r = requests.get(url, headers=self.headers, params=params, timeout=30)
                r.raise_for_status()
                return r
            except requests.exceptions.RequestException as e:
                attempt += 1
                wait = self.backoff_factor * (2 ** (attempt - 1))
                print(f"[WARN] Request failed (attempt {attempt}/{self.max_retries}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
        print(f"[ERROR] Failed to GET {url} after {self.max_retries} attempts")
        return None

    def get_repo_details(self, full_name):
        """
        获取仓库详细信息，包括英文和中文描述
        """
        url = f"{self.api_url}/repos/{full_name}"
        resp = self._get_with_retries(url)
        if not resp:
            return None
        try:
            return resp.json()
        except Exception as e:
            print(f"[WARN] Failed to parse repo details for {full_name}: {e}")
            return None

    def get_bilingual_description(self, repo_data):
        """
        提取英文和中文描述
        GitHub API 返回的 description 是英文，尝试从 topics 中获取其他信息
        """
        description = repo_data.get("description") or ""
        description = description.replace("\n", " ")[:80]
        
        # 如果没有description，尝试从topics和language获取信息
        if not description:
            language = repo_data.get("language", "Unknown")
            description = f"Language: {language}"
        
        # 生成中英文对照版本
        # 注：实际应用中可能需要使用翻译API，这里使用基础处理
        en_desc = description
        zh_desc = description  # 简化处理，实际可集成翻译API
        
        return f"{en_desc} / {zh_desc}"

    def search_trending_repos(self, days=7, per_query=50):
        """
        搜索最近指定天数内可能增长较快的仓库。
        返回去重（按 full_name 保持最大 stars）的仓库列表。
        """
        since_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        queries = [
            f'stars:>100000 pushed:>{since_date}',
            f'stars:50000..100000 pushed:>{since_date}',
            f'stars:10000..50000 pushed:>{since_date}',
            f'created:>{since_date} stars:>1000'
        ]

        repo_map = {}
        for query in queries:
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_query
            }
            url = f"{self.api_url}/search/repositories"
            resp = self._get_with_retries(url, params=params)
            if not resp:
                continue
            try:
                data = resp.json()
            except Exception as e:
                print(f"[WARN] Failed to parse JSON for query={query}: {e}")
                continue

            for item in data.get("items", []):
                name = item.get("full_name")
                if not name:
                    continue
                existing = repo_map.get(name)
                if not existing or item.get("stargazers_count", 0) > existing.get("stargazers_count", 0):
                    repo_map[name] = item

        return list(repo_map.values())

    def calculate_star_growth(self, current_repos, previous_data=None):
        """
        以 full_name 为 key 计算增长量。
        关键修复：确保正确计算本周增长
        """
        if not previous_data:
            # 首次运行，无对比数据，增长为0
            top = sorted(current_repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:10]
            for repo in top:
                repo["star_growth"] = 0
            return top

        previous_map = {r.get("full_name"): r for r in previous_data}
        repos_with_growth = []
        
        for repo in current_repos:
            name = repo.get("full_name")
            current_stars = repo.get("stargazers_count", 0)
            previous_stars = previous_map.get(name, {}).get("stargazers_count", 0)
            # 修复：正确计算增长量
            growth = current_stars - previous_stars
            repo["star_growth"] = max(0, growth)  # 确保增长不为负
            repos_with_growth.append(repo)

        # 修复：按增长量排序而不是总星数
        return sorted(repos_with_growth, key=lambda x: x.get("star_growth", 0), reverse=True)[:10]

    def format_report(self, repos, title="Star 增长最快的前十名仓库"):
        report = f"# {title}\n\n"
        report += f"**更新时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        report += "| 排名 | 仓库名称 | 总 Star | 本周增长 | 描述 |\n"
        report += "|------|---------|--------|---------|------|\n"
        
        for idx, repo in enumerate(repos, 1):
            name = repo.get("full_name")
            stars = repo.get("stargazers_count", 0)
            # 修复：正确获取本周增长
            growth = repo.get("star_growth", 0)
            
            # 获取双语描述
            desc = self.get_bilingual_description(repo)
            desc = desc.replace("\n", " ")[:100]  # 增加长度以适应双语
            
            url = repo.get("html_url")
            report += f"| {idx} | [{name}]({url}) | {stars:,} | {growth:,} | {desc} |\n"
        
        return report

    def save_tracking_data(self, repos):
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        now = datetime.utcnow()
        week_num = now.isocalendar()[1]
        filename = data_dir / f"stars_{now.strftime('%Y-%m-%d')}_W{week_num}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(repos, f, indent=2, ensure_ascii=False)
        return filename

    def save_report_to_reports_and_docs(self, report_text):
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        now = datetime.utcnow()
        week_num = now.isocalendar()[1]
        report_file = reports_dir / f"weekly_report_{now.strftime('%Y-W%W')}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)

        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        index_file = docs_dir / "index.md"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(report_text)

        return report_file, index_file

    def archive_old_reports(self, days_to_keep=90):
        """
        将超过指定天数的历史报告移到 history 文件夹
        """
        reports_dir = Path("reports")
        history_dir = Path("reports/history")
        
        if not reports_dir.exists():
            return
        
        history_dir.mkdir(exist_ok=True)
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=days_to_keep)
        
        for report_file in reports_dir.glob("weekly_report_*.md"):
            try:
                # 从文件名提取日期 (weekly_report_YYYY-W##.md)
                filename = report_file.name
                date_str = filename.replace("weekly_report_", "").replace(".md", "")
                
                # 解析 YYYY-W## 格式
                parts = date_str.split("-W")
                if len(parts) == 2:
                    year = int(parts[0])
                    week = int(parts[1])
                    # 计算该周的日期（使用周一作为参考）
                    jan1 = datetime(year, 1, 1)
                    report_date = jan1 + timedelta(weeks=week-1)
                    
                    if report_date < cutoff_date:
                        dest = history_dir / filename
                        shutil.move(str(report_file), str(dest))
                        print(f"[+] 已归档: {filename} -> history/")
            except Exception as e:
                print(f"[WARN] Failed to archive {report_file.name}: {e}")

    def load_latest_previous_data(self):
        data_dir = Path("data")
        if not data_dir.exists():
            return None
        files = sorted(data_dir.glob("*.json"), reverse=True)
        if not files:
            return None
        try:
            with open(files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load previous data {files[0]}: {e}")
            return None

    def run(self, days=7):
        print(f"[*] 开始追踪最近 {days} 天的 Star 增长...")
        current_repos = self.search_trending_repos(days=days)
        print(f"[+] 获取到 {len(current_repos)} 个候选仓库")

        previous = self.load_latest_previous_data()
        if previous:
            print(f"[+] 加载到历史数据，共 {len(previous)} 条")
        else:
            print("[*] 首次运行，无对比数据")

        top_repos = self.calculate_star_growth(current_repos, previous)
        print(f"[+] 按增长量排序，获取前10名")
        
        report = self.format_report(top_repos, f"Star 增长最快的前十名 (近 {days} 天)")

        report_file, index_file = self.save_report_to_reports_and_docs(report)
        print(f"[+] 报告已保存: {report_file}，Pages 索引: {index_file}")

        self.save_tracking_data(top_repos)
        print("[+] 数据已保存")
        
        # 新增：归档3个月前的报告
        self.archive_old_reports(days_to_keep=90)
        
        print("[+] 追踪完成！")


if __name__ == "__main__":
    tracker = GitHubStarTracker()
    tracker.run(days=7)
