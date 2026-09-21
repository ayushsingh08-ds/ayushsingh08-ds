"""Compile every README card and README.md itself.

Two local sources of truth drive the whole page:

* ``profile.json`` -- the content (name, about, stack, projects, ...).
* ``CARD_SIZES``  -- the geometry. Every ``<img>`` width in the README template
  and every SVG ``viewBox`` is read from it, so a rendered card can never
  disagree with the file it points at.

Two live GitHub fetches feed the analytics cards, both cached next to the other
assets so a build without network access still produces a complete README and a
fallback is always visible in the committed files:

* ``assets/github_stats.json``  -- repository, follower, star and language counts
  (GitHub REST API).
* ``assets/contributions.json`` -- the public 12-month contribution calendar
  (read from github.com/users/<user>/contributions).

Layout model
------------
The page has exactly one content axis. ``GRID`` is the width of a full-width
block; every other width is derived from it and pairs/triples/quads sum to less
than ``GRID`` so a row never wraps on a normal desktop window. Cards are always
centred as a group (``<p align="center">``), never one-by-one, so section
headings and cards share the same axis.

GitHub rendering notes (all of them load-bearing):

* A line containing a single complete tag is a CommonMark HTML block (type 7) and
  is emitted WITHOUT a wrapping ``<p>``. Bare ``<img>`` lines therefore flow
  inline -- cards share a row and bottom-align. Every card image must stay inside
  its own ``<p align="center">``.
* Nothing but ``src``/``width``/``alt`` survives sanitising on ``<img>``: no
  inline styles, no ``height``. Only widths are pinned, so a card scales
  proportionally (GitHub's ``max-width: 100%``) instead of squashing.
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
GITHUB_STATS_JSON = os.path.join(WORKSPACE_DIR, "assets", "github_stats.json")
CONTRIBUTIONS_JSON = os.path.join(WORKSPACE_DIR, "assets", "contributions.json")

os.makedirs(CARDS_DIR, exist_ok=True)

# ----------------- Content -----------------
with open(PROFILE_JSON, "r", encoding="utf-8") as f:
    profile = json.load(f)

with open(BASE64_ICONS_JSON, "r", encoding="utf-8") as f:
    icons = json.load(f)


def escape_xml(text):
    """Escape bare ampersands so profile.json fragments stay valid XML."""
    if not isinstance(text, str):
        return text
    return re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+);)", "&amp;", text)


def escape_dict(d):
    if isinstance(d, dict):
        return {k: escape_dict(v) for k, v in d.items()}
    if isinstance(d, list):
        return [escape_dict(item) for item in d]
    if isinstance(d, str):
        return escape_xml(d)
    return d


profile = escape_dict(profile)

GITHUB_URL = profile["about_me"]["github_url"]
GITHUB_USER = GITHUB_URL.split("/")[-1]
EMAIL = profile["about_me"]["email"]
RESUME_URL = profile["about_me"]["resume_url"]

# ----------------- Layout grid -----------------
# Full-width block, then the widths of rows of 2 and 4 cards. The gaps between
# images in a row are real text nodes (&nbsp;), and each row is sized so that the
# row plus its gaps adds up to GRID -- the rows therefore share the same left and
# right edges as the full-width cards. On a narrower window a row wraps instead
# of shrinking (GitHub gives images max-width: 100%, so a wrapped card still
# fills the column), which is the intended small-screen behaviour.
GRID = 850
PAIR_W = 419  # 419 + 419 + 11px of gaps = 849
QUAD_W = 203  # 203 * 4 + 35px of gaps = 847
ROW_GAP = "&nbsp;&nbsp;&nbsp;"

CARD_SIZES = {
    "header": (GRID, 88),
    "nav": (QUAD_W, 38),
    "hero": (GRID, 240),
    "action": (PAIR_W, 56),
    "info": (GRID, 112),
    "about": (GRID, 196),
    "stack": (GRID, 146),
    "principles": (PAIR_W, 232),
    "building": (PAIR_W, 232),
    "project": (GRID, 128),
    "gh_stats": (PAIR_W, 196),
    "gh_langs": (PAIR_W, 196),
    "contrib": (GRID, 212),
    "next": (GRID, 96),
    "closing": (GRID, 106),
}

# ----------------- Design tokens -----------------
# Warm off-white surfaces, charcoal text, one terracotta accent. Kept in one
# place so the whole page reads as a single system.
SURFACE = "#fffdfa"
SURFACE_TINT = "#f7f1e8"
BORDER = "#e5dacf"
BORDER_SOFT = "#efe6da"
INK = "#2c1e1e"
INK_STRONG = "#241c17"
BODY = "#4a3f39"
MUTED = "#7a6a65"
FAINT = "#9c8b86"
ACCENT = "#b05a30"

# Contribution heatmap ramp: empty cell up to the accent itself.
LEVEL_COLORS = ["#f2ebe1", "#ecd6c1", "#dcae86", "#c47c4c", "#a8542c"]

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Courier+Prime:wght@400;700&amp;"
    "family=Inter:wght@400;500;600&amp;"
    "family=Outfit:wght@500;600&amp;display=swap');"
)

COMMON_CSS = (
    FONT_IMPORT
    + """
body { font-family: 'Inter', sans-serif; color: %(body)s; margin: 0; padding: 0;
       background-color: transparent; }
* { box-sizing: border-box; }
.card { width: 100%%; height: 100%%; background-color: %(surface)s;
        border: 1px solid %(border)s; border-radius: 10px; padding: 18px 20px; }
.label { font-family: 'Courier Prime', monospace; font-size: 10.5px;
         letter-spacing: 0.14em; text-transform: uppercase; color: %(faint)s; }
.mono { font-family: 'Courier Prime', monospace; }
.rule { flex: 1; height: 1px; background-color: %(border)s; }
.head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.name { font-family: 'Outfit', sans-serif; font-weight: 600; letter-spacing: -0.01em; }
.chip { font-family: 'Courier Prime', monospace; font-size: 10.5px;
        color: #6f6259; background-color: %(tint)s; border: 1px solid #eadfd2;
        border-radius: 4px; padding: 2px 6px; }
.highlight-text { color: %(accent)s; font-weight: 600; }
.pill { font-family: 'Courier Prime', monospace; font-size: 9.5px;
        letter-spacing: 0.1em; text-transform: uppercase; padding: 3px 8px;
        border-radius: 999px; border: 1px solid; white-space: nowrap; }
.pill-done { color: #5c6b46; background-color: #f1f3e8; border-color: #dde2cf; }
.pill-wip { color: #96602f; background-color: #faf0e4; border-color: #eeddc9; }
"""
    % {
        "body": BODY,
        "surface": SURFACE,
        "tint": SURFACE_TINT,
        "border": BORDER,
        "faint": FAINT,
        "accent": ACCENT,
    }
)


def save_svg(filename, width, height, content, extra_css=""):
    """Write one card. Every card is a fixed-size foreignObject document."""
    filepath = os.path.join(CARDS_DIR, filename)
    svg = """<svg fill="none" viewBox="0 0 %(w)d %(h)d" width="%(w)d" height="%(h)d" xmlns="http://www.w3.org/2000/svg">
  <foreignObject x="0" y="0" width="%(w)d" height="%(h)d">
    <div xmlns="http://www.w3.org/1999/xhtml" style="width: %(w)dpx; height: %(h)dpx; box-sizing: border-box;">
      <style>
        %(css)s
        %(extra)s
      </style>
      %(content)s
    </div>
  </foreignObject>
</svg>""" % {
        "w": width,
        "h": height,
        "css": COMMON_CSS,
        "extra": extra_css,
        "content": content,
    }
    with open(filepath, "w", encoding="utf-8") as sf:
        sf.write(svg)
    print("Compiled: %s" % filename)


def head(label, note=""):
    """Small uppercase section label followed by a hairline across the card."""
    note_html = '<span class="label">%s</span>' % note if note else ""
    return (
        '<div class="head"><span class="label">%s</span>'
        '<span class="rule"></span>%s</div>' % (label, note_html)
    )


# Spoken and written form of each icon key, for alt text.
TECH_LABELS = {
    "go": "Go",
    "java": "Java",
    "python": "Python",
    "cplusplus": "C++",
    "javascript": "JavaScript",
    "apachekafka": "Kafka",
    "grpc": "gRPC",
    "rabbitmq": "RabbitMQ",
    "redis": "Redis",
    "apachespark": "Spark",
    "apacheairflow": "Airflow",
    "googlecloud": "Google Cloud",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "amazonwebservices": "AWS",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "terraform": "Terraform",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "git": "Git",
    "github": "GitHub",
    "linux": "Linux",
    "vscode": "VS Code",
    "intellij": "IntelliJ",
}


def icon(cat, key, size=22):
    """One tech chip. Warns instead of silently dropping an unknown icon.

    Self-closed on purpose: a card is an XML document, so an unclosed <img>
    makes the browser discard the whole image.
    """
    src = icons.get(cat, {}).get(key)
    if not src:
        print("Warning: no icon for %s/%s -- skipped" % (cat, key))
        return ""
    return '<img src="%s" alt="%s" style="width:%dpx;height:%dpx;border-radius:4px;" />' % (
        src,
        TECH_LABELS.get(key, key),
        size,
        size,
    )


# =====================================================================
# 01 -- Header
# =====================================================================
header_content = """
<div class="card" style="display: flex; align-items: center; justify-content: space-between;">
  <div style="display: flex; align-items: center; gap: 16px;">
    <div style="width: 44px; height: 44px; border: 1px solid %(border)s; border-radius: 8px;
                background-color: #faf6f0; display: flex; align-items: center;
                justify-content: center; font-family: 'Courier Prime', monospace;
                font-size: 14px; letter-spacing: 0.04em; color: %(accent)s;">AS.</div>
    <div>
      <div class="name" style="font-size: 18px; color: %(ink)s;">%(name)s</div>
      <div style="font-size: 12px; color: %(muted)s; margin-top: 2px;">%(role_short)s</div>
    </div>
  </div>
  <div class="mono" style="text-align: right; font-size: 11px; color: %(faint)s;
              line-height: 1.6;">
    <div>github.com/%(user)s</div>
    <div>%(email)s</div>
  </div>
</div>
""" % {
    "border": BORDER,
    "accent": ACCENT,
    "ink": INK,
    "muted": MUTED,
    "faint": FAINT,
    "name": profile["name"],
    "role_short": "Distributed systems · backend platforms · data infrastructure",
    "user": GITHUB_USER,
    "email": EMAIL,
}
save_svg("header.svg", *CARD_SIZES["header"], header_content)


# =====================================================================
# 02 -- Navigation buttons (rendered once, reused by the contact strip)
# =====================================================================
def button_content(label):
    """A hairline button, used for both the section nav and the contact strip."""
    return (
        '<div style="width: 100%; height: 100%; background-color: {surface};'
        " border: 1px solid {border}; border-radius: 8px; display: flex;"
        " align-items: center; justify-content: center; font-family: 'Courier Prime',"
        ' monospace; font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase;'
        ' color: #6f6259;">{label}</div>'
    ).format(surface=SURFACE, border=BORDER, label=label)


NAV_ITEMS = [
    ("nav_about.svg", "About", "#about"),
    ("nav_stack.svg", "Tech stack", "#tech-stack"),
    ("nav_projects.svg", "Projects", "#featured-projects"),
    ("nav_analytics.svg", "Analytics", "#github-analytics"),
]

for filename, label, _href in NAV_ITEMS:
    save_svg(filename, *CARD_SIZES["nav"], button_content(label))

CONTACT_ITEMS = [
    ("contact_github.svg", "GitHub", GITHUB_URL),
    ("contact_linkedin.svg", "LinkedIn", profile["about_me"]["linkedin_url"]),
    ("contact_email.svg", "Email", "mailto:" + EMAIL),
    ("contact_resume.svg", "Resume", RESUME_URL),
]

for filename, label, _href in CONTACT_ITEMS:
    save_svg(filename, *CARD_SIZES["nav"], button_content(label))


# =====================================================================
# 03 -- Hero
# =====================================================================
FOCUS = [("%02d" % (index + 1), text) for index, text in enumerate(profile["focus"])]

focus_rows = "".join(
    """
    <div style="display: flex; gap: 10px; align-items: baseline; padding: 9px 0;
                border-top: 1px solid #f2ebe1;">
      <span class="mono" style="font-size: 9.5px; color: %(accent)s;">%(idx)s</span>
      <span style="font-size: 13px; color: #3c2f2f;">%(text)s</span>
    </div>
    """
    % {"accent": ACCENT, "idx": idx, "text": text}
    for idx, text in FOCUS
)

hero_content = """
<div class="card" style="display: flex; gap: 40px;">
  <div style="width: 468px; display: flex; flex-direction: column;">
    <div class="label" style="color: %(accent)s;">%(kicker)s</div>
    <div class="name" style="font-size: 44px; line-height: 1.25; color: %(ink_strong)s; margin: 10px 0 12px;">
      %(name)s
    </div>
    <div style="font-size: 16px; line-height: 1.5; color: #5a4a42;">
      %(role)s
    </div>
    <div style="margin-top: 16px; border-left: 2px solid %(accent)s; padding-left: 12px;
                font-size: 13.5px; line-height: 1.5; color: %(muted)s;">
      %(quote)s
    </div>
  </div>
  <div style="flex: 1; border-left: 1px solid %(border_soft)s; padding-left: 28px;">
    <div class="label">Focus</div>
    %(focus)s
  </div>
</div>
""" % {
    "accent": ACCENT,
    "ink_strong": INK_STRONG,
    "muted": MUTED,
    "border_soft": BORDER_SOFT,
    "kicker": profile["kicker"],
    "name": profile["name"],
    "role": profile["role"],
    "quote": "".join("<div>%s</div>" % line for line in profile["quote"]["lines"]),
    "focus": focus_rows,
}
save_svg("hero.svg", *CARD_SIZES["hero"], hero_content)


# =====================================================================
# 04 -- Calls to action
# =====================================================================
def action_content(label, trailing, primary):
    if primary:
        style = (
            "background-color: %s; border: 1px solid %s; color: #f7f1e8;" % (INK, INK)
        )
        trailing_color = "#c9b8a8"
    else:
        style = "background-color: %s; border: 1px solid #ded3c6; color: %s;" % (
            SURFACE,
            INK,
        )
        trailing_color = FAINT
    return (
        '<div style="width: 100%%; height: 100%%; border-radius: 8px; display: flex;'
        " align-items: center; justify-content: space-between; padding: 0 20px;"
        ' %(style)s font-family: \'Courier Prime\', monospace; font-size: 11px;'
        ' letter-spacing: 0.14em; text-transform: uppercase;">'
        "<span>%(label)s</span>"
        '<span style="color: %(trailing_color)s;">%(trailing)s</span></div>'
    ) % {
        "style": style,
        "label": label,
        "trailing": trailing,
        "trailing_color": trailing_color,
    }


save_svg("action_email.svg", *CARD_SIZES["action"], action_content("Email me", "→", True))
save_svg("action_resume.svg", *CARD_SIZES["action"], action_content("View resume", "PDF →", False))


# =====================================================================
# 05 -- Profile information grid (four balanced columns, one card)
# =====================================================================
INFO = [
    ("Education", "B.Tech CSE (Data Science)", "Dayananda Sagar University"),
    ("Location", "Bengaluru, India", "IST (UTC+5:30) · remote-friendly"),
    ("Open to", "SDE · Data Engineering", "Backend · Infrastructure"),
    ("Connection", "Open to collaboration", "Reach me by email"),
]

info_cols = "".join(
    """
    <div style="flex: 1 1 0; min-width: 0; padding: 0 16px; border-left: 1px solid %(border_soft)s;
                %(edge)s">
      <div class="label">%(label)s</div>
      <div style="font-size: 13px; font-weight: 600; color: %(ink)s; margin-top: 7px;">%(main)s</div>
      <div style="font-size: 11.5px; color: %(muted)s; margin-top: 3px;">%(sub)s</div>
    </div>
    """
    % {
        "border_soft": BORDER_SOFT,
        "ink": INK,
        "muted": MUTED,
        "label": label,
        "main": main,
        "sub": sub,
        # The outer edges drop their padding so the four columns align with the
        # card padding of every other block.
        "edge": "padding-left: 0; border-left: none;"
        if index == 0
        else ("padding-right: 0;" if index == len(INFO) - 1 else ""),
    }
    for index, (label, main, sub) in enumerate(INFO)
)

info_content = '<div class="card" style="display: flex;">%s</div>' % info_cols
save_svg("info.svg", *CARD_SIZES["info"], info_content)


# =====================================================================
# 06 -- About
# =====================================================================
about_facts = [
    ("Exploring", profile["about_me"]["exploring"]),
    ("Interests", profile["about_me"]["interests"]),
]

about_fact_rows = "".join(
    """
    <div style="padding: 12px 0; %(border)s">
      <div class="label">%(label)s</div>
      <div style="font-size: 12.5px; line-height: 1.5; color: #4a3f39; margin-top: 5px;">%(value)s</div>
    </div>
    """
    % {
        "border": "border-top: 1px solid #f2ebe1;" if index else "",
        "label": label,
        "value": value,
    }
    for index, (label, value) in enumerate(about_facts)
)

about_content = """
<div class="card" style="display: flex; gap: 40px;">
  <div style="width: 468px;">
    <div style="font-size: 15px; line-height: 1.6; color: %(body)s;">%(text)s</div>
    <div style="margin-top: 16px; border-left: 2px solid %(border)s; padding-left: 12px;
                font-size: 13px; color: %(muted)s;">%(fun)s</div>
  </div>
  <div style="flex: 1; border-left: 1px solid %(border_soft)s; padding-left: 28px;">
    %(facts)s
  </div>
</div>
""" % {
    "body": BODY,
    "border": BORDER,
    "border_soft": BORDER_SOFT,
    "muted": MUTED,
    "text": profile["about_me"]["text"],
    "fun": profile["about_me"]["fun_fact"],
    "facts": about_fact_rows,
}
save_svg("about.svg", *CARD_SIZES["about"], about_content)


# =====================================================================
# 07 -- Tech stack
# =====================================================================
# Labels and column order are curated here; the technologies themselves come
# from profile.json in the order listed there, and each one appears in exactly
# one category (no icon is repeated across the grid).
TECH_CATEGORIES = [
    ("Languages", "languages"),
    ("Distributed systems", "distributed"),
    ("Data &amp; streaming", "data_streaming"),
    ("Databases", "databases"),
    ("Cloud &amp; DevOps", "cloud_devops"),
    ("Observability", "observability"),
    ("Tools", "tools"),
]

tech_cells = "".join(
    """
    <div>
      <div class="label" style="font-size: 10px; margin-bottom: 8px;">%(label)s</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">%(icons)s</div>
    </div>
    """
    % {
        "label": label,
        "icons": "".join(icon(category, name) for name in profile["tech_stack"].get(category, [])),
    }
    for label, category in TECH_CATEGORIES
)

stack_content = """
<div class="card">
  <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 22px 18px;">
    %(cells)s
  </div>
</div>
""" % {"cells": tech_cells}
save_svg("stack.svg", *CARD_SIZES["stack"], stack_content)


# =====================================================================
# 08 -- Engineering principles + currently building
# =====================================================================
principle_rows = "".join(
    """
    <div style="display: flex; gap: 12px; align-items: baseline; padding: 7px 0;
                %(border)s">
      <span class="mono" style="font-size: 10px; color: %(accent)s;">%(idx)s</span>
      <span style="font-size: 13.5px; line-height: 1.4; color: #3c2f2f;">%(text)s</span>
    </div>
    """
    % {
        "border": "border-top: 1px solid #f2ebe1;" if index else "",
        "accent": ACCENT,
        "idx": "%02d" % (index + 1),
        "text": item,
    }
    for index, item in enumerate(profile["principles"])
)

principles_content = """
<div class="card">
  %(head)s
  %(rows)s
</div>
""" % {"head": head("Engineering principles"), "rows": principle_rows}
save_svg("principles.svg", *CARD_SIZES["principles"], principles_content)

# The bars are the owner's own estimates from profile.json, not something this
# build can verify against the repositories, so the card says so. Anything the
# build cannot check is labelled rather than stated as fact.
building_items = "".join(
    """
    <div style="margin-bottom: 30px;">
      <div style="display: flex; justify-content: space-between; align-items: baseline;">
        <span style="font-size: 13px; font-weight: 500; color: #3c2f2f;">%(name)s</span>
        <span class="mono" style="font-size: 10.5px; color: %(faint)s;">%(percentage)d%%</span>
      </div>
      <div style="height: 6px; background-color: #f0e7db; border-radius: 3px; margin-top: 8px;
                  overflow: hidden;">
        <div style="height: 100%%; width: %(percentage)d%%; background-color: %(accent)s;
                    border-radius: 3px;"></div>
      </div>
    </div>
    """
    % {
        "name": item["name"],
        "percentage": item["percentage"],
        "faint": FAINT,
        "accent": ACCENT,
    }
    for item in profile["currently_building"]
)

building_content = """
<div class="card">
  %(head)s
  %(items)s
</div>
""" % {"head": head("Currently building", "self-assessed"), "items": building_items}
save_svg("building.svg", *CARD_SIZES["building"], building_content)

# Planned work, labelled as planned: the brief for this page (and honesty) is
# that nothing here is presented as finished.
next_items = "".join(
    """
    <div style="flex: 1;">
      <div style="font-size: 12.5px; font-weight: 500; color: #3c2f2f;">%(name)s</div>
      <div style="font-size: 11.5px; color: %(muted)s; margin-top: 3px;">%(desc)s</div>
    </div>
    """
    % {"name": item["name"], "desc": item["desc"], "muted": MUTED}
    for item in profile["upcoming_projects"]
)

next_content = """
<div class="card">
  %(head)s
  <div style="display: flex; gap: 28px;">%(items)s</div>
</div>
""" % {"head": head("Next", "planned, not started"), "items": next_items}
save_svg("next.svg", *CARD_SIZES["next"], next_content)


# =====================================================================
# 09 -- Featured projects
# =====================================================================
COMPLETE_STATUSES = {"production", "done", "complete", "completed", "shipped"}

for idx, project in enumerate(profile["featured_projects"]):
    done = project["status"].strip().lower() in COMPLETE_STATUSES
    tags = "".join('<span class="chip">%s</span>' % tag for tag in project["tags"])
    project_content = """
    <div class="card">
      <div style="display: flex; align-items: center; gap: 14px;">
        <span class="mono" style="font-size: 10.5px; color: %(accent)s;">%(idx)s</span>
        <span class="name" style="font-size: 15.5px; color: %(ink)s;">%(name)s</span>
        <span class="rule"></span>
        <span class="pill %(pill_cls)s">%(status)s</span>
      </div>
      <div style="font-size: 12.5px; line-height: 1.45; color: #5a4a42; margin: 9px 0 10px;">
        %(desc)s
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">%(tags)s</div>
    </div>
    """ % {
        "accent": ACCENT,
        "ink": INK,
        "idx": "%02d" % (idx + 1),
        "name": project["name"],
        "pill_cls": "pill-done" if done else "pill-wip",
        "status": project["status"],
        "desc": project["desc"],
        "tags": tags,
    }
    save_svg("project_%d.svg" % idx, *CARD_SIZES["project"], project_content)


# =====================================================================
# 10 -- GitHub analytics (fetched, cached, drawn locally)
# =====================================================================
# These numbers used to be images served by github-readme-stats.vercel.app and
# streak-stats.demolab.com. Both are third-party deployments with no uptime
# guarantee, and when the first was paused the whole section rendered as broken
# images. Everything here is fetched at build time, cached beside the other
# assets, and drawn in the same theme as the rest of the page, so the published
# README depends on no external image host at all.
DEFAULT_GITHUB_STATS = {
    "source": "default",
    "auth": "anonymous",
    "checked_at": "",
    "fetched_at": "",
    "public_repos": 23,
    "followers": 38,
    "stars": 105,
    "language_count": 8,
    "languages": [
        {"name": "Python", "repos": 8},
        {"name": "JavaScript", "repos": 3},
        {"name": "HTML", "repos": 3},
        {"name": "TypeScript", "repos": 2},
        {"name": "Jupyter Notebook", "repos": 2},
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
    """Refresh repository stats from the GitHub REST API, falling back to cache.

    The result records where the numbers came from -- "api", "cache" or
    "default" -- and how the attempt was authenticated, and it is written to disk
    on every run, so a build that reused stale numbers shows up in the committed
    file instead of passing unnoticed.
    """
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
            # Distinct languages across all repositories, counted separately from
            # the five the card has room for -- reporting the card's own list
            # length said "5 languages used", which was simply wrong.
            "language_count": len(languages),
            "languages": [
                {"name": name, "repos": count} for name, count in languages.most_common(5)
            ],
        }
        write_json(GITHUB_STATS_JSON, stats)
        print(
            "GitHub stats refreshed from the API (%s, %s)"
            % (stats["fetched_at"], "with token" if token else "unauthenticated")
        )
        return stats
    except Exception as exc:
        print("Warning: GitHub stats fetch failed (%s)" % exc)
        fallback = dict(cached) if cached else dict(DEFAULT_GITHUB_STATS)
        fallback["source"] = "cache" if cached else "default"
        fallback["auth"] = auth
        fallback["checked_at"] = today
        write_json(GITHUB_STATS_JSON, fallback)
        print(
            "Using %s stats (data fetched %s) -- recorded in %s"
            % (fallback["source"], fallback.get("fetched_at") or "never", GITHUB_STATS_JSON)
        )
        return fallback


def fetch_contributions():
    """Read the public 12-month contribution calendar for the account.

    GitHub has no token-free JSON endpoint for contributions, so the public
    calendar page is parsed instead: each day is a ``<td>`` carrying ``data-date``
    and ``data-level``, and the exact count sits in the ``<tool-tip>`` bound to
    that cell's id. The parsed grid is cached in ``assets/contributions.json``
    and reused whenever the fetch fails, so a network-less build still renders
    the last real calendar rather than an empty card.
    """
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
        columns = [
            [cells.get((week, day)) for day in range(7)] for week in range(weeks)
        ]
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
        if not cached:
            print("No cached calendar -- the contributions card will render empty")
        return cached


GITHUB_STATS = fetch_github_stats()
CONTRIBUTIONS = fetch_contributions()

# --- Stats card -----------------------------------------------------
stat_tiles = "".join(
    """
    <div style="background-color: %(tint)s; border: 1px solid #eadfd2; border-radius: 8px;
                padding: 10px 12px;">
      <div class="name" style="font-size: 20px; color: %(ink_strong)s;">%(value)s</div>
      <div class="label" style="font-size: 9.5px; margin-top: 4px;">%(label)s</div>
    </div>
    """
    % {"tint": SURFACE_TINT, "ink_strong": INK_STRONG, "value": value, "label": label}
    for value, label in [
        (GITHUB_STATS["public_repos"], "Repositories"),
        (GITHUB_STATS["stars"], "Stars"),
        (GITHUB_STATS["followers"], "Followers"),
        (GITHUB_STATS.get("language_count") or len(GITHUB_STATS["languages"]), "Languages"),
    ]
)

# The card states where its numbers come from, so a cached fallback is visible
# to whoever reads the profile and not just to whoever reads the build log.
stats_source = (
    "REST API · %s" % GITHUB_STATS["fetched_at"]
    if GITHUB_STATS.get("fetched_at")
    else "snapshot"
)

gh_stats_content = """
<div class="card">
  %(head)s
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">%(tiles)s</div>
</div>
""" % {
    "head": head("GitHub stats", stats_source),
    "tiles": stat_tiles,
}
save_svg("gh_stats.svg", *CARD_SIZES["gh_stats"], gh_stats_content)

# --- Languages card -------------------------------------------------
max_repos = max(language["repos"] for language in GITHUB_STATS["languages"]) or 1
lang_rows = "".join(
    """
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px;">
      <span style="width: 110px; font-size: 11px; color: #3c2f2f; white-space: nowrap;
                   overflow: hidden;">%(name)s</span>
      <span style="flex: 1; height: 6px; background-color: #f0e7db; border-radius: 3px;
                   overflow: hidden;">
        <span style="display: block; height: 100%%; width: %(width)d%%;
                     background-color: %(accent)s; border-radius: 3px;"></span>
      </span>
      <span class="mono" style="width: 22px; text-align: right; font-size: 10.5px;
                   color: %(muted)s;">%(repos)d</span>
    </div>
    """
    % {
        "name": language["name"],
        "width": round(100 * language["repos"] / max_repos),
        "repos": language["repos"],
        "accent": ACCENT,
        "muted": MUTED,
    }
    for language in GITHUB_STATS["languages"]
)

langs_total = GITHUB_STATS.get("language_count") or len(GITHUB_STATS["languages"])
gh_langs_content = """
<div class="card">
  %(head)s
  <div>%(rows)s</div>
</div>
""" % {
    "head": head("Top languages", "top %d of %d" % (len(GITHUB_STATS["languages"]), langs_total)),
    "rows": lang_rows,
}
save_svg("gh_langs.svg", *CARD_SIZES["gh_langs"], gh_langs_content)


# --- Contribution calendar ------------------------------------------
CONTRIB_CELL = 12
CONTRIB_GAP = 3
CONTRIB_PITCH = CONTRIB_CELL + CONTRIB_GAP


def contribution_heatmap(columns):
    """Draw the cached calendar as a warm-toned 7 x N grid plus month labels."""
    if not columns:
        return "", ""

    width = len(columns) * CONTRIB_PITCH - CONTRIB_GAP

    cells = []
    months = []
    last_month_label = -99
    for week, days in enumerate(columns):
        first = next((day for day in days if day), None)
        if first:
            month = first["date"][:7]
            month_names = [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            ]
            label = month_names[int(month[5:7]) - 1]
            if not months or months[-1][0] != label:
                if week - last_month_label >= 4 and week * CONTRIB_PITCH < width - 24:
                    months.append((label, week * CONTRIB_PITCH))
                    last_month_label = week
        for day_index, day in enumerate(days):
            if not day:
                continue
            cells.append(
                '<rect x="%d" y="%d" width="%d" height="%d" rx="2.5" fill="%s"></rect>'
                % (
                    week * CONTRIB_PITCH,
                    day_index * CONTRIB_PITCH,
                    CONTRIB_CELL,
                    CONTRIB_CELL,
                    LEVEL_COLORS[min(day["level"], 4)],
                )
            )

    grid = (
        '<svg viewBox="0 0 %d %d" width="%d" height="%d" xmlns="http://www.w3.org/2000/svg">%s</svg>'
        % (
            width,
            7 * CONTRIB_PITCH - CONTRIB_GAP,
            width,
            7 * CONTRIB_PITCH - CONTRIB_GAP,
            "".join(cells),
        )
    )
    month_labels = "".join(
        '<span style="position: absolute; left: %dpx;">%s</span>' % (x, label)
        for label, x in months
    )
    return grid, month_labels


contrib_grid, contrib_months = contribution_heatmap(CONTRIBUTIONS.get("columns") or [])

contrib_total = CONTRIBUTIONS.get("total")
contrib_note = (
    "%s in the last year" % format(contrib_total, ",") if contrib_total is not None else ""
)
contrib_window = (
    "%s → %s" % (CONTRIBUTIONS["start"], CONTRIBUTIONS["end"])
    if CONTRIBUTIONS.get("start")
    else ""
)

contrib_legend = "".join(
    '<span style="display: inline-block; width: 9px; height: 9px; border-radius: 2px;'
    ' background-color: %s;"></span>' % color
    for color in LEVEL_COLORS
)

contrib_content = """
<div class="card">
  %(head)s
  <div style="position: relative; height: 12px; margin-bottom: 8px;">
    <span class="mono" style="font-size: 9px; color: %(faint)s;">%(months)s</span>
  </div>
  %(grid)s
  <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
    <span class="mono" style="font-size: 9.5px; color: %(faint)s;">%(window)s</span>
    <span class="mono" style="font-size: 9.5px; color: %(faint)s; display: flex;
                 align-items: center; gap: 4px;">Less %(legend)s More</span>
  </div>
</div>
""" % {
    "head": head("Contributions", contrib_note),
    "months": contrib_months,
    "grid": contrib_grid,
    "legend": contrib_legend,
    "window": contrib_window,
    "faint": FAINT,
}
save_svg("contrib.svg", *CARD_SIZES["contrib"], contrib_content)


# =====================================================================
# 11 -- Closing
# =====================================================================
closing_content = """
<div class="card" style="padding: 26px 20px;">
  <div class="name" style="font-size: 25px; color: %(ink_strong)s;">Let’s build something meaningful.</div>
  <div style="font-size: 13.5px; line-height: 1.5; color: %(muted)s; margin-top: 8px;">
    Always open to collaboration, new opportunities, and interesting technical conversations.
  </div>
</div>
""" % {"ink_strong": INK_STRONG, "muted": MUTED}
save_svg("closing.svg", *CARD_SIZES["closing"], closing_content)


# =====================================================================
# 12 -- Alt text, assembled from the same data the cards are drawn from
# =====================================================================
def as_sentence(text):
    """Normalise a profile.json fragment so alt text reads as whole sentences."""
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


tech_names = ", ".join(
    TECH_LABELS.get(key, key)
    for _label, category in TECH_CATEGORIES
    for key in profile["tech_stack"].get(category, [])
)

# Alt text is read aloud, so it carries the same content as the cards with the
# markup flattened out of it.
def plain(text):
    return re.sub(r"<[^>]+>", "", text)


ALT_TEXT = {
    "header": "%(name)s — %(role)s %(email)s"
    % {"name": profile["name"], "role": profile["role"], "email": EMAIL},
    "nav": "Section navigation: about, tech stack, featured projects and GitHub analytics",
    "hero": "%(name)s: %(role)s Focus: %(focus)s. %(quote)s"
    % {
        "name": profile["name"],
        "role": profile["role"],
        "focus": ", ".join(text.lower() for _idx, text in FOCUS),
        "quote": " ".join(plain(line) for line in profile["quote"]["lines"]),
    },
    "action_email": "Email me at %s" % EMAIL,
    "action_resume": "Open my resume",
    "info": "Profile: B.Tech CSE (Data Science) at Dayananda Sagar University; "
    "based in Bengaluru, India (IST, UTC+5:30, remote-friendly); open to SDE and data "
    "engineering, backend and infrastructure roles; open to collaboration by email",
    "about": "%s Exploring: %s. Interests: %s. %s"
    % (
        profile["about_me"]["text"],
        profile["about_me"]["exploring"],
        profile["about_me"]["interests"],
        profile["about_me"]["fun_fact"],
    ),
    "stack": "Tech stack by category: %s" % tech_names,
    "principles": "Engineering principles: "
    + " ".join(as_sentence(item) for item in profile["principles"]),
    "building": "Currently building (self-assessed progress): "
    + "; ".join("%s %d%%" % (item["name"], item["percentage"]) for item in profile["currently_building"]),
    "next": "Planned, not started: "
    + "; ".join("%s %s" % (item["name"], item["desc"]) for item in profile["upcoming_projects"]),
    "stats": "GitHub stats for %s: %d public repositories, %d stars, %d followers and %d "
    "languages, from the GitHub REST API" % (
        GITHUB_USER,
        GITHUB_STATS["public_repos"],
        GITHUB_STATS["stars"],
        GITHUB_STATS["followers"],
        langs_total,
    ),
    "top_langs": "Top %d of %d languages across %s's public repositories by repository count: %s"
    % (
        len(GITHUB_STATS["languages"]),
        langs_total,
        GITHUB_USER,
        ", ".join("%s (%d)" % (l["name"], l["repos"]) for l in GITHUB_STATS["languages"]),
    ),
    "contrib": "Contribution calendar for %s: %s contributions between %s and %s"
    % (
        GITHUB_USER,
        format(contrib_total, ",") if contrib_total is not None else "unknown",
        CONTRIBUTIONS.get("start", "unknown"),
        CONTRIBUTIONS.get("end", "unknown"),
    ),
    "closing": "Let’s build something meaningful — always open to collaboration, new "
    "opportunities and interesting technical conversations",
}

PROJECT_LINKS = "\n\n".join(
    '<p align="center"><a href="%s"><img src="assets/cards/project_%d.svg" width="%d" '
    'alt="%s — %s Status: %s."></a></p>'
    % (
        project["url"],
        idx,
        CARD_SIZES["project"][0],
        project["name"],
        as_sentence(project["desc"]),
        project["status"],
    )
    for idx, project in enumerate(profile["featured_projects"])
)

NAV_LINKS = ROW_GAP.join(
    '<a href="%s"><img src="assets/cards/%s" width="%d" '
    'alt="Jump to the %s section"></a>' % (href, filename, CARD_SIZES["nav"][0], label.lower())
    for filename, label, href in NAV_ITEMS
)

CONTACT_LINKS = ROW_GAP.join(
    '<a href="%s"><img src="assets/cards/%s" width="%d" alt="%s"></a>'
    % (href, filename, CARD_SIZES["nav"][0], label)
    for filename, label, href in CONTACT_ITEMS
)


# =====================================================================
# 13 -- README.md
# =====================================================================
readme_template = """<!-- Generated by generate.py from profile.json -- edit those, not this file. -->

<!-- Header: monogram, name, contact meta. -->
<p align="center"><img src="assets/cards/header.svg" width="{header_w}" alt="{alt_header}"></p>

<!-- Section navigation. Real in-page links, not decoration: GitHub emits
     `id="user-content-<slug>"` on every heading and strips the prefix at runtime,
     so `#featured-projects` resolves to the heading below. -->
<p align="center">{nav}</p>

<!-- Hero. -->
<p align="center"><img src="assets/cards/hero.svg" width="{grid}" alt="{alt_hero}"></p>

<!-- Primary and secondary action. -->
<p align="center"><a href="mailto:{email}"><img src="assets/cards/action_email.svg" width="{pair_w}" alt="{alt_email}"></a>{gap}<a href="{resume}"><img src="assets/cards/action_resume.svg" width="{pair_w}" alt="{alt_resume}"></a></p>

<!-- Profile at a glance: four balanced columns inside one card, so they are
     always four columns on one row and can never wrap into a ragged 3 + 1. -->
<p align="center"><img src="assets/cards/info.svg" width="{grid}" alt="{alt_info}"></p>

<h2 align="center">About</h2>

<p align="center"><img src="assets/cards/about.svg" width="{grid}" alt="{alt_about}"></p>

<h2 align="center">Tech Stack</h2>

<p align="center"><img src="assets/cards/stack.svg" width="{grid}" alt="{alt_stack}"></p>

<!-- Principles beside current work: two half-width cards rather than two narrow
     ones stacked in the middle of the page. -->
<p align="center"><img src="assets/cards/principles.svg" width="{pair_w}" alt="{alt_principles}">{gap}<img src="assets/cards/building.svg" width="{pair_w}" alt="{alt_building}"></p>

<!-- Planned work, one row, labelled as planned. -->
<p align="center"><img src="assets/cards/next.svg" width="{grid}" alt="{alt_next}"></p>

<h2 align="center">Featured Projects</h2>

{projects}

<p align="center"><a href="{github}?tab=repositories">View all repositories &rarr;</a></p>

<h2 align="center">GitHub Analytics</h2>

<p align="center"><img src="assets/cards/gh_stats.svg" width="{pair_w}" alt="{alt_stats}">{gap}<img src="assets/cards/gh_langs.svg" width="{pair_w}" alt="{alt_langs}"></p>

<p align="center"><img src="assets/cards/contrib.svg" width="{grid}" alt="{alt_contrib}"></p>

<!-- Closing. -->
<p align="center"><img src="assets/cards/closing.svg" width="{grid}" alt="{alt_closing}"></p>

<p align="center">{contacts}</p>
""".format(
    header_w=CARD_SIZES["header"][0],
    grid=GRID,
    pair_w=PAIR_W,
    gap=ROW_GAP,
    email=EMAIL,
    resume=RESUME_URL,
    github=GITHUB_URL,
    nav=NAV_LINKS,
    projects=PROJECT_LINKS,
    contacts=CONTACT_LINKS,
    alt_header=ALT_TEXT["header"],
    alt_hero=ALT_TEXT["hero"],
    alt_email=ALT_TEXT["action_email"],
    alt_resume=ALT_TEXT["action_resume"],
    alt_info=ALT_TEXT["info"],
    alt_about=ALT_TEXT["about"],
    alt_stack=ALT_TEXT["stack"],
    alt_principles=ALT_TEXT["principles"],
    alt_building=ALT_TEXT["building"],
    alt_next=ALT_TEXT["next"],
    alt_stats=ALT_TEXT["stats"],
    alt_langs=ALT_TEXT["top_langs"],
    alt_contrib=ALT_TEXT["contrib"],
    alt_closing=ALT_TEXT["closing"],
)

# ----------------- Card validation -----------------
# Every card is an XML document, and a browser silently drops an SVG it cannot
# parse -- so a stray HTML-only entity (&middot;, &rarr;) or an unclosed <img>
# publishes a blank space with no warning anywhere. Both shipped once; this
# fails the build instead, before README.md is written.
INVALID_CARDS = []
for card_name in sorted(os.listdir(CARDS_DIR)):
    if not card_name.endswith(".svg"):
        continue
    try:
        xml.etree.ElementTree.parse(os.path.join(CARDS_DIR, card_name))
    except xml.etree.ElementTree.ParseError as exc:
        INVALID_CARDS.append("%s: %s" % (card_name, exc))
if INVALID_CARDS:
    for problem in INVALID_CARDS:
        print("INVALID CARD: %s" % problem)
    raise SystemExit("Refusing to write README.md: %d card(s) are not valid XML" % len(INVALID_CARDS))
print("Validated: every card is well-formed XML")

README_MD = os.path.join(WORKSPACE_DIR, "README.md")
with open(README_MD, "w", encoding="utf-8") as rf:
    rf.write(readme_template)

print("SUCCESS: cards written and README.md generated!")
