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
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from bs4 import BeautifulSoup




# ── 翻译 ──────────────────────────────────────────────────────

def translate(text: str) -> str:
    """将英文描述翻译成简体中文。
    优先使用 OpenAI 翻译（需 OPENAI_API_KEY），
    无 key 时用免费的 Google 翻译 API 兜底。
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import importlib
            openai_mod = importlib.import_module("openai")
            OpenAI = getattr(openai_mod, "OpenAI")
            client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Translate the following English text to Simplified Chinese. Output ONLY the Chinese text, nothing else."},
                    {"role": "user", "content": text[:200]},
                ],
                temperature=0.3,
                timeout=10,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # 免费 Google 翻译 API 兜底
    try:
        import importlib
        urllib = importlib.import_module("urllib.request")
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={requests.utils.quote(text[:200])}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            result = __import__("json").loads(r.read().decode())
            return "".join(s[0] for s in result[0] if s[0])
    except Exception:
        pass

    # 最终兜底：返回原文
    return text


# ── HTTP 请求 ──────────────────────────────────────────────

def fetch_trending_page(max_retries: int = 3) -> str | None:
    """Fetch the GitHub Trending weekly page."""
    url = "https://github.com/trending?since=weekly"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Fetch failed (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time_sleep(2 ** attempt)
    return None


def time_sleep(seconds: float) -> None:
    """Import time.sleep lazily to avoid top-level import in type hints."""
    import time
    time.sleep(seconds)


def parse_trending_html(html: str) -> list[dict]:
    """Parse GitHub Trending HTML and return list of repo dicts."""
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.Box-row")
    repos = []

    for article in articles:
        # Repo name: <h2><a href="owner/repo">
        h2_link = article.select_one("h2 a")
        if not h2_link:
            continue
        name = h2_link.get_text(strip=True)
        # Clean up extra spaces in name (e.g. "calesthio /OpenMontage" → "calesthio/OpenMontage")
        name = re.sub(r"\s+", "", name).strip("/")
        # Ensure owner/repo format
        if "/" not in name:
            continue

        # Star count: <span class="float-sm-right">
        span = article.select_one("span.float-sm-right")
        stars_raw = span.get_text(strip=True) if span else "?"
        # Parse "9,410 stars this week" → "9,410"
        stars_clean = re.sub(r"(?i)\s*stars?\s*this\s*week\s*", "", stars_raw).strip()

        # Description: <p class="col-9">
        p = article.select_one("p.col-9")
        desc = p.get_text(strip=True) if p else ""

        repos.append({
            "full_name": name,
            "stars_this_week": stars_clean,
            "stars_raw": stars_raw,
            "description": desc,
        })

    return repos


# ── 报告生成 ──────────────────────────────────────────────

def format_report(repos: list[dict], top_n: int = 10) -> tuple[str, list[dict]]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    top = repos[:top_n]

    md = f"# Star 增长最快的前十名仓库 (本周)\n\n"
    md += f"**更新时间**: {now}\n\n"
    md += "| 排名 | 仓库名称 | 本周 Star 增长 | 描述 |\n"
    md += "|------|---------|-------------|------|\n"

    for idx, repo in enumerate(top, 1):
        name = repo.get("full_name", "?")
        stars = repo.get("stars_this_week", "?")
        en_desc = repo.get("description") or ""
        zh_desc = translate(en_desc)
        desc = f"{en_desc} / {zh_desc}".replace("|", "\\|")[:120]
        url = f"https://github.com/{name}"
        md += f"| {idx} | [{name}]({url}) | {stars} | {desc} |\n"

    return md, top


# ── 邮件发送 ──────────────────────────────────────────────

def send_email(report_md: str, repos_top10: list[dict]) -> None:
    """Send report via SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.163.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    recipient = os.getenv("EMAIL_RECIPIENT", "jackzhao3925@163.com")

    if not smtp_user or not smtp_pass:
        print("[WARN] SMTP_USER / SMTP_PASS not set, skipping email.")
        return

    subject = f"每周 Star 增长排行 — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    # Build HTML body
    html_body = f"<h2>每周 Star 增长最快的前十名仓库</h2>\n"
    html_body += f"<p>更新时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>\n"
    html_body += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;font-family:sans-serif;'>\n"
    html_body += "<tr style='background:#f6f8fa;'><th>排名</th><th>仓库</th><th>本周增长</th><th>描述</th></tr>\n"
    for idx, repo in enumerate(repos_top10, 1):
        name = repo.get("full_name", "?")
        stars = repo.get("stars_this_week", "?")
        en_desc = repo.get("description") or ""
        zh_desc = translate(en_desc)
        desc = f"{en_desc} / {zh_desc}"[:200]
        html_body += (
            f"<tr><td>{idx}</td>"
            f"<td><a href='https://github.com/{name}'>{name}</a></td>"
            f"<td>{stars}</td>"
            f"<td>{desc}</td></tr>\n"
        )
    html_body += "</table>\n"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient

    # Alternative: plain + html
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(report_md, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())
        print(f"[+] 邮件已发送至 {recipient}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] SMTP 认证失败: {e}")
        print("      请检查 SMTP_USER 和 SMTP_PASS（授权码）是否正确")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"[ERROR] 收件人被拒绝: {e}")
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP 错误: {e}")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")


# ── 保存报告 ──────────────────────────────────────────────

def save_report(md_text: str, repos: list[dict]) -> None:
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    with open(docs_dir / "index.md", "w", encoding="utf-8") as f:
        f.write(md_text)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
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


# ── 主流程 ──────────────────────────────────────────────

def run() -> None:
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
