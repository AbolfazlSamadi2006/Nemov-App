import os
from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# ============================================================================
# Palette Definition - Nemov Tricolor (Emerald Green, Pure White, Crimson Red)
# ============================================================================
BG_DARK = RGBColor(11, 15, 23)        # #0B0F17 Deep Dark Slate
CARD_BG = RGBColor(20, 27, 38)        # #141B26 Dark Slate Card
CARD_BORDER = RGBColor(31, 41, 61)    # #1F293D Subtle Border

COLOR_GREEN = RGBColor(16, 185, 129)  # #10B981 Emerald / Mint
COLOR_WHITE = RGBColor(255, 255, 255) # #FFFFFF Pure White
COLOR_RED = RGBColor(239, 68, 68)     # #EF4444 Crimson / Ruby
COLOR_TEXT = RGBColor(226, 232, 240)   # #E2E8F0 Light Slate Body
COLOR_MUTED = RGBColor(148, 163, 184) # #94A3B8 Muted Caption
COLOR_YELLOW = RGBColor(245, 158, 11) # #F59E0B Warning / Notice
COLOR_BLUE = RGBColor(59, 130, 246)   # #3B82F6 Tech Blue

FONT_NAME = "Vazirmatn"
FALLBACK_FONT = "Segoe UI"

def set_slide_bg(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BG_DARK

def add_tricolor_strip(slide):
    # Top decorative tricolor banner: Green | White | Red
    strip_h = Inches(0.08)
    w_part = Inches(13.333 / 3.0)
    
    # Green
    g = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), w_part, strip_h)
    g.fill.solid(); g.fill.fore_color.rgb = COLOR_GREEN; g.line.fill.background()
    # White
    w = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, w_part, Inches(0), w_part, strip_h)
    w.fill.solid(); w.fill.fore_color.rgb = COLOR_WHITE; w.line.fill.background()
    # Red
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, w_part * 2, Inches(0), w_part + Inches(0.1), strip_h)
    r.fill.solid(); r.fill.fore_color.rgb = COLOR_RED; r.line.fill.background()

def add_header(slide, title: str, subtitle: str, category: str, logo_path: str = None):
    add_tricolor_strip(slide)
    
    # Category pill / badge
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(8.0), Inches(0.35))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = f"● {category}"
    p_c.font.name = FONT_NAME
    p_c.font.size = Pt(11)
    p_c.font.bold = True
    p_c.font.color.rgb = COLOR_GREEN
    p_c.alignment = PP_ALIGN.RIGHT

    # Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(10.5), Inches(0.55))
    tf_t = t_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.name = FONT_NAME
    p_t.font.size = Pt(20)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_WHITE
    p_t.alignment = PP_ALIGN.RIGHT

    # Subtitle
    if subtitle:
        s_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.1), Inches(10.5), Inches(0.4))
        tf_s = s_box.text_frame
        tf_s.word_wrap = True
        p_s = tf_s.paragraphs[0]
        p_s.text = subtitle
        p_s.font.name = FONT_NAME
        p_s.font.size = Pt(12)
        p_s.font.color.rgb = COLOR_MUTED
        p_s.alignment = PP_ALIGN.RIGHT

    # Mini Logo in top right if available
    if logo_path and os.path.exists(logo_path):
        slide.shapes.add_picture(logo_path, Inches(12.0), Inches(0.35), width=Inches(0.75), height=Inches(0.75))

def add_card(slide, left, top, width, height, title, items, border_color=CARD_BORDER, bg_color=CARD_BG, icon=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.5)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.2)
    tf.margin_bottom = Inches(0.2)

    p0 = tf.paragraphs[0]
    full_title = f"{icon}  {title}" if icon else title
    p0.text = full_title
    p0.font.name = FONT_NAME
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = border_color if border_color != CARD_BORDER else COLOR_WHITE
    p0.alignment = PP_ALIGN.RIGHT

    for item in items:
        p = tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.name = FONT_NAME
        p.font.size = Pt(11.5)
        p.font.color.rgb = COLOR_TEXT
        p.alignment = PP_ALIGN.RIGHT
        p.space_before = Pt(4)

def build_deck(out_pptx_path: str):
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    logo_file = "resources/images/nemov_logo.png"

    # =========================================================================
    # SLIDE 1: Title Slide (Cover with Nemov Logo and Tricolor Elegance)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1)
    add_tricolor_strip(s1)

    # Big Logo
    if os.path.exists(logo_file):
        s1.shapes.add_picture(logo_file, Inches(5.8), Inches(1.2), width=Inches(1.8), height=Inches(1.8))

    # Title box
    tbox1 = s1.shapes.add_textbox(Inches(1.0), Inches(3.2), Inches(11.333), Inches(1.5))
    tf1 = tbox1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "سامانه جامع مدیریت و برنامه‌ریزی ورزشی «نِمُو» (Nemov)"
    p1.font.name = FONT_NAME
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.alignment = PP_ALIGN.CENTER

    p2 = tf1.add_paragraph()
    p2.text = "تحلیل نیازمندی‌ها، معماری نرم‌افزار و طراحی سیستم (ارزیابی فاز ۱ تا ۳)"
    p2.font.name = FONT_NAME
    p2.font.size = Pt(17)
    p2.font.color.rgb = COLOR_GREEN
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(8)

    # Info Card in Center Bottom
    infocard = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.8), Inches(5.0), Inches(7.7), Inches(1.8))
    infocard.fill.solid(); infocard.fill.fore_color.rgb = CARD_BG
    infocard.line.color.rgb = COLOR_GREEN; infocard.line.width = Pt(1.5)
    itf = infocard.text_frame
    itf.margin_top = Inches(0.2)

    ip1 = itf.paragraphs[0]
    ip1.text = "درس: تحلیل و طراحی سیستم‌های نرم‌افزاری (SSAD) | نیم‌سال اول ۱۴۰۵"
    ip1.font.name = FONT_NAME; ip1.font.size = Pt(13); ip1.font.bold = True; ip1.font.color.rgb = COLOR_WHITE; ip1.alignment = PP_ALIGN.CENTER

    ip2 = itf.add_paragraph()
    ip2.text = "👨‍💻 طراح و توسعه‌دهنده: ابوالفضل صمدی کوچکسرائی"
    ip2.font.name = FONT_NAME; ip2.font.size = Pt(12.5); ip2.font.color.rgb = COLOR_TEXT; ip2.alignment = PP_ALIGN.CENTER; ip2.space_before = Pt(4)

    ip3 = itf.add_paragraph()
    ip3.text = "🎓 استاد راهنما: جناب آقای دکتر مهدی عمادی | منتور: مهندس امین اکبری"
    ip3.font.name = FONT_NAME; ip3.font.size = Pt(12); ip3.font.color.rgb = COLOR_MUTED; ip3.alignment = PP_ALIGN.CENTER; ip3.space_before = Pt(4)

    ip4 = itf.add_paragraph()
    ip4.text = "🌐 وب‌سایت رسمی: nemovapp.ir  |  گیت‌هاب: github.com/AbolfazlSamadi2006/Nemov-App"
    ip4.font.name = FONT_NAME; ip4.font.size = Pt(11); ip4.font.color.rgb = COLOR_GREEN; ip4.alignment = PP_ALIGN.CENTER; ip4.space_before = Pt(4)

    # =========================================================================
    # SLIDE 2: Problem Statement (4 Critical Pain Points)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2)
    add_header(s2, "بیان مسئله و چالش‌های عملیاتی باشگاه‌های ورزشی", "چرا صنعت باشگاه‌داری نیازمند یک راهکار نرم‌افزاری بومی و یکپارچه است؟", "فاز ۱: شناخت مسئله و تحلیل دامنه", logo_file)

    add_card(s2, Inches(6.8), Inches(1.8), Inches(5.7), Inches(2.4),
             "۱. آشفتگی در مدیریت شهریه‌ها و دوره‌های اعضا",
             ["استفاده از دفاتر دست‌نویس کاغذی یا فایل‌های اکسل نامنظم و پراکنده",
              "فراموشی تاریخ سررسید دوره‌ها و تمدید نکردن به موقع توسط ورزشکار",
              "عدم شفافیت در تسویه‌حساب مالی و ایجاد اختلاف میان باشگاه و شاگرد"],
             COLOR_RED, CARD_BG, "💰")

    add_card(s2, Inches(0.8), Inches(1.8), Inches(5.7), Inches(2.4),
             "۲. ناکارآمدی و زمان‌بر بودن نسخه‌نویسی دستی",
             ["صرف زمان طولانی مربیان در ساعات شلوغی برای نوشتن دستی تمرینات روی کاغذ",
              "خطای انسانی بالا در ترکیب عضلات روزهای متوالی و ایجاد بیش‌تمرینی",
              "فرسودگی، گم شدن یا مخدوش شدن سریع برگه‌های تمرینی در محیط باشگاه"],
             COLOR_YELLOW, CARD_BG, "📝")

    add_card(s2, Inches(6.8), Inches(4.5), Inches(5.7), Inches(2.4),
             "۳. ریسک بالای آسیب‌دیدگی مفاصل شاگردان",
             ["عدم وجود مرجع تصویری و ویدیویی اجرای حرکت در حین تمرین",
              "ناآگاهی از قلق‌های ایمنی و موارد منع آسیب (دیسک کمر، زانو، شانه)",
              "اجرای فرم غلط حرکات سنگین توسط ورزشکار و بروز مصدومیت‌های دائمی"],
             COLOR_RED, CARD_BG, "⚠️")

    add_card(s2, Inches(0.8), Inches(4.5), Inches(5.7), Inches(2.4),
             "۴. خطر همیشگی نابودی داده‌های تاریخی باشگاه",
             ["نوسانات شدید برق و آسیب فیزیکی به کیس کامپیوتر مستقر در باشگاه",
              "خرابی ناگهانی سیستم‌عامل ویندوز یا باج‌افزارها و از بین رفتن اطلاعات",
              "نبود سیستم پشتیبان‌گیری چندلایه و مکانیزم ابری امن بازیابی"],
             COLOR_GREEN, CARD_BG, "💾")

    # =========================================================================
    # SLIDE 3: MVP Boundaries (In-Scope vs Out-of-Scope)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3)
    add_header(s3, "تعریف حداقل محصول پذیرفتنی (MVP) و مرزهای سیستم", "تمرکز بر ارزش‌آفرینی هسته اصلی، اجتناب از Feature Creep و تضمین پایداری", "فاز ۱: مرزبندی دامنه محصول", logo_file)

    # In-Scope Card (Green Border)
    add_card(s3, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "در محدوده متعهد MVP قرار دارد (In-Scope)",
             ["ثبت‌نام و تشکیل پرونده الکترونیک سلامت و سوابق پزشکی اعضا",
              "مدیریت دوره‌های شهریه و رهگیری خودکار وضعیت فعال/منقضی",
              "بانک بیش از ۱۰۰۰ حرکت ورزشی به همراه ویدیوی ابری و قلق ضدآسیب",
              "ماژول تخصصی طراحی برنامه تمرینی چندروزه و موتور صدور PDF رسمی",
              "احراز هویت دو سطحی (مدیر باشگاه / مربیان) با تفکیک دقیق دسترسی",
              "پشتیبان‌گیری ابری و دیتابیس مقاوم در برابر قطعی برق (SQLite WAL)",
              "اعتبارسنجی لایسنس سخت‌افزاری مقید به ماشین (HWID Lock)"],
             COLOR_GREEN, CARD_BG, "✅")

    # Out-of-Scope Card (Red Border)
    add_card(s3, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "خارج از محدوده فاز اول (Out-of-Scope)",
             ["اتصال سخت‌افزاری به گیت‌های ورود و خروج تردد فیزیکی (Turnstile)",
              "اتصال مستقیم سخت‌افزاری به دستگاه‌های پوز بانکی (POS Terminal)",
              "اپلیکیشن محلی مستقل iOS/Android برای شاگرد (تمرکز روی نسخه دسکتاپ)",
              "چت و پیام‌رسان درون‌برنامه‌ای زنده بین مربی و شاگرد",
              "پردازش تصویر هوش مصنوعی با وب‌کم جهت شمارش تکرارها در حین تمرین",
              "سیستم فروشگاه و مارکت‌پلیس آنلاین خرید مکمل و تجهیزات ورزشی"],
             COLOR_RED, CARD_BG, "🚫")

    # =========================================================================
    # SLIDE 4: User Personas & Trainer Ethics
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4)
    add_header(s4, "پرسونای کاربران و رعایت موازین اخلاقی و فنی مربیان", "تفکیک دقیق سطوح اختیارات مدیر و مربی، و جایگاه ورزشکار به عنوان ذینفع نهایی", "فاز ۱: شناخت کاربران و ذینفعان", logo_file)

    add_card(s4, Inches(6.8), Inches(1.8), Inches(5.7), Inches(3.8),
             "پرسونای ۱: مدیر باشگاه (Club Admin / Owner)",
             ["دید کلان و سراسری (Global View) به وضعیت اعضا و مربیان مجموعه",
              "دسترسی انحصاری به صندوق مالی، تراز درآمد ماهانه و سود خالص باشگاه",
              "مدیریت وضعیت همکاری مربیان از طریق تعلیق دسترسی (is_active=False)",
              "🔒 اصل اخلاقی: مدیر حق دیدن رمز مربی یا حذف فیزیکی سوابق او را ندارد",
              "ورود توکن لایسنس معتبر صادر شده برای باشگاه جهت فعال‌سازی برنامه"],
             COLOR_GREEN, CARD_BG, "👔")

    add_card(s4, Inches(0.8), Inches(1.8), Inches(5.7), Inches(3.8),
             "پرسونای ۲: مربی ورزشی و بدنسازی (Fitness Coach)",
             ["ورود اختصاصی با رمز عبور کاملاً محرمانه و هش‌شده یک‌طرفه (BCrypt/Argon)",
              "طراحی برنامه‌های تمرینی هفتگی و ثبت مشخصات آنتروپومتری شاگردان خود",
              "استفاده از بانک حرکات و قلق‌های ضدآسیب جهت جلوگیری از مصدومیت شاگرد",
              "صدور رسمی برنامه تمرینی با درج نام معتبر خود مربی بر روی فایل PDF",
              "مالکیت معنوی برنامه‌ها حتی در صورت تعلیق یا قطع همکاری با باشگاه محفوظ است"],
             COLOR_RED, CARD_BG, "🏋️‍♂️")

    # Beneficiary Card at Bottom
    ben_shape = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.8), Inches(11.7), Inches(1.2))
    ben_shape.fill.solid(); ben_shape.fill.fore_color.rgb = CARD_BG
    ben_shape.line.color.rgb = COLOR_WHITE; ben_shape.line.width = Pt(1.5)
    btf = ben_shape.text_frame
    btf.margin_top = Inches(0.15)
    bp1 = btf.paragraphs[0]
    bp1.text = "🎯 گیرنده نهایی خدمات: ورزشکار / شاگرد باشگاه (Managed Beneficiary)"
    bp1.font.name = FONT_NAME; bp1.font.size = Pt(13); bp1.font.bold = True; bp1.font.color.rgb = COLOR_WHITE; bp1.alignment = PP_ALIGN.RIGHT
    bp2 = btf.add_paragraph()
    bp2.text = "ورزشکار در فاز اول اکانت مستقیم برای ورود به برنامه ندارد؛ بلکه اطلاعات او توسط مربی مدیریت شده و برنامه تمرینی استاندارد (PDF یا پرینت) و پیامک‌های اطلاع‌رسانی سررسید شهریه را به عنوان خروجی خدمت دریافت می‌کند."
    bp2.font.name = FONT_NAME; bp2.font.size = Pt(11); bp2.font.color.rgb = COLOR_MUTED; bp2.alignment = PP_ALIGN.RIGHT; bp2.space_before = Pt(3)

    # =========================================================================
    # SLIDE 5: User Stories & MoSCoW Prioritization
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5)
    add_header(s5, "داستان‌های کاربری و معیارهای پذیرش سه‌گانه (MoSCoW)", "مدل‌سازی نیازهای رفتاری سیستم همراه با سناریوهای موفقیت، شکست و پایداری داده", "فاز ۱: نیازمندی‌های رفتاری", logo_file)

    # Left: Acceptance Criteria Sample
    add_card(s5, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "ساختار معیارهای پذیرش ۳ گانه (Acceptance Criteria)",
             ["بیان داستان کاربری: As a [User], I want [Action], So that [Benefit]",
              "✅ معیار موفقیت (Happy Path): وارد کردن نام، شماره تماس معتبر (۱۱ رقم با پیشوند ۰۹) و ثبت آنی رکورد در دیتابیس با پیغام تایید.",
              "❌ معیار شکست اعتبارسنجی (Negative Path): رد درخواست در صورت وارد کردن شماره نامعتبر یا ثبت کد ملی تکراری با کد خطای ۴۲۲ یا ۴۰۹.",
              "💾 معیار پایداری داده‌ها (Data State): اطلاعات بلافاصله پس از ثبت، با ریستارت یا بستن برنامه در پایگاه‌داده باقی مانده و لود شود.",
              "🛡️ معیار مالکیت و امنیت (Authorization): مربی صرفاً مجاز به ویرایش پرونده‌های شاگردان خود است و سوابق مربیان دیگر محافظت می‌شود."],
             COLOR_YELLOW, CARD_BG, "📋")

    # Right: MoSCoW Prioritization
    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "ماتریس اولویت‌بندی نیازمندی‌ها (MoSCoW Matrix)",
             ["🔴 Must Have (حیاتی برای انتشار MVP):",
              "   • US-01: ثبت‌نام و تشکیل پرونده الکترونیک سلامت اعضا",
              "   • US-02: مدیریت دوره‌های شهریه و محاسبه تاریخ انقضا",
              "   • US-03: بانک حرکات ورزشی و قلق‌های ضدآسیب مفاصل",
              "   • US-04: تدوین برنامه تمرینی و صدور استاندارد فایل PDF",
              "   • US-05: احراز هویت دو سطحی با رمزهای هش‌شده امن",
              "   • US-07: اعتبارسنجی لایسنس سخت‌افزاری مقید به ماشین",
              "🟡 Should Have: US-06 پشتیبان‌گیری ابری خودکار، سامانه پیامک",
              "🟢 Could Have: سامانه کالری‌شماری و طراحی رژیم غذایی",
              "⚪ Won't Have: اتصال به گیت‌های سخت‌افزاری و پوز بانکی"],
             COLOR_GREEN, CARD_BG, "🎯")

    # =========================================================================
    # SLIDE 6: UML Use Case Diagram
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6)
    add_header(s6, "دیدگاه اول مهندسی — نمودار موارد کاربرد (UML Use Case)", "مرزبندی دقیق سامانه نِمُو، بازیگران اولیه و ثانویه و پرهیز از تجزیه کارکردی", "فاز ۲: دیدگاه‌های چهارگانه طراحی", logo_file)

    # Actor Cards
    add_card(s6, Inches(9.0), Inches(1.8), Inches(3.5), Inches(5.1),
             "اکتورهای سیستم (Actors)",
             ["مدیر باشگاه (Primary Actor):",
              "مسئول نظارت، مالی و مدیریت پرسنل",
              "",
              "مربی ورزشی (Primary Actor):",
              "طراح تمرین، آناتومی و ارزیابی شاگرد",
              "",
              "سرور ابری و لایسنس (System Actor):",
              "اکتور ثانویه خارجی جهت اعتبارسنجی امضای دیجیتال و پشتیبان‌گیری ابری",
              "",
              "💡 رعایت اصل مهندسی SSAD:",
              "پرهیز از تجزیه کارکردی (Functional Decomposition) و تمرکز بر اهداف واقعی"],
             COLOR_GREEN, CARD_BG, "👥")

    # Center/Left: Use Case Box
    add_card(s6, Inches(0.8), Inches(1.8), Inches(7.9), Inches(5.1),
             "موارد کاربرد درون مرز سامانه نِمُو (App Boundary)",
             ["UC-01: ورود امن با نام کاربری و رمز عبور هش‌شده (مشترک مدیر و مربی)",
              "UC-02: ثبت و ویرایش پرونده شاگردان همراه با سوابق پزشکی (مشترک مدیر و مربی)",
              "UC-03: ثبت دوره شهریه و محاسبه خودکار تاریخ سررسید (مدیر و مربی)",
              "UC-04: کاوش در بانک ۱۰۰۰+ حرکت، فیلتر آناتومیک و استریم ویدیو (مربی)",
              "UC-05: تدوین برنامه تمرینی و خروجی چاپی/PDF با قلق‌های ایمنی (مربی)",
              "UC-06: مدیریت پرسنل و تعلیق حساب مربی بدون دسترسی به رمز (انحصاری مدیر)",
              "UC-07: اعتبارسنجی لایسنس سخت‌افزاری با سرور ابری نِمُو (تعامل با System Actor)",
              "UC-08: همگام‌سازی و پشتیبان‌گیری رمزنگاری‌شده ابری (تعامل با سرور ابری)"],
             COLOR_WHITE, CARD_BG, "⚙️")

    # =========================================================================
    # SLIDE 7: UML Activity Diagram
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7)
    add_header(s7, "دیدگاه دوم مهندسی — نمودار فعالیت فرآیند اصلی (UML Activity)", "جریان اعتبارسنجی لایسنس، ورود امن، کنترل دسترسی و تدوین برنامه تمرینی", "فاز ۲: دیدگاه‌های چهارگانه طراحی", logo_file)

    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "مرحله اول: گیت امنیتی لایسنس و ورود به برنامه",
             ["۱. راه‌اندازی نرم‌افزار نِمُو",
              "۲. گره تصمیم‌گیری ۱: آیا لایسنس فعال و معتبر است؟",
              "   ❌ مسیر انقضا/عدم وجود: قفل نرم‌افزار و نمایش پنجره فعال‌سازی",
              "   📥 دریافت کد HWID ماشین و وارد کردن توکن لایسنس جدید",
              "   🔐 گره تصمیم‌گیری ۲: آیا امضای HMAC-SHA256 معتبر است؟",
              "      ❌ نامعتبر: نمایش خطای لایسنس و بازگشت به پنجره ورود",
              "      ✅ معتبر: بازگشایی امکانات سیستم و عبور به صفحه لاگین",
              "۳. ورود کاربر با نام‌کاربری و رمز عبور",
              "۴. گره تصمیم‌گیری ۳: بررسی نقش کاربر (مدیر باشگاه یا مربی)"],
             COLOR_RED, CARD_BG, "🔒")

    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "مرحله دوم: جریان کاری تخصصی مربی و صدور برنامه",
             ["۵. ورود به داشبورد اختصاصی مربیگری",
              "۶. انتخاب شاگرد و بررسی پرونده پزشکی و منع آسیب‌های فیزیکی",
              "۷. باز شدن بانک حرکات ورزشی و فیلتر بر اساس عضله هدف",
              "۸. بازبینی ویدیوی آموزشی و اعمال قلق ضدآسیب متناسب با شاگرد",
              "۹. تعیین تعداد روزها، ست‌ها، دامنه‌های تکرار و زمان استراحت",
              "۱۰. ذخیره اتمیک برنامه تمرینی در پایگاه داده محلی SQLite",
              "۱۱. فراخوانی موتور صدور گزارش و تولید فایل ساختاریافته PDF",
              "۱۲. پایان موفقیت‌آمیز جریان کاری و تحویل برنامه به شاگرد"],
             COLOR_GREEN, CARD_BG, "📄")

    # =========================================================================
    # SLIDE 8: 4-Layer System Architecture
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8)
    add_header(s8, "دیدگاه سوم مهندسی — معماری ۴ لایه سامانه (System Architecture)", "تحقق کامل تفکیک دغدغه‌ها (Separation of Concerns) و تضمین پایداری داده‌ها", "فاز ۲: دیدگاه‌های چهارگانه طراحی", logo_file)

    add_card(s8, Inches(0.8), Inches(1.8), Inches(11.7), Inches(1.15),
             "لایه ۱: رابط کاربری دسکتاپ (Desktop Client UI Layer — PyQt6)",
             ["فرم‌های گرافیکی مدرن، ناوبری سریع، رندرینگ ۱۷ پالت رنگی دارک و لایت، اعتبارسنجی بلادرنگ ورودی‌های کاربر"],
             COLOR_GREEN, CARD_BG, "🖥️")

    add_card(s8, Inches(0.8), Inches(3.1), Inches(11.7), Inches(1.15),
             "لایه ۲: منطق تجاری و اعتبارسنجی دامنه (Core Business & Service Layer)",
             ["AuthService (هش و سشن‌ها)، LicenseManager (قفل سخت‌افزاری HWID)، MemberService و WorkoutService (موتور صدور PDF)"],
             COLOR_WHITE, CARD_BG, "🧠")

    add_card(s8, Inches(0.8), Inches(4.4), Inches(11.7), Inches(1.15),
             "لایه ۳: پایگاه‌داده محلی و تراکنش‌های اتمیک (Persistence Layer — SQLite WAL)",
             ["مدل ORM با SQLAlchemy، حالت پیشرفته Write-Ahead Logging (WAL) بدون ریسک فساد فایل دیتابیس در قطع ناگهانی برق"],
             COLOR_YELLOW, CARD_BG, "💽")

    add_card(s8, Inches(0.8), Inches(5.7), Inches(11.7), Inches(1.15),
             "لایه ۴: فضای ابری و توزیع محتوا (Cloud Edge Layer — Cloudflare Workers & R2)",
             ["دروازه سرورلس Cloudflare با زمان پاسخ <۳۰ms، استریم ۱۰۰۰+ ویدیو بدون هزینه خروجی پهنای باند و ربات لایسنس تلگرام"],
             COLOR_RED, CARD_BG, "☁️")

    # =========================================================================
    # SLIDE 9: ERD & Data Model
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9)
    add_header(s9, "دیدگاه چهارم مهندسی — مدل موجودیت‌ها و داده‌ها (ERD)", "نرمال‌سازی اصولی، حل رابطه چند-به-چند تمرینات و تضمین یکپارچگی ارجاعی", "فاز ۲: دیدگاه‌های چهارگانه طراحی", logo_file)

    add_card(s9, Inches(8.8), Inches(1.8), Inches(3.7), Inches(5.1),
             "جداول اصلی سامانه (Entities)",
             ["USERS: کاربران سیستم",
              "  • id (PK), username (UK)",
              "  • password_hash, role",
              "  • is_active (تعلیق امن)",
              "",
              "MEMBERS: اعضای باشگاه",
              "  • id (PK), full_name, phone",
              "  • medical_history, trainer_id (FK)",
              "",
              "TUITIONS: دوره‌های شهریه",
              "  • id (PK), member_id (FK)",
              "  • amount, start_date, end_date"],
             COLOR_GREEN, CARD_BG, "📊")

    add_card(s9, Inches(4.8), Inches(1.8), Inches(3.7), Inches(5.1),
             "طراحی بانک حرکات و تمرینات",
             ["EXERCISES: بانک حرکات ورزشی",
              "  • id (PK), name_fa",
              "  • primary_muscle (عضله هدف)",
              "  • contraindications (منع آسیب)",
              "  • video_url, description",
              "",
              "WORKOUT_PLANS: برنامه تمرینی",
              "  • id (PK), member_id (FK)",
              "  • trainer_id (FK), title",
              "  • created_at (تاریخ صدور)"],
             COLOR_WHITE, CARD_BG, "🏋️")

    add_card(s9, Inches(0.8), Inches(1.8), Inches(3.7), Inches(5.1),
             "حل رابطه M:N با جدول واسط",
             ["WORKOUT_ITEMS: جدول رابط",
              "  • id (PK)",
              "  • plan_id (FK -> WORKOUT_PLANS)",
              "  • exercise_id (FK -> EXERCISES)",
              "  • day_number (شماره روز)",
              "  • sets, reps, rest_seconds",
              "",
              "💡 مزیت مهندسی رابطه M:N:",
              "یک حرکت می‌تواند در صدها برنامه تکرار شود، با مقادیر ست و تکرار کاملاً مجزا و بدون افزونگی داده."],
             COLOR_RED, CARD_BG, "🔗")

    # =========================================================================
    # SLIDE 10: REST API Contracts & Status Codes
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10)
    add_header(s10, "قرارداد APIها و استانداردهای ارتباطی وب (REST Contracts)", "استفاده از کدهای وضعیت معنادار طبق استانداردهای RFC 7231 و RFC 4918", "فاز ۳: قرارداد API و هاستینگ", logo_file)

    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "جدول اندپوینت‌های کلیدی سرویس (API Endpoints)",
             ["POST  /api/auth/login",
              "  ورودی: username, password  -> پاسخ: Token, Role",
              "  خطاها: 401 Unauthorized, 400 Bad Request",
              "",
              "POST  /api/members",
              "  ورودی: name, national_id, phone, medical",
              "  خطاها: 409 Conflict (کد ملی تکراری)",
              "        422 Unprocessable (شماره نامعتبر)",
              "",
              "POST  /api/tuitions",
              "  ورودی: member_id, amount, start_date, days",
              "  خطاها: 404 Member Not Found, 400 Negative Amount",
              "",
              "POST  /api/sync/backup",
              "  ورودی: Encrypted DB Stream  -> پاسخ: 200 OK"],
             COLOR_WHITE, CARD_BG, "🌐")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "توجیه کدهای خطای وب و امنیت توکن کلاینت",
             ["چرا به جای خطای عمومی ۴۰۰ از ۴۰۹ و ۴۲۲ استفاده شد؟",
              "  • ۴۰۰ Bad Request: فقط برای خطای گرامری و ساختار خراب JSON.",
              "  • ۴۰۹ Conflict: تضاد وضعیتی دیتابیس (مانند کد ملی تکراری) تا کلاینت مستقیماً فرم بازیابی عضو را پیشنهاد دهد.",
              "  • ۴۲۲ Unprocessable Entity: خطای اعتبارسنجی مقادیر (تلفن غیراستاندارد) تا کلاینت فوراً دور فیلد مربوطه را قرمز کند.",
              "",
              "امنیت توکن Bearer در کلاینت دسکتاپ:",
              "  • توکن‌ها هرگز به صورت متن خام در ویندوز ذخیره نمی‌شوند.",
              "  • استفاده از Windows DPAPI برای رمزنگاری متقارن با کلید سخت‌افزار ماشین و کاربر ویندوز."],
             COLOR_GREEN, CARD_BG, "🛡️")

    # =========================================================================
    # SLIDE 11: Figma Prototype & Cloud Hosting
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s11)
    add_header(s11, "پروتوتایپ تعاملی فیگما و توجیه هاستینگ اقتصادی", "پروتوتایپ با وفاداری بالا (High-Fidelity) و استریم ابری ویدیوها با هزینه صفر دلار", "فاز ۳: پروتوتایپ و هاستینگ", logo_file)

    # Left: Figma Prototype Card
    add_card(s11, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "پروتوتایپ کلیک‌پذیر در فیگما (Figma Prototype)",
             ["طراحی به صورت High-Fidelity و مدل‌سازی رفتار واقعی سیستم:",
              "  ۱. جریان ورود و شبیه‌سازی سناریوی خطای رمز و نام کاربری",
              "  ۲. داشبورد مدیریت و مشاهده سریع سررسید شهریه‌های اعضا",
              "  ۳. فرم ثبت عضو همراه با اعتبارسنجی زنده فیلدها",
              "  ۴. فیلتر بصری آناتومی عضلات روی آدمک هوشمند",
              "  ۵. ماژول تدوین برنامه تمرینی چندروزه و پیش‌نمایش خروجی PDF",
              "",
              "🔗 لینک رسمی پروتوتایپ فیگما در اکانت توسعه‌دهنده:",
              "https://www.figma.com/design/bxozUbyh4zZVSQXlJFVxeF"],
             COLOR_GREEN, CARD_BG, "🎨")

    # Right: Hosting Rationale
    add_card(s11, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.1),
             "توجیه فنی پشته و برآورد هزینه‌ها (Hosting Rationale)",
             ["پشته فنی کلاینت: Python 3.12 + PyQt6 (چندسکویی، عملکرد بومی)",
              "پشته وب‌سایت: HTML5, Modern CSS, Vanilla JS (فوق‌العاده سبک)",
              "پشته سرورلس: Cloudflare Workers در ۳۰۰ دیتاسنتر لبه جهان",
              "ذخیره‌سازی مدیا: Cloudflare R2 با سازگاری کامل S3 API",
              "",
              "💰 برآورد هزینه در فاز MVP: صفر دلار ($0)",
              "  • حذف کامل هزینه‌های سنگین ترافیک خروجی ویدیو (Zero Egress)",
              "  • پشتیبانی از ۱۰۰,۰۰۰ درخواست در روز در پلن کاملاً رایگان کلودفلر",
              "  • عدم نیاز به نگهداری سرور VPS لینوکسی و ریسک‌های امنیتی آن"],
             COLOR_RED, CARD_BG, "☁️")

    # =========================================================================
    # SLIDE 12: Conclusion & Next Steps
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s12)
    add_header(s12, "جمع‌بندی دستاوردها و نقشه راه فازهای بعدی", "پایان موفقیت‌آمیز فاز تحلیل و طراحی و آمادگی کامل برای ورود به کدنویسی هسته", "فاز ۴: ارزیابی و دفاع اول", logo_file)

    add_card(s12, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.3),
             "دستاوردهای تثبیت‌شده تا ارائه اول (Phases 1-3)",
             ["✅ تعریف شفاف MVP و تدوین داستان‌های کاربری با معیارهای ۳ گانه",
              "✅ طراحی و مستندسازی ۴ دیدگاه مهندسی (Use Case, Activity, 4-Layer, ERD)",
              "✅ تدوین جدول قرارداد APIها بر اساس استانداردهای RFC کدهای خطا",
              "✅ ساخت پروتوتایپ تعاملی و رفتار کاربری در فیگما",
              "✅ معماری پایگاه داده محلی پایدار با SQLite WAL بدون خرابی در قطع برق",
              "✅ استقرار وب‌سایت رسمی و استریم ابری با معماری بدون هزینه"],
             COLOR_GREEN, CARD_BG, "🏆")

    add_card(s12, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.3),
             "گام‌های اجرایی فاز بعدی (ارائه دوم — ۲۳ و ۲۴ آذر)",
             ["۱. پیاده‌سازی کامل احراز هویت و سطوح دسترسی (Authentication & RBAC)",
              "۲. یکپارچه‌سازی نهایی دیتابیس لوکال با لایه سرویس‌های نرم‌افزار",
              "۳. اجرای تست‌های یکپارچگی خودکار برای فرآیند ثبت شاگرد و شهریه",
              "۴. ارائه دموی زنده و قابل اجرا از حداقل یک ویژگی کامل سیستم در کلاس",
              "۵. آماده‌سازی پکیج ارزیابی مرحله دوم طبق زمان‌بندی Work-Plan"],
             COLOR_BLUE, CARD_BG, "🚀")

    # Bottom Thank You Box
    thx = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.25), Inches(11.7), Inches(0.85))
    thx.fill.solid(); thx.fill.fore_color.rgb = CARD_BG
    thx.line.color.rgb = COLOR_GREEN; thx.line.width = Pt(1.5)
    ttf = thx.text_frame
    tp = ttf.paragraphs[0]
    tp.text = "🙏 با سپاس فراوان از توجه شما — مشتاقانه آماده شنیدن نظرات و پاسخ به سوالات داوران محترم هستم"
    tp.font.name = FONT_NAME; tp.font.size = Pt(13); tp.font.bold = True; tp.font.color.rgb = COLOR_WHITE; tp.alignment = PP_ALIGN.CENTER

    prs.save(out_pptx_path)
    print(f"Presentation saved successfully to: {out_pptx_path}")

if __name__ == "__main__":
    out_dir = Path("scratch/presentation_deck")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "Nemov_Presentation_1.pptx"
    build_deck(str(out_file))
