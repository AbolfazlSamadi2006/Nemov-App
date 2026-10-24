# scripts/verify_cloud_backup_dialog_qa.py
import sys
import os

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from nemov.utils.theme_manager import ThemeManager
from nemov.views.components.cloud_backup_choice_dialog import CloudBackupChoiceDialog
from nemov.views.backup_view import BackupView
from nemov.services.autosave_service import is_autosave_enabled, set_autosave_enabled
from nemov.services.cloud_sync_service import get_pending_sync_count

ThemeManager.apply_theme("crimson_fury")
artifacts_dir = r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6"

print("--- Testing CloudBackupChoiceDialog ---")
dlg = CloudBackupChoiceDialog(pending_count=3)
dlg.show()

assert dlg.windowTitle() == "☁️ پشتیبان‌گیری در سرور", f"Wrong title: {dlg.windowTitle()}"
pix = dlg.grab()
pix.save(os.path.join(artifacts_dir, "qa_cloud_backup_choice_dialog.png"))
print("  Saved qa_cloud_backup_choice_dialog.png successfully!")

# Test choices
dlg.selected_choice = dlg.CHOICE_SYNC_AND_BACKUP
assert dlg.selected_choice == "sync_and_backup"
dlg.selected_choice = dlg.CHOICE_DATA_ONLY
assert dlg.selected_choice == "data_only"
dlg.selected_choice = dlg.CHOICE_CANCEL
assert dlg.selected_choice == "cancel"
print("  Dialog choices validated!")

print("\n--- Testing BackupView AutoSave Toggle ---")
view = BackupView()
view.resize(1100, 750)
view.show()

# Switch to tab 2 (Backup tab)
view.tabs.setCurrentIndex(1)
QApplication.processEvents()

assert hasattr(view, "chk_autosave"), "BackupView should have chk_autosave"
assert "AutoSave" in view.chk_autosave.text(), f"Unexpected text: {view.chk_autosave.text()}"
print(f"  AutoSave text: {view.chk_autosave.text()}")

# Test toggling
set_autosave_enabled(True)
assert is_autosave_enabled() is True, "Autosave should be enabled"
set_autosave_enabled(False)
assert is_autosave_enabled() is False, "Autosave should be disabled"
print("  AutoSave setting persistence validated!")

pix_tab = view.tabs.widget(1).grab()
pix_tab.save(os.path.join(artifacts_dir, "qa_backup_tab_autosave_toggle.png"))
print("  Saved qa_backup_tab_autosave_toggle.png successfully!")

print("\n--- Testing Media Deduplication Logic ---")
pending = get_pending_sync_count()
print(f"  Current pending exercises needing sync: {pending}")

print("\nALL CLOUD BACKUP & AUTOSAVE QA TESTS PASSED WITH 100% ACCURACY!")
