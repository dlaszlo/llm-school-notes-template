#!/usr/bin/env python3
"""Header banner at the top of every wiki page.

Usage: python3 tools/banner.py wiki/<subject>/<page>.md [...]

For each page it writes wiki/assets/banner/<page>.svg (subject color and
icon, with the page title) and, if the page body does not start with an
image, inserts the link right after the frontmatter. Safe to re-run: an
existing banner is refreshed, never inserted twice. Run it from the
project root.

Subjects and reader-facing labels come from tools/subjects.json:

    "subjects": {
      "math": {"name": "Math", "emoji": "📐", "dark": "#ca6f1e",
               "light": "#fdebd0", "icon": "math"}
    }

The key is the subject's directory name under wiki/. Icons: bubble
(language), book (literature), column (history), coins (economics; optional
"mark", e.g. "$"), flask (science), briefcase (careers), math, globe
(geography, foreign languages), pencil (anything else). A ready palette of
dark/light pairs: #1f6fb2/#d6eaf8 blue, #7d3c98/#ebdef0 purple,
#a0640a/#fbeee0 brown, #1e8449/#d5f5e3 green, #117a65/#d0ece7 teal,
#b03a2e/#fadbd8 red, #ca6f1e/#fdebd0 orange, #2e4053/#d6dbdf slate.
"""
import html, json, os, re, sys, textwrap

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subjects.json")

def icon(kind, c, mark="$"):
    """Large icon in the left-hand circle (center 90,85)."""
    w = 'fill="#fff" stroke="%s" stroke-width="4" stroke-linejoin="round"' % c
    if kind == "bubble":
        return (f'<path d="M58,58 h64 a10,10 0 0 1 10,10 v30 a10,10 0 0 1 -10,10 h-34 l-16,14 v-14 h-14 a10,10 0 0 1 -10,-10 v-30 a10,10 0 0 1 10,-10 z" {w}/>'
                f'<circle cx="74" cy="83" r="4" fill="{c}"/><circle cx="90" cy="83" r="4" fill="{c}"/><circle cx="106" cy="83" r="4" fill="{c}"/>')
    if kind == "book":
        return (f'<path d="M90,62 q-18,-10 -38,-6 v54 q20,-4 38,6 z" {w}/><path d="M90,62 q18,-10 38,-6 v54 q-20,-4 -38,6 z" {w}/>'
                f'<path d="M60,70 q12,-3 22,2 M60,80 q12,-3 22,2 M98,72 q10,-5 22,-2 M98,82 q10,-5 22,-2" stroke="{c}" stroke-width="2.5" fill="none"/>')
    if kind == "column":
        return (f'<rect x="60" y="52" width="60" height="10" rx="2" {w}/><rect x="66" y="62" width="48" height="44" {w}/>'
                f'<path d="M78,64 v40 M90,64 v40 M102,64 v40" stroke="{c}" stroke-width="2.5"/><rect x="56" y="106" width="68" height="10" rx="2" {w}/>')
    if kind == "coins":
        return (f'<ellipse cx="80" cy="104" rx="24" ry="8" {w}/><ellipse cx="80" cy="94" rx="24" ry="8" {w}/><ellipse cx="80" cy="84" rx="24" ry="8" {w}/>'
                f'<circle cx="110" cy="72" r="18" {w}/><text x="110" y="79" font-size="20" font-weight="bold" text-anchor="middle" fill="{c}">{html.escape(mark)}</text>')
    if kind == "flask":
        return (f'<path d="M80,52 h20 M84,52 v22 l-22,36 a6,6 0 0 0 5,9 h46 a6,6 0 0 0 5,-9 l-22,-36 v-22" {w}/>'
                f'<path d="M70,102 l8,-13 h24 l8,13 z" fill="{c}" opacity="0.35"/><circle cx="86" cy="96" r="3" fill="#fff"/><circle cx="96" cy="102" r="2.5" fill="#fff"/>')
    if kind == "briefcase":
        return (f'<rect x="56" y="66" width="68" height="46" rx="6" {w}/><path d="M78,66 v-8 a4,4 0 0 1 4,-4 h16 a4,4 0 0 1 4,4 v8" {w}/>'
                f'<path d="M56,84 h68" stroke="{c}" stroke-width="3"/><rect x="84" y="80" width="12" height="9" rx="2" fill="{c}"/>')
    if kind == "math":
        return (f'<rect x="56" y="52" width="68" height="68" rx="10" {w}/><path d="M90,56 v60 M60,86 h60" stroke="{c}" stroke-width="2"/>'
                f'<g font-size="22" font-weight="bold" text-anchor="middle" fill="{c}"><text x="73" y="79">+</text><text x="107" y="79">−</text><text x="73" y="112">×</text><text x="107" y="112">÷</text></g>')
    if kind == "globe":
        return (f'<circle cx="90" cy="86" r="32" {w}/><ellipse cx="90" cy="86" rx="14" ry="32" fill="none" stroke="{c}" stroke-width="2.5"/>'
                f'<path d="M58,86 h64 M63,70 h54 M63,102 h54" stroke="{c}" stroke-width="2.5" fill="none"/>')
    # pencil: the generic icon
    return (f'<path d="M62,114 l6,-22 l40,-40 l16,16 l-40,40 z" {w}/><path d="M68,92 l16,16 M100,60 l16,16" stroke="{c}" stroke-width="2.5"/>'
            f'<path d="M62,114 l3,-11 l8,8 z" fill="{c}"/>')

DOODLES = {"bubble": ["Aa", "?!", "...", "abc", "«»", "@"], "book": ["✎", "❝", "★", "♥", "∞", "¶"],
           "column": ["⌛", "✦", "⚱", "☼", "⚔", "♛"], "coins": ["%", "$", "↗", "€", "£", "+"],
           "flask": ["°C", "H₂O", "⚗", "⚛", "m³", "O₂"], "briefcase": ["✓", "✉", "€", "☎", "%", "★"],
           "math": ["π", "∑", "√", "∞", "x²", "≠"], "globe": ["N", "⛰", "☀", "✈", "⚓", "☁"],
           "pencil": ["✎", "★", "?", "!", "✦", "✓"]}

def doodles(kind, c, seed=""):
    """Small, faint decoration on the right-hand side."""
    k = DOODLES.get(kind, DOODLES["pencil"])
    h = sum(ord(ch) * (i + 7) for i, ch in enumerate(seed))
    k = [k[(h + 5 * i) % len(k)] for i in range(3)]
    if len(set(k)) < 3:
        k = k[:1] + [t for t in k[1:] if t != k[0]] + [t for t in ["✦", "·", "*"]]
        k = k[:3]
    pos = [(815 - h % 20, 48, 30, -12 + h % 9), (860, 110 - h % 15, 26, 10 - h % 7), (770 + h % 25, 128, 22, 6)]
    return "".join(f'<text x="{x}" y="{y}" font-size="{s}" font-weight="bold" fill="{c}" opacity="0.18" text-anchor="middle" transform="rotate({r} {x} {y})">{html.escape(t)}</text>'
                   for (x, y, s, r), t in zip(pos, k))

def banner_svg(title, subject, kind_label, header):
    name, dark, light, kind = subject["name"], subject["dark"], subject["light"], subject.get("icon", "pencil")
    for size, width in ((34, 34), (29, 40), (25, 47)):
        lines = textwrap.wrap(title, width)
        if len(lines) <= 2 or size == 25:
            break
    lines = lines[:3]
    lh = size * 1.2
    y0 = 92 - (len(lines) - 1) * lh / 2 + size * 0.35
    tspans = "".join(f'<tspan x="180" y="{y0 + i * lh:.0f}">{html.escape(l)}</tspan>' for i, l in enumerate(lines))
    label = f"{name} · {kind_label}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 170" font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img" aria-label="{html.escape(header)}: {html.escape(title)} ({html.escape(name)})">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="#ffffff"/></linearGradient></defs>
  <rect width="900" height="170" rx="18" fill="url(#g)"/>
  <rect x="0" y="160" width="900" height="10" rx="4" fill="{dark}" opacity="0.85"/>
  {doodles(kind, dark, title)}
  <circle cx="90" cy="86" r="58" fill="{light}" stroke="{dark}" stroke-width="4"/>
  {icon(kind, dark, subject.get("mark", "$"))}
  <rect x="178" y="14" width="{len(label) * 8.2 + 24:.0f}" height="26" rx="13" fill="{dark}"/>
  <text x="190" y="32" font-size="15" font-weight="bold" fill="#fff">{html.escape(label)}</text>
  <text font-size="{size}" font-weight="bold" fill="#1c2833">{tspans}</text>
</svg>
'''

def process(md, config):
    subject_dir = os.path.basename(os.path.dirname(md))
    stem = os.path.splitext(os.path.basename(md))[0]
    if stem in ("index", "log"):
        return "skip"
    subject = config["subjects"].get(subject_dir)
    if not subject:
        return "no-subject (add it to tools/subjects.json)"
    labels = config["labels"]
    text = open(md, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = m.group(1)
    title = re.search(r"^title: (.*)$", fm, re.M).group(1).strip()
    if title[:1] in "\"'":
        title = title[1:-1].replace('\\"', '"')
    typ = re.search(r"^type: (.*)$", fm, re.M).group(1).strip()
    kind_label = labels.get(typ, labels["topic"])
    catch = re.search(r"^catch_up: *(\w+)", fm, re.M)
    if catch and catch.group(1) == "open":
        kind_label = labels["catch-up"]
    body = text[m.end():]
    first = next((l for l in body.split("\n") if l.strip()), "")
    header = labels["header"]
    ours = first.startswith(f"![{header}:")
    if first.startswith("![") and not ours:
        return "has-image"
    os.makedirs("wiki/assets/banner", exist_ok=True)
    with open(f"wiki/assets/banner/{stem}.svg", "w", encoding="utf-8") as f:
        f.write(banner_svg(title, subject, kind_label, header))
    alt = f"{header}: {title}"
    if ours:
        line = f"![{alt}](../assets/banner/{stem}.svg)"
        if first != line:
            open(md, "w", encoding="utf-8").write(text[:m.end()] + body.replace(first, line, 1))
        return "updated"
    text = text[:m.end()] + f"\n![{alt}](../assets/banner/{stem}.svg)\n" + body
    open(md, "w", encoding="utf-8").write(text)
    return "inserted"

if __name__ == "__main__":
    with open(CONFIG, encoding="utf-8") as f:
        config = json.load(f)
    for p in sys.argv[1:]:
        print(process(p, config), p)
