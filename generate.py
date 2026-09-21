import os
import json
import base64
import collections
import datetime
import re
import urllib.request

# The devicon LinkedIn glyph, embedded as the fallback for the fetch below. The
# fetch returns "" whenever the CDN is unreachable, and that empty string used to
# be written straight into icon_linkedin.svg — a silently broken image in the
# published README, produced by any build without network access.
LINKEDIN_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
    '<path fill="#0076b2" d="M116 3H12a8.91 8.91 0 00-9 8.8v104.42a8.91 8.91 0 009 8.78h104a8.93 8.93 0 009-8.81V11.77A8.93 8.93 0 00116 3z"/>'
    '<path fill="#fff" d="M21.06 48.73h18.11V107H21.06zm9.06-29a10.5 10.5 0 11-10.5 10.49 10.5 10.5 0 0110.5-10.49M50.53 48.73h17.36v8h.24c2.42-4.58 8.32-9.41 17.13-9.41C103.6 47.28 107 59.35 107 75v32H88.89V78.65c0-6.75-.12-15.44-9.41-15.44s-10.87 7.36-10.87 15V107H50.53z"/>'
    '</svg>'
)


def as_data_uri(svg_str):
    return "data:image/svg+xml;base64," + base64.b64encode(svg_str.encode('utf-8')).decode('utf-8')


# Fetch the LinkedIn Icon, falling back to the embedded copy so the card is
# always complete. The fallback is the same glyph, so an offline build and an
# online build produce identical bytes.
def fetch_linkedin_icon():
    url = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linkedin/linkedin-original.svg"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                svg_content = response.read()
                svg_str = svg_content.decode('utf-8')
                svg_str = re.sub(r'<\?xml.*?\?>', '', svg_str)
                svg_str = re.sub(r'<!--.*?-->', '', svg_str, flags=re.DOTALL)
                return as_data_uri(svg_str.strip())
    except Exception as e:
        print(f"Warning: LinkedIn icon fetch failed ({e}); using the embedded copy")
    return as_data_uri(LINKEDIN_ICON_SVG)


linkedin_b64 = fetch_linkedin_icon()

# Root Paths
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_JSON = os.path.join(WORKSPACE_DIR, "profile.json")
BASE64_ICONS_JSON = os.path.join(WORKSPACE_DIR, "assets", "base64_icons.json")
CARDS_DIR = os.path.join(WORKSPACE_DIR, "assets", "cards")

# Ensure assets/cards directory exists
os.makedirs(CARDS_DIR, exist_ok=True)

# Load profile config
with open(PROFILE_JSON, "r", encoding="utf-8") as f:
    profile = json.load(f)

# Recursively escape XML characters (like ampersands) in profile data
def escape_xml(text):
    if not isinstance(text, str):
        return text
    # Escape ampersands that are not already part of an XML entity
    return re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+);)', '&amp;', text)

def escape_dict(d):
    if isinstance(d, dict):
        return {k: escape_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [escape_dict(item) for item in d]
    elif isinstance(d, str):
        return escape_xml(d)
    return d

profile = escape_dict(profile)

# Load base64 icons database
with open(BASE64_ICONS_JSON, "r", encoding="utf-8") as f:
    icons = json.load(f)

# Find banner background (optimized JPEG preferred, fallback to PNG)
banner_src = ""
for ext in ["optimized.jpg", "optimized.png", "png", "jpg"]:
    path = os.path.join(WORKSPACE_DIR, "assets", f"header_background_{ext}" if ext.startswith("optimized") else f"header_background.{ext}")
    if os.path.exists(path):
        with open(path, "rb") as bf:
            banner_data = base64.b64encode(bf.read()).decode("utf-8")
            fmt = "jpeg" if ext.endswith("jpg") else "png"
            banner_src = f"data:image/{fmt};base64,{banner_data}"
            break

# ----------------- SVG Card Compilation Helpers -----------------

# Common CSS styles shared across cards
COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Architects+Daughter&amp;family=Inter:wght@300;400;500;600;700&amp;family=Outfit:wght@400;500;600;700;800&amp;family=Courier+Prime&amp;display=swap');
body {
  font-family: 'Inter', sans-serif;
  color: #3c2f2f;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  background-color: transparent;
}
h1, h2, h3, h4, h5, h6 {
  font-family: 'Outfit', sans-serif;
  color: #2c1e1e;
  margin: 0;
}
.card {
  background-color: #fffdfa;
  border: 1px solid #e5dacf;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 10px rgba(139, 115, 85, 0.05);
  box-sizing: border-box;
  height: 100%;
}
.card-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2c1e1e;
}
"""

# ----------------- Card Geometry -----------------
# Single source of truth for every card's intrinsic size. save_svg() and the
# README template both read from here, so a rendered <img> can never disagree
# with the viewBox of the file it points at.
CARD_SIZES = {
    "header": (850, 380),
    "info": (200, 95),
    "about_me": (290, 380),
    "btn": (138, 40),
    "tech_stack": (290, 540),
    "principles": (290, 320),
    "currently_building": (290, 330),
    "what_i_build": (510, 330),
    "project": (510, 190),
    "upcoming_projects": (510, 210),
    "icon": (110, 32),
    "footer": (850, 110),
    "gh_stats": (510, 210),
    "gh_langs": (510, 210),
}

# Flattened aliases so the README template can reference sizes without nesting
# quotes inside the f-string expressions.
#
# Only widths are pinned in the markup. A fixed `height` attribute combined with
# the host's `max-width: 100%` squashes an image on narrow viewports (GitHub's
# markdown body is ~830px on desktop), so cards are rendered at their design
# width and scale proportionally from there.
HEADER_W = CARD_SIZES["header"][0]
INFO_W, INFO_H = CARD_SIZES["info"]
ABOUT_W = CARD_SIZES["about_me"][0]
BTN_W = CARD_SIZES["btn"][0]
TECH_W = CARD_SIZES["tech_stack"][0]
PRINCIPLES_W = CARD_SIZES["principles"][0]
BUILD_W = CARD_SIZES["currently_building"][0]
WHAT_W, WHAT_H = CARD_SIZES["what_i_build"]
PROJECT_W, PROJECT_H = CARD_SIZES["project"]
UPCOMING_W = CARD_SIZES["upcoming_projects"][0]
ICON_W = CARD_SIZES["icon"][0]
FOOTER_W = CARD_SIZES["footer"][0]
GH_STATS = CARD_SIZES["gh_stats"]
GH_LANGS = CARD_SIZES["gh_langs"]

def save_svg(filename, width, height, content):
    filepath = os.path.join(CARDS_DIR, filename)
    svg = f"""<svg fill="none" viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <foreignObject x="0" y="0" width="{width}" height="{height}">
    <div xmlns="http://www.w3.org/1999/xhtml" style="width: {width}px; height: {height}px; box-sizing: border-box;">
      <style>
        {COMMON_CSS}
      </style>
      {content}
    </div>
  </foreignObject>
</svg>"""
    with open(filepath, "w", encoding="utf-8") as sf:
        sf.write(svg)
    print(f"Compiled: {filename}")

# ----------------- 1. Header Banner SVG -----------------
header_lines = "".join([f"<p>{line}</p>" for line in profile["quote"]["lines"]])
header_content = f"""
<style>
  .header-banner {{
    width: 850px;
    height: 380px;
    background-image: url('{banner_src}');
    background-position: center center;
    background-size: cover;
    background-repeat: no-repeat;
    position: relative;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(139, 115, 85, 0.06);
  }}
  .header-overlay {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(to right, rgba(244, 235, 225, 0.95) 0%, rgba(244, 235, 225, 0.85) 45%, rgba(244, 235, 225, 0.1) 75%, rgba(244, 235, 225, 0) 100%);
  }}
  .header-left {{
    position: absolute;
    left: 45px;
    top: 35px;
    width: 390px;
    z-index: 2;
  }}
  .header-title {{
    font-size: 32px;
    font-weight: 800;
    margin: 0 0 12px 0;
    line-height: 1.1;
    color: #1e120c;
  }}
  .header-title .highlight {{
    color: #b05a30;
  }}
  .header-subtitle {{
    font-size: 15px;
    font-weight: 700;
    line-height: 1.4;
    margin: 0 0 15px 0;
    color: #2c1a11;
  }}
  .header-subtitle .coffee-emoji {{
    font-size: 18px;
  }}
  .header-academic {{
    font-size: 12px;
    line-height: 1.5;
    margin: 0 0 18px 0;
    color: #4a3a30;
  }}
  .header-academic strong {{
    color: #964016;
    font-weight: 600;
  }}
  .header-quote-box {{
    border-left: 3px solid #b05a30;
    padding-left: 14px;
    margin-top: 15px;
  }}
  .header-quote-box p {{
    margin: 4px 0;
    font-size: 13px;
    font-weight: 500;
    color: #3e2b20;
  }}
  .header-quote-box .highlight-text {{
    color: #964016;
    font-weight: 600;
  }}
</style>
<div class="header-banner">
  <div class="header-overlay">
    <div class="header-left">
      <h1 class="header-title">Hi, I'm <span class="highlight">{profile["name"]}</span>.</h1>
      <p class="header-subtitle">
        <span class="coffee-emoji">☕</span> {profile["role"]}
      </p>
      <p class="header-academic">
        {profile["academic"]}
      </p>
      <div class="header-quote-box">
        {header_lines}
      </div>
    </div>
  </div>
</div>
"""
save_svg("header.svg", *CARD_SIZES["header"], header_content)

# ----------------- 2. Info Cards (Separate SVGs) -----------------
# Card 1: Graduation
save_svg("info_1.svg", *CARD_SIZES["info"], f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: {INFO_H}px;
    box-sizing: border-box;
  }}
  .info-icon {{ width: 25px; height: 25px; flex-shrink: 0; }}
  .info-text {{ display: flex; flex-direction: column; }}
  .info-title {{ font-size: 14px; font-weight: 700; color: #2c1e1e; }}
  .info-detail {{ font-size: 12px; color: #7a6a65; margin-top: 2px; }}
</style>
<div class="info-box">
  <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="#b05a30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/></svg>
  <div class="info-text">
    <div class="info-title">B.Tech CSE (Data Science)</div>
    <div class="info-detail">Dayananda Sagar University</div>
  </div>
</div>
""")

# Card 2: Location
save_svg("info_2.svg", *CARD_SIZES["info"], f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: {INFO_H}px;
    box-sizing: border-box;
  }}
  .info-icon {{ width: 25px; height: 25px; flex-shrink: 0; }}
  .info-text {{ display: flex; flex-direction: column; }}
  .info-title {{ font-size: 14px; font-weight: 700; color: #2c1e1e; }}
  .info-detail {{ font-size: 12px; color: #7a6a65; margin-top: 2px; }}
</style>
<div class="info-box">
  <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="#b05a30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
  <div class="info-text">
    <div class="info-title">Bengaluru, India</div>
    <div class="info-detail">Currently in Bengaluru, India</div>
  </div>
</div>
""")

# Card 3: Open to
save_svg("info_3.svg", *CARD_SIZES["info"], f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: {INFO_H}px;
    box-sizing: border-box;
  }}
  .info-icon {{ width: 25px; height: 25px; flex-shrink: 0; }}
  .info-text {{ display: flex; flex-direction: column; }}
  .info-title {{ font-size: 14px; font-weight: 700; color: #2c1e1e; }}
  .info-detail {{ font-size: 12px; color: #7a6a65; margin-top: 2px; }}
</style>
<div class="info-box">
  <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="#b05a30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
  <div class="info-text">
    <div class="info-title">Open to</div>
    <div class="info-detail">SDE • DE • Backend • Infra</div>
  </div>
</div>
""")

# Card 4: Let's Connect
save_svg("info_4.svg", *CARD_SIZES["info"], f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: {INFO_H}px;
    box-sizing: border-box;
  }}
  .info-icon {{ width: 25px; height: 25px; flex-shrink: 0; }}
  .info-text {{ display: flex; flex-direction: column; }}
  .info-title {{ font-size: 14px; font-weight: 700; color: #2c1e1e; }}
  .info-detail {{ font-size: 12px; color: #7a6a65; margin-top: 2px; }}
</style>
<div class="info-box">
  <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="#b05a30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
  <div class="info-text">
    <div class="info-title">Let's connect!</div>
    <div class="info-detail">Always open to new opportunities</div>
  </div>
</div>
""")

# ----------------- 3. About Me SVG -----------------
about_me_content = f"""
<style>
  .about-text {{ font-size: 15.5px; line-height: 1.5; margin: 0 0 15px 0; color: #5a4a42; }}
  .divider {{ border: 0; border-top: 1px solid #e5dacf; margin: 15px 0; }}
  .about-list {{ list-style: none; padding: 0; margin: 0; }}
  .about-list li {{ font-size: 14px; line-height: 1.6; margin-bottom: 10px; color: #3c2f2f; }}
</style>
<div class="card">
  <h2 class="card-title">☕ About Me</h2>
  <p class="about-text">
    {profile["about_me"]["text"]}
  </p>
  <hr class="divider"/>
  <ul class="about-list">
    <li>🎓 <strong>Exploring:</strong> {profile["about_me"]["exploring"]}</li>
    <li>💡 <strong>Interests:</strong> {profile["about_me"]["interests"]}</li>
    <li>⚡ <strong>Fun Fact:</strong> {profile["about_me"]["fun_fact"]}</li>
  </ul>
</div>
"""
save_svg("about_me.svg", *CARD_SIZES["about_me"], about_me_content)

# ----------------- 4. Action Buttons -----------------
save_svg("btn_email.svg", *CARD_SIZES["btn"], """
<style>
  .btn {
    width: 138px;
    height: 40px;
    background-color: #3c2f2f;
    color: #fffdfa;
    border-radius: 6px;
    font-size: 14.5px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    box-sizing: border-box;
  }
  .btn svg { width: 14px; height: 14px; }
</style>
<div class="btn">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
  <span>Email Me</span>
</div>
""")

save_svg("btn_resume.svg", *CARD_SIZES["btn"], """
<style>
  .btn {
    width: 138px;
    height: 40px;
    background-color: transparent;
    border: 1px solid #3c2f2f;
    color: #3c2f2f;
    border-radius: 6px;
    font-size: 14.5px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    box-sizing: border-box;
  }
  .btn svg { width: 14px; height: 14px; }
</style>
<div class="btn">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
  <span>Resume</span>
</div>
""")

# ----------------- 5. Tech Stack SVG -----------------
def get_icon_html(category, name):
    if category in icons and name in icons[category]:
        return f'<img src="{icons[category][name]}" class="tech-icon" alt="{name}" />'
    return ""

tech_rows = []
for label, keys in [
    ("Languages", ["go", "java", "python", "javascript", "cplusplus", "postgresql"]),
    ("Distributed Systems", ["apachekafka", "grpc", "redis", "docker", "rabbitmq", "kubernetes"]),
    ("Data &amp; Streaming", ["apachespark", "apacheairflow", "googlecloud", "kubernetes"]),
    ("Databases", ["postgresql", "redis", "mongodb", "mysql"]),
    ("Cloud &amp; DevOps", ["amazonwebservices", "kubernetes", "docker", "terraform", "prometheus"]),
    ("Observability", ["prometheus", "grafana"]),
    ("Tools", ["git", "github", "linux", "vscode", "intellij"])
]:
    category_map = {
        "Languages": "languages",
        "Distributed Systems": "distributed",
        "Data &amp; Streaming": "data_streaming",
        "Databases": "databases",
        "Cloud &amp; DevOps": "cloud_devops",
        "Observability": "observability",
        "Tools": "tools"
    }
    cat = category_map[label]
    img_tags = "".join([get_icon_html(cat, name) for name in keys if name in profile["tech_stack"][cat]])
    tech_rows.append(f"""
    <div class="tech-row">
      <div class="tech-label">{label}</div>
      <div class="tech-icons">{img_tags}</div>
    </div>
    """)

tech_stack_content = f"""
<style>
  .tech-table {{ display: flex; flex-direction: column; gap: 14px; }}
  .tech-row {{ display: flex; flex-direction: column; gap: 6px; }}
  .tech-label {{ font-size: 13px; font-weight: 700; color: #7a6a65; text-transform: uppercase; letter-spacing: 0.5px; }}
  .tech-icons {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .tech-icon {{ width: 30px; height: 30px; border-radius: 4px; }}
</style>
<div class="card">
  <h2 class="card-title">🛠️ Tech Stack</h2>
  <div class="tech-table">
    {"".join(tech_rows)}
  </div>
</div>
"""
save_svg("tech_stack.svg", *CARD_SIZES["tech_stack"], tech_stack_content)

# ----------------- 6. Engineering Principles SVG -----------------
principles_items = "".join([f"""
<div class="principle-item">
  <svg class="checkmark" viewBox="0 0 24 24" fill="none" stroke="#b05a30" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  <span>{item}</span>
</div>
""" for item in profile["principles"]])

principles_content = f"""
<style>
  .principles-list {{ display: flex; flex-direction: column; gap: 12px; }}
  .principle-item {{ display: flex; align-items: flex-start; gap: 8px; }}
  .principle-item span {{ font-size: 15.5px; line-height: 1.4; font-weight: 500; color: #3c2f2f; }}
  .checkmark {{ width: 14px; height: 14px; margin-top: 2px; flex-shrink: 0; }}
  .coffee-stain {{ position: absolute; right: -30px; bottom: -30px; width: 110px; height: 110px; border: 3px solid rgba(139, 90, 43, 0.08); border-radius: 50%; pointer-events: none; }}
  .coffee-stain-inner {{ position: absolute; right: -24px; bottom: -24px; width: 98px; height: 98px; border: 1px solid rgba(139, 90, 43, 0.05); border-radius: 50%; pointer-events: none; }}
</style>
<div class="card" style="position: relative; overflow: hidden;">
  <h2 class="card-title">📋 Engineering Principles</h2>
  <div class="principles-list">
    {principles_items}
  </div>
  <div class="coffee-stain"></div>
  <div class="coffee-stain-inner"></div>
</div>
"""
save_svg("principles.svg", *CARD_SIZES["principles"], principles_content)

# ----------------- 7. Currently Building SVG -----------------
progress_items = []
for item in profile["currently_building"]:
    pct = item["percentage"]
    fill_cls = f"fill-{pct}"
    # Generate inline dynamic fill style
    progress_items.append(f"""
    <div class="progress-container">
      <div class="progress-header">
        <span>{item["name"]}</span>
        <span>{pct}%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="background-color: {'#5b7c56' if pct==100 else '#d48a37' if pct>50 else '#3c2f2f' if pct>0 else 'transparent'}; width: {pct}%;"></div>
      </div>
    </div>
    """)

currently_building_content = f"""
<style>
  .progress-container {{ margin-bottom: 12px; }}
  .progress-header {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: 600; margin-bottom: 5px; color: #3c2f2f; }}
  .progress-bar-bg {{ background-color: #e5dacf; height: 6px; border-radius: 3px; overflow: hidden; }}
  .progress-bar-fill {{ height: 100%; border-radius: 3px; }}
</style>
<div class="card">
  <h2 class="card-title">🏗️ Currently Building</h2>
  {"".join(progress_items)}
</div>
"""
save_svg("currently_building.svg", *CARD_SIZES["currently_building"], currently_building_content)

# ----------------- 8. What I Build SVG -----------------
what_items = []
icons_map = {
    "Distributed Systems": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>',
    "Streaming Infra": '<path d="M2 10h20M2 14h20M12 2v20"/>',
    "Backend Platforms": '<rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>',
    "Reliability Eng.": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
}
for item in profile["what_i_build"]:
    title = item["title"]
    desc = item["desc"]
    path_d = icons_map.get(title, '<circle cx="12" cy="12" r="10"/>')
    what_items.append(f"""
    <div class="what-card">
      <div class="what-header">
        <svg class="what-icon" viewBox="0 0 24 24" fill="none" stroke="#b05a30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path_d}</svg>
        <span class="what-title">{title}</span>
      </div>
      <p class="what-desc">{desc}</p>
    </div>
    """)

what_i_build_content = f"""
<style>
  .what-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .what-card {{ background-color: #fffdfa; border: 1px solid #e5dacf; border-radius: 8px; padding: 12px; min-height: 110px; box-sizing: border-box; }}
  .what-header {{ display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }}
  .what-icon {{ width: 18px; height: 18px; flex-shrink: 0; }}
  .what-title {{ font-size: 14.5px; font-weight: 700; color: #2c1e1e; }}
  .what-desc {{ font-size: 12.5px; line-height: 1.5; color: #7a6a65; margin: 0; }}
</style>
<div class="card" style="height: {WHAT_H}px; box-sizing: border-box;">
  <h2 class="card-title">💻 What I Build</h2>
  <div class="what-grid">
    {"".join(what_items)}
  </div>
</div>
"""
save_svg("what_i_build.svg", *CARD_SIZES["what_i_build"], what_i_build_content)

# ----------------- 9. Featured Projects (Separate Clickable Cards) -----------------
project_icons = [
    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="6" y1="9" x2="6" y2="15"/><line x1="9" y1="6" x2="15" y2="6"/><line x1="9" y1="18" x2="15" y2="18"/><line x1="18" y1="9" x2="18" y2="15"/>',
    '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
]

# Finished work previously got the in-progress badge, because only the literal
# status "Production" was treated as green.
COMPLETE_STATUSES = {"production", "done", "complete", "completed", "shipped"}

for idx, project in enumerate(profile["featured_projects"]):
    badge_cls = (
        "badge-production"
        if project["status"].strip().lower() in COMPLETE_STATUSES
        else "badge-inprogress"
    )
    tags_html = "".join([f"<span>{tag}</span>" for tag in project["tags"]])
    icon_d = project_icons[idx % len(project_icons)]
    
    project_card_content = f"""
    <style>
      .project-item {{
        background-color: #fffdfa;
        border: 1px solid #e5dacf;
        border-radius: 8px;
        padding: 14px;
        display: flex;
        gap: 14px;
        height: {PROJECT_H}px;
        box-sizing: border-box;
      }}
      .project-icon-box {{
        width: 32px;
        height: 32px;
        border-radius: 6px;
        background-color: #3c2f2f;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }}
      .project-icon-box svg {{ width: 16px; height: 16px; }}
      .project-content {{ flex: 1; }}
      .project-header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
      .project-name {{ font-size: 16px; font-weight: 700; color: #2c1e1e; }}
      .badge {{ font-size: 8.5px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }}
      .badge-production {{ background-color: #e2f0d9; color: #385723; border: 1px solid #c5e0b4; }}
      .badge-inprogress {{ background-color: #fff2cc; color: #7f6000; border: 1px solid #ffe599; }}
      .project-desc {{ font-size: 14px; line-height: 1.4; color: #5a4a42; margin: 0 0 10px 0; }}
      .project-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
      .project-tags span {{ font-family: 'Courier Prime', monospace; font-size: 12px; background-color: #f4ebe1; color: #5a4a42; border: 1px solid #e5dacf; border-radius: 4px; padding: 1px 5px; }}
    </style>
    <div class="project-item">
      <div class="project-icon-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="#fffdfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{icon_d}</svg>
      </div>
      <div class="project-content">
        <div class="project-header-row">
          <span class="project-name">{project["name"]}</span>
          <span class="badge {badge_cls}">{project["status"]}</span>
        </div>
        <p class="project-desc">{project["desc"]}</p>
        <div class="project-tags">{tags_html}</div>
      </div>
    </div>
    """
    save_svg(f"project_{idx}.svg", *CARD_SIZES["project"], project_card_content)

# ----------------- 10. Upcoming Projects SVG -----------------
upcoming_items = "".join([f"""
<li>
  <span class="upcoming-bullet"></span>
  <div>
    <strong>{item["name"]}</strong>
    <div class="upcoming-sub">{item["desc"]}</div>
  </div>
</li>
""" for item in profile["upcoming_projects"]])

upcoming_content = f"""
<style>
  .upcoming-list {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }}
  .upcoming-list li {{ display: flex; gap: 10px; align-items: flex-start; }}
  .upcoming-bullet {{ width: 6px; height: 6px; border-radius: 50%; background-color: #b05a30; margin-top: 5px; flex-shrink: 0; }}
  .upcoming-list li strong {{ font-size: 15px; font-weight: 600; color: #2c1e1e; }}
  .upcoming-sub {{ font-size: 12px; color: #7a6a65; margin-top: 2px; }}
</style>
<div class="card">
  <h2 class="card-title">📦 Upcoming Projects</h2>
  <ul class="upcoming-list">
    {upcoming_items}
  </ul>
</div>
"""
save_svg("upcoming_projects.svg", *CARD_SIZES["upcoming_projects"], upcoming_content)

# ----------------- 11. Social & Connect Buttons -----------------
save_svg("icon_github.svg", *CARD_SIZES["icon"], f"""
<style>
  .icon-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 6px;
    height: 32px;
    width: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #3c2f2f;
    box-sizing: border-box;
  }}
  .icon {{ width: 14px; height: 14px; }}
</style>
<div class="icon-box">
  <img src="{icons['tools']['github']}" class="icon" alt="GitHub" />
  <span>GitHub</span>
</div>
""")

save_svg("icon_linkedin.svg", *CARD_SIZES["icon"], f"""
<style>
  .icon-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 6px;
    height: 32px;
    width: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #3c2f2f;
    box-sizing: border-box;
  }}
  .icon {{ width: 14px; height: 14px; }}
</style>
<div class="icon-box">
  <img src="{linkedin_b64}" class="icon" alt="LinkedIn" />
  <span>LinkedIn</span>
</div>
""")

save_svg("icon_email.svg", *CARD_SIZES["icon"], """
<style>
  .icon-box {
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 6px;
    height: 32px;
    width: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #3c2f2f;
    box-sizing: border-box;
  }
  .icon { width: 14px; height: 14px; }
</style>
<div class="icon-box">
  <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
  <span>Email</span>
</div>
""")

# ----------------- 12. Footer Quote & Sticky Note -----------------
save_svg("footer.svg", *CARD_SIZES["footer"], """
<style>
  .footer-container {
    width: 850px;
    height: 110px;
    position: relative;
    background-color: transparent;
  }
  .footer-bar {
    width: 850px;
    height: 50px;
    background-color: #3c2f2f;
    display: flex;
    align-items: center;
    justify-content: center;
    position: absolute;
    bottom: 0;
    left: 0;
    border-radius: 6px;
  }
  .footer-quote {
    font-family: 'Outfit', sans-serif;
    font-style: italic;
    font-size: 13.5px;
    color: #f4ebe1;
  }
  .quote-author {
    font-size: 11.5px;
    color: #ebdcb9;
    font-style: normal;
    margin-left: 6px;
  }
  .sticky-note {
    position: absolute;
    right: 35px;
    top: 5px;
    width: 180px;
    background-color: #fdf5c4;
    border-radius: 2px;
    padding: 10px 12px;
    box-shadow: -2px 5px 12px rgba(0,0,0,0.12);
    transform: rotate(-3deg);
    border-bottom-right-radius: 12px 3px;
    z-index: 5;
    box-sizing: border-box;
  }
  .sticky-note p {
    margin: 4px 0;
    font-family: 'Architects Daughter', cursive;
    font-size: 10px;
    color: #3c2d1b;
    line-height: 1.3;
  }
  .sticky-note .smiley {
    font-family: 'Architects Daughter', cursive;
    font-size: 13px;
    text-align: right;
    color: #3c2d1b;
    margin-top: 2px;
  }
</style>
<div class="footer-container">
  <div class="footer-bar">
    <div class="footer-quote">
      “ First, solve the problem. Then, write the code. ” <span class="quote-author">— John Johnson</span>
    </div>
  </div>
  <div class="sticky-note">
    <p>Code is like humor.</p>
    <p>When you have to explain it, it's bad.</p>
    <div class="smiley">☺</div>
  </div>
</div>
""")

# ----------------- Derived profile constants -----------------
GITHUB_URL = profile["about_me"]["github_url"]
GITHUB_USER = GITHUB_URL.split("/")[-1]

# ----------------- 13. GitHub analytics (rendered locally) -----------------
# These numbers used to be two images served by github-readme-stats.vercel.app.
# That is a third-party deployment with no uptime guarantee: when it was paused
# the entire analytics section rendered as broken images, alt text and all. The
# numbers are fetched here instead, cached beside the other assets, and drawn as
# local SVGs in the same theme as every other card, so the README only ever
# depends on this repository.
GITHUB_STATS_JSON = os.path.join(WORKSPACE_DIR, "assets", "github_stats.json")

# Used when there is no cache and no network, so a build still produces a
# complete README. Refreshed values are written to GITHUB_STATS_JSON.
DEFAULT_GITHUB_STATS = {
    "source": "default",
    "auth": "anonymous",
    "checked_at": "",
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
    "fetched_at": "",
}


def fetch_github_stats():
    """Refresh repository stats from the GitHub API, falling back to the cache.

    The result records where the numbers came from — "api", "cache" or
    "default" — and how the attempt was authenticated, and it is written to disk
    on every run. A build that silently reused stale numbers therefore shows up
    in the committed file instead of passing unnoticed.
    """
    cached = {}
    if os.path.exists(GITHUB_STATS_JSON):
        with open(GITHUB_STATS_JSON, "r", encoding="utf-8") as cf:
            cached = json.load(cf)

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

    def write(stats):
        with open(GITHUB_STATS_JSON, "w", encoding="utf-8") as sf:
            json.dump(stats, sf, indent=2)
            sf.write("\n")

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
            # Distinct languages across all repositories. Separately from the
            # five shown on the card: counting the card's own list reported
            # "Languages used 5", which was simply wrong.
            "language_count": len(languages),
            "languages": [
                {"name": name, "repos": count} for name, count in languages.most_common(5)
            ],
        }
        write(stats)
        print(
            "GitHub stats refreshed from the API (%s, %s)"
            % (stats["fetched_at"], "with token" if token else "unauthenticated")
        )
        return stats
    except Exception as exc:
        print("Warning: GitHub stats fetch failed (%s)" % exc)
        # Reuse the last refresh, but record that this build fell back so the
        # committed file says so. fetched_at keeps the data's date; checked_at is
        # when this build tried.
        fallback = dict(cached) if cached else dict(DEFAULT_GITHUB_STATS)
        fallback["source"] = "cache" if cached else "default"
        fallback["auth"] = auth
        fallback["checked_at"] = today
        write(fallback)
        print(
            "Using %s stats (data fetched %s) — recorded in %s"
            % (fallback["source"], fallback.get("fetched_at") or "never", GITHUB_STATS_JSON)
        )
        return fallback


GITHUB_STATS = fetch_github_stats()

stat_tiles = "".join(
    """
    <div class="stat-tile">
      <div class="stat-value">%s</div>
      <div class="stat-label">%s</div>
    </div>
    """
    % (value, label)
    for value, label in [
        (GITHUB_STATS["public_repos"], "Public repositories"),
        (GITHUB_STATS["stars"], "Stars earned"),
        (GITHUB_STATS["followers"], "Followers"),
        (GITHUB_STATS.get("language_count") or len(GITHUB_STATS["languages"]), "Languages used"),
    ]
)

stats_footer = (
    "Updated %s" % GITHUB_STATS["fetched_at"]
    if GITHUB_STATS.get("fetched_at")
    else "Snapshot stats"
)

gh_stats_content = f"""
<style>
  .card-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .card-note {{ font-size: 11px; font-weight: 500; color: #9c8b86; }}
  .stat-grid {{ display: flex; gap: 10px; }}
  .stat-tile {{
    flex: 1;
    background-color: #f4ebe1;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 12px 8px;
    text-align: center;
  }}
  .stat-value {{
    font-family: 'Outfit', sans-serif;
    font-size: 24px;
    font-weight: 800;
    line-height: 1.1;
    color: #2c1e1e;
  }}
  .stat-label {{ font-size: 11px; color: #7a6a65; margin-top: 3px; }}
  .stat-foot {{ margin-top: 14px; font-size: 10.5px; color: #9c8b86; text-align: center; }}
</style>
<div class="card" style="height: {GH_STATS[1]}px; box-sizing: border-box;">
  <h2 class="card-title">📊 GitHub Stats <span class="card-note">github.com/{GITHUB_USER}</span></h2>
  <div class="stat-grid">{stat_tiles}
  </div>
  <div class="stat-foot">{stats_footer}</div>
</div>
"""
save_svg("gh_stats.svg", *GH_STATS, gh_stats_content)

max_repos = max(language["repos"] for language in GITHUB_STATS["languages"]) or 1
lang_rows = "".join(
    """
    <div class="lang-row">
      <span class="lang-name">{name}</span>
      <span class="lang-track"><span class="lang-fill" style="width: {width}%"></span></span>
      <span class="lang-count">{repos}</span>
    </div>
    """.format(name=language["name"], width=round(100 * language["repos"] / max_repos), repos=language["repos"])
    for language in GITHUB_STATS["languages"]
)

# The card lists only the top languages, while the stats card reports how many
# the account uses in total. Say which is which, or the two cards read as if
# they disagree ("8 languages used" above a list of five rows).
langs_total = GITHUB_STATS.get("language_count") or len(GITHUB_STATS["languages"])
langs_note = f"top {len(GITHUB_STATS['languages'])} of {langs_total} languages"

gh_langs_content = f"""
<style>
  .card-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .card-note {{ font-size: 11px; font-weight: 500; color: #9c8b86; }}
  .lang-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }}
  .lang-name {{ width: 110px; font-size: 12.5px; color: #3c2f2f; }}
  .lang-track {{
    flex: 1;
    height: 9px;
    background-color: #e5dacf;
    border-radius: 4.5px;
    overflow: hidden;
  }}
  .lang-fill {{ display: block; height: 100%; background-color: #b05a30; border-radius: 4.5px; }}
  .lang-count {{
    width: 26px;
    text-align: right;
    font-family: 'Courier Prime', monospace;
    font-size: 11.5px;
    color: #7a6a65;
  }}
</style>
<div class="card" style="height: {GH_LANGS[1]}px; box-sizing: border-box;">
  <h2 class="card-title">🧩 Top Languages <span class="card-note">{langs_note}</span></h2>
  <div>{lang_rows}
  </div>
</div>
"""
save_svg("gh_langs.svg", *GH_LANGS, gh_langs_content)

# ----------------- 14. Alt text for every card -----------------
# Assembled from profile.json wherever the card's content is drawn from it, so
# the accessible description cannot drift from the data it describes. The
# at-a-glance cards and the footer are rendered from literals in this file, so
# their descriptions are literals here too.


def as_sentence(text):
    """Normalise a profile.json fragment so alt text reads as whole sentences."""
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


ALT_TEXT = {
    "header": f"Hi, I'm {profile['name']} — {profile['role']}",
    "info_1": "Education: B.Tech in Computer Science and Engineering (Data Science) at Dayananda Sagar University",
    "info_2": "Location: Bengaluru, India",
    "info_3": "Open to: software development engineer, data engineering, backend and infrastructure roles",
    "info_4": f"Let's connect — always open to new opportunities. Email {profile['about_me']['email']}",
    # Alt text is read aloud in full, so these stay short: the cards themselves
    # are the detail, the description is the summary.
    "about_me": (
        f"About {profile['name']}: reliable, scalable and observable systems — "
        f"distributed systems, streaming pipelines, backend platforms and automation"
    ),
    "btn_email": f"Email me at {profile['about_me']['email']}",
    "btn_resume": "Open my resume",
    "tech_stack": (
        "Tech stack: Go, Java, Python, JavaScript, C++ and PostgreSQL, plus Kafka, gRPC, "
        "Redis, Docker, RabbitMQ, Kubernetes, Spark, Airflow, MongoDB, MySQL, AWS, "
        "Terraform, Prometheus and Grafana"
    ),
    "principles": "Engineering principles: "
    + " ".join(as_sentence(item) for item in profile["principles"]),
    "currently_building": "Currently building: " + "; ".join(
        "%s (%d%%)" % (item["name"], item["percentage"])
        for item in profile["currently_building"]
    ),
    "what_i_build": "What I build: "
    + ", ".join(item["title"].lower() for item in profile["what_i_build"]),
    "upcoming_projects": "Upcoming projects: " + "; ".join(
        "%s %s" % (item["name"], item["desc"]) for item in profile["upcoming_projects"]
    ),
    "stats": (
        f"GitHub stats for {GITHUB_USER}: "
        f"{GITHUB_STATS['public_repos']} public repositories, "
        f"{GITHUB_STATS['stars']} stars and {GITHUB_STATS['followers']} followers"
    ),
    "top_langs": "Top %d of %d languages across %s's public repositories by repository count: %s"
    % (
        len(GITHUB_STATS["languages"]),
        langs_total,
        GITHUB_USER,
        ", ".join("%s (%d)" % (l["name"], l["repos"]) for l in GITHUB_STATS["languages"]),
    ),
    "streak": f"Contribution streak statistics for {GITHUB_USER}",
    "contrib_3d": f"3D isometric graph of {GITHUB_USER}'s contribution calendar for the past year",
    "footer": (
        "Footer: First, solve the problem. Then, write the code. — John Johnson, "
        "with a sticky note reading: Code is like humor. When you have to explain it, it is bad."
    ),
}

# Every image sits inside its own <p align="center"> on a single line. That is
# deliberate and load-bearing on GitHub: a line holding a single complete tag is
# a CommonMark HTML block (type 7), which is emitted WITHOUT a wrapping <p>. Bare
# <img> lines therefore flow inline — cards ended up two per row, bottom-aligned
# on their shared line box, and a row of four broke into 3 + 1. An explicit <p>
# (type 6, block-level) is what actually puts one card per line.
PROJECT_LINKS = "\n\n".join(
    f'<p align="center"><a href="{project["url"]}">'
    f'<img src="assets/cards/project_{idx}.svg" width="{PROJECT_W}" '
    f'alt="{project["name"]} — {as_sentence(project["desc"])} Status: {project["status"]}.">'
    f'</a></p>'
    for idx, project in enumerate(profile["featured_projects"])
)

# ----------------- README.md Generator -----------------

readme_template = f"""<!-- Profile banner -->
<p align="center"><img src="assets/cards/header.svg" width="{HEADER_W}" alt="{ALT_TEXT["header"]}"></p>

<!-- At a glance: education, location, what I'm open to, how to reach me.
     Two per row: four 200px cards need 836px and the profile column is narrower
     than that on laptops and in print, so one row of four wrapped 3 + 1. -->
<p align="center"><img src="assets/cards/info_1.svg" width="{INFO_W}" alt="{ALT_TEXT["info_1"]}"> <img src="assets/cards/info_2.svg" width="{INFO_W}" alt="{ALT_TEXT["info_2"]}"></p>

<p align="center"><img src="assets/cards/info_3.svg" width="{INFO_W}" alt="{ALT_TEXT["info_3"]}"> <img src="assets/cards/info_4.svg" width="{INFO_W}" alt="{ALT_TEXT["info_4"]}"></p>

<!-- About and the two actions -->
<p align="center"><img src="assets/cards/about_me.svg" width="{ABOUT_W}" alt="{ALT_TEXT["about_me"]}"></p>

<p align="center"><a href="mailto:{profile["about_me"]["email"]}"><img src="assets/cards/btn_email.svg" width="{BTN_W}" alt="{ALT_TEXT["btn_email"]}"></a> <a href="{profile["about_me"]["resume_url"]}"><img src="assets/cards/btn_resume.svg" width="{BTN_W}" alt="{ALT_TEXT["btn_resume"]}"></a></p>

<!-- Stack, principles, current work, what I build -->
<p align="center"><img src="assets/cards/tech_stack.svg" width="{TECH_W}" alt="{ALT_TEXT["tech_stack"]}"></p>

<p align="center"><img src="assets/cards/principles.svg" width="{PRINCIPLES_W}" alt="{ALT_TEXT["principles"]}"></p>

<p align="center"><img src="assets/cards/currently_building.svg" width="{BUILD_W}" alt="{ALT_TEXT["currently_building"]}"></p>

<p align="center"><img src="assets/cards/what_i_build.svg" width="{WHAT_W}" alt="{ALT_TEXT["what_i_build"]}"></p>

<h2 align="center">🚀 Featured Projects</h2>

{PROJECT_LINKS}

<p align="center"><a href="https://github.com/{GITHUB_USER}?tab=repositories">View all repositories ➔</a></p>

<h2 align="center">📊 GitHub Analytics</h2>

<p align="center"><img src="assets/cards/gh_stats.svg" width="{GH_STATS[0]}" alt="{ALT_TEXT["stats"]}"></p>

<p align="center"><img src="assets/cards/gh_langs.svg" width="{GH_LANGS[0]}" alt="{ALT_TEXT["top_langs"]}"></p>

<p align="center"><a href="{GITHUB_URL}"><img src="https://streak-stats.demolab.com?user={GITHUB_USER}&amp;theme=default&amp;background=fffdfa&amp;border=e5dacf&amp;stroke=b05a30&amp;ring=b05a30&amp;fire=b05a30&amp;currStreakNum=2c1e1e&amp;sideNums=3c2f2f&amp;sideLabels=7a6a65&amp;dates=9c8b86&amp;border_radius=8" width="{WHAT_W}" alt="{ALT_TEXT["streak"]}"></a></p>

<p align="center"><img src="profile-3d-contrib/profile-south-season-animate.svg" width="{WHAT_W}" alt="{ALT_TEXT["contrib_3d"]}"></p>

<!-- Upcoming work, and where to find me -->
<p align="center"><img src="assets/cards/upcoming_projects.svg" width="{UPCOMING_W}" alt="{ALT_TEXT["upcoming_projects"]}"></p>

<p align="center"><a href="{GITHUB_URL}"><img src="assets/cards/icon_github.svg" width="{ICON_W}" alt="GitHub — {GITHUB_USER}"></a> <a href="{profile["about_me"]["linkedin_url"]}"><img src="assets/cards/icon_linkedin.svg" width="{ICON_W}" alt="LinkedIn — {profile["name"]}"></a> <a href="mailto:{profile["about_me"]["email"]}"><img src="assets/cards/icon_email.svg" width="{ICON_W}" alt="{ALT_TEXT["btn_email"]}"></a></p>

<p align="center"><img src="assets/cards/footer.svg" width="{FOOTER_W}" alt="{ALT_TEXT["footer"]}"></p>
"""

# Write compiled output to README.md
README_MD = os.path.join(WORKSPACE_DIR, "README.md")
with open(README_MD, "w", encoding="utf-8") as rf:
    rf.write(readme_template)

print("SUCCESS: Config compiled, cards written, and README.md generated!")
