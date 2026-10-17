import pathlib
import re
import subprocess
import os

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ARTIFACTS_DIR = pathlib.Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")

worker_js = pathlib.Path("yalda_cloud_server/cloudflare_worker/index.js").read_text(encoding="utf-8")

# Extract base64 constants
nemov_match = re.search(r'const NEMOV_LOGO_BASE64 = "(.*?)";', worker_js, re.DOTALL)
nemov_b64 = nemov_match.group(1).replace("\n", "").replace("\r", "") if nemov_match else ""

yalda_match = re.search(r'const YALDA_LOGO_BASE64 = "(.*?)";', worker_js, re.DOTALL)
yalda_b64 = yalda_match.group(1).replace("\n", "").replace("\r", "") if yalda_match else ""

dev_match = re.search(r'const DEVELOPER_PHOTO_BASE64 = "(.*?)";', worker_js, re.DOTALL)
dev_b64 = dev_match.group(1).replace("\n", "").replace("\r", "") if dev_match else ""

# Extract renderLandingPage() HTML template
render_match = re.search(r'function renderLandingPage\(\) \{\s*return `(.*?)`;\s*\}', worker_js, re.DOTALL)
if not render_match:
    print("ERROR: could not extract renderLandingPage HTML")
    exit(1)

html_content = render_match.group(1)

# Substitute image paths with data URIs
html_content = html_content.replace('/images/nemov_logo.png', f'data:image/png;base64,{nemov_b64}')
html_content = html_content.replace('/images/yalda_logo.jpg', f'data:image/jpeg;base64,{yalda_b64}')
html_content = html_content.replace('/images/developer_photo.jpg', f'data:image/jpeg;base64,{dev_b64}')

temp_html = ARTIFACTS_DIR / "temp_landing.html"
temp_html.write_text(html_content, encoding="utf-8")
print(f"Wrote temporary HTML to {temp_html}")

# Viewport tests
viewports = [
    ("qa_landing_desktop_1440.png", 1440, 1100),
    ("qa_landing_desktop_1920.png", 1920, 1200),
    ("qa_landing_mobile_390.png", 390, 844),
]

for out_name, w, h in viewports:
    out_path = ARTIFACTS_DIR / out_name
    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={w},{h}",
        f"--screenshot={out_path}",
        str(temp_html.resolve())
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Generated {out_name} (exists={out_path.exists()}, size={out_path.stat().st_size if out_path.exists() else 0})")
