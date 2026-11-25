import os
import time
from urllib.parse import quote
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from db import to_shamsi


class ArvanS3Storage:
    """ArvanCloud Object Storage manager for private backups and public exercise media."""

    def __init__(self):
        self.endpoint = os.environ.get("S3_ENDPOINT", "https://s3.ir-central1.arvanstorage.ir").strip()
        self.bucket = os.environ.get("S3_BUCKET", "nemov-storage").strip()
        self.access_key = os.environ.get("S3_ACCESS_KEY", "").strip()
        self.secret_key = os.environ.get("S3_SECRET_KEY", "").strip()
        self._client = None
        self._media_cache = None
        self._media_cache_time = 0.0

    @property
    def client(self):
        if self._client is None and self.access_key and self.secret_key:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(s3={"addressing_style": "virtual"}, signature_version="s3v4"),
            )
        return self._client

    def is_configured(self) -> bool:
        return bool(self.access_key and self.secret_key and self.bucket)

    def get_public_media_url(self, filename: str, is_image: bool = False) -> str:
        folder = "image" if is_image else "video"
        host = self.endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        return f"https://{self.bucket}.{host}/{folder}/{quote(filename)}"

    def upload_backup(self, phone: str, file_bytes: bytes):
        if not self.client:
            raise RuntimeError("S3 storage credentials are not configured.")
        for key in (f"backups/{phone}/nemov.db", f"backups/{phone}/yalda.db"):
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_bytes,
                ContentType="application/octet-stream",
                ACL="private",
            )

    def download_backup(self, phone: str) -> bytes | None:
        if not self.client:
            return None
        for key in (f"backups/{phone}/nemov.db", f"backups/{phone}/yalda.db"):
            try:
                resp = self.client.get_object(Bucket=self.bucket, Key=key)
                return resp["Body"].read()
            except ClientError:
                continue
        return None

    def delete_backup(self, phone: str):
        if not self.client:
            return
        for key in (
            f"backups/{phone}/nemov.db",
            f"backups/{phone}/yalda.db",
            f"backups/{phone}/metadata.json",
        ):
            try:
                self.client.delete_object(Bucket=self.bucket, Key=key)
            except Exception:
                pass

    def upload_media(self, filename: str, file_bytes: bytes, content_type: str, is_image: bool = False):
        if not self.client:
            raise RuntimeError("S3 storage credentials are not configured.")
        folder = "image" if is_image else "video"
        self.client.put_object(
            Bucket=self.bucket,
            Key=f"{folder}/{filename}",
            Body=file_bytes,
            ContentType=content_type,
            ACL="public-read",
        )
        self._media_cache = None

    def delete_media(self, filename: str, is_image: bool | None = None):
        if not self.client:
            return
        keys = []
        if is_image is True:
            keys = [f"image/{filename}", f"images/{filename}"]
        elif is_image is False:
            keys = [f"video/{filename}", f"videos/{filename}"]
        else:
            keys = [f"video/{filename}", f"image/{filename}"]
        for k in keys:
            try:
                self.client.delete_object(Bucket=self.bucket, Key=k)
            except Exception:
                pass
        self._media_cache = None

    def head_media(self, filename: str, is_image: bool = False) -> dict | None:
        if not self.client:
            return None
        folder = "image" if is_image else "video"
        try:
            res = self.client.head_object(Bucket=self.bucket, Key=f"{folder}/{filename}")
            return {
                "size": res.get("ContentLength", 0),
                "content_type": res.get("ContentType", "image/jpeg" if is_image else "video/mp4"),
            }
        except ClientError:
            return None

    def list_media(self, origin_url: str = "", cache_ttl: int = 60):
        now = time.time()
        if self._media_cache is not None and (now - self._media_cache_time) < cache_ttl:
            return self._media_cache

        items = []
        total_mb = 0.0
        if not self.client:
            return items, "0.00"

        paginator = self.client.get_paginator("list_objects_v2")
        for prefix, mtype in (("video/", "video"), ("image/", "image")):
            try:
                for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        fn = key.replace(prefix, "", 1)
                        if not fn:
                            continue
                        sz_mb = round(obj["Size"] / (1024 * 1024), 2)
                        total_mb += sz_mb
                        lm = obj.get("LastModified")
                        iso = lm.isoformat() if lm else ""
                        shamsi = to_shamsi(lm) if lm else "-"
                        items.append({
                            "filename": fn,
                            "type": mtype,
                            "file_size_mb": sz_mb,
                            "upload_date": iso,
                            "upload_shamsi": shamsi,
                            "url": f"{origin_url}/{mtype}/{quote(fn)}" if origin_url else f"/{mtype}/{quote(fn)}",
                        })
            except Exception:
                pass

        items.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        res = (items, f"{total_mb:.2f}")
        self._media_cache = res
        self._media_cache_time = now
        return res
