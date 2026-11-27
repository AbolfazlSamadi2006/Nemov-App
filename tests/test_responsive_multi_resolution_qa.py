import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QScrollArea
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import Qt, QRect, QTimer, QEventLoop

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestResponsiveMultiResolutionQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        for fp in (
            PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Regular.ttf",
            PROJECT_ROOT / "resources" / "fonts" / "Vazirmatn-Bold.ttf",
        ):
            if fp.exists():
                QFontDatabase.addApplicationFont(str(fp))

    def _pump(self):
        self.app.processEvents()

    def test_01_small_laptop_1366_at_150_percent_fits_every_dialog_and_mainwindow(self):
        """Worst-case 911x472 viewport: no dialog overflows height/width and primary action buttons stay visible."""
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.main_window import MainWindow
        from nemov.views.login_view import LoginView
        from nemov.views.password_recovery_dialog import PasswordRecoveryDialog
        from nemov.views.trainer_register_dialog import TrainerRegisterDialog
        from nemov.views.member_form_dialog import MemberFormDialog
        from nemov.views.sms_view import RechargeInfoDialog
        from nemov.views.components.trainer_details_dialog import TrainerDetailsDialog
        from nemov.views.workout_library_view import ExerciseFormDialog
        from nemov.views.food_library_dialog import FoodLibraryDialog

        ThemeManager.apply_theme("crimson_fury", self.app)
        small_rect = QRect(0, 0, 911, 472)

        with patch("PyQt6.QtGui.QScreen.availableGeometry", return_value=small_rect):
            with patch("nemov.auth.authentication.CurrentUser.get", return_value=SimpleNamespace(id=1, display_name="Test", role="admin", profile_photo=None)), \
                 patch("nemov.views.dashboard_view.DashboardView"):
                mw = MainWindow()
                self.assertLessEqual(mw.minimumWidth(), 911)
                self.assertLessEqual(mw.minimumHeight(), 472)
                self.assertLessEqual(mw.width(), 911)
                self.assertLessEqual(mw.height(), 472)
                mw.close()

            lv = LoginView()
            lv.resize(911, 472)
            lv.show()
            self._pump()
            sa = lv.findChild(QScrollArea, "login_host_scroll")
            self.assertIsNotNone(sa)
            # Scrollable down to btn_login on small 472px screens
            sa.verticalScrollBar().setValue(sa.verticalScrollBar().maximum())
            self._pump()
            self.assertTrue(lv.btn_login.isVisible())
            lv.close()

            pr = PasswordRecoveryDialog()
            pr.show()
            self._pump()
            self.assertLessEqual(pr.width(), 911)
            self.assertLessEqual(pr.height(), 472)
            pr._activate_step2(SimpleNamespace(id=1, display_name="تست", username="t1"))
            self._pump()
            self.assertLessEqual(pr.height(), 472)
            pr.close()

            tr = TrainerRegisterDialog()
            tr.show()
            self._pump()
            self.assertLessEqual(tr.width(), 911)
            self.assertLessEqual(tr.height(), 472)
            tr.close()

            mf = MemberFormDialog()
            mf.show()
            self._pump()
            self.assertLessEqual(mf.width(), 911)
            self.assertLessEqual(mf.height(), 472)
            mf_sa = mf.findChild(QScrollArea, "member_form_scroll")
            self.assertIsNotNone(mf_sa)
            # Save button sits below scroll area strictly inside visible bounds
            btn_save = next(b for b in mf.findChildren(type(mf.btn_photo)) if "ذخیره اطلاعات" in b.text())
            self.assertTrue(mf.rect().contains(btn_save.geometry()))
            mf.close()

            ri = RechargeInfoDialog()
            ri.show()
            self._pump()
            self.assertLessEqual(ri.width(), 911)
            self.assertLessEqual(ri.height(), 472)
            btn_ok = next(b for b in ri.findChildren(type(ri.btn_copy_card)) if "متوجه شدم" in b.text())
            self.assertTrue(ri.rect().contains(btn_ok.geometry()))
            ri.close()

            td = TrainerDetailsDialog(None, {"display_name": "مربی", "username": "u", "password": "pw", "recovery_code": "rc", "phone": "0912"})
            td.reset_pass_box.setVisible(True)
            td.show()
            self._pump()
            self.assertLessEqual(td.height(), 472)
            td.close()

            ef = ExerciseFormDialog()
            self.assertLessEqual(ef.minimumWidth(), 911)
            self.assertLessEqual(ef.minimumHeight(), 472)
            ef.close()

            fl = FoodLibraryDialog()
            self.assertLessEqual(fl.minimumWidth(), 911)
            self.assertLessEqual(fl.minimumHeight(), 472)
            fl.close()

    def test_02_standard_laptops_preserve_exact_original_dimensions_zero_regression(self):
        """Standard 1280x680 (FHD@150%) and 1920x1040 (FHD@100%) must match historical sizes 1:1."""
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.login_view import LoginView
        from nemov.views.password_recovery_dialog import PasswordRecoveryDialog
        from nemov.views.member_form_dialog import MemberFormDialog
        from nemov.views.sms_view import RechargeInfoDialog, SmsView
        from nemov.views.backup_view import BackupView

        ThemeManager.apply_theme("crimson_fury", self.app)

        for avail in (QRect(0, 0, 1280, 680), QRect(0, 0, 1920, 1040)):
            with patch("PyQt6.QtGui.QScreen.availableGeometry", return_value=avail):
                pr = PasswordRecoveryDialog()
                self.assertEqual((pr.width(), pr.height()), (540, 580))
                pr.close()

                ri = RechargeInfoDialog()
                self.assertEqual((ri.width(), ri.height()), (580, 570))
                ri.close()

                mf = MemberFormDialog()
                self.assertEqual((mf.width(), mf.height()), (650, 615))
                mf.show()
                self._pump()
                mf_sa = mf.findChild(QScrollArea, "member_form_scroll")
                self.assertFalse(mf_sa.horizontalScrollBar().isVisible())
                self.assertFalse(mf_sa.verticalScrollBar().isVisible())
                mf.close()

                lv = LoginView()
                lv.resize(avail.width(), avail.height())
                lv.show()
                self._pump()
                self.assertEqual((lv.card.width(), lv.card.height()), (480, 640))
                lv.close()

                with patch("nemov.views.sms_view.MemberService.get_all_members", return_value=[]):
                    sv = SmsView()
                    sv.resize(avail.width() - 230, avail.height())
                    sv.show()
                    self._pump()
                    self.assertEqual((sv.phone_mockup.width(), sv.phone_mockup.height()), (280, 490))
                    sv.close()

        with patch("nemov.services.backup_service.BackupService.get_all_backups", return_value=[]), \
             patch("nemov.services.notification_service.NotificationService.get_history", return_value=[]), \
             patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={}):
            bv = BackupView()
            bv.tabs.setCurrentWidget(bv.tab_appearance)
            bv.resize(1050, 680)
            bv.show()
            self._pump()
            self.assertEqual(bv._theme_grid_cols, 4)
            bv.close()

    def test_03_large_tv_2k_and_4k_fullscreen_expands_proportionally_without_dead_void(self):
        """On 2560x1400 / 3840x2100 fullscreen, Login card scales proportionally, Theme grid expands >4 cols, SMS expands."""
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.login_view import LoginView
        from nemov.views.backup_view import BackupView
        from nemov.views.sms_view import SmsView

        ThemeManager.apply_theme("crimson_fury", self.app)

        # Login card scales gently on 2K/4K TVs instead of staying 19% tiny
        lv = LoginView()
        lv.resize(2560, 1400)
        lv.show()
        self._pump()
        self.assertGreaterEqual(lv.card.width(), 600)
        self.assertGreaterEqual(lv.card.height(), 700)
        lv.close()

        # BackupView theme cards reflow into 6 columns instead of fixed 4 columns
        with patch("nemov.services.backup_service.BackupService.get_all_backups", return_value=[]), \
             patch("nemov.services.notification_service.NotificationService.get_history", return_value=[]), \
             patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={}):
            bv = BackupView()
            bv.tabs.setCurrentWidget(bv.tab_appearance)
            bv.resize(2330, 1400)
            bv.show()
            self._pump()
            self.assertEqual(bv._theme_grid_cols, 6)
            bv.close()

        # SmsView grows member table vertically beyond old 300px cap & gently enlarges phone preview on tall TVs
        with patch("nemov.views.sms_view.MemberService.get_all_members", return_value=[]):
            sv = SmsView()
            sv.resize(2330, 1400)
            sv.show()
            self._pump()
            self.assertGreater(sv.table_members.height(), 350)
            self.assertEqual((sv.phone_mockup.width(), sv.phone_mockup.height()), (320, 560))
            sv.close()

    def test_04_login_view_narrow_no_hscroll_and_horizontal_wheel_normalizer_qa(self):
        from PyQt6.QtWidgets import QLabel, QWidget
        from PyQt6.QtCore import Qt, QPoint, QPointF
        from PyQt6.QtGui import QWheelEvent
        from nemov.utils.theme_manager import ThemeManager
        from nemov.utils.ui_scaling import HorizontalWheelNormalizer
        from nemov.views.login_view import LoginView

        ThemeManager.apply_theme("crimson_fury", self.app)

        # 1) Narrow LoginView (510x580) with vertical scrollbar must NOT trigger horizontal scrollbar
        for w, h in ((510, 580), (420, 500)):
            lv = LoginView()
            lv.resize(w, h)
            lv.show()
            self._pump()
            sa = lv.findChild(QScrollArea, "login_host_scroll")
            hsb = sa.horizontalScrollBar()
            vsb = sa.verticalScrollBar()
            self.assertTrue(vsb.isVisible())
            self.assertEqual(hsb.maximum(), 0)
            self.assertFalse(hsb.isVisible())
            lv.close()

        # 2) HorizontalWheelNormalizer flips horizontal delta cleanly even from nested child widget
        flt = HorizontalWheelNormalizer(self.app)
        self.app.installEventFilter(flt)
        try:
            sa = QScrollArea()
            sa.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            sa.resize(200, 200)
            content = QWidget()
            content.setFixedSize(600, 200)
            lbl = QLabel("تست", content)
            sa.setWidget(content)
            sa.show()
            self._pump()

            hsb = sa.horizontalScrollBar()
            hsb.setValue(100)
            # Win32 WM_MOUSEHWHEEL +120 (touchpad swipe left -> scroll right) must INCREASE hsb.value()
            ev = QWheelEvent(
                QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(120, 0),
                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False
            )
            QApplication.sendEvent(lbl, ev)
            self._pump()
            self.assertGreater(hsb.value(), 100)
            prev_val = hsb.value()

            # Consecutive identical timestamp=0 swipe in opposite direction (-120) must DECREASE hsb.value()
            ev2 = QWheelEvent(
                QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(-120, 0),
                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False
            )
            QApplication.sendEvent(lbl, ev2)
            self._pump()
            self.assertLess(hsb.value(), prev_val)
            sa.close()
        finally:
            self.app.removeEventFilter(flt)

    def test_06_dashboard_quick_buttons_and_athlete_column_no_clipping_qa(self):
        from unittest.mock import patch
        from PyQt6.QtGui import QFontMetrics
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.dashboard_view import DashboardView

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        sample_members = [
            (1, "شاگرد تست شماره یک", "محراب حاجی پور", "09120000001", "۱۴۰۵/۰۸/۰۱", "۸ جلسه در ماه", "منقضی شده", "", "inactive"),
            (2, "ابوالفضل حسینی راد", "محراب حاجی پور", "09120000002", "۱۴۰۵/۰۹/۰۵", "۱۲ جلسه در ماه", "نزدیک انقضا", "", "warning"),
            (3, "Reza Ahmadi", "مربی دوم", "09120000003", "۱۴۰۵/۱۱/۱۰", "۱۶ جلسه در ماه", "فعال", "", "active"),
        ]

        dv = DashboardView()
        dv.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        with patch.object(dv, "refresh_dashboard", return_value=None):
            dv.show()
            dv.table.setRowCount(0)
            # Populate table rows directly in the same structure used by refresh_dashboard
            from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QTableWidgetItem
            dv.table.setRowCount(len(sample_members))
            for r_idx, (mid, name, coach, phone, exp, mem_type, status_txt, _, _) in enumerate(sample_members):
                dv.table.setRowHeight(r_idx, 50)
                cw = QWidget()
                cw.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                cl = QHBoxLayout(cw)
                cl.setContentsMargins(6, 2, 6, 2)
                cl.setSpacing(8)
                av = QLabel()
                av.setFixedSize(36, 36)
                lbl_n = QLabel(name)
                lbl_n.setObjectName("athleteNameLabel")
                cl.addWidget(av)
                cl.addWidget(lbl_n, 1)
                dv.table.setCellWidget(r_idx, 0, cw)
                dv.table.setItem(r_idx, 1, QTableWidgetItem(coach))
                dv.table.setItem(r_idx, 2, QTableWidgetItem(phone))
                dv.table.setItem(r_idx, 3, QTableWidgetItem(mem_type))
                dv.table.setItem(r_idx, 4, QTableWidgetItem(exp))
                dv.table.setItem(r_idx, 5, QTableWidgetItem(status_txt))

            for idx, (w, h) in enumerate([(1120, 740), (880, 680), (760, 620), (500, 560)]):
                dv.resize(w, h)
                dv._relayout_quick_actions()
                dv._adjust_table_columns()
                self._pump()

                # Zero clipping on all quick-action buttons + strict vertical centering with label inside actions_frame
                for btn in dv._quick_buttons:
                    fm = QFontMetrics(btn.font())
                    text_w = fm.horizontalAdvance(btn.text())
                    self.assertGreaterEqual(btn.width(), text_w + 10, f"Button '{btn.text()}' clipped at width={w}: btn.w={btn.width()}, text_w={text_w}")
                if not dv._quick_rows_mode:
                    frame_cy = dv.actions_frame.height() / 2.0
                    lbl_cy = dv.lbl_quick.geometry().center().y()
                    btn_cy = dv.btn_add_member.geometry().center().y()
                    self.assertLessEqual(abs(lbl_cy - btn_cy), 3, f"Label and buttons misaligned vertically: lbl={lbl_cy}, btn={btn_cy}")
                    self.assertLessEqual(abs(btn_cy - frame_cy), 3, f"Buttons not vertically centered in card: btn={btn_cy}, frame={frame_cy}")

                # Athlete column retains readable floor >= 200px so names never blur/vanish
                self.assertGreaterEqual(dv.table.columnWidth(0), 200, f"Athlete column too narrow at w={w}: {dv.table.columnWidth(0)}")
                if idx == 0:
                    self.assertFalse(dv._quick_rows_mode)
                    dv.grab().save(str(qa_dir / "dashboard_wide_qa.png"))
                elif w == 500:
                    self.assertTrue(dv._quick_rows_mode)
                    dv.grab().save(str(qa_dir / "dashboard_narrow_qa.png"))
            dv.close()

    def _pump_ms(self, ms: int = 320):
        step = 20
        for _ in range(max(1, ms // step)):
            loop = QEventLoop()
            QTimer.singleShot(step, loop.quit)
            loop.exec()
            self.app.processEvents()

    def test_07_sidebar_collapse_expand_and_notifications_qa(self):
        from unittest.mock import patch
        from PyQt6.QtCore import QPoint
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.components.sidebar import Sidebar

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        with patch("nemov.services.branding_service.BrandingService.get_club_info", return_value={"club_name": "", "club_logo_path": ""}), \
             patch("nemov.services.notification_service.NotificationService.sync_and_get_unread_sidebar_notifications", return_value=([(SimpleNamespace(id=1, full_name="شاگرد نمونه"), 0, 10)], [])):
            sb = Sidebar()
            sb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            sb.resize(230, 740)
            sb.show()
            sb.refresh_notifications()
            self._pump()

            # Expanded state assertions: transparent header, logo -> ~15px -> "نِمو"
            self.assertFalse(sb.is_collapsed())
            self.assertEqual(sb.width(), Sidebar.EXPANDED_WIDTH)
            self.assertTrue(sb.expanded_header_widget.isVisible())
            self.assertFalse(sb.collapsed_header_widget.isVisible())
            logo_left = sb.logo_lbl.mapTo(sb, QPoint(0, 0)).x()
            title_right = sb.title_lbl.mapTo(sb, QPoint(sb.title_lbl.width() - 1, 0)).x()
            gap = logo_left - title_right
            self.assertGreaterEqual(gap, 10)
            self.assertLessEqual(gap, 22)
            sb.grab().save(str(qa_dir / "sidebar_expanded_qa.png"))

            # Animated collapse
            toggled_events = []
            sb.collapse_toggled.connect(toggled_events.append)
            sb.btn_toggle_sidebar.click()
            self._pump_ms(320)

            self.assertTrue(sb.is_collapsed())
            self.assertEqual(toggled_events, [True])
            self.assertEqual(sb.width(), Sidebar.COLLAPSED_WIDTH)
            self.assertTrue(sb.collapsed_header_widget.isVisible())
            self.assertFalse(sb.expanded_header_widget.isVisible())
            self.assertTrue(sb.btn_collapsed_notif.isVisible())
            self.assertEqual(sb.buttons["dashboard"].toolTip(), "داشبورد")
            self.assertEqual(sb.btn_logout.text(), "🚪")
            self.assertEqual(sb.btn_dev.text(), "👨‍💻")
            sb.grab().save(str(qa_dir / "sidebar_collapsed_qa.png"))

            ThemeManager.apply_theme("olympic_white", self.app)
            self._pump()
            sb.grab().save(str(qa_dir / "sidebar_collapsed_light_qa.png"))

            # Clicking compact notif pill smoothly expands sidebar back
            ThemeManager.apply_theme("crimson_fury", self.app)
            sb.btn_collapsed_notif.click()
            self._pump_ms(320)
            self.assertFalse(sb.is_collapsed())
            self.assertEqual(sb.width(), Sidebar.EXPANDED_WIDTH)
            self.assertTrue(sb.unified_notif_card.isVisible())
            sb.close()

    def test_08_main_window_auto_collapse_and_manual_override_qa(self):
        from nemov.utils.theme_manager import ThemeManager
        from nemov.views.main_window import MainWindow
        from nemov.views.components.sidebar import Sidebar

        qa_dir = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6\scratch")
        qa_dir.mkdir(parents=True, exist_ok=True)
        ThemeManager.apply_theme("crimson_fury", self.app)

        mw = MainWindow()
        mw.resize(1180, 620)
        mw.show()
        self._pump()
        self.assertFalse(mw.sidebar.is_collapsed())
        mw.grab().save(str(qa_dir / "mainwindow_expanded_qa.png"))

        # Shrink below 1050px -> auto-collapse triggers smoothly
        mw.resize(960, 600)
        self._pump()
        self._pump_ms(320)
        self.assertTrue(mw.sidebar.is_collapsed())
        self.assertEqual(mw.sidebar.width(), Sidebar.COLLAPSED_WIDTH)
        mw.grab().save(str(qa_dir / "mainwindow_collapsed_qa.png"))

        # Widen >= 1100px -> auto-expands back
        mw.resize(1180, 620)
        self._pump()
        self._pump_ms(320)
        self.assertFalse(mw.sidebar.is_collapsed())

        # Manual user collapse while wide -> stays collapsed even if resized wider
        mw.sidebar.btn_toggle_sidebar.click()
        self._pump_ms(320)
        mw.resize(1220, 620)
        self._pump()
        self.assertTrue(mw.sidebar.is_collapsed())
        mw.close()


if __name__ == "__main__":
    unittest.main()
