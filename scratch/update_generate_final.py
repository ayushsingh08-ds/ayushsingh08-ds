import os

generate_py = r"c:\Users\AYUSH SINGH\Documents\GitHub\ayushsingh08-ds\generate.py"

with open(generate_py, "r", encoding="utf-8") as f:
    content = f.read()

# Helper function to replace both LF and CRLF formats safely
def safe_replace(old, new):
    global content
    content = content.replace(old.replace("\n", "\r\n"), new.replace("\n", "\r\n"))
    content = content.replace(old, new)

# 1. Update Card Title font size in COMMON_CSS
safe_replace(".card-title {\n  font-size: 15px;", ".card-title {\n  font-size: 18px;")

# 2. Update Info Cards
safe_replace(".info-icon {{ width: 20px; height: 20px;", ".info-icon {{ width: 25px; height: 25px;")
safe_replace(".info-icon {{ width: 22px; height: 22px;", ".info-icon {{ width: 25px; height: 25px;")
safe_replace(".info-title {{ font-size: 11px;", ".info-title {{ font-size: 14px;")
safe_replace(".info-title {{ font-size: 12px;", ".info-title {{ font-size: 14px;")
safe_replace(".info-detail {{ font-size: 9px;", ".info-detail {{ font-size: 12px;")
safe_replace(".info-detail {{ font-size: 10px;", ".info-detail {{ font-size: 12px;")

# 3. About Me Card
safe_replace(".about-text {{ font-size: 12px;", ".about-text {{ font-size: 15.5px;")
safe_replace(".about-text {{ font-size: 13.5px;", ".about-text {{ font-size: 15.5px;")
safe_replace(".about-list li {{ font-size: 11px;", ".about-list li {{ font-size: 14px;")
safe_replace(".about-list li {{ font-size: 12.5px;", ".about-list li {{ font-size: 14px;")

# 4. Action Buttons
safe_replace("width: 138px;\n    height: 35px;\n    background-color: #3c2f2f;\n    color: #fffdfa;\n    border-radius: 6px;\n    font-size: 12px;", "width: 138px;\n    height: 40px;\n    background-color: #3c2f2f;\n    color: #fffdfa;\n    border-radius: 6px;\n    font-size: 14.5px;")
safe_replace("width: 138px;\n    height: 35px;\n    background-color: transparent;\n    border: 1px solid #3c2f2f;\n    color: #3c2f2f;\n    border-radius: 6px;\n    font-size: 12px;", "width: 138px;\n    height: 40px;\n    background-color: transparent;\n    border: 1px solid #3c2f2f;\n    color: #3c2f2f;\n    border-radius: 6px;\n    font-size: 14.5px;")
safe_replace(".btn svg { width: 12px; height: 12px; }", ".btn svg { width: 14px; height: 14px; }")

# 5. Tech Stack Card
safe_replace(".tech-label {{ font-size: 10px;", ".tech-label {{ font-size: 13px;")
safe_replace(".tech-label {{ font-size: 11px;", ".tech-label {{ font-size: 13px;")
safe_replace(".tech-icon {{ width: 24px; height: 24px;", ".tech-icon {{ width: 30px; height: 30px;")
safe_replace(".tech-icon {{ width: 26px; height: 26px;", ".tech-icon {{ width: 30px; height: 30px;")

# 6. Principles Card
safe_replace(".principle-item span {{ font-size: 12px;", ".principle-item span {{ font-size: 15.5px;")
safe_replace(".principle-item span {{ font-size: 13px;", ".principle-item span {{ font-size: 15.5px;")

# 7. Currently Building Card
safe_replace(".progress-header {{ display: flex; justify-content: space-between; font-size: 11px;", ".progress-header {{ display: flex; justify-content: space-between; font-size: 14px;")
safe_replace(".progress-header {{ display: flex; justify-content: space-between; font-size: 12.5px;", ".progress-header {{ display: flex; justify-content: space-between; font-size: 14px;")

# 8. What I Build Card (Set SVG height to 330)
safe_replace('save_svg("what_i_build.svg", 510, 200, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')
safe_replace('save_svg("what_i_build.svg", 510, 240, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')
safe_replace('save_svg("what_i_build.svg", 510, 270, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')
safe_replace('save_svg("what_i_build.svg", 510, 290, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')

# Style rules in what_i_build_content
safe_replace(".what-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}", ".what-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}")
safe_replace(".what-card {{ background-color: #fffdfa; border: 1px solid #e5dacf; border-radius: 8px; padding: 12px; }}", ".what-card {{ background-color: #fffdfa; border: 1px solid #e5dacf; border-radius: 8px; padding: 8px; }}")
safe_replace(".what-title {{ font-size: 11px;", ".what-title {{ font-size: 14.5px;")
safe_replace(".what-title {{ font-size: 13px;", ".what-title {{ font-size: 14.5px;")
safe_replace(".what-desc {{ font-size: 9.5px;", ".what-desc {{ font-size: 12.5px;")
safe_replace(".what-desc {{ font-size: 11.5px;", ".what-desc {{ font-size: 12.5px;")

# 9. Featured Projects
safe_replace(".project-name {{ font-size: 12.5px;", ".project-name {{ font-size: 16px;")
safe_replace(".project-name {{ font-size: 14px;", ".project-name {{ font-size: 16px;")
safe_replace(".project-desc {{ font-size: 11px;", ".project-desc {{ font-size: 14px;")
safe_replace(".project-desc {{ font-size: 12px;", ".project-desc {{ font-size: 14px;")
safe_replace(".project-tags span {{ font-family: 'Courier Prime', monospace; font-size: 9.5px;", ".project-tags span {{ font-family: 'Courier Prime', monospace; font-size: 12px;")
safe_replace(".project-tags span {{ font-family: 'Courier Prime', monospace; font-size: 10px;", ".project-tags span {{ font-family: 'Courier Prime', monospace; font-size: 12px;")

# 10. Upcoming Projects
safe_replace(".upcoming-list li strong {{ font-size: 12px;", ".upcoming-list li strong {{ font-size: 15px;")
safe_replace(".upcoming-list li strong {{ font-size: 13.5px;", ".upcoming-list li strong {{ font-size: 15px;")
safe_replace(".upcoming-sub {{ font-size: 10px;", ".upcoming-sub {{ font-size: 13px;")
safe_replace(".upcoming-sub {{ font-size: 11.5px;", ".upcoming-sub {{ font-size: 13px;")

# 11. README template image element heights
safe_replace('height="290"', 'height="330"')
safe_replace('height="270"', 'height="330"')

with open(generate_py, "w", encoding="utf-8") as f:
    f.write(content)

print("Modification complete!")
