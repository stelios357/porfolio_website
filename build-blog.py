#!/usr/bin/env python3
"""
Renders Markdown posts from content/ into blog/<slug>/index.html using blog/template.html.

Usage:
  python3 build-blog.py                   # build all posts
  python3 build-blog.py <slug>            # build one post

Frontmatter format (YAML between --- fences):
  ---
  title: Post Title
  date: 2026-09-21
  description: One-line summary for meta tags and cards.
  tags: [ranking, infra]
  read_time: 12
  ---
"""

import os, sys, re, pathlib

ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATE = ROOT / "blog" / "template.html"
BLOG_DIR = ROOT / "blog"


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        raise ValueError("No frontmatter found")
    meta = {}
    for line in m.group(1).strip().splitlines():
        key, _, val = line.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("'\"") for v in val[1:-1].split(",")]
        meta[key.strip()] = val
    body = text[m.end():]
    return meta, body


def md_to_html(md):
    """Minimal Markdown→HTML. Handles headings, bold, inline code, code blocks,
    paragraphs, lists, blockquotes, links, images, and mermaid fences."""
    lines = md.split("\n")
    html_lines = []
    in_code = False
    in_list = False
    code_lang = ""
    buf = []

    def flush_list():
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for line in lines:
        # Code fences
        if line.strip().startswith("```"):
            if not in_code:
                flush_list()
                lang = line.strip()[3:].strip()
                if lang == "mermaid":
                    code_lang = "mermaid"
                    buf = []
                else:
                    code_lang = lang
                    buf = []
                in_code = True
            else:
                if code_lang == "mermaid":
                    html_lines.append(f'<div class="mermaid">\n{chr(10).join(buf)}\n</div>')
                else:
                    content = "\n".join(buf)
                    html_lines.append(f'<pre><code>{content}</code></pre>')
                in_code = False
                code_lang = ""
                buf = []
            continue

        if in_code:
            buf.append(line)
            continue

        stripped = line.strip()

        # Blank line
        if not stripped:
            flush_list()
            continue

        # Headings
        hm = re.match(r"^(#{2,4})\s+(.*)", stripped)
        if hm:
            flush_list()
            level = len(hm.group(1))
            html_lines.append(f"<h{level}>{inline(hm.group(2))}</h{level}>")
            continue

        # Blockquote
        if stripped.startswith(">"):
            flush_list()
            html_lines.append(f"<blockquote><p>{inline(stripped[1:].strip())}</p></blockquote>")
            continue

        # List item
        if re.match(r"^[-*]\s", stripped):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline(stripped[2:])}</li>")
            continue

        # Image
        im = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if im:
            flush_list()
            html_lines.append(f'<img src="{im.group(2)}" alt="{im.group(1)}">')
            continue

        # Paragraph
        flush_list()
        html_lines.append(f"<p>{inline(stripped)}</p>")

    flush_list()
    return "\n".join(html_lines)


def inline(text):
    """Inline Markdown: bold, code, links."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def build_post(slug):
    src = CONTENT / f"{slug}.md"
    if not src.exists():
        print(f"  skip: {src} not found")
        return

    meta, body = parse_frontmatter(src.read_text())
    content_html = md_to_html(body)
    template = TEMPLATE.read_text()

    tags_html = "".join(f'<span class="chip">{t}</span>' for t in (meta.get("tags") or []))

    html = template
    html = html.replace("{{TITLE}}", meta.get("title", slug))
    html = html.replace("{{DESCRIPTION}}", meta.get("description", ""))
    html = html.replace("{{SLUG}}", slug)
    html = html.replace("{{DATE}}", meta.get("date", ""))
    html = html.replace("{{READ_TIME}}", str(meta.get("read_time", "5")))
    html = html.replace("{{TAGS}}", tags_html)
    html = html.replace("{{CONTENT}}", content_html)

    out_dir = BLOG_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html)
    print(f"  built: blog/{slug}/index.html")


def main():
    if not TEMPLATE.exists():
        print("Error: blog/template.html not found")
        sys.exit(1)

    if len(sys.argv) > 1:
        build_post(sys.argv[1])
    else:
        for f in sorted(CONTENT.glob("*.md")):
            build_post(f.stem)
        print("Done.")


if __name__ == "__main__":
    main()
