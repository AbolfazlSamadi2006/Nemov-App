import pathlib

p = pathlib.Path('yalda_cloud_server/cloudflare_worker/index.js')
content = p.read_text(encoding='utf-8')

# 1. Update hero-logo-3d-wrapper to display: flex
old_wrapper = """.hero-logo-3d-wrapper {
            perspective: 800px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            width: 82px;
            height: 82px;
            position: relative;
        }"""

new_wrapper = """.hero-logo-3d-wrapper {
            perspective: 800px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px auto;
            width: 82px;
            height: 82px;
            position: relative;
        }"""
content = content.replace(old_wrapper, new_wrapper)

# 2. Adjust @media (max-width: 900px) to @media (max-width: 768px)
old_media = """        @media (max-width: 900px) {
            .window-content-grid { grid-template-columns: 1fr; }
            .mock-sidebar { display: none; }
            .floating-glass-widget { display: none; }
            .mockup-perspective-wrapper {
                transform: rotateX(2deg) rotateY(0deg) !important;
                animation: none;
            }
        }"""

new_media = """        @media (max-width: 768px) {
            .window-content-grid { grid-template-columns: 1fr; }
            .mock-sidebar { display: none; }
            .floating-glass-widget { display: none; }
            .mockup-perspective-wrapper {
                transform: rotateX(2deg) rotateY(0deg) !important;
                animation: none;
            }
        }"""
content = content.replace(old_media, new_media)

# 3. Mobile brand title sizing
old_brand_title = ".brand-title { font-size: 14.5px; }"
new_brand_title = ".brand-title { font-size: 13px; max-width: 175px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }"
content = content.replace(old_brand_title, new_brand_title)

p.write_text(content, encoding='utf-8')
print("Updated wrapper, media query, and mobile brand title.")
