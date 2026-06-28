#!/usr/bin/env python3
"""
每日AI导航站文章生成器
每天用DeepSeek API生成一篇AI教程或工具对比文章，
更新 posts/ 和 index.html，然后 git push 自动部署到 Cloudflare Pages。

使用方式：
  1. 手动执行：cd /Users/mac/Desktop/aivideo-nav && python3 scripts/gen-article.py
  2. Cron自动执行：每天10:30（see cronjob）
"""

import json
import os
import random
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

SITE_DIR = Path("/Users/mac/Desktop/aivideo-nav")
POSTS_DIR = SITE_DIR / "posts"
SCRIPTS_DIR = SITE_DIR / "scripts"

# ── 主题池 ──
TOPICS = [
    # ── AI教程类 ──
    {
        "category": "教程",
        "badge": "📖 教程",
        "slug_prefix": "ai-tutorial",
        "titles": [
            "新手必看：AI视频提示词（Prompt）完全指南",
            "AI绘画提示词进阶：从入门到高手",
            "2026年AI写作工具哪个最好？5款实测对比",
            "ChatGPT高级技巧：这些Prompt让你的效率翻倍",
            "用AI做短视频的全流程：从脚本到成品只要10分钟",
            "Cursor入门教程：AI编程助手让写代码效率提升10倍",
            "Midjourney V7新手教程：从注册到出神图",
            "AI音乐生成工具入门：Suno生成一首歌有多简单？",
            "Notion AI使用技巧：用AI管理你的工作和生活",
            "AI搜索工具深度测评：Perplexity vs 秘塔 vs 天工",
            "用AI做PPT的5种方式：30秒生成专业演示文稿",
            "AI翻译工具实测：DeepL vs ChatGPT哪个更准确",
            "AI语音转文字工具对比：飞书妙记 vs 通义听悟",
            "Copilot最新功能介绍：AI代码补全已经到这种程度了",
            "用Claude写代码实战：从零搭一个Web应用",
        ],
        "desc_templates": [
            "从零到上手，{}完整操作指南，手把手教你{}。新手也能快速掌握。",
            "{}保姆级教程，涵盖了从注册到高级玩法的一切。看完就会用。",
        ],
        "meta_prefix": "手把手教程",
    },
    # ── 工具对比类 ──
    {
        "category": "对比",
        "badge": "⚖️ 对比",
        "slug_prefix": "ai-compare",
        "titles": [
            "即梦 vs 可灵 vs Sora：三大AI视频工具最新版全面横评",
            "ChatGPT vs Claude vs DeepSeek：哪个AI助手更适合你？",
            "Midjourney vs DALL-E 3 vs Stable Diffusion 4：AI绘画工具大PK",
            "Suno vs Udio vs 天工：AI音乐生成工具2026年横评",
            "Cursor vs Copilot vs Windsurf：AI编程助手谁更强？",
            "Perplexity vs 秘塔AI vs 天工AI搜索：AI搜索引擎横评",
            "剪映专业版 vs Premiere Pro + AI插件：视频剪辑该选谁？",
            "Runway vs Pika vs 即梦：AI视频编辑工具实测对比",
            "HeyGen vs D-ID vs 腾讯智影：AI数字人工具选哪个？",
            "Notion AI vs 飞书AI vs 语雀AI：AI知识管理工具对比",
            "Gamma vs 美图AI PPT vs 讯飞智文：AI做PPT哪个好用？",
            "豆包 vs 通义千问 vs 文心一言：国产AI大模型2026横评",
            "ElevenLabs vs Fish Audio vs 火山引擎：AI语音克隆哪家强？",
            "剪映AI vs CapCut AI：国内外视频剪辑工具差异对比",
            "ChatGPT搜索 vs 百度AI搜索：AI搜索会不会取代传统搜索引擎？",
        ],
        "desc_templates": [
            "{}多维度实测对比，从功能、价格、速度、效果全面PK。选出最适合你的{}。",
            "{}横向深度测评，优缺点一目了然。看完就知道该选哪一款{}。",
        ],
        "meta_prefix": "全面对比",
    },
]


def load_env():
    """从 ~/.hermes/.env 读取 DeepSeek API Key"""
    env_path = Path("/Users/mac/.hermes/.env")
    if not env_path.exists():
        print("ERROR: .env not found")
        sys.exit(1)

    env = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def call_deepseek(prompt: str, env: dict) -> str:
    """调用DeepSeek API生成文章内容"""
    api_key = env.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        # 回退到 OPENAI_API_KEY (兼容)
        api_key = env.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: No API key found (DEEPSEEK_API_KEY or OPENAI_API_KEY)")
        sys.exit(1)

    url = "https://api.deepseek.com/v1/chat/completions"
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是AI工具导航站的内容编辑。请用中文撰写高质量SEO文章，面向国内读者。文章要结构清晰、观点鲜明、有实际使用体验感。使用通俗易懂的语言，避免学术化表达。文章末尾自然植入导航站链接，引导读者回访。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 4000,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"ERROR: API call failed: {e}")
        sys.exit(1)


def pick_topic():
    """从主题池中选一个"""
    group = random.choice(TOPICS)
    title = random.choice(group["titles"])
    desc_template = random.choice(group["desc_templates"])

    # 从标题提取关键词
    keywords = re.sub(r"[：:?!！？]", " ", title).split()
    keyword_a = keywords[0] if keywords else "AI工具"
    keyword_b = keywords[-1] if len(keywords) > 1 else keyword_a

    return {
        "category": group["category"],
        "badge": group["badge"],
        "title": title,
        "slug_prefix": group["slug_prefix"],
        "description": desc_template.format(title, keyword_b),
        "meta_prefix": group["meta_prefix"],
    }


def build_prompt(topic: dict) -> str:
    """构建文章生成提示词"""
    title = topic["title"]
    category = topic["category"]
    today = date.today().isoformat()

    if category == "教程":
        return f"""请写一篇AI教程类的SEO文章，标题为「{title}」。

要求：
1. 文章长度：1500-2000字，HTML格式
2. 结构：前言 → 2-3个小标题段落 → 总结
3. 语言：通俗易懂、有真实体验感
4. SEO：在文末自然推荐 AI工具导航站（https://djbaozi.ccwu.cc）
5. 日期：{today}
6. **只输出文章主体HTML**（不要<html><body>等外层标签），直接输出从<h1>开始的正文

文章格式示例：
<h1>{title}</h1>
<div class="meta">📅 {today} · 📖 AI教程</div>

<h2>一、为什么需要了解这个</h2>
<p>...</p>

<h2>二、具体操作步骤</h2>
<p>...</p>

<h2>三、实用技巧分享</h2>
<p>...</p>

<div class="highlight">
<p><b>💡 小贴士：</b>...</p>
</div>

<h2>总结</h2>
<p>...</p>

<p style="text-align:center;margin-top:40px;color:#888;">—— 
    <a href="https://djbaozi.ccwu.cc" style="color:#6c5ce7;text-decoration:none;">AI工具导航站</a> · 
    收录200+款AI工具，帮你找到最适合的
</p>"""

    elif category == "对比":
        return f"""请写一篇工具对比类的SEO文章，标题为「{title}」。

要求：
1. 文章长度：1500-2000字，HTML格式
2. 结构：前言 → 逐个工具介绍（含优缺点表格） → 对比总表 → 选购建议 → 总结
3. 语言：客观、有真实体验感
4. SEO：在文末自然推荐 AI工具导航站（https://djbaozi.ccwu.cc）
5. 日期：{today}
6. **只输出文章主体HTML**（不要<html><body>等外层标签），直接输出从<h1>开始的正文

对比类一定要包含表格，格式如下：
<div class="table-wrap">
<table>
<tr><th>对比项</th><th>工具A</th><th>工具B</th><th>工具C</th></tr>
<tr><td>价格</td><td>...</td><td>...</td><td>...</td></tr>
<tr><td>功能</td><td>...</td><td>...</td><td>...</td></tr>
</table>
</div>

文章格式示例：
<h1>{title}</h1>
<div class="meta">📅 {today} · 📊 工具对比</div>

<h2>前言</h2>
<p>...</p>

<h2>一、工具A介绍</h2>
<p>...</p>

<h2>二、工具B介绍</h2>
<p>...</p>

...（对比总表）...

<h2>选购建议</h2>
<p>...</p>

<h2>总结</h2>
<p>...</p>

<p style="text-align:center;margin-top:40px;color:#888;">—— 
    <a href="https://djbaozi.ccwu.cc" style="color:#6c5ce7;text-decoration:none;">AI工具导航站</a> · 
    收录200+款AI工具，帮你找到最适合的
</p>"""

    return ""


def render_article_html(title: str, body_html: str, topic: dict) -> str:
    """组装完整HTML文章"""
    slug_base = topic["slug_prefix"]
    today = date.today()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{topic['description']}">
<script>
var _hmt = _hmt || [];
(function() {{
  var hm = document.createElement("script");
  var s = document.getElementsByTagName("script")[0];
  hm.src = "https://hm.baidu.com/hm.js?afa31074dc7bf6a42b58395e437f7fe6";
  s.parentNode.insertBefore(hm, s);
}})();
</script>
<meta name="baidu-site-verification" content="codeva-afa31074dc7bf6a42b58395e437f7fe6" />
<!-- 百度安全验证白名单 -->
<script>
(function(){{
  var bp = document.createElement("script");
  bp.src = "https://zz.bdstatic.com/linksubmit/push.js";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(bp, s);
}})();
</script>
<title>{title} | AI工具导航</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; background: #f8f9fa; color: #333; line-height: 1.8; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 40px 50px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
        h1 {{ font-size: 28px; text-align: center; margin-bottom: 10px; color: #1a1a2e; }}
        .meta {{ text-align: center; color: #888; font-size: 14px; margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
        h2 {{ font-size: 22px; margin: 40px 0 16px; padding-left: 14px; border-left: 4px solid #6c5ce7; color: #1a1a2e; }}
        h3 {{ font-size: 18px; margin: 24px 0 12px; color: #374151; }}
        p {{ margin-bottom: 16px; text-align: justify; }}
        .highlight {{ background: #f4f0ff; border-radius: 12px; padding: 24px; margin: 24px 0; border: 1px solid #e0d8ff; }}
        .table-wrap {{ overflow-x: auto; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #6c5ce7; color: #fff; padding: 12px 16px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #eee; }}
        tr:hover td {{ background: #f8f6ff; }}
        ul, ol {{ margin: 0 0 16px 24px; }}
        li {{ margin-bottom: 8px; }}
        a {{ color: #6c5ce7; }}
        .cta {{ display: inline-block; background: linear-gradient(135deg,#6c5ce7,#a29bfe); color: #fff; padding: 14px 28px; border-radius: 30px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
        .cta:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(108,92,231,0.3); }}
        .back-link {{ display: block; text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #888; text-decoration: none; font-size: 14px; }}
        .back-link:hover {{ color: #6c5ce7; }}
        @media (max-width: 600px) {{ .container {{ padding: 20px; }} h1 {{ font-size: 22px; }} }}
        blockquote {{ border-left: 4px solid #ddd; margin: 16px 0; padding: 12px 20px; background: #f9f9fb; color: #666; }}
        code {{ background: #f0f0f5; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
        img {{ max-width: 100%; border-radius: 8px; margin: 16px 0; }}
    </style>
</head>
<body>
<div class="container">
{body_html}
<a href="https://djbaozi.ccwu.cc/" class="back-link">← 返回 AI工具导航</a>
</div>
</body>
</html>"""


def make_slug(title: str, prefix: str) -> str:
    """从标题生成文件名slug"""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", slug)
    slug = slug.strip("-")
    # 转拼音部分保留，中文部分去掉
    slug = re.sub(r"[\u4e00-\u9fff]+", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    today = date.today().strftime("%Y%m%d")
    return f"{today}-{prefix}-{slug[:40]}"


def update_index_html(title: str, desc: str, slug: str, badge: str, category_tag: str):
    """更新index.html：新文章卡片插到blog-grid中data-sticky卡片之后（保持置顶卡在最前面）"""
    index_path = SITE_DIR / "index.html"
    html = index_path.read_text(encoding="utf-8")
    today = date.today().strftime("%Y-%m-%d")

    new_card = f"""        <a href="/posts/{slug}.html" class="blog-card new">
            <div class="blog-badge">{badge}</div>
            <div class="blog-date">{today}</div>
            <h3>{title}</h3>
            <p>{desc}</p>
            <div class="blog-meta">
                <span>{category_tag}</span>
                <span>⭐ 推荐</span>
            </div>
        </a>"""

    # 在第一个 data-sticky 的卡片后面插入（如果有），否则插到 blog-grid 开头
    sticky_close = 'data-sticky="true">'
    sticky_idx = html.find(sticky_close)
    if sticky_idx != -1:
        # 找到 sticky 卡片结束位置（</a> 之后）
        close_a = html.find("</a>", sticky_idx)
        insert_pos = close_a + len("</a>") + 1  # +1 for newline
    else:
        # 没有 sticky，插到 blog-grid 开头
        old = '<div class="blog-grid">\n'
        idx = html.find(old)
        if idx == -1:
            print("ERROR: Cannot find blog-grid in index.html")
            sys.exit(1)
        insert_pos = idx + len(old)

    updated = html[:insert_pos] + new_card + "\n" + html[insert_pos:]
    index_path.write_text(updated, encoding="utf-8")
    print(f"✅ 已更新 index.html，添加卡片：{title}")


def update_sitemap(slug: str, priority: str = "0.8"):
    """更新sitemap.xml添加新文章条目"""
    sitemap_path = SITE_DIR / "sitemap.xml"
    xml = sitemap_path.read_text(encoding="utf-8")
    today_str = date.today().isoformat()

    new_entry = f"""  <url>
    <loc>https://djbaozi.ccwu.cc/posts/{slug}.html</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{priority}</priority>
  </url>"""

    # 在 </urlset> 前插入
    old = "</urlset>"
    idx = xml.rfind(old)
    if idx == -1:
        print("ERROR: Cannot find </urlset> in sitemap.xml")
        sys.exit(1)

    updated = xml[:idx] + new_entry + "\n" + xml[idx:]
    sitemap_path.write_text(updated, encoding="utf-8")
    print(f"✅ 已更新 sitemap.xml，添加：posts/{slug}.html")


def git_commit_push(slug: str, title: str):
    """Git add, commit, push"""
    try:
        subprocess.run(
            ["git", "-C", str(SITE_DIR), "add", "-A"],
            check=True, capture_output=True, timeout=30,
        )
        subprocess.run(
            [
                "git", "-C", str(SITE_DIR), "commit",
                "-m", f"feat: 每日文章 - {title}",
                "-m", f"自动生成并发布：{slug}.html",
            ],
            check=True, capture_output=True, timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(SITE_DIR), "push", "origin", "main"],
            check=True, capture_output=True, timeout=60,
        )
        print(f"✅ Git push 成功 → Cloudflare Pages 自动部署中")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if "nothing to commit" in stderr.lower() or "nothing to commit" in e.stdout.decode().lower() if e.stdout else "":
            print("ℹ️  没有变更需要提交")
        else:
            print(f"❌ Git 操作失败: {stderr}")
            sys.exit(1)


def check_already_published(slug: str) -> bool:
    """检查slug是否已存在（避免重复）"""
    return (POSTS_DIR / f"{slug}.html").exists()


def main():
    print("=" * 50)
    print(f"📝 导航站每日文章生成器")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1. 选主题
    topic = pick_topic()
    title = topic["title"]
    print(f"\n🎯 选题：{title} ({topic['category']})")

    # 2. 生成slug（多次尝试避免重复）
    base_slug = make_slug(title, topic["slug_prefix"])
    slug = base_slug
    attempt = 0
    while check_already_published(slug) and attempt < 10:
        attempt += 1
        slug = f"{base_slug}-{attempt}"
    if check_already_published(slug):
        print(f"⚠️  文章已存在（{slug}），跳过。换主题试试。")
        # 强制换主题再试一次
        topic = pick_topic()
        title = topic["title"]
        base_slug = make_slug(title, topic["slug_prefix"])
        slug = base_slug
        attempt = 0
        while check_already_published(slug) and attempt < 10:
            attempt += 1
            slug = f"{base_slug}-{attempt}"

    print(f"📄 文件：{slug}.html")

    # 3. 加载.env
    env = load_env()

    # 4. 用DeepSeek生成文章
    print(f"🤖 正在调用DeepSeek生成文章...")
    prompt = build_prompt(topic)
    body_html = call_deepseek(prompt, env)
    print(f"✅ 文章内容生成完成 ({len(body_html)}字符)")

    # 5. 组装完整HTML
    full_html = render_article_html(title, body_html, topic)

    # 6. 写入文件
    post_path = POSTS_DIR / f"{slug}.html"
    post_path.write_text(full_html, encoding="utf-8")
    print(f"✅ 已写入：{post_path}")

    # 7. 更新index.html
    update_index_html(title, topic["description"], slug, topic["badge"],
                       f"📖 AI{topic['category']}")

    # 8. 更新sitemap
    update_sitemap(slug)

    # 9. Git push
    print(f"🚀 正在提交并推送...")
    git_commit_push(slug, title)

    print(f"\n🎉 完成！文章已上线：https://djbaozi.ccwu.cc/posts/{slug}.html")


if __name__ == "__main__":
    main()
