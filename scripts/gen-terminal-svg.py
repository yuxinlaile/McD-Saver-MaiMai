#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-terminal-svg.py — 把真实命令输出渲染为终端风 SVG（确定性，无外部依赖）。

用法: python gen-terminal-svg.py <title> <cmd-label> <outfile.svg> < input.txt
输出是**真实运行结果**的排版渲染，不做任何内容美化；文件头注明来源命令与日期。
"""
import html
import sys
from datetime import date

W, H_LINE, PAD = 900, 22, 20


def render(title: str, cmd: str, text: str) -> str:
    lines = text.rstrip("\n").split("\n")
    height = PAD * 3 + 28 + H_LINE * (len(lines) + 1)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{1}" '
        'viewBox="0 0 {0} {1}" font-family="Consolas, \'Courier New\', monospace">'.format(W, height),
        '  <rect width="100%" height="100%" rx="10" fill="#1e1e2e"/>',
        '  <rect width="100%" height="40" rx="10" fill="#181825"/>',
        '  <circle cx="24" cy="20" r="6" fill="#f38ba8"/><circle cx="44" cy="20" r="6" fill="#f9e2af"/>'
        '<circle cx="64" cy="20" r="6" fill="#a6e3a1"/>',
        '  <text x="86" y="25" fill="#a6adc8" font-size="13">{0}</text>'.format(html.escape(cmd)),
    ]
    y = 68
    for line in lines:
        color = "#cdd6f4"
        stripped = line.strip()
        if stripped.startswith("===") or stripped.startswith("【"):
            color = "#89b4fa"
        elif stripped.startswith("·") or stripped.startswith("第"):
            color = "#a6e3a1"
        elif "最优" in line or "净用掉" in line or "可实现" in line:
            color = "#a6e3a1"
        elif "⚠️" in line or "注定过期" in line or "浪费" in line:
            color = "#f38ba8"
        parts.append('  <text x="{2}" y="{0}" fill="{1}" font-size="13" xml:space="preserve">{3}</text>'.format(
            y, color, PAD, html.escape(line)))
        y += H_LINE
    parts.append('  <text x="{1}" y="{0}" fill="#6c7086" font-size="11">'
                 '真实运行输出 · 生成于 {2} · 未做内容美化 · 命令见窗口标题</text>'.format(height - 12, PAD, date.today().isoformat()))
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: gen-terminal-svg.py <title> <cmd> <out.svg> < input", file=sys.stderr)
        sys.exit(1)
    svg = render(sys.argv[1], sys.argv[2], sys.stdin.read())
    with open(sys.argv[3], "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("written", sys.argv[3])
