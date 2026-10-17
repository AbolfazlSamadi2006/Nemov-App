import pathlib

p = pathlib.Path('yalda_cloud_server/cloudflare_worker/index.js')
content = p.read_text(encoding='utf-8')

checks = [
    'const LANDING_PAGE_ETAG = \'W/"landing-v3.4.0-nemov-3d-marquee"\';',
    '/* 3D Perspective App Mockup in Hero */',
    '/* Floating Glass Widgets with Blur Effect */',
    '/* Infinite Moving Marquee with Frosted Glass Cards',
    '<!-- 3D Perspective App Mockup with Floating Sports Widgets -->',
    '<div class="hero-badge">',
    '<div class="highlights-grid">',
    '<article class="gym-card reveal-on-scroll"',
    '<article class="gym-join-card"',
    '<div class="security-grid">',
    '<div class="developer-card reveal-on-scroll">',
    "var tiltCards = document.querySelectorAll('.feature-card, .highlight-card, .gym-card, .security-card');"
]

for c in checks:
    print(c[:40], '-->', c in content)
