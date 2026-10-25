import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import time
import urllib.request
import urllib.parse
import ssl
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

CLOUD_UPLOAD_URL = "https://storage.nemovapp.ir/api/video/upload"
CLOUD_SECRET_KEY = "nemov_cloud_security"
CHECKPOINT_PATH = "data/fitamin_crawl_checkpoint.json"

def upload_single_video(item_tuple):
    url, item = item_tuple
    title = item.get("title", "")
    video_url = item.get("video_url", "")
    filename = item.get("filename", "")
    
    if not video_url or not filename:
        return url, False, "Missing URL or filename"
        
    try:
        # Download
        safe_url = urllib.parse.quote(video_url, safe='/:')
        req = urllib.request.Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=60) as resp:
            v_bytes = resp.read()
            
        size_mb = round(len(v_bytes) / (1024 * 1024), 2)
        
        # Upload
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
        with urllib.request.urlopen(req_up, context=SSL_CONTEXT, timeout=60) as resp_up:
            res = json.loads(resp_up.read().decode("utf-8"))
            if res.get("success"):
                cloud_url = res.get("url") or f"https://storage.nemovapp.ir/video/{filename}"
                return url, True, (cloud_url, size_mb)
            else:
                return url, False, f"Server rejected: {res}"
    except Exception as e:
        return url, False, str(e)

def main():
    print("=" * 60)
    print("🚀 آغاز آپلود ویدیوهای باقی‌مانده فیتامین به Cloudflare KV (سرور storage.nemovapp.ir)")
    print("=" * 60)
    
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)
        
    exercises = checkpoint.get("exercises", {})
    pending = [(k, v) for k, v in exercises.items() if v.get("uploaded") is not True]
    print(f"📊 تعداد کل ویدیوهای نیازمند آپلود: {len(pending)}")
    
    if not pending:
        print("✅ تمامی ۸۴۸ ویدیوی فیتامین قبلاً با موفقیت آپلود شده‌اند!")
        return

    success_count = 0
    fail_count = 0
    
    # Process with 6 parallel threads
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_url = {executor.submit(upload_single_video, item): item[0] for item in pending}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                res_url, ok, data = future.result()
                item = exercises[url]
                title = item.get("title", "")
                if ok:
                    cloud_url, size_mb = data
                    item["uploaded"] = True
                    item["cloud_url"] = cloud_url
                    item["video_size_mb"] = size_mb
                    success_count += 1
                    print(f"[{success_count + fail_count}/{len(pending)}] ✅ آپلود موفق: {title} ({size_mb} MB)")
                else:
                    fail_count += 1
                    print(f"[{success_count + fail_count}/{len(pending)}] ❌ خطا در {title}: {data}")
            except Exception as exc:
                fail_count += 1
                print(f"❌ استثنا در پردازش {url}: {exc}")
                
            # Periodic checkpoint save every 5 items
            if (success_count + fail_count) % 5 == 0:
                with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
                    json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    # Final checkpoint save
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"🎉 عملیات آپلود به پایان رسید:")
    print(f"   تعداد موفق: {success_count}")
    print(f"   تعداد ناموفق: {fail_count}")
    print(f"   وضعیت نهایی در چک‌پوینت ثبت شد.")
    print("=" * 60)

if __name__ == "__main__":
    main()
