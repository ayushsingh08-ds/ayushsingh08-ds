import os

generate_py = r"c:\Users\AYUSH SINGH\Documents\GitHub\ayushsingh08-ds\generate.py"

with open(generate_py, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Card Title font size in COMMON_CSS (originally 15px)
content = content.replace(".card-title {\n  font-size: 15px;", ".card-title {\n  font-size: 18px;")
content = content.replace(".card-title {\r\n  font-size: 15px;", ".card-title {\r\n  font-size: 18px;")

# 2. Update Info Cards
# Change save_svg call heights from 80 to 95
for i in [1, 2, 3, 4]:
    content = content.replace(f'save_svg("info_{i}.svg", 200, 80,', f'save_svg("info_{i}.svg", 200, 95,')
    content = content.replace(f'save_svg("info_{i}.svg", 200, 85,', f'save_svg("info_{i}.svg", 200, 95,')

# Change height property in styles from 80px or 85px to 95px
content = content.replace("height: 80px;\n    box-sizing: border-box;", "height: 95px;\n    box-sizing: border-box;")
content = content.replace("height: 80px;\r\n    box-sizing: border-box;", "height: 95px;\r\n    box-sizing: border-box;")
content = content.replace("height: 85px;\n    box-sizing: border-box;", "height: 95px;\n    box-sizing: border-box;")
content = content.replace("height: 85px;\r\n    box-sizing: border-box;", "height: 95px;\r\n    box-sizing: border-box;")

# Change icon size and font sizes inside info box styles
content = content.replace(".info-icon { width: 20px; height: 20px;", ".info-icon { width: 25px; height: 25px;")
content = content.replace(".info-icon { width: 22px; height: 22px;", ".info-icon { width: 25px; height: 25px;")
content = content.replace(".info-title { font-size: 11px;", ".info-title { font-size: 14px;")
content = content.replace(".info-title { font-size: 12px;", ".info-title { font-size: 14px;")
content = content.replace(".info-detail { font-size: 9px;", ".info-detail { font-size: 12px;")
content = content.replace(".info-detail { font-size: 10px;", ".info-detail { font-size: 12px;")

# 3. About Me Card
# Change save_svg call height from 310 to 380
content = content.replace('save_svg("about_me.svg", 290, 310, about_me_content)', 'save_svg("about_me.svg", 290, 380, about_me_content)')
content = content.replace('save_svg("about_me.svg", 290, 340, about_me_content)', 'save_svg("about_me.svg", 290, 380, about_me_content)')

# Change font sizes
content = content.replace(".about-text { font-size: 12px;", ".about-text { font-size: 15px;")
content = content.replace(".about-text { font-size: 13.5px;", ".about-text { font-size: 15px;")
content = content.replace(".about-list li { font-size: 11px;", ".about-list li { font-size: 14px;")
content = content.replace(".about-list li { font-size: 12.5px;", ".about-list li { font-size: 14px;")

# 4. Action Buttons
# Change save_svg call height from 35 to 40
content = content.replace('save_svg("btn_email.svg", 138, 35,', 'save_svg("btn_email.svg", 138, 40,')
content = content.replace('save_svg("btn_resume.svg", 138, 35,', 'save_svg("btn_resume.svg", 138, 40,')

# Change height and font size inside style blocks
content = content.replace("width: 138px;\n    height: 35px;\n    background-color: #3c2f2f;\n    color: #fffdfa;\n    border-radius: 6px;\n    font-size: 11px;", "width: 138px;\n    height: 40px;\n    background-color: #3c2f2f;\n    color: #fffdfa;\n    border-radius: 6px;\n    font-size: 14px;")
content = content.replace("width: 138px;\r\n    height: 35px;\r\n    background-color: #3c2f2f;\r\n    color: #fffdfa;\r\n    border-radius: 6px;\r\n    font-size: 11px;", "width: 138px;\r\n    height: 40px;\r\n    background-color: #3c2f2f;\r\n    color: #fffdfa;\r\n    border-radius: 6px;\r\n    font-size: 14px;")
content = content.replace("width: 138px;\n    height: 35px;\n    background-color: #3c2f2f;\n    color: #fffdfa;\n    border-radius: 6px;\n    font-size: 12px;", "width: 138px;\n    height: 40px;\n    background-color: #3c2f2f;\n    color: #fffdfa;\n    border-radius: 6px;\n    font-size: 14px;")
content = content.replace("width: 138px;\r\n    height: 35px;\r\n    background-color: #3c2f2f;\r\n    color: #fffdfa;\r\n    border-radius: 6px;\r\n    font-size: 12px;", "width: 138px;\r\n    height: 40px;\r\n    background-color: #3c2f2f;\r\n    color: #fffdfa;\r\n    border-radius: 6px;\r\n    font-size: 14px;")

content = content.replace("width: 138px;\n    height: 35px;\n    background-color: transparent;\n    border: 1px solid #3c2f2f;\n    color: #3c2f2f;\n    border-radius: 6px;\n    font-size: 11px;", "width: 138px;\n    height: 40px;\n    background-color: transparent;\n    border: 1px solid #3c2f2f;\n    color: #3c2f2f;\n    border-radius: 6px;\n    font-size: 14px;")
content = content.replace("width: 138px;\r\n    height: 35px;\r\n    background-color: transparent;\r\n    border: 1px solid #3c2f2f;\r\n    color: #3c2f2f;\r\n    border-radius: 6px;\r\n    font-size: 11px;", "width: 138px;\r\n    height: 40px;\r\n    background-color: transparent;\r\n    border: 1px solid #3c2f2f;\r\n    color: #3c2f2f;\r\n    border-radius: 6px;\r\n    font-size: 14px;")
content = content.replace("width: 138px;\n    height: 35px;\n    background-color: transparent;\n    border: 1px solid #3c2f2f;\n    color: #3c2f2f;\n    border-radius: 6px;\n    font-size: 12px;", "width: 138px;\n    height: 40px;\n    background-color: transparent;\n    border: 1px solid #3c2f2f;\n    color: #3c2f2f;\n    border-radius: 6px;\n    font-size: 14px;")
content = content.replace("width: 138px;\r\n    height: 35px;\r\n    background-color: transparent;\r\n    border: 1px solid #3c2f2f;\r\n    color: #3c2f2f;\r\n    border-radius: 6px;\r\n    font-size: 12px;", "width: 138px;\r\n    height: 40px;\r\n    background-color: transparent;\r\n    border: 1px solid #3c2f2f;\r\n    color: #3c2f2f;\r\n    border-radius: 6px;\r\n    font-size: 14px;")

content = content.replace(".btn svg { width: 12px; height: 12px; }", ".btn svg { width: 14px; height: 14px; }")

# 5. Tech Stack Card
content = content.replace('save_svg("tech_stack.svg", 290, 440, tech_stack_content)', 'save_svg("tech_stack.svg", 290, 540, tech_stack_content)')
content = content.replace('save_svg("tech_stack.svg", 290, 480, tech_stack_content)', 'save_svg("tech_stack.svg", 290, 540, tech_stack_content)')
content = content.replace(".tech-label { font-size: 10px;", ".tech-label { font-size: 13px;")
content = content.replace(".tech-label { font-size: 11px;", ".tech-label { font-size: 13px;")
content = content.replace(".tech-icon { width: 24px; height: 24px;", ".tech-icon { width: 30px; height: 30px;")
content = content.replace(".tech-icon { width: 26px; height: 26px;", ".tech-icon { width: 30px; height: 30px;")

# 6. Principles Card
content = content.replace('save_svg("principles.svg", 290, 260, principles_content)', 'save_svg("principles.svg", 290, 320, principles_content)')
content = content.replace('save_svg("principles.svg", 290, 290, principles_content)', 'save_svg("principles.svg", 290, 320, principles_content)')
content = content.replace(".principle-item span { font-size: 12px;", ".principle-item span { font-size: 15px;")
content = content.replace(".principle-item span { font-size: 13px;", ".principle-item span { font-size: 15px;")

# 7. Currently Building Card
content = content.replace('save_svg("currently_building.svg", 290, 220, currently_building_content)', 'save_svg("currently_building.svg", 290, 270, currently_building_content)')
content = content.replace('save_svg("currently_building.svg", 290, 240, currently_building_content)', 'save_svg("currently_building.svg", 290, 270, currently_building_content)')
content = content.replace(".progress-header { display: flex; justify-content: space-between; font-size: 11px;", ".progress-header { display: flex; justify-content: space-between; font-size: 14px;")
content = content.replace(".progress-header { display: flex; justify-content: space-between; font-size: 12.5px;", ".progress-header { display: flex; justify-content: space-between; font-size: 14px;")

# 8. What I Build Card (Increase height to 330, reduce paddings to fit 14px title and 12.5px desc)
content = content.replace('save_svg("what_i_build.svg", 510, 200, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')
content = content.replace('save_svg("what_i_build.svg", 510, 240, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')
content = content.replace('save_svg("what_i_build.svg", 510, 290, what_i_build_content)', 'save_svg("what_i_build.svg", 510, 330, what_i_build_content)')

# Style rules in what_i_build_content
content = content.replace(".what-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }", ".what-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }")
content = content.replace(".what-card { background-color: #fffdfa; border: 1px solid #e5dacf; border-radius: 8px; padding: 12px; }", ".what-card { background-color: #fffdfa; border: 1px solid #e5dacf; border-radius: 8px; padding: 8px; }")
content = content.replace(".what-title { font-size: 11px;", ".what-title { font-size: 14.5px;")
content = content.replace(".what-title { font-size: 13px;", ".what-title { font-size: 14.5px;")
content = content.replace(".what-desc { font-size: 9.5px;", ".what-desc { font-size: 12.5px;")
content = content.replace(".what-desc { font-size: 11.5px;", ".what-desc { font-size: 12.5px;")

# 9. Featured Projects
for old_h in [135, 160]:
    content = content.replace(f'save_svg(f"project_{{idx}}.svg", 510, {old_h}, project_card_content)', 'save_svg(f"project_{idx}.svg", 510, 190, project_card_content)')
    content = content.replace(f"height: {old_h}px;", "height: 190px;")

content = content.replace(".project-name { font-size: 12.5px;", ".project-name { font-size: 16px;")
content = content.replace(".project-name { font-size: 14px;", ".project-name { font-size: 16px;")
content = content.replace(".project-desc { font-size: 11px;", ".project-desc { font-size: 14px;")
content = content.replace(".project-desc { font-size: 12px;", ".project-desc { font-size: 14px;")
content = content.replace(".project-tags span { font-family: 'Courier Prime', monospace; font-size: 9.5px;", ".project-tags span { font-family: 'Courier Prime', monospace; font-size: 12px;")
content = content.replace(".project-tags span { font-family: 'Courier Prime', monospace; font-size: 10px;", ".project-tags span { font-family: 'Courier Prime', monospace; font-size: 12px;")

# 10. Upcoming Projects
content = content.replace('save_svg("upcoming_projects.svg", 510, 160, upcoming_content)', 'save_svg("upcoming_projects.svg", 510, 210, upcoming_content)')
content = content.replace('save_svg("upcoming_projects.svg", 510, 180, upcoming_content)', 'save_svg("upcoming_projects.svg", 510, 210, upcoming_content)')
content = content.replace(".upcoming-list li strong { font-size: 12px;", ".upcoming-list li strong { font-size: 15px;")
content = content.replace(".upcoming-list li strong { font-size: 13.5px;", ".upcoming-list li strong { font-size: 15px;")
content = content.replace(".upcoming-sub { font-size: 10px;", ".upcoming-sub { font-size: 13px;")
content = content.replace(".upcoming-sub { font-size: 11.5px;", ".upcoming-sub { font-size: 13px;")

# 11. README template image element heights
content = content.replace('height="80"', 'height="95"')
content = content.replace('height="85"', 'height="95"')
content = content.replace('height="310"', 'height="380"')
content = content.replace('height="340"', 'height="380"')
content = content.replace('height="35"', 'height="40"')
content = content.replace('height="440"', 'height="540"')
content = content.replace('height="480"', 'height="540"')
content = content.replace('height="260"', 'height="320"')
content = content.replace('height="290"', 'height="320"')
content = content.replace('height="220"', 'height="270"')
content = content.replace('height="240"', 'height="270"')

# what_i_build image height in README.md should be 330
content = content.replace('assets/cards/what_i_build.svg" width="510" height="200"', 'assets/cards/what_i_build.svg" width="510" height="330"')
content = content.replace('assets/cards/what_i_build.svg" width="510" height="240"', 'assets/cards/what_i_build.svg" width="510" height="330"')
content = content.replace('assets/cards/what_i_build.svg" width="510" height="270"', 'assets/cards/what_i_build.svg" width="510" height="330"')
content = content.replace('assets/cards/what_i_build.svg" width="510" height="290"', 'assets/cards/what_i_build.svg" width="510" height="330"')

# project_idx image height in README.md should be 190
content = content.replace('project_{idx}.svg" width="510" height="135"', 'project_{idx}.svg" width="510" height="190"')
content = content.replace('project_{idx}.svg" width="510" height="160"', 'project_{idx}.svg" width="510" height="190"')
content = content.replace('project_{idx}.svg" width="510" height="210"', 'project_{idx}.svg" width="510" height="190"')

# upcoming_projects image height in README.md should be 210
content = content.replace('upcoming_projects.svg" width="510" height="160"', 'upcoming_projects.svg" width="510" height="210"')
content = content.replace('upcoming_projects.svg" width="510" height="180"', 'upcoming_projects.svg" width="510" height="210"')

with open(generate_py, "w", encoding="utf-8") as f:
    f.write(content)

print("Modification complete!")
