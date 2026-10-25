import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import urllib.request
import urllib.parse
import ssl
import uuid

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

CLOUD_UPLOAD_URL = "https://storage.nemovapp.ir/api/video/upload"
CLOUD_SECRET_KEY = "nemov_cloud_security"

d = json.load(open('data/fitamin_crawl_checkpoint.json', encoding='utf-8'))
exs = d.get('exercises', {})
pending = [(k, v) for k, v in exs.items() if v.get('uploaded') is False]
print(f"Total pending videos: {len(pending)}")

if pending:
    url, item = pending[0]
    title = item.get('title')
    video_url = item.get('video_url')
    filename = item.get('filename')
    print(f"Testing upload for: {title}")
    print(f"Video URL: {video_url}")
    print(f"Target filename: {filename}")
    
    # Download video bytes
    safe_url = urllib.parse.quote(video_url, safe='/:')
    req = urllib.request.Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=60) as resp:
        v_bytes = resp.read()
    print(f"Downloaded {len(v_bytes)} bytes ({len(v_bytes)/1024/1024:.2f} MB)")
    
    # Upload to Cloudflare
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="filename"\r\n\r\n')
    body.extend(f"{filename}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: video/mp4\r\n\r\n")
    body.extend(v_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-API-Key": CLOUD_SECRET_KEY,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Connection": "close"
    }

    req_up = urllib.request.Request(CLOUD_UPLOAD_URL, data=bytes(body), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req_up, context=SSL_CONTEXT, timeout=60) as resp_up:
            res = json.loads(resp_up.read().decode("utf-8"))
            print(f"Status: {resp_up.status}")
            print(f"Response: {res}")
            if res.get("success"):
                print("🎉 KV LIMIT HAS RESET! Upload was 100% SUCCESSFUL!")
            else:
                print("Failed response:", res)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"Error: {e}")
