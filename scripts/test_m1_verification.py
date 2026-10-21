import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image

def test_m1():
    # 1. Icons check
    ico = Image.open('resources/icons/nemov.ico')
    layers = ico.info.get('sizes')
    expected_layers = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
    assert layers == expected_layers, f"Expected {expected_layers}, got {layers}"
    print(f"PASS: nemov.ico has all 7 layers: {layers}")

    for img_path in ['resources/icons/nemov.png', 'resources/images/nemov_logo.png', 'resources/images/app_icon.png', 'resources/images/app_icon.ico']:
        assert Path(img_path).exists(), f"Missing {img_path}"
        test_img = Image.open(img_path)
        assert test_img.size[0] > 0 and test_img.size[1] > 0
    print("PASS: All icon and logo PNG/ICO assets exist and are valid.")

    # 2. Config check
    import config
    assert config.APP_NAME == "نِمُو", f"APP_NAME: {config.APP_NAME}"
    assert config.APP_TITLE == "نرم‌افزار مدیریت ورزشی نِمُو", f"APP_TITLE: {config.APP_TITLE}"
    assert config.APP_ENGLISH_NAME == "Nemov", f"APP_ENGLISH_NAME: {config.APP_ENGLISH_NAME}"
    assert config.APP_VERSION == "v3.3.0", f"APP_VERSION: {config.APP_VERSION}"
    assert config.APP_USER_MODEL_ID == "nemov.sports.management.desktop.v3", f"APP_USER_MODEL_ID: {config.APP_USER_MODEL_ID}"
    assert config.BRANDING_DIR == config.DATA_DIR / "branding", f"BRANDING_DIR: {config.BRANDING_DIR}"
    assert config.APPDATA_DATA_DIR == Path(os.environ.get("APPDATA", Path.home())) / "Nemov" / "data"
    assert config.LEGACY_APPDATA_DATA_DIR == Path(os.environ.get("APPDATA", Path.home())) / "YaldaGym" / "data"
    print("PASS: config.py constants and AppData paths correctly rebranded.")

    # 3. GUI elements check
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from nemov.views.login_view import LoginView
    from nemov.views.main_window import MainWindow

    login = LoginView()
    assert login.windowTitle() == "نرم‌افزار مدیریت ورزشی نِمُو - ورود به سیستم", f"Login title: {login.windowTitle()}"
    assert not login.windowIcon().isNull(), "Login window icon is null"
    print("PASS: LoginView window title and icon valid.")

    main_win = MainWindow()
    assert main_win.windowTitle() == "نرم‌افزار مدیریت ورزشی نِمُو (نسخه v3.3.0)", f"Main window title: {main_win.windowTitle()}"
    assert not main_win.windowIcon().isNull(), "Main window icon is null"
    assert main_win.sidebar.title_lbl.text() == "نِمُو", f"Sidebar title: {main_win.sidebar.title_lbl.text()}"
    assert main_win.sidebar.sub_lbl.text() == "نرم‌افزار مدیریت ورزشی", f"Sidebar subtitle: {main_win.sidebar.sub_lbl.text()}"
    print("PASS: MainWindow and Sidebar titles and icons valid.")

    # 4. Spec & NSI check
    with open('Nemov.spec', 'r', encoding='utf-8') as f:
        spec_txt = f.read()
        assert "name='Nemov'" in spec_txt
        assert "icon='resources/icons/nemov.ico'" in spec_txt
    print("PASS: Nemov.spec configured for Nemov executable and icon.")

    with open('installer.nsi', 'r', encoding='utf-8') as f:
        nsi_txt = f.read()
        assert '!define PRODUCT_NAME "Nemov"' in nsi_txt
        assert '!define PRODUCT_VERSION "3.3.0"' in nsi_txt
        assert '!define PRODUCT_EXE "Nemov.exe"' in nsi_txt
        assert 'OutFile "dist\\Nemov_Setup_v${PRODUCT_VERSION}.exe"' in nsi_txt
        assert '!define MUI_ICON "resources\\icons\\nemov.ico"' in nsi_txt
        assert 'Nemov.lnk' in nsi_txt
        assert 'Yalda Gym.lnk' in nsi_txt
    print("PASS: installer.nsi configured for Nemov setup and legacy cleanup.")

    print("\n==========================================")
    print("ALL MILESTONE 1 VERIFICATIONS PASSED 100%!")
    print("==========================================")

if __name__ == "__main__":
    test_m1()
