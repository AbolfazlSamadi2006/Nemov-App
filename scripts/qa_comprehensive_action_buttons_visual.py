import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
import config
from yalda.models.database_models import User
from yalda.auth.authentication import CurrentUser
from yalda.views.main_window import MainWindow

def run_qa():
    app = QApplication(sys.argv)
    
    mock_user = User(
        id=1,
        username="admin",
        password_hash="",
        full_name="مدیر سیستم",
        role="admin",
        is_active=True
    )
    CurrentUser.set(mock_user)
    
    qss_path = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    resolutions = [
        ("1100x780", 1100, 780),
        ("1280x780", 1280, 780),
        ("1366x768", 1366, 768),
        ("1920x1080", 1920, 1080)
    ]
    
    mw = MainWindow()
    mw.sidebar.navigate("members")
    
    def test_resolution(idx):
        if idx >= len(resolutions):
            print("ALL RESOLUTIONS CAPTURED SUCCESSFULLY")
            app.quit()
            return
        
        name, w, h = resolutions[idx]
        mw.resize(w, h)
        mw.show()
        app.processEvents()
        
        def capture():
            app.processEvents()
            tbl = mw.view_members.table
            row0_w = tbl.cellWidget(0, 7)
            buttons = [b for b in row0_w.findChildren(object) if hasattr(b, 'text') and b.text()]
            assert len(buttons) == 4, f"Expected 4 buttons, got {len(buttons)}"
            
            # Save screenshot
            save_path = f"C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_members_table_{name}.png"
            mw.grab().save(save_path)
            print(f"SUCCESS: Captured {name} to {save_path}")
            
            QTimer.singleShot(150, lambda: test_resolution(idx + 1))
            
        QTimer.singleShot(200, capture)

    QTimer.singleShot(200, lambda: test_resolution(0))
    app.exec()

if __name__ == "__main__":
    run_qa()
