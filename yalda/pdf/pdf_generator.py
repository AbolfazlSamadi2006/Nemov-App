import os
import re
import zipfile
import logging
from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import config
from yalda.utils.jalali_date import get_today_shamsi

logger = logging.getLogger(__name__)

EMOJI_PATTERN = re.compile(
    "["
    "\U00010000-\U0010FFFF"
    "\u2600-\u27BF"
    "\u2300-\u23FF"
    "\u2B50-\u2B55"
    "\uFE00-\uFE0F"
    "\u200D"
    "]+",
    flags=re.UNICODE
)

_ASCII_TO_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def clean_for_pdf(text: str) -> str:
    """Removes unsupported unicode emojis, converts ASCII digits to Persian numerals for B Koodak/B Titr, and collapses redundant spaces."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", str(text))
    cleaned = re.sub(r":\s*:", ":", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.translate(_ASCII_TO_PERSIAN_DIGITS)
    return cleaned

def reshape_text(text: str) -> str:
    """Helper to reshape Persian text and apply BiDi algorithm for ReportLab rendering."""
    if not text:
        return ""
    try:
        cleaned = clean_for_pdf(text)
        reshaped = arabic_reshaper.reshape(cleaned)
        return get_display(reshaped, base_dir='R')
    except Exception:
        return str(text)

def reshape_multiline_text(text: str, max_width: float = 120, font_name: str = None, font_size: float = 8.5) -> str:
    """
    Wraps and reshapes Persian text line-by-line so that multi-line text
    is rendered by ReportLab in the correct top-to-bottom reading order.
    """
    if not text:
        return ""
    cleaned = clean_for_pdf(text)
    if not cleaned:
        return ""
    font = font_name or FONT_NAME
    words = cleaned.split()
    if not words:
        return ""

    lines = []
    curr_words = []
    for w in words:
        trial = " ".join(curr_words + [w])
        reshaped_trial = arabic_reshaper.reshape(trial)
        try:
            w_width = pdfmetrics.stringWidth(reshaped_trial, font, font_size)
        except Exception:
            w_width = len(trial) * (font_size * 0.55)

        if w_width <= max_width or not curr_words:
            curr_words.append(w)
        else:
            lines.append(" ".join(curr_words))
            curr_words = [w]

    if curr_words:
        lines.append(" ".join(curr_words))

    reshaped_lines = [get_display(arabic_reshaper.reshape(line), base_dir='R') for line in lines]
    return "<br/>".join(reshaped_lines)

# Register TTF Fonts for Persian PDF rendering (B Koodak for body, B Titr for titles/headers)
FONT_NAME = "Helvetica"
FONT_BOLD_NAME = "Helvetica-Bold"
TITLE_FONT_NAME = "Helvetica-Bold"
FALLBACK_FONT_NAME = "Helvetica-Bold"
_TITLE_FONT_CHARS = set()

def _find_font_file(filenames):
    import sys
    search_dirs = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        search_dirs.append(exe_dir / "_internal" / "resources" / "fonts")
        search_dirs.append(exe_dir / "resources" / "fonts")
        if hasattr(sys, "_MEIPASS"):
            search_dirs.append(Path(sys._MEIPASS) / "resources" / "fonts")
    search_dirs.extend([
        config.BASE_DIR / "resources" / "fonts",
        config.BASE_DIR / "_internal" / "resources" / "fonts",
        Path(__file__).resolve().parent.parent.parent / "resources" / "fonts",
        Path(__file__).resolve().parent.parent.parent / "_internal" / "resources" / "fonts",
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")),
        Path("C:/Windows/Fonts"),
    ])
    for d in search_dirs:
        for fname in filenames:
            p = d / fname
            if p.exists():
                return p
    return None

def setup_fonts():
    global FONT_NAME, FONT_BOLD_NAME, TITLE_FONT_NAME, FALLBACK_FONT_NAME, _TITLE_FONT_CHARS

    # 0. Register Segoe UI fallback for any symbols missing from B Titr / B Koodak
    fb_path = _find_font_file(["segoeuib.ttf", "segoeui.ttf", "Vazirmatn-Regular.ttf", "tahoma.ttf"])
    if fb_path:
        try:
            pdfmetrics.registerFont(TTFont("SegoeUI-Fallback", str(fb_path)))
            FALLBACK_FONT_NAME = "SegoeUI-Fallback"
        except Exception:
            FALLBACK_FONT_NAME = "Helvetica-Bold"

    # 1. Body Font: B Koodak (with Segoe UI / Vazirmatn fallback)
    body_path = _find_font_file(["BKoodakBd.ttf", "KOODAKB.TTF", "BKoodakO.ttf", "segoeui.ttf", "Vazirmatn-Regular.ttf"])
    if body_path:
        try:
            pdfmetrics.registerFont(TTFont("BKoodak", str(body_path)))
            FONT_NAME = "BKoodak"
            FONT_BOLD_NAME = "BKoodak"
            pdfmetrics.registerFontFamily("BKoodak", normal="BKoodak", bold="BKoodak")
            logger.info(f"PDF body font registered: {FONT_NAME} from {body_path}")
        except Exception as e:
            logger.warning(f"Could not register B Koodak font {body_path}: {e}")
            FONT_NAME = FALLBACK_FONT_NAME
            FONT_BOLD_NAME = FALLBACK_FONT_NAME

    # 2. Title & Table Header Font: B Titr
    titr_path = _find_font_file(["BTitrBd.ttf", "TITRB.TTF", "F_TITR.TTF"])
    if titr_path:
        try:
            titr_font = TTFont("BTitr", str(titr_path))
            pdfmetrics.registerFont(titr_font)
            pdfmetrics.registerFontFamily("BTitr", normal="BTitr", bold="BTitr")
            TITLE_FONT_NAME = "BTitr"
            _TITLE_FONT_CHARS = set(titr_font.face.charWidths.keys()) - {ord("("), ord(")"), ord("["), ord("]")}
            logger.info(f"PDF title font registered: {TITLE_FONT_NAME} from {titr_path}")
        except Exception as e:
            logger.warning(f"Could not register B Titr font {titr_path}: {e}")
            TITLE_FONT_NAME = FONT_BOLD_NAME
            _TITLE_FONT_CHARS = set()
    else:
        TITLE_FONT_NAME = FONT_BOLD_NAME
        _TITLE_FONT_CHARS = set()

def reshape_title_text(text: str) -> str:
    """Reshapes Persian title/header text for B Titr and wraps unsupported Latin/symbol glyphs in fallback font."""
    disp = reshape_text(text)
    if not disp or not _TITLE_FONT_CHARS or TITLE_FONT_NAME != "BTitr":
        return disp
    out = []
    in_fallback = False
    for ch in disp:
        supported = (ord(ch) in _TITLE_FONT_CHARS) or ch.isspace()
        if not supported and not in_fallback:
            out.append(f"<font name='{FALLBACK_FONT_NAME}'>")
            in_fallback = True
        elif supported and in_fallback:
            out.append("</font>")
            in_fallback = False
        out.append(ch)
    if in_fallback:
        out.append("</font>")
    return "".join(out)

setup_fonts()

class PDFGenerator:
    @staticmethod
    def _create_header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        
        # 1. Large Diagonal Watermark covering the full page diagonal with Club Name
        import math
        canvas_obj.saveState()
        page_w = doc.width + doc.leftMargin + doc.rightMargin
        page_h = doc.height + doc.topMargin + doc.bottomMargin
        page_diag = math.hypot(page_w, page_h)

        # Retrieve dynamic club name from branding settings with Yalda fallback
        raw_club_name = ""
        try:
            from yalda.services.branding_service import BrandingService
            club_info = BrandingService.get_club_info()
            raw_club_name = (club_info.get("club_name") or "").strip()
        except Exception:
            pass

        if not raw_club_name:
            raw_club_name = getattr(config, 'APP_DEFAULT_CLUB_NAME', 'باشگاه بدنسازی یلدا')

        # Determine font and reshape if Persian/Arabic
        is_persian = any('\u0600' <= ch <= '\u06FF' for ch in raw_club_name)
        if is_persian:
            font_name = FONT_BOLD_NAME
            watermark_text = reshape_text(raw_club_name)
            base_size = 65
            y_offset = -20
        else:
            font_name = "Helvetica-Bold"
            watermark_text = raw_club_name
            base_size = 90
            y_offset = -30

        # Dynamically scale font size if text is long to prevent clipping beyond margins
        font_size = base_size
        try:
            max_allowed_width = page_diag * 0.75
            text_width = canvas_obj.stringWidth(watermark_text, font_name, font_size)
            if text_width > max_allowed_width and text_width > 0:
                font_size = max(24, int(font_size * (max_allowed_width / text_width)))
        except Exception:
            pass

        canvas_obj.setFont(font_name, font_size)
        canvas_obj.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.25))
        canvas_obj.translate(page_w / 2.0, page_h / 2.0)
        diag_angle = math.degrees(math.atan2(page_h, page_w))
        canvas_obj.rotate(diag_angle)
        canvas_obj.drawCentredString(0, y_offset, watermark_text)
        canvas_obj.restoreState()

        # 2. Draw top bar with active theme primary accent color
        try:
            from yalda.utils.theme_manager import ThemeManager
            active_theme = ThemeManager.get_active_theme()
            accent_hex = active_theme.primary if active_theme else getattr(config, 'COLOR_PRIMARY_ACCENT', '#8B0000')
        except Exception:
            accent_hex = getattr(config, 'COLOR_PRIMARY_ACCENT', '#8B0000')
        canvas_obj.setFillColor(colors.HexColor(accent_hex))
        canvas_obj.rect(0, doc.height + doc.topMargin + 10, doc.width + doc.leftMargin + doc.rightMargin, 15, fill=1, stroke=0)
        
        # 3. Footer: Dividing line, Gym Address (Right) & Date (Left)
        canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(doc.leftMargin, 28, doc.width + doc.leftMargin, 28)

        canvas_obj.setFillColor(colors.HexColor("#555555"))
        canvas_obj.setFont(FONT_NAME, 8)
        
        # Address on RIGHT
        gym_address = getattr(config, 'GYM_ADDRESS', 'باشگاه بدنسازی یلدا | مازندران، قائمشهر، خیابان کوچکسرا، نبش شقایق ۳')
        canvas_obj.drawRightString(doc.width + doc.leftMargin, 16, reshape_text(gym_address))

        # Print Date on LEFT
        footer_date = reshape_text(f"تاریخ چاپ: {get_today_shamsi()}")
        canvas_obj.drawString(doc.leftMargin, 16, footer_date)

        # 4. Centered Official Nemov Footer Signature at y=7
        canvas_obj.setFillColor(colors.HexColor("#777777"))
        canvas_obj.setFont(FONT_NAME, 7)
        official_sig = "طراحی و ارائه‌شده توسط نرم‌افزار مدیریت ورزشی نِمُو (Nemov)"
        canvas_obj.drawCentredString((doc.width + doc.leftMargin + doc.rightMargin) / 2.0, 7, reshape_text(official_sig))

        canvas_obj.restoreState()

    @staticmethod
    def _get_trainer_info(member):
        from yalda.auth.authentication import CurrentUser
        from yalda.models.database_models import User
        from yalda.database.connection import get_session

        trainer_name = "مربی باشگاه یلدا"
        trainer_phone = "-"
        trainer_user = None

        try:
            user_id = getattr(member, 'user_id', None) if member else None

            # 1. Look up assigned trainer by user_id from fresh session
            if user_id:
                try:
                    with get_session() as db:
                        u = db.query(User).filter(User.id == user_id).first()
                        if u:
                            trainer_user = u
                except Exception:
                    pass

            # 2. If no trainer found or trainer is admin, check current logged-in user
            curr_user = CurrentUser.get()
            if curr_user:
                if not trainer_user:
                    trainer_user = curr_user
                elif getattr(trainer_user, 'role', '') == 'admin' and getattr(curr_user, 'role', '') == 'trainer':
                    trainer_user = curr_user
                elif not getattr(trainer_user, 'phone', None) and getattr(curr_user, 'phone', None):
                    trainer_user = curr_user

            # 3. Fallback to any active trainer with phone if still missing
            if not trainer_user or not getattr(trainer_user, 'phone', None):
                try:
                    with get_session() as db:
                        candidate = db.query(User).filter(
                            User.role == 'trainer',
                            User.phone.isnot(None),
                            User.phone != ''
                        ).first()
                        if candidate:
                            if not trainer_user or getattr(trainer_user, 'role', '') == 'admin':
                                trainer_user = candidate
                            elif not getattr(trainer_user, 'phone', None):
                                trainer_phone = candidate.phone
                except Exception:
                    pass

            if trainer_user:
                fn = getattr(trainer_user, 'first_name', '') or ''
                ln = getattr(trainer_user, 'last_name', '') or ''
                name = getattr(trainer_user, 'display_name', '') or getattr(trainer_user, 'full_name', '') or f"{fn} {ln}".strip()
                if name:
                    trainer_name = name
                phone = getattr(trainer_user, 'phone', None)
                if phone:
                    trainer_phone = str(phone)
        except Exception as e:
            logger.warning(f"Error resolving trainer info for PDF: {e}")

        return trainer_name, trainer_phone

    @staticmethod
    def generate_workout_pdf(member, workout_plan, output_filepath: str):
        """Generates printable PDF for Member's Workout Plan."""
        setup_fonts()
        if hasattr(workout_plan, 'id') and workout_plan.id:
            from yalda.services.workout_service import WorkoutService
            joined_p = WorkoutService.get_plan_by_id(workout_plan.id)
            if joined_p:
                workout_plan = joined_p

        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=40,
            bottomMargin=40
        )
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName=TITLE_FONT_NAME,
            fontSize=18,
            leading=22,
            alignment=1, # Center
            textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT)
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontName=FONT_NAME,
            fontSize=10,
            leading=15,
            alignment=2, # Right
            textColor=colors.HexColor("#333333")
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=14,
            alignment=2 # Right
        )
        cell_header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontName=TITLE_FONT_NAME,
            fontSize=8.5,
            leading=13,
            alignment=1, # Center
            textColor=colors.white
        )

        # Title
        elements.append(Paragraph(reshape_title_text("برنامه تمرینی باشگاه بدنسازی یلدا"), title_style))
        elements.append(Spacer(1, 10))

        goal_map = {
            "hypertrophy": "هایپرتروفی (عضله‌سازی)",
            "fat_loss": "چربی‌سوزی و کاهش وزن",
            "strength": "افزایش قدرت بی‌هوازی",
            "corrective": "حرکات اصلاحی و بهبود قامت",
            "general_fitness": "آمادگی جسمانی عمومی",
            "endurance": "استقامت عضلانی"
        }
        goal_fa = goal_map.get(workout_plan.goal, workout_plan.goal or "-")
        trainer_name, trainer_phone = PDFGenerator._get_trainer_info(member)

        # Member & Trainer Info Box Table
        info_data = [
            [
                Paragraph(reshape_text(f"هدف تمرین: {goal_fa}"), subtitle_style),
                Paragraph(reshape_text(f"نام ورزشکار: {member.full_name}"), subtitle_style)
            ],
            [
                Paragraph(reshape_text(f"تعداد روزهای تمرین: {workout_plan.days_per_week} روز در هفته"), subtitle_style),
                Paragraph(reshape_text(f"مربی: {trainer_name}"), subtitle_style)
            ],
            [
                Paragraph(reshape_text(f"تاریخ انقضای عضویت: {member.membership_expire_shamsi}"), subtitle_style),
                Paragraph(reshape_text(f"شماره تماس مربی: {trainer_phone}"), subtitle_style)
            ]
        ]
        info_table = Table(info_data, colWidths=[260, 260])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F5F5F5")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#DDDDDD")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        # Days and Exercises
        for day in workout_plan.days:
            day_title = Paragraph(
                reshape_title_text(f"◄ {day.day_title}"),
                ParagraphStyle('DayTitle', fontName=TITLE_FONT_NAME, fontSize=12, leading=16, alignment=2, textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT))
            )
            elements.append(day_title)
            elements.append(Spacer(1, 5))

            table_data = [[
                Paragraph(reshape_title_text("توضیحات"), cell_header_style),
                Paragraph(reshape_title_text("ریتم"), cell_header_style),
                Paragraph(reshape_title_text("زمان استراحت"), cell_header_style),
                Paragraph(reshape_title_text("وزنه (kg)"), cell_header_style),
                Paragraph(reshape_title_text("تکرار"), cell_header_style),
                Paragraph(reshape_title_text("ست"), cell_header_style),
                Paragraph(reshape_title_text("نام حرکت ورزشی"), cell_header_style),
                Paragraph(reshape_title_text("ردیف"), cell_header_style),
            ]]

            for idx, we in enumerate(day.workout_exercises, start=1):
                ex_name = (we.exercise.name_fa if we.exercise else None) or getattr(we, "custom_exercise_name", None) or "-"
                ex_name_reshaped = reshape_multiline_text(ex_name, max_width=140, font_name=FONT_NAME, font_size=9.5)
                
                # Video target URL
                target_url = None
                if we.exercise:
                    target_url = we.exercise.video_cloud_url or we.exercise.video_url
                    if target_url and target_url.strip():
                        target_url = target_url.strip()
                        if not (target_url.startswith("http://") or target_url.startswith("https://")):
                            target_url = "https://" + target_url
                        if "workers.dev" in target_url:
                            import re
                            target_url = re.sub(r"https?://[^/]+\.workers\.dev", config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/"), target_url)
                        if ("nemovapp.ir" in target_url or "gymassistantapp.ir" in target_url or "workers.dev" in target_url) and "title=" not in target_url and ex_name and ex_name != "-":
                            from urllib.parse import quote
                            sep = "&" if "?" in target_url else "?"
                            target_url = f"{target_url}{sep}title={quote(ex_name)}"

                # Hyperlink exercise name if video URL exists (clean black text with very thin non-obscuring black underline)
                if target_url:
                    escaped_url = target_url.replace("&", "&amp;")
                    name_html = f"<a href='{escaped_url}'><font color='#000000'><u offset='-4.0' width='0.35' color='#000000'>{ex_name_reshaped}</u></font></a>"
                    name_display = Paragraph(name_html, cell_style)
                else:
                    name_display = Paragraph(ex_name_reshaped, cell_style)

                # Prioritize custom trainer notes, fallback to exercise bank description if empty
                raw_notes = we.trainer_notes if (we.trainer_notes and we.trainer_notes.strip()) else (
                    we.exercise.description if (we.exercise and we.exercise.description and we.exercise.description.strip()) else "-"
                )

                cell_center_style = ParagraphStyle(
                    'CellCenterStyle',
                    parent=cell_style,
                    alignment=1  # Center
                )
                table_data.append([
                    Paragraph(reshape_multiline_text(raw_notes, max_width=116, font_name=FONT_NAME, font_size=9.5), cell_style),
                    Paragraph(reshape_text(str(we.tempo or "-")), cell_center_style),
                    Paragraph(reshape_text(f"{we.rest_seconds} ثانیه"), cell_center_style),
                    Paragraph(reshape_text(str(we.weight_suggestion or "-")), cell_center_style),
                    Paragraph(reshape_text(str(we.reps)), cell_center_style),
                    Paragraph(reshape_text(str(we.sets)), cell_center_style),
                    name_display,
                    Paragraph(reshape_text(str(idx)), cell_center_style),
                ])

            t = Table(table_data, colWidths=[122, 56, 57, 50, 44, 30, 146, 30])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(config.COLOR_PRIMARY_ACCENT)),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
                ('PADDING', (0,0), (-1,-1), 4),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))

        # Bottom Helpful Guidance Note Section
        footer_tip_title = reshape_title_text("💡 راهنمای مشاهده فیلم آموزش حرکات:")
        raw_tip_desc = "ورزشکار گرامی، جهت مشاهده ویدیوی نحوه اجرای هر حرکت، کافی است در جدول بالا بر روی نام حرکت کلیک یا لمس فرمایید تا فیلم آموزشی آن به صورت آنلاین در مرورگر باز شود."
        footer_tip_desc = reshape_multiline_text(raw_tip_desc, max_width=500, font_name=FONT_NAME, font_size=8)
        tip_paragraph = Paragraph(
            f"<font name='{TITLE_FONT_NAME}' color='#8B0000' size='9.5'>{footer_tip_title}</font><br/>"
            f"<font color='#444444' size='8'>{footer_tip_desc}</font>",
            ParagraphStyle('TipStyle', fontName=FONT_NAME, fontSize=8, leading=13, alignment=2)
        )
        tip_table = Table([[tip_paragraph]], colWidths=[535])
        tip_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8F9FA")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ('LINELEFT', (0,0), (-1,-1), 3, colors.HexColor(config.COLOR_PRIMARY_ACCENT)),
            ('PADDING', (0,0), (-1,-1), 7),
        ]))
        elements.append(Spacer(1, 6))
        elements.append(tip_table)

        doc.build(elements, onFirstPage=PDFGenerator._create_header_footer, onLaterPages=PDFGenerator._create_header_footer)
        try:
            from yalda.utils.logger import log_info
            mem_name = getattr(member, "full_name", str(member))
            log_info(f"ایجاد پی‌دی‌اف برنامه تمرینی ورزشکار '{mem_name}' با موفقیت انجام شد: {output_filepath}")
        except Exception:
            pass
        return output_filepath

    @staticmethod
    def generate_nutrition_pdf(member, nutrition_plan, output_filepath: str):
        """Generates printable PDF for Member's Nutrition Plan."""
        setup_fonts()
        if hasattr(nutrition_plan, 'id') and nutrition_plan.id:
            from yalda.services.nutrition_service import NutritionService
            joined_p = NutritionService.get_plan_by_id(nutrition_plan.id)
            if joined_p:
                nutrition_plan = joined_p

        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=40,
            bottomMargin=40
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName=TITLE_FONT_NAME,
            fontSize=18,
            leading=22,
            alignment=1,
            textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT)
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontName=FONT_NAME,
            fontSize=10,
            leading=15,
            alignment=2
        )
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontName=FONT_NAME, fontSize=10, leading=14, alignment=2)
        cell_header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName=TITLE_FONT_NAME, fontSize=10, leading=14, alignment=1, textColor=colors.white)

        elements.append(Paragraph(reshape_title_text("برنامه غذایی و رژیمی باشگاه بدنسازی یلدا"), title_style))
        elements.append(Spacer(1, 10))

        nutrition_goals = {
            "muscle_gain": "عضله‌سازی (Muscle Gain)",
            "weight_loss": "کاهش وزن و چربی‌سوزی (Weight Loss)",
            "weight_gain": "افزایش وزن (Weight Gain)",
            "maintenance": "تثبیت وزن (Maintenance)"
        }
        n_goal_fa = nutrition_goals.get(nutrition_plan.goal, nutrition_plan.goal or "-")
        trainer_name, trainer_phone = PDFGenerator._get_trainer_info(member)

        # Target Macros / Details Box
        if nutrition_plan.target_calories and nutrition_plan.target_calories > 0:
            m_line1 = reshape_text(f"کالری: {int(nutrition_plan.target_calories)} کالری | پروتئین: {int(nutrition_plan.target_protein)} گرم")
            m_line2 = reshape_text(f"کربوهیدرات: {int(nutrition_plan.target_carbs)} گرم | چربی: {int(nutrition_plan.target_fat)} گرم")
            third_row = [
                Paragraph(f"{m_line1}<br/>{m_line2}", subtitle_style),
                Paragraph(reshape_text(f"شماره تماس مربی: {trainer_phone}"), subtitle_style)
            ]
        else:
            third_row = [
                Paragraph(reshape_text(f"تاریخ صدور برنامه: {get_today_shamsi()}"), subtitle_style),
                Paragraph(reshape_text(f"شماره تماس مربی: {trainer_phone}"), subtitle_style)
            ]

        info_data = [
            [
                Paragraph(reshape_text(f"عنوان رژیم: {nutrition_plan.title}"), subtitle_style),
                Paragraph(reshape_text(f"نام ورزشکار: {member.full_name}"), subtitle_style)
            ],
            [
                Paragraph(reshape_text(f"هدف رژیم: {n_goal_fa}"), subtitle_style),
                Paragraph(reshape_text(f"مربی: {trainer_name}"), subtitle_style)
            ],
            third_row
        ]
        info_table = Table(info_data, colWidths=[260, 260])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F5F5F5")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#DDDDDD")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))

        meal_names_map = {
            "breakfast": "صبحانه",
            "morning_snack": "میان‌وعده صبح",
            "lunch": "ناهار",
            "afternoon_snack": "عصرانه",
            "dinner": "شام",
            "evening_snack": "قبل از خواب"
        }

        for meal in nutrition_plan.meals:
            if not meal.items:
                continue
            clean_m = clean_for_pdf(meal.meal_name)
            fa_meal_name = meal_names_map.get(clean_m, clean_m)
            if ":" in fa_meal_name:
                parts = fa_meal_name.split(":", 1)
                formatted_meal_name = f"{parts[0].strip()}: {parts[1].strip()}"
            else:
                formatted_meal_name = fa_meal_name

            meal_header = Paragraph(
                reshape_title_text(f"◄ وعده {formatted_meal_name}"),
                ParagraphStyle('MealTitle', fontName=TITLE_FONT_NAME, fontSize=12, leading=16, alignment=2, textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT))
            )
            elements.append(meal_header)
            elements.append(Spacer(1, 5))

            table_data = [[
                Paragraph(reshape_title_text("توضیحات مربی"), cell_header_style),
                Paragraph(reshape_title_text("مقدار / واحد"), cell_header_style),
                Paragraph(reshape_title_text("نام ماده غذایی"), cell_header_style),
                Paragraph(reshape_title_text("ردیف"), cell_header_style),
            ]]

            for idx, item in enumerate(meal.items, start=1):
                food_name = (item.food.name_fa if item.food else None) or getattr(item, "custom_food_name", None) or "-"
                raw_amt = item.amount
                try:
                    amt_disp = str(int(float(raw_amt))) if float(raw_amt).is_integer() else str(raw_amt)
                except Exception:
                    amt_disp = str(raw_amt)
                unit_disp = (item.unit or (item.food.unit if item.food else "") or "").strip()
                if unit_disp and unit_disp[0].isdigit():
                    qty_str = f"{amt_disp} واحد ({unit_disp})"
                else:
                    qty_str = f"{amt_disp} {unit_disp}".strip()
                table_data.append([
                    Paragraph(reshape_text(item.notes or "-"), cell_style),
                    Paragraph(reshape_text(qty_str), cell_style),
                    Paragraph(reshape_text(food_name), cell_style),
                    Paragraph(reshape_text(str(idx)), cell_style),
                ])

            t = Table(table_data, colWidths=[180, 120, 180, 40])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(config.COLOR_PRIMARY_ACCENT)),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
                ('PADDING', (0,0), (-1,-1), 6),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 15))

        doc.build(elements, onFirstPage=PDFGenerator._create_header_footer, onLaterPages=PDFGenerator._create_header_footer)
        try:
            from yalda.utils.logger import log_info
            mem_name = getattr(member, "full_name", str(member))
            log_info(f"ایجاد پی‌دی‌اف برنامه غذایی ورزشکار '{mem_name}' با موفقیت انجام شد: {output_filepath}")
        except Exception:
            pass
        return output_filepath

    @staticmethod
    def generate_financial_pdf(output_filepath: str, summary: dict, transactions: list, filter_info: dict = None):
        """
        Generates an official A4 Landscape Financial Statement PDF for Yalda Gym.
        """
        setup_fonts()
        output_path = Path(output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        from reportlab.lib.pagesizes import A4, landscape
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            rightMargin=25,
            leftMargin=25,
            topMargin=35,
            bottomMargin=35
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'FinTitle',
            fontName=TITLE_FONT_NAME,
            fontSize=16,
            leading=22,
            alignment=1,  # Center
            textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT)
        )
        subtitle_style = ParagraphStyle(
            'FinSub',
            fontName=FONT_NAME,
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#555555")
        )
        cell_header_style = ParagraphStyle(
            'FinCellHeader',
            fontName=TITLE_FONT_NAME,
            fontSize=9.5,
            leading=13,
            alignment=1,
            textColor=colors.white
        )
        cell_style = ParagraphStyle(
            'FinCell',
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=13,
            alignment=1,
            textColor=colors.HexColor("#222222")
        )

        elements = []

        # 1. Title & Subtitle
        elements.append(Paragraph(reshape_title_text("گزارش تراز و صورت مالی باشگاه بدنسازی یلدا"), title_style))
        elements.append(Spacer(1, 4))

        time_lbl = (filter_info or {}).get("time_label", "کل دوره")
        trainer_lbl = (filter_info or {}).get("trainer_label", "همه مربیان (کل باشگاه)")
        sub_text = f"بازه زمانی: {time_lbl}   |   مربی انتخابی: {trainer_lbl}"
        elements.append(Paragraph(reshape_text(sub_text), subtitle_style))
        elements.append(Spacer(1, 14))

        # 2. Top Summary Stat Cards Table
        tot_inc = summary.get("total_income", 0.0)
        tot_exp = summary.get("total_expense", 0.0)
        profit = summary.get("net_profit", 0.0)
        profit_color = "#16A34A" if profit >= 0 else "#DC2626"
        profit_prefix = "+" if profit > 0 else ""

        summary_box_data = [
            [
                Paragraph(reshape_title_text("سود / تراز خالص"), ParagraphStyle('S1', fontName=TITLE_FONT_NAME, fontSize=11, leading=14, alignment=1, textColor=colors.HexColor(profit_color))),
                Paragraph(reshape_title_text("مجموع هزینه‌ها (مخارج)"), ParagraphStyle('S2', fontName=TITLE_FONT_NAME, fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#DC2626"))),
                Paragraph(reshape_title_text("مجموع درآمدها (شهریه)"), ParagraphStyle('S3', fontName=TITLE_FONT_NAME, fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#16A34A"))),
            ],
            [
                Paragraph(reshape_text(f"{profit_prefix}{int(profit):,} تومان"), ParagraphStyle('V1', fontName=FONT_NAME, fontSize=13, leading=16, alignment=1, textColor=colors.HexColor(profit_color))),
                Paragraph(reshape_text(f"{int(tot_exp):,} تومان"), ParagraphStyle('V2', fontName=FONT_NAME, fontSize=13, leading=16, alignment=1, textColor=colors.HexColor("#DC2626"))),
                Paragraph(reshape_text(f"{int(tot_inc):,} تومان"), ParagraphStyle('V3', fontName=FONT_NAME, fontSize=13, leading=16, alignment=1, textColor=colors.HexColor("#16A34A"))),
            ]
        ]
        sum_table = Table(summary_box_data, colWidths=[263, 263, 264])
        sum_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8F9FA")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ('PADDING', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(sum_table)
        elements.append(Spacer(1, 16))

        # 3. Transactions Table
        # Columns in RTL (Right-to-Left visually):
        # Index 7: ردیف, Index 6: نوع, Index 5: عنوان / طرف حساب, Index 4: دسته‌بندی, Index 3: تاریخ, Index 2: مبلغ (تومان), Index 1: مربی, Index 0: توضیحات
        table_data = [[
            Paragraph(reshape_title_text("توضیحات"), cell_header_style),
            Paragraph(reshape_title_text("مربی مربوطه"), cell_header_style),
            Paragraph(reshape_title_text("مبلغ (تومان)"), cell_header_style),
            Paragraph(reshape_title_text("تاریخ"), cell_header_style),
            Paragraph(reshape_title_text("دسته‌بندی"), cell_header_style),
            Paragraph(reshape_title_text("عنوان / طرف حساب"), cell_header_style),
            Paragraph(reshape_title_text("نوع"), cell_header_style),
            Paragraph(reshape_title_text("ردیف"), cell_header_style),
        ]]

        for idx, t in enumerate(transactions, start=1):
            is_income = t.get("type") == "income"
            type_str = "درآمد (شهریه)" if is_income else "هزینه باشگاه"
            amount_val = int(t.get("amount", 0))
            amt_prefix = "+" if is_income else "-"
            amt_str = f"{amt_prefix}{amount_val:,}"

            c_bg = colors.HexColor("#FFFFFF") if idx % 2 != 0 else colors.HexColor("#F9FAFB")
            amt_color = colors.HexColor("#16A34A") if is_income else colors.HexColor("#DC2626")

            desc_raw = t.get("description", "-") or "-"
            desc_reshaped = reshape_multiline_text(desc_raw, max_width=145, font_name=FONT_NAME, font_size=8.5)

            row = [
                Paragraph(desc_reshaped, cell_style),
                Paragraph(reshape_text(t.get("trainer_name", "-") or "-"), cell_style),
                Paragraph(reshape_text(amt_str), ParagraphStyle('AmtStyle', fontName=FONT_NAME, fontSize=8.5, leading=11, alignment=1, textColor=amt_color)),
                Paragraph(reshape_text(t.get("date_shamsi", "-") or "-"), cell_style),
                Paragraph(reshape_text(t.get("category", "-") or "-"), cell_style),
                Paragraph(reshape_text(t.get("title", "-") or "-"), cell_style),
                Paragraph(reshape_text(type_str), cell_style),
                Paragraph(reshape_text(str(idx)), cell_style),
            ]
            table_data.append(row)

        if len(transactions) == 0:
            table_data.append([
                Paragraph(reshape_text("هیچ تراکنشی در این بازه زمانی یافت نشد."), cell_style),
                Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style),
                Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style),
                Paragraph("", cell_style)
            ])
        else:
            tot_amt_str = f"{profit_prefix}{int(profit):,}"
            tot_amt_style = ParagraphStyle(
                'FinTotAmt',
                fontName=FONT_BOLD_NAME,
                fontSize=9.5,
                leading=13,
                alignment=1,
                textColor=colors.HexColor(profit_color)
            )
            tot_lbl_style = ParagraphStyle(
                'FinTotLbl',
                fontName=TITLE_FONT_NAME,
                fontSize=9.5,
                leading=13,
                alignment=1,
                textColor=colors.HexColor("#1E293B")
            )
            table_data.append([
                Paragraph("", cell_style),
                Paragraph("", cell_style),  # مربی مربوطه: خالی (بدون کلمه تومان)
                Paragraph(reshape_text(tot_amt_str), tot_amt_style),
                Paragraph(reshape_title_text("تراز و سود خالص نهایی تراکنش‌های جدول:"), tot_lbl_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
            ])

        tx_table = Table(table_data, colWidths=[155, 95, 95, 75, 105, 150, 80, 35])
        t_styles = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(config.COLOR_PRIMARY_ACCENT)),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
            ('PADDING', (0,0), (-1,-1), 5),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        if len(transactions) > 0:
            t_styles.extend([
                ('SPAN', (3, -1), (7, -1)),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#94A3B8")),
                ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor("#64748B")),
            ])
        tx_table.setStyle(TableStyle(t_styles))
        elements.append(tx_table)

        doc.build(elements, onFirstPage=PDFGenerator._create_header_footer, onLaterPages=PDFGenerator._create_header_footer)
        return output_filepath

