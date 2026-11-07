# فاز ۳: پروتوتایپ کلیک‌پذیر، قرارداد APIها و برنامه هاستینگ
## ددلاین رسمی: ۲۱ تا ۲۴ آبان ۱۴۰۵ | درس تحلیل و طراحی نرم‌افزار (SSAD)

---

## ۱. پروتوتایپ کلیک‌پذیر (Clickable Prototype)
* **پلتفرم طراحی**: Figma
* **لینک دسترسی تعاملی**: `[لینک پروتوتایپ فیگما در این بخش درج می‌شود]`
* **صفحات پوشش داده‌شده در پروتوتایپ**:
  1. صفحه ورود به سیستم (Login Screen) با حالت‌های موفقیت و پیام خطای اطلاعات نادرست.
  2. داشبورد مدیریتی (Admin Dashboard) با آمارهای سریع اعضا و شهریه‌های در شرف انقضا.
  3. فرم ثبت‌نام و ویرایش عضو (Member Form) با اعتبارسنجی فیلدها.
  4. بانک حرکات ورزشی (Exercise Library) با فیلتر بصری آناتومی عضلات و پیش‌نمایش ویدیو.
  5. ماژول تدوین برنامه تمرینی (Workout Plan Builder) و صدور خروجی.

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
