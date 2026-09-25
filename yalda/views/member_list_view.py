import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from yalda.services.member_service import MemberService
from yalda.views.member_form_dialog import MemberFormDialog
from yalda.utils.image_utils import get_circular_pixmap, resolve_image_path
from yalda.views.components.circular_image_preview_dialog import CircularImagePreviewDialog
from yalda.views.components.undo_delete_banner import UndoDeleteBanner

class MemberListView(QWidget):
    open_member_detail = pyqtSignal(int) # Member ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title & Add Button
        header = QHBoxLayout()
        self.lbl_title = QLabel("👥 مدیریت اعضای باشگاه")
        self.lbl_title.setObjectName("h1")

        btn_add = QPushButton("➕ ثبت ورزشکار جدید")
        btn_add.clicked.connect(self.open_add_dialog)

        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(btn_add)
        layout.addLayout(header)

        # Search & Filter Controls Bar
        controls = QHBoxLayout()
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("جستجو بر اساس نام یا شماره تلفن...")
        self.txt_search.textChanged.connect(self.load_members)

        self.combo_status = QComboBox()
        self.combo_status.addItem("همه اعضا", "all")
        self.combo_status.addItem("اعضای فعال", "active")
        self.combo_status.addItem("اعضای در آستانه انقضا", "expiring_soon")
        self.combo_status.addItem("اعضای انقضا یافته", "expired")
        self.combo_status.addItem("اعضای آرشیو شده", "archived")
        self.combo_status.currentIndexChanged.connect(self.load_members)

        self.chk_select_all = QCheckBox("انتخاب همه")
        self.chk_select_all.toggled.connect(self.toggle_select_all)

        self.btn_bulk_delete = QPushButton("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setEnabled(False)
        self.btn_bulk_delete.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #4B5563;
                color: #9CA3AF;
            }
        """)
        self.btn_bulk_delete.clicked.connect(self.bulk_delete_members)

        controls.addWidget(QLabel("جستجو:"))
        controls.addWidget(self.txt_search)
        controls.addWidget(QLabel("وضعیت:"))
        controls.addWidget(self.combo_status)
        controls.addWidget(self.chk_select_all)
        controls.addWidget(self.btn_bulk_delete)
        layout.addLayout(controls)

        # Members Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "انتخاب", "ورزشکار", "مربی مربوطه", "شماره تماس", "نوع عضویت", "تاریخ انقضا", "وضعیت", "عملیات"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(44)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 52)

        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(2, 115)

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(3, 106)

        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(4, 104)

        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(5, 95)

        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(6, 172)

        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 228)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table, 1)

        self.undo_banner = UndoDeleteBanner(self)
        layout.addWidget(self.undo_banner)

        self.load_members()

    def _adjust_table_columns(self):
        """Proportionally scales columns based on available table width so NO column is ever truncated."""
        vw = self.table.viewport().width()
        if vw <= 100:
            vw = max(960, self.width() - 40)
        if vw < 1100:
            # TV HDMI / Compact Laptop mode: exact fit for all 8 columns with zero truncation
            self.table.setColumnWidth(0, 52)
            self.table.setColumnWidth(2, 112)
            self.table.setColumnWidth(3, 104)
            self.table.setColumnWidth(4, 104)
            self.table.setColumnWidth(5, 95)
            self.table.setColumnWidth(6, 172)
            self.table.setColumnWidth(7, 228)
        else:
            # Standard Desktop / Wide Monitor mode: scale secondary columns generously
            extra = vw - 1100
            self.table.setColumnWidth(0, 52)
            self.table.setColumnWidth(2, min(165, 120 + int(extra * 0.12)))
            self.table.setColumnWidth(3, min(145, 112 + int(extra * 0.08)))
            self.table.setColumnWidth(4, min(145, 110 + int(extra * 0.08)))
            self.table.setColumnWidth(5, min(130, 100 + int(extra * 0.06)))
            self.table.setColumnWidth(6, min(190, 160 + int(extra * 0.10)))
            self.table.setColumnWidth(7, 232)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_table_columns()

    def open_avatar_preview(self, photo_path: str, member_name: str):
        """Opens a circular animated popup zoom of athlete's photo."""
        resolved = resolve_image_path(photo_path)
        if resolved:
            dlg = CircularImagePreviewDialog(resolved, title=member_name, parent=self)
            dlg.exec()

    def load_members(self):
        search_query = self.txt_search.text().strip()
        status_filter = self.combo_status.currentData()
        members = MemberService.get_all_members(search_query=search_query, status_filter=status_filter)

        total_members = MemberService.get_all_members(status_filter="all")
        total_count = len(total_members)
        fa_total = str(total_count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        if hasattr(self, 'lbl_title'):
            if search_query or status_filter != "all":
                fa_filtered = str(len(members)).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
                self.lbl_title.setText(f"👥 مدیریت اعضای باشگاه ({fa_filtered} از {fa_total} نفر)")
            else:
                self.lbl_title.setText(f"👥 مدیریت اعضای باشگاه ({fa_total} نفر)")

        MEMBERSHIP_TYPE_MAP = {
            "12_sessions": "۱۲ جلسه در ماه",
            "8_sessions": "۸ جلسه در ماه",
            "16_sessions": "۱۶ جلسه در ماه",
            "20_sessions": "۲۰ جلسه در ماه",
            "daily_access": "همه روزه"
        }

        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(False)
        self.chk_select_all.blockSignals(False)
        self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
        self.btn_bulk_delete.setEnabled(False)

        self.table.setRowCount(0)
        self.table.setRowCount(len(members))
        for row, m in enumerate(members):
            # Column 0: Checkbox
            chk_w = QWidget()
            chk_w.setStyleSheet("background: transparent;")
            chk_l = QHBoxLayout(chk_w)
            chk_l.setContentsMargins(0, 0, 0, 0)
            chk_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("item_id", m.id)
            chk.setProperty("item_name", m.full_name)
            chk.toggled.connect(self.on_row_checkbox_toggled)
            chk_l.addWidget(chk)
            self.table.setCellWidget(row, 0, chk_w)

            # Column 1: Circular Avatar + Name
            cell_w = QWidget()
            cell_w.setStyleSheet("background: transparent;")
            cell_l = QHBoxLayout(cell_w)
            cell_l.setContentsMargins(4, 2, 4, 2)
            cell_l.setSpacing(6)
            cell_l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            lbl_avatar = QLabel()
            lbl_avatar.setFixedSize(34, 34)
            lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

            has_valid_photo = False
            resolved_photo = resolve_image_path(m.photo_path)
            if resolved_photo:
                pix = QPixmap(resolved_photo)
                if not pix.isNull():
                    circ_pix = get_circular_pixmap(pix, 34, border_color="#8B0000", border_width=2)
                    lbl_avatar.setPixmap(circ_pix)
                    lbl_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
                    lbl_avatar.setToolTip(f"برای مشاهده تصویر بزرگ‌تر «{m.full_name}» کلیک کنید")
                    lbl_avatar.mousePressEvent = lambda e, p=resolved_photo, n=m.full_name: self.open_avatar_preview(p, n)
                    has_valid_photo = True

            if not has_valid_photo:
                lbl_avatar.setText("👤")
                lbl_avatar.setStyleSheet("""
                    QLabel {
                        background-color: #242424;
                        border: 1px solid #444444;
                        border-radius: 17px;
                        color: #777777;
                        font-size: 15px;
                    }
                """)

            lbl_name = QLabel(m.full_name)
            lbl_name.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: bold; background: transparent;")
            lbl_name.setToolTip(m.full_name)
            cell_w.setToolTip(m.full_name)

            cell_l.addWidget(lbl_avatar)
            cell_l.addWidget(lbl_name)
            cell_l.addStretch()

            self.table.setCellWidget(row, 1, cell_w)

            # Column 2: Trainer
            item_trainer = QTableWidgetItem(m.trainer_name or "-")
            item_trainer.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, item_trainer)

            # Column 3: Phone
            item_phone = QTableWidgetItem(m.phone or "-")
            item_phone.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, item_phone)

            # Column 4: Membership Type
            m_type_fa = MEMBERSHIP_TYPE_MAP.get(m.membership_type, m.membership_type or "-")
            item_type = QTableWidgetItem(m_type_fa)
            item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, item_type)

            # Column 5: Expiration Date
            item_exp = QTableWidgetItem(m.membership_expire_shamsi or "-")
            item_exp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, item_exp)

            # Column 6: Status (Synced with DashboardView)
            from yalda.utils.jalali_date import days_until_expire
            days_left = days_until_expire(m.membership_expire_shamsi)
            if m.status == "archived":
                status_text = "آرشیو شده ⚪"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.gray)
            elif days_left < 0 or m.status == "expired":
                status_text = "انقضا یافته 🔴"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.red)
            elif 0 <= days_left <= 5:
                status_text = f"در آستانه انقضا ({days_left} روز) 🟡"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.yellow)
            else:
                status_text = f"فعال ({days_left} روز باقی‌مانده) 🟢"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.green)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, status_item)

            # Column 7: Actions Button Widget (Index 7: View File, Edit, Delete)
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.setSpacing(5)

            btn_view = QPushButton("📋 پرونده")
            btn_view.setFixedHeight(30)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
            btn_view.clicked.connect(lambda _, mid=m.id: self.open_member_detail.emit(mid))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setFixedHeight(30)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #B45309; }
            """)
            btn_edit.clicked.connect(lambda _, member=m: self.open_edit_dialog(member))

            btn_delete = QPushButton("🗑️ حذف")
            btn_delete.setFixedHeight(30)
            btn_delete.setToolTip("حذف پرونده ورزشکار")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 2px 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #B91C1C; }
            """)
            btn_delete.clicked.connect(lambda _, member=m: self.delete_member(member))

            btn_layout.addWidget(btn_view)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)

            self.table.setCellWidget(row, 7, btn_container)

    def toggle_select_all(self, checked):
        for r in range(self.table.rowCount()):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.on_row_checkbox_toggled()

    def on_row_checkbox_toggled(self):
        count = len(self.get_selected_member_ids())
        total = self.table.rowCount()
        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(count == total if total > 0 else False)
        self.chk_select_all.blockSignals(False)

        if count > 0:
            fa_num = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
            self.btn_bulk_delete.setText(f"🗑️ حذف انتخاب‌شده‌ها ({fa_num})")
            self.btn_bulk_delete.setEnabled(True)
        else:
            self.btn_bulk_delete.setText("🗑️ حذف انتخاب‌شده‌ها")
            self.btn_bulk_delete.setEnabled(False)

    def get_selected_member_ids(self):
        selected_ids = []
        for r in range(self.table.rowCount()):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(chk.property("item_id"))
        return selected_ids

    def _hide_rows_by_ids(self, ids):
        id_set = set(ids)
        for r in range(self.table.rowCount() - 1, -1, -1):
            cell_w = self.table.cellWidget(r, 0)
            if cell_w:
                chk = cell_w.findChild(QCheckBox)
                if chk and chk.property("item_id") in id_set:
                    self.table.hideRow(r)

    def bulk_delete_members(self):
        selected_ids = self.get_selected_member_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        fa_count = str(count).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        reply = QMessageBox.question(
            self, "تایید حذف گروهی اعضای باشگاه",
            f"آیا از حذف کامل پرونده {fa_count} ورزشکار انتخاب‌شده اطمینان دارید؟ تمام سوابق پزشکی و برنامه‌های آنان نیز پاک خواهد شد.\n\nنکته: پس از حذف، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_rows_by_ids(selected_ids)

        def commit_delete(ids):
            for mid in ids:
                try:
                    MemberService.delete_member(mid)
                except Exception:
                    pass
            self.load_members()

        def undo_delete(ids):
            self.load_members()

        self.undo_banner.start_countdown(
            item_count=count,
            pending_items=selected_ids,
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label="ورزشکار"
        )

    def delete_member(self, member):
        reply = QMessageBox.question(
            self, "تایید حذف ورزشکار",
            f"آیا از حذف کامل پرونده ورزشکار «{member.full_name}» اطمینان دارید؟ تمام سوابق پزشکی و برنامه‌های وی نیز پاک خواهد شد.\n\nنکته: پس از تایید، ۱۰ ثانیه فرصت بازگردانی (Undo) خواهید داشت.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._hide_rows_by_ids([member.id])

        def commit_delete(ids):
            for mid in ids:
                try:
                    MemberService.delete_member(mid)
                except Exception as e:
                    QMessageBox.critical(self, "خطا", f"خطا در حذف ورزشکار: {str(e)}")
            self.load_members()

        def undo_delete(ids):
            self.load_members()

        self.undo_banner.start_countdown(
            item_count=1,
            pending_items=[member.id],
            on_commit=commit_delete,
            on_undo=undo_delete,
            item_label=f"«{member.full_name}»"
        )

    def open_add_dialog(self):
        try:
            dialog = MemberFormDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_members()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطایی رخ داد: {str(e)}")

    def open_edit_dialog(self, member):
        try:
            dialog = MemberFormDialog(self, member_data=member)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_members()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطایی رخ داد: {str(e)}")

