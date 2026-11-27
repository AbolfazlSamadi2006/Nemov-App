"""
Unit tests verifying that all client, connectivity, and server modules are aligned
with Runflare + ArvanCloud (no remaining Cloudflare or non-Iranian DNS dependencies).
"""
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication(sys.argv)

import config
from nemov.services import backup_service, cloud_sync_service
from nemov.services.sms_service import SmsService

ROOT_DIR = Path(__file__).resolve().parent.parent


class TestRunflareArvanAlignment(unittest.TestCase):
    """Audits source files, server templates, and runtime config for Runflare/ArvanCloud."""

    def test_no_cloudflare_traces_in_client_or_server_code(self):
        legacy_dir = ROOT_DIR / "nemov_cloud_server" / "cloudflare_worker"
        self.assertFalse(legacy_dir.exists(), "Obsolete cloudflare_worker directory must be removed")

        forbidden = re.compile(
            r"cloudflare|کلودفلر|کلادفلر|wrangler|1\.1\.1\.1|8\.8\.8\.8|google\.com",
            re.IGNORECASE,
        )
        scan_targets = [
            ROOT_DIR / "main.py",
            ROOT_DIR / "config.py",
            ROOT_DIR / "installer.nsi",
            ROOT_DIR / "Nemov.spec",
            ROOT_DIR / "nemov_cloud_server" / "README.md",
        ]
        for folder in (ROOT_DIR / "nemov", ROOT_DIR / "nemov_cloud_server"):
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix in {".py", ".html", ".md", ".txt", ".yml", ".yaml", ".toml"}:
                    scan_targets.append(p)

        offenders = []
        for path in scan_targets:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            m = forbidden.search(text)
            if m:
                offenders.append(f"{path.relative_to(ROOT_DIR)}: {m.group(0)}")

        self.assertEqual(offenders, [], f"Found forbidden Cloudflare/foreign DNS references: {offenders}")

    def test_default_cloud_urls_and_sms_gateway(self):
        self.assertEqual(config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/"), "https://storage.nemovapp.ir")
        self.assertEqual(SmsService._get_base_url(), "https://storage.nemovapp.ir")

    def test_backup_view_restore_tooltip_no_cloudflare(self):
        from nemov.views.backup_view import BackupView
        with patch.object(BackupView, "load_backups"):
            view = BackupView()
        tooltip = view.btn_restore_cloud.toolTip()
        self.assertIn("رانفلر", tooltip)
        self.assertNotIn("کلودفلر", tooltip)
        view.close()
        view.deleteLater()

    def test_is_internet_connected_uses_iranian_runflare_arvan_fallbacks(self):
        checked_hosts = []

        def fake_create_connection(addr, timeout=3.0):
            checked_hosts.append(addr)
            if addr[0] == "s3.ir-central1.arvanstorage.ir":
                sock = MagicMock()
                return sock
            raise OSError("unreachable")

        with patch("urllib.request.urlopen", side_effect=OSError("head failed")), \
             patch("socket.create_connection", side_effect=fake_create_connection):
            ok = backup_service.is_internet_connected(timeout=0.5)

        self.assertTrue(ok)
        self.assertEqual(checked_hosts[0], ("nemovapp.ir", 443))
        self.assertEqual(checked_hosts[1], ("s3.ir-central1.arvanstorage.ir", 443))
        for host, _port in checked_hosts:
            self.assertNotIn(host, ("8.8.8.8", "1.1.1.1", "google.com"))

    def test_is_internet_connected_returns_false_when_all_offline(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")), \
             patch("socket.create_connection", side_effect=OSError("offline")):
            self.assertFalse(backup_service.is_internet_connected(timeout=0.2))

    def test_cloud_sync_check_internet_connection_endpoints(self):
        probed_urls = []

        def fake_urlopen(req, timeout=3.0, context=None):
            probed_urls.append(req.full_url)
            if "arvanstorage.ir" in req.full_url:
                resp = MagicMock()
                resp.__enter__.return_value = resp
                return resp
            raise OSError("timeout")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            ok = cloud_sync_service.check_internet_connection(timeout=0.5)

        self.assertTrue(ok)
        self.assertTrue(any("storage.nemovapp.ir" in u for u in probed_urls))
        self.assertTrue(any("arvanstorage.ir" in u for u in probed_urls))
        self.assertFalse(any("1.1.1.1" in u or "google.com" in u for u in probed_urls))

    def test_cloud_sync_check_internet_connection_offline(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.assertFalse(cloud_sync_service.check_internet_connection(timeout=0.2))


if __name__ == "__main__":
    unittest.main()
