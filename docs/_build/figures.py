# -*- coding: utf-8 -*-
"""生成技术文档用的两张图：分层架构、skills 流水线。

只依赖 Pillow（随运行时提供），中文字体用系统自带的微软雅黑。
画布按最终插入 Word 的宽度（16 cm / 13 cm）反推像素，保证 300 dpi 左右。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(r"C:\Windows\Fonts")
OUT = Path(__file__).resolve().parent

INK = (33, 37, 41)
MUTED = (110, 117, 125)
LINE = (170, 176, 184)

STYLE = {
    "io":     {"fill": (236, 239, 241), "border": (69, 90, 100)},
    "rule":   {"fill": (232, 245, 233), "border": (46, 125, 50)},
    "llm":    {"fill": (243, 229, 245), "border": (106, 27, 154)},
    "branch": {"fill": (255, 248, 225), "border": (249, 168, 55)},
    "layer":  {"fill": (248, 249, 250), "border": (206, 212, 218)},
}
LABEL = {
    "表现": (33, 84, 141), "接口": (13, 110, 122), "AI": (90, 52, 140),
    "评测": (166, 96, 11), "数据": (24, 110, 78),
}


def font(size, bold=False):
    name = "msyhbd.ttc" if bold else "msyh.ttc"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        trial = cur + ch
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def block(draw, x, y, w, h, title, sub=None, *, kind="io", radius=14,
          title_size=34, sub_size=26, align="center"):
    """一个圆角盒子：标题 + 可选副标题，居中或左对齐。"""
    st = STYLE[kind]
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                           fill=st["fill"], outline=st["border"], width=3)
    tf, sf = font(title_size, True), font(sub_size)
    if sub:
        tl = wrap(draw, title, tf, w - 32)
        sl = wrap(draw, sub, sf, w - 32)
        total = len(tl) * title_size * 1.25 + len(sl) * sub_size * 1.35
        cy = y + (h - total) / 2
        for line in tl:
            lw = draw.textlength(line, font=tf)
            draw.text((x + (w - lw) / 2 if align == "center" else x + 16, cy), line,
                      font=tf, fill=INK)
            cy += title_size * 1.25
        for line in sl:
            lw = draw.textlength(line, font=sf)
            draw.text((x + (w - lw) / 2 if align == "center" else x + 16, cy), line,
                      font=sf, fill=MUTED)
            cy += sub_size * 1.35
    else:
        lines = wrap(draw, title, tf, w - 32)
        cy = y + (h - len(lines) * title_size * 1.3) / 2
        for line in lines:
            lw = draw.textlength(line, font=tf)
            draw.text((x + (w - lw) / 2 if align == "center" else x + 16, cy), line,
                      font=tf, fill=INK)
            cy += title_size * 1.3


def arrow(draw, x1, y1, x2, y2, color=LINE, width=4, head=14, dashed=False):
    if dashed:
        # 简单虚线：按 12 像素分段
        import math
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            return
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        step = 0
        while step < length - head:
            a = step
            b = min(step + 12, length - head)
            draw.line([(x1 + ux * a, y1 + uy * a), (x1 + ux * b, y1 + uy * b)],
                      fill=color, width=width)
            step += 22
    else:
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    pts = [(x2, y2),
           (x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45)),
           (x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45))]
    draw.polygon(pts, fill=color)


def polyline(draw, points, color=LINE, width=4, dashed=True, head=14):
    import math
    for i in range(len(points) - 2):
        (x1, y1), (x2, y2) = points[i], points[i + 1]
        if dashed:
            length = math.hypot(x2 - x1, y2 - y1)
            ux, uy = (x2 - x1) / length, (y2 - y1) / length
            step = 0
            while step < length:
                b = min(step + 12, length)
                draw.line([(x1 + ux * step, y1 + uy * step), (x1 + ux * b, y1 + uy * b)],
                          fill=color, width=width)
                step += 22
        else:
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    arrow(draw, *points[-2], *points[-1], color=color, width=width, head=head, dashed=dashed)


# ── 图 1：分层架构 ──────────────────────────────────────────────

def figure_architecture():
    W, H = 1800, 1180
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    layers = [
        ("表现", "表现层", ["题库与提交", "比赛与榜单", "算法学习/图谱", "星语学生端", "星语教师端"]),
        ("接口", "接口层", ["DRF 视图", "JWT + 权限", "限流/净化", "SSE 流式", "Admin 后台"]),
        ("AI", "AI 服务层", ["P1–P5 编排", "skills 流水线", "确定性校验器", "RAG 检索", "AI 反馈池"]),
        ("评测", "评测层", ["评测队列", "Docker 沙箱", "运行名额", "资源限制"]),
        ("数据", "数据层", ["MySQL 24 表", "Redis 缓存", "笔记与向量", "静态/临时文件"]),
    ]

    x0, band_w = 30, 1490
    y, bh, gap = 40, 168, 30
    left_w = 200
    chip_y_off, chip_h = 42, 84

    for i, (key, name, chips) in enumerate(layers):
        top = y + i * (bh + gap)
        d.rounded_rectangle([x0, top, x0 + band_w, top + bh], radius=16,
                           fill=STYLE["layer"]["fill"], outline=STYLE["layer"]["border"], width=2)
        # 左侧层名
        d.rounded_rectangle([x0 + 14, top + 24, x0 + 14 + left_w, top + bh - 24], radius=12,
                           fill=LABEL[key], outline=LABEL[key])
        f = font(34, True)
        tw = d.textlength(name, font=f)
        d.text((x0 + 14 + (left_w - tw) / 2, top + bh / 2 - 23), name, font=f, fill="white")

        cx = x0 + 14 + left_w + 26
        avail = band_w - (left_w + 26 + 14) - 20
        n = len(chips)
        cgap = 16
        cw = (avail - (n - 1) * cgap) / n
        for j, c in enumerate(chips):
            bx = cx + j * (cw + cgap)
            st = STYLE["llm"] if key == "AI" else STYLE["io"]
            d.rounded_rectangle([bx, top + chip_y_off, bx + cw, top + chip_y_off + chip_h],
                               radius=12, fill="white", outline=st["border"], width=2)
            cf = font(33)
            lines = wrap(d, c, cf, cw - 20)
            ty = top + chip_y_off + (chip_h - len(lines) * 42) / 2
            for line in lines:
                lw = d.textlength(line, font=cf)
                d.text((bx + (cw - lw) / 2, ty), line, font=cf, fill=INK)
                ty += 42

        # 层间箭头
        if i < len(layers) - 1:
            arrow(d, x0 + 60, top + bh + 4, x0 + 60, top + bh + gap - 4, color=(140, 148, 158), width=4, head=12)

    # 右侧：平台外的大模型与向量服务
    sx, sw = 1550, 225
    block(d, sx, 40 + 2 * (bh + gap) + 12, sw, 66, "LLM 网关", kind="llm", title_size=27)
    block(d, sx, 40 + 2 * (bh + gap) + 92, sw, 66, "Embedding", kind="llm", title_size=27)
    arrow(d, x0 + band_w + 6, 40 + 2 * (bh + gap) + 45, sx - 6, 40 + 2 * (bh + gap) + 45,
          color=STYLE["llm"]["border"], width=4, head=12)
    arrow(d, x0 + band_w + 6, 40 + 2 * (bh + gap) + 125, sx - 6, 40 + 2 * (bh + gap) + 125,
          color=STYLE["llm"]["border"], width=4, head=12)

    note = "请求自上而下，结果自下而上；AI 调用经右侧网关出平台，返回内容一律先过校验器再落库"
    f = font(26)
    d.text(((W - d.textlength(note, font=f)) / 2, y + 5 * (bh + gap) + 6), note, font=f, fill=MUTED)
    img.save(OUT / "fig_arch.png", dpi=(300, 300))


# ── 图 2：skills 流水线 ─────────────────────────────────────────

def figure_pipeline():
    W, H = 1240, 1270
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # 图例
    lx = 80
    for kind, text in (("io", "输入输出"), ("rule", "规则 skill"), ("llm", "大模型 skill"), ("branch", "分支处理")):
        st = STYLE[kind]
        d.rounded_rectangle([lx, 40, lx + 34, 68], radius=8, fill=st["fill"], outline=st["border"], width=2)
        f = font(25)
        d.text((lx + 44, 40), text, font=f, fill=INK)
        lx += 54 + d.textlength(text, font=f) + 46

    mx, mw = 80, 470
    bx, bw = 700, 450
    y0, step, bh = 128, 122, 88

    steps = [
        ("io", "① 学生输入", "一句话，最多 200 字"),
        ("rule", "② segment 分词与规范化", "NFKC · 空白 · 术语保护 · jieba"),
        ("rule", "③ echo_detect 仿说检测", "排除选项与正反问 · 相似度 ≥ 0.8"),
        ("rule", "④ lexicon_map 词表映射", "精确 → 同音 → 相近 三轮"),
        ("rule", "⑤ pronoun_tag 代词标注", "只生成理解提示，不改原文"),
        ("llm", "⑥ intent 意图识别", "大模型 P5 · 无模型时关键词兜底"),
        ("llm", "⑦ 生成回复", "大模型 P3 · 温度 0.2 · 一句话 + 选项"),
        ("rule", "⑧ plain_check 字面化检查", "12/20 字 · 双重否定 · 反问"),
        ("io", "⑨ 返回结果", "{intent, reply, options}"),
    ]
    for i, (kind, title, sub) in enumerate(steps):
        top = y0 + i * step
        block(d, mx, top, mw, bh, title, sub, kind=kind, title_size=33, sub_size=24)
        if i < len(steps) - 1:
            arrow(d, mx + mw / 2, top + bh + 4, mx + mw / 2, top + step - 4, color=(120, 128, 138), width=4)

    # 分支 A：仿说
    by = y0 + 2 * step - 6
    block(d, bx, by, bw, 104, "判定为仿说 → 停止流水线", "不调大模型，改用选项按钮重问",
          kind="branch", title_size=29, sub_size=23)
    arrow(d, mx + mw + 6, by + 52, bx - 6, by + 52, color=STYLE["branch"]["border"], width=4)
    polyline(d, [(bx, by + 52), (bx - 60, by + 52), (bx - 60, y0 + bh / 2), (mx + mw + 8, y0 + bh / 2)],
             color=STYLE["branch"]["border"], dashed=True)

    # 分支 B：字面化不合格
    by2 = y0 + 7 * step - 6
    block(d, bx, by2, bw, 104, "有错误级问题 → 回填重写", "错误清单回填，最多改写 1 次",
          kind="branch", title_size=29, sub_size=23)
    arrow(d, mx + mw + 6, by2 + 52, bx - 6, by2 + 52, color=STYLE["branch"]["border"], width=4)
    polyline(d, [(bx, by2 + 40), (bx - 60, by2 + 40), (bx - 60, y0 + 6 * step + bh - 6),
                 (mx + mw + 8, y0 + 6 * step + bh - 6)],
             color=STYLE["branch"]["border"], dashed=True)

    note = "顺序固定，不让模型自己决定调用哪一步；每一步都可单独关闭，用于消融实验"
    f = font(26)
    d.text(((W - d.textlength(note, font=f)) / 2, H - 48), note, font=f, fill=MUTED)
    img.save(OUT / "fig_pipeline.png", dpi=(300, 300))


if __name__ == "__main__":
    figure_architecture()
    figure_pipeline()
    print("ok")
