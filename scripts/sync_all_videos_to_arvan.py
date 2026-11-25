import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
import ssl
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

ENDPOINT_URL = os.environ.get("S3_ENDPOINT", "https://s3.ir-central1.arvanstorage.ir")
ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
BUCKET_NAME = os.environ.get("S3_BUCKET", "nemov-storage")

LOCAL_DIR = r"data\uploads\exercise-media"
MEDIA_LIST_FILE = "scratch/all_cloud_media_files.json"
CHECKPOINT_FILE = "data/fitamin_crawl_checkpoint.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(s3={"addressing_style": "virtual"}, signature_version="s3v4", max_pool_connections=25)
    )

def fetch_existing_s3_keys(s3):
    existing = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix="video/"):
        for obj in page.get("Contents", []):
            existing.add(obj["Key"].replace("video/", ""))
    return existing

def process_file(filename, s3, fitamin_map):
    s3_key = f"video/{filename}"
    
    # 1. Check local disk first
    local_path = os.path.join(LOCAL_DIR, filename)
    data = None
    source_type = ""
    
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        with open(local_path, "rb") as f:
            data = f.read()
        source_type = "local"
    
    # 2. If not local, download from storage.nemovapp.ir
    if not data:
        url = f"https://storage.nemovapp.ir/video/{urllib.parse.quote(filename)}?raw=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
                data = resp.read()
            source_type = "cloud"
        except Exception as e:
            # 3. Fallback to fitamin
            fitamin_url = fitamin_map.get(filename)
            if fitamin_url:
                try:
                    safe_f_url = urllib.parse.quote(fitamin_url, safe='/:')
                    req = urllib.request.Request(safe_f_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                        data = resp.read()
                    source_type = "fitamin_fallback"
                except Exception as ef:
                    return filename, False, f"All sources failed: {e} | {ef}"
            else:
                return filename, False, f"Cloud failed: {e} and no fallback"

    if not data or len(data) < 1000:
        return filename, False, f"Downloaded data too small or empty ({len(data) if data else 0} bytes)"

    # Upload to S3
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=data,
            ContentType="video/mp4",
            ACL="public-read"
        )
        return filename, True, f"{source_type} ({round(len(data)/1024, 1)} KB)"
    except Exception as e:
        return filename, False, f"S3 put error: {e}"

def main():
    print("=== Nemov to ArvanCloud Video Synchronization ===")
    s3 = get_s3_client()
    
    with open(MEDIA_LIST_FILE, "r", encoding="utf-8") as f:
        media_files = json.load(f)
    print(f"Total target files in registry: {len(media_files)}")
    
    # Load fitamin map
    fitamin_map = {}
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                cp = json.load(f)
                for item in cp.get("exercises", {}).values():
                    fn = item.get("filename")
                    vu = item.get("video_url")
                    if fn and vu:
                        fitamin_map[fn] = vu
        except Exception:
            pass
    print(f"Loaded {len(fitamin_map)} fallback URLs from checkpoint.")
    
    existing = fetch_existing_s3_keys(s3)
    print(f"Already in ArvanCloud S3: {len(existing)} files")
    
    to_upload = [f for f in media_files if f not in existing]
    print(f"Remaining to upload: {len(to_upload)} files")
    
    if not to_upload:
        print("All files are already synchronized! 100% complete.")
        return
        
    start_time = time.time()
    success_count = 0
    failed_count = 0
    failed_details = []
    
    # Multi-threaded execution with 16 threads
    max_workers = 16
    print(f"Starting upload with {max_workers} concurrent threads...", flush=True)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, fn, s3, fitamin_map): fn for fn in to_upload}
        
        for idx, future in enumerate(as_completed(futures), 1):
            fn, ok, msg = future.result()
            if ok:
                success_count += 1
            else:
                failed_count += 1
                failed_details.append((fn, msg))
            
            if idx % 25 == 0 or idx == len(to_upload):
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                remaining = (len(to_upload) - idx) / rate if rate > 0 else 0
                print(f"Progress: [{idx}/{len(to_upload)}] {round(idx/len(to_upload)*100, 1)}% | "
                      f"Success: {success_count}, Failed: {failed_count} | "
                      f"Speed: {round(rate, 1)} files/sec | Remaining: ~{round(remaining)}s", flush=True)
                      
    total_elapsed = round(time.time() - start_time, 1)
    print(f"\n=== Sync Completed in {total_elapsed}s ===")
    print(f"Total: {len(to_upload)} | Succeeded: {success_count} | Failed: {failed_count}")
    
    if failed_details:
        print("Failed files sample:")
        for fn, err in failed_details[:10]:
            print(f"  {fn}: {err}")
            
    final_existing = fetch_existing_s3_keys(s3)
    print(f"Final files in ArvanCloud S3 nemov-storage: {len(final_existing)} / {len(media_files)}")

if __name__ == "__main__":
    main()
