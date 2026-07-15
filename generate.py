import os
import json
import base64
import re
import urllib.request

# Fetch LinkedIn Icon and base64-encode it
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
                b64_data = base64.b64encode(svg_str.encode('utf-8')).decode('utf-8')
                return f"data:image/svg+xml;base64,{b64_data}"
    except Exception as e:
        print(f"Error fetching LinkedIn icon: {e}")
    return ""

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
save_svg("header.svg", 850, 380, header_content)

# ----------------- 2. Info Cards (Separate SVGs) -----------------
# Card 1: Graduation
save_svg("info_1.svg", 200, 95, f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: 95px;
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
save_svg("info_2.svg", 200, 95, f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: 95px;
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
save_svg("info_3.svg", 200, 95, f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: 95px;
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
save_svg("info_4.svg", 200, 95, f"""
<style>
  .info-box {{
    background-color: #fffdfa;
    border: 1px solid #e5dacf;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    height: 95px;
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
save_svg("about_me.svg", 290, 380, about_me_content)

# ----------------- 4. Action Buttons -----------------
save_svg("btn_email.svg", 138, 40, """
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

save_svg("btn_resume.svg", 138, 40, """
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
save_svg("tech_stack.svg", 290, 540, tech_stack_content)

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
save_svg("principles.svg", 290, 320, principles_content)

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
save_svg("currently_building.svg", 290, 270, currently_building_content)

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
<div class="card" style="height: 330px; box-sizing: border-box;">
  <h2 class="card-title">💻 What I Build</h2>
  <div class="what-grid">
    {"".join(what_items)}
  </div>
</div>
"""
save_svg("what_i_build.svg", 510, 330, what_i_build_content)

# ----------------- 9. Featured Projects (Separate Clickable Cards) -----------------
project_icons = [
    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="6" y1="9" x2="6" y2="15"/><line x1="9" y1="6" x2="15" y2="6"/><line x1="9" y1="18" x2="15" y2="18"/><line x1="18" y1="9" x2="18" y2="15"/>',
    '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
]

for idx, project in enumerate(profile["featured_projects"]):
    badge_cls = "badge-production" if project["status"] == "Production" else "badge-inprogress"
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
        height: 190px;
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
    save_svg(f"project_{idx}.svg", 510, 190, project_card_content)

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
save_svg("upcoming_projects.svg", 510, 210, upcoming_content)

# ----------------- 11. Social & Connect Buttons -----------------
save_svg("icon_github.svg", 110, 32, f"""
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

save_svg("icon_linkedin.svg", 110, 32, f"""
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

save_svg("icon_email.svg", 110, 32, """
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
save_svg("footer.svg", 850, 110, """
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

# ----------------- README.md Generator -----------------

readme_template = f"""<!-- CUSTOM THEME HEADER BANNER -->
<div align="center">
  <img src="assets/cards/header.svg" width="850" alt="Hi, I'm Ayush!" />
</div>
<!-- INFO BAR CARD ROW -->
<table width="850" border="0" cellpadding="0" cellspacing="0" align="center" style="margin-top: 15px; margin-bottom: 15px;">
  <tr>
    <td width="200" align="center"><img src="assets/cards/info_1.svg" width="200" height="95" /></td>
    <td width="16">&nbsp;</td>
    <td width="200" align="center"><img src="assets/cards/info_2.svg" width="200" height="95" /></td>
    <td width="16">&nbsp;</td>
    <td width="200" align="center"><img src="assets/cards/info_3.svg" width="200" height="95" /></td>
    <td width="16">&nbsp;</td>
    <td width="200" align="center"><img src="assets/cards/info_4.svg" width="200" height="95" /></td>
  </tr>
</table>
<!-- MAIN GRID (LEFT & RIGHT COLUMNS) -->
<table width="850" border="0" cellpadding="0" cellspacing="0" align="center">
  <tr>
    <!-- LEFT COLUMN (About, Stack, Principles, Progress) -->
    <td width="300" valign="top">
      <img src="assets/cards/about_me.svg" width="290" height="380" style="display: block; margin-bottom: 10px;" />
      <!-- Clickable Action Buttons -->
      <table width="290" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 15px;">
        <tr>
          <td width="138" align="center">
            <a href="mailto:{profile["about_me"]["email"]}">
              <img src="assets/cards/btn_email.svg" width="138" height="40" alt="Email Me" />
            </a>
          </td>
          <td width="14">&nbsp;</td>
          <td width="138" align="center">
            <a href="{profile["about_me"]["resume_url"]}">
              <img src="assets/cards/btn_resume.svg" width="138" height="40" alt="Resume" />
            </a>
          </td>
        </tr>
      </table>
      <img src="assets/cards/tech_stack.svg" width="290" height="540" style="display: block; margin-bottom: 15px;" />
      <img src="assets/cards/principles.svg" width="290" height="320" style="display: block; margin-bottom: 15px;" />
      <img src="assets/cards/currently_building.svg" width="290" height="330" style="display: block;" />
    </td>
    <!-- GRID SPACER -->
    <td width="30">&nbsp;</td>
    <!-- RIGHT COLUMN (What I Build, Featured Projects, Analytics, Upcoming) -->
    <td width="520" valign="top">
      <img src="assets/cards/what_i_build.svg" width="510" height="320" style="display: block; margin-bottom: 15px;" />
      <!-- Featured Projects (Fully Clickable) -->
      <h3 style="font-family: 'Outfit', sans-serif; color: #2c1e1e; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 10px; padding: 0;">🚀 Featured Projects</h3>
      {"".join([f'''<a href="{project["url"]}"><img src="assets/cards/project_{idx}.svg" width="510" height="190" style="display: block; margin-bottom: 10px;" alt="{project["name"]}" /></a>''' for idx, project in enumerate(profile["featured_projects"])])}
      <table width="510" border="0" cellpadding="0" cellspacing="0" style="margin-top: 5px; margin-bottom: 20px;">
        <tr>
          <td align="right">
            <a href="https://github.com/{profile["about_me"]["github_url"].split('/')[-1]}?tab=repositories" style="color: #b05a30; font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; text-decoration: none;">
              View all repositories ➔
            </a>
          </td>
        </tr>
      </table>
      <!-- Live Styled GitHub Analytics -->
      <h3 style="font-family: 'Outfit', sans-serif; color: #2c1e1e; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 10px; padding: 0;">📊 GitHub Analytics</h3>
      <table width="510" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 15px;">
        <tr>
          <td width="250" valign="top">
            <a href="{profile["about_me"]["github_url"]}">
              <img src="https://github-readme-stats.vercel.app/api?username={profile["about_me"]["github_url"].split('/')[-1]}&amp;show_icons=true&amp;theme=default&amp;bg_color=fffdfa&amp;border_color=e5dacf&amp;title_color=2c1e1e&amp;text_color=3c2f2f&amp;icon_color=b05a30&amp;border_radius=8" width="250" height="170" alt="GitHub Stats" />
            </a>
          </td>
          <td width="10">&nbsp;</td>
          <td width="250" valign="top">
            <a href="{profile["about_me"]["github_url"]}">
              <img src="https://github-readme-stats.vercel.app/api/top-langs/?username={profile["about_me"]["github_url"].split('/')[-1]}&amp;layout=compact&amp;theme=default&amp;bg_color=fffdfa&amp;border_color=e5dacf&amp;title_color=2c1e1e&amp;text_color=3c2f2f&amp;icon_color=b05a30&amp;border_radius=8" width="250" height="170" alt="Top Languages" />
            </a>
          </td>
        </tr>
        <tr>
          <td colspan="3" style="padding-top: 10px;">
            <a href="{profile["about_me"]["github_url"]}">
              <img src="https://streak-stats.demolab.com?user={profile["about_me"]["github_url"].split('/')[-1]}&amp;theme=default&amp;background=fffdfa&amp;border=e5dacf&amp;stroke=b05a30&amp;ring=b05a30&amp;fire=b05a30&amp;currStreakNum=2c1e1e&amp;sideNums=3c2f2f&amp;sideLabels=7a6a65&amp;dates=9c8b86&amp;border_radius=8" width="510" height="330" alt="Streak Stats" />
            </a>
          </td>
        </tr>
        <tr>
          <td colspan="3" style="padding-top: 10px;" align="center">
            <img src="./profile-3d-contrib/profile-south-season-animate.svg" width="450" alt="3D Contributions Graph" />
          </td>
        </tr>
      </table>
      <img src="assets/cards/upcoming_projects.svg" width="510" height="210" style="display: block; margin-bottom: 15px;" />
      <!-- Clickable Connect Social Icons -->
      <table width="510" border="0" cellpadding="0" cellspacing="0" style="margin-top: 10px;">
        <tr>
          <td width="110">
            <a href="{profile["about_me"]["github_url"]}">
              <img src="assets/cards/icon_github.svg" width="110" height="32" alt="GitHub" />
            </a>
          </td>
          <td width="90">&nbsp;</td>
          <td width="110">
            <a href="{profile["about_me"]["linkedin_url"]}">
              <img src="assets/cards/icon_linkedin.svg" width="110" height="32" alt="LinkedIn" />
            </a>
          </td>
          <td width="90">&nbsp;</td>
          <td width="110">
            <a href="mailto:{profile["about_me"]["email"]}">
              <img src="assets/cards/icon_email.svg" width="110" height="32" alt="Email" />
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
<!-- FOOTER DECORATIVE BAR AND STICKY NOTE -->
<div align="center" style="margin-top: 20px;">
  <img src="assets/cards/footer.svg" width="850" height="110" alt="Footer Banner" />
</div>
"""

# Write compiled output to README.md
README_MD = os.path.join(WORKSPACE_DIR, "README.md")
with open(README_MD, "w", encoding="utf-8") as rf:
    rf.write(readme_template)

print("SUCCESS: Config compiled, cards written, and README.md generated!")
