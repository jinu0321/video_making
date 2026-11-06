"""Generate the HyperFrames compositions from content.json + build/timing.json.

  python3 tools/build.py

Writes index.html, compositions/chrome.html, compositions/shot-NN.html and
compositions/captions.html. Re-run after changing content.json or the narration.
A shot shows either typed `blocks` (code box) or a `diagram` (boxes and arrows).
"""
import html
import json
import math
import re
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920

# Layout measured from the reference short (1080x1920)
EDITOR_TOP, EDITOR_BOTTOM = 105, 1000
PROGRESS_H = 12          # progress bar on top; the terminal title bar fills the rest above the editor
BOX_W, BOX_PAD_X = 1000, 48
LINE_H = 1.17            # line-height of the box text
BOX_PAD_EM = 0.78        # vertical padding of the box, in em
FS_MAX, FS_WARN = 220, 34
BOX_MAX_H = 800
FS_BASE = 120           # text is laid out at this size and scaled to the target size
TYPE_FRACTION = 0.8     # a block finishes typing within this share of its window

COLORS = {"k": "#ff6b8b", "n": "#b699ff", "s": "#e6db74", "c": "#8b98ad", "r": "#ff4438", "w": "#ffffff"}
ACCENT = "#3ddc97"       # mint, only for what is live: progress, prompt, cursor, word being read

# Diagram shots: laid out at natural size in a DIA_W-wide space, scaled down to fit the plate if taller than DIA_H.
DIA_TOP, DIA_BOTTOM = 125, 985     # the plate
DIA_W, DIA_H = 880, 810
NODE_H, NODE_H_SUB, TEXT_H, DB_H = 100, 140, 64, 116
NODE_FS, SUB_FS, FRAME_FS, ARROW_FS, BADGE_FS = 54, 36, 48, 40, 30
DIA_FS_WARN = 40         # box text smaller than this (after scaling) is hard to read on a phone
NODE_PAD = 44            # text padding inside a box, each side
ROW_GAP, COL_GAP = 64, 40
FRAME_TOP, FRAME_BOTTOM, FRAME_SIDE = 90, 26, 60
LONE_MIN = 0.7           # boxes alone in their row share one width, at least this share of the column
DB_MIN_W, DB_RY = 300, 16
EDGE, EDGE_TEXT, BOX_BG = "#8b98ad", "#aab4c3", "#22304a"
BORDER = {"box": EDGE, "spec": COLORS["s"], "impl": COLORS["k"]}   # spec = standard (dashed), impl = implementation

CAP_MAX_CHARS = 38       # longer sentences are split at a comma or period
CAP_LEAD, CAP_TAIL, CAP_MERGE_GAP = 0.08, 0.12, 0.25
BEAT_MAX = 0.42           # longest heartbeat on the word being read

GHEAD_FONTS = """
      @font-face { font-family: "D2Coding"; src: url("assets/fonts/D2Coding-Regular.ttf") format("truetype"); font-weight: 400; }
      @font-face { font-family: "Pretendard"; src: url("assets/fonts/Pretendard-Medium.woff2") format("woff2"); font-weight: 500; }
      @font-face { font-family: "Pretendard"; src: url("assets/fonts/Pretendard-Bold.woff2") format("woff2"); font-weight: 700; }"""

font = TTFont(ROOT / "assets/fonts/D2Coding-Regular.ttf")
CMAP, HMTX = font.getBestCmap(), font["hmtx"]


def cells(text):
    """Width in half-width cells (D2Coding: Latin 500 units, Hangul 1000)."""
    total = 0
    for ch in text:
        g = CMAP.get(ord(ch))
        total += (HMTX[g][0] / 500) if g else 2
    return total


def parse_line(src):
    """'<k>SET</k> key' -> [('k','SET'), ('w',' key')]"""
    out, pos = [], 0
    for m in re.finditer(r"<([a-z])>(.*?)</\1>", src):
        if m.start() > pos:
            out.append(("w", src[pos:m.start()]))
        out.append((m.group(1), m.group(2)))
        pos = m.end()
    if pos < len(src):
        out.append(("w", src[pos:]))
    return out


def font_size(line_cells, n_lines):
    fs_w = (BOX_W - 2 * BOX_PAD_X) / (0.5 * max(line_cells, 1))
    fs_h = BOX_MAX_H / (LINE_H * n_lines + 2 * BOX_PAD_EM)
    return round(min(FS_MAX, fs_w, fs_h), 1)


def r3(x):
    return round(x, 3)


def build_shot(n, shot, t_shot, t_start, t_end):
    sid = f"shot-{n:02d}"
    p = f"s{n:02d}"
    dur = t_end - t_start
    sent_local = [s["start"] - t_start for s in t_shot["sentences"]]

    # Units in DOM order: each line = lead + chars. Track text per line for sizing.
    lines_html, units, lines = [], [], []   # units: (line_idx, char or None)
    for b_i, block in enumerate(shot["blocks"]):
        for src in block["lines"]:
            li = len(lines)
            pre = bool(block.get("pretyped"))
            spans = [f'<span class="u lead"></span>']
            units.append((li, None, pre, b_i))
            text = ""
            for cls, seg in parse_line(src):
                for ch in seg:
                    spans.append(f'<span class="u ch {cls}{" p" if pre else ""}">{html.escape(ch)}</span>')
                    units.append((li, ch, pre, b_i))
                    text += ch
            lines.append(text)
            lines_html.append(f'<div class="ln{" p" if pre else ""}">{"".join(spans)}</div>')

    # Typing steps per block.
    visible = {}       # line_idx -> typed text so far
    for u_i, (li, ch, pre, _) in enumerate(units):
        if pre:
            visible[li] = visible.get(li, "") + (ch or "")
    steps, offs = [], []

    def state(cursor_line):
        """(scale of the text, scaleY of the 1000px box plate) for what is on screen."""
        if not visible:
            fs, n = font_size(1, 1), 1
        else:
            widest = max(cells(t) + (1 if l == cursor_line else 0) for l, t in visible.items())
            fs, n = font_size(widest, len(visible)), len(visible)
        return fs, round(fs / FS_BASE, 4), round(fs * (LINE_H * n + 2 * BOX_PAD_EM) / 1000, 4)

    _, s0, by0 = state(None)
    cur = (s0, by0)
    min_fs = 999
    for b_i, block in enumerate(shot["blocks"]):
        if block.get("pretyped"):
            continue
        idx = [u for u, (_, _, _, b) in enumerate(units) if b == b_i]
        t0 = 0.0 if block["at"] == 0 else sent_local[block["at"]] + 0.05
        nxt = [sent_local[b["at"]] + 0.05 for b in shot["blocks"][b_i + 1:] if b["at"] > block["at"]]
        window = (nxt[0] if nxt else dur) - t0
        typing = min(TYPE_FRACTION * window, len(idx) / 9.0)
        step = typing / len(idx)
        if 1 / step > 32:
            print(f"  ! {sid} block {b_i}: {1 / step:.0f} chars/s")
        for k, u in enumerate(idx):
            li, ch, _, _ = units[u]
            visible[li] = visible.get(li, "") + (ch or "")
            fs, sc, by = state(li)
            t = t0 + k * step
            changed = abs(sc - cur[0]) > 0.003 or abs(by - cur[1]) > 0.003
            if changed:
                cur = (sc, by)
            min_fs = min(min_fs, fs)
            steps.append([r3(t), u, sc if changed else 0, by if changed else 0, r3(min(0.1, step))])
        offs.append([r3(t0 + typing + 0.35), idx[-1]])
    min_fs = min(min_fs, state(None)[0])
    if min_fs < FS_WARN:
        print(f"  ! {sid}: font down to {min_fs}px")

    # terminal title: files are shown as `cat <file>`, commands (no extension) as typed
    f = html.escape(shot["file"])
    tab = f'<b>❯</b> {f}' if "." not in f else f'<b>❯</b> <i>cat</i> {f}'
    return sid, f"""<template>
  <style>{GHEAD_FONTS}
    #root {{ position: absolute; inset: 0; }}
    #{p}-tab {{
      position: absolute; left: 44px; top: {PROGRESS_H}px; height: {EDITOR_TOP - PROGRESS_H}px; white-space: pre;
      font: 400 30px/{EDITOR_TOP - PROGRESS_H}px "D2Coding", monospace; color: #e6edf3;
    }}
    #{p}-tab b {{ color: {ACCENT}; font-weight: 400; }}
    #{p}-tab i {{ color: #7d8590; font-style: normal; }}
    #{p}-stage {{
      position: absolute; left: 0; top: {EDITOR_TOP}px; width: {W}px; height: {EDITOR_BOTTOM - EDITOR_TOP}px;
      display: flex; align-items: center; justify-content: center;
    }}
    #{p}-plate {{
      position: absolute; left: {(W - BOX_W) // 2}px; top: calc(50% - 500px); width: {BOX_W}px; height: 1000px;
      background: #172033;
    }}
    #{p}-box {{
      position: relative; text-align: left;
      font-family: "D2Coding", monospace; font-size: {FS_BASE}px; line-height: {LINE_H}; color: #ffffff;
    }}
    #{p}-box .ln, #{p}-box .ch {{ display: none; }}
    #{p}-box .ln {{ white-space: pre; }}
    #{p}-box .ln.p {{ display: block; }}
    #{p}-box .ch.p {{ display: inline; }}
    #{p}-box .u[data-c="1"]::after {{ content: "\\258c"; color: {ACCENT}; }}
{chr(10).join(f"    #{p}-box .{k} {{ color: {v}; }}" for k, v in COLORS.items())}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    <div id="{p}-tab" data-layout-ignore>{tab}</div>
    <div id="{p}-stage">
      <div id="{p}-plate"></div>
      <div id="{p}-box">
        {(chr(10) + "        ").join(lines_html)}
      </div>
    </div>
  </div>
  <script>
    (() => {{
      const tl = gsap.timeline({{ paused: true }});
      const box = document.getElementById("{p}-box");
      const plate = document.getElementById("{p}-plate");
      const units = box.querySelectorAll(".u");
      // [time, unit index, text scale, plate scaleY (0 = unchanged), tween duration]
      const STEPS = {json.dumps(steps, separators=(",", ":"))};
      tl.set(box, {{ scale: {s0} }}, 0);
      tl.set(plate, {{ scaleY: {by0} }}, 0);
      // [time, unit index]: cursor leaves when a block finishes typing
      const OFFS = {json.dumps(offs, separators=(",", ":"))};
      let prev = null;
      for (const [t, i, sc, by, d] of STEPS) {{
        const u = units[i];
        if (u.classList.contains("lead")) tl.set(u.parentNode, {{ display: "block" }}, t);
        else tl.set(u, {{ display: "inline" }}, t);
        if (prev) tl.set(prev, {{ attr: {{ "data-c": "0" }} }}, t);
        tl.set(u, {{ attr: {{ "data-c": "1" }} }}, t);
        if (sc) {{
          tl.to(box, {{ scale: sc, duration: d, ease: "power2.out" }}, t);
          tl.to(plate, {{ scaleY: by, duration: d, ease: "power2.out" }}, t);
        }}
        prev = u;
      }}
      for (const [t, i] of OFFS) tl.set(units[i], {{ attr: {{ "data-c": "0" }} }}, t);
      tl.set({{}}, {{}}, {r3(dur - 0.001)});
      window.__timelines["{sid}"] = tl;
    }})();
  </script>
</template>
"""


def plain(src):
    return "".join(seg for _, seg in parse_line(src))


def markup(src):
    return "".join(html.escape(seg) if cls == "w" else f'<span class="{cls}">{html.escape(seg)}</span>'
                   for cls, seg in parse_line(src))


def fit(src, fs, room):
    """Largest size <= fs at which src fits in room px (a D2Coding half-width cell is 0.5 em)."""
    c = cells(plain(src))
    return round(min(fs, room / (0.5 * c)), 1) if c else fs


def need_w(nd):
    return max(cells(plain(nd["text"])) * 0.5 * NODE_FS, cells(plain(nd.get("sub", ""))) * 0.5 * SUB_FS) + 2 * NODE_PAD


def item_h(nd, cw, gap):
    if "rows" in nd:
        return FRAME_TOP + measure(nd["rows"], cw - 2 * FRAME_SIDE, gap) + FRAME_BOTTOM
    if nd.get("kind") in ("text", "db"):
        return TEXT_H if nd["kind"] == "text" else DB_H
    return NODE_H_SUB if nd.get("sub") else NODE_H


def measure(rows, width, gap):
    total = 0
    for i, row in enumerate(rows):
        cw = (width - (len(row) - 1) * COL_GAP) / len(row)
        total += (gap if i else 0) + max(item_h(nd, cw, gap) for nd in row if nd)
    return total


def place(rows, x0, y0, width, gap, out):
    """Append (node, x, y, w, h) for each item of rows; a frame comes before what it contains.
    A row splits the width into equal columns (null = empty column)."""
    lone = [r[0] for r in rows if len(r) == 1 and "rows" not in r[0] and r[0].get("kind", "box") in BORDER]
    lone_w = min(width, max([LONE_MIN * width] + [need_w(nd) for nd in lone]))
    y = y0
    for row in rows:
        cw = (width - (len(row) - 1) * COL_GAP) / len(row)
        row_h = max(item_h(nd, cw, gap) for nd in row if nd)
        for j, nd in enumerate(row):
            if not nd:
                continue
            kind, h = nd.get("kind", "box"), item_h(nd, cw, gap)
            if "w" in nd:
                w = min(nd["w"], cw)
            elif kind == "db":
                w = min(cw, max(DB_MIN_W, need_w(nd)))
            elif len(row) == 1 and kind in BORDER and "rows" not in nd:
                w = lone_w
            else:
                w = cw
            x, top = x0 + j * (cw + COL_GAP) + (cw - w) / 2, y + (row_h - h) / 2
            out.append((nd, x, top, w, h))
            if "rows" in nd:
                place(nd["rows"], x + FRAME_SIDE, top + FRAME_TOP, w - 2 * FRAME_SIDE, gap, out)
        y += row_h + gap


def cue(at, t_shot, t_start, sid):
    """Shot-local time for `at`. None = there from the start, int = when that sentence starts,
    "+1.5" = seconds into the shot, "word" or "1:word" = when the first spoken word starting
    with `word` begins (in sentence 1 only)."""
    if at is None:
        return None
    sents = t_shot["sentences"]
    if isinstance(at, int):
        return 0.0 if at == 0 else r3(sents[at]["start"] - t_start + 0.05)
    if at.startswith("+"):
        return float(at[1:])
    m = re.fullmatch(r"(\d+):(.+)", at)
    word = m.group(2) if m else at
    for s in ([sents[int(m.group(1))]] if m else sents):
        for w in s["words"]:
            if w["text"].startswith(word):
                return r3(max(0.0, w["start"] - t_start))
    raise SystemExit(f"{sid}: no spoken word starts with {at!r}")


def arrow_geo(a, b):
    """Straight arrow between the borders of rects a and b: line end, tip, head polygon."""
    (ax, ay, aw, ah), (bx, by, bw, bh) = a, b
    acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
    dist = math.hypot(bcx - acx, bcy - acy)
    ux, uy = (bcx - acx) / dist, (bcy - acy) / dist

    def reach(w, h):
        return min(w / 2 / abs(ux) if ux else 1e9, h / 2 / abs(uy) if uy else 1e9) + 6

    x1, y1 = acx + ux * reach(aw, ah), acy + uy * reach(aw, ah)
    x2, y2 = bcx - ux * reach(bw, bh), bcy - uy * reach(bw, bh)
    head = [(x2, y2), (x2 - ux * 20 - uy * 13, y2 - uy * 20 + ux * 13), (x2 - ux * 20 + uy * 13, y2 - uy * 20 - ux * 13)]
    return (x1, y1, x2 - ux * 18, y2 - uy * 18), head, (ux, uy)


def build_diagram(n, shot, t_shot, t_start, t_end):
    sid, p = f"shot-{n:02d}", f"s{n:02d}"
    dur = t_end - t_start
    d = shot["diagram"]
    gap = d.get("gap", ROW_GAP)
    items = []
    place(d["rows"], 0, 0, DIA_W, gap, items)
    nat_h = measure(d["rows"], DIA_W, gap)
    s = min(1.0, DIA_H / nat_h)

    tweens, sets, live = [], [], []    # tweens: [t, selector, from (null = to-tween), to]; live: (t, key)
    paint = {}                         # key -> [(selector, property, normal colour)] for the mint highlight
    frames, nodes, badges, labels, svg = [], [], [], [], []
    rect, t_of = {}, {}
    min_fs = 999
    appear = ({"opacity": 0, "scale": 0.94}, {"opacity": 1, "scale": 1, "duration": 0.3, "ease": "power2.out"})

    for k, (nd, x, y, w, h) in enumerate(items):
        key = nd.get("id", f"i{k}")
        el, kind = f"{p}-{key}", nd.get("kind", "box")
        t = cue(nd.get("at"), t_shot, t_start, sid)
        rect[key], t_of[key] = (x, y, w, h), t
        hidden = " opacity: 0;" if t is not None else ""
        box = f"left: {r3(x)}px; top: {r3(y)}px; width: {r3(w)}px; height: {r3(h)}px;{hidden}"
        if "rows" in nd:
            style = "spec" if kind == "spec" else "box"
            fs = fit(nd["text"], FRAME_FS, w * 0.6)
            frames.append(f'<div id="{el}" class="fr {style}" style="{box}">'
                          f'<div class="lb" style="font-size: {fs}px;">{markup(nd["text"])}</div></div>')
            paint[key] = [(f"#{el}", "border", BORDER[style])]
        elif kind == "db":
            fs = fit(nd["text"], NODE_FS, w - 2 * NODE_PAD)
            rx, by = w / 2 - 2, h - DB_RY - 2
            nodes.append(f'''<div id="{el}" class="nd db" style="{box}">
          <svg width="{r3(w)}" height="{h}" viewBox="0 0 {r3(w)} {h}">
            <path class="cyl" d="M2 {DB_RY + 2} V{by} A{r3(rx)} {DB_RY} 0 0 0 {r3(w - 2)} {by} V{DB_RY + 2}" />
            <ellipse class="cyl" cx="{r3(w / 2)}" cy="{DB_RY + 2}" rx="{r3(rx)}" ry="{DB_RY}" />
          </svg>
          <div class="t" style="top: {2 * DB_RY + 2}px; font-size: {fs}px;">{markup(nd["text"])}</div>
        </div>''')
            paint[key] = [(f"#{el} .cyl", "stroke", EDGE)]
        else:
            fs = fit(nd["text"], NODE_FS, w - 2 * NODE_PAD)
            sub = (f'<div class="sub" style="font-size: {fit(nd["sub"], SUB_FS, w - 2 * NODE_PAD)}px;">'
                   f'{markup(nd["sub"])}</div>') if nd.get("sub") else ""
            nodes.append(f'<div id="{el}" class="nd {kind}" style="{box}">'
                         f'<div class="t" style="font-size: {fs}px;">{markup(nd["text"])}</div>{sub}</div>')
            if kind in BORDER:
                paint[key] = [(f"#{el}", "border", BORDER[kind])]
        min_fs = min(min_fs, fs * s)
        if t is not None:
            tweens.append([t, f"#{el}", *appear])
            if key in paint:
                live.append((t, key))
        if nd.get("badge"):
            bt = cue(nd["badge_at"], t_shot, t_start, sid) if "badge_at" in nd else (None if t is None else r3(t + 0.18))
            pop = " transform: scale(0);" if bt is not None else ""
            badges.append(f'<div id="{el}-b" class="bd {kind}" style="right: {r3(DIA_W - (x + w - 18))}px; '
                          f'top: {r3(y - 22)}px;{pop}">{html.escape(nd["badge"])}</div>')
            if bt is not None:
                tweens.append([bt, f"#{el}-b", {"scale": 0}, {"scale": 1, "duration": 0.3, "ease": "back.out(2)"}])

    for k, a in enumerate(d.get("arrows", [])):
        key = a.get("id", f"a{k}")
        el = f"{p}-{key}"
        (x1, y1, x2, y2), head, (ux, uy) = arrow_geo(rect[a["from"]], rect[a["to"]])
        length = r3(math.hypot(x2 - x1, y2 - y1))
        if "at" in a:
            t = cue(a["at"], t_shot, t_start, sid)
        else:
            ends = [v for v in (t_of[a["from"]], t_of[a["to"]]) if v is not None]
            t = max(ends) if ends else None
        off = length if t is not None else 0
        pts = " ".join(f"{r3(px)},{r3(py)}" for px, py in head)
        svg.append(f'<line id="{el}-l" x1="{r3(x1)}" y1="{r3(y1)}" x2="{r3(x2)}" y2="{r3(y2)}" '
                   f'stroke="{EDGE}" stroke-width="5" stroke-dasharray="{length}" stroke-dashoffset="{off}" />')
        svg.append(f'<polygon id="{el}-h" points="{pts}" fill="{EDGE}" opacity="{0 if t is not None else 1}" />')
        paint[key] = [(f"#{el}-l", "stroke", EDGE), (f"#{el}-h", "fill", EDGE)]
        if t is not None:
            tweens.append([t, f"#{el}-l", {"attr": {"stroke-dashoffset": length}},
                           {"attr": {"stroke-dashoffset": 0}, "duration": 0.25, "ease": "none"}])
            sets.append([r3(t + 0.25), f"#{el}-h", {"opacity": 1}])
            if "at" in a:
                live.append((t, key))
        if a.get("label"):
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            tw, th = cells(a["label"]) * 0.5 * ARROW_FS, ARROW_FS * 1.25
            if abs(ux) < 0.35:      # mostly vertical: beside the line
                lx, ly, cls = (mx - 20 - tw if a.get("side") == "left" else mx + 20), my - th / 2, "al"
            elif abs(uy) < 0.35:    # mostly horizontal: above the line
                lx, ly, cls = mx - tw / 2, my - th - 8, "al"
            else:                   # diagonal: on the line, over a plate-coloured chip
                lx, ly, cls = mx - tw / 2 - 12, my - th / 2, "al chip"
            hid = " opacity: 0;" if t is not None else ""
            labels.append(f'<div id="{el}-t" class="{cls}" style="left: {r3(lx)}px; top: {r3(ly)}px;{hid}">'
                          f'{html.escape(a["label"])}</div>')
            paint[key].append((f"#{el}-t", "color", EDGE_TEXT))
            if t is not None:
                tweens.append([r3(t + 0.1), f"#{el}-t", {"opacity": 0}, {"opacity": 1, "duration": 0.2}])

    arrow_keys = {a.get("id", f"a{k}") for k, a in enumerate(d.get("arrows", []))}
    for key, at in d.get("focus", []):
        t = cue(at, t_shot, t_start, sid)
        live.append((t, key))
        if key not in arrow_keys:     # arrows only change colour
            tweens.append([t, f"#{p}-{key}", None,
                           {"scale": 1.06, "duration": 0.18, "yoyo": True, "repeat": 1, "ease": "power2.out"}])

    def colour(sel, prop, c):
        return [sel, {"border": {"borderColor": c}, "stroke": {"attr": {"stroke": c}},
                      "fill": {"attr": {"fill": c}}, "color": {"color": c}}[prop]]

    # mint = what the narration is on right now; it moves on, never stays on two things
    prev = None
    for t, key in sorted(live, key=lambda e: e[0]):
        if prev and prev != key:
            sets += [[t, *colour(sel, prop, c)] for sel, prop, c in paint[prev]]
        sets += [[t, *colour(sel, prop, ACCENT)] for sel, prop, _ in paint[key]]
        prev = key

    if min_fs < DIA_FS_WARN:
        print(f"  ! {sid}: diagram text down to {min_fs:.0f}px")

    f = html.escape(shot["file"])
    tab = f'<b>❯</b> {f}' if "." not in f else f'<b>❯</b> <i>cat</i> {f}'
    top = DIA_TOP + (DIA_BOTTOM - DIA_TOP - nat_h * s) / 2
    return sid, f"""<template>
  <style>{GHEAD_FONTS}
    #root {{ position: absolute; inset: 0; }}
    #{p}-tab {{
      position: absolute; left: 44px; top: {PROGRESS_H}px; height: {EDITOR_TOP - PROGRESS_H}px; white-space: pre;
      font: 400 30px/{EDITOR_TOP - PROGRESS_H}px "D2Coding", monospace; color: #e6edf3;
    }}
    #{p}-tab b {{ color: {ACCENT}; font-weight: 400; }}
    #{p}-tab i {{ color: #7d8590; font-style: normal; }}
    #{p}-plate {{
      position: absolute; left: {(W - BOX_W) // 2}px; top: {DIA_TOP}px; width: {BOX_W}px; height: {DIA_BOTTOM - DIA_TOP}px;
      background: #172033;
    }}
    #{p}-dia {{
      position: absolute; left: {r3((W - DIA_W * s) / 2)}px; top: {r3(top)}px; width: {DIA_W}px; height: {nat_h}px;
      transform: scale({r3(s)}); transform-origin: 0 0; font-family: "D2Coding", monospace; color: #ffffff;
    }}
    #{p}-dia svg {{ position: absolute; left: 0; top: 0; overflow: visible; }}
    #{p}-dia .fr {{ position: absolute; box-sizing: border-box; border: 4px dashed {EDGE}; border-radius: 18px; }}
    #{p}-dia .fr.spec {{ border-color: {BORDER["spec"]}; }}
    #{p}-dia .fr .lb {{ position: absolute; left: 28px; top: 14px; white-space: pre; color: #c9d1d9; }}
    #{p}-dia .fr.spec .lb {{ color: {BORDER["spec"]}; }}
    #{p}-dia .nd {{
      position: absolute; box-sizing: border-box; display: flex; flex-direction: column; align-items: center;
      justify-content: center; white-space: pre; line-height: 1.15;
      background: {BOX_BG}; border: 4px solid {EDGE}; border-radius: 14px;
    }}
    #{p}-dia .nd.spec {{ border-style: dashed; border-color: {BORDER["spec"]}; }}
    #{p}-dia .nd.impl {{ border-color: {BORDER["impl"]}; }}
    #{p}-dia .nd.text, #{p}-dia .nd.db {{ background: none; border: none; }}
    #{p}-dia .nd .sub {{ margin-top: 6px; color: {EDGE_TEXT}; }}
    #{p}-dia .nd.db .t {{ position: absolute; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; }}
    #{p}-dia .cyl {{ fill: {BOX_BG}; stroke: {EDGE}; stroke-width: 4; }}
    #{p}-dia .bd {{
      position: absolute; height: {round(BADGE_FS * 1.5)}px; padding: 0 16px; border-radius: 999px; white-space: pre;
      font: 700 {BADGE_FS}px/{round(BADGE_FS * 1.5)}px "Pretendard", sans-serif; color: #172033; background: {EDGE};
    }}
    #{p}-dia .bd.spec {{ background: {BORDER["spec"]}; }}
    #{p}-dia .bd.impl {{ background: {BORDER["impl"]}; }}
    #{p}-dia .al {{ position: absolute; white-space: pre; font-size: {ARROW_FS}px; line-height: 1.25; color: {EDGE_TEXT}; }}
    #{p}-dia .al.chip {{ padding: 0 12px; background: #172033; }}
{chr(10).join(f"    #{p}-dia .{k} {{ color: {v}; }}" for k, v in COLORS.items())}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    <div id="{p}-tab" data-layout-ignore>{tab}</div>
    <div id="{p}-plate"></div>
    <div id="{p}-dia">
      {(chr(10) + "      ").join(frames)}
      <svg width="{DIA_W}" height="{nat_h}" viewBox="0 0 {DIA_W} {nat_h}">
        {(chr(10) + "        ").join(svg)}
      </svg>
      {(chr(10) + "      ").join(nodes + labels + badges)}
    </div>
  </div>
  <script>
    (() => {{
      const tl = gsap.timeline({{ paused: true }});
      // [time, selector, from (null = tween from where it is), to]: boxes appear, arrows draw, badges pop
      const TWEENS = {json.dumps(tweens, ensure_ascii=False, separators=(",", ":"))};
      // [time, selector, vars]: arrow heads, and the mint highlight moving with the narration
      const SETS = {json.dumps(sets, ensure_ascii=False, separators=(",", ":"))};
      for (const [t, sel, from, to] of TWEENS) {{
        if (from) tl.fromTo(sel, from, to, t);
        else tl.to(sel, to, t);
      }}
      for (const [t, sel, vars] of SETS) tl.set(sel, vars, t);
      tl.set({{}}, {{}}, {r3(dur - 0.001)});
      window.__timelines["{sid}"] = tl;
    }})();
  </script>
</template>
"""


def split_caption(text):
    if len(text) <= CAP_MAX_CHARS:
        return [text]
    words = text.split()
    best, best_d = None, 1e9
    pos = 0
    for i, w in enumerate(words[:-1]):
        pos += len(w) + 1
        if w[-1] in ",.?!" and abs(pos - len(text) / 2) < best_d:
            best, best_d = i + 1, abs(pos - len(text) / 2)
    if best is None:
        return [text]
    return split_caption(" ".join(words[:best])) + split_caption(" ".join(words[best:]))


def build_captions(timing, total):
    groups = []
    for shot in timing["shots"]:
        for s in shot["sentences"]:
            words = s["words"]
            k = 0
            for part in split_caption(s["text"]):
                n = len(part.split())
                groups.append(words[k:k + n])
                k += n
    spans = []
    for i, g in enumerate(groups):
        start = 0.0 if i == 0 else g[0]["start"] - CAP_LEAD
        spans.append([start, g[-1]["end"] + CAP_TAIL])
    for i in range(len(spans) - 1):
        if spans[i + 1][0] - spans[i][1] < CAP_MERGE_GAP:
            spans[i][1] = spans[i + 1][0]
    spans[-1][1] = total

    items, sets = [], []
    for i, (g, (a, b)) in enumerate(zip(groups, spans)):
        words = " ".join(f'<span class="w" id="cw-{i:02d}-{j}">{html.escape(w["text"])}</span>'
                         for j, w in enumerate(g))
        items.append(f'''    <div id="cg-{i:02d}" class="cg clip" data-start="{r3(a)}" data-duration="{r3(b - a)}" data-track-index="0">
      <div class="txt">{words}</div>
    </div>''')
        for j, w in enumerate(g):
            nxt = g[j + 1]["start"] if j + 1 < len(g) else None
            beat = min(BEAT_MAX, (nxt if nxt is not None else w["end"]) - w["start"])
            sets.append([f"cw-{i:02d}-{j}", r3(w["start"]), r3(nxt) if nxt is not None else None, r3(beat)])
    return f"""<template>
  <style>{GHEAD_FONTS}
    #root {{ position: absolute; inset: 0; }}
    .cg {{ position: absolute; left: 0; top: {EDITOR_BOTTOM}px; width: {W}px; height: 520px; }}
    /* the panel stays on for the whole video; only the caption groups come and go */
    .panel {{
      position: absolute; left: 0; top: {EDITOR_BOTTOM}px; width: {W}px; height: 520px;
      background: #080a10; border-top: 2px solid #21262d;
    }}
    .cg .txt {{
      position: absolute; left: 110px; right: 110px; top: 0; bottom: 0;
      display: flex; align-items: center; justify-content: center; flex-wrap: wrap; align-content: center;
      text-align: center; word-break: keep-all; overflow: visible;
      font: 700 48px/1.7 "Pretendard", sans-serif; letter-spacing: -0.01em; color: #ffffff;
      text-shadow: 0 2px 3px rgba(0, 0, 0, 0.85);
    }}
    .cg .w {{ margin: 0 0.18em; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
    <div class="panel"></div>
{chr(10).join(items)}
  </div>
  <script>
    (() => {{
      const tl = gsap.timeline({{ paused: true }});
      const NOW = "{ACCENT}", DONE = "#96989e";
      // [word id, time it is spoken, time the next word starts (null = last of its group), heartbeat length]
      const WORDS = {json.dumps(sets, separators=(",", ":"))};
      for (const [id, on, off, beat] of WORDS) {{
        const el = document.getElementById(id);
        tl.set(el, {{ color: NOW }}, on);
        if (off !== null) tl.set(el, {{ color: DONE }}, off);
        // heartbeat: two beats (lub-dub) when the word lasts long enough, one beat otherwise
        if (beat >= 0.3) {{
          tl.to(el, {{ scale: 1.1, duration: beat * 0.2, ease: "power2.out" }}, on)
            .to(el, {{ scale: 1, duration: beat * 0.25, ease: "power1.in" }}, ">")
            .to(el, {{ scale: 1.05, duration: beat * 0.17, ease: "power2.out" }}, ">")
            .to(el, {{ scale: 1, duration: beat * 0.38, ease: "power1.inOut" }}, ">");
        }} else {{
          tl.to(el, {{ scale: 1.08, duration: beat * 0.4, ease: "power2.out" }}, on)
            .to(el, {{ scale: 1, duration: beat * 0.6, ease: "power1.in" }}, ">");
        }}
      }}
      tl.set({{}}, {{}}, {r3(total - 0.001)});
      window.__timelines["captions"] = tl;
    }})();
  </script>
</template>
"""


def build_chrome(total):
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    #chrome-track {{ position: absolute; left: 0; top: 0; width: {W}px; height: {PROGRESS_H}px; background: #21262d; }}
    #chrome-fill {{
      position: absolute; left: 0; top: 0; width: {W}px; height: {PROGRESS_H}px;
      background: {ACCENT}; transform-origin: 0 50%;
    }}
    #chrome-bar {{
      position: absolute; left: 0; top: {PROGRESS_H}px; width: {W}px; height: {EDITOR_TOP - PROGRESS_H}px;
      background: #161b22; border-bottom: 2px solid #21262d; box-sizing: border-box;
    }}
    #chrome-term {{ position: absolute; left: 0; top: {EDITOR_TOP}px; width: {W}px; height: {EDITOR_BOTTOM - EDITOR_TOP}px; background: #0d1117; }}
  </style>
  <div id="root" data-composition-id="chrome" data-width="{W}" data-height="{H}">
    <div id="chrome-track"></div>
    <div id="chrome-fill"></div>
    <div id="chrome-bar"></div>
    <div id="chrome-term"></div>
  </div>
  <script>
    (() => {{
      // progress bar fills left to right over the whole video
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo(document.getElementById("chrome-fill"), {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total}, ease: "none" }}, 0);
      window.__timelines["chrome"] = tl;
    }})();
  </script>
</template>
"""


def main():
    content = json.loads((ROOT / "content.json").read_text())
    timing = json.loads((ROOT / "build/timing.json").read_text())
    total = timing["duration"]
    comp = ROOT / "compositions"
    comp.mkdir(exist_ok=True)
    for old in comp.glob("shot-*.html"):
        old.unlink()

    starts = [0.0] + [t["sentences"][0]["start"] for t in timing["shots"][1:]]
    ends = starts[1:] + [total]
    hosts = []
    for n, (shot, t_shot, a, b) in enumerate(zip(content["shots"], timing["shots"], starts, ends), 1):
        sid, doc = (build_diagram if "diagram" in shot else build_shot)(n, shot, t_shot, a, b)
        (comp / f"{sid}.html").write_text(doc)
        hosts.append(f'''      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html"
        data-start="{r3(a)}" data-duration="{r3(b - a)}" data-track-index="1" data-track-kind="graphics"
        data-width="{W}" data-height="{H}" style="z-index: 2"></div>''')
    (comp / "chrome.html").write_text(build_chrome(total))
    (comp / "captions.html").write_text(build_captions(timing, total))

    index = f"""<!doctype html>
<html lang="ko" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <!-- Generated by tools/build.py from content.json + build/timing.json -->
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000000; }}
      #root {{ position: relative; width: 100%; height: 100%; background: #000000; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
      <div id="chrome" data-composition-id="chrome" data-composition-src="compositions/chrome.html"
        data-start="0" data-duration="{total}" data-track-index="0" data-track-kind="graphics"
        data-width="{W}" data-height="{H}" style="z-index: 1"></div>
{chr(10).join(hosts)}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html"
        data-start="0" data-duration="{total}" data-track-index="2" data-track-kind="captions"
        data-width="{W}" data-height="{H}" style="z-index: 3"></div>
      <audio id="narration" class="clip" src="assets/audio/narration.wav" data-start="0"
        data-duration="{total}" data-track-index="3" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
    (ROOT / "index.html").write_text(index)
    print(f"{len(hosts)} shots, {total}s")


if __name__ == "__main__":
    main()
