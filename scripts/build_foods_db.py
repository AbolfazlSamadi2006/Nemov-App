# -*- coding: utf-8 -*-
"""
Builder script to generate the comprehensive Iranian Sports & Nutrition Database
for Yalda Gym App (resources/data/foods_database.json).
"""
import json
import os
from pathlib import Path

foods = [
    # =========================================================================
    # 1. MEAT (گوشت، مرغ، ماهی، تخم‌مرغ - منابع پروتئین)
    # =========================================================================
    # مرغ و ماکیان
    {
        "name_fa": "سینه مرغ پخته / آب‌پز (بدون پوست)",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 165.0,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 3.6
    },
    {
        "name_fa": "سینه مرغ گریل / کبابی",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 165.0,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 3.6
    },
    {
        "name_fa": "سینه مرغ خام (بدون پوست)",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 120.0,
        "protein_g": 22.5,
        "carbs_g": 0.0,
        "fat_g": 2.6
    },
    {
        "name_fa": "فیله مرغ پخته / گریل",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 140.0,
        "protein_g": 28.0,
        "carbs_g": 0.0,
        "fat_g": 2.0
    },
    {
        "name_fa": "فیله مرغ خام",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 115.0,
        "protein_g": 23.0,
        "carbs_g": 0.0,
        "fat_g": 1.8
    },
    {
        "name_fa": "جوجه‌کباب سینه مرغ",
        "category": "meat",
        "unit": "۱ سیخ (۱۵۰ گرم)",
        "calories": 245.0,
        "protein_g": 44.0,
        "carbs_g": 1.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "جوجه‌کباب فیله مرغ کم‌روغن",
        "category": "meat",
        "unit": "۱ سیخ (۱۵۰ گرم)",
        "calories": 220.0,
        "protein_g": 42.0,
        "carbs_g": 1.0,
        "fat_g": 4.5
    },
    {
        "name_fa": "جوجه‌کباب ران مرغ با استخوان",
        "category": "meat",
        "unit": "۱ سیخ (۱۵۰ گرم)",
        "calories": 310.0,
        "protein_g": 35.0,
        "carbs_g": 1.0,
        "fat_g": 18.0
    },
    {
        "name_fa": "ران مرغ پخته بدون پوست",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 209.0,
        "protein_g": 26.0,
        "carbs_g": 0.0,
        "fat_g": 10.9
    },
    {
        "name_fa": "ران مرغ پخته با پوست",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 245.0,
        "protein_g": 24.0,
        "carbs_g": 0.0,
        "fat_g": 16.0
    },
    {
        "name_fa": "ساق مرغ پخته بدون پوست",
        "category": "meat",
        "unit": "۱ عدد (۷۰ گرم)",
        "calories": 125.0,
        "protein_g": 18.0,
        "carbs_g": 0.0,
        "fat_g": 5.5
    },
    {
        "name_fa": "بال مرغ کبابی",
        "category": "meat",
        "unit": "۱ عدد (۴۰ گرم)",
        "calories": 95.0,
        "protein_g": 9.0,
        "carbs_g": 0.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "سنگدان مرغ پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 145.0,
        "protein_g": 27.0,
        "carbs_g": 0.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "جگر مرغ پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 167.0,
        "protein_g": 24.5,
        "carbs_g": 1.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "فیله بوقلمون پخته / گریل",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 135.0,
        "protein_g": 30.0,
        "carbs_g": 0.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "سینه بوقلمون خام",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 110.0,
        "protein_g": 24.0,
        "carbs_g": 0.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "ران بوقلمون پخته بدون پوست",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 170.0,
        "protein_g": 28.0,
        "carbs_g": 0.0,
        "fat_g": 6.0
    },
    {
        "name_fa": "کباب بوقلمون زعفرانی",
        "category": "meat",
        "unit": "۱ سیخ (۱۲۰ گرم)",
        "calories": 190.0,
        "protein_g": 32.0,
        "carbs_g": 1.0,
        "fat_g": 6.0
    },
    {
        "name_fa": "گوشت شترمرغ پخته / استیک",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 145.0,
        "protein_g": 28.0,
        "carbs_g": 0.0,
        "fat_g": 3.0
    },
    {
        "name_fa": "گوشت بلدرچین پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 190.0,
        "protein_g": 25.0,
        "carbs_g": 0.0,
        "fat_g": 9.0
    },

    # گوشت قرمز (گوساله، گوسفند، شتر)
    {
        "name_fa": "گوشت راسته گوساله پخته / استیک",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 210.0,
        "protein_g": 29.0,
        "carbs_g": 0.0,
        "fat_g": 10.0
    },
    {
        "name_fa": "فیله گوساله کبابی / پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 190.0,
        "protein_g": 30.0,
        "carbs_g": 0.0,
        "fat_g": 7.5
    },
    {
        "name_fa": "گوشت ران گوساله بدون چربی پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 200.0,
        "protein_g": 28.0,
        "carbs_g": 0.0,
        "fat_g": 9.0
    },
    {
        "name_fa": "گوشت چرخ‌کرده گوساله کم‌چربی پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 220.0,
        "protein_g": 26.0,
        "carbs_g": 0.0,
        "fat_g": 12.0
    },
    {
        "name_fa": "گوشت چرخ‌کرده مخلوط پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 260.0,
        "protein_g": 24.0,
        "carbs_g": 0.0,
        "fat_g": 18.0
    },
    {
        "name_fa": "کباب کوبیده سنتی",
        "category": "meat",
        "unit": "۱ سیخ (۱۰۰ گرم)",
        "calories": 280.0,
        "protein_g": 18.0,
        "carbs_g": 2.0,
        "fat_g": 22.0
    },
    {
        "name_fa": "کباب برگ ممتاز گوسفندی / گوساله",
        "category": "meat",
        "unit": "۱ سیخ (۱۵۰ گرم)",
        "calories": 285.0,
        "protein_g": 42.0,
        "carbs_g": 1.0,
        "fat_g": 12.0
    },
    {
        "name_fa": "کباب چنجه گوسفندی",
        "category": "meat",
        "unit": "۱ سیخ (۱۵۰ گرم)",
        "calories": 330.0,
        "protein_g": 38.0,
        "carbs_g": 0.0,
        "fat_g": 19.0
    },
    {
        "name_fa": "کباب سلطانی",
        "category": "meat",
        "unit": "۱ سیخ (۲۲۰ گرم)",
        "calories": 460.0,
        "protein_g": 55.0,
        "carbs_g": 2.0,
        "fat_g": 25.0
    },
    {
        "name_fa": "کباب شیشلیک گوسفندی",
        "category": "meat",
        "unit": "۱ سیخ (۳۰۰ گرم با استخوان)",
        "calories": 480.0,
        "protein_g": 45.0,
        "carbs_g": 0.0,
        "fat_g": 32.0
    },
    {
        "name_fa": "کباب بختیاری (مخلوط جوجه و چنجه)",
        "category": "meat",
        "unit": "۱ سیخ (۱۵۰ گرم)",
        "calories": 290.0,
        "protein_g": 40.0,
        "carbs_g": 1.0,
        "fat_g": 13.5
    },
    {
        "name_fa": "کباب تابه‌ای خانگی کم‌روغن",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 215.0,
        "protein_g": 22.0,
        "carbs_g": 4.0,
        "fat_g": 12.0
    },
    {
        "name_fa": "گوشت راسته گوسفندی پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 260.0,
        "protein_g": 25.0,
        "carbs_g": 0.0,
        "fat_g": 17.0
    },
    {
        "name_fa": "گوشت ران گوسفندی پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 245.0,
        "protein_g": 26.0,
        "carbs_g": 0.0,
        "fat_g": 15.0
    },
    {
        "name_fa": "ماهیچه گوسفندی آب‌پز",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 230.0,
        "protein_g": 27.0,
        "carbs_g": 0.0,
        "fat_g": 13.0
    },
    {
        "name_fa": "گردن گوسفندی پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 275.0,
        "protein_g": 23.0,
        "carbs_g": 0.0,
        "fat_g": 20.0
    },
    {
        "name_fa": "گوشت شتر لخم پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 175.0,
        "protein_g": 29.0,
        "carbs_g": 0.0,
        "fat_g": 5.5
    },
    {
        "name_fa": "جگر سیاه گوسفندی / گوساله",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 165.0,
        "protein_g": 26.0,
        "carbs_g": 3.5,
        "fat_g": 4.5
    },
    {
        "name_fa": "دل و قلوه گوسفندی پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 150.0,
        "protein_g": 24.0,
        "carbs_g": 1.0,
        "fat_g": 5.0
    },
    {
        "name_fa": "زبان گوساله پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 270.0,
        "protein_g": 20.0,
        "carbs_g": 0.0,
        "fat_g": 20.0
    },

    # ماهی و آبزیان
    {
        "name_fa": "فیله ماهی قزل‌آلا پخته / گریل",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 190.0,
        "protein_g": 23.0,
        "carbs_g": 0.0,
        "fat_g": 10.5
    },
    {
        "name_fa": "فیله ماهی قزل‌آلا خام",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 145.0,
        "protein_g": 20.5,
        "carbs_g": 0.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "ماهی سالمون نروژی پخته / استیک",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 205.0,
        "protein_g": 22.5,
        "carbs_g": 0.0,
        "fat_g": 12.5
    },
    {
        "name_fa": "فیله ماهی تیلاپیا پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 128.0,
        "protein_g": 26.0,
        "carbs_g": 0.0,
        "fat_g": 2.5
    },
    {
        "name_fa": "ماهی شیر پخته / کبابی",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 175.0,
        "protein_g": 25.0,
        "carbs_g": 0.0,
        "fat_g": 8.0
    },
    {
        "name_fa": "ماهی سفید شمال پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 135.0,
        "protein_g": 22.0,
        "carbs_g": 0.0,
        "fat_g": 4.5
    },
    {
        "name_fa": "ماهی کپور پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 160.0,
        "protein_g": 21.0,
        "carbs_g": 0.0,
        "fat_g": 8.0
    },
    {
        "name_fa": "ماهی سرخو پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 140.0,
        "protein_g": 26.0,
        "carbs_g": 0.0,
        "fat_g": 3.0
    },
    {
        "name_fa": "ماهی حلوا سفید پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 130.0,
        "protein_g": 23.0,
        "carbs_g": 0.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "تن ماهی در آب‌نمک رژیمی (آبکش‌شده)",
        "category": "meat",
        "unit": "۱ قوطی (۱۲۰ گرم خالص)",
        "calories": 140.0,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 1.2
    },
    {
        "name_fa": "تن ماهی در روغن زیتون (روغن گرفته‌شده)",
        "category": "meat",
        "unit": "۱ قوطی (۱۲۰ گرم خالص)",
        "calories": 230.0,
        "protein_g": 30.0,
        "carbs_g": 0.0,
        "fat_g": 12.0
    },
    {
        "name_fa": "تن ماهی در روغن معمولی (روغن گرفته‌شده)",
        "category": "meat",
        "unit": "۱ قوطی (۱۲۰ گرم خالص)",
        "calories": 260.0,
        "protein_g": 29.0,
        "carbs_g": 0.0,
        "fat_g": 15.0
    },
    {
        "name_fa": "میگو آب‌پز / گریل",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 100.0,
        "protein_g": 24.0,
        "carbs_g": 0.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "میگو خام پاک‌شده",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 85.0,
        "protein_g": 20.0,
        "carbs_g": 0.0,
        "fat_g": 0.5
    },

    # تخم‌مرغ و فرآورده‌های آن
    {
        "name_fa": "تخم‌مرغ کامل آب‌پز",
        "category": "meat",
        "unit": "۱ عدد متوسط (۵۰ گرم)",
        "calories": 74.0,
        "protein_g": 6.3,
        "carbs_g": 0.4,
        "fat_g": 5.0
    },
    {
        "name_fa": "سفیده تخم‌مرغ آب‌پز",
        "category": "meat",
        "unit": "۱ عدد (۳۳ گرم)",
        "calories": 17.0,
        "protein_g": 3.6,
        "carbs_g": 0.2,
        "fat_g": 0.1
    },
    {
        "name_fa": "سفیده تخم‌مرغ مایع پاستوریزه",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 52.0,
        "protein_g": 11.0,
        "carbs_g": 0.7,
        "fat_g": 0.2
    },
    {
        "name_fa": "زرده تخم‌مرغ آب‌پز",
        "category": "meat",
        "unit": "۱ عدد (۱۷ گرم)",
        "calories": 55.0,
        "protein_g": 2.7,
        "carbs_g": 0.3,
        "fat_g": 4.5
    },
    {
        "name_fa": "نیمرو با ۱ قاشق چایخوری روغن",
        "category": "meat",
        "unit": "۱ عدد",
        "calories": 95.0,
        "protein_g": 6.5,
        "carbs_g": 0.5,
        "fat_g": 7.5
    },
    {
        "name_fa": "املت گوجه‌فرنگی سنتی کم‌روغن",
        "category": "meat",
        "unit": "۱ پرس (۲۰۰ گرم)",
        "calories": 190.0,
        "protein_g": 13.0,
        "carbs_g": 7.0,
        "fat_g": 12.0
    },
    {
        "name_fa": "املت اسفناج و سفیده تخم‌مرغ ورزشی",
        "category": "meat",
        "unit": "۱ پرس (۴ سفیده + اسفناج)",
        "calories": 120.0,
        "protein_g": 20.0,
        "carbs_g": 4.0,
        "fat_g": 2.0
    },
    {
        "name_fa": "تخم بلدرچین آب‌پز",
        "category": "meat",
        "unit": "۱ عدد (۱۰ گرم)",
        "calories": 16.0,
        "protein_g": 1.3,
        "carbs_g": 0.0,
        "fat_g": 1.1
    },

    # =========================================================================
    # 2. RICE (برنج، نان، غلات، کربوهیدرات‌های پیچیده و خوراک‌ها)
    # =========================================================================
    # برنج و خوراک‌های برنجی
    {
        "name_fa": "برنج سفید کته بی‌روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 130.0,
        "protein_g": 2.7,
        "carbs_g": 28.5,
        "fat_g": 0.3
    },
    {
        "name_fa": "برنج سفید آبکش کم‌روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 135.0,
        "protein_g": 2.6,
        "carbs_g": 29.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "برنج کته روغنی خانگی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 170.0,
        "protein_g": 2.7,
        "carbs_g": 30.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "برنج سفید زعفرانی کته",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 240.0,
        "protein_g": 4.5,
        "carbs_g": 48.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "برنج قهوه‌ای پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 112.0,
        "protein_g": 2.6,
        "carbs_g": 24.0,
        "fat_g": 0.9
    },
    {
        "name_fa": "برنج باسماتی پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 125.0,
        "protein_g": 3.0,
        "carbs_g": 27.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "برنج کته با شوید کم‌روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 140.0,
        "protein_g": 2.8,
        "carbs_g": 28.0,
        "fat_g": 1.8
    },
    {
        "name_fa": "عدس‌پلو با کشمش کم‌روغن",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 270.0,
        "protein_g": 7.5,
        "carbs_g": 52.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "لوبیاپلو با گوشت چرخ‌کرده کم‌چرب",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 285.0,
        "protein_g": 11.0,
        "carbs_g": 44.0,
        "fat_g": 7.0
    },
    {
        "name_fa": "باقالی‌پلو بدون گوشت",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 260.0,
        "protein_g": 7.0,
        "carbs_g": 46.0,
        "fat_g": 4.5
    },
    {
        "name_fa": "زرشک‌پلو بدون مرغ و روغن کم",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 255.0,
        "protein_g": 4.5,
        "carbs_g": 50.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "استامبولی پلو با سیب‌زمینی و گوجه",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 250.0,
        "protein_g": 5.0,
        "carbs_g": 48.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "ته‌دیگ نان لواش",
        "category": "rice",
        "unit": "۳۰ گرم",
        "calories": 140.0,
        "protein_g": 2.0,
        "carbs_g": 16.0,
        "fat_g": 7.5
    },
    {
        "name_fa": "ته‌دیگ سیب‌زمینی",
        "category": "rice",
        "unit": "۵۰ گرم",
        "calories": 135.0,
        "protein_g": 1.5,
        "carbs_g": 17.0,
        "fat_g": 6.5
    },

    # نان‌ها
    {
        "name_fa": "نان سنگک سنتی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 255.0,
        "protein_g": 9.2,
        "carbs_g": 51.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "نان سنگک (۱ کف دست بدون انگشت)",
        "category": "rice",
        "unit": "۱ کف دست (۳۰ گرم)",
        "calories": 77.0,
        "protein_g": 2.8,
        "carbs_g": 15.3,
        "fat_g": 0.5
    },
    {
        "name_fa": "نان بربری سنتی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 265.0,
        "protein_g": 8.8,
        "carbs_g": 53.5,
        "fat_g": 1.6
    },
    {
        "name_fa": "نان بربری (۱ کف دست بدون انگشت)",
        "category": "rice",
        "unit": "۱ کف دست (۳۰ گرم)",
        "calories": 80.0,
        "protein_g": 2.6,
        "carbs_g": 16.0,
        "fat_g": 0.5
    },
    {
        "name_fa": "نان لواش سنتی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 285.0,
        "protein_g": 8.0,
        "carbs_g": 58.0,
        "fat_g": 2.0
    },
    {
        "name_fa": "نان لواش (۱ کف دست)",
        "category": "rice",
        "unit": "۱ کف دست (۲۰ گرم)",
        "calories": 57.0,
        "protein_g": 1.6,
        "carbs_g": 11.6,
        "fat_g": 0.4
    },
    {
        "name_fa": "نان تافتون سنتی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 260.0,
        "protein_g": 8.5,
        "carbs_g": 52.0,
        "fat_g": 1.8
    },
    {
        "name_fa": "نان تافتون (۱ کف دست)",
        "category": "rice",
        "unit": "۱ کف دست (۲۵ گرم)",
        "calories": 65.0,
        "protein_g": 2.1,
        "carbs_g": 13.0,
        "fat_g": 0.5
    },
    {
        "name_fa": "نان تست سفید",
        "category": "rice",
        "unit": "۱ ورق (۲۵ گرم)",
        "calories": 68.0,
        "protein_g": 2.2,
        "carbs_g": 13.0,
        "fat_g": 0.8
    },
    {
        "name_fa": "نان تست جو و هفت‌غله سبوس‌دار",
        "category": "rice",
        "unit": "۱ ورق (۲۸ گرم)",
        "calories": 70.0,
        "protein_g": 3.2,
        "carbs_g": 12.5,
        "fat_g": 0.9
    },
    {
        "name_fa": "نان تست پروتئینی ورزشی",
        "category": "rice",
        "unit": "۱ ورق (۳۰ گرم)",
        "calories": 80.0,
        "protein_g": 7.5,
        "carbs_g": 7.0,
        "fat_g": 2.0
    },
    {
        "name_fa": "نان جو سنتی خشک",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 330.0,
        "protein_g": 10.5,
        "carbs_g": 68.0,
        "fat_g": 2.0
    },
    {
        "name_fa": "نان پیتا سبوس‌دار",
        "category": "rice",
        "unit": "۱ عدد (۶۰ گرم)",
        "calories": 160.0,
        "protein_g": 5.5,
        "carbs_g": 33.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "رایس کیک / کیک برنجی ساده",
        "category": "rice",
        "unit": "۱ عدد (۱۰ گرم)",
        "calories": 38.0,
        "protein_g": 0.8,
        "carbs_g": 8.2,
        "fat_g": 0.3
    },
    {
        "name_fa": "نان باگت فرانسوی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 275.0,
        "protein_g": 9.0,
        "carbs_g": 55.0,
        "fat_g": 1.8
    },

    # سیب‌زمینی و سبزیجات نشاسته‌ای
    {
        "name_fa": "سیب‌زمینی آب‌پز بی‌روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 87.0,
        "protein_g": 2.0,
        "carbs_g": 20.0,
        "fat_g": 0.1
    },
    {
        "name_fa": "سیب‌زمینی آب‌پز متوسط",
        "category": "rice",
        "unit": "۱ عدد متوسط (۱۵۰ گرم)",
        "calories": 130.0,
        "protein_g": 3.0,
        "carbs_g": 30.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "سیب‌زمینی تنوری بدون روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 93.0,
        "protein_g": 2.5,
        "carbs_g": 21.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "پوره سیب‌زمینی با شیر کم‌چرب",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 105.0,
        "protein_g": 2.5,
        "carbs_g": 19.0,
        "fat_g": 2.0
    },
    {
        "name_fa": "سیب‌زمینی سرخ‌کرده خانگی",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 270.0,
        "protein_g": 3.5,
        "carbs_g": 35.0,
        "fat_g": 13.5
    },
    {
        "name_fa": "سیب‌زمینی شیرین پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 90.0,
        "protein_g": 2.0,
        "carbs_g": 21.0,
        "fat_g": 0.1
    },
    {
        "name_fa": "ذرت پخته / بلال آب‌پز",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 96.0,
        "protein_g": 3.4,
        "carbs_g": 21.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "نخودفرنگی پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 84.0,
        "protein_g": 5.4,
        "carbs_g": 15.6,
        "fat_g": 0.4
    },

    # جو، غلات و ماکارونی
    {
        "name_fa": "جو دو سر پرک خام (اوتمیل)",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 389.0,
        "protein_g": 16.9,
        "carbs_g": 66.3,
        "fat_g": 6.9
    },
    {
        "name_fa": "جو دو سر پرک (یک سهم اوتمیل)",
        "category": "rice",
        "unit": "۴۰ گرم",
        "calories": 155.0,
        "protein_g": 6.8,
        "carbs_g": 26.5,
        "fat_g": 2.8
    },
    {
        "name_fa": "اوتمیل پخته‌شده با آب",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 71.0,
        "protein_g": 2.5,
        "carbs_g": 12.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "ماکارونی / اسپاگتی پخته بدون سس",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 158.0,
        "protein_g": 5.8,
        "carbs_g": 31.0,
        "fat_g": 0.9
    },
    {
        "name_fa": "ماکارونی با گوشت چرخ‌کرده کم‌چرب و رب",
        "category": "rice",
        "unit": "۱ بشقاب (۲۵۰ گرم)",
        "calories": 420.0,
        "protein_g": 22.0,
        "carbs_g": 60.0,
        "fat_g": 9.0
    },
    {
        "name_fa": "پاستا سبوس‌دار پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 145.0,
        "protein_g": 6.5,
        "carbs_g": 28.0,
        "fat_g": 0.8
    },
    {
        "name_fa": "کینوا پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 120.0,
        "protein_g": 4.4,
        "carbs_g": 21.3,
        "fat_g": 1.9
    },
    {
        "name_fa": "کینوا خام",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 368.0,
        "protein_g": 14.1,
        "carbs_g": 64.2,
        "fat_g": 6.1
    },
    {
        "name_fa": "دانه چیا",
        "category": "rice",
        "unit": "۱ قاشق غذاخوری (۱۲ گرم)",
        "calories": 58.0,
        "protein_g": 2.0,
        "carbs_g": 5.0,
        "fat_g": 3.7
    },
    {
        "name_fa": "بلغور گندم پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 83.0,
        "protein_g": 3.1,
        "carbs_g": 18.6,
        "fat_g": 0.2
    },
    {
        "name_fa": "کوسکوس پخته",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 112.0,
        "protein_g": 3.8,
        "carbs_g": 23.2,
        "fat_g": 0.2
    },
    {
        "name_fa": "حلیم گندم با گوشت بدون شکر و روغن",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 310.0,
        "protein_g": 18.0,
        "carbs_g": 48.0,
        "fat_g": 4.5
    },
    {
        "name_fa": "فرنی با شیر کم‌چرب و عسل",
        "category": "rice",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 180.0,
        "protein_g": 6.5,
        "carbs_g": 32.0,
        "fat_g": 2.5
    },
    {
        "name_fa": "شیربرنج با شیر کم‌چرب",
        "category": "rice",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 210.0,
        "protein_g": 7.0,
        "carbs_g": 38.0,
        "fat_g": 3.0
    },

    # خوراک‌ها و خورش‌های پرمصرف
    {
        "name_fa": "خورش قورمه‌سبزی کم‌روغن با گوشت",
        "category": "rice",
        "unit": "۱ ملاقه (۱۰۰ گرم)",
        "calories": 145.0,
        "protein_g": 8.5,
        "carbs_g": 4.0,
        "fat_g": 10.0
    },
    {
        "name_fa": "خورش قیمه با گوشت کم‌چرب",
        "category": "rice",
        "unit": "۱ ملاقه (۱۰۰ گرم)",
        "calories": 155.0,
        "protein_g": 9.0,
        "carbs_g": 7.5,
        "fat_g": 9.5
    },
    {
        "name_fa": "خورش کرفس با گوشت گوساله",
        "category": "rice",
        "unit": "۱ ملاقه (۱۰۰ گرم)",
        "calories": 130.0,
        "protein_g": 8.0,
        "carbs_g": 3.5,
        "fat_g": 9.0
    },
    {
        "name_fa": "خورش فسنجان با سینه مرغ",
        "category": "rice",
        "unit": "۱ ملاقه (۱۰۰ گرم)",
        "calories": 280.0,
        "protein_g": 10.0,
        "carbs_g": 12.0,
        "fat_g": 22.0
    },
    {
        "name_fa": "سوپ جو با مرغ و هویج",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 160.0,
        "protein_g": 10.0,
        "carbs_g": 22.0,
        "fat_g": 3.0
    },
    {
        "name_fa": "سوپ ورمیشل با مرغ",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 140.0,
        "protein_g": 8.5,
        "carbs_g": 20.0,
        "fat_g": 2.5
    },
    {
        "name_fa": "میرزاقاسمی کم‌روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 95.0,
        "protein_g": 4.0,
        "carbs_g": 6.0,
        "fat_g": 6.0
    },
    {
        "name_fa": "کشک بادمجان کم‌روغن",
        "category": "rice",
        "unit": "100 گرم",
        "calories": 140.0,
        "protein_g": 5.5,
        "carbs_g": 8.0,
        "fat_g": 9.5
    },

    # =========================================================================
    # 3. LEGUMES (حبوبات)
    # =========================================================================
    {
        "name_fa": "عدسی پخته خانگی کم‌روغن",
        "category": "legumes",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 230.0,
        "protein_g": 16.0,
        "carbs_g": 38.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "عدس خام",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 350.0,
        "protein_g": 25.8,
        "carbs_g": 60.0,
        "fat_g": 1.1
    },
    {
        "name_fa": "عدس آب‌پز بدون روغن",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 116.0,
        "protein_g": 9.0,
        "carbs_g": 20.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "خوراک لوبیا چیتی خانگی",
        "category": "legumes",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 240.0,
        "protein_g": 15.0,
        "carbs_g": 42.0,
        "fat_g": 1.8
    },
    {
        "name_fa": "کنسرو لوبیا چیتی در سس گوجه",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 105.0,
        "protein_g": 6.0,
        "carbs_g": 18.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "لوبیا چیتی آب‌پز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 127.0,
        "protein_g": 9.0,
        "carbs_g": 22.8,
        "fat_g": 0.5
    },
    {
        "name_fa": "لوبیا قرمز آب‌پز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 127.0,
        "protein_g": 8.7,
        "carbs_g": 22.8,
        "fat_g": 0.5
    },
    {
        "name_fa": "لوبیا سفید آب‌پز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 139.0,
        "protein_g": 9.7,
        "carbs_g": 25.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "لوبیا سیاه آب‌پز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 132.0,
        "protein_g": 8.9,
        "carbs_g": 23.7,
        "fat_g": 0.5
    },
    {
        "name_fa": "نخود آب‌پز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 164.0,
        "protein_g": 8.9,
        "carbs_g": 27.4,
        "fat_g": 2.6
    },
    {
        "name_fa": "نخود خام",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 364.0,
        "protein_g": 19.3,
        "carbs_g": 60.6,
        "fat_g": 6.0
    },
    {
        "name_fa": "نخودچی بو داده بی‌نمک",
        "category": "legumes",
        "unit": "۵۰ گرم",
        "calories": 180.0,
        "protein_g": 9.5,
        "carbs_g": 30.0,
        "fat_g": 3.0
    },
    {
        "name_fa": "لپه خام",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 341.0,
        "protein_g": 24.5,
        "carbs_g": 60.0,
        "fat_g": 1.2
    },
    {
        "name_fa": "لپه پخته",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 118.0,
        "protein_g": 8.3,
        "carbs_g": 21.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "ماش پخته",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 105.0,
        "protein_g": 7.0,
        "carbs_g": 19.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "ماش خام",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 347.0,
        "protein_g": 23.8,
        "carbs_g": 62.6,
        "fat_g": 1.2
    },
    {
        "name_fa": "باقلا پخته / آب‌پز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 110.0,
        "protein_g": 7.6,
        "carbs_g": 19.5,
        "fat_g": 0.5
    },
    {
        "name_fa": "حمص / هوموس سنتی",
        "category": "legumes",
        "unit": "۱ قاشق غذاخوری (۳۰ گرم)",
        "calories": 50.0,
        "protein_g": 1.5,
        "carbs_g": 4.5,
        "fat_g": 2.8
    },
    {
        "name_fa": "حمص لبنانی (100 گرم)",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 166.0,
        "protein_g": 7.9,
        "carbs_g": 14.3,
        "fat_g": 9.6
    },
    {
        "name_fa": "فلافل ترد سنتی سرخ‌شده",
        "category": "legumes",
        "unit": "۱ قرص (۳۰ گرم)",
        "calories": 75.0,
        "protein_g": 2.5,
        "carbs_g": 8.5,
        "fat_g": 3.5
    },
    {
        "name_fa": "فلافل رژیمی پخته در فر",
        "category": "legumes",
        "unit": "۱ قرص (۳۰ گرم)",
        "calories": 45.0,
        "protein_g": 2.8,
        "carbs_g": 7.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "دانه سویا بو داده آجیلی",
        "category": "legumes",
        "unit": "۵۰ گرم",
        "calories": 225.0,
        "protein_g": 18.0,
        "carbs_g": 15.0,
        "fat_g": 10.0
    },
    {
        "name_fa": "سویا بافت‌دار خشک (پروتئین سویا)",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 345.0,
        "protein_g": 52.0,
        "carbs_g": 30.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "سویا خیس‌خورده و پخته‌شده",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 120.0,
        "protein_g": 17.0,
        "carbs_g": 10.0,
        "fat_g": 0.5
    },
    {
        "name_fa": "ادامامه / دانه سویا سبز بخارپز",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 122.0,
        "protein_g": 11.0,
        "carbs_g": 10.0,
        "fat_g": 5.2
    },
    {
        "name_fa": "توفو ساده (پنیر سویا)",
        "category": "legumes",
        "unit": "100 گرم",
        "calories": 76.0,
        "protein_g": 8.0,
        "carbs_g": 1.9,
        "fat_g": 4.8
    },
    {
        "name_fa": "خوراک دال عدس تند",
        "category": "legumes",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 210.0,
        "protein_g": 14.0,
        "carbs_g": 36.0,
        "fat_g": 1.2
    },

    # =========================================================================
    # 4. DAIRY (لبنیات)
    # =========================================================================
    {
        "name_fa": "شیر کم‌چرب (۱.۵٪)",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 110.0,
        "protein_g": 8.0,
        "carbs_g": 12.0,
        "fat_g": 3.6
    },
    {
        "name_fa": "شیر بدون چربی (زیر ۰.۵٪)",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 85.0,
        "protein_g": 8.5,
        "carbs_g": 12.5,
        "fat_g": 0.5
    },
    {
        "name_fa": "شیر پرچرب (۳٪)",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 150.0,
        "protein_g": 7.8,
        "carbs_g": 11.5,
        "fat_g": 8.0
    },
    {
        "name_fa": "شیر پروتئینه پرومیلک کاله",
        "category": "dairy",
        "unit": "۱ بطری (۳۳۰ میلی‌لیتر)",
        "calories": 215.0,
        "protein_g": 30.0,
        "carbs_g": 16.5,
        "fat_g": 3.3
    },
    {
        "name_fa": "شیر بدون لاکتوز کم‌چرب",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 110.0,
        "protein_g": 8.0,
        "carbs_g": 12.0,
        "fat_g": 3.6
    },
    {
        "name_fa": "شیر بادام بدون شکر",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 35.0,
        "protein_g": 1.0,
        "carbs_g": 1.5,
        "fat_g": 2.5
    },
    {
        "name_fa": "شیر سویا طبیعی",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 90.0,
        "protein_g": 7.0,
        "carbs_g": 4.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "شیر جو دوسر بدون شکر",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 120.0,
        "protein_g": 3.0,
        "carbs_g": 16.0,
        "fat_g": 4.5
    },
    {
        "name_fa": "ماست ایسلندی پروتئینی کاله",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 60.0,
        "protein_g": 10.0,
        "carbs_g": 4.0,
        "fat_g": 0.1
    },
    {
        "name_fa": "ماست یونانی کم‌چرب",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 70.0,
        "protein_g": 8.5,
        "carbs_g": 4.5,
        "fat_g": 2.0
    },
    {
        "name_fa": "ماست کم‌چرب معمولی (۱.۵٪)",
        "category": "dairy",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 110.0,
        "protein_g": 7.5,
        "carbs_g": 11.0,
        "fat_g": 3.0
    },
    {
        "name_fa": "ماست همزده کم‌چرب",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 62.0,
        "protein_g": 3.8,
        "carbs_g": 5.5,
        "fat_g": 2.5
    },
    {
        "name_fa": "ماست چکیده کم‌چرب",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 90.0,
        "protein_g": 7.0,
        "carbs_g": 6.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "ماست و خیار خانگی با نعنا",
        "category": "dairy",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 115.0,
        "protein_g": 7.0,
        "carbs_g": 10.0,
        "fat_g": 3.2
    },
    {
        "name_fa": "ماست و اسفناج (بورانی)",
        "category": "dairy",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 125.0,
        "protein_g": 8.5,
        "carbs_g": 11.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "کشک مایع پاستوریزه کم‌نمک",
        "category": "dairy",
        "unit": "۱ قاشق غذاخوری (۲۰ گرم)",
        "calories": 25.0,
        "protein_g": 2.5,
        "carbs_g": 1.5,
        "fat_g": 0.8
    },
    {
        "name_fa": "کشک مایع پاستوریزه (100 گرم)",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 125.0,
        "protein_g": 12.5,
        "carbs_g": 7.5,
        "fat_g": 4.0
    },
    {
        "name_fa": "کشک خشک سنتی پرپروتئین",
        "category": "dairy",
        "unit": "۳۰ گرم",
        "calories": 110.0,
        "protein_g": 16.0,
        "carbs_g": 5.0,
        "fat_g": 2.5
    },
    {
        "name_fa": "پنیر کاتیج کم‌چرب",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 85.0,
        "protein_g": 12.5,
        "carbs_g": 3.5,
        "fat_g": 1.5
    },
    {
        "name_fa": "پنیر سفید کم‌چرب صبحانه",
        "category": "dairy",
        "unit": "۱ قوطی کبریت (۳۰ گرم)",
        "calories": 65.0,
        "protein_g": 5.0,
        "carbs_g": 1.0,
        "fat_g": 4.5
    },
    {
        "name_fa": "پنیر فتا کم‌نمک",
        "category": "dairy",
        "unit": "۳۰ گرم",
        "calories": 75.0,
        "protein_g": 4.5,
        "carbs_g": 1.2,
        "fat_g": 5.8
    },
    {
        "name_fa": "پنیر تبریز سنتی",
        "category": "dairy",
        "unit": "۳۰ گرم",
        "calories": 85.0,
        "protein_g": 5.5,
        "carbs_g": 0.5,
        "fat_g": 7.0
    },
    {
        "name_fa": "پنیر ریکوتا",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 140.0,
        "protein_g": 11.0,
        "carbs_g": 3.0,
        "fat_g": 9.0
    },
    {
        "name_fa": "پنیر موزارلا کم‌چرب",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 240.0,
        "protein_g": 24.0,
        "carbs_g": 2.0,
        "fat_g": 16.0
    },
    {
        "name_fa": "پنیر چدار ورقی",
        "category": "dairy",
        "unit": "۱ ورق (۲۰ گرم)",
        "calories": 80.0,
        "protein_g": 5.0,
        "carbs_g": 0.5,
        "fat_g": 6.5
    },
    {
        "name_fa": "پنیر پارمزان رنده‌شده",
        "category": "dairy",
        "unit": "۱ قاشق غذاخوری (۱۰ گرم)",
        "calories": 43.0,
        "protein_g": 3.8,
        "carbs_g": 0.4,
        "fat_g": 2.9
    },
    {
        "name_fa": "پنیر لبنه",
        "category": "dairy",
        "unit": "۳۰ گرم",
        "calories": 70.0,
        "protein_g": 2.0,
        "carbs_g": 1.5,
        "fat_g": 6.5
    },
    {
        "name_fa": "دوغ نعنایی کم‌نمک بدون گاز",
        "category": "dairy",
        "unit": "۱ لیوان (۲۴۰ گرم)",
        "calories": 55.0,
        "protein_g": 3.5,
        "carbs_g": 4.5,
        "fat_g": 1.8
    },
    {
        "name_fa": "خامه صبحانه پاستوریزه (۳۰٪)",
        "category": "dairy",
        "unit": "۱ قاشق غذاخوری (۱۵ گرم)",
        "calories": 50.0,
        "protein_g": 0.4,
        "carbs_g": 0.6,
        "fat_g": 5.0
    },
    {
        "name_fa": "سرشیر سنتی",
        "category": "dairy",
        "unit": "۳۰ گرم",
        "calories": 120.0,
        "protein_g": 1.5,
        "carbs_g": 1.0,
        "fat_g": 12.5
    },
    {
        "name_fa": "کره پاستوریزه حیوانی",
        "category": "dairy",
        "unit": "۱۰ گرم",
        "calories": 74.0,
        "protein_g": 0.1,
        "carbs_g": 0.1,
        "fat_g": 8.2
    },
    {
        "name_fa": "کره حیوانی زرد / روغن حیوانی",
        "category": "dairy",
        "unit": "۱۰ گرم",
        "calories": 88.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 9.9
    },

    # =========================================================================
    # 5. FRUITS (میوه و سبزیجات)
    # =========================================================================
    # میوه‌ها
    {
        "name_fa": "سیب درختی با پوست متوسط",
        "category": "fruits",
        "unit": "۱ عدد متوسط (۱۵۰ گرم)",
        "calories": 78.0,
        "protein_g": 0.4,
        "carbs_g": 21.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "سیب درختی (100 گرم)",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 52.0,
        "protein_g": 0.3,
        "carbs_g": 14.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "موز متوسط",
        "category": "fruits",
        "unit": "۱ عدد متوسط (۱۱۸ گرم)",
        "calories": 105.0,
        "protein_g": 1.3,
        "carbs_g": 27.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "موز بزرگ",
        "category": "fruits",
        "unit": "۱ عدد بزرگ (۱۵۰ گرم)",
        "calories": 135.0,
        "protein_g": 1.6,
        "carbs_g": 34.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "موز (100 گرم)",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 89.0,
        "protein_g": 1.1,
        "carbs_g": 23.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "پرتقال تامسون متوسط",
        "category": "fruits",
        "unit": "۱ عدد متوسط (۱۳۰ گرم)",
        "calories": 62.0,
        "protein_g": 1.2,
        "carbs_g": 15.4,
        "fat_g": 0.2
    },
    {
        "name_fa": "نارنگی متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۹۰ گرم)",
        "calories": 47.0,
        "protein_g": 0.7,
        "carbs_g": 12.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "خرما مضافتی بم",
        "category": "fruits",
        "unit": "۱ عدد (۱۰ گرم)",
        "calories": 28.0,
        "protein_g": 0.2,
        "carbs_g": 7.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "خرما پیارم مرغوب",
        "category": "fruits",
        "unit": "۱ عدد (۱۵ گرم)",
        "calories": 45.0,
        "protein_g": 0.4,
        "carbs_g": 11.5,
        "fat_g": 0.1
    },
    {
        "name_fa": "خرما زاهدی خشک",
        "category": "fruits",
        "unit": "۱ عدد (۸ گرم)",
        "calories": 23.0,
        "protein_g": 0.2,
        "carbs_g": 6.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "کیوی متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۷۰ گرم)",
        "calories": 42.0,
        "protein_g": 0.8,
        "carbs_g": 10.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "توت فرنگی تازه",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 32.0,
        "protein_g": 0.7,
        "carbs_g": 7.7,
        "fat_g": 0.3
    },
    {
        "name_fa": "توت فرنگی تازه (۱ لیوان)",
        "category": "fruits",
        "unit": "۱ لیوان (۱۵۰ گرم)",
        "calories": 48.0,
        "protein_g": 1.0,
        "carbs_g": 11.5,
        "fat_g": 0.5
    },
    {
        "name_fa": "بلوبری تازه",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 57.0,
        "protein_g": 0.7,
        "carbs_g": 14.5,
        "fat_g": 0.3
    },
    {
        "name_fa": "شاه‌توت / تمشک تازه",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 52.0,
        "protein_g": 1.4,
        "carbs_g": 12.0,
        "fat_g": 0.6
    },
    {
        "name_fa": "انار دانه شده",
        "category": "fruits",
        "unit": "۱ لیوان (۱۵۰ گرم)",
        "calories": 125.0,
        "protein_g": 2.5,
        "carbs_g": 28.0,
        "fat_g": 1.8
    },
    {
        "name_fa": "هندوانه قاچ‌شده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 30.0,
        "protein_g": 0.6,
        "carbs_g": 7.6,
        "fat_g": 0.2
    },
    {
        "name_fa": "خربزه / طالبی قاچ‌شده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 34.0,
        "protein_g": 0.8,
        "carbs_g": 8.2,
        "fat_g": 0.2
    },
    {
        "name_fa": "انگور سفید / قرمز",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 69.0,
        "protein_g": 0.7,
        "carbs_g": 18.1,
        "fat_g": 0.2
    },
    {
        "name_fa": "هلو متوسط",
        "category": "fruits",
        "unit": "۱ عدد متوسط (۱۵۰ گرم)",
        "calories": 58.0,
        "protein_g": 1.4,
        "carbs_g": 14.3,
        "fat_g": 0.4
    },
    {
        "name_fa": "شلیل متوسط",
        "category": "fruits",
        "unit": "۱ عدد متوسط (۱۴۰ گرم)",
        "calories": 60.0,
        "protein_g": 1.5,
        "carbs_g": 15.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "زردآلو تازه",
        "category": "fruits",
        "unit": "۱ عدد (۳۵ گرم)",
        "calories": 17.0,
        "protein_g": 0.5,
        "carbs_g": 3.9,
        "fat_g": 0.1
    },
    {
        "name_fa": "گلابی متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۱۶۰ گرم)",
        "calories": 90.0,
        "protein_g": 0.6,
        "carbs_g": 24.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "گیلاس / آلبالو تازه",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 63.0,
        "protein_g": 1.1,
        "carbs_g": 16.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "انجیر تازه",
        "category": "fruits",
        "unit": "۱ عدد (۵۰ گرم)",
        "calories": 37.0,
        "protein_g": 0.4,
        "carbs_g": 9.6,
        "fat_g": 0.2
    },
    {
        "name_fa": "انجیر خشک",
        "category": "fruits",
        "unit": "۱ عدد (۱۰ گرم)",
        "calories": 25.0,
        "protein_g": 0.3,
        "carbs_g": 6.4,
        "fat_g": 0.1
    },
    {
        "name_fa": "آلو سیاه / قرمز",
        "category": "fruits",
        "unit": "۱ عدد (۶۰ گرم)",
        "calories": 28.0,
        "protein_g": 0.4,
        "carbs_g": 7.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "آناناس تازه خردشده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 50.0,
        "protein_g": 0.5,
        "carbs_g": 13.0,
        "fat_g": 0.1
    },
    {
        "name_fa": "انبه تازه خردشده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 60.0,
        "protein_g": 0.8,
        "carbs_g": 15.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "گریپ‌فروت متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۲۰۰ گرم)",
        "calories": 82.0,
        "protein_g": 1.6,
        "carbs_g": 21.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "لیمو ترش تازه",
        "category": "fruits",
        "unit": "۱ عدد (۵۰ گرم)",
        "calories": 15.0,
        "protein_g": 0.5,
        "carbs_g": 4.5,
        "fat_g": 0.1
    },
    {
        "name_fa": "آب لیمو ترش تازه",
        "category": "fruits",
        "unit": "۱ قاشق غذاخوری (۱۵ گرم)",
        "calories": 4.0,
        "protein_g": 0.1,
        "carbs_g": 1.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "کشمش آفتابی / مویز",
        "category": "fruits",
        "unit": "۳۰ گرم",
        "calories": 90.0,
        "protein_g": 1.0,
        "carbs_g": 23.5,
        "fat_g": 0.1
    },
    {
        "name_fa": "توت خشک سفید",
        "category": "fruits",
        "unit": "۳۰ گرم",
        "calories": 95.0,
        "protein_g": 1.2,
        "carbs_g": 23.0,
        "fat_g": 0.5
    },
    {
        "name_fa": "برگه زردآلو / قیسی",
        "category": "fruits",
        "unit": "۳۰ گرم",
        "calories": 75.0,
        "protein_g": 1.0,
        "carbs_g": 19.0,
        "fat_g": 0.2
    },

    # سبزیجات
    {
        "name_fa": "کلم بروکلی بخارپز",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 35.0,
        "protein_g": 2.4,
        "carbs_g": 7.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "کلم بروکلی خام",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 34.0,
        "protein_g": 2.8,
        "carbs_g": 6.6,
        "fat_g": 0.4
    },
    {
        "name_fa": "اسفناج خام خردشده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 23.0,
        "protein_g": 2.9,
        "carbs_g": 3.6,
        "fat_g": 0.4
    },
    {
        "name_fa": "اسفناج بخارپز / پخته",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 23.0,
        "protein_g": 3.0,
        "carbs_g": 3.8,
        "fat_g": 0.3
    },
    {
        "name_fa": "کاهو پیچ / کاهو رسمی",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 15.0,
        "protein_g": 1.4,
        "carbs_g": 2.9,
        "fat_g": 0.2
    },
    {
        "name_fa": "خیار بوته‌ای با پوست",
        "category": "fruits",
        "unit": "۱ عدد متوسط (۱۰۰ گرم)",
        "calories": 15.0,
        "protein_g": 0.7,
        "carbs_g": 3.6,
        "fat_g": 0.1
    },
    {
        "name_fa": "گوجه فرنگی متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۱۲۰ گرم)",
        "calories": 22.0,
        "protein_g": 1.1,
        "carbs_g": 4.7,
        "fat_g": 0.2
    },
    {
        "name_fa": "سالاد فصل بدون سس (کاهو، خیار، گوجه)",
        "category": "fruits",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 35.0,
        "protein_g": 1.8,
        "carbs_g": 7.5,
        "fat_g": 0.3
    },
    {
        "name_fa": "هویج خام متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۶۰ گرم)",
        "calories": 25.0,
        "protein_g": 0.6,
        "carbs_g": 6.0,
        "fat_g": 0.1
    },
    {
        "name_fa": "هویج بخارپز",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 35.0,
        "protein_g": 0.8,
        "carbs_g": 8.2,
        "fat_g": 0.2
    },
    {
        "name_fa": "قارچ دکمه‌ای خام",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 22.0,
        "protein_g": 3.1,
        "carbs_g": 3.3,
        "fat_g": 0.3
    },
    {
        "name_fa": "قارچ گریل / تفت‌داده بدون روغن",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 28.0,
        "protein_g": 3.5,
        "carbs_g": 4.0,
        "fat_g": 0.4
    },
    {
        "name_fa": "فلفل دلمه‌ای سبز",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 20.0,
        "protein_g": 0.9,
        "carbs_g": 4.6,
        "fat_g": 0.2
    },
    {
        "name_fa": "فلفل دلمه‌ای رنگی قرمز / زرد",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 31.0,
        "protein_g": 1.0,
        "carbs_g": 6.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "کدو سبز پخته / گریل",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 17.0,
        "protein_g": 1.2,
        "carbs_g": 3.1,
        "fat_g": 0.3
    },
    {
        "name_fa": "بادمجان کبابی بدون روغن",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 25.0,
        "protein_g": 1.0,
        "carbs_g": 6.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "کلم سفید خردشده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 25.0,
        "protein_g": 1.3,
        "carbs_g": 5.8,
        "fat_g": 0.1
    },
    {
        "name_fa": "کلم قرمز خردشده",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 31.0,
        "protein_g": 1.4,
        "carbs_g": 7.4,
        "fat_g": 0.2
    },
    {
        "name_fa": "گل کلم پخته / بخارپز",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 25.0,
        "protein_g": 1.9,
        "carbs_g": 5.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "ساقه کرفس خام",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 16.0,
        "protein_g": 0.7,
        "carbs_g": 3.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "لوبیا سبز پخته",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 35.0,
        "protein_g": 1.9,
        "carbs_g": 7.9,
        "fat_g": 0.3
    },
    {
        "name_fa": "سبزی خوردن تازه (تره، تربچه، ریحان، شاهی)",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 20.0,
        "protein_g": 2.0,
        "carbs_g": 3.5,
        "fat_g": 0.3
    },
    {
        "name_fa": "پیاز خام متوسط",
        "category": "fruits",
        "unit": "۱ عدد (۱۰۰ گرم)",
        "calories": 40.0,
        "protein_g": 1.1,
        "carbs_g": 9.3,
        "fat_g": 0.1
    },
    {
        "name_fa": "سیر تازه خام",
        "category": "fruits",
        "unit": "۱ حبه (۳ گرم)",
        "calories": 4.0,
        "protein_g": 0.2,
        "carbs_g": 1.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "چغندر قرمز پخته / لبو",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 44.0,
        "protein_g": 1.7,
        "carbs_g": 10.0,
        "fat_g": 0.2
    },
    {
        "name_fa": "کدو تنبل پخته",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 26.0,
        "protein_g": 1.0,
        "carbs_g": 6.5,
        "fat_g": 0.1
    },
    {
        "name_fa": "جوانه گندم تازه",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 198.0,
        "protein_g": 7.5,
        "carbs_g": 43.0,
        "fat_g": 1.3
    },
    {
        "name_fa": "جوانه ماش تازه",
        "category": "fruits",
        "unit": "100 گرم",
        "calories": 30.0,
        "protein_g": 3.0,
        "carbs_g": 6.0,
        "fat_g": 0.2
    },

    # =========================================================================
    # 6. NUTS (مغزها، دانه‌ها و چربی‌های مفید)
    # =========================================================================
    # مغزها و دانه‌ها
    {
        "name_fa": "مغز گردو (۶ عدد مغز کامل)",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 196.0,
        "protein_g": 4.5,
        "carbs_g": 4.1,
        "fat_g": 19.6
    },
    {
        "name_fa": "مغز بادام درختی خام (۲۴ عدد)",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 173.0,
        "protein_g": 6.3,
        "carbs_g": 6.1,
        "fat_g": 15.0
    },
    {
        "name_fa": "مغز بادام درختی بو داده",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 178.0,
        "protein_g": 6.0,
        "carbs_g": 6.0,
        "fat_g": 15.5
    },
    {
        "name_fa": "مغز پسته خام / شور",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 168.0,
        "protein_g": 6.0,
        "carbs_g": 8.5,
        "fat_g": 13.5
    },
    {
        "name_fa": "مغز بادام هندی خام",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 165.0,
        "protein_g": 5.5,
        "carbs_g": 9.0,
        "fat_g": 13.0
    },
    {
        "name_fa": "مغز فندق خام",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 188.0,
        "protein_g": 4.5,
        "carbs_g": 5.0,
        "fat_g": 18.2
    },
    {
        "name_fa": "مغز بادام زمینی بو داده",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 170.0,
        "protein_g": 7.5,
        "carbs_g": 4.8,
        "fat_g": 14.8
    },
    {
        "name_fa": "مغز تخمه آفتابگردان",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 175.0,
        "protein_g": 6.2,
        "carbs_g": 6.0,
        "fat_g": 15.4
    },
    {
        "name_fa": "مغز تخمه کدو تنبل",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 160.0,
        "protein_g": 8.5,
        "carbs_g": 4.2,
        "fat_g": 13.0
    },
    {
        "name_fa": "دانه کنجد خام",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۰ گرم)",
        "calories": 57.0,
        "protein_g": 1.8,
        "carbs_g": 2.3,
        "fat_g": 5.0
    },
    {
        "name_fa": "تخم کتان آسیاب‌شده",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۰ گرم)",
        "calories": 53.0,
        "protein_g": 1.9,
        "carbs_g": 3.0,
        "fat_g": 4.2
    },
    {
        "name_fa": "شاهدانه بو داده",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 165.0,
        "protein_g": 9.5,
        "carbs_g": 2.5,
        "fat_g": 14.5
    },

    # کره‌ها و ارده
    {
        "name_fa": "کره بادام زمینی خالص بدون شکر",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۶ گرم)",
        "calories": 95.0,
        "protein_g": 4.0,
        "carbs_g": 3.1,
        "fat_g": 8.1
    },
    {
        "name_fa": "کره بادام زمینی استاندارد",
        "category": "nuts",
        "unit": "100 گرم",
        "calories": 588.0,
        "protein_g": 25.0,
        "carbs_g": 20.0,
        "fat_g": 50.0
    },
    {
        "name_fa": "کره بادام درختی خالص",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۶ گرم)",
        "calories": 98.0,
        "protein_g": 3.4,
        "carbs_g": 3.0,
        "fat_g": 8.9
    },
    {
        "name_fa": "کره پسته خالص",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۶ گرم)",
        "calories": 94.0,
        "protein_g": 3.2,
        "carbs_g": 4.5,
        "fat_g": 7.8
    },
    {
        "name_fa": "ارده کنجد خالص",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۵ گرم)",
        "calories": 89.0,
        "protein_g": 2.6,
        "carbs_g": 3.2,
        "fat_g": 8.0
    },
    {
        "name_fa": "ارده کنجد خالص (100 گرم)",
        "category": "nuts",
        "unit": "100 گرم",
        "calories": 595.0,
        "protein_g": 17.0,
        "carbs_g": 21.0,
        "fat_g": 54.0
    },

    # روغن‌ها و چربی‌های گیاهی
    {
        "name_fa": "روغن زیتون فرابکر",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۴ گرم)",
        "calories": 119.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 13.5
    },
    {
        "name_fa": "روغن زیتون (100 گرم)",
        "category": "nuts",
        "unit": "100 گرم",
        "calories": 884.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 100.0
    },
    {
        "name_fa": "روغن کنجد تصفیه‌شده",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۴ گرم)",
        "calories": 120.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 13.6
    },
    {
        "name_fa": "روغن کلزا / کانولا",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۴ گرم)",
        "calories": 124.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 14.0
    },
    {
        "name_fa": "روغن نارگیل خوراکی",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۴ گرم)",
        "calories": 121.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 13.5
    },
    {
        "name_fa": "روغن بذر کتان",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۱۴ گرم)",
        "calories": 120.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 13.6
    },
    {
        "name_fa": "آووکادو تازه",
        "category": "nuts",
        "unit": "۱ عدد متوسط (۱۵۰ گرم)",
        "calories": 240.0,
        "protein_g": 3.0,
        "carbs_g": 12.8,
        "fat_g": 22.0
    },
    {
        "name_fa": "آووکادو خردشده",
        "category": "nuts",
        "unit": "100 گرم",
        "calories": 160.0,
        "protein_g": 2.0,
        "carbs_g": 8.5,
        "fat_g": 14.7
    },
    {
        "name_fa": "زیتون سبز شور",
        "category": "nuts",
        "unit": "۵ عدد متوسط (۲۰ گرم)",
        "calories": 29.0,
        "protein_g": 0.2,
        "carbs_g": 0.8,
        "fat_g": 3.0
    },
    {
        "name_fa": "زیتون سیاه شور",
        "category": "nuts",
        "unit": "۵ عدد متوسط (۲۰ گرم)",
        "calories": 23.0,
        "protein_g": 0.2,
        "carbs_g": 1.2,
        "fat_g": 2.2
    },
    {
        "name_fa": "زیتون پرورده سنتی",
        "category": "nuts",
        "unit": "۱ قاشق غذاخوری (۲۰ گرم)",
        "calories": 65.0,
        "protein_g": 1.0,
        "carbs_g": 3.5,
        "fat_g": 5.5
    },
    {
        "name_fa": "شکلات تلخ ۸۵٪ به بالا",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 170.0,
        "protein_g": 3.0,
        "carbs_g": 11.0,
        "fat_g": 14.0
    },
    {
        "name_fa": "شکلات تلخ ۷۰٪",
        "category": "nuts",
        "unit": "۳۰ گرم",
        "calories": 175.0,
        "protein_g": 2.5,
        "carbs_g": 14.0,
        "fat_g": 12.5
    },

    # =========================================================================
    # 7. SUPPLEMENTS (مکمل‌های تخصصی ورزشی و فیتنس)
    # =========================================================================
    # پروتئین‌ها
    {
        "name_fa": "مکمل پروتئین وی ۱۰۰٪ (ایزوله)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 115.0,
        "protein_g": 27.0,
        "carbs_g": 1.0,
        "fat_g": 0.5
    },
    {
        "name_fa": "مکمل پروتئین وی ۱۰۰٪ (کنسانتره)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 120.0,
        "protein_g": 24.0,
        "carbs_g": 3.0,
        "fat_g": 1.8
    },
    {
        "name_fa": "مکمل پروتئین وی هیدرولیزه (Hydro)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 116.0,
        "protein_g": 27.5,
        "carbs_g": 0.8,
        "fat_g": 0.5
    },
    {
        "name_fa": "مکمل پروتئین کازئین (دیرجذب شبانه)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 118.0,
        "protein_g": 24.0,
        "carbs_g": 1.5,
        "fat_g": 1.0
    },
    {
        "name_fa": "مکمل پروتئین گیاهی (نخود و برنج)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 120.0,
        "protein_g": 24.0,
        "carbs_g": 2.5,
        "fat_g": 1.5
    },
    {
        "name_fa": "مکمل پروتئین بیف / گوشت",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 115.0,
        "protein_g": 26.0,
        "carbs_g": 0.5,
        "fat_g": 0.5
    },
    {
        "name_fa": "پودر سفیده تخم‌مرغ آلبومین ورزشی",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 110.0,
        "protein_g": 24.5,
        "carbs_g": 1.5,
        "fat_g": 0.3
    },

    # کربوهیدرات‌ها و گینرها
    {
        "name_fa": "مکمل گینر افزایش وزن (مس گینر)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۵۰ گرم)",
        "calories": 190.0,
        "protein_g": 15.0,
        "carbs_g": 30.0,
        "fat_g": 1.5
    },
    {
        "name_fa": "مکمل گینر افزایش وزن (سروینگ کامل)",
        "category": "supplements",
        "unit": "۱۰۰ گرم",
        "calories": 380.0,
        "protein_g": 30.0,
        "carbs_g": 60.0,
        "fat_g": 3.0
    },
    {
        "name_fa": "پودر کربوهیدرات ورزشی / مالتودکسترین",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 114.0,
        "protein_g": 0.0,
        "carbs_g": 28.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "پودر کربوهیدرات و الکترولیت ورزشی",
        "category": "supplements",
        "unit": "۱ پیمانه (۳۰ گرم)",
        "calories": 110.0,
        "protein_g": 0.0,
        "carbs_g": 27.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "کرم برنج پودری ورزشی (Cream of Rice)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۵۰ گرم)",
        "calories": 185.0,
        "protein_g": 3.5,
        "carbs_g": 40.0,
        "fat_g": 0.5
    },
    {
        "name_fa": "پودر نشاسته ذرت مومی (Waxy Maize)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 112.0,
        "protein_g": 0.0,
        "carbs_g": 28.0,
        "fat_g": 0.0
    },

    # آمینو اسیدها و ریکاوری
    {
        "name_fa": "مکمل کراتین مونوهیدرات میکرونایز",
        "category": "supplements",
        "unit": "۱ اسکوپ (۵ گرم)",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل ال گلوتامین ورزشی",
        "category": "supplements",
        "unit": "۱ اسکوپ (۵ گرم)",
        "calories": 20.0,
        "protein_g": 5.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل بی سی ای ای پودری (BCAA)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۷ گرم)",
        "calories": 25.0,
        "protein_g": 6.0,
        "carbs_g": 0.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل آمینو اسید ضروری (EAA)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۱۰ گرم)",
        "calories": 35.0,
        "protein_g": 8.5,
        "carbs_g": 0.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "قرص آمینو اسید شاخه‌ای (BCAA)",
        "category": "supplements",
        "unit": "۴ عدد قرص",
        "calories": 20.0,
        "protein_g": 5.0,
        "carbs_g": 0.2,
        "fat_g": 0.1
    },
    {
        "name_fa": "مکمل بتا آلانین خالص",
        "category": "supplements",
        "unit": "۱ پیمانه (۳ گرم)",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل ال سیترولین مالات",
        "category": "supplements",
        "unit": "۱ پیمانه (۵ گرم)",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل ال آرژنین پودری / کپسولی",
        "category": "supplements",
        "unit": "۱ پیمانه (۳ گرم)",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل اچ ام بی (HMB)",
        "category": "supplements",
        "unit": "۱ پیمانه (۳ گرم)",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "مکمل تائورین خالص",
        "category": "supplements",
        "unit": "۱ پیمانه (۲ گرم)",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },

    # مکمل‌های قبل تمرین و انرژی‌زا
    {
        "name_fa": "مکمل قبل تمرین و پمپ (Pre-Workout)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۱۰ گرم)",
        "calories": 15.0,
        "protein_g": 1.0,
        "carbs_g": 2.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "پودر الکترولیت و هیدراتاسیون ورزشی",
        "category": "supplements",
        "unit": "۱ ساشه (۸ گرم)",
        "calories": 18.0,
        "protein_g": 0.0,
        "carbs_g": 4.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "ویال ال کارنیتین مایع ۱۰۰۰ میلی‌گرم",
        "category": "supplements",
        "unit": "۱ ویال (۱۰ میلی‌لیتر)",
        "calories": 5.0,
        "protein_g": 0.0,
        "carbs_g": 1.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "ویال ال کارنیتین مایع ۳۰۰۰ میلی‌گرم",
        "category": "supplements",
        "unit": "۱ ویال (۲۵ میلی‌لیتر)",
        "calories": 12.0,
        "protein_g": 0.0,
        "carbs_g": 2.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "قرص کافئین خالص ۲۰۰ میلی‌گرم",
        "category": "supplements",
        "unit": "۱ عدد",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "نوشابه انرژی‌زا ورزشی بدون قند (Zero)",
        "category": "supplements",
        "unit": "۱ قوطی (۲۵۰ میلی‌لیتر)",
        "calories": 5.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "نوشابه ایزوتونیک ورزشی",
        "category": "supplements",
        "unit": "۱ بطری (۵۰۰ میلی‌لیتر)",
        "calories": 120.0,
        "protein_g": 0.0,
        "carbs_g": 30.0,
        "fat_g": 0.0
    },

    # بارهای پروتئینی و میان‌وعده‌های فیتنسی
    {
        "name_fa": "پروتئین بار کم‌شکر شکلاتی",
        "category": "supplements",
        "unit": "۱ عدد (۴۵ گرم)",
        "calories": 165.0,
        "protein_g": 15.0,
        "carbs_g": 14.0,
        "fat_g": 5.5
    },
    {
        "name_fa": "پروتئین بار حرفه‌ای ۳۰٪ ورزشی",
        "category": "supplements",
        "unit": "۱ عدد (۶۰ گرم)",
        "calories": 220.0,
        "protein_g": 20.0,
        "carbs_g": 22.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "پروتئین بار کتوژنیک کم‌کربوهیدرات",
        "category": "supplements",
        "unit": "۱ عدد (۵۰ گرم)",
        "calories": 210.0,
        "protein_g": 14.0,
        "carbs_g": 4.0,
        "fat_g": 15.0
    },
    {
        "name_fa": "جو دو سر بار ورزشی (Flapjack)",
        "category": "supplements",
        "unit": "۱ عدد (۶۰ گرم)",
        "calories": 245.0,
        "protein_g": 6.0,
        "carbs_g": 38.0,
        "fat_g": 8.5
    },
    {
        "name_fa": "انرژی بار میوه‌ای طبیعی",
        "category": "supplements",
        "unit": "۱ عدد (۴۰ گرم)",
        "calories": 140.0,
        "protein_g": 3.0,
        "carbs_g": 26.0,
        "fat_g": 2.5
    },
    {
        "name_fa": "ژل انرژی‌زای ورزشی استقامتی",
        "category": "supplements",
        "unit": "۱ ساشه (۳۵ گرم)",
        "calories": 90.0,
        "protein_g": 0.0,
        "carbs_g": 22.0,
        "fat_g": 0.0
    },
    # اقلام تکمیلی پروتئینی و ماکیان
    {
        "name_fa": "گوشت کبک پخته",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 160.0,
        "protein_g": 25.0,
        "carbs_g": 0.0,
        "fat_g": 6.0
    },
    {
        "name_fa": "فیله اردک پخته بدون پوست",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 200.0,
        "protein_g": 24.0,
        "carbs_g": 0.0,
        "fat_g": 11.0
    },
    {
        "name_fa": "کوفته تبریزی سنتی کم‌چرب",
        "category": "meat",
        "unit": "۱ عدد (۱۲۰ گرم)",
        "calories": 220.0,
        "protein_g": 16.0,
        "carbs_g": 14.0,
        "fat_g": 11.0
    },
    {
        "name_fa": "کتلت گوشت خانگی کم‌روغن",
        "category": "meat",
        "unit": "۱ عدد (۵۰ گرم)",
        "calories": 110.0,
        "protein_g": 7.5,
        "carbs_g": 7.0,
        "fat_g": 5.5
    },
    {
        "name_fa": "شامی کباب سنتی",
        "category": "meat",
        "unit": "۱ عدد (۵۰ گرم)",
        "calories": 105.0,
        "protein_g": 8.0,
        "carbs_g": 6.0,
        "fat_g": 5.0
    },
    {
        "name_fa": "خوراک زبان گوساله با سس قارچ",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 240.0,
        "protein_g": 19.0,
        "carbs_g": 3.0,
        "fat_g": 17.0
    },
    {
        "name_fa": "قلیه ماهی جنوبی با تمر هندی",
        "category": "meat",
        "unit": "۱ کاسه (۲۰۰ گرم)",
        "calories": 210.0,
        "protein_g": 22.0,
        "carbs_g": 6.0,
        "fat_g": 11.0
    },
    {
        "name_fa": "میگو سوخاری ترد",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 240.0,
        "protein_g": 18.0,
        "carbs_g": 16.0,
        "fat_g": 11.5
    },
    {
        "name_fa": "فیله سالمون دودی",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 170.0,
        "protein_g": 21.0,
        "carbs_g": 0.0,
        "fat_g": 9.0
    },
    {
        "name_fa": "سوسیس هات‌داگ گوشت ۸۰٪",
        "category": "meat",
        "unit": "۱ عدد (۷۰ گرم)",
        "calories": 195.0,
        "protein_g": 9.5,
        "carbs_g": 3.5,
        "fat_g": 16.0
    },
    {
        "name_fa": "کالباس و ژامبون مرغ ۹۰٪",
        "category": "meat",
        "unit": "۱ ورق (۲۰ گرم)",
        "calories": 26.0,
        "protein_g": 4.2,
        "carbs_g": 0.6,
        "fat_g": 0.8
    },
    {
        "name_fa": "ژامبون گوشت بوقلمون ۹۰٪",
        "category": "meat",
        "unit": "۱ ورق (۲۰ گرم)",
        "calories": 24.0,
        "protein_g": 4.5,
        "carbs_g": 0.5,
        "fat_g": 0.5
    },
    {
        "name_fa": "بیف استروگانف با گوشت راسته گوساله",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 180.0,
        "protein_g": 18.0,
        "carbs_g": 4.0,
        "fat_g": 10.0
    },
    {
        "name_fa": "چیکن استروگانف با فیله مرغ و قارچ",
        "category": "meat",
        "unit": "100 گرم",
        "calories": 160.0,
        "protein_g": 20.0,
        "carbs_g": 4.0,
        "fat_g": 7.0
    },
    # اقلام تکمیلی کربوهیدرات و پلوها
    {
        "name_fa": "ته‌چین مرغ سنتی کم‌روغن",
        "category": "rice",
        "unit": "۱ برش (۱۵۰ گرم)",
        "calories": 310.0,
        "protein_g": 18.0,
        "carbs_g": 38.0,
        "fat_g": 9.5
    },
    {
        "name_fa": "ته‌چین گوشت سنتی",
        "category": "rice",
        "unit": "۱ برش (۱۵۰ گرم)",
        "calories": 340.0,
        "protein_g": 19.0,
        "carbs_g": 38.0,
        "fat_g": 13.0
    },
    {
        "name_fa": "کلم‌پلو شیرازی با گوشت قلقلی",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 270.0,
        "protein_g": 10.0,
        "carbs_g": 42.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "ماش‌پلو سنتی با شوید",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 260.0,
        "protein_g": 8.5,
        "carbs_g": 48.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "پلو مکزیکی تند با ذرت و فلفل دلمه‌ای",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 245.0,
        "protein_g": 5.5,
        "carbs_g": 47.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "سبزی‌پلو سنتی با سیر و شوید تازه",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 235.0,
        "protein_g": 4.5,
        "carbs_g": 46.0,
        "fat_g": 3.5
    },
    {
        "name_fa": "رشته‌پلو سنتی با کشمش و خرما",
        "category": "rice",
        "unit": "۱ کفگیر (۱۶۰ گرم)",
        "calories": 280.0,
        "protein_g": 6.5,
        "carbs_g": 54.0,
        "fat_g": 4.0
    },
    {
        "name_fa": "آش رشته سنتی با پیازداغ و کشک",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 330.0,
        "protein_g": 12.0,
        "carbs_g": 52.0,
        "fat_g": 8.5
    },
    {
        "name_fa": "آش جو سنتی پرکشک",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 280.0,
        "protein_g": 11.0,
        "carbs_g": 46.0,
        "fat_g": 5.5
    },
    {
        "name_fa": "آش شله‌قلمکار سنتی با گوشت",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 320.0,
        "protein_g": 16.0,
        "carbs_g": 44.0,
        "fat_g": 8.5
    },
    {
        "name_fa": "سوپ شیر و خامه و قارچ",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 210.0,
        "protein_g": 7.5,
        "carbs_g": 18.0,
        "fat_g": 12.0
    },
    {
        "name_fa": "سوپ سبزیجات رژیمی و اسفناج",
        "category": "rice",
        "unit": "۱ کاسه (۲۵۰ گرم)",
        "calories": 85.0,
        "protein_g": 3.5,
        "carbs_g": 16.0,
        "fat_g": 0.8
    },
    {
        "name_fa": "کوکوسبزی خانگی کم‌روغن",
        "category": "rice",
        "unit": "۱ برش (۷۰ گرم)",
        "calories": 125.0,
        "protein_g": 5.0,
        "carbs_g": 6.0,
        "fat_g": 9.0
    },
    {
        "name_fa": "کوکوسیب‌زمینی خانگی",
        "category": "rice",
        "unit": "۱ برش (۷۰ گرم)",
        "calories": 140.0,
        "protein_g": 4.5,
        "carbs_g": 17.0,
        "fat_g": 6.5
    },
    {
        "name_fa": "کورن‌فلکس ذرت ساده صبحانه",
        "category": "rice",
        "unit": "۳۰ گرم",
        "calories": 115.0,
        "protein_g": 2.2,
        "carbs_g": 26.0,
        "fat_g": 0.3
    },
    {
        "name_fa": "موسلی رژیمی بدون شکر افزوده",
        "category": "rice",
        "unit": "۴۰ گرم",
        "calories": 150.0,
        "protein_g": 4.5,
        "carbs_g": 27.0,
        "fat_g": 2.8
    },
    {
        "name_fa": "گرانولا با عسل و مغز بادام",
        "category": "rice",
        "unit": "۴۰ گرم",
        "calories": 180.0,
        "protein_g": 4.0,
        "carbs_g": 28.0,
        "fat_g": 6.0
    },
    # اقلام تکمیلی لبنیات
    {
        "name_fa": "ماست پروتئینی وی‌پرو میوه‌ای کاله",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 75.0,
        "protein_g": 9.0,
        "carbs_g": 7.5,
        "fat_g": 0.5
    },
    {
        "name_fa": "ماست پروبیوتیک کم‌چرب",
        "category": "dairy",
        "unit": "100 گرم",
        "calories": 58.0,
        "protein_g": 4.5,
        "carbs_g": 5.5,
        "fat_g": 1.5
    },
    {
        "name_fa": "پنیر موزارلا قالبی رنده‌شده",
        "category": "dairy",
        "unit": "۳۰ گرم",
        "calories": 85.0,
        "protein_g": 6.5,
        "carbs_g": 0.8,
        "fat_g": 6.5
    },
    {
        "name_fa": "پنیر گودا هلندی ورقی",
        "category": "dairy",
        "unit": "۱ ورق (۲۰ گرم)",
        "calories": 75.0,
        "protein_g": 5.0,
        "carbs_g": 0.5,
        "fat_g": 6.0
    },
    # اقلام تکمیلی مکمل‌های ورزشی
    {
        "name_fa": "مکمل پروتئین ایزوله سویا ورزشی",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 112.0,
        "protein_g": 26.0,
        "carbs_g": 0.5,
        "fat_g": 0.8
    },
    {
        "name_fa": "مکمل کراتین کپسولی کری آلکالین",
        "category": "supplements",
        "unit": "۲ کپسول",
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "پودر نشاسته ویتارگو ورزشی (Vitargo)",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۵ گرم)",
        "calories": 130.0,
        "protein_g": 0.0,
        "carbs_g": 32.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "کپسول امگا ۳ غلیظ روغن ماهی",
        "category": "supplements",
        "unit": "۱ کپسول (۱۰۰۰ میلی‌گرم)",
        "calories": 10.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 1.0
    },
    {
        "name_fa": "قرص جوشان مولتی‌ویتامین و مینرال",
        "category": "supplements",
        "unit": "۱ عدد",
        "calories": 8.0,
        "protein_g": 0.0,
        "carbs_g": 1.5,
        "fat_g": 0.0
    },
    {
        "name_fa": "نوشابه پروتئینی بدون گاز ورزشی",
        "category": "supplements",
        "unit": "۱ بطری (۵۰۰ میلی‌لیتر)",
        "calories": 120.0,
        "protein_g": 30.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
    },
    {
        "name_fa": "پودر آب پنیر سنتی غنی‌شده",
        "category": "supplements",
        "unit": "۱ اسکوپ (۳۰ گرم)",
        "calories": 115.0,
        "protein_g": 20.0,
        "carbs_g": 5.0,
        "fat_g": 1.5
    }
]

def main():
    target_path = Path(__file__).resolve().parent.parent / "resources" / "data" / "foods_database.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Validation
    valid_categories = {"meat", "rice", "legumes", "dairy", "fruits", "nuts", "supplements"}
    seen_names = set()
    for item in foods:
        name = item["name_fa"].strip()
        cat = item["category"]
        assert cat in valid_categories, f"Invalid category: {cat} in {name}"
        assert name not in seen_names, f"Duplicate name: {name}"
        seen_names.add(name)
        assert item["calories"] >= 0
        assert item["protein_g"] >= 0
        assert item["carbs_g"] >= 0
        assert item["fat_g"] >= 0

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(foods, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {len(foods)} food records at {target_path}")

if __name__ == "__main__":
    main()
