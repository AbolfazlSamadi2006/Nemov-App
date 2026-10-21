import os
import tempfile
import time
import uuid
import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox, QCheckBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap


class CameraCaptureDialog(QDialog):
    """
    Dialog for live laptop/webcam camera stream and snapshot capture.
    Designed for 100% stability across all Windows laptop webcams (Integrated, USB, Virtual).
    """
    def __init__(self, parent=None, title="ثبت تصویر با دوربین"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(700, 600)

        self.cap = None
        self.timer = QTimer(self)
        self.timer.setInterval(33)  # ~30 FPS smooth update rate
        self.timer.timeout.connect(self.update_frame)

        self._is_processing_frame = False
        self.current_frame_rgb = None
        self.captured_bgr_frame = None
        self.captured_file_path = None
        self.active_cam_index = 0

        self.init_ui()
        self.detect_and_start_camera()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header bar (Camera selector + Rescan + Flip option)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        lbl_cam = QLabel("انتخاب دوربین:")
        lbl_cam.setStyleSheet("font-weight: bold; font-size: 13px;")

        self.combo_cam = QComboBox()
        self.combo_cam.setMinimumWidth(180)
        self.combo_cam.currentIndexChanged.connect(self.on_camera_selected)

        self.btn_rescan = QPushButton("🔄 جستجوی مجدد")
        self.btn_rescan.setObjectName("secondary_button")
        self.btn_rescan.setToolTip("جستجوی مجدد دوربین‌های متصل به سیستم")
        self.btn_rescan.setStyleSheet("font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        self.btn_rescan.clicked.connect(self.populate_cameras)

        self.chk_flip = QCheckBox("تصویر واقعی (غیرآینه‌ای)")
        self.chk_flip.setChecked(True)
        self.chk_flip.setStyleSheet("font-size: 13px;")

        header_layout.addWidget(lbl_cam)
        header_layout.addWidget(self.combo_cam)
        header_layout.addWidget(self.btn_rescan)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.chk_flip)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Live Video Preview Display Area
        self.lbl_video = QLabel("در حال اتصال به دوربین...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setFixedSize(670, 460)
        self.lbl_video.setWordWrap(True)
        self.lbl_video.setStyleSheet(
            "background-color: #000000; color: #aaaaaa; border: 2px solid #333333; border-radius: 10px; font-size: 14px; padding: 20px;"
        )
        layout.addWidget(self.lbl_video)

        # Control Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_capture = QPushButton("📸 ثبت عکس")
        self.btn_capture.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 8px 22px; background-color: #0088cc; color: white; border-radius: 6px;"
        )
        self.btn_capture.clicked.connect(self.take_snapshot)

        self.btn_retake = QPushButton("🔄 عکس مجدد")
        self.btn_retake.setObjectName("secondary_button")
        self.btn_retake.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 8px 18px; background-color: #555555; color: white; border-radius: 6px;"
        )
        self.btn_retake.clicked.connect(self.resume_camera_stream)
        self.btn_retake.hide()

        self.btn_edit = QPushButton("✂️ ویرایش و کراپ")
        self.btn_edit.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 8px 18px; background-color: #0088cc; color: white; border-radius: 6px;"
        )
        self.btn_edit.clicked.connect(self.edit_snapshot)
        self.btn_edit.hide()

        self.btn_confirm = QPushButton("✅ تایید و استفاده")
        self.btn_confirm.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 8px 22px; background-color: #2e7d32; color: white; border-radius: 6px;"
        )
        self.btn_confirm.clicked.connect(self.confirm_snapshot)
        self.btn_confirm.hide()

        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setObjectName("secondary_button")
        self.btn_cancel.setStyleSheet(
            "font-size: 14px; padding: 8px 18px; border-radius: 6px;"
        )
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_capture)
        btn_layout.addWidget(self.btn_retake)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def detect_and_start_camera(self):
        """Entry point called during initialization."""
        self.populate_cameras()

    def populate_cameras(self):
        """Scan available video devices and open the first working camera."""
        self.stop_camera()
        self.combo_cam.blockSignals(True)
        self.combo_cam.clear()

        devices_found = []

        # 1. Try QtMultimedia for real device names
        try:
            from PyQt6.QtMultimedia import QMediaDevices
            qt_devices = QMediaDevices.videoInputs()
            for idx, dev in enumerate(qt_devices):
                desc = dev.description() or f"دوربین {idx + 1}"
                devices_found.append((desc, idx))
        except Exception:
            pass

        # 2. If QtMultimedia found nothing or is unavailable, probe via OpenCV
        if not devices_found:
            for i in range(3):
                cap = None
                try:
                    if os.name == 'nt':
                        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                        if not cap.isOpened():
                            cap.release()
                            cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
                    else:
                        cap = cv2.VideoCapture(i)

                    if cap and cap.isOpened():
                        devices_found.append((f"دوربین {i + 1}", i))
                except Exception:
                    pass
                finally:
                    if cap:
                        cap.release()

        # 3. Populate ComboBox
        if devices_found:
            for label, cam_id in devices_found:
                self.combo_cam.addItem(label, cam_id)
            self.combo_cam.blockSignals(False)
            self.btn_capture.setEnabled(True)
            self.open_camera(devices_found[0][1])
        else:
            self.combo_cam.addItem("هیچ دوربینی یافت نشد", None)
            self.combo_cam.blockSignals(False)
            self.btn_capture.setEnabled(False)
            self.lbl_video.setText(
                "❌ هیچ دوربینی شناسایی نشد.\n\n"
                "• لطفاً از اتصال وبکم یا باز بودن درپوش دوربین لپ‌تاپ مطمئن شوید.\n"
                "• بررسی کنید که دسترسی به دوربین در تنظیمات ویندوز مجاز باشد.\n"
                "• یا می‌توانید تصویر موردنظر را مستقیماً از فایل‌های سیستم انتخاب کنید."
            )

    def open_camera(self, cam_index: int):
        """
        Open video capture with multi-backend fallback on Windows (DirectShow -> MediaFoundation -> Default).
        """
        if cam_index is None:
            return

        self.stop_camera()
        self.active_cam_index = cam_index
        self.lbl_video.setText("در حال برقراری ارتباط با دوربین...")

        # Backends to try in priority order
        if os.name == 'nt':
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        opened_cap = None
        for backend in backends:
            try:
                cap = cv2.VideoCapture(cam_index, backend)
                if cap.isOpened():
                    # Attempt quick frame read to verify backend actually produces data
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        opened_cap = cap
                        break
                    else:
                        cap.release()
            except Exception:
                if 'cap' in locals() and cap:
                    cap.release()

        if opened_cap is not None:
            self.cap = opened_cap
            # Safely request standard resolution and frame rate
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            except Exception:
                pass
            try:
                self.cap.set(cv2.CAP_PROP_FPS, 30)
            except Exception:
                pass

            self.btn_capture.setEnabled(True)
            self.timer.start()
        else:
            self.btn_capture.setEnabled(False)
            self.lbl_video.setText(
                "❌ امکان دریافت تصویر از این دوربین وجود ندارد.\n\n"
                "دوربین ممکن است توسط برنامه دیگری (مانند Teams، Zoom، یا مرورگر) در حال استفاده باشد."
            )

    def on_camera_selected(self, index: int):
        cam_id = self.combo_cam.currentData()
        if cam_id is not None:
            self.open_camera(cam_id)

    def update_frame(self):
        if self._is_processing_frame or not self.cap or not self.cap.isOpened():
            return

        self._is_processing_frame = True
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                if self.chk_flip.isChecked():
                    frame = cv2.flip(frame, 1)

                self.captured_bgr_frame = frame.copy()

                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_frame = np.ascontiguousarray(rgb_frame)

                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w

                # Memory-safe QImage creation with full copy
                qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                pixmap = QPixmap.fromImage(qimg)

                scaled_pixmap = pixmap.scaled(
                    self.lbl_video.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_video.setPixmap(scaled_pixmap)
        except Exception:
            pass
        finally:
            self._is_processing_frame = False

    def take_snapshot(self):
        if self.captured_bgr_frame is not None:
            self.timer.stop()
            self.btn_capture.hide()
            self.btn_retake.show()
            self.btn_edit.show()
            self.btn_confirm.show()

    def resume_camera_stream(self):
        self.btn_retake.hide()
        self.btn_edit.hide()
        self.btn_confirm.hide()
        self.btn_capture.show()
        if self.cap and self.cap.isOpened():
            self.timer.start()

    def edit_snapshot(self):
        if self.captured_bgr_frame is None:
            return
        try:
            temp_dir = tempfile.gettempdir()
            filename = f"cam_snapshot_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
            save_path = os.path.join(temp_dir, filename)

            success, enc_buffer = cv2.imencode(".jpg", self.captured_bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            if success:
                with open(save_path, "wb") as f:
                    f.write(enc_buffer.tobytes())
            else:
                cv2.imwrite(save_path, self.captured_bgr_frame)

            from nemov.views.components.image_editor_dialog import ImageEditorDialog
            editor = ImageEditorDialog(self, image_path=save_path, title=self.windowTitle(), allow_retake=True)
            if editor.exec() == QDialog.DialogCode.Accepted and editor.result_image_path:
                self.captured_file_path = editor.result_image_path
                self.stop_camera()
                self.accept()
            elif editor.retake_triggered:
                self.resume_camera_stream()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بازگشایی ویرایشگر تصویر: {str(e)}")

    def confirm_snapshot(self):
        if self.captured_bgr_frame is not None:
            try:
                # Save frame to a temporary file safely using imencode (Unicode/Persian path immune)
                temp_dir = tempfile.gettempdir()
                filename = f"cam_snapshot_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
                save_path = os.path.join(temp_dir, filename)

                success, enc_buffer = cv2.imencode(".jpg", self.captured_bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                if success:
                    with open(save_path, "wb") as f:
                        f.write(enc_buffer.tobytes())
                    self.captured_file_path = save_path
                else:
                    cv2.imwrite(save_path, self.captured_bgr_frame)
                    self.captured_file_path = save_path

                self.stop_camera()
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در ذخیره‌سازی تصویر: {str(e)}")

    def stop_camera(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self._is_processing_frame = False

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)

    def reject(self):
        self.stop_camera()
        super().reject()
