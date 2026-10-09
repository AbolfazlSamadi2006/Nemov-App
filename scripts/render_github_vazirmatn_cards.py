import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea
)
from PyQt6.QtGui import QFontDatabase, QFont, QPixmap
from PyQt6.QtCore import Qt

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR"] = "2"

app = QApplication(sys.argv)
app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

p_reg = str(Path("resources/fonts/Vazirmatn-Regular.ttf").resolve())
p_bold = str(Path("resources/fonts/Vazirmatn-Bold.ttf").resolve())
id_reg = QFontDatabase.addApplicationFont(p_reg)
id_bold = QFontDatabase.addApplicationFont(p_bold)
families = QFontDatabase.applicationFontFamilies(id_reg)
FONT_FAMILY = families[0] if families else "Vazirmatn"
print("Loaded Font Family:", FONT_FAMILY)

default_font = QFont(FONT_FAMILY, 11)
app.setFont(default_font)

OUT_DIR = Path("resources/github_assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)
BRAIN_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")


def make_badge(text: str, bg: str, fg: str, border: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 13px;
            padding: 5px 14px;
            font-family: '{FONT_FAMILY}';
            font-size: 12px;
            font-weight: bold;
        }}
    """)
    return lbl


def make_section_header(title_text: str) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet("""
        QFrame {
            background: transparent;
            border: none;
            border-bottom: 2px solid #991B1B;
            padding-bottom: 6px;
        }
    """)
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(0, 8, 0, 6)
    lbl = QLabel(title_text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            color: #FFFFFF;
            font-family: '{FONT_FAMILY}';
            font-size: 18px;
            font-weight: bold;
            border: none;
        }}
    """)
    lay.addWidget(lbl)
    lay.addStretch()
    return frame


def make_feature_table(rows_data: list) -> QFrame:
    tbl = QFrame()
    tbl.setObjectName("featTable")
    tbl.setStyleSheet("""
        QFrame#featTable {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-radius: 12px;
        }
    """)
    vlay = QVBoxLayout(tbl)
    vlay.setContentsMargins(0, 0, 0, 0)
    vlay.setSpacing(0)

    # Header row
    hdr = QFrame()
    hdr.setStyleSheet("""
        QFrame {
            background-color: #21262D;
            border-top-left-radius: 11px;
            border-top-right-radius: 11px;
            border-bottom: 2px solid #991B1B;
        }
    """)
    hlay = QHBoxLayout(hdr)
    hlay.setContentsMargins(16, 12, 16, 12)
    hlay.setSpacing(16)

    lbl_h1 = QLabel("🎯 بخش / قابلیت")
    lbl_h1.setFixedWidth(255)
    lbl_h1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl_h1.setStyleSheet(f"color: #F87171; font-family: '{FONT_FAMILY}'; font-size: 13.5px; font-weight: bold; border: none; background: transparent;")

    lbl_h2 = QLabel("✨ شرح کامل ویژگی‌ها و ارتقای عملکرد")
    lbl_h2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl_h2.setStyleSheet(f"color: #F87171; font-family: '{FONT_FAMILY}'; font-size: 13.5px; font-weight: bold; border: none; background: transparent;")

    hlay.addWidget(lbl_h1)
    hlay.addWidget(lbl_h2, 1)
    vlay.addWidget(hdr)

    for idx, (col1, col2) in enumerate(rows_data):
        row_f = QFrame()
        is_last = (idx == len(rows_data) - 1)
        bg_col = "#161B22" if idx % 2 == 0 else "#13181E"
        b_bottom = "none" if is_last else "1px solid #262C36"
        radius_css = "border-bottom-left-radius: 11px; border-bottom-right-radius: 11px;" if is_last else ""
        row_f.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border-bottom: {b_bottom};
                {radius_css}
            }}
        """)
        rlay = QHBoxLayout(row_f)
        rlay.setContentsMargins(16, 12, 16, 12)
        rlay.setSpacing(16)

        c1 = QLabel(col1)
        c1.setFixedWidth(255)
        c1.setWordWrap(True)
        c1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        c1.setStyleSheet(f"color: #FFFFFF; font-family: '{FONT_FAMILY}'; font-size: 13px; font-weight: bold; border: none; background: transparent;")

        c2 = QLabel(col2)
        c2.setWordWrap(True)
        c2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        c2.setStyleSheet(f"color: #D0D7DE; font-family: '{FONT_FAMILY}'; font-size: 13px; line-height: 1.6; border: none; background: transparent;")

        rlay.addWidget(c1)
        rlay.addWidget(c2, 1)
        vlay.addWidget(row_f)

    return tbl


def build_download_button() -> QWidget:
    w = QFrame()
    w.setFixedSize(840, 82)
    w.setObjectName("dlBtn")
    w.setStyleSheet("""
        QFrame#dlBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7F1D1D, stop:0.5 #DC2626, stop:1 #7F1D1D);
            border: 2px solid #F87171;
            border-radius: 14px;
        }
    """)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(20, 12, 20, 12)
    lay.setSpacing(4)

    t1 = QLabel("📥 دانلود مستقیم فایل نصاب نسخه ۳.۲.۱ (Yalda_Setup_v3.2.1.exe)")
    t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
    t1.setStyleSheet(f"color: #FFFFFF; font-family: '{FONT_FAMILY}'; font-size: 18px; font-weight: bold; background: transparent; border: none;")

    t2 = QLabel("نصب خودکار به همراه تمامی پیش‌نیازها و فونت‌های فارسی  •  حجم: ۹۸.۵ مگابایت  •  ویندوز ۱۰ و ۱۱ (۶۴ بیتی)")
    t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
    t2.setStyleSheet(f"color: #FEE2E2; font-family: '{FONT_FAMILY}'; font-size: 12.5px; background: transparent; border: none;")

    lay.addWidget(t1)
    lay.addWidget(t2)
    return w


def build_hero_box(is_release: bool = False) -> QFrame:
    hero = QFrame()
    hero.setObjectName("heroBox")
    hero.setStyleSheet("""
        QFrame#heroBox {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1F0B0E, stop:1 #11161D);
            border: 1px solid #4C1D24;
            border-radius: 14px;
        }
    """)
    vlay = QVBoxLayout(hero)
    vlay.setContentsMargins(24, 22, 24, 22)
    vlay.setSpacing(10)

    lbl_title = QLabel("🏋️‍♂️ سامانه هوشمند مدیریت باشگاه بدنسازی و برنامه‌ریزی ورزشی «یلدا»")
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_title.setStyleSheet(f"color: #FFFFFF; font-family: '{FONT_FAMILY}'; font-size: 22px; font-weight: bold; background: transparent; border: none;")

    lbl_en = QLabel("Yalda Gym & Fitness Management Suite — v3.2.1")
    lbl_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_en.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    lbl_en.setStyleSheet(f"color: #F87171; font-family: '{FONT_FAMILY}'; font-size: 14px; font-weight: bold; background: transparent; border: none;")

    lbl_desc = QLabel(
        "یک دستیار همه‌فن‌حریف، سریع و کاملاً فارسی برای مربیان حرفه‌ای و مدیران باشگاه‌های ورزشی؛\n"
        "از سامانه هوشمند اطلاع‌رسانی پیامک تا پرونده ورزشکاران، طراحی تمرین و تغذیه، حسابداری و پشتیبان‌گیری ابری"
    )
    lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_desc.setWordWrap(True)
    lbl_desc.setStyleSheet(f"color: #C9D1D9; font-family: '{FONT_FAMILY}'; font-size: 13.5px; background: transparent; border: none;")

    badges_lay = QHBoxLayout()
    badges_lay.setSpacing(10)
    badges_lay.addStretch()
    badges_lay.addWidget(make_badge("🔥 نسخه ۳.۲.۱ (Latest Release)", "#7F1D1D", "#FECACA", "#DC2626"))
    badges_lay.addWidget(make_badge("💻 ویندوز ۱۰ و ۱۱ (۶۴ بیتی)", "#1E3A8A", "#BFDBFE", "#3B82F6"))
    badges_lay.addWidget(make_badge("📩 سامانه هوشمند پیامک فعال", "#047857", "#A7F3D0", "#10B981"))
    badges_lay.addWidget(make_badge("☁️ پشتیبان‌گیری ابری و ایمیل فعال", "#7C2D12", "#FED7AA", "#F97316"))
    badges_lay.addWidget(make_badge("✨ رابط کاربری ۱۰۰٪ فارسی و واکنش‌گرا", "#4C1D95", "#DDD6FE", "#8B5CF6"))
    badges_lay.addStretch()

    vlay.addWidget(lbl_title)
    vlay.addWidget(lbl_en)
    vlay.addWidget(lbl_desc)
    vlay.addSpacing(4)
    vlay.addLayout(badges_lay)
    return hero


def build_footer_box() -> QFrame:
    ftr = QFrame()
    ftr.setStyleSheet("""
        QFrame {
            background: transparent;
            border: none;
            border-top: 1px solid #30363D;
            padding-top: 12px;
        }
    """)
    lay = QVBoxLayout(ftr)
    lay.setContentsMargins(0, 12, 0, 4)
    lay.setSpacing(4)

    l1 = QLabel("طراحی و توسعه جهت ارتقای سطح حرفه‌ای مربیان و باشگاه‌های ورزشی ایران")
    l1.setAlignment(Qt.AlignmentFlag.AlignCenter)
    l1.setStyleSheet(f"color: #C9D1D9; font-family: '{FONT_FAMILY}'; font-size: 13px; font-weight: bold; border: none;")

    l2 = QLabel("© 2026 Abolfazl Samadi — تمامی حقوق این نرم‌افزار محفوظ است.")
    l2.setAlignment(Qt.AlignmentFlag.AlignCenter)
    l2.setStyleSheet(f"color: #8B949E; font-family: '{FONT_FAMILY}'; font-size: 12px; border: none;")

    lay.addWidget(l1)
    lay.addWidget(l2)
    return ftr


HIGHLIGHTS_ROWS_V3_2_1 = [
    ("📩 سامانه هوشمند ارسال پیامک\n(SMS.ir Smart Center)",
     "اتصال مستقیم و پایدار به وب‌سرویس پیامک خدماتی SMS.ir؛ قالب‌های رسمی تاییدشده برای یادآوری سررسید شهریه، تبریک تولد، تغییر سانس و اطلاعیه تعطیلی بدون مسدود شدن توسط بلک‌لیست مخابرات."),
    ("🛠️ بازطراحی و تب‌بندی تنظیمات\nو مرکز پشتیبان‌گیری",
     "تفکیک استاندارد پروفایل مربی و ادمین، ماژول پشتیبان‌گیری و بازگردانی با چیدمان منظم دکمه‌ها در سمت چپ، و تاریخچه اعلانات و لاگ‌ها در قالب تب‌های مستقل بدون نیاز به اسکرول صفحه."),
    ("🔐 قفل امنیتی سخت‌افزاری پایدار\n(Persistent Hardware License)",
     "تثبیت لایسنس و فعال‌سازی روی سیستم؛ عدم قفل شدن نرم‌افزار پس از نصب آپدیت‌ها و نسخه‌های جدید نصاب بدون نیاز به لاگین مجدد با حساب ادمین."),
    ("⚡ ناوبری سریع و هوشمند\nبا کلید Enter در لاگین",
     "انتقال خودکار فوکوس بین نام کاربری و کلمه عبور و ورود مستقیم به برنامه با فشردن کلید Enter به همراه ذخیره امن مشخصات آخرین مربی."),
    ("💳 همگام‌سازی مبالغ و\nتاریخ سررسید شهریه",
     "هماهنگی خودکار مبالغ و تاریخ‌های انقضا میان دیالوگ پرداخت سریع و مشخصات پرونده عضو با ذخیره‌سازی لحظه‌ای در دیتابیس."),
    ("🖥️ بهینه‌سازی جدول اعضا\nدر تمامی رزولوشن‌ها",
     "تنظیم دقیق عرض ستون‌ها و اختصاص فضای کافی به ستون عملیات جهت نمایش بدون نقص و کامل دکمه‌ها در تمامی مانیتورها و لپ‌تاپ‌ها."),
    ("📊 مستندسازی و تحلیل جامع\nرقبای بازار ورزشی",
     "تدوین سند فنی بنچ‌مارک (BENCHMARK_AND_COMPETITIVE_ANALYSIS.md) با ارزیابی بیش از ۳۰ شاخص در مقایسه با نرم‌افزارهای پیشرو داخلی و بین‌المللی."),
    ("☁️ پشتیبان‌گیری چندگانه ابری،\nایمیل و محلی",
     "پشتیبان‌گیری رمزنگاری‌شده فشرده (ZIP) در ۳ مقصد با قابلیت بازگردانی مستقیم از سرور ابری کلودفلر و آرشیو محلی."),
]


def build_steps_box() -> QFrame:
    box = QFrame()
    box.setObjectName("stepsBox")
    box.setStyleSheet("""
        QFrame#stepsBox {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-right: 4px solid #10B981;
            border-radius: 12px;
        }
    """)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(18, 14, 18, 14)
    lay.setSpacing(8)

    steps = [
        "۱. روی دکمه قرمز «دانلود مستقیم فایل نصاب نسخه ۳.۲.۱» کلیک کنید (یا از بخش Assets در پایین صفحه، فایل Yalda_Setup_v3.2.1.exe را دانلود نمایید).",
        "۲. فایل نصاب را اجرا کنید؛ تمامی فونت‌های فارسی و پیش‌نیازها به صورت خودکار نصب شده و میانبر برنامه روی دسکتاپ شما قرار می‌گیرد.",
        "۳. در صورت ارتقا از نسخه‌های پیشین، کلیه اطلاعات، پرونده‌ها، تنظیمات و لایسنس سیستم کاملاً حفظ خواهد شد.",
    ]
    for s in steps:
        lbl = QLabel(s)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet(f"color: #E6EDF3; font-family: '{FONT_FAMILY}'; font-size: 13px; border: none; background: transparent;")
        lay.addWidget(lbl)
    return box


def build_release_showcase() -> QWidget:
    root = QFrame()
    root.setFixedWidth(940)
    root.setObjectName("rootCard")
    root.setStyleSheet("""
        QFrame#rootCard {
            background-color: #0D1117;
            border: 1px solid #30363D;
            border-radius: 16px;
        }
    """)
    vlay = QVBoxLayout(root)
    vlay.setContentsMargins(28, 28, 28, 24)
    vlay.setSpacing(16)

    vlay.addWidget(build_hero_box(is_release=True))
    vlay.addWidget(make_section_header("🔥 ویژگی‌ها و تغییرات کلیدی نسخه ۳.۲.۱"))
    vlay.addWidget(make_feature_table(HIGHLIGHTS_ROWS_V3_2_1))
    vlay.addWidget(make_section_header("📥 راهنمای دانلود و نصب سریع (بدون نیاز به پیش‌نیاز)"))
    vlay.addWidget(build_steps_box())
    vlay.addWidget(build_footer_box())
    root.adjustSize()
    return root


def make_info_card(title: str, bullets: list) -> QFrame:
    card = QFrame()
    card.setObjectName("infoCard")
    card.setStyleSheet("""
        QFrame#infoCard {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-radius: 12px;
        }
    """)
    vlay = QVBoxLayout(card)
    vlay.setContentsMargins(16, 14, 16, 14)
    vlay.setSpacing(8)

    lbl_t = QLabel(title)
    lbl_t.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl_t.setStyleSheet(f"""
        color: #FCA5A5;
        font-family: '{FONT_FAMILY}';
        font-size: 14.5px;
        font-weight: bold;
        padding-bottom: 6px;
        border-bottom: 1px solid #262C36;
        background: transparent;
    """)
    vlay.addWidget(lbl_t)

    for b in bullets:
        lbl_b = QLabel(f"•  {b}")
        lbl_b.setWordWrap(True)
        lbl_b.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        lbl_b.setStyleSheet(f"color: #D0D7DE; font-family: '{FONT_FAMILY}'; font-size: 12.8px; border: none; background: transparent;")
        vlay.addWidget(lbl_b)

    vlay.addStretch()
    return card


def build_readme_showcase() -> QWidget:
    root = QFrame()
    root.setFixedWidth(940)
    root.setObjectName("rootCard")
    root.setStyleSheet("""
        QFrame#rootCard {
            background-color: #0D1117;
            border: 1px solid #30363D;
            border-radius: 16px;
        }
    """)
    vlay = QVBoxLayout(root)
    vlay.setContentsMargins(28, 28, 28, 24)
    vlay.setSpacing(16)

    vlay.addWidget(build_hero_box(is_release=False))

    # Intro callout box
    intro = QFrame()
    intro.setObjectName("introBox")
    intro.setStyleSheet("""
        QFrame#introBox {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-right: 4px solid #DC2626;
            border-radius: 12px;
        }
    """)
    ilay = QVBoxLayout(intro)
    ilay.setContentsMargins(18, 14, 18, 14)
    ilay.setSpacing(6)
    it1 = QLabel("🌟 چرا نرم‌افزار باشگاهی «یلدا»؟")
    it1.setAlignment(Qt.AlignmentFlag.AlignRight)
    it1.setStyleSheet(f"color: #FFFFFF; font-family: '{FONT_FAMILY}'; font-size: 15px; font-weight: bold; border: none; background: transparent;")
    it2 = QLabel(
        "نرم‌افزار یلدا (Yalda) با درک دقیق نیازهای روزمره مربیان بدنسازی و فیتنس طراحی شده است؛ محیطی با تم تاریک اختصاصی (Dark-Red Obsidian)، "
        "چیدمان کاملاً راست‌به‌چپ (RTL) و سرعت اجرای لحظه‌ای که بدون نیاز به اینترنت نیز تمامی امور باشگاه را مدیریت می‌کند و در عین حال به سامانه پیامک و سرور ابری مجهز است."
    )
    it2.setWordWrap(True)
    it2.setAlignment(Qt.AlignmentFlag.AlignRight)
    it2.setStyleSheet(f"color: #D0D7DE; font-family: '{FONT_FAMILY}'; font-size: 13px; border: none; background: transparent;")
    ilay.addWidget(it1)
    ilay.addWidget(it2)
    vlay.addWidget(intro)

    vlay.addWidget(make_section_header("🔥 تازه‌های نسخه ۳.۲.۱ (Release Highlights)"))
    vlay.addWidget(make_feature_table(HIGHLIGHTS_ROWS_V3_2_1))

    vlay.addWidget(make_section_header("💎 امکانات جامع نرم‌افزار در یک نگاه"))
    grid = QGridLayout()
    grid.setSpacing(14)
    grid.addWidget(make_info_card("۱. 👥 پرونده کامل ورزشکاران و سنجش فیزیکی", [
        "ثبت مشخصات فردی، تماس، تاریخ تولد شمسی و عکس پروفایل (وب‌کم یا فایل).",
        "ارزیابی آنتروپومتریک (قد، وزن، درصد چربی، دور سینه، کمر، شکم، بازو، ران و ساق).",
        "مقایسه تصویری قبل و بعد (Before & After) جهت پایش پیشرفت بدنی شاگرد.",
        "مدیریت مدارک پزشکی چندصفحه‌ای (PDF و تصویر) با قابلیت زوم و چرخش صفحات.",
    ]), 0, 0)
    grid.addWidget(make_info_card("۲. 🥗 مهندسی تغذیه، رژیم ایرانی و BMR / TDEE", [
        "محاسبه خودکار متابولیسم پایه (BMR) و کالری تثبیت روزانه (TDEE) با فرمول Mifflin-St Jeor.",
        "محاسبه لحظه‌ای گرم و درصد پروتئین، کربوهیدرات و چربی بر اساس هدف شاگرد.",
        "بانک جامع غذاهای ایرانی و مکمل‌ها با ارزش غذایی دقیق و امکان افزودن خوراکی جدید.",
        "ذخیره و بارگذاری آنی الگوهای غذایی پرتکرار در بانک الگوها.",
    ]), 0, 1)
    grid.addWidget(make_info_card("۳. 🏋️‍♂️ طراحی برنامه تمرینی و بانک حرکات چندرسانه‌ای", [
        "برنامه‌ریزی ۱ تا ۶ روز در هفته با تنظیم ست، تکرار، سیستم تمرینی و توضیحات حرکت.",
        "بانک حرکات مجهز به تصویر و ویدیوی آموزشی با تفکیک عضله هدف و تجهیزات.",
        "بانک الگوهای آماده تمرینی جهت صدور سریع برنامه برای شاگردان جدید.",
        "خروجی چاپی PDF، فایل وب تعاملی HTML و بسته فشرده ZIP.",
    ]), 1, 0)
    grid.addWidget(make_info_card("۴. 🔐 مدیریت چندمربی، امنیت و سامانه پیامک", [
        "محیط کاری کاملاً مستقل و تفکیک‌شده برای هر مربی با نام کاربری و رمز اختصاصی.",
        "ارسال آنی پیامک یادآوری شهریه و تبریک تولد از طریق وب‌سرویس رسمی SMS.ir.",
        "پنل مدیریت ارشد (Admin) جهت مدیریت مربیان و لایسنس پایدار سخت‌افزاری.",
        "ثبت خودکار وقایع و لاگ‌های فنی (System Diagnostics) با نمایشگر داخلی.",
    ]), 1, 1)
    vlay.addLayout(grid)

    vlay.addWidget(make_section_header("🚀 راهنمای دانلود و نصب سریع (ویژه مربیان — بدون نیاز به پیش‌نیاز)"))
    vlay.addWidget(build_steps_box())

    vlay.addWidget(make_section_header("🛠️ معماری و تکنولوژی‌های به‌کاررفته"))
    tech_row = QHBoxLayout()
    tech_row.setSpacing(8)
    tech_row.addStretch()
    for t in [
        "Python 3.10+", "PyQt6 (RTL & High-DPI)", "SQLite 3 + SQLAlchemy",
        "ReportLab PDF", "OpenPyXL Excel", "SMS.ir API",
        "OpenCV & PyMuPDF", "Cloudflare Workers Sync", "PyInstaller + NSIS"
    ]:
        p = make_badge(t, "#161B22", "#C9D1D9", "#30363D")
        tech_row.addWidget(p)
    tech_row.addStretch()
    vlay.addLayout(tech_row)

    vlay.addWidget(build_footer_box())
    root.adjustSize()
    return root


def save_widget_png(w: QWidget, out_path: Path, qa_path: Path):
    scroll = QScrollArea()
    scroll.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(False)
    scroll.setWidget(w)
    scroll.resize(1000, 800)
    scroll.show()
    app.processEvents()

    target_w = w.width() if w.width() > 0 else 940
    if w.layout():
        w.layout().activate()
    target_h = w.layout().totalSizeHint().height() if w.layout() else w.sizeHint().height()
    w.setFixedSize(target_w, target_h)
    app.processEvents()

    dpr = app.primaryScreen().devicePixelRatio()
    pix = QPixmap(int(target_w * dpr), int(target_h * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    w.render(pix)
    pix.save(str(out_path), "PNG")
    pix.save(str(qa_path), "PNG")
    scroll.hide()
    print(f"Saved {out_path} ({pix.width()}x{pix.height()} px, {out_path.stat().st_size // 1024} KB)")


btn_w = build_download_button()
save_widget_png(btn_w, OUT_DIR / "download_btn_v3_2_1.png", BRAIN_DIR / "qa_download_btn_v3_2_1.png")

rel_w = build_release_showcase()
save_widget_png(rel_w, OUT_DIR / "release_v3_2_1_showcase.png", BRAIN_DIR / "qa_release_v3_2_1_showcase.png")

rdm_w = build_readme_showcase()
save_widget_png(rdm_w, OUT_DIR / "readme_full_showcase.png", BRAIN_DIR / "qa_readme_full_showcase.png")

print("ALL ASSETS RENDERED SUCCESSFULLY FOR v3.2.1!")
