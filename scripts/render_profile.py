#!/usr/bin/env python3
"""Render a neofetch-style profile card (light + dark SVG) for the GitHub profile README.

Static rows live in PROFILE below. Dynamic rows take their values from stats.json
(written by the daily workflow: GitHub GraphQL stats, account age, AI usage, alphaXiv library).
Every row is padded with dots to the same character count, so the right edge lines up
in any monospace font.

Usage:
  python3 render_profile.py stats.json out_dir/ [ascii.txt]
"""
import json, sys, datetime as dt
from xml.sax.saxutils import escape

LINE = 78            # characters per row
FS, LH = 13.5, 17.5  # font size / line height (px)
Y0 = 34
ART_FS, ART_LH = 7.4, 7.6   # ASCII portrait: small font, tight line height keeps proportions
PADX, GAP = 26, 30

THEMES = {
    "light": {"bg": "#ffffff", "border": "#d0d7de", "text": "#24292f", "key": "#953800", "value": "#0a3069",
              "cc": "#c2cfde", "add": "#1a7f37", "del": "#cf222e", "accent": "#8250df"},
    "dark":  {"bg": "#0d1117", "border": "#30363d", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff",
              "cc": "#616e7f", "add": "#3fb950", "del": "#f85149", "accent": "#d2a8ff"},
}

# row kinds: ("head", title) | ("kv", [key parts], value, cls) | ("pair", (k1, v1), (k2, v2)) | ("blank",)
#            ("loc", total, add, dele)
def profile(st):
    return [
        ("head", "samynhn@github"),
        ("kv", ["Name"], "Samynhn"),
        ("kv", ["University"], "National Yang Ming Chiao Tung University (NYCU)"),
        ("kv", ["Degree"], "Master Student, Computer Science"),
        ("kv", ["Uptime"], st["uptime"], "value", "age_data"),
        ("kv", ["Location"], "Taipei, Taiwan"),
        ("kv", ["Terminal"], "Warp"),
        ("kv", ["IDE"], "Cursor"),
        ("kv", ["Agent"], "Claude Code, Codex, Cursor"),
        ("blank",),
        ("kv", ["Research", "Focus"], "Diffusion Models, Vision Transformers, World Action Models"),
        ("kv", ["Languages", "Programming"], "Python, C++, CUDA, Java, TypeScript, Swift, Solidity"),
        ("kv", ["Hobbies"], "Coding, Music, Basketball"),
        ("blank",),
        ("head", "- Contact"),
        ("kv", ["GitHub"], "github.com/samynhn"),
        ("kv", ["Blog"], "samynhn.github.io"),
        ("blank",),
        ("head", "- GitHub Stats"),
        ("pair", ("Repos", st["repos"], "repo_data"), ("Stars", st["stars"], "star_data")),
        ("pair", ("Commits", st["commits"], "commit_data"), ("Followers", st["followers"], "follower_data")),
        ("loc", st["loc"], st["loc_add"], st["loc_del"]),
        ("blank",),
        ("head", "- AI & Papers"),
        ("pair", ("Tokens (30d)", st["ai_tokens_30d"], "ai_tokens"), ("Primary", st["ai_primary"], "ai_primary")),
        ("pair", ("Papers saved", st["papers"], "paper_data"), ("Top folder", st["top_folder"], "folder_data")),
    ]


def dots(n):
    return " " if n <= 0 else (" " if n == 1 else (" " + "." * (n - 2) + " "))


class Row:
    """Collects (text, class, id) segments and the plain-character length of the row."""
    def __init__(self): self.seg, self.n = [], 0
    def add(self, text, cls=None, id_=None):
        self.seg.append((text, cls, id_)); self.n += len(text); return self


def key_parts(row, parts):
    for i, p in enumerate(parts):
        if i: row.add(".", "text")
        row.add(p, "key")
    row.add(":", "text")


def build(kind_row):
    k = kind_row[0]
    r = Row()
    if k == "blank":
        return r.add(". ", "cc")
    if k == "head":
        title = kind_row[1]
        r.add(title, "text").add(" ")
        return r.add("—" * (LINE - r.n), "cc")
    if k == "kv":
        parts, value = kind_row[1], kind_row[2]
        cls = kind_row[3] if len(kind_row) > 3 else "value"
        id_ = kind_row[4] if len(kind_row) > 4 else None
        r.add(". ", "cc"); key_parts(r, parts)
        r.add(dots(LINE - r.n - len(value)), "cc", f"{id_}_dots" if id_ else None)
        return r.add(value, cls, id_)
    if k == "pair":
        (k1, v1, i1), (k2, v2, i2) = kind_row[1], kind_row[2]
        half = LINE // 2
        r.add(". ", "cc"); key_parts(r, [k1])
        r.add(dots(half - 3 - r.n - len(str(v1))), "cc", f"{i1}_dots").add(str(v1), "value", i1)
        r.add(" | ", "text"); key_parts(r, [k2])
        r.add(dots(LINE - r.n - len(str(v2))), "cc", f"{i2}_dots")
        return r.add(str(v2), "value", i2)
    if k == "loc":
        total, add, dele = kind_row[1:]
        tail = f"( {add}++, {dele}-- )"
        r.add(". ", "cc"); key_parts(r, ["Lines of Code on GitHub"])
        r.add(dots(LINE - r.n - len(total) - 1 - len(tail)), "cc", "loc_data_dots")
        r.add(total, "value", "loc_data").add(" ")
        return r.add("( ", "text").add(f"{add}++", "add", "loc_add").add(", ", "text") \
                .add(f"{dele}--", "del", "loc_del").add(" )", "text")
    raise ValueError(k)


PROMPT_USER, PROMPT_PATH, CMD = "samynhn@github", "~", "neofetch"
T_TYPE0, T_CHAR = 350, 75     # typing starts / ms per typed character
T_PAUSE = 280                 # "command runs" before output appears
T_ROW = 45                    # ms between printed rows
BLINK = "1.1s"


def prompt_spans(c):
    return (f'<tspan fill="{c["add"]}">{PROMPT_USER}</tspan><tspan class="text">:</tspan>'
            f'<tspan fill="{c["value"]}">{PROMPT_PATH}</tspan><tspan class="text">$ </tspan>')


def render(st, theme, art=None):
    c = THEMES[theme]
    cw = FS * 0.6                                   # monospace advance
    rows = [build(r) for r in profile(st)]
    art = art or []
    art_w = max((len(l) for l in art), default=0) * ART_FS * 0.6
    X0 = PADX + (art_w + GAP if art else 0)
    # prompt line, gap, the neofetch rows, gap, final prompt
    lines_h = (len(rows) + 3) * LH
    info_h = lines_h - LH
    art_h = (len(art) - 1) * ART_LH
    w = int(X0 + LINE * cw + PADX)
    h = int(Y0 + max(info_h, art_h) + 24)

    t_out = T_TYPE0 + len(CMD) * T_CHAR + T_PAUSE   # first output row
    t_end = t_out + len(rows) * T_ROW + 120          # final prompt + cursor

    css = (f"text,tspan{{white-space:pre}}"
           f".text{{fill:{c['text']}}}.key{{fill:{c['key']}}}.value{{fill:{c['value']}}}"
           f".cc{{fill:{c['cc']}}}.add{{fill:{c['add']}}}.del{{fill:{c['del']}}}"
           # rows/art lines: hidden until their delay, then printed in one frame
           f".ln{{animation:ln .01s linear both}}@keyframes ln{{0%{{opacity:0}}100%{{opacity:1}}}}"
           # typed command: a background-coloured cover shrinks one character per step
           f".cover{{transform-box:fill-box;transform-origin:right center;transform:scaleX(0);"
           f"animation:untype {len(CMD)*T_CHAR}ms steps({len(CMD)},end) {T_TYPE0}ms both}}"
           f"@keyframes untype{{from{{transform:scaleX(1)}}to{{transform:scaleX(0)}}}}"
           # typing cursor: follows the typed text, gone while the command runs
           f".tcur{{opacity:0;animation:tmove {len(CMD)*T_CHAR}ms steps({len(CMD)},end) {T_TYPE0}ms both,"
           f"tshow {T_TYPE0 + len(CMD)*T_CHAR + 120}ms step-end}}"
           f"@keyframes tmove{{from{{transform:translateX(0)}}to{{transform:translateX({len(CMD)*cw:.2f}px)}}}}"
           f"@keyframes tshow{{from,to{{opacity:1}}}}"
           # final cursor: steady blink forever
           f".cur{{animation:ln .01s linear {t_end}ms both,blink {BLINK} step-end {t_end}ms infinite}}"
           f"@keyframes blink{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}"
           f"@media (prefers-reduced-motion:reduce){{.ln,.cover,.cur{{animation:none}}.tcur{{display:none}}}}")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'font-family="ui-monospace,\'SF Mono\',Menlo,Consolas,\'Liberation Mono\',monospace" font-size="{FS}px">',
           f"<style>{css}</style>",
           f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="6" fill="{c["bg"]}" stroke="{c["border"]}"/>']
    Yi = Y0 + max(0, (art_h - info_h) / 2)
    if art:
        ay = Y0 + max(0, (info_h - art_h) / 2) - 2
        for i, line in enumerate(art):
            if line.strip():  # the portrait is static: always visible, never animated
                out.append(f'<text x="{PADX}" y="{ay + i * ART_LH:.1f}" class="text" font-size="{ART_FS}px">'
                           f'{escape(line)}</text>')

    # 1) prompt + typed command
    plen = len(PROMPT_USER) + len(PROMPT_PATH) + 3
    cx = X0 + plen * cw
    out.append(f'<text x="{X0}" y="{Yi}" textLength="{plen*cw:.1f}" lengthAdjust="spacingAndGlyphs">{prompt_spans(c)}</text>')
    out.append(f'<text x="{cx:.1f}" y="{Yi}" class="text" textLength="{len(CMD)*cw:.1f}" '
               f'lengthAdjust="spacingAndGlyphs">{CMD}</text>')
    out.append(f'<rect class="cover" x="{cx-0.5:.1f}" y="{Yi-FS:.1f}" width="{len(CMD)*cw+1:.1f}" '
               f'height="{FS*1.4:.1f}" fill="{c["bg"]}"/>')
    out.append(f'<rect class="tcur" x="{cx:.1f}" y="{Yi-FS*0.85:.1f}" width="{cw:.1f}" height="{FS*1.1:.1f}" '
               f'fill="{c["text"]}"/>')

    # 2) neofetch output, one row per frame
    for i, r in enumerate(rows):
        y = Yi + (i + 1.5) * LH
        spans = "".join(
            f'<tspan{" class=" + chr(34) + cls + chr(34) if cls else ""}{" id=" + chr(34) + id_ + chr(34) if id_ else ""}>'
            f'{escape(t)}</tspan>' for t, cls, id_ in r.seg)
        out.append(f'<text x="{X0}" y="{y}" class="text ln" style="animation-delay:{t_out + i*T_ROW}ms">{spans}</text>')

    # 3) fresh prompt with a steadily blinking block cursor
    yf = Yi + (len(rows) + 2) * LH
    out.append(f'<text x="{X0}" y="{yf}" class="ln" style="animation-delay:{t_end}ms" textLength="{plen*cw:.1f}" '
               f'lengthAdjust="spacingAndGlyphs">{prompt_spans(c)}</text>')
    out.append(f'<rect class="cur" x="{cx:.1f}" y="{yf-FS*0.85:.1f}" width="{cw:.1f}" height="{FS*1.1:.1f}" '
               f'fill="{c["text"]}"/>')
    out.append("</svg>")
    return "\n".join(out)


def uptime(since, today):
    y = today.year - since.year - ((today.month, today.day) < (since.month, since.day))
    anchor = since.replace(year=since.year + y)
    m = (today.year - anchor.year) * 12 + today.month - anchor.month - (today.day < anchor.day)
    mm = anchor.month - 1 + m
    anchor_m = anchor.replace(year=anchor.year + mm // 12, month=mm % 12 + 1)
    d = (today - anchor_m).days
    pl = lambda n, u: f"{n} {u}{'' if n == 1 else 's'}"
    return f"{pl(y, 'year')}, {pl(m, 'month')}, {pl(d, 'day')}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    st = json.load(open(sys.argv[1]))
    art = open(sys.argv[3]).read().rstrip("\n").split("\n") if len(sys.argv) > 3 else None
    today = dt.date.fromisoformat(st.get("today", dt.date.today().isoformat()))
    st["uptime"] = uptime(dt.date.fromisoformat(st["github_since"]), today)
    for theme in THEMES:
        path = f"{sys.argv[2].rstrip('/')}/profile-{theme}.svg"
        open(path, "w").write(render(st, theme, art))
        print("wrote", path)
