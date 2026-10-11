#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate side-by-side comparison test PDFs and PNG images for PDF Watermark:
- Option 1: Large diagonal Latin watermark "NEMOV"
- Option 2: Large diagonal Persian watermark "باشگاه بدنسازی یلدا" (Custom Club Name)
Renders high-res PNGs using pypdfium2 to artifacts directory.
"""

import os
import sys
import math
from pathlib import Path
from types import SimpleNamespace

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pypdfium2
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import config
from yalda.pdf.pdf_generator import (
    setup_fonts,
    reshape_text,
    reshape_title_text,
    reshape_multiline_text,
    FONT_NAME,
    FONT_BOLD_NAME,
    TITLE_FONT_NAME,
    PDFGenerator
)
from yalda.utils.jalali_date import get_today_shamsi

ARTIFACTS_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def create_header_footer_option1(canvas_obj, doc):
    """Header & footer with Option 1: Large diagonal NEMOV watermark."""
    canvas_obj.saveState()
    
    # 1. Large Diagonal Watermark: NEMOV
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica-Bold", 165)
    canvas_obj.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.25))
    page_w = doc.width + doc.leftMargin + doc.rightMargin
    page_h = doc.height + doc.topMargin + doc.bottomMargin
    canvas_obj.translate(page_w / 2.0, page_h / 2.0)
    diag_angle = math.degrees(math.atan2(page_h, page_w))
    canvas_obj.rotate(diag_angle)
    canvas_obj.drawCentredString(0, -50, "NEMOV")
    canvas_obj.restoreState()

    # 2. Top bar
    canvas_obj.setFillColor(colors.HexColor(config.COLOR_PRIMARY_ACCENT))
    canvas_obj.rect(0, doc.height + doc.topMargin + 10, page_w, 15, fill=1, stroke=0)
    
    # 3. Footer
    canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
    canvas_obj.setLineWidth(0.6)
    canvas_obj.line(doc.leftMargin, 28, doc.width + doc.leftMargin, 28)

    canvas_obj.setFillColor(colors.HexColor("#555555"))
    canvas_obj.setFont(FONT_NAME, 8)
    
    gym_address = getattr(config, 'GYM_ADDRESS', 'باشگاه بدنسازی یلدا | مازندران، قائمشهر، خیابان کوچکسرا، نبش شقایق ۳')
    canvas_obj.drawRightString(doc.width + doc.leftMargin, 16, reshape_text(gym_address))

    footer_date = reshape_text(f"تاریخ چاپ: {get_today_shamsi()}")
    canvas_obj.drawString(doc.leftMargin, 16, footer_date)

    # Centered Official Nemov Footer Signature
    canvas_obj.setFillColor(colors.HexColor("#777777"))
    canvas_obj.setFont(FONT_NAME, 7)
    official_sig = "طراحی و ارائه‌شده توسط نرم‌افزار مدیریت ورزشی نِمُو (Nemov)"
    canvas_obj.drawCentredString(page_w / 2.0, 7, reshape_text(official_sig))

    canvas_obj.restoreState()


def create_header_footer_option2(canvas_obj, doc):
    """Header & footer with Option 2: Dynamic Persian club name watermark."""
    canvas_obj.saveState()
    
    # 1. Large Diagonal Watermark: باشگاه بدنسازی یلدا
    canvas_obj.saveState()
    # Persian text needs Vazirmatn or Titr font and text shaping
    canvas_obj.setFont(FONT_BOLD_NAME, 58)
    canvas_obj.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.25))
    page_w = doc.width + doc.leftMargin + doc.rightMargin
    page_h = doc.height + doc.topMargin + doc.bottomMargin
    canvas_obj.translate(page_w / 2.0, page_h / 2.0)
    diag_angle = math.degrees(math.atan2(page_h, page_w))
    canvas_obj.rotate(diag_angle)
    club_name_text = reshape_text("باشگاه بدنسازی یلدا")
    canvas_obj.drawCentredString(0, -20, club_name_text)
    canvas_obj.restoreState()

    # 2. Top bar
    canvas_obj.setFillColor(colors.HexColor(config.COLOR_PRIMARY_ACCENT))
    canvas_obj.rect(0, doc.height + doc.topMargin + 10, page_w, 15, fill=1, stroke=0)
    
    # 3. Footer
    canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
    canvas_obj.setLineWidth(0.6)
    canvas_obj.line(doc.leftMargin, 28, doc.width + doc.leftMargin, 28)

    canvas_obj.setFillColor(colors.HexColor("#555555"))
    canvas_obj.setFont(FONT_NAME, 8)
    
    gym_address = getattr(config, 'GYM_ADDRESS', 'باشگاه بدنسازی یلدا | مازندران، قائمشهر، خیابان کوچکسرا، نبش شقایق ۳')
    canvas_obj.drawRightString(doc.width + doc.leftMargin, 16, reshape_text(gym_address))

    footer_date = reshape_text(f"تاریخ چاپ: {get_today_shamsi()}")
    canvas_obj.drawString(doc.leftMargin, 16, footer_date)

    # Centered Official Nemov Footer Signature
    canvas_obj.setFillColor(colors.HexColor("#777777"))
    canvas_obj.setFont(FONT_NAME, 7)
    official_sig = "طراحی و ارائه‌شده توسط نرم‌افزار مدیریت ورزشی نِمُو (Nemov)"
    canvas_obj.drawCentredString(page_w / 2.0, 7, reshape_text(official_sig))

    canvas_obj.restoreState()


def build_sample_workout_elements():
    """Build document flowable elements for a realistic workout plan."""
    setup_fonts()
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
    cell_center_style = ParagraphStyle(
        'CellCenterStyle',
        parent=cell_style,
        alignment=1 # Center
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

    elements = []
    elements.append(Paragraph(reshape_title_text("برنامه تمرینی باشگاه بدنسازی یلدا"), title_style))
    elements.append(Spacer(1, 10))

    # Info box
    info_data = [
        [
            Paragraph(reshape_text("هدف تمرین: هایپرتروفی (عضله‌سازی)"), subtitle_style),
            Paragraph(reshape_text("نام ورزشکار: علی رضایی"), subtitle_style)
        ],
        [
            Paragraph(reshape_text("تعداد روزهای تمرین: ۳ روز در هفته"), subtitle_style),
            Paragraph(reshape_text("مربی: محراب حاجی‌پور"), subtitle_style)
        ],
        [
            Paragraph(reshape_text("تاریخ انقضای عضویت: ۱۴۰۳/۰۸/۳۰"), subtitle_style),
            Paragraph(reshape_text("شماره تماس مربی: ۰۹۱۲۳۴۵۶۷۸۹"), subtitle_style)
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

    # Day 1: سینه و جلو بازو
    day_title = Paragraph(
        reshape_title_text("◄ روز اول: سینه و جلو بازو"),
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

    sample_exercises = [
        ("پرس سینه هالتر", 4, "10-12", "60", "90 ثانیه", "2-0-1", "انقباض کامل در اوج دامنه و کنترل منفی حرکت"),
        ("بالاسینه دمبل", 3, "12", "22", "60 ثانیه", "2-0-1", "کشش عمیق بخش بالایی سینه"),
        ("پارالل سینه", 3, "تا ناتوانی", "وزن بدن", "60 ثانیه", "-", "تمرکز بر زاویه ۳۰ درجه رو به جلو"),
        ("جلو بازو هالتر EZ", 4, "10", "30", "60 ثانیه", "3-0-1", "ثابت نگه داشتن آرنج‌ها کنار بالاتنه"),
        ("جلو بازو دمبل چکشی", 3, "12", "14", "45 ثانیه", "-", "تمرکز بر عضله براکیالیس"),
    ]

    for idx, (name, sets, reps, weight, rest, tempo, notes) in enumerate(sample_exercises, 1):
        ex_name_reshaped = reshape_multiline_text(name, max_width=140, font_name=FONT_NAME, font_size=9.5)
        name_html = f"<font color='#000000'><u>{ex_name_reshaped}</u></font>"
        table_data.append([
            Paragraph(reshape_multiline_text(notes, max_width=116, font_name=FONT_NAME, font_size=9.5), cell_style),
            Paragraph(reshape_text(tempo), cell_center_style),
            Paragraph(reshape_text(rest), cell_center_style),
            Paragraph(reshape_text(weight), cell_center_style),
            Paragraph(reshape_text(str(reps)), cell_center_style),
            Paragraph(reshape_text(str(sets)), cell_center_style),
            Paragraph(name_html, cell_style),
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

    # Bottom Guidance Note
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

    return elements


def generate_and_render_option1():
    pdf_path = ARTIFACTS_DIR / "qa_test_option1_nemov.pdf"
    png_path = ARTIFACTS_DIR / "qa_watermark_option1_nemov.png"
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=40,
        bottomMargin=40
    )
    elements = build_sample_workout_elements()
    doc.build(elements, onFirstPage=create_header_footer_option1, onLaterPages=create_header_footer_option1)
    
    # Render to PNG using pypdfium2
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    page = pdf[0]
    image = page.render(scale=2.0).to_pil()
    image.save(str(png_path))
    print(f"[Option 1] PDF generated: {pdf_path}")
    print(f"[Option 1] PNG rendered: {png_path} ({image.width}x{image.height})")
    return png_path


def generate_and_render_option2():
    pdf_path = ARTIFACTS_DIR / "qa_test_option2_clubname.pdf"
    png_path = ARTIFACTS_DIR / "qa_watermark_option2_clubname.png"
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=40,
        bottomMargin=40
    )
    elements = build_sample_workout_elements()
    doc.build(elements, onFirstPage=create_header_footer_option2, onLaterPages=create_header_footer_option2)
    
    # Render to PNG using pypdfium2
    pdf = pypdfium2.PdfDocument(str(pdf_path))
    page = pdf[0]
    image = page.render(scale=2.0).to_pil()
    image.save(str(png_path))
    print(f"[Option 2] PDF generated: {pdf_path}")
    print(f"[Option 2] PNG rendered: {png_path} ({image.width}x{image.height})")
    return png_path


if __name__ == "__main__":
    p1 = generate_and_render_option1()
    p2 = generate_and_render_option2()
    print("ALL WATERMARK COMPARISON RENDERINGS COMPLETED SUCCESSFULLY!")
