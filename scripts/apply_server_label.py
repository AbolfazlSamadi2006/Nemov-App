import pathlib

p = pathlib.Path('nemov_cloud_server/cloudflare_worker/index.js')
content = p.read_text(encoding='utf-8')

# Update ETag
content = content.replace(
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.1-nemov-3d-polish"\';',
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.2-nemov-server-label"\';'
)

# 1. Floating Widget 3:
content = content.replace(
    '<span class="widget-subline">پشتیبان خودکار در کلودفلر</span>',
    '<span class="widget-subline">پشتیبان خودکار در سرور</span>'
)

# 2. Marquee cards:
content = content.replace(
    '<span class="marquee-card-desc">همگام‌سازی امن با کلودفلر</span>',
    '<span class="marquee-card-desc">همگام‌سازی امن با سرور</span>'
)

# 3. Quick Highlights:
content = content.replace(
    '<p>همگام‌سازی رمزنگاری‌شده با سرورهای توزیع‌شده کلودفلر در پس‌زمینه</p>',
    '<p>همگام‌سازی رمزنگاری‌شده با سرورهای امن در پس‌زمینه</p>'
)

# 4. Security card:
content = content.replace(
    '<h3>پشتیبان‌گیری ابری خودکار در کلودفلر</h3>\n                    <p>\n                        با اتصال به اینترنت، بکاپ‌های امنیتی به صورت خودکار به فضای ابری توزیع‌شده Cloudflare ارسال می‌شوند تا در صورت نقص سخت‌افزاری، اطلاعات بلافاصله بازیابی شوند.\n                    </p>',
    '<h3>پشتیبان‌گیری ابری خودکار در سرور</h3>\n                    <p>\n                        با اتصال به اینترنت، بکاپ‌های امنیتی به صورت خودکار به فضای ابری امن سرور ارسال می‌شوند تا در صورت نقص سخت‌افزاری، اطلاعات بلافاصله بازیابی شوند.\n                    </p>'
)

p.write_text(content, encoding='utf-8')
print("Successfully replaced کلودفلر with سرور in landing page.")
