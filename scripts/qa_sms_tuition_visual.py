import sys, os
sys.path.insert(0, os.path.abspath("."))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
import config
from nemov.auth.authentication import CurrentUser
from nemov.models.database_models import User
from nemov.views.main_window import MainWindow

app = QApplication(sys.argv)

# Apply global dark stylesheet
qss_path = config.BASE_DIR / "resources" / "qss" / "dark_theme.qss"
if qss_path.exists():
    with open(qss_path, "r", encoding="utf-8") as f:
        content = f.read()
        arrow_down_path = (config.BASE_DIR / "resources" / "images" / "arrow_down.svg").as_posix()
        arrow_up_path = (config.BASE_DIR / "resources" / "images" / "arrow_up.svg").as_posix()
        check_path = (config.BASE_DIR / "resources" / "images" / "check.svg").as_posix()
        content = content.replace("resources/images/arrow_down.svg", arrow_down_path)
        content = content.replace("resources/images/arrow_up.svg", arrow_up_path)
        content = content.replace("resources/images/check.svg", check_path)
        app.setStyleSheet(content)

# Set mock admin user
mock_user = User(
    id=1,
    username="admin",
    password_hash="",
    full_name="مدیر سیستم",
    role="admin",
    is_active=True
)
CurrentUser.set(mock_user)

main_win = MainWindow()
main_win.resize(1200, 800)
main_win.show()

# Switch to SMS Center view via sidebar
main_win.sidebar.navigate("sms")
sms_widget = main_win.view_sms
sms_widget.tabs.setCurrentIndex(1)

def step1():
    # Scroll down to reveal cardTuition and buttons completely
    sms_widget.tab_automated.verticalScrollBar().setValue(
        sms_widget.tab_automated.verticalScrollBar().maximum()
    )
    QTimer.singleShot(200, step1_capture)

def step1_capture():
    artifact_path1 = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_sms_tab2_scrolled_down.png"
    main_win.grab().save(artifact_path1)
    print("Saved QA Tab 2 scrolled down screenshot to:", artifact_path1)
    
    # Also save close-up of tuition card
    for c in sms_widget.findChildren(object):
        if getattr(c, "objectName", lambda: "")() == "cardTuition":
            c.grab().save("C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_sms_tuition_card_closeup.png")
            print("Saved tuition card close-up")
            break
            
    # Test toggling
    sms_widget.chk_auto_tuition.setChecked(False)
    QTimer.singleShot(200, step2)

def step2():
    print("Tuition combo enabled state when unchecked:", sms_widget.combo_tuition_days.isEnabled())
    sms_widget.chk_auto_tuition.setChecked(True)
    print("Tuition combo enabled state when rechecked:", sms_widget.combo_tuition_days.isEnabled())
    
    # Test constrained window (1024x600)
    main_win.resize(1024, 600)
    QTimer.singleShot(200, step3)

def step3():
    artifact_path2 = "C:/Users/user/.gemini/antigravity/brain/4b6897a3-c508-4ec6-8c8a-20cd600f30a6/qa_sms_tab2_small_screen.png"
    main_win.grab().save(artifact_path2)
    print("Saved small screen QA screenshot to:", artifact_path2)
    app.quit()

QTimer.singleShot(500, step1)
app.exec()
