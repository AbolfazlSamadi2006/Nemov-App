import re
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

def clean_for_pdf(text: str) -> str:
    """Removes unsupported unicode emojis and collapses redundant spaces/colons for PDF."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", str(text))
    cleaned = re.sub(r":\s*:", ":", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def reshape_text(text: str) -> str:
    """Helper to reshape Persian text and apply BiDi algorithm for ReportLab rendering."""
    if not text:
        return ""
    try:
        cleaned = clean_for_pdf(text)
        reshaped = arabic_reshaper.reshape(cleaned)
        return get_display(reshaped)
    except Exception:
        return str(text)

# Register TTF Font for Persian PDF rendering
FONT_NAME = "Helvetica"
def setup_fonts():
    global FONT_NAME
    candidate_paths = [
        config.BASE_DIR / "resources" / "fonts" / "Vazirmatn-Regular.ttf",
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf")
    ]
    for path in candidate_paths:
        if path.exists():
            try:
                font_id = "PersianFont"
                pdfmetrics.registerFont(TTFont(font_id, str(path)))
                FONT_NAME = font_id
                return
            except Exception:
                continue

    FONT_NAME = 'Helvetica'

setup_fonts()

class PDFGenerator:
    @staticmethod
    def _create_header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        
        # 1. Large Diagonal Watermark covering the full page diagonal
        import math
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica-Bold", 175)
        canvas_obj.setFillColor(colors.Color(0.80, 0.80, 0.80, alpha=0.26))
        page_w = doc.width + doc.leftMargin + doc.rightMargin
        page_h = doc.height + doc.topMargin + doc.bottomMargin
        canvas_obj.translate(page_w / 2.0, page_h / 2.0)
        diag_angle = math.degrees(math.atan2(page_h, page_w))
        canvas_obj.rotate(diag_angle)
        canvas_obj.drawCentredString(0, -55, "YALDA")
        canvas_obj.restoreState()

        # 2. Draw dark red top bar
        canvas_obj.setFillColor(colors.HexColor(config.COLOR_PRIMARY_ACCENT))
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

        canvas_obj.restoreState()

    @staticmethod
    def _get_trainer_info(member):
        from yalda.auth.authentication import CurrentUser
        u = CurrentUser.get()
        trainer_name = "مربی باشگاه"
        trainer_phone = "-"
        if u:
            trainer_name = u.full_name or f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username or "مربی باشگاه"
            trainer_phone = u.phone or "-"
        if (trainer_name == "مربی باشگاه" or trainer_phone == "-") and hasattr(member, 'user') and member.user:
            trainer_name = member.user.full_name or f"{member.user.first_name or ''} {member.user.last_name or ''}".strip() or trainer_name
            trainer_phone = member.user.phone or trainer_phone
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
            fontName=FONT_NAME,
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
            fontSize=10,
            leading=14,
            alignment=2 # Right
        )
        cell_header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontName=FONT_NAME,
            fontSize=10,
            leading=14,
            alignment=1, # Center
            textColor=colors.white
        )

        # Title
        elements.append(Paragraph(reshape_text("برنامه تمرینی باشگاه بدنسازی یلدا"), title_style))
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
                reshape_text(f"◄ {day.day_title}"),
                ParagraphStyle('DayTitle', fontName=FONT_NAME, fontSize=12, leading=16, alignment=2, textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT))
            )
            elements.append(day_title)
            elements.append(Spacer(1, 5))

            table_data = [[
                Paragraph(reshape_text("توضیحات / ریتم"), cell_header_style),
                Paragraph(reshape_text("زمان استراحت"), cell_header_style),
                Paragraph(reshape_text("وزنه (کیلو)"), cell_header_style),
                Paragraph(reshape_text("تکرار"), cell_header_style),
                Paragraph(reshape_text("ست"), cell_header_style),
                Paragraph(reshape_text("نام حرکت ورزشی"), cell_header_style),
                Paragraph(reshape_text("ردیف"), cell_header_style),
            ]]

            for idx, we in enumerate(day.workout_exercises, start=1):
                ex_name = we.exercise.name_fa if we.exercise else "-"
                if we.exercise and we.exercise.video_url and we.exercise.video_url.strip():
                    url = we.exercise.video_url.strip()
                    if not (url.startswith("http://") or url.startswith("https://")):
                        url = "https://" + url
                    link_text = reshape_text("🔗 فیلم آموزش")
                    ex_display = f"{reshape_text(ex_name)}<br/><a href='{url}'><font color='#0055CC' size='7.5'><u>{link_text}</u></font></a>"
                else:
                    ex_display = reshape_text(ex_name)

                table_data.append([
                    Paragraph(reshape_text(f"{we.tempo or '-'} / {we.trainer_notes or ''}"), cell_style),
                    Paragraph(reshape_text(f"{we.rest_seconds} ثانیه"), cell_style),
                    Paragraph(reshape_text(str(we.weight_suggestion or "-")), cell_style),
                    Paragraph(reshape_text(str(we.reps)), cell_style),
                    Paragraph(reshape_text(str(we.sets)), cell_style),
                    Paragraph(ex_display, cell_style),
                    Paragraph(reshape_text(str(idx)), cell_style),
                ])

            t = Table(table_data, colWidths=[100, 70, 60, 50, 40, 160, 40])
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
            fontName=FONT_NAME,
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
        cell_header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName=FONT_NAME, fontSize=10, leading=14, alignment=1, textColor=colors.white)

        elements.append(Paragraph(reshape_text("برنامه غذایی و رژیمی باشگاه بدنسازی یلدا"), title_style))
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
            macro_text = f"کالری: {int(nutrition_plan.target_calories)} ک‌کال | پروتئین: {int(nutrition_plan.target_protein)}g | کربوهیدرات: {int(nutrition_plan.target_carbs)}g | چربی: {int(nutrition_plan.target_fat)}g"
            third_row = [
                Paragraph(reshape_text(macro_text), subtitle_style),
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
                reshape_text(f"◄ وعده {formatted_meal_name}"),
                ParagraphStyle('MealTitle', fontName=FONT_NAME, fontSize=12, leading=16, alignment=2, textColor=colors.HexColor(config.COLOR_PRIMARY_ACCENT))
            )
            elements.append(meal_header)
            elements.append(Spacer(1, 5))

            table_data = [[
                Paragraph(reshape_text("توضیحات مربی"), cell_header_style),
                Paragraph(reshape_text("مقدار / واحد"), cell_header_style),
                Paragraph(reshape_text("نام ماده غذایی"), cell_header_style),
                Paragraph(reshape_text("ردیف"), cell_header_style),
            ]]

            for idx, item in enumerate(meal.items, start=1):
                food_name = item.food.name_fa if item.food else "-"
                table_data.append([
                    Paragraph(reshape_text(item.notes or "-"), cell_style),
                    Paragraph(reshape_text(f"{item.amount} {item.unit or item.food.unit}"), cell_style),
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
        return output_filepath
