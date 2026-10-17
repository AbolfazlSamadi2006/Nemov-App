import pathlib
import sys

def main():
    p = pathlib.Path('yalda_cloud_server/cloudflare_worker/index.js')
    content = p.read_text(encoding='utf-8')
    initial_len = len(content)

    # 1. Update ETag
    old_etag = 'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.0-nemov-3d-marquee"\';'
    new_etag = 'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.1-nemov-3d-polish"\';'
    if old_etag not in content:
        print("ERROR: old_etag not found")
        sys.exit(1)
    content = content.replace(old_etag, new_etag, 1)

    # 2. Add 3D Spinning Logo CSS and update Hero Mockup & 4 Floating Widgets CSS
    old_mockup_css = """        /* Top Scroll Progress Bar */
        .scroll-progress-bar {
            position: fixed;
            top: 0;
            right: 0;
            height: 3.5px;
            width: 0%;
            background: linear-gradient(90deg, #FCA5A5 0%, #EF4444 40%, #DC2626 70%, #991B1B 100%);
            z-index: 9999;
            box-shadow: 0 0 14px rgba(239, 68, 68, 0.8), 0 0 4px rgba(252, 165, 165, 0.6);
            transition: width 0.08s ease-out;
            pointer-events: none;
        }

        /* 3D Perspective App Mockup in Hero */
        .hero-mockup-container {
            perspective: 1200px;
            max-width: 980px;
            margin: 36px auto 44px;
            position: relative;
            padding: 10px;
            width: 100%;
        }"""

    new_mockup_css = """        /* Top Scroll Progress Bar */
        .scroll-progress-bar {
            position: fixed;
            top: 0;
            right: 0;
            height: 3.5px;
            width: 0%;
            background: linear-gradient(90deg, #FCA5A5 0%, #EF4444 40%, #DC2626 70%, #991B1B 100%);
            z-index: 9999;
            box-shadow: 0 0 14px rgba(239, 68, 68, 0.8), 0 0 4px rgba(252, 165, 165, 0.6);
            transition: width 0.08s ease-out;
            pointer-events: none;
        }

        /* 3D Continuous Rotating Nemov Logo (Strictly Never Stops on Hover) */
        .hero-logo-3d-wrapper {
            perspective: 800px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            width: 82px;
            height: 82px;
            position: relative;
        }

        .hero-logo-3d {
            width: 76px;
            height: 76px;
            object-fit: contain;
            transform-style: preserve-3d;
            animation: rotateLogo3D 8s linear infinite !important;
            filter: drop-shadow(0 0 18px rgba(220, 38, 38, 0.55));
            will-change: transform;
            cursor: pointer;
        }

        .hero-logo-3d:hover {
            animation-play-state: running !important;
            filter: drop-shadow(0 0 28px rgba(239, 68, 68, 0.85));
        }

        @keyframes rotateLogo3D {
            0% {
                transform: perspective(800px) rotateY(0deg);
            }
            100% {
                transform: perspective(800px) rotateY(360deg);
            }
        }

        /* 3D Perspective App Mockup in Hero */
        .hero-mockup-container {
            perspective: 1200px;
            max-width: 840px;
            margin: 36px auto 44px;
            position: relative;
            padding: 10px;
            width: 100%;
        }"""

    if old_mockup_css not in content:
        print("ERROR: old_mockup_css not found")
        sys.exit(1)
    content = content.replace(old_mockup_css, new_mockup_css, 1)

    # 3. Update Floating Glass Widgets CSS (Positioned completely outside window frame)
    old_floating_css = """        /* Floating Glass Widgets with Blur Effect */
        .floating-glass-widget {
            position: absolute;
            z-index: 25;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 11px 18px;
            border-radius: 14px;
            background: rgba(22, 28, 42, 0.94);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1.5px solid rgba(239, 68, 68, 0.55);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.75), 0 0 25px rgba(220, 38, 38, 0.35);
            transform: translateZ(40px);
            pointer-events: none;
            text-align: right;
            white-space: nowrap;
        }

        .widget-icon-glow {
            font-size: 20px;
            flex-shrink: 0;
        }

        .widget-headline {
            display: block;
            font-size: 13px;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.25;
        }

        .widget-subline {
            display: block;
            font-size: 11px;
            color: #CBD5E1;
        }

        .widget-bmr {
            top: -18px;
            right: 20px;
            animation: floatWidget1 5s ease-in-out infinite alternate;
        }

        .widget-cloud {
            top: 30px;
            left: -20px;
            animation: floatWidget2 6s ease-in-out infinite alternate;
        }

        .widget-pdf {
            bottom: -15px;
            left: 40px;
            animation: floatWidget3 5.5s ease-in-out infinite alternate;
        }

        @keyframes floatWidget1 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(-8px); }
        }

        @keyframes floatWidget2 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(10px); }
        }

        @keyframes floatWidget3 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(-7px); }
        }"""

    new_floating_css = """        /* Floating Glass Widgets with Blur Effect (Strictly Outside Window Frame) */
        .floating-glass-widget {
            position: absolute;
            z-index: 25;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 11px 18px;
            border-radius: 14px;
            background: rgba(22, 28, 42, 0.94);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1.5px solid rgba(239, 68, 68, 0.55);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.75), 0 0 25px rgba(220, 38, 38, 0.35);
            transform: translateZ(40px);
            pointer-events: none;
            text-align: right;
            white-space: nowrap;
            box-sizing: border-box;
        }

        .widget-icon-glow {
            font-size: 20px;
            flex-shrink: 0;
        }

        .widget-headline {
            display: block;
            font-size: 13px;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.25;
        }

        .widget-subline {
            display: block;
            font-size: 11px;
            color: #CBD5E1;
        }

        /* Desktop Coordinates (> 1340px): Completely outside the mockup window frame */
        .widget-bmr {
            top: 25px;
            left: calc(100% + 24px);
            right: auto;
            bottom: auto;
            animation: floatWidget1 5s ease-in-out infinite alternate;
        }

        .widget-sms {
            bottom: 25px;
            left: calc(100% + 24px);
            right: auto;
            top: auto;
            animation: floatWidget2 5.5s ease-in-out infinite alternate;
        }

        .widget-cloud {
            top: 25px;
            right: calc(100% + 24px);
            left: auto;
            bottom: auto;
            animation: floatWidget3 6s ease-in-out infinite alternate;
        }

        .widget-pdf {
            bottom: 25px;
            right: calc(100% + 24px);
            left: auto;
            top: auto;
            animation: floatWidget4 5.2s ease-in-out infinite alternate;
        }

        @keyframes floatWidget1 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(-8px); }
        }

        @keyframes floatWidget2 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(8px); }
        }

        @keyframes floatWidget3 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(9px); }
        }

        @keyframes floatWidget4 {
            0% { transform: translateZ(40px) translateY(0); }
            100% { transform: translateZ(40px) translateY(-7px); }
        }

        /* Responsive Breakpoint for Medium Screens (769px to 1340px):
           Dock 2 above the window frame and 2 below the window frame (100% outside) */
        @media (max-width: 1340px) and (min-width: 769px) {
            .widget-bmr {
                bottom: calc(100% + 14px);
                right: 20px;
                top: auto;
                left: auto;
            }
            .widget-cloud {
                bottom: calc(100% + 14px);
                left: 20px;
                top: auto;
                right: auto;
            }
            .widget-sms {
                top: calc(100% + 14px);
                right: 20px;
                bottom: auto;
                left: auto;
            }
            .widget-pdf {
                top: calc(100% + 14px);
                left: 20px;
                bottom: auto;
                right: auto;
            }
        }"""

    if old_floating_css not in content:
        print("ERROR: old_floating_css not found")
        sys.exit(1)
    content = content.replace(old_floating_css, new_floating_css, 1)

    # 4. Update Marquee CSS: Guarantee zero overlap and exact gap matching
    old_marquee_css = """        .marquee-track {
            display: flex;
            gap: 16px;
            width: max-content;
            will-change: transform;
            animation: marqueeScroll 45s linear infinite;
        }

        .marquee-section:hover .marquee-track {
            animation-play-state: paused;
        }

        @keyframes marqueeScroll {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-50%, 0, 0); }
        }

        .marquee-group {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-shrink: 0;
        }

        .marquee-card {
            direction: rtl;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            padding: 12px 20px;
            border-radius: 16px;
            background: rgba(22, 28, 42, 0.75);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            white-space: nowrap;
            flex-shrink: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            cursor: default;
        }"""

    new_marquee_css = """        .marquee-track {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 0 !important;
            width: max-content !important;
            min-width: max-content !important;
            will-change: transform;
            animation: marqueeScroll 45s linear infinite;
        }

        .marquee-section:hover .marquee-track {
            animation-play-state: paused;
        }

        @keyframes marqueeScroll {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-50%, 0, 0); }
        }

        .marquee-group {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 16px !important;
            padding-right: 16px !important;
            flex: 0 0 auto !important;
            min-width: max-content !important;
            box-sizing: border-box !important;
        }

        .marquee-card {
            direction: rtl;
            display: inline-flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 12px !important;
            padding: 12px 20px !important;
            border-radius: 16px !important;
            background: rgba(22, 28, 42, 0.75);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            white-space: nowrap !important;
            flex: 0 0 auto !important;
            min-width: max-content !important;
            margin: 0 !important;
            box-sizing: border-box !important;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            cursor: default;
        }"""

    if old_marquee_css not in content:
        print("ERROR: old_marquee_css not found")
        sys.exit(1)
    content = content.replace(old_marquee_css, new_marquee_css, 1)

    # 5. Update Card CSS definitions for tilt: position relative, overflow hidden, transform-style preserve-3d
    old_hl_css = """.highlight-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 18px 16px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            transition: all 0.25s ease;
        }"""
    new_hl_css = """.highlight-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 18px 16px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            position: relative;
            overflow: hidden;
            transform-style: preserve-3d;
            transition: all 0.25s ease;
        }"""
    if old_hl_css not in content:
        print("ERROR: old_hl_css not found")
        sys.exit(1)
    content = content.replace(old_hl_css, new_hl_css, 1)

    old_sec_css = """.security-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 24px 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            transition: all 0.25s ease;
        }"""
    new_sec_css = """.security-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 24px 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            position: relative;
            overflow: hidden;
            transform-style: preserve-3d;
            transition: all 0.25s ease;
        }"""
    if old_sec_css not in content:
        print("ERROR: old_sec_css not found")
        sys.exit(1)
    content = content.replace(old_sec_css, new_sec_css, 1)

    old_dev_css = """.developer-card {
            background: linear-gradient(145deg, rgba(22, 26, 36, 0.9) 0%, rgba(14, 16, 24, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 32px 24px;
            max-width: 820px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
            position: relative;
            width: 100%;
        }"""
    new_dev_css = """.developer-card {
            background: linear-gradient(145deg, rgba(22, 26, 36, 0.9) 0%, rgba(14, 16, 24, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 32px 24px;
            max-width: 820px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
            position: relative;
            overflow: hidden;
            transform-style: preserve-3d;
            width: 100%;
        }"""
    if old_dev_css not in content:
        print("ERROR: old_dev_css not found")
        sys.exit(1)
    content = content.replace(old_dev_css, new_dev_css, 1)

    old_join_css = """.gym-join-card {
            background: var(--bg-card);
            border: 2px dashed rgba(220, 38, 38, 0.35);
            border-radius: 20px;
            padding: 28px 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            transition: all 0.3s ease;
        }"""
    new_join_css = """.gym-join-card {
            background: var(--bg-card);
            border: 2px dashed rgba(220, 38, 38, 0.35);
            border-radius: 20px;
            padding: 28px 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            position: relative;
            overflow: hidden;
            transform-style: preserve-3d;
            transition: all 0.3s ease;
        }"""
    if old_join_css not in content:
        print("ERROR: old_join_css not found")
        sys.exit(1)
    content = content.replace(old_join_css, new_join_css, 1)

    # 6. Add 3D spinning logo above hero-badge in HTML
    old_hero_badge = """        <section class="hero" aria-labelledby="hero-heading">
            <div class="hero-badge">"""
    new_hero_badge = """        <section class="hero" aria-labelledby="hero-heading">
            <!-- Continuous 3D Rotating Nemov Logo (Never pauses on hover) -->
            <div class="hero-logo-3d-wrapper" aria-hidden="true">
                <img src="/images/nemov_logo.png" alt="لوگوی سه‌بعدی چرخان نرم‌افزار مدیریت ورزشی نِمُو" class="hero-logo-3d" width="76" height="76">
            </div>
            <div class="hero-badge">"""
    if old_hero_badge not in content:
        print("ERROR: old_hero_badge not found")
        sys.exit(1)
    content = content.replace(old_hero_badge, new_hero_badge, 1)

    # 7. Update 4 Floating Glass Widgets in HTML (Positioned completely outside window frame)
    old_widgets_html = """            <!-- 3D Perspective App Mockup with Floating Sports Widgets -->
            <div class="hero-mockup-container">
                <div class="mockup-perspective-wrapper">
                    <!-- Floating Glass Widget 1 (Top Left) -->
                    <div class="floating-glass-widget widget-bmr" aria-hidden="true">
                        <div class="widget-icon-glow">🟢</div>
                        <div class="widget-text">
                            <span class="widget-headline">محاسبه خودکار BMR</span>
                            <span class="widget-subline">ارزیابی ترکیب بدنی و کالری</span>
                        </div>
                    </div>

                    <!-- Floating Glass Widget 2 (Top Right) -->
                    <div class="floating-glass-widget widget-cloud" aria-hidden="true">
                        <div class="widget-icon-glow">☁️</div>
                        <div class="widget-text">
                            <span class="widget-headline">همگام‌سازی ابری</span>
                            <span class="widget-subline">پشتیبان خودکار در کلودفلر</span>
                        </div>
                    </div>

                    <!-- Floating Glass Widget 3 (Bottom Left) -->
                    <div class="floating-glass-widget widget-pdf" aria-hidden="true">
                        <div class="widget-icon-glow">⚡</div>
                        <div class="widget-text">
                            <span class="widget-headline">صدور فوری PDF چاپی</span>
                            <span class="widget-subline">سربرگ اختصاصی بدون اینترنت</span>
                        </div>
                    </div>

                    <!-- Main 3D App Window Frame -->"""

    new_widgets_html = """            <!-- 3D Perspective App Mockup with Floating Sports Widgets -->
            <div class="hero-mockup-container">
                <div class="mockup-perspective-wrapper">
                    <!-- 4 Floating Glass Widgets (Strictly Outside Window Frame) -->
                    <!-- Widget 1: Top-Right Outer (BMR Calculation) -->
                    <div class="floating-glass-widget widget-bmr" aria-hidden="true">
                        <div class="widget-icon-glow">🟢</div>
                        <div class="widget-text">
                            <span class="widget-headline">محاسبه خودکار BMR</span>
                            <span class="widget-subline">ارزیابی ترکیب بدنی و کالری</span>
                        </div>
                    </div>

                    <!-- Widget 2: Bottom-Right Outer (SMS Notification System) -->
                    <div class="floating-glass-widget widget-sms" aria-hidden="true">
                        <div class="widget-icon-glow">📩</div>
                        <div class="widget-text">
                            <span class="widget-headline">سامانه پیامکی هوشمند</span>
                            <span class="widget-subline">تحویل آنی بدون بلک‌لیست</span>
                        </div>
                    </div>

                    <!-- Widget 3: Top-Left Outer (Cloud Sync & Backup) -->
                    <div class="floating-glass-widget widget-cloud" aria-hidden="true">
                        <div class="widget-icon-glow">☁️</div>
                        <div class="widget-text">
                            <span class="widget-headline">همگام‌سازی ابری</span>
                            <span class="widget-subline">پشتیبان خودکار در کلودفلر</span>
                        </div>
                    </div>

                    <!-- Widget 4: Bottom-Left Outer (Instant Offline PDF Print) -->
                    <div class="floating-glass-widget widget-pdf" aria-hidden="true">
                        <div class="widget-icon-glow">⚡</div>
                        <div class="widget-text">
                            <span class="widget-headline">صدور فوری PDF چاپی</span>
                            <span class="widget-subline">سربرگ اختصاصی بدون اینترنت</span>
                        </div>
                    </div>

                    <!-- Main 3D App Window Frame -->"""

    if old_widgets_html not in content:
        print("ERROR: old_widgets_html not found")
        sys.exit(1)
    content = content.replace(old_widgets_html, new_widgets_html, 1)

    # 8. Add glare overlays to highlights-grid cards
    old_highlights = """            <!-- Quick Highlights -->
            <div class="highlights-grid">
                <div class="highlight-card reveal-on-scroll">
                    <div class="highlight-icon">⚡</div>
                    <div class="highlight-text">
                        <h3>کارکرد ۱۰۰٪ آفلاین</h3>
                        <p>پایداری مطلق در سالن ورزشی و چاپ برنامه‌ها بدون وابستگی به اینترنت</p>
                    </div>
                </div>
                <div class="highlight-card reveal-on-scroll">
                    <div class="highlight-icon">🛡️</div>
                    <div class="highlight-text">
                        <h3>پشتیبان‌گیری ابری</h3>
                        <p>همگام‌سازی رمزنگاری‌شده با سرورهای توزیع‌شده کلودفلر در پس‌زمینه</p>
                    </div>
                </div>
                <div class="highlight-card reveal-on-scroll">
                    <div class="highlight-icon">📄</div>
                    <div class="highlight-text">
                        <h3>شناسنامه چاپی شکیل</h3>
                        <p>تولید سریع و استاندارد PDF فارسی برای ارزیابی فیزیک و برنامه‌ها</p>
                    </div>
                </div>
                <div class="highlight-card reveal-on-scroll">
                    <div class="highlight-icon">💰</div>
                    <div class="highlight-text">
                        <h3>مدیریت مالی و شهریه</h3>
                        <p>کنترل دوره‌ها، صندوق، تراز مالی و یادآوری هوشمند سررسید اعضا</p>
                    </div>
                </div>
            </div>"""

    new_highlights = """            <!-- Quick Highlights -->
            <div class="highlights-grid">
                <div class="highlight-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="highlight-icon">⚡</div>
                    <div class="highlight-text">
                        <h3>کارکرد ۱۰۰٪ آفلاین</h3>
                        <p>پایداری مطلق در سالن ورزشی و چاپ برنامه‌ها بدون وابستگی به اینترنت</p>
                    </div>
                </div>
                <div class="highlight-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="highlight-icon">🛡️</div>
                    <div class="highlight-text">
                        <h3>پشتیبان‌گیری ابری</h3>
                        <p>همگام‌سازی رمزنگاری‌شده با سرورهای توزیع‌شده کلودفلر در پس‌زمینه</p>
                    </div>
                </div>
                <div class="highlight-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="highlight-icon">📄</div>
                    <div class="highlight-text">
                        <h3>شناسنامه چاپی شکیل</h3>
                        <p>تولید سریع و استاندارد PDF فارسی برای ارزیابی فیزیک و برنامه‌ها</p>
                    </div>
                </div>
                <div class="highlight-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="highlight-icon">💰</div>
                    <div class="highlight-text">
                        <h3>مدیریت مالی و شهریه</h3>
                        <p>کنترل دوره‌ها، صندوق، تراز مالی و یادآوری هوشمند سررسید اعضا</p>
                    </div>
                </div>
            </div>"""

    if old_highlights not in content:
        print("ERROR: old_highlights not found")
        sys.exit(1)
    content = content.replace(old_highlights, new_highlights, 1)

    # 9. Add glare overlay to gym-card
    old_gym_card = """                <!-- Gym 1: Yalda Gym (باشگاه بدنسازی یلدا) -->
                <article class="gym-card reveal-on-scroll" aria-labelledby="gym-name-yalda">
                    <div class="gym-status-badge">"""
    new_gym_card = """                <!-- Gym 1: Yalda Gym (باشگاه بدنسازی یلدا) -->
                <article class="gym-card reveal-on-scroll" aria-labelledby="gym-name-yalda">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="gym-status-badge">"""
    if old_gym_card not in content:
        print("ERROR: old_gym_card not found")
        sys.exit(1)
    content = content.replace(old_gym_card, new_gym_card, 1)

    # 10. Add glare overlay to gym-join-card
    old_join_card = """                <!-- Modular Prospective Card: Join Platform -->
                <article class="gym-join-card" aria-labelledby="join-heading">
                    <div class="join-icon-box" aria-hidden="true">🏆</div>"""
    new_join_card = """                <!-- Modular Prospective Card: Join Platform -->
                <article class="gym-join-card" aria-labelledby="join-heading">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="join-icon-box" aria-hidden="true">🏆</div>"""
    if old_join_card not in content:
        print("ERROR: old_join_card not found")
        sys.exit(1)
    content = content.replace(old_join_card, new_join_card, 1)

    # 11. Add glare overlay to security-cards
    old_security = """            <div class="security-grid">
                <div class="security-card reveal-on-scroll">
                    <div class="security-icon-box" aria-hidden="true">💻</div>
                    <h3>استقلال ۱۰۰٪ از اینترنت در باشگاه</h3>
                    <p>
                        تمام فرایندهای اصلی سامانه شامل ثبت‌نام ورزشکار، ارزیابی فیزیک، طراحی برنامه و صدور PDF چاپی به صورت ۱۰۰٪ آفلاین و محلی روی سیستم باشگاه اجرا می‌شود.
                    </p>
                </div>
                <div class="security-card reveal-on-scroll">
                    <div class="security-icon-box" aria-hidden="true">🔒</div>
                    <h3>حفظ حریم خصوصی و رمزنگاری داده‌ها</h3>
                    <p>
                        پرونده‌های پزشکی، اندازه‌گیری‌های بدنی و تصاویر پیشرفت ورزشکاران روی پایگاه داده محلی ایمن و غیرقابل دسترسی توسط افراد غیرمجاز حفاظت می‌شوند.
                    </p>
                </div>
                <div class="security-card reveal-on-scroll">
                    <div class="security-icon-box" aria-hidden="true">☁️</div>
                    <h3>پشتیبان‌گیری ابری خودکار در کلودفلر</h3>
                    <p>
                        با اتصال به اینترنت، بکاپ‌های امنیتی به صورت خودکار به فضای ابری توزیع‌شده Cloudflare ارسال می‌شوند تا در صورت نقص سخت‌افزاری، اطلاعات بلافاصله بازیابی شوند.
                    </p>
                </div>
            </div>"""

    new_security = """            <div class="security-grid">
                <div class="security-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="security-icon-box" aria-hidden="true">💻</div>
                    <h3>استقلال ۱۰۰٪ از اینترنت در باشگاه</h3>
                    <p>
                        تمام فرایندهای اصلی سامانه شامل ثبت‌نام ورزشکار، ارزیابی فیزیک، طراحی برنامه و صدور PDF چاپی به صورت ۱۰۰٪ آفلاین و محلی روی سیستم باشگاه اجرا می‌شود.
                    </p>
                </div>
                <div class="security-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="security-icon-box" aria-hidden="true">🔒</div>
                    <h3>حفظ حریم خصوصی و رمزنگاری داده‌ها</h3>
                    <p>
                        پرونده‌های پزشکی، اندازه‌گیری‌های بدنی و تصاویر پیشرفت ورزشکاران روی پایگاه داده محلی ایمن و غیرقابل دسترسی توسط افراد غیرمجاز حفاظت می‌شوند.
                    </p>
                </div>
                <div class="security-card reveal-on-scroll">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="security-icon-box" aria-hidden="true">☁️</div>
                    <h3>پشتیبان‌گیری ابری خودکار در کلودفلر</h3>
                    <p>
                        با اتصال به اینترنت، بکاپ‌های امنیتی به صورت خودکار به فضای ابری توزیع‌شده Cloudflare ارسال می‌شوند تا در صورت نقص سخت‌افزاری، اطلاعات بلافاصله بازیابی شوند.
                    </p>
                </div>
            </div>"""

    if old_security not in content:
        print("ERROR: old_security not found")
        sys.exit(1)
    content = content.replace(old_security, new_security, 1)

    # 12. Add glare overlay to developer-card
    old_dev_card = """            <div class="developer-card reveal-on-scroll">
                <div class="developer-avatar-box">"""
    new_dev_card = """            <div class="developer-card reveal-on-scroll">
                <div class="tilt-glare-overlay" aria-hidden="true"></div>
                <div class="developer-avatar-box">"""
    if old_dev_card not in content:
        print("ERROR: old_dev_card not found")
        sys.exit(1)
    content = content.replace(old_dev_card, new_dev_card, 1)

    # 13. Update JavaScript tilt selector
    old_tilt_js = "var tiltCards = document.querySelectorAll('.feature-card, .highlight-card, .gym-card, .security-card');"
    new_tilt_js = "var tiltCards = document.querySelectorAll('.feature-card, .highlight-card, .gym-card, .gym-join-card, .security-card, .developer-card');"
    if old_tilt_js not in content:
        print("ERROR: old_tilt_js not found")
        sys.exit(1)
    content = content.replace(old_tilt_js, new_tilt_js, 1)

    # Write back
    p.write_text(content, encoding='utf-8')
    print(f"SUCCESS: index.js updated cleanly! Length change: {initial_len} -> {len(content)}")

if __name__ == '__main__':
    main()
