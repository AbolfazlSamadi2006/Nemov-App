import pathlib

p = pathlib.Path('yalda_cloud_server/cloudflare_worker/index.js')
content = p.read_text(encoding='utf-8')

# Ensure marquee track and group have max-width: none !important
content = content.replace(
    '.marquee-track {\n            display: flex !important;',
    '.marquee-track {\n            max-width: none !important;\n            display: flex !important;'
)
content = content.replace(
    '.marquee-group {\n            display: flex !important;',
    '.marquee-group {\n            max-width: none !important;\n            display: flex !important;'
)
content = content.replace(
    '.marquee-card {\n            direction: rtl;\n            display: inline-flex !important;',
    '.marquee-card {\n            direction: rtl;\n            max-width: none !important;\n            display: inline-flex !important;'
)

# Navbar mobile refinement
old_mobile_nav = """        @media (max-width: 640px) {
            .navbar { padding: 10px 12px; }
            .nav-container { gap: 8px; }
            .brand-logo-img { width: 34px; height: 34px; border-radius: 8px; }
            .brand-icon-box { width: 32px; height: 32px; font-size: 15px; border-radius: 8px; }
            .brand-title { font-size: 13px; max-width: 175px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .brand-subtitle { display: none; }
            .nav-cta { padding: 6px 10px; font-size: 11px; gap: 4px; border-radius: 8px; }"""

new_mobile_nav = """        @media (max-width: 640px) {
            .navbar { padding: 8px 10px; }
            .nav-container { gap: 6px; }
            .nav-brand { min-width: 0; flex-shrink: 1; gap: 6px; }
            .brand-logo-img { width: 30px; height: 30px; border-radius: 6px; }
            .brand-icon-box { width: 28px; height: 28px; font-size: 14px; border-radius: 6px; }
            .brand-text-box { min-width: 0; }
            .brand-title { font-size: 12px; max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .brand-subtitle { display: none; }
            .nav-cta { padding: 6px 9px; font-size: 11px; gap: 3px; border-radius: 8px; flex-shrink: 0; }"""

if old_mobile_nav in content:
    content = content.replace(old_mobile_nav, new_mobile_nav)
    print("Replaced mobile nav styles.")
else:
    print("WARNING: old_mobile_nav not found")

p.write_text(content, encoding='utf-8')
print("Successfully refined index.js")
