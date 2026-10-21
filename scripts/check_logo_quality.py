import pathlib
import base64
import io
import re
from PIL import Image

# 1. Embedded
js = pathlib.Path('nemov_cloud_server/cloudflare_worker/index.js').read_text(encoding='utf-8')
m = re.search(r'const NEMOV_LOGO_BASE64 = "(.*?)";', js, re.DOTALL)
if m:
    b64_clean = re.sub(r'\s+', '', m.group(1))
    raw = base64.b64decode(b64_clean)
    img = Image.open(io.BytesIO(raw))
    print(f"Embedded in index.js: {img.format} {img.size} ({len(raw)} bytes)")

# 2. Local workspace files
for p in [
    pathlib.Path('resources/images/nemov_logo.png'),
    pathlib.Path('resources/icons/nemov.png'),
    pathlib.Path(r'C:\Users\user\OneDrive\Desktop\NEMOV_Logo_Iran_4K_NoBG.png'),
    pathlib.Path(r'C:\Users\user\Desktop\NEMOV_Logo_Iran_4K_NoBG.png'),
]:
    if p.exists():
        im = Image.open(p)
        print(f"Found {p}: {im.format} {im.size} ({p.stat().st_size} bytes)")
    else:
        print(f"Not found: {p}")
