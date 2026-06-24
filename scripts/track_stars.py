#!/usr/bin/env python3
"""
GitHub Star Growth Tracker
每周从 GitHub Trending 页面抓取 star 增长最快的仓库，
生成报告并通过邮件发送。
"""

import os
import re
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html.parser import HTMLParser
from pathlib import Path


# ── HTML 解析器 ──────────────────────────────────────────────

class TrendingArticleParser(HTMLParser):
    """从 Trending 页面提取 <article> 标签中的仓库信息。"""

    def __init__(self):
        super().__init__()
        self.repos = []
        self._in_article = False
        self._in_link = False
        self._in_h2 = False
        self._in_spn = False  # star count span
        self._in_p = False    # description paragraph
        self._buf = ""
        self._repo_idx = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")

        if tag == "article" and "Box-row" in cls:
            self._in_article = True
            self._repo_idx += 1
            self._buf = ""

        if not self._in_article:
            return

        if tag == "h2":
            self._in_h2 = True
            self._buf = ""
        elif tag == "a" and self._in_h2:
            href = attr_dict.get("href", "")
            if href:
                self.repo_name = href.strip("/")
            self._in_link = True
            self._buf = ""

        elif tag == "span" and "d-inline" in cls and "float-sm-right" in cls:
            self._in_spn = True
            self._buf = ""
        elif tag == "p" and "col-9" in cls:
            self._in_p = True
            self._buf = ""

    def handle_endtag(self, tag):
        if not self._in_article:
            return

        if tag == "h2":
            self._in_h2 = False
        elif tag == "a" and self._in_link:
            self._in_link = False
        elif tag == "span":
            self._in_spn = False
        elif tag == "p":
            self._in_p = False

        if tag == "article" and self._in_article:
            self._in_article = False
            if hasattr(self, "repo_name"):
                self.repos.append({
                    "full_name": getattr(self, "repo_name", ""),
                    "stars_this_week": getattr(self, "stars_week", "0"),
                    "description": getattr(self, "desc", ""),
                })

    def handle_data(self, data):
        if not self._in_article:
            return
        if self._in_link:
            self._buf += data
        elif self._in_spn:
            self._buf += data
        elif self._in_p:
            self._buf += data

        # Flush buffer when leaving the tag
        if not (self._in_link or self._in_spn or self._in_p):
            pass

    # Override to flush on tag close
    def handle_endtag_real(self, tag):
        pass

    def _flush_buffers(self):
        text = self._buf.strip()
        if self._in_link is False and text:
            pass
        self._buf = ""


class BetterTrendingParser(HTMLParser):
    """更稳健的 Trending 解析器，逐标签收集数据。"""

    def __init__(self):
        super().__init__()
        self.repos = []
        self._in_article = False
        self._repo = {}
        # State tracking for buffered content
        self._buffer = ""
        self._buffer_target = None  # "name", "stars", "desc"

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")

        # Start of a repo article row
        if tag == "article" and "Box-row" in cls:
            self._in_article = True
            self._repo = {}
            self._buffer = ""
            self._buffer_target = None

        if not self._in_article:
            return

        # Repository link: <h2><a href="owner/repo">
        if tag == "h2":
            self._buffer_target = "name"
            self._buffer = ""
        elif tag == "a" and self._buffer_target == "name":
            href = attr_dict.get("href", "")
            if href:
                self._repo["full_name"] = href.strip("/")

        # Star count: <span class="d-inline ... float-sm-right">
        elif tag == "svg" and self._buffer_target == "name":
            # Skip SVG icon inside h2
            pass
        elif tag == "span" and "float-sm-right" in cls:
            self._buffer_target = "stars"
            self._buffer = ""

        # Description: <p class="col-9 ...
        elif tag == "p" and "col-9" in cls:
            self._buffer_target = "desc"
            self._buffer = ""

    def handle_endtag(self, tag):
        if not self._in_article:
            return

        if tag == "h2" and self._buffer_target == "name":
            self._buffer_target = None
        elif tag == "span" and self._buffer_target == "stars":
            stars_text = self._buffer.strip()
            self._repo["stars_this_week"] = stars_text
            self._buffer_target = None
        elif tag == "p" and self._buffer_target == "desc":
            desc_text = self._buffer.strip()
            # Strip HTML entities
            desc_text = desc_text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            desc_text = re.sub(r"&#[0-9]+;", "", desc_text)
            self._repo["description"] = desc_text
            self._buffer_target = None

        if tag == "article" and self._in_article:
            self._in_article = False
            if "full_name" in self._repo:
                self.repos.append(self._repo)

    def handle_data(self, data):
        if not self._in_article or not self._buffer_target:
            return
        if self._buffer_target == "stars":
            # Star count looks like "1,234 stars this week" or "1,234 star this week"
            self._buffer += data
        elif self._buffer_target in ("name", "desc"):
            self._buffer += data


# ── HTTP 请求 ──────────────────────────────────────────────

def fetch_trending_page(max_retries=3):
    """Fetch the GitHub Trending weekly page."""
    url = "https://github.com/trending?since=weekly"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    import requests

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Fetch failed (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                import time
                time.sleep(2 ** attempt)
    return None


def parse_trending_html(html):
    """Parse HTML and return list of repo dicts."""
    parser = BetterTrendingParser()
    parser.feed(html)
    return parser.repos


# ── 报告生成 ──────────────────────────────────────────────

def format_report(repos, top_n=10):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    top = repos[:top_n]

    md = f"# Star 增长最快的前十名仓库 (本周)\n\n"
    md += f"**更新时间**: {now}\n\n"
    md += "| 排名 | 仓库名称 | 本周 Star 增长 | 描述 |\n"
    md += "|------|---------|-------------|------|\n"

    for idx, repo in enumerate(top, 1):
        name = repo.get("full_name", "?")
        stars = repo.get("stars_this_week", "?")
        desc = (repo.get("description") or "").replace("|", "\\|")[:120]
        url = f"https://github.com/{name}"
        md += f"| {idx} | [{name}]({url}) | {stars} | {desc} |\n"

    return md, top


# ── 邮件发送 ──────────────────────────────────────────────

def send_email(report_md, repos_top10):
    """Send report via SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.163.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    recipient = os.getenv("EMAIL_RECIPIENT", "jackzhao3925@163.com")

    if not smtp_user or not smtp_pass:
        print("[WARN] SMTP_USER / SMTP_PASS not set, skipping email.")
        return

    subject = f"每周 Star 增长排行 — {datetime.utcnow().strftime('%Y-%m-%d')}"

    # Build HTML body from markdown table
    html_body = f"<h2>每周 Star 增长最快的前十名仓库</h2>\n"
    html_body += f"<p>更新时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>\n"
    html_body += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;'>\n"
    html_body += "<tr><th>排名</th><th>仓库</th><th>本周增长</th><th>描述</th></tr>\n"
    for idx, repo in enumerate(repos_top10, 1):
        name = repo.get("full_name", "?")
        stars = repo.get("stars_this_week", "?")
        desc = (repo.get("description") or "")[:150]
        html_body += f"<tr><td>{idx}</td><td><a href='https://github.com/{name}'>{name}</a></td><td>{stars}</td><td>{desc}</td></tr>\n"
    html_body += "</table>\n"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText(report_md, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[+] 邮件已发送至 {recipient}")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")


# ── 主流程 ──────────────────────────────────────────────

def save_report(md_text, repos):
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    with open(docs_dir / "index.md", "w", encoding="utf-8") as f:
        f.write(md_text)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    now = datetime.utcnow()
    week_file = reports_dir / f"weekly_report_{now.strftime('%Y-W%U')}.md"
    with open(week_file, "w", encoding="utf-8") as f:
        f.write(md_text)

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    data_file = data_dir / f"stars_{now.strftime('%Y-%m-%d')}.json"
    with open(data_file, "w", encoding="utf-8") as f:
        import json
        json.dump(repos, f, indent=2, ensure_ascii=False)

    print(f"[+] 报告已保存到 docs/index.md")
    print(f"[+] 数据已保存到 {data_file}")


def run():
    print("[*] 正在抓取 GitHub Trending (weekly)...")
    html = fetch_trending_page()
    if not html:
        print("[ERROR] 无法获取 Trending 页面")
        return

    repos = parse_trending_html(html)
    print(f"[+] 获取到 {len(repos)} 个仓库")

    if not repos:
        print("[ERROR] 解析结果为空，请检查 HTML 结构是否变化")
        return

    md_text, top10 = format_report(repos, top_n=10)
    print(md_text)

    save_report(md_text, top10)
    send_email(md_text, top10)
    print("[+] 完成!")


if __name__ == "__main__":
    run()
