# فاز ۲: دیاگرام‌های تحلیل و طراحی مهندسی سیستم (UML & System Architecture)
## ددلاین رسمی: ۱۶ تا ۲۰ آبان ۱۴۰۵ | درس تحلیل و طراحی نرم‌افزار (SSAD)

در این بخش، چهار دیدگاه طراحی مهندسی الزامی طبق راهنمای درس مهندسی نرم‌افزار به همراه کدهای استاندارد رسم دیاگرام (Mermaid) قرار داده شده‌اند.

---

## ۱. دیاگرام موارد کاربرد (UML Use Case Diagram)
این دیاگرام اکترهای اصلی برنامه نِمُو (مدیر باشگاه، مربی و سرور ابری/لایسنس) و تعامل آن‌ها با قابلیت‌های هسته MVP را نشان می‌دهد.

```mermaid
flowchart LR
    subgraph Actors [اکترهای سیستم]
        Admin((مدیر باشگاه))
        Coach((مربی ورزشی))
        Cloud((سرور ابری و لایسنس نِمُو))
    end

    subgraph Nemov_App [مرز برنامه نِمُو - App Boundary]
        UC1([ورود امن با رمز عبور هش‌شده])
        UC2([ثبت و مدیریت پرونده شاگردان])
        UC3([ثبت و پیگیری دوره‌های شهریه])
        UC4([کاوش در بانک حرکات و قلق‌های ضدآسیب])
        UC5([طراحی و صدور PDF برنامه تمرینی])
        UC6([تعریف مربی و تعلیق دسترسی - بدون افشای رمز])
        UC7([ورود توکن لایسنس و اعتبارسنجی انقضا])
        UC8([پشتیبان‌گیری رمزنگاری‌شده ابری])
    end

    Admin --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC6
    Admin --> UC7
    Admin --> UC8

    Coach --> UC1
    Coach --> UC2
    Coach --> UC4
    Coach --> UC5

    Cloud -.-> UC7
    Cloud -.-> UC8
```

---

## ۲. دیاگرام فعالیت فرآیند اصلی (UML Activity Diagram)
فرآیند کلیدی انتخاب‌شده: **اعتبارسنجی لایسنس، احراز هویت، انتخاب شاگرد و تدوین و صدور PDF برنامه تمرینی** (همراه با مسیرهای شکست اعتبارسنجی و موفقیت).

```mermaid
flowchart TD
    Start([شروع کار با برنامه]) --> CheckLicense{آیا لایسنس فعال و معتبر است؟}
    
    CheckLicense -- خیر / منقضی --> LockScreen[قفل برنامه و نمایش پنجره فعال‌سازی]
    LockScreen --> EnterLicenseToken[دریافت و وارد کردن توکن لایسنس جدید]
    EnterLicenseToken --> ValidateToken{امضای کریپتوگرافیک توکن معتبر است؟}
    ValidateToken -- خیر --> ShowLicenseError[نمایش خطای لایسنس نامعتبر]
    ShowLicenseError --> EnterLicenseToken
    ValidateToken -- بله --> UnlockApp[فعال‌سازی و بازگشایی امکانات]
    
    CheckLicense -- بله --> LoginStep[ورود کاربر با نام‌کاربری و رمز عبور]
    UnlockApp --> LoginStep
    
    LoginStep --> CheckRole{احراز هویت و تعیین نقش}
    CheckRole -- مدیر --> AdminDashboard[داشبورد مدیریت: اعضا، شهریه، مربیان و مالی]
    CheckRole -- مربی --> CoachDashboard[داشبورد مربیگری: شاگردان، بانک حرکات و تمرینات]
    
    CoachDashboard --> SelectMember[انتخاب شاگرد و بررسی سوابق آسیب‌دیدگی]
    SelectMember --> AddExercises[انتخاب حرکات و اعمال قلق‌های ایمنی]
    AddExercises --> ExportPDF[تولید و چاپ فایل PDF برنامه تمرینی]
    ExportPDF --> End([پایان موفقیت‌آمیز فرآیند])
```

---

## ۳. دیاگرام معماری سیستم (System Architecture Diagram)
نمایش لایه‌های چهارگانه نرم‌افزار، نحوه تبادل داده، پلتفرم‌های میزبانی و سرویس لایسنس:

```mermaid
graph TD
    subgraph ClientLayer [لایه کاربری دسکتاپ - Desktop Client UI]
        AdminUI[پنل مدیریت باشگاه - PyQt6]
        CoachUI[پنل مربیگری و طراحی برنامه - PyQt6]
    end

    subgraph ServiceLayer [لایه منطق تجاری و اعتبارسنجی - Core Services]
        AuthService[سرویس احراز هویت و امنیت رمزها]
        LicenseManager[سرویس اعتبارسنجی قفل سخت‌افزاری HWID]
        MemberService[سرویس پرونده اعضا و شهریه‌ها]
        WorkoutService[سرویس تدوین برنامه و موتور صدور PDF]
    end

    subgraph PersistenceLayer [لایه داده محلی پایدار - Local Storage]
        LocalDB[(پایگاه‌داده محلی SQLite - nemov.db)]
    end

    subgraph CloudLayer [لایه ابری و سرور توسعه‌دهنده - Cloud & Vendor Edge]
        CloudAPI[Cloudflare Workers API Gateway]
        LicenseBot[ربات تلگرام / سرور صدور توکن لایسنس نِمُو]
        MediaStorage[(Cloudflare R2 Storage - ویدیوهای آموزشی)]
    end

    AdminUI --> ServiceLayer
    CoachUI --> ServiceLayer
    ServiceLayer --> LocalDB
    ServiceLayer --> CloudAPI
    LicenseManager -.-> LicenseBot
    CloudAPI --> MediaStorage
```

---

## ۴. دیاگرام مدل داده و روابط موجودیت‌ها (ERD - Entity-Relationship Diagram)
در این ساختار، فیلد `is_active` برای جدول مربیان لحاظ شده تا درصورت نیاز، تعلیق شود.

```mermaid
erDiagram
    USERS ||--o{ MEMBERS : manages
    USERS ||--o{ WORKOUT_PLANS : authors
    MEMBERS ||--o{ TUITIONS : has
    MEMBERS ||--o{ WORKOUT_PLANS : assigned_to
    WORKOUT_PLANS ||--|{ WORKOUT_ITEMS : contains
    EXERCISES ||--o{ WORKOUT_ITEMS : references

    USERS {
        int id PK
        string username UK
        string password_hash "هش یک‌طرفه امن"
        string role "admin / trainer"
        string full_name
        string phone
        boolean is_active "تعلیق همکاری در صورت نیاز"
    }

    MEMBERS {
        int id PK
        int assigned_trainer_id FK
        string full_name
        string phone
        string medical_history "آسیب‌دیدگی‌های پزشکی"
        datetime registered_at
    }

    TUITIONS {
        int id PK
        int member_id FK
        numeric amount
        date start_date
        date end_date
        string status "active / expired"
    }

    EXERCISES {
        int id PK
        string name_fa
        string primary_muscle
        string equipment
        string contraindications "منع آسیب‌دیدگی"
        string description "قلق اجرایی و ایمنی"
        string video_url
    }

    WORKOUT_PLANS {
        int id PK
        int member_id FK
        int trainer_id FK
        string title
        date created_at
    }

    WORKOUT_ITEMS {
        int id PK
        int plan_id FK
        int exercise_id FK
        int day_number
        int sets
        string reps
    }
```
