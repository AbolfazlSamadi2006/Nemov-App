from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt, QRectF

def get_circular_pixmap(source_pixmap: QPixmap, size: int, border_color: str = "#8B0000", border_width: int = 3) -> QPixmap:
    """
    Center-crops a QPixmap into a square and clips it into a perfect anti-aliased circle,
    with an optional elegant dark red border ring.
    """
    if source_pixmap.isNull():
        return source_pixmap

    w, h = source_pixmap.width(), source_pixmap.height()
    min_dim = min(w, h)
    crop_rect = QRectF((w - min_dim) / 2, (h - min_dim) / 2, min_dim, min_dim)
    cropped = source_pixmap.copy(crop_rect.toRect())
    scaled = cropped.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)

    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    
    # Draw high quality anti-aliased border ring
    painter.setClipping(False)
    if border_width > 0 and border_color:
        pen = QPen(QColor(border_color))
        pen.setWidth(border_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        offset = border_width / 2.0
        painter.drawEllipse(QRectF(offset, offset, size - border_width, size - border_width))

    painter.end()

    return out


def resolve_image_path(path_str: str) -> str:
    """
    Intelligently resolves an image path whether it is:
    1. A valid absolute path that exists on disk.
    2. A relative path to DATA_DIR, UPLOADS_DIR, or PROFILE_PHOTOS_DIR.
    3. A simple filename (e.g. 'trainer_3223e5d6.jpg') located in any candidate
       data/uploads folder (runtime DATA_DIR, APPDATA_DATA_DIR, installed Programs directory).
    Returns the resolved existing full path as a string, or None if not found.
    """
    if not path_str:
        return None

    path_str = str(path_str).strip()
    if not path_str:
        return None

    import os
    from pathlib import Path
    import config

    p = Path(path_str)
    if p.exists() and p.is_file():
        return str(p.resolve())

    filename = p.name
    candidate_dirs = [
        getattr(config, "BRANDING_DIR", config.DATA_DIR / "branding"),
        config.DATA_DIR / "branding",
        config.APPDATA_DATA_DIR / "branding",
        config.PROFILE_PHOTOS_DIR,
        config.EXERCISE_MEDIA_DIR,
        config.DATA_DIR / "uploads" / "exercise-media",
        config.DATA_DIR / "uploads" / "profile-photos",
        config.DATA_DIR / "uploads",
        config.APPDATA_DATA_DIR / "uploads" / "exercise-media",
        config.APPDATA_DATA_DIR / "uploads" / "profile-photos",
        config.APPDATA_DATA_DIR / "uploads",
        config.UPLOADS_DIR,
        config.BASE_DIR / "resources" / "images",
        config.BASE_DIR / "resources" / "images" / "exercise_thumbnails",
    ]

    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidate_dirs.append(Path(sys._MEIPASS) / "resources" / "images" / "exercise_thumbnails")
        candidate_dirs.append(Path(sys._MEIPASS) / "resources" / "images")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        installed_nemov = Path(local_app_data) / "Programs" / "Nemov" / "data"
        candidate_dirs.append(installed_nemov / "branding")
        installed_data = Path(local_app_data) / "Programs" / "YaldaGym" / "data" / "uploads"
        candidate_dirs.append(installed_data / "exercise-media")
        candidate_dirs.append(installed_data / "profile-photos")
        candidate_dirs.append(installed_data)

    for d in candidate_dirs:
        try:
            cand = d / filename
            if cand.exists() and cand.is_file():
                return str(cand.resolve())
            cand_rel = d.parent / path_str
            if cand_rel.exists() and cand_rel.is_file():
                return str(cand_rel.resolve())
        except Exception:
            pass

    return None


def extract_video_thumbnail(video_path: str, output_thumb_path: str = None) -> str:
    """
    Extracts the first frame (frame 0) of a video file and saves it as a high quality JPEG image.
    Returns the path to the saved thumbnail, or None if extraction fails.
    """
    import cv2
    from pathlib import Path
    import os
    
    if not video_path or not os.path.exists(video_path):
        return None
        
    if not output_thumb_path:
        p = Path(video_path)
        output_thumb_path = str(p.parent / f"thumb_{p.stem}.jpg")
        
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None
            
        success, frame = cap.read()
        cap.release()
        
        if success and frame is not None:
            Path(output_thumb_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_thumb_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            return str(output_thumb_path)
    except Exception:
        pass

    return None


def get_app_icon_path() -> str:
    """Finds the absolute path to nemov.ico across all runtime and frozen environments."""
    import sys
    from pathlib import Path
    import config

    candidates = []

    # 1. sys._MEIPASS (PyInstaller frozen bundle internal)
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            candidates.append(Path(sys._MEIPASS) / "resources" / "icons" / "nemov.ico")
            candidates.append(Path(sys._MEIPASS) / "nemov.ico")
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "_internal" / "resources" / "icons" / "nemov.ico")
        candidates.append(exe_dir / "resources" / "icons" / "nemov.ico")
        candidates.append(exe_dir / "nemov.ico")

    # 2. config.BASE_DIR
    if hasattr(config, "BASE_DIR"):
        candidates.append(config.BASE_DIR / "resources" / "icons" / "nemov.ico")
        candidates.append(config.BASE_DIR / "_internal" / "resources" / "icons" / "nemov.ico")
        candidates.append(config.BASE_DIR / "nemov.ico")

    # 3. Current source directory
    source_dir = Path(__file__).resolve().parent.parent.parent
    candidates.append(source_dir / "resources" / "icons" / "nemov.ico")
    candidates.append(Path.cwd() / "resources" / "icons" / "nemov.ico")
    candidates.append(Path.cwd() / "nemov.ico")

    for c in candidates:
        try:
            if c and c.exists() and c.is_file():
                return str(c.resolve())
        except Exception:
            pass
    return None


def get_app_icon():
    """Returns a high-resolution QIcon for Nemov, populated with multi-resolution .ico and fallback .png."""
    import sys
    from pathlib import Path
    from PyQt6.QtGui import QIcon
    import config

    icon = QIcon()
    ico_path = get_app_icon_path()
    if ico_path:
        icon.addFile(ico_path)

    # Also add PNG candidates for crisp multi-resolution rendering
    png_candidates = []
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            png_candidates.append(Path(sys._MEIPASS) / "resources" / "images" / "nemov_logo.png")
        exe_dir = Path(sys.executable).resolve().parent
        png_candidates.append(exe_dir / "_internal" / "resources" / "images" / "nemov_logo.png")
        png_candidates.append(exe_dir / "resources" / "images" / "nemov_logo.png")

    if hasattr(config, "BASE_DIR"):
        png_candidates.append(config.BASE_DIR / "resources" / "images" / "nemov_logo.png")

    source_dir = Path(__file__).resolve().parent.parent.parent
    png_candidates.append(source_dir / "resources" / "images" / "nemov_logo.png")

    for png in png_candidates:
        try:
            if png and png.exists() and png.is_file():
                icon.addFile(str(png.resolve()))
                break
        except Exception:
            pass

    return icon


def apply_windows_taskbar_icon(window):
    """
    Applies the native Win32 window icon (WM_SETICON for ICON_BIG & ICON_SMALL, and SetClassLongPtr)
    directly to the HWND. This guarantees that regardless of whether the process was launched directly,
    via desktop shortcut, or from the NSIS installer finish page ("Run Nemov"), the Windows Taskbar,
    Alt-Tab switcher, and window titlebar reliably display the custom Nemov icon.
    """
    import sys
    if not sys.platform.startswith("win"):
        return

    try:
        ico_path = get_app_icon_path()
        if not ico_path:
            return

        hwnd = int(window.winId()) if hasattr(window, "winId") else None
        if not hwnd:
            return

        import ctypes
        user32 = ctypes.windll.user32
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010

        # Load standard 32x32 icon for Taskbar / Alt-Tab and 16x16 icon for Titlebar
        h_icon_big = user32.LoadImageW(None, str(ico_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_icon_small = user32.LoadImageW(None, str(ico_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if h_icon_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
        if h_icon_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)

        GCLP_HICON = -14
        GCLP_HICONSM = -34
        if hasattr(user32, "SetClassLongPtrW"):
            if h_icon_big:
                user32.SetClassLongPtrW(hwnd, GCLP_HICON, h_icon_big)
            if h_icon_small:
                user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, h_icon_small)
        elif hasattr(user32, "SetClassLongA"):
            if h_icon_big:
                user32.SetClassLongA(hwnd, GCLP_HICON, h_icon_big)
            if h_icon_small:
                user32.SetClassLongA(hwnd, GCLP_HICONSM, h_icon_small)
    except Exception:
        pass
