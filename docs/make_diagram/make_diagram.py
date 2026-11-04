"""The radar as it runs now, one column, straight down, as a PNG.

  python docs/make_diagram/make_diagram.py docs/make_diagram/radar.png

Three gates and a verdict, nothing else. The old upstream drawing (six signals, a keyword table
with page-one competition, a 14-day review) described a product this fork no longer runs, so it is
gone along with the animated SVG and the GIF: a still PNG is what a person actually opens.
Needs rsvg-convert (brew install librsvg).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 760, 958
FONT = "Hiragino Sans GB, PingFang SC, Noto Sans CJK SC, sans-serif"
GREY = dict(fill="#F1EFE8", stroke="#5F5E5A", title="#444441", sub="#5F5E5A")
BLUE = dict(fill="#E6F1FB", stroke="#185FA5", title="#0C447C", sub="#185FA5")
PURP = dict(fill="#EEEDFE", stroke="#534AB7", title="#3C3489", sub="#534AB7")
GREEN = dict(fill="#E1F5EE", stroke="#0F6E56", title="#085041", sub="#0F6E56")
AMBER = dict(fill="#FAECE7", stroke="#993C1D", title="#712B13", sub="#993C1D")

STEPS = [
    (GREY, "", "输入：六个查询词", "config.effects.queries —— ai dance filter · capcut filter · ai pet filter …"),
    (BLUE, "", "① 发现：TikTok 按最新排序搜一遍", "150 条/天 · $0.0003 一条 · 播放数用来排序，不用来下结论"),
    (BLUE, "", "② 新鲜：只留 14 天内上传的", "更老的视频，窗口早就关了，名字已经被别人拿走"),
    (PURP, "门 1", "③ 命名：这是不是一个「效果」的名字？", "教程、品类、段子、吐槽、模型发布 → 丢掉；漏掉的下标会重问"),
    (BLUE, "", "④ 归并：去掉 ai / capcut / filter / template", "jeremy clarkson filter = ai filter = capcut filter，只算一个"),
    (BLUE, "", "⑤ 取前四：按播放量，只看最热的四个", "少于 20 条评论的候选要单独标出来，它的分母不可信"),
    (GREEN, "门 2", "YouTube 评论：问「怎么做」的占比 ≥ 20%？", "免费先问；不够 20 条才花 $0.05 买 TikTok 评论"),
    (GREEN, "门 3", "Google 标题 ≤ 20 页，.com/.ai/.io 还没被注册？", "intitle $0.004 · 域名走 RDAP 注册日 + DoH 存在性"),
]

VERDICTS = [("open", "四道全过，今天可以看"), ("cold", "没人问怎么做"), ("busy", "标题太多，赛道满了"),
            ("claimed", "域名已经被注册"), ("thin", "评论太少，判不了"), ("cooling", "视频老了，已经凉了")]

CHIP = dict(fill="#FFFFFF", stroke="#993C1D")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(y, h, c, tag, title, sub, x=30, w=700):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="1"/>',
           f'<text x="{x + 18}" y="{y + 27}" font-size="17" font-weight="600" fill="{c["title"]}">{esc(title)}</text>',
           f'<text x="{x + 18}" y="{y + 48}" font-size="13" fill="{c["sub"]}">{esc(sub)}</text>']
    if tag:
        out.append(f'<rect x="{x + w - 62}" y="{y + 12}" width="46" height="20" rx="4" fill="{c["stroke"]}"/>')
        out.append(f'<text x="{x + w - 39}" y="{y + 26}" font-size="12" fill="#FFFFFF" text-anchor="middle">{esc(tag)}</text>')
    return "\n".join(out)


def arrow(y):
    return (f'<path d="M380 {y} V{y + 20}" stroke="#888780" stroke-width="1.4" marker-end="url(#arrow)" fill="none"/>')


def scene():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * 2}" height="{H * 2}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
             '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
             '<path d="M2 1L8 5L2 9" fill="none" stroke="#888780" stroke-width="1.5" stroke-linecap="round"/></marker></defs>',
             f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
             '<g text-anchor="start">',
             f'<text x="30" y="46" font-size="24" font-weight="700" fill="#2C2C2A">新词雷达：现在真正跑的东西</text>',
             f'<text x="30" y="74" font-size="14" fill="#5F5E5A">python3 -m radar effects --state state --out report-effects.md · 6–7 分钟 · $0.073 一天</text>',
             '</g>']

    y = 104
    for i, (c, tag, title, sub) in enumerate(STEPS):
        parts.append(box(y, 62, c, tag, title, sub))
        y += 62
        if i < len(STEPS) - 1:
            parts.append(arrow(y))
            y += 26

    # the verdict: six outcomes, one line each
    top = y + 26
    parts.append(f'<path d="M380 {y} V{top - 6}" stroke="#888780" stroke-width="1.4" marker-end="url(#arrow)" fill="none"/>')
    parts.append(f'<rect x="30" y="{top}" width="700" height="128" rx="10" fill="{AMBER["fill"]}" stroke="{AMBER["stroke"]}" stroke-width="1"/>')
    parts.append(f'<text x="48" y="{top + 28}" font-size="17" font-weight="600" fill="{AMBER["title"]}">结论：三道门都过才叫 open</text>')
    for n, (name, why) in enumerate(VERDICTS):
        col, row = n % 2, n // 2
        x = 48 + col * 348
        yy = top + 54 + row * 24
        parts.append(f'<text x="{x}" y="{yy}" font-size="13" fill="{AMBER["stroke"]}"><tspan font-weight="600">{esc(name)}</tspan>  {esc(why)}</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def main(out):
    svg = scene()
    target = Path(out).with_suffix(".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "radar.svg"
        src.write_text(svg)
        subprocess.run(["rsvg-convert", "-w", str(W * 2), "-b", "white", str(src), "-o", str(target)], check=True)
    print(target)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/make_diagram/radar.png")
