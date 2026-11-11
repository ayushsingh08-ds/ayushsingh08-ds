"""Compile pure-SVG Camo-safe README cards and README.md from profile.json.

Every card uses native SVG primitives (<rect>, <text>, <path>, <circle>, <image>)
with zero <foreignObject> or external @import CSS, ensuring deterministic rendering
behind GitHub's Camo image proxy.

Two live GitHub fetches feed the analytics cards, cached locally so offline
builds remain reproducible:

* ``assets/github_stats.json``  -- repository, follower, star and language counts
* ``assets/contributions.json`` -- public 12-month contribution calendar
"""

import collections
import datetime
import json
import os
import re
import urllib.request
import xml.etree.ElementTree

# ----------------- Root paths -----------------
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_JSON = os.path.join(WORKSPACE_DIR, "profile.json")
BASE64_ICONS_JSON = os.path.join(WORKSPACE_DIR, "assets", "base64_icons.json")
CARDS_DIR = os.path.join(WORKSPACE_DIR, "assets", "cards")
DARK_DIR = os.path.join(CARDS_DIR, "dark")
GITHUB_STATS_JSON = os.path.join(WORKSPACE_DIR, "assets", "github_stats.json")
CONTRIBUTIONS_JSON = os.path.join(WORKSPACE_DIR, "assets", "contributions.json")

os.makedirs(CARDS_DIR, exist_ok=True)
os.makedirs(DARK_DIR, exist_ok=True)

# ----------------- Content -----------------
with open(PROFILE_JSON, "r", encoding="utf-8") as f:
    profile = json.load(f)

with open(BASE64_ICONS_JSON, "r", encoding="utf-8") as f:
    icons = json.load(f)


def strip_tags(text):
    """Remove inline HTML fragments (e.g. <span>) and decode basic entities."""
    cleaned = re.sub(r"<[^>]+>", "", str(text))
    return cleaned.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


def xml_esc(text):
    """Escape XML special characters without double-escaping existing entities."""
    s = str(text)
    s = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", s)
    return s.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def html_attr(text):
    """Escape plain text for HTML attributes in README.md."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


GITHUB_URL = profile["about_me"]["github_url"]
GITHUB_USER = GITHUB_URL.split("/")[-1]
EMAIL = profile["about_me"]["email"]
PORTFOLIO_URL = profile["about_me"]["portfolio_url"]
RESUME_URL = profile["about_me"]["resume_url"]

# ----------------- Layout grid -----------------
GRID = 880

CARD_SIZES = {
    "header": (GRID, 220),
    "hero": (GRID, 250),
    "action": (GRID, 48),
    "info": (GRID, 76),
    "about": (GRID, 232),
    "principles_building": (GRID, 244),
    "stack": (GRID, 422),
    "project": (GRID, 144),
    "certifications": (GRID, 248),
    "next": (GRID, 110),
    "analytics": (GRID, 224),
    "contrib": (GRID, 220),
    "closing": (GRID, 148),
}

# ----------------- Theme Tokens (Cozy Parchment & Crimson) -----------------
CANVAS_BG = "#FBF7F2"
CANVAS_BORDER = "#E4D9C8"
SUBCARD_BG = "#F3ECE2"
SUBCARD_BORDER = "#E2D5C5"
ESPRESSO = "#381E1F"
DARK_HILL = "#261718"
MID_HILL = "#5A1D1E"
CRIMSON = "#8C2D2D"
CALLOUT_BG = "#F6E6DC"
CALLOUT_BORDER = "#E8CFC0"
CALLOUT_ACCENT = "#C86428"
CALLOUT_HEAD = "#B85D2B"
TEXT_HEAD = "#231815"
TEXT_BODY = "#4A3B36"
TEXT_MUTED = "#7A6A63"
TEXT_EYEBROW = "#5C4B45"
PILL_BG = "#EAE0D3"
PILL_BORDER = "#D8CBB8"
PILL_TEXT = "#3A2A25"
NAV_BG = "#F2EAE0"
NAV_BORDER = "#DFD3C3"
ON_DARK = "#FAF5EF"
ON_DARK_SUB = "#E8D8D0"

LEVEL_COLORS = ["#EAE0D3", "#E8CFC0", "#D49B85", "#B35D4E", "#8C2D2D"]

# ----------------- Dark Theme Palette (Cozy Espresso & Crimson) -----------------
DARK_COLORS = {
    # Surfaces
    "#fbf7f2": "#181312",  # outer card canvas
    "#f3ece2": "#231B19",  # bento sub-card surface
    "#f2eae0": "#251C1A",  # nav inactive & portfolio bar
    "#f6e6dc": "#2B1B17",  # callout highlight box
    "#eae0d3": "#2E2320",  # tag pills, progress tracks, heatmap level 0
    # Borders & hairlines
    "#e4d9c8": "#3A2C28",  # outer card border & horizontal rules
    "#e2d5c5": "#3E2F2A",  # sub-card border
    "#dfd3c3": "#42322D",  # nav inactive border
    "#e8cfc0": "#523029",  # callout border & heatmap level 1
    "#d8cbb8": "#4A3934",  # pill border
    # Espresso & Crimson accents
    "#381e1f": "#8C2D2D",  # active nav pill, Email Me CTA, DONE/ACTIVE badges
    "#8c2d2d": "#C44B46",  # crimson badges, icons, bars, closing wave, heatmap level 4
    "#c86428": "#E6884A",  # lightning accent & underline secondary stroke
    "#b85d2b": "#F09C62",  # callout bold headline
    # Typography on card surfaces
    "#231815": "#FAF5EF",  # headings
    "#4a3b36": "#D8CBC2",  # body text
    "#3a2a25": "#EDE2D8",  # pill text & nav text
    "#5c4b45": "#C2B0A6",  # eyebrow text
    "#7a6a63": "#A6958C",  # muted labels & cat whiskers
    # Header crimson banner & illustrations
    "#943030": "#8C2D2D",
    "#822627": "#782223",
    "#5e1a1b": "#521617",
    "#5a1d1e": "#4C1819",
    "#261718": "#201314",
    "#1a1011": "#170E0F",
    "#a53f3a": "#993632",
    "#181010": "#140D0D",
    "#4a2525": "#4A2525",
    "#6e2223": "#9C3838",
    "#f0d5c6": "#F0D5C6",
    "#faf5ef": "#FAF5EF",
    "#e8d8d0": "#E8D8D0",
    "#ffffff": "#FFFFFF",
    # Heatmap mid-tones
    "#d49b85": "#7A3A35",
    "#b35d4e": "#A1433F",
}

HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b")
UNMAPPED_COLORS = set()


def to_dark(svg):
    """Map every non-data-URI hex colour in an SVG to its dark-mode counterpart."""
    parts = re.split(r'(data:image/[^"]+)', svg)
    out = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            out.append(part)
            continue

        def swap(match):
            light = match.group(0).lower()
            dark = DARK_COLORS.get(light)
            if dark is None:
                UNMAPPED_COLORS.add(light)
                return match.group(0)
            return dark

        out.append(HEX_COLOR.sub(swap, part))
    return "".join(out)


# ----------------- Camo-Safe Typography -----------------
FONT_SERIF = "'Playfair Display', Georgia, 'Times New Roman', serif"
FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'SFMono-Regular', Consolas, monospace"
FONT_CURSIVE = "'Caveat', 'Bradley Hand', 'Segoe Print', cursive"

GENERATED_CARDS = set()


def save_svg(filename, width, height, body, dark_body=None):
    """Write one standalone Camo-safe SVG card in both light and dark themes."""
    GENERATED_CARDS.add(filename)

    def wrap(inner):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'viewBox="0 0 %(w)d %(h)d" width="%(w)d" height="%(h)d">\n'
            "%(body)s\n"
            "</svg>\n"
        ) % {"w": width, "h": height, "body": inner}

    light_svg = wrap(body)
    dark_svg = to_dark(wrap(dark_body if dark_body is not None else body))
    with open(os.path.join(CARDS_DIR, filename), "w", encoding="utf-8") as sf:
        sf.write(light_svg)
    with open(os.path.join(DARK_DIR, filename), "w", encoding="utf-8") as sf:
        sf.write(dark_svg)
    print("Compiled: %s (%dx%d light + dark)" % (filename, width, height))


# ----------------- Text & Pill Layout Helpers -----------------
NARROW_CHARS = set("iltfjI1!.,:;'|()[]{}/ ")
WIDE_CHARS = set("mwMWGOQ@#%&")


def est_text_width(text, font_size, family="sans", bold=False):
    """Conservative pixel width estimator calibrated for Georgia / Sans / Mono."""
    if family == "mono":
        return len(text) * font_size * 0.61
    scale = 1.05 if bold else 1.0
    if family == "serif":
        scale *= 1.03
    total = 0.0
    for ch in text:
        if ch in NARROW_CHARS:
            total += 0.34
        elif ch in WIDE_CHARS or ("A" <= ch <= "Z"):
            total += 0.72
        else:
            total += 0.54
    return total * font_size * scale


def wrap_lines(text, max_width, font_size, family="sans", bold=False):
    """Word-wrap text into lines whose estimated width fits inside max_width."""
    words = text.split()
    if not words:
        return []
    lines = []
    cur = words[0]
    for word in words[1:]:
        candidate = cur + " " + word
        if est_text_width(candidate, font_size, family, bold) <= max_width:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def layout_pills(labels, x0, y0, max_width, pill_h=24, gap_x=7, gap_y=7, font_size=11, pad_x=18):
    """Pack pill tags cleanly into rows within max_width."""
    placed = []
    cx = x0
    cy = y0
    rows = 1
    for label in labels:
        pw = max(34, round(est_text_width(label, font_size, "sans", bold=False) + pad_x))
        if cx > x0 and (cx - x0 + pw) > max_width:
            cx = x0
            cy += pill_h + gap_y
            rows += 1
        placed.append((label, cx, cy, pw))
        cx += pw + gap_x
    total_h = rows * pill_h + (rows - 1) * gap_y
    return placed, total_h


def card_frame(w, h, fill=CANVAS_BG, stroke=CANVAS_BORDER, rx=16):
    """Outer rounded rectangle inset by 0.5px so 1px stroke is never clipped."""
    return (
        '<rect x="0.5" y="0.5" width="%(w)s" height="%(h)s" rx="%(rx)d" '
        'fill="%(fill)s" stroke="%(stroke)s" stroke-width="1"/>'
    ) % {"w": w - 1, "h": h - 1, "rx": rx, "fill": fill, "stroke": stroke}


def subcard_frame(x, y, w, h, fill=SUBCARD_BG, stroke=SUBCARD_BORDER, rx=12):
    return (
        '<rect x="%(x)d" y="%(y)d" width="%(w)d" height="%(h)d" rx="%(rx)d" '
        'fill="%(fill)s" stroke="%(stroke)s" stroke-width="1"/>'
    ) % {"x": x, "y": y, "w": w, "h": h, "rx": rx, "fill": fill, "stroke": stroke}


# ----------------- Crisp Vector Icons (16x16 viewBox) -----------------
VECTOR_PATHS = {
    "home": '<path d="M2 8.5L8 3l6 5.5V14a1 1 0 0 1-1 1H9.5v-4h-3v4H3a1 1 0 0 1-1-1V8.5z" fill="none" stroke="%(c)s" stroke-width="1.5" stroke-linejoin="round"/>',
    "code": '<path d="M5.5 4.5L2 8l3.5 3.5M10.5 4.5L14 8l-3.5 3.5M9 3.5L7 12.5" fill="none" stroke="%(c)s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
    "folder": '<path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h3l1.5 1.8h4.5A1.5 1.5 0 0 1 14 6.3v6.2A1.5 1.5 0 0 1 12.5 14h-9A1.5 1.5 0 0 1 2 12.5V4.5z" fill="none" stroke="%(c)s" stroke-width="1.5" stroke-linejoin="round"/>',
    "medal": '<circle cx="8" cy="6.5" r="4" fill="none" stroke="%(c)s" stroke-width="1.5"/><path d="M5.5 9.8L4.5 14.5 8 13l3.5 1.5-1-4.7" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/>',
    "chart": '<path d="M2.5 13.5V8.5M6.5 13.5V4.5M10.5 13.5V6.5M14 13.5V2.5" fill="none" stroke="%(c)s" stroke-width="1.8" stroke-linecap="round"/>',
    "star": '<path d="M8 1.6l1.9 4.1 4.5.6-3.3 3.1.8 4.5L8 11.7 4.1 13.9l.8-4.5-3.3-3.1 4.5-.6z" fill="%(c)s"/>',
    "bolt": '<path d="M9.2 1.5L3.5 9h4.2l-1 5.5L12.5 7H8.3l.9-5.5z" fill="%(c)s"/>',
    "target": '<circle cx="8" cy="8" r="6" fill="none" stroke="%(c)s" stroke-width="1.5"/><circle cx="8" cy="8" r="3" fill="none" stroke="%(c)s" stroke-width="1.4"/><circle cx="8" cy="8" r="1.2" fill="%(c)s"/>',
    "mail": '<rect x="1.8" y="3.2" width="12.4" height="9.6" rx="1.6" fill="none" stroke="%(c)s" stroke-width="1.5"/><path d="M2.2 4l5.8 4.4L13.8 4" fill="none" stroke="%(c)s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
    "compass": '<circle cx="8" cy="8" r="6.2" fill="none" stroke="%(c)s" stroke-width="1.5"/><polygon points="10.8,5.2 6.8,6.8 5.2,10.8 9.2,9.2" fill="%(c)s"/>',
    "grad_cap": '<path d="M1.5 6.5L8 3.2l6.5 3.3L8 9.8 1.5 6.5z" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/><path d="M4.2 8v3.6c0 1.1 1.7 2 3.8 2s3.8-.9 3.8-2V8M14 7v4.2" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linecap="round"/>',
    "pin": '<path d="M8 14.5s4.5-4.3 4.5-8A4.5 4.5 0 0 0 3.5 6.5c0 3.7 4.5 8 4.5 8z" fill="none" stroke="%(c)s" stroke-width="1.5"/><circle cx="8" cy="6.5" r="1.6" fill="%(c)s"/>',
    "briefcase": '<rect x="2" y="5" width="12" height="8.5" rx="1.6" fill="none" stroke="%(c)s" stroke-width="1.5"/><path d="M5.5 5V3.5A1.2 1.2 0 0 1 6.7 2.3h2.6a1.2 1.2 0 0 1 1.2 1.2V5M2 8.5h12" fill="none" stroke="%(c)s" stroke-width="1.4"/>',
    "handshake": '<path d="M1.5 7.5l3-3 3.5 2.5 3.5-2.5 3 3-4.5 4.5a2 2 0 0 1-2.8 0L1.5 7.5z" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/>',
    "layers": '<path d="M8 2L2 5.2 8 8.4l6-3.2L8 2zM2 8.2l6 3.2 6-3.2M2 11.2l6 3.2 6-3.2" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "database": '<ellipse cx="8" cy="4" rx="5" ry="2" fill="none" stroke="%(c)s" stroke-width="1.4"/><path d="M3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4M3 8c0 1.1 2.2 2 5 2s5-.9 5-2" fill="none" stroke="%(c)s" stroke-width="1.4"/>',
    "cloud": '<path d="M4.5 13h7.2a2.8 2.8 0 0 0 .4-5.6A4.2 4.2 0 0 0 4 6.2a3.2 3.2 0 0 0 .5 6.8z" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/>',
    "check": '<circle cx="8" cy="8" r="6" fill="none" stroke="%(c)s" stroke-width="1.4"/><path d="M5.2 8.2l1.9 1.9 3.7-3.8" fill="none" stroke="%(c)s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
    "activity": '<path d="M1.5 8.5h3l1.8-4.5 2.6 8 1.9-3.5h3.7" fill="none" stroke="%(c)s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
    "wrench": '<path d="M10.5 2.5a3.5 3.5 0 0 0-4.3 4.3L2.5 10.5l3 3 3.7-3.7a3.5 3.5 0 0 0 4.3-4.3l-2 2-1.8-.4-.4-1.8 2-2z" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/>',
    "server": '<rect x="2.2" y="2.5" width="11.6" height="4.5" rx="1" fill="none" stroke="%(c)s" stroke-width="1.4"/><rect x="2.2" y="9" width="11.6" height="4.5" rx="1" fill="none" stroke="%(c)s" stroke-width="1.4"/><circle cx="4.5" cy="4.7" r="0.7" fill="%(c)s"/><circle cx="4.5" cy="11.2" r="0.7" fill="%(c)s"/>',
    "book": '<path d="M2.5 3.5h4.2A1.8 1.8 0 0 1 8.5 5.3V13a1.5 1.5 0 0 0-1.5-1.2H2.5V3.5zM13.5 3.5H9.3a1.8 1.8 0 0 0-1.8 1.8V13a1.5 1.5 0 0 1 1.5-1.2h4.5V3.5z" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/>',
    "repo": '<path d="M3.5 2.5h9a1 1 0 0 1 1 1v9.5a1 1 0 0 1-1 1h-9a1.2 1.2 0 0 1-1.2-1.2V3.7A1.2 1.2 0 0 1 3.5 2.5zM2.3 11.2h11.2M5.2 2.5v8.7" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linejoin="round"/>',
    "users": '<circle cx="6.2" cy="5.5" r="2.2" fill="none" stroke="%(c)s" stroke-width="1.4"/><path d="M2.2 13a4 4 0 0 1 8 0M11 4.5a1.8 1.8 0 0 1 0 3.5M12 10.2a3.2 3.2 0 0 1 2.2 2.8" fill="none" stroke="%(c)s" stroke-width="1.4" stroke-linecap="round"/>',
}


def vec_icon(kind, x, y, color, size=14):
    scale = size / 16.0
    inner = VECTOR_PATHS[kind] % {"c": color}
    return '<g transform="translate(%.1f, %.1f) scale(%.4f)">%s</g>' % (x, y, scale, inner)


def sparkle_path(cx, cy, r, fill=CRIMSON, opacity=1.0):
    ir = r * 0.24
    d = (
        "M %(cx).1f %(top).1f Q %(cx).1f %(cy).1f %(right).1f %(cy).1f "
        "Q %(cx).1f %(cy).1f %(cx).1f %(bot).1f "
        "Q %(cx).1f %(cy).1f %(left).1f %(cy).1f "
        "Q %(cx).1f %(cy).1f %(cx).1f %(top).1f Z"
    ) % {
        "cx": cx,
        "cy": cy,
        "top": cy - r,
        "bot": cy + r,
        "left": cx - r,
        "right": cx + r,
    }
    _ = ir
    return '<path d="%s" fill="%s" fill-opacity="%.2f"/>' % (d, fill, opacity)


def find_icon(cat, key):
    src = icons.get(cat, {}).get(key)
    if src:
        return src
    for mapping in icons.values():
        if key in mapping:
            return mapping[key]
    return ""


TECH_LABELS = {
    "go": "Go",
    "java": "Java",
    "python": "Python",
    "typescript": "TypeScript",
    "c": "C",
    "bash": "Bash",
    "javascript": "JavaScript",
    "fastapi": "FastAPI",
    "nodejs": "Node.js",
    "react": "React",
    "tailwindcss": "Tailwind CSS",
    "apachespark": "Apache Spark",
    "apacheairflow": "Apache Airflow",
    "pytorch": "PyTorch",
    "duckdb": "DuckDB",
    "sqlite": "SQLite3",
    "grpc": "gRPC",
    "rabbitmq": "RabbitMQ",
    "redis": "Redis",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "amazonwebservices": "AWS",
    "docker": "Docker",
    "nginx": "NGINX",
    "githubactions": "GitHub Actions",
    "pytest": "Pytest",
    "vitest": "Vitest",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "git": "Git",
    "github": "GitHub",
    "linux": "Linux",
    "vscode": "VS Code",
    "postman": "Postman",
}


# =====================================================================
# 01 -- Header Banner (880x220)
# =====================================================================
header_body = """
<defs>
  <clipPath id="hdr-clip">
    <rect x="0" y="0" width="880" height="220" rx="16"/>
  </clipPath>
  <linearGradient id="hdr-grad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%%" stop-color="#943030"/>
    <stop offset="55%%" stop-color="#822627"/>
    <stop offset="100%%" stop-color="#5E1A1B"/>
  </linearGradient>
</defs>
<g clip-path="url(#hdr-clip)">
  <rect x="0" y="0" width="880" height="220" fill="url(#hdr-grad)"/>

  <!-- Layered rolling hills on the right -->
  <path d="M320 220 C410 155, 505 182, 600 138 C695 94, 785 112, 880 78 L880 220 Z" fill="%(mid_hill)s" fill-opacity="0.72"/>
  <path d="M410 220 C495 168, 575 188, 668 152 C748 120, 818 136, 880 112 L880 220 Z" fill="%(dark_hill)s"/>
  <path d="M565 220 C645 185, 725 198, 805 165 C840 150, 862 154, 880 148 L880 220 Z" fill="#1A1011" fill-opacity="0.88"/>

  <!-- Ringed planet doodle (top-center) -->
  <g transform="translate(432, 54)">
    <circle cx="0" cy="0" r="14" fill="#A53F3A" stroke="%(on_dark)s" stroke-width="1.6"/>
    <path d="M-8 -5 Q-2 -10 5 -6" fill="none" stroke="%(on_dark_sub)s" stroke-width="1" stroke-linecap="round"/>
    <ellipse cx="0" cy="1" rx="25" ry="6.5" transform="rotate(-18)" fill="none" stroke="%(on_dark)s" stroke-width="1.6"/>
    <circle cx="29" cy="-9" r="1.5" fill="%(on_dark)s"/>
  </g>

  <!-- 4-point sparkle stars -->
  %(s1)s
  %(s2)s
  %(s3)s
  %(s4)s
  %(s5)s
  <circle cx="355" cy="42" r="1.6" fill="%(on_dark_sub)s" fill-opacity="0.7"/>
  <circle cx="515" cy="88" r="1.4" fill="%(on_dark_sub)s" fill-opacity="0.6"/>
  <circle cx="605" cy="34" r="1.8" fill="%(on_dark)s" fill-opacity="0.85"/>

  <!-- Peeking black cat silhouette (bottom-left) -->
  <g transform="translate(38, 166)">
    <!-- Ears -->
    <polygon points="8,24 14,2 27,18" fill="#181010"/>
    <polygon points="41,18 54,2 60,24" fill="#181010"/>
    <polygon points="12,21 15,7 23,17" fill="#4A2525"/>
    <polygon points="45,17 53,7 56,21" fill="#4A2525"/>
    <!-- Head & shoulders -->
    <ellipse cx="34" cy="34" rx="26" ry="21" fill="#181010"/>
    <path d="M4 54 Q34 38 64 54 L68 58 L0 58 Z" fill="#181010"/>
    <!-- Eyes (O . O) -->
    <circle cx="23" cy="31" r="4.8" fill="%(on_dark)s"/>
    <circle cx="45" cy="31" r="4.8" fill="%(on_dark)s"/>
    <circle cx="23.8" cy="31" r="2.1" fill="#181010"/>
    <circle cx="45.8" cy="31" r="2.1" fill="#181010"/>
    <circle cx="24.6" cy="29.8" r="0.8" fill="#FFFFFF"/>
    <circle cx="46.6" cy="29.8" r="0.8" fill="#FFFFFF"/>
    <!-- Tiny nose dot -->
    <circle cx="34" cy="37" r="1.3" fill="#F0D5C6"/>
    <!-- Whiskers -->
    <path d="M12 36 L2 34 M12 39 L2 40 M56 36 L66 34 M56 39 L66 40" stroke="#7A6A63" stroke-width="1" stroke-linecap="round"/>
  </g>

  <!-- Title & subtitle (left) -->
  <text x="38" y="102" font-family="%(serif)s" font-size="44" font-weight="700" fill="%(on_dark)s">%(name)s</text>
  <text x="40" y="132" font-family="%(sans)s" font-size="14" font-weight="500" fill="%(on_dark_sub)s">%(role_short)s</text>

  <!-- Top-right tilted handwritten annotation with double curved underline -->
  <g transform="rotate(-8 730 56)">
    <text x="730" y="54" text-anchor="middle" font-family="%(cursive)s" font-size="22" font-weight="700" fill="%(on_dark)s">Dream Big. Code Better.</text>
    <path d="M635 63 Q728 57 826 62" fill="none" stroke="%(on_dark)s" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M648 69 Q730 64 815 68" fill="none" stroke="#F0D5C6" stroke-width="1.3" stroke-linecap="round"/>
  </g>
</g>
<rect x="0.5" y="0.5" width="879" height="219" rx="16" fill="none" stroke="#6E2223" stroke-width="1"/>
""" % {
    "mid_hill": MID_HILL,
    "dark_hill": DARK_HILL,
    "on_dark": ON_DARK,
    "on_dark_sub": ON_DARK_SUB,
    "serif": FONT_SERIF,
    "sans": FONT_SANS,
    "cursive": FONT_CURSIVE,
    "name": xml_esc(profile["name"]),
    "role_short": xml_esc(profile.get("role_short", "Backend platforms · distributed systems · data engineering")),
    "s1": sparkle_path(290, 48, 8, ON_DARK, 0.9),
    "s2": sparkle_path(548, 42, 10, ON_DARK, 0.95),
    "s3": sparkle_path(628, 72, 6, ON_DARK_SUB, 0.8),
    "s4": sparkle_path(384, 88, 5, ON_DARK_SUB, 0.7),
    "s5": sparkle_path(838, 92, 7, "#F0D5C6", 0.85),
}
save_svg("header.svg", *CARD_SIZES["header"], header_body)


# =====================================================================
# 02 -- Navigation Bar Pills (5 individual clickable SVGs)
# =====================================================================
HAS_ACHIEVEMENTS = bool(profile.get("achievements"))
HAS_UPCOMING = bool(profile.get("upcoming_projects"))

NAV_SPECS = [
    ("nav_about.svg", "About", "#about", "home", 114, True),
    ("nav_stack.svg", "Tech Stack", "#tech-stack", "code", 152, False),
    ("nav_projects.svg", "Featured Projects", "#featured-projects", "folder", 202, False),
    (
        "nav_certs.svg",
        "Achievements" if HAS_ACHIEVEMENTS else "Certifications",
        "#achievements" if HAS_ACHIEVEMENTS else "#certifications",
        "medal",
        168,
        False,
    ),
    ("nav_analytics.svg", "GitHub Analytics", "#github-analytics", "chart", 196, False),
]

for filename, label, _href, icon_key, width, active in NAV_SPECS:
    bg = ESPRESSO if active else NAV_BG
    border = ESPRESSO if active else NAV_BORDER
    fg = ON_DARK if active else PILL_TEXT
    ic = ON_DARK if active else CRIMSON
    tw = est_text_width(label, 13, "sans", bold=True)
    content_w = 18 + tw
    sx = (width - content_w) / 2.0
    nav_body = """
    %(frame)s
    %(icon)s
    <text x="%(tx).1f" y="24.5" font-family="%(sans)s" font-size="13" font-weight="600" fill="%(fg)s">%(label)s</text>
    """ % {
        "frame": card_frame(width, 40, fill=bg, stroke=border, rx=12),
        "icon": vec_icon(icon_key, sx, 13, ic, size=14),
        "tx": sx + 20,
        "sans": FONT_SANS,
        "fg": fg,
        "label": xml_esc(label),
    }
    save_svg(filename, width, 40, nav_body)


# =====================================================================
# 03 -- Hero / Split Bio + Focus Card (880x250)
# =====================================================================
bio_lines = wrap_lines(profile["role"], 505, 13.5, "sans", bold=False)[:2]
bio_svg = "".join(
    '<text x="28" y="%d" font-family="%s" font-size="13.5" fill="%s">%s</text>'
    % (106 + i * 20, FONT_SANS, TEXT_BODY, xml_esc(line))
    for i, line in enumerate(bio_lines)
)

quote_lines = [strip_tags(l) for l in profile["quote"]["lines"]]
quote_l1 = quote_lines[0] if len(quote_lines) > 0 else ""
quote_l2 = quote_lines[1] if len(quote_lines) > 1 else ""

focus_items = profile["focus"][:3]
focus_rows = []
for idx, item in enumerate(focus_items):
    ry = 98 + idx * 46
    sep = (
        '<line x1="590" y1="%d" x2="854" y2="%d" stroke="%s" stroke-width="1"/>'
        % (ry - 22, ry - 22, CANVAS_BORDER)
        if idx > 0
        else ""
    )
    focus_rows.append(
        """
        %(sep)s
        <circle cx="603" cy="%(cy)d" r="11" fill="%(crimson)s"/>
        <text x="603" y="%(num_y)d" text-anchor="middle" font-family="%(mono)s" font-size="10.5" font-weight="700" fill="%(on_dark)s">%(num)s</text>
        <text x="624" y="%(txt_y)d" font-family="%(sans)s" font-size="13" font-weight="600" fill="%(head)s">%(text)s</text>
        """
        % {
            "sep": sep,
            "cy": ry,
            "crimson": CRIMSON,
            "num_y": ry + 3.5,
            "mono": FONT_MONO,
            "on_dark": ON_DARK,
            "num": "%02d" % (idx + 1),
            "txt_y": ry + 4.5,
            "sans": FONT_SANS,
            "head": TEXT_HEAD,
            "text": xml_esc(item),
        }
    )

hero_body = """
%(frame)s
<line x1="565" y1="22" x2="565" y2="228" stroke="%(border)s" stroke-width="1"/>

<!-- Left Column -->
%(star)s
<text x="46" y="42" font-family="%(sans)s" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="%(eyebrow)s">%(kicker)s</text>
<text x="28" y="80" font-family="%(serif)s" font-size="38" font-weight="700" fill="%(head)s">%(name)s</text>
%(bio)s

<!-- Callout Highlight Box -->
<rect x="28" y="162" width="510" height="60" rx="10" fill="%(cbg)s" stroke="%(cborder)s" stroke-width="1"/>
%(bolt)s
<text x="72" y="187" font-family="%(sans)s" font-size="12.5" font-weight="700" fill="%(chead)s">%(q1)s</text>
<text x="72" y="207" font-family="%(sans)s" font-size="12.5" font-weight="500" fill="%(body)s">%(q2)s</text>

<!-- Right Column: Focus -->
%(target)s
<text x="615" y="47" font-family="%(serif)s" font-size="22" font-weight="700" fill="%(head)s">Focus</text>
%(sp1)s
%(sp2)s
%(focus_rows)s
""" % {
    "frame": card_frame(880, 250),
    "border": CANVAS_BORDER,
    "star": vec_icon("star", 28, 31, CRIMSON, size=12),
    "sans": FONT_SANS,
    "eyebrow": TEXT_EYEBROW,
    "kicker": xml_esc(profile["kicker"].upper()),
    "serif": FONT_SERIF,
    "head": TEXT_HEAD,
    "name": xml_esc(profile["name"]),
    "bio": bio_svg,
    "cbg": CALLOUT_BG,
    "cborder": CALLOUT_BORDER,
    "bolt": vec_icon("bolt", 44, 182, CALLOUT_ACCENT, size=18),
    "chead": CALLOUT_HEAD,
    "q1": xml_esc(quote_l1),
    "body": TEXT_BODY,
    "q2": xml_esc(quote_l2),
    "target": vec_icon("target", 590, 31, CRIMSON, size=18),
    "sp1": sparkle_path(842, 34, 7.5, CRIMSON, 0.9),
    "sp2": sparkle_path(826, 46, 4.5, CRIMSON, 0.75),
    "focus_rows": "".join(focus_rows),
}
save_svg("hero.svg", *CARD_SIZES["hero"], hero_body)


# =====================================================================
# 04 -- Calls to Action (880x48 each)
# =====================================================================
email_body = """
%(frame)s
%(icon)s
<text x="48" y="29" font-family="%(sans)s" font-size="14" font-weight="600" fill="%(fg)s">Email Me</text>
<text x="854" y="29" text-anchor="end" font-family="%(sans)s" font-size="16" font-weight="600" fill="%(fg)s">→</text>
""" % {
    "frame": card_frame(880, 48, fill=ESPRESSO, stroke=ESPRESSO, rx=12),
    "icon": vec_icon("mail", 22, 16.5, ON_DARK, size=15),
    "sans": FONT_SANS,
    "fg": ON_DARK,
}
save_svg("action_email.svg", *CARD_SIZES["action"], email_body)

portfolio_host = PORTFOLIO_URL.replace("https://", "").replace("http://", "").rstrip("/").upper()
portfolio_body = """
%(frame)s
%(icon)s
<text x="48" y="29" font-family="%(sans)s" font-size="14" font-weight="600" fill="%(head)s">View Portfolio</text>
<text x="854" y="28.5" text-anchor="end" font-family="%(sans)s" font-size="11.5" font-weight="700" letter-spacing="0.8" fill="%(body)s">%(host)s →</text>
""" % {
    "frame": card_frame(880, 48, fill=NAV_BG, stroke=SUBCARD_BORDER, rx=12),
    "icon": vec_icon("compass", 22, 16, CRIMSON, size=16),
    "sans": FONT_SANS,
    "head": TEXT_HEAD,
    "body": TEXT_BODY,
    "host": xml_esc(portfolio_host),
}
save_svg("action_portfolio.svg", *CARD_SIZES["action"], portfolio_body)


# =====================================================================
# 05 -- Profile Information Grid (880x76)
# =====================================================================
INFO = [(item["label"], item["main"], item["sub"]) for item in profile["info"]]
INFO_ICONS = ["grad_cap", "pin", "briefcase", "handshake"]

info_cols_svg = []
for idx, (label, main, _sub) in enumerate(INFO):
    cx = idx * 220
    div = (
        '<line x1="%d" y1="15" x2="%d" y2="61" stroke="%s" stroke-width="1"/>'
        % (cx, cx, CANVAS_BORDER)
        if idx > 0
        else ""
    )
    info_cols_svg.append(
        """
        %(div)s
        %(icon)s
        <text x="%(lx)d" y="30" font-family="%(sans)s" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="%(muted)s">%(label)s</text>
        <text x="%(vx)d" y="52" font-family="%(sans)s" font-size="13.5" font-weight="600" fill="%(head)s">%(main)s</text>
        """
        % {
            "div": div,
            "icon": vec_icon(INFO_ICONS[idx % len(INFO_ICONS)], cx + 22, 19.5, CRIMSON, size=13),
            "lx": cx + 40,
            "vx": cx + 22,
            "sans": FONT_SANS,
            "muted": TEXT_MUTED,
            "label": xml_esc(label.upper()),
            "head": TEXT_HEAD,
            "main": xml_esc(main),
        }
    )

info_body = card_frame(880, 76) + "".join(info_cols_svg)
save_svg("info.svg", *CARD_SIZES["info"], info_body)


# =====================================================================
# 06 -- About Card (880x232)
# =====================================================================
about_lines = wrap_lines(profile["about_me"]["text"], 480, 13.5, "sans", bold=False)
about_text_svg = "".join(
    '<text x="28" y="%d" font-family="%s" font-size="13.5" fill="%s">%s</text>'
    % (82 + i * 21, FONT_SANS, TEXT_BODY, xml_esc(line))
    for i, line in enumerate(about_lines)
)

exploring_lines = wrap_lines(profile["about_me"]["exploring"], 274, 12.5, "sans")
interests_lines = wrap_lines(profile["about_me"]["interests"], 274, 12.5, "sans")

exploring_svg = "".join(
    '<text x="564" y="%d" font-family="%s" font-size="12.5" fill="%s">%s</text>'
    % (106 + i * 17, FONT_SANS, TEXT_BODY, xml_esc(line))
    for i, line in enumerate(exploring_lines)
)
interests_svg = "".join(
    '<text x="564" y="%d" font-family="%s" font-size="12.5" fill="%s">%s</text>'
    % (176 + i * 17, FONT_SANS, TEXT_BODY, xml_esc(line))
    for i, line in enumerate(interests_lines)
)

about_body = """
%(frame)s
%(icon)s
<text x="52" y="42" font-family="%(serif)s" font-size="22" font-weight="700" fill="%(head)s">About</text>
<line x1="126" y1="35" x2="852" y2="35" stroke="%(border)s" stroke-width="1"/>

<!-- Left narrative + coffee quote -->
%(about_text)s
<rect x="28" y="168" width="484" height="40" rx="8" fill="%(cbg)s" stroke="%(cborder)s" stroke-width="1"/>
<rect x="28" y="168" width="4" height="40" rx="2" fill="%(crimson)s"/>
<text x="44" y="192.5" font-family="%(sans)s" font-size="12.5" font-style="italic" font-weight="500" fill="%(body)s">%(fun)s</text>

<!-- Right sub-card: Exploring & Interests -->
%(subcard)s
<text x="564" y="88" font-family="%(sans)s" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="%(muted)s">EXPLORING</text>
%(exploring)s
<line x1="564" y1="142" x2="834" y2="142" stroke="%(subborder)s" stroke-width="1"/>
<text x="564" y="159" font-family="%(sans)s" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="%(muted)s">INTERESTS</text>
%(interests)s
""" % {
    "frame": card_frame(880, CARD_SIZES["about"][1]),
    "icon": vec_icon("book", 28, 26, CRIMSON, size=17),
    "serif": FONT_SERIF,
    "sans": FONT_SANS,
    "head": TEXT_HEAD,
    "border": CANVAS_BORDER,
    "about_text": about_text_svg,
    "cbg": CALLOUT_BG,
    "cborder": CALLOUT_BORDER,
    "crimson": CRIMSON,
    "body": TEXT_BODY,
    "fun": xml_esc(profile["about_me"]["fun_fact"]),
    "subcard": subcard_frame(544, 62, 308, 146),
    "muted": TEXT_MUTED,
    "exploring": exploring_svg,
    "subborder": SUBCARD_BORDER,
    "interests": interests_svg,
}
save_svg("about.svg", *CARD_SIZES["about"], about_body)


# =====================================================================
# 07 -- Engineering Principles + Currently Building (880x244)
# =====================================================================
prin_rows = []
for idx, item in enumerate(profile["principles"][:5]):
    ry = 76 + idx * 33
    sep = (
        '<line x1="44" y1="%d" x2="412" y2="%d" stroke="%s" stroke-width="1"/>'
        % (ry - 18, ry - 18, SUBCARD_BORDER)
        if idx > 0
        else ""
    )
    prin_rows.append(
        """
        %(sep)s
        <circle cx="53" cy="%(cy)d" r="9" fill="%(crimson)s"/>
        <text x="53" y="%(ny).1f" text-anchor="middle" font-family="%(mono)s" font-size="9" font-weight="700" fill="%(on_dark)s">%(num)s</text>
        <text x="71" y="%(ty).1f" font-family="%(sans)s" font-size="12.5" font-weight="500" fill="%(head)s">%(text)s</text>
        """
        % {
            "sep": sep,
            "cy": ry,
            "crimson": CRIMSON,
            "ny": ry + 3.0,
            "mono": FONT_MONO,
            "on_dark": ON_DARK,
            "num": "%02d" % (idx + 1),
            "ty": ry + 4.0,
            "sans": FONT_SANS,
            "head": TEXT_HEAD,
            "text": xml_esc(item),
        }
    )

build_rows = []
for idx, item in enumerate(profile["currently_building"][:3]):
    by = 76 + idx * 72
    sep = (
        '<line x1="466" y1="%d" x2="836" y2="%d" stroke="%s" stroke-width="1"/>'
        % (by - 16, by - 16, SUBCARD_BORDER)
        if idx > 0
        else ""
    )
    desc_lines = wrap_lines(item.get("desc", ""), 360, 12, "sans")[:2]
    desc_svg = "".join(
        '<text x="466" y="%d" font-family="%s" font-size="12" fill="%s">%s</text>'
        % (by + 20 + li * 16, FONT_SANS, TEXT_BODY, xml_esc(line))
        for li, line in enumerate(desc_lines)
    )
    if "percentage" in item:
        pct = int(item["percentage"])
        badge = '<text x="836" y="%d" text-anchor="end" font-family="%s" font-size="11" font-weight="700" fill="%s">%d%%</text>' % (
            by, FONT_MONO, CRIMSON, pct
        )
        bar = (
            '<rect x="466" y="%d" width="370" height="6" rx="3" fill="%s"/>'
            '<rect x="466" y="%d" width="%d" height="6" rx="3" fill="%s"/>'
        ) % (by + 12, PILL_BG, by + 12, round(3.7 * pct), CRIMSON)
        extra = bar
    else:
        badge = (
            '<rect x="782" y="%d" width="54" height="19" rx="9.5" fill="%s"/>'
            '<text x="809" y="%d" text-anchor="middle" font-family="%s" font-size="9" font-weight="700" letter-spacing="0.8" fill="%s">ACTIVE</text>'
        ) % (by - 13, ESPRESSO, by, FONT_MONO, ON_DARK)
        extra = desc_svg

    build_rows.append(
        """
        %(sep)s
        <text x="466" y="%(y)d" font-family="%(sans)s" font-size="13.5" font-weight="700" fill="%(head)s">%(name)s</text>
        %(badge)s
        %(extra)s
        """
        % {
            "sep": sep,
            "y": by,
            "sans": FONT_SANS,
            "head": TEXT_HEAD,
            "name": xml_esc(item["name"]),
            "badge": badge,
            "extra": extra,
        }
    )

pb_body = """
%(frame)s
%(left_sub)s
<text x="44" y="46" font-family="%(serif)s" font-size="18" font-weight="700" fill="%(head)s">Engineering Principles</text>
<line x1="252" y1="40" x2="412" y2="40" stroke="%(subborder)s" stroke-width="1"/>
%(prin_rows)s

%(right_sub)s
<text x="466" y="46" font-family="%(serif)s" font-size="18" font-weight="700" fill="%(head)s">Currently Building</text>
<line x1="634" y1="40" x2="778" y2="40" stroke="%(subborder)s" stroke-width="1"/>
<text x="836" y="43" text-anchor="end" font-family="%(sans)s" font-size="10" font-weight="700" letter-spacing="1.2" fill="%(muted)s">%(build_note)s</text>
%(build_rows)s
""" % {
    "frame": card_frame(880, CARD_SIZES["principles_building"][1]),
    "left_sub": subcard_frame(24, 20, 408, 204),
    "right_sub": subcard_frame(446, 20, 410, 204),
    "serif": FONT_SERIF,
    "head": TEXT_HEAD,
    "subborder": SUBCARD_BORDER,
    "prin_rows": "".join(prin_rows),
    "sans": FONT_SANS,
    "muted": TEXT_MUTED,
    "build_note": "SELF-ASSESSED" if any("percentage" in i for i in profile["currently_building"]) else "ACTIVE",
    "build_rows": "".join(build_rows),
}
save_svg("principles_building.svg", *CARD_SIZES["principles_building"], pb_body)


# =====================================================================
# 07b -- Optional Next (Planned, Not Started) when upcoming_projects non-empty
# =====================================================================
if HAS_UPCOMING:
    next_cols = []
    n_items = profile["upcoming_projects"][:2]
    col_w = 398
    for idx, item in enumerate(n_items):
        nx = 28 + idx * 424
        next_cols.append(
            """
            %(sub)s
            <text x="%(tx)d" y="64" font-family="%(sans)s" font-size="13" font-weight="700" fill="%(head)s">%(name)s</text>
            <text x="%(tx)d" y="83" font-family="%(sans)s" font-size="12" fill="%(body)s">%(desc)s</text>
            """
            % {
                "sub": subcard_frame(nx, 42, col_w, 52, rx=10),
                "tx": nx + 14,
                "sans": FONT_SANS,
                "head": TEXT_HEAD,
                "name": xml_esc(item["name"]),
                "body": TEXT_BODY,
                "desc": xml_esc(item["desc"]),
            }
        )
    next_body = """
    %(frame)s
    <text x="28" y="30" font-family="%(serif)s" font-size="17" font-weight="700" fill="%(head)s">Next</text>
    <line x1="78" y1="24" x2="690" y2="24" stroke="%(border)s" stroke-width="1"/>
    <text x="852" y="28" text-anchor="end" font-family="%(sans)s" font-size="10" font-weight="700" letter-spacing="1.2" fill="%(muted)s">PLANNED, NOT STARTED</text>
    %(cols)s
    """ % {
        "frame": card_frame(880, CARD_SIZES["next"][1]),
        "serif": FONT_SERIF,
        "head": TEXT_HEAD,
        "border": CANVAS_BORDER,
        "sans": FONT_SANS,
        "muted": TEXT_MUTED,
        "cols": "".join(next_cols),
    }
    save_svg("next.svg", *CARD_SIZES["next"], next_body)


# =====================================================================
# 08 -- Tech Stack 4x2 Bento Grid + Primitives Card (880x422)
# =====================================================================
BENTO_CATS = [
    ("Languages", "languages", "code"),
    ("Backend & APIs", "backend_apis", "server"),
    ("Data & Lakehouse", "data_lakehouse", "layers"),
    ("Databases & Queues", "databases", "database"),
    ("Cloud & Infra", "cloud_infra", "cloud"),
    ("CI & Testing", "ci_testing", "check"),
    ("Observability", "observability", "activity"),
    ("Tools", "tools", "wrench"),
]

import base64 as _b64

DARK_ICON_SWAPS = {
    "github": ("#181616", "#FAF5EF"),
    "amazonwebservices": ("#252f3e", "#E8D8D0"),
    "grpc": ("#244C5A", "#7CC6D4"),
}


def find_icon_themed(cat, key, dark=False):
    src = find_icon(cat, key)
    if not src or not dark or key not in DARK_ICON_SWAPS:
        return src
    old_hex, new_hex = DARK_ICON_SWAPS[key]
    prefix, b64 = src.split(",", 1)
    raw = _b64.b64decode(b64).decode("utf-8", "replace").replace(old_hex, new_hex)
    return prefix + "," + _b64.b64encode(raw.encode("utf-8")).decode("ascii")


def build_stack_body(dark=False):
    bento_svg = []
    for idx, (label, cat_key, vec_key) in enumerate(BENTO_CATS):
        col = idx % 4
        row = idx // 4
        bx = 26 + col * 210
        by = 76 + row * 108
        tech_keys = profile["tech_stack"].get(cat_key, [])[:3]
        n_icons = len(tech_keys)
        icon_size = 30
        gap = 16
        total_iw = n_icons * icon_size + max(0, n_icons - 1) * gap
        ix0 = bx + (198 - total_iw) / 2.0
        imgs = []
        for i_idx, tkey in enumerate(tech_keys):
            src = find_icon_themed(cat_key, tkey, dark=dark)
            if not src:
                if not dark:
                    print("Warning: no icon for %s/%s" % (cat_key, tkey))
                continue
            ix = ix0 + i_idx * (icon_size + gap)
            iy = by + 46
            imgs.append(
                '<image href="%s" xlink:href="%s" x="%.1f" y="%d" width="%d" height="%d"/>'
                % (src, src, ix, iy, icon_size, icon_size)
            )
        bento_svg.append(
            """
            %(sub)s
            %(cicon)s
            <text x="%(lx)d" y="%(ly)d" font-family="%(sans)s" font-size="11.5" font-weight="700" fill="%(head)s">%(label)s</text>
            <line x1="%(x1)d" y1="%(line_y)d" x2="%(x2)d" y2="%(line_y)d" stroke="%(subborder)s" stroke-width="1"/>
            %(imgs)s
            """
            % {
                "sub": subcard_frame(bx, by, 198, 96),
                "cicon": vec_icon(vec_key, bx + 14, by + 13, CRIMSON, size=13),
                "lx": bx + 32,
                "ly": by + 23,
                "sans": FONT_SANS,
                "head": TEXT_HEAD,
                "label": xml_esc(label),
                "x1": bx + 14,
                "x2": bx + 184,
                "line_y": by + 35,
                "subborder": SUBCARD_BORDER,
                "imgs": "".join(imgs),
            }
        )

    return """
%(frame)s
<!-- Header row -->
<text x="26" y="48" font-family="%(mono)s" font-size="22" font-weight="700" fill="%(crimson)s">//</text>
<text x="58" y="48" font-family="%(serif)s" font-size="24" font-weight="700" fill="%(head)s">Tech Stack</text>
<line x1="194" y1="41" x2="610" y2="41" stroke="%(border)s" stroke-width="1"/>

<!-- Tilted handwritten annotation (top-right) -->
<g transform="rotate(-8 738 40)">
  <text x="738" y="38" text-anchor="middle" font-family="%(cursive)s" font-size="20" font-weight="700" fill="%(crimson)s">Build. Scale. Innovate.</text>
  <path d="M652 46 Q738 41 824 45" fill="none" stroke="%(crimson)s" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M664 51 Q738 47 812 50" fill="none" stroke="%(callout_acc)s" stroke-width="1.2" stroke-linecap="round"/>
</g>

<!-- 4x2 Bento Grid -->
%(bento)s

<!-- Full-width Primitives Sub-card -->
%(prim_sub)s
<text x="42" y="314" font-family="%(sans)s" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="%(muted)s">SYSTEMS, DATA &amp; STORAGE PRIMITIVES</text>
%(pills)s
""" % {
        "frame": card_frame(880, stack_total_h),
        "mono": FONT_MONO,
        "crimson": CRIMSON,
        "serif": FONT_SERIF,
        "head": TEXT_HEAD,
        "border": CANVAS_BORDER,
        "cursive": FONT_CURSIVE,
        "callout_acc": CALLOUT_ACCENT,
        "bento": "".join(bento_svg),
        "prim_sub": subcard_frame(26, 294, 828, primitives_sub_h),
        "sans": FONT_SANS,
        "muted": TEXT_MUTED,
        "pills": pill_svgs,
    }


core_skills = profile["tech_stack"].get("core_skills", [])
placed_pills, pills_h = layout_pills(
    core_skills, x0=42, y0=324, max_width=796, pill_h=23, gap_x=6, gap_y=6, font_size=10.5, pad_x=14
)
primitives_sub_h = 44 + pills_h + 14
stack_total_h = 294 + primitives_sub_h + 20
CARD_SIZES["stack"] = (GRID, stack_total_h)

pill_svgs = "".join(
    '<rect x="%d" y="%d" width="%d" height="23" rx="6" fill="%s" stroke="%s" stroke-width="1"/>'
    '<text x="%.1f" y="%d" text-anchor="middle" font-family="%s" font-size="10.5" font-weight="500" fill="%s">%s</text>'
    % (px, py, pw, PILL_BG, PILL_BORDER, px + pw / 2.0, py + 15.0, FONT_SANS, PILL_TEXT, xml_esc(lbl))
    for lbl, px, py, pw in placed_pills
)

save_svg("stack.svg", *CARD_SIZES["stack"], build_stack_body(dark=False), dark_body=build_stack_body(dark=True))


# =====================================================================
# 09 -- Featured Projects (880x144 each)
# =====================================================================
COMPLETE_STATUSES = {"production", "done", "complete", "completed", "shipped"}

for idx, project in enumerate(profile["featured_projects"]):
    done = project["status"].strip().lower() in COMPLETE_STATUSES
    status_txt = project["status"].strip().upper()
    pill_w = max(56, round(est_text_width(status_txt, 9.5, "mono", bold=True) + 22))
    pill_x = 852 - pill_w
    title_w = est_text_width(project["name"], 18, "serif", bold=True)
    rule_x1 = min(pill_x - 16, round(64 + title_w + 14))

    desc_lines = wrap_lines(project["desc"], 822, 13, "sans")[:2]
    desc_svg = "".join(
        '<text x="28" y="%d" font-family="%s" font-size="13" fill="%s">%s</text>'
        % (66 + li * 19, FONT_SANS, TEXT_BODY, xml_esc(line))
        for li, line in enumerate(desc_lines)
    )
    placed_tags, _ = layout_pills(
        project["tags"], x0=28, y0=102, max_width=824, pill_h=24, gap_x=7, gap_y=6, font_size=11, pad_x=18
    )
    tags_svg = "".join(
        '<rect x="%d" y="%d" width="%d" height="24" rx="6" fill="%s" stroke="%s" stroke-width="1"/>'
        '<text x="%.1f" y="%d" text-anchor="middle" font-family="%s" font-size="11" font-weight="500" fill="%s">%s</text>'
        % (px, py, pw, PILL_BG, PILL_BORDER, px + pw / 2.0, py + 15.5, FONT_SANS, PILL_TEXT, xml_esc(lbl))
        for lbl, px, py, pw in placed_tags
    )

    proj_body = """
    %(frame)s
    <circle cx="39" cy="34" r="11" fill="%(crimson)s"/>
    <text x="39" y="37.5" text-anchor="middle" font-family="%(mono)s" font-size="10.5" font-weight="700" fill="%(on_dark)s">%(num)s</text>
    <text x="60" y="39.5" font-family="%(serif)s" font-size="18" font-weight="700" fill="%(head)s">%(title)s</text>
    <line x1="%(rx1)d" y1="34" x2="%(rx2)d" y2="34" stroke="%(border)s" stroke-width="1"/>
    <rect x="%(px)d" y="23" width="%(pw)d" height="22" rx="11" fill="%(pbg)s" stroke="%(pbd)s" stroke-width="1"/>
    <text x="%(ptx).1f" y="37" text-anchor="middle" font-family="%(mono)s" font-size="9.5" font-weight="700" letter-spacing="0.8" fill="%(pfg)s">%(status)s</text>
    %(desc)s
    %(tags)s
    """ % {
        "frame": card_frame(880, CARD_SIZES["project"][1]),
        "crimson": CRIMSON,
        "mono": FONT_MONO,
        "on_dark": ON_DARK,
        "num": "%02d" % (idx + 1),
        "serif": FONT_SERIF,
        "head": TEXT_HEAD,
        "title": xml_esc(project["name"]),
        "rx1": rule_x1,
        "rx2": pill_x - 14,
        "border": CANVAS_BORDER,
        "px": pill_x,
        "pw": pill_w,
        "pbg": ESPRESSO if done else CALLOUT_BG,
        "pbd": ESPRESSO if done else CALLOUT_BORDER,
        "ptx": pill_x + pill_w / 2.0,
        "pfg": ON_DARK if done else CRIMSON,
        "status": xml_esc(status_txt),
        "desc": desc_svg,
        "tags": tags_svg,
    }
    save_svg("project_%d.svg" % idx, *CARD_SIZES["project"], proj_body)


# =====================================================================
# 09b -- Certifications / Achievements Card
# =====================================================================
if HAS_ACHIEVEMENTS:
    ach_rows = []
    for idx, item in enumerate(profile["achievements"][:3]):
        ay = 84 + idx * 62
        sep = (
            '<line x1="40" y1="%d" x2="424" y2="%d" stroke="%s" stroke-width="1"/>'
            % (ay - 16, ay - 16, SUBCARD_BORDER)
            if idx > 0
            else ""
        )
        dlines = wrap_lines(item["desc"], 356, 11.5, "sans")[:2]
        dsvg = "".join(
            '<text x="68" y="%d" font-family="%s" font-size="11.5" fill="%s">%s</text>'
            % (ay + 18 + li * 15, FONT_SANS, TEXT_BODY, xml_esc(line))
            for li, line in enumerate(dlines)
        )
        ach_rows.append(
            """
            %(sep)s
            <circle cx="50" cy="%(cy)d" r="9.5" fill="%(crimson)s"/>
            <text x="50" y="%(ny).1f" text-anchor="middle" font-family="%(mono)s" font-size="9" font-weight="700" fill="%(on_dark)s">%(num)s</text>
            <text x="68" y="%(ty)d" font-family="%(sans)s" font-size="12.5" font-weight="700" fill="%(head)s">%(title)s</text>
            <text x="424" y="%(ty)d" text-anchor="end" font-family="%(mono)s" font-size="10" fill="%(muted)s">%(period)s</text>
            %(dsvg)s
            """
            % {
                "sep": sep,
                "cy": ay - 3,
                "crimson": CRIMSON,
                "ny": ay,
                "mono": FONT_MONO,
                "on_dark": ON_DARK,
                "num": "%02d" % (idx + 1),
                "ty": ay,
                "sans": FONT_SANS,
                "head": TEXT_HEAD,
                "title": xml_esc(item["title"]),
                "muted": TEXT_MUTED,
                "period": xml_esc(item["period"]),
                "dsvg": dsvg,
            }
        )

    cert_rows = []
    for idx, cert in enumerate(profile.get("certifications", [])[:5]):
        cy = 84 + idx * 30
        sep = (
            '<line x1="476" y1="%d" x2="840" y2="%d" stroke="%s" stroke-width="1"/>'
            % (cy - 17, cy - 17, SUBCARD_BORDER)
            if idx > 0
            else ""
        )
        cert_rows.append(
            """
            %(sep)s
            <text x="476" y="%(y)d" font-family="%(sans)s" font-size="12" font-weight="500" fill="%(head)s">%(name)s</text>
            <text x="840" y="%(y)d" text-anchor="end" font-family="%(mono)s" font-size="10" fill="%(muted)s">%(issuer)s</text>
            """
            % {
                "sep": sep,
                "y": cy,
                "sans": FONT_SANS,
                "head": TEXT_HEAD,
                "name": xml_esc(cert["name"]),
                "mono": FONT_MONO,
                "muted": TEXT_MUTED,
                "issuer": xml_esc(cert["issuer"]),
            }
        )

    ach_body = """
    %(frame)s
    %(lsub)s
    <text x="40" y="46" font-family="%(serif)s" font-size="18" font-weight="700" fill="%(head)s">Leadership &amp; Hackathons</text>
    <line x1="274" y1="40" x2="424" y2="40" stroke="%(subborder)s" stroke-width="1"/>
    %(ach_rows)s

    %(rsub)s
    <text x="476" y="46" font-family="%(serif)s" font-size="18" font-weight="700" fill="%(head)s">Certifications</text>
    <line x1="604" y1="40" x2="840" y2="40" stroke="%(subborder)s" stroke-width="1"/>
    %(cert_rows)s
    """ % {
        "frame": card_frame(880, CARD_SIZES["achievements"][1]),
        "lsub": subcard_frame(24, 20, 416, 192),
        "rsub": subcard_frame(456, 20, 400, 192),
        "serif": FONT_SERIF,
        "head": TEXT_HEAD,
        "subborder": SUBCARD_BORDER,
        "ach_rows": "".join(ach_rows),
        "cert_rows": "".join(cert_rows),
    }
    save_svg("achievements.svg", *CARD_SIZES["achievements"], ach_body)
else:
    certs = profile.get("certifications", [])
    cert_h = 84 + max(1, len(certs)) * 34 + 18
    CARD_SIZES["certifications"] = (GRID, cert_h)
    sub_h = max(1, len(certs)) * 34 + 12
    cert_rows = []
    for idx, cert in enumerate(certs):
        ry = 86 + idx * 34
        sep = (
            '<line x1="42" y1="%d" x2="838" y2="%d" stroke="%s" stroke-width="1"/>'
            % (ry - 19, ry - 19, SUBCARD_BORDER)
            if idx > 0
            else ""
        )
        issuer = cert["issuer"]
        iw = max(72, round(est_text_width(issuer, 10.5, "mono", bold=True) + 20))
        ix = 838 - iw
        cert_rows.append(
            """
            %(sep)s
            <circle cx="53" cy="%(cy)d" r="9.5" fill="%(crimson)s"/>
            <text x="53" y="%(ny).1f" text-anchor="middle" font-family="%(mono)s" font-size="9.5" font-weight="700" fill="%(on_dark)s">%(num)s</text>
            <text x="74" y="%(ty)d" font-family="%(sans)s" font-size="13.5" font-weight="600" fill="%(head)s">%(name)s</text>
            <rect x="%(ix)d" y="%(iby)d" width="%(iw)d" height="22" rx="6" fill="%(pbg)s" stroke="%(pbd)s" stroke-width="1"/>
            <text x="%(itx).1f" y="%(ity)d" text-anchor="middle" font-family="%(mono)s" font-size="10.5" font-weight="600" fill="%(pfg)s">%(issuer)s</text>
            """
            % {
                "sep": sep,
                "cy": ry - 3,
                "crimson": CRIMSON,
                "ny": ry + 0.5,
                "mono": FONT_MONO,
                "on_dark": ON_DARK,
                "num": "%02d" % (idx + 1),
                "ty": ry + 1,
                "sans": FONT_SANS,
                "head": TEXT_HEAD,
                "name": xml_esc(cert["name"]),
                "ix": ix,
                "iby": ry - 14,
                "iw": iw,
                "pbg": PILL_BG,
                "pbd": PILL_BORDER,
                "itx": ix + iw / 2.0,
                "ity": ry + 0.5,
                "pfg": PILL_TEXT,
                "issuer": xml_esc(issuer),
            }
        )

    certs_body = """
    %(frame)s
    %(medal)s
    <text x="52" y="42" font-family="%(serif)s" font-size="22" font-weight="700" fill="%(head)s">Certifications</text>
    <line x1="196" y1="35" x2="854" y2="35" stroke="%(border)s" stroke-width="1"/>
    %(sub)s
    %(rows)s
    """ % {
        "frame": card_frame(880, cert_h),
        "medal": vec_icon("medal", 28, 25, CRIMSON, size=18),
        "serif": FONT_SERIF,
        "head": TEXT_HEAD,
        "border": CANVAS_BORDER,
        "sub": subcard_frame(26, 62, 828, sub_h),
        "rows": "".join(cert_rows),
    }
    save_svg("certifications.svg", *CARD_SIZES["certifications"], certs_body)


# =====================================================================
# 10 -- GitHub Analytics (fetched, cached, drawn locally)
# =====================================================================
DEFAULT_GITHUB_STATS = {
    "source": "default",
    "auth": "anonymous",
    "checked_at": "",
    "fetched_at": "",
    "public_repos": 16,
    "followers": 36,
    "stars": 75,
    "language_count": 6,
    "languages": [
        {"name": "Python", "repos": 8},
        {"name": "JavaScript", "repos": 2},
        {"name": "Jupyter Notebook", "repos": 2},
        {"name": "TypeScript", "repos": 1},
        {"name": "Go", "repos": 1},
    ],
}


def read_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (ValueError, OSError):
            return {}
    return {}


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def fetch_github_stats():
    cached = read_json(GITHUB_STATS_JSON)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "User-Agent": "ayushsingh08-ds-profile-generator",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = "Bearer " + token

    def api_get(url):
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    today = datetime.date.today().isoformat()
    auth = "token" if token else "anonymous"

    try:
        user = api_get("https://api.github.com/users/" + GITHUB_USER)
        repos = [
            repo
            for repo in api_get(
                "https://api.github.com/users/%s/repos?per_page=100&sort=pushed" % GITHUB_USER
            )
            if not repo["fork"]
        ]
        languages = collections.Counter(repo["language"] for repo in repos if repo["language"])
        stats = {
            "source": "api",
            "auth": auth,
            "fetched_at": today,
            "checked_at": today,
            "public_repos": user["public_repos"],
            "followers": user["followers"],
            "stars": sum(repo["stargazers_count"] for repo in repos),
            "language_count": len(languages),
            "languages": [
                {"name": name, "repos": count} for name, count in languages.most_common(5)
            ],
        }
        write_json(GITHUB_STATS_JSON, stats)
        print("GitHub stats refreshed from the API (%s, %s)" % (stats["fetched_at"], auth))
        return stats
    except Exception as exc:
        print("Warning: GitHub stats fetch failed (%s)" % exc)
        fallback = dict(cached) if cached else dict(DEFAULT_GITHUB_STATS)
        fallback["source"] = "cache" if cached else "default"
        fallback["auth"] = auth
        fallback["checked_at"] = today
        write_json(GITHUB_STATS_JSON, fallback)
        return fallback


def fetch_contributions():
    cached = read_json(CONTRIBUTIONS_JSON)
    today = datetime.date.today().isoformat()
    url = "https://github.com/users/%s/contributions" % GITHUB_USER
    request = urllib.request.Request(
        url, headers={"User-Agent": "ayushsingh08-ds-profile-generator", "Accept": "text/html"}
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", "replace")

        cells = {}
        for tag in re.findall(r"<td\b[^>]*>", html):
            if "ContributionCalendar-day" not in tag:
                continue
            date = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
            level = re.search(r'data-level="(\d)"', tag)
            cell_id = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
            if date and level and cell_id:
                cells[(int(cell_id.group(2)), int(cell_id.group(1)))] = {
                    "date": date.group(1),
                    "level": int(level.group(1)),
                    "count": 0,
                }

        for tooltip in re.finditer(
            r'<tool-tip[^>]*for="contribution-day-component-(\d+)-(\d+)"[^>]*>([^<]*)</tool-tip>',
            html,
        ):
            key = (int(tooltip.group(2)), int(tooltip.group(1)))
            if key not in cells:
                continue
            text = tooltip.group(3).strip()
            number = re.match(r"([\d,]+)", text)
            cells[key]["count"] = int(number.group(1).replace(",", "")) if number else 0

        if not cells:
            raise ValueError("no contribution cells found in the calendar page")

        weeks = max(week for week, _ in cells) + 1
        columns = [[cells.get((week, day)) for day in range(7)] for week in range(weeks)]
        payload = {
            "source": "github.com/users/%s/contributions" % GITHUB_USER,
            "fetched_at": today,
            "checked_at": today,
            "total": sum(cell["count"] for cell in cells.values()),
            "start": min(cell["date"] for cell in cells.values()),
            "end": max(cell["date"] for cell in cells.values()),
            "columns": columns,
        }
        write_json(CONTRIBUTIONS_JSON, payload)
        print("Contributions refreshed (%s, %d total)" % (payload["end"], payload["total"]))
        return payload
    except Exception as exc:
        print("Warning: contributions fetch failed (%s)" % exc)
        return cached


GITHUB_STATS = fetch_github_stats()
CONTRIBUTIONS = fetch_contributions()

# --- Analytics card (880x224) ---
langs_total = GITHUB_STATS.get("language_count") or len(GITHUB_STATS["languages"])
stat_items = [
    (GITHUB_STATS["public_repos"], "REPOSITORIES", "repo"),
    (GITHUB_STATS["stars"], "STARS", "star"),
    (GITHUB_STATS["followers"], "FOLLOWERS", "users"),
    (langs_total, "LANGUAGES", "code"),
]

tiles_svg = []
for idx, (val, lbl, ikey) in enumerate(stat_items):
    col = idx % 2
    row = idx // 2
    tx = 26 + col * 190
    ty = 64 + row * 68
    tiles_svg.append(
        """
        %(sub)s
        <text x="%(vx)d" y="%(vy)d" font-family="%(serif)s" font-size="24" font-weight="700" fill="%(head)s">%(val)s</text>
        %(icon)s
        <text x="%(lx)d" y="%(ly)d" font-family="%(sans)s" font-size="9.5" font-weight="700" letter-spacing="1.0" fill="%(muted)s">%(lbl)s</text>
        """
        % {
            "sub": subcard_frame(tx, ty, 178, 58, rx=10),
            "vx": tx + 14,
            "vy": ty + 28,
            "serif": FONT_SERIF,
            "head": TEXT_HEAD,
            "val": val,
            "icon": vec_icon(ikey, tx + 14, ty + 37, CRIMSON, size=11),
            "lx": tx + 29,
            "ly": ty + 46,
            "sans": FONT_SANS,
            "muted": TEXT_MUTED,
            "lbl": lbl,
        }
    )

stats_source = (
    "REST API · %s" % GITHUB_STATS["fetched_at"]
    if GITHUB_STATS.get("fetched_at")
    else "SNAPSHOT"
)

max_repos = max((l["repos"] for l in GITHUB_STATS["languages"]), default=1) or 1
lang_bars = []
for idx, lang in enumerate(GITHUB_STATS["languages"][:5]):
    ly = 74 + idx * 28
    bar_w = round(210 * lang["repos"] / max_repos)
    lang_bars.append(
        """
        <text x="444" y="%(y)d" font-family="%(sans)s" font-size="12" font-weight="500" fill="%(text)s">%(name)s</text>
        <rect x="598" y="%(by)d" width="210" height="8" rx="4" fill="%(track)s"/>
        <rect x="598" y="%(by)d" width="%(bw)d" height="8" rx="4" fill="%(fill)s"/>
        <text x="854" y="%(y)d" text-anchor="end" font-family="%(mono)s" font-size="11" font-weight="600" fill="%(muted)s">%(repos)d</text>
        """
        % {
            "y": ly,
            "sans": FONT_SANS,
            "text": PILL_TEXT,
            "name": xml_esc(lang["name"]),
            "by": ly - 7,
            "track": PILL_BG,
            "bw": max(6, bar_w),
            "fill": CRIMSON,
            "mono": FONT_MONO,
            "muted": TEXT_MUTED,
            "repos": lang["repos"],
        }
    )

analytics_body = """
%(frame)s
<line x1="418" y1="22" x2="418" y2="202" stroke="%(border)s" stroke-width="1"/>

<!-- Left: GitHub Stats -->
<text x="26" y="42" font-family="%(serif)s" font-size="19" font-weight="700" fill="%(head)s">GitHub Stats</text>
<line x1="152" y1="36" x2="274" y2="36" stroke="%(border)s" stroke-width="1"/>
<text x="394" y="40" text-anchor="end" font-family="%(mono)s" font-size="9.5" font-weight="600" fill="%(muted)s">%(source)s</text>
%(tiles)s

<!-- Right: Top Languages -->
<text x="444" y="42" font-family="%(serif)s" font-size="19" font-weight="700" fill="%(head)s">Top Languages</text>
<line x1="590" y1="36" x2="758" y2="36" stroke="%(border)s" stroke-width="1"/>
<text x="854" y="40" text-anchor="end" font-family="%(mono)s" font-size="9.5" font-weight="600" fill="%(muted)s">TOP %(nlangs)d OF %(total_langs)d</text>
%(bars)s
""" % {
    "frame": card_frame(880, CARD_SIZES["analytics"][1]),
    "border": CANVAS_BORDER,
    "serif": FONT_SERIF,
    "head": TEXT_HEAD,
    "mono": FONT_MONO,
    "muted": TEXT_MUTED,
    "source": xml_esc(stats_source.upper()),
    "tiles": "".join(tiles_svg),
    "nlangs": len(GITHUB_STATS["languages"][:5]),
    "total_langs": langs_total,
    "bars": "".join(lang_bars),
}
save_svg("analytics.svg", *CARD_SIZES["analytics"], analytics_body)

# --- Contributions heatmap (880x220) ---
columns = CONTRIBUTIONS.get("columns") or []
n_weeks = max(1, len(columns))
PITCH = 15.6
CELL = 12.2
gx0 = 26
gy0 = 76
month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
month_labels = []
cell_rects = []
last_m_x = -999

for week, days in enumerate(columns):
    first = next((day for day in days if day), None)
    wx = gx0 + week * PITCH
    if first:
        lbl = month_names[int(first["date"][5:7]) - 1]
        if (not month_labels or month_labels[-1][0] != lbl) and (wx - last_m_x >= 52) and wx < 832:
            month_labels.append((lbl, wx))
            last_m_x = wx
    for day_idx, day in enumerate(days):
        if not day:
            continue
        cy = gy0 + day_idx * PITCH
        color = LEVEL_COLORS[min(day["level"], 4)]
        cell_rects.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2.5" fill="%s"/>'
            % (wx, cy, CELL, CELL, color)
        )

months_svg = "".join(
    '<text x="%.1f" y="66" font-family="%s" font-size="10" font-weight="600" fill="%s">%s</text>'
    % (mx, FONT_MONO, TEXT_MUTED, lbl)
    for lbl, mx in month_labels
)

contrib_total = CONTRIBUTIONS.get("total")
contrib_note = (
    "%s IN THE LAST YEAR" % format(contrib_total, ",") if contrib_total is not None else ""
)
contrib_window = (
    "%s → %s" % (CONTRIBUTIONS["start"], CONTRIBUTIONS["end"])
    if CONTRIBUTIONS.get("start")
    else ""
)

legend_rects = "".join(
    '<rect x="%d" y="191" width="10" height="10" rx="2" fill="%s"/>' % (752 + i * 14, col)
    for i, col in enumerate(LEVEL_COLORS)
)

contrib_body = """
%(frame)s
<text x="26" y="42" font-family="%(serif)s" font-size="19" font-weight="700" fill="%(head)s">Contributions</text>
<line x1="158" y1="36" x2="690" y2="36" stroke="%(border)s" stroke-width="1"/>
<text x="854" y="40" text-anchor="end" font-family="%(mono)s" font-size="10" font-weight="600" fill="%(muted)s">%(note)s</text>
%(months)s
%(cells)s
<text x="26" y="200" font-family="%(mono)s" font-size="10" fill="%(muted)s">%(window)s</text>
<text x="744" y="200" text-anchor="end" font-family="%(mono)s" font-size="10" fill="%(muted)s">Less</text>
%(legend)s
<text x="826" y="200" font-family="%(mono)s" font-size="10" fill="%(muted)s">More</text>
""" % {
    "frame": card_frame(880, CARD_SIZES["contrib"][1]),
    "serif": FONT_SERIF,
    "head": TEXT_HEAD,
    "border": CANVAS_BORDER,
    "mono": FONT_MONO,
    "muted": TEXT_MUTED,
    "note": xml_esc(contrib_note),
    "months": months_svg,
    "cells": "".join(cell_rects),
    "window": xml_esc(contrib_window),
    "legend": legend_rects,
}
save_svg("contrib.svg", *CARD_SIZES["contrib"], contrib_body)


# =====================================================================
# 11 -- Closing Card with Crimson Wave Footer & Sleeping Cat (880x148)
# =====================================================================
closing_body = """
<defs>
  <clipPath id="cls-clip">
    <rect x="0" y="0" width="880" height="148" rx="16"/>
  </clipPath>
</defs>
<g clip-path="url(#cls-clip)">
  <rect x="0" y="0" width="880" height="148" fill="%(bg)s"/>

  <!-- Crimson & dark wave hills along bottom-right -->
  <path d="M0 148 L0 132 C160 120, 320 138, 480 122 C630 106, 760 88, 880 96 L880 148 Z" fill="%(crimson)s" fill-opacity="0.92"/>
  <path d="M360 148 C480 132, 620 118, 740 122 C800 124, 848 114, 880 108 L880 148 Z" fill="%(dark_hill)s"/>

  <!-- Sleeping black cat silhouette + z z z -->
  <g transform="translate(744, 72)">
    <!-- Curled tail -->
    <path d="M52 44 C70 46, 74 34, 64 29" fill="none" stroke="#181010" stroke-width="5.5" stroke-linecap="round"/>
    <!-- Curled body -->
    <ellipse cx="36" cy="39" rx="22" ry="13" fill="#181010"/>
    <!-- Head & ears -->
    <circle cx="19" cy="34" r="11" fill="#181010"/>
    <polygon points="10,27 12,15 19,24" fill="#181010"/>
    <polygon points="20,24 26,15 28,27" fill="#181010"/>
    <!-- Sleeping closed eyes -->
    <path d="M13 34 Q16 36.5 19 34" fill="none" stroke="%(on_dark_sub)s" stroke-width="1.2" stroke-linecap="round"/>
    <path d="M21 34 Q24 36.5 27 34" fill="none" stroke="%(on_dark_sub)s" stroke-width="1.2" stroke-linecap="round"/>
    <!-- Floating z z z -->
    <text x="34" y="18" font-family="%(cursive)s" font-size="13" font-weight="700" fill="%(crimson)s">z</text>
    <text x="44" y="10" font-family="%(cursive)s" font-size="16" font-weight="700" fill="%(crimson)s">z</text>
    <text x="56" y="2" font-family="%(cursive)s" font-size="19" font-weight="700" fill="%(crimson)s">z</text>
  </g>

  <!-- Closing copy -->
  <text x="34" y="58" font-family="%(serif)s" font-size="25" font-weight="700" fill="%(head)s">Let’s build something meaningful.</text>
  <text x="34" y="86" font-family="%(sans)s" font-size="13.5" fill="%(body)s">Always open to collaboration, new opportunities, and interesting technical conversations.</text>
</g>
<rect x="0.5" y="0.5" width="879" height="147" rx="16" fill="none" stroke="%(border)s" stroke-width="1"/>
""" % {
    "bg": CANVAS_BG,
    "crimson": CRIMSON,
    "dark_hill": DARK_HILL,
    "on_dark_sub": ON_DARK_SUB,
    "cursive": FONT_CURSIVE,
    "serif": FONT_SERIF,
    "head": TEXT_HEAD,
    "sans": FONT_SANS,
    "body": TEXT_BODY,
    "border": CANVAS_BORDER,
}
save_svg("closing.svg", *CARD_SIZES["closing"], closing_body)


# =====================================================================
# 12 -- Alt Text & README Assembly
# =====================================================================
def as_sentence(text):
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


tech_names = ", ".join(
    TECH_LABELS.get(key, key)
    for _lbl, category, _vk in BENTO_CATS
    for key in profile["tech_stack"].get(category, [])[:3]
)
core_skill_names = ", ".join(profile["tech_stack"].get("core_skills", []))

ALT_TEXT = {
    "header": "%s — %s" % (profile["name"], profile.get("role_short", profile["role"])),
    "hero": "%s: %s Focus: %s. %s"
    % (
        profile["name"],
        profile["role"],
        ", ".join(profile["focus"][:3]),
        " ".join(quote_lines),
    ),
    "action_email": "Email me at %s" % EMAIL,
    "action_portfolio": "Open my portfolio at %s" % PORTFOLIO_URL,
    "info": "Profile: " + "; ".join("%s: %s" % (label, main) for label, main, _sub in INFO),
    "about": "%s Exploring: %s. Interests: %s. %s"
    % (
        profile["about_me"]["text"],
        profile["about_me"]["exploring"],
        profile["about_me"]["interests"],
        profile["about_me"]["fun_fact"],
    ),
    "principles_building": "Engineering principles: "
    + " ".join(as_sentence(item) for item in profile["principles"])
    + " Currently building: "
    + "; ".join(
        ("%s — %s" % (item["name"], item.get("desc", "")))
        for item in profile["currently_building"]
    ),
    "stack": "Tech stack: %s. Systems, Data & Storage Primitives: %s"
    % (tech_names, core_skill_names),
    "next": "Planned, not started: "
    + "; ".join("%s %s" % (item["name"], item["desc"]) for item in profile["upcoming_projects"]),
    "achievements": "Leadership & Hackathons: "
    + "; ".join(
        "%s (%s) — %s" % (a["title"], a["period"], a["desc"])
        for a in profile.get("achievements", [])
    )
    + " Certifications: "
    + ", ".join("%s (%s)" % (c["name"], c["issuer"]) for c in profile.get("certifications", [])),
    "certifications": "Certifications: "
    + ", ".join("%s (%s)" % (c["name"], c["issuer"]) for c in profile.get("certifications", [])),
    "analytics": "GitHub stats for %s: %d public repositories, %d stars, %d followers and %d languages."
    % (
        GITHUB_USER,
        GITHUB_STATS["public_repos"],
        GITHUB_STATS["stars"],
        GITHUB_STATS["followers"],
        langs_total,
    ),
    "contrib": "Contribution calendar for %s: %s contributions between %s and %s"
    % (
        GITHUB_USER,
        format(contrib_total, ",") if contrib_total is not None else "unknown",
        CONTRIBUTIONS.get("start", "unknown"),
        CONTRIBUTIONS.get("end", "unknown"),
    ),
    "closing": "Let's build something meaningful — always open to collaboration, new opportunities and interesting technical conversations.",
}


def img_tag(filename, width, alt, href=None):
    markup = (
        '<picture><source media="(prefers-color-scheme: dark)" '
        'srcset="assets/cards/dark/%s"><img src="assets/cards/%s" width="%d" '
        'alt="%s"></picture>' % (filename, filename, width, html_attr(alt))
    )
    return '<a href="%s">%s</a>' % (html_attr(href), markup) if href else markup


def row(markup):
    return '<p align="center">%s</p>' % markup


nav_row = row(
    " ".join(
        img_tag(fname, width, "Jump to %s" % label, href=href)
        for fname, label, href, _ik, width, _act in NAV_SPECS
    )
)

PROJECT_ROWS = [
    row(
        img_tag(
            "project_%d.svg" % idx,
            GRID,
            "%s — %s Status: %s." % (project["name"], as_sentence(project["desc"]), project["status"]),
            href=project["url"],
        )
    )
    for idx, project in enumerate(profile["featured_projects"])
]

CONTACT_ITEMS = [
    ("GitHub", GITHUB_URL),
    ("Portfolio", PORTFOLIO_URL),
    ("LinkedIn", profile["about_me"]["linkedin_url"]),
    ("Email", "mailto:" + EMAIL),
    ("Resume", RESUME_URL),
]
contact_row = row(
    " · ".join('<a href="%s">%s</a>' % (html_attr(href), html_attr(lbl)) for lbl, href in CONTACT_ITEMS)
)

README_BLOCKS = [
    "<!-- Generated by generate.py from profile.json -- edit those, not this file. -->",
    row(img_tag("header.svg", GRID, ALT_TEXT["header"])),
    nav_row,
    row(img_tag("hero.svg", GRID, ALT_TEXT["hero"])),
    row(
        img_tag("action_email.svg", GRID, ALT_TEXT["action_email"], href="mailto:" + EMAIL)
        + "<br>\n"
        + img_tag("action_portfolio.svg", GRID, ALT_TEXT["action_portfolio"], href=PORTFOLIO_URL)
    ),
    row(img_tag("info.svg", GRID, ALT_TEXT["info"])),
    '<h2 align="center">About</h2>',
    row(img_tag("about.svg", GRID, ALT_TEXT["about"])),
    row(img_tag("principles_building.svg", GRID, ALT_TEXT["principles_building"])),
    *(
        [row(img_tag("next.svg", GRID, ALT_TEXT["next"]))]
        if HAS_UPCOMING
        else []
    ),
    '<h2 align="center">Tech Stack</h2>',
    row(img_tag("stack.svg", GRID, ALT_TEXT["stack"])),
    '<h2 align="center">Featured Projects</h2>',
    *PROJECT_ROWS,
    '<p align="center"><a href="%s?tab=repositories">View all repositories &rarr;</a></p>' % GITHUB_URL,
    *(
        [
            '<h2 align="center">Achievements</h2>',
            row(img_tag("achievements.svg", GRID, ALT_TEXT["achievements"])),
        ]
        if HAS_ACHIEVEMENTS
        else [
            '<h2 align="center">Certifications</h2>',
            row(img_tag("certifications.svg", GRID, ALT_TEXT["certifications"])),
        ]
    ),
    '<h2 align="center">GitHub Analytics</h2>',
    row(img_tag("analytics.svg", GRID, ALT_TEXT["analytics"])),
    row(img_tag("contrib.svg", GRID, ALT_TEXT["contrib"])),
    row(img_tag("closing.svg", GRID, ALT_TEXT["closing"])),
    contact_row,
]

readme = "\n\n".join(README_BLOCKS) + "\n"

# Remove stale SVGs no longer produced in either light or dark directory.
for directory in (CARDS_DIR, DARK_DIR):
    for existing_name in os.listdir(directory):
        if existing_name.endswith(".svg") and existing_name not in GENERATED_CARDS:
            os.remove(os.path.join(directory, existing_name))

# ----------------- XML & Dark Color Validation -----------------
INVALID_CARDS = []
for directory in (CARDS_DIR, DARK_DIR):
    for card_name in sorted(os.listdir(directory)):
        if not card_name.endswith(".svg"):
            continue
        path = os.path.join(directory, card_name)
        try:
            xml.etree.ElementTree.parse(path)
        except xml.etree.ElementTree.ParseError as exc:
            INVALID_CARDS.append("%s: %s" % (os.path.relpath(path, CARDS_DIR), exc))

if INVALID_CARDS:
    for problem in INVALID_CARDS:
        print("INVALID CARD: %s" % problem)
    raise SystemExit("Refusing to write README.md: %d card(s) are not valid XML" % len(INVALID_CARDS))
if UNMAPPED_COLORS:
    for colour in sorted(UNMAPPED_COLORS):
        print("UNMAPPED COLOUR: %s -- no dark counterpart" % colour)
    raise SystemExit("Refusing to write README.md: %d colour(s) missing from DARK_COLORS" % len(UNMAPPED_COLORS))

print("Validated: %d pure-SVG cards (light + dark) are well-formed XML and every colour has a dark counterpart" % (2 * len(GENERATED_CARDS)))

README_MD = os.path.join(WORKSPACE_DIR, "README.md")
with open(README_MD, "w", encoding="utf-8") as rf:
    rf.write(readme)

print("SUCCESS: cards written and README.md generated!")
