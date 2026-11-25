import html
import json
import re
from pathlib import Path
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"

SHARED_FONT_CSS = (ASSETS_DIR / "shared_font.css").read_text(encoding="utf-8")
EXERCISE_TITLE_MAP = json.loads((ASSETS_DIR / "exercise_titles.json").read_text(encoding="utf-8"))
LANDING_HTML = (TEMPLATES_DIR / "landing.html").read_text(encoding="utf-8")


def escape_html(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def escape_js(s) -> str:
    text = str(s if s is not None else "")
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def resolve_exercise_title(filename: str, query_title: str = None) -> str:
    if query_title and query_title.strip():
        return query_title.strip()
    if not filename:
        return "حرکت تمرینی نِمُو"
    base = re.sub(r"\.(mp4|webm|ogg|mov|m4v|jpg|jpeg|png|webp|bmp|gif)$", "", filename, flags=re.I)
    if base in EXERCISE_TITLE_MAP:
        return EXERCISE_TITLE_MAP[base]
    # strip trailing _hash
    no_hash = re.sub(r"_[0-9a-f]{6,10}$", "", base, flags=re.I)
    if no_hash in EXERCISE_TITLE_MAP:
        return EXERCISE_TITLE_MAP[no_hash]
    clean = base.replace("_", " ").replace("-", " ").strip()
    return clean or filename


def render_login_page(error: str = None) -> str:
    error_html = f'<div class="error-alert">{escape_html(error)}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به سرور ابری نِمُو | Nemov Cloud</title>
    <style>
        {SHARED_FONT_CSS}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #0F0F0F;
            color: #FFFFFF;
            font-family: var(--font-body);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
            overflow-x: hidden;
        }}
        .card {{
            background-color: #1A1A1A;
            border: 1px solid #2D2D2D;
            border-top: 4px solid #8B0000;
            border-radius: 14px;
            width: 100%;
            max-width: 400px;
            padding: 36px 28px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.6);
        }}
        .logo-box {{ text-align: center; margin-bottom: 24px; }}
        .logo-box h1 {{ font-family: var(--font-heading); font-size: 21px; font-weight: 800; color: #FFFFFF; margin-bottom: 6px; }}
        .logo-box p {{ font-size: 13px; color: #9CA3AF; }}
        .input-group {{ margin-bottom: 18px; }}
        .input-group label {{ display: block; font-size: 13px; font-weight: bold; color: #D1D5DB; margin-bottom: 8px; }}
        .input-group input {{
            width: 100%;
            height: 48px;
            background-color: #262626;
            border: 1px solid #3F3F46;
            border-radius: 8px;
            padding: 0 14px;
            color: #FFFFFF;
            font-size: 14px;
            font-family: var(--font-body);
            outline: none;
            transition: border-color 0.2s;
        }}
        .input-group input:focus {{ border-color: #8B0000; }}
        .btn-submit {{
            width: 100%;
            height: 48px;
            background-color: #8B0000;
            color: #FFFFFF;
            font-family: var(--font-heading);
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s, transform 0.1s;
        }}
        .btn-submit:hover {{ background-color: #A91D22; }}
        .btn-submit:active {{ transform: scale(0.98); }}
        .error-alert {{ background-color: rgba(220, 38, 38, 0.15); border: 1px solid #DC2626; color: #F87171; padding: 12px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-box">
            <h1>☁️ سرور ابری نِمُو (Nemov Cloud)</h1>
            <p>ورود مدیر کل به سامانه مانیتورینگ و پیامک</p>
        </div>
        {error_html}
        <form action="/login" method="POST">
            <div class="input-group">
                <label for="username">نام کاربری ادمین</label>
                <input type="text" id="username" name="username" placeholder="نام کاربری" required autofocus>
            </div>
            <div class="input-group">
                <label for="password">رمز عبور</label>
                <input type="password" id="password" name="password" placeholder="رمز عبور" required>
            </div>
            <button type="submit" class="btn-submit">ورود به پنل مدیریت</button>
        </form>
    </div>
</body>
</html>"""


def to_fa_num(n: int) -> str:
    return f"{n:,}".translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def render_dashboard_page(
    trainers: list,
    total_size_mb: str,
    last_activity: str,
    media_list: list,
    total_media_size_mb: str,
    default_tab: str,
    origin_url: str,
    sms_list: list,
    total_sms_remaining: int,
    total_sms_sent: int,
    sms_logs: list,
) -> str:
    trainer_rows = []
    for idx, t in enumerate(trainers):
        phone = t.get("phone", "")
        tname = t.get("trainer_name") or "مربی ناشناس"
        trainer_rows.append(f"""
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">{idx + 1}</td>
            <td class="name-cell">{escape_html(tname)}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #9CA3AF;">{escape_html(phone)}</td>
            <td><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(t.get("last_backup_shamsi", "-"))}</span></td>
            <td style="color: #60A5FA; font-weight: bold;"><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(t.get("file_size_mb", 0))} MB</span></td>
            <td>
                <div class="actions-group">
                    <a href="/api/backup/download/{quote(phone)}" class="btn-action btn-download" title="دریافت فایل SQLite دیتابیس مربی">📥 دانلود دیتابیس</a>
                    <button type="button" class="btn-action" style="background: #10B981; color: #FFF;" onclick="quickFillRecharge('{escape_js(phone)}', '{escape_js(tname)}')" title="شارژ سریع بسته پیامک برای این مربی">⚡ شارژ پیامک</button>
                    <form action="/api/backup/delete/{quote(phone)}" method="POST" style="display: inline;" onsubmit="return confirm('آیا از حذف دیتابیس مربی \\'{escape_js(tname or phone)}\\' از سرور اطمینان دارید؟');">
                        <button type="submit" class="btn-action btn-delete" title="حذف این نسخه پشتیبان از سرور">🗑️</button>
                    </form>
                </div>
            </td>
        </tr>""")
    trainer_rows_html = "".join(trainer_rows)

    media_rows = []
    for idx, m in enumerate(media_list):
        fn = m.get("filename", "")
        is_vid = m.get("type") == "video"
        type_badge = '<span class="badge-type badge-video">🎬 ویدیو</span>' if is_vid else '<span class="badge-type badge-image">🖼️ تصویر</span>'
        title_fa = resolve_exercise_title(fn)
        play_btn = (
            f'<a href="/video/{quote(fn)}" target="_blank" class="btn-action btn-play">▶️ پخش ویدیو</a>'
            if is_vid
            else f'<a href="/image/{quote(fn)}" target="_blank" class="btn-action btn-play">🔍 نمایش تصویر</a>'
        )
        media_rows.append(f"""
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">{idx + 1}</td>
            <td>{type_badge}</td>
            <td class="name-cell" style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{escape_html(title_fa)}"><span dir="auto" style="unicode-bidi: isolate;">{escape_html(title_fa)}</span></td>
            <td class="filename-cell" style="direction: ltr; text-align: right; font-family: var(--font-latin); font-size: 11.5px; color: #9CA3AF; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(fn)}</span></td>
            <td style="color: #A78BFA; font-weight: bold;"><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(m.get("file_size_mb", 0))} MB</span></td>
            <td><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(m.get("upload_shamsi", "-"))}</span></td>
            <td>
                <div class="actions-group">
                    {play_btn}
                    <button type="button" class="btn-action btn-copy" onclick="copyMediaLink('{escape_js(m.get('url', ''))}')">📋 کپی لینک</button>
                    <form action="/api/media/delete" method="POST" style="display: inline;" onsubmit="return confirm('آیا از حذف کامل فایل رسانه \\'{escape_js(fn)}\\' از سرور اطمینان دارید؟');">
                        <input type="hidden" name="filename" value="{escape_html(fn)}">
                        <input type="hidden" name="type" value="{escape_html(m.get('type', 'video'))}">
                        <button type="submit" class="btn-action btn-delete">🗑️</button>
                    </form>
                </div>
            </td>
        </tr>""")
    media_rows_html = "".join(media_rows)

    sms_rows = []
    for idx, s in enumerate(sms_list):
        rem = int(s.get("remaining", 0) or 0)
        total_cred = int(s.get("total_credited", 0) or 0)
        used = int(s.get("total_used", 0) or 0)
        is_zero = rem == 0 and total_cred == 0
        if is_zero:
            status_badge = '<span class="badge-type" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444;">غیرفعال / شارژ نشده</span>'
        elif rem <= 10:
            status_badge = '<span class="badge-type" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B;">رو به اتمام ⚠️</span>'
        else:
            status_badge = '<span class="badge-type" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;">فعال و پر اعتبار ✅</span>'
        sms_rows.append(f"""
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">{idx + 1}</td>
            <td class="name-cell">{escape_html(s.get("trainer_name", "مربی"))}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #9CA3AF;">{escape_html(s.get("phone", ""))}</td>
            <td style="color: {'#10B981' if rem > 0 else '#EF4444'}; font-weight: bold; font-size: 15px;">{to_fa_num(rem)} <span style="font-size: 11px; font-weight: normal; color: #A1A1AA;">پیامک</span></td>
            <td style="color: #60A5FA;">{to_fa_num(total_cred)}</td>
            <td style="color: #F87171;">{to_fa_num(used)}</td>
            <td style="font-size: 12px; color: #A1A1AA;"><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(s.get("last_recharge_shamsi", "-"))}</span></td>
            <td>{status_badge}</td>
            <td>
                <div class="actions-group">
                    <button type="button" class="btn-action" style="background: #10B981; color: #FFF;" onclick="quickFillRecharge('{escape_js(s.get('phone', ''))}', '{escape_js(s.get('trainer_name', ''))}')">➕ شارژ مجدد</button>
                </div>
            </td>
        </tr>""")
    sms_rows_html = "".join(sms_rows)

    log_rows = []
    for idx, l in enumerate(sms_logs[:50]):
        lt = l.get("type", "custom")
        if lt == "registration":
            tbadge = '<span class="badge-type" style="background: #1E3A8A; color: #93C5FD; border: 1px solid #2563EB;">ثبت‌نام شاگرد</span>'
        elif lt == "expiration_reminder":
            tbadge = '<span class="badge-type" style="background: #78350F; color: #FCD34D; border: 1px solid #D97706;">یادآوری تمدید</span>'
        elif lt == "plan_assigned":
            tbadge = '<span class="badge-type" style="background: #064E3B; color: #6EE7B7; border: 1px solid #059669;">برنامه تمرینی</span>'
        else:
            tbadge = '<span class="badge-type" style="background: #374151; color: #D1D5DB;">عمومی</span>'
        log_rows.append(f"""
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">{idx + 1}</td>
            <td class="name-cell">{escape_html(l.get("trainer_name", "مربی"))}</td>
            <td>{tbadge}</td>
            <td class="name-cell" style="font-weight: normal; color: #E4E4E7;">{escape_html(l.get("member_name", "-"))}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #60A5FA;">{escape_html(l.get("recipient", ""))}</td>
            <td style="font-size: 12px; color: #A1A1AA;"><span dir="ltr" style="unicode-bidi: isolate;">{escape_html(l.get("date_shamsi", "-"))}</span></td>
            <td style="font-size: 11px; color: #10B981;">{escape_html(l.get("detail", "موفق"))}</td>
        </tr>""")
    sms_logs_html = "".join(log_rows)

    media_last_date = media_list[0].get("upload_shamsi", "-") if media_list else "هنوز رسانه‌ای آپلود نشده"

    backups_body = f"""
                <div class="table-responsive">
                    <table id="trainersTable">
                        <thead><tr><th>ردیف</th><th>نام مربی</th><th>شماره تماس (شناسه)</th><th>تاریخ آخرین پشتیبان‌گیری</th><th>حجم دیتابیس</th><th>عملیات</th></tr></thead>
                        <tbody>{trainer_rows_html}</tbody>
                    </table>
                </div>""" if trainers else """
                <div class="empty-state">
                    <p style="font-size: 16px; margin-bottom: 6px;">هنوز هیچ نسخه پشتیبانی در سرور ابری ثبت نشده است.</p>
                </div>"""

    media_body = f"""
                <div class="table-responsive">
                    <table id="mediaTable">
                        <thead><tr><th>ردیف</th><th>نوع رسانه</th><th>نام حرکت / عنوان</th><th>نام فایل</th><th>حجم</th><th>تاریخ آپلود</th><th>عملیات</th></tr></thead>
                        <tbody>{media_rows_html}</tbody>
                    </table>
                </div>""" if media_list else """
                <div class="empty-state">
                    <p style="font-size: 16px; margin-bottom: 6px;">هنوز هیچ ویدیو یا تصویری در باکت آروان آپلود نشده است.</p>
                </div>"""

    sms_body = f"""
                <div class="table-responsive">
                    <table id="smsTable">
                        <thead><tr><th>ردیف</th><th>نام مربی</th><th>شماره تماس</th><th>اعتبار باقیمانده</th><th>کل شارژشده</th><th>تعداد مصرفی</th><th>آخرین تاریخ شارژ</th><th>وضعیت</th><th>عملیات</th></tr></thead>
                        <tbody>{sms_rows_html}</tbody>
                    </table>
                </div>""" if sms_list else """
                <div class="empty-state"><p style="font-size: 16px;">هنوز هیچ مربی در سامانه پیامکی ثبت نشده است.</p></div>"""

    logs_body = f"""
                <div class="table-responsive">
                    <table>
                        <thead><tr><th>ردیف</th><th>مربی فرستنده</th><th>نوع پیامک</th><th>نام شاگرد</th><th>شماره دریافت‌کننده</th><th>تاریخ و ساعت</th><th>وضعیت ارسال</th></tr></thead>
                        <tbody>{sms_logs_html}</tbody>
                    </table>
                </div>""" if sms_logs else """
                <div class="empty-state"><p style="font-size: 15px;">هنوز هیچ پیامی ارسال نشده است.</p></div>"""

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مدیریت ابری و استودیوی رسانه - سامانه ورزشی نِمُو</title>
    <style>
        {SHARED_FONT_CSS}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: #0F0F0F; color: #F3F4F6; font-family: var(--font-body); min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }}
        header {{ background-color: #18181B; border-bottom: 1px solid #27272A; padding: 14px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
        .brand {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
        .brand h1 {{ font-family: var(--font-heading); font-size: 17px; font-weight: 800; color: #FFFFFF; }}
        .badge-live {{ background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: bold; font-family: var(--font-heading); }}
        .btn-logout {{ background-color: #27272A; color: #EF4444; border: 1px solid #3F3F46; padding: 8px 16px; min-height: 40px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; font-family: var(--font-heading); display: inline-flex; align-items: center; justify-content: center; transition: background 0.2s; white-space: nowrap; }}
        .btn-logout:hover {{ background-color: #DC2626; color: #FFFFFF; }}
        .container {{ max-width: 1240px; width: 100%; margin: 0 auto; padding: 20px 16px; flex: 1; }}
        .tabs-nav {{ display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 2px solid #27272A; padding-bottom: 12px; overflow-x: auto; white-space: nowrap; }}
        .tab-btn {{ background-color: #18181B; color: #A1A1AA; border: 1px solid #27272A; padding: 10px 18px; min-height: 44px; border-radius: 8px; cursor: pointer; font-size: 13.5px; font-weight: bold; font-family: var(--font-heading); transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; flex-shrink: 0; }}
        .tab-btn:hover {{ background-color: #27272A; color: #FFFFFF; }}
        .tab-btn.active {{ background-color: #8B0000; color: #FFFFFF; border-color: #8B0000; box-shadow: 0 4px 12px rgba(139, 0, 0, 0.35); }}
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px; display: flex; align-items: center; gap: 14px; }}
        .stat-icon {{ width: 48px; height: 48px; flex-shrink: 0; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }}
        .icon-red {{ background-color: rgba(139, 0, 0, 0.2); color: #EF4444; border: 1px solid #8B0000; }}
        .icon-blue {{ background-color: rgba(37, 99, 235, 0.2); color: #60A5FA; border: 1px solid #2563EB; }}
        .icon-green {{ background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #10B981; }}
        .icon-purple {{ background-color: rgba(139, 92, 246, 0.2); color: #A78BFA; border: 1px solid #8B5CF6; }}
        .stat-info h3 {{ font-family: var(--font-heading); font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 2px; }}
        .stat-info p {{ font-size: 12px; color: #A1A1AA; }}
        .table-card {{ background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; overflow: hidden; }}
        .table-header {{ padding: 14px 18px; border-bottom: 1px solid #27272A; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
        .table-header h2 {{ font-family: var(--font-heading); font-size: 15px; font-weight: bold; color: #FFFFFF; }}
        .search-input {{ background-color: #27272A; border: 1px solid #3F3F46; color: #FFFFFF; padding: 8px 14px; min-height: 38px; border-radius: 8px; font-size: 13px; font-family: var(--font-body); width: 260px; max-width: 100%; outline: none; }}
        .search-input:focus {{ border-color: #8B0000; }}
        .table-responsive {{ width: 100%; overflow-x: auto; }}
        table {{ width: 100%; min-width: 620px; border-collapse: collapse; text-align: right; font-size: 13px; }}
        th {{ background-color: #202024; color: #A1A1AA; padding: 12px 16px; font-weight: bold; border-bottom: 1px solid #27272A; white-space: nowrap; font-family: var(--font-heading); }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #27272A; color: #E4E4E7; vertical-align: middle; font-family: var(--font-body); }}
        .name-cell {{ font-family: 'B Koodak', Cambria, Georgia, serif !important; font-weight: bold; color: #FFFFFF; }}
        tr:hover td {{ background-color: #202024; }}
        .badge-type {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; font-family: var(--font-heading); }}
        .badge-video {{ background-color: #1E1B4B; color: #A5B4FC; border: 1px solid #4338CA; }}
        .badge-image {{ background-color: #064E3B; color: #6EE7B7; border: 1px solid #059669; }}
        .actions-group {{ display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }}
        .btn-action {{ white-space: nowrap; flex-shrink: 0; min-height: 36px; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 12px; font-family: var(--font-heading); display: inline-flex; align-items: center; gap: 4px; cursor: pointer; border: none; }}
        .btn-download {{ background-color: #2563EB; color: #FFFFFF; }}
        .btn-play {{ background-color: #059669; color: #FFFFFF; min-width: 100px; justify-content: center; }}
        .btn-copy {{ background-color: #6366F1; color: #FFFFFF; min-width: 80px; justify-content: center; }}
        .btn-delete {{ background-color: #DC2626 !important; color: #FFFFFF !important; min-width: 48px; justify-content: center; }}
        .empty-state {{ padding: 45px 20px; text-align: center; color: #71717A; }}
        footer {{ text-align: center; padding: 20px 16px; font-size: 12px; color: #71717A; border-top: 1px solid #27272A; }}
        .toast {{ position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background-color: #10B981; color: #FFFFFF; padding: 12px 22px; border-radius: 8px; font-size: 13.5px; font-weight: bold; z-index: 9999; display: none; }}
        .toast.show {{ display: block; }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <h1>☁️ سرور ابری سامانه ورزشی نِمُو (Nemov Cloud)</h1>
            <span class="badge-live">سرور ایران آنلاین 🇮🇷</span>
        </div>
        <a href="/logout" class="btn-logout">خروج از پنل</a>
    </header>
    <div class="container">
        <div class="tabs-nav">
            <button id="btnTabBackups" class="tab-btn {'active' if default_tab == 'backups' else ''}" onclick="switchTab('backups')">💾 پایگاه‌داده‌ها و بکاپ‌ها ({len(trainers)})</button>
            <button id="btnTabMedia" class="tab-btn {'active' if default_tab == 'media' else ''}" onclick="switchTab('media')">🎬 بانک رسانه‌ها و ویدیوهای حرکات ({len(media_list)})</button>
            <button id="btnTabMessages" class="tab-btn {'active' if default_tab == 'messages' else ''}" onclick="switchTab('messages')">📱 مدیریت بسته‌های پیامکی ({len(sms_list)})</button>
        </div>
        <div id="panelBackups" class="tab-panel {'active' if default_tab == 'backups' else ''}">
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-icon icon-red">👥</div><div class="stat-info"><h3>{len(trainers)}</h3><p>مربیان دارای نسخه پشتیبان</p></div></div>
                <div class="stat-card"><div class="stat-icon icon-blue">💾</div><div class="stat-info"><h3>{total_size_mb} MB</h3><p>مجموع حجم دیتابیس‌ها در آروان</p></div></div>
                <div class="stat-card"><div class="stat-icon icon-green">⏱️</div><div class="stat-info"><h3 style="font-size: 16px;">{escape_html(last_activity)}</h3><p>آخرین فعالیت پشتیبان‌گیری</p></div></div>
            </div>
            <div class="table-card">
                <div class="table-header">
                    <h2>📋 لیست پایگاه‌داده‌های مربیان (ArvanCloud S3)</h2>
                    <input type="text" id="searchBackupsInput" class="search-input" placeholder="🔍 جستجو بر اساس نام یا شماره..." onkeyup="filterTable('trainersTable', 'searchBackupsInput', [1, 2])">
                </div>
                {backups_body}
            </div>
        </div>
        <div id="panelMedia" class="tab-panel {'active' if default_tab == 'media' else ''}">
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-icon icon-purple">🎬</div><div class="stat-info"><h3>{len(media_list)}</h3><p>تعداد کل ویدیوها و تصاویر</p></div></div>
                <div class="stat-card"><div class="stat-icon icon-blue">📦</div><div class="stat-info"><h3>{total_media_size_mb} MB</h3><p>مجموع حجم رسانه‌ها در آروان</p></div></div>
                <div class="stat-card"><div class="stat-icon icon-green">⏱️</div><div class="stat-info"><h3 style="font-size: 15px;">{escape_html(media_last_date)}</h3><p>آخرین آپلود رسانه حرکات</p></div></div>
            </div>
            <div class="table-card">
                <div class="table-header">
                    <h2>🎬 بانک ویدیوها و تصاویر آموزشی حرکات ورزشی</h2>
                    <input type="text" id="searchMediaInput" class="search-input" placeholder="🔍 جستجو بر اساس نام حرکت یا فایل..." onkeyup="filterTable('mediaTable', 'searchMediaInput', [2, 3])">
                </div>
                {media_body}
            </div>
        </div>
        <div id="panelMessages" class="tab-panel {'active' if default_tab == 'messages' else ''}">
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-icon icon-green">👥</div><div class="stat-info"><h3>{len(sms_list)} نفر</h3><p>مربیان فعال در سامانه پیامک</p></div></div>
                <div class="stat-card"><div class="stat-icon icon-blue">📩</div><div class="stat-info"><h3>{to_fa_num(total_sms_remaining)} عدد</h3><p>مجموع اعتبار باقیمانده پیامک‌ها</p></div></div>
                <div class="stat-card"><div class="stat-icon icon-purple">📤</div><div class="stat-info"><h3>{to_fa_num(total_sms_sent)} پیامک</h3><p>کل پیامک‌های ارسال‌شده به شاگردان</p></div></div>
            </div>
            <div class="table-card" style="margin-bottom: 24px; padding: 20px;">
                <h2 style="font-family: var(--font-heading); font-size: 16px; margin-bottom: 8px;">⚡ شارژ آنلاین و فعال‌سازی بسته پیامک برای مربی</h2>
                <p style="font-size: 13px; color: #A1A1AA; margin-bottom: 18px;">پس از واریز کارت‌به‌کارت مربی، شماره موبایل و تعداد پیامک مورد نظر را تعیین و دکمه شارژ را بزنید.</p>
                <form action="/api/admin/sms/recharge" method="POST" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end;">
                    <div style="flex: 1 1 160px; min-width: 140px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB;">شماره موبایل مربی (شناسه)</label>
                        <input type="text" id="rechargePhone" name="phone" required placeholder="09123456789" style="width: 100%; height: 44px; padding: 0 12px; background: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; direction: ltr;">
                    </div>
                    <div style="flex: 1 1 150px; min-width: 140px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB;">نام مربی</label>
                        <input type="text" id="rechargeName" name="trainer_name" placeholder="نام مربی (اختیاری)" style="width: 100%; height: 44px; padding: 0 12px; background: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF;">
                    </div>
                    <div style="flex: 0.8 1 120px; min-width: 110px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB;">تعداد پیامک بسته</label>
                        <input type="number" id="rechargeAmount" name="amount" min="1" value="100" required style="width: 100%; height: 44px; padding: 0 10px; background: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; text-align: center; direction: ltr;">
                    </div>
                    <div style="flex: 1.5 1 260px; min-width: 220px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB;">بسته‌های سریع</label>
                        <div style="display: flex; gap: 6px; width: 100%;">
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; justify-content: center;" onclick="setAmount(100)">۱۰۰ تایی</button>
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; justify-content: center;" onclick="setAmount(250)">۲۵۰ تایی</button>
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; justify-content: center;" onclick="setAmount(500)">۵۰۰ تایی</button>
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; justify-content: center;" onclick="setAmount(1000)">۱۰۰۰ تایی</button>
                        </div>
                    </div>
                    <div style="flex: 1 1 160px; min-width: 150px;">
                        <button type="submit" class="btn-action" style="background: #10B981; color: #FFFFFF; height: 44px; width: 100%; justify-content: center;">🚀 ثبت و شارژ حساب مربی</button>
                    </div>
                </form>
            </div>
            <div class="table-card" style="margin-bottom: 24px;">
                <div class="table-header">
                    <h2>📋 لیست مربیان و وضعیت اعتبار پیامک‌ها</h2>
                    <input type="text" id="searchSmsInput" class="search-input" placeholder="🔍 جستجو بر اساس نام یا شماره مربی..." onkeyup="filterTable('smsTable', 'searchSmsInput', [1, 2])">
                </div>
                {sms_body}
            </div>
            <div class="table-card">
                <div class="table-header"><h2>📤 گزارش آخرین پیامک‌های ارسالی مربیان به شاگردان</h2></div>
                {logs_body}
            </div>
        </div>
    </div>
    <div id="toast" class="toast"></div>
    <footer>توسعه داده شده برای سامانه هوشمند مدیریت ورزشی نِمُو • میزبانی ابری ایران (Runflare + ArvanCloud) © 2026</footer>
    <script>
        function switchTab(tab) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            if (tab === 'media') {{
                document.getElementById('btnTabMedia').classList.add('active');
                document.getElementById('panelMedia').classList.add('active');
            }} else if (tab === 'messages') {{
                document.getElementById('btnTabMessages').classList.add('active');
                document.getElementById('panelMessages').classList.add('active');
            }} else {{
                document.getElementById('btnTabBackups').classList.add('active');
                document.getElementById('panelBackups').classList.add('active');
            }}
            if (window.history && window.history.replaceState) {{
                history.replaceState(null, '', '?tab=' + tab);
            }}
        }}
        function setAmount(num) {{ document.getElementById('rechargeAmount').value = num; }}
        function quickFillRecharge(phone, name) {{
            document.getElementById('rechargePhone').value = phone;
            document.getElementById('rechargeName').value = name;
            switchTab('messages');
            document.getElementById('rechargeAmount').focus();
        }}
        function copyMediaLink(url) {{
            if (navigator.clipboard && navigator.clipboard.writeText) {{ navigator.clipboard.writeText(url).then(showToast); }}
            else {{ var ta = document.createElement('textarea'); ta.value = url; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); showToast(); }}
        }}
        function showToast() {{
            var t = document.getElementById('toast');
            t.textContent = '✅ لینک مستقیم رسانه با موفقیت در کلیپ‌بورد کپی شد!';
            t.className = 'toast show';
            setTimeout(function() {{ t.className = 'toast'; }}, 3000);
        }}
        function filterTable(tableId, inputId, colIndices) {{
            var input = document.getElementById(inputId);
            var filter = input.value.toLowerCase();
            var table = document.getElementById(tableId);
            if (!table) return;
            var tr = table.getElementsByTagName("tr");
            for (var i = 1; i < tr.length; i++) {{
                var matched = false;
                for (var j = 0; j < colIndices.length; j++) {{
                    var td = tr[i].getElementsByTagName("td")[colIndices[j]];
                    if (td) {{
                        var text = td.textContent || td.innerText;
                        if (text.toLowerCase().indexOf(filter) > -1) {{ matched = true; break; }}
                    }}
                }}
                tr[i].style.display = matched ? "" : "none";
            }}
        }}
    </script>
</body>
</html>"""


def render_video_player(title: str, stream_url: str, filename: str) -> str:
    safe_title = escape_html(title or "حرکت تمرینی نِمُو")
    safe_url = escape_html(stream_url)
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} | راهنمای اجرای حرکت</title>
    <style>
        {SHARED_FONT_CSS}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: #0b0c0e; color: #ffffff; font-family: var(--font-body); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }}
        .player-container {{ width: 100%; max-width: 780px; background: #14161b; border-radius: 18px; border: 1px solid #232730; box-shadow: 0 20px 50px rgba(0,0,0,0.85); overflow: hidden; display: flex; flex-direction: column; }}
        .player-header {{ padding: 14px 20px; background: linear-gradient(135deg, #1d212b, #121419); border-bottom: 1px solid #282d38; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
        .header-title-box h1 {{ font-family: var(--font-heading); font-size: 16.5px; font-weight: 800; color: #ffffff; margin-bottom: 2px; }}
        .header-title-box p {{ font-size: 11.5px; color: #9ba3af; }}
        .gym-badge {{ background: linear-gradient(135deg, #A91D22, #7a1418); color: #ffffff; font-family: var(--font-heading); font-size: 11px; font-weight: bold; padding: 5px 12px; border-radius: 20px; }}
        .video-box {{ position: relative; width: 100%; background-color: #000000; display: flex; align-items: center; justify-content: center; min-height: 320px; }}
        video {{ width: 100%; height: auto; max-height: 75vh; min-height: 280px; display: block; outline: none; background-color: #000000; object-fit: contain; }}
        .player-footer {{ padding: 12px 20px; background: #101217; border-top: 1px solid #232730; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; font-size: 12px; color: #8b92a0; }}
        .player-footer span {{ color: #A91D22; font-weight: bold; }}
        .download-btn {{ display: inline-flex; align-items: center; gap: 6px; background: #1e232d; color: #60a5fa; border: 1px solid #2f3644; padding: 5px 12px; border-radius: 8px; text-decoration: none; font-size: 11.5px; }}
    </style>
</head>
<body>
    <div class="player-container">
        <div class="player-header">
            <div class="header-title-box"><h1>🎬 {safe_title}</h1><p>پخش اختصاصی حرکت بدنسازی (بدون فیلترشکن)</p></div>
            <div class="gym-badge">سامانه ورزشی نِمُو</div>
        </div>
        <div class="video-box">
            <video id="gymVideo" playsinline preload="auto" loop controls autoplay muted>
                <source src="{safe_url}" type="video/mp4">
            </video>
        </div>
        <div class="player-footer">
            <div>طراحی شده برای ورزشکاران • <span>سامانه ورزشی نِمُو</span></div>
            <a class="download-btn" href="{safe_url}" download="{safe_title}.mp4">دانلود مستقیم ویدیو 📥</a>
        </div>
    </div>
</body>
</html>"""


def render_image_viewer(title: str, image_url: str) -> str:
    safe_title = escape_html(title)
    safe_url = escape_html(image_url)
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} | سامانه ورزشی نِمُو</title>
    <style>
        {SHARED_FONT_CSS}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background-color: #0d0d0d; color: #ffffff; font-family: var(--font-body); display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 16px; }}
        .viewer-container {{ width: 100%; max-width: 680px; background: #181818; border: 1px solid #282828; border-radius: 14px; overflow: hidden; display: flex; flex-direction: column; }}
        .viewer-header {{ padding: 14px 18px; background: #141414; border-bottom: 1px solid #242424; display: flex; align-items: center; justify-content: space-between; }}
        .image-box {{ background: #0F0F0F; display: flex; align-items: center; justify-content: center; padding: 10px; }}
        .image-box img {{ max-width: 100%; max-height: 72vh; object-fit: contain; border-radius: 8px; }}
        .viewer-footer {{ padding: 12px 18px; background: #141414; border-top: 1px solid #242424; display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #777; }}
        .gym-badge {{ background: #8B0000; color: #fff; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="viewer-container">
        <div class="viewer-header"><div><h1 style="font-size:16px;">🖼️ {safe_title}</h1></div><div class="gym-badge">سامانه ورزشی نِمُو</div></div>
        <div class="image-box"><img src="{safe_url}" alt="{safe_title}" loading="lazy" /></div>
        <div class="viewer-footer"><div>برنامه تمرینی اختصاصی • سامانه ورزشی نِمُو</div><a href="{safe_url}" style="color:#60a5fa;text-decoration:none;" download>دریافت تصویر 📥</a></div>
    </div>
</body>
</html>"""


def render_not_found_page(title: str = "رسانه یافت نشد", msg: str = "فایل درخواستی در مخزن سرور موجود نیست.") -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{escape_html(title)}</title>
<style>{SHARED_FONT_CSS} body {{ background:#0F0F0F; color:#fff; font-family:var(--font-body); display:flex; align-items:center; justify-content:center; min-height:100vh; text-align:center; }} .box {{ background:#1A1A1A; border:1px solid #333; padding:30px; border-radius:12px; max-width:380px; }} h2 {{ color:#DC2626; margin-bottom:10px; }}</style>
</head><body><div class="box"><h2>⚠️ {escape_html(title)}</h2><p>{escape_html(msg)}</p></div></body></html>"""
