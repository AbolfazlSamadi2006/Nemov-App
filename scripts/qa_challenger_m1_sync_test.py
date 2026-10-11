"""Adversarial stress-test suite for Milestone 1:
- AppData migration and directory synchronization (config.py: sync_data_directories)
- NSIS installer compilation check (installer.nsi)
"""

import os
import sys
import shutil
import tempfile
import time
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_nsis_compilation_check():
    print("\n" + "=" * 60)
    print("TEST: NSIS Script Compilation Verification")
    print("=" * 60)
    
    makensis_path = Path(r"C:\Program Files (x86)\NSIS\makensis.exe")
    if not makensis_path.exists():
        makensis_path = Path(r"C:\Program Files\NSIS\makensis.exe")
    
    if not makensis_path.exists():
        return False, "makensis.exe not found on system"
    
    nsi_file = PROJECT_ROOT / "installer.nsi"
    if not nsi_file.exists():
        return False, f"installer.nsi not found at {nsi_file}"
        
    # installer.nsi expects dist\Nemov to exist for File /r "dist\Nemov\*.*"
    # Create temporary dummy dist folder for compilation test
    temp_dist = PROJECT_ROOT / "dist" / "Nemov"
    temp_dist_created = False
    dummy_exe = temp_dist / "Nemov.exe"
    dummy_ico = temp_dist / "_internal" / "resources" / "icons" / "nemov.ico"
    
    try:
        if not temp_dist.exists():
            dummy_ico.parent.mkdir(parents=True, exist_ok=True)
            dummy_exe.write_text("dummy binary content")
            shutil.copy2(PROJECT_ROOT / "resources" / "icons" / "nemov.ico", dummy_ico)
            temp_dist_created = True
            
        cmd = [str(makensis_path), "/V2", str(nsi_file)]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        
        print(f"makensis returncode: {res.returncode}")
        if res.returncode == 0:
            print("PASS: installer.nsi successfully compiled with makensis v3.12!")
            # Clean up generated setup file in dist
            for f in (PROJECT_ROOT / "dist").glob("Nemov_Setup_*.exe"):
                try:
                    f.unlink()
                except Exception:
                    pass
            return True, "installer.nsi compilation succeeded with exit code 0"
        else:
            print("FAIL: installer.nsi compilation failed:")
            print(res.stdout)
            print(res.stderr)
            return False, f"makensis error: {res.stderr or res.stdout}"
    finally:
        if temp_dist_created:
            shutil.rmtree(PROJECT_ROOT / "dist", ignore_errors=True)


def test_sync_data_directories_scenarios():
    print("\n" + "=" * 60)
    print("TEST: Empirical Stress-Testing sync_data_directories()")
    print("=" * 60)
    
    results = {}
    
    # We will test using isolated temporary directories and patching config module variables
    import config
    
    # -------------------------------------------------------------
    # Scenario 1: Legacy exists, Nemov does not exist
    # -------------------------------------------------------------
    print("\n--- Scenario 1: Legacy YaldaGym exists, Nemov does not exist ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        sim_legacy_dir.mkdir(parents=True, exist_ok=True)
        # Create legacy files
        legacy_db = sim_legacy_dir / "yalda.db"
        legacy_db.write_bytes(b"SQLite format 3\x00_LEGACY_DATA_V1")
        
        legacy_uploads = sim_legacy_dir / "uploads" / "profile-photos"
        legacy_uploads.mkdir(parents=True, exist_ok=True)
        (legacy_uploads / "avatar1.png").write_bytes(b"PNG_LEGACY_AVATAR")
        
        legacy_branding = sim_legacy_dir / "branding"
        legacy_branding.mkdir(parents=True, exist_ok=True)
        (legacy_branding / "gym_logo.png").write_bytes(b"PNG_LEGACY_LOGO")
        
        # Monkeypatch config paths
        orig_data = config.DATA_DIR
        orig_nemov = config.APPDATA_DATA_DIR
        orig_legacy = config.LEGACY_APPDATA_DATA_DIR
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            config.sync_data_directories()
            
            # Assertions
            nemov_db = sim_nemov_dir / "yalda.db"
            app_db = sim_data_dir / "yalda.db"
            nemov_avatar = sim_nemov_dir / "uploads" / "profile-photos" / "avatar1.png"
            nemov_branding = sim_nemov_dir / "branding" / "gym_logo.png"
            
            assert nemov_db.exists(), "Nemov DB was not created from legacy!"
            assert nemov_db.read_bytes() == b"SQLite format 3\x00_LEGACY_DATA_V1", "Nemov DB content mismatch!"
            assert app_db.exists(), "Runtime DATA_DIR DB was not created from legacy!"
            assert nemov_avatar.exists(), "Uploads were not copied to Nemov!"
            assert nemov_branding.exists(), "Branding was not copied to Nemov!"
            
            print("  [PASS] Scenario 1: Legacy successfully migrated to Nemov and DATA_DIR with zero data loss.")
            results["Scenario 1 (Legacy -> Nemov)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    # -------------------------------------------------------------
    # Scenario 2: Both exist, Nemov is NEWER -> MUST NOT OVERWRITE
    # -------------------------------------------------------------
    print("\n--- Scenario 2: Both exist, Nemov is newer (prevent overwrite) ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        sim_legacy_dir.mkdir(parents=True, exist_ok=True)
        sim_nemov_dir.mkdir(parents=True, exist_ok=True)
        sim_data_dir.mkdir(parents=True, exist_ok=True)
        
        legacy_db = sim_legacy_dir / "yalda.db"
        legacy_db.write_bytes(b"OLD_LEGACY_DATA")
        t_old = time.time() - 3600  # 1 hour ago
        os.utime(legacy_db, (t_old, t_old))
        
        nemov_db = sim_nemov_dir / "yalda.db"
        nemov_db.write_bytes(b"NEW_NEMOV_DATA")
        t_new = time.time()  # Now
        os.utime(nemov_db, (t_new, t_new))
        
        # Legacy upload vs Nemov upload
        (sim_legacy_dir / "uploads").mkdir(parents=True, exist_ok=True)
        (sim_legacy_dir / "uploads" / "old_doc.pdf").write_bytes(b"OLD_DOC")
        
        (sim_nemov_dir / "uploads").mkdir(parents=True, exist_ok=True)
        (sim_nemov_dir / "uploads" / "new_doc.pdf").write_bytes(b"NEW_DOC")
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            config.sync_data_directories()
            
            # Assertions: Nemov DB must NOT be overwritten by older legacy DB
            assert nemov_db.read_bytes() == b"NEW_NEMOV_DATA", "Nemov DB was wrongly overwritten by older legacy DB!"
            # Runtime DATA_DIR must have the NEW Nemov data
            app_db = sim_data_dir / "yalda.db"
            assert app_db.read_bytes() == b"NEW_NEMOV_DATA", "DATA_DIR did not get the newest Nemov DB!"
            
            print("  [PASS] Scenario 2: Newer Nemov DB was protected and NOT overwritten by legacy.")
            results["Scenario 2 (Nemov Newer Protection)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    # -------------------------------------------------------------
    # Scenario 3: Both exist, Legacy is NEWER -> Should update Nemov
    # -------------------------------------------------------------
    print("\n--- Scenario 3: Both exist, Legacy is newer -> Should update Nemov ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        sim_legacy_dir.mkdir(parents=True, exist_ok=True)
        sim_nemov_dir.mkdir(parents=True, exist_ok=True)
        sim_data_dir.mkdir(parents=True, exist_ok=True)
        
        nemov_db = sim_nemov_dir / "yalda.db"
        nemov_db.write_bytes(b"OLDER_NEMOV_DATA")
        t_old = time.time() - 3600
        os.utime(nemov_db, (t_old, t_old))
        
        legacy_db = sim_legacy_dir / "yalda.db"
        legacy_db.write_bytes(b"NEWER_LEGACY_DATA")
        t_new = time.time()
        os.utime(legacy_db, (t_new, t_new))
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            config.sync_data_directories()
            
            assert nemov_db.read_bytes() == b"NEWER_LEGACY_DATA", "Nemov DB was not updated with newer legacy DB!"
            assert (sim_data_dir / "yalda.db").read_bytes() == b"NEWER_LEGACY_DATA"
            print("  [PASS] Scenario 3: Nemov DB successfully updated when legacy DB had newer modifications.")
            results["Scenario 3 (Legacy Newer Update)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    # -------------------------------------------------------------
    # Scenario 4: Backup Fallback (latest_backup.db in backups/)
    # -------------------------------------------------------------
    print("\n--- Scenario 4: Backup fallback (latest_backup.db in legacy backups/) ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        legacy_backup = sim_legacy_dir / "backups" / "latest_backup.db"
        legacy_backup.parent.mkdir(parents=True, exist_ok=True)
        legacy_backup.write_bytes(b"BACKUP_DB_DATA")
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            config.sync_data_directories()
            
            assert (sim_nemov_dir / "yalda.db").exists(), "Nemov DB not created from latest_backup.db!"
            assert (sim_nemov_dir / "yalda.db").read_bytes() == b"BACKUP_DB_DATA"
            print("  [PASS] Scenario 4: Backup DB successfully restored to Nemov when yalda.db was absent.")
            results["Scenario 4 (Backup Fallback)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    # -------------------------------------------------------------
    # Scenario 5: Corrupt 0-Byte DB Handling
    # -------------------------------------------------------------
    print("\n--- Scenario 5: Corrupted 0-byte DB in legacy ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        sim_legacy_dir.mkdir(parents=True, exist_ok=True)
        corrupt_legacy = sim_legacy_dir / "yalda.db"
        corrupt_legacy.write_bytes(b"")  # 0 bytes!
        
        # Nemov has valid DB
        sim_nemov_dir.mkdir(parents=True, exist_ok=True)
        valid_nemov = sim_nemov_dir / "yalda.db"
        valid_nemov.write_bytes(b"VALID_NEMOV_DATA")
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            config.sync_data_directories()
            
            assert valid_nemov.read_bytes() == b"VALID_NEMOV_DATA", "Valid DB was corrupted by 0-byte legacy file!"
            assert (sim_data_dir / "yalda.db").read_bytes() == b"VALID_NEMOV_DATA"
            print("  [PASS] Scenario 5: 0-byte corrupted legacy DB was correctly ignored.")
            results["Scenario 5 (0-Byte Corrupt DB)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    # -------------------------------------------------------------
    # Scenario 6: Deep nested hierarchy in uploads
    # -------------------------------------------------------------
    print("\n--- Scenario 6: Deep nested upload directory structure ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        sim_legacy_dir.mkdir(parents=True, exist_ok=True)
        (sim_legacy_dir / "yalda.db").write_bytes(b"VALID_DB")
        
        deep_file = sim_legacy_dir / "uploads" / "exercise-media" / "chest" / "incline" / "bench.mp4"
        deep_file.parent.mkdir(parents=True, exist_ok=True)
        deep_file.write_bytes(b"VIDEO_DATA")
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            config.sync_data_directories()
            
            dest_file = sim_nemov_dir / "uploads" / "exercise-media" / "chest" / "incline" / "bench.mp4"
            assert dest_file.exists(), "Deep nested file structure failed to copy!"
            assert dest_file.read_bytes() == b"VIDEO_DATA"
            print("  [PASS] Scenario 6: Deep nested upload hierarchy reproduced flawlessly.")
            results["Scenario 6 (Deep Directory Hierarchy)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    # -------------------------------------------------------------
    # Scenario 7: Idempotency (re-running sync multiple times)
    # -------------------------------------------------------------
    print("\n--- Scenario 7: Idempotency of sync_data_directories() ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sim_data_dir = tmp_path / "app_data"
        sim_nemov_dir = tmp_path / "Nemov" / "data"
        sim_legacy_dir = tmp_path / "YaldaGym" / "data"
        
        sim_legacy_dir.mkdir(parents=True, exist_ok=True)
        (sim_legacy_dir / "yalda.db").write_bytes(b"IDEMPOTENT_DB")
        
        try:
            config.DATA_DIR = sim_data_dir
            config.APPDATA_DATA_DIR = sim_nemov_dir
            config.LEGACY_APPDATA_DATA_DIR = sim_legacy_dir
            
            # Run 5 times in succession
            for i in range(5):
                config.sync_data_directories()
                
            assert (sim_nemov_dir / "yalda.db").read_bytes() == b"IDEMPOTENT_DB"
            print("  [PASS] Scenario 7: Repeated invocations are 100% idempotent and stable.")
            results["Scenario 7 (Idempotency)"] = "PASS"
        finally:
            config.DATA_DIR = orig_data
            config.APPDATA_DATA_DIR = orig_nemov
            config.LEGACY_APPDATA_DATA_DIR = orig_legacy

    return results


if __name__ == "__main__":
    print("STARTING EMPIRICAL CHALLENGER VERIFICATION FOR MILESTONE 1...")
    
    sync_results = test_sync_data_directories_scenarios()
    nsis_ok, nsis_msg = run_nsis_compilation_check()
    
    print("\n" + "=" * 60)
    print("FINAL CHALLENGE VERIFICATION SUMMARY:")
    print("=" * 60)
    all_passed = True
    for test_name, status in sync_results.items():
        print(f"  {test_name:<40}: {status}")
        if status != "PASS":
            all_passed = False
            
    nsis_status = "PASS" if nsis_ok else "FAIL"
    print(f"  {'NSIS Compilation Check':<40}: {nsis_status} ({nsis_msg})")
    if not nsis_ok:
        all_passed = False
        
    print("=" * 60)
    if all_passed:
        print("ALL ADVERSARIAL STRESS TESTS PASSED EMPIRICALLY! VERDICT: APPROVE")
        sys.exit(0)
    else:
        print("ADVERSARIAL STRESS TESTS DETECTED FAILURES! VERDICT: REQUEST_CHANGES")
        sys.exit(1)
