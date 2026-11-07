# فاز ۲: دیاگرام‌های تحلیل و طراحی مهندسی سیستم (UML & System Architecture)
## ددلاین رسمی: ۱۶ تا ۲۰ آبان ۱۴۰۵ | درس تحلیل و طراحی نرم‌افزار (SSAD)

در این بخش، چهار دیدگاه طراحی مهندسی الزامی طبق راهنمای درس مهندسی نرم‌افزار به همراه کدهای استاندارد رسم دیاگرام (Mermaid) قرار داده شده‌اند.

---

## ۱. دیاگرام موارد کاربرد (UML Use Case Diagram)
این دیاگرام اکترهای اصلی سامانه نِمُو (مدیر باشگاه، مربی و سیستم ابری) و تعامل آن‌ها با قابلیت‌های هسته MVP را نشان می‌دهد.

```mermaid
flowchart LR
    subgraph Actors [اکترهای سیستم]
        Admin((مدیر باشگاه))
        Coach((مربی ورزشی))
        Cloud((سرویس ابری نِمُو))
    end

    subgraph Nemov_MVP [مرز سامانه نِمُو - MVP Boundary]
        UC1([ورود و احراز هویت امن])
        UC2([ثبت و مدیریت پرونده اعضا])
        UC3([ثبت و تخصیص دوره شهریه])
        UC4([جستجو و فیلتر بانک حرکات ورزشی])
        UC5([تدوین و صدور برنامه تمرینی])
        UC6([مشاهده وضعیت و قلق‌های ضدآسیب])
        UC7([پشتیبان‌گیری رمزنگاری‌شده ابری])
        UC8([همگام‌سازی ویدیوها و فایل‌ها])
    end

    Admin --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC7

    Coach --> UC1
    Coach --> UC4
    Coach --> UC5
    Coach --> UC6

    Cloud -.-> UC7
    Cloud -.-> UC8
```

---

## ۲. دیاگرام فعالیت فرآیند اصلی (UML Activity Diagram)
فرآیند کلیدی انتخاب‌شده: **ثبت‌نام عضو جدید، تخصیص شهریه و صدور برنامه تمرینی اولیه** (همراه با مسیرهای شکست اعتبارسنجی و موفقیت).

```mermaid
flowchart TD
    Start([شروع فرآیند]) --> EnterData[ورود اطلاعات عضو و کد ملی]
    EnterData --> CheckNationalCode{کد ملی تکراری است؟}
    
    CheckNationalCode -- بله --> ShowErrorDuplicate[نمایش خطای کد ملی تکراری]
    ShowErrorDuplicate --> EnterData

    CheckNationalCode -- خیر --> SaveMember[ذخیره مشخصات در دیتابیس پایدار]
    SaveMember --> PromptTuition[درخواست ثبت دوره شهریه]
    
    PromptTuition --> CheckTuitionPayment{مبلغ و تاریخ معتبر است؟}
    CheckTuitionPayment -- خیر --> FixTuition[اصلاح مقادیر شهریه]
    FixTuition --> PromptTuition
    
    CheckTuitionPayment -- بله --> ActivateSubscription[ثبت شهریه و فعال‌سازی اشتراک عضو]
    ActivateSubscription --> SelectExercises[انتخاب حرکات از بانک ورزشی با فیلتر عضلانی]
    SelectExercises --> ValidateWorkout{حداقل یک ست/تکرار مشخص شده؟}
    
    ValidateWorkout -- خیر --> WarningEmpty[اخطار: برنامه نمی‌تواند خالی باشد]
    WarningEmpty --> SelectExercises
    
    ValidateWorkout -- بله --> SavePlan[تخصیص و ذخیره نهایی برنامه تمرینی]
    SavePlan --> CloudSync[ارسال متادیتا جهت همگام‌سازی ابری]
    CloudSync --> End([پایان موفقیت‌آمیز فرآیند])
```

---

## ۳. دیاگرام معماری سیستم (System Architecture Diagram)
نمایش لایه‌های چهارگانه نرم‌افزار، نحوه تبادل داده و پلتفرم‌های میزبانی:

```mermaid
graph TD
    subgraph ClientLayer [لایه کاربری و ارائه - Client UI]
        DesktopApp[نرم‌افزار دسکتاپ نِمُو - PyQt6 / Python 3.12]
        WebPortal[پورتال وب و لندینگ پیج ریسپانسیو - HTML5/CSS/JS]
    end

    subgraph ServiceLayer [لایه منطق تجاری و اعتبارسنجی - Business Logic]
        AuthService[سرویس احراز هویت و توکن‌های نشست]
        MemberService[سرویس اعتبارسنجی و مدیریت اعضا]
        WorkoutService[سرویس طراحی و نسخه‌نویسی تمرین]
        SyncService[سرویس همگام‌سازی پس‌زمینه و بکاپ]
    end

    subgraph APILayer [لایه واسط برنامه‌نویسی - Cloud Edge API]
        CloudflareWorker[Cloudflare Workers API Gateway / REST Endpoints]
    end

    subgraph PersistenceLayer [لایه داده و ذخیره‌سازی ابری - Persistence & Storage]
        LocalDB[(پایگاه‌داده محلی SQLite - nemov.db)]
        CloudR2[(مخزن رسانه‌ای ابری Cloudflare R2 - ویدیوهای آموزشی)]
        CloudKV[(مخزن ابری Cloudflare KV - سشن‌ها و لاگ‌ها)]
    end

    DesktopApp --> ServiceLayer
    WebPortal --> APILayer
    ServiceLayer --> LocalDB
    ServiceLayer --> APILayer
    APILayer --> CloudR2
    APILayer --> CloudKV
```

---

## ۴. دیاگرام مدل داده و روابط موجودیت‌ها (ERD - Entity-Relationship Diagram)

```mermaid
erDiagram
    USERS ||--o{ MEMBERS : registers
    USERS ||--o{ WORKOUT_PLANS : authors
    MEMBERS ||--o{ TUITIONS : pays
    MEMBERS ||--o{ WORKOUT_PLANS : receives
    WORKOUT_PLANS ||--|{ WORKOUT_ITEMS : contains
    EXERCISES ||--o{ WORKOUT_ITEMS : references

    USERS {
        int id PK
        string username UK
        string password_hash
        string role "Admin / Trainer"
        string full_name
        datetime created_at
    }

    MEMBERS {
        int id PK
        string national_id UK
        string full_name
        string phone_number
        string medical_history
        datetime registered_at
        boolean is_active
    }

    TUITIONS {
        int id PK
        int member_id FK
        numeric amount
        date start_date
        date end_date
        string payment_status "Active / Expired"
    }

    EXERCISES {
        int id PK
        string name_fa
        string primary_muscle
        string equipment
        string contraindications
        string description "قلق اجرایی و منع آسیب"
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
        int rest_seconds
    }
```
