# فاز ۳: پروتوتایپ کلیک‌پذیر، قرارداد APIها و برنامه هاستینگ
## ددلاین رسمی: ۲۱ تا ۲۴ آبان ۱۴۰۵ | درس تحلیل و طراحی نرم‌افزار (SSAD)

---

## ۱. پروتوتایپ کلیک‌پذیر (Clickable Prototype)
* **پلتفرم طراحی**: Figma
* **لینک بوم طراحی فیگما (Figma Design Canvas)**: [مشاهده بوم طراحی پروژه نِمُو در فیگما](https://www.figma.com/design/bxozUbyh4zZVSQXlJFVxeF/Nemov---Interactive-Prototype-(SSAD-Phase-3))
* **لینک اجرای زنده و تعاملی پروتوتایپ (Interactive Presentation Mode)**: [اجرای آنلاین پروتوتایپ تعاملی](https://www.figma.com/proto/bxozUbyh4zZVSQXlJFVxeF/Nemov---Interactive-Prototype-(SSAD-Phase-3))
* **صفحات پوشش داده‌شده در پروتوتایپ (High-Fidelity Screens)**:
  1. **صفحه ورود به سیستم (Login Screen)**: ورود مربی با اعتبارسنجی ورودی‌ها و تم تاریک مدرن نِمُو.
  2. **داشبورد اصلی مربی و مدیریت (Admin Dashboard)**: کارت‌های KPI، آمار ورزشکاران، شهریه‌های منقضی و دسترسی سریع به ماژول‌ها.
  3. **بانک هوشمند حرکات ورزشی (Exercise Library - Dark Edition)**: فیلتر تصویری بدن بر اساس آناتومی عضلات و جدول حرکات با پیش‌نمایش رسانه.
  4. **ماژول تدوین برنامه تمرینی (Workout Plan Builder)**: انتخاب هوشمند حرکات، تنظیم ست‌ها، تکرارها و سیستم‌های تمرینی.
  5. **ماژول تخصصی برنامه تغذیه (Nutrition Planner)**: محاسبه کالری، توزیع درشت‌مغذی‌ها (پروتئین، کربوهیدرات، چربی) و تنظیم وعده‌ها.
  6. **پایگاه داده جامع مواد غذایی (Food & Macro Database)**: جستجو و انتخاب اقلام غذایی به همراه جدول کالری و ارزش غذایی.

---

## ۲. قرارداد APIها (API Contract Table)

| متد (Method) | مسیر (Path) | ورودی‌ها (Input) | پاسخ موفق (200/201 OK) | خطاهای احتمالی (Errors) |
| :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/auth/login` | `{ username, password }` | `{ token, role, user_id }` | `401: Invalid credentials`, `400: Missing fields` |
| **GET** | `/api/members` | `Header: Bearer Token`, Query: `search, status` | `[{ id, name, national_id, phone, status }]` | `401: Unauthorized` |
| **POST** | `/api/members` | `{ name, national_id, phone, medical }` | `{ id: 101, message: "Member created" }` | `409: National ID already exists`, `422: Invalid phone` |
| **POST** | `/api/tuitions` | `{ member_id, amount, start_date, days }` | `{ tuition_id: 55, end_date: "1405/09/20" }` | `404: Member not found`, `400: Negative amount` |
| **GET** | `/api/exercises` | Query: `muscle, search` | `[{ id, name_fa, muscle, video_url, description }]` | `500: Database error` |
| **POST** | `/api/workout-plans` | `{ member_id, title, days: [...] }` | `{ plan_id: 12, created_at: "..." }` | `400: Empty exercise list`, `403: Forbidden` |
| **POST** | `/api/sync/backup` | `Multipart/Encrypted Database Stream` | `{ sync_id: "...", timestamp: "..." }` | `401: Invalid API key`, `413: Payload too large` |

---

## ۳. توجیه معماری، پشته فنی و برآورد هزینه هاستینگ (Technology Rationale & Hosting)

* **لایه کلاینت**: Python 3.12 + PyQt6 (عملکرد روان، چندسکویی، عدم وابستگی به سخت‌افزارهای گران‌قیمت، رابط کاربری مدرن با تم تاریک).
* **لایه لندینگ پیج و معرفی**: HTML5, Modern CSS, Vanilla JS (بارگذاری فوق‌العاده سریع بدون سنگینی فریم‌ورک‌های اضافه).
* **لایه بک‌اند سرورلس (Serverless API)**: Cloudflare Workers (اجرا در بیش از ۳۰۰ دیتاسنتر اج جهانی با زمان پاسخ زیر ۳۰ میلی‌ثانیه، امنیت پیش‌فرض DDoS و SSL خودکار).
* **لایه ذخیره‌سازی ابری و استریم**: Cloudflare R2 Storage (سازگار با S3 API، بدون هزینه خروجی ترافیک Egress Bandwidth Fee، فوق‌العاده اقتصادی برای ویدیوهای حرکات ورزشی).
* **پایگاه داده محلی**: SQLite با حالت WAL (Write-Ahead Logging) که پایداری داده‌ها حتی در قطعی ناگهانی برق را تضمین می‌کند.
* **برآورد هزینه و محدودیت‌ها (Cost & Limits)**:
  - هزینه هاستینگ در فاز MVP: **۰ دلار (کاملاً رایگان در پلن Free کلودفلر)**.
  - محدودیت ترافیک کلودفلر: ۱۰۰,۰۰۰ درخواست در روز (که بیش از ۵۰ برابر نیاز فاز MVP یک باشگاه است).
  - دامنه ملی: `nemovapp.ir` با هزینه سالانه اندک ثبت دامنه ir.
