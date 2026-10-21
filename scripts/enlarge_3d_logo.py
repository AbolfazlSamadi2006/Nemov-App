import pathlib

p = pathlib.Path('nemov_cloud_server/cloudflare_worker/index.js')
content = p.read_text(encoding='utf-8')

# 1. Update ETag
content = content.replace(
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.2-nemov-server-label"\';',
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.3-nemov-enlarged-logo"\';'
)

# 2. Update CSS for 3D logo
old_logo_css = """        /* 3D Continuous Rotating Nemov Logo (Strictly Never Stops on Hover) */
        .hero-logo-3d-wrapper {
            perspective: 800px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px auto;
            width: 82px;
            height: 82px;
            position: relative;
        }

        .hero-logo-3d {
            width: 76px;
            height: 76px;
            object-fit: contain;
            transform-style: preserve-3d;
            animation: rotateLogo3D 8s linear infinite !important;
            filter: drop-shadow(0 0 18px rgba(220, 38, 38, 0.55));
            will-change: transform;
            cursor: pointer;
        }

        .hero-logo-3d:hover {
            animation-play-state: running !important;
            filter: drop-shadow(0 0 28px rgba(239, 68, 68, 0.85));
        }

        @keyframes rotateLogo3D {
            0% {
                transform: perspective(800px) rotateY(0deg);
            }
            100% {
                transform: perspective(800px) rotateY(360deg);
            }
        }"""

new_logo_css = """        /* 3D Continuous Rotating Nemov Logo (Strictly Never Stops on Hover - Prominent Display) */
        .hero-logo-3d-wrapper {
            perspective: 1000px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px auto;
            width: 140px;
            height: 140px;
            position: relative;
        }

        .hero-logo-3d {
            width: 130px;
            height: 130px;
            object-fit: contain;
            transform-style: preserve-3d;
            animation: rotateLogo3D 8s linear infinite !important;
            filter: drop-shadow(0 0 26px rgba(220, 38, 38, 0.65)) drop-shadow(0 8px 18px rgba(0, 0, 0, 0.75));
            will-change: transform;
            cursor: pointer;
            transition: filter 0.3s ease;
        }

        .hero-logo-3d:hover {
            animation-play-state: running !important;
            filter: drop-shadow(0 0 38px rgba(239, 68, 68, 0.95)) drop-shadow(0 10px 22px rgba(0, 0, 0, 0.85));
        }

        @keyframes rotateLogo3D {
            0% {
                transform: perspective(1000px) rotateY(0deg);
            }
            100% {
                transform: perspective(1000px) rotateY(360deg);
            }
        }"""

if old_logo_css not in content:
    print("ERROR: old_logo_css not found")
    exit(1)
content = content.replace(old_logo_css, new_logo_css, 1)

# 3. Update HTML width and height attributes
old_html_logo = '<img src="/images/nemov_logo.png" alt="لوگوی سه‌بعدی چرخان نرم‌افزار مدیریت ورزشی نِمُو" class="hero-logo-3d" width="76" height="76">'
new_html_logo = '<img src="/images/nemov_logo.png" alt="لوگوی سه‌بعدی چرخان نرم‌افزار مدیریت ورزشی نِمُو" class="hero-logo-3d" width="130" height="130">'

if old_html_logo not in content:
    print("ERROR: old_html_logo not found")
    exit(1)
content = content.replace(old_html_logo, new_html_logo, 1)

# 4. Mobile responsive sizing in @media (max-width: 640px)
old_mobile = ".hero { padding: 35px 10px 24px; }"
new_mobile = """.hero { padding: 35px 10px 24px; }
            .hero-logo-3d-wrapper { width: 95px; height: 95px; margin: 0 auto 14px auto; }
            .hero-logo-3d { width: 88px; height: 88px; }"""

if old_mobile in content:
    content = content.replace(old_mobile, new_mobile, 1)

p.write_text(content, encoding='utf-8')
print("SUCCESS: Updated 3D rotating logo to larger prominent size!")
