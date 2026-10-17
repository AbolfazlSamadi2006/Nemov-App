import pathlib
import io
import base64
import re
from PIL import Image

MASTER_LOGO_PATH = pathlib.Path(r"C:\Users\user\Desktop\NEMOV_Logo_Iran_4K_NoBG.png")
if not MASTER_LOGO_PATH.exists():
    MASTER_LOGO_PATH = pathlib.Path(r"C:\Users\user\OneDrive\Desktop\NEMOV_Logo_Iran_4K_NoBG.png")

print(f"Loading master logo from: {MASTER_LOGO_PATH}")
master_img = Image.open(MASTER_LOGO_PATH)
print(f"Master image format: {master_img.format}, size: {master_img.size}")

# High-Definition 720x720 Lanczos Resampling
TARGET_SIZE = (720, 720)
hd_logo = master_img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

# Save to resources/images/nemov_logo.png
local_logo_path = pathlib.Path("resources/images/nemov_logo.png")
hd_logo.save(local_logo_path, format="PNG", optimize=True)
print(f"Saved local HD logo to {local_logo_path} ({local_logo_path.stat().st_size} bytes)")

# Convert to Base64
buf = io.BytesIO()
hd_logo.save(buf, format="PNG", optimize=True)
b64_str = base64.b64encode(buf.getvalue()).decode("ascii")
print(f"Base64 length: {len(b64_str)} chars")

# Update index.js
index_js_path = pathlib.Path("yalda_cloud_server/cloudflare_worker/index.js")
content = index_js_path.read_text(encoding="utf-8")
initial_len = len(content)

# Update ETag
content = content.replace(
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.3-nemov-enlarged-logo"\';',
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.4-nemov-720p-hd-logo"\';'
)

# Replace NEMOV_LOGO_BASE64
pattern = r'const NEMOV_LOGO_BASE64 = ".*?";'
replacement = f'const NEMOV_LOGO_BASE64 = "{b64_str}";'
new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
if count == 0:
    print("ERROR: Could not find NEMOV_LOGO_BASE64 to replace!")
    exit(1)

# Add image-rendering: -webkit-optimize-contrast to .hero-logo-3d
old_hero_logo_css = """        .hero-logo-3d {
            width: 130px;
            height: 130px;
            object-fit: contain;"""

new_hero_logo_css = """        .hero-logo-3d {
            width: 130px;
            height: 130px;
            object-fit: contain;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;"""

if old_hero_logo_css in new_content:
    new_content = new_content.replace(old_hero_logo_css, new_hero_logo_css, 1)

index_js_path.write_text(new_content, encoding="utf-8")
new_size_kb = len(new_content.encode("utf-8")) / 1024
print(f"SUCCESS: index.js updated! New size: {new_size_kb:.1f} KB (Safe limit: 1024 KB)")
