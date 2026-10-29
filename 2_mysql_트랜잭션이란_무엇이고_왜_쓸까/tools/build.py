"""Generate the HyperFrames compositions from content.json + build/timing.json.

  python3 tools/build.py

Writes index.html, compositions/chrome.html, compositions/shot-NN.html and
compositions/captions.html. Re-run after changing content.json or the narration.
"""
import html
import json
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
        sid, doc = build_shot(n, shot, t_shot, a, b)
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
