/**
 * Yalda Gym Cloudflare Worker - Serverless Backup Server & Admin Dashboard
 * Author: Abolfazl Samadi
 */

const PRIMARY_SECRET_API_KEY = "nemov_cloud_security";
const LEGACY_SECRET_API_KEY = "yalda_cloud_sec_2006_gym";
const SECRET_API_KEY = PRIMARY_SECRET_API_KEY;
const ADMIN_USER = "Abolfazl";
const ADMIN_PASS = "Abolfazl2006";
const AUTH_COOKIE_NAME = "yalda_admin_session";
const AUTH_SECRET_TOKEN = "yalda_auth_token_secret_2006_gym";

// Gregorian to Shamsi date converter
function toShamsi(date) {
    if (!date) return "-";
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    if (isNaN(date.getTime())) return "-";
    const g_y = date.getFullYear(), g_m = date.getMonth() + 1, g_d = date.getDate();
    const g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if ((g_y % 4 === 0 && g_y % 100 !== 0) || (g_y % 400 === 0)) g_days_in_month[1] = 29;
    let gy = g_y - 1600, gm = g_m - 1, gd = g_d - 1;
    let g_day_no = 365 * gy + Math.floor((gy + 3) / 4) - Math.floor((gy + 99) / 100) + Math.floor((gy + 399) / 400);
    for (let i = 0; i < gm; ++i) g_day_no += g_days_in_month[i];
    g_day_no += gd;
    let j_day_no = g_day_no - 79;
    let j_np = Math.floor(j_day_no / 12053);
    j_day_no %= 12053;
    let jy = 979 + 33 * j_np + 4 * Math.floor(j_day_no / 1461);
    j_day_no %= 1461;
    if (j_day_no >= 366) {
        jy += Math.floor((j_day_no - 1) / 365);
        j_day_no = (j_day_no - 1) % 365;
    }
    let jm = 0, jd = 0;
    for (let i = 0; i < 11; ++i) {
        const days = i < 6 ? 31 : 30;
        if (j_day_no < days) {
            jm = i + 1;
            jd = j_day_no + 1;
            break;
        }
        j_day_no -= days;
    }
    if (jm === 0) {
        jm = 12;
        jd = j_day_no + 1;
    }
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')} ${hh}:${mm}`;
}


// Persian & Arabic numeral normalizer to ASCII 0-9
function normalizePersianDigits(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/[۰-۹]/g, d => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
        .replace(/[٠-٩]/g, d => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)));
}

// Constant-time string equality helper mitigating timing side-channel attacks (supports multi-key arrays)
function timingSafeEqual(a, b) {
    if (Array.isArray(b)) {
        return b.some(target => timingSafeEqual(a, target));
    }
    if (Array.isArray(a)) {
        return a.some(target => timingSafeEqual(target, b));
    }
    if (typeof a !== "string" || typeof b !== "string") return false;
    let mismatch = a.length ^ b.length;
    const maxLen = Math.max(a.length, b.length);
    for (let i = 0; i < maxLen; i++) {
        const charA = i < a.length ? a.charCodeAt(i) : 0;
        const charB = i < b.length ? b.charCodeAt(i) : 0;
        mismatch |= charA ^ charB;
    }
    return mismatch === 0;
}

function getCookie(request, name) {
    try {
        const cookieString = request.headers.get("Cookie") || "";
        const cookies = cookieString.split(";").map(c => c.trim());
        for (const cookie of cookies) {
            const eqIdx = cookie.indexOf("=");
            if (eqIdx === -1) continue;
            const k = cookie.slice(0, eqIdx).trim();
            const v = cookie.slice(eqIdx + 1).trim();
            if (k === name) {
                try {
                    return decodeURIComponent(v);
                } catch (e) {
                    return v;
                }
            }
        }
    } catch (e) {}
    return null;
}

function isAuthenticated(request) {
    const token = getCookie(request, AUTH_COOKIE_NAME);
    return timingSafeEqual(token, AUTH_SECRET_TOKEN);
}

function isAdminSubdomain(hostname) {
    if (!hostname) return false;
    const h = hostname.toLowerCase();
    const adminPrefixes = [
        "admin.",
        "panel.",
        "dashboard.",
        "cloud.",
        "backup.",
        "backups.",
        "storage.",
        "messages.",
        "sms.",
        "gym."
    ];
    for (const prefix of adminPrefixes) {
        if (h.startsWith(prefix)) return true;
    }
    if (h.endsWith(".workers.dev")) return true;
    return false;
}


function getStorage(env) {
    if (!env) return { r2: null, kv: null };

    // 1. Resolve KV storage (Cloudflare Workers KV - Primary Storage)
    let kv = env.BACKUPS_KV || env.KV || env.BACKUP_KV || env.NEMOV_KV || env.nemov_backups_kv || env.YALDA_KV || env.yalda_backups_kv || null;
    if (!kv) {
        for (const key of Object.keys(env)) {
            const val = env[key];
            if (val && typeof val.get === "function" && typeof val.put === "function" && typeof val.list === "function") {
                kv = val;
                break;
            }
        }
    }

    // 2. Resolve R2 storage if available
    let r2 = env.BACKUPS_R2 || env.R2 || env.BUCKET || null;

    return { r2, kv };
}

// In-memory cache for decoded font bytes to minimize CPU time on Cloudflare Workers
let cachedFontBytes = null;
function getFontBytes() {
    if (!cachedFontBytes) {
        const binaryStr = atob(BKOODAK_WOFF2_BASE64);
        const len = binaryStr.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }
        cachedFontBytes = bytes;
    }
    return cachedFontBytes;
}

let cachedLogoBytes = null;
function getLogoBytes() {
    if (!cachedLogoBytes) {
        const binaryStr = atob(YALDA_LOGO_BASE64);
        const len = binaryStr.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }
        cachedLogoBytes = bytes;
    }
    return cachedLogoBytes;
}

let cachedNemovLogoBytes = null;
function getNemovLogoBytes() {
    if (!cachedNemovLogoBytes) {
        const binaryStr = atob(NEMOV_LOGO_BASE64);
        const len = binaryStr.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }
        cachedNemovLogoBytes = bytes;
    }
    return cachedNemovLogoBytes;
}

let cachedDevPhotoBytes = null;
function getDevPhotoBytes() {
    if (!cachedDevPhotoBytes) {
        const binaryStr = atob(DEVELOPER_PHOTO_BASE64);
        const len = binaryStr.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }
        cachedDevPhotoBytes = bytes;
    }
    return cachedDevPhotoBytes;
}

// Sanitization & HTML/JS Escaping helpers for XSS immunity
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function escapeJs(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "\\r")
        .replace(/</g, "\\u003c")
        .replace(/>/g, "\\u003e");
}

function safeDecodeURIComponent(str) {
    if (!str) return "";
    try {
        return decodeURIComponent(str);
    } catch (e) {
        return str;
    }
}

// Bounded concurrent batch fetcher preventing subrequest exhaustion
async function batchFetch(items, fn, concurrency = 10) {
    if (!items || items.length === 0) return [];
    const results = new Array(items.length);
    let index = 0;
    async function worker() {
        while (index < items.length) {
            const i = index++;
            try {
                results[i] = await fn(items[i]);
            } catch (err) {
                results[i] = null;
            }
        }
    }
    const workers = [];
    const poolSize = Math.min(concurrency, items.length);
    for (let w = 0; w < poolSize; w++) {
        workers.push(worker());
    }
    await Promise.all(workers);
    return results;
}

// Resilient KV key lister supporting Cloudflare cursor pagination
async function listAllKeys(kv, prefix) {
    if (!kv || typeof kv.list !== "function") return [];
    try {
        let keys = [];
        let cursor = undefined;
        let complete = false;
        while (!complete) {
            const res = await kv.list({ prefix, cursor });
            if (res && res.keys) {
                keys.push(...res.keys);
            }
            complete = !res || res.list_complete !== false;
            cursor = res ? res.cursor : undefined;
            if (!cursor) break;
        }
        return keys;
    } catch (e) {
        console.error(`Error listing KV for prefix ${prefix}:`, e);
        return [];
    }
}

export default {
    async fetch(request, env, ctx) {
        const { r2, kv } = getStorage(env);
        const url = new URL(request.url);
        const path = url.pathname;
        const method = request.method;
        const validSecrets = [PRIMARY_SECRET_API_KEY, LEGACY_SECRET_API_KEY];
        if (env && env.SECRET_API_KEY && !validSecrets.includes(env.SECRET_API_KEY)) {
            validSecrets.unshift(env.SECRET_API_KEY);
        }
        const secretApiKey = validSecrets;

        // Force HTTPS 301 Redirect for plain HTTP requests (fixes mobile Safari & Google App ERR_CONNECTION_CLOSED)
        const proto = request.headers.get("x-forwarded-proto") || url.protocol.replace(":", "");
        if (proto === "http" && url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
            const httpsUrl = "https://" + url.host + url.pathname + url.search;
            return new Response(null, {
                status: 301,
                headers: {
                    "Location": httpsUrl,
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                    "Alt-Svc": "clear"
                }
            });
        }

        // CORS Headers
        const corsHeaders = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key, Authorization"
        };

        if (method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        // Security Guard: Reject unsupported / dangerous HTTP methods
        if (method === "TRACE" || method === "TRACK" || method === "CONNECT") {
            return new Response("Method Not Allowed", {
                status: 405,
                headers: { "Allow": "GET, POST, HEAD, OPTIONS", ...corsHeaders }
            });
        }

        // ====================================================================
        // 0. Static Font & Asset Delivery (GET /fonts/bkoodak.woff2, /images/yalda_logo.jpg, /favicon.ico)
        // ====================================================================
        if (path === "/fonts/bkoodak.woff2" || path === "/fonts/BKoodak.woff2") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            const fontHeaders = {
                ...corsHeaders,
                "Content-Type": "font/woff2",
                "Cache-Control": "public, max-age=31536000, immutable"
            };
            if (method === "HEAD") {
                return new Response(null, { headers: fontHeaders });
            }
            return new Response(getFontBytes(), { headers: fontHeaders });
        }

        if (path === "/images/nemov_logo.png" || path === "/nemov_logo.png" || path === "/images/logo.png" || path === "/favicon.ico") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            const logoEtag = 'W/"nemov-logo-v3.4.5"';
            const ifNoneMatch = request && request.headers && (request.headers.get("if-none-match") || request.headers.get("If-None-Match"));
            const logoHeaders = {
                ...corsHeaders,
                "Content-Type": "image/png",
                "Cache-Control": "public, max-age=31536000, immutable",
                "ETag": logoEtag
            };
            if (ifNoneMatch && (ifNoneMatch === logoEtag || ifNoneMatch.includes(logoEtag))) {
                return new Response(null, { status: 304, headers: logoHeaders });
            }
            if (method === "HEAD") {
                return new Response(null, { headers: logoHeaders });
            }
            return new Response(getNemovLogoBytes(), { headers: logoHeaders });
        }

        if (path === "/images/yalda_logo.jpg" || path === "/yalda_logo.jpg" || path === "/logo.jpg") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            const logoHeaders = {
                ...corsHeaders,
                "Content-Type": "image/jpeg",
                "Cache-Control": "public, max-age=31536000, immutable"
            };
            if (method === "HEAD") {
                return new Response(null, { headers: logoHeaders });
            }
            return new Response(getLogoBytes(), { headers: logoHeaders });
        }

        if (path === "/images/developer_photo.jpg" || path === "/developer_photo.jpg" || path === "/images/developer.jpg" || path === "/developer.jpg") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            const devPhotoHeaders = {
                ...corsHeaders,
                "Content-Type": "image/jpeg",
                "Cache-Control": "public, max-age=31536000, immutable"
            };
            if (method === "HEAD") {
                return new Response(null, { headers: devPhotoHeaders });
            }
            return new Response(getDevPhotoBytes(), { headers: devPhotoHeaders });
        }

        // ====================================================================
        // 0.05 SEO Assets: robots.txt & sitemap.xml
        // ====================================================================
        if (path === "/robots.txt") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            const robotsHeaders = {
                ...corsHeaders,
                "Content-Type": "text/plain; charset=utf-8",
                "Cache-Control": "public, max-age=86400"
            };
            if (method === "HEAD") {
                return new Response(null, { headers: robotsHeaders });
            }
            const robotsTxt = `User-agent: *
Allow: /
Disallow: /api/
Disallow: /dashboard
Disallow: /login

Sitemap: https://nemovapp.ir/sitemap.xml
`;
            return new Response(robotsTxt, { headers: robotsHeaders });
        }

        if (path === "/sitemap.xml") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            const sitemapHeaders = {
                ...corsHeaders,
                "Content-Type": "application/xml; charset=utf-8",
                "Cache-Control": "public, max-age=86400"
            };
            if (method === "HEAD") {
                return new Response(null, { headers: sitemapHeaders });
            }
            const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://nemovapp.ir/</loc>
    <lastmod>2026-10-12</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
`;
            return new Response(sitemapXml, { headers: sitemapHeaders });
        }

        // ====================================================================
        // 0.1 Explicit Landing Page (GET /landing)
        // ====================================================================
        if (path === "/landing") {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            return createLandingResponse(request);
        }

        // ====================================================================
        // 1. API: Upload Backup (POST /api/backup/upload)
        // ====================================================================
        if (path === "/api/backup/upload" && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            if (!timingSafeEqual(apiKey, secretApiKey)) {
                return new Response(JSON.stringify({ success: false, detail: "کلید امنیتی سرور نامعتبر است." }), {
                    status: 401,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }

            try {
                const formData = await request.formData();
                const phoneRaw = formData.get("phone") || "";
                const trainerName = formData.get("trainer_name") || "مربی";
                const file = formData.get("file");

                const phone = normalizePersianDigits(phoneRaw).replace(/\D/g, "");
                if (!phone || !file) {
                    return new Response(JSON.stringify({ success: false, detail: "فایل دیتابیس یا شماره مربی نامعتبر است." }), {
                        status: 400,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                const fileBytes = await file.arrayBuffer();
                const fileSizeMb = (fileBytes.byteLength / (1024 * 1024)).toFixed(2);
                const now = new Date();
                const shamsiDate = toShamsi(now);

                const metadata = {
                    phone,
                    trainer_name: trainerName,
                    last_backup_iso: now.toISOString(),
                    last_backup_shamsi: shamsiDate,
                    file_size_mb: parseFloat(fileSizeMb),
                    filename: "yalda.db"
                };

                // Store in KV (primary) or R2
                if (kv) {
                    await kv.put(`db_${phone}`, fileBytes);
                    await kv.put(`meta_${phone}`, JSON.stringify(metadata), { metadata });
                } else if (r2) {
                    await r2.put(`backups/${phone}/yalda.db`, fileBytes, {
                        httpMetadata: { contentType: "application/octet-stream" },
                        customMetadata: { phone, trainerName, shamsiDate, fileSizeMb }
                    });
                    await r2.put(`backups/${phone}/metadata.json`, JSON.stringify(metadata), {
                        httpMetadata: { contentType: "application/json" }
                    });
                } else {
                    return new Response(JSON.stringify({ success: false, detail: "هیچ مخزن ابری (KV) در تنظیمات ورکر یافت نشد." }), {
                        status: 500,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                return new Response(JSON.stringify({
                    success: true,
                    message: `نسخه پشتیبان با موفقیت در سرور کلودفلر ذخیره شد (حجم: ${fileSizeMb} MB)`,
                    timestamp: shamsiDate
                }), {
                    status: 200,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            } catch (err) {
                return new Response(JSON.stringify({ success: false, detail: "خطا در پردازش فایل: " + err.message }), {
                    status: 500,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
        }

        // ====================================================================
        // 2. API: Download Backup (GET /api/backup/download/:phone)
        // ====================================================================
        if (path.startsWith("/api/backup/download/")) {
            const rawPhone = path.replace("/api/backup/download/", "");
            const phone = normalizePersianDigits(rawPhone).replace(/\D/g, "");
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            const authed = isAuthenticated(request) || timingSafeEqual(apiKey, secretApiKey);

            if (!authed) {
                return new Response("دسترسی غیرمجاز", { status: 401 });
            }

            if (kv) {
                const data = await kv.get(`db_${phone}`, { type: "arrayBuffer" });
                if (!data) return new Response("فایل پشتیبان برای این مربی در مخزن ابری یافت نشد.", { status: 404 });
                return new Response(data, {
                    headers: {
                        "Content-Disposition": `attachment; filename="yalda_${phone}.db"`,
                        "Content-Type": "application/octet-stream"
                    }
                });
            } else if (r2) {
                const object = await r2.get(`backups/${phone}/yalda.db`);
                if (!object) {
                    return new Response("نسخه پشتیبان برای این مربی یافت نشد.", { status: 404 });
                }
                const headers = new Headers();
                object.writeHttpMetadata(headers);
                headers.set("Content-Disposition", `attachment; filename="yalda_${phone}.db"`);
                headers.set("Content-Type", "application/octet-stream");
                return new Response(object.body, { headers });
            }
            return new Response("مخزن ذخیره‌سازی پیکربندی نشده است.", { status: 500 });
        }

        // ====================================================================
        // 2.1 API: Upload Exercise Video or Image (POST /api/video/upload, /api/image/upload)
        // ====================================================================
        if ((path === "/api/video/upload" || path === "/api/image/upload" || path === "/api/media/upload") && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            if (!timingSafeEqual(apiKey, secretApiKey) && !isAuthenticated(request)) {
                return new Response(JSON.stringify({ success: false, detail: "کلید امنیتی سرور نامعتبر است." }), {
                    status: 401,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }

            try {
                const formData = await request.formData();
                const file = formData.get("file");
                let filename = formData.get("filename") || (file ? file.name : "");
                if (!file || !filename) {
                    return new Response(JSON.stringify({ success: false, detail: "فایل یا نام رسانه ارسال نشده است." }), {
                        status: 400,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                // Clean filename
                filename = filename.replace(/[^\w\d_\-\.\u0600-\u06FF]/g, "_");
                const fileBytes = await file.arrayBuffer();
                const fileSizeMb = (fileBytes.byteLength / (1024 * 1024)).toFixed(2);

                const ext = filename.split('.').pop().toLowerCase();
                const isImage = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'].includes(ext) || path === "/api/image/upload";
                const mimeMap = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'webp': 'image/webp',
                    'gif': 'image/gif',
                    'bmp': 'image/bmp'
                };
                const videoMimeMap = {
                    'mp4': 'video/mp4',
                    'webm': 'video/webm',
                    'ogg': 'video/ogg',
                    'mov': 'video/quicktime',
                    'm4v': 'video/mp4'
                };
                const contentType = isImage ? (mimeMap[ext] || 'image/jpeg') : (videoMimeMap[ext] || 'video/mp4');
                const r2Folder = isImage ? 'images/' : 'videos/';
                const kvPrefix = isImage ? 'image_' : 'video_';
                const metaPrefix = isImage ? 'imeta_' : 'vmeta_';

                if (kv) {
                    const metaObj = { filename, fileSizeMb, uploadDate: new Date().toISOString() };
                    await kv.put(`${kvPrefix}${filename}`, fileBytes);
                    await kv.put(`${metaPrefix}${filename}`, JSON.stringify(metaObj), { metadata: metaObj });
                } else if (r2) {
                    await r2.put(`${r2Folder}${filename}`, fileBytes, {
                        httpMetadata: { contentType: contentType },
                        customMetadata: { filename, fileSizeMb, uploadDate: new Date().toISOString() }
                    });
                } else {
                    return new Response(JSON.stringify({ success: false, detail: "هیچ مخزن ابری (KV) برای ذخیره رسانه در دسترس نیست." }), {
                        status: 500,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                const mediaUrl = isImage ? `${url.origin}/image/${encodeURIComponent(filename)}` : `${url.origin}/video/${encodeURIComponent(filename)}`;
                return new Response(JSON.stringify({
                    success: true,
                    message: isImage ? "تصویر با موفقیت در سرور ابری کلودفلر ذخیره شد." : "ویدیو با موفقیت در سرور ابری کلودفلر ذخیره شد.",
                    url: mediaUrl,
                    filename: filename,
                    size_mb: fileSizeMb
                }), {
                    status: 200,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            } catch (err) {
                return new Response(JSON.stringify({ success: false, detail: "خطا در پردازش رسانه: " + err.message }), {
                    status: 500,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
        }

        // ====================================================================
        // 2.2 Public Isolated Video Streaming & Player (GET /video/:filename)
        // ====================================================================
        if (path.startsWith("/video/")) {
            const rawFilename = path.replace("/video/", "");
            const filename = safeDecodeURIComponent(rawFilename);
            const ext = filename.split('.').pop().toLowerCase();
            if (['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif'].includes(ext)) {
                return Response.redirect(`${url.origin}/image/${encodeURIComponent(filename)}${url.search}`, 302);
            }

            let videoBody = null;

            if (kv) {
                const data = await kv.get(`video_${filename}`, { type: "arrayBuffer" });
                if (data) videoBody = data;
            }
            if (!videoBody && r2) {
                const object = await r2.get(`videos/${filename}`);
                if (object) videoBody = await object.arrayBuffer();
            }

            if (!videoBody) {
                return new Response(renderIsolatedNotFoundPage(), {
                    status: 404,
                    headers: { "Content-Type": "text/html; charset=utf-8" }
                });
            }

            const acceptHeader = request.headers.get("Accept") || "";
            const isRawRequested = url.searchParams.get("raw") === "1" || (!acceptHeader.includes("text/html") && acceptHeader.length > 0 && !url.searchParams.has("play"));

            if (isRawRequested) {
                const videoMimeMap = {
                    'mp4': 'video/mp4',
                    'webm': 'video/webm',
                    'ogg': 'video/ogg',
                    'mov': 'video/quicktime',
                    'm4v': 'video/mp4'
                };
                const videoContentType = videoMimeMap[ext] || 'video/mp4';
                const totalLength = videoBody.byteLength;
                const rangeHeader = request.headers.get("Range");

                if (rangeHeader) {
                    const match = rangeHeader.match(/bytes=(\d*)-(\d*)/);
                    if (match) {
                        let start = 0;
                        let end = totalLength - 1;
                        const hasStart = match[1] !== "";
                        const hasEnd = match[2] !== "";

                        if (!hasStart && hasEnd) {
                            // Suffix byte range (RFC 7233): bytes=-N (e.g. Mobile Safari / QuickTime requesting the last N bytes)
                            const suffix = parseInt(match[2], 10);
                            if (!isNaN(suffix) && suffix > 0) {
                                start = Math.max(0, totalLength - suffix);
                                end = totalLength - 1;
                            }
                        } else if (hasStart) {
                            start = parseInt(match[1], 10);
                            if (isNaN(start)) start = 0;
                            if (hasEnd) {
                                end = parseInt(match[2], 10);
                                if (isNaN(end) || end >= totalLength) end = totalLength - 1;
                            } else {
                                end = totalLength - 1;
                            }
                        }

                        if (start > end || start >= totalLength || start < 0) {
                            return new Response(null, {
                                status: 416,
                                headers: {
                                    "Content-Range": `bytes */${totalLength}`,
                                    "Access-Control-Allow-Origin": "*"
                                }
                            });
                        }

                        const chunk = videoBody.slice(start, end + 1);
                        return new Response(chunk, {
                            status: 206,
                            headers: {
                                "Content-Type": videoContentType,
                                "Content-Range": `bytes ${start}-${end}/${totalLength}`,
                                "Accept-Ranges": "bytes",
                                "Content-Length": chunk.byteLength.toString(),
                                "Cache-Control": "public, max-age=86400",
                                "Access-Control-Allow-Origin": "*",
                                "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length"
                            }
                        });
                    }
                }

                return new Response(videoBody, {
                    status: 200,
                    headers: {
                        "Content-Type": videoContentType,
                        "Accept-Ranges": "bytes",
                        "Content-Length": totalLength.toString(),
                        "Cache-Control": "public, max-age=86400",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length"
                    }
                });
            } else {
                const videoStreamUrl = `${url.origin}/video/${encodeURIComponent(filename)}?raw=1&v=${Date.now()}`;
                const titleParam = url.searchParams.get("title") || filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
                return new Response(renderSandboxedVideoPlayer(titleParam, videoStreamUrl), {
                    headers: {
                        "Content-Type": "text/html; charset=utf-8",
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                });
            }
        }

        // ====================================================================
        // 2.3 Public Isolated Exercise Image Viewer & Delivery (GET /image/:filename)
        // ====================================================================
        if (path.startsWith("/image/")) {
            const rawFilename = path.replace("/image/", "");
            const filename = safeDecodeURIComponent(rawFilename);

            let imageBody = null;
            if (kv) {
                let data = await kv.get(`image_${filename}`, { type: "arrayBuffer" });
                if (!data) data = await kv.get(`video_${filename}`, { type: "arrayBuffer" });
                if (data) imageBody = data;
            }
            if (!imageBody && r2) {
                let object = await r2.get(`images/${filename}`);
                if (!object) object = await r2.get(`videos/${filename}`);
                if (object) imageBody = await object.arrayBuffer();
            }

            if (!imageBody) {
                return new Response(renderIsolatedNotFoundPage("تصویر یافت نشد", "فایل تصویر درخواستی در مخزن سرور موجود نیست یا حذف شده است."), {
                    status: 404,
                    headers: { "Content-Type": "text/html; charset=utf-8" }
                });
            }

            const ext = filename.split('.').pop().toLowerCase();
            const mimeMap = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'webp': 'image/webp',
                'gif': 'image/gif',
                'bmp': 'image/bmp'
            };
            const contentType = mimeMap[ext] || "image/jpeg";

            const acceptHeader = request.headers.get("Accept") || "";
            const isRawRequested = url.searchParams.get("raw") === "1" || (!acceptHeader.includes("text/html") && acceptHeader.length > 0 && !url.searchParams.has("view"));

            if (isRawRequested) {
                return new Response(imageBody, {
                    status: 200,
                    headers: {
                        "Content-Type": contentType,
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "*"
                    }
                });
            } else {
                const imageRawUrl = `${url.origin}/image/${encodeURIComponent(filename)}?raw=1`;
                const titleParam = url.searchParams.get("title") || filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
                return new Response(renderSandboxedImageViewer(titleParam, imageRawUrl), {
                    headers: {
                        "Content-Type": "text/html; charset=utf-8",
                        "Cache-Control": "no-cache, no-store, must-revalidate"
                    }
                });
            }
        }
        // ====================================================================
        // 3. Web: Login Page (GET & POST /login)
        // ====================================================================
        if (path === "/login" && method === "GET") {
            if (isAuthenticated(request)) {
                const dest = isAdminSubdomain(url.hostname) ? "/" : "/dashboard";
                return Response.redirect(`${url.origin}${dest}`, 302);
            }
            return new Response(renderLoginPage(), {
                headers: { "Content-Type": "text/html; charset=utf-8" }
            });
        }

        if (path === "/login" && method === "POST") {
            const formData = await request.formData();
            const username = formData.get("username") || "";
            const password = formData.get("password") || "";
            const validUser = (env && env.ADMIN_USER) || ADMIN_USER;
            const validPass = (env && env.ADMIN_PASS) || ADMIN_PASS;

            if (timingSafeEqual(username, validUser) && timingSafeEqual(password, validPass)) {
                const isSecure = url.protocol === "https:";
                const secureFlag = isSecure ? "; Secure" : "";
                const dest = isAdminSubdomain(url.hostname) ? "/" : "/dashboard";
                return new Response(null, {
                    status: 303,
                    headers: {
                        "Location": dest,
                        "Set-Cookie": `${AUTH_COOKIE_NAME}=${AUTH_SECRET_TOKEN}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000${secureFlag}`
                    }
                });
            }

            return new Response(renderLoginPage("نام کاربری یا رمز عبور اشتباه است."), {
                headers: { "Content-Type": "text/html; charset=utf-8" }
            });
        }

        if (path === "/logout") {
            const isSecure = url.protocol === "https:";
            const secureFlag = isSecure ? "; Secure" : "";
            const dest = isAdminSubdomain(url.hostname) ? "/login" : "/";
            return new Response(null, {
                status: 303,
                headers: {
                    "Location": dest,
                    "Set-Cookie": `${AUTH_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secureFlag}`
                }
            });
        }

        // ====================================================================
        // 4. Web & API: Delete Backup (POST /api/backup/delete/:phone or formData)
        // ====================================================================
        if ((path === "/api/backup/delete" || path.startsWith("/api/backup/delete/")) && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            const isAuthed = isAuthenticated(request) || timingSafeEqual(apiKey, secretApiKey);
            if (!isAuthed) {
                if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                    return new Response(JSON.stringify({ success: false, detail: "دسترسی غیرمجاز یا کلید امنیتی نامعتبر است." }), {
                        status: 401,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                return new Response("دسترسی غیرمجاز", { status: 401 });
            }
            let phone = "";
            if (path.startsWith("/api/backup/delete/")) {
                phone = normalizePersianDigits(path.replace("/api/backup/delete/", "")).replace(/\D/g, "");
            }
            try {
                const formData = await request.formData();
                if (formData && formData.has("phone")) {
                    phone = normalizePersianDigits(formData.get("phone") || "").replace(/\D/g, "") || phone;
                }
            } catch (e) {}

            if (!phone) {
                const errDetail = "شماره تماس مربی نامعتبر است.";
                if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                    return new Response(JSON.stringify({ success: false, detail: errDetail }), {
                        status: 400,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                return new Response(errDetail, { status: 400 });
            }

            if (kv) {
                await Promise.all([
                    kv.delete(`db_${phone}`),
                    kv.delete(`meta_${phone}`)
                ]);
            }
            if (r2) {
                await Promise.all([
                    r2.delete(`backups/${phone}/yalda.db`),
                    r2.delete(`backups/${phone}/metadata.json`)
                ]);
            }

            const wantsJson = !!apiKey || (request.headers.get("Accept") && request.headers.get("Accept").includes("application/json"));
            if (wantsJson) {
                return new Response(JSON.stringify({ success: true, message: "نسخه پشتیبان با موفقیت حذف شد." }), {
                    status: 200,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
            return new Response(null, { status: 303, headers: { "Location": "/?tab=backups" } });
        }

        // ====================================================================
        // 4.1 Web & API: Delete Media (POST /api/media/delete/:filename or formData)
        // ====================================================================
        if ((path === "/api/media/delete" || path.startsWith("/api/media/delete/")) && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            const isAuthed = isAuthenticated(request) || timingSafeEqual(apiKey, secretApiKey);
            if (!isAuthed) {
                if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                    return new Response(JSON.stringify({ success: false, detail: "دسترسی غیرمجاز یا کلید امنیتی نامعتبر است." }), {
                        status: 401,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                return new Response("دسترسی غیرمجاز", { status: 401 });
            }
            let filename = "";
            let fileType = "";
            if (path.startsWith("/api/media/delete/")) {
                const rawFilename = path.replace("/api/media/delete/", "");
                filename = safeDecodeURIComponent(rawFilename);
            }
            try {
                const formData = await request.formData();
                if (formData && formData.has("filename")) {
                    filename = formData.get("filename") || filename;
                }
                if (formData && formData.has("type")) {
                    fileType = formData.get("type") || "";
                }
            } catch (e) {}

            if (!filename) {
                const errDetail = "نام فایل مشخص نشده است.";
                if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                    return new Response(JSON.stringify({ success: false, detail: errDetail }), {
                        status: 400,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                return new Response(errDetail, { status: 400 });
            }

            const ext = filename.split('.').pop().toLowerCase();
            const isImage = fileType === "image" || ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'].includes(ext);
            const r2Folder = isImage ? 'images/' : 'videos/';
            const kvPrefix = isImage ? 'image_' : 'video_';
            const metaPrefix = isImage ? 'imeta_' : 'vmeta_';

            if (kv) {
                await Promise.all([
                    kv.delete(`${kvPrefix}${filename}`),
                    kv.delete(`${metaPrefix}${filename}`)
                ]);
            }
            if (r2) {
                await r2.delete(`${r2Folder}${filename}`);
            }

            const wantsJson = !!apiKey || (request.headers.get("Accept") && request.headers.get("Accept").includes("application/json"));
            if (wantsJson) {
                return new Response(JSON.stringify({ success: true, message: "فایل رسانه با موفقیت حذف شد." }), {
                    status: 200,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
            return new Response(null, { status: 303, headers: { "Location": "/?tab=media" } });
        }

        // ====================================================================
        // 4.2 Web & API: Admin Recharge SMS for Trainer (POST /api/admin/sms/recharge)
        // ====================================================================
        if (path === "/api/admin/sms/recharge" && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            const isAuthed = isAuthenticated(request) || timingSafeEqual(apiKey, secretApiKey);
            if (!isAuthed) {
                if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                    return new Response(JSON.stringify({ success: false, detail: "دسترسی غیرمجاز یا کلید امنیتی نامعتبر است." }), {
                        status: 401,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                return new Response("دسترسی غیرمجاز", { status: 401 });
            }
            try {
                let phoneRaw = "";
                let trainerName = "مربی";
                let amountRaw = 0;

                const contentTypeHeader = request.headers.get("Content-Type") || "";
                if (contentTypeHeader.includes("application/json")) {
                    try {
                        const jsonBody = await request.json();
                        phoneRaw = jsonBody.phone || "";
                        trainerName = jsonBody.trainer_name || "مربی";
                        amountRaw = jsonBody.amount;
                    } catch (e) {}
                } else {
                    try {
                        const formData = await request.formData();
                        phoneRaw = formData.get("phone") || "";
                        trainerName = formData.get("trainer_name") || "مربی";
                        amountRaw = formData.get("amount");
                    } catch (e) {}
                }

                const phone = normalizePersianDigits(phoneRaw).replace(/\D/g, "");
                const amount = parseInt(normalizePersianDigits(amountRaw || "0"), 10);

                if (!phone || isNaN(amount) || amount <= 0 || !Number.isFinite(amount) || amount > 1000000) {
                    const errDetail = "اطلاعات مربی یا تعداد پیامک نامعتبر است (تعداد باید عددی مثبت باشد).";
                    if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                        return new Response(JSON.stringify({ success: false, detail: errDetail }), {
                            status: 400,
                            headers: { ...corsHeaders, "Content-Type": "application/json" }
                        });
                    }
                    return new Response(errDetail, { status: 400 });
                }

                let account = null;
                if (kv) {
                    account = await kv.get(`sms_trainer_${phone}`, { type: "json" });
                }
                if (!account) {
                    account = {
                        phone: phone,
                        trainer_name: trainerName,
                        remaining: 0,
                        total_credited: 0,
                        total_used: 0,
                        status: "active",
                        created_shamsi: toShamsi(new Date())
                    };
                }

                if (trainerName && trainerName !== "مربی") {
                    account.trainer_name = trainerName;
                }

                account.remaining = (account.remaining || 0) + amount;
                account.total_credited = (account.total_credited || 0) + amount;
                account.last_recharge_shamsi = toShamsi(new Date());
                account.status = "active";

                if (kv) {
                    await kv.put(`sms_trainer_${phone}`, JSON.stringify(account), { metadata: account });
                }

                const wantsJson = !!apiKey || (request.headers.get("Accept") && request.headers.get("Accept").includes("application/json"));
                if (wantsJson) {
                    return new Response(JSON.stringify({ success: true, message: "شارژ پیامک با موفقیت انجام شد.", remaining: account.remaining }), {
                        status: 200,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                return new Response(null, {
                    status: 303,
                    headers: { "Location": "/?tab=messages&recharged=1" }
                });
            } catch (e) {
                return new Response("خطا در پردازش شارژ پیامک: " + e.message, { status: 500 });
            }
        }

        // ====================================================================
        // 4.3 Web & API: Admin Delete/Reset SMS Account (POST /api/admin/sms/delete/:phone)
        // ====================================================================
        if (path.startsWith("/api/admin/sms/delete/") && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            const isAuthed = isAuthenticated(request) || timingSafeEqual(apiKey, secretApiKey);
            if (!isAuthed) {
                if (apiKey || request.headers.get("Accept")?.includes("application/json")) {
                    return new Response(JSON.stringify({ success: false, detail: "دسترسی غیرمجاز یا کلید امنیتی نامعتبر است." }), {
                        status: 401,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                return new Response("دسترسی غیرمجاز", { status: 401 });
            }
            const rawPhone = normalizePersianDigits(path.replace("/api/admin/sms/delete/", "")).replace(/\D/g, "");
            if (kv && rawPhone) {
                await kv.delete(`sms_trainer_${rawPhone}`);
            }
            const wantsJson = !!apiKey || (request.headers.get("Accept") && request.headers.get("Accept").includes("application/json"));
            if (wantsJson) {
                return new Response(JSON.stringify({ success: true, message: "حساب پیامکی مربی با موفقیت حذف شد." }), {
                    status: 200,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
            return new Response(null, {
                status: 303,
                headers: { "Location": "/?tab=messages" }
            });
        }

        // ====================================================================
        // 4.4 API: Get Trainer SMS Balance (GET /api/sms/balance)
        // ====================================================================
        if (path === "/api/sms/balance" && method === "GET") {
            const phoneRaw = url.searchParams.get("phone") || "";
            const phone = normalizePersianDigits(phoneRaw).replace(/\D/g, "");
            if (!phone) {
                return new Response(JSON.stringify({ success: false, detail: "شماره موبایل مربی ارسال نشده است." }), {
                    status: 400,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }

            let account = null;
            if (kv) {
                account = await kv.get(`sms_trainer_${phone}`, { type: "json" });
            }

            const trainerName = url.searchParams.get("trainer_name") || "";
            const gymName = url.searchParams.get("gym_name") || "";

            if (!account) {
                // Auto-register trainer in KV so they appear immediately in the admin web panel with 0 credits
                if (kv && phone) {
                    account = {
                        phone: phone,
                        trainer_name: trainerName || "مربی باشگاه",
                        gym_name: gymName || "باشگاه یلدا",
                        remaining: 0,
                        total_credited: 0,
                        total_used: 0,
                        status: "pending",
                        registered_at_shamsi: toShamsi(new Date()),
                        last_recharge_shamsi: "-"
                    };
                    await kv.put(`sms_trainer_${phone}`, JSON.stringify(account), { metadata: account });
                } else {
                    return new Response(JSON.stringify({
                        success: true,
                        phone: phone,
                        trainer_name: trainerName,
                        remaining: 0,
                        total_credited: 0,
                        total_used: 0,
                        status: "pending",
                        last_recharge_shamsi: "-"
                    }), {
                        status: 200,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
            } else if (trainerName && trainerName !== "مربی" && trainerName !== "مدیر سیستم" && account.trainer_name !== trainerName) {
                account.trainer_name = trainerName;
                if (kv) {
                    await kv.put(`sms_trainer_${phone}`, JSON.stringify(account), { metadata: account });
                }
            }

            return new Response(JSON.stringify({
                success: true,
                phone: account.phone,
                trainer_name: account.trainer_name || "",
                remaining: account.remaining || 0,
                total_credited: account.total_credited || 0,
                total_used: account.total_used || 0,
                status: (account.remaining || 0) > 0 ? "active" : ((account.total_credited || 0) === 0 ? "pending" : "depleted"),
                last_recharge_shamsi: account.last_recharge_shamsi || "-"
            }), {
                status: 200,
                headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
        }

        // ====================================================================
        // 4.4.1 API: Explicit Trainer Registration (POST /api/sms/register)
        // ====================================================================
        if (path === "/api/sms/register" && method === "POST") {
            try {
                const body = await request.json();
                const phoneRaw = body.phone || "";
                const phone = normalizePersianDigits(phoneRaw).replace(/\D/g, "");
                if (!phone) {
                    return new Response(JSON.stringify({ success: false, detail: "شماره موبایل نامعتبر است." }), {
                        status: 400,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
                const trainerName = body.trainer_name || "مربی باشگاه";
                const gymName = body.gym_name || "باشگاه یلدا";
                let account = null;
                if (kv) {
                    account = await kv.get(`sms_trainer_${phone}`, { type: "json" });
                    if (!account) {
                        account = {
                            phone: phone,
                            trainer_name: trainerName,
                            gym_name: gymName,
                            remaining: 0,
                            total_credited: 0,
                            total_used: 0,
                            status: "pending",
                            registered_at_shamsi: toShamsi(new Date()),
                            last_recharge_shamsi: "-"
                        };
                        await kv.put(`sms_trainer_${phone}`, JSON.stringify(account), { metadata: account });
                    } else if (trainerName && account.trainer_name !== trainerName) {
                        account.trainer_name = trainerName;
                        await kv.put(`sms_trainer_${phone}`, JSON.stringify(account), { metadata: account });
                    }
                }
                return new Response(JSON.stringify({
                    success: true,
                    phone: phone,
                    trainer_name: account ? account.trainer_name : trainerName,
                    remaining: account ? (account.remaining || 0) : 0,
                    status: account && (account.remaining || 0) > 0 ? "active" : "pending",
                    message: "مشخصات شما با موفقیت در سامانه پیامکی ثبت شد."
                }), {
                    status: 200,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            } catch (err) {
                return new Response(JSON.stringify({ success: false, detail: err.message }), {
                    status: 500,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
        }

        // ====================================================================
        // 4.5 API: Send SMS via Gateway (POST /api/sms/send)
        // ====================================================================
        if (path === "/api/sms/send" && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            if (!timingSafeEqual(apiKey, secretApiKey)) {
                return new Response(JSON.stringify({ success: false, detail: "کلید امنیتی سرور نامعتبر است." }), {
                    status: 401,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }

            try {
                const body = await request.json();
                const phone = normalizePersianDigits(body.phone || "").replace(/\D/g, "");
                let recipient = normalizePersianDigits(body.recipient || "").replace(/\D/g, "");
                if (recipient.startsWith("0098")) {
                    recipient = "0" + recipient.substring(4);
                } else if (recipient.startsWith("98") && recipient.length === 12) {
                    recipient = "0" + recipient.substring(2);
                } else if (recipient.startsWith("9") && recipient.length === 10) {
                    recipient = "0" + recipient;
                }

                const trainerName = body.trainer_name || "مربی";
                const memberName = body.member_name || "ورزشکار";
                const msgType = body.type || "custom"; // birthday, tuition, holiday, welcome, custom
                const templateId = body.template_id;
                const parameters = body.parameters || [];
                const messageText = body.message_text || "";

                if (!phone || !recipient) {
                    return new Response(JSON.stringify({ success: false, detail: "شماره فرستنده یا گیرنده نامعتبر است." }), {
                        status: 400,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                let account = null;
                if (kv) {
                    account = await kv.get(`sms_trainer_${phone}`, { type: "json" });
                }

                if (!account || (account.remaining || 0) <= 0) {
                    return new Response(JSON.stringify({
                        success: false,
                        remaining: 0,
                        detail: "اعتبار بسته پیامک شما به پایان رسیده است. جهت خرید یا شارژ مجدد با مدیریت تماس بگیرید."
                    }), {
                        status: 402,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }

                // Send via SMS.ir API
                const smsApiKey = env.SMS_API_KEY || "";
                let smsSuccess = false;
                let smsResponseDetail = "";

                if (smsApiKey) {
                    try {
                        if (templateId) {
                            const sanitizedParameters = Array.isArray(parameters) ? parameters.map(p => ({
                                name: String(p.name || "").trim(),
                                value: String((p.value !== undefined && p.value !== null && String(p.value).trim() !== "") ? p.value : "-").trim()
                            })) : [];

                            const smsRes = await fetch("https://api.sms.ir/v1/send/verify", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                    "X-API-KEY": smsApiKey
                                },
                                body: JSON.stringify({
                                    mobile: recipient,
                                    templateId: parseInt(templateId, 10),
                                    parameters: sanitizedParameters
                                })
                            });
                            const smsJson = await smsRes.json();
                            if (smsRes.ok && (smsJson.status === 1 || smsJson.status === 200)) {
                                smsSuccess = true;
                                smsResponseDetail = "ارسال موفق از طریق الگوی خدماتی SMS.ir";
                            } else {
                                smsResponseDetail = smsJson.message || ("خطای درگاه پیامک: " + smsRes.status);
                            }
                        } else {
                            const smsLineNumber = env.SMS_LINE_NUMBER || "";
                            const smsRes = await fetch("https://api.sms.ir/v1/send/bulk", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                    "X-API-KEY": smsApiKey
                                },
                                body: JSON.stringify({
                                    lineNumber: smsLineNumber,
                                    messageText: messageText,
                                    mobiles: [recipient]
                                })
                            });
                            const smsJson = await smsRes.json();
                            if (smsRes.ok && (smsJson.status === 1 || smsJson.status === 200)) {
                                smsSuccess = true;
                                smsResponseDetail = "ارسال موفق پیامک متنی";
                            } else {
                                smsResponseDetail = smsJson.message || ("خطای خط پیامک: " + smsRes.status);
                            }
                        }
                    } catch (err) {
                        smsResponseDetail = "خطا در اتصال به درگاه پیامک: " + err.message;
                    }
                } else {
                    // Simulation mode when SMS_API_KEY is not yet configured in Worker Secrets
                    smsSuccess = true;
                    smsResponseDetail = "ارسال آزمایشی موفق (شبیه‌ساز پیامک فعال است)";
                }

                if (smsSuccess) {
                    account.remaining = Math.max(0, (account.remaining || 0) - 1);
                    account.total_used = (account.total_used || 0) + 1;
                    if (kv) {
                        await kv.put(`sms_trainer_${phone}`, JSON.stringify(account), { metadata: account });
                        try {
                            let logs = await kv.get("sms_logs", { type: "json" }) || [];
                            logs.unshift({
                                id: "sms_" + Date.now(),
                                date_shamsi: toShamsi(new Date()),
                                trainer_name: trainerName,
                                trainer_phone: phone,
                                recipient: recipient,
                                member_name: memberName,
                                type: msgType,
                                detail: smsResponseDetail
                            });
                            if (logs.length > 100) logs = logs.slice(0, 100);
                            await kv.put("sms_logs", JSON.stringify(logs));
                        } catch (e) {}
                    }

                    return new Response(JSON.stringify({
                        success: true,
                        remaining: account.remaining,
                        message: "پیامک با موفقیت ارسال شد.",
                        detail: smsResponseDetail
                    }), {
                        status: 200,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                } else {
                    return new Response(JSON.stringify({
                        success: false,
                        remaining: account.remaining,
                        detail: smsResponseDetail || "ارسال پیامک با خطا مواجه شد."
                    }), {
                        status: 502,
                        headers: { ...corsHeaders, "Content-Type": "application/json" }
                    });
                }
            } catch (e) {
                return new Response(JSON.stringify({ success: false, detail: "خطای پردازش پیامک: " + e.message }), {
                    status: 500,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
        }

        // ====================================================================
        // 4.6 API: Get SMS Send History (GET /api/sms/history)
        // ====================================================================
        if (path === "/api/sms/history" && method === "GET") {
            const phoneRaw = url.searchParams.get("phone") || "";
            const phone = normalizePersianDigits(phoneRaw).replace(/\D/g, "");
            let logs = [];
            if (kv) {
                const allLogs = await kv.get("sms_logs", { type: "json" }) || [];
                if (phone) {
                    logs = allLogs.filter(l => l.trainer_phone === phone);
                } else {
                    logs = allLogs;
                }
            }
            return new Response(JSON.stringify({ success: true, logs: logs }), {
                status: 200,
                headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
        }

        // ====================================================================
        // 5. Web: Public Landing Page (GET / on apex domain)
        // ====================================================================
        if ((path === "/" || path === "") && !isAdminSubdomain(url.hostname)) {
            if (method !== "GET" && method !== "HEAD") {
                return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD, OPTIONS", ...corsHeaders } });
            }
            return createLandingResponse(request);
        }

        // ====================================================================
        // 5.1 Web: Admin Cloud Dashboard (GET / on admin domains or GET /dashboard)
        // ====================================================================
        if (path === "/" || path === "" || path === "/dashboard" || path === "/dashboard/") {
            if (!isAuthenticated(request)) {
                if (path.startsWith("/dashboard")) {
                    return Response.redirect(`${url.origin}/login`, 302);
                }
                return new Response(renderLoginPage(), {
                    headers: { "Content-Type": "text/html; charset=utf-8" }
                });
            }

            // Fetch list of trainers & media & SMS in parallel (Promise.all acceleration)
            let trainers = [];
            let totalSize = 0;
            let mediaList = [];
            let totalMediaSize = 0;
            let smsList = [];
            let totalSmsRemaining = 0;
            let totalSmsSent = 0;
            let smsLogs = [];

            try {
                if (kv) {
                    // Stage 1: Parallel list queries and sms logs fetch with pagination support
                    const [metaKeys, vmetaKeys, imetaKeys, sKeys, fetchedSmsLogs] = await Promise.all([
                        listAllKeys(kv, "meta_"),
                        listAllKeys(kv, "vmeta_"),
                        listAllKeys(kv, "imeta_"),
                        listAllKeys(kv, "sms_trainer_"),
                        kv.get("sms_logs", { type: "json" }).catch(() => [])
                    ]);

                    smsLogs = Array.isArray(fetchedSmsLogs) ? fetchedSmsLogs : [];

                    // Stage 2: Resilient parallel/batch fetch for keys (using k.metadata if available, or bounded batchFetch)
                    const fetchMeta = async (k) => {
                        if (k && k.metadata) return k.metadata;
                        return kv.get(k.name, { type: "json" }).catch(() => null);
                    };

                    const [metaItems, vmetaItems, imetaItems, sKeyItems] = await Promise.all([
                        batchFetch(metaKeys, fetchMeta, 10),
                        batchFetch(vmetaKeys, fetchMeta, 10),
                        batchFetch(imetaKeys, fetchMeta, 10),
                        batchFetch(sKeys, fetchMeta, 10)
                    ]);

                    for (const meta of metaItems) {
                        if (meta) {
                            trainers.push(meta);
                            totalSize += (parseFloat(meta.file_size_mb || 0) || 0);
                        }
                    }

                    for (const meta of vmetaItems) {
                        if (meta && meta.filename) {
                            const sz = parseFloat(meta.fileSizeMb || 0) || 0;
                            mediaList.push({
                                filename: meta.filename,
                                type: "video",
                                file_size_mb: sz,
                                upload_date: meta.uploadDate || "",
                                upload_shamsi: meta.uploadDate ? toShamsi(new Date(meta.uploadDate)) : "-",
                                url: `${url.origin}/video/${encodeURIComponent(meta.filename)}`
                            });
                            totalMediaSize += sz;
                        }
                    }

                    for (const meta of imetaItems) {
                        if (meta && meta.filename) {
                            const sz = parseFloat(meta.fileSizeMb || 0) || 0;
                            mediaList.push({
                                filename: meta.filename,
                                type: "image",
                                file_size_mb: sz,
                                upload_date: meta.uploadDate || "",
                                upload_shamsi: meta.uploadDate ? toShamsi(new Date(meta.uploadDate)) : "-",
                                url: `${url.origin}/image/${encodeURIComponent(meta.filename)}`
                            });
                            totalMediaSize += sz;
                        }
                    }

                    for (const acc of sKeyItems) {
                        if (acc) {
                            smsList.push(acc);
                            totalSmsRemaining += (acc.remaining || 0);
                            totalSmsSent += (acc.total_used || 0);
                        }
                    }
                }

                if (r2) {
                    // Parallel R2 queries with error boundaries
                    const [r2BackupsList, vObjects, iObjects] = await Promise.all([
                        !kv ? r2.list({ prefix: "backups/" }).catch(() => null) : Promise.resolve(null),
                        r2.list({ prefix: "videos/" }).catch(() => null),
                        r2.list({ prefix: "images/" }).catch(() => null)
                    ]);

                    if (r2BackupsList && r2BackupsList.objects) {
                        const metaKeys = r2BackupsList.objects.filter(o => o.key.endsWith("metadata.json"));
                        const metaObjs = await Promise.all(metaKeys.map(item => r2.get(item.key).catch(() => null)));
                        for (const metaObj of metaObjs) {
                            if (metaObj) {
                                try {
                                    const meta = await metaObj.json();
                                    trainers.push(meta);
                                    totalSize += (parseFloat(meta.file_size_mb || 0) || 0);
                                } catch (e) {}
                            }
                        }
                    }

                    if (vObjects && vObjects.objects) {
                        for (const obj of vObjects.objects) {
                            const filename = obj.key.replace("videos/", "");
                            if (filename && !mediaList.some(m => m.filename === filename)) {
                                const sz = parseFloat((obj.size / (1024 * 1024)).toFixed(2)) || 0;
                                mediaList.push({
                                    filename: filename,
                                    type: "video",
                                    file_size_mb: sz,
                                    upload_date: obj.uploaded ? obj.uploaded.toISOString() : "",
                                    upload_shamsi: obj.uploaded ? toShamsi(new Date(obj.uploaded)) : "-",
                                    url: `${url.origin}/video/${encodeURIComponent(filename)}`
                                });
                                totalMediaSize += sz;
                            }
                        }
                    }

                    if (iObjects && iObjects.objects) {
                        for (const obj of iObjects.objects) {
                            const filename = obj.key.replace("images/", "");
                            if (filename && !mediaList.some(m => m.filename === filename)) {
                                const sz = parseFloat((obj.size / (1024 * 1024)).toFixed(2)) || 0;
                                mediaList.push({
                                    filename: filename,
                                    type: "image",
                                    file_size_mb: sz,
                                    upload_date: obj.uploaded ? obj.uploaded.toISOString() : "",
                                    upload_shamsi: obj.uploaded ? toShamsi(new Date(obj.uploaded)) : "-",
                                    url: `${url.origin}/image/${encodeURIComponent(filename)}`
                                });
                                totalMediaSize += sz;
                            }
                        }
                    }
                }
            } catch (err) {
                console.error("Dashboard parallel query error:", err);
            }

            trainers.sort((a, b) => (b.last_backup_iso || "").localeCompare(a.last_backup_iso || ""));
            const lastActivity = trainers.length > 0 ? trainers[0].last_backup_shamsi : "هنوز ثبتی انجام نشده";

            mediaList.sort((a, b) => (b.upload_date || "").localeCompare(a.upload_date || ""));

            smsList.sort((a, b) => {
                const aPending = (a.remaining || 0) === 0 && (a.total_credited || 0) === 0 ? 1 : 0;
                const bPending = (b.remaining || 0) === 0 && (b.total_credited || 0) === 0 ? 1 : 0;
                if (aPending !== bPending) return bPending - aPending;
                return (b.last_recharge_shamsi || "").localeCompare(a.last_recharge_shamsi || "");
            });

            const isStorageDomain = url.hostname.startsWith("storage") || url.searchParams.get("tab") === "media";
            const isMessagesDomain = url.hostname.startsWith("messages") || url.hostname.startsWith("sms") || url.searchParams.get("tab") === "messages";
            let defaultTab = "backups";
            if (isMessagesDomain) defaultTab = "messages";
            else if (isStorageDomain) defaultTab = "media";

            return new Response(renderDashboardPage(trainers, totalSize.toFixed(2), lastActivity, mediaList, totalMediaSize.toFixed(2), defaultTab, url.origin, smsList, totalSmsRemaining, totalSmsSent, smsLogs), {
                headers: { "Content-Type": "text/html; charset=utf-8" }
            });
        }

        return new Response("Not Found", { status: 404 });
    }
};

// ============================================================================
// HTML Page Renderers (Dark Red Gym Theme - High Performance & Responsive)
// ============================================================================

// Embedded Nemov Official Logo (Base64 PNG for 100% self-contained delivery)
const NEMOV_LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAtAAAALQCAYAAAC5V0ecAAEAAElEQVR42uz995NcV5YneH7PvU+5FhEeWgCBgGBAECSoRYIpKkV1VU2JRc/29thYre3s7Nqazdr+B6z8K9Zsf5idtZ2ZtR50VXdXV3WWyMwik8lkkklNIKACgdDKI8K1P3/i3rs/PA8gAAJMsjIrk5l5PmZhUKHgEfH868fPPQdgjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxhhjjDHGGGOMMcYYY4wxxj434puAMcZ+K6/hhm8exhjjAM0YY+yffw03X+D9cfhmjDEO0Iwx9lt7naZ/4fDMYZoxxjhAM8bYl+r6az7HtfmLX6svXbr3Npcvm8/1+p9+PQ7TjDH2EBbfBIwx9mstXNChYPqrKWocDtcP+/vPE7gZY4wv5Iwxxn7F11z6jIou/dLD8WE7O5/9OkND5oEQ/bDP87NCPwdwxhgHaMYY4+sjftHDevSF3u+jgvDPqw4/7O0eFpjb7Ye//2zW3A3Rj/6Y5nNOAeEgzRjjOwjGGOPr3hc6kPfP8yoI3wXwav/P8w+E4rl+oP3ufW9z/58PB+mDAP2w0Oz7yd+lUuZTIfrBIP1gmP6sanfyehyiGWPgHmjGGOOCwb+87z7w+0uPDNoPf5svaA7APD6j3eNwiP68Fe5Ll4DLl7mtgzHGdyiMMfYbfJ37Rce9mV/BshN66Nu/eigkv/oFQvirD1SvH1KJnvN9ui88H65EA/dXo/FA+8fBv7XbdLeSffA+DreCcDWaMcYBmjHGfmOuZfQF2g3wJR3hRl+4/eNh5i/RfZXifgi+AOA9AJ8KwJ/l0OvO9X8Np8K7f7ew4pj7gvT9hxINb05kjIFbOBhj7EtZBKDPPZni4TOQvyzMv2Sx472D35wGcLX/6+KnX2/ucMA+FJrDzxm0cenSwYOVzzP7msM0Y4wr0Iwx9mtrzXjYYTo8MLINj6xI/7xRbl/u6/jhavT8I26HBw8Wzvh0UFWev/roKjMARP74pz62nVo3QFKFngMwf7gK/aiK/8PnT3PLB2OMAzRjjP0LzVL++RXmRwXGz5o2MXfZ4Lu/EQH6599Or4L+WQG6H57D1hTdC833V6JVENz9s3RdczhEA8BCtaA/83Y+/Pk8PGRzkGaMfekIvgkYY78BQfDwCx74/T/f4fD4sOr0q6BH9hR/+ZmHjr77HA4OFc62puhR4VkFAT0sPONhbRwP3s4Pvjzs3+49KPrlfK0ZY4wDNGPsdyg0s1+xuV/Ke5n9xd6cQzRjjFs4GGPsC4dn/NLWWT9YXX5wDBseaC+4t6jE/BYcbKPPbOM4uC1mPn1IcPZQ9Rn4fO0bQNLC4aw4Zh64N9HjYePw8BnPCHx6DB63czDGOEAzxtgjw/PDepq/yJSMVx+yve9RYfphvc+/PeH58Cxp+nkj7fBAL/ThinTYmqKFQ3Xl6CFTOZLe51kAC1jI9UfZLR6aCf15gjMesVb80wc7OUj/ZmQL/joxcAsHY4z9S/t5BwJ/mQ6H57nL5rc0PCf/h+8eepm7fP9UjIcF3MWUwWJSPZ4H4ORWzOwXaNuY+2V+9p9u53hUbzz79YZmAUD2fxWH/sxfH8YVaMYY+5VUnx+czPCwCvSrn7HC+lV8kdXZ5nesYkafa8QdcH91+FBV+qC9Y+GB6OzkVsz83XnSn7N941EV6IdNSnn0MxG/a1/DL1vLlcCFC8lGyrA/7tBxzN1lOq+/rrkFh3GAZoyxf6mZzp83QL/6zwrH4C14nzHq7mGB+rPG3s18eiPh/GLK/NwxgZ8V0h+1EfFwOwc+s72Hg/SvsuJ84YKA7xM6HTGhFEXlstBxTAAgLMvY+/t6zfM0xscVXn/dAND8dWEcoBn7zfte5wv3l/vrI+5urNvZoYfMBTafuZvv039PXPX6JYXqnxes8XNaZPAZ/eiPCtCPCtGf9b65Vxq/kvbPixcFqlUxkW/KqFsWcRCI2POkiSJhtCYAICGM7PWUk83G291u3A/Ruh+iGQOv8mbsy3yhv3SJsLgo7t4Bv/664jvV37CNgnOXzX3tGvS5SwJ8R/2LeLB6by4b/MWhW3mu/+/zl+hL/v3FP++/7Krz+roYTqetrvZknI4tBdfSomd5aUvCCEKPjIhjZWWzcY+IhtNpbK+vAxcvAq+/zj+bjCvQjH1pv7cvXRK4elWOplJW6LrSxDHJdlunK514GUdiDtJfwvD82dM3PutrxV/HX+d9whddNvMZWxHn+hXo+Qff5lGVaODT1ehHt3Tw98ovITxP7+7KXqEge0R2bIzjGuMoF44F2Np2bRhDULGWgYniKAocKXtRt9vzfD/aLJViVCqae6IZB2jGvozf1xcvyumlJas9Pm4HduC22x27nM1LoZUKeiL0Op2gCoSYn4/BlZAvxzruBwP05btV59/UnlZ6aMz/i1fpYW3c86fnH3I9vgTg8v3Z8Oqcue/85F/8hbn74eiRDy7oMx9yHPqcHum73/3l3P6fdXjxgVaO2akpWlhZMZ8K0T8vQD967OHnOYDIHnFNRbUqpjsdcRCevbRxwtD2BIJ07IiUJulF2jhSSrKNUSJQgYnRcYBOhzod15e9vV4vwuCg6j8baA5df/lrwDhAM/ZrD89Yslr+sBMQpeKsnXnq+XOpqx98ZFFbKysK/U4kOh5Rd39/P8DCQgxA8U33a7vmPDxAz102X4LwTD//6OG9T+vVv/gLmj99mha//33hj9Yo3B+hqNwk1ewSAKx1fEKtlbQTBREhjAmxSj5GFBOymtAAENcIyAMZTeiI5ANY0kAKA9tK/px2NVzbwHUM6q7B8ZSZWANkOm3sfN4AgFPeMqmxkvE3anR4TffsfosOpmfgVv/X4ft7j6cBLANAPmWwlTMoLRrcyN4bfzc3Z/Dd75pfWoh+yGKX2VZICyvOryJAc4DD5+93jryuDMOsa1uRJ2wvYyzklRQ5n0zm8cfnvDvLa6JXbcS2oQ6CuAEyDerpRqxUN2VZQa7bjRccx/Qr0eZQJZq/BowDNGO/rvA8m1qXteaQY2VMqh6HudLR8dL/5b//P+X/X//T/8feX9qMM0q3qaPqIqKGolq3vI9g4YknYly+zKfDfxUh+bOWn3z3UFn2u7/yQ2CUVIj7n+sDfb2XkoB/3xvsXL1Kr29uElZ+KFDtSMiMBdGzQI6FlLThZS04KQuukPDSAjZJSGPZqYy0PFum3JT0UnmRkcJy0o4UliOJhLQtIY2BMFqTlBa00SaKI6VjreJYRd2eHytl4lq7GcWhiqN2I4YfxegGMcJejKAboxMpxKFCaGkIYZA/CKEZyuayAIBcLocccmi6MWUBtNFCuw2YuiKyfANLGhEHmkJXy6yvZZjSlp/TzkBLL3eH9H2h+uEztB/29aOHhunDy13a7WQc2mkAV4FfYoDm8XdfdDzdxYsC6+tyotcTUbksIs+TcbttxamUa7lIk6E8PFEKbSo5lULh//7/+B/S/+5//d+sxfevxHnLbZputEfK7EWh3tNx3HTcbs9DKdrc3dXIZDRSKYOZGY3Llw9uf35GkHGAZuzX0fM8bFl2t+J6wkrnGqY1cOHrXx/+b/7P/3bwb/76e94P/t1/jMp2pm787k7sd6tplanHRH7WXo/6fdF8QvyXvYb78yxGSarN+BW3bNC99dZX5aifsoJCxUp72grh2o6lLWVIak3SD9ui6fuEWo+gfAGlBQppgULWQjpv54p5J18ouJmBvJtKZ7xSLuem8zknlUnbjuvaXtazHEdaRtqWlMKCFJa0HAtENoGkJNhGCMvAWJaAFZGwBCAALZJyNRkNxDpWSgCRIQq11pExCI0xoYhUaOI4jMMw7AVB0PXDIPL9MOgGod/uRJ1uT3XrddOst0yj3jKdRgOq0wH8HqHTSW4N2xGwJOC6SLsZWGSUDSitTEikQx2KnjJRL+r0etJO96yUH1ltHTs6UJtxRaFa1cgeCtOf/QCIHlmVPgjSnzUb+rNmS//zwzQH6YcdFmw0xGihIHUU0cGkjbRlWYGUHkmVNRlZFGl3YDfoVeYuPlP+8//r/zH3Hy7/tfPWX30vLlmpJnV7VXTDTR3SNsmwprqm4wKh22yqNSnN3RB9r6WDq9EMPIWDsV/l8o2rV+VEPi9brm87ZLvaiTOQ3sDEudmxjifGTzx1JvOTt96O/J3abkpa0nbSUa+jQ6216tpHDJaWgAsXFN57Dxyif8HwfOlQNXFn59Oh5vDBsaEh85BlKOZfvJ/zCKyB1YLtlHyX5PFU0FUZP2hlG7u9rNJRFrHJQAgPwrjIZWxndMQaPDtgVUaHZGmwaKULBTtXKriptJtyMumU7XlpWFaGbOEZSQ4BdmiUFYGEJCN7RgtlIMloqUBCI7YESEZaSQASMNLACAOSBpqUIbL7jc1EgDYwJGEEkSJNGsIoEGIiqYRLsRB2ZMEJbeSCsqRAQARkqCcNBVrpWGoTx2GkQj8ycdc33W4HnWaHOrUa2vUG7e3VRbW6i85+w3QbbY2gF8OIEJblW4LaELLmWu5+qpyv20bWOySaSPU6PfL8gu8HjZlsPIFArQEKr13UuHQ3SH++r+lB4H71cjLd48F14wB+bqh+2Pzwn/cg7l645mkdh39G+ocFw8FBEfu+UNmsMLZNxvaFJiOMgIArhQRZobQdlIQ389SZ7J4wxaOPn3Lf+dFbqt3oWp4lI+FYHW2CFkVOV1kqiO22ElbZTDcaajkMk8Urvm9w8aLuT+ggnhfNOEAz9i8dnHd2CFeviulKR7QjZSmVsk0KKeNQ1hsoDY7MTE7txcGRwpGx3LEnTsdXf/DjYibnUnc36rpp3bFjHYSoq+FCwWw3GgYXLxoes/QLBOeH9bMeDj4Pqxze37Zh/sV6OV+9KKaXjlgo1r24E2TrjXppL/SHEAbjsJxx5FKj6fFKJVsuFEojw+mxkWF3YHzIypSL0s1lhOXZQrqO0AIiFiQ0aalgZAgj21pbsQ4sY5QMYyNCrcjAkDYGsdGCYEAAxWQohoAwEAYgI0DSaFIGBBhSQpIgQGgDpYmkIJDREASjjAEIRhmCBBmptbGk0AZktDGaAG0IWgBaQsREQtkgJUhoQcJ4GakpYxuHPJTFIAaFBQcExDF0EJEKIvQ6Pjq1lt7bquqdjW21s7kddvf2g1az2ep0OrXk/C1t2razYbuprYyUVSttarnYatejXFCKa5Ez6cTbckdh/pLGqzsa85+qSn92kD6oRg8NmftC9M/baMij736ZbRuiVyjIuN0WRilSQSCgNRmRoRYgnGxMMIKijEdthLI4c8QZmp1J7ca9TOXoRLowNaz3r62QHaEHSQ3HclKGtB2F0lK+F8cq0OHgoJne3dXLtm3uXicuXKB+NVpwiGYcoBn75Yc1wsWLhMXFpFey0hFdZKxYSMtxPMfYrleLotzg8MCQXcyM70X+ZC6dyT329Fl19b0P0u1GENlpa4/CeC+G1dZtEepSJ55ID4o1nlX6i6/fPuhhPWTuNPqb6vDwp+F/ueE5+divvkoXNjdldjSQq5tdd/POXna5dn0A2+0RWM44yvnx4tGj4+NHJkYHhirDw2NDA4NjwwU7l05ZqZRNFslQEoVGU1dFpHSMQHUQxDFpGGgYKB0jIoIxIAmNEAYBYGwBGK2T2CwNDBEEgBiANAoaBBgDSwARTPKNRpQUl0GwCIhl8g0oBGBgQCZ5G0UCygAWtOkZBSICIQnayiQ3oSBhjDGAAaQxAKQRimAMjE2ARQIWSThCwhYStiOQSjmwymlUpitmTB8DaTIUxjpot1R9Zzfc3Njp1ja3m7ub1f2tje1qvVrbRqOzBbK2pOdVPcve12mrqex0q+zLbhTt+84HUZgt7UTL83Mar1aSMP3wQ6IPhOjLh7vPv5idHXpoJfphDr53k0o0PTC5xPwOniMRWF+Xo4WODNtS6Gw22SyoNZmMIhNpSqdBkXaIPAvwLCiKxcknT9ui4Lr7cZjK5fLpsWNHzf6NJS1TomMpkdYGromV4yKwY8eNtJRKR5FWo4qw+ZDPJLkGc4hmHKAZ+6UF54PVsdUqEIY0PR5Rr1aQoW1LlUpZPRk6OQ8eoig/PTtdEVlvuNNtDoUhMiPHp/Tw7FFn672rPduz1lSoV402dsaNROhnhVKRnh6PaLlaFbh0yeDyZX5a9/M+C/BgcJ4KadofJwCwU+smbAELAODj/pm+n3/d9ufracZFMY0jlteV9vrK2957G5sZLKg8bFnGeHFk4OyR6cmjkzMTR6aOlkaHxrLlYjldymaE5zpdHctARaJtFPWiBvl+DGVi9CgJwD2joLWChoEWBAkDEkAIQBAZIQixMjBkACFgRPIYTBiDUCStGMIQKZ2cWDT9QH0Q27Q2EIIQgxDDgAygCNAaEIKSV6P+4zoCYoCU0cZowBKChIDRBiACCIrIJIFegGCTIm2ECZQiEMExyft1YkAQgQxBEMGChEsSlmXBIwnXspEpOygMTrtDZ45lJGQ5bLcnWnuNoF3d71TXduq3F5d2dtc2tzrV2g7qrSr03q60U3u5YmbPEqVaGFFz1Mp1g4U4dH0/3oxjhc3/XuPiDYNXXtf9Ng/z0Ep0crj385/nuXSJfm5oflSQ/t1u50h+nqtVMR1F1PVLwhSypIOATCoSWZWhZqQp4zgiVkTwYoInRVuHwh6v2DOPz7lVFaVaQS89MVBOT548aq784EcxQkqRJT0dx662yIZKWynhy0BCxm2lt+1hA7X98M+IQzTjAM3YL7xkI6k4t9uERkNMRxEBgBodpbAdUZxtCy3ywiOyyHLsWFAatsxPHpseUEIN7rXrBTeV8grFAZx75pzcur7QNYEaUlaYd0OyTCpFCA8m2R0BwvVke+GlS+DpHJ+j8vyw4Ozfe+XIHyc7lTKzAJzTK0kVOnvf9Abzz183nVSZd0cD2e7W7L1PVrzlzj9lQU4R5eLIwOMnp0aOTh0dmhw+Mnpkcqw4VBqU2VReSZExQrtdHdnbcUsErT3qqRihVlCCYIyijtGAIGgSsGAQk4aUgCEgpqQaDEqCraDkU9ISsAwAoyCSDmYoMsnrAoAROHhTIQjGJAHXALAkAUTQWh+kYGhjIACI/si8g3cjiBBrDcCQLQQ0GQTakNU/dgijQQJQxoDIIDQGijSUNFAGkIKgtUGA5M8REWwDWCAoBcg4uYOwTXJje0JKW9jSsxwrLW03NV5MDU4M5IbPHh84Gz4zEbV7wd7GTm91YamzeXu1tbaysVvf2l1Hz78DN7uU9dyNrJXe75XQGYrCwFufD/0hGVXnn1O4NKmws6Mx9LrB5c981uez5jgn35MHIfjSL7wdkX6HDhXeK040GqRGR0nXamSUIvTXcje1powTCe0IYUDCkJAyZVtx2PVOnX0sk6nkC8v1WrEd9AqBUenK+Ki2ygXtb9WbRpALIW0bwpapQLY7rrDgk1GKhqOI7IkJg7U1WgMA2zYIQ3rgQTYXMhgHaMa+4CSHe8G5WiWEIU0M9oTCBFQUEaIIse8LjaxIZ33Zs2FLK+WFQFaUcuXScLkSQpe2/FYa3aY7ks+ZqVNHqTwzXq5dXaiU0m5BRz3bKHPfne3sLLCw4nOI/jyV5354np0K6SAsqyC47/aUrmsOzyF+xLSGz+/VV2kO8xYAZ+/2T9Lv7ezmcac3gJQ3LKYGRqZOPTc6e/LYcGFsqFIaGaykC7nBWKLcM3FuV4VuN2rIwA8p1BEFJk5CpDAgKWAJjYgIQghoIRAbAFBJCCaD/om/fjsGQQiZxF+jYCDgQCSVZWNAINhEIG3gEkFCwIAgASilIEUShI0BSJukJm2Sno0kWBsIIqhD86b1wc4UY+CCQNQfK60NpAGM0fcinwYcElA6aQtxCWRAiISArxUsAaDfWiINEBnAECEyBpbWUDCIjYExBr6KEMVdWJFFjiFIkpSSlswI2/FsJ50uu6Y8cFSPnzuuyA+ivc09f3dts7l6e2Xvzs071ebG5m67sbMHQ1XX9rajQmpbwtkZjpz9Tmuz7RZ0L7tzMVq+0FaYmdH9BTJfZDLGg9sI8YWD9IOve2+02m9zgLvX91yt0nQUURhFhAEAAYACYIIMZVMRqcAVyiFLObClK922MVlU8uVTF06PNI0eq/faY/t+r9iKfKdQzMYD4yNme3uvIV0rRbFyYUdS96T0ZCijyBOmIEn7PkXdrrABPaHUvRB98IA8qUIbDtGMAzRjXzQ4t9s4qDqHg4NCRQXoqHv3jk4XFWk7pqb0ZKxiu+hYqY4OSoPjEyPZcmGwEfdy3aDrbrc71mylgsliGXNPzuV+fGupEglZprRxe92mTJVtoJq0GywsAED/dPjiInis0iMqzwDmfJ/CQ+H5s954IbdisJgyyP7zPvbFV1+VW90PUtX1twvzG5uD6PaGURmolM4eHR49Nj0yOzc7PjBWGXfymWGZS5cCYdIdHTsbYV22w57o6QA9o6BgQEQQkhALDSkICoAhhRgEQxIaGtIYWJTcbwshQEBSidZJZdkBQcc66VfWgAMNIkKsDSwQyBhIApy77REGsv8tLiENtEg+DyLYgiD7VWwBAglx97Y0RhtjkupzTP2QbDSMMVCxRgTAJUEwBrHSSb80ESKdhHASgIGGICQBnhRsYyBhoI2BEsmXVQgBAZX0TIvkGz7QSY+2JQ2kJHSMQqQBmIjqoYFlAKsnyJM2XCNE1vZkznGd3LFK5rGTEwMnXjg/HdRbcX2z2lu4ttBeunZ7v7q6uVXb212Dxpqby6/lyqn1KMLmTjncLQ2hlVldDdeiCzEwo/Hq5S/S4mMeqFjSp0bYXXrEGnE8ZBxe0tbx27xs5V54brcJYZhUn7tdgtv/D8cZMjoiJW2pclIqqW1F0tUpK9eLO5XZx1+YKk0Oz2wHnaMbfnOoE0SZeq8rh3KVcGRyzGx/cLVhLCujZegIWJYQShrhiLSMRNBVQmVDgza0Gh4mub1t+NkAxgGasV/kcOChijOiiCaUonB4mHS/dUPHMQnLunchVZo8O5TGcZxIylwUtisj45VxJ+cN9Nq1dNv3rSD05e2dTZRTGRw9cyJ15WefVFo3V4azrsg7gbNr4pjkwWnwWfQbdgH4fnIH87t1qJDw6HnbdHj18nz/5npUeJaua+xUyjh3w/OhbXaf43N49dVX6W/GNuWdH62kXn/zchFxNIpi4fjA2RNzM48de2z82JHJoanRAaeYS4fSuCEpe1eFViPYE50ooJ6OqK1iiknDsiRIEAUAFBlkBPo9x0mQhAYMCVj9Cq8kgjYG2gA6VrBgYAzBAiXtDTDQRLBB8CwHkiSkSPaluCRgE0AkICEgiCANQEpDawOtkiZkFSioWAFGQykFrRSo3xqilOq3ehhIIWBJiaRsLUC2BSksWEJASAKkhJEChgBFSStIrCJ0VdKzHUIj1Apax4i0RqANFJLKdGCS6rdRSduJgkZy/DGpTlsmqbZHMFD9w5NSADoZSg3XaPRMDzrSUGGL3LaBJ2wUnRRlnZQolrOiNHjUfvnsseyLflzZXlqf2bq9HCxeudW5c2txK6jt3UJkPkl56WuWO7DSmcb+hEYn2NkJq61vR7joq36v9Od9IGt+oX0Hh6fGHCzP+e0L0vcm5ywuJq1x4xGp4CGvmVKkIy0UhG1Z0g0d5BRhEMX89NFzp06GEifW9mpj7SDIkjZO1/eJSuSUxkc0XLcYhyZnkUxJV9iWhAjaoWgbTVYGZKICadUmHUUkATMNYLl/nQeQPFt18SL1r78cohkHaMYecQL8bksAwpCmo4iUUqSUotj3hVbJ2mMh5X0XUJPOkBFa9GLjZCQK8JzR0vDQREwoNYKeExktHEG0Wa9hp7Qvjw4OeScePzX4zuL6RKzECGBtF7LZlvLqUXKqq9/G4UeE9f4dalKN+m1/KvfRgePByt1B60YYfur1vWJRLwBAbiW5rRZTBn4lqTx/dnimg6Ual07/b/TBG29Y333tP6bQqZUxUZktPXn63LHTs2ePnz5xpDQxPGwXsiUtkWlEPWcnallN36dW2EUPCoExRkFDSUG2KyFIIDlglwRjMhqASAIqAaQBi5KqshUlOc1Aw5CATQRP2CAYpGwHGduFAMGBgEwewIGUQtSLgCBA4PfQ8wM0uj46nR46nTZUL0TP9xG2fBMEMVQYIu4FiKIkQJt+eFZxDJikmcNoDRKUTNkgghBJUBZWcshPSguWLWF5NmzXhZ324KZTyGQzyGTScDIeMtkMZNpDPuXAchyQk4KdtmCEgAahB4VIJYsM4zhGR4VQEIihEBkD1V/RKAEERsMlwBKEsB+6iQx6RFBKQ1qaLCK0lUZd+Wj1fERdiZSwxaDjIm17VHBSduHUqDt6+kjm3CvPFPY3d8qrN+6MX//g6tzOnfXVanXzFoQ7b7LZRWvM3sj0Go10zulW3/52hEu5L7ox1DxQlb6/tePBMXkPhuhs9t6/J61cvy0h7v42rIN2iSUAo8krCFsaE0uTBxApTaHlSNuGHQmk7JRd9I2aGj119OTo7OSJqt8cX6vvFywduybWYq/TRAgtyoOljEx7BeV3CragtCHlaFISjkMgm3QXguJYU0GRbsekhhWt7Upzd4384a/DvRDN4ZlxgGbsvq1XFy8SqlVxUHWGUhQqRbpSIR3HpJVKDrWUAbQfCNBKkbYsaaRxQx0NUDY1Vh6tDIGQbfUCqxNGYkhItHs+LVarGCqUrNlzp4of/fTjqWC1etz1rI1ar9VIO27o+OMaqXWzAGAaR4DxJVpebwgsLuK3tB+aHjrJAI9YUPGIhRZ2at0As0mbxuHQDAAzjwjN85cIl0DAZWDnIs29MiRSmyVr4da8e/lHr+ZBNOzMTU3PPfl7x2bPnDg1Mj1xysqnjyhbFJoqcJrBPu312tgPulBQFJIGhEnGyhFIWBZiowGtYQt50OoAAQOHBIxJDtJZAGyNZOO2dCCFQMYScC0btrSRIgIZAR2EUJ0AQbeGZq2JTqON1l4d9XoTzXoD3WYLYaeL2A+gewGgNKAMoFRyajBODiXCEEAyGYPRrxYnDQcCMEn7BSiZ00H9g4ZJFNR3Dy4eHBRMRnT0cwVRv0Ldf5wnBOBYEJ4DJ+3BzWaQL+ZRKheRLeaRKeaRLmSRzudQyaThptIwbgahJRCqCN04QieO0YtCKDLoagNFhPjg/yOoP0lEw6Lk4+v+AUlHCMTGIFIK2ihq9HzorkFR2ChYHmUth4YyeSqdGstemB3LPv7KM8Mbt1eP3v7k5omFq7fm6gsrd9COF6WVup1x5Z1Kzt8RddXavnAhxB+8p/4ZYw8/3SN9+Pv8YUtaDv7uIEh/uhptfivOMPSnGalgNClQ2LaBA+jIMkIIg1QGJoZQUjjKUnlNGEXKPnb66cePU8aZ2N/eKbZ6vpsSkM04pp7fhh8FVKqU3Vy5kG3st/KORBaBcRSRhIyFF2gRpojQ0GSU7t/2Y5hQ27R80AcN4G64vzfykrgKzThAM3a3dePi3Qv5QXgefVh4PkTYtklaOgaQQ4ROpISb9tx2pMrZXHFooFIu+FHo+EFPCKUo6k8z2KzVsNtsyuGhcmrumXNjH6z942nHtVdEGOyFncgPc4GajWfVAhawjKUkREdLSZXmt+tQIX1maP45gfnAwhNO0poBAKjivtA8d6j/dP7+1g/M+ISdihiedGSYvmQ5bt2d/+FHGaiggInK4NjFC5OPPfX4qenjR87lRkvHlWMNdnTk1Xp1a7fZoXbQJt/EaEPBkUSwCLHRICFgoBGbZN6yTQJGa+hk+QgcIxAbgQwJSCGRtiQy0kbGcuAKCQsStjJQfoDGdh27e/vY3dlHY6sKv9ZAu9lGp91B1OoCQYSkIfjgFiWQECBhJb3TRoBAQL96bYwy2hiQENCqf5xQaWijQSDoKExaMQ4Cs+yHZ0pm2QnLAkAgKWH6k0IsR97N3oIIShDooKfZaOhIQ/s+evsd9EwVDaWwqg0gCcnqbgdONoNMIYtcMYf8QBH54QoGR4eQGyyinMuA0hmEpBFCo6tidKIQsVLoqBg9pRBBQYukpaWHpO86BhDCJP3hgmBkUuVvqwB+FCD0DW41qjTgpMyAl0E5nbcGzh3Nj5+dzZ7fqU3tLK5euP7B/MbSR9fmd9Z33kcvvpEul9fHxif2OrdG2uk/2Ao2U34MnFb9Pucv3t5x+TJw8eK9gPaQ+eUPrUon14DfxINt/Wo67j8ADKAXjJI61Doh9m0DF2gAiJUmy3JEaIyXSqdLtbg3WTl5/NjYiaOTTb9bXNzd81QcyUCQkEajHoQmCAMxWMjZqUIuXYfOk+XkjKUcK4CITETQLhnVI5NRhKjUn28JrB18AofbOB4eoDlEMw7QjOEigGr/jkspwkPCs9GaUCoBqnZfiBZ23bSQAUlLuJZwlA7yqUKumMllvUYcW2HPFxloCBJQxsCPQlrf26XBfME+8fip8rWfvH/MX9o6lXWdLStSjV6vF8t23aAIjZRtln3Q9JEjWF5fPzxaiX4rnsL9PNXmz5JKGSweunMbeiA0P2hxUaDSEMPOUcu1fccfglvv+ulgebUIWw/nz52YPvbE3Oypp+ZmyxOjEyplD0ZC5Zf9VrrR8e39Xoc6kY9IGBIC0DIZ9RYIAxsaymjYJEAQsAHoSMMIIEMSNgTytgdPOEhLB3nbRlpa0JGC6vjo1nextbWLva0qdta3UNveRbfZQeT3kpAc93t7ZDKDw7YsSOHB2CYZJ6cNtNEwgYIREXTUH4uoVBKAVRK0pecBpJNqt+P0DxECnpeCjhVcz4NRGlEUAQSEQQAhJWAMIgBBEEBYFnphgFhpKAA6DAHLAoIg+VWI/vM6SUU75XnwoxiuJWFZQKgUdJLPEfsaYaeBcLuOmo6Tt3NskGvByWaSED06hOGxYRSHykgNlFAsZGFnM9Ck0Q4DtKMemnGAUCtQFCLUMTQl4VlTMstaAGhqjUy/OYakgYbGqt+jlU4dXr2KgpsWI6mcGC3m5MTTJ93J8yey3erXxhav3Dh/58PrKyvXFq91l259jGzutp0rbQ+ZsWakar3MpefCtatNhdOn1Rd+cPtZbRw4dA7i4Pv94MHkpUvi0AFF85s6PQeVjugF6qH/f2HXjbBTGuQYI5UQnp0KhKnorDPzxPNPTdqFTGlna9Wr9XyZISM8IdCEQCMIqBUEGCkWRLFSdjaJMtAmZ0AuhBaAC6QM0EuR0Y271/n+GRcDANP9EL18MNau3abkjuJ1Ds2MAzRjdy/sh6vPAIYfEp51LkeIYwirZFDxgfan31EkjG0MZcpDA1knnbaDdk3sdTroKE2aAJeS7XALu1UzURkSk6ODqceeOjv8wfr2nLTtdR2b7Thwek6uE89iVi9gAUitG/jjhFkAKz7dfSr3N7cf+tGrtz/rMNXDHD4QeBCcH5yY8CoI85cIi4ti+kxWym7JrTsyt99SlahdnUAhNzX+9WemLnzlqYmpkzNjVikz3CNV2Yt6uVpn39n129QOOiY0ihQByhKASEbJmf5GvWQ6RjI9wyiDNARsk1SY87aDjO2hYHtIkwUZA0Gzg/rWBm6tbKC6uoHa1g5q1X2YZjtpuSACpAVhWbDIgiQLsBzoOE4CtwoR6RARCSCM4aRTIK0hpcTASAWNZhvTs6Po9gIUCzlkMmkEfoCR4SFoYxBHMVzXg2VZCHo9FAaKuDJ/A19/+QX8p7/9PmZnpjE9NYEfvvYmfv8rz9Hq2gbGxkbx7nsf4Pe//Q387fe+j2OzRzFYKeP7338N3/jGRXz0yVUcmRjH1s4emq02bCmwvLaBYj6HpeVVlIsF1PfriABok7SOKK0BS0JKK/mOsBx4toXIGOhejMBvIdiuYffKbdyEAVwbdjGHyvAQSsNDqEyPoTIxjPGhAYznCgiNQjvsoRmHaIYdtFSIQCt0lYIyCkUS6JGB6o/s09CwLYFIGQQmwE67R4uNPQzZHlXSWRrPlzKFsVz6/OSL5bMvPz26cXt5ZvXKzbMf/eSD1d3N6iJgLeaypTuRyW3nJ9DI+Iu9zQsXIsy8p3EZ6nNVopNWjof/DIQhzfYPFC84jrmvOp2ci9C/Ie0c/fB8f+UZYUjTAO6OBT1sFBCBZWBKyHgt8klatiPytTAYGz1/dnp67nhlr9vJLNf2LK2VSEuC1jEZQ0AcmW7PJyUgBkaGLNjCi4GMDeMYIQWgYbSmtCbydYag752jmMDB405F8vBZF98nXADw3kUA3AvNOEAzdv9F+6D6/GB4fqB9Q0eH/1wBycAEWlMaJCF0qjw4kNJCynbPpzCKKQdAap1MQSBgr9ej1eo2BrIl6+xz53PXP5w/1lnaWnNtWrWMrEdqrBf5vppNzRochGgAmAoJK9WDzVi/iQH6/vD8Ods0HvpU6oPB+VHh+W8uyOkzO7I5U3JbRmdbnUYlWt+fwsTQ8VMXv3bi7MtPzQ5Oj026xdRAPexl6n7N2vObtN1poat6gCRDwpC0kmkRggBoA0sQpCEoY2AbA5BElmQSlqWHouMhb7uwYoWw1UVrew3X7qxj9dYS6qtbaNebQKebpHAQYFmwpAuyBQwMBAmErS40CcRxDFgWsp4HJ5XCYGUAlrSQy2RRKpURxSHGxkfhWhYWFhbx5IXzeOfdD/HK+TP44MNPUCwVgLzB7v4eZbMZs762gaMzR/Hxx1dw5Og0Fj5ZQyadwn/6xx9g7vRx7O7t4+9f+xE9/eQ5/Phn76FcLOCTa9cwNFLBv/+Pf4PpIxPYrlZxe2UZTz11Fu9/9DGGKwPY2NnBQLmEdNqF6zp4+aVncXX+Jr7xta/gzsoabEtCANjdr6PeaiHqBYjiGPVaHe2uj9hodDq95GtnW4AUEHYKtgC01ojDCPFWExsru9gwV4GUAyufQa5SwvCxKRyZPYryyCDGS3lMFfPoIEYn6GI/8NGIAnSjCEEcISZAguCa5DCigIYiIGsTtAAaJkCj1aPbzT0MpDJmKluUQ9licezJk4Wp07NHzrxwoXXjwysb8z/96FZ9Yfl6yzcLmWJpOdKZ9dHReB/+he7mxWyI119XX/hntP8s05zv07zjmIUVAE4Sph/6TM39hwvNlzs8HzqkDeCg71lFUVL9He63boze/w605QgLwg6lKSGTGn/mlWdHTMrK7+7vWhutFhE0lAGFWgGQ0EZTEAYGAOVLRQlpeRTG6ViSa2tIRyqhQ0NGG8qmFPnhoQ82gUN9HP1WjsP90BcAvAfDvdCMAzRjBxfGgwpIpZKsjz1ceU72HB+MsINwAR1FJA4urABcALGKBCSsfDFvK6NENwwQxDFy/TXIGskEBlsAy/v7ODLUEBPDA965F56ovL32vRM2yRUVRWsFtFsqiCO7f2e6gGRU20GIXqjencohfsNG2306PB/0dX7e8HwQnC9fNnj1UaPu+nfWr8Eqn0o53a6frrV2y6i2Jq0jk6ef/uNXnjjx9JnHKrOTw4Etco2g7e3W1uVquyV2e22yoaClgWURhYIQALC1TsbHGY1YaQhFkMKCIy0UbBcDbhp520Pe9mBChebmLu4srWH79gpWby+jtbYNdMP+3a2A7bgQdjrZfW2AMIgQIwSiEHAdWJbEYydmYVkWRkeGIaSAEAL5Yh77e/s4efIYXn/zHcwMFvD2ux9it15DMZvGwtIKjAD2avv4ux++hnIxj+W1NTiOA9uy0ItD2GkX2/u7ODZ7BFvVPbi2wNGpMfz47fexW99HO/CRy6WwW9tFy2/j+OwErt+8jXTWgxI6qVjfeBunZo+g1mwiikMoo1Bv1tFqtyClQKfrY2V9A81mG22/i71aA8ViHp1mE8OVQZybOoFu1wdIoNFsY2yoguWVVaQ8Dzu7e9jdraHR9dHtdBAEvaQ1RCazrR0nBUiJWCvE+x3UtuuoXVnEdfdN2AMFjB4Zx8jMJEaOTaI0PozRXA4dMmhFPez7XbSjAPthgFYcIjAKKQI8SpbLuERQRIjIINIa290mbbZbyFk7GM8WaLJQskdmBovPH/u9zBOvPDdx492rF66+9cHK5pVbVzuheq+UyV3z0qW1ctys71+a62FuPsZ3f87P6OXL5u4Bwf4DyflUynxmP/ThB51f3hD90PA8G4YUPSQ8A8PQ5W0SSK6rOiyRzvYEQUq3YKVqfnfw2IWnx8ZPHS1VI9/baexL28QiRTBdo2EJQh5AQxv0ogARFOVLeUGu5aqeztgEz+jIDrQhy9GklRY6UsIoTaagCL37P/nlB/uh7z4LcJG4Cs1+3STfBOxLcYGvVASiiEbjWKRcVxhjCP0X47oErZNDhMYQSWlIZCAHYkO+BLIdKCclYes0HBoKbev00197cTYzMpC5trUh1xs1cqS8O9dX9Of31sKQLCkwOjhAlXJZLC6uUK/W9HOOvRqJcJ+Q81fFot7POQauRDm8V/XezwSEdR84cYKwvPybuQSl06GDp6kRhklVKo7vf7Hte8HZce6vOr+CT0/USKUkXipJ7MxZlSE4hQLS1d39gW63cSI1M/7chT/95te+dun3Xzr+wrmz1khhfCdoF+erG6mr+1tyo70vdkJfaKHJkaAuNDmyvybbGJAGUiBITcjaHsp2CkOZAo7lBzCRLqEIG2qnhcX3ruH9772Od//uR7j945+hemMJ4X4L0ki4lgtpubCFhI4U4lhBBREAg3Ihj6mpcZw+fQpn5k7g5IlZ5PNZeNk0Wr0e4jjGxsYmstk0Prp6DfV6HeVyCVfmb+DcuVMQgtDpdPH4+TN4/+p1vPLyc1hcWcPU9DhWt3dQLOVh2xJXrt+k3/u9i/T9H/0EhUIOE6NDqO7uo1qr48lzc7SyuU2ZTIpmj07hzbd/hj/9k+/gjbd/hmw+h7GRIdTqTezv7+Ps6VPY2K5CxTGmp8bx3vsf44Xnn8L8wiJOz51Aq9uF4zp4/Mxj+NnHV/H8049ju7qLwcEBNFpN7OzvY31zE6mUg0a7iWavi1ArCDvpzS7kC/j2730NtiVx5uwc0tk0gk4XNghBGCHuBjA6aXVxHA+CJBADquWjsbyB9Su3cOujG1iZX0Rtu460FiilshjKlzCYKSBv2UgJC06y4BGR6h/8JIJNBkrrZDgJgWLSBBXRTrdDG8067XVbFOvYcnJpb+bEkezMmePlsePTo00VTlZ3dgbbO3uOm88FxVwlyi0UTDs3Bry0SckazEccoj19mpDJAKWSQRQBjpOME7Ht5MWYpP9dKZpVivalTP4+aT0DnnkGmJ//soS6g+AsULkosD0o7v6MhyHlxiMCjuCgSGG0Ju2UyChFJHswqkJGpSh22jIlHRsusj0LY3Ehfe7rf/ad8+5weXi5tu1d3d4QaWEooqS4YRMhQrLAJ+WlcXRgGJYC5t//JIrq7aYHsSxCtaUjtIisWESh6RptRApKGKVlbJtN2zfNJpAHkDeGmger6aXsnz8AMGWAzU3DAZpxgGa/2+H54kWBbpcQRdRWijKpFH0qQBtDRilBBQKFBGHbhkQPYsA2RmmKpStd0umeoSGVsc6cf+XZY6KYTd3a3pS7nRYlyzIAWwj0jEHcn6nbDUMazOWpVCiIlLSshRu3A6Gx4Rm5E4i4NdLOq0amawBgvx+iI3+cinGeKoUq7dcF8NJLB3ecvxmj6k6fvr91o3/HOjsVUrmgqFxQtN/oXxps+9MHBCvznw7OVysC+qZVEcYZLJY9K+vmd+vNSrtRO5o7MXb+mT/79gtfvfSdlyafOHkhLrgz6+298tXqpnttb1vu91rUUSEZQZS2BCwBREZBJHMkoA0hijSywkHZzWAiW8LRbAnTxQqGrBTUThur71/D2997A+/8zQ+x+JMP0LizDt0O4EgPtpuCTRYsSIRhjKjVgXBc5Ap5lIt5zJ07jSefPIdjx48iUDFGRofwycdX4KVdvPPuBzh6bBpL65s4dmQCUgpcvX4T3/nOV/Hjt9/D3KkTqLea8H0fzW4XW9VdOJ4LSxBu3LqNM2dO4a33PsR3vn4R7398FVMTY6hUBvDhx/N4+YWnabu6S7Vmm158/mm6s7xKmXQajufgxsIi8vkcTp44hn/4+x/iKy8/j1qjicWlNTzzxBmsbW0jn8+jF4YYGa7gxuIyLlw4h5+99yEuPHkOV24s4LETx3Dj5gKUMRgbrmB1fROlYg6bm5soFHIQgjA1OY5bt+9gaLCMxTvLeOLMKfzd62/i8TOPYWdzB+9/+AkGhwYAIZDPZzE8OoSnnnwcGsDkxCjCIEgq90EIHUbJXGoh4abSICOhewrdrT1Ury/i5odXsXj1JvxqDQ4ExvMljJcGUMlkkLMdOMKCACGONXydbHQ0xsDqF4+Tp3o0lI6w1+3QSn2PdtpNCuJAZvIZd+zoRPHM46crlenRiq/VwM76Vr69X0vrXFHmBzNINQfhz6aA8bOEZ55Jfg4OvxyWySQvB0E6DJMHlP0gt68UQUrcfaBpDB4I0V+GB8oCO5V7LRvdrphVinL9yvPBVCOjNZmKJqPaBHRh1ACZAUWKekLBskzO9ZB1y7Vu68QT3/rKhVPPPvHYftzOX9latdu9DuVlMsrQIYIhgt8/oGrZHk0ODCJlpLn5wRUV7Oy1PIiVOFKbti0aJtIRWdKo2NFkAi1rWkvbNh3bN2gCTSQhuiQEigAa/QcvOHjgsnnioEbNIZpxgGa/o/OfjxyhgwCNQwHaKJVMt3VdMnEskO2HahegWBpQABIEHcYUk21J4aR7FA+7o6Uz519+5ljPlanFvaowUY+s/qpmBQNLEoiAjBRoaAMhCQP5Ag0NVuTG+la8v7FRt2x704ni/ThHcbc1qOE2kspzqKgY50kFARlTQqPRSJ7G/fKH6E9Xnw8ObvbD8+FXvi9AH1SeHzZdY/4SAVflcBQ6hfRYOshkitv1vWG/1TjqHp84/fK/+c4zX/mzb14cO3/iuTArT6w1q+Ube1vuJ7vbcjfokkWaXJFMg+gYgzT15wcrDaEBrQUGLA9H8yWcKA1hpjSEEScD7HWw9N41fPC9N/CTv/4Bbr32MzSXN6E6ARyy4ToeDCRUGCNq+TAkIbTGcGUAL118Eal0Cs8++yQsz0WsYyytrmG/2UC+lMM7H36EZ546j/1GAy9/5TlcvXYLY8MVfHT1BsrlAizXweLqBi48fgYfX5nHmbmT2G80MT4yjAtPnMXP3vsITzxxDn4QINYapWIBCwuLmJ05ims3FzE5Por567fw5ONnsbaxBWWA/UYTgwMD2NjewdTkGEaHh3FrcQnDgwMQlgMDQBlCKZ+DJQS29/ZRLhcQa4Pt6h6Oz0xj4c4SKuUSUmkPd9Y3MVQZhNEasdHIZdLY2t5BqVSEFIThoQpWN7dhAAgp4DouyqUiNrZ28Mz5s7h65Tqmp8aRz2eRzeXwozfewpGpMbz9yVXs7O1htDKAbq+Hc2fnMDUxhuHBAWRyWfT8ACpW6DXbUAaQJGFZNmzLgQpCBNUatucXcPODK1i9dhu1rSrybgrjA0MYzBVR8dLIWBY8IQCl0O0vlXGR/MyGWkFAI2ULOALoBD2sNRvYbDUQqhBuxrMnjkwVTz15ZmJ4ZuJoI+gN1VbWcn6z5Tqlkkw7JTEY+5TqGeo0m4SlpeTnIIqSn4lMBndbOubngT//c4NuNwnHB9XoOKa7ldADB5XoUsn8mq8DD5+00Z/zHLnDwqgcqSi6W3kGAJPSRFKA5CjMgCLV8oWCZXmOsk3WybVCf9yZGL7wrT/7zvko60ytNne9tdouuWQoMoBlDFT/BZQUK1xpY7o8iIxlY/GDq7qxttVxYa9SZNahdM0IFQtNyou7WklSoqu0tG1Tsn2TPxSgV4VAA/0WvoMQ7XkGm2/hC4wuZIwDNPstrEA/IkADQFKB9gnaITjJ35EgICQIp2CALnRUJCVjS+a9TNtvj+Snx888/vIzM11SqZvbGyKKQiIALhlkLAFhDDxB6CBZ49zqBRjM5ymfy9NALovr12/FaWFvBT1VVbHsDWBftXtjBm4D6Ado0z/gWMrvU6MaEfb3CXNzwDPPEObn6Ut7Wx9U2jodunsoKo6pXFCfHaAzGdxXeZ6/RHg7JRHdssqlWReUze13toe6rdps7uTRC8//62+/+JU/+9ZL42ePP61y9vGV1u7Qx1trmRu721YvCshYghQMkdEIlYZNBFcI9JSBjjVyloMhL4NTxUHMlEcxnSnD7caoXlvCO997HW/+5d/hxhvvYW9hBbEfw3I8OMKCRRJRqBCGMXSsMFgq4uTcSUxNjuPpZ56Am0lBGYVqo4laq4HN7R2Mj49Ak4HtSKQcOzlo59j46PotdDod9HoBpqYn0Ov6kEKgWCqg0+4il8viztoGKgNl1BoNtDod7DaaaLXacDwX9VYbrmcjn8+h2+0hn00jk8miVqvh2afO4z//wz/h7NxJnDg+gzd++jO88MyTuHJzAcKyEMcR9veTFhFDhHc++ARff+k5fPDxFYRhhG+88iL++nvfx7MXHkcvCNDqdjA2MgwjJe6sbWJwoIxWp4vpqQl88tFVTE5NoNfrYWx8FEGvh4XFZUxMjkMKARVrOLaNQi6PD6/cwFClglqjhZGRIXz4yTxsS+IrLzyFrZ0qJkaHQEgWvdSaLaRTDm4tLsNJpXFkehInTsxi5ug0XC+ZMNKoN6GiGHEQwrJt2LYFQIBChfbGDrav3sL1965gbXEVVmRQyuQwXh7EYDaHopuCSxIqNojiGK04QlZKuAIw2iA0GloQMpZAoEJarNexUt8nPw5kNptyxmemcyfOnhwtT4/OtMLg6P7a+kCv3XEomzfK07CjDrJwRXHE0EDoUKNavVd9PgjBr79+r7UjipKQfBCiDztod4oi4MiRX1db16F+58p94RnjEeX6/c4Hofm+N/QlqChhVJMUWUJZrkx5xg6MSSOTHmqb4NTLf/R7z0+dO3my1msV7uxtyU7kkyMEtVUMfXA+QSQTcaQQsITAeHkQpVQWq/O3zO7tlY4jrFX0wjVA7kNFoTBC+XGkhYCSWSjLpLSQHaw1gYkJYK3ZH8V4N7H0r0vGAFNTwOYm34syDtCMA/SnAvTdFo4CERGMpQnIAcYhyilDoYCwC0ZnQ6E1pHSsjB+0R4szU2dOPv34TNuE7u3dHdGIQipKAQsGBEIkCBERIAQ8QQigiSxJA+kMDQ1WqNVoW6u3l7ppN9NAx2/GRoaVbFdNYNZU3FFEnc69pz9VjpqlBlAHEATJHdOXqxfy/tt6fv7TgSCOab8hcfAy0pCoAsk0goP2jUwGqJ5OWjWuDIpZy5JyRDj5zGim0dirtFpbs/b0yFNPX/rWi1/7r3//2enzx89FaXFsqVUd+WhzNXd9d9vxw57wBIhgqGc0pDFIE0EKgabSMBBI2x7GskWcLA7g5MAIKnYG/moV86+/gx//x3/EB3/7GnavLyLqRrDIgu2kII2AVBq9jg8hLeRLRUxNjOKVrzwPZTSOnzyGxdVV7OzuIFQKy+sbOHfmFNqdDsbGhrGzvY1ms4lz507j+z98A0ePTOLdT67jj7/1NaysbeHM3En8/Q/f6Pcc76Dd8SGEwPLmNv7s97+Jv/zbf8BXX3oOlm3j2sIdXPrjP8Bf/90P8Md/9G3cvLkIpQ2OTE3gww+v4tTJY7h64zaOTE8in89iY2MLd5bX8Gd/+B38L//ur/Anf/gdLKysoZjP46VnL+B7//g6vvqVFzA6PIS/+6c38Gd/9B3MX7+FequN8bEx7DYaiI1Bu9fD2HAFV28sIOV5+PrFF/H3P/gRhitDePrJx/H6j3+Kb3/jK/jr730fU2NjyGYzKOQyeOdnH+LZp5/AzYUlEAhHpychRDLZ5Nat2/jG176CG7duY69ex+07yzh/bg7X+x9jcnICb73zPmZmpiFgsLK+iU9uLEBKgfGxERQKBTz55DkIIliug9D3EbS7MITka2a7sKQN5Qdor25h6b0ruPnxdXR2a8haLkbLA5gcrGAok4UnbRit0QgDhLGC6K8Tdwjw+wuSCKAwDmmr1aKlvV3qBr6dLWQzYzNTpeNnT1Zyw5Xheqs52ljfGOhFkedl02QsR/e6oVEpheKARHu9kXy///mySc6oAQ/9mTnoiz4cpOM4uY5lMubXFKJFUnlOwvNsoyFyIz2Rc4dFpucJFQRChaHQpZjQAUhKSNs2QkoIKSG6EtotkzK+SNspKzDwkEkVmlFrZvDksae+8ae/f75J8dhKY9fdaNUECUOR0bBgoA0hLSVsgWRkIQQMSUyWBjCQztLK1QWzc32x4wh7HZFeIWV2YVQgFGlPuSo2gZYSSirHbOz0zLQQWG0LQAhMKEV3e6E/VYXeNDyJg3GAZr/bAbpeF9A62T74QICmTCY57GJpMtpO/s4E/TYOAlxNKtSW9OyM3+2OTp0/dXbm/Kkj1ajn3tmrChhFpr9iWBMhJoImSjbFEZCyJdpRjJTjoJQviIF83r5x/baler6yBDWCSHXQCkKz2zYkBKRtI+717t5x5lWOSqUGGg8P0V+mbYN0XyDodOjuQamDIJBKmepBOACS6vNBxXp7W6BQkMNew1ZpL92TcXlve3lKlb2zT/3xN5/75r/9oxdnnzr9tMrZx5ea1aEP1pczV6vbdt3vioItScKgZ4DAGNj9/mbSBiQsDKezOJkv43RlBLPFCjI9g80ri3jjL/8eb//197H81kfwqw0IYcPzUjBkQfVCQGkIA6TSaTz79BNIZdJ44YWnsFHdQT6fxSc3bqFRqyGVTWNqahzdoIdTJ2bw45++C0tK7FR3MTE1hoHBEt6fv4ETJ45hcnoS9VoTzXYHjU4XKdvByeOz8MMIgdb45tcu4vriEsqFPDqtDoYGylhe24RtWSjm8li4s4LnL5zHT955H08/cR671X2Ui0XMHDuK3d19fOv3voZ/+OGP8PWLL8FxHGilMVAqopjLItYGGc9Dt9tFs93FsSOTuH5nFaOVCiQRLNeF57ko5HM4c/okPvrkGv7oD76FsBdgaWUdf/5v/zW2tqv46OoN/Kuvv4Kbt5fgd304jo3FpVWcPHYUrXYXE5PjeO3Nd3Dxxeewu7uPeqOJ4aFB2LaDH/3kbbzylecRBCF8v4fq3j7mTh1HeaCEW7eX8NwzT+LOxhY8L4XR4SHk8nmsrm/Bsmw8c/4sllbWsLdfw2a1inQmjZ5SePbpJ5HOpHF05ih63R7CXoAwCKGCCJbjwnI9aC0Q19vYvraAGx/OY+XabcR+iKFCCVNDQ5gqD2LA9SCNQT2K0Yzi/gg8QBkD2V+iowTBjyJaa9RoebeK2MQiV8qnjpycGZg9c2LMqxRG93Z3i531LS8mI/LpgtEqMIGyTTGnTGegbVB95f5WjAdDtOPcd8hwLo6pevC63W7SE/2rbetKDgweVJ4bDZF7YMqGjmPSxSIZ3SFkABEm4Vm6rlm1LOSVIu26pAqupMg48GRO5cSIL+jst/71HzybmRya2Qvb+Zv7O6IV98gSRNoYOP218oqSBTkWAEMCEQhj+SIGM3lsLayYjflbXRf2moj0siG1A233BEzsx6SljJXcN1o6jmkPdU2jfu8/lu8/G9k0hnA4RBsDJM8acHhmHKDZ73CAbrUEtKbcAwGaiADPJ6McMpYmGCdp45CxQZpAoYCxFWlXWTJlZ/x2a/zIM2fPjJ6ZPVrrddz1+h4RDMHoZM2xAVJSwBABghAKwAgBIqARK5TTaVGpVAQMMks3bnuOtJUd6bpw7HacNpHV1lraNixvzcS99N0QLaxBFPN5anS7BsbgS9AL+bA525+eOHAQCA76Ow+mbRy0d4QhodEQGKyL0YJnDdjC8zPZ/M7O2nAg45Mnv/nic7/33/zJ106+9MRzlHdOrLX2Bt/fWEl/tL1phWFHpCyQKwUCbcgA6CoD9B8bWVJgPJvHsfIgjpcqGE0XYKotXH/jXbzxl3+PD/7mh6jfXoXyFaTjQVgOEMWIghhGKQxWyiiVCnjxhadRLOXRDkO4KReLq6tQSmF9exsXnjgHx3HQajURGY07G5totjs4f+40nJSHk6eO48233sXY6DBanQ6IBN56611846svY3ljCy8/cwG3FpeRy+Wwu1eDJOCtn76LuRPHkfVSWLyzgj/9kz/A7cVlTE9PYnCgjEajiYmJCaxvbCGdSmOruotavYHtvT1cWVzG/K3baHW6ePu9D3Hzzgp263X85N0Psd9s4YOPPsH69g6W1jawuLKG1fUNrKys4c7aOja2tpPpH90Ori3cwQdX5tGNY3z0yTWsbW6j1fVx+84yeu02VBSjkC9gbWsbxXweT547i3qzjeOzxxCGEfb26jj92CnsVPdw5ep1/Mkf/z7+9u9/gPJAGbNHprG2so79Zhue6+LYkUm8//E8jh6Zwt5+HRvVPbS6XbiOAz8I8PGV6/jGKy+h0+2i0/Gxs7uHr158AdKWuLO8jP1WC4I0NnaqOHFiBoFSeP75p5FOpeB4Ljq9HsJOFxACwrIhHRc6CNHe2MHyh9dw/eNraG7vwxUSk8MjGCkNYMj14IHQi2P0VIwUEWIDdLVCHGtYRLAtgXYc0creLlb2dylWkSwPFt3pE0fzx84+NmLl0qPV3WqutblBsZPSVsbRQU+YfC1t/Nu3Dc6e/XQlen4eWF42eOYZ3H0AGoZUfbClw7aBWu1XeTYimbbRD8/TUUShNShUEAijNcXZQGgrL6A1QXsk7NAcBGg3lzNl24YxBrGUItI9y6TiNDx3sB62Tjx28bknn/zaC4/vqe7ASnPX2e3UyRaAgKFYawhQMkJUa8QAYhKwSEAKgeFcESOFMnburJvVj651HVhrKoqWRGi2IJQvfRkrK4il1e+BdhzTdroG/QA9DcAYQ3fHQj84kWNuzvQr/RyiGQdo9jsYoAcHBYKAHgzQlKwhJniGjHJIi1iYSIgkQXsgEUEo28A1pLtGypyT8TvNscnnzp8eOXXsyFa34a429kVPKxABjpQwlPQ9aylgBGARQQtCzrPRikMSQqKQzoqJ4WF78c5KurtfS7uu7cfdoOGF1NSpbryS2dP7rkRTtNA0JZQsqz+zdClp5fA88yUN0PdXoQ8HgpdeSkL/4VDdaAiMjYnRgdCyQ89Fbji7Ud8Y8tv1EyPPzj37rf/u0sUL33zxeXe0+NhOpzb67vpS7r2NVXu30xKDNhEsQcZoailNjhSAAYQyyDseJvNFPDYwjNmBIRThoLtSxQd//wbe+vd/h9s//Cm62/sAWbCkA8fxEAURTK+HdDaN0bFhTE6M4tz504gBLNxZQqlcwG69jvGxYezt7eHZp86j7fuo1evodLsgKbC1u4c/+vY3sL5TxW69iZXNHfi+j+OzRxHGCpu7NXzl+WcQ9gJEsUIUhtjY2YUkiWw2i73dfXzr66/AtR0QAAUgjhU++ugqemGEj68v4NriEmrNFt559wNEKsb87SV0ul3UGk1s7tdBUqDl9yAEAUICBPhKQXouIpWs8dYASFqwHAeGDBzXRYhkckzKddAOwuQcgEgCZCfoIYwVgihAdW8Pe3s17LfbuDJ/Dc1OF3fWN/HJtRvYqe7i5uIShkslLK9twHNTSLkOCrksoijGzMwRNNst2JaDmzfv4Du/91W8+/4niOIYR6fGUduvIQhCnJqdwVPnzuJv/+4H+NrFF1DI53B98Q62dvbgOQ5eev4p/OD1N9HrdlEeKOKJc3O4dvM2soUMbiwuQQhAUXL24Mzpk3AsC+OTo+h0fQRBAB1EIAik0mkYkyyz2b5+O+mVvrkExBpjlQqmKhUMZXOwIeBHClEcw2iDtCURaAUVK5DRICEoDnu0vLdPm/U6QcAeGR5MHztzKj/92OygzqaGdja3i0G9aaUyXtyTVpwrSDXoGzSvDx+uJJu7P0Pz87gboh/WF30wneNX82xU0rqxvS3uhufBQXFQdVb5SJi4QPev6E4CtJ1OG9l/tknHMYUDSoY946ZTqWLbUVMql3nyO5f+4Eldykzu+I3MZq0qSCjqwZA2BpIEIm0Q9Kek2ADaSFprbGGhkM5SJV+i3Tsbevm9T3wytCZiui2U3iIJP4jDWFhCCRhtBVB2Oq2bVhsHAbrRr0DnkRwq/FSAzmTMb9AYUcYBmrFf8li1sTF6WIBG/xAhPEM6lMIIT2Q8JRwHCGMBYStDmeSCqrNCKNvOhJ322NEXLpwdmp06stluOKuNGpExsKSEgIEjCGRbKGc8GACWFBAWIZaElAC2ewENZjNUyOVpoJB3r129kdGhliJQTRLxduQrv5eKYyymDLqeQaOBxmAdxThPRRTRaLWSau7QkPkNGG2HQ09Rm7uB+vRpwva2mC6VpOX7DuULmcDSldrW0rHsY0fOf+3P//T5l//0my/kjwyfr4btmQ/WF4vvr6+4e+2W8GwSaYsoUMloL2UMpCbEGkhZDkbzJZwaHMHJgSEUtYXqtSW8/Z//CW//+7/D9vvXEO61ICwXJB3AEHSvh9j3MT41gamZKYyOj2Dm2DQWlpchHIlGp43Hzz6Gm3eWURkawNbuLlIpD9du3YbjOEin0wARzj9+Gu1uF1dvLWCgVMLI8BCGBsuwbAt+GCGMYgyXS/jwynU8cfY0rt28ja9ffBntRgsjlUFUBsrY2tzGBx9dxfrWDj6+fhN3VlaxV6ujurePlt+DIYIR/baglAdFB4eeDGIAhgxUHAFaJQtI4gixUTAANBkoAqL+U+HaIigBKGEQk4EWBAODCLq/AttAqRgmTmZYG6WgtUo2B0oBLSVsx4GUApoE0N/g2AkjLC4uod0LcGfhNtZ2drGztY3N3X1EQYDltS2cnDmC4eFh3Lh1G6dPncD42Ch6fg9ra1v46isv44033sLK2gZefvFp3LyzDK01tvZq+JPvfBPXby4ijmM0ux088+RZrG9tYWNrB+m0h6nJcfSiCLMz07h6fQHlcgHXbi9CWgLlwRK8dArPXjiPKIrh+z30Gq3+jGkHwnZhugFaq1tY/vg6FucXoMIYo4ODODI8hoF0Bg4I3Vhhv9eDrTVcAEZpkDJwSUKA0O51aXlvl6rNppC2cIdGK4Vj504Njs8eGWwHvUJ1adkzMCadLUUd04sHSka37Q3g9CsGl+Zxtxp9OEQfnhkdxzQHoHpvHJ5Bp0OHQjQ9dAb1L9S6cUlgZyepPPd6Qo2OktGaVBgKlc0KE9nibjucECDLMiR7EKFtpOPcDdBRuSMCpGxLdtOUTw83ot7pb1z6/afHz544WY+7xZXmnlWLuwJkQMaALAkYgmNJeI6LbqygTfLAUgCIDVDO5DBWKKOxuqUX3/vEF5pWvVjfJogNKOp6AnHcNloEpKTW2nJd01xr3/3PTShFa/1pHA8N0MbwODsG3kTIfjddugQsLuLuGu+xMcD3k+zcP6in41w/WvRnlmpN2ZQw3fjQ5IgW4FjCQCTBQRndb9sAhBCwjYFFAFkC+UwahWwauttDtdOBKwS0MYgEwRIai/VdFLy0mHjsmDX33BPFq//41nkn5WxGLb3oOnYDrUoPWV/fXTBSbZNdWRcLQLKucOVLfYubR94RH2wV/JtFMTFjW/Wu8gRRbntreRjlzLGn/9s/OXv65Scfz00MnvARDN5cv5Oa396w24EvjG0h60gyWqGjVZINtIEgQtpJYSJfwpFCCeV0DrYC7rx3A/NvvIPlj64DTR8gCSFcGGmgQwXo5Ot9+txjGJ0YQa3VRKQiaNL48MYNHD9xFCBCt1rFnbU1CEmwLAHPcyGFwMTYMFKpFGJD2N6v4Qdvvo2zp44jl88hnfKwcmcFx2aPYmVlHWdPn8LOVhVPP3Eercab6HUDlHMF/OM/vIZGp4vd/X0gVnBSHmIAKc+Bl0kDRsMYjdgSiFSMKIyBmJJd8ZYFCECkPNipFDJpD7lcDl7KRSrtwXNduCkvmRnt2IAlISwLRgi40oJtCRiTbIvXWkMbA60VYqVAsUYcx4iiCHEQwcQKvV4I3++i2+3C7/YQ+CH8ro+w04UOQyhjEIZRP9S5UGEMmfEQGw1jSdTbLezv7kI6Hv7qr78HKS0YQahWdzFQKsFohROzM1heXMHR6Wnky0Vs7+yh3upg5sgkXjw/jHd++h4qg2Xs1msYGRrEyuYWpLRwfHYGS0srWFtZx0Ahj6XlVRQKGaRSDk4eP4qbt28jH2Sx3+kgXF9HulzA00cnIZTBR1euob67DxICBgJ2Og9tFJq3N/D28gauvPEeTj7/BM48+zieHD2CiUITS7s7uFOvo9ntAlpDkkBXxzCxhiMlJAyWa7u0srsrToyMOuenj5SHz05nvj3xZ0MLj5+cfPOvfzi8u7z6broweDOyc9vlVq2zjw8CvHZR4dXXNb6LT28w3Nm5u83zoQ+bD1Z+H/ysXb5vJKT5hcNztSoQhqRGD/U8FxWZQJHOxoQ6ICzr7scRjmXkoS2uke9TpHIickM7P5TJbDfqo0NPnjx57oUnj9QQlrY7dWuv2yRLCnSUgiuSZ5Q820LacWALAa0NtjtdFKWEIEJoCIYACAJZgiAIUhEpADKODUXKkGMZSBgBGGHMp2+HCWBi7f7N3oxxgGYMuLfQoz+BQ0cRaXUvGJuCJsSAyWgyIhadOBnBlFOajMqQjkIStmXIEiYUZGBJI6WFOMkecISANCrpfyZCznaQcT040kYlJeBHMQKj4EiCIoOMbcEPu6h2m3CyNj398jPO0vytge7K7qmsa51u1DtLo167uYmswiuv62QOMrBQhZ5tNMSC4xj013//hs0oNQAIr10UmAmsRpRJB9grh/v1oyMvPnHuxT/6+lMTc7PHOxSNze+s5K9sbzq1TlNmLIJrAd04pK62kBJArIHQGBRcGycGBjBRHMRgKgfdDrDx/g18+MbPsP7JTaDRAYQFIR1oDegwBghIpz1MH53C0WNHcXttHXW/AzftYmt9DydOHkO310XKc3HlxgKOzx6FjhVSrotWq4Nmu4MTszPY3t3D7lYV+UIe3/jK83jng4/heil8cv02zj12Avl8ARMjowi7PUR+gNpeDf/j//i/INYGn3xwJaluCQK5Dtx0Cqa/ZhrGoON3k9qh60B6DvL5HNxcGl4+h8JgGYVCHsVSHoVCDpTyYKdcSMeB5zqApP73IkCSoGGgoWGEgOo/6EA/g+t+1VgbQEJAwsDAJA82kFQBYQBbSMBoQAM6UjDaQEUKQRAg6PoIu8n0i9peHbv7dbRrDfiNFnqNFvx2G6EfADoGpIAyMSjlQhPggLC5tY2NrW3oOMb8jQWkXAejoyMQQqDdaOHSd34Pf/lfvo9jk+PY2api5mTS4/zS2Tn8h//yDzh9/Bjmb9zCiWMzqO7VsN9sQUUxTp08jnc//ASPnZyF47goVyro9GJorSBcG80wQC6VwvknTiOOFBZu3EatVkfQ8eG4NqSdQmwUOne28f7K93Dzzfdx6oUncOLJ03hi5AjGC23c2d3G0t4+2mEPlhDIWQI9FaMTK0hhIWsRLWxtYKNWs+bGx+Tx4TH7zDeeSU2cODrw0//y2tTCOx+/093fe78wMLFSCJxaLgh6a39zIQbeU8Bnh+jPUTig/tvinxmkk/C8uCgOVnP3BgeFiiKKfV/ooiIdZIV+sDcbgLBtI/bt5CQvgF69LqJcTvTSoW1Dp5qKBlXaPvLiN1460XHEcN1vetVuSxoYuAT0hISnAQWJQcdGpIHBfB5RrFEPejCC0NAGOZG0zGmjIYRMRpIqA6210VJo10B3w0BLO9aIUnc/v+kjAJburfFeS3L03afMP9WwcREHzwwQV6EZB2j2u9O+AQC+f/cif3DBP1gxq2OVrPHWmgw0ebErkAJ0HBmjbX3fO5XCINaaSBiLiFSsERoDrz/jypEEJQWmywP4+OoN2JbAyckxXK3twQCw+0+/x1pjob6PtJPC8HBZvPTNl92//5/+ajp06LR07Le6rV4V7XaUVKIuG7wKg9cuigXgXlX68mXzG/c1ee2imBgK7Cim3Hb19iiGK6cv/t/+zYVTLz71uF3OHFtu7A9+srXuLe1sS0kGjivJVxE8QygIiUBrBApI2Q5OFIqYLJYwVijBjQm3fzaPj19/Bxuf3AL8CBAWrFQWOoqhwxBkWXBTLk6fO4WBShm3l9dwZ3MdTtpGLw6hpUG5UsJ+o45AxdirNTAyNIh6rY4gjJDL5ZAvFZHN57Fd3cPAQBnHjkzh+q1FfDR/E5OjY6jVGvizP/g23nnnA+TTafz7v/rPUNqgvbcPOA6ElCBBkCkn6ZEHYKAQRD3Ac+FVBjBQLqA0OIBsuYjcYBGFUhG5Uh5WxoOVcgEpEZmDWKwQGo2u1gi0hjFd6FijpxTIKJj+HOPQJAHaaAMFStbNmxjUb71QJhm/KIy5O2PX3I1bBhYJCAhYUoAg4AgJsg1sV8IqFpERZRQgME4SUBomUtBRhLDro73fQG2vjlaticZ2FbvbO6jv1qGabQRBDNgi+diWC0tKdKMQNxcWcfPGLbiZLNb/538PRxDs6Uk8NncSo6MjSKfT+MfXfoLBgUFMTk0hjjV29utY29rBKy8/h+vXbmK/0UIYREilPQwNDeKt9z/Bn3zn63j7nfdRKubx0bUbOHnsCFa3djFQKGD6+BE8lcvjkyvXsLffQLtWh3QcWJYHTRrtOzt4985/wfwb7+PMy09j7rnzqEzNYrJQw2J1G3dq+6gHAUBATgporRHEBpa0qBn4+OnCLVrf3XPOTE2VjkwNpb/z53+Sv3Hu5MBP/uafxhq3Vt9P5wrXwkp6Y7i3296em4tw+rTC3JzBd797L0S/+uq9Pz/YnnFQfT68AXRoyODSJcLly4eDn/ncC6gWF+/2PEdHANV+SHjO6WSDVFEY8qUhyzLCqRn003PYbgtdLlNojOVE8OIht9jeqR59/NK3Hps8e2pyLWjm7jTr0lchSBIpAnJCIogVJgsFqP0GFu6s4NgrL6JqtWEbAwcEhwR6WsOPYxgDCCkJJAhGk01kYqV0T0gjpTAEaUhLgyhKwnIwShhduxuaD1NK0QSAtUPV84fcNhyiGQdo9lseoi9evLcNTykarlQoDoK7M5ZRAhAXYVREUGlKo0fa1QQNGC9F6B4Oz9IYpTRiowyZZLwdAUYAIQzS0kIsCAXXRS6dBmotrKyt4/T0FCbTGawHPrpGo6kUBiyBduhjvblPbtE2M48/JqbOzw2u/Pj92Xzemxah2Zyt5PyFV6HwXWh8F4RLQ+a+O8bftIv4pUuigh1vtxGXekFzevrrz5997l+98tzosYnzDRNOvn/nZvrK+qodGy1cS0AZg04YwZXJo4ZGpCCkhdF8AbMDQ5jKF+FowvIHN/HhP72NzflFoB1C2A6kmwYZIPR7sBwbmXwWx0/NYnxyDJ/cuInOVggv7YAEIZ/20I0i+EEAPwxQyGcAQSgPlnD95m1UyiWkPQsD5TLWtnYwWCoAroue38PSfgNfeeF5fPjhJxgul3D92i1Ut3dxa+EOoDVg25BSwirkoaIYOo6Scm/KhZPLIF0pozI5huHxUQyODSNfKiCdy8BOe4gFISaNbhyhqRVCHSEOfIQExCpGZDSCfgsRIanIgwCbDEIQJBkYSlpcNAGCBMhKqvdEQEQAoGCBIE3ye6WTBSaC9EGhGpE2IBhIQyCVbCuUxtztQ5UQEESwQZCGkvfXD9uZog1vYBQTJyfhQkCGMYKOj069hc5eA9XNKjZX1lFf30K71kSv6wNagVwblvQAAPVGA9Aaf/+P/wQhLTz5xFn0ghDnTp3C0HAF//TGW0h7DgrlAs6cOo4b126h0WjDdT288vJz+MlPfoqnnnkSQRjhnfc/QhDGqNWbOH38GKIgQKGQh+PaiKIYP7s6j5effwbtWhObm9tYWdtAbXcPIIGUk0KkFbqL23hn6a9x880PcPriU5i9cAZDR2YxUdjFws4ONhp1dMMAjrTQ0xpSx0hJAceysLG/Rxt7e+L42Lh34cjR0dnnzuZHj06MffTaT0c+/Ic3hrrtxsf5wvBy4Wi0X9zZ8ZcXFxUuXdJ3A3QSnh8ehC9fTrYDDg2ZuyH64NeLF4GhocPVaPNzD15fvEioVmk6ipK2jfa9to3D4dnEGSKrY0TbMuRaRhwEz1FAISIdRBQaY4XUcUXGKzQbzanM8YnT57/yzNy+CQfrvY7bCbsEAsEQtEmOpRRsB6PSxVtXbsENQ2QcD5aQCAXdfTDYM4AGwcAYggBgCARSUgAySB5V2tJAqcMdG3iwYeNwkF6T8tO3TbtN9z2LxgGacYBmvxNV6IPqs1L0sKcbP9c7sqQh2TGIYGC0Jg0DAmIpACngCILuHz7xhIQjHOQgcefGEpauLWJs7hhiGGyEPaSERENrlGwLm90WSukMvFQJz3/zZW9zcWWss7F/Lp2zVmqqWcNrFxXwugZgcPmyxqVL4u6d6W/ScP9Ll+RAsJ6ubqxV5NToqa/+d//mhVPPPv68zLvHrm9vDFxZW/bW9mvSdW1IQYiDCFoKpCQhiGL0iDBeLOPU4BAqhTLy0sHe7TW8/9rbuPP2R0AvAgkb0k1BayDqhRCWRLGYR2VkEI+dPomfXbmG2q0FCFtiYnIM21s7KBTzuH1nBROTYxgdHkKj20Wj00Yhn8PttQ2cmjsF1wBXr95EoIDZmWmoMMJWvY0nnzyNq1eu4advvYfbd5bwzrsfJV8MrWClPGgi6DiGCgPAtuEMlVAZraAyNYbB8WGMTI0hVS7ASbuIhYBvFAIVYz8KEXa78E0MpeNkrjg0IihERkNKiTCJCjAiCRxEybQXCYOwv/0yOnSC2xLUPxpIUBIgoyHp4AxtUqXWxoCs5FeNuy3mUJKgIQCjIWEgBCGGSJ42N4BE0j8Nkxzq0gBsA4jIwERAuh+oPSHhCQteyoaTHUBhYggjj5/EBUMIm23UtvewtbqB3eUNbC2voVHdB9pdQFqALWG7yWTvd9/7CLAtLK+uQ1oWjk1P4ukLj2P+xg1Efg9RGOL5557ClfkbqDcayGSzyOdzUCA0uj1846Xn8NN3P8BQKoWN9WSJzetvvoOTx44gk81g/uYCVtc28fUXn0WukMP66ga2tnbhd7ogDUiyIQxQv3oHb95cxvW3PsC5b7yIo+dOYvhYEau1Pdyq7mBrfx9QCkISjDJohSEsQbAFcHt9lTb39u1z09O5uYlJ56X/3TeL47NTR9/63uuz+x/e+Ek6W5rvZtJbA5Hb2Wt9EKJa0Lh0SX/Gzz0davV4+DXuoEc6eR/0mWcVLl0iLC4mbRuHep7jbCBMXCAdB/3wrOhTrRtOzQg3CdFJeLYt1+o5WspsB9GIcujMN//rP3xcDhWPbvjNzGKnKdIWIVbJh1YguEJixM3Ar9aw+c7HmH58DpYh2I4Hz7IgBYEoedYkZcnkmRQYAoiIlEjGdwhNUhjqCoNQGLiPjMyf7xp28SLw+uvEIZpxgGa/G60bB6KIRgGE/fXYD76RyWgygSZDKTIU9ls8NCHVn9SxD8ABqGBpGK2EgCat4VgCWUsiRDKdwANgSCbj1IwAOiEW37uCozNHUHIz6MCgFQWAINRUDBsGa+0audLB2PSIfOYbLw6++f/7m2eVYy/oll5Hf2jC3V7ny5f1L+lk/a/Oq6+K4ds/8bYXFieOfOcrTz//p9/+SuXoyBONqDv50a1r+asrK3asY7Jti5RSMMqABIF0EgZzXhpHSiUcGxrFoJdDe6eOn7z2Q8z/+H3ovSbIdiBkUp0K+ofYKsMDmJgYRXmgiOWNDbz+7vsYrgxianwEt5aWsNdooBdFKAuJ8mAZTsrDu+99hItffQn+coRisYxSWeD6jUVY0sLXv/FV3Lq9hM21LQyUi0hlMvj//q9/iShWUHEMJ52C9DxoFUHHBrGKgHQK+fEKJo8fw8TMFIYmRpAfLEKnbGhB6CLGXhQgCBvoxCF6RkMbjVBr9IyGIQNNAB00LFMyPUNCwQgBAcCC6X+DiH5DR/JsujQGLjQ0AAVCqAwkEaRI+p4JyQGtWGsQEXT/MKYA3d1ibIw5VOpM+qENAKU1JIAgOXB7d8mFhgEkIdYGigwsSrYN9oyBpQ2EErCVAZEFyyShOm85EBDI5myki+M4O3cUUgG9WhO1zV1sL61hceEO9tc2EdRbQBRBelZSiVQx4ijEh1ev4er1m4BR+ObXL8J2XHQ7PrrdLqJcDjPHj+E/fO8H+K++/XW88d6HWFxeRRDFIGlBWDZ2dms4cmQa42Mj2NzawejQIHK5DDZ3q7h26zZOz85iduYIbtxYxO7mDrrNNsh1IJ0MoCPsvX8L/3RjGbefOYdz33gBM0eGMVQoYLG6g5ubm+j4Psjqt83opMM87Vjo+m38eH5e7jQbqTOTE870hZOpoenR0ns/fGvs4++9+Xa33X6vUBlaKOylGjnb7q1dvapw6ZL6jNYt86lrw73KadL2lYRo8Rnv4yA8C/g+RePR3crzQXhWQSCQO1jV3Z9dIW0jXFcfhGe5axs1GJEOS6SzSgQWeV7OqzRqOydO/1ffuDB5fu7EatQuVsOu3Y4DSjki2QRrgLRto0A2imThzdffganW4Qkbon8pjqREWhgExoCEQNz//gujuN+OBCOUgkdADwDQAg6l5zUctG5MfCo880FCBh5jxzhAH5r/3O0KRJHIDA4KrVSyultrQjG5IhvtkpFKGCWFJYQwZEsgIrIsrZLCshaxZYyjCZ7nBc39oZmXnjpXPDp2rBl27c12k2IYZKWEJELBS2O8VMHO7VVs3FxE0OwiEhInTh1HREBXxwBp7EYRMrYFpRSIBLmOi4nhUXu7upfeX1ptOU5617FpLxyeCrG8rB9yEOhLXwG5+Oqr1vIP/t/5TmxOfu1/+D+89Pwffu2bXiX7wp1a9cgb81eytzc3rJwUZBFRTyvYMjnGFisAJDBaLOOJ8QmcGh6DFxCu/uhd/NP//J+w8bOrMAEgpQsiCW2AuNvF0OgwRkeHcOGZ87izsYG9VhPStnDu9CmEQYBrN29jfGIcWmtkshls7NYghUTb93H27Bx2a01IaWFoYADv/exD/Okf/it02z66zRYkgK2dKt557yOsbu8AgpDyXBhbIgp60EaBcmmMnjiK2eefxPPf+Sqe+/YrmHnqLDJTQ1A5G3sIsBO0sd5rYctvYifuYV/10NIBOogQkYIWBlICsUxG1hmRVHVJEIiSjXjoV4kJBEnJIyyAYAkCAbD7LRVGGXgkQJCQIBhNgCGI/gsgQIZgIfkgwgACAqST922RgNQG0gCWSBZXxCDESMIOUTK9LAYQgyBgYJGBIoLfby+JCeiRuNvupAQQ6hiBjtEyMTo6RC3y0VAh2lEPzbgHyqeQHxnAyOwkTp2fw6knz2DoyBhExoMyGp2eDxWGADSEJe4ehLxxewm3F5IxdyNDgxgbG0Gn66NYLGC7uouZiTH0Ol0UshnM37yNgVIRjusilXJw/dYCjk5PotZswrIkVtc38exTT6DeaGJ5bQNjYyM4e/oUYq0RBiF6u/uQtguyXFAM1JfWcHv+BsJuD5VKBZOjIxjM5wAhsN/tIlYxjExuzzBWSAuBlCVpfW8fS9vbQtrCLZULhWMnjw8NToyVdvb3M83lJSmz5dh37bjo+qq7VDV45ZWHzXymu+EXSGZHHw7PBwuLHAd3R96dPk2Hxt7de/v+uDqEIRXzUxR1OiIOAmGcAhmlyOR1sqUIAIkIZFtGplwttWtkWhm5m1SfTVpTnCLh2NpVTnpgv1U7kZ2bee73/9s/fWrfMePbQcvb7DSEkIZ6Wvcn6gjkLA8TmSI2PrqBaz/4KRAqlGeOYHLuOHaDLnZ7HaQloQuDCAIFN42JXAm1lW3ceedDXyisIDLXEYs1YxCI2FOUTub5yzg2eeSxITtooon8wW3TPPTLg2PsDm9MTeZBc/WZcQWa/daG58P9z5/vDTvC3P1OpZ4BCF2tSRiTJA7c3VJlIKDDKDTGGCOFQEAAtIFHBj1NMP1DWJZtA1pAGImFn3yAiZkpjJ46At8orHRbyEgJiwxSFmGn20Le8SidLcuXf/9r5b9aXHm2U21WPQebGEKAV9HFd6F/CWOp8Cuat0Fz/3rOfv0v/5+lygtPHn/5f//7Xx+bm/mqb4K59xeu5z9aXrG0UeTaNvWUIkIyAjDWGgpALp3G3OgYjg4OIUMSS+/ewMc/eAvVqwtATBBOGpawEIcRtFFw0x7OX3gW0rXR7Lbx7pWriACcP3EMN+8sYXlzC0EQ4uzcKYRxhE4Yobq7h3Q2g6+89BzefPdDXL2+gOHBAXT8AL1CiIsvvoCf/eRdRFGMn8xfg9EacG1YmVR/3FuEtgogi3lMPX4Cx+eOozI5hvLYMETGQVPH2I5CdLpVdKIAERR6Ok7CpkxaLrpk4MBAWgJkgLg/FQMw0CbZZpn0GSddnmQIlknu42OdVCeSFwKRgIw1qL9kAgawYCFlBIgEYgMIAmwpofW96rIUSQUahGTyRr+aHSudVJwhQEYjebb+oPps+lMPNGKjEQGg/iIWG8n7cohgTH/tcr8/W4GgjIYmAykJhjSkMRDGwNcaLd0DSMBrdWBBIE0WSo4He8DDxPAZzD57Br1GF3vr21i7sYiFqzfQ3N5DHIQgknAcG+mUi9WNTdy+fQe25+L03ElMjI+hurcH17KwcPsOzp8/i5PHjmJyYgyv/ehNDJb//+z9WZBl15UdCK69z7n3vtnn2T3CY54HIDASJIIEOJPJpJQiSylKqaosVVqpVN390WZtPZg1LbutzfTZ/dE/ZS2TVF3KUiZTSSqTEziADBAAMQSmCITH7PM8v/kO5+zdH88DBEAyU1ktVSWzfJmFhVuEPw+P6/fdu+7aa6/Vg0bmMNDfh5mlFYyPjSF2HktrG1jf2sb508ewsrqB+Y01tH2Kiw+dw+bQKmZmFhDXmuBiAWwi+PUGbnzzecy+cxtnP/UUTj16Bv2TRzDa1YW7q8tY2d5BqkBuL5It8x7dUUBtl+rPrl2jmf7l4PHjJ3uOPn7mofJw//DbP3rxwJ0fvfYCxLwT9g3NdWG7Wq2/1cZXvuL2plH4pdSN9fVfkOd2m96X2INfItW/iL3D+197GkBzbIx8knQ+vw+Ae78sxtqxbFilmlGDvNhyQx6QZ0wAspuRK5RMk9K8+vaQlKLTT3/p0xd9T3F4J6nlFps1DgNDLRFEMLAM5DnAQFSEqbbwxo9+Dko8VAlBEMAwIzSEPBN2oYj2plSB6USESpYA3iux8YZEyIuAAmihs+T4YPK4AmD8V6jPfyWuXPlV95p9Ir2PfQK9j7+FRLrRILTbhCz79ZaHHQDlvRcx/5UXQzKpIhOfppkHoCYINLQW4hW1jstjr0FOwSYAvAIQUOLx9vOv4NmxYQwWSmg5h420Db+XnpBohsVmFQUb0uih4fCRz3/i8Mv/4188rt7OdtXjZnXqK0vAN7LfiAu2KuGrZ4KpO7WBR37/dx6+8JmP/lZusPLo8u7Wwdfu3Sktbm5YGwQwbDsJGQBylpGgE0V1qK8PR4dGMFLqQnN5Ez/90Uu4//LbQD0GR7lORXomSLMWyj1lHDx8AD193Ui8w735OfQO9OLIoQPInMPC+gbiNEN/fw59Pd1oxglWNjYxONCHi+fPYHpmDt/45nfxkScfx9DFi2jW69jdqWLq+i148VieXQTCAEEhD8OKOEvh0hZsdxkjk4dx9NwJTBw/jMpgLzQXoO0dVl2MreoOaj5Fph4ppNMGSEBo8J73OIN2cpgNIfN7nuQ9D7FVQiYeBIaHokCMTAVMjBAEVoMABMuMnAkAGERskGcLwwxmRs4YJXROwYAMCCBW2Rv0/8LKSURQ6dg9lLlj3VAF753Hio5/2qvAa8dNFDuHRBVePBLxSEUACDLpFF1kTMggyKRzugZQ+L2kGhHteFaJIHsE3BPA6jvFLczIgxBopyxuPWsiJEbJhihwgEopQN+5Qxg7ewQPf/JJrC+sYvrGHczdmkZ9eQNJKwaHIUo9XRDvcf3dm50lz8F+ZEmGZz/xNHzmMDO3hNW1dQwO9OORh89jaWUdN+/PYnRoAAvLq2BrEUURjh49gmt3p7G9uYUDY6OYPDSBTARZFOBjzzyFu7fuY3amE8we5iJ4hGjOrOHVf/0tLE3dxflnn8DJEwcxVC7j3soybi0to5mmiIxBBEI1zcAqFFqDpfUN/LDRsucOHSweHR2f+OhXP1vomxgduPoXV8Z355d+Xurru1Wq283yxnRr5dKlDIffEHwD+p5yvHfNO41fkxX9fiL9wNLxYbTbNJWmNJ4kHe9zjyNtd71nfeNGJ+uZjFHKrHJ+V23Z/4I870G6e8jDByZfKTW3No48/He/dPrgQycPLKaN8lKrZhrqKELH4pNjhpBBxebRoxYvP/c80oV1mCgHn6YIwxAUWGSiYJW9HQBCmRkFa8AAsnYMOK9MxhHYA/JL/zVxjvC+dI3FD7mh/wM80Pt3133sE+h9/K/E+7yHEe/JfXiBcOeDn1MC4H4NidaKJ2QApaww7JJG06v3GpgApSBEpq4TF+YFTjpkKMpFnSplTwCH2L05hzuvvIOHPvMxVMMESkDDpYiJULAGu1kbK0mDSjbiU09crCzcnTm98NI7zxZ686ulrfV64ytf2cE3vuH/Zv8UCBilPC5dOvB3//l/9cTw6clnfZ6fvLEwO/rq7ZtRnKZUjiIIlFQEunfMml7Q392Fo0ODmOjuR5gqpn70c7zz3EvIljdBJgKbHMgxnHcIcxH6hvvxyCPnsbCxgbtz8wiKORw5ehD9/b149foUcsbAhhEeffQh/OTKSzg8eQBJkuCjH3kUM3OLeOXNaxjq6cM/+/1/jFdeeQNvzizi5u07IMOI4wQILIKeCpx4ZK6NLAowcPwADp89jkPnTqBvfAgaWdRcitm0ifpujNhnnWVAUmQEBNwhwBkBjhkRAQ3voQrkuUOGnVM48YjIANJJuwhtACsGeSaE1iJki4gNIjLIWQtLBhYMCwK5Tj6za2dw7RZckqDdaqOapJSlGVyaIEtdZ6ExcxAnEOm0CtLeNDp1HlCCMQwiQmAtjDXgMEAYRSBrEIYhisU8EAbI5yN0F/KgMAQFBhyYDqlUj2Rv2THzDrF4ZOLRlgxegdR7JCKwzACkYzMhgueO0p6QRbqn6yXqQUSIRZC6FORilIlhhFEwFr1BiK58Dv1nD+HguaNIdpqYvTOLmeu3MXN7Go1qHVCgmIvgJcD61g5q9SbevXELx44cQn9XFw4fPoipe/fx3I9ewOjgAMCMdpKh3mrjsYvn8eab19Df24N8PofPf/YZ3Lx9H9v1GjbXt3Dk0CHcmJ5BV6WIT3z6Mt5+4xp21tbB+QJsVIRKhsWXr2H57gwuPvskTjx5EefGDmCgUsH1+QWsbG/Di8Kw6dhvBAjDkOrtJl669i6t71Rz5w4dGj779MPF3pHB8mvf/kn/xus3Rmy+61pQoPmeltYq65eTudMbghs3AABHD6R0D0C617d0bz7U90d4AsB7ivSH1ej34eBYRj4B5H3iw14KEb1Hnq1VWywKR4mG9ZI8sBn7wYSy3TKnhdSa7mKxurk20nPh+OmLn3j0+A5c945r23raop6QseUyFIhgyKCgISaK3Vh6cwpzr14DcQDxAhgLm4sg4pGph2NCDwOxV8TovDZigySOFSICpgSCjIzZMyUJ3r/sOLLng/4Aid4TpH+lLv1hFX8f+9gn0Pv4W2nb+PDHe/F1v/KVPZ3fGFZ9lqGBjmbRuQ/kkUeGRPKkWqf3xpWBFUBc2owdPCQfMAx11lRKRPDEIDJgMsgVCp0EgcTD7EWEXf/BSzh49BDGD43AkaItikLAcFDkLLDUrKIchBjLd/PHvvjJ4T9b3niyPbs4Wyrldwb8+o0NoIVfJa3gb0bSBl79QeXIf/F3Dn3ki5efqoz0fHY7bTx+9e3b5buLS5YNoyeMqOUEsXpE1iBJE0S5PI4N9OPk6Dh6cwXMT83gredexNb1O4BnmKAAKMOnGeBSjB4aw5lzJ1BrtfDTq29iYnwUYxPDKBWLWFxbx/ruLrqKeZw5cQw37kzjzRu38cilhxBFARaWVnDtxi3kwghf+/IX8aMfvoA//uNv4u7MPKAKE1oQE6JSHkncRuYc8oO9OHzuBE5dPI2e8SEEPSU0NcNs3ESt1UbNpUg7pgdk6MTDhdzJNnYQkHbi3vIiYCKECmTew3YSt0AiqNgIBbKwxqArjJAPcgi541MOBECaIW2lyFoNtHfqqO02UN3eRW17V+N6XV0zlqQZS9JqexcnkqWpIMt0r14QECGIdtiqKsBEwJ6XVcGdfvA9qxLt7aIpOlGNlhXMAHGn2CUMEOVDyuVzZHN5isp5Cnsr1NXdRZW+HnT3dlGpXEQQBWoKOaKcgTOEpnjE3iFzGWJxaLl074EDYOqkezARcujkUsdQlJiRkCJlQpkIbVV4daiJx2qrhXwT6Arz6A7z6C0VceTJszh+6Qxqq5uYnrqPm2+9i62ZBSDzCMIAmQryYYAbt+/BMGNpaQUnjx9Bb76AJE1RjHIYGhpEaNbwzjs34LxHb083qo0m7k/PY2tnF2eOHkZgQ3j1GDswisX5RZRdikMnD+PM+VO4+tpbiJsthIUcOCzAV1O8+ac/wP1rt3Dx0x/F4XPH0HuyhBuL87i1sIQsTRFZi0wVWewQMMNawt25Wdrc3uZzh49UDh8ZP/XsP/pS//XRwdEbz700uCP+zWJ/ZXpju7XVWyq1gq7Y83ag8W5Fx9FZnst1b8rRAymF86FOfZgQ/jqkKR0FECed5A0AkKybHvg3aC/izeTzwuGOBnURk5Y0yOc12/u6vp1R2q3WmqBQbTSHuL/n1Bf+0e+c8l25sc2kHq3GDULA8KQoGwMRAnnGgVIFfnUHr/z5j4HYAWRABKg1iIoFwJi9oLqO7z/XmZnAUmeZNY1TwIsnpoSEUmT0XpHLr0KHLI9/iE7/8vFAGOr7VGjClSuK/UzofewT6H38rSXUly/jV/mf9deR6T0UAAizqrTpA6fuTodwkw8EGrhao+nUe6GQYE2AlnbiuiwTPASpOIT5PMAGmrbhsbeYstPAy99+Hp//J38fg/kK2iB4zWCoQyoD9pivb1NYCXTiwJD96G89O/Sj/8+//WzitMqp38A/vryMf30l+Rt10VYlPPKIxTvf63rs//JfnTvz0Uc/U+grPnNvffnoa7dulXaquyaMQmIAbec7y3AAEu8w0teHYyOjONg3CF9r4+ff/TFu/uRVYLcFthHIGPjYAd6he6AfT370Edy6fx83Z2dQKObxkScvYW1jC8YGuL+0AmsYvaUSenu68cOfvIRnPvE0vPdYWl7F8toGLp4+gZGBAbRbLfx3/+KPsL2zC59kyJdKIFbELoN3MZwNMXzuKA5fPIWj50+i2FtBwsBO1sZOdQ07WYyGeCQQZCoIDcHt+X4bKggEKDMjVQUpoB4w1DkHyiZAFOZQDiJEbFEJIhRsgJAYmjikjTaaq5vY2NhGY2Nbdza3sbm6icb2LrJaS107ViSZwolAvYNoAuU2RFuAtgBqgblNxmQPurqJjAHUQNkqE3cS77QjYgMRPIWda7WYvX0yURUhJU+ZiKgo1Ks2UngmakFNS9Wi05YRwiCEYYPAWIoitsU8RZUCFbtK3DvUj+7BPhT7e1HpKaOnrxtBoURSANqSoekcGi5F3aWIxHd+Btzh+pl4kChCJrQUSLzA7mVeRwxkqqimLawnLdhGFcM2h75cEV1DFZwfexIXP3oJC3dncfvNdzE9dRfZxg7qLkOQi2AArK2tY21tAwdGhzE0OIADw0N4e+o2isUiRkaGkM+FmLp1D5VKCVEU4tiRQ7i3uIzD42O4fuMWHr90AWQJLklxb3kJ504dx5lLZ5C2E1x/+12AGWEUwROhemsBV5a+hYXHzuCRTz6FJ46ewFC5C2/PzmJzZ6czAbAWPnN7UyzGzm6Vfvbm27RxaCc6f+jo4KUvfSLfPTw4/PpfPH+oObP+Uq7S+27T0Uqwwc3AILVRzfOO1aBQkHi3n00U6T1s6OkPvWWnAPySzSNNCTiKbKxNSBLIe/aND07uTL7jdw7rPRJ0f1CZTcsNTpyxqZFcUAz73U56/OO/89uPdR8aPTyT1EqraYszdQB5xF5hyYCVMZwropcC/OS5F5DOr4IoBKkDRRYwBvl8rpNdvvfvMAEZG4SwyNkAJIq43lKAHBPaRMiIaU9pBz5MpH/hgV78QPzGr3VGP3joKJUUuEwPagn3yfM+9gn0Pv62KdG/pLTIwADJ3kKMitAv+eL+Su+zUdSAdpgJApPVdquZpJmjYqQBM0IAng1EO/FKTgRRPkJYyCPdbsJKJxpMOMD2u/dw/cWrOP/Zp9EuAKutKoQ6G16kBKcOa0md8jbE8Uun84vTTx279YOffdKUivXuevr93T+4tIz/7g33N+LirUqYpAgnTwz/9v/jDz/Sd3TimdT4x167e3PyrXv3i947yuUiOO8pNAZCQMtlsIHFsaEhnBgfR2+uhNU783j5Wz/C7s1pEAJwWFRJHcQlCAzj4pOPoukyure4CI4CnDl2DO/evYdGs4m1rW0YJoyMDGOwvwevXrsBAePSQxeQJilefPUNPHHpIk4dOoxysYg//ea3Ua03wKLIF/KQXIQkS+Gdg6kUceTseZx89ByGjk/ClHKouxjL8S5qcQttydASB0cKhYANI/+elxeIzJ5S6j0aXhGwQZ4M8jZAVxCiHOZQsiHyxiIUgrQSNLdqWFtaxdryGnaX1rC7sY3adg2u2gCShOC1kz0nnIHQhGKTlJbBZh5KyySyCWNrgLZINPawCUhSdeKReIXtBG/AkwE5A1LWzpjEQnwIojwEBShKUBTAe1uGhjNVnwHs4FVAKgAD/KCSxYdqbJ5JSqLookx7NJUejdvd2W6rlC2tFxtAbo00gCGLQp6i7jL1DPahONiPgfEhjE6MoHeoH2Nd3Z0sbPGougS1NEEza6OapchU4X1Hkc7v5V4XSdECQQD0GyDVjh3KxRmW2w30BhGG8yWUozxGzh/FkXMnsD6/gttvXsfNN99FY20TmQcKQYTMC+7PzGN6egHlQh4feeIRTEwexF/86HmMjwwhcx5DAwN4/ZXXceTkMaRpinK5gFw+xMziIpbXNnHm+BF09XVju1lHqx3j8OgoHgofwvz0PLZWtxDkIxDloS3B9E/ewMq9BTzyucs4cek0ugpFvD0zi/vLy/A+AzMhUEKWOTBABsDN2/dRrdWjM0eOBCeePJfvGeorvfxnP+zdfufeUBjm39aeaIba6W7cKsZBjjK0WuAgUBNFevRASimAro0ueeNDJPr918qjAHAUiHc73mcMAdLsqM/v+Z/3ourMZkGD7ryG5Xmd6skrdto0vlthN1jixKW5XKXQs7W5cezoJ5545OKzj59b8clALWsH0IwKUUCtzCMghgihywYYz5cx+9q7WHj1bTAF0NR3hiKZAIUcokIRiffIfCd7Jt4r+TE2QGADOCdot9sKIhcArVh9QgF508oUHwyA/pU69AeY814ToQEw9+vbCPexj30CvY+/5XgwhnSOHlR3/2Wf3kITuV8599vGth3UYpQKOEhbtVrq2rGP+goohRFCJZAXKBgeQCKCUqWCYrGAVDojcfEKks6W2PUfvoTJMycwcmQEicuw61vwBGTiYRRopE2sm5DK5Yg/8cVPlDdWVi9uXb+TcCna6Vkr/Hzn8uUVXLni8L9ovPPX+Q/7qXj4n3xl8okvPftkZXzws1tZ49GrU7cHZ+YWbBQGxMwEJ2AmtJ2HZ0F/VxmnJyYw3jcAk3hc/e4LuP79F6G7bTVhDvAE305ARDoyNoIzF87QwtoqbdWqOHP2BJY31nFvdg6hNbg9PYuzJ44jzEW4Mz2LhZVVPPXwRURhiFfeuoax0VH8g9/+ItZW1/HWm9dw+9ZdmMAiFwZAYNFI2oB6BAM9OPnQGZx78mF0TwwhZsVau4Hq9jZqWYy6d3t13wTDBA9FsNc0Yg2BvCKnikQIAVvkYdGXK6A7DFEJ8+gKcyjAwDVaqK5sYnF5HQv357E2t4z2xrYm1QbQjgWpE4AFxI7YOMCmpNJWpRpEtiBYUsGcKt0H3AwEi+qCbSRBE1GU/TXOCcLlywaARb4dwsc5MBXAVABg4RhgdXvmfg/nBTYTGFJkEQlnBoIAVvPeSxmGupUwAOFhsA6BZJCM7QWjG4IKlAqoZ1GyvRGuzqyGMGTv5wLmYs7k+3qo/+AYjR0ax8D4CAaGBzFS6YZ09aKapdhuN9FIY9TSBLH3aIpHE4Jor268ropMXCdOjwnsPRaSJjaSFkKyGMjlMVwoo/9APz46+Wk8cvkJ3HjzXbz78hvYnl0ChBDkQlgyaLfb+N5zP8WB8REcm5zAmfNnELcT1JotfOzjH0W90UClWcStu/dw4uRRrK1v4NDBMTTbMU4dm8Tq+iZ6e8q4OjWFU0cP48Cxg+jurmBhdglZrQEuFWBthPbsBn72r76F+VvTePQzH8PHTp1Ff1cF70xPI2604JUANqBMYJigxtLy0ip26y1+6MTxwqFDIxOf+yd/r/zz7/6kMv381YpzvmjzpXsmTjdDo63EB2nYmzlfTwgYQ5Bf0jfenweNX5EVffSvOGN6gAfNrCaKFACmpjsK9NGBA1Qve44zifLdpa6devVg/tDoQ5/6nc8/3ApovNFuF+tpi9QoOfHIBwFiryiCcajSC1tN8Pp3fwKKHSAWxivIWHhV2DBAvpCH874TBcgGQKeuvmA6UYo+y9BqtAXKWea0FSgnzrGAvf4qoWTxQ0kcI9kQYQhYXFvTB0uFc/t3z33sE+h9/C1Xnf9K9XjEe3o/q5CyJ7ZGxZX3GiA6pLqE9+JAAeTxi4FhBcAmgC1Qe0CRj3xWb2VZs+3yIITGgo1BAYSMCE4EzSRFV76IfKmIHe8AWAS+09jmA4ZsN/Dzbz2Hz/3B76I/X0KcCBpJHcFeIxwbwk5cxxJZOtw1oJ/7nc/1//H6+qXW6m4j6Cm2K+3dZu0rqOIb+F9mqfDyZfuH/+r/WTr7f/iDo2eefezjud7S35nZWjnx+p27le2dHRMGAaVeSWUvrkwJahjjA304N3EAA+UuNFe38fN//yMsX50CedYwLECcwHmvhWJBj548DJuL6LVr13Hy1FEcODyOq++8i4HhPnR3daHeaODskUO4fusesjjBl7/wGVR3dvDujVswNsTX/t7fwY3rN3H75l28cOVFkO3ciMUQWmkKuBj58SGceOQsTl06h/LoIBqSYK69g624iVqWYCdLOi4Ia2BZkUDfi5JzBMB5tJwiAKMrCFHK5dGbK6AvV0CRQ4Si2txpYHX2DtbnFnRtZkHX5pfEb9U6ZFnJQ+EBcgSTkjGpeoohaKlHAyo7KrwK0nkG3xfhaYBWYLiKciPG+oBg8Iri9N404spfo2TnyhUBkOLrSDGFJtYvb38goaH9vs9lAP3vq5J/kPhwOLDYyUKknEeQleGkF5b6mXhAvPRDtI+s6VXSLgBdJFSBDUsAlZBoXuJWrrnTDJt35+2cNQaVIleGB2jwwAi6D47i0LFJTA72EboqSCHYTNrYTWPspDESl6HhMtTVo8swDHUSb9oqUOqknKS+jUY9xmajiv4gh75iGYPlrk4yxqWzuPfWTdy4eg1rt6aRpTGCMIdCmMPqxhYWllYwO7eARx+7BIFiYXkFaxubOHvmOKbuz6BaayBxggtnj+NHV15GHLexsLqKS+dPY3hkALuNOrxX9IwPYnxiFHdu3MHK6gbUMYIwhMSCueevYuP+Ii598eO48NgZ9BZLePPuPaytrQOZgMggzTxEFGGnIIZeeuttbB3eDR46eqzn4//ZF84OjI/kX/3Gc8X6TjUKi+W70pb1nLWNdBsxelsOdUiQ/0umVaWSnm63Kf3QH0v6y5M5DoJOy2AKhOV5xUYep9ttqpV3OU6jgCOUsywe8wFd/PzXvnzJ9FeOLsc7pdW4zgkLEXVSaLwSSsQYzpcxTCF+9J3n0F7cACOAZh6WLbwIRBzyYQjOhUi9f6/ExxCDSWFMACYDFydo1mpCzKmob1vrkyKrT5QVpb3Wnz2sABjJMvJAJx7mP859aF+p3sc+gd7H316oCEnZE6RCkoIe7OI9UKYb2PNAAwDaACyKeNBm1YlCTWxbA7I+a8WuWW36Mlst2E61ryeCqsBIR630URlRpQwYAoMRChB7AXkAxmD9rdu4+oOX8PiXn0Ea5pG5FLGkMAyEluE9sBnXUQwDnjw0op/8nS/0f+9f/clTceI3ct35al/8kbe28HLjf/aL91e+YjD7UtcT/+c/OHvq6YufcRafvLU0f/SNm7fLSZaZXBCSl86CDxPgxSFfKODEgQkcHBhE2USYf/MWXv3zH6M9tw62uU6UWurVidfBkUG9cOkspqZnKILgkUcvYH5jQ28vLdJjD5/H9Pw8Gs02it1duDO3gJNHDyNvLZ6/8jJazRa+8uXPY2N1HT/6wU/x+itXO49DpRKMYTTabUAUlQPDOP3kQzh+6SzC/grqLsG93RVsJTF2shht8WDLMBAkUCTeIwdFObBoe6AlAkuMkSiHYphDV76IvnwRXTYEEofGyi7u3JvD4p1p3Zpe0urqpkej5eDRBlOTQHWIaUC0pqINqDQU3FSgSURN8tJSNnUQ7xrD2z51m2JkExxso51v/UeaPnTOmz98j1H/9b/CG8jwla+kWFhIETVTaJDBu5hN0BDRLVZTgqKgoDy85Ik4LxlKEClBpAJjuom0F0A3hLp1p1msbdej2s17BrmIr/V2U3GoFweOH8Gh00fQP9iPse5+tNRhK4nRSNpYT9popPF7DY4hE4oMNL2gBUU3o5O9Hjew0KyjUt1BT76EsXIXTn7iERx96BRmr93BWy9dxcbMMrI0Q2QNQpPH/MIKFle+j55KCadOH8cjF89jcW0daeJw7PBhvPLqVVx56VX09FQwOjyIsQPjuHn/Pk4eOoD5lXWM9vXi+s27KOcLePLZj+Ldt25gfmYRSavdiWajCK3pNfzsX34TG/NLeOiTH8EzF87hxvQspu7NwbUTRMTIiJAlGdhYMCndujONZhzbR0+erJy5fOlIubsS/PSPvp2Ll3eKUb5807f9is1xNZdSHJdbmWmPKQ5vEKZ/dZrEVD6vmAcODrT5L1u4fj/S+gE6fXgeaf0AtZOaDSPkfBQNbtd2Tj35D7/8+MGzx04spI2uhksCsFJAnbxmI4zMC/qjEg6WenDzylXc/9lVWBNAUg8L6qRvcKctM1cuIl/MY805eBHkRJGRwgAoG4O8tUibDUprDSWmzDq0yCOljPVBxZD6IlF3Cln1NIK/3NDxAAc/rEI/sAReLimuvOeD3ifO+8B+E+E+/jYo0PTepnSjQXCOkGXUyDLORxGrCGkgrD7Yk0T1vUYtlJRKYqnBji0bhioRgDYFwlQX1i7Z5hIiqHFERfHJmcFTR04NHT3Q3fSJ2WzU0RKBgGAU6MoVMFTqxub8Klan7oJhoZnrtLft+ffIMNaXltA/OoyRsWFkUDRdBhgDQ51gBK+yV0LBdOzgAQNFYfbGraIJc6lPZSE9N9LA1OL/fFaOy7DwMvjMf/2fXzj86OnPxRafvDk/e/rq1K2iS5yxNqDM+44/kQEPQU93Fy5MHsSRwRFEqeKtH7yI1//sh3CbDbDNwcCo96JkWQ4cPqCTRw/Su3fv0MjIEJkopI3qLtVabbp04QzuzM3DE9DT04X7M3N46NxpEAzuz8zjqccfw3B/P95+8x28+uqbmJ9fQlQoIMjnEKcJUp+i69AoHv7cZTz1pWcxfu4YaiEwX9vCvZ0NLLUbaLoUAXwnEeHBhhx16qlTryCvCMliKF/EsXIPJiq9mKz0YkAtWstbmH37Fq79+Of6yr//kcy88LrbuT3XStarVTSzdVKzQDD34HALmd6Ekyl43AToJmBvQcwdKO4b5WkhmoFiFhrNq3PLULOOeriLy6+28a/n/mZFGU5NAWdzjDhnYWAAsKgCypkqWuqpDmO2odhQyBoUy/CyDMIyBKskuqZKW3CuDkGLlFNSFoo9+d0mxcvrWLs5TbeuXsf8rXtIt2pkvXbU5Eo3+vNF9EW5vZpDhTiP3TSFJUKFGSqCqvfQvdbGtkux3Ghgp11HK01AuRATRw7g9EPn0DM6hGarher2DnzmYPcKPNI0xfL6Jsh5HJmcRF93F27fm0F/Xw/OnzuNnUYTd+cXkQsDFHI51Jst7FRrsIZx9OAEiAgr6xtoJwnOnDyKzY1ttJMERgkKA6QOm7emsby8hqGRERycmEAhH6Fab6AVx2BmQBTqpWNoN4Z2d6rYatapUimG/WNDhckTh0rLq+tRbW0LQbHgKEXqQC4VFey0tV/6UK1WO8sYYfjLaRPOUXex+J7VTUJHKjmCCCHau04mBOIuUF8LWlVkzSK1mG3bIGcGy73bmxunjn36qac+9Z998eFV1xrZlTi3lTaZDZFXj5ANnBAKHGEsV0JrdhU//u+/Ca22wRmBXSe1xoFA1kAkQ//JQzj+xEPYiutYrtdA2sksD4nRmy9iqNitO9NLuP3C64l1vKxOXyMK5rM0bXI+FGICkk5rIre8EBHIdGhJWUpUltJ79xCtlUi1RMxNMDO6RagKAN7Te62EaUo4/l4r4T72sU+g9/EbT6B/QZ4f3BD2KryHBgbIpymLc4yo6xdV3u8j0RoIJd5wwXjWBwSaCE6NkoZSFdFeABLBmIALaRqfKk6MnDx64VRvTN5stOqIswRMClJGIcyjr9wFX23i/ps3Om0WDmAvynvxZUIEdZ6WFpdw7PRxdPX2wgEQcfAPai4MIfOdDA/LBieOHKH1rWrv2t3pKCrkNgupWY8HDzYxN6f/qZsF8e1LQWF8vP8L/+w/P999dPwzLco+89qtW8du3bkXEdh0DpjvJJGogxjG+PAQLhycxEhXL5K1HbzwJ9/DzE+uAo7VmhChMUjiRKJ8KM9+6rIm8HR3bpYOHBzloZFB3FtcotHhAbKGsLK+CSHG5OgwwIwzp09ien4ZpIyHTp9CqISXf/Zz3JudB9kAQRQhzVK4LEZ5YgiPfPEZPP13Po2J88exawTT1U3c2d3EYqsGqIAhMCog6N6JRYidoJ46eCX05fI4UOnFib5BHCv3opsimJ2G3r86hTe+/zO8+b0rOvPT19zOnbm27LbqlOo2eVohzzPwehtObsDJu5zhBoNvdXzMZg7CyxBdh/B2YOwuidZFtYEULVhtw9sUaduhlzzuHJf/5D/rvy6+DsbaoRBtzQHIgTkCNLDWkjB5K5wKSQvCTQSmDqYaQDsQ3obIJggbAG8CZguKGpy24TWFhychIWUhp4o002RtU1eu38W9d29j+c4Mapu7KJsQPcUyDnR101CxhJ4ghxxbtDKHNM2QOgcLRgAgE0UGRcCAqMdGs4GdZh27SYwgCnDw2CROXjiDvtFBbO9W0drYhBBgoxBePFYXFrG4ugYFcPnJx7C6uYV3bkxhbHQIPZUiWu0YC0srODg2ikajhbGRIdybmYcXgQ1DWMNw3uPY0UMolYpYnV8CRBFwAFJCa2UT96fuISrkcXjyIPp7Kmi5DLV6HSp+z3cPiAjCMKBavUHLW5tU6SoGw2PDhYljB8vVViu3eX9WbCmXhk6zdiq+q9Tj450d7e/rw1i1io0Pk+gPEWifJKz5vs518v0EOg9QwtCsQFKoUoYSx2E75P5CZWd3Z3LgwvHHvvh7f+8j7Rwf2NGkuB03rMCR7pUkMRg5WBwodKM7EXznX/4pmjMrarwBUulweyKACdJZ1KUDj13AyNmjWG1VsdNuIkcAgwAy6ClU0B8WsX5zBrNXb7SNpwVO6TXj00VY2+a2VcR7tePWKQWpUkzgDy0HSpaRipAWhajbQGs1AgBmRnWPbH+g1vvn4fv1adq/Fe9jn0Dv4zefQE9O/oJAJwnBOSoEAUuWsZY76vOHFwm1KARfIHjPgc2TsucHxDrKG3WpSr7klJ1VLRgGBfk0aR2P+rpOnHryoYEWebverKGeJsgRISCCsQEGyl2wicPUa9c6yzEOMNKpWhZ0ao7BTK7ZxMZuFadOH4fJ5+EAxC5DaDsFC50yDkAECKMcDh88aObnlwrV9e1yqVBYaCFbw9+fS3HlP9E4UZVw7N+EA4/09z7z+189131g4FN1l3z61evvHlxcXMyHJjDwHlCQsQaZOnAY4vTBCZwZH0dXkMfc27dx5X/8Nqq3ZsE2B0sBrELjdiwHThyWsxfO6LvTM0jU0+lTx7iZJHT9zj30d1eo0xWiKBQLGBsexPLKOrLUYW1jG5975hMY7+vHN//s27j61nXsrK0jrJTgnYdLWigM9eKRLzyDZ776BYycOYya8bi1vY672+tYbdUR7zXrKRRMCkEn0SEWIHECawJMlLtwbmAY5waGcaDUrdhpY+n6Pbz1wxfx+rd+jOkXrkr13rzzu+02CW2z0JJmdA9Ob8LTFDzdZMVtVZ4Fm0UlXjcwu0LcQCoxiFKwyZBBjIdkQoBRDdnCKwgs3Nlw25vlP1FWTG3If8L304Nf/B/0qhOXLJZdHnDFMLRFryYP7yJRGMukjtUjExeozyyQmYxTI1nqiVIIUhhNANOG34vgE20Q2zoUDXhtwWkM0QQeCcFkpCRoxNpe2dSNW/dx962btHhvHr7WRN5GNNTdjbHuHgwViyiYAAyCcx6xdDy0DkAinbIR0o49ZyOOsduoo9puQkOLiUMTOHfpPIoDvdiu7qK1tQ0FoVAuIU0zbKxvYmrqFh46ewq9PV3wCswuLuH4kUPo7u5CvlBA5hzml1dAbGBsgFwYYnx0CLv1Bm7PzuPA6DBGx8dQr9bQbrQQGAsVhtTbWLo9jXYc48jxo+jv7oKootZuwXkPw50HcO88AmsQJwnWarsURKEZHBnIDR+eKLacK6zfn4VEYRZxkGbqfBYWRJiBYlHfU6LTlJCmdLrdpq4DKWXNiH2Wke9KWbKQ1DnSSieBowdAzAwUOwsjEoSUsA9MpVhqtJoj3F+59NV/+ntPRKO9p1eSRlc1bdpUUurwYQaDYZQxFJUxYnN4/k+/h6VXr8EigCZOrYcGUDXEcAAJBBoZOv/Mk6gcGMZaq4ZmloDQWdYFGQwXuzAQFHD/6g2sXr/bMrCzxulrVt0yJVFMUVsg4d6kMQG5kiJJHrRvEhnzgbKYvcQloF7GMjdRZe4Q5w8T6JUQwCQBc/sWjn3sE+h9/EYT6A+qzw8qvOOYoUrFKGJxjjUsk3rP76nPec+wQtAiqQgVcp7VG4YRgkQMCsABxFmvrKJUZFTrhnPdiJIsPcylwrHjj54fpkIQVNtNbKcxCh2tA8oGA+UulIICbr35LrKtKgIliPMwgDoREHc80xRYNDY20SbQyZNH4YyBN4TYOwTWwEERe0HqPKxhKpcrNHnwQHTn9t1SvVpL+/O5ndbNwgbur7lf+Fn/I+FPvmLwqa/mJr/y8aGnfveL54Kh7k/utOpPv/TO9aMba+vFwFoW13kgISI4eBRLBZyenMCh4RHKe4M3n3sR73zrx/DbLZCJNDABsiQVykV66dGL0j88KDPrazAB85HJMZ5fWeW1rS06evAAdZdLqDaapN6jt68PjXoLIIMvfeGzMMJ4/rmf4MUXX0VtdxdBFIByAbKkDa4UcPGTT+FTX/sSjlw6jS1OcWd3A3d2NrDUqAHqIMzItFNw46FoeUWihEyAShDhaE8/zg8O41jvAPpMhN3pZb32w5/j1W//RG8994LfvTmTut1mkxyq5GgNGebJ444m/hYc3WY29wiY04yWGbTByrvGc0MMEqMmM2AxKioaUiDExqrNGCYgaw3UZp4s4EKo5gEqBGQKYl2ERmRxYZJwvgxMbfzHt3N89miEwYE8zhyJ0D/BOHIEmJuTX6s+v3wwBPk8jC16NkUo5cEUWCJ2wgCxBCICIk9qfeozMWTEWBUvRkBeICQgeIhkAFIoEjhpE7QFojoENSjV4LQGpzUSNBkcIxOnrVTbS+u0dP0W3btxl7YWV4FMqLdYwURfP0bKXShFEVgUceYApyhAYbWTJw0oQurUkq80G9hq11FrtxAVIxw7dRQnL5wG5XPY2NhEUm+AjEE5n0cjjjEzvwhVxanjR1CpdOHm/RlUGw1s7uyikM8jEY9Pf+wjmFtcRnexgJ+99iYmxoYRBhYrG5soFgroHehHd1cX1uYWYaIcDFtokmJ7ZhEbm9s4cGAco0MDsNaikSaI0xSMzsOeAAhCS2k7xvLONoehsV19PdHB45P5DJpfnVuwxoYC0tRkmctn6mNrdaBY1IGuDeotTlBvcYXicJgfkGdXarNk3SSFhIUz7pIKJSZFDICYAS8krYSzvAZBmM/H7IYS9ud++5/+3seGzhy6sJE1B3ddHNaSBjGDhIGIDUiBis3hYLGCt376Cq595yfKYiBtJ8bDm73m+AyAV4UwyFQKeOzzz5Cv5DBf3UYrTeAVsETI2wjDxS5UOMKbP34Z9dnlWqDB/VDo9UzMqqVW2lnC6Fj2iPNAmoKKCSgmUMfeQ+JcR33e+wUA1G3Q3Wyi9mEC3akCB0ZT6pDofRV6H/sEeh+/6eQZlwmT7yPPaUoQoRHn2IUhqwiJMe8pyygIqRQI2rm4FkVITYdAK3sGLIEIxKJOREm8chhomBpOyEdKGE/ZHzn+0OmJ4lBfsBE3qN5sggEETGA26CqW0FsoYe3+PHbvLcAaC8oEogQiVVEFs1FmJgojbMwvoNjXTZNHDiLOHNR0Guv2QvBgCOREyBhGf18vDw0MhLfeuVnOWokv5wqbpf/hfL19+3b2H+34/sEfBPg3f16++Pv/YOLc556+GPR3Xd6o73zshVffON5oNAuRtSZLHBl07nwiDr29Xbh4+CAmevvhdlr04p98Dws/ewuUkjIHsGSQNVsyfviAHD42KWpZby3Mo6+nQuWuAt+dn+fUZXRkcoJyUYQ337lBp08dh80VYMii2Ypx4fhxvPX6O5i6cRtLs/MQw4gKOcRZDDGKycfO4TP/6Ms49fQlNALF7c0V3Npax3KzBhIHJUULgNUOd4MoEucRwGAon8eJ3gGcGxrDgXIPgkasc2/fwmvf+Yle/ffPu5VXrreT5c0aZbxNyuvkaQVeF+B0Gk7vsOCuITstHovsdJ1Ed5lMkzziAOxERVg6qr7z3oi1BlAr6kMGhUwaARRCETEhR0wFZlNiMl2O0GWgJWMpF3iyPlPgoUnFmScVU1N/jbZ1gqoSPv5xm3+4Ehw6czyXO32i3HX6QF9w/MhEaCqTpXxpzIpWqADqKohrn3/CY2rql9W2j4OQjlv4IIJqwbLPMVPAzOxECMpqASFrPTxrBlGoqiFC6pTAlgJVMl5ZiBhC1BEf1UORMaitHk2Aa1CtkmAHxLsk2CUndQi3IJSSsiNRlXoT1fllmn33NmZv3kdab1MxymGoqwtjfX0YyJdgCNhNUjTTDE4VFXQmQxCBZSAhQTWJsVirot5uIV/K4+jZ4zh+7jQcKdbW1hA3mojyObAINje2cW3qDo6MjWK4rw8Hx8ewvbGJU0cPY3FpBSsra4gCi1Yc49zJ47g5PYdDE+PoXF8IjUYT5UoZXT3d2N7chk8dwiCCAaM2v4y5+/PoHRrA5OQEwihA02dotdsgQ2AovPcwQUAQocX1dQoja7q6yrnxIwdKnM8VFm/cDkSNhrkoS0SyiBJpZ6RSs8haLc5aOfZpSlmzaVypxJJa9lHbaFZkaEQ5ZiQmBdlOC6G6CrlSzgbKBZ+PBhut3VOf/C9/96mTTz38yGrWnNjO2rntpM7ERAJFjg28AKUgj8muXmzcmcGP/uhbCDMCUhH2cOQ1g2gGqChIPYMAz8XJMXr4k09RnRxma7uAz2C4c9nvigrozldgGimu/+BFJFu1HSN8l1z2JryuG6MZAGjK/IAcs3NKXITmWkQxvdcJIN6TqhIxv0esTbutPcyoinT8zw980A9I9C8I9D553sc+gd7HbyqB3lOe+/fIM/aWPkSo7D35KGKfZYww/IXn2XgGUkAsFVVJ80LqhREyQ4Q1NASjRN7BQ4VKBYXLFL5NEprAhHYgi1uTw2ePHx44OJarJW3aaLc6ijITHDPK+SL6ChXUVzawdO0WoAbeKywRDANKpKA9P7QomIkWFxYxOjGOgdEhaouHIwVBYI0BGQOjgqb3ZNhgfHSUC4V81/3rN0uGiRjpWjxebmB6zf3/fWw/+9kQG6/1XPzd3zo0+dSlx8Pu/Cfn19aeeuXta5NZOykxYMUDpCA1BIFieHQIZw8dwFhXDzbuLeLFf/td2p2aAZucQhksEK8qA2OD/sKl87K0ta1btV0cnByjnt4KL6xv8aGD41wu5tFstmir1sDHPvIYbe/UsbNdw6mjh1EKAszcn8fVF19BI02RqxThfAaXtdF/ahLPfu1LeORzH4P05HF3ewNTGytYbtSQ+nTP9yqIRRABSJ1H3QsCMpjo6sG5wSGcGxzBSKFL26tbuPWzq3j5Wz/Uqe9e8dXbc7E00l1WswK1M5rKPXJ6jz2mSXkWinlVXiLWdShVWbgBogSsjhTemlBdp4zCQGGg1jI7G3oKDFEIg9CKRAwKRXwEIGeY8gwpWsNlKHUB1GUsl1m0QJ0zlaOEyKEpGD7sf61K/MH3TAig9Id/+Id9V/7sXw/de/nd0ek70xMbK+sntzd3Hm3uVi8ntcYTre3Nk0rcX4hyvpm5lq8mbcz9iuXFK1AcyBkkQRjlohCKAGC2QuxI1VLncYEIAhY1ZGGJAePIGJBxMB2NEiwqJtLAGFaGGFDnzeQMI4FIm4hbpNSAogalKhQ1hq3BS0NVY3hkUKMkRIgzpBs7WJ66S3ffvY3dtS1EQYCh3j4MdffQQLGIvDWIsxS1LIPb+yaZCE4VDEIGxWaSYKW6iyRLUenrxqnzpzB5/DAS77CxsgrnHIr5PEJjcPPmXezs7GJsaBCtZgsz84s4cegAyDB6KmXcW1xGqZDHUE83FtY3EFqL3d0acrkQcZwgyoc4fuQQars1NHZqYBgwW6Rbu5i/O4OokMeRIwdRLuWRQlGP2yASkDEQL3uLuwYrW5vsoKa3txL2jw6Xi92l7sX7M3mXZmAEaRZnWUTWJ96rRA3yNmWHvBFjuBSGxpbVxMRciYAoEGJvNTFpR30G4JFZ57nApfxAtbp1+tJXv/DUE5//+FObEh+sSbuw1qoasHT8O6pgJVTCPIYKFdhqG9/9H76F9tImyKkiUR8KZSySQJGyMc4TEATWeJfyxMOn6NiTD1HVx1it7wDq4RRwSugtFDFU7EFrYQ1TV14FtbJN63DLeLwDm2yxsocXUm+pGKQmNULgHJAkeECiNfSkDU8P/m8PCDQAmHZbVZU+QKIfqNEfJNB/eaHXPvaB/Ri7ffxNJdKX31cG8H78itru95ZiAAAlFCFoiFBBhIACVFLSMHpvlKdRRApldULwQmSNkjhPyNfQSra3llbjE04kH0bGGgunHsyMlgjqSYyUFAMHx4FiAWh7sDWAU3ghGGZVJYUQ4EDeE8t2g57/1nP02wO/i4HeArx2EgQMdcbNYgg+aSPHBhDwmacfjRo71ZOv/bvviQlz7e5c5bndz372Nr7//fR/YsQS4StfCbD+Ws+jX/ny8cOPn/6YROaJW0uLJ6/dvD0A5/OGyYpTAhQiHhqEOHZwAkdHh1G2Ee6+OoU3vv1TyE5DmfPQVFWJxGexXPzIo254bEh+8OLPcfrsMRqfHDEzy8s0vbhEQ/195NIM9XqbwsDi4vljeOPaFI4fOoJyVMDqwjJefvE1pEmG4kA/nEsRtxuIhntx6dmP4NRHLoLKEeZrO5iv7mCmXgWTosdaNLygroIcEbwIdgSIjMWJ7i4c7OnDcLkLoVPU5tfxxmvv4M5r76C9sOrRcikZ24DYbXisiOgyqa6zoGqNbRlFKl7STCllooS8TQzDwSh5p2ydAIEhlQzKABxgrQWgcGxJVQkMtqJs2BgnYoxlAy+GmQ1AlokjZcopYJlJwRwoKTQjcSaQQsK+FYaCr0Pwh/h1JJq++Ad/kI+67aGczT3Olh8iogmoFBUUAZRzzhe8+EKcZdbmo/TuzOzKnYXZ7lKhmCUlX8XXv57iD//wl8+pjS5BDzJylMEgC7xaDUC5lCk2LFARqEVgPCMRhfUKZzUEkKgQvGFVYmsUIK/eG2dIU6cdj5OIZFATQNRA2KhRw4Bl4roXqimZOnltKKEB0aZm2gtCmSwV4SXKZlbN3cV1c+/qdRo9fRinHruIidNH0D88hoM9PZjd3sTMzg6qSYocCYQZCTyUDXIqaKvD21vrWGvWMVbqwvGjo/jC5O/g3sNn8fMf/Aw79xYQkEVYzGN7awff/vYPcPb0MTzz5OOYXVnFO1N38MTFs3j4zElcu3UPxSDAQHcXNrarGBrsR5pkqHSXcG92Ds0kxcOPncf1N29gfWUDhi1CW0C6E+PqN36A3Y1NXPzUk7h46BCKpTymV1fh4gTGMEQ7ahWxpbuzsyZN4vzpg5Pm6GNnAyKTu/rnV4rtWqNQLuWtT9x8apOq5YEUpq7dQQKf5DkzbdaWpyIAb0RNFMguALOnPnsTmsxJjvrD/urW2tnjn//Ex576wjOPbWl2YMe1iuvtmvHwZLiTXMNKKIU5dIdFdAvjW3/6PezcmYWBFWQiRsk572Imig1TlpGyKEihAQKyY4cPgHMWO402vHai7fZSiWCMRd4azC8sI9upag4mtSJNgrrONyukrkgaxdzIhFTypFmmksuAlJXRBTLVX3mN5I1AH0h/c78+keh/UvLjPvaxT6D38TdDfb58Gb+U05mmhA8thvwyiS4QHpDnfOfi2nKOc/y+hA4A6jznNOJE1UiJlZpNJQpFclSD0vr63NJu0k66i1GUKwQBmpIRG0akQOpTNLIYPcMDKA31ozGzgtAa+CwDA2CQEpHPRAUE2ETYW8uN6UXzwp//gD/7D75EGYeEQFHPEljueANtZLCWtkiJ1QaWHvnM05WN5bVTMz95LS7lCo1KVmvWvnJ6Ad+YSv/aR/YrpwPcvNLz5P/2H50ePHf46TSkp+8tzZ24futurwFZYwxn7YyMYXgVcBTi6OQ4jo4MI6+Maz9+Fbd++HMgUZCGCqeqIr7U0+XOP/y426xV3avvTtFHnniYl7e3bHN9nbI04XMnjnA7jml6bgmXLpzF8uoa5uaWcezgQZSjHN69OYW5xWUQE/KVIppxA4gMjnz0MTz5mY+iONKL1UYNMwvLWGzU4b1HiRR1VawnMbqNgQJopA4BW0xWunCkrx/D5W4UlbE1vaKvvfwG7rz2DrKVDY9UUyLbBMJdbWdbTHZNBSuBwbr3WgNRSzPvOv0Mne1Dw2SNYQVA4pEZUqNh4OG9erJqASC0AHl13gEakZoHUYrEzsMYYywzGa9kDIgVxrKoIQNiEKHz5a1zEnFgCjn2RQQalyFp/dXPOuBXPjjRwX98Ofq//fP/+7G+UuETRvBZhZ5VxYBhCpkNmAmqnWa/zHvYMO//j//8/9p7/eaUVHp7lqIsnUmmvtFEZ/cOHy7i6LVtbRvvyQWO2GWZEwqsYUuk8AJSpUCUMiuk3jJMpioBhRE4zdgECqMGlGUqVkXUwBHA6sFiDABR9mKYAoaqEVInHh4EhWpn0dUQICQAPAgZOWTqtQBwRMqBLu/YpfWrtPTmFI9fPElnP3IJY6cP08OjB3G4ZwB3NtZwf3MT7dQjby0iBdrayTMPLGM7bqOaxFhrNXCybwiTj5zG+JFJvPqjl3DtyqvQRowon0OBDaam7mJ+eR1njh/Bl599Bi++ehVDI0PoK1cQBRZbO1VcPHUCr7z+FkaGBjF1fxqXzp3CnXszuD4zgwuPXsDMrfu4N3UXIhFy+QJSn+Lej19Hq97ER//ep3FyfAJhLsSdxSVkrTZCZaTeUR5WSYnmZhdNlvjo7OQBc/jSidAEQfjaN5839Z2WLwcl4cxqQO1GAJulANTGJHHEKFqQYaU01XrLKucaSmGk0ko4SrOQ+rsGdjfWzvZdOv2xz/yD33qsFtKh7axZ2InrJpWMhIFMBMYr+nMFRLAYDPK4+tzPsPj6dbUmB6nHEsFm3ksMcAvQFgycUVgYtWqQQ6GEvgNjSCFIsgRKALOBVQVxiFKUByUZduaXgDhTRyaxQo0wYBfXi5CSsCJmzSLOGTJKKcXIwFkOksSAiHDYJYQOiWZj9hcC94F9C8c+/tdDoOcm6T3rRprSe6rzHgku9vezeE/iHCMMO+S4IB3vMwAUlAJVUm/Yhp5VIgYLqw+YchYwjsiQOiNKzimyHCAxOUsBiHsbLps8dulcf663lN9MWqilCUWGYajz5StRAQPFClbvzWNnbglsQoIIDLESqYiqt6CUiNpE2hKvCQWBr66ssoaWT504Rpl4CDM1xIFJ4QFwp02PwEy5IMLxY0eCxYXl/p25ZS6USlUTYzUbOZr8B4z1P9AuCNauJ/7xl4/3nZq4TDn+zLuz0ydv3bnfY8FBAHCaddrEvHfIVUq4eOoYxnr6EKSC17/7AqZ/8pqSM2A1IDUi7dj1jAympy+eSWqtZlKLW1lXT1lbcWw2G3U7PNBjervKZnVzi+qNGI9cPEuJE4AMHZ6YoN31Lbz44mvYWF1DrlAAWUactNB9eAzP/sPfxvlnn0ScY9zbWsWt9VXM7e7AOIdMFbECJeqEDWw7B0OM4XIFF0bHcW5oFINhAdvTy/rqXzyPV/7d93X1tesi1VZK3jRJ7DYclo3HHCnPqpclVazDa5XBMXkSUSIGrCqFDAoMm8ArLHkYBliIWFRZ1TBATIDxAIkSG6ccWmI2hgIihsIEIRk2bEBsAgMmYg64M+lmYlVST8Y4EnJkOGNjHCm8gRF2qUah+uR8UX4poePSpWAg1zX41S9+4Zm+Yvm3Q6InIja9ORuYvLUaKtSSUaNARJ0DZo2l7/zwOXtnZiZfKBXXxctsWaOt9u2F7Jcj7E7ZQJKcj4IodBqkrIbYkBdBYK0aERgbduLXPCFgJgPL0NSAjfHqjTCxgAxEmIOASECinq0xpErceZpVZgL5vVQygAyglkCWWY0qzN5xBimEiHwnygGiDgqvQkJCqWhtZhH3btyltYUV5EyIgd4+mhwcwmCpDBbFbjtBljnkCRAiiAiwt7y2FsdYr9fQTGKUKgWcvnAGE0cOYntnB9W1TSTOIRcGSJoxFpZXMTo4gNHBAYgC61vbePzh81heWcO92QWMjw6DmFEpl7CwuorRwX7k8jlM3Z1BqVTAoUMHsb6+gbQVI4xyYGtRXd3A0tIKDhw9hJGRQeRyIappiiRNwAqkqSd4pUIY0fZOjWrNJpVLRds/1J8bGBvKLc+vULyz2yh0VRou8SlEVIhYje0kEAHgNBCbJ0klUI68wgtlYTHMeot9td21M+UTk0//zn/7ex9rdxcO7WpS2Ejrpu7a5Fmh6JxHxSBCxRYxWerGvdffxU+/8V01qYJj7ynVVDNtW9E6E9VUtelFO4FzoQ29ywrliZHwkc9dpnZEtLq7hbbL4BVgBcpBDsPFMsKWx1vffwHxypY3nucD799Rz9M+QIOyDJpFHFFs1VoDYg5EKWMH4gjkXMdCV0hAqVFiBlurHASKMsDNJowxWn2PyXzIwhHuZ0HvY59A7+M3l0AzLvV3mKpz9AHLxh6BLuXz9EsEOhZC0CHQBeNZRQmeGUZYHRmlgBEIQZQAS7AOPnYgySvyXiFKAliNgpLEreHDl86N5UcHKrWsjWbWftDN3ElzyBcwWO5Cc7OKham7MGCwKKCq2lmiT0S1YUCbqrrGxJtepEXW0uryStg/2GcGhwcpFk/Cig4PUHTkN0WSphAFyoUiHzt6xEzPzvdWt7ZtsViaizTdTe7OJ/9BR/TrX2e8+7PSR772+YMT5498wln/zFv3752am1/qsiCrIuQVCJjJcydS7sLxIxjv7YevtfHqn/8Eq69PgTQAqVUi9tJsZSNHJ5NTF0+33rl9u5X4JB0dGxbymd1ttOzYyKAREXNjeo57urtw7PAh2t2tY2Z+EZODg7Qyv4JXX3oNZC1KlSKaSQwXMs498wQ+8dXPoefwCJbrO7i6NI87W5uoZylyxCAiFJmQiMCrwIDQXSzh1NAIzg6NYjBfRnNhDW899zO8+Mff0Y23b4mvthMS06SUtimjFTidN2LmSGWRldaIzA4ITYbJOoESxqgiJKWQmHJMJoCItUrGEZGyAkrKzMqgThEGK5iUOhG8Bg4GmfhOdTsT2DB5IRIIAQxVp1ZVLLP30IzYZKTICJSC4Q2xCmBEYX3I1jilqBVI8nDF75Fo+vrXv85XZt7pOtg7cOLvfuGLn+vOlZ4yQFfI1holIhAxGyKALBEZtqQKssbQ957/Id2avmuDYn479W4x02wpGz0W7+VQEy5fttjqj0rMpVRcWUkL5DlnOm5RynGkRr0KUScvgkEmYIIygTyBmJWZDRGnYpghxqphqBCIiUTJK8gyQTrt9sTETASGsiGFVSJLBKtEAYlaQ2RUlKEK7XA5Dw8P5gxKGXly6tSRsqd2ovX5Vdx/9w6tLKxwZCMcHB3DeH8funM51NIMm+02ClCwKmgvDSfPjEw8Nht1rNZ2weoxNjGKU+dPg0KLleVVpI0WwjCAgeL2zTtYXFzBk488hNAYvPnODfR1d+HMyWOYXliC94LBvm40my3s7FbBRDh1/DAcFEqE8bERxHGMdpwgCiKosWht7mJhYRnD4yMYHRtBGBjUkjbajTZYABVAnSIAoVavY6fR4EIhb3r7eszgyLBZXlhtNzZ3GuV8ocVsxauqWkskomyNGut8I8uLybcF6EWWtQLTl+9K2s0TwXDP5S//0699vHBkbGLDtQrrcZV3sxY8lB5IuDkO0B8WMRDkUZ9bx3f/+38HrbWhsXjELmFBnT12RLDtobsBc0OIMiLYIGeLqbjiwYdPh+cvP04rzSqt1HeQQWChYDDy+SLGil1oL2zg7e9dUZuoYyezksk7geq8B7XUWMr5xKqxRtLMqggjsxQEjMh4zQKvlDHIZPqAQBNzJ8ZuGWBuYoHfl+T4YQL9iyzofeV6H/sEeh+/aQT6MmE0/eDiIABkGcF7GvGetFj8AIEGABSVIAkBIQIrpD7HGnrWMGKQsFoYiDBswBEz+UzJ5gDnHUi8QoRykSEObCGL477igZFDE6cmezMD3mo3yRGgzMiU0BPlUIqKKHKIm2/dgMkc4BUsChbxImgoYcWL3LJM7wZkbpM1i15cSzMXzE3Plo8cO2TzXWU4KHkVtJwDEWCIkIlHKkLGGHR1d9OhgweLd6ZuF1tbuyafz6/FY+Xtv3KpUEH4P93PffL3vzoyeHryUoPSZ965d/fC0tJqX8EYqwA5DwqIKBWHYncZDx07ioFyN5KtOl76sx/ozrvTIArVwCiUxCdJdubR80lUzsezq8uxzQXZqROH9d78vN3ZrYUnjx0K5heXbTtJzYnjh+jAxAG6PT2P8cFhBF7p1VfexMLMPErdFYghtNot9Bwew+e+9ts49fQl1OBwa3UR19ZWsNNugUVRMQbeeWQAUvEgUQS5HE4ODePM4AjGCxWkmzW8++OX8cKffFeXXrshshun5LgOR1vIaI2VV1SxwuBViG4AvEuCJhuOxZNXUoLCqiAAc+iJIhAFFjCdkskOcRNSx8Y6gnoYFkMsRiDMBGsDAauqQBidTmLDDFEiGAUBoirCxI44yEBIPKFtyLSJkRCQ5dggDIwNYPJsuRyoKbO1RYTWFoMuFB47i+6xY2aFdvO1zd2xge6eJ7/8mc8/3VssH2VBYE1ArAATwESwRHvbT9ThA8z4zvM/xL3ZacqVizWFrAQazBUK3e3BJ4Ypd+54VM6FlRxHg6w6xsaMWuUeA+QCEHciDUQyYek8OYDgXIeAdD5mNYYDEWaxxFZJFGTAnTuGCMgwiJiMEgFCXolJwYaJ4YWpk1NtQLAKslA1EDUgMJQ6lSOiAiYPMo6IMwJSFSTwmkKNYwpE2wkac8u4f+Muba9uIAxzNDk6ikOD/chbi604RpKmKDCDiDtxkh25G42ss2RYbzdRKuZx7qGzGDk4jvW1NdTWtwA2yEU5pHGCm1N3oM7j0x9/Gvfvz2JldR2D/b2o1mpoNFtI0hQPnz2F5Y0ttOMEXgU9vd1Y2tzCxfOnsbyyhnacoRDmIGyQ7tQwe3cavSNDGBoZQDGK0MxStJoNsBLgBOoVTIZazRZV4zb19XSZUrHIwwMDrrZTa9ar7UY5sKkKSWitiA/F5Nm32tabYiLqPDkfB/mhSlczTg6nOfOJL/+z33u659Sho8tpq7jtGrwZN0gAclBENkAIgy6Tw2BUQr7t8c1/8cfaWtyAEfaIszZ72giVl6G0CMUqoNtkuWmYhAzyCKgrs1w+98mn7Mixwzzf2EG1VQd3HqRAbDFUqqAnKmJzahozP3tDWTjmxN0zbN4xoBVnbALEzI4CIbahRsapM4gsIQbgjWYZg4peWcpKafoBAm1aawqgE2P36wj0fhvhPvYJ9D5+A8GdO/1kh0A717FvPCDPe+UfZdVfJtCqHQU6LAHa8WTaYC95A2TUWAPvTWCsYWOMAsYbb6AhWe/hQEAYIhMmGBM5ybrTYnD8xEOnh1zEdidtk1OPyDK8VxTDCN35AvoKJdy/eRfN9W0QCOoFKpoxaAPADSJ+VYE3M8UUq8ySl01jrc8ajeL80krh1JmToc3lKPYOxLSX9gUQAR5AIkIgYHhggEbHRwu33r4xkCVpo7dc2W6VhnaxuOh/7cPIty9ZRPnKxcuXjoZd+Y+9OTf96MLqyhgbE3gPFgEFhpD6DN19PbhwbBJD3b2or2zhZ3/6A21OrwImEkuB+NR5EGUnzp1Mw3IhXavuZMNDA350sA/vTN22k+Nj4dDwYPTuveng4IEx+/CFs3x/bomTOMOTFy5Qc7dBV154BaRAVCoicxkyC5x6+hI+87u/hfLEAJbqO7i5tozr62vI9qwZpNqpPQehnWYIbIBjg4M4NzyK8a5e2GaGey++qS/8229j7sU31W/UPDnbRqK7lGGdhZcBrEBpnUHbANeIqAVBQkSOOtZ4BmAs2DJRAEEAIosOB1UAykTOEGVsTKrGpETqAHjD5AEWEIuFioBFmcUyqbGhWCVlMsqGhcV4JWQhm1RJEyJqWcPNyIYtCNIcjJKXwKiWGTpohUahGDeCEQPt5cyXuRGXLPlyGvshJPGpgVLl6S9++tPnuorlPgsmy0zc0Z9h0FEsiRggwHkPMgbf/+H3cOfePYRhEEOwEzCtG25pHNuKSdyYOnfSEs4bxTkrOMrihy1xUQ0oU5+xDdKAjLPsVGA1gIEoKUgpYCYW4QwgtkwKgDnslDg/ICkdARakSnsfAoaJoKRQQDqqNCmZziye2DATiYDYQA0pAAGxhyKDk0yBlMnGREjUUwrvHSkLKQPNhHbuz9L9G7dR3a6iv7cXB4eHaKy3GwRgO4lRS/amHNqp1c5Tpyp8uVbDar0K5xwOTU7g1IWz8NZgeXYeWZohsiFUFFs7u1hbXcOh8TEUSkVs71Tx8PmznQSNMMDU7XsYGuiHF4dmq41mu40DY8O4eW8aj126iFarjc2NbeTDqBPmkmSYu3kHXT1dOHjoAAq5EE3n0Kw3QF7gRUmchw1DtOM2dhot6i8UaaTSg+3VrWRrZb1RyuXbVjnLVL0G6mxifbGXJUkSZLlSUOjLdzXb8ZG20ae+8N/8w0+MXDx+ak2T4lbW5Ll2nULLyCAwbGDB6ImKGAwKqHjGX/zLP9XNm/cQCHlpZdVIzYI4f0s93QbRLEFXDGjXQRNiWAm4JzHcF3QXyx//7c9YqeRppbqFetoCMyEDITAWI8UKeijE2z96Gbt35rxVrpHXWyHhXae06dllkeSMsAnV+YAsWTbWGO/Ze4BMKpHNa+atknNKSQI2Rk0UqVnrkOfFThXhf4gCvY997BPoffymLRBO0oMK2g94n/8qAl0GILbzsRWyiWHNhxw6Zxxg1FjDzlm1alSNYWHr2RuQhRVR7xzAhjmkwDMqwnL8yIVTI2FfV9j2Ce3uLbwEAJwoenIFdBdKSGoNzE/dAbMFOa+kSJlpxhBedKovBUZvJqJLvtFeExMsk2Tblq1vb231bmxtl0+fPmk4F1FGoEQdnPfwqiACXOaQqpBXxcjQkB0eG83fevN6v4vTtLenvNgaGG/9yhgygHBpNAqjcHDq2o0ztpR7amJ08HAzTSqNJDbWGkTMFItHua8HF48fwVB3r27NrtDL3/ox4vk1ZQ4lhPGSpC6IwuzCQ6ezjMSt7mz7of5erTabPLO8YkdHhqJUfLS4sRWeO3Es2K01zNLqOg8PDNKl06fw59/8Hr3zxjXkcxFsaNFO2ggGKnj2q1/Ao5/7GGrkMLW6gOury1ip1dFjAxAU8B5KAMQjE8VEdzfOj43iSP8gSmqxeu0uXvzj7+it77+EdL2qJJzCcZMS3SaHFUtmmUDrBNpRRYMUbRFNofAGrKIAwTCTGiiMYTaqMEQwzAwQqWH2xJwZcOqtaYtKbIkTBmcG7MDGkREhA1El8URiAytgFguIB8QYFYLxpOKUNTNkElHbgqCVgVssmlijXlO1oaBivI5ZpSNGcTz0dDwAjliPQ+xlwmQyQlk2Zrw/pnHyUH+x9MiXPv9bYz2VcgRRWDb0C7eTgqjzlhJViCqsMfjBj3+Iudk5lPJ5otR5ZM5J4ism84cjxSMBcDkUPBUoPUROjhmlMRFfJmbPxja9atOoxqxwXkWEWckI4JmElHnv5uBEAG9AVpUMC6BKajt+AGs6mbwmIFXAML33/RoiAohobyxAUGIiJeJO/oN6IWIPUTEgz4BjYseqGQmlADIVTUnhoarUUa2h7RRbd6Zx58ZdSpMEB8ZGMTkyjJ5cnpz3qLXbSJ2HEKGVZki9oMSMzDus7O6i1mqiu6eMk2dPoHd4EKtLy2htbMPYAJG1qG5Vsb29i4nhIfR2d+GFV69ip1rF4fExmCDA1u4uDBucOnYYC2vrKORz6OvpQq3ZwPDwEEqlIpYWV1CMchAFfJxi8e4sOAxx5OghlHIR4jRFvd6AUSAghnMeARvqjgoYKVbozSuv88y1264nV2rDo+G9b3urqbJzbCC1JIHjIDCB6XIWRxqUffSpr/32p8984tETG5pWVtM6b7YaIBISKAJiMCy6bYT+sIAhivCjb3xX5156Q41ap7HbMpneVq+vMPA6q9xUxYIC65583RryCilRLhhxcIMjp4+WHvvU07zlWrRU3UQqGUImWGNQjPIYKnTBNlK89u3n4bbraeBphTJ/nZlvKtvdABB1FIjXyLIL1VOgolZFWEwKUqNInDoRIeeUu7xwapSDQJebTVQAVP4qBXo/B3of2E/h2MffFvwlyRu/xBqZ9b1K73wnmSP2wmGYYwEZiawBsVF2RkXZEAsTkzcBQpMSWZFMyRfyUbOxuVNbuD/fPnv8QKlgQg2JiQgwRuEkQ9slaMNh/NghoFyENB3CwEJcmimwbghTIWS21Sxt4soV34mSO93Kua520vY1W7CN1Veuf/ZnpeLFp7/6hUhCS8ZEWPUCD+lspkeERtzCKogskR54+FT+43//i8d/+kd//qmGJI2uwfA71cuXF3DlygftHF/5CnetrERpyXcLdPCtH/+854x7OLpwfBzvEulKvUqZB7q7u3Dh+BEMlrqwPr2Cl/7dD9Wt7oo1ec8OzqumUSGfXbh0TupJW1a3NnHxwhl6Y+qWHR0epK6+HpOmsW2lcTDc12tbSWoUhj966RJuXJvCv/2jP6Pq9i4K5RIy75DFCUYvHMczf/ezKI8PYK66hen1Vdzd3gIRoWIMUq8dtwEI7SxDMYpwYWQEE739KFGA3dl1vPXjlzH7yjWg1gbDePIm8ZmvEdlNIt4k1k2rXHWqLQJSCPmONV07zgEQQcUIiQORsBCEGUKqVuEEgtBYJSATUOKYEoHGxJQQawJCRsoeBLFk1QFwBgiIFKpqeU+iJgIpYCGgwPoI6r2nzJAkHpIEJp8FgdDO+lbumSc/Uv7f/9f/bVdIfJgUZ6E0piolJVgidlCNRbVJbFqk3vgsrUQcDAz19ObhhJgNlIAHhtUHynPHuUEwZCAi+N/9N/8b+trXfo8o4DKAk4ZtGYQmEwWq2uXFdwNacKpWvGi+VIp/+OIL3f/8//3/Qv/I0JZJ03VV5zINUqNCIqlVCoLAgBRKWWeSpIEYynjPSaopESAZMs4TixK03XFwILRGvffq2YpRdIg2kQDeW4IARjLvHRMyVslEkUIltMQZBKGAAogar2IM2BhmbzrPDwKBiGqmTguUIYfARNnsun37j79nF969zQ9/+ikcOHcCA4ePYnpjHW8vLaPaaiIHQgqgKYIcdzKk311dwVazgdPDIzj26Gn0jw3ipW/9GDOvXIcXRlQsoNZo4ScvvIKTJ4/iS89+HPcXFnHj9j2cOXkMg33dmF5cwtzKKg6MDKBRb2Cz1sTYQD9uzE7j3NGjOJ6muHN7GvlcDpZziFsJrv3FFSDzOPHYWZw+OAkixvLcEgAlNgEO9A3qyf5BvvrCVbs2NVssRMUBOJpQ0nVh1EOYuClwYAtLTMihHOf4SDupP/3R3/u7T136zFPHFuJ617bGvNWqE7gTd2KJAY9OPF9UwKjN4cV//0Pc+9GLYDGO0mytCH4x9v5F5/RmzvBmxoghjpQ1NBpUmKDO2jFPGkB8dPLCafIho1VrI/YZAqaOUCCKog1RNAG25+eQbFXFmiCRTOYBmlcvtcgYn2ZqVTUwLJHABNaSyRxAzntjLBljNMh7pSyRJCiJTwImH6tkGY1jXBexiHEAB/co8oPfkaaEMNT9m+0+9gn0Pn6zcQXApQ/+0cEPDdXEOdIP50HXARQaABf0vVg7JoqCgDw7IwprNQhSnwRqA2tUDATqVY0nB2ikzOoy78RKFCPJaou37rdOXX5US2Ee1oQQyUBEIPWotpvoL3ajd3wII0cPYuXNW3DWKDNnUGwL6UKLfRXPvUduFd+YSpvABj77WIyaJmEpr9PPv2rzxeLpx3/rE8WEDHptDg2XIAXQcg750CD1MTYyIkvEFz71VJmZzz3/L/5trKzbIwcqfuXy5eU9kt5ZBFtfD0JjIpempTAMi5R4e+Mnr0NV9OzxcbTTFN6ynj98iEbKvZifmtFX/+yH8DtNsQizQDlpJ3G73F2JH33iYXlzaop6+7vMkcMH7Ds3b5veStlYQ2wN29mtbfPQ6eN2t9G0aep5uFKhu9dv481X3oAJLHKFPFpxC8hZPPxbn8STn/kYWuxxe30J15aXUWs10BuFiL1gN0kRGAujHi1RTPb14cTIMIZKXaBajGsvvoy3v/8z9avbILUKb1Lx0iJPu8R2I1Sz4VS2RFFz6mJW8rK33iYisMwdvwEpsdkrGWZVGBJ0NGlPDDUw6gEJiFNiSkk1scwJQWMvSAG4wMAHTPJAqgpgEQSkznv1qtjrQVfvSUMiJSJx7DNDnDpoYilKrKEs1MBEGUXFMCqcOXZytIjgRAAcBtBngMB3CCl0b4dMANkb1zADRsXhge+5k5xInThFJuie8kzEnb8XwfGJgzg+AfjOMGVAgW6gEzfMnes6d2oDoR7QACi8VblmrNeGVUw1vTcamjSIJVH15EMWn4DIKqkQw7AAgCOhEEAGAJlFAADWqxNRS4yAgAweolAQqQUJLDobBE49oJ4Vng28IWSsCD0oZZgUqjkFZcqI1EsE1RDE1qsqe1ViVlVREihUHdhm6iUlrzkKTYRYw603bgc/vDdnDj/5ED/8madx8uAI+ksVurG0hPsbGxDxHT906pFng54wwnq9jq1WC7vNFk6OjOIL/+SreOfYIbz4755Du9pEEOVgwLh18w7qjQaOHpnEoYlxXJ+6hYGhAYwND2JtfQPLjTr6e3twcmQI27t1XLxwCq+9cR2XTp5CuVLGW1evIbIWAQycB65983kk1SYuPPs4To2OgzKPpaU1HB4YwKGuXnrpBy/p7swqFzkXGCcVeAwJMGKIdoWpHXomVp+1i7YsVg+3W7uPfuz3v/r4hU995PhiFheryHiuvktsFApCxBaqjHwQYCQsYjQs4er3ruDat36kRozT2C2ol5968HNw/Falq7yxg0aKBcLARMG0240cs8aOTRcHJA6aDwb7o6Onj1MqDrtxEwqBMuC9IKAAxSBEJYjw1rt3IdWGsxTsRsA9ZcyKcD0T8QFz4NVFDMqragijNrDMHtaRsmWAMzB5yanYtnAG0S4viIHFoYyw9ovFwIPvF2iCQJGmhHxecalBeOMygCv6PhV6n1zvY9/CsY/fhAbC93mg95oHH0QOjauSqpLk8x1mUhGChER78XKIOjaOPDmjREZBhoPQxk5DBiJnODKMHAQFJsoxI3DkSckIAvJkrXAWkLNaENbxls8mDp873l/q7zWJpNRIEygULAKvQD6M0FWswLcSzN24CwtWctIkpXfE0RVfbOxiauOXLRb3ljKMHdtiSqscBbQ2PTeuQVA+evSQ8QCYQbFzsFCICJQZLZ8h8Z6iwGLy0GS+1NNbuXv9RpAmSa2nL7/dKg44HDkCPFa0PanmDGddBB4GMEGEcWLqXl1YygWFAp88cgh9Xb002juA6bdv4eq3noffaYlB4IxwO0mS6sBA3+6xE4fra7XdLF/MY3CgN7h1514weXAiGOjvsXPLq3arWrMnjkza+aUVQ0rmibNn6JWfvYY7795CUCwSW4MkbiI30otP/IMv4cLlR1HTBNeX5vHG4iKMT0FEqDm3J5YS0jRDLorwyMEDODUyiqGojPWbs/jJ//dbuP/jV1WribIaT45idthlj1UGFll5WaDrrLwDkTqDEgE8qYIJxMydZbaO+1YVEDLkmcgr1BkiT2SdknFqKAU4VUKiRIkFJYY1toZSp3BBaB2pePHkU4EYEwgBYhhqiPaKvVlt0Fk0FOPFhuxD0gxkMphcaiGZJfXlSsjVar18aHz8yKc++olLFvSQODdIqhGpdtJktGPWFu9YRQxEjKqw9x7MTNaYXxi295IluJMwvWfhADo8tRPdJqqQvfIhFbHqJTAAqwqL98i8h8syeOfIMtNr19+2P33pRR8Ui/fTTKczJ2uwGjuXSiCGtMDEYJOxI4gBlDTwoEwIICPwXsUakLKSJXTGP3spgKKwBDCTihchsFjD0hkKkKiqCEhA7AgknW4RUnAnKVpIYMl0dgdUlXjvGIhqJ6QOQiAPwEHUQ+BISQislDnamVnEvZt3SbzSxPgoDo2MUG+pgFa7jWqrjYAN4BxS51FhA6hgaXcXjXYbUT7A0VPHMHxwAivLq2hvboPYIh+E2Nrcxk6tjonBfpTLJUwvryIXhUhdhsOHDmJ6YQnFMMTKxhZUFCOD/bh+5x5GB/rRXS5heWkVxgtIARLCxvQ8WqnDkeNHEAQRBivd6DU5XP3Ja6jNraFo8moEykKeFRkBsSdKxYO8QSFhM5Sxnol9/NQjX/3C04984eOHd4wrrGdNnqtvkyFBokBAhMwL8hxgIiphNCzh3ed/jlf++DtKsTikfsl6XDHK/6bN/lXfen01/u50jKlFh8VF15qac+nIcZ9EjkJCn4TmpIubZ45/5OH+cx973GynTVqtbiKRDGIIITGiIMJwoQLdaerV712hdLPaNJ5mkGQ/M4IpY7lKLEoqkQcXDXGZCUUvWmSiAhNyYGO9OOqcOF5CwHsKBS5QJAm6w1AbzSZqALqZMQfgA1F2HYvg+2wck/Q+2Yb2SfQ+9gn0Pv4mk2f8OgL94BNrexnQKrIn7XUI9AN/NEIlSEyZtWRRMN4iIHBEJDnOhznDVFBwyRsUoSgoIwKI2JJTpYxIHcHDBCakXDSQNGoTvZPjI0NHJmzbpxR3qgnAhpF6QSHKoRTm0ZUr4Na1m/D1tgZkYvXyLqX0oquXa78ms1kxN+dltKsmoWmQUHn1/txgVCr2HDw0gUQ7MmIGgUKRMUBQpC6Fg5INQhw5ejjq6e0ZuH1tyrh6HBf7yq2APSJ0hUayovPcBUUfwIPqZJhB3eolv766aaKowIeHRujOGzfw1vdfhNTaYjR05JC4zNV6eirbj3/kkd03rl1vd/dWsF2rhc12O3fo4MFweWsz2NjescVyyZ45ftSsbWyaY4cmuWAMPfedH1O9VkdYLEJJKUtaGLp4Ap/9/b+HgWMTmN3ZxJvzM7i3sQlAYbTzMGJAEO/gwDg6OIBHJicx2dsP7LbxxvdexM//5Lto3l0Ea6CaIUMqDfVYZaVFAhYhtEZKWwpUWbUFUNLZXCNl6kRimPfOEhWAnALOMGVEJmWijIA0sDYFNGPmFOBUSBMVJDlrU6dIlDi1hjLy5MnY/x97/xUkWXZe6YJr/f8+57h7eERkRGakVpWlBQooFDRQqIIGCE0QoGp1ea3vtR6bGbszNvNM48u8zDzM0+2xVpdsimaDbJBEkwAJQaBQEAVRAiWzRGqdkRnS1Tl77/+fh+ORVQVB8Ua0xS6LiowIjwzP8OPnLF97/d/KVDWzbNYGqd3U3eBOcS8luHqCJfeyVEu1mVOT0qJnTyE1aRDUu6FfrV+/snTbkZvu/6X3fejNHdFjyNZRihCkcrqEVBEKlaJCVaWSVAqULbaC3JrEbd1nTD+HG050mzeWrf8E7d8p7eihubWxY3OaGdnu4ODx55+Rv/32I3U123/BYS94VVzqTsqavWylFsyNqypFpgUpJJBTQhmCKwAr3Jnc4QYkd4PSIEg5elUUgLvTzFzEIGJOswDNbC31VlTDjYCZi5OeQTgBE6dT6MxuNHchXdrTibecbToBoyNTJLXDh8wtR9qcVOaNIS8eP8ELZy+yPzfLQ4cOYt/iAuCOzfEIANAjsdnCelCJ4Np4hLXJCBTH7oP7cfs9d2BjOMTKuYswCuY6XUyGY5x84WUs7dmDe+64BSsbmwgiWF/fwP7du3B5eQX7d+3ExSvXsGO2jx39Hk6dPYtOCDi4by/WVteR6gSFwA1YPXMeg0mNO47dhG7j+P7Xv4vNc8vohxmENlTkpGQHkoERFDL4bNJwMFW4t/HJW971zz/9+gc/88E9l9Kwe60ZyMXJOpSZoGHrhVjBAoe6czhQzeL0Y8/g4d//AnSSk0RbY2NfEvM/rEPnSfQOr+NLz+WfOre95YzPNzeFpsTBJH4/Zrp3vPOj75vfcXgfr47XuTxch9GhqvDsmC+7ONjfgeXnT+GZr3+XZZbrobYnSsejJTpnkL0xFgFEP6jsAH0RkAUzLEBlhwT2I7wys1Ba9iCFxRRzZswssskom6j6wnjscwBE5IZ4PgK8UumdM+EO3DXjOIqfpHFsC+jttS2gt9c/ZfcZ+KkhQjNOT2wEgH63yxyjeM7i1fyWi9Z+b9kmXLsyK2YWrNCSwbsSym5279fEPAsuwLmDwlkFK4eDzqhADZYNC2YxDylwPud8oKn04F1vvKeSKshK01bPttvljhKC2aqDXbNzWLmyzKtnznsJyZ7SC275O3ltsolLl35+6cmZ5QaHD48gMqGnfRdePHWgtzhfHj64jzXAhDZlQGkrv51AnRK0Bf3K0aNHenPz8/MvPn98hziqDqXAOJbu2icxR5UFt7xEYrc6F9zRY8zhyoWrvHLmEk49/hxkkr2wMjMhpfFktH//nrU777l99btPPLl59NghW9nYrHYu7ujvWtrZO37yVHX4wN5iYzQKB3bv1PGk1rIopXLwB997nLFJKDsdJovM1uCuD70L7/uNTwDzXbx05RJ+fPECLq+vo6SgtNbwAVvyQdaANx46iHsPH8EsA8499RK+/V+/hNPf+AF8EJ1WGCZpwuyrQr0YgHPuuKCQa6CuARwKMQbZUCRTac7WjRTSnTACmZTowoaqjYC10WshJxRp3NmYoIEhBrIhWYuzKQUNhdFzEak5CSSTNAKuIm6AaXBPgCsKpxPm7hbEy0AgixthopKjIAlD1m6y2AD9sjMzXF85dNvRm9/2kfe8/95SZBHm2vrHNzgVcG+314E2V80pJkRuPHE4hajzxpX+xs4MAHrrZqpMJbbwhmttZm1o2AxmhmwZ2QwUQRkK/Oj5Z+Sb3/nWuJzrP+Nuzwrqi8v95Wa8MuuFF1TJGsVVs4kAVDMEEsgGBIMltkANoZckJLR57MrhcDokeIZZoWLinpWSAc9ZJDtoApibm4uYCc3NTQBvfxNwcZi0j4dlMBOwdvDQnYQb4YF0iLabD+7urQvd4m4MZHYOL13lieMnWKfEA/v34qYD+9DrVFibjLEynqCniol5y9gjcH00wkY9QSFA1e/idfffC1QFLpw4hRQzemUJ0QLnz19AXSfs270L3arEpK6hqhiOJojZsHNuFifPnAPNcMvRw1hZ34CL4JYjh3Hm5VNoR/kEgGDt/GUMVjZw8tkTWDtzBd3QQ5kF2qLIzQETwhgE2fOMVWF3XeBYk5tbH/jnnzr6zk9/cNelPCyHmPD0cJ1ji9S2oQaEYC5U2FfNYF85g+vPn8JX/v0fOwcNpPE1ifbVmRC+MEz2KP7m++t47rmffW77LNi5eLhjM3p7k9MDizcfuuk9n/jgzKQEzqwtcxBrmBIKoNQCO2fm0WeJp7/5fVw/foqS5JIYvhdMnvLKriGCSX2mZNglwJ7afE8GdhdlsbuB7dxsmnmldgvVMB0/TZ5zUrOUY5FZVYa6hiwuugyHEBHsmDrQszlzQ6QdVN8aKGyh7sCZ17jQ2wJ6e20L6O31T1xAn/kZDvRUPG8xoHPTCNzpVXXj6z7TimjPXQmkWr8ogqHDIL2GaXZmaX6hs2N+1+Zgc09VFktK7nB6d8oqaCzIGLQJg6YcSJh3vQp7B8PR4Vted/vMzK4dOskNmlQjo83uNTGiW3XRKyssdPt45vFnINGY63SqdPwgsreKM2f+bl7zwZvjTIprVnHWc1469/Lpxd0H95eHDh9EY5lCIuYESCuWVASjpmk1UFAePXZ0fn5hfvfxx55cNJEZVc4g+YxQ5rL5DiV2SfY9AVz0bD0FgiZwtLLO0gUaaaWLTSaTuLi0MDp80+GN50+dGhw7eiBeuHSlWNqza3ZUT2aXV9d7d912U3XxynK4/w336Msnz+rC3Jz4aMLvf/9xWsrodEtO4gTeCXjg1z+GN3743dhkwguXzuPJc2cxnEwwqwViNjQ5o3TDICbsXlzE247dhFv37gPWRvjBX34T3//8lzE6fcWZ1SUiMfowIFxz8/MKnqHwIjOuGzgw+JiijSqjm2cA2dxM2NrB1GAGydZGJGsFmkJ0AuEku09IrVW1piNqkOiijQNNAW2UjBHSgGyElqgh0y0ngQXCWJamQiezqQdHsLZgBAoYodZyCQPcXSQbPUuCCUsrVFkJ5gZrG8duPnToLR9+7wdvK0S7ZllkSxZPychEK3jpaLm2r3KdDe3g5ZZevrHf3OYZXhHY5A0R3rKtW/0jZDti6dPI0FaeWoiqKPHEC8/x69/+1rA7N/tYY/L0QuxdXLnvewmnj/p8uC4qlZq6plwwQ2ja8sw5DVMrAGXleVono0GRW+IG4Oa07KKF0ZnpMNBzNrEAacsMYcYiWDY3ejZVNxVpy759GtMgWrdaaeYwJ4yOKTq6NfHd0UKo29cabNMuBGz6+4XSByNeffk0Ll5axq6lXThy8AD3zs8hpoTL65soANAMTTaUFGyOaywPNlCVBUIVcOyOW7Br/x6cfvk0xpsDFGWJkoL1tXVYSmhiRBMT1tbWcezQQVy6soycEo4c2I/VtQ2sra5h785FnL9wAXBg18ICrp65gBACSlFAAlYvXcdkMEG/6qI0dWaA7R6cwc1EiJpeoNS5sdruKHn/A//807ve8tGHZi7bOGz6mKfXrjN6BOmYpAx3oGLAUtHDgd48xqcv4y//3R95Wt5A6bKGxp/QhD/slfzO8K9/eP3vPKc99NvUC2fnOaNviBbf99aPvnfvwXtuK5bHm7wyXEPy1B6f2VFIgQOz8yiGEd/94teQVofG6GcLw3fE8glJOsiSq4LcKYIDmXqYxAEpdN/I057uwvyuQwcPzF1budYrNAS4m7k3QquThqaCplzWN1xoHY/dp1HAuel15QaVY0tAF0U7WHjpNUi7bQG9vbYF9Pb6Jy6g8fMF9Ow+Z24q8Zxp/b54jPJq9xmYBczYdKFiXoKpq2UxO4j1wsG77lh627veuv/pF48fRJC9cF9UYR90EWGTkg+85EhDqGHiiSxCVSzF0fBwsXNu4aZ7bi8nFn2zrhlTnCZ2CYOg3+lhsT+Pi6fP+erZi6pBr1oTj/dnhhfrF65M8Hchkc6csfiBvY1dsYGoApYPnD1xqr9r7+6wb+8eJjdmOII7gBt5UWw2NRzGqip55Mihzszi4s4Xn31+TzZbUA09uM3QfV7IJQX3AL4IYMacoYRIJSVSdFenNylapyrj0WOHJxdWrk927JitozvHMXWrKsx1ut3ZxcWFztlLV4q52b5eXV6RowcP0Mc1f/i9x1iUJbQqMGnGLHfvwPv/1Wdw+7vux/JoHT84+TKOX7gABzFDQZNaskGTM6IZXn/0CN5+yy1Y6s7i/LMn8Le//2d+9pHHgbG55GCobSIm6zRepPOMmZ0BeUkgKwSGgDZ0b+slTJzCTHETp9FgIUh2Z3ZBKoJGkI3DJyIyIdHmm1Vrg0cXiUqJrpIobLzNLCdRxpRScpUUhDkVIVciHlPykJM3Ih5s6vJK0XavaCui2wLzaagiSS7EzFxy+3GWIoTZjfW1m24+cPgNH3n/B48UEoq2faV1kKdUtxuOMqed1mjVINpmkenk343oRiuyt1QVpvnnVxxpv/GEM1j7zQAs27Tmr30vquiEAo89/wy/9sgjm9352e/Unp+6OIzL+L0zhjNnfHjbfdQqi46zOijtjwptv3kgGneqqsMTWyFNIGVmU6glMARnFqfTqDAAlhy5UM10ywywQsQMMHG3QmnudKE7ATOIS8vqzgBN6dbuw7MNRIMkIeKiNAvCtoSDlpXO9iWWCN0AzwZYq7RH56/w5eMvMZvz2NHDOHxgHwoRXN3YRBMjOjKNcYmiSQmX1tdR5wbdqsCBo4dx5JabcPniFWwuX0cIJWCO9bUNFCJ48333ookZ65sDHNq9C2uDIS5eXcaehXk0TYN60qDf78Oyg9kw25/F5vomhIIgAVXVQSkBdKJlPdJDoFMEWYgkEASWjaKfgs++6zc+2X3XL38gLHsta3nIi4NVRCT4NIZeiqCLgIO9eRzozWN0dhl/9e//C8aXr3vwssYkPSkZn2dK31yfu+kynnvu79UH1U4/MErNO4qlHe/+wK98dC7PdeTi5gpWxgO4bu1+EDtn5rBvZh7nnnoJL37zh14laTTxBFN+1DxcArNRynl3P+QqN2f4TaY86N1i72Q8WHr7h96zY9+h/bMvPPNcp6y6imyJycYGG5lxLAzRckjS7RqbxrljBBm+grF7DRf61QIa+MlSlW0Bvb22BfT2+qcsoB8k7h+8tsb71QK6v49bBA4vy9d8rRXQDWCBrh7EvEQlPRbV/Jh558yB3fs+9rmPHzp77cr+qxcv7hbRHSlbn0AwMlaFbhRebBpsLEXMjkJMfGe2eHCQ4t5bX3d7p5ybwShHptS0TGgVjGJCt6iwc3YeIRpe/vGzQvOohvVUh+fziQtrfy9T9LFLjkO3DbWYDMAQ83C0cPb8hfmbbj5a7ti5A+6YVokbkjuiJQiJcV3D3ChFIcduOlJ1Z2dmTjx3fB7u84EyS/N5B3Zms90OmQfZEXoAKDk7wrTAwMx8ac+SjXPM3W6Vy06FUxculvfcfVt/0sTZDOuOUy4Xd+wIuxcXdKbq8OKZ83zqmePsdDtISsZYs394Lz78W5/DkdffjpeuXML3X34Jy2vrqKTNOmZzFGjpIvMzM3jrzbfgnoOHUdSOp7/+XXzzD/4Co5OXwKzGxIYJ6yrFZYt+lpDTJM+a+2UAq3CMMjwSboWocSvrCsuAZFXJIpJU2LKc6TG5N+JeM+gEohOn1HBrkrCpVGMI2tRuyXOOQRAFGtmK6VQoc/AiR/XcCjd3qnhQ8eDuJAzeEiCgChhQmsHg3sY5gtEla/BsDFl1bBhGdGb7vc2VtQNHDx6656Pv/9DBSrWwbCTaKnCIgFOsH6QVwZxSNrYocSTbr7u3w4JTt9qn7jNly3lutfe0rwc39Nd0WJXY4r853ByUlsTw+PFn8bVvf2t1Zm7H305ifnrytW+u3RAUBw5wbgKZVJBCdPp8rBECUZuiKsRjA2i4oeYRCZSwNtIRFMaWpU3CKMyBNJoZgxkAUwRvspkGmkNcQctmDhEnLZOS2ca8TYUtfAQyNZ9dxF0IF28Pv0Ag0BmckJbKwiluDwanIbf8aNsY4tILJ3nl2hp279vLY0cPY3Gmi+XhCBvjCbpBUWeDusHgWB+NsDYaoVME7D2wFzfdcUs7THjhEjQEdIoSGxubuHzlGhbnZjE7M4PHnz2Oo/v2oNKAjcEA3arCcDhGJYpAAc3RCyWGwxEIgqLgNEYCB0QDhAIjPJOexcmKmkqWjaTy3b/xyfCuT39AztcbXMsjnt9cwSTHdmfDDQGCgIA9vXnsKWeAawN88d/9EYanLkI8NDKOTxfgfy/gXxrF6xfwpe/Gv/eMfhRlZ9fSG+rR5kN3PviWe+95x5uqdZvw0mAdo1wDBEpVFFJg78w8Fljhe//9b33thTMeXNfV8II4nwjGjVRIhy77CbvViduMOIxKd0+YF7sHd8997l/86syZS5c6J587XogqGK0Wx6YA6wIOoVZ3G0tbbGhyDpibgwyHAICNrfmZ9u21w4Tf+9721Xl7bQvo7fULNkD46hrvqUjelzOt03kl/1wUbYwjZ0HfSRGH9wkzdgLUCpTQ0EMlO+rU7Jo/vG/v6x5406Glw3v2PH38+EIcjvuU0LOci0LFILJpxHoRfGD07A71nBelVx0cr68dXDi0b2bPrUc4tsxBM0G2jNTuQCOooiwqLO3YhZMvncTo0nIQ0kviyWZ276W/Mwf9ihMd54/sH4zNVjv9PprBYOb06bPzt952czG/Y57ZyeiOOicU3EKVCVbGQ2QHizLwpmNHitkd890Xn3qmb4a+qs6nlBcBLLhyRgUlQSUphnaATCkoOpVvjEftnrYIVjY2wt133FKtbm52r29u9m49drQzGo0LJXRtZU1Wrlzj2XOXWIYAFsrYjLHrzmP4+L/+dSwe2o0nz57BoydOYDAYoj8Vz3G6196kiP07F/G2W27BwcXdSCsDfPvzf+U//rOvAWM3WpgwYiO4XvGE83ScU8gZBy+J+3Wlbip84mRkWzHuquLZadnb+EYRJAOeFJYJSQ0QzSXC0ah4TWWdzWqo1G5sqGhKIooy0iWpIwo1UXMSQxJhJsocLRtZGDw6CSNKDyagJ2cIoKq3+l0cZghFcCPBoEb3rIbUULNWZRrXOXfqievsTLmxsr5429Gbbvul93/4QOmsckrtYB+ljWZsPVGmyrfNILQxDNxwqduv+xRbB7bphPY2Apu60CLTjHQbon7FVnNHSgkOb6kdZiCJTlniyReP29e+9fByd+eOrwzq8fPNy2dHrzpufXTnnZxJwiKNxFUJFsh1RtWWPCIIW9kKEO7UqS3MNjpiDGpiahTLMcJC0dJRYnY3iGVJuSAcLCx49oZbw4MwoHWnaW0G2ogsoubWOuv0NgrtgFIYSAnapl/UDQJzQXvcu7SDhhkZBqPR6TTnxunzOHnqLDu9Lo4cOYh9iwscpoRrG+soiXZHBUBPFavDEZYHmyiFmN8xh1vvuR11jLhy8gwoilILjIdjrK8PsG9pJ5YWF3Hh8lXMz81iUjcQEXSLEusr62hGY+SYcebMeXTKCiICQ/tiSEXRGv7tecAUnpVAN0itWWPh+t5/+Sty/4cfkItpxLU84pmVq+1g8rR5XZ0IUOzszmJPNYvuKOHP/t1/8Y2XzpFejDmOJ0vjFwviy5tYexFfP1X/veex34bMjd46O4rD93i/fPA9v/xLB2cOLIULg1VcGqzCBShFkLJjZ3cW++YWsHLiAn70378BH0XzzKtV9uNKvpgpyS3vkmzHMnm7FnokKfdExUJSn3nocx/v3vWm11fPP3tczzz/IgM0FoZNul0T54qKbWT3ySR6FHeTlFyLwqkK72/QN9pirsGWAy3yWhf60qVtCsf22hbQ2+sXxH0GcCO+AQCTiSBnImcOAPSqSnyK9PKtBkIA7GxtcUd4VgkBalKVgZxJivmGedfMob17b33L6/dXO+d2SlHMnXnxZFdUSiULdcLAMQTrRmwaJLuzdGKBhexPdX1kJJi97XV3iJUFNyYjDJoITF3oFDOqUGK2P0fUCeeeeq4Sh+aMF6qiuJBOnhv8Q34Zk39+KeLCwc3UNFdDWVmztr7z1InT88duOVbOL+5gygbAmc2msASHClE3NSKcZVXiyJHDurhvT3n86ed6sYmzoSpng6MLsuJWHJUCtFVvULKFHajChFzZ3NBD+/cUw3pSetDq8KF95drGZkFnuP3IEX3ppVO8cOEyO1UBFspJPcSBN9+DX/qXv4Kwo4/HTp3A46fPwqcZ0ZQN06QBkhtuO7gf9998M5b6C7j24hl85f/4U7/46FMurlmSjGySrxUSziHhlILnQF4y4LqbbQoxIRhBtVYYOrT1Xs1gJoKsKknMkpGJyuyQmJ0pSEvXYGBDhFpFGiWaINoER4zmkYYkRKJIFmEm1cRDFvUcPWUGGJO7dINRxTvq3iT3UHRaOWIECnHkBLp7boMDmSlmLTQ1hhTKEOt6nLTSmJqOzS7McfXaSufmg4cOf/i979vfLau+EKoaWmd0KnzBtt3PpkN/OUek3GZXG8vI5og5wdyQzdBYQsrTNzfYtOGyyRHZDNltevtp7hneBoo5LWERAkIXVTz2/NPN17/9rfPV/OxXLVYvj19+uXnNgfubL/uuwW6OQgdVrICOOLfC6KgRTB3Qlsd2I6hNIBJtSjw5jSZNtkxaacw0mCU3InnJjrU4OjfPms3MVILBzeDMImrqlqnMhGbz7BRtpyZBVwoUpLkr0WKzzV2nyOzW6SfN3TOzJwIR5gki2WN7konXV3n6+Zc4ycajx27CoT27KAJcXV9HMkcnKIYpo6uKmBLOra/CkTE328ct99wBlCXOv3QSdKJbVIh1wskTp3HT4YPoVBUuX7mKvTsXMR6MUEjAzpk+lq+uYHNlHaWWNxScikxfBHGajyeSEB4EqJRNyJI6ou/955/m/R96F6+jxpV6gEury4A6BEAgp28Bu7tzONBfRDWs8ef/6U985flTXjJkGeezRfa/ZrQvDHXXU/jrH8R/kIhcvquYOzS3dzBa/6UDb7j77W/+yHtmr/tErgzWMEw1CgGSOwIL7O7PY3c1i8e/+m1cevw5FCxyiHZeKC+Y+SVz74joQQpu84LHErkX3TBfS5458o43VG/9pfcVtVDPnjjFc8++mEvqUBtbhvvFHNNVp66TnHRLjzkiS87WCugruNEdAOBnCuiUiMOHgUuXfDvCsb2wXaSyvfCL1KLSNK+JPewDkAD8VIHK9ERIEcfc9L24AzXGqFCpAhCa5BCDl+tpUt77wJvLM6fPhjPf+pEXRcmUmyWhHBGRy+62npQFNKg4yphyYtWdXD15Pi2fPF/svudmrHRmsD4eQ+CI2TBINYrBBmbLHm6//x489fD3ZPPFMztKDe/Q0l8AcPEf9M//HRg++4Ph4uZbTq6M41dCR9Po7KXir//zn93xoX/xy719h3aJNsCaG2rLiADqaVva5dEmkjljbx53vP0Nharql3/3v1mzPjbpFvBJbFlodBiM6m2dct5CPbhrTpmVBLl6dSVIN9iRY4cxGjdh764lvXT+Er/6jUewuTHiTH8GjWfEeoRbH3wL3vfZj2Aojh8efw7HL13GrAZoOyMEVcEkZ0CJt958M27ZdxBVAl781o/w3c//lcer6y4oo43jQIArBfUCsl02x4pQBu6YuOUo7tlICi20XGC6vjIoZyrMcEmEJ2qZ1S2be84Gq0pmQ0hwy/SQyNzQNdE9sZBEMFVumaQ3iQ6KVwFApFPgtZkzq5FqnVIcaQKgg8n0TNjkxE4HmEyACk5nZWANWEJD8a5WuYmWq1LjZCKx6lgs8zjr7sK73jCP6yuU4sWi07u1W5RLUpSF/IwSB3vNJ4obNwiv3cZ5zTfaz3nVOn3PV39sP/G9CS1avTc/P4k5XS9ENldmV+PPOG79/INVPLi7xnBYeBp67knS5MzmGqSyYAAQlc40NV9KlGWDmNFGdjQbUZgENWkahzu7XXCSOjnlJIVI9piTlQhlI9kFyQ3J6YV4jiosk6NMsJLCCCCJizvM2XK/EaBi07jFlEBiThROCuHtJKXc8PwVCZGO5Mm6LOC4Piyf+8LXw/qla3zzL70bb7rpViz0ZvD9EycwbhqoKsbu6JFQED8+fwGjpsHte/fjjR95B2bmuvj257+CvDlCFUp0igrf/tb3sbR7EUdvOoT1jSF6ZRdpVOP4mbOQZOgUFSwZbBrLUW3d2za/7tOdBocFMpdkrAIe+rWP4k0fehcuNiNcG6/j8uY6Eg3F9EW3TH8bu3qzWOrMotwY489/90+x/PSLKFg4RpMrZeZ3MvD5cb96Hl/86/offAq/e6lc3Vjdj6o69IZ3vnmR/Ypra2tYnQwBGgwChWCm7GCh7GFweRkvPvY0yOCIltR9JEAy9x2BrJQ4Eskj2W2PBd+R3XrFwaXyoU9/ODSzpQjpEUYQMEdMxEgNQ1EZM1l2U0PZkvbcjJYSpXitGN6XM1XVz29dW7ZbCbfXtoDeXr9w68EHgcHPNmttaYlI6edWeFPVHZlQ9bGYh+heFNK6VHQzd3clIxk2CH3wYx8If3r6PCaXrqPTKWa9yXsbs8OBYZ1gqZ4tw3sFggcN9Xizjj/+9mOdj95+Exa6fV4bbGIQxzAahMTKZITrzQj9+Tne9+Db8a2Xz/VM9E2TWH8fDz74A3zz4fpVhLGfv/4EeQU/2MQn3vFy2SSRmWpm4+T5+Fe/9yf3fPK3Ptffd2AXCHC1HsIsQUEkAp1CcH20gWRG75vf+vbXS9Xtyl/8uz/y4bUNLwuBxAzCoGzLNaZ76tAQGLN7QTK6czyayNL8TvNkmJnpsRlO5MTLpwlzLsz1McqRMde44wPvwIc+91FcG2/gkWeO4+zKGuZDiWiOZIZ+obgWG5Rlgbfcdgtu2b0bGEV8/0vfwrN/+Q3HOBtNao9xLVCu0PyC5XQ5QFcFPqZ4dHdDS08Igdpaz8rcYoMlk8iAurYI4mzmKcNzCJrUU0ZQIyXDkQoWKRORYCIRRSRGz4kWMgtkRrq00QYXGOv2l+RdKbwO9G6RrG7EgYDujPkMAIzb5EkzBqQDxAkASU4pHFp76UUeWMxiKZMS5+YtncdGxtUlQ3e3a3HVe/3q+vWN1ef+9nuPHGKT9llOhz17L7txuuMCswyz7CDMctumSKKlWrf5Dbi39mrrJRsAOKeoOm5x7gi2vAne2P53b5m8hEM03Ph8zoay2/Gnnn92DRrOpHG9hksx/Uyu+cMP5/Of/axj4dm8b3ws1GkzJJPQqXpFEbOlbEUOxopKB6SxhhBxuDi9duapeHbLjWUHgA4rihgdwhyyGFQdKRVgMiJ4RnKEwpGDu0eKxqCIbpacnnMyC8JMp2WYuzvALSweMolIonJAc/s0JqltFDq7eDuTZ0BwT9kIOC3hwjd/GNaXr+Odv/Jh3nrHUfSqCt996UWsbQ4QigIJQOmOGRGcuHIV4xxx796DuPOB+1AUJb75B3+JyTCiEwrMSw+bawO8+PxJ3H/fvbhyZRlXL16D2qtiuSRUBOaOZI48fXyoRI0MdkqOvQHLDj7+v/4mb37LPTgzXMPV8SauD9aAQlC1T4426O2Cfd0Z7K166Iwa/Nn/8ae48tSLKLU0DJp1Tf4Ig/55L9qzky9+d/MfsZvovR76o/XhHbvf8IZ9R+6+pVqdDHyjGSF6hkgr4AsGzHdnsKPq4ns//A4mV1a8VDVxHxukDkApKnvguiMjH3ZgvwXZgZkwkxGrt37gAdW9C3p9Msahua7HNuZnCq8JbAhlI3sce1nGItU2GosrDFhon68WlyjLy685F+fcXju2L8Lba1tAb69f3DUe8yfd5xsi+me4zxS5cdLjUB3lJnrjGTSleLLaAjoJIim3ZiRSUG7UEzlyaB/f/+uf4hf/w38pmuGkq5YXgusBUDYl5VKCjGnowyExpToExjM/fs7PHT/BnXffhLmywnAyRBZHEEG0hMujTSyWPdx8313+1G03FevPnTxWVOVdVa4P1v/r/WeAx+I/8Lfg+OJ3h9Vn3//yaHP9S6Hf5ejcZfz5f/zjOz7xW5+b239oj7o5cx4iu8GFGFtGEYhhPcTJHBnNsO/eW/Br/7ffwn/7t3/I4dnL0F7Xi0kEna1IcDjdma3N1SYzugEznYory6uye+eSXz1/mSdePs1ut2QoS4xjg4nXuOfDD+B9n3wfzm9cx7deeAGrmwPsCAHiLRdhaI5rdY352Vm8/c7bsLs/h8HF6/6d//pXuPTDZ50R2U3HNK4i+UUozhO8CsNGptUGMckuJAO3pKK7G5nNLIPM5u7qzKQZBNmyZ1XNwSU1jkSXTLoRSAU1ESmRiISmShgzEYVVIiyzdmMQQxfA2CF0dkvnBAVqaZwqLilYL4iPtfZJmvZHFD0QIyBXbC1bdUnRNJd51Ak5r6ZcRctdQzp/vU742Mcyfud3fMtIPvPb8KXRg4MXX3jxzL/53/63p5V+yNyDmO9y92DtDOIEZqP2nnkCwOxWkixhVoioOOBuyIBHB5PCs5NGUtwtCFBmeqWUkmAgEVrdLAqDGEGnCyk38tUEzYAaQS93+zMvjYeTdXzssYzHfs4x+yd/kgHYpc/enbG5mJfqsdVF4y7KlExCDsoS4hkoUaJBggidUGtEjSmZWDYUwQGggbtMURM+cUGYGHKRtUhZoMnKkCzGGEJRWEwpS44iGh1MqX2qZ2ZkF2Q6M2AZLpFkY55rwHsGdACUKgxwKgEmg0zrTc0gU9CdGSLcs4EFMHjmVPja2p/wjR9/D+56x3148M678dipkzh//TrKELCWMoIZ5oqAC8srmIwmeMuxm3Hr21+HstfFV/7Df8N4mKAi6HiBNMl47NEnAXfEmFFpALTlZd/YdVBph0idcGmr0HMpjJNNdA7txqf+T/8Me+69FctphKuTDVzcWEVVahv9cUdQgVOxo+ph3+wCwsYEf/Lv/wuuv3AGJdVtUA9Cxo/p+LLU9sjK/JEh8IN/zNmbsU47MdN9wzs+9MBezndxbfM6Lg43oTRMSzUxWxaYK7sYLq/i+UefhGRHrnMqXEaFqsNsntQZgjuNsj+rLKLDfuN1dccHHyjuffAtcrEeiokiWjbLSUBaNq+D+0YSDtRlYrUnZjUIHWY/bchM10+KaTQNf8KF3hbW2wvbGejthX/SFd5HAYxGLX0DwA3KRs7SYp3aQhWSuMGAfkVITwWNs0GlqigMrLyj3Yg021nauXjH2+/fu6m+Y9OaTso5HDm4X9yc5146AVLh7hnmLq1LV0DYM8c8gV0m2JHrupsKkVvuuo1ZidV6hJgzGmu3VEcxY7aosGt+B4KTp585HgSy6eJX7Go+g5OX6r+XyPGqk/bk7vsTrBlajitlp5rUaxsLp86cndu9tKs6uG8Pazgn09KLJidka4Gww5iw3tQQAjt378Ltd92OS8vXsHb1GqUITCkTPkWKkWDbLbHlSNPN6Q65fGmZq9dWOd/tSRCVsWWpEXHfRx/kez/1PpxcuYqvPHccg8kE/elg0Dg7CjhGMWJhfh4P3HUH9s0v4OrzJ/G1//B5rPz4RRcLjTcYMOMqDGcdetYdlyylVZATR7BAqACFkwUBJURVpwBkEbJtnMskUxFCVKBpMXShaeCJ4gkaEoEEl+hu0SUkyRalCBFEEnoqTHIFT2ZlFkRjbCGxWc2zl46cwZJgCpaLaDm6q5YmCC4IjqYhgtOzCNzZA5ByAm3iqZlYqFKuZmK+uG4JH3ss43ce3hLPnKaWOLp7n3QnDCik46oVhKUHyVboBoJeoMizKPR7KPRbLMpHWRRPueqLHvQ0QjhjIichfAFF8WMU4XFW4Ucewo+0DE+kQp+F6kuu4SyCXjHRNVNumoYRijCBMCahWaFt44wKLCgy4KbSoAhrDPqcmT9a53Qi3Xx5gIf/HkHx3HPEe+c5uznUpJUqJARIERgLMw8uKhAwuHsrUIMVQvPQZLi4FIVJjCaECdDa8HBjqJxmbsHNknimWhBzB81UrYi0RJgSrXdrcCEdcFOG7JjGssEkgkRtdyZcmEgxupvDTNmGHNzb2hq35ATb+b32/0pQbHOoF8+cRQ3g2LGj2L97J2JOuLqxDpWWoFE37dDvZl3jysYGqk6BI8eOYPeBfTj5zAuI4waVFAhOYHoPCw1IKd9geL+CL+SUnuJIAqQSiHmCHXccwcf/zW9g6a5juNwMcHb1Kq4ON6GBmOSMKcwP5ordM7M4NLsArAzw5//xv2Ll+CmUCG6jVIvJqdL4x2L5G5tv+8hF/O//u/1jzuW3/9Yn+lfPnLn3pve/7XNv+8hDx1a8Cec2rmEjTSjTIVcRxZ7eLA7N7sCPH/kRTj7yI5RZXJrcKLhO8zHJAPgiaHsawa7UDbNRrLvrrpvL9/zqx8J6AV3JkUELzmqBM08+b8vPnxhVXlyWZC+J84KarSF4XSMkITNzdilmXVLyG9eKrTs+GuHSVgb6pwcJtzPQ22tbQG+vf+IC+sGjraB4tYCOUbZaCPv9/qukpdPLsjUmRfDqE6IHo3tUKbzwgJLKTqT3ZbG/8+533Lc3dmVhsxl3Taigyp23HOP5C5e5dmWZGgqxnFTIQMtlEYpeyj4Hz4tBOO+i3ZXr12XvsUNc2r8HGzFidTLGJLfkAyHQDQFV2eHB3Xtx5tRZDC5f7YayiIH2WH7xwvo/6rfz3HOOe98S5yfDYcM8RChjs7Y+f/LUmflde5aqfXt200U5TnGKtWoxZk5gbTLBqJ6AQi7sXuKd99zB62vrXD5/EVoElBQmM1Qi9HZrl0G2Wu5IBViIoluUkszZpEwryLd/7L18x0cfwrPLl/H1l16E5YyOKgYxowDhJIZNg317duNdd96OndUMjn/3cXz7D/7Cx6evGFHUkrAqWS7D9RzMLxJYBrCpjoYicLdAsnB4gbawTIStaIa7k7RCJSsRNbChI5pINHhjlKYAkgtidiZXJKVEIaK4JaJIkj1J8EQrcoQns5wl0VRzFsBQFEAmoIFdAqWrZxFndJeyMImN0bIjlnAm8Syhr0WZEKvkuYKwFA860+lRVFGn7Ltlxtef2QX8L5ccD+MGsQCD+3XnqCiHcdzPgh055QWAvWiWktmy5fySwX+c3Z4y8rjTz+bGrhjTsoPXDLzijgsOP5M9n6TjZAJO5WhnAbvo2a4k8+vZbdWdG+a2aTkPzTHKOdfmVme3xtoWOyQ3z23vdzb42Nyvw/xlKp8DeSHVDwzx3HP+0/z2Vz2nH3xQD170opjtVrm2LkudQeMzJLoQLUVVFICruBmMIlmUlj26SGkSG5NCXerQFul4cHbFpa38dtSlU1uMnam7RXpAMhMYATdzF6oT2d3FpB06NTqzu2eKJ3cmM09ORJpnEplwYwuLaenZJJETCGSKtjYuQIEIKYrsZB157ex5jpoGB44cxO5dixABrm1swnKGqCDGCHVgUk+wkhrMdbs4dGAfDiztwdnjJxHrBMkAqW28ytrBW1VFMT235engJVWRlLCOoolj7L//Lnzq//Iv0Tu8B2cGqzh9/Qouj9oYXOOGQqa17VTsnZnDge48dGUTf/EfP4/VF89AvXCOsjHhfMf5bQe/NBhUL+P3fq/+R53HP/tZ2RhcucMXuh98/29+6qGwf9fCxfEaL26u3cCPG4h+UeHIjt3A2ggPf+Fv0FzfhNRmRWZj2UfTQck+NCw0wgXplv0U2MPOfvmp/+mzIexZ0Ev1gCM39qqKMww8/r0nff3E+XGX4SqSv2QxXbRQbGjDaDLO9GCtgC4cdQ0JwX9SQM9iOky4LaC313aEY3v9j7/WAMxtTU/7lmPtZnSbYY0GqmIAEtwa5jzJlpOg8GyZG/WQHQmc6c7xA7/yUfzJ6lo1PL+8QyyoJe+a+apampQqZXbtxphFO8HTxgg//u7jeM9NB7BYdXEhlEhNgy4cFR0XBhvolD0szC/xzR98CF8+eW6vR78P2rkPD96/iYcfu/aP+mf+yZ/k9Qcf3Oz38onJqC68W86nq+vdL//ef7vz/b/2sd6he28HO31enQyRcgJIDHNGKcDEIp67ehGjnHHbjiV8+F99Bo/uXOATX/4WCorTlXVMLVPY4ZaNyjb7CtIznDkZRIQxZ87MLuD++++DhQJSlViYncW1tXVkd8yGgM0Y4THj1sMH8IabbsKcFPjx337Pf/SnXwbWJkYvJqjzKlwuB5FLTlnO8HWBjwkxUdXsrgwSzKkwKFqynhnNW2Q3zIXJck4uGpP69QABAABJREFUTKW3eWYjYnBEETZwJBpyqczJkbLnXKhmIVL0Jncs5FY8j5NYkcVylg6NOr2wNhFWFAIRJ4BJy3Z2EbTirioNADKh853FkOrUp6e5WenNu2GGQJBSE+Ejke5wppofyIKN79XddT5+MJW/1s3ACOkplfGhcTVMzfyuVO2dNJObEpvDNN+REioSOWenKkVcihSky+il9NghbM7M+gm5A6EQSMxupuJBqCw8O6lCr6L5bDKfp/gsM3qEVwYUAJRod3Syu4toO07apoV9WguuZSjmQlkc7Pdnzi2FcXPPb//24OhDD6W7H1p24LNY/XePydcGfxjOnE6FxvOdlVXrSbKZaHF2ptJ+46lnPZYa6LmpmzrZKAFDz5iUFdIrow3dVmZpO9NAHTuDuKh6rqN47pJdcUpyK0pH3cDF3EVdpLKmbryo6Mhilt1U1LzQbDlmN88ObwhvRGSSwQmBiWSfMbGGog0dDQQdd6vMrRK2Bx2o4u6ZbeuSuHtARAChcBeuN3j5S49wuL6Jd/7yB3H7nv2oVPHU6bOIdURHFZO6hnQrLFQlrq5eRy8J7rzndjxzaD9OPvEiyrIHTzZ1iwGhQtrHBVRtcy9CJAViQTR5gts++A586F98Gk2/xPnhKs6sLOPycICZqsAkZ1RQUBRBA/bNzOLQ3CIml6/jC//p89g4eRFBSuck5ZC5jpiOu/ujRdBzQDsfi3/47Iru7W8uXD5z7f57P/6JB/bdecuOs/WmnNtYdUwbLVUE2QSzRQd9KfDMjx7HxomzqBCQcvROUUFoFZ2SSY2wygqWKKVMJcP7fvmXwtyh/Vz2MQe5gXnbpOlmiHUtcIRMirpnBk+SLVEbA8WRBwBKWEpkzu0gYQgOXAGwBwBw6dX/nu0hwu21LaC31/8wS8RleRlYWrqRg5agbmkDwI6fuPEs0B2gI6WnSGepSeC1p1R7SilNraiUE9cmm6xUcODAkrz3kx8ovvj7XyCEIY5TtyM6j2TjnM0NPqOUkGOGFiUuPv0irp44j113HcW+zhCWIwIMMWVkGpaH69hV9XDkdbfhpre8QU89/IODnTL8UmemvLbnwQd/cOahhxv8Dv7h26MPP5wHH7t/WGk45+P8KDq6w9ZGC1//47/a9+6Yure9+XVQIS+MgdXxsC12sAxQ0A3EmWuXMW4a3LVzDx74zIfR7fXw3b/4KnXSQEVQOtutY2kB2KC3GY4t2yUbuqHEcHUdv/tvf9c/9D/9Mm+/+yYszvbwwxMncfry5ZbGC+CuY0fwhqNHUTaOR/78b/zFL30LnOSsHiY28VVmXiR5MXu+7sIBwGgOEaDKcLG2NU4ApxQKkG5OgyCSjBBGMWtcwkSJmpTG4A3NatGirpkbCGIJTfSQy5xNguaYLVtR5E7OFtttjcykJshZO2WWpjFS3FOPKAGfKIFok2lMSIrCxJJJVZo2tVlvhnkw1qtXLvdj4/sVcoRuh4Xc7ZSuCM3MRg5sekqb7hiQHOecY9ySjOIC956I7Mzw/ch+UMi9bjbnQHDzBmZ7kW0/cryM7GsgDNAOaHMg+6CUbcOGJ+Q8ATmBeTM1LRVAB5QZKGcBmQXYh3sHZAciFcwKCEpQClENZllbV5lOeNedOxvhbVTGlZTD2Trvfuwr31rG/+f/NQZp8N8U9HoFiqqLSvtAMVd0ynkqFwoN80URZkiW7fgaRt2Z3vWq173klq8oYSl5A6vpXhEco+V+AByra1XY5mjLLQx5pqrFGyPKEmgikDNcCrccIQC6Hbg100oUISyIm7kp3FxCEnrl7tHdG4M3AmlcLYprBNhQ2NC8oWgnuSQxT1mk9GRBhAoClk0JLx1SgloALj62QKNfeuQJfG1zyAd+7aM4umsP1IGnTp9BXdcoygJL/T5mXbC3N4ewOcbv/t5/xpXnT6Iqy2knuSN72z5OAO7GLYY3hGgKQe0RWQTv+PVP4B2ffD+u2RjnVi7j3No1xBhhAAZNxEwREFNGkAJ7Z+dweG4BqyfO40u//wWMzl1FRzueB42XzkkwnE7UHwN+PDd5gIfeb3j44X+Y8/zb4PxL/dnlq5fv7t527F33vfutb9gM3lkZDLBeT0g6xAFCMBMK7O7vQH19A09843tgJjwbulB6tuDwnhNmArVCgnTLMPFG7//g+/UNb7+Pl5ohlyebGKcGM0WJggBSRJpM2k2znMTcrXDNlpIxBOMgO6r2BRl+apZmJyRsO8vba1tAby/8D0CwA4C7pu9j5LRe1fGq4UFR9fyzUHavPqtr34HoMMs5p8iSdTMc1/VoHMulnsONZokRjpXRBkoVHr33dr7l/e8qfvDlh7UAS0xyR8CGDqtTFqGXBYXZibg6wJMPP4r3Hd2PPTOzuDYZYtTUqFTQVcFmnODqZBNzsyXf8t634+yPn9kZ14bvKSu5sMy0jufe9iLw6OQftS3YHacyzmx24ac2JulxKBaxMnzzt//8a3tSsuqWN90j3gGblLFZjwFRmDuabGhSxonrV+HmuGXHLrz1ow9hZraHb/3pl1EvryKUFfKoIVyBmLwlNDhgjkBBbMfU0dHgmxev8Qv/vz/COz75Ptz1zjfggdvvRL/q4MXz5/H6/ftxx94DSBtjfP+LX8eJrz0KmXhGljGN1wr4RUi47PQVuoyTm5uhEJHS3EUo0jZQu5PMBjGAGYKktJbjTIkmrN1RB5EJVSaETwoPk+xWl5SGjkTPKTozQzJTt5Y3XFt0NRaFieXMXJrOeJamMa0KA4B1jDCjlVMm7u0lenpMiUtRWuE5owjIKckMtfrYxz+9uxuq11vO99P8FrO0YOaVQ1iEkN09kZaVksCtkr9pR6BlZsuaci6T5U5KqWMxVw5qzkYARuIAzG+lex1U4zRALYAX7lASklvX0iA0mhtFzae5fLhLpge6q5kHgAo3gUOU7S8YoGhbeEhr71nLRqOHoiiCqFYSdFdVdO6uynJVCx0UWkQnKRRVeOHulQOVk5WZFdmsYFvSKNngIhIh3HjiuWcvvHjqxPPVTAdN8tqQJm5lhAIYA4Q4u+oMI5eicumMDQAs9jnsVGaTWvpNYyhLuBldxRnUmlDAk7h7REEBRLzO9ODRhVV2i9k1ZLOUnIwBmA4bSsq0JPBGnJFANPdI92zwDBGjooSgIFxgnhxoSNYECriLx0zLLkzg2g+P4+GY8MBnP4Ij+/ag1IAnTp1CKYr9M7PYPTOH8akr+PaXv43BySsopYPCCLM8ZZq3Ne3OKaERjgaAdQLGeYKw0MPH/tVncdeDb8KleoCXVq7gxMoyZuho3NsypBAwycBsWeHm+UUcnl3Ahadfxtf+6Itorq2jYAUfRWhCXdCuJsNzbv4CxVfUUsY3vyk/h4D4U87z/JPoN93Vm3Mhn3zwlz/0tplDe/tnR2tyabCJvgoIQ3TAjZitethVzeCJ738T47OXUFgBbxLau+0KR+UKtyKId0QnzHLo/rvlHR98F6/mBqtxhI16jJYw43AKBI7cRMJM6crCPWeTLDnkCessoTQZm6GQn3OuvQJAsO8nXejttb22BfT2+oVaD6JNw/59toeqYx0QA7CwiZZPBNgWvWPSXlSFKXnWGCB1ndKkqZtmhmIZjklOoACpGVNHgtAF3vG+d2K4MdRnH/6+sAzapLrqiVghcPcszCbigGrAladexMXnTmD/G2/Hnpk+zsUGsXWNUFnEmcEaFjtdHL71EF7/nncUj//FVw+mUj+kluqZVOX+P/vAqSt/8NXRzxHRr32B8NnPCjafYEjdNO6M1woNL+Uk89mlzJfX7v7OH/73vfWo6d759nvVenO8TGJtPEDOGeNkEDPMS8CpK5exsrGBe/cdxF3vvh87di/iK3/wZ1g/fZHdfuVxnCiuLgByaq9oDiBIWwqZmsxOVWByfeCP/MEXcfH0eT7wyffjTUduwuGFRXRDARnWeOSP/xIXHn7MmDV55Egyr1nOF0m5KOKrAGrQ29i1oGCbc1YXdziNwkSIlQozMJEe4RI9WyNkHYJMzFkbfMLsYxGrs6MWy7UADeEpWshSSKZ2jbFxKEy0Y0i1k2JilUmnMY4LZyUuRfD1rVDveOycC47xK4hEtZwLIg9yP++YTWwuXQs79h+Y+X/+X/8fR/fO7XgDYPcLfE+bQ6C2XJNXCM4tZ7idQXv1Y2xTUJlMh8TMp+4j/MaRQW//3AaPCU77uKXN6QIAsjuE2IrpTncPbgDsplXe05rvrTvAV0eZp+Hf6W3aIIGDgAAosuUZOHYLGeHMWxHhtgbPFOJKtA0sfuP4NaClDpvDEiDj3/n//r93PPbjH3tvvj/wZryq5KZVANIEXXTRTN1nqdTXB+rabZ1DDWPPg65IrmxQ1TIzVpcymE+EKMSRoiFloCggMQJOF0meQSMtq2mOOUUzTwoWLkhCZoFnMybCYnZPdCRRRGTNIjmL05OYg043VxXm7IgAGjhqgipQInuwxlXMfeOHx/nwsMY7f/UjOHx0L7o3B6Q6YqHo4MUfPYdnvvJdYLNBWcygjIZgDvO23ERVpkU3ue2JCkTuFJjUQ8zdtB+f+jf/DLvvOIzzg1U8ffUCLm6sYUaBxhxjJ8o2joVup4c7duzEvu4cTn7/aXz9D/4MPmwQoG5N40X0RMdak/00gBNBcAWmTRYqdtcF7r+fOHbMcNefOH4H/qrzFPHbIL7/4QLxer/pz986Xll9z4F3vvGBW9923+E1RLk83ORmPcZMIIIblAKVgAP9eWyeu4In//a7QJMAIzrWHrcuLuYSsgikW3DiE5k9tF9+6Vc/gUkvcH28joub64A6aAm1F1ACqW7QjMctOaZlXiZ6k6lmrIOxmhhz4cAaJKhjUYD17Uvt9sL2EOH2wv+4FI4pgeMggJlp46DPzLQZZ/ctSCrR3cpOoiVJhDEdlcYA1QCFQqxAkQPmbn7zvYd7+xb2XR0P5jZiHVRADUROCdEcRVnytmNHefHiFa5dvEzVILnJWsAVoGQzWnYxEXgzwUZd47bX3wUtAwa5wWZOmEyjE+IGc6AsO7j1yCGeOnWWwyvXd3eqbj8l3xwP09X8hplNPLdsP2sIC2+ZCbh7SXH3kuLq6YDuok4StBSRYMzRcoNkkRRlts6F518sG3O94+Yj0i1LmDvWm4YBAM0hZijhuD4a4cz6KmY7JfYf3o9bX3cXVjY2cO3sBWqnRKEBkyYCQleqwx2WM7YmgaxJHhCgGrh88ixOvnwavV4PhxZ2Il7fwMN//CVcfOQJZw4Nkg4087o6LsDlIsEVEY4d9AQWcO9QpCuCjguDMggBAyWLsqFIdFijZCPUmvCJARMoJgQmBWSSgHEQmcCsFq0aDWiEZSrpyUSy1LWJSpagme4uRTBNySSYS1OYVLWJqm8MBKiBucLo2ehJBKGgFME1RyvQz0NUWWfH1q9nMRmsFgv9ud2f+sjH39rvVG/N49HNcTLpWozqMQtSS83zlOjZyJzBbEA2SHYwpdYtNEcAoGaAZdAc6oCaU9w8gFB3FCQKEIGAOhC87aMOU/azAih8+nfhla8VaAVVaP9OhGmRhgIUb48LcQfdINPjRHKe4ggNbhnIuf05ZkJngOWS7iXdS0+5gOVAc/GUaDHSUoLFiFQ3yHXN1DQioGoIxVf+9hudZ48/Z91udyOmfAXAhkefaIFUWzKVZOLBQ0OL1cilU7oOqvbFTL+B55IojKXVRBEIJCAmIIQWVZESclEgu3nFgBzNg4u7ZqOIF6pGEYPTzZJDaAJ1kGagKWAuwfNUMJLOdlOE4oQSVJX2VwVACVAp4rmF97g56UCzssbzp89hz9ISbjlwCN0G+M6ffRUvf+OHkIYoWUGbjAIKc07LTVrChpPISqRCmSpBbTWOPXA/Pv1//heYvWkfzqxcwQ/Pn8alwQYWgyDl3D7eoa33Xpqdx52LS9jXmcXjX/k2vv2HfwEOG2gmdJIQspmAAzFcAPmCw19C9suEDDND7gyjzOx3nUXU+bO7dHDs9YL7SsW7DguOLeiel/ZVqNKcdztHU5o8gF1zH/nYb33uzmL3jtnTmys4v36NJYFxy8eES4H9M/PYX87gsb9+BJce/THUFZ3cvkQzM6gqo4DsVzLxRoqd8/LL//rXUexZ5HIzxNXBKiYekS2jRcETC50+uDnBs1/7rtv6ZFQYz6LOPxaXy5rCIIdx0ro0KYd2Y9B8xV9DbqKMwRFfaSQUeSUDvT1EuL22Hejt9QvjPv+cdQltE6EsLzuWln6ilc0IrN5woV+jRFM0aMila1OP60k9GEzMmAMBWMbEOcWDClbGGwCBgzM78KHPfBh/sbGJ68dPcaZTohlFes4o2YZNQwZj0cHK8ydx8vHnceyB+7DYnWA1JZhFuDhEHZcnA/THHeyY24UHPv5+/sXZS+VkFG8PgZ8Qswv98dLqoL3z+YZ4vv/+sG92UExWu4VNGlkHML9zh2MtwasoOc5bKjCSOLlclB1pxjHnIGNNdu/xv/zGgWZjc+5tH3tPODQ7z4KKq4MN1LnNRHvKmA2KxjK+c/okhnWNO/YdwMf/58/huwf24PGvfBt50JAzFbROYtmzwC07oQ4GClPOLXV4nFGUFTZePM+vn/6vuPb2+3xwfdUvPvKYqVSNNz4U54rQLxvkCoUbhKWUoUYPIDsK7xJeZIcotZUeoi10gEzm1jh84sQYjpqUcRBO3DDOhqZRTCr4JAONujZS5BhrJPEmUcQVbuhWLjEac3aqOCyDZXCO2yE1QPBKzvYnjp+JOHXi0uvYcGK5dM/Fudr6u4wXVLxxVEGw3+p66fTJk1WKWcsiIEjBImhLZhGBkBDV6TAVobK1We/QoBAVqCi2qDKuAUKBqrRgYuGU8vKK6zyNZ2CrGrstCcENn3nrc7zRN/jaZVPBttXMR2stbjNrq729hU6YA55bBoSZIZsj5Ty9bYtQdGt99GwZlg3kVt14RsoZ5o4Dhw5ipqoCLHbEbJHkEuk9bSMgbYBCvH18wsiR2yy0rBcu5apLCU8bfZHewPNGAVStU83SXBDMYgQ6Fds7mt2K4DFn78Db4p1IddJUJNcezcksEPOM7JZzEslKz6RmczN3MyFNKZ5hkJZuGcw8mCHQPJFoSBE6qC1q2LMjIENoYP3iRTzyB3+FyQNX8eSPnsT66UsIvVkgtTtVWzx2EWl3Egi4EDWAUAVEZiRxvOXTH8IDn/4Q6q7iqQun8MyVS6hjg7lA1Ckhg4AbulJi3+JOHJpfxDxKfOcLX8Ezf/m3CFnATCBlwOgkahJrQi7n5OtKZgEreu6DgEinwdjywOtM7+e9GOQRDmac3sBM2ZdJz7oqaW/R07eNR+MH3/yhB+/eecuR2UvNBi5urpE5w8QRhMgQzGqF/d0+1s5cwnMPfx9EgERDmhYAhRDQuDEXSqUBvRIf+Y1PYuHYAVydDHBtuIa12KAQQwIgILpUlKLwuoHXjbt7bdmGQWWcMppYxqwMJiiNOnasAD5vxAJ+woHe8w/b9txe22vbgd5e/2Qd6DM/24HemGLrBgAGAPo/4UJzhu3+t3foZjR21DkS16RBVGqaFL1C65Rn97zulkNLtxw6uN7UC1dHw1DQSW+31YcpYjipoUrsWNiBw4cP8aXnX2K9OWiFY5NYaqCZ0aydLE85Y2VjHUfvuAW9+T6uNzVqi+gEQYRhkFpnqBsK7N23jzkmXnjhRKWh6BSGNQquNq/bdw3Pns/4HQCf/aweXBgUm5voBZbdcUA3BK2sroK5qGuPyEYUAMxczJJnRsITzIns1erJM9XVlbVi/8H9nJ+fZ1EoJzlh0jQIIJI7OhSUcJxaW8P6ZIylhXnccc+dmF/axXPnzrMZjVo0oGfEbB4C4WZuDlQa3Mxao8wMNHM00S8/fzKvnr6aBMWEphvMvirAcjZcN2AoZHJCQVYgu0GlG1QqFS1A0kHL9EaEk6AyQUvmGInomMaxCceBGDl0ZGqTEjIulJNsuVYWdQrSuDEqPEkKJpKzqmQV2qgJ1kFhzDrFotU+LM1jEbwRAWPrTs3PT+t+y0o8dwl3SmFeKpJNPM2VZTq9uZln7u1ieOZasTgzu+8zn/j0u/udzi0r16/3SUUIBUNQCGUqjAVBWpFMTt/gUCFEWmUrlDZsQUJCANGWXijbIEiQNqCMKa+bUwG9VbKxJaansvpVT6qW8f2TTzZ4m7Pdyphs3cT9lc0Qn3Lt2vfevgBrFXf7fdNYyY1XstPcPNvkB9oIt0/b8zLm5+dZVB18+atf5bMvvpA6/f71poknFHpZizxwaDYRE7qJm2+iMq1p2u060AfQh8VIdAH3DpraURY1maqWFk6COQOxaLndZo6iQKa4oW2jMRGPklyFzixuENNAZ4aT7jS40xwixjZP5N4WlxCAwCjurnSqiki7s+Nbjx7MjDCHQOjZASPj+gBnnniO9eoIWnQhDVBCUU4Lazh9QSQCmBCxVOpMyWEaU3fN4iP/+lfxzk9+ACt5hCcvnMZL1y7DLcEsgW7oBEGdDWUocNvuPTg0v4juJOObn/8yjn/5YUgWeOOQ2hDah6MRxyYzrsGwXAhWPWMoKk0ysywWlF4iaFmQlTNVwlAFeCeI9ppK5hvGQzLTuXeUJw8ceNM9973/cx9fusYULgxXeXmwAYNhkBM6IUClxP7uLBaswHf/299g/dkTUASEdlZ5+u8HPQC5ExA94b2/+Sne8c438mo94NXxOpYnIwRm0BIUQDZDVXaw2O1j49xVvPDIYzlM7GrIeD6QTwGyjAknEiVLselcV6cIfGhEF2D9Cv6UsvyzHehu1/HYY75dprK9th3o7fULv/Zt/aFYdqClcdyo7wYArAI2Q3QzMTZCtA11ZrHEIiEP6o3VjVHhaEpVFxApGwKAbBEkkTzizNp1KBV79+/EB3/jk/jLf/sHmKxPUHVLjMY1KgoURB0zpFNgePICjn/vCdz/iYewv9tDbRHJGxBAIcD18QAXOz10iwpvft87cOr4CV07fnoxdDpvtXFzeqEpLqx+7m3X8GAVcfVq2NxRVUGHvRo+05FQkvSYY1SyqScxsgiGgRFlzkyclJ3yuls+GxvvQlF6CLzy3R/bV5avz773n32q3HNor5ZzgvMOrmwMULb2IOiOrgLnV69jbTjEW47ehNvfdg/27l/C1//0r3n+8WeRqKJBUI9TLpTuJnkcMyoROJy5SayUSCbm0s0mVtMwUmLDgqzlJq0L0AAk3TpUFQAFHCXhAaBkEBSJQk9qaEit3WyswolARnQfOcNY3cfmPhHFJECbDKtJ1jlL8iJGQZnELYtblq4YtXRpakMG5kp1hlcPEQnmVX0DAF/lPltMtJzpTvoW7aUqbXNS2MzuQX75KjI+9pgdwG/7cnMpp5RAoAOyVA3I2UnR9korbMWkbAnLrUIMTkHDWy4ybshe91ZMk9Pc8w13uf3eVui2EQxOXe1s9qpWFtwo3rjRrfyqq7+5Q6Zb2e0LJN9iprWu8zTu04rgDLO2+r29besyt7OFfOV+UyCUaWbX4RDkG0J86368gotOKbOpY2HJCrgzZ7Mcci4NWSyb5I5J5S4cOOLUha5W3OrIVkgDUgzcctcZsgNjSJPNu902KiPZ3aYxnBjNi0I8Z0FVGnM2i7AkYoVKJmI2g1lwc0PWoNmMWSkpBcvItLZkyIQZokKhBM2Wp7kLcTezDEt0JoJZyQqGUkQ1payACrUkjMDEWZUKNzBZgoYAI9sMMAn0CngAhmmM3a+7Ge//jU/hptffhrNry/jRuTNYH2+iL4aJOxKJSgXjlDHXncHNu3bj0MIuTK6u44v/+Qu49vRLKFDAmowiwWmEiGQxrwmM3G0MlZydJWF9JOygMhfZA8QbmGVIacV0GyrkKFZIacgLodO5aWj1GzDXvffBT35oTzPbCWubyzi5eh0dBepk6BCoU8bBXokjsws4/9hzOPfDp0EpgWQoRJHdkMzg6jBV5lTjnb/2cdz9zjfiymQTV8frOD/YwExBMBuSt6/sxhno5TZbXY9q97rJ4lgT+HK0PCxYRC8mJjbjP9Vau/7zdznxdzXDbq/tte1Ab69/uhnoM8TRoz/lQONVDvTsfuDSRWBuxwiee3R3shawFnhptI6KOdVjqSizBFCTKFVVY1PP9A8u7T34+ruOTCTvXh4NQmsAtj8jT0t7szvWmwkCgX379mBp716cPP4y0rhu56XSlGsKAuZwAZYvX8a+Y4exuHcJ4xyxEps2HEmiI4JBkzBTlpjrz2Bp1yKOP/W82LieE5GBu12alc6wayMv+0URJ9b1krPimM3wmSazci+0kExqYmiEkbXAswokiHvRxBToRgMcySlFoc3KWnHq+AmdnZ+V/fv3sdepEN04SqkVYUKYG2aDYtiMcWJlBYGGffv34u7X3QnvdXj+wgVaPUHVrZis9SPbamkY3LJlT+4ekb3xaGMYNj3bOo0bARyCbBxwJQOASsgugS7pFZwhkSKkEYxCjkVkbMCQ5FgkDEVl6PARaWOnjBU+NuEEwlqhEwWbUhndGEWYJSXTTpmlnri4uVSFMahrEXwwKT3m4L0cXHLwjfiK87zlPucYxVOPhiheiTARaqNsM5Z2hvW4/KUfJTwM/1cPPYS/efLJsLPf3/vrn/nMg72qe3h1ZaUiyBACRBSko60LaQsxRHQqOF9pf9wa1dM2IQyRlv0rojfcaZJTUc0bInxrPNG3cpzTj3Uq0F/dbvLTop3T+UB/5WNvrUlOrWefOt3u1g4vWvuxver9q0W5m7fZ1CmXd6vQh/A2IuKOubl5dDoVv/TVr/gzL7yQerP9S9nSM1rKeZVys0kxae5khpHrpPQmJFd0japgGMOz0WJJVEaY01PBTtXiLCEEY4J4z5lHzpyd3Y5TxJEy2K1eKWEpSxe45ZS8gBpdnBBDoLu7i8OFhJm7avscl/YfyyCkZWO7E8BMIgcyAkwwSyrIAhinwlrahnQj1ZDbPDvBG618FDJxWrfYUdQe0QTDvR9+Nz71v/wmFm7ai+NXzuN7p09gUA8AATZiRFcUTsEoJeyem8fd+w/j4OwCzjz5Ar7ynz6P9RfPofQATjLKTGjydso0WwrgJGcbEDIUyoRA45REalLVBMIFohSWcHbKwmaMMhfhOy3IARZ6Ryzl9bXFe9/7a5/Yf/i+u3orcSDn1q9zEseAZ7gZxIGZUOHojl3Q9TG+8ft/jnRlFTABUou2A4CkhFSKZA3u+ci78a5PvB/XkXBtvIHLm2so1CE5Te++TY8qYrHTw67uHC4/+7Kd/8HT4yLxhWB8Iqd8qiQ3vGAUHxgAaCpeaR+cXlNecaDncHk02sKlvuJAFwVw223AmTPb4nl7bQvo7fVPXUA/SJx5GFha+pkCGgAGm8C+/XiF99zmPNvrfjlPHybxjogrFB40iEkQpSs1oumG+dk9x978uqNe6Z718aAYpYbTndg2x5kTYIZRitiMEd2qxP6DB7CwuIBTx1+Gp9Q6i+aw3A5cGQGfTLA2GeOu190JLRTjGCF0hOnJ3txRp4yqKLB/717knHnxhZNlUah49uwxraLUVDtCIbErHmbNbcZcenQrFElgTosCF2fOWUoUhcPLnFAqpQS8cDOBwyx51hCQh2M999KpkOF6+PBB7pjt04NgHOs2f6uKSWqrhgMMVwabWBsNsXNhHjfffguW9uzExStXMNzYoIbAnN0CmWEWxTwqvaGzBjh2x5COQQCHZj5GiwJziralhsLSWsxZIc5AoTjppEQXjJ0YB9GhkkOKjBwcBXKU3caZYRTgEyl0Asu10usQvImSokOTdCyrSZYymDS1DafRjEaIOFTv5uD1FIlYywZq6d04prZWqYkWs1gJsSaqi5BWe1FoRuyn0xudhDNnDAC+9a1vOfZrsTS3Z++v/fJnHuqV1eG11bVSKFRts8xKvsbt5RZUw9vJM5FWCBOcCu5X5ZynondLRIOtM/0KFr3NzPpUCOMnBPNrrDP3V6Us2OLRtoT8q+w1R25Vom/FQQSc8sS3ctWOaeX7lpCeimxzu4E93JL2W7d1M2QD5ubmUXUqfPnrX/dnXzje9Pv989HSEy5+PtfNoFBPw8K8Nymdql5rA7HSqdfAoPC8RIvxFQHtHTQNUY2N7AoGI/WYs0cLXlUAU4S4OasKzDYVzwVuCGkzDyLexMa1mKY1HN5CRVrXnTCQpDucIi7OtnDbkUBEBSZwHwMcOTAhvDGzRLSEj7bdkInwrKquohAlKe1b484cBOgoaqtRLM3hod/4BN77qx/DpDA8euplPHHxHNwSRIC1lNBRQXBg3YBbd+3GnXsPYF5KPPPNH+Dh3/9zxIurCKbAOEOTQ619AaTuppTk3iIgCdROmQCoIToRel1IS8wzFToYQimdDM6L+m6IHzKVWzlT3jloRrcde/t9+97z6Y/MrKHRc+vXeGF9BZUKJimjpKDUAjt7s7i5v4DH/+qbuPCdJ0BT0NoMczaDB0KnjYo3v+fteN+vfxLXkHB9so6L6ytIyKjoiGZIN443QCFY6M1iKVR44XtP2rUnX9oopHwqxPwEvLjQQRqmoWQJsd0MalqSy43Y35QJfU0EfVnG3IhtE2FROIrCb7QQluW2gN5e2xGO7fWL+jJtyoDeguD/DP6zqPoNMP7cq4SDGZ1GaBsggJZ5bWVtnDdHddWfS9mJmB1dMdRm6IIYpQwh0VHB1c31dsx+p+PI/XfigxT8ze/+KXwwQRZAMyCiQMqQboVrT7+E5x59Ere9+34c7PZxarQBtM3TKAUYTIZYmXQwE0rc/+634MLLZ8O1p188GgLfSQvrhaVuJbgKKSDRuh6Kik0qYI7cbre7wb0EtefiDpVMKd1SCbhCaBrzSKtwPUOkGWeXXpF9mPJzf/HNnevXVrvv/Nh7wrFdCzJbFriwuoK18QQIipStFWMiOHF9GdfGE7z54EHc+tbXYXH/Hj78hb/GmUd/LAwInRDcUspG1IWE2pEbz5wAVovIGKlFyTkls42WSgYVoBIMAhMnQA1ZAYNbJEPjwgnBMciJZRuTPqGzLrScOLwWysQs1yqMKbHJaklRJeZoEoNJE4w6bhvspnENDtUZWjwddNNf22I5fQHWS/ScuVYbZ5pSDEmsKKRnBkUPqxs1ZnatOHYce+2FdFkce5x0qlDIKT4MZlOxyxtO7tRtbNvltobHzOHausc555aM0SrbNt8KxXSg8ka22dFmon1raHD6d9/4Ga8aKNz6c35VrONGnGNLyU9dbbsx/NeK+OwZnnObgZ7ellMn2m4g9rYy1FOxPFXx7d3a4u+1mW/3uHUbJ+lm2TKscctji0UsYWlYd42qvq5bIRu0mWcsAFh9BVE5jdpsnR82Aeyo1VltPa47UPSDp0ktADBIyfs503OX0ph5x+kCkl1JjCZCS4kWrIChQZZMbVtwIBAayRDUPSc3RVaG2iUPU8oFSTVA6dQgWmb3HshZg88Gat8dPadVDqkA6ThZwVyMJglG73Vh4khxhENvez0+/C9+GUu3HMKZlSt4+uJZnF9fQxEEkYYmO/aFgHFM0LLCm/fsxdHFXZDBBI/8+V/ixa9/H2IEksCbNPW+HS50YYvIy9MHhfQAIKi7KtsjJbt7jg7VQBKSaBqT9UR9EcI9puFAKuVQnSb7Z47s2fX+z3ykt2J1uB4HvDhYQ7dUpJzRCYJhBvYWFW6eXcD5p1/G8w9/v4UnZpseJICUAi+Iuh7i1ve/Cw/+2kdxDQ3W6iHOrl5DZEsNiibTZ4CDuXWgixBQUGB1wvj6RobZhpDLyfx6yLEeeZNDmPGfi0CdXjeWXnOp0dfe/rG+Aw9vi+fttS2gtxf+hwBB79v/CpGjbSMMbinduLB6NkKsteYogJUEgCZFD5XmdH1tMlwfTOYO7kwLZemDyQhujh6AHCMK97Y+1wzzCqwMNvCyCGRxNw684VZ85Lc+iy/9x88DG2Not0AaRQQhkFuawY+/8ggO3nIECwd3YTNGrMcxoNKyoQNxeXMdZShwbMciH/jYe/0L5y7MxbXR7aK+GQ2q2Z4HuSFKILq4KjKAYGBmVhUrDSooFMhQTSwoWrnnQh100ey1Txiw3lWVepyBAmRH9cIjj+FLy9e7D37mQ+HAzQdZgDwrq7g6GqKQdqgm5YRuETAcbeJrLx7HfQeGeP2Bw/jk//xrfOKWm/CdP/tKGFwfsOoVrpMUm0mqAxhJ1qXoxNxqiDQOz+bu0ja3UYR0kEEIF0V2t4LIItqQWiewDo5WKKvU6qzd0Bi18YwoZCMBEUTUxCZXlmSYsnRDllwafezD0oyh8K29icFUPOOnxHPbXDnbq7mxAfRzpqcerWzEkCSraicUYuMxJmjLVbRb/PSFdCFJTimYu7bGJVv8nLziIMOBINpGK7wlIm9J4bbYro1nYCuaIW3+GVMiA7dE6XQYT/nTOI0tKoe9yomWqaj2V4vnra/zVclod+RpzGJLkGN6v1p3+1U/j225h7jDhS3Z2vIN5oeSyGz7V14j+fmKmPcbTXCW4Bi7YRSQ65F3c1uYMhXLsc+52Ofm3Ji2AQALsBjpc4meMl9pH10DFL72qscVWMP6AI482/J1UuIwCzGX4Ml4Q0z3zPKk8l5XLU3oWWrQ6ZCCIkb3TCPFzFiYu1PNc26S+JAmhYjLdFCToIuCBVy6lm1eRBcNvijAvIN9DeoE1YDSvaWCo1OiyQ2KxR14xyc+hjd/9CEUC108d+EUHj1zCpvNBDs7AcPUIAOYKwIGdcTc7Bzu2r0Hh3fswtVTF/CNP/5LXHvqZYgrWDs0Yuo6t0fDNGrm0dtCV9KDSijccnBvUfrqbgIa6Z6Zp4ezlwicMfFFA/YntSNeyAEjF9/76V/qVks7wsp4g2euX0MQIJAIVNTmmBfFgf48ilHED770Ddj1TQgC3GL7wlIJFyDniFs+8C489OufwKgruDZcw9nVa2Boo0TR24hQQIthdACDbBAFZjR4Go65sXw9QWSFbtc024aKNAiFsVl/zXNWQnAJwVNdC/6+/HO369sZ6O21HeHYXr9AMY4zxP27iJReiXC8Kr4BALMbztnZ9oTXtxnecJrd6eWQRpV2txLaIRWMghAgJlJUWjXjyY5Db7zz6OLhffsHsZm5Ph4KzMiUYO6Iud3sbosMDB0lVscT1DmhO9PD0v69WNq3B2dfPoU4HEOmA2IOgEGRJ2MMLOOe190JBsEoJzRoebrJEoyOcUzolRWWlpbY61Y8c/xEIfB+2yHCpoJMzCQZPCmR4JYI5pizVSgsI0nhUAAl4VXOXoEo1VCRKAgL2UwLIQSkgbSYRYOGenUznHr5pFZVR246cpCzMz0QwKietM4piEGO6KugQ+LEyiqubW5iaX4Ot99+Gw4cO8Lra2tcP39JYjYRCRCjiXsCEB2e3JBAZgo9t4UfFAkQgWfSQwimZARZkxiTMjZwJET7BpmoysQpdUHU6pwkokZGo6IxqiZxySKSJaiPbOKxLIxBnEN1RkETBX+XePa6lqoCipBpdSVWNGpNoRZcO6GQXDcKDcxxZHPaiTIu4vqbv5Tx8BYbmMD8vs7SztnDv/qZzz3Y7/b2X7u2HODOrfpzTkXwVqzBp+1y2R3a1i222WNrXTmZutHWcsSmwrp9amwNFvqUyiHTHPVUEb/GXb4hVrey1j/xNd7Ie7RxDueWYyytY4wWXbflLZs58lTI+PT++hRn525Iqc045yn+zrLBpjlYd0dT16ibBvM7FtDtdvGVb/ytP/nM0+tzO3Ycjyn/0LrhCkexllw6umPAnG4lJwDIGugCXiSiMnrKbN3nCdq3V6+f+FgaQHpgGDiL7Iw9MBLRpni7kJ154qlWTwASAwIDSjpjDhQh0TZpg+bmRFSVxh0TYxiqcpPCdRJrdK46fV0oA6E01qrq4GQFSodk1x1dd+9UVVGYUieTEQ697T7++v/9X+OOB96IIWt8+4Vn8cLFc8ieEcRRe0ZJIJph6MDde/fh3r0HsKc7h5d/8DS+8rtfwMbLFyCRkNrRdYHmlgEuU8qFToMoAFhQ3AgTIolI7cSIqhtCbkIwgkgtZKZSoOgaseDC/V7wcFPJwdri4ps++p7e6x94U1iOY5xcv86V0QAgkNzRWNtOf6g/j5vnduHRLz+Ms9/6EcQV3rRDpgwCKYhsEbd94N143z/7NIYVcGm4ihdWlkHPbb2QGRQtWSXlDCWh7fAyqqKDvbPzaK6u8ulvPDqy9fHzJfBEme1E7T6Skaat+MZWhGMrA70cgve3NpGuX/fhWPzGDmdVOcrS8dSCv1KNuy2et9e2A729fhHXVjRj6/1+ABenOeii8Esxcuknv8eMXSpGAKrppxppXNFPqOvJ6sXLw0MxTwoN5ubIbm2LmzsmZigAVKKwlDDxjB4Fl1ZXIFrAdizi4P134gOq+Ot//8fI66PWNXSHgDCtcOHxZ/HsTYdw73vfiiY3OD+MSFPaVyWKuqlxfm0Vuljgzre+gedPnitOPfL4UuiWd8XN8Vigm2oYSOCImTGIOBjodKbapGizwwpzdUcAUxCXwgWFGIoMDRBnk9wpaDoiG4la5InRK7F0aXXHo3/8V72N66vhjQ++Re7YuYS5quKzV68gpoSeCOBAsra06+LaCr40HOH+vft5111H8St7fxM/+sp39PEvfavTXF6lmUpfVC27wkUYzLMzC5El0yGW23SDMLDlIBPMjaER54SCkcInbt6QSKpI2TwHRTJDcvVMwuhqTNHYhZGVidCkCTar0QcAsPHKy/qfFs87ptv7wGxVi4XMXBs9Z1opYkUSA6UTCrHY5s0hcKr4ZjW2nWFpq43tNcdZNJfclnFgaWkXAhVbGWhMebX/f/b+M8qy67wORef3rbX3yZVDV3d1ArobjRwJEExgAANIMUkEJZKWRAXTli1dSZZoy/a948nDUQ66lq5lW5aVLMm0RIkSo0iCBAkCJEBEInfuru7qqq5cJ5+991rf936sfU5VA6Ds98Z44w3RtcaocbqqT977nDXXXDP0jX8D+UTf8DdginMQbLbppfPtdkVgriVvawMpPCTf0N62AqVtsXL5Y22/hvaBtuo2zTNB+j2I2yQimpd5QBViGEQWnO/MGNUAkEVgscV497Wp1Jdy9B9HFWmWIk0zWGvhRJC7K+seskzG12PVRKfEAR6uWWXf7TJKmwSMQLIqMVoDycYIRqDbZFz1vswrZ545emmed2trqoq62r8fAhD5GolG4go9o2RIu0SmxOScGtLEMEVBRSOiIJNlrBzKm1gtQyDkvaqPFN5ZFivgFFI2jB4Jx8QYE/GsREVRrRjmcqVSievNBu+5cj/d86EfAPaNYc+1V+LZhTN4bO4UGq1NRBEjAmFDMpStReI9hA1umd2LI+PTiHuCR7/8AB777FeBRoIYoQ7bKkFcKOIR0GCCFhFCyBlXFSEiw5SvlgwTqSoLYAyJ9YRYDYsPEv0hIRrvkU6VSsXJLOuOTF1zRenVb32dWfUJzbc2sNKsoxgxut7DMiNSwlixitnhCcw9fwLHvvFo+N5MHKAKLlgoPBwJbvnAPXjVu9+CdUqx0WnhxZVLyMSjEhm0U48SMwQC39/dyPX0KkDVWhTYYnFlE+l6MzXgpTTzqyY2PfIk6L0y5l2KVnQ6myRYq0tYAngbeO5flkp98Kw74Hln7ADonfHXY9x6K+F/JcZuNy6LwJe/6kZMiixFwUbiXeZA1LlwbrFxXeJa1bjkMzIQl6GMAKKLCPXghhBC/gXwUJSYcXJ5CU4E8YTBnpuvxrv+zt/Al37vT5EurcPaGFnmYT2gCfDYF7+BXft3Y+bAbnTEY7ndCKH/qoitwflmHdbGKFSH8db330Of3mzGS08d2x0XonrWkwuRpXmXUceQtlOFqEs4Eo0MbJxQEotjY0hhmEk1MjnzHClprIqYPGJrYJ0XddAeMW2CSUh8ygWTKuvoC59/sLp68VL8hnffbQ4cmNFasUTPLC5gs9VAgQ26InBeUDMWWdLDQydP4OLaGm4/cIhe/313485bbjMvfPWx4v1/9jnTajbjseHROPM+8h4mr6ZuK2kqZISI1XDIkUbAWt4SpwrqAdo1QKJEKYBMvDoQnHfwhqwD+ZAtJ5A0ijw7EfKsiDyANshESpZz7fM2APUyzXNgnuvWUyXJWH2JJHYsbLjYU+6Io44SF0QITGrEe1RKjrrGn8q6/mWTaVQXaw4khVK5XbZRUpvaVTB5cba8JEJukJixbVZ+6b//qutvT9VQvGIvymVU2Uuv/93uc3sh0Xe7/nfrmN/+WLpNTvLS6/UvXX5ZrlWcd9kqmBZAtpm5YjLsSj7rdkniDfLdIoAR1AoJNxqA+JLWygH4eiRbD9AAhq1VeE/1l+pXv9vXwTaA3Yy6WuuV2Lqih7VAqYtUPFkVp4jZMCllmRpYn0LYGELmjRCLh/WeU3VGrcsi7wsZa2LBNpWuGrZEkkA0MmRqqjpcKMRVl7ni8oWL5u3vvod+/h/8EqK9Y/jSyUfx4qnj+ObZY2hKgiIDaZrBGMKQMVhOUuwaGsIdB67ArtoIeisNfO6/fxrzDz8bOhNTwKUJInBemtPfZQjpIbnGXfvrK2IDKEFhYPJ4EIXGKlIUUMUwQYSKYI1EzGjG2KWxnW72OmOlmdHyuz/yftuwShtJGwv1DRApUlVYohBdF5ewZ3gUcSfDt77wAHy9DVIOxutCBPEJULR4/d94P65/y51YZ4e1VhMvLi3AqmKIAZdmiFUhJNDcLCsUDpsTQQpGbGMUVLF5aUnQ6fbYFC6xl/XUcxpJ4tmWFBgDsL7t2Ec6Gxmdx0o+lzAuA89RpIMGwp2xM3YA9M74XhqLAGYWtgPoBQDb+edRAO3Bb0UiBQczWeIyEdUUttCqL62sSatTL09W/VShqPPdNhFC8xqxgScgdQ6qCsuMlnMoQDFmLS6sryLzHjdO7cH0dYfwgZ/7Sfzl7/8ZNo6dBhcK8KkDYKAbTXzj01/Fu37sB7CrWkMrTdDOUhAUnhTVyOJSs46qMSjVRunuD7xTP72+We7MLe82heiKtOeft5S6jrMtJnYqntVKrOyLLFaUlJ1wFJtcrSiOvZLxhIgJMRPigKzBEHWG0FKhJCLqZCnaqr5HRTO5/OSJoc8ubxTueOcbzTWvvhGF2X10bmUJF9bX4cRDRGHEwTiPSD1OL13C6vombpnYTTftPoSP/72P8/fd/rr4t//Db5pnn3zalqqVqFAqReS8cUlKxpoWEXeJkDGMYyZRFQHYMSNT1RSqCZhSY9ixE6dgB8DBkCOBy0S8sUbIWB9UB6zwXVAvVrxMzZiHvBp++UToa4Qhh2oiJH3wHEVczBx3ooiLQUMPiqxQkmjK5NKuyUYAhwce8C9NtoAfTT3T5n0PPTBfiQp1cdkQ8lptyaUbQbbBW0UnpFAJggkdpCPnRUDQQZGJ5CkYfXTaJ4lJ8834HJb6vldvYFbs263yvOfg2svBVWCHVQni/bbHo4FGWkQHBsW+JltEtp6DKsDoP7P8/gPIYSJQ/vwHQD1/PpR3YkeFgh4/fTIzhXhZQQuSUqdWgDu1siKHJuvc8weBsTpGusH8WK14UpexTwDNc98H66OhSASOOM/xHsEINjPQKzPRrzA2gCa6IqUSV5JEmK0IkWdVhxLBp5kIO3FiMjBAQdYvgDjK1AGxgzjvJRKKWCPylqIyKRIvXoogGo9tNCHOjbTWN4u1oRr/4s//PH30b/4EyrUxPLb2Is6eP4unWsvoIIO1QFM8YkNIHNDWFNfN7sENs3sxXqrhzLMn8Y3/8TnUj18AiwWlHkYJJGFnYOu8oMGOA3JBEQMqIhBjwUSqIqpMpEoRE5VheQjeEylKJhTPFL3KuI3iWWFMa6k4fPe9747iqVFe69XpxNoyUp+CCOhmipgYFga7KkOYjEu4/9NfQP30eZAtQLMMHBtImiKaHMGbP/Je7L3tOqxThouNdVxYXQZ5DyJFywGFXKaUeg+bJ8gkAMRaqCoMKUrGIO1luHD6nIeXtmVaIZIGiXfUjUK4P9ZB9T5A3r7wNbo4j8uN6timfa4+ods3Y3ZY6J2xA6B3xvfY6KPo7BVoJtYesRaYVVPVHpECDHKa2ULcSpdWV+oLK6u1iWo6WojL8yJYF48iFJEQYkvwHNq9NrMM42wh3kG9YIQIF9fXYABcN7kLE/um8f6/9RF86ROfwcUnnwNHBkHMwdg8fhaP3Pcg3vj+t2FveRjHGhvoiQNzmBRqrDhb34Alwt6ZcXrDD9xDf/lf/mQkbXQPxUU7LW0bc8RZgbMEsYFbj9KEyFVKmapjY8hHYCpAHMCGADXsyaggyndwI0PEKqKqnADSFbFtA20gQVNBbWN4JplbHfvGH322tL64bG9685101fQejJQq+M7Fi3CuC4ai7Rx6zmMyskiTLp45fRLlzOCWqSvoLa97K1593a32v//+79Of/I8/oaWVNTs8OhJzXCgQIVIQhODZGPHiUyJyQpQByEBwBpQSKIMgE2anBBcae8WTIR+DxXsWsqTEpCBVEg7bBd0KgBTqhIKFb7jPL77stKi5nMj2nrQkJBzAsxYkJHoBYMvSTVUNk48sMuY4m0tT94qT6EdOZWufL6z+4j/6pecipauh2EVA5EP8YjD19WPdFBAKW9AgBm9DxUHiwX3xwzZWV7fkHbSV1WxMAEgifVMhweeRcbzNZLhlQOwbCPttedqPgFYVHxJqcstiyKYmUqatp5eXpiBP1wiexzzOToNeW3PY7lXykpeA3yTPnDZ5FbmHelOI2kMjw2u9pLeZlMmVOwkdmpzk3mbEUkhJoyHySYsl16cDgJY8aag2BBlW6hqt+4SG20brdvsew//i2MjX2wCQGWVjlIiUbSopyMcwQSLuSx7SJTJG2Bc9vPdcIGd87LsijmsikXFa8kLdpAiJBci4VogLMzGb2XajOdZrt4tvvuuN/Pd+4Rfw6ptuwWJ7HS2pY7PTwHpzEwyBdykyD1QMoe48qFjCHVccwtHpXSiC8cjnHsATn7sfbqUBCwskCrjcnNkPthCACbD5oseHtU7Q1RNg2ChCIp/mx4SZUPCqVShUiYoi6kwEVkFFDI07zXZlSTZ214c/UNh/09XmQncTZ+prSF2K2IRzIgFBBZisVrF/aBTHH38WJ7/5BIgs1HtwKYJ0Oqgd3I17fvyDGD28D5e6DSxvbGJubQXsHSJmeC+wIHTVh3pv5iDbUEVMBBVB4jyGiiWUowi9jRatzS+lYN50TjbISScuFgUd9/IpwVo10dJ3B8Lb2ecHdmbXnYEdE+HOwF8vE+Hu3YRul5CmhCy7zEA40y9S6WOjZhOo1YKB8CUmQrBh5YSdAyIbITapOlsUeA/EhqTVKlevnJ2ZPnTgUAuuvNSos/ceNSJkokhEMFwuYbxawWaawYlHTARRwIlHBYr1bhvdNIONIlSHh3DdjdfBE7Bw+tygmpmYsb64jMroMGb37UEnTdHzDgyFFwcDQjNJsJmlGC8VaXJygiq1mjn3wgnjPTbgsVhO9ZLNmr1hnchQrgtQFagjFhgXJIcRecSqvqBEBQYXDbhAqnGeDgEFPKAp1PQU6DBRh0AdySSxCqcCaOLs8okzZunSKk1PjtOu6Skaq5TRSTPM15uIAJSY4TJB6hxKZFHxjBv2HkTRg2oc4+7Xv5lvv+NVZnV5OTp+7FjMzFGhULRMzKpeDRlPRI4MZwrOQPARW8eAE9WMgBSEhMgkbDiBSmJgUyhlatixc17Fe0qNkhGlHmubCClS1JiRFvtUlRBZ97LJMvERxbGS+jIJHKsxZEWo5wnkCZ4j8d1IbKyu2xSnVcpGuJKtf/Wr/hUB9APQwuHdTKZYZcMHHNFeZip4JvJhexwwDAlhwBAiKLPCGqgx6gEVQx7GOjASYeqp4a5n6qihrmfqeEZHjWnDclOIGmpoQ4nXhWlVyayI4WUlLGWEZTW0AmvWHGFTmOueUfdEdSHUPWFDmNc80yVhWlDLF2HNvBgzL2zmvTGLaniZjF2D5boa0xDLbWXqgm0Ca5yyEY4jFQbEMshYkLXQEDsCWANYDnoBa8FxDM3zdNUacBzDFuLMRtEmmF4k1ROmoxvZ0JBLWi1O09RmqlGZyHoRoxmzFn2IFcwcSxaxxsyaWEKcoei9IgUyaxXcwHZjITUYKG0Dy6WXHLtSXlxqHcF3KJGYCoUMSCwBDrFhJVVlWDG26KxHlnmfxSWfJr6YqXOZjWMXNzNne5B2mRkuKwJmcqhcvlm9f9XKwqUjs1O7av/XP/rH5h//w39IB/bspeW1FfRcBi1ZPHH2ebxw6TxaksFBwYawkWSolKt4/VVX4ej0bqTrbdz/J1/As5+9H1LvhRzlnsAKowDeKuMJUHmwgPJE4LB40b7OngElJg9iTwQHqBoiWMAY5pgIJTJUE8JoRjqJopnspd2xa9/xuvJt99xl16XHpzdW6FyjjloUwK0guFBLtoAj45PIluu47/c/BV1vAWxABtCkhz23XIf3/dQPozg7jaVuCyvtOl68tICCOBgJkYkFInRE0UXQOKde0PV+sMnUX7CNVWqYqQ7r6vFzOPmNJxqU6Alk/mGb6EWrLqGqUUoZxAkoD9wIALqr84tG0eIwrxij6JerGINB9vPi4o7+eWfsAOid8dcQQH+XBI5W/3KQ3gug1oRKZRuAFtJORCpdBiIqGUvwDqRGnapSpKIA+aRTjCdGd19xyzVXOcu1zW7bdLs9FIiQQdERQaEQo1ipYGZkGM0kwXovReY9DAgpFEM2Qr3Xw5lGE5U4wnC1jINXXYmRXdM4d/ocpN0G2QgQxfzcPGYP7sWumSnUOx20XAYDQSaCCIpmt4dGmmKsUsa+vbOcOjWXnjtuOI7rXnRRZLRVIcrOL3X8tLXSyQAUEiawJaHYMmLvEWeQggEVSCVmZmuISJi8QjP12gvtftRT1Z4IegbagaIbi2biIWwMNxeW+czJsyYqlmj31ASmh2qImWm52UY7y1DMzYUFZZQdcHTXXuwqDaGxuEyul9DhA1fyPW9/O19z9KiZO3M2Pn3qdCGKosLQ0JBVVVIREdKM2XhVcqQqHPBlRswpQAmx9Ixqz3skYE6NlSwROGH24UCnSoaVPGuBOijkEXwFJiQ9pWDCK4UUhsskHBH12HOsCSkb1sSQE1YqsrLLxDCJReK6aezsiLjCinfnOx2PxcXvKrOvTNdibwqj3vnDAB303pdFxHjvCSpbDX4aUsWIGV5ERUSU4Iko8dCOF2kB2PQqm55oU1TrSqgraFOhGyK6qqpLCl1wKhdU9ZyonAH0jFecAfQcgAuiWADpEohWBVgV1TUlrIjqJc1vR4TTXnFSvZxSL2dUdY6J5wWyKCJrXrQu3jeh2oWgJ6JONNROqmie2gESFRLxhBCDR+plUPctqnDe54bGIGMBAGuMY6aWBxaN4RUi9FgSy+rKXIoqZaNlJl8UoyalsMjRHnPBqMngjDrPSo5JikoZgYoOaUYYoRKSbcdb47CwHhahbv7v/s9QVuGCi6gXRQQtEFDEkAghBRCnIFeAt6oFlCThnkcGRyWfxRq5bqLORpGPej1vVYWMQVYumygzpZFadVc5jq69NDf/BiO48Sd/9KOT//pf/Mvora97PbWbLZw9ewZJmqI6NoyG9vDlJx/BfGsdLQN01KOeOuybmsJrjlyFvcNjOP/0MXzx9z6FS489D8oINmNEiYeRUMpjFC8NKQLAUAiUFPFWQ6VCVdkYVVIlIs8hppAhYogpUnBRDZWIaahHMkJFO9ruNYdn77ih9JaPvM82TcbnNlZxdmMdw5FBL0thieHBiJRx9fgURhzjq5/4DFqnLoDZQtMEYOD2d78Vb/sb3492xWI9beP48iLOLi+hxoye97AAUhG0vCAyFkenpzA1OozlVhtZmqEEwHtB5gVtVewbHsVkqYYXvvkUVp4+vmyFn7WenmDOVoyyI2tUO0JEZVCa6nYA3WjxVuPgS9nnUklD9vOc7sTX7YwdCcfO+J4br2QkfBkaZ1ZlVrJWIEIcWaFeVyFClHEGNa2lM+frm0ur3fK+SV+wBaRO0FCHjBklDqwKmQgdIVwzPYPl4iZOr64hBTBCBt55dIkR+wynFi+i0+3iyMQuXPPaWzA8Poqvf+oLWDlxFlwsQuodfO0v7sM7P/oDmB0awcb6ctiyzDK0UocCgFargbmoAB6b1Dve/rpCc3nt8LkHHntdXB5atdLr1tt0AUAy12r5mZmZRDdhfSSRZymKkzIx+wJIAPXExntVxzpAOJkaTo0gIfFJ5tWFRjS0SKhJoLoRWXekGzaKZtPzaxPf+oNPVxeOXxfdcNcddHRmBkM2phcXFrDZaqNMjJq16CUOnV4PNo5QT1Msrc9DewkmJ6fw/nvebd5w5+v4E3/8CfNHf/LH8dz8xfLQ6FilVC4Vey4zzvs1JvJsyEECM+ahmQdlkUcmnGc/A5lL1RVJPUdWs8QIWQkVzZW+hKO7LZmBtf9vQu0lRsKw+BJfIopFSRLlyAq1WdsxhDskpgpvuqmabkkw08I73CSvfOxj9h/cfbfce++9l93XB3/5l+0zT32zutHojCVeSwjuR90qWMw1zoqgIw4xXCLM6hXBbkroMbRtDFpK3HbECak44jwGQ1VIkQpzooIuEVoEdBjaVqWuAKlV8mAlIrUQLSmZikIqUBQFiCBKbOBAmqiiCzLdiKgHVZfDiEgZUKECEffT64gHflom9CUb/dSQ0AcnFsoMUL+VULZF5XGQ7oCtBRsDMIGNYWNNJWJ7wBq6JSpGVQCbERkHIlEPR7HpFFWazaTbFNUeF7wXjjR2nlVjIs4kQ6IUq5L3OoQI4hwNo4b69uPthRTDGAZQRx3DGIY4R5LbGYe3GU4lL9ZgZ7xUQ5ala/RQNJGaYkGa3a6YUkOKWUmMiKJchs8ySgstMzQ+XB4Wu+v0iVM3QuSt77nnnls/9pN/c9erb7rFpi7DuQvnsb62jk7Sw/SeGXhS1LstrLfqQMTYSDrwxQJedXAfrt9/EFk3xTc/dR+eue9ByGYHhmJoNwMrwcAEb6AIfL+2feAXJBAFRlqwJftR5I2Y1FfeqyFmQDwTUaRMRQ8VpwrPbCS2Uc+l8fDhA9GbPvgu0zJCFzY3ML++CiseGgI1kHlBzBaz1SFMxxU8ft9DWHnuBEwcwzfbiKfG8cYPvBNXv/5VaLgEy50WTi4toN1uIoOi4TKU8vSjlnOYqFZxaGoS60mKqFhArVhE0u6GzD0vcAREcYRKoQBJHdbOXhAkrkEcL3LiO4zIgwTwQsEZu6FABDZGl6IVnX0lzi96Sb77XQMJxw5w3hk7AHpn/LUYf1WwwGVGDwPAe09Y+CtAtGGlLmsXiQBAxWcgZoWzwrG4qFLt9uYvtdfOX+oc2L/LjxdLOKOkmRIVnSBVwUarjf2TUzi2sIyWeNxyxX6MRgU8u7KC1SzFSBQhIkKZCFY9Ti4vodXt4eDkNPZctQ/v/akfxoOf/hKOf/NxUByhfX4Bj3zxAbzl3rdjf7mKs41NQD2KEGSiiIjx7KVFMDNdOTyJN33w+6pfbLRvWHzqWG+kOlxvJ+vJ/mp1Ya7V8qOlM+6SqybkbFcz6jC44kkzqDoiZF40JXgKxBRJMMpLKkopCaWWKPPig7yQpKWGG8y0HglW01RX2Jg9aKQz5772xPjqucXqTXe/1u49vA+1vfvp1PIKzqyvoa2CKoBu0oUSwRqDTAQrKyvIeimNjI5jcmICv/i3/k70nne+y/z+H/1h9Bef/Wy0vroaFyqVuFQoRpl49uJhmV3qfJ7MJp45SjPxqRAyZWTGiWMbSSreE1ul3CBIXdZgGuXvft74GgVj4TDUJ7Q9Ao2jUPvd0aKPInjOWCxlguExuHabF4/V7eLKqRhf/KL54H/5LyZ/IAPAII6LqBbGUC4dBNvbiXBUvdQAmJAPJ4D3W0LkLRceg1igyqFUcoA1i1AaAsEFClH7t1WIdzDGARQMlypBq6BIIJIFvEQEIAKoAEYRQSEeD1pRoAKFA5ODaAbvgq6bDUFhwRwDUgCoAKICRGIwxQBF4bteLcgYABY0qFkkqPRz+F7yCabBJUUWHBlQyLa2xpiqMXylAhVRusqCuhxywR2AdurdilM9PzIyPGer5dWU0WLAKRGDMhCIIwCZYSXDKgUv3DZaRx3woOFcB7/pHDmfUBNADUU4JNCyEHW2DKacg+hmobu1y+BCWgeRUWJWG29IoRWpSYYUUbhK1ulw8eBotAeztblzp/bNLa3c/pY3vfl1P/ljP37TO9761l0WKKytrdLq2hrarTa8dyjEMQqlIlIILi5fRKPbRBJ7TNRqOLp/L47s2YeFMxfwzT//EhaffB4QA6MGyDJEuTnVaWi5VMrNndCQRa9hdyNo3CWvhg/s9FakIsgpcTC4Chs2hllVADUEpAQiy5yRmGhq1Lz9o/eynRymheY6Pbe0iEg9lIC29xgrxHBOMVKKccXQCM49cxzPPfAw2Bj4boLdN12Duz/8PlT2TuFit4nVdh2nVlfRSXpQKKrMyDKPTAQZEQ6NjOHKqUmcu7CAExubuOu269HuJmh5h0wVVWvgAIwWi6gUy1i9sKIb80uOPOoqssSQLiU9QTGGOk8Eo+JqxNuywecLedLGS8f25I0HHtgu3dgB0TtjB0DvjL8m44knFNdc81cC6XkAs8bofK70m+63EfZZR2M0zICslLCiJNQBQJGVFoBS1hUUhxzam73VM3O9g6++3o9XaxgpFtFptUB5JnSWpEiSDFcPD+PBL30NtUYX115/FSpRASfXV7HUbqFoDXw+AVQs4eTGKi512rhxegZ7Ridw90feh137d+PhL9yPtOtx4cln8eTkCG544+1YbbfRyBxiEDreQyAoqOI7c3MoHbS0f3gCb/qhd019tlG/rX5ycWNofKi9vL7RA3jzBcDNWO9amSZFjrpeom7EruccEhWJRcVwXjtHlrx471SRsqFUnKTWcGaZMoE676GG0EigG6y6VmC+5L3Mq7V7DOls69iFmYfmPzU6e9u11etfd1t07fQuniqXcGF5jVrtHpIsC3nFRGA2KNoYnXYb3VYH3UaDJqcmcWjvfv4Xv/SPow+8/wcqv/V7v2u+dN+X42ZjNR6bGC84poJz3pKKGLY9IpCHCEfI4JAx4DiKfCreU7atojsH0W2zLccVW03urdw02AhCCwAO1bKQpLkRrRti77qInJXUF4pwcRaJb5Ypqy2xY7U//JEfqI2XxybAOlOM4gmOuCLOx2w4gmi510vGer3eXu/cYZ9lu71I1XsxIA5aVBGEvpRtdj4iiCgTgUXUqkikKiVjGc6rMrF6kfwWRHl6hkpwFAoReVX1Cjgm8kShz4RUSQADVauqBoAREbPV5tKPMxsEgCgzQ0X7QSCmv3dDuWuxzyTnZkAiZs2biwb/50VCgogipNjkYI0o1EiDDZT7DCiFznPmApGZsoZGlEwGwBtjPAEOoA7HdkmAk9946MHS2YWLJ4pDNU1c2o3Rtw2TIgHiEmmWJMqsAg+poZKzyQ5176kGQMtCVQDh+6Eaoj3KXfRBdN00lVtWjSkMIhA52lQO/fNqmBXNMhAF0JwVi2aiVIpH9k7W5s7MTT0+//zBm667/rp/+n/+v+68521vv3ZiaGhsc3PTbm6sU6PegM8cbGShyjDGAERo99o4O38BmXhUyxXcfPggRktVPPbFB/HE5+9HurSJyMSQJPglWDgonDW08Xn1+X0xvAicV1A4avBeYIhgmZA5D2WCpZBG7kEqpBz2RxQCqPMKY6AOSlyMqOMTkkqJ3/+xH6LyvklaaG3g5PISbJaCochUUTCM9V6KsbiA/dVhNC6u4OHP3QdttqGFIm695y149dvegJ4lXGxs4MTyJZxv1DHMhBEmtH3I52/7APQPjY7i8MgoLp29iCe//DXc8X13g8HYbLVRyV9z1wscEUZKFQyx0WPnFzRb2ewx2XXq+ZVMuBebYQW6QANQeCJ+SRLPubDEfEXgXCopqtUdwLwzdgD0zvgeYqGNUWxjDQcgGoDHbiBaUMkmiY1RrXtFhcP2PndUpUxgVrTDF2cVYf4kFQ/YbO6Fk8n1a00fjxW1Vixic2MDMROqzGimDi5JMDW1CzO1YTz32a/At7q46dW3oLR7D06tr2NucxOsgFWFF8WQNYjU4eEL57C/1cQNu2Zw9HW3YnLfbnz7y1/HhWefxzNffQiFkRquu/4wvr1wHj0FhplRTzNECK1nj56fQ3TA0J7d4/qWD71n/Av/9ZN3Ny6utWqlWrsM97zdHKujsK7sUu9BiTC6MXNHoCWBxoYtAc4JPFggSuogyEiQWsMZCJkoJaJwRMYpRFihAG+KyAoU80bcKZ/4aWP4gN/sHpr/2uOzSyfnRq957S2lo7dcE9Wmpnmhu4RerwcGU2Rt6C4QhTUGpIpmo45et4ONtTUan5jALVcdjf6ff/kr/M0PfMD+3h/+Yfyl+79SdYJaZXSkOlQqx71uByIuUUUzZgYMi4j3qaqnzAiYlUwSjm9OPFdRBaGLJoBaK/ytmZ9IjW3nTLXiSRKf478mEbNyoSCmSb4w5V3F1f2pFuTQ5CR3G2yNa1b+9k/8rQNX7p69zSjdzkxXETBOTAUEWUMuSoCl8F1oXxK/PPiFv7vufxCd7F8hC5pemQq77E/6yvnMfcROeTjDIPqZvgurRtv6WOgVPoh5yffgtdBLMqX/V4ZgEH/HCsT5+6ZbtSsQD3gBRtvw1cXFBTx/4kR3bHy8S12nZMRnAKzPhAsRfJaJRpGXHjGVnUonHHsVCeC5CkiaMVCBilA/sYfhhcDatG3lVqxcKIittELt93qkRobUoKDRZEmzbpfSVosTY+xIpVIsTQ/XNhdXJk587Zn9R45cff3P/vI/ufX9733fVftmdk+1Wq3i3Nwct5pNuDQFUwDNWZZBVDA2PgGOLNLUY2VjA8PVIczMzqKxuIm/+NJnsPD0MaDn89Y+gREKi5J8hdNvuGRsvWOEUKGdhx6GshtjQnFNbEHMcKECnkIaM4fEQWYlQ1BlOAZ8TNTTlHw5xrt+7AM0cmgPLrY3cGzxAjbabVStQdM5lIxBxBYRCHuqwyimDl/48y+gN7+Asauvwhve+3bsPnwQGy7D2eUFnFpZRiPpocoEQwapC2VSS0mCoUIZ145PYLpQwNyzJ/DY57+KytQ49u3Zg4XNBiTLEFsDhiJxHs5GqBXL8Klg+eR5j07SYC2ssroNsKaEVKkdqeLyuEO2Ns9//p+B5wd2qrt3xg6A3hl/jcFzqaRIU/qf3WAewMzCwivKOKjNqiUOVXLt3IzYArQkBBVKmwm4WHCdc5d69UsrfmTiCkyUK1hAYA2LzOiIYKnexOzYJA4cvhKXHn0GL37pQfTqbdz4+ttx7eQMqnERzy2vwDmPMjMSUQCCiIEzaytoJl0cnZjA7j0TeNMPvhvPHdiDJx/4Jh77wldQG6niytERPL+yDMdAxRi0U4dIFd518di5MzD7D9L+oweiuz/07okv/tc/ubvXzMiWI6131k8UmtUGvCeukKeeSzKgw9aUNUPEweMViWcQkyeoM4YdqTpPyAjIRNVZppTUOw/NSMTncWZQtQTxMRMuqvcXFHZOVQ9mZxcPPH3pvj0Xj50du+W1t5Znq8Ox6yTMKoOt4n6RNRPDRgbee2yur6PdalFjZFRHxyfMm259VfGOW2819339gcLv/MEflB994vGRbqM+WhsdqSmz9aouS32PDVI1NiswUepVB4xSp48i2ttUFUCLWYeN0ZeBP+9J8uIULQmhDZBJtJ0UJC4ZqbiL/lR3j8cVUxrjeaq0xmw98RO+l766YMybO83WdeL8KBMKhg33uVkChcrqPkDMTYP9rfR+lJvZBkeZ825C6iPdwOayyUvuNDTQBKTv81ZCszWbq5IxnN+cXgZ0+0UaGMTWgULGcx4OTCGZWXNJieR5z4OqcWhoK1QMMqBFFOCtdsOQCx1C95iCZEAHDYchS5qQ50NrP7ovGD0VAIlSToyz9jvD84pzUdVSuWy9eJ90O02IXxT1a5mmmRFOxBghigVpCjEkcWq8i61nnwgEqDFrA3nsXVoiFUsqjrb7I8JSOgGarFwJ4DlqlgUATLUweKt7m5uc1TpcKA3FY+Plamu1vefEE89ftXfXrht/6e//0tEf+sAPHrjq4P7Jbq87tDA/HzWaDSS9BAQiJob3Lm+YNGAhxKUiRDxWV1fhugl2D4/gma8/ime/+TiSSxuwcQkkDEl9qOAOrD1I8/fZS57vTYP3lQHYOEbqHIgNCnEBzWYTtVoVXgVOQtlSaIcnIgqAOhwGRcZKzgBkgUw93vKh99GBV12L840VvHDpIpaadRRyuUWZDVgJvdRh79g4JqMC7v/UX6Jx4SKuf9fduP3uu2BHa1hqbuL46gourK8hTVPETOiJoEoWHe/R9oK91SEcnZhG2Qle/NZTePb+h6CtFmbvfBUqlTLWlxfBovBO0MpXfSOFIiZKFSRrLSy8cCqDxxKpLjCoAfIZmUjR3yV56Xwx/11iD0ol3Z6qs5O+sTN2APTO+OsKosMcvZ0dyDLCS1vGckZ60RidgX/Z9yUZo8Si6rfwhZYkJHtokWISUhM56XY7Cyfn0smrDuh4tUZxXEDa68JkIbau0e2h2+1h757deGZ8DJ35JZx98Em015q44x13Ye/YEEozEU6urWCl1UItipA6D2MY1cig3WnhgXMtHBlv4crRcdzypjsxvncGj37l67j/c/fhrfe+E4fGx/Hcykpenx0MNVVrsNrt4uGzp1G80tK+m45Gb/jQew5+/ff+7E31JJFitfIN1+gdiyO76ZXUFtSRQ09F2sxkFBAiExMBpOozz45YvYA9iXgyxlmizGfOkTWOnMsY5GDYk/cCEY/YwGduUy2vW2NWXOoWlKML1JMDq99+bv/Xz1/afeNtt04dvnm8TM6bmJkcKAeQoXHR5xpNYyxUFMtLS9Sob2J9eJhGx8fid73xTeau1742/uxf/mX1j/7HJ4afePqZkSi2I7XhoVpUikq9NJtD5ldtZFqJyZS04IhZ2Voh01UykfbTnqkTJBlN2942gQ5DnaPaECBJYCa1KVtbu6aptmYlPhMrrp3Kz7Fr0ZZTpQiyxxJujsDXrywvT62trJhysURQVWu2zGcKkOEckBJgyICZwZyb5hiwbEDEYCYYY/OCkvB3qAaTHVFoiQPBsIFhHRjE+kCac3MrAzB5qgXlKF1yhEx98xg0lKzkAg7VXGJOee225M83l1+EKm4JsWgUwLRLHUQF3vucQQ7gOIBqGYBw5wOAVgVUHJxz+XsTnpdzbpBGohoAef4Y5LwPCdIEpFkGYwwdOnzYRnFUJaJpZrNLMx3zoDqCNsU5ZAJmtRkZ8ZkRVVYKOeAqQtWSJ/UlEhc8khKFSzKslLKS6aotpGKoNADPphCAs08S8llGrtrlkh2LJsoHq941pk48+eKhkVLpur/5wz983d/4yEeOXH/NNXt8klWXlpZ5fW0VzmekqjBMEK958kj4QvMiiAsxTByh1e1gfWUd6xcu4Ym/fAbnT5wGYBCZIqSTgZlhty+P8u2E/vtN+R6Cih8U7qRJglKphEqxiPm5eXzwBz+IoZEh/LdPfALDoyPkvYeoqijADPIUClqNNWCjoEjRS9r0uh/5fhx5zc2YW1/Cs8sLWGpsYMQadJ0DASixQU8VlWIZu8oVPPCVb2BjbQPv+NiPYO+RK7Ga9LC2eB5nlpew0OtiMrJgJqSBAUc9zQC2ODA0hGvHJmC6Gb715Qdx/pEnAOdA5Sr2HzmMZreHpUYLrGH7BCroCnCgXENMVi+enpdkfqVHyhfV6wJ7bStFnnpGOW6quJDTxM2mcrGoS8i3LBdfwj73wfOWdGNH+7wzsBNjtzPw1zTKDlhcJOzbByQJXZbP2f8RCegjAE6qNZRopAMgZEKj2CX1MWlXCIUUEBvux4YIKxCzkhYsm3En6d7EYO+Rm68ZstUyr7aatNlqosgGBox2lmGkXMFEbQhpO8Hy86dhOEZrcRUXzl7A6Ngodk1PYrxaARNwqdVBOZ8sxIdiFgvBYn0Ta+02es5j/+wuHDh6CIkKnjx1Brv3zECJsNntwoggJsKGKCpE6DqH+XoDE+UiHTp0BVfHRobOvHB8r/SyUqFcBEnmMlFxKQGsZGFYwyQJAyteJANxqkSpU2RGvSNiR0KOAKfiPRl2xOyEEcA1IscqLoNzRSpkHpJq6rvEVCdH64Z4TWHa0k704nMny1NDo6V7XveWyDXb8N0eRZy3KxDlK6KtemFmhvce7XYbzWaLer0uFWxkbr/hxviee95ZPnTlFUPLl5bG5s6eHU6SXmmoVjOFcgndXiKwkZcie3KZGEqlnUSSiVXyJvwwI2hYk60mQu0RJKaIPUOVVCyhpESOwDHEt9jbFuRsFHl85SuCF16g4X37TNJqTKVZdssPff8H3rR7cupgvV63aZZSHMVkjaHIWmIOOmE2HMreSGGMAbGBsRHYBPbQmi3gzBSEH8QMwwRDHH6Myd+fHDwbA2YDa00OchlswnWZwnWIecum128BJNoC1XkmcNj6p1DckjPGhAD0qQ/EczFIP0OY+sUrisF9Iu9ml5xpDprmLdEHm8BW0+B5BDZdOafh++w45znR+flBRDDW5AA+pHiMj4+DmOkzX/iCP3v+/FqlWlv1mTREyINzybVnJSuiRr1q6lhLSoUMiJTUSzjWqiSRY5UCQUO+s6FIOo69c9ZHvZ6P9HLw3GW2plQq7R7fN+w6nd1nX3zuqrTdvf0H3ve+N//TX/7lu370wx+5cXp8fHp9ZaW4srzMjc1N+MyRyV+j5mw853pnLx5KhNGxMYyMj6GbpfjN3/otfOkLX8TaxSUYjhBzBMkEkHAMmAC7bXdB8gKbEBfYb5sMwNIQoVwogrxg/dIqfvxHfgS/8Iu/iN//b/8NG+triAqFYCokJmUmkJISSAnkDMhZUE8Suu0H3oGb3voarCcNPL+0gPMryxi1BqkXVPM67QyEgo0wMzKCx554BhEY7/nQ96MyMYaFxgaeXpzHiUsLUJ+CGfAqMKroKiNVxXi5gusmp3F4bAIrZxfw4J98AUtPvwhmC6QOU1cfxi1vvBOLrQZOLy9Bnc8TRQBlxtUzezBCBTz/lW+lm8+cWjVinkQmz0DcosmKPWb2m5HTis2UbaacWV2NY0W0oliOtgyExmzJNuI4xG48MLfDPO+MHQZ6Z/y1l3FssdCvJOWIIh2UrLwCC011VlRYOYpEOGMwq/YzpUVIiQhg6aauiyhab5xbaF04eS7bf8f1ZtfwEC5eWoIThfMO3nssrq3h4MQk9h25Eseqj8CvtcHGonv2Er75yb/EVa+/DdfccROumdqNsolxbHkFLklRswap9yANE1C93cLTnQ42W03sm5jALa+5FcX5izi2so6j0+NI0gzdbheZKiIvUAFqTKi3m3jw7BncdSXTNa+/OXbiph7848+9udvJpuLITGfOPVktxJd8z2WCLFMyXa+iopJaMuzIKyuLAELMSt4rclkHWZODZhEYURgrpE4SOCVnhYwICXsy4iIbpYn6noDb5NOeiQuSdbqVxqX1auypaMiYvhxAdasKWsH5tn6QOlCuhfRZhvXVdXTaHWpUh8zo+Dj/4LvfE73tzW8pfPEr91X/9FN/NvXYE0/ta6fpC1Mz0y+YYuFM2m4ttzLboCKriigZo2Tb29oHcXmNt2ElWLQ6XiuF3GTa2zIWkTHBJJZttVn2apusa2aIyezLnIwZICYiZFlGffAq/ersPjDMGwBFAcPB5KVqBvIG4gAQczoSzAZKQfJBxg4qskkV6LcVGh4Ig5HLQPrBHKJhG58Ug/bC7UD3srrxQaVz3mQoMpBavKT2cEuGsV2OodvkGZIz17lcxXuf35/JI+wU4hz8ttsP2GkRQASSM7KD5wbAeQ/vPbJc8iAq4HAiWXFSEtWyACWOOWVhiIiq9wyyFBZJBVIVUl/K34Q2VITEOVZT2PpuMKzMqRCqYgCJmAfgubcRm8Learw79pXmcnP8mUce2T86XLvhg+/9/ht/+MMfPnLHq26fLlgztLG2Htfrde52O8E6m5/PKn7QMmksI3UpQIRiuYxytYqZvfswN38Bv/Jv/zU+89nPICoXUIxK8IJgNu1zznmroN+mPCfty2dyHbQEapaJUIwLSNptFE2Mf/iLv4i/97f+Lv7yoQdw7IUXUK5WkDoX2ivzJj+Xx0I7A2jRoCcJrnnra3Hr21+HDdfFdy5ewOnVZVQNI0lD6kZm++DZYLhUxnyzhZmD+3HHkUOodxMcO3MKC80GEpeiYkKkTAQggaInAJsYB4fGcHR8CsMc4eS3n8Pjn70fbmkdHEVQ76AAjt58HUypgIX5OtIkQ4kIbQkdRqMjoxgtlrW1vKGLL57pQrCkQhcZukaIM4p6UodT2EhpLZdLGaPTAJail+xgbpdtXC7d2GGfd8YOgN4Zf81B9BNPKG69deuvf4Umehb9ySZ8YXrviW1TJa0QmgAqHYUU8xIFJRgAaaZGtW1KpaV0vb4y//Sx3Vfecm08WRvicrFArttFrIyECa1uF+vNBqZnpjBz+ArMX3wCXAigxy3V8fznHsDq4gpuf/NrcHR6ChPFIp5bWsLFRh1jhsMWpPcoIUxic+vrWGm1MDs6jD3jY6jWqminKabLZZzv9tB1HiUQHCl6IihbRr3TxDfPnsadBw7S9XfdFlnDU/f/wV/c5LuuUChHsU/1KY5onsSkMVGaKoQyREwI0gr1GoHUkxcQKXwmpNYRGyFVnwkkA6QgpOFTXQDg0QNQJFJo5HqSKTEJqwqbOGLl0Yx4tcBRhxRiQSZM9HlxRr5FFRi5kNJhIhO2osWDwbDWkHiPjbVVNOqbVBse0vGJicKH3/u++Pve9vbyVx94YPiPP/WpyW898q193RV3fGRq7IXhUuFMp7G5XCybVsRZ1vHD/vKsZwZHVvtVzYImuCDSToqoFBKoLxGZrraTolhs60e5917CmTNcnJMos9GQFdltgAoBgaPNJSmGTV9ZnDOmCmNtADq5iAI5g0sc6FLdpim+3ObHYYExyPDNt+7zCGgRBTOjn7EMDhIZ3sZObmmUtoHl7b/nWmVsY6gvA8l9YL/tb9QH/pRTldSvDvd5FjTgvc9lGRRS9/oSj/z2mssOtoN0ZYJ3frC46gN6LzpYQCgA8dIH7GSYLNTHDB9ZZyOn3hvywsZmqkrhXP0uPTcloOTC4rnLiRLHahIjRrpivRdTrapPEqpMTdlKxVVWF+amVjYbR4YrQ9d+9MMfPvpD9957xR233jobGTPWqDfilc1N7nQ7IAKsYTjxCCFw+fMnyqunPaK4gLhYwMTUFOJKBX/x+c/hn//zf4az589haGICXgXqw/sIa4K2OW8P7DPx0GAQRH48jDFgFTgviKxBbCM0V9Zx5YED+Ff/4l/itXe8FquNTdx3333IvEfBGkjiQEwh/i4/f5xRSDFC6rq45m2vxevf/zaspR0cW72EM6trmDAWaV/HroSuE4wXixBj0MwyXLVrGpU4xrPnzmFhfQONXg8ERYmBrhMUYguLIO0ZrdZwdGIGM9UR+HoHj339IRy7/xGgm4Gkr5FPUb5yN6YPH8BGp431ZgsRMSImeO+QimBmeATDpTJeOPWs7y2uNMhEc/C6SF6bpM5R14Rc+DVgzRidzM2DHEU6i+CZuUy+0ZdtbMXW7QDnnbEDoHfG99AolRTd7uWa6FcA04sLALCik6Oj291aSsyqEAqhZsUwjyesFMPHlLWd84tQnlt4/vSezfml2tje8XiqVsNco4HIxohBaHa7WN7cwPTwKK685TpcfPQ5+CTLtagG6HksffsZfHV5Hbe95TXYe9UB3LpnD0aKMc6uriFNQ1lApIqMgdHIgp3DqUvLmFvfwJ6RYVSiKEw2cQGrSXDss4S1RApg3Fhstpp45NwZ3HngIB2580bYQjz61T/8i2vTjbZwqSBWvIDsklVJ2CFTw8LeG6iliIg8eWUYdSQCREIqnkCSGS8EL7FjhaGt91mFoEQ9IoUqFVPWrnEeRM6JT6tcSrqKhMR7ytM3GJx3fwQw0AdbARwEABYKHDjPYzBhUucwWbcaDeq021QqlzEyMlr8wDveEb3tzW8euu+BB3b99u//3r5vffvh3Wr42ZnZmWOJk/lO2t1waHQthjIudqUPmqlhFAZAAzAwqkOegB7aSRHVckrUiZQKbSWpqQk7GuE11+vcu2LCJutJNRIZV5XY5OCPQUGakzNiRCFGjDRnBA3nQGqLDQ7ggGAM5yRwX2KheVEPg1QgPsg3lHQAXtnwZRZBQWBxbS69gAbWsg/kt0oztnTRfY0s9f8fLyscGkgOXq6nCkxwn6mWXONMtLUg0G3X1f4GEjEgOeCnvLsDCu/lMsI7GA9zg2K+5KJcQx8WWQLvPOCFCGQUiBy8ZbDNhJ2BYZAjXPa62i97HV1OtG8e5DSRZoGkuKHelMvqk4SKIxItn3pupNnoHDh84OBNH/3AD932fe/6vuuvv/rqveU4rm5sbEbtVpPTNFUVBbOBeAdRP5Cd9BcHWebAbFCplFEbHcXIxDiOnzyJf/3v/h0+95efB8cxRiYnkbpsgNgMM5z3IMOD/BPNc0kYgDEcElqIoM7DQ1GwFj5Jsba8hnvufjv+9a/8K4yPjOLiwgUsr6/jwW89hFK1AuccjAngeaCVZ4KPgcwnOPym2/Ha97wZbXaY21zBcwsLmIotvA9xdTUKj50poecFwwWLkWIJa+t1PL6yEpoGFYihIfrTA2UCktRB4hiHxyZwcHwKY8UaVk5dwCNf+AY2nzsN8iEOXZ2A46DnPnLz9RiemsCxpQWsd9oo5jp8IUKxXMHu0VH1vUznXziVotVdYyqdRZYuk+ceZSTN8NEHA1izVsNSdQkmikJ9d79t8DLm+YGXAucdEL0zdgD0zvgeL1XB5Wkc2+OKxHtFHUBlk8gMKbEomBVdVhRElXsKx97FpiOZW4pLpeO9heXZxWOnd109O2X3jo3yxaUlYuSmqMxjbmUVu8cnsefwfowc2Y+N75wAcwTOcvBDETpzS/jGH38eV7zqOtz42ltx/dQejMdFPL+0jM16HTXmEHeXZlAilACknR6OtzqoFQvYVSkjAlBUIMvCVrbPJ9OGKMaiCOvNJh46cwavPnAFHbr1GmbioS/9waeu6zaSbLhW9dRInusKrTLiXgSnMMZnmVBkAa8MIpHIsHpWDxFPTrUAK/CqGTuBE02EtcAAFYAk1eBaA9BTIUhEEXn2Ilatj+FRdJlaBuWJATqIbVORYE4TQRxZRHGEpNeDqgRNrjED45kxvPW7CLqtFpJuDxsbG2Z4ZJjf89a3jr/x9a+vfuHLX9r1yT/94wNf+caDe9WYp6b37jpViQpLGxvtlnVRYkYz/0rnCDWMohRMhiYx2iy0lbux2LGWRKajwB7F8jJhoseuYw1zViClkqpa3cbiqioMcQiyUB30l/SBKBMPdMVEugWaNb+OSjATEgdDn0qesHE5wO1rkLcYawaUYJm3MZQBzF0GfilssGxHBdu10tvZZe0btHLWfCC5Ud22l903/uWvhQnq+4AXYQGRg2GBDLTuud0tX08o1Ae5gZd8gZA/Zwmy375kPtxPbjQEIEzkRaHwyipiDVnrVIxRNaCUEBIFUUIX6SDvuz3I/d6evMGZFRYW441w5NVnGVWMseunN2pHj1576CM/eO/r3/SGu956cO++QwYYajQa0YWlJZP2ehDnwdaGKJM8JQUSFlRE4fMqIiiVKxgaHsb45CQ2mnX8u3//f+O3f/f3sLSyjPLoMMCMXpaGXsc8VcNGEVjCIkwQACMrwHkiitdgyg2Z4gTLFlmjBQbwj/7+L+Fn/vZPod1q4dTxExgaH8XXHngAK2urKI8NI3FZrpcO73miAkQWWdrC5M2H8ab3vxVJ0eDEpYt4dnEBo7FF5kOSTEEpxFICYBIg82g1Wzi3VkfmBcZnmIoMet4HSU7QFqGhguFaDdfvnsXMyBgiB7xw/7fx1Je/CVlpwCCCOAG8BEtLksLuGsWBm65G26c4v7oCyRw0CsVMznnMjtcwUR3G6vHzuvT86TZRvKRJdoHBm0Sakk0FsiXLmAawhCXMRKz/C3MNdhjonbEDoHfG9wp4DpdPVIFbWzRgob/b8J5mAGA3IH0p6xjA3qg43hZpZ0VZCKxKxnoW9EC6BtVT6KT7jj381IFDr7qhsGt4tFgpl5G02yBlGFK0mi2s1jcxNjOLa+68Gd98/hTIhzDbSAhZJwNiA7guzjzwONbmL+H6196GXVfuxe2zBcwVSzi9tgaXpigai4gA9YKCNbAAWq0OLnR7qFqbbwEH+UMlB22pKjLvYEFYq9fxxLkz4H0H6IqbrzL32HuHv/z7f37N5nqTy6WoaHt6HCqXxHCblVNyTp14JYGSJXUiAjGevEomXgqApMZo6kQLeYxdkkeNFfK0kwSAGmMiRSTGFlSyMlSHSHVInC+IKvd1zmLsS+QA4e/DwxPISiXUG41cMxxQEwGw1g5SO4gIURRBvFCv00bS7VB9Y4OGRobND77nvYU3v/4Npa8/9ODE7//BHxx8+IlHnzCF6Dszs7OnN+vdzazOXSviqBC2bgFAsozUOTLdgqjPtA2AqzFYChI1I4kbTjGJXA40izTOOHJMmilJn2WVsEDgHIwOygURmGOmLR6W83g7CnLmrWBlAEQMwxy0zlBAADUBTOmAtQbY9CX7Ehh7AkKkBqCkA4nIZaYBytuLVQfP0b8C89yXZiiFRU6QjnCQYUhf6yyDRBGQwomERUCe8EFqwIZyVlny++yzzSGyTuAHsKR//0IU5Dv5cyXq67j7gXs5bFdRELwyZaIiQfJL7EgMAwxjCGKgqqTS4Y4q2aDxJaAUFjZ5kRIh7ESxTcRoWSACyTJy1Son7XZtaLhy6Df+/a++6forDr0tde7QxurqULvVNi5NSbwDsw0adh+SuokJhi0oP19FgGKxjLhYwPDoGDiO8cX7v4J//+u/hke//SgKo8Oojo8F1tkHGQaYod6HRYOXwdfeIEIwhAXmZxQg3iOOLIwoGiurOJRLNu56w11YnL+IhYWLGBkZgQC4/+v3o1QpB419/o3KFCRhMIRUUlQP7MZbPvQe9GLC3Moinpm/gBIURTA6ClgltL3Cq2CYw2KwkyUQKApgDBmLVAzqvQxOBIXIoOMciAgHJ6dwZNcMRko1rJ9bwne+9m1ceuo40HUw3oDSLP+MCGAtVD1mb7wao7snsdisY3FtDQQg6Z87YMyMjiH2jPnnTjpZ2Vw3ZOeN+qWI0PLeu3ZkZNhfrnOeiVgXF4BZA6AYvTzzObDPO2Nn/P9t8M5bsDP+fzqeqOormj5eMmRSSLJJEpfnva5fHmnHXSswHaXEClkj5J0nQpoJWpLqAtic3Dx59vTSyXPtkinooakpdJ1HTApDgLoMc4uLaPa62Hf1IYxddRDepaGGNnWg1AO9DNr1oJ6g/sxpPPRHn8XT930LtpniyOQ0bt+7F9NDQ+g6h1YWYqGM94i9YIIZZYQtYOc9ElFkEtgnpwqjAXCXRTBlDFY2NnD/ieO42NigK64/ZN7x0fdPFnYNX9NG7zVSK96eWroqE5lyma8WQg0aEZHCkcKzEGWaeS9kjM+s9yTeg1lgjBSYtYAEscakVlit5YjZRuSsahqr8yX1OiQeIyo6rCoFQ6A+U9nffhfRga43SVP0ej2MT0zg4MGDqNZqMNaEdmnVQRaxNSaXSchW+gQRet0OLS8s8rlTp6KYeOTdb7/nyt/9rf96+7/5l7/y1umhsbdeOH36VbWh0qxxrpoBkSRJ/t20Es6BvGGOjFEyRrnTkjhJvCkU9IVXOLdERJzziQI+7CQLsiRBlmZIsiwYTJ2D+BTeZfBZFgxyXuC9g0hgJGUQ7xZMqc47iAuGOWgw6IkG15j3ikDaU66N7qeYBPYwACKBH9wGuX5YBiUlkhsb+y+on7jBfXi2TfdMA/lH//+2kD5tY4c1v7WIH2iWt9jmsDhiyvXL4hFSEB0kNwaGSwfnPHyWwqUp0iRBkibIshQuyyCZQ5akyNJM0yRRIvLEnFk2CUSzPHfaMJHxyqxO+6sNAoCiFmhgFL58R0rYWjGFzBtX8Cav686KRTMzPl5ev3Bm9mM/8Tdfd9UVh+6qNxtXL16cH65vbpgsS0ihMFEM5bDY8Cq50hsQUSgxKIpQrlQxNjmJPfsP4OzFi/ipn/lp/OiP/xieev55VKYmAcNI0iTkx3FoDhTngxxGc0mQhDQNQxQWl2GlFI6tKqqFIpB61FfW8IH3vBef+4tP43V3vhpzp0/hzOkTsIYxtWsKX3/gazhx6hQQRcicH6Sh+P5uQUTwRvD6970F4/umsNbexGPn5lB0DkUFmqlDQYLGugrBeH4iJJlHBKDGBkUCukkC4zwKYJAoNrsJhktlvOrgFbh1/0HUJMKL33gS9/3WJ3HpkedAPYAzAnpeyUPJqTIxnM9gJodx4123QyPC2cVFpL1OaO8UD/GCkdoQ9oxNINlo6OlHv+OQyaom2TxlssGeexRbX+2wghtKdVY2JsTWYTdgjM73I1BfKt/YkW3sjB0Gemf8bwGib23R/yc3IWMUdYCHmwBGVdKUqS2KIisSK1RiVecULoNjuxHbwpm03njx9OPPHZi99lBlz9hE8XhlAWmnQ8FVb7DeaGJpcx3jM3tx9atvwjePnwNnIVGgAILJFM4JKCF4y9DNBCfv+zYWjp/DtXe9CruumMVNu2exUFrH+c0NrHcTxACGDKOd56waIsR901i+/d7LzYdlhC3NjgiGDaPV7eD+F57HG6+6ivZfd6W558fuHf/yH/1FoXl6sVaqVEayVq8mJOfZp6sEagn5hNWEfW1HSsxC3glghAxpcWAu61GSAIVICBqRes9qvFGwVdWYvS8rUGOVEQBVBkWhkC9vQ6N+dq0CIiDDsMYijmO0Wi0sLS3huuuuQ5ZmunTpErq9bgDdRMQ5+PMuaElNX6erQY+bdXtYXliguFSMytXq+I984IPlV918y/gvfPzjkw8/+sjQkaPXPntpc/N8XCw20lYr4cLIZe4yyk1FHPc0jqoyt7IimJxUTIUM6PnlR3W6u1u9SOq8tkQ1SUW0OjREewwrG9NvuQ6SFe2XpgSmmSlnqfsV2HkI80DLnF+HKIfIzLkxkAZRdMi390M2Mg3qBIMGul92EsyMThxICXYb8NKXmAoHkgndqiEMgN4PpBv9isI+Mx4yq/v6aQYjApsgKTA2Gkg7RDV0BxLnPjrpE+sBtOXmOi8ejCB78X2jYP44QWbdl4p4BSBxVHDeSeK97yghJSJhIvZOORDhBA3NPeGlxkJKBdIsG2R8c5QIWnnSChWl2WsrS6yAp/FSKZ4/e3z6yJGj17/nne98o2TumsbmZilLU46sJSeSp4JkA9bdWBsysPOIOrIRakNDGB4bw+LKCv7Dv/4V/MEf/RGWV5dQHRtDpoosy0KqCnP4LPSNpQCMKpzKICtanebnQADoUEUpjmGJsL60jLHaEP7dv/hX+MiHPwRJU5w8dhxLl5ZgIotarYZO0sPnvviXyMTDSP7c8yIWMINiRidrY/9rb8Khm6/GQmMd3z57DuwdDBEamUNBFZkSrIa1iZqQoBMxQwRIvAAqKCnQ8R4d52GjCAcnx3FoZga7SlWsnFvCE1/5lq48ewqUapCpZ6lGAcWHXREoiZIiS3HgtlfT5L4ZXGrWMbeyEs6f/POPLMPh6WmMFMv6zEPf0e7FlYTJLsOnC2LQSL2mJukJcUnZGl3PzYNhLLw8affli+Wd5I2dsQOgdwa+BwtVHgBwF4XLW/Hd5BvTIhRUb4FvHN8OmOqsOrxB4FqItYt6IUc6ESJAKk7Elyx6vWSRo+jY+adfOLJ06paRqWuvmNo9OsbHmy1ENjBH8B4XV1exf2IK+6+/Ci9edRDrT59CbKJQHiLAgOPIBJ4VFBu0Ty3i0YUvYOKag7j+zptwxb5dGB8awvz6Gs5tbGAtzVAkguUwUWciiIjQkdARXc2ZRa+BASQReAUKUDTbbTx04gTuPCQ0e+Ue+/Yf+f7aV//H5w7Wj8/VSqXCOLE8nyZyqkB20TjZzHzWjYSFiR1DlIk0JQoa8TzmDyjk4FlJvbAaYzRTq0SRAgUQl4ikSoIKKYqiagmgfqRZLvkN7CSC9MA7j0IUY2R0BD/5kz+J3bN78Hd/+qdxww03aqfZxOrKCiVJgtQ5WGPyKvCA6rxzg85qzrfpu40msl7PuF6vfGTf/n2/+Z/+c+UXPv4Lk19/8MHJA1cceni92TwdWbtRiqKk2e1Kn4Hus9K8XtJo8qKiNBzA8yc/qbj3XkIpUkYqmmmHiFZqw0OtIvP49OSE5cmJgRgiR+VK26Zo2VaB3f+3+Z/UWm+fve13uc4rZKW/dLKnJGcq4zyqbND4B8ozhAPWDIw3EBmDyJjB89xuPKDv0m70V4e3X14//krPnb/LfW6vKM9VB1kKdB3QLFarde9824tzPk+h8AJ452HgSaOYYih5ESoRUS9noYlZqWu0U009mqoMqCmVVL2nIhCVCoXa5oWlIx/7+Efv2rtn7+HG5uZQlmZ9qh2kIWqQxAdduTFwzoGNQaFQgIljjI6Podnt4Pc+8Uf4nd/9Xbxw/DjK1QqGJybR7HVhDIENBZJ8WyIKNCwuOAfTqn7wXhWshc8cWAVxoQBkDo16A6979avxz375n+DGa67F0qUlXLo4j416HSqKSqmC0YlJPPbUE3jhxWOoDg+hlyUDrbuJLBwrUmTgoRKuu/Nm+Jhxdm4Rq60Whq2Fc4FhdiIgJUTGoAeCEwkpIHlUY6xAVxU9L8hEMT48jMO7dmHf5Di0neCpr34bL3z92yqrDSWJwBlEM/H5ykiNYVJRA6PGe8fRzBhd99pXwUWMM3NLSDtt2CiCB+CzFKVgHoRvtHHm8ecytHt1QnzJC5aNoEeR9eRrCnGXnWvTABaXjGI7+/w/2cXcGTtjB0DvjO8xLfQDYU5+oqq4Fdiuhd4PIO1vXefSjcltEzf1vzxzJlpcDdyLRL0nrYSJthVZqaQEGL8R2dLZZGH5mbPPHts1c3jf6IFdM/G5pSXyaQoiAwZjcXkFF8aXcHT3Ptz0xjtw/6k5+J6CfQAIIgr1HqwIMk0BMgbQbWP14Wfw4PlFXHXnjdh3w1Ecnd6F0VoVc6urWKk30XMeVRNeuFBgMR0IXoFEJFR8a84G+cDqjRiLRrOFB55/nu667lrM7t9lvu+jH6h+5ROfjZaePlGkYqHqk2yEHZ0g1XMkWDEgL+JdzkwpslSJSqqxEpgV3m+BZ2sZznNkDQuZyCsKAi1wpiUuosREEYkw5zmzhnP5hQb2NMS+hcOZZilKxSIqIyP63//wD/H1bz7k3/Pe9/kf++iP6tFDR8zG+obZXFsjcRlElKwxgySHrezhcBlZSy5zqG9scpZlpZmZmV2//qv/d/Fjf/unio9958na7MEDDzXqrWPtVmvVRVFiksSTMarOEaJwbp1CHmX1yU8GPPfJTwLXXKPRWOpbSk2KzIXPfP4LS4+MjIz3ur0aeReE2sZQzkpSztoq5xrmID3pJ5mECy9CxNSvt95KnRMPn7O+mms9Cf2K7ABnRbfqwUN7oKgXgXivqgqfplQuFPXHP/pj2D09TT6XAmCbqvby6Logi/mjP/sUnnnuWVRqNYioKlNuWCRQnpSeGyZVlaCcG0ODwESD0c9pX7gsAoCNMm015m2B8jy9BISBG7FvVMz13SoqIBKoz0R8IqBGsVhcOz9/fj0uxk2f+R6pevJ5Th4ARKQxgESVrCqJ96wFUcpYibvajpzYtOrNSEt4QxVZhjSKbDWKCpdWVnbv3bfvune98x03sepEu9W0oaDT5NF7+Y5AFBo0iRhRsQg2FiOjoxDD+NyXv4jf+p3fxkPfehjlahUjE2PoJglSlyGydpB73k/T6GdxG+6Xo9DA4GcUYCZkSQJrIpTjCK16E6wev/CzP4ef/z9+FhERzpw8hZXlFTRbDRRLZVgApWIZAOFTf/5pNJst1AoRvPcwcRzW8j6DRhaJZJg6fAX2Xn0FlltNnN7YRJEY4jwSL4gRTJ7WMDrSV2FvxRtGhtB2gkbmUCuVcPXEBPaPT2I4LmDh2Bye+vojWH/xHNB1YG89Em2R801LpuNVvZKJRFAWoCpMRYGPbnjzq2nXlbO42FjH2YUFxEQQ58J3hyqOzu7BRLWGkw89pavPn0gI0ZLvZYuW4g1mSsg7D86UuKjYAMajV5hJom3655dH1+2MnbEDoHfG96yZ8KVE12DMbWcc7JoC0xDnaO2ybbycDWwZJd8mHRaStMLU2zKctIuZKzvbyaLsEmzh2RPf/s4VR267YXb34b0TB3fN0LGz5ygOXipYAMcvXMDe8XHsueZK7LntWlx88CnAxkCKMAGIAOJhlOGcBMc9BFRguPk1PP+Zr+H8sTO48Y13YOaKWQzNFLA21MLp1TVstDuIDaNIIRqq6wMDVM4fu5fXIjMYBWKIE4wxo52m+PKTT+P1R4/S4V0zdM+PfH/h/j/9wsT5B58smYKtZonUbCplY/hU5j3IQNSJQyEmOIMCgCSlAKLRj0uNod6TRkoi1hjyFkoRVAtKKIAQE8Go6GXHRvqtdmwGEWa5wgMKgI1FZWpKPZv2b/7O77Q/8/nPyUd/9MdKH/2RHykdOHRlvLq0ZFr1RsjzZs5lIQH8UQ7QVRSxtXDeUbPRgBdvd8/Ojv7ar/7qtX/np3+68p3nn432HDxY3NxsvGgit5Rl6JpS4ky3IJKNEJDgEIBTQbqxNZlOTkqr2/WRZA3RbO5X/s2/OqmZ1OCyPVAtQ9WGCAZokJaqQ6i+CD8BIMrLSFkC5zTwFsmrQgM+Wfs6D8FAAD0Qb2wjeRUCiAPIg0jRapup2X3FD977wYgB41RhmWkQaydbiRpboBj4+tcfwG//p98AjY2q9p2AhH4MB13WqhJeX/4eqWBg+wsLpUGHeb8nnPsO0v5CQgAy/eCObcBFQ+QdkUC8hzEOQAaiDgh1KNYqtaHVQrXS8FnWM8wZWL1VFQev5CNNTYZILHm4kAEjBQI8OI3EIPKm25JyadJh9Bx8MkPFbpdMqVTZXFo6/JEf+tANN1577Z6N9fVilqa0VXoTdOEiHoYt2BiwtRgeHUWxUsZjTz6JX/21f4/7vvZVKDNGp6aQOodmpzvYfcEguYT6YvQgy8hBdK5CgehWnbuIoFQsQTOH9dU1XHfkKP7lP//neONrX4v19TWcnTuP5eVlGGZUSmWkzqFYKmNiehpzF+bx4Dcfgi0V0c1SGGuQuSy0ITKQwgMGuPaOG+FjwsXFVbS7HYwag1bmEKlClRGB4AVwFFJTYiJEREgArDmP2DD2TU3i6l27MTU0jM7SOr5938M48fBTQDOBhfWSujY7WbYecypYIkibVSNlP+5F91DBGtE0Lh/eg2tfcwsSzXD64kV0O20w5Qsq7zFSreHKySmVVg8vPvykoN5pRyied8oL5KlJFil1jVDqFfH2/aX+fuTO2Bk7AHpn7IBoeqmGbX+W0RyAwRYdtgxEky+5kz6glrx8nuP2YHd52NWo3ovEFLNUxNS1GJ91F1dffPahxw++fnZX7dDkVPn80jJ67Q4MAGMM6vUGzl5axPUHrsQtd92B5eNn4ZfbABFc5kP81KBbQWGgIMNwPQFbQD2j+cI5fHNhFbM3X4Wjr7oRe6dGMV4bwvzGBubWN9BIeygTwxIQ5cgjlS39aAGKTEIWcCpAlQD1GR549lm0ux3csP8gvf3D77WPDNdqz37pmwe6mVSLsRnWzBUD1CGFsZ4yJ4UIkjgTwLNI+Bl8wpXUGVYVVmWjEMtApMyRA1kHsOSAq2+WGzDFAwAR2PLMhYQ5r4LUey+W18d3z1xs9pL0X/3qvx399Oc+O/ljP/LDQ+9/z3uK+yevtCuLi2g1WqR5AQQ4xH4pBbbOiwMzISKDXreHixfmzYH9+yu/8eu/fvDv/uzPlJ569vmhmX37yt1O5zuFOL5EQLsTd71JS1tRd8vLdNn5NjWl0fHjPo1cW4UuDo2MPZOmmfEu66r4CQaVAo+sjgg9VeoA0lNQBoWDwiupD5BYFcTqNVd6qBgmYhCxSEi6yxlbCn5LIogymA1BLUARCBYKAwgRs4A4JWiPlLrWWumZuDQyMjJlrR1XoEwvidygbY12PDAlAqVqBWZ4GJWREZ94lxE0VSKfxwqSBBwsKiJE5BXwQvAM8mE96DFwIYZ0EQ3HXJSMBTQfgbyGAkrKwoFiFwWpQJWJhYhFoUKETInTiNCLjGmCuS7QTXXSVmMSB58ZD6fMnpTEkVcGI1UNhZkiXDJGEhFqR10pNODLk5NubmVFUJrQQ/VVbu/ZY3sbG6PDteFrv/997z8KonKv22XqN2cyDUpnjDGwNgIZi+HREcxfWsJ//b3fwSc++cfYaDRRG6lBidHqdfOSmvAdY/rZ2zkQH2Ry5zGAPs/YYGJEBHgvsMwoRhF6jRYMMX7ih38Uv/Txj2NqYgJzZ89ifm4OSZIijqIBKDfMKJbLKFUr+OzvfB71VguV8RGkmgWJCAc5mFiCy1KU981g5vBe9DTDcn0DpILUBy02yVayTBmAA6GVZ423nYcnxr7RUeyfmMTs6Bi0m+HFbz6F5772MHpzl5RhFZ6dZFnLOJwyXh5Xh6cVvMIAiPy4Fz4irEWCn0TR0G3vuIuqu8Ywv7mCU3PnYUTBFB5LRXHNgQMYKlZw+pFndPnp4ymRXdfUnS0qLTmVDok6spmQxELGKEYBtF7+/f9XmAd3xs7YAdA7438HIP0A8MRd6JsJ5/I6734LoSwF2oG3aV2XohWdATCD3VjMMoK1OtkKUg/xnnTYE6MJuBqahUgqjhJRXme1J84//twVa6++ef/o4dnClbum7bPHT6JkbdgaFcHzZ+cwPTaGXQf34OhrbsGzf35/KNn1kmcEB9bU5IYqVoKG6NO8eAOQ5Tou3P8YVs/M4/Crb8YVNxzB4ekZTNRqOL+5jouboc52yHDopgBQyJv+Uh9c/KkoyqToSCAQi6p4/PhJpL2Erj9wBV733reaUq1SfvzT908lm0nkImNjqDWeFApvrBVRUbXeBfVAYJNjjUnVU7+KzLJlUWfgxYIo8qDYCCKrZDjXM4SIt9xw1S8R6RveiBFZu2Ues+w901qapSejYqExWd09fnpubs8//ie/vOtTf/7nEx/64A/W3vaWu6OZ/ft4+dIlSnrdoIsebH8Hna+owITubEq6PcyfP8/7Zmcr//k//Mc9f+dnfubOx555pji770DU7nWeSHuyUKoMdxLfFckyAg4B6L5sl4OjSNMMPaTpKls6AfHeq64QdMoTFb0XAaTHhI4QtQF0SSUDkQhBWIPKAjTIsSAQM4ONQI2IMwxmr8ReEQLl8lMGEAuVSGEKCh+SxUQLZMhCvAI+AairXnpeFKJ+2IuogooEFKBqt+LhQiLHK5WoeBH1zsE5J95nqUBbStxTwIeSF4gQOyLNoJIpyEHUeSbZysyTEPBBIfcjHG4FSSYQ1QAgSURFARao91D2IPIg8SCIB9RonlKn5AHvhJB6kZ4x3DVsW8TUVZFUoWKM9aTqVMQTRZ7ECaigGseEXg/dbhemWFRqG7WlOJhEr73WA8Cp55+nm6Mofur8+en3vve9V7zqtlt3tRpN670E+Uq+6FMB2DKMMUiyDKO1Gh5+9FH8/N//OM6cP4/ycA2VkSF00iQHx7yVXZKbf/u1MCAayFmMCXnfUIXhvObdeVQLRZAIGhubOHr4KvzjX/olvOttb0Oz3sQL33kGGxurEC8oFOLLUlRsFGF8YgLzFxfw2c9+GhzZPIVlEBIHTzowAh648SrEY0M4v7mM86trsM5DGbAath888lZEVigbuEyQETA6VMWhqSnMjk2gxjEWT53H0197RJefPg50UmLPQOp6pLyo3n+HCI8YwXco4otZL+t6QYFiu5tURmzMWea68e7bbjNX3noddSWl586dQ9brIY5MkAOlCSanprB3YhK+1cNzX/u2oNGrkzfnNfHnlOwaG0o4s55SFbK5f2MDQNTP3VkKv/x/t9u5M3bGDoDeGd9rLPTLzYTzAGZzFrpPovDKimI3MAPALBmdn13CDKYBLGAx2q3IMpoEIHUAw8AoLKTpoKXMtRtptzhSPd+7tP7iM9949Ohde6bKV+6aqZ2/tIxGvUGWCRUTodPu4djZOQxfVca1r7kV575zDM0XzoOMhUs8CvkkFnHQAWeZh7UGBgLng+41IwBk0D19Cc9c+gouHD+Do3fcgF2H9mNoZjemq1Wc39jEcr0Or4IyARkR1IcYM/aCGhiZV7ScRzFXFhgifOfF42i0WnTH1dfgxrvuwNDISPH+3/3TiXStYxAXKU68xMRIXQpovCEWPXJZ3p8c00BBq5agjjIjLMIsEGvAkfEaGaYIUAORfFM6EG1mUGccCjFMX+sqIfqMw/ESZqqTMRedc6te/Xp1bLRtQe2nnnu++9jj/2Dq1ptuGv7pn/qp0htf/3pTX1+ner2O2NqBbnQQBywCY0I+b6/bpaWFBeye2VP8T//xP83+7M/9LD/06KPYe+CAaqfDmmUXsyqUs6pkW3r6y9BlXK2KXV/PEuaGSrYghjIGr6rqCMPEQiLwSBTaU0XPMGdeZdAdIszh4AgLQGqg5J0jMYZBbKBsyCiHaAZPIdALCHEXZAGKBVpipbJ4XyFQCaBCMAdSBkUCtlne8e1IMaWqGQ3aTba0z/IKDYO6veY7JC47hXYBbRGblEgFKk5VEyVKQUhJKVMml3cLgUAm7zTnXLsxKG0BqYA0YD1GvmQkUZAnIgewB6kPy0iVQF2zglSZWUjVESiDUipAyuodMYlR40WdNzCerXUW6ntkPavL/a0ASiVwzwjHsZgoUlSrkmvcgWuuQaPVKltg/w998Ad3lwpxdXl9jUWELHOIVByoawQOBBtH6LkMv/zP/xnOnD+PsV1T6PS6kCwLDYF5KoXmjDVyE2c/qaVfhkNKATTnuygAENsIpXIVzY0NWBD+9o//JH7h5/8eRqo1XLxwERfn59FuNxFZCxtH/ZSSgTmwWCigXK3gU5//LM7NX8Dorin0nANbAxHAc1gIJOJQ2jeFI7ffgLZPcebSCrJegmocoZM6qAIx562YBkhVkGaCoVIFu8ZGcWByClOVGprL63js20/jxQceBTY6ZNRk5MympH5BUjkXkZ4C6AkV9zxbvlh1691FuxuVLKsm3g+J1UizXqWwd6J057vfZFzMOHNhHnMXLgZywjl4hMXMDVccRNnEeuyxx3XthVMJUXxJnDtpYRaMcMOTz6jgPYsN7DM3tG/ZnQTAmMbS9ixTfNf2wR3wvDN2APTO+N+knfCJJxS33hrqvHNzyHxe9oGVFZ2ezDefF4BFY3QWwCwALC3pPAwwDZqJIu1rODw8bWADw6iB2kZRLafS6a2aUvHE+W89+cziTddMTN14pHz1vn386HMvQL1Sz3kYYszNzWP38Biu3LUHt95zF74+/0n4zR5Mrtv1KiAvgzQGyVliVoW6APoCh8dAV7Dx9Ak8fOY89lx/BIduuw7Te6YwtLuEjeEqzq6uYbXRQBGEiA1iJZAHnBdYEKoAMp8nB4sDWYsz8wvo9hK87oYbaO/1V9JbP/aD0dd//y/GkvnVIyauUC/xagjEEBjQps84KZSMAIokxZasMIpgBexJrDE2gpcYQEEFMQSs/TYUyquIB+UZBKNbVqSBkDfXgpIiVfVNMrQpIkkvy4TFJ6WhoXY0pN1nX3xh90/8rY+Nf+RDHy79X//oH1m2Fuurq4ijiKwJbF/ohghsW2QMLDO67TatLC5gembG/vqv/drM3/v437/9G998SPZdcYU2so6vpvFiR0XSVivspt97L+GTnxycaHMXL+q4Mc5FUeJSqgt5b5WbqfoSSWZJDYEgXtiDvPeh9CPP/eqjV1YICcipR76fbpghIRDCO0MwarBlL4P3YCgMLGIGevBImDgRlTJEiwCxCgRMGdQ7oxx5Iq8qkuNVGrgUNZcnv6SlsH94JP/MeOcpaC2QgaUL1S7AXqEplHpQ6YE4harLq1zyfEUyCBsN3K93IdFgSvUC5YHIt59BEXq7lTxIHUJZoagXFZAyS3h5ImLZCJScenVexSuRFKwVMeI1g8CQV/Yu5JmTEOCJSIhZKbPCUSJkjBZXVwU339wHS/SOt7yFvvrbv11707vedeVrX/3qiXarZb3zoUJdfa6/pbzanOCcx/TUNP7wj/8YTz/3HEbGx9DudEIDZKhNxGXRjYOFC/LTIY8j1K1SHGjYEagUSyBRrM4v4PZbb8M/+Pgv4s2vez2azTZOnziJ1dUVAIpSsTioPEfuH3CZA7HB0MgoOt0uPv2ZzyAuleC8z/0WW4U0QoDAYc/1RzA8PYGFxjoWllZQkNCe2Bfhc86U97zDUKmMK8bHsXt8EuOVKtobLXzn4W/h5KPPaO/8JSCDs57bmrhL5PUFq+ZRT/osHOYytSuISq2sXE2bDxxTHKpYHbZGmYbIYK8YTF//jjcUh/fu4tVug77zwguI0gwqBkICnyY4fPgQ9oxPorO8iWe/8ahDzzXgzPmC8gkCVjJxXSuxZxGhKBJuNpU4UnBYnG/fhdy/3Svz8vKUHfC8M3YA9M7436idsI/D4liRpn9lNvTsNpp6HsDsLDCPJV3MPAGTA63caK6PrnNDoRWXtrUVxTTnW63Hv/O1bx28e//u8b3jU7ULkyt08cI8isYg8wJyDs+cPI3JoWEcuOYQrnnTq/HCp+8HRYw09YgkRFX1Cy1UFMLhktiARIFMwZbhuwqOGJoluPj1J7F0fA57bziCK2+7FrPTYxitVLCwvo6za+totbuIFYjyaD0vYS533sMQkDmBZUKBGYuXlvDV7Em89vrrsPe6Q3T3T9wb3f+7fzbavbByuFwoMVJE4oXY89liyW6K54SMl0KARErEKl6IjDJABk4jIi44koIRjYnJEhP1SzjEa068hglZKDSu6TYzWx8MhAhi8kxIvSpIXVOIjHPOK4mzpZLjyOrv/O7vjq+vr5f/6T/9p2Zscorqa2tgIhjq12eHHOQ+82cNo91uEZYuYdeuXdFv/PqvT/zMz/3cqx56+BHs2rtH2r2eWlXfA/z+alXmlpcV996L7ZpoNkbZOcdECdTCMzJ2pi0GlsQbaBBchBfNDNUcfSmFnWNSkNsy0hEUzgPW5GJ8YjApMkewJs9MJoaywgkRvFHAhK7uAFRBZNF37wmpGFIIiIzpbwBsa0nMy1f6DOi2cpUtMJenfYgKMVIlbhOoAw0sN0F7ABL1WabMnmA85REVCjHQvjXUAWTDfbmMyDCRGgaEFUTa7yUnKEg9QiemR2j3UYBVAo5TJhJRKENVLIf3j0i9qkAhUcQeEA+x3lnvOYXnQsGz9964yPtiJsZEYhoNieNYB+zzXXfx+smTBbF24t4PfODwyNDQ6MqlS6EkKa9g15x5JmY4r4gKRVy4uID//Ju/CRNFcCIDnbT3+WKY+nXnoaad822YPGgETOE0EQUiYhjDKBeKaG82MFSu4O//3C/gYz/5E5gYGcb8/AJWlpfR63Rg2MAYQuZcbkZkSL5CMtbCRhFGxsfxqc98Gt959hkMTY4hVQFMOJdIguvYSQaeqOHKm6+GGMGFxSWkjSZKUYjeLEcGDkArTUFxjCumpnDF9DTGa6PImj2c/vZzeOGhx9E5t6DwrEZspqlbo8w/aoTuJ0+P9zoyj2LS8CM+wdTtGT75SRkkFxoTZ2InqYBrXNa5bvaNr5o58pqbbQ8ZnjtxAu21DXAcwTkHYqA2No4bDh2GdcBTDz+hrVMXElKeZycnlcx5kV7DEqdUSD25kph2W9DPYTdGB/KNFVYYswWedyLsdsYOgN4ZO0AarwiaZwAsAlha4b7g8PJLAPOLAGY8ITI6gwguj74TVyNgE8OiVO9GUosrSbPbWrOF4vHVJ59/5tjRQ7uuvfvOw1fPzsZrq6tIWx0Qwm57c20dz589i5uPXIXr3ng75o+fRuO5syCOYDTUPAeWK5+g+0EMEqKtjCrIGmSiMKnAMUFg4C6s4ezSI1g8NYf9t12HK647jMPjU5ioDuHi+gbmllfQ7iWoEsPn2bKMHK4pYDQ8bsQW64vL+IZ/Bm+46Qaaumo/7v6JD8b3/dYnxrqLG1wslMgmQobhXeIEhjZcymmRWcBhXz2wxoaZ1SojVq8la7hkiGMm4oF6Id+2HkgHaEtKoKSD3OOgs1YSBZOq8U5CswiJQjkjY1pZ6ijzjiyRGd01TX/xqT9DL0lK//bf/Bs7PD6OjZU1KsSBjd+K2NXAJjLBCCHpdqmxvo6R0bHCf/4P/8+un/65n735q1/7uuw7fKU0uy0vlGQdVP01KyvyQj/9cGWF9+/JqLMSg6NImMih2yUJOdkeGQwsDMTayIhRkbyZBgQWkzdFEIgCC00UgGNoLCF4YSgYVgkCMszsZbC0IKPEUGVPIGYDgQeHXAeScD1iE7GQgJUMVNnnC5RXGsz8ykHS+fUNsabwjmA6BG4otElAkFAQJQBlZMlBIMzst5LpiENcsiNiqyAmJiaBEAsxSI2ADImwGsODDy1xTpWDGKzC4XMgl+dFa+BqWZmhRiFC4iMx3nsRWOtFvTeZOC4WXeq9Z+e8KVpnRVwzTaVcKskL2+Rf905N8We/8tDInW984+xb3/yW2VarWZFA3A9MfoP683yHZGRsDH/wH38DJ158EWN7dqOTJaHl0fdVzttCuYPHFf0iIFUFWxsyn71HMYpRjmIk3R7W1pfwzre/Az/7d/4u7rz5JqzXmzh+7ATWNzZgmRHZkLOYZmmI0mObs9x5y6cqhkaGkbgMf/JnfwqKbADNxgBM4Jx5RsTwWYbZa6/EyMwENusNXFi8BJKwx+AISNQBhrBrfAJXTk9h79gExAFLz5/BMw98G2vH5oDEgz2UVJbJ6fPI5LEi88Op0LO98c4CHjuV4OXZSIRbby3EvrPLFfgmdd274gPTV97yrruqXI7p+Pk5OnPiNJgN2AOiHuIU115xELViGUvH5/SFB76dkedNdv6UVZxkTVdETYcldpyJcKmpAIem2QF4ziu8TZ4B3Y+wC+zzTnnKztgB0Dvjf3MW+oknCNdcE1joLKOXgujtoBnYlgOaZYTF/P8mtgFxEVJfITJGh7GJegqPLOpwsXSJ0+zpZ7/04OzEgdnpsSv2jB7Zf8A88/SzZClse1aMxcmTZ7BrdBR7p3bhVe95K762+N+h6104+n+z9+ZRcl3Xee+39z733qrqGWjMIGaAmEESnEWKEq1ZtmJZAyVLjiLbsuLp2bGdl5c4L07s5SQvzy95iR07kqzREmWJGqx5lgVxBglSIAGQmEiAGBpAz93VNdx7zt7vj3OruklRkePkPWet13utWt2NRndX3bpV9zv7fPv3JUARO1pc8m5JDQoCicx3ZTvkDop+SnYMLXFOrVMXcPzCZYwcPYHtN12DtdvWY3jVGqzu78eZK2M4PzoO8zl6XVJerCMH2JnBB4OowqUZpi+P4fuHHsMd112LvvUr6FW/9Lbkm+//1FDz0uTWNKuQb/lWJXF5QpqziYe1lHymaQrziYM3z6xIjaQC1pqq1YwtMzVWH8EMRAR2AhaGqnZT8RZ2P62D9ApKBDgmy4iRFgoHJaekrEURzKxBLONq6tq+4MFVK+nrX/uqzdVna3/2p3/mlixbiqnxCUhK1OEeR8BFHM7KUoEa0KjPERFhcOlw+qf/8T+t/d9+93fpM1/8QrFl+9Xtet21pqandbJa1Z2jo/5YtWrIc8rrwxzyabY0JcpzI+eUook9CuMQzCQAnmMbHB7OMXkFxfi0F2SLdDrP0RRb+nuIAU9BHAFGAgDmCDBGwo6DCWDMZmWKD5hgUW7GxMZAZEKuzH0kKnvK84uJbhu0E91NC055lPBpZmXmthGmQTZORjMgKDsJGqwgosAssU2tUAaXq0AmYQXYzXOtzZhJCGwOSgqQQpjJUE7MxU68MFvnfrnoAFFwbGwzsbKRkkhQsiABQU29GXtlDWoWTPMgJoFFAnsfWDVIJXin6ht5HlxfXxBVQ1EAb3kL4coVutDuy1qzk2vf/XPv2jE0MDA8MzmRqKkxc2cuNcajx/hFpGmGK1eu4NP33INKfz988KXHnyzYvHS2Ej/IRNHeXmakEwmgIBFBLa0ARcDE6DjWr1mL3/mXv483/fRPI2XBqWfOYnx8HKoBjmJip4aAoiiQJikKX3Q4J+g8pWmaYWjJEhx44H4cO34cPX29KDRSDUkcWBgFKdQC0F/Flmt2wGUJnnvmLOZm6qiIQ7NdwITRP9iPq1evwroVK9BDDiOnzuPwvY/i8rGTwEzLyNhEuY2AEVY8ahq+xZ7vne1ZchYPHGi9IHtn/n13y5Y08/XlRcrXGlovs/70hlve8tqlA6uX83h9hg7/4Ai4CBH9LQrNW9i0cxs2LF+OYqphj3zjXgsjE3MckufM21PecEbaNC0JtTn3fiZr6hJJrCueS9vGi+Lr5rvPhh+fC7RYi/X/WfHiIVisv+taWwrnkR/3HxcA9UdwMRI7JoA4gDJfQ05sIOQ+n8pn2dVOhIujTxz6+vefzWebzfUrVmD1mtXwhYdpjO5mH/DE0ycwOTeLldvWYd9P3QmrxNZZ4DJNj2IoBrpbunErmCh2ilGipBiACwoKAFoK5ARuGmaOncHBT30N9376G7h49BkskxquXbcet2zfhpXLhlHXgEbRhreACim8BkANLTW0ioDMOUyPTeD7jxzCdGMWfetW4GX/4GdctmrJYG7FplB1N3ihHW3jFeSspiySZjGpxqkyg5wRZzDUANTMrGqglAnSEWZctr/V5nm3Zc+0G3fdbQlGD7MzIA2QlBgpCRKYicLDWwhE1jDQeAjhUl74y/3Llk3d++CDzV9673t9o8ht2epV8KrILcSoYmJYiQRjZjiJLolmfQ6TY6PUW6mm//7f/buV73zrW28+8/SJ27LM7VparS6t81x1slp163t7BWsK0qIgGxh4AQ6OjCRXMCuYlaQaIBKIOYDT4ANHNRDInpcob2CRlMXAYsLCwiLMArCwCIxFTBgsDDaJN457/QaCJGDEx8POETGLGTHiHYEpK7GL96lLWrZup/mF9A0Yupi2EtRQGKgBwgSIrxjTKJGNmWKSiGZZeA5AE8wtJmszc4uZ2wDaYM4BtAG01Sw3cNvICgK3QdRmoZwNBTPlTFQ4oYKNPAOeyQpmFCArFChYOWelgs28CRUwK0TRNtU2MXInKEjMk1iRuoonkUBJCJL4UjxXfSPPg1SrwdXrKiOZ7QeAK1fo5uXLk8fv+2b/DXe+dNdtt9y8X4u8z+cFk0V6SNwxifYfFoYidng/+alP4eTJE6j2VFEEH20xZdImlbaseBEsY9c1bjQQC4QZmQgSBZqTU5AQ8A/e8U584bOfxbvf8hY0pqdx9MhRXLp0Ke5EEUOY4YsChfdIk3SBJC0Ty03hRFCr1aAEfPqzn0XbFyDnEFDuvpQsRQjBI2DZjs1YtXUjWnkLz1y8FN8Tco9KlmH7unW4Y/tO7Fi5FnPnxnDv576Jb37g07j84BPGU7m5glVaaKClZ6WwL5DnD6YkX8ynmmdw4ED7R4rSO+5wcG6JZ+wh6KuM9Pbtr7l9+fp9VyfNooVDP3gC+eR0pH8UAaHZQs/Spdi2aRNEGUcfOIQrjx0LrDKuLX8UeTiZ+XCFE2lyKDwniS6ZSxQT3YHkrnDm0VEbuVw2SZLEkKa2wPu8ODy4WIsd6MX6/3vENwzVajeVsEPiCOVg1Mjf8JddBrAEADAIkufvgUs1DTBq+7nWFXHpsckHf3DVme2bVmy/fX9196YNMnZljPxsHVmSISHB9Og4njpxCvt378SOW67BlQuXcOG7h0BZCvMGK7TskAK+M2S3YEudyqE7CnErlqwMWc61jPwlaKuB0YNHMXriDFbvuRqbrt2JVZuuwvLt/Tg/NooTz53D1NQ0vJV2ERioFLMx0IUxNT6Bg08+iVuv2UvDW9fihje/2j1w95cHw5zfSo7nrBFyEs5TTi9rbk0TZgRIKpYGQyUYes2oD0CNiVIQWA0gKxcINo9Q61oI1ECILOeu8IgDVgwjF8wLjIRA891AoqCqOcCzJOSIxflgsmTZsDzwwP30y7/yK5U//k//yS0dXoqJsTFSGBJxsOC7wiZoFNNmREWzhdmJCfT2D1T//b/+t6sSdrd+/C8/aes2bQpL0hVHJkdHr/je3nzF5ID5dpvVjNV7tkqFrbPLQWzkXOh0oaFqRi6m5pgFBxfg1MOcQJRhjqJdxRNAcBbIq1hp4YCwAwI6zL8YNULOADVPFMRJAEswNs9kwVQFzAZmWBHiHgXD2HFgQqBII+t2NqwzuLqACDGf68Eo49sLZppRojEiGndmdcCRsTGgneAXVgU4Rn8bArjbdeTozuAQCAwGhEBUxnfABZjjMuLQEcNTadHwqiSsMAtxqSAKVRjBJP5bQUCLhNreqCGEFhG1WbLChxBENZCxtZg1MdOGRfGctFohqdX0bOOCnW2mtLPZJLdmTaU5cWnt29/yL3euXrli69TYeAXlueE1dIVpKKcka7UeTE5N48tf+TLSSgVeNe6oUBkWY9EmQaUVxWBGZgui0QlV51A022Aj/MTtd+DXf/VXcduNN6Kd5zh26hRmJicBI1SyDERAnhddr3oSA4KgGpClKVpFEQeRheESh6XLh3Hs+HE8+PBDqPb1wmuAcy6Sb9Ri7g0LkArW796KtL+GE2dOYXZqGq5aw7ply7DrqnUY6h/AzOUJPPq9A3j64BMIo1MgT3DBAV69U6ob+KQZ/hqgbyah+UT94ImJF0+YX+AQmpjokx7bjkReG0LjlmU37Fmz/zW3p5qAjhw9RZefORePdxHfMNg5XLd7J/qqPZg4c8GOfPNeo6avI7hzrHSUyS44l876uZAz0oAs2vToBTuNKxa+94vYfyW+e1E8L9aigF6s/1+L6PnWmoidD4EWimi82BT2i3wdawpAf/n5IIDZ2InW3E+2bS5kfJYJTzzx1e/vGl69cmhg/cq+HZs32uEnj5FXhRGjmqQ4c/IZDPT04OoNG3HTa1+Gv74yhcknT4NcilAokjJoruMR9mUst5TDS5DYywo+RKBFVKYIRYFOmh9nAhubw8UDh3DpyZNYd8MeXH3jHqxfMYzlQ4M4df48nrlwGXl9Dok4ZAAKLam0akizDKOXLuPgE0/ituv3Y83uLbT/ja9IH7nn60tbBXYlCbyp5RqMQTzKHIIPSMiQMlA1Q68CfUyoEigxYzKN+8tEDC7FWjdEpRRwYWGgnhnYmKDKIFBCTDGZWhWmCgVYyDhAI8RDZmGUseNK4UM2tGqVe/jhh/g9730v/fn73ydLhocxMTpGaTWS1TqCsRsCyAIzRXNujkwNPb191X/7B3+woVat2Z994AN+89bNrD09RyfGx8ccUY40hRYFW5qKec/dYJk2GZAbZWaQTOG9kmpI01TyEDyF4ECJmFOJHhxwAMi5aHMIZpSYsDdjEYuDh6wCFRIBByMTIwOzOVUYKTOrh7IPBA8iV1qGScmIieKazEzJyErwRgdHXC7SqGvf6FhpDICPGkhJuEXqZwGbBPEUmBswZufIBW8cqWLMImHB6lK6uRtcIpBZOJKdmRkhkBEJmEWURM2YASoij8QMHIcHzYJQafUwM6WIu2NQAKwIsLYD2sxomVo7N2mx+pyJPDErMSs7pwwoAyr1uib9/SrZiG1BAuQ5uY0b3SP33Te46yW37H7D61+/0wo/bMGLqo/+W+ZI4yuHLYuiQFat4utf+jKOHTmCgeXLUM9bSNLUgmpnJNTUCAQlJjIykJQHnZmRsiBvNLFsaCn+7R/8IV59551ImHB+5DLGrlxBu92OKTrl4GswQJxDXuTIXII8b0PVI0lShBDDgkAEKe0b1Z5efPozn0Gz1bJaLUPuvTGEorvGSIlQ+DbSq5Zh/e5tmMlbOHJ+BMPLl+HaLVuxdmgpmtNzOPK9h3H0wCNoXxwDAiDkjL0p5aFFSpPMfFoND4npNwjFk/VDJ8Z/zHszYf/+KtpT2zVJ7jRt317Zsmb9rW99bcZ9GR0/c5aefuIpMAgh9wAxLBTYvGMblg8tBWYaOPjF78BfHPNUyGXL8xMMesYrxovQbnOqgXzFgClMlIznHwpNeXHvsy3aNxZrUUAv1mJ13gQPHTLs3BlRdmWH8DyiDxo/Iu574deryjZK8cLfrtqdC5oUNmirgJcJqmTPhueunHzsqwfWvPQdb+jZuGwFz6ybxbOnz4CTBL4wVJlx+MljSLMMW9Zchdve/Bp8a/rTaJ0bA1cEeTsmzqoBwlHYhIjMjY7KEnkXuQQlSQHSDSQhA0JTIzKXDOZnceZbD+L80RPYfNM+7Lz5GuzbuBlrlizFyfMjeO7iJQT1SFlQGCAKmPdIKxWMjFzGQ4efwM3XXIOrb9hNU6PjycnvPLwy7amgXS+itkroOJSmiZCohopjqTKjZoYeKKqAOjNjlPRcLjnAC/22sfOJ+QHD0mGgZVSjqpEwKZkqG7xF6zQ4lO5pMwRQzo6bplYPZjMafDawYoV74sgRfte73kXvf//7Zd2a1TZ5+TKyJKHEuXhsQ+g6FYgBUkLeapKpYoAHKv/yd393gzC5P/6zP+GNW7em/arHGt5PJM61qRLMZj1plnGz0QCISmJE56TxILMQH3+LM0rZKiQIhYCdwEwA4gQFgVz3YHgLBBUJBHJmQnDOnDEZGKZCHFhE2AczkoTUIMaawMyDKMDgmCyKUgabQRamD5rFxEEt3RxaDlb+0CCBapkzhzaYZ4lsVojmiKgJISGlBA4skTYiCAIBLFc1sJEIUxeaDMBCICIBSNmcIzIjMRNIZLzFSJcoegRQiCAYKZEFhGBKpE6k7OqTh6JgoG0ihZrlEOQMKhjI2TlP7bbmROrSwuqzaon35gYGVEZGrKenR3PkNDcwIL0itfaVK6t+4Z//ixvWrlq5ZWp8IlUNJCLl4C13E9NVDS5JkecFPvihD8GlabfzbNG6YWZQ6VifmdnUOrnmQDyXURHBeH0Ov/JP/il+5hU/gYvjE7h86RKazRbUDM45aOHLEKB4rhbtHJwIihAimrIMHfIaIC4BMSNNEiwZXobjJ0/Ydw98D7W+XiuCVyJo8J7IiRgpPAGGQOv3bkff0gE8OnIOy5cuxe2bNqOCBCceO4ojBw5i6tgzQFvNcQL1ZtBQEKhuissMOmHBP8KGh83RU3PaN/1jxCdj584aUN/IPemdavmrecXA+pf+/Z+p9l+1nC9PjOPQo4+B8jwCa9RgoY2VWzZg26aNSFTw5H2P2fjjTyt5blg7PMOBjxHz5Uo7nyMyT2nyvL+/JATSea48foz3ebEWa1FAL9ZiLbBxdFF2a7tc5/96dTrQI1jgm3Ni6mcA7S+pHIGmAWCaDT2iKNAKKMZZ3KmJR49tf3rtqlXXvvaOdMeG9TQ2MYnG1AxSJrRVkZjhyaNPo69awfJVw7jtrp/Egb/4PPzoDLjqEDPdIpcsxgsqNARQp5VXRnVDsYAtG0UpE8O8h1LMRyYgsqDPjuL46Pdx4egpbLlxN9bv3Iqbt2/HqqVLcPLMOUxMTiJhBolDKJu8Lk1x7vwF9PbUsHvzFuy/8xaaHLmSjh89s6KWumsKr0yKioFPsWguJlU1VEGoMXE1aEiDgcEESVy8/wuSCDvCo2MdiOg6W5iKY0ZsTBTIrIAijnQBoGjyRWAwQ5goGPngA6EFljkA1bYPac/goBx76mn84nt+Kf3A+94nWzdswMTly+Xf5jJnpDSzlAObwgz1bapPT6F/cKjyL/7ZP13Lzt35p3/2XwaWrFw+ONjbe2R8cvKKONdkCZ5UDTUYGgCJlDBeNmAOQA8QApMKWZoyqQZDYMqDWII4CZqmhBxAUsKADQTzAhIhgsAhkJoEM04ANnIcvIoTUQ+YiLEFywJIGWYkTGwqLi5GnBC5YNZVEFTO6qFroZmnoiz0Q5d0DmPiHECLwS2CtMmQG4SdUAhmomIs3ggIUCIlRwoIqUaCjcz/wtJgzUwwgnRBM+XrMoKjUWJKVMkYph5kEDEhVSZVOGchTtTlgBUwFJKgoMCBHXsKIbCqL5wLAii3STmjIMwqSWJJ2XksioKqGEounTs3vG3v3h2vffWrd+d5scJ7HzMhmVHkRXlMCNAAHwKWLFuOL331qzj8g8OoDQ0iD/MEHbJIcS6HNiNSu+R/UzlESCDUZ+tYu3o1XvfqV2Nybg7PnT0DX3gkZeKglQmRXO7UqIU4fEuEZquJajWynwvvkaQpfFBkHO1fg0uW4P0f+wguj42ib2hQTUNBMB8hPJoYi4MF4v4aduzdgXpeYDCpYu+GFZg8cwmPf/dBXHryFDDbAsMBRQFSHxyo7dhNAPyMGp5kDYdZ5KkQ3JnmXDGBY4eKH9l1Bgj79vXDFdsocz9pVLwCvdVtt/7cG2prd22kyzPTeODgIWi9WVq9Incz6+/Drp3b0V/pxYUjx3Hs698n8mgjt4tkfJQCHefCT7FpTolTNNiMlUiNhlQJzGYdEe2cvWj64PPJG4tCerEWBfRiLdYL63xnmHBhN+JHdCbWA8ixGvqC/rOV9g+CAT5goKcU0mkSkKOuZucIduHpb92/efmGq5as3buVrt+5g+599HE0W63oYRRGa7aOhw8/idtu2I81Ozfilre+Fvfe/UVow4M44qgQAA0KC9H6QBo74kLxYh4QRTKX0W8MhgaDo+iz1BBTopUUJACCR/3JZ/CDM+dxdudJ7L39RmzZuhGrB4fx7OURnLxwAY16HVL6kBMA5Byeeuo4BnpquHr9Rrr5dXfgayNjWXu8sbyvkuzO20HFe2GKVyYCKiDLQtCMgCTCIGKLWakUyaVgY6KSrRu75Z2Yby5pGTHSWA0x9rogYxMGGxiiICNjIXMhqCXM0HggAjO1vQ8NYcq8D65neJiePn6cfuGX3oMPve8DsmXDepseGyNJJKZFd7y/5VxjRzwWRU5TE2PcNzRU/f3f/WdX1aoV9+/+/X/oXb5q5ZKBvr4jzVbrPBHNeOZWxaehxT6A2YjZwI0y9awFcr1q3jOFoGZGpMpmFuLOPhh5qRoLAlIjAsgoFRRBvEDII5hAEnFiqhJEWAAjZsCDicjDzCeg0AmFZhIGGTOzUyLHMSe849zokDio0x+O6GbuOIK6C5iIbaDgRIoAFGArHFMOAwfzBph3JAQHRiADQR3Fs1MCAc4B8M97DQUzEgiAYNF0EBAAsAPMx6MWxagZJaRMKH1KZlpa3zk+Vs8mnlSLIoRAIiEh0xysCME4TQMBOsesqYg657QyNqanBgZ0P4DJapXXrhiqPvO9Bzb+yh/84Y2b1q29anJyuhpCICYmM4MkCVQVPkQPsQWFV8Xdn7wb3kJsTIPirkqnyawGLX3osBhXziWs0cys6hK6cmWUfv6d78Tm1WvwzLlzCKpI0hTBe7BIZ9EOqKGd50iyFBoC8rxArVrtLparlWrsipcpm0NLh3Hh0gj+6ktfQpKlWqh6NWsTrCARIZiRYxS+Ieuv3smr1qymmRCwNqnisW88gKe/fxAYr4M9G3uAC2+kHFS1yUQTUD1lhMcEdCiBHM8KGakMTc2cPXC2+JFvvDt3JuiV5UB7n6TycuNwh6a09aZ3/lTftpv30nSzTod+8ATql8fARnEjRWO8+L7r9mFZ/xAaV8bx6F99CzYxFyjwNAKOuNyOQZOLkoUGz7GPp1kUzZjfRSFa8PXlUY6dic7w4CKybrEWBfRiLdaP9EH/+G5z8vxtv3lLx0UAy7BUxGxSCX2df5+BhX7qD6XW0ClCKpSmWRG8H1fDBUy3rjz8+W/0Dgz1V4dXLcWubZtx+OhTcGbIVSFZirmZWRx84kncccP12HjtDhRFjgc//VWQemgwQAHHhOA9UkkQtBwWVO2mg2mInVTSGJjH8xTfUlDHwTyFIbQ1OgfqAZOHTuD7p85h3Q37sOPm67Bvw0asXLoEJ849h2cuXARCgBFBiUCJw2NPHcfQ4ABWrF+F6175Enrkc99JW8DKxFMOkDclB2hOZlVTZEJwEBE2Y1WjEEqKSJl8RyIQIsR0DJ2PeO6ua8r0Z6JAzIU4FKGw0Ok8K4M0xv1RPCAU0QdKZhZCIpIX3jeIyMGMh5Yvo9NnnqWffec78bGPfER2b7/axq+MIk0S0qBQDQCXg5olpSJadT1NT06AgPSf/tZvrenrG6z983/5L/qXrlwxWKlUnpiZm3s2MRtXkTk4pxSCdUV0vdN5bRmpmtViZ8ykqgiB4ZXIlFAtDbPoJBVmBAsBqQnYOeOgcUBS1TlRqEV1pwqSwCAJwuyJOHgVNQ0ROCLCRhAmEuJuuLmWHVKyzmrBOoOk1g34mIc7xJASBRSkgQQ+KBewnIVFE3HkvQfEkSM1Yg6eYq4epwAsEEDwNE8eIcDUGwCxDvMjAATv4BygvgyIF8AbjAB1MJATBZFRYC1cCKkn9c57gvPCSSAutCAzjtsZYO+DmAVWVQE0nZvTU8PDit5eO1Sv061r1sgThw8OXnf9jVvf+Mafvq7wYahot9nMTBEXd50RQBFCO88xuGQIDz78IB568AH0DPTHYBQnCKqxr16e452mNREpDMTMpGbsRChvtbB6+Qq8/a63o95qYXJqKg7xaijPudDdKSiCR5pG/GReeGSJg7Cg1W6jWq0CFuCDR09fL7wqBoaG8PlP/IWdfvYZG1y2VBs+zwG0iTgHTBTlDkmaJHv27HbD1T4+89hjeOC792H22YugVgAKhrU94E3JLDhO2ko8rWoXQXjKEJ4Ey9MeychUoz6DJ84WL/JeS3gLeOkTV9fGe3QVA/s5lVcE8ndYRquuf/tPVbbeso/reRMP/+BJXDp9BkwC9b5cPAdcvW8n1qxYAas38MBnvmrNZ0fAljQ114vO+LAZnnHMMzybF3DOUFNCPYrmeaQ4//A1oNM0qVYjfWOx87xYWMTYLdZi/bCIPtQbOw0vEMk/yv/8vLosL/pzpr2k3rOmuWiaS09ekVqeCtoATBvmbYTMnW8/c2Hu/s9/M+STs9i8Zg02b96I3AzOCUIIcInD5OQk7j18GFN5Aztu2oeb3vgKhJqDZQyqJDAyOJHYoUVkQHe60FJepansRhHK6THTKE00ivDolyaQVyA3YE5BTYNdmcPZbz2E73z4Hhz+/qPopwS37NiBm/ftQe9AL0I5BlZJE3hf4AenTqERcly9fxeGt2+gphZpkfAKCG8BYS0RDUGpRkYps7jYZI7dZytRXobSxkElT4N+RJiHqTGxMXEAc6GQQklyJWkboQ1YDjOvZl6YCpgFCxYSUCAS7y3kEG6BeU6BuVbhm0NLlrYvjY36d737XeHxJ57A8IplyIsAgOFc2sXqMXNEhoGRiAOpYXpigqYmJpJfec/PL/l3//rf7KpPTr28OVN/2WBP3y4yXulz9Fieu27Hq8FW0jA6PgmjllPKk8BpHjjJAyVJoDT1VLjAIfEcEs+aFuS9pyR4BOfJtCB1nsyK1En8aOrJSRGA3Cl7Z+zB7BXmQRYgrFpOlDKIELRjm+nG0z9P6XRS2lDGvL9ATZRIRYM6D2VPzJ7E5QzXDt63ialJGprM3GCmZqrcSCVrMFOTlRus3KBATVJukIYGmzZYtMEc4kfhRio8lzqrM1ydndVZuCFO5li4QUytwNQKvrwxNzl+bDGhzZnlAuRiWSHQglPvpVIpWiH4RpYFShJl56ynp0fR22tYvtxKKoirj4+vuOttd23eunHD2vrMTNU0GBMRdVWwdU0lxJFh/olPfhJzrSZcpQKIRBQjMzSuSbo/LXEhoUQU1CwQEFJimxwbw2te9Wrbue1qXB4dR95qxy0BZmh5/hERfImqYxG0Wk1UKxkcM9rtFmrVKghA4QNc6hBCQG9/H2Ybc7j7Lz+Jaq2KwsyboRDmPAC5mrVMqFUUvrVyzdr2tnWbiu997uv+W3/xBZ09esakDUMb5lreXKAgoIIhbYXNEWgKZpdV9RLDrgSE6XqeN3Httf4FxI046rBlS9r7zLahRi25ugp+NTu8XTm8yiq8+vq7fjLb9/KbqK0FHjr8JM6fehaSZVDtzG3kWLVxHXZu3QIXDI9+9XsYO3wCbE61FaZY7Yx6e440TLJqQc5pHUB3wfrC87vkQAM/PP+yILZ7UUAv1mIHerEW6/ld6AMG7Izd5vJNdG0IJCJ2FsCPEtZ4Xhe6v+xkhOcHq/jA5jO2xMikEHjHQZHDwpgpXeTUbZp47KnaY0O9fNPfewVvX7cec80WLl24AE4ShLITO37pCg4ePYJbdu/G9luvg5Hg4Oe/Dd/UiIyCIXjtDg0SMYLqfLKZdWAcZV+6NF4aEYgNqnFoLAFHZAUxtFmAEgEZUJy5jB985pu4ePw09r7sRuzYvhErB3rx+KnTOHthBEEBcYKRkUs4PbwMezdsxjUvvQHfOXORwkxR1WDDIKwRM2dMArNKCJrATMq7BFdmh1ApENDFpzGYBCH4SINATCNUM5iqxe62FUTwFeai0BzlTJY4Es0DTAEysjZgeTAtzOBhVBBZoYSc1Npp4txcu82V3l46P3KJ3v2e99B//uM/5puvv96mx8bJNHYcncx3AFEuSBhGqkB9ZgYwcr/8rp8bCBrc7/3+v0qbjFqlUqv6fEYyrp6DhNBWVeqDlaCWH+qEWQMghVJvHrtlWitxbw2DGoGrMeHGeWTewVxAKzgr4JEEEXMwCmoQBhkKNRMyFMaci3EeQvBqCAITBkohT4FAITJPrIuw6yTiWYfJbTHJzolEK4EZqRkxyJhUIYknkwIoLBBRRikKIgUVCExKnjUlMniPHFyy8uKuQexmZ9ZhZoMKy4isG1GXA0g9AEIGQrtd/lyaAnkOZGWAuJlSokoCpSJRVhdaoQgwM7Is7gCYGVerJnkeXJ6HZGhIj83MdJ+PnZs20fGDB7OtV+9c//d+8vUbfeH7vPfCDDJTgKT0yUc8ZN4u0DcwgEOPPY6vff3r6F+2DIUGCFMXS9cJk1Q2MEs0H8E8ESvFxnRS5LkM9Q/grre8Beo9JsfHYVb67jX+LYAi6SPLABiarRaqtR7ADIUvUK3VQMTw3kPEIctSFN5jxcpVuPtTn8Lx4yesd2ggNHwRmDmYaWBiT8QKUAigkLosfOGTn9PTR44llGSOgxAaOUkwpOwMpMEMhRJaUJsjxjQbTUMww0pNg/dwVVsYXInfA+OenW6oWq02KF+qwNWe/U2U8u1IaYc6G977xle6XXdcj+m8SYefehrPPX0SzDEYhiRysgdXr8T11+5BjRyOPXAQp7/zICgHLFfPgaYINCKGKUDzzntxL+Y7z+ycdl5z8+J5FLjMGOm833fYz4viebEWBfRiLdZ/RUSXk9ZnEZMG1/+oiWzM2zqAOGxYFEp+IcmuZwZAL0yVTJUsBLY0ZSvMwZSdwjShOVMatcKuENHAue89mvQM9bt9L7+F9mzZRHnewsTkJEQctLRzjJy/iEeYcfOe3djxkv1IkgT3f/qrYE/wIDgACRHQsRugg4IDdMHYnZV8EEVMQYx79fECz+JgGkBqSCRFEWKqGgUA9QJXHnkKf33+Erbffh123bwPL92zB8cGBnD45Gl4H73CR589g5VLlmDVlqto3TXbcfZ7h1wqaW/ibUUeVFNQMFAVqolqYOccCXH0AXQnA63b6Y1dp87nEWfXvaYRGxkCjL2CfAA8mcARmQezEjliDWRmZOrULCOiCoCciTJvFsQQxDmf50UBoGgXhesdGuLRsXG8++d/3r3/T/+M77zjZRi7fBnSWXQQdWfeFnqjhQjtxhxdCkF++d3/oDdJk/W/+Y9+u9Iz0Oeyag/nPngFgiV5IEBpgJ8norsXdWYzVbKGEoEN2iL0lr1ehkFLIodTasMjE6EKBCYxyBuqDBcs8QEKYhMRDdQmWK5AzozC1LwRsZoJOVYWCdEvAut0ohmIwvmFRBQqhbUqgQiOCEZMRqYIIcDgSZKAxMh7r1zaPFCQEZN6yg3IwGa0QGA9z1ZFaBvaZL4KEwBoAaiU/6sFFKlRtIBY3MFwjkhzgyMjVkMuyiZKaRJa7baSc0p5Htg5jdYWMZiZVKuapmmojI0pBga63edNQ0Pu2Nmzvf/4H/+TzevXrFk/MzubANrtORNsfuYRBEkSpJUqPvDnH0SjKNAvAiZANZTnM3e7+a5jTDGoiOSm8ETMTCQzY2P2U697Pd14ww24eOEiWq1W9FardhcwIQRUKhWYRfFcySpgAM1WC7VaDWmSYG5uDpVKBcQMHzyGhpag1Wrjns9+1pIsNU8IRhYi+S86i424YLO8kmbt88+ez9XnWaXSWynaeZoYiWkkDoagCtVAzG0CGmo6Y95miVCHUg4iqxSJVKp1N3nlYIKdOxX9/TLwublKK8kHmqG1WomuNrb9XJHrCyquVrLeG+76Kdl++36aKZp4+plncPLI09FjbgCcgxU5KkODuOmGa9BfqeLMo0fx+Be+DWqbIYeKcRFM5xJC3UgCNCULXiwERQ/izG7HKjRDhmSevsGO7TLzPL6uWn2x4JTFWqxFAb1Yi/V8G8chxf793KFx/LjOcxdjFwJFDkd7wXf7YSVdAFolSws278VEnGnbgcDOzPsizELsCuCWQX3t6S9/n/sGBmTLzXtx456duP/IUcxOToPSFKEowC7BuXMXwES4YfcebNq/C+wE93/mG7DRGXCaQps+dqoKH4NHjEqCgkB9QCcqG2rRKy1UbgmXdzeE2H80KzvWhgDt+jVhjDAyjaOf/y4unH4Ot73+5di7bgMGqlUcPnka49PTaDfmcPriCIa2b8eWa7fjuR88Ra3xdgbVJQLzatY2ox6FpUTEgJGaxvCGUqBFewSVVIaIE2GKyGMi7m6ZWxyUi0gQJg3eq5h5JVUmwIyZWBNTKDETa3CApUZcIaKq+Th26X18tExQA/s8z6XW18t5q8W/+Eu/RH/0f/yfePNP/zRduXwJZISIL1OoaTkcVnq0S8GkrQZdHhnhv/+2t1WqabbyV3/jf0ksKPcuGWrPNhq5U/GZ8Vyz6j2Bf+R5RsxmPRr3EGYB9AEIuhCDYcQVo8IrkgJt7yh1AcSJmpQ+Y2KCGqtDQopcQ8gNaKfMaVBlYpcgmFqEaD9vWip0UyCjToUZhOYnC62kFxuIwQRAlNQCp1bAq1JOBkosdjZzowwGNqU8M1MlZEYwo644bpO1yr9fIWeUsFGZythM4oq1iji92vGEmyrBfCnvJaICmY1cruRUpUCgNFVqtVSyLHCaKk1Pm6SpMpElzFqZmNBTAwOKTZsU99xj+/fvlx80m5V1V+9a/pOvf+1GDbrKF15sIXOvQ7Zhgg8eg4NLcPDRQ/ju9w+gr38AISiIqQu5K4kb5RxCOQLJpkySG2tuZk5AlTRJ8Pd/7p1gYszOzsI51yXBCDN8CEjKhMFGo4FqpYJEBK1mA329vQARms1G9EUTQS0gTVIML1+OL33ta3j08cesb2hAmz4PqhbApgYCESsTPBly5IX2ZikHqWS+mVfZUGFYakYixBSgCkKBEFoiXCfQJNimyFA3WO7MKGSUhnat0sfeWZqzb0/XcifLHCWb1Gw3i16nCW/PUaxAj6u+5Gd/irfcfA0aHHD0xDM4cfgoXJoidLz3WiDrreGmm67D0sFBjJ48h4fu+SowXgcKASsrzHIKmscgoZAYNDVvollQUlZotGsQ140ltU6Iyuj4eNyFSVNFkhgGBhSHut5nXbxELtaigF6sxfqbDBMuYEL/N/2S7mDKDIDa/DdaAFgZZpIouxxwQAAHy0E0q+0wQ8aDmPPJob/6NtcGemn13q24fucOPPzkETSmZ0FJUg4DEs6eeQ4A4dqdu7D+mu1IKhXcf89X0L44CU4Z3AoAU+xGl6zeDtqOASQlTqsIJZnD0GX/WknX6Gb5EYE74Q4K+LYCbQXXBFOHT+EbV8Zxzatux84bdqNvXxWPnjyNCxcv4dzFi9i4ZjWGVi/H2l1bce7A4y446eFgSwq1NpslMEtBJBY6M3naxT4QACkzomOXL2Kr+IVR3iAzUyOoCQBlVurw7pg1wEiYvWmI/Ad2SQihqrAeMirEzAzEASZk4AAjFiYzsmZeaJZmoWi36bf+yT9m1UA/89M/jamJCUAVQhST2zqIsi5mj2Cm8K1AE1eu8Nve8uYKiJb99u/8zp7py5f9wNLlrbY2ijy3oE3XYvX+hYNMC4ecAKDbpQ5KVto5iNnQVLOsZcSpogAqiYeFxGCBQGqcJKYFgWBMPuRB0BZBbkpeDR7ghEsjPBHF7L8Xi1ozij55io+tk4ApkaFGSgozskAaHGmgkAZyPpCwgqpGRaHIElCbDErW5PjEVr3FlMUSxEGOrFZaOVoLvOFAA9SKX7cAVCtKrQaASoUqnWNlRt1NDGajXJVNtOGccp4HzjKVZjNICOoGBjQdG9OzSWLw3jAwYB3xDICW3XorH/rjP+7/3/7gX2/etGHD2tnJqT5f5CyJxN0dKr36NG85IhF8/O67MTM7iyXLl6GVF/G4kUGIrOw4g6hcpQiBjNTMPAwhc4mbmZiUl992G992y62YGB9Hnufl+RQHVjUo0iQBsWB2to6eWi3uepQWDi79z84lkMTB+wIuSdHb34+8KPDJT30KCrVW8MGbeWYO3XMXZGzkTa3JRM2Q59EERFwhtRoRKsSc+hCIzBSKnIgbAGaYbEqDjRrLJBGaHmQwpI7aPaYpBUhvYrQGbLuC6r6CbSccrfaU97vhvuy2u15PW27eR9N5E4efPoETTzwFEkHo7jgZkCW49oZrsXLZMtQvjOGhz3wd4dIUyAusrSAmje1mkKpPYaiYcWqJE1LvIREhSc4p1b1RyuayKb08yvNzLB3x3NtbWvsWO8+LhcUhwsVarB9bhw7NY4t+nO/5Bd+35yUX9r+IujaCKlsIzlQdEzkwyBSewLl5y60wr+Oz9sA9X7Oxk89hVe8Art2xA5WeKqwoQGQx0EIYZ089i4NPHEYjtLFix3q87F1vRO/65VDy0JQgqcA6E/+leJZIR+6yjFlKmkIJLeNyK96VQ4foMJg1BjZqoeBC4QKB2wYqGMXIJB753DfwyHcfQtUS3LJzJzZu2oC5RhPPXL4MqTis272NuL9KhfpMYX1BQ38w6zFDokFlYW+u0wElJpBQvI+daxhztA7YvHxWi+YUThiAwAFGyiHE4cGCKbRMuWnGDTObI7YGOddg5jaZqSMiMhIyJMKUMMhZFGIAkRVFYZVazTzM/tH/+r/aPZ/7nA0vWx4HwhaEu3RDX6gzaAeIEBAKunzhAv3sm9+U/uf/+CcrE/DexuzMbdWkb48SrUxEapW+vkTTVKxS4ReK59h9LjvPtWgJ6ng6a+XntdLyQczKiQvkyluQUJh6b1Z4s4LEisSsIONCmAswe5iZginmvpPALO5FWBmSoqWvvnseRU99J8wmbhsYyjRDkEbKBrhQ8lIOPgbPzoW2d3Eo0jnt8T7UnFMSUWLWVpkISCJKuWjL+4A811qea0+7rVQkgUS0c2uVXyPPteV9IOeUkiSw94G9D62iCJIkoZmmoRTPweW5T2q1kPX3h5Hp6XB2wwaPa6/1OHbM49ChUIpnu+OOO+jgw1/Llm/evOpNb/x71wUf1uZ5OxGhuIh10o24jxw/Q29vP44cPYqvfePr6B8cgAZF4pLo3DAyR13ucxTS5RFlForHnBIypI5I3vLmt1C1UsH4+HjETBLBuRSmBGEHIYe52TlU0gzMgjxvI80yJIlDq9mEsCCrVlAUObIsQ5Ym6B8cxMOPPmr3P/SA9Q8OqfdFYCJFHMI1LkVqUA0MNJlomgJGE9ClFHwxYboIxYiqjajhEohHjHARjPNKdC6An4PQORG6bIxZ4qDiXIasOpDn+Woi7ADjVu/Dy3KyW5DJVm/FcLqiv/Ka99zF2265hmbaDRw9cRwnfvAkxAlQcrZhCiVg//XXYPXSpWiOzeLBz3wDM08/B9IECGwCNg4w9WpC7MhQg1nNESUwI3CPUasUz8zGzqmkaRTPndTBSkW7vudo3dBFAb1YiwJ6sRbrvyVUJU1//A0d2tGLe6Wpy/ptdpPnksQIztgRuRCQMVxFgJQBISVQASMvWlyYwPc/+WVceeY8Vg0M4brdO5HVMljwUZx5j6SS4uLZczhw8BHMtBoYvGoFXvYP3oRl+7ZAUUAlQFlhzJDSi8kUKQFaXsGfd2mgBd5jAFwm0bGW+LIQun5qjhnOcG0D5QSqexz76vdx35e+C9Tb2LduA65adxXOTUxizudYsnoYfWuWkVfvCrIMhpoZKiCkBBMttZiW1hEqfaK0kJVGBBF6vv+2EyKhisi6C/AUzFOwRMQTfM4eOZNvM1GLOGmZ1xZpyMnMR/1LwozECSUMJEJwMfKvZFMzWSNvq8syVSH9jd/5HXz4Lz5qwytWQKFxexnUHXjsYM1KLQ1SBUKg8889x69/zSsrH/noR1dbUdw0ceXKS4Z6e/cmwBprtwfSEDLNc7FKha2nh6ynJ4rlUCOEGvUUFTZf4R6tUY/OC+kaADRKDB6zUS7K3oe294GcDxxcIAkhc+oJrggmnqJw9hFGrCAjhpEjUFJuPRDK+y9EeD4C1xC0Kx/LxY50u+YiYkm0UCg7F0hEOY2CFnmuzVbLuN1WFlFqtQwtNnJOa84pOadgNpJce4isV0Q7IpjK7z/vlqaBkyRwkoRWUcRbkoRWlnmuVHzTV72E4F1Pj3etVkh7e0Nlejqcn5kJuPZajwMHAu65J5RCqXOj6t69MnHw1OC73/muzdu2brmuOTe3nDi+iEW45GGXiSjlMUgrGT700Y9iYnoa4hyK4MvjB3UwVTUzM4uvQQaLIyamoMpkyBKR6sz0dPWaffvca1/9KszMzCAvchgMaZrBFwWcc6hUK2g2m6hWKsiyDK1mE2mliqxSQWNuDkkiSJIErVYLSZqAOXqzs2qGD3/0Iyg0WGGmxKxxBNesCL5zETYhCmzUZmCWQVNQGyMNl1lthJkuCtEFEToHoefEJWeN5AxAz4rIs+SS53LFZSbUCzgEtV71xSpm2W6mN3gNLykY1yDj1T40qn1bVvOr3vt2WrptA6abczj05BEce/IoOEtjo4AIIc9hIrjhphtw1bKVoHobD939JYw+dATkBdSMi3o2NgKM40xpVZgHmKjP4DOkRtRqKadp4EZDudkMnCQ66pw9L7J7YECxbJniwAFdFM+LtSigF2ux/jbR3vPRrfhxXejzCzBI89+Yn+THXOc/5IYcgDnyWiSGUDVYnwH9qqFGhlSMGS0Febb22Ss48BdfwPiZEVy1bDmu3bsLWW8N5gs4ERTtAlmSYGLkCr5/34O4ND6G2vAgXvb2N2DjnTeiEEWBApYQcjMUGr26iUi3kwuKjUdw3IKOjNr47465TDjTkjlFoKBxiC4oKMRAC24ZuKmQFuH8fYdx4HPfAmbb2Lf2KtTSDM9NTqCnv4YVG1YDjkhVE2NK2SzV4EVVI3bYLHY2Yzu/HBAst8eF0QmaEJ6P8u58FCao13mGMJEG1sBOfHCuCDF+JFcgJ6aIcSNSYyJjkhjPgQRMTpkdEYkGL0RgiCAQWStvm4hYUsnsn/zv/zv+8/veh4HhZdDSk8rM0HK4q2zfRlqIGqABAsPk+Ci97LaXVD74gT9f3VfJbhm9dOUV1ax2XWG2Li9oKHGumpql1WbT9RQF91Qq3KNK5j13BlLr3nPde65mgeshcKPzmFvR89vhS9dElP2CTnSQ4EMIUPUw80SkEhdKTGSOyRIYEo52OuoMu2nHu1t2WrUcR9X5NRgZQBy97N338eh9bhvluTbbor3Oaa+I9oood7qAIipJEbjd1la7rdxuqxRFaIpo0zltOKeNVkup0TBqtfRFb3keKM8De+/ZVz1lWew453ngLA9SrYa0KHx1aMiPTE+Hs8PDAbt2Bdxzz4sLpLe8hU49/HBWGRxc//fe8FPXMGhj0W73xLhuooXJMlLaXaq1Gp48dgxf/MqX0dPfh8IHGAh58GqAGnEwgoLIjAhacnCiexoOQIUMNfNF9ta3vIWX9PVhfGwMWnhkWQbvPVyaIkkTzM3WUalkSJIE7VYblWoVLnVotppglyDLKih8Xs4MxNf3kuGlePSxx3DvA/cjqVTM+yKelV5NgxpYYsySwcQQAMtDsCYR6sw0rYSJALusQUcIOO+MnxO1s8HwjAKnDDjNZGeI9CLDJonRFkMK0+UgutqYbvBmNweHHValpR55turWffzaX3snBjeswtjMJA48+BBOP30CQgLzAURA8AWkkuC6G6/FptWrgXob93/iS7hy/2GwF6BeAEXEcFoIUFMiYRc09Hj1Q2YYFHEVaxmRiHKzGZKenmK6p8ePz8wETEwoKpUFnudDHfFsi+J5sbDogV6sxfpbeaHpbySiy4HDH7JqoH9h8IcZkVWoYg0EiBmLcylUexU0ZIYlpNRHjjM1CBnIWgpSoDh7Bfff/SXc/nNvwLpNq5DsFTx+5Cjq41NIJYHlBVISzI5N4oEHDuK6a/Zi7bKVuPlnXoXBZUtw+Et/jfZ0Cy5LkORR4HVGoMQ5+BBAna15ImhkakHKGGemeJlnxEjtTteXWMoJMwWDQZ6hOaCkGH30KTygwM0/+XLsWrYc52Zm0BrwGF67Eid6UvJ5mzMT0mBgYlJEP62WaX8o0bpM0XNrZYx0pA/H7exumEoI0OAjf1jYQKQAKVJS5FBPFEg0WM7kmSnGfXMgC2ZkzOREAWdkiQVzMEugwYHA5ITNjLTT3Sa2oKpOHFyS0D//vX/BBsV7fv4XaGZiHO3CIy3Z3VFwxmMULMCJwDlGoYHGr4zwq15xZ+1P//hP1vz6P/pNN3Z5pGdweNnSNudPEvMZUp321WqLVT0xGzWbVgOgVaWqGplWSucEUNVGp1MfdzvaAFBgTpWqZoRKhZDn0fdppomqBSJFR+lGeoWDWWJAFkJIfQiOAIYpdTy+3d0BWIcaDXBpten67BcM1xEZqmRkZE0i6y29zMRscwuGH8FsPSUTmxZ0Ubq7N6gD8/aUHz1o2V285hFzl2Umc5kK6uqc03R6Ws96r1izRrF8uf1I8QzQHbVacuDgwcGf/9Vfv2bL5i03txuNJYC5OIgb76FHiIs6iuz1ak8v/uITd2NiagoDS5ciL7wZs0FVOUmCRusGE0DaOZ6R9U4IngFK260W79u9h3/m770BU9Oz1Gq0wCyAGZwwqtUK6vVZSCLIshSNuTm4xKFaraLeqMNJ7Dw32zmICIlzYBGIOEia4C8//WnMNubQv3SJzTWbCqYAZnVCxkxKxkqEAMAbwTMhN6MmGRqAeQYBjgEF1EJhzE1S1EV1VlOaDUotUvOcOCnUeh3pMIi2BbU9BXSbZXKVORtQ0WTbq2+jm37q5aCKw8j4GB5+5DHMjI5HbGfuwalATZHWKrjhhmuxZtlyNMen8chnvolL9x0GFQIrFGQchzFLYg8BTKaJmtXIySCJDJppFakRaaJppeJHJycVIvPc/zSNDZNDhxa7zou1KKAXa7H++7vQvc9/E91f/9EDhSLGo6OG/v4fHgDjDmCZrYWWESXWas8xeqppkiZ9wesQAg2xWS8oWjmCgciI1EcPcH76Iu79+BdwxzvfgHWb16Ln2n04+MQRTFwaBRnDfOwU+rkWHr7/IGZ278COrVuw644bMLxiGPfe8zW0zl4GpxVYrhAtbQ8ApBOFTZ3MQiwY0rMSbzffle5wgcsfAYNh3hCChwWO8brVBFcePoIHCsXtP/NKaK0P03NNLFkxTOlQP/LpURTBKKMOjYC7KszMyt8tkWzBnRTCeQ/uPMKu9G4TG7MLCO0QjJWVjFxEpSWAeU82T8jzMBGygtgA8SEkwpKycBLMHMXICwmmzEQUyueRysVFMMC8N2ZGpdajv/vPfpfnZufst//Rb9LElcvwagvCXuJiIAbcxAUAkcEBNHrxHL36lT9R/diHPrjm77/753umxyd6h1es7JuZq9cgeLYSwpipNvNcPCWJErPFfBwlLBwurNUMzKB22xoLAll6VamuSlVuMTg1UNuArPTfmhGpBWNiZiYiR0AK1ZQdJyLMsatM3chpKj3PUavY/A5AZxeg81ySm/ertwAYGZIomnvKu9wDYG6BIG6UuL7OZg0xGzUa5fcdyLHRC21SLxDT7JzR9PS8rSpNlWtmlaFl4ezoqGLDhh8nnMv6PRo9/o1aNjCw9a1ve9t1WTW9emZyMkslohQ7D5pFAIrHplar4dlnz+ArX/0KenpqcSHBhLgGFTU1JYYpCXG5KC1fS6TxhcWpExodG6e73noXrxgcxJlzF5AXBZwTmAG9vTXU63MQEaRZhrlGA2maIssqmGs2kSZJ6YUuxXOSgSU+EwNLluDpEyfx+S/8FXp6esznhbKTYAQlJmUjhUENpI45wBAC4InIQ7XtiRpk1HJmvgACzBfM1FKEBombIydzqS9anFDQ3DtP3MeMIQZv8SFcVzB2mtCqENq9PNQnt77l1bTllj1ASjj+7Bkcevhx+EYT5By08JA0QWjnqC0fwi03XY/l/QMoZlu4/5NfwfgDT0JCAouB8WAzJEzw8SllA8EYjh1X81D0o9kc4qxac6bMzunozExAT492LXjVqqH3kOEAFlF1i4VFC8diLdb/sGCV5eWb6YE4XHjoUBTWvb3zNo/yjXhk4Q/3luznjvhiNqKmEZPlVLcdN+6lytLetEDRRzUeREX6LJUscgiISZiiz5iB3ECWID8/hgN3fwkXn3oWS/uGcMPePViyYhnM+6gL8wLwAWLAU08cw4OPPIqJ5ixW7dqMV//S27Dyxt3ItQmfApYyAgztEOA1RH0vAiZGKgLHDGHuxn0zcRwsJAaXaLk4VEagUo4IGBQMrAw0PdgLxg49hQf/6tsYNkEPGNVqhqHlQwAbcSKlijeibiYbR4EaD1pXRHcyo5mo7H7yvHWjFKcEC2QonFkg5oDACiIryHf953FhwxxUhYUcMdJqlmUucSkMTlwi8Q8zG4ihygwwEZUqs/OXgaBqHrCe/kH91//63+Df/Jt/a0uWLYOxRKtMyU2O5ATpUgSom2BIuHThHF17zTXJJz/x8aHVy4b3XDj77Et7apXbU3I7FVitzP2S+IoyO/OezXvGgvNqodeendPeF3RpewAQ93Y7v8hzFN11BxOCEZM4iDgWSQ2WskjCEYpLXTfNgoHBDnGigxzkchEGja5vVeMAUOfvNGvz9+WF9xmNhqG0ZnQtF3keqNWat3gkiVKSKKdpeZuLFI25OZW5OXWtVnCtVuB6XSVNNanVQmdIsDI9Hc7W69GuceCA/njxDPzSL43IsYceWvKK173upmv27d09V68PmKn4Dqqw3MFZ6HWv9NTw2c9/HhcujqDa0wvrUMENSkzBYKZlCEpn8ckgCDkzNYgIz9XrvGXzJn7ta16NubxAvV6Puz9q6Kn1oNlsgZmiPSPPkaYZ0krWFdlJksB7H88tEVgJJU+yDGmlgr/89KcxPjZm4px51RC56QisqmSmZKpCFIKRN6LCkRQMLgySs1HTiGaD2FQmOpawXGajEQp2KWO9YgVPaEqzhU9aIDI26yWvm9oh7PNi+0xsbQit3p5NK+Tl734Ttr3kWjS0wCOPHcbD9z0MP9eMsdwhojJDkaN/eAluue5aLOsbQnN0Bt/98Gcx/shTYEsRmgoKHAebNWYJgZmUgeCIgiPJtUhry4d69r/ypYNSTSq5gWakHocE16wJOHYs3g4dUhx4nv99sRZrUUAv1mL999s47sHf1AcNAOOdLtnMi53dZGBRzBW6ae8OvPd3f9WtuXFnVTPqsZQqllDCmZOQRLnWoR8QGJYrqA3kz43ivr/8Cp59/Gn0J1XctHs3VqxbAws+MpzNYCGK6JEz5/H9Bx/BsyMXUF0+iJe94w3Y+YY74WuCBhdos0cQApzr2iWMAF8OhnUBcRrtHDE2mOdpE52Y8HKgkBUwH+CMIMqwpge1DJceehKHvnEf+gogI8bQkqHYwWMq2a7lKFpXbPIPdW5foBafb+0ghqkhmKmw81E8B00WiuZoUyBTZbAKS5qaUZXY1YqiqPrgsyRxiZo6NRVjoqRrtKbS4sJkZqVbIh4DU0UgoG9gwP7oj/4Iv/+Hf4i+wSGwS1CogVji8zdvzYaU990Jg4lo4sol2rtnV/KRD/553/YtWzZNjFy+OXXuZULJ/kJpnREN1EQqCVGSpSn/ENruhaJUxChJdK4jpOfmujsiaZJQYkZOjEs4tsBMAjgBOCGQIzMHYon4b4MqyiFN6wapxOd//nnpdKKhBgZDIEjK71VRQ+1F7nMvEKkiCz8usG5Q+Tg4TbXTXY63+D1JU5U0VZdl87dqVZNaTSvT06F/ZiYSNiJZ42+8NX/g0pEKKpU1737Xu26qpummot0SiuvZGIZSets7gT6VSgUjI5fxFx//OHr6ehHK553nYTIxnIg50kw0mMCMAZApHAscC3xe4K43vRlb167B+NgEiryAOIdarYoQFOoVWZqhKAqYAZVqBaqRQZ6kCYrCIymZzyzlglMiiePCpRF87nOfRbW/H4X3FgyqzApihbHCoMIuCHFgQgBRCDAfgIJI2mrcZFjDjGa8t0n2NEEOE8aVSVhlpuZ9I52xHNIwoWrNhNcEtr2U0a5Cwgqf+NraO/bLnb/4Vlq9ayNdmhzDvQ88jKcePwLxBhjFmFAYrPBYsXY1brn+OiztHcTMmRH89Uc+j4kfnAZrCm3G2Qt0UlU55jp6GCwTWArSCmTtS69L3v1Pf62y55breop6PUsBoJkGrFkTFgwILjwvFjvPi7UooBdrsf4Hlc53omHAHYi3A8ABAHfcge4WYGnjWPajRA1zxCflbUWlogcevNfQ3yNv/PW/n+6/6zUVWTOQWMUkVJksZfIWQEkShZrG4AhrK9AGigsTeOAvv4pTDx9Bpoxrt2/Dpu1bEMhgGkrBqEiFUR8dx333PYSjp08hT4BrXn8HXvKuNyK7ailCoghVgXeA8rwUImYYWQwbJkIiAunGlcQXqWOOA4Y2v+vpQ4ADw7yCFSAfE83ZM5478CiefuBx9ATGYK2nDGuJIiSYIaiWkdyhHFgszQM8H+fdEfBAyVkuSSEhUg0MZkERfGANlLF6IitK4Zw4I3NGJspG7Mgsc0lSg4bevt7eWsJSyfN24pyIMRPFtiExl9YSZjIiEiex/0pECiNxEmUSk1UHBuw//rv/y37/D/7AegcGAXHdoc3Yuew20rutXWYgcUJjI5ewd9cu+diHP9y3Yc3q9ZOXL+9PHb8kI96fQNYFk0GfpqmKCCqV5wWosHPK7bYSs80lidLcnBGz9XWSDKvV0oeRctvacSFhxmImIHUBGv3PpglFL7SQWWnhiM+3Wkzb1Nh5j89VnDfrgCjKN/CIsQsLfNBNVWq8GNMaAM2VHfPZHxbO8bHNzgvnBaKZRYydM1etKieJcZJYUqtpOjam58fG9OzwcDj2tyApEBGOf/Oxode94Y3bb735ls1zjbkBIiKDUSe6HDbfhfchoK+3Bx+/+xN49uwZpJVqHB5UNQKZMEXCCbRMW7RoRWFRi4N6KkxW5C2sXb0a73j729EsPNrNBkBAlmVgiRznSrWG4GNWUK1ahS+KMmk6QZEXSFIHH3xp29Ay3hsYGlqCT37yk7h44QIkTcxDgzF5VSvIyKvCG8hD4WEoDCjiBgIXqporaZuYmwab0+BnkcgMpemMtrneo9qY7B1rjy6b8zHXxtXm0FoTOFyDnnRPC8VVtKRau+5tr+Pb3/GTVFkxiOMXzuH79z6Iy888BxEXdy6YQRyHANdu24xrdu1EX1rB6PEz+M6HP4vpJ58BtQnWCBBy5U5IFM8BBk0ZqDCUCqLlvdj3ttfSa37hzZKsGkruO/RIBaHgEk/3wnNi0baxWIsCerEW6//FTnSnN1V+fkfX1fHCGn0xhB1mQPW6zTEbSa9mlYrVx0b16OmnMI6Cd77mFnn1b7yLh1+yh7QCmHiijCnGMQPQAPIKNgGaCqoH4OI0Hv/U1/Hkdx5GpSDs2rARe3Zvh1RSaJHDzJC3PcgIKAKePPQD3P/II5hu1bHuuqvxmve+Datu2g1PbeROESqCHAoji3gt5tgElkjq8BbTDGVBwElHUJgZhBiOIjNYAFAIEDASb+CCQDnw+Je/hwvHz6E3qQGIw4xU4t/MELdvzWA+lAKtgxfuxEdH/B6XVo+Ftg4DwbFTUgqkHfuGt4TIEnOcl/xtBBYDEm8hY5Ha9ORU7x0vfWnPB/7sfVkKckWzxT3VKnkLBGHACYlIHOSKNDoKxKQApy5hMmZmoZb3IBL0rViO//x//Qf89m/9DvoGBiFpinaRA9xhbb/gDa8MtalUMhofvUKb16/nv/z4x6ub1q9bc+X8hWuqWXar+XANUVibAP3BLMnKgbvOYB2328rO6VxrXjwDs88jwnTFqyVkztibkDGzmTk2cmRwMJUY4Qe2ks8SYnIKMaIHOmiA90VMWTTtrGHKYVMi40hnkRDQCS+sAqjG7v/zbE0/hHt8nnB2JnNzyvVEScRIxDod5s4tqdVUksTSsTFNx8a0MjamZ3t6FJ0kwQMHwn/jljypKqHVWvOOt991Xa1aWZq32xIvTAyh+LogJgRVBFVUqz04c/4C7v7Lv0Sttw9eg6G0a4BIqTOvS0RK6BjFVc08C3kDvEucztXn8La3vBUb16zG1OQ0Wu02sjSNlI2iDZe4cpTCo6dWA5l1bVYAoVKtIC/yOGirCpdkMCP09vXj4sURfOYz95gkiQFkqggWQmFmhZnmRFwKZuQGawPWVtMmmbUcS5MDGhbCnHiqO6RziRXNIs9bFaK8MjQdcCGxpUUlaVQq/YXKhpC5/UXKt7SKuU2DO67qu/MX38q77ryJcmd48uQJHHzgIBpT0+AkRSg6i7EAY2Dr7h3Yt20rBpMKnnvkKA584B60j58HtQw2VwC5gsogKQNAqQBVB00AqwmGb9mNV/76O+i6199O0xLo3KWL8tzJU4wkMWppgZmZsCiWF2tRQC/WYv1dpBPiwILbi9To6HwnrV4vb/Hr3jJJDcKKektPHD2hORd4rjlDA5tX8mt/8a20/+2vpWzzKlhmsNSABGDHgBBQeFChsIYH6gVosonT33gAD33xuygm53D1ug24/rprUBvoh/kQhWZQmFcICy6fv4jv3Xc/nr14Dn2rluAV734Tdr/5lcCSClrUhtYEljoECxGEKxJtIVSiukoRmFAUfggBrrQ3mCqkE62tioQIKTPUK6gI8fI808Lh7z4EaniwSbR8qJX2D4VjgnS7zNEvKh3fbSnopeRCcxleoig50CIAw8AcPLNGz3M0ERQAElV2KiKsjskljqSaJGlvIklvY3qm+qpbb07//H3vSwZ7emRuapL7KlUSljL50Mr4ZIFR3C5Wom4XMpgRkVAAkJuhd9VKfOKjH8Wv/vqvASKo9vWi8L6M+p7vdEbHMEc6BzMSZtSnprBl00b++Ic/nF67Z/fwlXNnd/bWqi9JTPYwsDI116MlN42dUymKwM4pJ4kO8JxRxy/cSrTT1e1QYVJVSs0I5siJUbRwkBiRY4IQsYDK9ntX6YXuTgQ9777Ps8INcaGlVKZIludL3n1RNGEVpR8yQb9APHeGAtm57sAgd4RzlikniUnndvmyyciIVcbGNEkSS5LETqWpYdmyTgz3fzNJ4fd+z4iIKm94+9vX33TzzfvbzWa/CJfR9db5gBACjAjeB/T29eKzn/88jj91HJVqFaqdQcuIsrHuadLZv4EawTNTYYq2CBetZkOvWr0ab37Tz6AIhlarCZghyzKoKpxL4JIE3hdIK1k8B5lhxAAznBMUeYEsySAicEkCYQEJY2BoCF/52ldx+sRJ9PQPwOd5MKAgotwR5URUANZmWMugTYU1YdYw07qSzQS1WQPqAtTVbC4NoZE3uS3NZgCA1uSADPT0VOeavETht1qvuzNw8Rrvit3r79w/9Kr33MVr9mym0bkp3H/oEJ4+cqzcXSJoXoAcw9QjqWa47vprsWfb1aipw5Fv3IeDH/kr6MUpUOFgjQDykfgTVBGIoA7QlKCpId24DNf87GvxU7/6DizbsR6np0eRm6fTp05TPjapzK7dBtpYscIvCujFwiKFY7EW6//zLjTNd6A7Inr/8/7jsmXLEPL8+faN7ud1I5cpmBWB9PKzz4Xm9IzaYNXuO3US+1auxL6fuBlX7dqGw999EGcefgI6PhsvHErQtge8db2mph6UF7j0vUN4YHwa173mDmzYsBo9N1TxxLGnMXZhBCQR56slo3huegYPHTyEialp7N5+Na573UuxYtM6PPzZr6F++iJSTiAJwylAxhCNxF9XDhQGhOg7JAZT7B53vKAAIMYgxOGy2I0uvY2mgEtw8eRZUCvEFEMfwFaGjJjBQqmIyw43UxSYzBw9yERgBjQ6SuPwYIkCi4OOokRBE/IGuBjNDCABrCAyBwAmJKTOAtLgiyoBVfVFZbbVSl55223y5//lz/hXfu3XeXxikrJaDS3vY4R5GS4TBTQTmSGYgRFpC8yMoKG0CSt6VizHZ+/+JIL3+L//7/8Al2Vo521kiSv5iFFoiUu6JBEhgjimibFR27ZlE3/0Qx/M3v2e9y49fOTJq5evuardLuCDIQeZV9cbGHno2Da41VIkiUmWqYVA6j3mXFNrnMZu9QI/ePlWS+DACMaASUQnEkONGcSOiMtlQvSX0/Nc8ZHOYhZFc8eTAkIo7S4BQGIJLTBzRLzGC1skfQsY6QtIGiRinKbGzkUh3RHOIyPxOa1UDABOdfBjANDba38zysaPqn/JAIbf/e53b1q2ZGjt9ORkFuO3IznDrPQvIYY1VioVjFwexcc+/glU+vpQeIXGhZ+BYheau0mNRlzuGpiGQITCyLxzLpuZGE/e9fafxY5NGzExU4cvCmSVSjyeISBNM4TgkaQpxDloOWhHBDAL2u02kjSBBg/n4iXUpQnYOYyNj+Pjf/EXoDSFL7yyiFcgJ1iLgZYheIACMedgaVrwdRaZZuZpMpom0IxymFWhRupdq9lseqlWFb29aLXbSZEWFRS0QlLeXji8ZK41fYMsH9qy9/W3De5+6Q2SO6JnRs7j8SeOoj4xFecWQmn7SQSmAbXlS3DdtXuwaskyhMk5PPKVAzjzvYNx0V0QrMjB5AD1UCaQcwApTAugvxcb77gBe192E5avX4WJ5gwefeoZrF46ZOQdXTz+jKLZbkJ66uCkWWLqFmuxFjvQi7VYf0d0jvjZ/v1RUDebBABrAbAbt473sytcyhs3nFJLtD1baNLXG9pnLhQz5y4Vq3t6w9z4hH3zm9/FkVMn0LO0By9/2+vwqn/4Nqy+dS+sP4VxAUoJ5CxePEIA8gBrBVDLMHPoOO6/+4t49vAJLKn24pbrrsGmHdviJD4CIKVlQgREwImjx/C9hx7GaH0Sq3eux6t/+R3Y+IqbkSeKpgQUFYeCYqdHnCBoKNFlPE/IEFfyhxkRWFHiryM+OHafSyMte0PFGM4TLp46C2q2oxXEoqeTyjjuoBpZ0KByoLAjFDoBL2U3VLjrv3XltrpqMLAFUgkkIRAHJQ5aMGsaWImDIgRDCCCGg2pq5rPcF4kGdaPjE3L7jTfyX3zkI7xm1UqqT01SNUlIQCTEJcFNiYQBEShF73gcvrTYrY9YMlIz9K9ejb/67Gfxi7/4HhgLqj29aJd83s59Z5ZSZMXHGnxA6oSmJiZo+dIldPfHPprecv0NSy8+++zu3qxyI6HYK8ar+5zvDUDS9Tczm2SZdnjInS4uiRg1my8iJv0C36+wAhxgAjMxIrbosYl9U4pCLnqfCUoWJ69swbBpnDiEA1F5EsTWf2YUTRzoYjiex3KeLfnNpW2DpuftGuxc19vcEc8Lu82nBgY0IshKKk4Uz38rPysR4V/9q3+V3vCyl+28Yf/+na1Goy8aUsqhzw5OMcZuo/Aevf39+OKXvoynjh5DX19fZH+boiiKcmEZIy6hxDCiOMiqlrAENfNkFvJWy1atWEnvePvbSQ3UnKuDGKhkGYIGpGna9fqLc3Gx6OJ9SbIMeV6UPHQDJF4+XZIAZliyZAm+9c1v4sjhw6jVavAagg8+Z7YWCC2CtWFog9ECU4OYZ1ncFAvG2TDOhElTneXALW5ZQczWU6lwlSgBt/sko9WBaG/e6+5scXhDXtRfPbh3455X/MO3LLnmFTdLgwo6/PQx3Pvgw6hPT8OlSXxNC4GhMA0YXrcat9xyPdYuW47G5Qn89cc+jzPfehDsOcYeeYApCm1zAKWAoQ3rFSy/bS/u/LV34OVvfx2G1y/H8bOn8fVvfhsTV65gWW8fJkfGMHn2YgHlUQo8jpmZ5mL3ebEWO9CLtVh/Zz5o0I9GQYsVlwvQoBir/tCFXEMAmK0KqFfvMdNoP3f0dHP13u2tTcPL9dGnT+Lg/Q/hzJmz2LtzBzbs2IA1G9fh1JMn8NS9j2D08FNA8HGwDoDmATCOIjohFM9exsG7v4iZV74Eu26/Eft2bkdPfy+OHjsObbfBicT0M6+QNMHElSv47vfvw85dO7Bz02bcetdrsebqzfjBN+5D/fQFSOZgnlDTmD4IM4SSt9DpCKt10vZKIYkYqmJsUbDHr0AiEIt/2zEjqAIaRRmXVAex6FSJrk7r8qiJGWQdkR3/rTPARihpFlDATLXQ4IDAZEEDowDApsFLMPVMzBSCQgkeTKkQLBGDE4JM1etS5Dnt27mDPvGxj+G9//CX8cSRJ7F0+QrM1usgU3MkADEFKIgjmcI603bUEU0xgKZZ5Ohdvhzf/uY38XPv/Dm8733vw9KhIczNTKNarUbri8UOrRMpbSKxg83EaNZn0V/rpY9+8M+TX//N31r2lW9+c9/6LVukkbdQBLUsyPk8b2hvmoZGx1c8AWBJKaLTVOtzc1x1zojIcrRMNLWUgxYgCyGAAeIYLlMSAokJEGNiNSOvBrb4XHa6G6oEM49uQ7bcLegQUqjzkknmLRwAAXOIPGdmm2uwkUuUk6DPF8/TttCuAQAyklmSXLBTSYJu4EXvAkb7vHDG31YgfepTn5K3vvWtA7/+a//LzT3V2rWN+kzSXTJB53ddWBBUkaQVTM/M4sMf/jBckiDP8/Iclo4/n6BGkYEIGEvJrS6FdFBK05Rnpybl7W96M+/ashmzjSa8D0jSCkwVSeIgxChC6AaimMbjnmUVNBuNaKlKUwTvy4VkvI8iDu1mC5+8+5MgcUbCRqoeTG1VbRJzS01zMBVkyDXoXEI6FczGTe2Kmo3BMO0EDQvwmiTsw1zmLat4a1cpuKVt5k3I5HpfNPajJ9my+aUv7bvmVbclAysG6ZnLl/DEkWOYuHwF4gQmglB4cOqg7Rwgw/qtm7Br+9UYqPbg7BMn8NhnvoHWM5dA6mC+g9iguHARAJYDqcOSPVux585bsenanaBaivOXR3Ds6FM4/9xzgA+4ZutmVCnBc+cuo7gy0ZKsdoab/ko4f769KKAXa1FAL9Zi/U8oos8CWMVsPDFhNjBg1hn2mk9JY2s0NPT0KOUoQGnj3JFTMzsujs+tWDro+waHrD5yGVfOnsd3Rq5g3Yb12LF1G7ZdvxNrt6zD2SefxtP3P4rxE2eho9MgF++KqcJyAgKBxmbx9Be+i+mJKVz7mjuwfdMm9A304fCRo5ibnAYlDmRACAZyhHa9gccPPY4r4xPYe/V2bL15D1ZvWIOHvvzXeO6RI9CmAp6QutLPrHHyPRqQtbRQRItGKWPjQFC5fa0wWEmDMw1gYrBJDKSAdoWZlr7GDuGgK5SJIExIOkOHJPNGgnKQKHgfO1Rk5kiVOAkUVH15/0g1gMTYBfiCvACezEL0mYBUjWHEGgLqM7N0RRw2r1+HD3/wz/He9/5DPHLoUQwsHUYrbxFrHJxLCMjRucADbLGbzhR93D5ET3ir8OgZXoZ7DxzAL/7CL+K/vP+/YMXwMFqNOVTSFBo8pLR/MHXiwKm0jRC1m3PW09vP//mP/2Mqv/lby7727W/tGV61Rjyo4iUgpdq5XHPtKYp2M02VlohhojxEAwsGWYkMLVZKWQuvCmYVMiUjMIG0RIt4GBsTgziS+2LT9HkvgMjqZZiFuLjpsqGZoFZuSTCKgiwJZEgBNOJ4Ync+wCVKPGfgxBbaNjriubsoLbvOp4AfFs/LS0b787vOf6vu82/8xm9k195xx5qX3XHHLu+LdTDj4L25xBFKfnP0sBNCUAwt6cenPn0Pnjh8GD2Dgyi8h4ib78pHPCMJlcxCqBFJfD0ALnGJhSLQQG9f8o677hIG0G61o/glgjdF5lL4oogDukkCDQWEBM4J2nkOYkaWpvB5Dudc9F6LQFWxfPlSfOnLX8IjDz2EWn8/mnmuaZIUgaxJxnWoNYyRMyg3siYpzQTVMTIdhcpYIjQdTBsQUWGkxsEJZ2kLOhAIa5Hx9kB+t4Z8c8/VV6244XUv7dm0bzs3LccPjj9NTxw9Dt9qgZMMGvy8Tz4EZIN92LplM9YvX4lMGUe//RCe/Mr3YGN1EBJY4eMbrDAsFECRA0v7MbRjO66+9Vps3LMN/cMDuDw5jqM/OIlnTp1GmKsDzKgsHcSyJUvQmJrF+WOnDY2izuZOFG29ssh4XqxFAb1Yi/V3K6Kp+/FQr71YOiEzm5ZDUAuHoQDopPfck+chVKhwWWXOP3dl8tLJs1M71t6QDw8P2+yFy+DEQVseZ48cx7nTz2HLlk24essWbLthL9ZdvRlnjp3AswefwKWjp4DJ2RIjRoA3GAmoUWDkrw+iPj6B69/wCqzeuAa1G6/HE8efxpVzF2AuiezUoCAXo6YvnDyNifEpXL9vDzasXIWX/exP4umNa/HoF7+L1tgMNElBGrUQlX5dpehZdmW/WEv8XGeJ0WEFwzSGrlB0n1goIHEykGInOw4eQgSmiF5SLTnDHd5yecg79gfVaH/oxI/HXjeUIN6rBk7Uc3AM5CiCBIio+cLEuCCiQoMVpghQmKqxmTLA5AvF9OQUaQhYs3Il/vz9H8B7fuk9eODgQQwNL4UPocTuxThr7QxEIfKP2RS5DxAW+OBhZii8R9+KFXjg3nvx7nf/Aj760Y9ixfASNOp11LIMIQQQRZuMcFwoBPNIkhRGTHOzM6jUevCnf/LH2a/82q8u/8o3vu1WrV9P7YKoYA/kokVfn/a1WjqbphrJ3OjGWxOzcaulJqIcQiCRgBA8Ii/boByfMdU4QEjEasroRLcvsGpohEJDQ/R7IyjgOrsG6MRTW+IcXBn7DlRBnBs7p3PM1t9KlJOWghOTuUxJprt+527n+Twg8l8RzwcAYKcB/wr/nRgyAmAjIyNLf//f/8ebBwf6t85OT/WYKsQJqRpSl5TEEYMPBZLEYXJqCh/80Ifi4jAa86PbuzTvEzqd59i5Li3LlCYphTy3arXC41eu8Nve9KZk744dNNdokW+3UUkSFD56mTtDmmmSwBD/fpZlaLdzaFBUa1Xk7Xa0ZXXIOcxIEod2keMzn/ks2s0m0sEBo3YIXrXJJLMBOi3Ec0yIPmiTWZBNmumYEY8bY9oITQKZ+lADS8UMA00KKyTlq7SabWy1GxsxULlq660v6dv3ilvcwMqlNFmfwiOHn8C5Z8+WA8gCbefgxIGg0OAxsHwY1+zYhuGBJfCTDRz82vdx/nsPA+0AIgf4EHfKfCvm1C8bxJo912Ht9bux7bpdyHoquDw+jsMPP4JnTp5Ca3Im7shVMmieY/mSpehPq5h8dgRjp5/LAZkUDWcL1anFy9diLQroxVqs/3mwdvTCIUIRMVUlnhDDsnkhMwpgKYABIgsiSloUkMoc6nPjZw8dGdtx077m5nXrwtkTp53OtSjG/DJstokTjz2JMyefwYaNG7Bl62ZsvekabNm3CyMnnsUzPziG84efQn5lAmgX0eJBAIvD7BOn8P2Jaex53R3YeM3VeMm1+/D00kGcOPUsQqMVfcQRGwBJMzSnp3Hvvffj0uZN2LP9auy+/TqsWLMS93/+G5g4chqcOJg6cFvhzJBw6UMOWnKjY7ey0xmOAXaRstHBz0VqBoMJ6MgrLUMpokUkeqLnB+ui3xOdwaMy3Y9II/EBnUhkNmYJar7gNPWs6k0DAw4UoiInc+ad944klyBtAEVQjQ1yMKkZgUAhBExMTCCEgNWrVuFjH/4wfvnXfg3f+O53sWzFCrSLPFJKjOA4ispodS0jyDlaW+JgYQyJabXbqC1fjkM/eBxv+9m342Mf+Siu3roZE6NXkLkk+mdRogNRBkuUj88xo2i1KMky+i9/8ifJb/2Tfzp896c+ve+qTVtc0S5yg1d4Ci2rWU9ztpjtSZSdM/We+kKg0G4bp6kqkeaAsvcBzMFCCGoUQDEKUmNKjsRMN4pNZeuOPCIEjUzycofAtPS4x3xFqCpKO7gh5JZDkYABZiOiiHFsiM1lLQWzyVymktaVXRaF8+XERLLS8AsknU50J3IZCywbAP4HiGeYGXbt2pUOrNmw8c6X3fETvijWmAYiIhMSKOIqq+v1D4a+gQH81Re/hAfuuxf9y5YjhACWBKWJhhiAcNxBYJQoRiEDjNR7Sl1CebttPVmF3/TTP80VYZ5utiC0wONf+s7FSTSRqCItPc8+eNSqVRRFDqLojYbFYVYRRm9fPx4/fBjf+Po3UBteika7ZU5crkR1M0wwyyiIpol4zmANJp4G20Qwm2JgRkTahRmlzDUzLClgqw26EZlsaiW23uf1Zb1b1/bc/FM/kWzYt50aWuDY6ZN44skjmJueBTsHMoIWIQ795m0gTbF19w5sWrsafWkF0+cu4ZEvfBtTh0+CQ2zYW9EGyGBZiur6VVh37S5suHYXrtq+GZowxicncPzgE3j25LNoj02WC0QHNiAUCqpWsWbtWjgIzj/9DDBRnxVP51XtCs6fby1ofizWYi0K6MVarL/DLvTzq7zInw+BVjEbMA4dXUpYBvC4M+AyxpcuxZIkUXVOOVChwTeF0/HpU89duXTq7MzavduWr71qTfbcsZNGRqRFiIJMBPl0AycefxJnz5zF6qvWYuumDVi5fSNWblmHmZfdhHPHT+PCU6cwfuYCwtgkLHiABXp5HD/47NcweuEidr38JuzdsgXDAwM4/NRxzIxOgiSi2kK7iGKIDCePPoUrI5dxze5d2Lp5HX7yPW/Do995AMe+8xDy6SaSagb2BF8ESMcIa1H8qZXUAZonNuB5BIcOaKNkScOiir8AAQAASURBVMO6346hLQyLmdCll5NhpU3AOqEt82ywMh2uE+ZBgcw8qfpc1achEaRNIpNIPlHl1FtQZm+mnqKRV6HxPnWCMaQcypqemoKpYtmyZfjgBz6A3/zt38ZnPvc5LF+9GkEVzaJE01kAyCIdgQWM0jqC6B82i4lwMMXQ8DCePnkKP/eud+FD738f9uzeicnxcTjh+NAQO9sdZpqVwohgaDcaqPb20v/xh3/gnPDQ3Z++Z8fSlasCs1gr956S9oV23jOr7dmig0WZVqXevj5QURi1RQFVctw5HioEJZD5yNhmqAnFNUVMeEZMSzaL0eSKGHahal3EYVSNscdKFMflAFjGrBBRarViHDezsWsqp1Xlel1dzZSTaknXyOxs5UL3RNnywtdXh7QB/I3DQf+mdezYseXv+91/sXvFsqW7Z2dmBgGzbtoiSxncU+6osEOeF/jQn38IMcSxdOITSrd/tDMZuDsIG5Mzmaxc/CVJIvXJSbzkxhvp1ptuxGwrj8e3DNtxIlAziMQB0yJ4uCSNixgNqFVr3ddWlqbQEGDMcIlDuyggicPdn/gEmnN11KpLYYASUUuIJpTpIpjPxwFBzApTHaKzBjcLKuZgWgQlErV+FV4BoasD0y5NaFNOfrnV0p5tt74k2XfnzTK0ZjldmhrHkeMn8czp00DhY9c5L+I5LAQNhrSvB9u3b8O2q64CtQsce+AQjh84CD8yBnIcBTYR3FXDGN54Fa7adzW27tmOnqEBNNXjzOULOHP2HM6fPY/W+CQQyoRPNWgeYCkDwaNvaBjLly5B0Wjh/BMnCQ1/hSx9yrVtKv9R79uLtViLAnqxFuvvqAt96BCwf3+XxAEAIyK2QpWw7IcZ0RgYANXZSJqBLWlJb2WqNTF75eyTJ8bWbN+45qrVq3rOHT9NKLTsrRHMx04kuQTt6TqenTqGM6efxcrVK7HuqjVYtWI5dr50P7bfuAejF6/g3KkzuHzyDKYvjcLabaBd4MJDj2FybBR7X3kb1m/bgIEb9+PQseMYOXseCAa2kpoBwLFg+so4vn/vgzi3+RKu370bt7/xFVi1cS0e/vJfo376Asw5JAB8W5GxQL3CjMCAdbuWZWogUUfkkhERkpgsSKqhMwfY7QbSwoE0GFQNjgng2N1Wjb/PCXd5xIwuqzkQc+CQBA4aclegEhyBySjPzZLEiFlJWWEhmJlaUBgDIQQKfh65xiQoihxTE5MQZgwODuJP/+RPUKvW8NGPfwzLV69BNU3QbBeQ0tIhLNGKQhwHK0tQNVP0NCsMrTzH4MAAnjr+NO56xzvwoQ98ADfuvw6TE+NIXdJlDXcCOxbaWMQxmnNzlFYq+A9/9H8maZYtfd+HPrRr5aq1eSoJt9vtR0j8+TSrzrgQ/FySKNIUs7NAb42NiK3GrDkFswVYO9VoTyZjYWYhojKeg6CmplDqDgyW+D4zK7302l18WNmZhsICkbIg0mdElJiNWi2lLIviOcs0mahp16bRkxqqA937dOrFXnW9vYYDne7zPfY/oPtMW7duTffcdOt1d77s9peHolhuGpLIvI40GRiBWKCm8EHRNzCI73z723jgvvtQHRgoRTV30lLirkGkxZDB4mKM4hyAsJgQkYUAqOKuu+5CX5bSlfHJuNhyDkXh4YhhGgcHC+8jVYMIrWarFM+GdjtHmmXQEM+3JEmgGtDX34fjJ07gi1/4K2S9NdP4es4BTHuvFySTMwx6jsgm2VCH44YqNwLl7cyJN1WmoL1B3JJci63Ikv1W4S1tbS2rrh2u3PKGV/LW63ahHgo6cvo0njh6FPXpmXIngqF5ESk8pDBiDK5ZiZ1bN2Ll0BLMXBzFke8/iIuPPhF3yxIHq6UY3LEZG3duw5ptm7Fs7UpIJcHE9DSeOnoE589dwOjIZaCdAyxgcpFNHjrvMfH1ATVctWoV+io1nDx8xBoXx4iML5i3JxrJbGPxkrVYiwJ6sRbrf76BwnkRnee0XsRCCBSYDePjuAxgRXm73Bko5LpxkgZVLVpNzMIlo+cOHx+ZvfW6TSuXDQ8NDC+lqecugozISLp/zbyCXRyi01YbI6efxci58xhcMojVa1Zi9aoVGN68Biu2rkPztv0YHxnF2dNnceWZM2hMTKBx5hwe+txXMXbb9dhx3R7cfM1unF66FE89+RSK6TmQJEDuo6+XCZYXeObo05gYn8CN+/Zg8zXbsHLTVTj4le/h5IFH4BselVqKvB3ilnVQMAARh6AhduKo7A2XvGCOIROxuapKXPKDTRXCBq8KtXJPt6OuF1C4O+KGFsT6qUasnwazYOZdGgKLBuQJWq4QynMDKgACkANwHhqiV9egZTB3/HvSIXwQIUkzwBRjo2Mo8hxLhofxH/79H6Gvrxd/9v73Y+ny5cicoCi0/LnYQUZ5/EgZytFqEjuYMbu73mqjb2AQ5y5cxJvvehs+9IH347WvegUuX7qEWqXSFcwAnredTwCccwhFgYYP9Id/8PtJmibD/w97/x1n2VWe+eLfd6299zmncq7q6qxudauVQQkQiGwMmIxAIMAYHDDJHo89jjMG7Blzx3dsbP+cCAKEQGCCwZgLmCiCJFBCWa3uVueu7srxhL33Wu/9Y61zqpmZO2PPz/YduLU+Hz5IperqU+fsc/a7nvU83+eP3/Nnj5vcsdOCsb5096Rw3Ph0sZpS2KJw0mU0tP/ZzuCo3hu8sQ5NEtXEqybgjXpvUTUiiPeeDkxG2sNzeE09IVBqzgoRxsesGPEgvijFZy7xUnG61ky9rai3a2s+6ery6XyXr1Zn/cGsO5SfAJ3h+Nr4ek9P/7BieMuYxsGZf4765Xd885v24MGDQ+9/1+9fNjk+ceXaynJkAkoo0AnE73haYjBGcaXjA++/gbzRojIwQBl96yIEC89ZDZ3rX4+hWJDEWOqrq1x80UX8xDOfwUpexkBmLOtJLN55kiSh9EGFViO0WjmVSgURocgLskrWYa9XauHrrWZJV1c3n7j5ZmanztAzNkKzKLxNkob3fkaQEzg9lhh3olCWEpvWjaOVpL4Qm/hmaa2h6FHLsKaca9L04oYW53nKkd1PvyJ73DOfZHonhjm9tsT9j+znsYOPQVFi0xTnSkSVNEkpigKtZOzcs4s9O7ZSNYYDd9/Pw7fcTnnyDPT20rdlkMl957LzvHMZ2jROpVaj2VjjsTOnOHL0GNOnTtNYXIbSY5IUJfTDq3PtTGYbpo4rHNlgL5snNqFNz5F7HlFWms7YyknbLPa7bKgV8DQb9o2NtTFAb6yN9b9buUqQQ7JMjxaFbPmvvvGM9zJ+NvtWRFlbU9OfFpUibZRJMl8eOX3iyAP7Fy56xpMmdu/Yae86dUbUafD+qtJuTvBlULisMXhjUOdZPD3D4vQsjzx6iJHRYSY2TzK5aZzxvdvZtHcnjXqDqaPHmDpynJPHj3PwW7dz9PgJ9j3x8ZyzczuD3TXuvudBVk7PYTA4FxNRIpgsY3Fmjq9+89ucf8F5XHLeeTzzlc9j+3m7+N7ffZWV/cewJiVRwbgwKBoNvl0X0HKdJsF2l12YydqxP985WPX6w0+vieEoMSBOYllKoCF4dYE+Qmy/Mwas+DL3jrJ0ias6TZpikkQ0ApoJ7R5CVFNNkAzXydaRLmJNwNEJJpSlWMvy8gplWTI6Nsa7/9PvYxLLn/7pnzE8NhZa9/I8DDvRC9yutxZjEbWo9yFUFjcYzVZOV3c3zWaD1772dfzpn7yH6697JXMzM5GowA/hDyXilYNKrngcbnWFd/z7f58Iycgf/9mfXjq2eXO32LSWl/ldHnPE5JXFoiktm+ZOTK+q5uKdNyrW2sRnzpqKdb4ixmaqmqrXxBgTqXZBh/aqlGUZBnljA6M7Oje814gXDI2Fgc8mXtV7o+pTSQJxw2gIMmaZt86tD8/9/X5dVf7kf8eice1Z18M/3+DcftO+99WvzvZcctk5z37ms/aURT5RFIUVaW+iJPjvvUNQ8tLR3z/A17/+Db72ta9SHegPr0tsl2y3Ndr47ya+zb0Ghdi0r3lRWvU1XnXddQz39jC/tBpxj8TTGoNNE9T5YOsx0GzlpGlClmY0W01MYjvDuUj7pAZ6+/o4cugwn/ibT5J1d+NKhyhl6dyqsXbaJsmUWJkuPIvGulVXlrm31pFDYsiMtLrVmgmXmvN8qpc1i/oFlS0jo1e84Onp7ssvEp8KDx0+yP0PH2BteQmDoMbii6KDMyy8ozY6xLl7d7FjcoL5MzN87/a7WHzgUdKBAXY+6xq27tnN1h1bSWoVWq5gem6W4/tPc/LoSVZmYpZDQLAhWOxCxoD2SVz8JPGddkhlctMmhvsHOb3/KNMPHFQpzQqFO5XDFAcPlhu3q421MUBvrI31v98Q7QHDXXdpVKHVEiwBROXZM4ofRkah01IoIiot60XXCvHVJVru+MHv3T+1/fw9W7aOj1YeHeg3y9PzSMSImSxDws8NqDQiZ1kEm6Z4VXy9yfTRk0yfnuaRvh6GRoeZmJxgdGiQrRfsYdeFe1haWWFmdo6jJ09y/8MHODA7x76d27nmqsdx110PcvrIyeDlVEVV0CKE4bRwPHDvg0xNneGSiy5k16V72bR5gu//w7fZf8sduKUmaZaSOkNZelDfVqQUEdSrahy8rBp8gBPgfVCQTacaG5zXGLxqF6jYdf5wu1ZaDdYk7bEjsKS9V3HGm2ri17ShtST1rilG1KAVL+qcUZ8YVWeE0oiKiBhEkSiJo+qwJo3dNwEyYWyCWFirN0gWFnDqefe73kk1q/B//tEf0TMwQK1SoZUX7daXQAbxHmPjzT7WlifGhHBYrIJOK1Va9Qa/+Ja3kecFr3/da5ifnSNLbXgOwu6jUyHdbj1MRGjlhdRXV+Q//M5vpUmaDr/nz/7M9g0NZFlW6W6VLlNfHrJpsVBKV0ts0yNevPc20SRxaivel10i2uVUuwQyxKZ4tYKRAFvx4rzHqmLE4jXYclQET6j4Nu3RSWLjjbafNBOucWnoWrPb20rTm9XcJ8s9/kT3rGfzZhcHZ///eLLDJ+V/ePLz/8/8LKJTU1N9/+4d77pmfGR438ryUipxh2NsLALSUErivceK4Lznhg9+kLyV093bC3FQ1vYGN7KiwcdimfXdtXqHtYaVpWXO27OH5zzrmdTjoGgSizqNz3oIp4bDCiEvC6wRqpUqrbxFYm0YXEXCgB1Sq3ggyyp87nOf4+TBQ/SOj2mrLD0irdQmixgzLaLz4nxdExxejTeS4ZzYVDJnpU9tuplacl6zbFzijZ6346mXjT/u2U9OR7dNyMn5WXnw0Uc5cvgolA6bZvgynIoYA05ArWFwfJR9+/ZQ6apw2yMHmDt4hIGswpOuewnjExP09vbQUmV6aZFjB6aYmT7D4uwcvt6CMliexATrjHoleIdM5xRE5Kz3RXDkI5WM7du3khSeh797Bzq7VFiXHVSnhzh2bJUfqsPcWBtrY4DeWBvrf6chOtzY70I4P9OjAM7ppmAvEGPm1M8Mix9ycnbFt1jrpZUW5ZpfsTY5Vd9/7OiJBw9tv/DpV/XvOGenvW9mTohV1iFhFsyqXiAvi9A6IobSaVRqLTZNcEC+Wud0o8np09PYWkZ3Xw/jgwOMDQ8xNDnOyOQ4Th3TK8vML62wsrTGvl07kGbB1KlpTDCwgvd4p0gcq+ZOnOKbM3Oc3ruXi/fu5enXPp/JXdu54/NfZ/XwFNhUBNFEBYvgUFGvajyx0ZCOuurV4zSqyhqpGho82O1n1hgJdIJY470O3pCOBzo2JQtiFBFvWomXCl4axohtqjonUOl8Y5Cy27p3VLoRrLGk7WptJAzT1rSL4MiyCouLS5RFiXh41+/8FuNjY/zGb/8OpreHrkqVtVYLxGKsxWtOGYdmMYAEr7QnvHSqkBcFlVoNXxS8+c1vplFf401v+gUWZ+dI0yQMrGhEomn0VXucKlbAlQXLi/Pyjt/5jWRifHzw137z188bGhm11UolabXyLEmTxyxuzvu01ZJcRaqpmrwqaros9Kin11jf5UWqoppqJw4YfL3h6bIh0Ehb8dcOeQMkwnXXBWIrBm1DRYxRYU3NWrc3VadZNuvpH/FnDc/6j7ZK/XO9YVUReYW96LLjoy96wU9d4cpiWyjksSKxUl5j+2VEydDb38ct3/oOX/7il+ga7Kd0JVmSRZ9/nHzj5WVEcMQCUggYR2PAOYpWi+teeR3bxkaZW1qNyn4I33qvJIkNg2li44mMkFUqlGXwRltrQ2iwveE00RqFYWFxgQ99+EZsdzfNskQFlyZJw6lfEs+SQssaI1ZtjYSaFZ8WXrtzp4OSyhapJbsaxcq5yUjfjqte8IzBC5/wuKzMDPc/dkjuu/8B1haXEJNCCS5vhd86jWc5qWV0ZJjdO7azUG9yfGqKTdUqF1x9FYNd3azVm5yYnWX6kf3MLizQWF3FF3ncQYcNWsS3xN1mrIxXD0UB1oIxgeTjAk3bJBbvSkYnJ9gyOs70oWN6+t79IiW5d/4uLfzDnF25ubE21sYAvbE21v+uZI67lFrwQmOtTsX/OO69wAzq+n9YUVtb00aWeRqNpvQmc6y2jhy+56HdOy45b+u2LZsrRw4f1eUzsyLGomUZMFlpwr59u0h7u1hsrHF6ZpZ8cRktQkOhEwWbEELw4absVhssr9VZPj3DAWNIqzVqlYyuripDQwP0GcPi8hI/WD5F2WhFJPDZ5RkKRTssZvCNnIfu/AFTJ6a47HGXsPPSvYxu2cQ9X/kOB265I0jFkiFq8IXXzFoRK+BVLYLTNr4ujmCd2SvQDkKjn2mXc3S+R4yJvtQwqGikTnvnxMUmPjHGi2moaXR5MauKsYpz0GxCYSApNFEbdHBjVEOXi/caA3ChQyT+HaEwxHnFOUcihlqlRr3RxM3M4BXe9PM/y9DQEL/8K7/CanOZnv5+GnmOqCe1FichdCc+0EikjevTwAkWTAiKGUNPfz+//Cv/loWlZX7r13+NxflFRBzGGIq8iP7v8JjQsAERgUwM8zNz8saf+Wnb3dXV86u/+et7kryo9A32Z/V63m2rHBbR+aw0LSs+9STdZen6LNLnDX14062+rHkhBbXGBtlcVTqlOeFyUNT5cH24YL3Rs2Zc7xX1LvxuNqFFKPEONg6rSa3mj+a5cs45nrv+p8Pzv9gKTHbf/5a333Tu+Ojo7majPuC9Ym24nogisljBWEPecoix3HDDDeRFTmp6sKrB/xxJGUS7jiJ4DZu+tmVHCJvJtdVVdm7bzste8hLqeRHDtSWVNMWrjVz1SJgQQ1mWVKvVgAckIOoA0jQLGQMTNpitomBwsI+P/fX7eezgQboH+rVZFt4YW+Te1RMxa4gWKElptMeI7zVqugqRfqyOmTTdkht3jmutbJu88qLhy557TXVi52azuLYsd9zzMEcOHwHnEbWYvES8UoaiGFyuiFXSLKUsSn5w8DClEYa7qmRpxmMHj7KyuMTi0grabIUn1hrEhpMltTZkNYsyfhBE5rsoVCr0j44wMTLIytwip46fDpsHDS2gKort7Wbf3t1UxPDIrXfjTy8gZdrQ0t2N6sGNW9PG2higN9bG+tGxcsD55//wYOC9wChinfqiMIQQlwB0G6NrxriypG7SdGrxgYOnpx48UN9x1UU927ZtMQ9Mzwavr2oIFhUFq3mLC3ecy0Qi7C7OYWZmllMnz7A0t0AZa3LRoILhwpCFTRDn8aWjzNdYLhZZdo7ToWKYJE0pSwdFGNhCYYZBfPAfaKTRqYv2DGNYOHmaWxaWOP+ifVx0/nlc8/LnMLx9Mz/46ndpHptG0xqJNZSlkiGiXsH7MER3MoDtkNpZ4cB2WUosWRFjsQouNgtaMSGcGFF4HYW+vS8xRq1dU2MTb5rW+9ILmTNiCi9l4l3ivIQfV6hzTkuvEjXs9uNYH31i8NFaRIPdJE1TnPPMzy/gnOP6l7+U7q4u3v7Lv8zayjK9AwPUW60wiRlFS4eX9vE+gcigBnFB0W1XoqsYegcGedfv/T5FnvNbv/mbrK0sB8uHNevKOIpKVM7FRKScsrK4yKtf9UpTrdW6f/O3fnPH0vxitaevb6LZKh4Qaw4YMbNgnPe+D2RYkGGDGQDtVbRmhAzvLSJibYJoYHirD6FBE20KMd64Thqh3cS4/p9VfQR489/iHn+4OfBf942qKsYYveiqJ+982jVPvkZUR9R5CU3qehbPPXTKF0XJYH8f373tdr761a9T7e2NZSnBn09sy2y3cqIeI0rbrWvbfGxjaDQavOLal7NpbITVlTVsvKbQgEIMgcWAxitceB+22dCJMZjIFxdRrCg2SSmdo1atsbK2xs0f+yhiDTZJMaXzqpRiTAvBGRWLocd7SUmlpsJo4YrNppZuLbQ1qZkdufh5z+i55JlXJ0lvRR4+cljufehhVhaWQqkLCmWJj/QLEx+XiQSMspGzWC5CYjEop8uS02VUkyPdxmRZONHw4T1Ae5MedsHheysZfaM9jG4aZ3JynEpfDz2VCqcOHuHUidPhcViBxKKuYPPWSbZNbOLUwaOcvOdhKCi19As4c4yZ0/Mb7OeNtTFAb6yN9aM0RD/0kOf888PE45wYY9T7GTlbgVYNM5uueiERpekKqcgyRXP+we/esbLlwnMHt2/dkj722BHqs/NIkgTlVoTjJ6fYeu42Zn3B2vIKF2/bwvZNE6yuNZhdWOLUzBwLcwtoXhKlSqSMA2eIeSFeUC9QlMEG0izjoG2jlSLcMG1k/4oLPs44uaKlQ6yhWKtz7x13s7CwwEUXnM8FVz+ezTu3cstn/4HZBw7iUytWjLpS8aISqF5BxbQCTiUM5xJxb3HIFIlH4ZGJLMZiJYTYgvilnVCiiES1HZBSsRU11vq1tTVfSxIPJT5PkVSlEOcSn5Sl5rlLtKVIbhPrIo2D9ZynWfdYEtTEDjEkejHzvMXS0hJlkfPS5/0kYyM38fO/8CamZ2ep9fXRKgq8a4fSPG26n5GgrnsXNgjt8gyvHoPQ09fLf/r9/0hROn7nt36TteUVrAmDMxoUeGNs9I8H00UilrJ0Mjd9hle8/IWmp7ur+y1ve9u2tZWlrlpv36hTtqFy2AsLiliMjIgmI+rKAdBeY0xN1WfgjdGABlT1eOeCUmhitZ5b53E770mlzf02oftFxYdJKPgZ1NcE0+C/y3P+f2eJqlbf9pZfPG/b1q1PbtXr/e3XwER/OgokJrCcTbgCbvrox1hZWKBnfJRWUWJSIYmBQdqbuKg6h1CfQ7HBGq7K2uoq5+zYwbUve1n0yoe/M02ScIVF3rSJmylrTCCulGXnNEZjQYt6R5KmIRuB0F+rctOnPsM99/yAnoFBWkWhxhjvBYeIGiNWvfYIDGEQV7ohl8gW6U625s21idr28YEnv/wnK3suu8AstOrcfscdHDh0GJzHWovLC1TBikVEO1YrvAYqhjF4LYPVQgQXSTvtzXBn01cUYGy4jrzr8LPJUnqGx5gcGWFsdITRgX4SCw8cO4pzBXs3b+L47Hwsi2nnMzy2p4vd5+zEenjoO3dpeWpeRO2ilvpgKnKmiFHojVvTxtoYoDfWxvqRGqJryvlAUegUMFqWMA++13XUZ/XeRJMpFIU6TXKp2dWV/UeXjz24P9/zpMdVz92z2967fHdQP50iWYo2mkyfmWXfhXv52sMH+NpdD7B377ls2b6dfdt3smv7TpbqdeZn5zg1O8fK/CKtej0ekxrUKeIVi8WVDtUCkySoDT5NDRIcEpm/eLAKPg631vtOxXN7gD22/yAzc3Nc9vhLOXfnTl7wxldw25e+ySNfu51cvXgEKeO051VlXccMx7Hed2q62wODtRZ1baRdFP7aN904UEQLB+q9JKjmRaHGe2/cgDdZ7uuNhldXpVYpoCjxmjkxWoiXFqJNUW2p96UoKiLYxIQNhggibexbeEnbldZBKQy1ynmRU697jp+e4eorL+cTH/sYr37d6zh+8iSDwyOsuiYeJTEppS/DZkZiA6SxsTRGIvYPCg34s8GxMf7w3e8mb7X4/Xe9i5WlJZwrSBPb4d+qd6HG2JgwTBlDV1cX06en5dnPfLrc+KEPZj/38z8/vry83Ns3ODTWyotNqEwZoeGQbqd+RIwMoHR7r7U0MZmIscYmpo0LNNaG4ceDwweqRJsFLYrHx22GIh6vgsPj4oAo3pVG8aLe/W8xyFx++eV2aGJi5zOf+YxL1bk9zpfVeIoRuzTDa5HajLx01GpdPPzIo3z+839P9/AQZdku2gm/jpdglVqvnG/bREKwt3CeWpaydmaal/7cz7Nz6xYWl1ZIbHgdxayHMNX7aJkRKkkSBnFRNHp/O7YiG65FYwPZZrXZ4qaPfhQ1Rm2SUBa5iogilsSQAN1iZTgXVxGlKqkdoyJbXFEfG7l0T+/TXvH8dGznFjlw4ih33nsf87PzmDQNv2OrAIVQD6RUCVk/F9//RqRjMVGiLynWl2s8GcEGmok6Fy0cCUl3jf7BAYZHR5gcHWW4p4fUJJSNJicfO8r+hx9hvsx55oufS9HMmZ2d6yj8NgnWqB27drBpeJgzj53g+J0PBGqH44zB3FpkMrtxO9pYGwP0xtpYP5KhwrsUzhfSVNsqtHPxG7wP6rPWRKvOVApvfJqaQguVklxXm2sPffP7xeSec3Tnju0cO3GChWMnkLQSbkIinDh+it17dvGsJ1/NVz/+Oe7/9D/w6NAwk+fsZHjXTsa3TTKxYxfn79rNaqPByZkzzE7PMTO3QHN+ES0dpSt+iB0nbduEMSGsp2GwxXtKAp4OH7i2wSQbjmLVCSbJaCyv8p3bvsep6WmuuOQSnvaS5zA8NsLtf/sV8tlVsjTBNQsSjBgxGlB27SbCdUxdakzbDtlhDHNWE6GIhCEiPqZocRF8CabqxXpNklWv9YbTLBP1pU/KqnFZrs650nmbG2jiXEO9z/Hq2wqk9+EGHfwIQfFXDUftVgQowtAjgneOLLEYY1lbXeHkaccF+/bw6Zs/xs+++c3cfe99jI5PstZqURZ5+D1M5PVFLzRqgqonAc3X9hy3nGNgdJQ/ec97aDQa/Mff/z2kBUVZkKRJQAai2Egl0DazWB1ZlrK0MM8Tr7xCPnjDDfZtb/+l7iPHT6RDY+O9pfoJdboY+x57BPpUTJeIyRSxiLVevRTOSZKERjw0DEh46Ry3ew0wvfZr471X9U7Fq1PvnXjaHDjRsmp8bym+UKEs/18bpFVVRKT7d//g/3jyxNjolUWrWRWR9ZSottVk6eQAalnKhz/yEeYXFhgYHaXMW9G+ErnhbS9/W2mNJwQaVelELM16g8nNm3n5S19Gq3C0gY7GtAOYgAY8oAesDSqteB9UbrP+4ERMfJ0Da7qnu4svf+MWvvHNW+jp66NZFEENVxVrxYpITfGDTkCR0ht6xDLqjRveec0Tup7ywmcntrcq37nzTh545FF8q4VJUzT3keMefPAubnBLDbKuD09UOD1xjkDrk/XrOn4M+jam0gi14SFGhgcZGR9jeGiIwd4eEoTWWpP5w1NMHTzC1GOHWTp1CnqqPPH6F7NlfIw7776fYnk10lEczpdUhgc4b/dOxCv3ffNWdG5Zjbeo6iljuM2X5cK/ZBB1Y22sjQF6Y22sf8khuq1CN5ucAYbFahzAVL0PR9zOWXyaQCsBm/jSqVSqzdWDJ/LD9+13j3/+08zjL7tEvrG4JNpshTS6GJorqxw6eYrHX3gBT3j2M/j2qU/TOnCSww8e53DP3fRMDNO/cytb9u1ibNskezZtZc/m7ayurbEwv8Ds7DwzM7PUl1dpNRr4Mh542miZIKLkYkqeyJxrC+YiJpRpGNMpghCxWBUee+QAC4tLPOFxl3DJky+jt6+Xb37s72iemJUkTZUSUvVCaLLTSmKQIHkikTscdxphYGh7suON2BiJQSIbTojjTduLqJjCm7WqT8dS78tStNl0vrdX6iZXn+c4kaKamIJWmVtTzVFXiMF1qpsjY9m2edMRsacRY2azLHqSbeT6xsCjelZXVpgSw3m7z+HGD97AL7z5rdz+/e/TOzSCczaA39pNddEaIV5xPhAWMEQvdDCG5s7RNzjIe//yL8lbOf/5P78brKUsWiRJEuw2RhDVYM0xEX8mgXiyMDfLVZdfJu9971+bN7/1rdVjJ04kPf0DFY8OqvcF+ASVijFkHizGGpMkxhsxlWol2E7iY0mTEBJTr5GO4PCxgVE6bvH2CYxXrJjUpsYXpVVRo4U3HmR3nstBrpV/9j7uf8R67nOfm3WPj2+59mUvebJBLyyL3P7w5izaiJIM55Turm4OHTvBZ/72s1R7eijVB6RhLPGRdot926oQEXSh1jtMwyYx1NfWeOXLXsoF5+9laWGZNE0injFYHVx0vBgJNBjitWZiC2KwGWvHzqsarBsOpVmU/MVf/XUIqlqL8Q7EEstwUm+kS0XUi1YltaJGu32Vvkue/4zqNS98tj2zuiS3fue7nDh6HCMGoxZtluv15EmwfPmorhcaMTpyNp++TfHzULTCw6ykVLpr9A0NMDA4wMjQAMNDA/TUuhAsRb3J/IETnDp0jNMPH2LpxBn80nLYEfdU2PucJ7D3/H0srqxy4sRJcKHZULozVIS9e3czMjjEoTse5NRdDwXWesmiwR5N0+R4efJkY+M2tLE2BuiNtbF+1FVoaxXnFGYxtl9dlKLbjXDqSVRNhmjFpFmi3im5Lx/5zl1u66X7kk3bN8ulT7ycu2+5FZOlmMRQquPokaPs3LGNke1buOgZ13D3hz+LaRb4M8usTi2z+uBRTn7nHtKxIcZ3b2Nk6wRjOzazeWCYyaFRdO9eVuprzC4usri0xPLKMssrq+T1RqjOdZG9GgNjvq3USeC+tm/oiRVcZNO60mGsZWF6lq/c8h0uv/giLjpvN09/zYv4xsf+jubUYjgqL1ArgSzgCR15IrYTqgv0DenoR20/pZig8LmzLSTx2VaHl7L0kq766qzzNEegD3yzKb7oUem2qqtqbFkWOaYUKFApxSQaBmHBu+D1DNS5ti82DolJgtegCqJKkkQWXqRpIAlrqyscB7ZunuSjN36Q1/7MG/nmt77NyPgmVuoNrBFKFwb0gPCNjAYJNeUmPofB7xl+58GxMT70vvexurrCn/3Zn5JmFYoiJ4s0BhvDl8aEwaYsw/OVZRmLCwtccN5e+ZubP6av/ZmfSR548KHuodGxSqsoSxGrKmqsGGuNNc456erukUMHH5M//fO/kF/75bdTKRx5ngdUifpYEhNoKd55yqKIr0+4pMNvZcR4SVRMQmps1eS2VfY455dMUWyW/6qA6F9jiTFGv/SlL42+/Td+68k7d+68uFGvD3nvtY2qaw/FHgn+8tLRnaV89KM3c/LkKQZGR8ldGfFxdDzJGvecznvS9rArhKIjV1I0W/R2d/P6172OoigDeaWNYIwkFcVjY1C2rWab+PQYm6DqSQRc9B6rhlOg7lqNL33tG3zzm7fQ2z9A4TxOPcZa8eoFIVHRijNqfGa6vPUJtaRy1ct+MrvyWVfLwalT8t077mJ5egYbN3OlC8xrjcq6Kz2SRAxjJGi0IdfqNZxQRYuT1KoMDvTRMzTIyOgIQ/299HV3UUlS8J6VhWWOPnSMmaMnmXrsJI3Ts/j5ZajnAWXXleErhr5zd7H38ReTIxw5PsXS9BymWgmnAkYZ27qZfXvPpbHc4MFbvg9LTXDWi3LCYg42Go3ltki+sTbWxgC9sTbWj7IKvTtXnNO5JPEsLdHf0yM4F82PFdGklZROqsZoj5a+pkZTSSytI6f9A1+7Ta95zYs4d9c5Wngn9999LxghzWrkzRYPHjrM1Y+/lN1XXMzJhw9z5h++h2iovTW5wZ9eoTi9xIlHjnGimpKNDzK0ZYK+rRNM7NjCwNgQO0fHSLZupUBZq68xt7jIwsISs7OzrM4v4ZotKIsw81iLJGZdkRalwIdwoY9DhfekWULZLLj99jto1hs8bt8+nvmaF/P1m/+expFpSmvEeKPq2oqmqqpKGEhs55haiHQHH5oLnfOY1GBsEpjK0cLRvuMXpXW17sQfTFMPs2xZblIMDRlvG1quNZE0cbn3LlUt1beNKm0FMgxP4fG0B+NY7EAgIrgi+I6tbeOkgzLnvSdNErwq9dVVpoHBoUFu+uAN/NwvvpW//+IXmdi0mXqrifionpvoeyVuCMIYjhGDF9/Of1K6koGJcT718U+wuLDIBz74AXq6e1hdWSHLUpz3VNI0KMbRUy4+DHFihfrqKhNjo/KxD32QN7zpF+1tt98uE5NbbL2VR4XfSimIunC8YGzCO3/v92VmZoZ3/8ffQ4FGvRmCmtoOyEUBUk30oXvwGl4m1dSpz4zNK5gs9YUta9WGz1drLh9dNexAuOVf9634spe9wn7j9tt3XvvSlzzfGLPFe4cxP0wJkRhYdc7R3dXF4ROn+fjHP0Gtu6fjeQ4NlWG49HgSDBIpEz5uZEShLHOqWcrs7DSvuu46LrrgAuprdTKbYDucc8WahCROxRqZ5OE6NKxTQeLmMb4nrBhaeY6gfPazn2NtaZnhnl5azYZgDaX3GCPGi4oaRatJoqbEDnTZq1/5PLPvykvM/uNH+eZ3byOvN0hsSpnHtsmzzxPoZADj8jFIHKX3Skqlu4uhgQGGh4bo7+9jqL+faqUCpaNstlg+Ps2Zo1MsHDvF/Mkz1I+dhrVWTDMYjAf1SQhtlg6zeZQnvODZ9E2Os1Zf5cCBx8LGJksgy6jUqlx60QVU0ir3fv8OFn6wPwSkS3Uox0vxR6hUyo3bz8baGKA31sb6kQ8U3gXZ+UJRtAOGJKuraK1mvIjiGwZNMot2q8og6ocR6dVcUzEqR79zlx675DzddOl5snfvXnr7e7nr7ntpNVuYNOPk1BQn57YwOTzOFS9+Nt84NcPa/YcRBZd7pF3554BGi3zhBKf3n+R0NeFAXxdd40P0bxlnbPsk/ZvG6B8fZufoBNsnJsnLnNXVNRYWl5ienWVlaZnVlRV8sxV8AmnaaSTR2HAiGgbgMnfx3z333vcgIsJl5+3j8c94Ard++iv4lQKXK2m7rS22jrX50231V4zGkpMkHGtHy6pGr2jA3LWDWHixpUu7+jxbt3qmp/XEyZNsme/CuUIYBL9qDZI7Jy0XHA9exBhpl4O01bc2sq2t+LXHikADCcHFJE1DO2D0ArcV+sRaVpeXg3o8OMT7/vLP+bk3v5W///svMDo2RpKl5EXZhocHW4pGPrQP2EETR3MfzMY084KB8VG++pWv8JpXv4a/ft/7GB8bYW11NWxW1K/bqttMbRRjBJMkNNbqTI6P88H3/jVveuvb5Dvf+Y7tHxnDGxNUUB8Z3F5x6hkeHeUDN9zA6soK/8e7/xN9fT3Mzy8Gi4tvs6i1oyGrtuHcmipaNSI9Rk1NVCvOSCm58a7aKsuGMzQa64iTfxXvMyLyyf5f+a3f2nXxhRddsFZf6+9YNuKUKCKdIKZTpZJa/uZTn+TAw48wMDFBURTY1OLjhklEgsUi+vZ9x8MvweJjhLzVpL+vn9e8+noSE+vcbRLsO7GxspMliD5ziZQX7fiqw3XXKbE2gRve01XlBw8+wt/+7WfpGhggz1sxiBhec0VFraCZtWo92leTq697vlzy5Mu5/+ABbv3eHeSNBgYJxUDxzxLLJDVS1tXHIhMUqhmVni56BnoZHOpneGiQgd5+ajYhsxn5WpO1M4tMn55l+shxFo5PsXZ6jmJhGRoFqI31oya+Z4OViSSw131fF4977tPYtHsbUkm55679rC0sQCWld6Af093FpefuZnRgiPkjp9n/tduReonmqDhKEVkDmsSQ9sbaWBsD9MbaWD/yKvRDDi5Tdi8ZrNW5PFfW1kx3mvrQUeKy1Eh/id+kzm1C7KCIVCjF6HxdvnPT53l2fx+9uyfZtGUz1wz0ce8DDzM9fQaKgnsfepj+J/XTs2WEq171fL4++1E4tQilDzcrBS3as4oN1oAVh64usTa1wNoDj3GqkkB/D7XxYQYnRundNMLo9kkGx4YZ2jTJ7m1babiS+eVF5ucXmF1YYH52Hm3lYfAygdohhAIIMQZ1PpQ9oPzgBw+QmoRd5+1k+oqLOPC175GYNDBh20fBRjGRPUwkE8hZFKq2F1k73XfaaTT0oY/bmyRxJ2ZnPbffHp77pz6VEzMzytqa2bQwQp7NqkkShxrvQxrKompEEemEBsMQa62hKF1sSlSyapUUaNXXqCQZeRGoGBqtGKph+DQY0qxKo9ECFhkeGuSGv/oLfvHtv8TnPvc5hkbHAiWwbeWJMl/77/Kxwc75UPkddhiGVuHoHRnh29/4Bq+5/npuuukjjI+PU19bIcuCb9dYi2+jz6KPPLEJxsDqygqjQ0PceMMH5HU/8wa+ccu3GJvcHLAZqhEfE9T3vPTUevr54Ic/wtLSEn/+p39CT28P87EhUdXjSocL1BYVK4HGhmai0oOhT4Qeo27VIKWzuevKM+ukkN3Oyb9mw8U73vEOSGq7XvqSl10qosO+dIl6r9Za6QynUVQVhCxNODM7xwc/+CG6BwdiuYqJpwRgbGzGbPtWgNQE5bf0SppYjC9ZWlriJ57zEzzxCVexurJKJUlR1c4Ji0j0xcdK9LYy7VlXfaXjrQ4nFIEQ50hthY/e9DEWFxYZGBmmbHdCCjh1YsSoWiOaIr5qufQFz5C9V17IA0cO8d077qKIYUHfDH9SvUOSwP72WgZbRuRd1wb7GRsZYmBshJHhIbq6a3RnCWXuWJld4PjUDAvHzrByaprFE9MUs4uw1oS8BBXE+XBrj7QYVFEDaZbgkxStCD7x7PmJq7nwaVfRSgynjh7jyJFjSDVjaKCfIjFs2zLJ7i1b8YsN7vy7r9M8PIVoAs6p8aoqptsaGXRCN9DcqPDeWBsD9MbaWD/ay3daCg/i4TLD7iWlLI0Y43FOKiJVJ4xYla1O7BZRM6CeCrk3olAem+ZrN3ySp/z0ixjcvYVqVxdPftIVHDl1ivse3s/q3CyPHDnMxXv2MnL+Dh5/3XO5+wOfQcpGOAYugy3AuViZW7rQMmdTEA8tDy2Hri3RODFHwzwK3RUODPfTPTpI95ZxxndvY2zrBBND/WyfmCB3juW1NU7PznDy5CkW55fQtQZKoFKoKxEXapFtxaJ5zoHHHmPn5kkmztnMgdur+FUnThUbubfrpSrt3UcYGDhLjfPheLqjBHY80CHopI1WS6lUtPO833KL8tSneoApZhlKU4+I15b3vuKVGF+UTjFLqMi2Z6H08qIkTVKKIqe3twdrYG1lhUqaBFUxSr+K4DT4wSW6A+r1NXzpGBoe5Mb3v5dfHhjg/Td8kNGxCdQrZVRzjQiliUMSgX5iowotZ+3GWnlB38QEd999Ny96wQv5+Cf/hr17zmV2Zpquri5UPSYyhdsDWFEWpEmKpEKr0SDLMm7+yI28/d/8Gz5288eZ3LGTzAh5GXzuEsKdqDGMjk3w2c/+HadPneajH72JodERpqdOU6lk0XP9Q0f94g2ZenoUMwD0OW+WEZ97YwpfKVs+7zGFm/1XUwiNMbzzne9M3vqrv37B3j17Li/zIiMEIcU7HwOAQRlN0oRWnjPcV+Ov3vt+Dhw6xMDwaHiNTKCkBHyidI4lhBByDdaZcA2rd6j3VLKM17/up6kklpb3GBu89aGIKIlOCEHVxBCexA1TDO11jig0bOKM4MuCnlqVhx89xMdv/kSogYfoz4Y0Vl6XRsVbjy9z9lzzFC675nIeOz3Fd++8i7LMg8/bKZJaTERkqoaWP6yhq7ef4bERxsdGGBwcYqC7RuE8ZaPB0qETHDx5mrnjp1k5NU3jzAIsrkKjDLkJjdteH1ja6mz4mngSa3Hx/VqWZbBuGGHLM67kkudcQ15JaLQa3Hn3D0gQ+gcGWHIFPV29PP6c3ZQLa9z2d9/g9PcfQEqDltEOpRjUTyLJvkT9/nL79pyjR5c2KBwba2OA3lgb68ciVAhwl+cglk2bLKq0vE8ypM85vwV0uzF2TLzvdl4ztVjASCLkR87w9Y9/gZHLz2PrBecwvn0T52zexMhwP/c+/AiPHX6Mrv5udoxtYseTLmZ1fpFHP/EPmDWPNh2+CMfGQWGKh8UlqERknXhwIJKC81AHX19g5eQcKw8e5vRt92JHBxnatomRbZsY3raJkc3jXLzrXHZt2cr03BwnT0xx5vQMrcWliGcLhR95K0cSWKmvsZY3SWoVpFZB1+qdM3bfRrtJGIxV1lFfbTxYKCwM065F8e0jbtO2O3hERM8q6wiD9C23CE99KgDpXOJ8tXRNU3dI4uLkGwbhGNxq+0C9xpBkYrHWUqlWWFoKzWyDw8OsLq9gbDxuNwZflusBMcIQXnpPM2+xvLRMT28P7/kvf8jE+Di//x/fzeDICNVKhUarFXzj1gbudpycVDrW7lDQoWEgrDdbdA8McPCxx3jFy17Oh2+6kUsvuYTFxYXgiY7lFhqtAcYYnHcdU3feapGkKX/6nvcwNDTM+264gb7BQSppRqPZwmuosNbSUW/lDAyNcOt3b+XlL72W99/wPiYnJ5mbmSXL0g6dQYiVhdgEoUuRfu+111jXLUrT5JJ7Sa0v8yiN/+uQOD7+8Y/bV7ziFQOvvf76CyqVdN/q0lLa3hy1XzeJG4FWWVDtqnHizAw33vRRkiTFqQYZM3DaYrFKsNiYODxHz0z4WZHaUl9d5SlXX83Tn3oN9bVGJG6EE4L2S6w/NNsFynkZG0ADzMMHVVyiVUnCoVJmDTfeeBNnps/QMzREUYbX2xrwREZ3avCaM3zJuVz5nGtYbKzyvR/cS1Gvx2AisRRFcXke4g21KqPDw2waH2NidJi+rm7UhfDfwQcPMn/iNLPHTlE/M4uuNsKDKcIGXTzgbKhAV4mWoPiePavwyHvtNI1KImgCw1ecz6XPu4Z0tJcCx3fvuof66gpiE+YbDfbu2sFlu3YxdfA4d33lVua+cx9SL6EAUQuq4tHUGNlcOneVFVlO8zwvxscf4cyZ+sYQvbE2BuiNtbF+nLzR3d1udXUVRGq5K8YltbtxTHrn+xAqYo1R1CAW9QZpKRydRidGOOwKHjx8hJ6xfoZHh3ncBXuZX5ngoTMzDAz1051V2PesJ5Cv1Dny99/BlA7vBXF07Aj4EIIyKiAmANzaZ9nR2irGCMaEgbpo4pbOMPPYGWYq9yPDffRtGmZ09zYmztnK8OQYmy++iIXty5w6NcXxk6dYXVxGywJJkkjoKDueX/VlJ0BnCdgu53z0QGscvtdvfUYMpY++auKgrY72IXpQgtGaiDb+2+cbbrnF89Sncmb5kJ9Iq87ktkyMlqgEBrQE17G1Fu8DjSGwoRO8L8mLFqNjIxw4sJ/3/fX7ePd//s8M9PextLQU6R0Om6T4yGROkhTvHdYmGIFm3kRXoNt38du/8Wv0dPfx79/5TqrVGlmaUWiOFYPzZWx9M6G4JBasiEgY3lSx1lA6R9/QEEeOHuX6V13PRz56ExdffBEry8tUKhk+ogDDwKadkppAkVCKvIUYyx/+H/+J3r4+/uiP/5je/gEym9LKcwCKIscaS54XDI6Ncdedd/KaV1/PBz/8IbZt28b83BxppYKelXQTxBiVTES7VOgWNV0Gv1Ya08DkifZYccub/jUUaBERfcUrXlF98bWv2nfu7nN2Ndbq/YD4eGogkajhXEmaZgB0VzI+8Lef44EHH2J0coKVZo61Ka69sYrvEbUSgrRionlCEfXxBMNQlAWvfvWr6e2qsjC/SCVNY+V8G8MYXxNd55yLAS01WohMCBRGj324/pVqJeXwiSk+9/kvYLNKDHV62jjr3DmSWhrKkYa7ufK5T8Wnyu1338vq/GKw+iiocWhZIknKwOAom8bH2DQ6xmBPLzilOb/Mofvv48QjB1k6OU3j9Bw0WpGz0rZlBKSmFr4T8rXGBgW+3XgabTEq64O0V4+pGDwl/Zfs40nX/gTJWD+llHz7rnuYPXoEurvo6+5h77bN7Bgf4667H6R+5AzFY6eR5Ra0BNHgJ48Xk/VKn4rs9anFN5st0jQHHgY2QoUba2OA3lgbix8XW0d/v+f0aQa2TPTt2rd3y13fu227GDukha9Yk9jgLFDUa2gvENDlFs1DUzz3GU/heFnn8PIsy36WO2ZnSRLDQHeN/SenOG98giJNuOzFT8cUjsf+7lsYm0LLU7YKEixePRZR59cVsI7dlthWqKLqBIzFqBFfRqNoq0BXZlk6Os3SDw7w2FAffedMsvm8c9i8axvn7ziH7ZOTHD99mqPHTrC6vEK8k9LIi/gMeIx6FIPXzkl1VMPXm91QRTQE3Tp1K1GZFTGdPkMNjWgqTaNM9uh/9wTglltg925fb2bOpI1CvbTwvjQS62TiUbyKdGwQGlVfEciLnInxCb7yD//A/Nw8N974Ifr6B1hcWCBNghobFOAyDAnGxF8oPMYiz1l2jiIv+ZW3/QK9fX28/e2/TFdvN1ma0Wg1O8qxj1XIxtjYjB1pJSJY0di0XtI3PMyxEye59tprufkTn+DKyy9nbmaG7q5qoHh4h02SjipdFgU2sWEj5ZWF+UXe+du/wdjICL/5279NraeX1KY0m01SYyldaB/UQukfGebBBx7i1a98FTfedCO7d+9mZXW1HQLVQDfz4L0xxiZGyYy6zBvJklJSYxPb0KophuqGXdPCLf8qKLuht7z5zU+x1u5ulYVV75U239sYytKRJFmgqGQZ0/NLvP/9H6BSq9EsHIm1lBojgm1LxQ/53W0M7YEvS7I0ZWV5iSc84Qn8xLOfxWq9RZqmHXpHuy3exLBq9CjFa187Gx6vgXxp40ZO46CcpQmf+/wX2P/gw/RPjNLIc4wxpIkl90VAXBqHNyUXPPUKJnZOcu/BRzl55DgmS8lLFywkWcrExCjbJifZOjFJNcloLq4yvf8YB+55kPkDR2lNz8NqHQoXWjmj/Qtjw7a3fdKCjbaWsMEQMdiY0JT4uFFCZ2UiSApeWwxcupcnvuInySYGKRLl2/c/wNzMLFu2b2XH5ARjAwMcPXmar9xyB5eNbOLQ8TlWHj6KFgbrQrbDhQCrGCOiQmpTM+yNXrD3yksas1NnzsxNTx8DVjawdhvr/wvLbDwFG+v/E6unR+lSU3eN4ae89Dlbdz7+wlGVvMvU0sQbjEcD3EEFHGgOVlNWD53izi9+l01UyKcWkellhlrKgLeY5SbNuRXuefQIS80meWa54sXPZvtzrsanHkkFNYJTF3Uhg1FRUVEQVR9IciKiiUnUYjVVUeMELbxaZ5AcJBekFf7f1BV/YoHF2x7kwY99gW/e8Bnu/OK3ac2ucP72nTz96idw6eMuontoAC1L8iKP7GQJ7Xve451DREjMegmFiVSMdklLuzaYSEv4rykQEt3mDRH9HyDSlP5+n1TzsvQ+dxRNRFsipgz5xHVcmLGm88+ikCQJWZLgnaN/cJAvff7vuPa661laWWZ800TsoAnDrkRVch1Dth4Gc2VJM885M7fMz/70q3j/+99LmeesLi/TU61iIxO7Xe5hItmhrXZK+3WTwAKut3L6hodZWF7mule8km99+ztMTIzSaLWCT1wE50swoXLZ2vDTEwkqvgDzi0u85Rd+lr/68z+nVa/TWF2hkqW0ihwTv8erkpeegZFhHjv8GK+69loeefhhhoaGKVzw9yLiJfTZOFwJzhkVSax6q9ZZb03SVbSsL0thdVX+hVsHUdWu173h53decslFTyuazZ15WYSgY1Tj2xXUENB1PbUqn//7L3D/Aw/S1d2DKx1ltCI4DTXVEsODVgxGgp/XaVCNkzQN87BzvPLl1zI60BdUfGsx1nY2R+sM6UgCiaHCDte8Yy2PvmQEp4pNLPOrdT5y00extQp5GUkuAnlZ4I2QVCwqJb3nbuXCqy/j2OwMDzzyKOI9vpVjrDC6bQtPeeKVPPWJT2TvjnMoFta49yu38fUP/S3fev/fMPXV79E6NAUL9fBedwlSGGiBcQZbGhIvUCpSakA7OhDnsV4RT8e+0b72A5bPgVUUR+8Fu7jqZc9hYPsEVFJOnplhIK3w3Csu44q9ezGNgru+fz+n9h/noq4hDn/nPg5/+wfgLKY0uNKjzpEYgzWCN6CJGKdF0rNppPfCJz3+Ul+xjyPLJnbv3p1u3HA21oYCvbE21o/T0i7JU4bzimy+8oXP6j12/Gjil5oiYoix+mBz8JE9Wy+Q1HD41nupL61QHepiURyzVcvwxChDA71Mjg7SPThAmXsKKchtwtNf9ly+upZz4rv3YKQC9RyjhrJwdDCvZx2xttvn2tzfTk2x8xFZF7/JCuqDHCwFUHjyg2c4enSaU/c8wuTF53LO4y9g99ZtnHvODu48dIhSlaytNsfBuP17egk0gPUAoaAq2CQO0V5jyEo63OY2txeniIiKbXqeCv8PQ7Ry113enn++t3meW2MaGG2WrizbBSFB1Y683UhFUF+G6vOiwCYJ3kO1f5Bvf+tbXPvya3nf+97L3j17WJibD+HD2CxHW2UkKMEASZqS54FcMrOwwrXXvoiu7hpve+vbWFxaprevj3qrifdKmiTBH47pFJm0PdZtZF6aWpp5i6yri8WlRX7m9T/Nhz54A09+8pNZWlzAWkOSJMGW0rYuRIXbd9i+wsL8Ate/8uVUsoy3/tIvs7K0QK2nh7xVrjdNGqFZFnQNDHLi1BRvfOMb+dCNN/Kkx13Ubm9WFSlUpIVICyi9916NlUStcd4bX3HG56Uhz82/ZJnKO0Ag23r9617zhFp3befC3Gw3cSOAd6Gox4TAXVHkZJUa80ur/NV730dareJl3Y8fkHMS/ci0jz8ivg5MvIYTKzRX19hz7rm86IUvoJGXgdIignJWw2enbZJ1L3Z7cI4+YcF3PPB4R+5KBnpq/M3f/T333X0Ptd5eGqULSEXvMalFLRTi0Ey46BlPoNJf46Hb7yNfXYFaFxNjY5y3Zzdjo6NYr8w+dooDdz/E1H2P0jo5C60wCJvS4nOHaBphg9HfLYRcQDwparcuxhhBJwhsRGLVu6IeNHqtTZbgXc7QBefy3DdcRzI5iDMJrcVVJqTKZGqZf/QkJ06eZm1hiYoXtvUNc+aO/Rz6xvcxziKekOfQEOZUiVkBUSQB0oR9T7o0NYPVwVVt7mGgdv48TAGtf+Xyno21sTYG6I21sf7F1uqqSfZs6z9enxvbtHdLZec1l5uDX/o2YkQ08n/DsXhgJKsPVAvygjPffwg73Efa3w0JnHl0itOJpW+4n6Svh76hPrZs30LX8ChJzwCveN0r+IK37P/m90kqGdpyqISqYe9D+5gPlgW1bVVOVaJyGkajME0jID76KNSBkQScDzdXK0jhKY7OcPTMPMfu3c+Ox5/P3qsu5il7z8c5z9TCCXCKL1xo/ZNYI+gl0gdikDDG+pxznYFbYnuhizfxIAxGKoL3iohyyy3/o5uk71pbK1edy1HTwPm6MbZo+8DFWiwSlGTvOpSJoLCGABigzjv6Bgf07rvu1pe97Fpz440f4orHXyZnZmZIk4SyLLESQmEqBH+0C+2JibUURQuvjoUF5QXP+wkGb/oIr3vd65menaW/v4+ibZ0gNNuJEdCIUhPBisU51/G/FkVJraeHxcUlrnvlq7j5Ex/jWU9/GmemZ4L62Q43Ch3WdifgFdnFp6bO8LKXvJDe/n5e95rXsry8TK2nB3WRMOKVLEkpnadrYJCDh47wute8lk//7afp6x8A733pXcvDmjG27rzLrYi3iJYBEyjeVYz6bsEs/Uuqz0ZEeq599WsvvfSSS59VbzRGPCpiRMUavNN1QHREzw33dfPBD36Eu++4k76xUVpFgVhLIm0Ss3SUY2mHEAkbOhs3S5UkYble5yUvfjFbRoaYW1olzVJoD9rRJuRVzvKDrHuMpG3X6BiT4keAhBOQlUaLD9zwIUoX3rtJPIUQE2wmagxOC3r2nsPuS8/jkZPHmZqZpn9yE3t2nsOOyUlSDKcePcKjd9zP1H370dkVaHnEhQtNnaDOYNvTewxPtjcSEivMQ/tnOAlp78LLiH+kIz4H8kYIahpca40dl13EK972RtKxPqZWF1g4PcPimTNMHTvF0twCtplTX1qhqBc0MKyWR1g6cQZaYTNtvJKJoYzbfcXjRJEsKO/DF54r51x5IcvLS2naW9tZiL+0mee3A8sbN5yNtTFAb6yN9eMxPAs0xHZlPUva7HeNhWTPNZfIiYOHpHlwCrGCulCKkCA4Fytz1SOpDdba+QaVXEgSochboYnuyAzLrmBe4MRQH1l3N0Njo+yYnOSS8/fhzyxw5MGDYCLyShExRtuEDo3tf14DlUKjotRRfKN0ZiOmLVADhNSmOCHUXhsLpUJD0VNLHJ77PscfOMCOx53PE5/yJAbIoFmGm7T36n0cUSTcolGwHXHLrwcJrekEr9qTrLBOvjMYlbpRuJb/AeFBu7u7vZltFImYJl7rSWJzEdE2Tq6jHPuA5LI27ZS7SDySdt5rXhSuZ3DAnzx1yrzoBS8yH/noR8yzn/UMOX1mNoS1yjJUOsfacTFRXRRDmqSU3pG3mkzPOp5w1ZV85lOf4o0/93M8+PBDDI+MUnhP4QI6LQiYpkMKcbFUw8eBS0Ro5jm13h4aq2u8+pWv5n3vfx8veeHzOTMzS5qmnbKQoHIGFTY8thjmNMLJk1M85UlX85nPfobXvOa1TJ06Rc/AIEXpyZKE0nvSNKXZatE3PMihw0d48Uuvpbe/Xys9vU5UmiKsYmRNsC0RSicSdEwNLhnvStnuCjn6L/TWetrTnpYB5776Na99Und37bKZmenu0PAYpdF4wuDVo07Jsipz80u874YbwAZPvleNynJAy7X95xKvRac+lAbZJLCjE0ur3uCcHTu49tqX0XI+nEa0y1VUO8U5ikfaNIpIm2kPqYqLDy+eGFhLq9miv6+bz3/+i9zxvdvp6u3BOxeyA9ZgRPGWoMBWDBc84WLWrPLA1BQ79uzmop276DUpU0dO8cjtd3P6oUPo9BIUYEpBS4OoIBquzySy1rVNFkE6nwtW5KzNV3iLJEmgx0jcnNk42KfG4L1go8XknF27ecpTnsKphw/y6Jcf48zsLPXlFcq1OuVqHYoSW3okd1gPRizN0pMUSkISNz6RVx7fE04VSQ2SKDrQw95rLmMt9bKmBWlvdYLE7HPed2/ccDbWxgC9sTbWj9NqQHWwt2K6s66Z5rIZ7q1x2fOfwnc/+DlYKkLJSCk4FzyWoWBE0FIx1pA0HdY16atUKFaamLJA1dGPo+Fa6PQipTXMmAPMZBmjwyN0ZTX6EkORF/H42sWAT7vxz+B8CO61b5AavaLSRm+11Wc8ibQ9pB4vbdtJON52pQMfgnDlqSUOnr6VmQeOMDwwiKwVUHpUTccv6b0Hr1gbvcdoZ96xMVwVcGE2IMGihUPDgKpe1Imp+/8ZHu2h0VHft3yowNgm3tfF2twY8daaYHQlNNKp2NiQ6DshrzRJSAKKTBHKZisvKl01Gs1m9prrX5v81V//pX3Zi18oU9OzGInH/sbg4vG8imKwockwyXCuwKLMzy9w/vn7uOnGG/mFN72J7915JyPj4/G4Pwz1IZgonRrtdp26V0+CYoyl1cqpdNVo1uu8/mfewNJ7/ojXv/Z65uYWwK5vjNoKbLtqUQibk8RaFuZmueJxj+fjN9/MG97wBg4cPMTA4DBFWZKmKa2iJLWWVquge2CAE6dOwcmT2tPb50p1TUHqotIU1ZZgC4w4KD1i/8WDXL+rat4pMvjcF7z0aVc/8QlPaNTXesGbzqZL1wfX9td6+/v45Kc/w5233Ubf2BitPA8Iu3Uq97rMatqqbHivGCOdkOfKyjI/94afYe/2bSw38hAcjJtP065Bb1uiorKtnSZE7ZSMtB8fhJCjSQx5XvDhD99Is9Gkp9ZFKy9I0hQVpVAlSRKaFHRv28TOC/ZwYGaGfTt3cu74JhqzS9x52/c4cOsP0DMLUILVBN8q8aVDNPj9DYH+YlBKiR2jGvMGZ51atIdYibXx6tcLeMLTE/B71ngSr2TW0FutkLaa3PLxT7G0thJoJT78d9tsUc0LEpMiYvEiVHr7yI1lodEgiS2JouCiXcNI3EQmFk3Ap8rOJz+OoW1jnKkvYRNIuirdGBn1mtd+SO7fWBtrY4DeWBvrR3ddBtwFkvR1VSSlupg3ZL6xxqX7drD7mVdx8AvfwZDg62UoI4mot3UXn2I8FGtrjG4e4HnPfhpLx0/QXFqiyJustdZYaq4xX19lxeU0bUlr4SirJqG3UqUMCpw4REsQJ0LhFe+CztY+2rdtyq9qDJ2ZGOSLR7vSFoO1cyqtOFQD0sqXiq+XmCxBrLD06AmW9ATGZoiKRoCeBhxIVLpUpO0TNR2WnbQHZYx42kEwjWqhCGpVvEmS//mQdsstPhnaXaabTAuRBl5z74KR1ZzFzhNVfNv3KaAmeGEBrDVaIg5rmo08L2u1WrZWX6u+8Y0/W1ldfU/yyuuuk/m5OayE42srQS0zcRix1oZqcpvgnMeKZWlxkd27z+Hmmz/GG3725/nWd77N8MgIufPrjTwSveixOduIUAr48MqgSBiuqlU0z3nr295Oo9nkjT/zBhaXFjDG4L2Ll1BQO71TnC9JbIJIGPBOnTrFRRddwN988pO85tXX88BDDzM4NBxoHlH1ttaE2uo0I7NWW0XhkyQrxEjT4lveaCHiSzxebQinIkaNNXr0X6gj7qFXvKICTL75zW+6oren69yZmWnTruhWbW/+tOPrNWlCvVHnr/7yrxAb6DSCxtcmDJPh8osKazwFMhLOZ3xZkoihaOVMjE3w0he/hNIreI+NzYNnFQt2gPBnPx5VwmlTm/sdT3VEBOdKqrUqt996O1/58pep9fbQbLVIrY1YwsB/1iSw3Ledt4usq4t+lzPR38+he/bz0NdvZWX/0RAILAQKxZVFKOrxJqjKcUAOjE1dRydK2MBL9Dg7p3hZLzvyvv29MfwrYBQSdVTEUjGQilJVwZ2eoUs9tdIhRUFPWqEnrdBd7aFnoJuurm5IM7pHhjFDA/z9t78F9RaSVXCdivMwtJcaMhMmTVBT0L/vHPZefgGPLczgxdOX1Ehq1Qwr3epMJTpoNkgcG2tjgN5YG+vHZII2XT1dqaRJSuHl0PHjjFeqPO4ZVzJ3bIqFO/cjWYIv2qGn4IE1keOMETJjmT4+xeym0zz7goup1Js0l+bJm3VaLqcUZdmVnFlb4eT8PKtlyWKzwWK9Tr0oycWI2oRChNwYmqqao+JUSGwIzLXJAbH+IBzutquiJZSgmKgMtcN/okomgcDnHNDymMRgbYaxBl96FVeCWDWRYRtUJqUs3VniaKzt1vWJS6Pi1wnoqceXsd5M5B8TEtL5dMUN5oMF3jestYWJobBOYLJtsG7/z4TBxpWuE35MRFxLtWlE6mVeSFrtqrmy6Pn5n/uFrrm5+ezNb32rzM/O4otSsiyLPvZwLB+eM6F0jjRNOy2Lc7Nz9Pf18amP38Sb3vw2PvWZv2V0YhznA9asjdRTYiOeCVSOdhlMm3qg3kOaYq3l7W/7ZZaWlvl3v/pvmJ6dCzag2KjnXdu+YclLF/cHnixLOH3qFFsnJ/nc5z7L63769Xz367fQNz6GwXc2Ls4Hq0LhHGmaKSIusdZ570vBOBF1aqwTJ0609FRKFdOnmFT/JbjPX/jkJ/uf8ZPP23fFlZfvWl5eHsiLHDHh6vUdFTr8/q50jI2P8Lef+xx33HYbaVd3IIpI2Iq0X6POsOh8UFzbbSrOYawlsYbFxXmufdGLuHjfHpbrTVKzXh5yFhWkM0y70seKcIm13nQG6mCx8TgN6MHUWt733vfTWFuja3AQ4x2l8zG4J7gYUjU9XZx/6cVYJwx5yx1f/A4HvvE9mF3GOIM4weeeRAxGDUXpo+IcT5G8jydRwePcth91TmTiXiIxsfAntnaiYDykBjIVKmKoiMe0GmROGa51kRUlg7UeulLLQLWLicEBerIqfVkFnNIqPH2jo1SGBzm6tsqnvv1NlmbnSGs1ymjl8hqv94jjFgNeStLNQzzuOVez4ps8cuwIWyfGGa71qKlmhsRWaLkK559veeihjQF6Y20M0BtrY/24XO+VWjUzxqTigcUlHjlwkLHLr+DqlzyLr84v0jwwFYbolpKYEKQhNtP5WJyQq+eL3/wadmGJ5114Ad1OqZ+eRfMmfd0Z/ZWMbd39PHF0Ez1Dg6yWjlMLiyy3Whw6fYb7Dh9hprlCra+bTKyslErePqqmfWQrwTMbizw67YEqHdWyPTBIPPotIp4uoDKCdUCcw5ioWmGDUUR9x+6gEQnGfx2X1zYhQ8/6b7GhzwfHKIgaa/9RAzTVqsuqJgffMkhhrfW+LKNMFarFA7ChRPCIhiNtk9iAuEPwodu5KaJL3tMiL9I0TXqSnu6hX/+13+g/evR49Z3vfKct8lxbzZYkqcUHxleoNHauQ9owNvx9SZqSt1pklYz3v/evGB8f58//4i8ZHB2lWqlEgkcYIqw1lKpBSYy2gvAyBKtGUZRkaUJPXx+/8+//A9PT0/z+f/w9VpZXaDYaZFmCK11QFjW0PpZl0SkYydKUxblZBoaG+OhHbuRXf/XX+NQnPkXX4CBibaRZhNfXGqte1VtBy4CRUMF7J8YlqiWeopVYV22J12xJ6en3/9xEBO+9iMjo63/6Zy7r7e0dnZ+bE7xXI2Ej2G7g1ngCkFVSCue46aaPUuYFlW5LhwtHNPOoItbiIqxcVWJld9hEiHrKvMlgfx+vee31ET2oHaWf6Kt37Y2N+s6JTRvAqF5/6DrX+L1lUdLdVeMH99zHV776VZKuWkA+dnz4SukcJrX4Vs7k1p1ccM4u7nnoQb79lVtY3H8U1gpMYdHcgQeLITOhlMjGbEV4LUMZSmJDhNgT7Cae9fe2jxmA8HOCcp5Fydl6JfOOHhGSVpNKq8UFW7Zxxe5zGevpos8a+isVWqtr5PUmqTU01xrMH5/GJClbtkySVCscOHWSv/v+9zg6N43p6abwPthJoo+8E7i0AomH/ioXPOMqeoZ6uO2hB/ELy/iRIcRCpasGiU1UyioLCwlQbNxyNtbGAL2xNtaP+Fo6tmTISKs9XRnW2qJogXPMnz7Dw4cOccm553H5i57FrR/+HEyv4UulzF0MJYXAURF6c6mrJ60kfOO+u9G1NZ574flsmRzn5MHHWDs5S5oacu9Ja1XM0AAj42Ps3rQJU6sxv/McHtm2jW/e/wD752ZYosDYlJZJaKqn0HDXsYmNoPZw43QxFCdt/zLrDYK0h+gYxjOxWc/Gk18tgxUjtak454LdExXiYN6marSH8bYP2LcVVhOpCKwXqqBhYjNL6T9uMDva7d24lkDTGCnVaxyMwu8o6jthSYl4emsAFwaNSGNw3vumIIvWsIJK4ZxLMGaw1tcz+Rd/8qeb5ufne9797ncntZ4u1tZWSdM4oPh1JJ2q4qPymaQprixpNVvUuqr84X/+AwYHh/jjP3kPVekKSLo874S4QvAzjmKx+U0JFMQkCUUoxhr6env50z/6YxYXFvhP7/4DskqVPG9iI4GjYxCN5JBOgYfA9Ow0gwPDvP9972Xz5CR/8p4/o7u/N1ZCK8aIqnpNklQ1KJmSWqsqePHqXEqhoqUpKeuZc73LvY6Jnn/W4fl3f/d3RUSSF730VZPPfMbTL23WG4N53uoMm759XXkXaS6Grq4ebvnmt/j6V79Opb8/FOGI7eDjOn+2LGNVto3Wl6jIuhKbZiwtLHLtS1/G4y66kLVmHv6eDoxRWX9Vwga4DTeUcCGw/pX1C7edC8gSy0033cT8mVN0D42Q50UoW0FDSWj7T5SOp1z5RA7d/TBf/pu/JZ9dxDoDRVSdvQ3XhwhlVL/bYbw2V92YcNoSAq+B3GIjBaTzz15DWQqKFcU6JVGlilL1Dluvs6t/iKdediVPPu88tg/201xYoLGwyOLUNMXcInmzRd2X1Osl3f19jE+OY/q7uW9qik/dcTtH6wvQ1UtTldKsFydBDH5iEAu+mrD7qZez++Jzue/wIeZmZsF7XF7ivVKpZFBJE7TsIcsyoL5x59lYbBSpbKyN9WOwutMsqVQSDXwyERGhdBx45ABHT51k+/m7uOAnrsYnGlLmEsfUtuKr4ERopZZVIyyS880DD/H5u+9hNTXs3LuDgeEByB39Rugpchonpjh+zwMcuO37rB46xGjR4inbt/GmZz+TF1xwEWMl9DQb9PmSXoQaULMG40OI0bkwWKZJu/zhrLIECWn+pM2TdiGEZdrYKx89kwiiKhoGNTFexbsyZNkQCWSIHz72DpSCdrlJ2EC0WcgmCV/3XpSRH7Kc/g/WQ5pWKiVQiEjZJllYa2M4LHB7TZvMEa0jGgf4+HWXGdswxix5ZQYjJ0rRR0vvf2DE3NU7OvzQxz98w8zrX//6fGFxUbt7ejXPHWJs9FrHgGRisdbExsASa0ODerPRYGV5md/7nV/jj/7wP7O6vIxrtahVqlSyrGPZMNE8G4ae9UBYm83bPqXoHxnhxve/l1/4+V8I1gubUEQkmvcesQlOlSQOxu0KdWsMi0sL1Bt1/ssf/gHvfNc7aKys4IuCirUYhCRJ1btwJCGICYFQ8WLElc47Y60Ta/xQpeKybNZzy5j+cyrQ73jHOwB6f+HNP7elv793+/LKcldZlFhrxXuH+gJXFORlSZJmiDEkacKHP/xh8kaDrFLBGksZh0pzFrbNq4uFMsH+oSjelaRpgisLerq6eM3115OYYAtpk2TCNepitXW0WZj2RrMdBlUKV+JcSekdzpXha2VBV1eVg48d5bOf+xxJrTtc72b9Ped92JyWrZzu3n7mjp3mU3/xYfJTCySlRZsO13KkGrB0JlaRe1WchjIdQ5sMI5EaEpCNpmMticSS9rUWOdrWOyreUysL+tRRra9SWVnmqdvP4e3PfS6vvuoqdtUqzDz0MAe+eyfHfvAAaydOUSua1MoSUy8ZG+pnxzlbqQz0ccfhI/zNrd/iZH2RotrNGkJLBCdC6ZXCt+0zQKJ4cYxdspfzr7yIo7PTHDk1FZ6QsqTMi/C5kiVgTOJUB7qgunHD2VgbCvTG2lg/Bqu52DRU00wNqU0ijiwm4n0r56FH9lPBsuOiPTROL3Lwi7ci1gYShlecuhBwiiGyNSNompGgfPfoo+R5kxdffilb9uxgppKyeHyarkTor6X4XCmX1jjxwH7m+k+xfc9ONg+N8FMXX8i+7Vv4wh13c/exI5hqis0y1nLAWErxQYVSwfmA8rI2RA7bxIEwOEjHOyqxIjxMxxpCdW2vp3cSoXmRBx2CVdaYoDJH1Vmi1zoyqM/i5IZ/N2bd2jE3b//Rg1lSpB4oFFxiE3UU2rZBqGd9yEVjaDKEDIXO71YaMQ1Vv6TWzKnXRbwsI1Ii/li9UZzpGhmrf/PLX9xz7UtfOnbjTTdVdu7YyfzsjNRqVeKMHhXNcHAuxnTKZGyaUpYFZxZXeMPrr6e/v49f+jf/ltW1VXr7+ijKsoPza4fS2t161lhCmWWwhTv1NMuSvolJvvC3n2V+bp4P3PAB+vt6WVxaortWCyo4oN5hgNIFRdLaBPUlSyvLNBpNfv03fpXxyQne+ua3ghG6u7tpFk6MTYyIpFYkVdqlh8ZngqN0zqTerawVfjhNFT75zzY8B6X4aeZJT3321ssff9meVqs14L1Pgriq0vGbe4cRCwhd3b3ceefd/MOX/4G0p5tWnmNt0tksBYtUm1PetjC4yAKPIUpjWFxc4IXPfz5PfsKVrNVbGCM49Z2NolePNes7Ou8c6wRo6SAO25xlY0JtvVNPkiZ84m8+yYnDR+gdHmKt2SJNbMglSPh+5zxZYinWmnz1s1/AVCukYnBlQSqWMoaNiZj09gY0iYQRBJJE1nec7Wu+jUdEO/kH4xyJClaVRD1dImQuR1brbO0e5KeedCXX7N3DWJqwduw4Jw8coT4/T0WUWsVS5AWtJuSlMrJplOHtm1kUw7cefoQvP3I/Z3yTZlphFWhKyFmABIJN9NuTgJY5wxeex2XPuprFosn+Y8fJ1xoYDYFYdcHLX8lSJDGpGhlxql0bd52NtaFAb6yN9WOwXOGErkomFZtIWy70Ghr1vGHl9Cz3P/wIS401tp63k6S/Gy1zojMCQ/AKu1gEURhDI01YxrCUGG6fOszHvvs9Hlups+28c9mydwelWBprOQZPqp6Kc5Tzixy66yGm9j9Kf5FzxaZJ3vyTP8G1V17FJCnZ8hK9LqfHl9RQMjQg0+IxvzU20htifTXtASQqWICN/0xkzTqvnaNhF60MofUtep/bZII4GEo7sNgOFZ7lkwbQ0kWsHWDm/rGDmU/SwgPOiPEx4QfedUJmIvJDVdztcF6wLRgVI6Xi62LssoosquqcGGZSK1PN0h0y1tyTN/Nv9Y6M3vPAD35w6pUve2nr7rvv0rGxMcqiCBQIK1grZzGtNdJNhLIsO22L8wvLXPuSF3Djh25geLCfhfk5apVKLJDRqJhH3F0Yd1BpK+XhtSm90sgLekZHuO3b3+b6V72aUyenGOwfoNVqRcJGGLScDwhBVaEoSsCg3tNs1jlz+gw//ZrrueGD78cYWFtdke5aZqzRDO+71bte9VpF1UCpUhpvbOJsnjqTpv5glv2zqs9eVeCW6r/91V++uK+n5/HNZrOm3pNYKx1esfd470KxCUK1VuO9730fq4sLJFkWiS7xChSDiInecl0n/sXtmxFIbEJeFNSqNa5/9fWkaUJeFiFUq+2XxcfXIyjNzrtQhKPt967r2Cg6jzGqvVmacWZ6jo/ceCNJrUruXPAqs+7RDsgLwutTelKTkZQgpSfxoM6TqHTGdWPCaYJEpvPZmYVone8gE8OJUvicSURJFVJVqr6k2zv6fUl1bZmeRs6zd53P77z8FbzyissZ9Z5TD+7n0Tvvozk9S5dREhytRoP6Wo4Xw7Z9O5jcs5Nla/mHBx/m7x/8ATO0WEsyVq2hZQ1F9Dz7MPmH0yATVHKMMLF9E2mtwoEjR1meX0Sconl4HtQ5nHeIFay1Kd6NtXyz+6z91sbaWBsD9MbaWD+qyxdeqNmsq5pZBUoXmMk4RYsgMa2u1WkVOdOzs7gix0R7QbsPQvWsljxjyEVoJJbVtMJKknDf/BSf/v493Hl8isHtW9h16R7Snm4aLYcIJChd1pC0Wpzef4QDd9zH6vHjjHjPiy69lLc9/3lcs2M3fc0WlbU1esqCXqCSl9QEKoDxbZtGHJA7AxudMFTwlAZ/tLYhGUKHieuJR8Qx2e/cOulC1XfgX8ZoR5mOuvDZVD/AAeP/+OOuNPVhbnFKVLqTWNYiZxE5YP3vbBePeO9VVApB1vB+VbwsC7IilrUctyJi51T98TRJ7m/UW9/tHR35/oH9+4+9/rWvbXz71lt1cGREy2BbCZYUETCmUyXeLjyx0SKBKrPzSzzraU/mphs/xPatm1lcmKe3u4sssdFeEn3n0bPaHvwi74E0sSBCK3f0jIxwzx138sY3vJGjx45Rq3XRarWCqi2CQ1FR2oXf7ddERMhbTWZnZ7juFS/nhve9l57g77ZZYqvqy0FRRhJMv3daKUsoTelbee5FjP5LvJcuuOCC9NxzLxp78hOvvriZt87PW3lirA3s8Pi7F0URqTJKT28v37vjDr70pS+SdEdrxFk+adUwBIuYyD43nabAzhXhPa16nSdffTVPu+YprKw1kajaB6tFIFWUzgVrhvp1CkcsHGmrzz4Gcr33OOcoi5Leriqf+uQnOXLoMdJqBdemYrTLjVA0nhik1oZ8gfNo6amSYDz40lGU7r+ZGiUO7D+0SYwTtIk34cQIJjYt1hBqKP1WGBCl3xd0ra2xr2+Itz3nebzlJ5/DeX09LB89wv233sGxBw+SlSXViqHMC0rnyEvIBvvZftG59G/ZzBnv+Myd9/APBx5kMVFWkxprNqWwKWXbAhYfS3tb7qNSj4HlRp16q87y8go0WlDGlKhE3KcqWZoiSZKAH6GQDQV6Y20M0BtrY/2ILwE4U3qhkmZOSGySRBXJ0YGdlp7UJhhVirxAi3I9SKdQSZKO5zjU6oZbfGktdWtYTWusVqo8sDTDJ793J7cdOQb9A+y6+DxGtm4id5DnjiIvMUbpSqAxP89D37uXQz+4n2RxgcePj/L25z6PX3jmT3Lp8BhdqytkK4v04+kBaupJXUlKaC8zbY5zVLXaR98SW/Mw4eaPCfc7kU6lx3rbYdwZKJ2CFNQHZdBHjdorGGPP6nWIHcQAnOGfXv0coSBxoJDYRxwDchEdJ23lGWMskdhXAHVFV0V9HaNN8aaVetsS75slZgnvTmaV5P611frtvcOjdx8/derEq155Xf2LX/yijo0Oa+kdhSs7rYLtJ8TaJIQ1fTvUFXzZ03PzXHXF5XzuM5/i/PP2cOb0FFmWkSUJaTzqTqNSKbRLJ8KfdbHUxSSWVuHoGxvjvnvv5dXXXcexY0eZnJykLApcO2h3ls9cnQuUQIRWnrO6tsrJqdO88kUv4BM33yyDA4NmYX4+6+nq6jfGTGB0EnTAimSpqtTEqJg4QOe5/DOy63jooYf6/82v/spl/QO9l9Tr9TFVNUZMCFCKwXkXyCnxdezq6uJjN93EwvQZsloXzimJ2KA8r7+V8GjYnMbgLj9kRQKXF7zu+uupVjPyvBmZzmEQLl0ZcHdneefp0DPO2vR536l4b5f1GGNZWWvyd5/9HL4ssTYNlhAjHT50e7SEdY9+e/ht5UUoM8KQGtN5P531pAWrUCfMGH5mYoTUgBHFqlIBqqp0qTKA0tOoU11cYqukvPYJT+F3X3kdP7FvL9nSAg9/707u/e6d5EuLdFUF7wtarRxvhJYz9G8aY+dF+0iGRziwvMLHvn0b3zp2gOXUsGIy1mxCmaQU8bGdvVnJ2t7sDn/e0t5Wp2KhcEGljgQVY0ywu6UpNrUJyoBNktrGrWdjbQzQG2tj/Tgs54UsrajYFBOHYOdDKr90UDqs9+CUvNGC0qFlGW6w6jHekVlDYgSJCCqJDWbOGBrWsGZTVtOEw60lPnX79/naQ/tZq2SM79rGln3nYLu6aDrfaUizBlJfMnfkJA/efjcn7n+I7tUVnrPnXH7lp36KN17zDC4aHKWrvkZ1dYleX4RwoiqJcxjnydqhwWjvCD5QXdeRxHaUUjEGjaEo6VQm08GotSke7XIJjUfhXkP73g8pasaI/yfpz2dvaHzEIxgJA2vEl8WNiRjp+KGtDe1zAmpUc1EaAmtiqYsxOSKuFPFZxbjMlIXzrBbK6Vql9vBaM7+9q2/gB81W89QbfvaN+Y0f/ZhOjAxpqNR2nQGhTY0Qa6O9JdgASg1Ejbn5OXZs287f3Pwxrnnyk5g5PUViIt4QxSqkcSBK4nBkjcW27QQiiDXkRUnP4CDHT5zkla94Jd/5znfYuWsXQiBztGvCVT1GAnNYvcMYQ14UtFpNTk7P8NQnPYG//8yn5YLzz0/OnD7d1V3LRi260xqzWZEBbyqpZs6ssoo6J7v/mY7SVZFt27ZVL7j08h3P+6nnPLfeaJ3XajYTETHtUKjXuGmwFpsEpN9999/HZz79abLeforSxdbJEA71MXhpje2E1mxi4+Z1/blYWlzg0ksv4corr2B5ZQ1UY8A2IN7K0sVClHCi4MqgajsHrtROIU1befbe4b3DOUdvdzff/da3+d6tt9LV30+el2RJgvMxwJrYGPQLm1KvUKpSSqByxJhjsHqJiZvAcD2YWAgT7D4ha5BY0yG6GIVMldSVdCsMqdLTrFNbWmKrJlx7+VX89stexmuuvorhsuDoPfdz/233MH/iFDWrVFLBuxLE41QpxDKyczPD5+yg6O7m7tOnueHrt3DH9AnqtQorklBPLC0RchQfLVvWCJkxJEDilYpq+JxTB74MgoKLdevtD4lYcuMEvLXYSoox1iLSi/eVjZvOxmIjRLixNtaPwSq8Ial22yTJTERGcRbuqp2bS9tH+N4h3pOalKoYjMabpBFyH45axcRmODGURqi364IFTvoWn7/vPmaWlnj6vr3sGB9jd18PJx47xsKpmRAGjF7sWmYoGi2OP3SIudOzbD5nK5OTE7zwwgu4cuc53Hn4MW595BEOz8+yIg0qtS7SJKElFgeU3uOMdFQj3y5D7pSUhBu617MtnRqRdXSwXno2hVrW1e0o63VUu6IookLq/xf0Z2xqU2kHFI2xHcwZBG91mz8LIaTknap61Uj4q4uhUTrTEqXAqk9VyXMQU1ExZUmS+rwsptM0ldIVJuuqSavZTN7ylrdNzM3OVd/21rexurKMK1xE9AVSR3ACWASPLz02SfDeY4xhcWmZzZsn+fhHb+Jnfvbn+dKXv8zQ0DAKNIuC1CbRM64kwRkUeM2s22kwQl46ql09nD4zw2tf99P8l//yX7juuuuYOn2KVisPKLyiCKE6r+tDpBHyVs6q88yI4aLz9/Kpmz8qb/i5N9nv3Hpr75at27Y0Ws19xiZzpXezrjArNZ/Y0takmZ8x/zxeVJWjR2Xyz3/rd68YHRu/fG52bsy5UOzSjpmGDYBgrSFNUrq7u/nITTcxf2aantFRcrdeKiPtosngRuq0P4aQJ4F3Hhsxvfe88pWvYGR0lIW5OUQUa5JQNx1DmOqVMiqjsWEzzK2s/xyJRUDO+5AlQCjKghtvvJFWvU5PV3fw5ccyEdVAztBwsWLjB0Wb3dw+/bFnWXhENbLaDWCxkSRjVbCi0RMN4hwVY8gUEleStnIqzZzt/YM88cJLefJ5+zh3bARWV5l6eD/TR0/RWFzBolRSE0qGohWp0XJ0D/Uztm2SbKCfpcTyrfsf4B/uf4AzvkmrWmXNWOoCeeSZhxOAwMoWhUTC8Cze0d3fx9zaCmXcOHvvSa0liQzrwJgMz4kHTGJFKhU0Sw0iPYhPN246G2tjgN5YG+vHYc06a85J+rJKpWqsDYq095FNFURRkySduub2oKnNFuPj4/T39HD8+AkoS0ya4EXInQMklmIYSoGGtWgerA9OPF87dIDTC2GIvnTrFjaft4uewT6OHzxB0WyRpQbvlSQ1WFWKpWUO3vUQfcem2LRjM1vGx9l28cU8adcufnDkKN879CiPnD7DsuRkaTyGNZbCB29zKz4WoqfYqXJWNm8dx+cVG6Y7XFkGUkccgTrDdRwiTGjD7ng520E7FxS/f7TP1jsngHGoFZC2J1va7XMCzpWdScoYS+nK0JQooqgWAg0HTTGai1cX9HcV0sRQOqFSQVotR5Y2WkU+U8mSR+qNZlZLK5lzOb/x7359fGl5pfqb/+7fyerKqnjnSBKLL3JMWolNgWFodmWwIogNm4mF+UVq3V18/KMf4c1v/yU+dtNNDI2MUEkSitJ1NiZe159J6fQZx0HFGlplSU9fH81mk59/48+ysLDAm37xTczMzNBoNMAEqoMxSWTyxiEaKPKcmdkZCleyc9sWPnHzR+QX3/L27O8+/4Whic2b9zjnlkSZ8YVb1YptuFYjd25ceOou4ZZbhP/FMKGqytatWysXXHzF+c989jOfUeTFljzPszCrqqiLNdnRDGBNQrVa49H9j/KZT36GpKubIsjTYE3HdetjSZHEqvi2r1YI/mhrhJXFJS7Ydz4ve+lLWV1ZwXlHJUtDMNAFYkuSph3iRru2vVM21GYti4RsQ7QcOFfS29PHA/ffz5e++CWqfX0URdkpMDKRqe5iMFc7jzqEcEU9SRzPVeKplrTZzsTWyhjsRUDDqVGiSgqk3pGVBbbRpKv0nDsyxlWPP5erzz+P7QN9yNoac/sPcProCdbmFjCq9GSGIldcEQqWWg2HyTJGd0wwMD4KPT0cXl3l/7rrHu6eOsZqItQrFRpiqAM+CaQQjegbUUiMIUORVouKNQwM9FOgGFdirAlUDjnrwmlvcK0BCa59L0KWJSSVxIDvxvts46azsTYG6I21sX4clvcmSbL+xNqai4xV2t7GGIJJrUWshGAX4QaZicE3mxSqnLN5kqnpGRZX62i1gos3fY/iY92z84pPEtSHIchVhB8sznL8tiUOz8zxlH3nMjo2wrZqhdkT0yxNzyPOk1bCw0mjL7I+M89jC0v0DJxkfNsmJiZGef6+PTx5zy7uP3mK7+5/lPuOH2Wu2SRPE3y1SiEpxnm8CEW7ijceIWvn1hdaCK1YUBWJgzFeifJaRJC1S1TAE/yo3ruOio3/p89hZVEYIIl0PllXt3Udlxc5uMaa2P5nSZIEEfEq5E60IWqaiaEQ9a6UMMClqqYEUVWRSlXzVtORaqPVKmZrqX2kkTfTLM2S/sEh/YN3vGv89MlT1ff88R+ZIs+l0WySpSm+zInSZzjyF4mFK2EYtollrV6nq1rlvX/x/2Pz5CR/+O4/pKu7h2pXjWZRYCXYE7wGhKBXj41zoYs+3CRJyEuHpCnVLOVXf+mXOH3mNO961zuYmZ1jZXGJxKZhgxJ5werDUb3EIo6lhQVcUTIxOSE3fOB9/Ntf/XeVGz960+aRkdGmEVnKLWvG5a2KTYu8e7VgpmHiLK//i9xne+LEiaHf/N13XrJ5ctNV83Pz3WVZkhgjLnrX20SLNLHYxNLb28snbv44p44dpW90gkZRErmMHduQMW0fc0S+GV0PtErw7bdaLX76p3+a0dFhTp6YIkkszkclOA5zZUQMtk9OUA1+5niKgLSV7MCZTsRgxVKppPzVX/0Va8vLdA8OUJYeE2AieJV2q3y83sP7vB2sNZj18tCYqWt7Im28ji0+2Hq8I1WoiZB6B80GSStn0GbsHZvkaRddyCXbtjHeVUXrdaYfeoT541O0FldIrac3CX9/6UoSY3A55CX0jg3RNzJEz9gQdZty+2NH+NJ993KsuUyeZayZhDpCSwyliap6JIQYEaxCRRVT5PRWMvp7e2g1GvT19zO/alhzJZDiymAxkhiM7XwGWLBJgiaWsgCbWoNQU9ENBXpjbQzQG2tj/VisLrVqpddAxRobKBxtJUUB70iskCUW8WXw/eHxZUkCjPT1sbywRH8lY7C/nyMnTlKrVMiNoYUiBiRygEsR8iTaK5wjr1paec7/9ejDHJqe4eq9u7hwcoLJvefQO9jH7NQ0jcUVstQEz6QXuishjNSanefo3CJzwyfoHx9hYGKUJ24a58KJcQ4vXMz3Dx3kvuPHeGxuhrRSpaenmxaehkKz9Gia4EQCcCS2sFmznuQ7O+jU+ZoGPoBGHrPiYmBqnYxxlrT6T6p+jp851nkv1tpASFAfNjLama/i300nTOa996Imt0abiual0yI14jjrt0jTxBSlN4hqpVJB1XutuaZ6M5dZf6BUn7hcXdfgoP/g+98/sbS8XPuTP3mP7e3tZXltNXiX9YedDhJLy70GZnRiE+qNJqXzvON3/wND/YO88x2/R6veoNrVjfOO3DmSGFLUSJrwba5EROj5qJyqCD3Dw/yff/AHLMzP8wfv/gOy4YSFxQWMMdSbTRJrsAJiA6UiSUK4dWVlheJ4ycjoCH/2Z39qxibGK3/8nj/Z3tPbR0+16lYbTe8kLzKHY22thGsdfJL/lRTuOz/wgXRiy+7dz/6JZ+9t1BsjrVYrWWeke9TajvXCWENfXz/Hjp/gk5/5DLYWnhdtc8nb4dG2YBsnUBET/fka/e+W1ZVlLti3jxe/8AUsLa7E4htDWZYhXBp/ZlGW6+Uk3uPixqcsy2hhirQZQkund47+gX4efPBhvvzlL5N21Tr+7aBkr3PWjax/TFhjY8W4p7P57Ng21m1UNiRSyUTIRKigVJwjabZIWwXjtSqXnncuT9q3j/MmxulSRdfqTB8+yvypM+TLqyTq6Irto2URCniMMbQKpdLTzejEKL2jw5TVjEMLi3zt4f3cfuwgS1ZppSkNsTTFUFhDGT8D2gFHC6QImStJvaOvq4vh7h6sKAMDA6y5EnEOmwglgW6iIiRpuv5kRJqKsZY0MUga++6NVnG6MVtsrI0BemNtrB+LtaqCMbVSJLVpuu5/TmzwPBohj6bMNEvWFStVurtqNNbqjPT0UHpPSz27Jzdxcn4eKR22klEvy+jpDMpa7oOS5UxCWTqaNqVlClYWT3H0zgUu37aDJ5yzg12T42wf6Wf5zCxzJ2fI63Uq1mA0+CqTNBz9t2YWOTWzyMxjx+kfH2Vg8xiXDA+z76orOXXhhdx//AS3PbqfQ/NzrOJJKhWqSUpDHbk3OGMUlWAG8JEpYATFUxaFaLR6OO/WSQNRAQyDXuRFC+0K7sDgsvYfrWiWZWqAVESshD7qDn2iXVKjGMRERbKD1kONGG9ECl/SNKJ5Zn0hIh5VETlrK6DedCAIqoYcdZam92YuFX3MqaYOQ9/QkPvMzR+bWFpc7Pnzv/xzOzY6xtLSImktDUq4tj2w7frvtn6viBXqjQbNVsG//TdvY+u27bzlTW9hbXWFnt6eTkjUtBsWNdaVmzaTeH00VZTcKV2DQ3zgL/+SpYVF/st7/pj+wUHm5uZIEqHIWxSyPsUJErzj3rGwsEAzb8n4xCZ913/4bTM4ONj9rt/7/e3qy6d0V7vSZlHaojR3bzOD5bHzH3Q89E9WoQUR5cSJrrf/n392xdjIxPlzczNZ6ZyY2MxprQkbLBOCckYs1VqVT3/6Mxx8eD/dw8OUpSNLEsqAJIwtfBpIJbKeaNc2GSW+jxqNBtdd90q2TE5w7OQUYdMVPNeld52Ti3YxinMuWnODjUN9sIiULgz71gg2lqNkWcLHb76ZmVMn6B0ZpyjKTuOmRttFakM5i6oEskhbakZIo0Ujll2H97/XEO41YXCuophmg6TZog/D9v5BnnDpuVyxexc7hoeweUF9dpaZM3MsnJ6mtbxKxQrVtpqtgWUdrGKK2IzR7SP0jY1gevs43Whwx/4DfPPhhzncXKCRWBompY6hJYJGGoyPGw2ngeCTek8VweQ5OyY30ZMmNFdXmBgZ5fiZKbqHhuIxkemw4k1iw+dle0cRT2tKm+CTlEoFJLQyVayYzG/cdTbWxgC9sTbWj4MCjZRYq8aaxAZVliQJ5+rVDHJPJbM40XA8rOEmnxpYWV5mdHScFGjW6/T39GCcY8+mCR47fYblRpPuLCOPt1cf8U4alUeXWFooLU3p7k5pNevMHX6Ih0+f4pq953HZ9s2MbdtM73A/i6dmWJ6ep9nMqVpDYgW8J00NKoaimTPz2AlmT0zTO9rP4KZRtoyPsv3883jirnN4+PRpvvvwIzw4NcVcY4Wsp4tVY6k7wSZWRYz6DgvXx+kohq46JAXfQYJJ53fSDh+2k0H8JwqZVfUCpCqaGBHxzotqCHZJxH+Vbv2IWSPFIlo8vKovRF1LrM1LQ4GISksNgmaZaFECGWR4m+egqgZVCwUi5AUsJHAE70xZevrGxvVrX/zixLUvv7bnxo/caHfv2sXMzKx0d3fjKKONw4ALlhLtMJo9SfTZTp2e4xUveyEjQ0O85rWvY35xkf7+fpp5CXisSTqc3OCtdTHYFmkf3oWNmlj6Jyb41Cf+hjOzM9xwwweYGB9nevoMZETF1XR8vmUM1pnEsra6yuHDh2VkbJw3v+XNZtPkZPfb3vbWPUtLi8nwyLBdrdc1r/h7h3I9Of9UPLdQ/hNeN73mmmuSBw8cG37hi3/qkpXV1R1ra3WMETFJGpzexlC6ktQE73N3bw/T03Pc8MEPkdSCsquYDtWijRAMFJtIW+ko01C4kmqWsrq6ys5zdvHil76UxZU1yqIM9g3nkMjiNoTGQzCdXJu2/dU+7BVcRFW22ztVobu7i8NHTnDzzR8n7eqlcL5j9G3XaQfLRLAxqYTPBBdLdBIbQ6comUR/c+lIFDIPWZEjzQZZUbKlu48LzjmXJ523lz3jY4xWK+handUjR1mYmmFlZh7KAivQnZrAm7YhWekcFE4xWcbA6DC9I8OkfX2sGcODp8/w1fsf4IHpKZaMo5FVWUNoIOTGIjYMzxqV5/+bvT8Pu/Sq6vzh71p73/d9pmceah4zkYQkSFBBkAA2rdAgqBAUxBFBsbXb7nbqSX+v2totdrfTrwVkRgRkCD+0u1FQAjIoBEhIKklVpeaqZx7PcA9777XeP/Z9ThV2ezX4vtd7veE667oOIZWannNO1Vl77e/6fEQUCTOSENBQxWSjgb1zc5htNbG9vo6FqUn0trcwPzmJXgjI0hQiJUBJfXJTmNTGBpo0ZqAtQwwD1sIAYGsJ4DTEDPRYojKucQM9rnE97msAtSreGiPWGHCWAlkau0PngEBgQ0gTE/fiakSGBI921sBEs4H+xhYaRLAhIPUBSZLguj17cHFjE9tFCbYWJSMuonGdo6wnVMYYBDC8BDSSDN4EnMq3sfylv8UXzy7iGddfhzuPHsLiDccwt28Ru8vr2FnZhFQVbKRnRdMZEVoJIQSH/vI6dlc30Zy8jPkDezC1Zx7fevAAnnTwIB64dBmfO38ef3vxPKq8D+q0UUBRaQCDdDhl42EINVpZRmSEIeZNhlg8opGNcKRJFgCXvuoJNDnjDIAM0ASjHpJHuUzVq0QUXLtgyISgGpSoEuJKgnhTR56HmQvyAEAaN5dS0qRklGISa00lZIFAlsiJ6K6CLosQF3mBifmF8OCDD+2/+7tf2n7DG19vn/q0p9LK6ppaayjquuuYfE0gCSpR/W0tjImLhksr63jGM56OD93zAbzyB38IZ8+ew+KeRfTzsiY21EIaEJRR53Z1tJyJ+np9UDq05+fxqU9/Gi9+0Yvxtne8HTfdeCMuXrxYEzlCnPqNkkcKCbExD85heekKfFXhRS98Ac/MTGf/9J/+1HWXL11u7D+wv+G9Zxbn55ZvWt7Ao4PagvNVcZ/vvffezuv+y/99bHF+4djm5uaMDwEppwiiUXVdRx6CAtYYzE608c53/hFOPXoSrcnJuumMX+NwqU5xVY8t9R4B6puIxBgQgCLP8ZKXvATHjx3B0vJKzJZLXGoNLsCwHb0uRAQfBKbWbQcZXkLoSBMuSkhsBiZGu5nine96Fy6fP4fmzEy88aipKYI66ztSfjNCfbi09bg8IQKpQH2AgSIhIA0exjnYokJLBDctLOIpx6/DNxw9jOvm59ASQb61g81zF7G9tonB5i6MBKQUv2ZFVIpLEIQAKBOCMiYWZzG1OI/mzDSqxOKR9U3ce+JRfPHyZaz4AYo0QV8ZfSU4m6CsJ8a2Zk9THb8yAIwoElFMNRvoMGOx2cRgt4vJLIMNAaGsMDU1iaW1NUioDyw1qA9EMNZGXAddbaJtmiDNUqSG4wkJYqCU4s47Le67L/x/04I5rnGNG+hxjev/10Uk5KWfcFImWQOTM1PYaGVgATRXqFiIYZBNYAwDGqePIXgszM6gKirMdjpImLC2sYnrD+7HQ2fPYW7PHrQPHsTJK8vYLPKIk7PxqlTk6pJTlJoQSgKEIxO4kRl48bh/ZwWXvrCFhy5fwdOuvw637t+LvTdNYXbvAraX17B1ZR1l5WCJYG1c+CMCGnVjUG3u4MpuDxuXl+uc9CK+9eghPPmmG/ANly7hfZ//HL68sQpOUiJilWvQW6oyGinHyMpQnW3qqdVwInx1E3HI300ABZKvPsLh2ABoAEhUlYCvNEyzMVANkFGzPpwaQolUwOQMkTNMTuADcUPizwM4VCCkIGJVqTiaABOuVIw1bJVgIEJE7CC6S4RlIpM45zE5OaWnT5/a98pX/sDEH/zBH9hn3nUXrW+uI0vTOrsbxR7iQ22n4zi9pzi/DyJYXVvFnU9+Et77x+/Cj77q1fjygw9idn4OhfNg4pGcheoculLUdxPFpjrUE2onAe2pKTx04gS+9/tejje98Y247bbbcOXKZThXQWrMn4gfhdBFYosjrsLy0hUqixLPfuZd9La3vDX76Z/+qQOPnjz5jMU9e1MX0DC5fHzP7bevrDzwQP5VpNhJVXDDDU/c99zv+PZvcc7vy/OcVVRDCEiJo5CIaqMgG7Q6E7i8uo43vfmttTyEYsMrQ2TdkHAT/4ygbrqVh9yX+HasygL79u3DK17+cvT7OULloUGg1kClzugQICHU4p3IhQ71zz28SWGi2DxDkbCFD4JWK8P5y8t4+9veBttsjjjkozsXirljoXiujCbCegegvjFh52BUYYOgwUBaleC8wKxJccuBw/iWG2/Ck44exmIzA/p95Jev4MLKOvKNHUhRIjOECY4ki4hqDDFbjciYhk3Rnp7A1MIcWvMzkCzD2a0tfPrR07jv3DlcKQfopwb9NMUAjMJGM2ogHkWQRCKnnDkuBpu4fIDpZhMH52ah/R5CPoCWBaZmpuGDwFK0GR7evxeXHjkBThsYnqrVGKSZjTEOIiBNgckWbLuJdquFpBDEayAmkE1w6VIKIB9/+IwLY5HKuMb1eH6nc5CBW28E6isMjh4/hnTfAkIzAzotIEvAiQUZjvfbdUYzTSw2NrfQtBauLLG9sYWmMTh37iIWJybQJMbm0jIOLS6gnWWwIFgFkpgmiJKEmgpAqggKVCC4JEGeZOgmTfSSJlYt4a+XL+Btn/kU/vizn8cD69soJyexcMN1OPrkmzF9eB9CmqKXBwRoLWgQMATNBGgZhXR7WHn0HE7ddz8e++IDyK9cwZ2HD+OuJ94G6g+IQwDr1TBtPYVWkZqCQRg1/qMmBdHsJj7E6eFQ6aYKgShw+qtsoG8hZrIAmhJCiprLG0KMMGA0ga512BoPHCFE4QUxe5sYR6yVZ/FkjCf2wZng2QTP3ng2wZPjQMwBgLrYqTNUjVW1CjWAEix5YvQMYSWonC/L6uz07MyVy0vLOy9/+cvdxz72Mdm7uEfzQRHjPIhkFmZGkGjbg0TRB1FcLGTDWFpZxW2334L3vPuPcOedd2JjYxPNLKtzvTFqQLVMg9nUFrc4KYwRhjiRzYsSk7OzeOzUabz85a/Agw89hIMHD4LZIoT4WgCR6y3D96oqUpuAiLC+vo6HTzyEJ91xO73rj96VPfkbnnxgeXn5aZ1W63lkk7sG690D++68s/F/+vu/vhFo/fS/+pkbDh7a94yN9Y155zyMMWSNgfcuZo7rd4C1FhMTbbzv/R/AA5//PNqTk3Be4GrE3fB9NWxKDXG8WdEo6KD6OUoSi163hxd/13fhyLGj6Pf7KIqibmQ5kjKU4J0fvWdC3YDi6oZbnIzXERmus9oKxVS7iXe+/e04f+oU0kZzRFqJeeaYTJfhxDVS98CIfGSrQFMELRFMQqJme3cXi5Xg24/dhH/1/BfiXzz/+XjOdUcx0e1i5csn8NgXHsDFh04iX1lDUhaYSBgNJrAqOBASa0DMKJ2gEkJzbgZ7rjuMxRuOId23B5ecw58+8CDe8NF78T8ePYEzUmC7kWIbBjswGFiLyhj4OicdUTeI8icCUuKaBCKwErB/fhbbq8uY63Sws72F22+8Diurq2gkFgcXF7C6toGJZhuNZqvOtQNkLYwBPFNsoNMENNkCpiex/+B+NJpthEEFlAEIADOZmaqy4xjHuMYT6HGN63Fes3v2uM0LVy7vLK1sTx7fh4XZOf2mO59En/niAwhb24DP4K2BJAzTatZTltg0TU1MYHF2Fiv9PqY6bQCKViNDo9HAyu4uju/fh9WyhOsPkDbTmArJC3BQ2DRB6XwcvxlTc2MVAoInwLOBTxhOVFs2wZIEbF44gy8vXcZt+w7gm64/jhv3LNDi1BRm9/fQW9/E7vomql4fVHmkSRQ1QGMW06YE7yusnrmIvPI4PjeHZhC0kgYqBUiFVIgEcRVfVYmMgdKQGnGVyatydSJItV46GvLMcPtev/rr2YpcVSUANUOo85EjjfewUdehWXz064YQIEFUVQKCuCDq2LLnigOIpIGa1ceImhUuCC5VEmXLJIpEAU+qhqEwABuoGFERVhoAtBZEuZsXaLRbWpSlfv/3fe/EL/+/fiX9idf+JC+tLJMTjdPo4GHYjCQ1pIAPHsaa0cTz0qUlHDx8CPd88E/wAz/8KnzsI3+Oxb370CvKq18UMYJG6sTw8DLK/3oPAlCWFZqdCayvr+O7XvgivP6Nb8Dznv88nDp9CvlgAEsJguGaiKIwdrgkZ4CE0R8McOrkozh27Dh94H3vNT/787+4/93vfe/TF+YXs+n2RMg3+59duOWWK2snThTXxDn0GvAGbrjhhnRmz6GjL3j+P7mzLKtb83LQsRybPT/MdXP8ulObotPpYH19E294wxthGw24EEZfG9PV2HwkZ8SJc5Sd1GISEVhm9Hs9zM/P4+Xf93KoKoqiqukZFnUDH9+jIcAm9qp+vj7ckIkHr8hDR8TZcUQSTk9N4vLSCt75rj+GyRrwQUfJfq1jMTzcAxCMjJMGgFFFIoKmCjJxMHmJGbJ46g234Dm33oInLC7AlhV6S8u4tLKKYqcLn+dIoEgNYClO48VLTUIneBV4DyBJ0JqewuTCLFrTMwhZiiu9Hu574AQ+f+4szuxsYGCAPGUUnKAAobIMd82SIJhgEQ2CVuMSY8gLEBsgSUAcMZksgkN79yEjxvGDB3FpaQUHFhchIWDgPPYvLKDb7SFJEqhWgE1AqQVlCTRJgCyBmezAd1o4ePQQjhw8CFID3c3RX96IyBoFRCYJ2Bp/+Ixr3ECPa1yP01IA2JwvHE4NrnzmfR/ZlkaKw097IvYv7sGdt9+CBx5+FEVVgRoJklYDaacJJCmMZZAWcGWO85cuYTpJUOQ5gndIrcXKzi5m5udxeWUV6cw0SAXkBewdZtMUnbSBrY11pAw4NXBEcdGw3l6XWsAAjtPeIEYKDpIRo+8rWrl4mh5YukK3HziIJx89SjctzmHxxmksHtqDnbUNbF9ZRzUYQFyANbGZUe/B1qBpGAniB36DACMCch4KA7JMoqqkQmQZxF/pRxjSMVAvXMlwVMkcUVi16s3HLa2vctm+4OBbFkCTmBNjmERq0USdW712WDWcLLKxMNYqRIMXdaJcGR+nzMSV5ACasUlTAMhhkQVnGrAU2BkoG0cUDDygxMpqjCoHAGzIB6G+YawHBXsXxCapd1W57+d/9mcnRKTx6le/xuz2uuRDzIQHFZAOIyYEJoPgw1VJDRM21tcxOzeLP3rbm/HjP/5Pcc8992BmfhFeJMYF5KryWSnm4odT2KGWXRUovEMrzdAf9PEjP/TD+K3/8lt46d1349KlS9je3orLeNDRFFdqY6GFAVmLwSDHuXNncezoUfqd3/6vND8/N//GN77pm9qdDidpmvV3y7+aOX58bY65OH16SoD76tfyLnrBCybSP/3TP539zd/5b8+enZ9/9oUL56eYiRObjEgXAODLClmaQIKg3W7jt3/7d3DigQfQnp6BCxJlMPU+AAyNlic5+h5hechPjn8GMmOw2+/jxd/5IjzptluxtbWL3d1dZGlaR4siTLGsKiSJHaEZmeNhQjWykkUElmI0BIhWRGZGmqZ4//s/iFMPPYzWzAxKV98s1JNbqhdXh5p7SMw32yDIAGTiYfMCM8p40sHj+Lbbb8cT9y4irUr0zl/A9soGBjtdkHcwpMhMlLGQAAGxqQ+sCF4gYNh2A5PTU2jPzsBOtBCSBBe6fXzx5Gl8/ux5PLazgZ5VVA2LgRIqMCoycEyRQ19TcoYHEiOCJARkonBugGN7D6I9PY0Tj50GpxlCWaC3u4NjR4/h3MnTmO200e/3sXduDpvbO8jSFAt7FrEpAQgBZOIChmlkQJZBMgtMtuCnO5jftxd33HQDEiH41XV84b9/HOWFFSFlJ1UIzLvj7PO4xg30uMb1uC+3xyPxq/lDZ3Y//Y57YJsp5p54DPv27AWI8PmyRNVIwY0MttUAUgvi2NgszC1gWgEMBmhmKUwjg2FCliYYDAa45fpjuP/seTApDAFVUeDg7H58//Ofj7/57N/g8w8+iL44eCbkGqUGgRkuLldpTSUIOcRXwr4yiU/YSkCgQVUky+dOJvddPG9v3buXn3LkCG5cmKd9Bw9gZu8iiu1dbC2vY3ttC+IcbEJxYU0U4iLPOiGukVQgYlKBIjUmgrKEAAkEFURIRsx6at08aN2caY31GyHYYj5a8XeDzH9f7QsUmC2ATOSq5lcQXYIyXIurm3cZUiaY66kvBRA5S+yJORCMFMxCRFpGb7JSniupUtloiMIh8ZaEiRPvnDBFsHeIgVauidOG1AWVvgjWGaTeh2CS1CfMe3/+X/7L6bW19ea/+tmfNb4oKLJJCCH4mNeunw+qM85DfJoPHqsra9izMI83v/mNaDSbePe73425hUU4L6h8gLV2hF1LyMBrFLcYilP4oILUGEgQ2KyJsizw2p94Lba2tvGjP/oqsEmwtbkOrtXU0KgeBwD1caqaZSmKvMDFCxdp//79+JX/61ftwtz83K/92m88pd1ph06jnTgXPr2k+dLs9Tt50r09AEC73bOf/OTDc9c98Y7bX/yi77yr1+3e0h8M0jRLEZ+72KxWIea7AaDT6WBjYwNvf/s7QDapTZhxUVIVQ3kliLluVLVeABQYY+POgSqC85jsTOBHfuiHIUGwvbVV0xItQvBI0xTOuREecNhA15iWSM4Qj8RYKCI/OU2i8js1Fttb23jTm9+CpNWEqafLVK/ajaQriAcR9oIEioyAJiuSokSWF7hlbh/+yZ1PxpMOHYAtS+w8dgb9tQ2U3R4sASnHQzEhTpuNYagBxAPeK0ySIJtsoTM7jdb0FLjVxG4QXNjaxgMXL+P+cxdwvr+NniHkKaMyCQoleGYEY+A08sNFCaaO/SQiSAloMIGKApkAd9zwRLzwO74DXzx1Eg8/8iCMNbCpRZZlWF9bw+LsDCwRjuzdg/sffhR33HwT1ja3sLS6hql9ixAfYBtpXBRsZeBWCjQsMN3BgaOHcOvRI4AQdGsXX/jQx3DxLz+j7ERITBFUqi3DMl4gHNe4gR7XuB7vdd99AVNTO2jwbvXohfITf/gnyTNe9T009cTj2L9nL26+I+Dy6jqcMWh0OoBNIKiQNTKcPncGT7/hRuxsVWhYA1c59MoKc3NTWNlcwUSvi06rCbMRqR2JCpLKYTYIXv7Up+FJc/P4yOc+h/PdbSRpgtwpCrFgYg2xwwgB6oW4CoxBAAoHKQunknGauAY3S3Wt9cvnGw9dvmKPz8yaJx85TLcfPYh9C3M4OD9Ps9s72Fhew9bqBrxzCARY0iiSkBoVZ+r4gYKCCszQwihXBRDBh5q8ATDVjbNKNJ4zX520EtU6Bny1FhWSEAzAKQFmGN3QEMkSRDQicYxy0RRFNCFq6sTABE8SULFQVjfNBQuxEaKBwhhlIpWqMuJTVLYi9YYtG0ukpRFNShIDIsNDOAMhSKBKVftCCgZJCCLMJjSnJsPrfv1XZzY2Nlq/9uu/bquqhKscksTSkNowXL7E0FqodZY2eCyvrmNhfh5v/sM/wPTMNP7gv70ek7NzMfNKQOUc7Og55TqCEF8LSxGTB8PwziNJMxBS/NzP/AwuXbqEX/qlXwYzY3V1Ob52bCFer8mRhxj3riMRF86fx/4DB+hf/sw/N3sXFxf+5c///De7Xsgmp6ca5Y75ctJKrhQo+8xOJhqTnZ2djRv+5b/9xX+0b9/eO06dPDk7tK2XZQVrLIJG8ZBCYROLzsQE3v72d+DkwyfQnppG5QXGmFp7PYxrxDy9Rnd3fP9FxTtAitRabK6t4+6XvhRP++anYG1jG3meI8saUBUkJjLVVWNUpfIOTAxj4jKjuQaPBwzjMLW4Bor52Un8wR++FQ8/+BCaExOo6miHqo6whFzLXWxQpFA0JKClAvR2cbg1jRd8y1PxzJuuRycEbJ27hO3VNfheH4l6tCxGh9C4NBr36aoggDKMbaA93UF7Zhqt6WlII8VGVeL0xcv4wplzeHhlGStVjgETytSiMEYLYpQgiKmRjhRDJiKAZcCoIBVFQxVNCaCijz1ZG8/7pqfhqbfdDrIZPrWyimR46A0Oh/ftRXdpBRNTU9ja3MLFfIDjhw7g8vIKAMbs1BQmpiZRVSWYUsASuNUEpwmKRob2wf24+dgRZJTAbPdx3wc+iov/81OgvoM6DizSzzjJy5TD+INnXOMGelzjwtdBlGN6urA7Ozsh+G716MXpv37rPfzNP/QiLN5+I47tO4gsacARI23HpUJQlDUc2r8PjTTBLmKzCQVmpyawsbGNJ954Hc6trmNydhoUPACCtQZUlsDOLgwbPP3QQVw/MYHPnHoMnzh9CkvlAGmaokoaGHinlaEQwJWSDoi451W7QdE1lgs1lqogzQw01Wjaaa/S3tpeb5za2rSfPX3G3HpgL912+BCOzM9hcWoKk/sWsbGyRitrm+hXIZIOiOs8s6phRiWCIDS0csAwD6lytaH3aoSDRg1ZLRXBcNIXiWpfUwMtwQJIiNkQ0WjCrAIIJD61InG5sL6Or2UqqlARCuLhNWsEzYlk1DxzLmysEHOEMzArUAE+hdgK3hEbghEDY8AEAQtJHOGpMAjBgkow1QuNREEiRbo5PadveeMf6vr6eus//5f/ajudCe71umqtGYlgVGOWFwSEWrfNNkHwHmtrq5iZnsZv/9ffxMzsLH791/8jJqdnYKwBS7iqnkYkq0CHy4TRgBhCRCBWPuLb2nNz+J3/+tu4vLSE3/qt/4zDh47gytJlaAj19HTI9I5xE6VIYBgMcpw9dw69fg933303LexZnPvZn/+Fbzx77sLswtz8saJ0X0osLaVpVq2urO+54bbbnnz3S15y1/r65v48z2FtguBixljExxy/AlmaIm1k2Nzewpvf8ubIdSYGEAUgkZBx9fA1vK7gOrpDtY5wmP9utZv40Vf9KIgI21ubo3sKFcADCN6h0WiOJs/WRKuoaqShSC0w8iEg+IAkTWCsQZJkWN7Yxtve/s54wwHAB62n21ffi6xRgtIUQZsJaVWhVQQ8/YZb8fw77sANM9MYrK7jyqUlFNu7sFBkNl6hkMSvbZhv9z4yspNmhs70JNrTk0gmOvBJijO7XZx47AweuHAeZzc2sKMeA4aGdgu5KHIFKmPEUVw/FlVVopjqVuGEGYkqMoBapEgrh44XfNOxJ+B5dz4ZxxcWsbm5Be20YZ2vQTsCBMXS8gpmkwQ727topCmcqzAoCmRpiol2Gys7u1g9XyJrNtGv/6w3Oi14Q5iZnsTR1h40OUFY3cXn7/lLLP3l50G7hVpviQICwLuWNS+Xxi6VcY0b6HGN6+ujgT5/3ie2ud2abGz1BuVk9fBZ/O0f/3c8zRjM33IcB2bmEPIKtt2BSSyobqC9c7hweQkHJicRqhLdagAJCRJmrK9vIk0s8kEOYyx8CBBXxetmVTTKCv21DRydm8Ke22/DjXv34qMnTuCBlSvohj4oyQTEXhmFEPdF0VeiPrHpBUVfAMeG2QfdqkSmC8JUo5lO5K5o7Qy2Go89up1+9twFc8P8orn5wD66+fABmrvxONoH9mJlYxu9AMAYsLUxfxtqbJ0KiEytQXax2akn1FrjxYYxjiFiK6qTa1OM1siCr6GBVjUR3EXEVBMoqG44QBrxfDUdJISAUCuxI0JPhcGSUCKgoESksXm2YpIkgEjrpUZICGQAD1SAS0hsxeyiyjA1gMCTF0JUGBJDtfa6qGfiQlV2GGpI2figlE5N48MfeB92d7qt3/m930n27dtLOzu7YKbI9w4yEpwYEzFr4gOMMSiKHBubmwAB/9e//0UszM/j3/y7X4YXQbPRQF6UUAissai8qyUeUUVNdfM7nPqLKISA1uQ03v+ud6O7u4vX/ef/jMOHj+Dy5YvQokb/GQsJYSTACSLwEpD3C1Suov4gxz9+7j8y09NvmPpnP/MzT3j0kUenJydnbgDJWWbe2e3vzP/rH/rZW/bv3XvoxImHWyJDmjWgEhA0fq1JkiBJLGamp3HPh+7B/V/4IhrtDkrnYY0dLYQyE8I1N/lDlTYxxfdf8Gg3G9hY38CLv/MF+MZvfApWV9dRFAUajSagsbn1vkKapFCJOefUJiPsIpFCJZJimAyqqorvqVoVPz0ziff9yfvxuc9+Bq2pSZQuwGAoTLlK2rCqyLygw4q0O8AeTvBdT38qvv2O26Bb21h9+BH0VjehlUczYUAF6qWeDNdM7wCQNWhPdpBNttHodMCtFvoALmzu4IELF/Hg0hVc6m0hZ8ClFpVpolRGKRDHRjyTD0QuECpR8QqKaGeljKCZCZI0NVBDA1plwNGJKXz7bbfh2bfdgrb3WDl3DuIFE+0M7F1tNYx/F7QbDVy3bz8eefhR7J3bg7woYevs+ZWVNVx3w3VYKQu4K+eBRgsgjgcRtjgwOYWOTeFXdnDfBz+Klb/6PLA1QFYqsiqg8iGYLNsNyjmuTxSnxxGOcY0b6HGN63FfL33vS/Xkz3wuX1lf6Zsm6W53gPLLZ/A37/ozPP37X4jp6w7D2gw7IBibIKjCGIu8KHHb0aNYu3AJ5WCAg3sWcPbiMm698ThOnD6HQ8cPw2UZ7nv4EXCaxgyxCCABGQGrl5ehO7vYc3AvnrK4iOv37cNnz53HR048iLODnooXL0y5s9oNkB4xDwRagLnQoIVlDp7RE2N6LshOpTJhTaOT2dAuGK3tot+8cPlM9rkrF5Lrzi/a2w4f4psOHqC5Y4fhkwb6YYtCnEKrcu3sjq0FRAIxSKFKqrFZDhLVxKpRfiG1AhlBRlGP2EB/9Te0cwCs0Tr7wSPNsvCQ9EFXM9AQCMUpYTQVKohZQBAfgmRpQzEoAQMQsQ6bZ9qOP5kBa5gAWCQAKeCUjGWCrxCYIGzIIkDJMEMZ0YXBzFAELwStiG0vqCZCZOADN2YX6d6P/Tle/n3f13z7O9+RHDl8mDc3tyhmcaM4J16Rxyno8BBgjIVzDmtr6xAl/PPX/hgOHjqIH//Jn8Zut4upyUmUZYkgAjPMUtdxFiKCSiRDDKe4IQhUBe25Ofz5h/8Mr7i8hDe8+Y04fuw4li5eQFlVcdnOMCTEab7WHPIkS0EAtra3cf8DD9Edt93GH3z/n3Re/ZqfOPaZT396bnp6+ki/u7t74w03tF/wwhfu2djcbJdliawRIxSu8mATTYKJZVjDSNMGqqrCG9/whxFTV9NJtD6g4ZpbDXPNtmrEyhmE4JEYg6pymJicwKte/Wo0shS7Ozuj2w5DDB9kJNapXDVSdQ8NjUwUn0ObwPsACVIruwVplqHfH+Dt73gnQlCEEJc1OQ78RwuhJgiaxOhogN3p4aapWfzgs+/CNxzYj/6VJWxeuAK3vYMGJAIRg4/Pc/yjAa9A2kwwOTMB22ohm5oCNRvYdA5nV9fx+bPn8PDKFd2oChqwwmdWS5A6slopxDN5YVMKc+5FcgADF7RvjSnj+FhThU4aldlMdTrzLpsB8z+67Q564ZOfhP1ZgrC1hdUryxh0e5jeu4gEAcFVsACq4NDIGkiNxYMPP4IbDx3C6TNnsX9xEWcvXMKdt92K85eXce7iElp7ZmolvdTUoQY6aRPsKmC7h8++/8+x/okvgrb7aBUBrTxgpjmBib3z/vSlKz1JucTpqfEEelzjBnpc4/p6qDP/8Qz/9Eu/lz74px/Cl86cRDaVYatXojhxDp98x4fxjJc9Hzfe/ATYzhSMTSAUm6PgHBpJAlLg+sMHcPnKKo7u34MLFy/j4J55FP0cReUxOzOL1Z0dGGvhg0flHcAWDUMot3ew1MuxcGgf5ufm8Kzrb8BN11+Pt3zyXnzm3GOSZM3cq+4yoStBSgUVMKhAVAmRUwa8oiTmfim6lVpuOHAr966d2GQiTWmiL9paXbnUuH9lKTlyesHeft11fNsTb+Ew0aZSBcKRShApU0wiIBFlgIjqqWCQGENRpchArm18w5hBnCjWm2E6ksr9H2sDwESgWhsXMROhnhgaa0fWt1DjzLiOl+hVMLSSUIgX5aTtNmleshLzqHkmumpFNF0IOkpAAah3xlmCTQi+4oRSCgxGUHbCDBWjEfmrAqhllqDBEXFfRS2UuKocWrML+tBDD8l3vuCF7be+7a3JU5/6VF66sgQlIWsiiQLXRFy0/h9rU4QQsL6+AQB48Qufh8nJt+Of/vQ/w5nHzmBmfg5VWY0y0cNpL9dsbqobmeEyJzHB+YCpPXvx4IMP4qUv/h68/o2vxzPveiZOnz6NXq8LXyPkVGqmsQKibvRq7e5s49GTJ+nYsSP6x+94m/mFX/w3U+/9k/d2COxe+j3fzYcOHUpOPHTCGMMUQoxsDM12cUKusEmK6elpfOj/+RA+/7efQzYxgToOPloQtDXiz9aRDUWcHluOS5ih5ldvb2/ied/xHbjrGc/A0toGBlWJNLGABEjdiCdJClf5+jaE4aoKwyGycwJiRggB3sUYzfCw18ga+OtP/DX+6i8/jqzdqZnmdYS9JiBaUbQBtIJDOujjqfuP4oee9UxcN9HC7rnz2LxwBcZXaCQE5+Py4lCo4wOAJMXU7ASyTgdJZwIhTbFaOjz02Dn94sXzOLW2jnXNpWKjvpFKpSwlRIRNCGRcYFQKGghTD4pdEHW9So+ArpeQM5Ej1YwUs6nQEeNKM5s1zGue+x3pMw4fQqcYoHvpMnorqyDn0TYEgxBfK+9holgIBIPJRhPzi3sw6OfYv7gAheC2J9yABx89hZnpaczPz2PVFXHhkwiwCaYaHUyoRbG2gU996C+w/pkvw2z30c4dJouApge+79uei3Mrq3LysVODRqNRDdAZT5/HNW6gxzUuPP5ZdkT33Wey27954see+x0T7/wzx1+8chaGm9jeLTA4cQGfedd/R+e7CQcW9yANQL+Wh0xNTeD8pSVYKHrdAaCKhCle3QZBlqYQaxCCG/WTLng4LzBNCzCQEEBlgZWzF5Fu76JzcB/27NmD62bn8Lkzp9RAclLaFsKuEjnVSL1TkAsqngENyo4hhTCxA3EgNVBOE2NbRdCOhZ9KsuZEDu3s7G42Hvz8cnLT+rJdPHTQFEzsFQwmJmGjokwEw4ZpGHWOBsY48dRaP8315X1sjCLHlpjqq/iv4XqWWQOFGnunQhRxZEOqR4waRMue1nrvegwLBakSBERCRIKy1L4AbPnqrz+L/wU5y9ZKnQkOpVifuorVWg5cETtrxHgiwKiQMSRWCQni0Bexl6eSgR4MmyBKZemkPTEly0vL+vLv/b7Ob//u7ybPe97zeGNrHcHXiLI6jzts4ER1RJ/w3mNjfQPeBzz3rqfhHW97K1772tfii1+8H5Ozs2hmGcqqiuQRwwheUD/VUVFdZyKIGMpRuNKenMLSygpe+YM/hN/4jf+A733Z3Th/4QK2trbiQcRGyYqqwpAZcZkNGFVZ4MK5c7T/wH687rd+k/ft28vvfOc77Yte9CKsra5Qf9BHs9EEFGDLo2y8IQtjLKYmJxFE8I63vxO+qtDoxMU86HAx7+9o2TXqyImGIh9BmhgAijRN8YM/8ANImNDd3oYxDGMtikGBLGXYJEVVVvHPXpoieF/nlgniA0QVlngU/UmzNDbubGHZ4E1vehN8WSBrZHA+QAiwNTaQRdBURZsUWb+Pb9x7CD/2bXfhgLVYefgUys1NpL4C15l8ZkCEIQHgZoaJ+Q6ak5PgRhM+S3BpkOOh85fw+XNncXpnXbsE8WnqC+5UedAygCqxpvTQSokKBeWBtA/DPVLtKmGgKrmCcsPog1CAyBklJh9mWUEU3PRiY6b9hLm5BFubdOn0WWh3Bw0A1jIKDyTEkFoCRAAsG/h8gN2dXRyemsLl5TXMz05hZWMTofKYneig1chw/vIVTB/cCxWNlJWgmDEZktUuPn/PR7H2N19GtpWjkwdMFgFzmuBl//i5OL6wiC9/6f7QgimJ2AH3jj94xjVuoMc1rsd73R0Hek3u92bm03T6R5/9HHrPJ+7FZy+fiR+iVKB34jw+1r8Hz33ut6HDDQyEYJSxtbWD648ew4HWXnz5gYfxhOOHcPLMRRw9sAcb27sYDEocf+JN+NRDD0a2LxSV86hCACWmXrwSNBKGEcHWpVVQI8O+g/sxaSxlROSISgPeNoyNAPYU15KCEgKgNTHNqzLDACoiIgq1SUqFamLZZRXZtmV0ctV2Sr6ZmGbzC5cvNXTpckOMzSrDmZOQEduMSVIAqQQlVY2hZNTX4ByvvsFA0GgCjEtadmQmvGbwrF+VbYxZmcUD4klJ4k0/IUgAC0OUri4v1s30VzCpBaIaAihISVYNsxCxEvcUsMAmhjltFQlEZFS3hDBJMS9tylBK4lPjCN4SW7CFYRVYJW+UKGEgAXMCJVFCSIi8gEuv2iWQkmHJK6dZu6Mbm5v0qh/5kfbv/O7vJC+5+yW8tLxMQx60YRPJJVpzn+uIgLUWVVVha2sTqoo7br8F73n3H+NHfvhV+Ou//hRmF+aRGAMvAh8CMmNG6u7I9qgJE/UmniJOorNWZPn+xKtfg5XlZbzm1a+BhICt7W1472GHeLuIVkHwPmLmmKJw5dRp7N+3j1772p/ALbfcQrOzM1hfX0ezkdWCmIAaAA5jLFQFTAaTE1P48498BH/98XvRmJxCXlUwdU4+PgfxtRwq40Md3YjZZK0V8YxBt4fnPOtZ+Mff9hxsbu+iKApYa1EWJRqNRlScOw+R2ByKBFRlhSRJABFIEKRZChcCKlchTWNOGoYxv7CIT/31J/GXH/0L2EYWb1iGLPNIm0MTwIQqsn4P33zgCH78ud+GWeexcvoU3NYOGnXGR1ThReEF4CTD5HwH2dQkTLsFl6a4sNvFg+fP4wvnLuip3TXtMYUqYedsIy8V3YpMNzS471RyIlsEaEmkORQ5iPoEDFSRe4SKyTij6oiQk2AQCC46jrhiE/YYaNUmhvR75Ht9lFtbmE4ZVgGtCShEDOcDyirSSrwIpjoTOLxnEf3Vdcx2WpjIMmSLe1B5h8QaLK1v4Zabb8Tnzp0D2xTeA5lamM0cH//sn+HyX9+HVuHQ7uWY7pdYEIvvfcYz8KT9B7Dd7yMLXoFQEYWAMcJuXOMGelzjevzXzJ138p777ptiV841q6pjyop/6JlPR+NThHvPnISleI3bPXUJf1N8DK47iEIKxOyn94L7HjiBY3sWsL6+jalOG7vdPlQUBxfmcO7sRXTaHWxvboCNgYdgp99HmJkGDbOfiNniVmYhpYNxniazlDIoDVQqiGyz2FWKODsCBCQ1sgBSUxqgXkQYCEQUAqlAAE8JM2si0IyVMqeUGh8aNk1bADqV6IRXnRClDkLoMFGHCB1ASSTqJrQ2EQ4xcoZszDTUk2DUiC8oXb3//morSUSROACVQGVojos86eFPR7VRLmaJdRTXBkDxzEAcglImJH//r321iWYFAhGzkqqQMcE4JVjDwVfsmAwbNRXUMEwiEhJDZJXJQJWhCELqWImEtFZJE6rKmazdscE5fs2PvZrW19fta3/yJ3l1ZRWDPCdrdcRHHn4NQ7a1TRJ477G6ugIJAQtz8/ijd70Tr/2J1+LPPngPZvfvh0RMSI0Q1JElD9dOtSPUOzamPoDYotlu49/93C/g0oVL+NVf+1UYTrC6ugJXObCJE38JkRChde48TSwUwOrqKna7XTztqd+Mjc3NiI9LU0AD2PBoqh5q9nOWNeCcx5vf/Bb4IEiJQSIIEIDNkPAHU5t2aETeiDcYWv+TKUZ27r77brSzDJcuXgGD4H2AtcloSbPepIQxFmVZ1JIfrfcUeNQ8R+pHjCMlSZS+vO9970N/dwuNyTm44GGGXHQFUijaImhUOW6amscPPvtbsZcJGxcuIWxso8UxThS8QoihSYLOZAfN6Slwq4UysbjUG+BzJx/Tz58/i/O9rvZIQ5UmVcnpoGLulkQ7nmlTDe+CuKeBCyGqlFAFRUlAwaolCLmCHEAhblGIV885EXICKoY3RNxkaCCIaduUJ2wCEwIazGDRmIEiQDkeuoqqROGqmknt0ZpMESqPXreLGw7ux6Mnz+Hw4X3Y7vbQ6bQBVVTeo9nM4H2A0Qw88Pjk+/4HtjY3MFF6dIoKE4MS+8XiR5/9HNw0P498cwsT7RZ8XiByWjDOP49r3ECPa1xfD/XAyopNgAVXlNMTCSd5z5PpVnj5N38jWkmCvzxzGqQMU5XoPnYJThQZLCRUSNMEU1OTkOlJzE1P4oGLp3HzjUews7sb2bPBo9OMyzkiCjUMp4JeUYKNAScJVGM2wBLFaVZVgYPHVKNJTZPyTlDHBrsgXgNRAVVWJaMcLABWBiHU5GViWEJkRyukBj0riSGFkkNgBhmTptaRNBToKNGUEqZVdZqY5nzQWWUlQBNRTVWHDXMdYqU4sVT9X7MwEcvMiPO7r7IuNcTcqA7QkiB+lOnVIXbtqkglGuVkJCYxxqqK1nLlRFtUaIUmgN2/968wZqMhBOJdozKhihBAXEguqTSM86qW1buyYOKMjXFBEya2jmBYYEAwSuQBIiElKLFABglgFJpWLiRMbG2jQb/487/QXFpatv/23/1bTrMUu7u70RBYRzGkntiPUIBMUK9YXV3FzIzD1PQ0Xv/G1+PfLizgrX/4h2jOzKDdaCAvK4ThAmcEmYwiEarDpDTgVUEhgGDRnpvD63//97G6soLffN3rcPTIUVxZugzno3LcMF+V5NQLjwrAWoM8z3Hh4kUQEZrNZrwJgMI5N7oJCCGg2Wxifn4en/3Mp/HJT3wCWas1WvJjYhDH6XYIdfNP8dA1PEioxkiKqRnVdz75Tvzj5z4X27t9uOESJBskNhk1/yoCw4yiyGNEI0nj11QTZoqiiPpuY+CDQ5ZmmJmZwdkzj+Geez6EpDWJoOGaQw2BVZEGj8QXmKcUr7jr6TjcaGD15Bn4jU00TVR4OwGCMcimptCem4XptFEaxpntHf3CIxfxxfOXcG6wo9smeN/MXK524Ag7JdGGWN5wxNsK9FRNzqKVKAVRDWB4Q6i8aEWkpRKVoFCRxL9GQOys5UJUS5A4CKWsYEjIDKg11WwaK0oUQjQRakT7RRCjAduIP8yLElRLeRbn5kHB4wlHDyOUJY4d3ANrGZYIU50ObKOJS0urUKsQ78EC2Nxj68xFtA2j7R2ynS6uyybxw89+Jm6ZnUG+tYuZVgtrZYmiLEBgsu6ruJUa17jGDfS4xvX/1xXpunluDTC/3e9NkCp3DGnYGWAKwA98y1NBAfirx07Ctiy6QeFMhuBjvnllbQ3rG+uYarfwyKnzuP2Wozh3YRmWGXsWZ/Hg6fN46jOfhouDPk4uX45yEpg4+eFo/6oI0NhJxOUwCaAgaCcpEjAZFZ8a2/fQTUdaCJShmhCRVVVDIAaUiEEkkS4X3YEUwCwAqSOoCaIEIjUGHmqYbKoifSYMFJoDKJQQhJUZ2oBqm60RIlZITBvrcOmMYlM0XEhDGjFqV7fT/NdwRXtaJLnVAShJyTNxJNsOp9DDjX+NMhGpp6SiCrAi7j+ywJWSB1aT9ZW4Xhrc+j+HSGhoK2SWojQhTZxnY6rUOxOIChJNJIrdLCmMglgUHMXrzJbhRagKFHJRdKEhBdiAWZNGU377t17X3NraTH7jN/6jmZ9foO2tLTjvEF+waw4HGgkdkRktWF9fR1mWWNy7F7/1X16H6Zkp/O7v/R4YiiTNoJWDakT+RWd3bbYTrXPidUQCHDPkArSmZvDBP3kPet0ufvv3fg/Hjx3HpUsX0csHUGZANCq2jY0Z4ppfniQJRADvHcqyBCGKbMiaUTSFmTE1OQljCG9581uQ93pozszC+1DfUtSjZ4lNMtcab0WcfA+lKvVTgOADvvdld2Pv7BTOX1lBkedIkgTWWHjnYGrOs7E8slMmNo0LlybGRaqqRPAeNkkACLwPmJiYQKPRwAc++EFsra6gMT0dqSi1ChyiyKBoaUDmHZ512+14yqED2HnsHMqNTbTiVQuqANhWCxNzMzATE0CzheWyxH2nz+DTpx/Dmd1t7Vn1/cyUOWW9ErRVMW+oNRuesaVC3QAdAORUg1ewQEXjS0gCqGdoFaCORByEvLEUECBE5IOII2ZX79dCgyYsaKcwrYlG0yREEVkYBJyYOmceueQKxqCq0A9lNF0y4crSEo7deCPWNzbh8gKLc9M4feEinnLbrfjM/Y9g/8H9OLx/EX9z5gwIDHKChAQNAdpViaTXxY2dOfzQ05+O22dnUG5soQPAGkLeHyAvCgIJe/hxAz2ucQM9rnF9PVQpwgp0eoO8IRAYETQkAN0+SBkvffIdaBqDjz52ChaCXVchWAuEyOvd2e1hfmYa+/fO49SZS5hsNzE3M4nT5y7jm+64GQ+fegzdbhe2XhgLEOwMcnjEaRr46rWxtYzCebiqQruRoWVT4lAGS5Qb2G4J9BnOGMuJqkkAtVBlZVCITTRoyKELGgKRRspz0BCBr2SV4VUZJI7ZBiERFVYlBSklpGgRaApgB1FRVQQQxavz2iBXEzFCqNFyUscR6o9G+doyjmok8QBKEHsoQBJjERGnF1nKUud/ibjmQqOOMIgaaFwiZBY2iOIUIsUMgG1AZwJhx3zl72kG0cAxaqRZwSqVsz5NDKkqwzsWTqwhNZ6CgTKTChMZEkjcGyPywmBRqgAdgNgSEYUQgjFctWdmO29/0+vbG+ub2e//t9+3c/PztLW5ibIq4zi/bnSGE1BRjCQgG5ubqJzD7Pwc/sNv/AoOHDqAf/ML/wYiimarhRAUztX5ajIIEjAUkhDV9j0lDBdBQwiYmF3EX/zP/4FXvPzleMMb34jrr78B58+fQ7/fh0k4RkmCXuVFuzAy+BEb2DovRBw5zapRkd1utzE9M4NPf+pT+Iu/+HM0p6ei1ISG9koCK0FRc76JwAC8DCMbBC8ejTRBng9w3fHjePGLX4TtvMT6+nr8PiZ+jTEz7mBrHF1RFGhkDXjvR/bGsqpABBhrAIrT8marjWazhbW1Nbz/fe8HpWl8vuIIHMyMhIBUAlLv8YTpvfiOJ92OwcoqdldWkVGM4LhA6MxNoTk3A2k00TOM+89fxMcfekQf296QHRaXt5JiAO4NmLYL4s1AZkM0bAqwDaWBQksC+fiykwpiJKY+ZahAAxEFIg0gCCyFAARLEkDWE8ETiQdIDQxZloYVtDJwNpFlZAhwtZ1RMVSmE4QJlBiUhUPuPYQAJwHXHzuK1bUt3Lx/Eb3tHnwVcMeN1+PEo+fwlNuegAur62hkDbiqiIe1EGCJ0JaApN/DbXMH8KrnPAvHswxubR1pWcAkFoaBMnhUIiBO4P3oLTqucY0b6HGN6/FeHjB5WdKQsWsFSFlR9fuY0CZe8o13otFo4oNf/DxCZlAhq9m2Ch8Eg7JCm4CF+SkYYqxt7OCGowdw6coa9u6Zx/awUxSBQNErCygzqKZbROOfjnTBIQRMdVpoN5qEXhFAKJR93yj6qmAJlKjxKdSYON7zYFioKgsQnXoGUl/KI7YqIAuQKhtLyhAVYkWIXaEFKCPVASC5IVMA8CJD5YVClSg2zHHha4ivwzWKZNLhr2a+lqdfbSIegFPVEEKI2DwdNRRXcSm18nmYy47fTiqxg6/tg9Br5SmYrZt6CcT8d5roOHmOQsNawNICECpPSAJBLSupkeA59mWBVQy8qjJZGAj5CGdjS+ScSGHijYAwcSmqeeH8oDO3b+rPPvSBzsbGWvOtb3tbeujwYbO0tKR5npP4OkssWj9rtc2RCFmWodfvxUSMCl77kz+OPfv24adf+1PodbuYnJpB8CFSJjQ+LzJ6J9WDadUYJ6oV484FTM8v4otfuh/f9aIX4Y1v+kPc9cxvxcmTJ9HtduGcg/Me3gcQM9IkrRXttbQleIhEmyBquoW1Bq1WC400xZ+8973obW+hPTcPXyPk4okuvm+45suFIDGCUgdwhABDAKuiKkr8wCu/H3sW53H58hLKokCj2RwdLlzl6ty1oCxLpGkysi0m1qJyJfwwxsGRey2qsMZidnYGv/e7v4eTD59Ac3ISlQuwhkEMkAhSVWShQiNUePYtN2PBGKxdWQEVFUxmQUmG6ekpJFNT6lsNnF7fxCcePom/PXdWN9Q718zKPpneQMxWybzmDK85ok0Cdn3gXCEVAnk2HBiAgNRy9AkxCBKDFmKIJEovjQ4J2kQkgA1E4kHsQfBwoEBKVjUjkUZKnMy0WpQaRik6Eu0QADUEthZkLbplCacS/x6CYG1jE087dgyXL17BTKuBpbWNeprPKPMC65ubyGZnYY2FgYJEYFwFdjlumdmHVz37LhzPGtCNDWRlAZIA4gRkGJWP6E4yLEggKMYN9LjGDfS4xvW4rx6zAOgXVVn5ENCsJ4LqFakR8CAK9l5wxxPRbLdwz5fuw4orITZBv9/D3vlZLLRaOHniFPbMTsLDw/mAvKjQ7fUxvbiAiWYzsm6JoMTolyWcAEmaoqwXq+LNsMbpa+XQnuhgutUEb68HJq2MaMWSlkgBkeDVJs5VaqwqeYIAHtZads5RCgpu+AUmQOpAlSp7KEGDgbVs1ViRoJQwk2qqQiU0lAaoVMQDGoZtsmGGaIAKX2UOR6gv6u3CupeWWgwcvqYJNMWzi6sXICE12UCC1NDjGG1RqbXMIcTFs9gZKwyESh80Sb+ieR4pvI1RZqPMGzHmK9OKbQATgUYxDs5Fpck5G1HAiwNS6wjGIMDGpbbgoRqUhupyIpAGkBJEQYaIQKKq5ImoEC99Y7ibV2W3NTc389lPfXr6e178XZO//9/+W+Mbv/mbzMrKCvr9fh0hMDGrG0eFoyl/kiTo9fpwlYMXxUu/+0WYm57FT7zmtVhZW8PU5DTKsorT+rpJBSKPWK/5eYbcbCVFXjq02h2sra/hFd/7cvz6f/x1fP8rXoHLVy5jaWkJzIQ0TWP0I4RamhFJG6hzyBGAEnXirVYL8/Nz+PIDD+L97/8gkvYEqspDKb5KhuMUPAhgDWorIEEk1E11Hd1gQr/fxxOecBNe8tKXoj8osLS0NDJgGuJRFtoYg6KKpjyowktcLgwhQCQ2yyICMoSiyNFqtTA9NYnlpWW864/+aBQDomuY4lYViXdIvcNNM4t4ypGD6K6uwXUHaCQpTKuFzvws0qlJrFUV/vbESfzlQyf0XL4dBlnq+kj7ufJ2xXbNJ7TioBtedceL9A1RSUxBw2jJlQVQhkY/ezyxKhsICYlTEQOICUCE3BjUVy8CUEhIvPdBPMBNGEpAKYtmGTFPtZrEoijLslaSMzTUdBFrQNZiOx+ggtS3A4zZiQ40xOVkw4zZ6UlMT3XAzFjf2sHTnnw7Tq1vYXNrC4mxIO+RqeIZN92Blz7pSTggAreyhjTPkSBAoKP38+5ggFK8kkkqIgrjT51xfb0Xj5+CceHrHgENdNI0OGCzWxT9gXMjq5mKwCIuE5l+D6bXx4ueeieec/sd4LJEooLMxivgx85fwU3XHUa72cT29gA3Hj+Ec5dWcdtNx3Hu/CX4qkKn0YRIXIXfzfvoVyVskgx7pShtMAwSRXAeCTEmGhkYQUlC8N475lCxDZXzofRBSrAU3mhOxuaZsYUXzcnYgTc2JyM5BckzsQWxKTJj84xtQcEUSZCSgpTEprTCZfBakqA0ZKqg4hTwQ9UYgUZNida83mHzIRKnxaLD6Aj9g25nTccKAE9MwpZViUbcXvEBo0DHSM8cXx8NccJpyEhFLMS5jOQp/JWLjMwbysz1wyiRiaIVjt+XiJRNEeIU2wgb66skqVwIZVAMSF2f1fYSY3vE6EHRJ9UcqoWSliCtWKlipdIQDZjRY4NtJqwy6VJRVpc6czNLDz304MbLXnZ3/8///M/d3r17pNOZUGstKlcBNepQ6zhBzOUSEpugKEqsrKxgdXUTz3nOt+LDf/pB3HLLzVjbWINJ4qSVhu+m2uuIWmUdHY8KQ1eXP4P3SLIm+oMBfvLHX4vf+q3/jPn5RRw5cgRRshgxhT5czbl4V0HEw3sXFx9FQKRoNJrotNt473veg/7OduQx11SWiBqMM/H65uLq1L9+zwuAIAprDPK8wAv+yQtw7OB+XLlyBXlewNoEBEZVlVCJ+wd5noMJMEwoizw2zCGgrMq4oKk6Qt5pzWRvNZv46F/8Be7/whfQmJiAD6HWwQsoBKSiaEjARACeccONmICit74FBEVjZko7e/eoTk/qozs78sef/ry8+/Ofc6erXrHTbHR3kmytlySXcmvOFYRzFeiyWLuu4K4hKiVaioiZDZisaLDQYH3w7H2ASJQfGqHAgBiBJjCAMcp1+xzTzqREFDxR8CBpJokYo2RUU2PYZsZwK0tifl08LEe2d3zuCTAWai22BgN4AMKExBqIF5w+cx7fcOsNuLK0jgP75vHgw2exODuD2ak27n/4JOZmYizHAiBf4sDEJH7w274NR1otFCvrSPMcDRWYICAFjLVgY9EvS1QIApjCeFONIxzjGjfQ4xrX10HttNshBzb6letWPigZA2aK2+sSwCHAOofUVbBlif0TE+iwAQUHEsHubh8Lc9PY3u1haWUdMzMT+PIjZ3D7E47hoUfP4ubrDuPAwnyt8I6yi8oHFM7DpCnY2lE/bwiABoSqQitNMNvpECEQApCBpGTjy8p4YuPIh4pM/fChcj5UHKRkKyVZKSnYkowtnQ+l86FyJj7SzFTMpiKWilhKYi2JuQBpAdIcRAUBFZiCAhIFF1dzz0PqgtScXRlmLK+eS2LX9jUUxe8fOLESQqCgcTLmgiBIzHJ6iYbCUVZYRjQsFRHJokxlZB4kUz+2jGJ9vZ6gxsl0nESvg7Z5uECobK2wtUI8EDJFIFMGdomjJKnIShGSpM+Wemyoa9l0k4R6hqlnyAwscWGICoBKJioNUcmqBSsPVGUXqhsEWnFVuNyemb28trm99rKXfE/vDa9/g19cXNBWq6XEBpX3UL76XEd6RRyRpkkKFcHy0jJWltZw803X4/3v/WM8/zu+HZury2hkaTT0ASO5DSFys5Wi/EaZatkHIMqoSg+bpEgbTfz7f/2v8dqf/AmwMbjuuuvBzPB1hnaIDjQmNkTWWjSyBrLEYnpyCgf27cOpU6fxoQ99CKbRQKitlIYo8ljq+A1zzCcPu/i4wMnKxJokRvNBjsOHD+GVr3wluoMKm+ubSGwCZoOypmwwM/KiiIcNBcqyRKPZrHnk9STfx5x0Xv+YRrOFTrsD5z3e/Ja3gGoWNdfhJgKQgJAGh8QVuGF2Ad903VF01zYhLmBiYVabC/Nwrab+9anz4U0f+6T/+MXT5XpKvU1rNzfVLHcF53tEZwqmc46x5KA7qigEEIDZMlmGxr0FwESmHzNMDG4xICTiAQRjTGA2EgANdSwnvvNJiIL4APUekhBFn30AqWgC55JOltFUuwmjAo4h/asxK2bYLEEFYKMXG2gCUDiH/QvzuP2m6/Cpzz2AG44fxImT5/H0b7oNV1ZW4J3H0YMH0O0PYtQoBCQi2NfqYJYNuJcjcx4ZFEbiwq+E+qaCCIPKwQMBzH1P3o0/dcY1bqDHNa6vgzpw4EDoATv9YtArg3OIxuQ4LZYYT7AqSMQjE8VcM0PGDI5pBaxvbQEETHY6SJME050WmmmKIq+QWYu1lQ1sbWxhotmKy11MqIJHXlWwqQUbGk3yGAqWAF8WSEhpYWaSUiSJYU2BFESFsKk8G+vJWEfOOHLGE9dNNZv626wjHj7q/+bYk2PPPjgypmJjCxLNRXVAjIECfVX0SdEHaQ6ROGYkUhpNhH2NLPM1eu2qyENrjB2RGX7af9U3AZWrJ9CISsJRgy4Sm+dQ87vqfHhQGU1cVSEQkooqYWvFmB1h3lTeNMqbm8q8qdZaSZJEjDGapqkws1prhcgo75rhmDbGP6wVkySBjQlsK2+8r9inZVO14AQDAfUEoSueuqzoE6OvigHrqImuRNWpUMWgEkQlFAMm3gmqa4O8umyT9CKxWfvnP/VTvV/69//eT0xM6PzCfGz+ROJSGxE8Ii6O64y8pdiUrq6u4fKVVRw4sBdvedMb8MM/+sNYW12FiCC1pj6IRaxhYm1cXtUa0aJxGY9jN4vSe3gI2rMzePc7/wgveN7zceLEQ7jlllvRabfABCRpMvr+0LhgWJUFCEAja6DdauG973kPli5eQNZoQ1yAGabn49VBPBBoXPtkHaa0KR7KKCbny6LE3S95KW66/iguX76MIi+QJSm89zXX2aAsy5jNtRZl5WCSDADD11IfEUGSJiiLIhIomGFtgrn5BXz0Y3+J+z73OSQ1ii9ms+OHXSKCTAI6YDzribeiqcCgl6M9PYX2ngXtZkm450sP+nd89jPu0Xw33200drfZbu6SWcqNOZcTn/OqF4VohZh3jKECQKg/SI0qWSVjBBKlnfFYIQwTEsAbIsfGOhMRiYEIgQjBRHGSIASJ8Q0rAAVrqc5Ek8KDDCMxQDLd6tBEowlfVQgujPjgIICsBacZKgU2et14qyOK+elpVHmJ1dVNLM5Ooyw9ZiYmUJQlQhBMTEwgSSxWNtYhUoFNRG7umZxGmwnGOaQq4JoTP8zMK0ds53a/DwGCEOfeGXftDeC4xjVuoMc1rsdpPeveewVAf3fQ3xmURV/itg58jVFjBjQIXFFCvcNcp4O2tYAIvChm56YBk+DEmXM4emQfTpy8gOuPHMDS8jquP3wA0502SICpdgfQiMuqnMNOvwuTGJgkrp1Zw2AG2BB8VYJFMJll1CTTYNWmJsrISSk3gUzliUwgZiHmAGIhNuErH2X9z8rX3+ZB7Ctmz8479qHyxpYkmgfVPjG6CtlVYAdCXQCFAmG4wq/DiXO4SsYYLhJeXeirrXZfYxmbCICKCIGYdGgeVFV4X0GD1ItnAVXwMXod+R8KUSGi0OBWwA5dE9O4NrLBaozR8+22nE+Sa5robWFOxHSvPrhr46OfBJMkgYwJbBNvfVr6XHOTYsA26XOGnih1VdEn0gGR5my4IKJS6iYadQ8sYC+qZQjStQbrouGKsr2Ytdsrr/v1X+393M/9nJegunfffjAbVM4BHHnIxFGKwmxqjnL8q3ljYxOXr6yi2Wrhd3/nt/Gv/sXPYNDrwbsK1jASY0BaZ9VRy1XAMf4yEpjEcwNzRBI2p6fxwP1fwve//BX40w//Pzh2/DimpqZRlVX9ekQSijKBTcxJL8zN4cK583j3H78HSbMzYoTr6HahlhUyjYQv9X9WBkRVhYk1eI/FxUW89O67Mcgdtra2kKYpfAiovIdNE5RVBecDkjRFPsiRJBZJkqAsS0iIPWaSWDjn4byDTSxAhJnpaUgIeOtb3gJflmBrgDqHrSIwokhFYKsC183O46Z9i9jd2kVrsqPNPfNy2Tt5xyf+xn/gwS9Wy8YNus3G7o6azV3ilTJJrhRMS0K0SsxbpOgzUQWBiBewgEmVAYaqan30DtaQTwxVCWkF4oqIKmupEpAjEgeQBzRAxBtBsEQhpsiDJBSEgg8OEDgHNmosUcoQO9VuUTNJEHw85BoTl5WFOS4RZglKKLpVHl8EjRGPfFDAMmOq1cbpxy5j78IMHjxxHgf3LeL85SWsbu5gbnYGVY1HTADMNlvICCDvYKBA0BHPG4bBWYJBCNga9CGACEnJ5PzfgxQd17jGDfS4xvV4ql+OH+bVwLmtXum2YDiQjc2KkkK8xIU1UahzmGw1R3lmIsLq1g5gGbfdfCMeOnkBN11/GCcfu4hWM8PFpWWcvXAZt990HSg6TUDMqMRhu9uDTRLYLIkJX4oCCwNAKg/1HrPtDrWTtAXnJxpqbKsFELGwMYG4ECITiFiIWFA/iE1gUwa21rOtPFvr2VSeqAxsnCc23hjrKjaOvJTGap4p9QjYZdAWgTYVvAXVPhP5aFu+Gt0YLnQNjYFDayDVBJN/QKm1lQCooOJZa9yWBGjwIBUE8aP8M+qmPdSxAjAFQEJZVWJMItc2zcysSZJImqZyvt0WNJuKNNXk7zTRxqRCVOeiOYlNtYnNtBmknm3pyyRzbNPKDaQwglwqGrBBnxQ9BvVVZRA05KJakFLFzB6gwMzCBGFiz4ZKAbpGdSOILCnz5c7c4vpbXv9/D17zYz/me7u7undxjybWwA2RbPX/DknKqCexgGJ5aQmXLl1GURT4jV/7JbzuN38DriwQgoc1piZexIsU1Pi4QPFUFCSMXrNQEzqq0qE1PYOtnR285lU/ht/93d/F/gMHMTU9HRc6Adg0QZJkIJOg3W5jYmoS733ve3Dx7Bk0m00EURCbiGgcDcLrRn4kxgENMXbDhcDe7i5e8pKX4LbbbsHGxiaKvIASoaxtea6o4J1Dmljkgz5AgDEG+WAQJ8/ew1A0Ffb7PWRpCoUga2aYnZvDX3384/jkxz+OpNOJuX2KynMDwIaAVD2aYDz1CU9AyyTwxDpzYJ8uhSBv/cSn/V9efLTatTTY5XR328tGbsyKs2a5hKwEoo3A6AppKSqhEoGvjw1KSgAjxFNmYOYAIudFSx+09F5LUS0hWoloRcyViDoSdSLihCQEIyGAQggUSELwRIGIAyLHLqaSVDPSkCxOTVJmDMT7mO3m+GmukWWIrNlEr6rQK6sot4EiNRZPfdITEVzA5eVV3HzjITzy2CU8+bYbcPrsFRw+uA979i7izOUlGGJoEDTIYs/0JNh7qCsjZ7o+SIsonAhgDEoRbA8KSPwb0BVXBZTXNs80bqLHhTGFY1zjwuPNpqIAQiV+o19Vq4HMPmMtAsfGguuFLtRLa81mgqlmB7od2bRbu9vY3O1CmTA92UblPfbtW4gIMR+wZ3EeD554FA1ja1sgwUOwW+RxkmctnAwFEjEz6vISUnnMTk7wTKfVObu1MU3tkKkqEZHSwAgEkAZbVSXiQoAWiPKY6e0boWtyyKrC2hJWVSJ1VNYnZJUGu8AhFR8QWEqukChl1soCgC6zcfHSXa/hFOuImRskGvSGYNc62apkvrbrWVsmAqAEkyNA1fso0wg+NmJU0zdG9m5cm4GWyMtl2aQt3Yf06mTbGDXGaJIkihNNBToKdPT0nT3Czg4fAWLmOmyRiBCwp/6RKxCZIwAIoWLOjYZ2YSI4OoXxFWAZIWZ8SYKyWCVI9L0ROP6eVcHCsDFUAbCBh4f3GICYRMi4StKp2b32I3/6YX7Z8nLzLW97mz1+9LheuHiBSu+gQZBaOzq8EHOdRQdsYrG+toaqLBH27cNP/eSrsX//XvzEj/8UdnZ3MTM7jUFZRWscx5gDDxXaRJCRoU7hJf7cZeWRNTJwluE//eqv4eSjj+I//ebrMDU5iStXltBI0hi5sBYzs3NYXlnB29/5R7DNJsqaZ01EIyEKRhGCeAhgpeEQmogJmUlQFgUt7N2Dl77kJZAguLJ0JWrjVWBsFKdICOh0OsgHOWAYrWYTvh5mVs6h2Yhoyf6gjyzL4htcCLMz0zCG8b4/eR+Kfg/N6dmYpVeFQGEBJKQwzuH47AJuPXxEKw9M7VvEg+ub8q57P+kf2V0pq6xZdAO6JSfbjmhTDW04YMsBuwoZsJCDYWEVRlDDDBYW4igLVSYN1pD3AieizhA5kDqyVIHISxBv1cQXFkxKngKIDYKQWA8KwSbsERKfQEMAQhp1Q8SqFsFnKThdmJyCJaBfFLB1/rlusWOGPU2xvbWJvCpgTORoz05M4LN/8wVcPz8LaSToDXIcP7wPKxubmJ+bxpXVDcwdyrC5sx3/PAaPjA32TE1CnYOvHFIAxgASAOH4XiKbYDcv0K8KENugRK7+e2n4Nrx2WDeOdIxrPIEe17geb/VLv4SwC9nYHOTLgSDKFsHLcNMpEg1EIc6hQQazExM1+gpw3uPooQO4srqB2dkprG1uo9vvY2e3iysr63DeYf/8DI7s3w8bEcFQGGz1+igVSJuNeuGLYBRIDQMa4MsSbWNootHsGA0zhqmpmhkiViIjzDYuupkyELOwKQMNTOCBCcYkgbkfmPvB2twbk3pTpM4UieP6Ycq0MlUobaa5T3UQEuo2EtoWQ5swvA7VbVUpIwGarplAC4IqfD2VDhJqNTOuttHytT3/jUYrACg1iIvYtLpRp7jsRVcReaMMtJeAEEQZJEIkIJYFZl2qm+Zrf/7TaarAfQrcK8C9gvvuE5yekvPttjQaDambbGFe0/hgtXZLmDfUmDROpPtpMHnqOXGusr5yQQpWzY1Fnw164tEj5oEQ5Z5QgqgwRBUYHgyRmvALYTBDmakiRjeIrOdltZbNzG7d/8UvFK98+Sv8F774JRw5cgSTrTYSayMRo25CR3GZWvporcVudxfnzp3D+sYuXvZd34kPfvC9uOmmG7Cxvo4sTSPqLQY46sW+mF3X+saA6+k0c3wfBhFUEtCYmsI9f/In+PHXvBrdXhfHjh+LBxeJXOrp2Vm864/fjTOnH0Oz3bqKyxtyuqm2JI7kLjVlhIbYFiUionwwwF3PfCbueNIdWFvbwKA/qLtvgvc+Zp6zDHlRwAePZqMRsX7ew4eANEngg6A/6IM5Eie882i3WpifncNDDz6IP/3wh5FNTI6aZ6iCRWAkRHGKBNxy+BiyrAFqZvrw+np440c/6k5016ui0Sl2yXbzLNuuErteGVr1pGsK3TKqfRaqLCEgCAuUEdNYxGAVIAjEgahSodKQFg3m3BByIs4hWpAgJ+aCrJZEWhJJScRVRlQRJQ4kLiF2ROwDi/fMnogElVMboziWxDWaZJP5iQ5ZVbjcAToin0RcXWJAicVWr4fCORDHXY+Z9gQOLSwgOI+yqKBBUZQlVtY3cdP1h7G10wOMgdcwGju0kwzTrSakqqA+gEgRfIBGwRCMTWCsxaAqMahKUajzTqoa2DmeOo9r3ECPa1xfD/XLv6yaAxu9olhRokBMkBr5RfXATLyPDbQxmOm06utvwPkK9z9yEkcPH8DK+hY6rSYW5maw2+vjG267Hg+eOAMLwBc5UjYxi8rAeq+LSgW2kQKGa2BcnBSqF/iiRKeR0cLERIuBaQq+k0iwRKzGdIXIiMkTTwMTqM9CfRZmI8xWjOkFa21I09Qzs1jb99YOfJIU7tpHllVlWlVl4tq59Rh4bXQFtA3mLQA7TFx9BX0jJghG0Q1VGU2Ch3tDICjz1zZNyrNSAORkjAPRVcJHECgIzgtCCPDO1wi7AGMYJopWxIgENmVYs1ZgjF4CsGSMXjJGzyeJotm8dkheP+4TnFiQ02mql+om+u8+ho20tdtibSMYkwYzSD0niWObVsZLGUTzIG7AxvbFh75hMzCkAyIUQloRqfdA8EDc4INyvT2nEoJXSF+ATVdVG9nE5PZD99+fv/xlL/Of/ZvP6qHDh7TTaSNJklH84SsOMjWVxFqLIs9x6tRJXFzewF3f8s34wPvejW/91m/F9vo60iwBanU4MyExNXucuBbf0HA/MCq8lTC8eWjOzeEvP/IR/OArfwDnz5/H8ePXQURw6MBBXLh4CW944x+CrIULsWHmGp8HAB5R62L4GnX3MApNSkEUPgRMTk3Sa179Y5SmFiurKxgMBnHFjgjBBzQaDUAEeVGgPTGB4D28c9G8WP9aeT6Ii6W1OERF0coaaLcbeM973oPdzQ2QMXWkJDbZRoFECMYLprI2br3xRp2cmdUzW9vyhv/5EX+22HWDNMt3iXp9Y3Yc0WaAbghjIyh2KMacSksc36hgAlsGmCTyRwKDAhtygFYgLUW18KSFsObEmhObnFhKEi1JpSSJzTMxOWvZEYkjYheYHAXyROQpMi09ZSSAEqlaSMimG+10rt0m8oEo+K/QGakqKLEQA6zu7qBEAIhhjcX++Xm0mxnOX1jCVLsJUkKZOzzh2GF84jP346lPuR3bvQF6eYE0awDBY25iCrPtTh3Lrl8Hiu8aL7VAhwm9skIZQlAyFRvKidjX/cXfbaDHE+hxjRvocY3r8VglsLPZ7a7l3gdOU0hNCJDa8AYAoarAEjDdaddqboJTAeqMZ2INvPO4eHkZ1x85gC8+eBLf9ownY3l5DYfmFrB3ZgbBOZAx2Or3sJ3noMTGH2+HnyAKrTyqwYBa1tLi9FQjA02QCxNBQgKQGmNkx/ZiQ2eSeuJsY1Nt0pAkSUjTNFhrpdls+jRNQ6vVcq1WyzUaDddoNFyr1XKdTsdttlqu1aqqLHOFdZqzUhfE24DugKkakg3C1cjEiAcdarX2aGGMY9jyaxxAoz01FQAUzMYxs8bdLoUbsqCHvwfvhmIPZaJa8CICskLMAmMUSaIwRo8Yo0cAIE0V93X+rj64/vd7Y7QjTfV8kqipm+5LdQOdpqmkaSorSSLWbokxO2JMImaQBLaVr0xSOSslG5uTcQNiHZDqwLLmor6oG6ZKVT0zBEzKtdNQIMzR0Oe9hJ4qNp3zm62Zmd31rY3i7u95qb/nnnv02JEDOtGZQJqlo+Y5hIDgryL9ACBrZAARLpw/i3OXV/CE64/hng+8F9/3yldg6/ISbGJh0hRBEOMaQ3tkzT1njR20SpSxECInIniP1uwsHj11Ci/57u/G//ifH8GtT7wNaaOJ9777vbhw6iQanU6t9Y4TT6obKVNzmmloIBy+R2pXTGYNdbc26R9/+3PxlG98ClZW1rC0dAUmiYLNPM+RNRqQoOj3+pidmYGowIugrCoABGsM+oM+kiSppS1RSAMiTM9M48yZ8/jgBz+onKYagmio359DfbhlgnqPJ918qx44sF+/dO6cvPWjH3PL4suy0Rn0OOkOyGx7ok0FbQboNhN3STUXISdA/bcEUJ88wJGc4S0ZzyqVeK1SppKCFkRcBtFSREtSLUikJNGCSEoRLYRNSaylkJYiUoGpSjhxROyITUVsKsemgvOeiIJFgow5JQnN2U4rmW624MsKIXgYy/WSrgEsw6QpBt5jeWtrdBhupxkeevhR9HZ28U233YRLl9bQSAzajRTb2z3Mz0xhbXMHLgS44FGfkbEwNYVWksDlRdzduCayoxKXCMkm2O7nKCFOmftKPGC2/n+Tfx7XuDDOQI9rXI/TqoDu2k53s+dCmLIWSoygHrb+tCcofOWAEDA/OYkMBmUdZ1ACtnZ7yIJi/+I8Li+toiwqWGNx8eIyWBTtNEHDJNAg0CzBTtHHdj7AwU4HsHHphwnQEIUXZX8AcSXNTXTStkkmut5NN1tp2hWAmRXMyn4HwNQ1spAdsdZKo9EI55NEcRoA0msax6YC99X//07EWAOwBBCuvz5gawvNAQaGeReq3cQm5bUM6OE0XhGXK+NikgIaRs1/Dbv+mqZJ7XxSAJRpYt1wJTHUimeulzlVY642Pk981UQIFiEK1GfBnobg9JTg+h0+7xxhNH2+9ytj2l9R9wlO3EW4ZY3PX/Ot5wHAOToC4Igxw8trYe4q0bQiB7RRElxCxlYRdaAwAhgEMGnETqgI2dg0U1ABgwiixBxxGExQIXbWoE/EtnAVp40m5WWhP/KDP9y8ePGi+Wf/7Kdobc1ic2MTvqpig2qiRps4TpZFBFmWQULA+fNn4VyFI0cO4Q9f/3tYnJvH7/ze76PRyGCtjdlhqVXfAkQ5nsKCIi+6xmQEjYhC5zya7TZ6gwFe++M/ge3tbbzyld+PD37g/eAkBamClGAMxyXCYWOuUZAyUoHXTbWIQiCoXEB7ooOXvexuZFmCy5cvQlWQ2ASuqpCkKcQLBoMBJicnIaKoqgrexwbZMKEoBpEQIxKbYmb0B33s2bMX83MzeMtb3obzpx9DY3oKzvlRTIVBsASgKtBpT+ApT7lTT66uyts/8ufVSt4tQ7M96KnuVsy7gbEDpS0QtolNl1RKJfIwo4W4uKtnSQEKkHj+JlJPxMGAnAhVZLS0rBWBSyKtiMmRShUXAjnURxgSUSYYI+oMKxDIBaLUM0slRipCcCTGkROGczBGU4Zms+2ObTdSuF4X6jxAcVchXgsZcJJgEBSb/T6EGN57TExM4Onf8ETsXlrGyuomDu2bR6+XgxNFrzfA9TcewanVTeRpfVCuc/R7pqdgRBGcAxDigjTiQJqYYdMUpQIrOztw0CIwb3s2/T4PAnA9AafHjfO4xhPocY3rcV9E8EC/W5Y7varylCSAtZD6GluDglShzoNVsDA1ialWO3JmQVjb3MTexQU0mxkePXke1x/eh7W1HXzDE66P4gEQqjxHM8lAKhDvMdCA9W4ftpGBUxupC6SwzEgMoxwMQN5j/9yMmW212urCDJgbgBIzK5JENtI0WNsNsXHuBmutrDQa4fz5tuD0aQFOe+BEAE74+LgvIG7CeeA+X/sZ4redPu3R6bgkcYWABoD0VMXVDAiVeqlLNTb5w6Z6uOCFq4AMDeFrA0FPT5cCwEHhqSZEGGsBCJx3sZlzLjZqIKjEJiyayWOXxmwFp9O4KJhec2i479qJM/C/TqHrSXSzqZiaEqTp1R+fJHq+flxqNGTpK8kdweSJZ5u6yielEynIJDmp9kVNXxLTF9KBsg5EImnBEDkAAga4JskZIk0sAqBORAoC9ULld9mmPRAXv/Cvfj78ws//ojSbTZ1fmEez0Rjxjk0MsdaEi6uHnMQmuHjhAk6fPgMo4b/8p1/Br/+HX4E6j6oskFgDpjhtDoh6eea4FCl61dDOqAkexKhcACcZvCr+/b/7JfzQD/4wTp85B9NoIgjAbODlqlQnqEIotlVUM6SZOM5qCUiSBIN8gGc9+1n4R895NpaWlrG2ugbDFlVZRX4zM/q9HtrtNow1KFw1or40Gg2UZRmNimmKqnJgipKVLMuwZ88eXLi4jHe+/R1RVqSQyE1mgUA0qDKRlpXTW265WXyjEd70Zx+ulqp84Jrt7V2l1dKaFc+0LESrgbAZCD2IVnHqjLgMx0zMDDasIA5C8ELqCFwRcWWISiItSLUQ1TI4KUlcSSIFiRbMpgzGlsFI6UVKNqZkYwtmLYhNQWzq76OFD1JysCU5UxFXntn4JEkA55IMlB2cnbdtY+DzItJa6jiLl2ixMc0MG4M+NntdgOIy6tzkJPJejt5uHxPtDCoCLx6WGYf3LeDEo2dx5OBeXFlZAdUnLgtg7+w0GoYgVRUJRUPBEgFqGCZLkXuvS1tbcEA/KK2L6GCKOfx9VthxjWvcQI9rXI/D6gD55mB3d2cwKJVZbWIjfUIB7wNIAHEeUpSYzBqYaXdGi1F5WQLMKKuAW286iocfOYv5mQ6++MCjGPQGuPn4IVy+sIzbrj8Ws6DM8AAubW1DbAKbZnEmVi9ZpYbgByWkrDDXbPFcq900EuaaAc0JFVoyRtFoCNJUrLUyjGskSSI43xbgxFBeJv+bh/49D8H58343SZwRlIDkROS1DmVofb0fvP8KhJ3zYcQVjsFVKP3DPhAdCIGpRgZ6H5s652IWmgAnIcovRrIGrpUjpnbdnbgay0gS/Wp17rHR7ijuA3Ci/vdhI33t4xr8nTGpGJMGtqVnmzj2tjKiBdtkQKr9RNEjmB6IB8o6AGkhqhUROSYEGREqQFBlhcZ4PKlj0lx9GAhx3p6aqn77db8pP/jKH0AIXvfu24tmszXCxBlmiCjYcM1gjuzfVquFpStX8MijJ7HdL/Ev/vlP4s1vezPajQa6uzuwjQRKgDVxUiw6XPK7eqs+un2Ib3QEH8BJiqCC//7hD6P0HpZtNM/Vi3k0XBysoxtEHJdMRUfLoUPudGJT/MArfwBZmuLC+QuoKgepfw4mwvbWFqamJpAmBmVZoKocvPNIshRFniMEAZsE3nmkaQLnHPr9LiYnJjA1OYl7/+qvcOLLD2qzM6EueInmalKoqoiqEJTTTFya+vd99C+qs9sbfd9obvaYl13DXnGMy56xBNCaQndENSdS70W0bpypPggpmOvpszqKhI1KVKrh4UlIS8R8c0nEJTNXgaXyxlSZkZJDNISGIKUPoQpGymCkqP9ZcpDKWCltIiXbtGJrHXPl4aEqIZ3mRrp3espQ8PBVAVO/kgrAe0EggmlkWO92sTHogayFIcL6+g4sgKP79mJtdRMraxs4vH8B/X6Bnd0+JjptNJptBPG1ll3Q4QyzrTbgHVyRw4zeK5FcJFBwmmIQfM2Apl0lsxxIcmOM/J34xrh5HhfGEY5xjevxi7Kju+5CtXpvNVjf2c3D4nxQJqNQxIGZxuUo51ENckzMTGO23QLWAGMsSuewvLGB/sYO9k9PYHpqAokx2L84h1Yjw/0PnML+Q3swcHUjLgoP4PL6BkoFbJbBjYQXAhKFhArVYIDOzCztnZpupSuXFyryHS8wuGTraEaqS0eu+UKSROvmefj4Wio20c2mN5RUAEoiClRP6EXl6uS5TjnLiOtbX9ET6T/kA7HVaikAR0QhhEgMqHxAkkR8W3AOJkli9lckxjuA2tBHMAa6bpJrDggdRZrXv4+OfpVNNI1iLk1cTboM65ackKZaxzxkH7YgMkncD0FbFakkXPmKUmsAjhPYhAlEBqWQqEBJhGCURdSAyBKQKJSCqiEiCwXbePIJGvPnZel90plbMP/9w39KL7x4mV//xjfozbfcShcvXUQ+6EO8r2MXWh9kCCEIQIRmq42trW0M8hM4duw4vvNFL8Ts3Cx+6rU/iVMnTmBiYRESFKrhmmlxfM/HlVCBAcecgsZMtIQAMYRkahJGY04dtScFteQlRmBNHSuiKNeJ5haQxj8z3Z1tPOuZz8RznvNsrKyuY3t7B2x49ON2e11MTk6CTGRiRy64wiYGrqzgnEOapXXjHk2V3V4XnVYLs7MzyPMB3vKWt4CthVdVJpLIERdiw2wUGlTBjVQ+86X7Kw1hYDqzW12SFQesiGJD1O4ShYKgPr63o0+ROZIkJEicPIPhvQpDAxF5Y8hB1JGQC6SOiDyEK7KoiLliQUVsHHk4NlJ5Dd55kiyr4T6aMoKyqtTCRqds1BmfVCUSZ9LKUy/RUkib8GCRdLLRSQ/MTrNWFcreAEzxzycTga1B2mjAE2N5dxcFwugj/o6bboQBYbfbjW/zG4/g0ccuY2Z6AmnWALUyPHL2AorKwZJB8B6zU4uYbbcRygrwAUbr9wzHAQCZSPvYyQvsloUIaEdBS8aHfNMkgpgtu/bP3riJHtd4Aj2ucT1OS+/9BPkBMNge9HcDkUsaGSldZRwbYxCCoByUmEhTHJqbj+xTaDSkBcHTvvl2PHTyPNrNJoqiwsrqFqxlpNYgVAHqA+ampiM9AMB6bwe590jbTQgTlBQU4iIWi6LqDdA2hg7PLzSb4AWqQic0Q71cf0KAE4rzbUGSxInr6fTqNPkf+Dzg0iVhdgGAFxFVUQLFpsx7H3nMIjW+ztf/lKvaZrCy+dp+0cnJSQWitY8oqlQwzM+yidbDmgQiIdQK7zjNVAIFADA7cvVrv1dwolmzn+/9P31AX41xoKO48+/5XieaOppMI1I+RnSOQRJM4hzbtKp8KI1Nclb0g6KvQM+q9g2jr8x9CRgQUcUEr6qBaYhlJiaCDUpWAZYI/Q4q4qui8p2ZmfDlLz+gd3/PS/HJT9yLY8eOYGp6DiZJIzFDFYY5vhYgiAA+CNhadHs9PPLoI7h8ZQnf+q1Px7vf91488x99G7qbG1BIPQfUmo181SA4OmDW/00Rp8PeC3wV4PyQwMIx7iQa87Y60qVEpFk9jRa52i9ZY/CqH30VJjpNnDt7DpWrkGUZFIqiKNBsNJGkCSpXwYeAsqxgbcQalmWJJE3iTUgIsEkahSoSMD0zg5mZGXzkIx/B33z2s2g0Gxq8ExGJ6mtSUWgIhOChvoRWheG8aiQ7fUOrBdMVYXNFQMtKYZNEdo1qn1VzUa2YKFiC2mFsA0YMKCQGwRhyhqgS1dKplI61JOLSkpaJlYqEHbE4z8YRsyNm12D2VFFoEHvjrTPeOmNDxcY7NjbqvY2pTJJUpXXOFM6ZQSTqMFvfaBi2Epr7p6aTvdNTHMoSripqVCFqHjODsxSFKC6srsWrKcMwZGABnDl7EYf3L4LBuLK8gWYzxdRkG1dW17G+3cXePfPY7fdHhJXFyQnMttuAq0De10IcqRWTBJulMFmK5c0t7ZZVANstp7zs2raIk/rr/3dRqnGNa9xAj2tcj9cqgMHabncj91KaJImLhIi625iDFmjwMKrYOz2FVo0G8+oxKHOcunAZNxw/COc81rd38Q133IgHTpzD4YN70Wok6Hdz7FtYgJMQSRyDHCs7XdhGBqkbDCIgsQwLRdHrg4OnvdMTWcukc+rddKvixsGrv+UY1zg9zO2ekP8PP4wUgHC8ZpWRaabO3MYN+5hLjgQOukaUEaeNUFER+of8HgLT/5u9P4+y7LrOO8Fv73PuvW+KOSIjIjNyQg4AEiAIEpSomZJHtUouWbIoUZYtqWqVVHbb5R6qa61u2WUWZWvZNdhdLrfLrpLVtgZaFClbsuwlq6u8qpvWyAEcQCABJDKRU2TGHC/eeIdzzt79x7kvMgGSEgfQolBvL15mIDIjXsR99737nX2+/ftYmAlBau6xSByCUkVVlccfC/TYT0sAQQLijfnh36NTH1/w+Ygi+tlOTe14/VGL6Kt1p79mRx8c+6FTPxHRJkhhrOYmwUiUhmIwIDZDaGRFQzUHtLTWOGYKBIiKElQNABYiVhUSCSCOxOKyqLQzN6+bW1t4z3veg5//+fdjY2MVS0vLsDapBapgwuyezHGKBCRJgjzPcePGDdy8eRuPnH8E7//AB/DnfuSHMO4dARpAHPnPHLcS4GsTdGydAwSBoQlLejLEyXGgkwimZkwbovp7RX63odgVp9qTm2UpukdHeOc734lv+yPfivtb+9jd3QXXATH5OEfWyNBsNY8juouiiLHe3qMqa6FdM8iTNEVRjDEeDdBqNjE7O4uqqvDP3v9+rYpCiY2qagBRvfYjCUFFRIPAuEBcesPjXKkbGPvEZk+IDn2QPpGOlDgX4tIQVQmMh5CHJF68BMAEAwSQeghVpFwKaWGIC0tcGOKCWEoRLoNISSxVKCLP2fvgmY2vyARuGc9sQsHWF2x9WZnAznhi54mdZ2ddWVnP1nprGz5NU3+YJIF5JOrAFmidXlpKZ5KEXD4CfDgmobgQ4FSRthrwhrDdPYqDDz4gSxIwFG9//CJefPk2FhY7gCrarQwv3biLJ69cQBUCBkWOwlUwxoIArM7OoZNYlMMx1PkH9I0Jv90YCBscDEc61KpQaw+FeZdLW8XX6fVpfPe0pgJ6WtN6M1UCjLePetu9PM8pTYDEqBDFnWkRGCIEV4G8w6mlRXTSDPABDIODfh955eFEIFCcPnkCL9+4h3Nn19AbjvDStdt49NwprMzPRZ8BGwxdgTsH+6BGBqS2Dm0hqAcsMcphTuQ9VuZm0xMzM/PsqhWTJTPlSmle2725Krh6Vd6gbo7WVgxSJnpAp5p4WAUPkzlQM4TfgI6SkCGNQ2IC78q4DR2iF7ooK8gkxlq0DsQQKKL+RJK8bvHw4d+HvvH5avJ1H37d10yEdDN2+ttt2TRG1x/yQ09EdGXTyoWkMJqOvWLESIYCDBLGkBhDIh4qeASlAqAKTJ4AsSAlBBgoaqRxbP4SCIYwzgttddrqVfEXf/TH8BPv+xtYW13G6okVpEl6LKCPWci1n1hVkWUZgvd45foruHHjBtIkwd//f/0DvPdv/g1URYFQOTSyLH69MZGpXHuZJ25V0Qffk4lBStHaIbWorskbUIWtP6a6wU11EqGKwBiDH/iB9+DE/Azu3b0DCb6O5c7RarfQyDJ4F2kr43wMNnGxVFUVjDEw1iD4AMMGVVViPBqDjcHs7CxmZ2fx7Mc/hg/H2G4tvQvE5BnsAfIAgmHjidgptFJQLoIBE4684jAI9UV1nBiqoBxTAgEvMB5kPJFxRFSRcEWqpVMUopQrY+xYx8QYM2v+4E9TEEvBbEoOpkwzU2XsfYPZExvPxvmyMqE01vNxMJIJBZlQOesrZ31prGdbeTNOfZqO/F6WBSSJMLOQVrYBzF5YX0sbBHLjAgYCw/XzRYrADGpk2O4PsDPqQ42BcxUeOX0aWgbcvHUXWWLRajSwvX+ETruFS+c3cOP2FpZXFnBvdxeCaJVpgrC+MA8rClfkUAmYOLe8BIgSyCbIRXH/qKsltB+Udl0Ih9aWFbZSwbTjPK2pgJ7WtN5EpQoGxlu9o/u9qhybLAOMqe0WcUaNSeHGOdxohJMLs1hud6JPlA16wxxnz5xCo5FhlJdoZilGeY4givm5NlZPLGJndw/j4RgtY6BMKCC4d3AATlOkzSaUGZyYmsYB+HEOP86x2pk1p5cWOyy6lgRd9t6bz02TwBtyc9K4B28jLZegoiQiCME/CFWpu9LeuSiqjkO29Yv+GRYXF7VuZItqwPF0UZ1mJxqH5MqiiJ+rBxotce2+VsKm0d93UPD3tXF8If+2FtG153wrTSXL+iEyotNg8syZ1FcmCaULWnCiY6MYGeIBW9tnoE+G+obNQJmHhkzOSoUlKj1QMbMnhkzWJExg1UAKEBnmqnKkymjNzuG//lt/G3/hL/4lZFmGUxun0Gq1XrdbEKklk+60MRZpkuLOnTt45ZVXMMxz/F//i/8b/tFP/c9ot5oYD4fIstiVJCJA4hCgYROhgRN2dM0Cjuy2yHATejibOVqfJr7nyRLMWEZZ5HjqySfxnd/xH2D7oIud3R2wMQjeodNpI01SOBcH1oqygI0EDeR5DmMMiAhFXiBJE4gKRsMRFECn3Uan00FiDN7/c+/HeNCHsUaU1BPiUB8xHECVqDqBVkRUABiJal+VegQMlDQHaeVEfJ0iGEQoiKgnochsFi1AOoby2DKGwjQUNkPLNCRjRgI7YmPGZDRn1TyIFkGk9BwqDsH5YCvH3hNXgSsTiE2gOlGUmIVMGcjUn6//jsc2WDsMSZIINhuCTaMLAExRNBaS9sLG4kLGwSMfDWOedh2Kw2yQZBnSdgt3Dw/RK8fgtAE2Bvu7+5jvtLA4N4vF+TZu3LyPr3nbo9jeOUS3N4CqYmPjJLqjQb3EDWgnDZxeWoYJAVI6mNqmExdsgE0tkmYTg8phdzAIAtoTY7aDQS/LsgpI9It/zU1rWlMBPa1pfVVXs9ksDl2+tT8YjsVEbmokQHFMJQwCdQ6+KNBkxonZOTAAaw2KssDd7V3cvLuNyxdP49PPv4pHzqyh1Urx/LWbmOk0MNtuoJVkyGyC4AMCgDsHBxhKQKPTiiZgEZACiTUg9SgHA2pb5tWZuWYCnIFzJzOXpQ9NsMsbJZwfREQLAUg0BAMVAmJMbwghEjHqMA8JAh8CnPe1hVYA0SAPzK5f1MPGSGmmUCeZiQi4HmC0xsA5h7Ioa/6bRYhpiBz8Z20Hfyk3589BJvmwvLYj/eEHg4l1AAuSRDeN0SzLQpIMgrWNwKMksLWerXMcssIEHbNiZMADBvUE6ClC36sfBPEDIhoLoVBCERSlqHqBhjppEdYwITZz4eu35ioo2vML+Nl//I/xoz/6o8jHY5za2ECapghBUB0PF8aBwklKHxEjTVPc39rCyy++iO5hF3/+z/8APvhLv4hHzp9Dr3uERpbCEh0vUkSjkifV492GCEGJR0wXlAcf16mDx0g8REuJqmKc53j3u9+N1ROLePXmbeR5Hm1LiUWaxM6oiKAoi2NbQOWq4866cy76sJ3HoD8AiJClCdIsw0Id+PLr/8v/R22rIz4EJ0qFkhaqWgBSEEkF1pKICiYagzBUQp+JBlAeQ8mJUDBkJJ5yE0C1t5m0EELuFCNiM1SmPgEDAvUtwoCBgfgwEKVhUIylSsZBNGc2JbGpmE3tfzaemL1x1hevF8/1UXei5fjvyIi1VjaNUWBOzuI20mbTulB2Ti8tLq/MdFIpKoS8nCws49yGImL8khT3D49QQBHEg5XwyMYGZlsN9PtDdI+GuHB+Hc+/eBNZYjHXaWNpaQ6ffPEahnke32xCwHKrjfX5WWhVQioHiBxHeQsBwgacZdorcuz1hgEwm1Xw96xtjPf2sjC9y0xrKqCnNa03YxPamGoI2ds67I19PQyjk06exM4aicLlJVomwbnVExHhpIqxz2FTi/OPnMbNO9t421MXsXtwhINuD+c2TqDVyPDSSzfxjU8/iU6jFQfuiLHT62F/NEY600GovaPx8QTsBaPeACkUZ1eW0hlOT1PlNiih5kVc5C9TMP4eAjplAKkAVgESmQzs1Yw6fcB9rdOga59snF+rtd4XW6JUkwNrz/PkcRNj45Y9KA4UTn5VJaIIcOPfQxB/KT7wh79WP9sa8tki2tSe6MlgIY+SYIrUmcQ5l2SlDZqLYiyCITvqi6ceAX1RDKAyJMKQicZElItSScTOuRAkqIY4nEVMhpiJJuuFygW0llfwL3/pl/D93/8e7O3t4vwjF9Buz9RDhKH2H6MWVAzU3eV2q4XRYICXrl7F5uY2vvVbvhG/9m/+Ff7oH/02dLe3YBMDkzB8iFSYCTDwOG2w3rUhECzjOHp70qiuPzymchAz8vEYG6fP4E//6e9Cf5xjZ3cHqhPxnKKsIvPbeVcvnhjOubi4bTRrJni87o6OjkBEaDUbYCIsLS5iYWEBv/iBX9TD3V2xiXVQFMwYQ2kMUA5FAVBOoJyAXESHBPSZqKeqQyUtAXUJKAASQBBD5EHiHGkhbHJRDC3TgA0NSKkvSj0G9RXUVx8GLBixujGL5mykYGPLh456OND5ylnPD4lnHhnhkRW2Vnhk6k50EdiYOKRqBsLMcWgYzyJgg7Q0mQHmLqycWJjPsrTo9yGVo8SYmvYDeAGSdhvDEHBrbxcOgCpDJaCTNfDpT7+Ey+dOIrEGO7sH6DQzzM91cNgboDfMMb8wh/2jLgxzDFCZncNcs4FyPIavKjCjTmxFpL9YA7IWu90+9sd9HwzfEZPcazZ9AWwG4LpM7zTTmgroaU3rTaSdAUDStMqBw82Dg2LoKiRZpgIgeIEGASuBBXB5iUQUF9fW0YQBqcBwinv7h8i9Q+EdtvcPMTvTijcVBcajMc6dOoFr125gvtkCA2BjcJgPca97hHSmHRm7cec8dh6JUA5HkCLHmZVFs9xprcHlp1qwMwMM7FcqjECSYADOYhJzHNyLI/gPxLOESOLgSZzdgwrGfHE/y8mTJxVAoIlnQxVBFC7IcWIFQeG8AxsTt4sf+H0N9A17v/pcC5HP1Zn+LBF9u+5E79SDhdY2grUNb/LUc+2LtqK5SZIxGwzZoE8wPWLTU+aeAn1VHjKZUWLsWAOKdqtdJdYEX5aaWPsgersOVAYRqsqjvbSMj370I/ieP/2n8YlPfhKPXXkMy0sLNd4t1PQE1K6TBMwxOCVrNFAUBZ577jlcu3YTpzY28LPv/zn8yF/4UfT3tuG8g7FxBkBFYdnEnZFJMAoItvZDG2NgiJEaEwcL2cAk0apkmKFEKKsKf/YH3oNz507j1RuvYjDoo9VugTlBUUdzhzq+PUmSYyGdpRm897DGgplx1D+CsQZZI0NZVWh22lhYXsbtO3fwr3/t15TTzIuiEOgQRCMljJkot8bkhjkn0BiCIRMNGOgxc5+YxkxUGqVKiBwReUPkQFRZSkrLaW4Fo8TYIbMdCqjPGgYGPAga+qw0ZKsjn+jIWx0bK4WzUhorJdtQGh8qdt6xs44r64lNyCfi2RghYmW2wgMrRFFMmyQJPLLCbMUYI2maSm0fohKl0bI7uwi7dH71xGwGssOjASjEHSwA8EEhhpG2W9gZDHGvewhihg8eJ+YXcfrECh575DS2tvZhmTHTbqKZJdja7uLsxhoa7RYCCJV4MEdix9kTJ9AAx7CWEO1WogoJCgHBphkCMW7v7CGHd5rYeyphZ29vz9Vs+s/1+prWtKYCelrT+sNcc1nmS6C30++P+pUTm2WgJMFDPU9YZvg8bpWuzc5hpTUTu8VEOBocodFqY21tGQf9IZrNBhKboNNuYWvrADONDAutNp6+/ChUAtgmyCG4sb0Dxwam3URA3AIPqkgShpQO+XCIxU6L1+ZmZxD8CVa3VMwVCb4iSGyQ5MEAaMS5ykhiEB9qz7OPUdDHPOi4lx+DASk2HOVLHCJkIyBSY8wxQcJ7jxCk5gMTvPdQVSImgISCilGj/AWFpXyJCyt83mHDh0T09diJhjF1SuRDvuhxErhwrrRpZYMWRpJxUBowpKdAj9j0g/KAGENmHrGxw5CPR5cuXij+3//kn7pz586Fot+XNLXHVgbiSMJgAorKodGewbWXX8EPfv978Kv/8pdx6dJFrK6uQSRi32KEdVwAGWPiG3wQpMYiswlu3byJzzz3PJqNBv77v/f38OPv+68gzsFXJYwx0NoGUg81Qglga6JJmwhcm53pmMaB45/PMKPIc5w9cwbv+f73YDDIcefOXVibIEnSmujCqGo/fZIkqMoKKopmo1l7uOP11x/0wExoNJooyhKigpmZGczNz+FXfuVX9NWXXgxJq1364EdEGBEoN0wloE5BlRKXIlowYaSKgVcaiGCkijFpJG6QkIOQm4SgBEEu4nMxGDNjZCwPWGjINh0aS8Nmko5tipFNkpxDUpJPKhfSkn1SVc66SbfZmMSVxvrSVp5t5dmYYJIk0MAIatlLxGpMIhMxzWwlJo1auZ0kOgGUnzzbsn5YLK135tbOLC+3uHLs8wIJKA5uTl6T1sK0W7iz38VBHgNU2Fo0bIa7t+7CqOL2nW2c2ziBne0uDCdYXZnH7zz7ImbnZ3Hj3n1I7aNPwTi3soIUCjcuwHXAUhwqjjtUNktREnD34BAO7ILyfpHI0UPieVrTmgroaU3rzVb51oIHMNjLB0fbvf6YGimSZha3rZlBqmBVhKqCG+dYbDaxsbKMIB5Qj3FVojcaYevwCG+5cgEvv3oPjUaGvcMerjx+Fq+8egfDfg9H3UM0ODJtAcKr27sYK5DOdOCZoBw7jcwMcQ7j3gAziaVLJ082MmAZ4k9mPsu+QqeB1IoBOCWgnh6L9AT1IXKYayuHF0HlPCYjhEqkUEjsG3/hdfnyZZ0kJ2qNsDPMCN5DoPA+QMGw1sZADdVJoAoByvEHSD5fVPcb1Y1+/ccPETuefUDnqEX0hjFqrZVjEW2SwLbypU0rZ6RsSDJmTYakNKAQBqwYQDHwIQxUdADmfpGPB9/6be8a/+q/+hX31NNvlfHRkaaJVUME+5DPmDlaLdKZGRwcdfEf//AP46d/+qdx5vRpbGxsILEJqrJ8sIMgEoWujUSLNEthrcXNWzfx3HPPYTQc4q//lz+Of/AP/0fMtFoYjwdIUxspCxEQDmOi3yZOfgISnc4RfweqY91jN5SZUBYFvvM7/xSuPH4Rm5v3kI/yaMtwDqKC4P0xraOqKgQJaDQbICaUVQlVxeHRAZgZ7XYHeZmDmDAz28H62ir29/b0Z//pP1VKMi8qJYEKKFUq6qEaOEZIexGpiFAqac6EMYNGohiJai4aChItQVqIIIeYnMTkCeuYVEckGAWlsagbmwRjm1RjE6QwXkrr07LyvmLrK5P4iq1zbJ0jU3kylS+tc4VNPBkbyJjA1ga2VtAjZTZqTCJErERdJTIaO9I9sXYQrLWylaZ1VP0zOIuzPCiKVOHXzyytbJyam02LYZ+lLGOyJBRkGLCMRrsDTVLc3N3FGAKYBKGqcGplBQgB+/s9PPOWS3j+hZtYPbGArJGgNyxx4dIZjEPA3tERmBjwDkuNGZxeWoKUJao8j4iYetxBTVxQcZaim+fY7B1KCS28aG/Uao1el4I6rWlNBfS0pvVmqqu4GhrN5vCwyrfvHhweemK1WQaps6knTgaWgGI4RDthnFlePh5qOxqNcDAcotlq4da9XWycXIEXwWhcYne/h5XFeZxeW8Zs1sTy7Dy8C6C0ga1eDzujEdKZNjSxCBzRxiFEoZIfDYid0OVTJ828bSxqVZxtWmq+NkHvjSsVyyBKSWFwnPj3INo5hACIQkNEi8UO4vHfhwmE4Yssb0gDoKoPWUKC85FLHDzIMIhjZHXdrQMRUYDSH5DtRz+LzpE+QNxtGaN7zEpklNmKGUcRzbWIZqNjMnYobAfEZqAwA68YKusAoD4T9wa9o+Hjly/kv/qrv+z/5Lf/SRnt76ORpXVoTc3erk+49wG2kYGsxf/5L/9l/LW/9lexvr6GS5cuodHI4MoCEgK4joyf2CW8i3SVdruF+/fv44Xnn8fdezv44R/+QXzwl/8FLl+6jP7BPtI0qePDCaKxsxyTOqNNg4jqUA0FGwswgw0heI/V1VX8yI/8MHqDHHfu3D62kagovPNxd8daVFUFAqHVasWo+Lor3ev1kWVNZFkDxTiHMQybWLTbLczNL+Bf/vKv4OWrL2qj3fbB+4ldQLh+jhTQOr3bGUbBTAURRkwYGcWIyIyJtCBGQayFTUxOrDmlyI1JxszJmI3m3mpuQlrYoIXxaWltWlWJrwpb+Tg4+nmO3HoeF4HHxXHXmQdWonA+qoVzN0YR8aEaE7vO1lrZaTQCbid1VP2zWq1XLGXZnAWfPr+2ttG0nIx7fXhXwZposVEAToC03ULfOdzY2YbUw5edrIGmTTHfauPimZO4dXcLq6sLqILDzt4RAgQ2S7DfH2C3fwhbL/ZPLi1gvtGI/OfKIWGuY+AFwRMoSYA0xc5gQAfFOIgxeUU8wt5KNaVuTGsqoKc1rTd36YxdyHvQV+8dHt4dVU6UGV4UXuVYRLIo3HiMBIozJ5bRZluHTwCjssSpjXXsHh6h1WqgKB0uX9jAOC/AzPjEp17C+dUVzDdbcU6JGT03wsv37sO0W6Asgwcg5sELsRiOUQ2HWO3MYH1hYRFldd420vZX6HVKVoIFkChFAR0khmkoFE4CfAh18p0BlCAhDhERVEHkv9ghwr29Pa0fRqI4nvitBYro4yWK/th4nkOND2QoiOUPPpThtXYOPAhbQT1YWCcsKo+MsK08mcQZm5ZskSfGjogxIg3jxGBkmIcgHSik10jT/kG3N15YXKre/wvvD//JX/o/au/gAAQBceQ9hxARYgRC8IIARtru4O//3b+L//g/+hGICp588knMzM0CtXBm5omqPEbfkQLtZhPdw0NcfeEFbN7bwTd+4zvxS7/8L/Btf+KPo3ewjyQx0dIRc26QWHsc6R7XTwytA4aUAGsYvV4Pf+Z7vhtPPP4o7t27h35/EMVyHcltEwtjIvMZELRazTqSPMA5h6OjI6SpRafdhqvc8eIBBCwsLGIwGOBnfuZnQGxERAITCRuKBn6gBloDDA2GtVLVQgXjaNvAiFjHhnVMbMZEmjMjF9UisBakmgerBRspnQ8VuVAxe1ew9YUxobCVp7EJJk88j22064ysTA4zTuLn+KGjFs7MicRu88S1vAxm1smRJEnsPN9uCzB3HG40W1XGjEadlaSz8ej62knrgykGQyQxvrOOXBeoYaQzLeyNhtg83AMZAxXBbLMDKSoMjwa4d38XM+0mAMVRb4yzZ1fRaGY47I/Q7LQwLkoQx2Cns0vLmE0TuNEYqNzxYinU748mS2GbDWz3BxgE7wKbnhIXwNUpfWNaUwE9rWm9yUu44UoHvLLT69/slVWwrZZSYuuc6kiGtUTweQkZlziztIylVhtSD7htdw9we3vVE041AAEAAElEQVQXTz15EXc29yAh4OVX7iDLLJaXZrC+PI97m/fRyRpRnZKiBHB9axvBJkg6HXgYiMY4ZgNAnEPeG2Ch0cITG6fnUtUziYbZyGp+o4XgWVJVhsKKBBZRKAGVc/A1Xi76NCaiuaYxULRBQtWJyJdywxRjrFCN4EJt4yAVSPDRAxtijDhz9Hd670GqxJMJxz9Q8fzhOjb8IRH98KqEjDLHrXkasbCxoXTO+yBlEJeLIgdpIdBxCDoCaBiCDIQwqJwfvfjytUqA8N/93f9O/8ufeC9cniO4CmwMGApmqi1BD0RNOjOHX/7gL+I97/4+3Lu/hSeffAuWl5fATKjKqiZm0DE3OvrN4wDfeDTCpz75Sdy9u4Xz58/iFz/4AfzIj/4nGA56YBWkhh9idXN9LVD9c8RFjyGGcx7r62v4oR/68yAI7t/bhISAUHeXbWIRvEM+HoMMod1uI4QQI7ydx6DfR7ORYXZ2NnLARZFmKYIXzLY7OLl+Er/6q7+K5z/9nCbtlgQfVGP2IOQ4Uzw6TwhwqqZi8JjJDBQ8CMCQFCMGjSgK6nFQzUk0T8XmLFq4XKN4ZuPYRPQcF2XgvAw0YmE2tf0iepmjb/n1R7RpxOHSQTCmJ8yHau2RPBDNh3UHmnUnSSKy7nY7po3i2WMLROrbtnJu4ZGVldXTi/MLMs65GuXxpk3x7h2YwI0M3Gzgle0d9FxxjDWcyTJ889ueQmoM1pbnYcDY2TnC2996CR//9HWMqxJpq4lX79+HUwFpQJtTnDuxhgyAz3MQFOIDNNTDvLV9YxQEt/b2MVRfephDIR7jASJ8mkA4ramAnta03rQVtxvv3Dns3t3uD3JKErWN7HjfMQQPhkKqCsVwhLX5OazOzUPEg63F3tERKgnY3O1ibXUBy0uzaLUamJ/t4NlPvYz1E3NgFbz9scto1+lwMAlu7+9hdzxGNjMDRwahJhcoAPIBw8MjyoLHhdW11hxnq+5osHL27NnmGz9EWLFayyDwcfOuFmahHpbUOpFQxSNI9CnX+SYCoCBm9yXlt4jEjmrd3iSN0dEIAu8DoBE0HHz08EZmBzPrV+SmTA8dv99g4eu2pzvHeLuNWhAxH+oxaYGtEOdCZAIZ61hMRSKlMBeqnBNjBKKhqA5VZESGizzPq1defjl0Dw7kx/8f/7n+9M/+E203GqhGA6SJhXo5xtQFqf3IQdCcX8FHfvt39Lu+80/psx//uF658oQur6zAJglcVR2Lbh/8sT1HVZGlKcQHfOLZZ3HtxWtoN1v4H/6Hv4f/9r/9byAiKKsCSWqj+Nb4eEECnA+wHD1PqorReITv/u7vxjNvewuuv3oL+3t7sNZCRZAkCbzzyIsCbA2ajRaKooiR3VWFwaCPmZkO2u0WRqMRRAVsDcZFAWLG2to6ukdd/JN/8k8nph8R1aCK+D9A2ZAaQEjVKZlCVceqNFDRPhH1iKkvTANRP2KDERs7ZrFjNknOVgsfpCAOFRnr2ER6BpsyELHUhxKZ14jkiX+ZOXnNYUxaYw7t8TERz591RRmjaE/E8zHrHQDQSClrAetPnj+7MpdlzVGvR6GokLA5vlidCrKZJkJi8eLmJkooIATWgEdPb+C3f/fjaKYGL1+/DWMYC3MdfPzZl/Hk44+gUsH5i2dxOOzHBFIfsNBq49yJFfi8QDEcwVJ8jmNKpMKLgtMUY1XdPDpCCS08mV1hUzz0mpmK52lNBfS0poU3rw9apN0+PAyj7Tv7+/0KGshYVKEekyICk8ICKAdDtJhxce0ULCLuq3AOJk2QNjLsdfvY2joEAHR7Qzz95EXcvbcDV5YoxyOsLy/FwAvD2B0OcGtnH2mnBUkMAtV5bwoYQ6iGY+h4jI2FueTswvycVKMzaa6LX5HXqlNCHcABIhhDMa5XJQpnomjjqAW+iGjcwmcBdEzypQnoQLX/uRZxqLkOIqFOv5PjZGkVReRQgIz5it+Y9Qv/dzWdo+5CG2PUGKPMfOxxBUhpFAMzGpULROwSNiWJyQ1pbsBjgMakGKtqwcRVmqVBCXLv3qbeur2JP/1d34Vf+OA/w+VHL2Hc6yJJLUItgg3xxJeswXltzS/o3Xv35M98z/fIz/3sz+HRy4/q+vqapmmmE4/xpCaR4KX3SLMUibF4/oXn8ezHPwHvPP7yf/YX8f73/zxOn9pA9+AAWZYATDEAiAjEQKg96t5VWF9dww/98A/BecHt27eOkyyJIlHFOYdGs4E0zaJ4DgHjfIzxaIROu4ksy1CWLlpNQKhqKsvMzAyWlpfxm//uN/Gx3/ltZJ22eB+CEgIxB4pwcAHUi6ojohKq44is0z5b6rHRHkN7jDBgY4esyUjUjdhobixy45OSjK1abHy92PHERWQ0v0Y8m2OCBpHR2F2OiyZrjyRN+yFN+8HariRJIsYY3UpTmRwP2zaYWbeAaAG6+hrxrAD03QC6/e32qu2cf2TlxHKmavP+kBgScZKqECKIYTRnZ7A3HuPW/i5CvQCea81gttnETGpxZm0Fa6tLmJvroD/OkaYJsmaK7f0ert3ZxNb+fvQ/Q3BqfhFrMx340RjiIv+ZKDKgfVAgsUhaLRzkObaGA3jQ2BnaElOOP8/CdFrTmgroaU3rTVYyk2VFARzc3T/Y9syVaWSQutMCjaESrIAbF7De44mzZ9Bii+BKKDOef/Um0maG82dPwqQGGydX0D0aYDTMMd/p4OTyAoa9AWYbTVg2CAAG6vDy1hZCkiBtt+An4SWqSAyjGIyQ9/s4szBHF9fX5xrgt9tQnD+Ls8kbe0MSqo0hEiOlY7CLisTupOgx+/VBBHotdi0HQAZstPxSHtk8FK9IzPHxmEDGxIE38QA0GjaORTVRCACQ6ldoSPBL+L4frtVo5EMfv6ky113o2srBRpg5EAfnQ0zIEzWFRjvHmIwW1pDTECDOkWFD3nna2d7BjVdv4Bu+6Zvw8x/4Z3j7O78WRb+LJE0iSpBjvIxXQA1L5bxLG81yOBqXf+kv/EX3t//W35ZTJ0/h3LlzaHbaKFwVOb91dD2Z+LHzHiCg2Wzi7t27+NhHP4Ld7T181//hj+ODH/wgvuEbvx4HB/uwhmCNiT7qeOkgTQzKvMAf/2N/DG976glsbt7H/v5+zaGe2DwEjWYDzFwPCwryPIerKnQ6bWTNJsqyqtMMCeIDLAHtdgMn19cQfMBP/c8/NXmWhECemLyoeig8AAeliolyIhoz8VBV+0HRY0NHDOqxwYCNHRqkoyDI2SSFCVoYHypjgiO2vrSJ47LyNC6Exiw0mojn+Fw+EM9dZT48FsKTDvNkETU5NhsNQZJEYku9yHpNF9oYxfW5z+o8AwCuXDHjspy5vLp+6fTi/IqMc8r7AxjE16go4BHAjQTpTAfX7m9je9ADJwm8BMw0GtDS4cTiHD7x6ZeRGcZvP/s8Lj6yARjGzbu7+OZvegcGRYGjfARrLRIQLqyto2UN8sEQHAQqAu89vAiUFGk7AzUy3Nzbx17eh9h0XIned87mv4d9YzpQOK2pgJ7WtN5MNcoyL0D35v7+/YO8KJNWA2yNhnrLMngBQ6HOwY3GOL20iPXZBagPkcYx7MMD+N1PPY9T6yt4/oVX8dSjj0BVsbWzh7v3tnHh1AlsLJ9AZixUGSCLa/e2cOQcsnYbgeiY/kFKMKIYdXtknMPjJ0+25tg+HcbFo8VqMVtrzzemVgF4ryB2KnE7PASBDwIVPfbLkmpMuHu4nyQqgI5YbPWlPHQ9rEigmKIXEDvdzBzPO4Cyth3EuOjJz8MAruLfI3XjC7jxP6sPd6Ffv01PxAoaa0EsxByYTZUwl5Y0J47BHyJUVl5URQwUiSsry9awiKDf6+H2rVs4/8gFvP8XP4Cvf9e7UB4dIUlsJHIEUWNIRcSpYlz50DdJcmTSdPA3/vqPF3/tr/54mJ+fx6WLF3VpeTlGs6tGf7nEAUWqdxgUilanjd3dPXz0ox/D1Vdu4soTj+GDH/wgfuD734OjvYN6qDNuBVjDqFyFTruFH/pzfw4qitt37kCCwFgDFxwEgkYrg0iIg48+YDwqIEHRardhkgSjfHy8aPXew9oYAtJqNrG0vITf+s3f0I995COatNoSogfFAVQRoyJQCaKSiApR5EExUpaBAgM21PNO+wwaGCRDAxoFqcY2odwGKSuTVKVNq9I6Z0rnOC8DkQnMJjzoPEc7TvwzDgO+vpNsjNE0TeVh4Xw7SaK9Z3LUATw4tvqwotF42PP8mtoF0g6weGl9/ZHFRmO+7PUR8pySOuxGWeGCwjbbcInFte0tDDVAiWHZ4JGTp3C4d4hUCWtL8ygKj6956jHc2zrAwsIslpZn8ermNjb3d+NL2nu02OLSyXXYEIenSQUs0aIjEHgCKE0xhuDO4T5GCPDGjhzTTmGq4nUCmoErmBI5pjUV0NOa1puwzNaWqsXg/qC7vdMfFJRlYJvUm4/xhm6ZoFWFoj/AUquBx06fhkLBDAyKAv2ywNraKirn0ek0ceP2fQCEC+dO4eypVTz3mWtIAJw/eRK5L6DW4lZvH7cPj5DOziAYA5moUwLShDE+GkLGY1xaX81OzS+c1yK/0gl8eh3r6Rv5+3sigfpqEn4g9a2Ool8DEKnxYw4SAnzw9Z1QBdAxN8yXJqChFEQjRZo4pjgS155e1GEgCiKNaXjRAk3mQeMa//6GBn8vAfCu+oh1G8DDSLtI5ACISJsgpcoJiH0QLQNrIYpcRHOFelI1EMmgIWMiG5xnji1c2t/bxZ1bNzE/P48PfOgX8R3f890oB0MYa6N9I6gnRQGiI2Le9c5ve5Gd5tzS4T/8+//P0Y/8yA85CUHecuUJXV09ERcmIDQbjTpNkI/jur1zaDRbyPMSH/3oR/GJZz+FhcUF/KP/6R/hr7/vv4KrKlRlXiPygNFggG/+lm/C137N23Bvew/b29swNoFzAWmSIUkyBCeQoCjyAqPRCFBFp92BIg4YGo4dcVVFlqXwEmCMweLiIhqNBt7/8z+PYtRTNsaLSAVoSaolg0qQFkxUQDVnorEhjFQwUsaQFANWDBQ0LCs/CqLjSde5tL7ixDnOq4ieYxuYbeR4sxXmJEw8zw93nSfeZmbWrdqiYYzR20mit9ttud1uC9I0dpavNqM9o06xvFhHwU+sHZH3/NnX13sB2rl1a2adW6eeOH1qLRVtDbtHakTr8BSCKkGI0ZybRc8FvHz/fiToKMAiWGx18NjZdVy7cRsznSYMAYdHfQxHY4AVI+fAmcXd3R0YwxDxWJtdwMbiAsJ4hHwwBj2UBCoiQGKQdFoYieDV/X11gDrCSNgewNrqIdsGAxcJqKYWjmlNBfS0pvUmqYcHxihgnThtjfsIe3e73VyyVKiZwQVBCNHCYBSgIPCjMVpMeOzkSTTAQPDwEnB7exsnTi5jr9fDzFwTa6uLOOoPcf3mfZRFhZMnFtHJEsy1OiAVBCjGCHh5axum0wa3WggwEERMnCFCOcwx6vaxNjfLT54517YanuBQvUM72n7DbBzMmhIJYFzcCle1zDDEiFC5uKcckwDjQTXsgMkogDyIfikeaCIiYjYINRZPtWYE16xgKEVqgyqCBDzETvvq7Wal0VqyAWCdH2z5A6QYkuZESkRCRIFIHAlXZEwJhNIYEmKyQdEQQSpQYzjSL6LnGOh2D7F1/y6ajQb+8U//FP7Ed3w73GgImxll0lKZe0zYZqU7sMktKG5V3m+2FlZ2/s2/+tf97/2ed1evXLsWnn76aZw5fQZsCKI1yrvu9BPFa9A7D5ukyLIGXnzpRfzGv/sNDEcj/N9//L/AT//0T+HM6dMYDgcwxqDZbOL7vu/70GikuHXzJsbjMYyx4EmAUOTuYTQeY5iPkTWbaHc6dVQ8H1NFjLERmwc9DlE5eeoUPvPcc/j//m//G7gxE7z3jogqYi7BXLFSCVBJQMFsCpAWCh0bwjhhHtoYxz0SxbhhbMEmqSpjXWmd49x6kyc+CuYolh8MCUb8XETQ9WTCan6447yVplLjC19j34mieUJneba+Xp8VXG3q9TTVzUYjUjeSRB8aHHxNXX33uymM3eq5pdXL55aX5zXPzbA3gDVRIceBPoLaBI3ZWby6t4fNo0OAGZV3OLWyirlGhls372Jhto25TgP7u10kxuDK42dx4842BITGTBtH41EMUAFwYX0dJzodlMMRSDwSE01bxhqADWyaIWm3sD8e4+7hARxb51VHQdwQ1obXvL+edTS1b0xrKqCnNa03l3jmybEFIVBWjIDDV7Z3Rv0QfNJu1V1hHLdjE45Ip3IwxJmVJay1Z+sBKcagGOPFW5uwqcG4LNEdDPD45TNYWZrH8sIsbt68h1NLC2hZi4QsAoAKiufu3MGhd0g6LXhmENu6I0sABEf7XRjvcGXjpFkw6SXOi2fSFCvAleSN6q4SmwCgBBBNx6oIKtFiIRpDOGoBNInxRYQxKwCf0RfHgZ40/i2YVYUm39MYA+ddfNwaWwcyMTyEGODIVoahf983Y/09riW8JlzlalNRdxgBYI8PlMgcd6CJSAuQErHAUwCJS1krgIIGUAjSALQFpiSIcLS4xIFVYw3SNEG3e4TD/QOszM3g0ccfUwSvpAgAchHdU+hdIr1FQW8p8U0iulG5cKO9sHz7U89+Yu/d3/t9o1/7tX/jHn/8Mb18+RK4Zm5PRKxqtHQYEwc6gwCNRgs3b97Eb/3mb+LunXv4nj/zH+Ln3/9+fOu3fRsOd3fwjq95Bt/+7X8Sm9sHuLt5F1mavebsOefQ6/UQ6ihuYwycBKAOZKmcB+phSC8+hnWEgIWFBbRbbbz/59+v/cN9SRqZg1KpjEJJSwYqYjgCVURUeZVSlQomLoyxY1aMRTVng5yNFt5oWflQsU0dW+uNedBhNmbwGsHM3BOirr5eOO/UvOaJFQMP2zQmHWc8Oznktf76Z4870bjdloe8z591bQ0++Ulr4c49eW7j7bPWdIbdI2hVHt+sVQFPgqTTAhopPnP7brRvGAsCcGZ1FUe7XTSMxZULp/Hsp17B6dPLmJubwcc/8QqeessliLX46PMvQOpNnQyEi2vryFQx6vVhVMEUA1QU8SJrdNowjSZe3dnHkSsgSToStn0iLuNrFCYeZxkh0JTIMa2pgJ7WtN48ApofFtErK0J9H0oHdG8fHBxtD4Zl0mmrplY96jhCEXBQhKKCGwxwemEeF9fWgODRSFPsH/VxamMNnZlZDMcFjGF88oVrIFLcuHUfVx49i09++kWcXFjA+ZMnUQUBkgx3jw5wfXcfjcV5OGa4eqpeFcgMY3B4hLx7RBdWlunRtVMnuHSPZ6BH1zvd2TfkXGwBnn0ApDBMTjX2C0PtfQ4qUTwj+pTlOM1XX0Nz+GLqhRdWYlOf1IgqEdMkQbyOqfZgExnDoX5MNhEDIBAR+WqLCZ5EfH9YJ0i720miW8boeu2FftCJBoCGApVSyoEoDSASBA8iWGZqEqGpKnaSBMkMGIrniIiQJBbWGkAVZVHEhYWqqOiYIFsKui3QW0q4TcAtEbpOoJeLonx5dmnpxt7e3tYPfv97ej/9Uz/tLpw7o48/9oQ2G02tqhJmMhxYUzOO7e4i6LRn0Ov18Nu/9Vt44fmXcPnRS/iFX/h5fP8P/ll8x3d+J2Zn2njhheeRj/PafgPYxKIoCwwGAyQ2QbvZfHAtSYD3Dr5ysfspQJBw/Ly3221sbGzgxis38M8/9C/UNNreV74CowCoUFAJJqeAY2YXVB0ITomqoFr6EAphLVhQBNEyhKRk5yOezhQxAIXtsWCOC5wHVI3X4+d2kkTShzrOx0ea6oOO80Q4v8b28zlE9FWJgSPPhs8loN8N8NXre62Tdu78kxsbTzRUG8ODLowPxBAElRh7zwbNhTns5gWu3rkLhxiq0rIprBAaCWG208JHnn0Rf+Sb34r7u10c9oc4e24Nu0dDZO0WjsbjKI59wFp7Do+urQFlBT8swBIRkwqF9wqBgWk2kStwbWsbQ4g6Qd8pDkHkEQIDZw2wYbBaGDjHdRd62oGe1lRAT2tabxLrxnEHei8ErlD6xJjendHR7q39gyE1G+CsAScPYr2JFOodqsEQbSa89dw5tMmARFC4Cjc272PkHGZnOphpt3BydQUKoKwcUmuxPDeDg919WAVUHNQwulLh6r17SGY6MJ0mPBGUIiaMGZCqwGBvH8tZhredP590KDllvPv6zPKphxYCX0YZJUcCoFSQi6Sqmr5BkfUbLRYRRxZCOPZps4mBb9UXy2X+VgCA9UGNKkhUydhI3jBsIDWxASAIantHzYmOiSv01Xgz1mOs3aTDaIxu1VHNDxlXNAo1FhAJyIuPbnNiy2kAmgrOmAzxRDQroIj+ZA2C2KeNYjqzyaQdGcA0NMxbxHJHVW8T4S4IdwHccao3ie3L+bi4mjQaLyVpdvev/OW/fPTev/6T5framr7tbW/HwvyiRvFrEHyIiDSRY4JGCB7NWgB/7OMfw8c/9lEYY/AP/sH/iB/8sz+I+9u7uH/vPpQUZAwEQK/Xg3MOrWYLSZJAQkxANCBAInO4niitw3rin0mSYHl5GUuLi/iZn/kZHO3viklSryqVKuLAoKqDqlOiEJ30FFjJA+oY5IiospRUxFIF1orY+8okjkwZePR6X/ODcJOJeJ4M+pk6ph21xznymvEayw4eWDU+T/T7a8T0w6i6z7178+4rZoTe6tPnz509s7i0Mj48skV/iKRmbhMzHAiaJMjm5vDS/W3c7R2C0wROBBdObeDS+jqGvRGW5mZw7vQqbry6jfm5WSwvz6ESQXc4xtF4jN2jIyR1QM/5lRM4vTiP/KiHUFWwRNAgE14PqGFh2y3sDEd4dX9XK0A886GADolIEAJjtTBYKQ28j7ridqJTG8e0pgJ6WtN604joswxsMLDKCIGZWkFsYzCA3ntlZ+doJKqm0YDUbOaIbwNYFOVgBD8c4uLaCSxkTUADLBvsHfXRnumAjMFL1+6gkSYYDMe4fOEUrr54C51mA2fWlnHh1AZaSQM+KDwRXti8i8OqRHO2A19j86AKEoEVwWC/C81zXDm5ruut9hKP8q+z8GfOnj2bftkCej1Q5DkjihGoRFUeO8waBOr9cYc4iES/bOySEwCr8Uu+4Dp57RoBMCEEFihVtW1jYhU2JvqiVbXuvE46lgpSBPNAfPxB2Dg+lyh63eeeFVxdEcRBMpng7CZHk1hLgjqCElE8ocawKFIIZQAlGhMXwUQgip50VcT/xsRKUzt9VGGIxYDGQNhmprtEeo8IW0xmmwxvGzJbBLqnxDfLyl/zSi83Z2Zv/+RP/mT3r/xnf6WqikK/7mu/FuvrJ1HkRUQqkjnGF3JttfDeI0kSNBtNvPrqTfzWb/4WivEYC3NzuH37NvIyR5o1MC4K9IcDiAhazVb9nEaxbJih9XDqJLJd6nRLEQ/vHIwxOHXqFF6+dg2/8su/LJxlQUQdCCUYJSkcAx6qAUAAcWAgMBBACCA4EFUkWpXCFYXg2BhPxoTIdTbSJf4se8bDQScT8bxZi2c87HF+zYDgpPP8eQWyfo5r6fNaNwDg1d/s2lWYtzx26tTljqFseHhIblzUdqaI+auCwrY6CGmGz9y6i4F6AAwDYL7RxOioh5ksxaA/xN5OL3Kh59u4+tJtjCqHc+fPYK/fRx4qMBhNYjy+sYFMBKOjHnBsF4mLtUoEttFE1ungXm+ArWEfgW2oBIeecFAn8ySoKosQGA+SIafieVpTAT2tab15BHQgrDrGkmcAVBBJyTwKwP1rW1uHh0Xus5kWhAleJd7xvMBAUY3GcMMBTi/O4/L6ScB7pGmK3e4BenmBrN3Ek1cuYPfgCN4FbN7fx5OPn8V4NMLLL9/E6vwcUmPggwBscOtoH9e2tpHNdoDUwNcDVAxFMzEoekOE0ZhOz8/j8ZOnWlnwj2RCG9VB1XlDzkiDFBBPxJ6JQ8TFheMY7RDixxLjA2MDWo/bzpwg+RJFfHReio9MYGMNggqY6fjxa60eu+CxKy3ypXmuv5JEDv3s48PHfmh+mMZBYy2oFCKWlEgc6m56CESERCSkho2JA5YUv6QWzUzmWDhLveCQEID43AhIx6q6I0F3DNk9Q2aflA8J0oWGIwmuKxp2VeSu93rdB325PTv36k//T/9w9/ve/X35Cy88L8+8/e36yMWLUJ34ovk4LtxYC2stvPdgZjSbTdy7dw//7jf+Ha69cg13bt+JbOkQELxHYi0azSacd7UtJ4pw51wtyk28nmp/vfMOKgDX5I25uXl86IMfwr3br2raaHpVqUBUkZJjqAORVyCoaoBqAMXlHos6Q+REtcqdVsRaEbMvK++JCzHjJDAbXaKu7r1OOE/E88McZwCv9TkDeO2A4LP6BSysvpjpWry8tdV6fGH1bY+dPHnJlBUNDg7JksROfRAoAYEZsycWca8/wPN370CIUFYOK7PzOL28goVWhnaSoshLXHnsLBYWZnFncw8XL5zGidUlbHd7uLW1BQOCBIfFrI0nT2+Ay7jLxhAE7yAaEAgICmSdDkYAXrp/H12pVIwplXFAim68IBsWziUI4SHU5vUpwm5aUwE9rWm9OepsFM/eM0TiAdLSm0KZd7cG3YO7h73SttpiGw2EGnkcEHnQ4koUvT7aBDxz+QJSAKSCcVXizs4OhoXDjbtbaDUyrK8to9Fo4NqN+8jSBBfPnAQqh0fPnI2dXJsiR8Cnb90BGg2knU6c5KOYypcwg7xDb2cfbWZ83WOX7JLNOtaVp9tpcuINGc4pazULCaLQEGcEY1e4HvCrqhKq8XMTj+xEzFX6xWGq7l++rAAc2ARjIoHBuQrGxs6kyASSJ3CugojCWos6SUWPo+/+QK0av+chx53o66luGVPTOKJ9AyAFsThnAjwJvFcEEAkbEBllcNzuqM9DPbE5IWTUOeiYTCaCiURFvEouTAcMPkzE9GygAdtySGLHRGaMRMfEOhSmLhm5JxJeLpy7Or+8+srHPvrRne/8ju8c/dIHPxieevIt+ta3vlWbzQbKsozhPkkad0UIsDZGeosIOp0OhoMBfvu3fxt5PgYbC1VFo9kEWwMfYvQ7GYOAGBZkTCRzOFdBRWGSBJWr4vBiHeSytr6Ozbub+oFf+IBy1hQR8QqtGOSg6kDkADhm4wnsAXUq8ETkiMh51UqEHUgcEXvH1hHH7nN8HmqxXCcBbtU2jckx6Tzfflg8f266xudaWH0516d+7/d+r8mApXc8cuGJlVZjY9Q9RDEYwpJCRKECOFGYVgPZ/Axe2trCZtGD2gQBikdObmCh0cBnPn0NczMZEku4dv0ODnt9nDy5hO1uF8OiQtZp4P7RHhJjACgeP7mBk7OzqIYD+DyH4bgjpKyoQojpg50WDvMcL9+/jwrwjmyfbLJPhD5QaVPFtLVlZqTelYoLkql4ntZUQE9rWm+a7rMIHYtnVQYAzth5m3X7KgefvnVnVBlS227CaaRQxDARQQLAj8ZAWeDS2hrWOvMQ72FMgu5wiNn5WTTbLTgFXrp+F8YSLl86ja3tLkbDMfa397DSnoGR6DNVY/H8vTu4Nxwhm5uBh4GCYEz0vWYMjLuHkNEAj5xYwuMbJ1PKxxcbGs5/mQKaIEJR1CGwsdFLShypF3WHk8C1J7YeLAxR6NjEEgBKki8OCPLE3p4CKNmwE4Wqko7zou54G3jv4zCbChRUx3lPkteCfhVN9f9e4qAW0c24/Y+9+ENzjPSmqgoZOQE5IeIAQBhxWFBra8bENoE6bZCIjsNtgsiDB/ceCg0gygnomURGw2bIR6krjEsKYikSNpUlriBaGMJIVI4EfD9hfmUwHD/f6nRe7A162z/2Yz+W/9Uf/3FZWV7G13/9N+DkyVMgYgTvauGLOjwvhqg4VyHLMjSbTbAxkaTBBt4HiNbYQyKE4OsgHoL3DiISMXfWoCjHDxZj3mNubg5Li0v45//8n+POq69q1mh68aEyxCUzlSCURFQR2JFSxaSOQd4YcgA8iDyRViCpiNiRYQfmQMzCJkZxE0VO93ES4Ovq9uSDh20bX9iuxJctFl/9t/+2c9m0zr31zMZqS0JjcHAIrapISUHkPjtipLOzGIPx7I2bqAAoW1gihKLEjWs38dRjZ1EVDt3uAGdOr4ItY+fgCMIEsRbXNjfjy0gFDRDecuY0Zpgx7h6B/ORdKG4QBAU4y2A7TdzvD/T20QGCMZUn2nGku0F0BGTQTIyq8GBi33hwbqcielpTAT2taf2hF9HrxwKaJgI6h5Ij5yVwvwT2X9m+d9gtC2/bDQjHVDyN9xpYYhTDMarBCGcXFnDl9Glo8Egt4/7+Pnb7A3TmZtBsN/Ho5TM47A6xt3+EubkWTp1YRigd1ucXcPHUaZRVDrIp9qoRPrN5D+n8HKiRQcEgYpAIUsso+0OMDw/oRDPF0+dP2xnmx6wvL168ePGNSiUUFQkgDsfcXo2i1RABMHBlBWsMmGP6XfTHkjUiX9TP8O53vzsKaEWlQQIpgUGoKoc0TaA1wkxVji0jMfpZieIoJz80DPrVXJHKUds4mI3SMEZ6o04kJGLvOQpoofjLEjNEY6BMXMhw/XyEY5Sgaq3WRCenQQyoJNZR7hoF9uYcGg035sIRs/fkAwXy1pKHSEXCY1LpI4QdY8zNqnIvZlnrZZs27v29v/Nfj/6jH/7zYdjv6zu/7mtx6dIFNBrZsXVDJ8OFdQS7r5GHxBxFdL10mIiviMardxTKAqoSWcZQFEUOayJVRETQabWwvLyMra37+MAHPgBKrHoJQQgVqRZQ5ASUTFQxc0VMlYIqJVRBtIJqRaKVIaoscUUsFfng2XnPpgw0iN7nAz5UMOuxwJv4nI3Rsw/bNgB8tm2j83rbxhslnglE2Op2177h/MVvObu4uOr7Awz2jyg1Jg72GkANw7NFc3EOr+zu4aWde1BjULgSp1fW8PjZs2inFnPtFm7e3sYzT1/C9Zv3MNvq4MTyItJGEwtL83jp9i0Ym0BEsNFZwGMnT4LKEnmvDwupM6T02DKSzbQhSYIX7t7FkVTqyIw99LYPskPEeW31YVXhTj0wW5/fqXie1lRAT2tab4IONLAlVA+4EFQZ2iIAVFUUXMrjwLy7Oeht39jbL7NOWyhJEFQApdh9hUILh/5uFw0Abzl9BjNsARF4Vdw72MO9/S7u7+7j/vY+lpfmwExgZrz0yi0sznWwv7OHU0vLMCAoMUoCPrN5GwUTWvMdOI1WBgbBqMJCcbi9DxmP8dipk/zI8soZHY/PN6uq9WULSSIFjBA0MCAEVakxY5Nv3GhkCBLDNbgmAcT3DdMWQvoldG49ARUbdgDUMMNVFZxzSJIEKgKuO+A6cWzELiXVOwZ/GN6zarTdgzhvIlYa50K1gIbjkDovQAhaG4JjJqVMFFUcKn1Ig0R8INVekQiUIbAoqUfgCjwKwHXFViqIlgVBJK3ogy8TD1AlihFDD4j5blWFa0HkenvxxM6v/at/Ofre7/ke//ILz+vb3v4WfezxxzE/P3/svQ7BQ48HXh8ku6sIDFP93Elt+6DjeG5jDawx8CGg8g5ZI4uBIBKHRufn57GysoJf//Vf12tXX9Aka3gVrZip8ECu0BxA4UVKVa2YqWLSSYx3SaSlkBYitXhmU03sG2xtYDYK6urqw93nhwXzJBDl9Z3n19g2PvwV6TzXJ5FOIjv91jOnv6UDXervH8KPC0oTE3M/ATgFsrkO0rlZfOT6DezXyaZeAhY6HXR3DtBOLa5du4NLF9fwiedfwcJCG4Wr0B8VOOgN8KlXXkERHCbjBJdPncSpuTmUR31IWSE1Jj5/IMAQYBM052ZwmJd4aXsLBeA86NAzvaqgHWIpQFW8MJug4eQ96fa0+zytqYCe1rTeLPQNwkotoEW4rW1qqsSJ8QZpIC6DSXcOxW1eu7c1dMaEtNOCJ6qhcRG/ZQnIe30U3R6eOLuBjblliPdgY7BzNMCZR86gMzuDJE0BAra2DzDTbmJhvoO5dgsNBtrG4sTcPCpXASbB9f1dvLy7g+bSHMQauMkEnRIya1D2hsiPelhvd+jp82dn2qIn3WBw6izOZl/WguIY9au1lSD+jhP3YhwmA9LUoqoqEAiWAQISkF1WkfaXmEQYNKg/xpepoKqiVWCSehg70RpT0GJb8yGKyh+KUszNSZIkMglUAUgnXlygUscUO9AiGvQBkSKuU+KTcJwEWdueH/hYqNbFE2FMgok4fKiiy4YUvp5EM4BBUIBCFaRSRT+o3helG+O8uN5eXN55/vnPjL7rP/yu6hfe/4t68cJ5ffItb8Hy8tKx/YIoht3wQ1cS1x1yZgOmGAXvXS22rY34Ne8QVJBlabR01IukZrOJE6urGAwG+NCHfgmqEBCcQgsRHQMYKZATUwFwAaJCvBSiWmiQAqqFKBWkVDBrTmxKF4Ij5zwZG2gQFzArzLrzcPf5yx8mfUME4nvf+14CofNtjz565tLqiYthMGwP9g81NQwgdv29KEoArYV5bA1HeO7OXTgmVD5gqT2DpfYMUgbWl5fQbKbIkgSdVgPnzqzj8GiAxRMLeOrpxzHyHqUEaAiYYYu3nD6LpigG+11Q5UD144GAoATTyJB1Ori5d4C7h4cIRCNPfE/AN8iEXRBXNRyeVDW+v76WwjGtaU0F9LSm9YdbRMdkrDkR6qjSKBozqAEABTT4UAXi/RK4e/vwcLfvfNFZmFM1Rn2d0iaisIYhVYWiP8CJdgdPnj8LUkFqDXa7B7iztw+kKYQNvBc8euk09g6OMB7lODw4RDtJcGp+DmdWTkCDBzWa6EuFT9++AzPTjl7o2gxLQkhAoMpj//Y2Ui/0josX+fzS8iU7qP5EY0kWv2RfsAhVVCkQgoTgVTSIRIPAZFAsaIDzHtYmYCKoxHOoIgmI1oPSzOeKSH/o53nN5z70oQ8xgKb3YpkjhSJ6yBlVVR7jziZe6CBRRrIxICJSVYvVwuAPR7qZ4tnJh/uTTxEAlGWpRKTpcao6g4hJRSjaHrTGCdaJkBPUnypo0krWaPOQ2KuO31uEgIsEBJpRJaAg5wBPXgCohYUJAGAoQMlaq4HIGcZAgS0mc308rl5uz8zd7h71uz/2oz9W/MRP/GSYnZnRp59+GqdOrsN7h8q544lJY0wUzcwgSLSb1Oxwwwxbe6a992ATaR7OeVSVizQOAJ1OBydOrOK3fut38OzvfkRNq+W9CyWURkQYgmksRLmqFkxaEaECaclEJZMpDHNumceUmLEochYtGsZUxCYQjeshzu4D7/MXXV8R28aDJvfV99FjwKW3P/LIW040shk3HHI1zpFahoSYqCPMoGYD6fwcnr11B7eGByC28CEgswnWF+awtjCP556/jvOnT+Dqy7exOD+L3/3UVaxvLOH+3gE+8dIruHn/Xs2UVmzMLuKJ06fgRyNUwzFYUc88xKFhJ4K03UJlDF68d18PQwFPZrcSeskQbntNjpwPJREFEElBpEBnereZ1lRAT2tabyr7Ri0aP+e/aEArkK9Eu8x8+/rezqub/UEPWUNNlqL0AUoEodghpBAwOjqC8RXe9sh5zHIKcRU8FDfu38dRXmB2roP+MMfObhez7SbObqzAENBMCC+/8DIWmy00rYGvHChJ8anbt3C318fMiSVokgBsAI7DY6kqxt0eql6PTs3M4G3nz51t+PBHmlKcA66kX/I5KaGA8S6IEw0+SBTMVFsHiBgiUdTaJAHXTGIFW5NkJxI259YuPr3yrve+l+uQEH3ve99r3vWud2Xf/u3fnr3rve81MfKcVFXx87/+6y1r7cWyKteJyUS8GUN8AIFQ5jlqgYkgWg+xTUSkMjMZVJX9w3PpdXTTmGNEWqwxGg0AGbRKABhLqsFCxTAziUSRrTHBJ3KZ60MmcdsT9cY8acyzNdZANaa/rTpW7dRtaycASaAgoCBUO5XN8euCBKASip4C95jpmgv+qk2zazZr3PtbP/HXe3/hL/ynVa/fD299+q164cIFJWPgQoAPAcFHz3oM3gkIwQOq0TNPXC8GaEJTOV4kETGcc2AmnFhdBYP0F3/hF0RFHBEXYBqA0CeiIRONLahkMq6mcVQxUIVzIsqVeERkRqwYkWoeREp2D+wbxiRyUJM3vuDuc5oqrv6eJJY36N2J8KEPIfmm9QvPnF1YeGfifNLd3odFpB+Co/e5VEJncRFDInzi1m0UUHgAzISve+IJ3Lt1D/3uES6dW8edu3uYabdAxHj0wlkUlcfiyiLEAAeDHhJjYDVa0JYbGfr7B/BFDmvpGC0YRKN9Y7aD/XGOF7e2kIOkMsmOWvsyQHuZl3EG8iAKRCTNfHqzmdb/vspOT8G03vx1hYA+AKCH2CNpx31vBRRlSZoRhZJ4KNbe366ql164e//C408vnkg6ncQNxlCecHgVlgh5b4D8qI8zy0u4ePIkPnbvDtJGE7uDHp565Dx6eYnObBNSVugPhzjqD9FqNxAqh29462N4afcQC402dkYDIMnQdTk+ev0mvu9tT4GbTZS9AbJ6qz6xQFE6HO3sYm1xQd9y7sz877xy/cqLg6NnHl3l+y/v4M4XfVMXoXr5HEDwRBSYSKGRNWxtAqlDVWJCoRzTGKqqMsGVc92D7jP54N7N7fe972qE4mn2vve9rwWgAUDx679e0vveVwBwRMS2Mb/ivf+m4XBwhYlTVzlWIlRlFFIeQGpiN7OqHCwzQtAHN3VmnvFNO0CXP2+S21eVD/qEIrn3Wc9LUUunRBNG8JaZUiayzDyBUoCIoXG2rHZoPKBzcN21BhGImeHJQCXptFpmWFW85D0Xajk+DVUAUYCS91CyCQFODJQlhGCgjGCsAJoDGkg196I9590BDHU7SyfOfuif/bPVz3zmuZm/83f/bvqN3/BNJms0+dbtWyjLEjaxMegGANOEXB2tN6oKrT8zmSwMIdQEPtYgAa1mA2urq/jEsx/X3/yN33C22c5VtAfgUAldVQwsUQlSz6AgRF4FjllLEAqAhgCGChoozNAaGQuoNBRcsMHTIBOyXQXb1w4OfkHV/Fzx3G+or/e93/It9r/58IeXvvmJK88sN5pPjbZ3zLg/RFavkogYHgQkCRqL83hudw8v7d6DECNIQMskKHpDnD2xiDljsXNvD5aAyxc28OKNe1hYnMPOaIiUCLd3dyJu0AcsmAxvv3AeifeRviEh7skFARlGUEWj00bS6eDVezu42TvQksiXQfacpbvwdlgZdQ1VQglCs16MESlUCWfxENJkWtOaCuhpTesPaV0FsAEAmAMgRKo6AtAAEWmjAdUxBUdcFmIOAvDqZ+5t7nzz5QuPnFqYt/nhEYWyAmkMGGFmSOmQdwdYPnECz1y+jE9u3oHzDgdFha3uEa6srmH37l2cXlqABMHCwgx6/RH2D3rIy4Cl+Rl8w5NP4ld/93egUDg2+MydO/gjVx5Ha2kOo+EAiReQKIiBlBTdrV3Mr63g4vIyveORc8s3P/nJP1UUbvsszm7fxu3qCxSVD1ksaowdRWIfESkbVqiS1II5BB+77qKoXIUgisWFOZw5s5E1WjPfEEJYI9IdAKmqzCrQkRBSidRjUUUF0kJDKNNGmhzup2ukui6qSag7mMZYiPjjgbM0a2DYHyCowFoDYo5236BGxFvgCgNXCV/1Q0ofAq5fBK+y1ucaqk1SrUgL5SoRA4OUYBpgtlJ7RxVcR8jH31Brj3GENWj9zOlksJCZyTqlhL23ELE+BNYWMyoGZSQI7JSVSFlDEFFiMobIqLIqKAQBjAoAL3EhNE4SMwoio1FejbK5xdFLL1xd+4Hv+/659/3Nv9n4wR/8weTs2TPsvWdVIVEhaNwtAWkUYnXXnCkO4EZqmtQWFI1ee2NgEyML87Pysz/3M37c7+Xp3PyRK/0BGdpjYMiGKkADg1WggUEhEDkGSiUaCzBi0JCBIZRGQZPCCpcmUc9jCjzZAfiS7RufN43yjdgZ05/78Ifb37m8+vSFE0sXGsG3tvYOgeDBtfVfEINT0rlZ+CzFR165jq5UQJpBqhKnVlcwmyVImfDCi6/i656+hOEgx/NXb+PchZPgRobmiUXcK3Lc2z+AZYYEjydOncGlE2vIDw/gRmM0CJDas06qUJuguTCPMRt86s4ddKXS0qa5Y9sLjCMrvgKMAqAirpjrczMEkExvOdOaCuhpTetNUxsRoNZjrk2mJC0iVlVFDq1jrX1FPLLAzqsHe9svb+/2Ns6fbdlWi1xeUFoLA1KFATA47GKmP8Tj6xs42VnAq8MjpGzxwq3bOHdiFUmjAQEwzisU5T4aWYbHLmxge/8IvYMuKmOx0pnB3mgImyS4MzzEJ27ewh87fxqD7QQ+eFiJKLDEAuNRjt72Li3MdPD0I2ebv339lbe+Mhy9A0vZZy4e4Ob1STTKFz7NpxMKhMShQQohkGGGDx5BAtIkhUiIYtZYiAB/8yf/Jqqy4sSYtcr7BUBLH0IafGgoIYHG4AcJAg0BRPDOOc/MWnmfZFnGzjlK0nijNdbCF75OHXRotBrIsgwaBCADw6ZuYAYjmbdY6Btsxpybr3IRrcCcMI+U2WgI9GAGUJWtMQZBM2K0AKRxDo+gGrnY8RvU5A2NcdevxU0DSkKkMBZqJaQWMjI9VWpFD7TCWYH1nsRCIQKokBUKAjJgkCEgeBgYQkwT9AYafBBhwwIJUlala8zM5IPBcPk//z/9X+auv3Kt9eQTT6Y+iM1Sa4w1bNkwG2ZjLPlaMJvExjRLLzF5W1WDD3UgDzSEIEmahIPDg+p//V//7Zgbjb6qHpDBgRIdBdIKSlAIgQRMFAD21qAyZIogPjfWjhg8rIKODNzYSlaUNjife29MKsw9Yba6DmDr4e7z7895/kK531+WfQOqJ77l8pXvOJE1LxcHBzTs9bVham4mEYQAx4zFE0u4ftjFc5t3Ykqqd2imGb7xqbdg5/pNiADv+san8Du/+xzWV5ZxYnUew1GB23fvY3b1BK7tb8OFgIQIDTDeeu48OkTY3zsEOQemGjlIFJNSmxlMp4PN4QhXd6N9w1HS90Q9EilKsDYB5ADQBIocaBLQQQfDL+5taFrTmgroaU3rq76YdYlZDqIXmmNXkJQIGjU1B09csm30D3yx/ek7dw++5szGiWymbYqDLnRi+ggBBoRRf4DhwSFOra/jsdOncfPFAxCn6BVD7A37SIOgNy7QbGZYXphB92iIu/d24ZzgkXMnca83xDOXHsP/8smPQRQoSPG711/B15w9hebcDIph9CWqF6gHGqnB4c4eOieWcG5h0Txz/pHFO5/+5Du0Kl/uddYOMNze/2Ju9ETlMepBJEyamkAMuas90NGLzETY39/HrZs3kWYppWkCBpKEEktM7VQEZAyIWEQEhmPSYM0BNipiqIa05UVO9+/fQ1mWSBKLsipiSB8BlXMwpUEjSyP4RKTGuZFhNlZCkqyUpdnDFVN3oeWr2M4hwLO8ZTZ0Ad3a2QIAGZASqQQLmEwVLagmxHWfmejB0GBt2YggEj7uSMeuvMawG1YmYgMJZkbarKoUjlMiSYgoKDNInUKtalCGBA5GCaJMliloMCaAEAICIMLqEXSswKGxFmVeeWPTETMW/sF//3dmANuCSTImSplhmWCY2YDYKJRiSs+khV5XpDU8+FPVK9RJCGNKsgElyaEP0mXmHgEFx1ebIebYHycEInUAKoUWBDNipZESDxtWRoKkqEKoTBmcMWkwJpFJTLd52LbxhYjnq1/R7jMUwJpq+xuXz156+vSZb85ETm3e21FUFXFCCE6QNFMIGNlcB9pq4JMvXcNuNYAaAwnRvnH31iZMUeGxxy7g08+/irm5Ds6fW8NLL9/FifUVPH36JLbLEtc/80lwEsOKLs4u463nziAMhhgf9pACEF9HqzMhkEFntgNqtvCZl17C5qgPxyY4wgEZewSVgAY4L9VkmTAEoCYHKmmKrZvWVEBPa1pvslJsGsV60IOHGMhELGMoNVUx2YasiMMYacEodl/a3d6/fXjknpydTcbtJvnxGEaiJ5cMA8FjeNjF6uoJfP2Vx/Bbr7yIrq8Atrh2dxN//Kmn4LpdjA76qIpDzHZamFtqIs8r3L6xCcksVlZWcHJhGXe7e0iNxau9fVzd3sXXLi9hvNuNISYgaBAYRkw0vL+D9YV5fM3FR/gjr1x/682yOEib/GnE/dP89986fgbgO4poXAQTM4iZKJIT4lrDHg+yBYnWld29XWzvbIOIYOoBNhc8QSfoK4K1luqUaRjDsDaJyDIXUX9AnU5HhCRJYCeR3j7EIBFRjMZjtFstMFtEIpogiihNVUxaVQ2LsyOP21cmSuerObRB0GgI57kwGxHKFYVRGIKKGjBSMDcASlSUiLjuOGukJ4oiPj1x/I+J61/UTIYIFQKBiXxzVeGIE2sS4EAkqo6EEoLGBSMSYnYENsSsKiaAmAgUNBjAEIwS1254Ji3VhYE1xoiqAzBqdBY7IYQWoA0oNRSaCDRR0URVLAhGo12bNKiKBGFLQkRSy2mASIits4ySMho5QZ9Ue8o0EJWCQSHGGx6Pu2sAeQt1pFwKkBs2Y4GOTOXyoFxYK1VIGo69C1FA98RaK1uvZz7/fnX938c7kqJDdO7rHr34teszMyeK3V0zPOxqgwEJCmPia8Ebxuz8PDb7Azx761V4IgRlNK3Fo6fP4vzaCqrDFB//5Eu4fP4kDg+OcPPuLmAN9vsDtJoZXrh7F8OqRJamIFU8ff4RrLVaGN+6C/IOx1gbpjg8mFo0ZudwUBT41K076COoo6xwRNtepevjDIWBKpUKZNFXJKpKw8l8RQhTlN20phSOaU3rzVFJvIky6wKzRgE90hZI81p8FbUvMSfvfNLY3yyGu5+8cyfPmSSZmcHYBQgxYOIAV0LA+KiPcbeL88vLeHR9AwqFZcb2wR72B0PsdAc4vbGKRpaCSXHnzjaaaYKl+RY2lhdAZYmnzp+L3VZmDCD4zWuvYMSMdGEWgTkGGlAUrKklHO0dID/q0cnODD197txCVvlH06r62tW51VV8QUl9z9KDIBUQIAkgiaiQSAzF0LodHUKA9w5BBGmSIEtTZGkWxW/930liwcYgSZIY9W0MkiStZW3sYCdpCmaGYapRzwTvPXwQGDKwJkFVVdEPHgLGeRE738aCiEmCJqrI1HIWQmVXi8Jgo28QExn5q3rxdv16SNM0GDMKZEwgNgHRMgSALSsyhdoggeThrvND3egYb/66JzaajQMR+RAoAIC2lV5HEovGZHKaESnICxEFSwjeQwKgkQsNGBgyRhkIjJj6CAjEgpySjJm0r4JD5/2+Aruq2AmEbTG0DTbbwrytxNsC2mYy2wzeAvg+s72vMPeVzJaS2VYyW2C7rcS7HrTngh6Q4oiJhlAtGOQh0QrOxEIgDyUnSqWCc1WMVTEmxpgFuTFJzhzK0iSO89ITGSHqHneePyth8Hqqx8fnqotfcV8PERF/44kzb7ty8tR3NEKY3dvcAXlPxtQvTUMovYJbTZjZNp69dRv3ix6UGCoBp1dXcfnkOl54/iUE53DxzEkszs2iezjE6tI81teWsdPtY2ZpAa9s3o1Em6rEUtLCMxfOIwyH6O/ug0MAc7RbhSDwAGy7iWSmhWs7u3jlYAcVG1+aZBCI74vqkQUoEZumaWKhqYGmPGU/T2sqoKc1rTdrB/ohGwcR6VwUj0pE2gRpo4kJ0g6UkiuJDwpg+7nNze5+6Xw6PwskaYz2RuSlGgKq0QiD/QMsWIOvf+xRtMiAVJAHh5fu3kF7dha7R30cHY0AACtL8zBMODjoo8zH2Nq8j/W5OZxaXInBKmzw8v42XtjaQefEInxi4ZSgBhCNHchqkGPv7hbaEHz9pQt8ZmZ2nYriXZkvHgGufAETPFde15EWq6pWFCSQGpdWI8lqAkRQRVFVKKsKlasiJzpMkHcUQ1Dqb+e8RwgBSZqB2ER2cFVBVRFqxrQrS3hXoSwLhCAwxEitrbFngPOu9v8CqsQApSFI0wbfEEmSomgkS3lu10cjA1z5ahbRCkC2thZ8mqbeFo2KbeLIhyohEghIgIRAxhh7HIVNRMfBKYJIswgq8DLJIFQFRInIBZUcpCWx8TRioRHFBSKz1IskBaBVRYIKAqLgiUKSULBEAQRJAYlh3KQGJPUREiIH0gpCuSpGIAyYcESKLhMfKvRARQ6C6gEpDpSwD9g9Fdr1ojtEukOEHSXsiNKuCnZBtK/QA4V0VdFjNkMyXADsLFtlGAIbgrACHEjZAVQyUQ7SMQEjUoxE/TiIFt5IVZnEsa08sxVjErHWymvwgUnyuUVz+nlE9JXPGTr0htR/+swz9gJw/l1PXHnHxmznyaPt3ay3e4jUMihEK5OAEIxBZ3kRO0WBj756AznFiV+C4mseexxXn38Jb798AaHyGI6GePbZl/C2Jy/g9r1d3Nnex+UrF/Dc9Rs4KkawJr48nnnkIi6eWIHr9eFHIxgJkCAQ0uiDShK0F+YxEMWzt+7ogRRacTIumLaU6D4RDwBLUElUJElVjE7Ec+uhXzJ2oKeielpTAT2tab2Z6pBIe8zCx6lwODY+lAXUMfuCueetvX970Lv38v5+bjptbczNaOEEQTXG67oAq4rB3iF0OMTTp8/g0ZV1hOCRmATb3S7ai7NImk2snFjAcFTAu4Dt7UOcP7eK7tEAl06vYdw9wursLAQKGIMxBXzsxqsosxTJ4iwKKAIDPgSIEySWsXd3F8XREZ1bmMfXXrg431D/Tiv+ycXF/krc3//9/eBERa1QiVXERNtFDLuIvN4Y4qHAcSgG1zaLonLw3qOsKgSRz1IaRVlgnOfwIYB4kl7nAADWJkjTNAaBiKAocnjvkSSxux1COA5z8SEgiAMQrFBoKKMpaZWGUFnv27aqqtiJxrv4q/iGLcBVt7OzU/VmQpn5fm6SUBhrS0A8EXEQcPSaM0Q1XmOTJjPheEeghsLFOJXoJhpb5iNSjEwayiRpOmMyZ0rniK0nNvFw7InZExvnyHsidj4EByJnKakCSUXkKiIpiaiCSBlEC4EWSjoG0Rigoar2VdEDoaeQHivqQ/uR22z6Cu0H0j6TxH+n6LGgB5UeE/pQ9KEYsGLEhEJVqyAUJI6FMgRcJ7oD0CCqzhIVhjEiNSNhMyLGOIgpiG3JzjsyJvDYhiige8LMupWmsmlMjOg+Fs5Nfc1xtRbRDwvr68DnYEDjDSFvEPDrzz7b+YblM992ZX397Zlz2e7dLTYhWinEBUAVTgBuN2FmW/jYjVdxd9yFGgMXBGdX1zE8PMLlUydRFSWq0mGm3cRTT57H5s4+mu0GVk+uIO3M4Lkb1+sUVcGiyfDOixfQFMFgrwt4DyJFCAJiQmBC0m6htTiPm90j/cz9u1qS8RWZA1HcCKBdEBdQNQAMVKyqcrQOKWFcx6h8ecSTaU1rKqCnNa2vrroefdAPvbnX4R9CREotUkApawBVRUHYDJ3NNg/Vv/KJW3cGXRe0ubgATwQfB5qgACwRpChxtL2HpTTF11y8jAYAy4yjfIgXbt7C4bBAqQoVwuxsG1kjxVFvDGsMJAjy/ghPnTuHtZm56EFMUry0v43nt3bQXJ5HyFI4BbRmJRMD4hx272whqSq8/fxZe35mccVU5Te0JX/HAhbav/dr+2p9Hpo1FtfAMKsCCCFaOIgiloyZ6xTCyecZxiQwbI67ycdsvNr7PBHJqgTnPMqyrIcRY0S3c1F0c22FCRJQVSVEArJGBjYE7xygUbgTgxRqDCNzEhpiTSrikomIXilLg4v3TL1woK/iTrTH5mbV7S4V4xDGsOkAwIiIHVTU+0g70fpcHts5iI+tHESvoREqKfqqtM0ajkYi426Xi948imHmCluF0lShZJuWbLOCTFKysSUHW5KRMmWbB7FjET8KoiMxZmgZQxIdEmNApENS7ZOiRxq7ziB0QdxVxUFQHEK1KwE9BvqkOhCVIRPGDIwBykkpZ9KCQYVVyqGag6gAUArgjJCDxOYnA4zoC+doxScFwVumQhk5BYw1YCiKkSjGLCjYSGWidSMYk4ZI3XhoaPA1nufm5xB2zc8OTLlYd6Cv5PTZ6Mcvr971Le+yDWD1jz75xLevZo2nD7e3adztotW0gArIADCMYA06KwvYKQo8e+smyppBnxmDlskwOuxjrtXAzdv38NTj53BncxfjvMTeYR+rq0vojgp8+voNHAz7SNhAJeDJjTO4sr6O4d4Bht0jMASiNc0F0TJiO234NMWnNzex40daGjt0bO4T86tgOrSWAixYjbEuvse85rwMASxMbzbTmgroaU0Lbxb7Rn3UN9PaAx0tHMMJo1cbTdKyJAUoeC95AG2XwPWrO/cOru8fVOlsG6bdRFWHDYjWEIsQsL+1Cx2N8TUXL+D0zCLUlbDMuLm9jWy2jWymjZmFDvYOexiOCsy2WzAwaGUpOolFcTTA6sw8JHgoJ+jD47evXYdvt5DMdVCIwitBNN7s0oSwf38fo8Muzi0u0jc99njWDnhHWpTfalpyYWVlpfX7IbmIy8j+DeqI2Kuq2tqKYY2BsSZ2gEMAM8c0uTrcwxiDNElhrY1+ZhG4unN8HPjBEckWgocPfoIvi/YE5vh9LCNJE4Bj19q5ElnWQNpIoXWsOAkACeTj4FKqwaeSpVYa3oaWM97PmPXRaOKHntg56Kv0WgzAdYfuej7bSXqAHBIwIGbHFAXysWqLFmeEECZZMpAaaxjd6yREvKtKtysxR9jby4HrFW7frnBwruh0NM+y2Tz1PE4Dj9PAI+tpZDyGrI1BUAxYXT8oemxxZMBdBXWDoS4bHJGhrhjqEttDYjogpn0F7ZLKrkB3DNOOgnbJYC8AB6LoMumAIUNWzUmpBKQUcCmMShhOmBwDHkTBEnkBhABNFDDERIYhACxD2cCLaKWKUlRzIh4TY0yCnNgUbKRk550xJjDbQMT6WdaNiecZD8dyP3x8nqoq+ryJpl9y95n05oc/fOY/OPP4n3r7ubNvzYKfOdraQxKzs6FBwIbgRGFbLTQX5/DJm3dwd9QFGQMQoUEGb7/0CDaW53HvzhYubqzjzt1drK4sImtkuHD+NJ575Q4WTizjzt4OfG3HmiGDr7t0CbOGcLS9C6kqgDS+viGoVMFZhsZMB5v9Pp7b3EQO+ErNrgduArRlicc+AKpsY5hlQq9FYsbq4itnf5nWtKYCelrT+oOqepAQ0cahky408gciutHiQMRlbvSQ0vTW/Srf/NTtO8MRSFsL85Gj5QSiEf/EQVH1xuhu72I5S/F1lx9DAkKWZOjlA9zYuo/9/hAH/RE6M23MzbaxvdvF4uIs7t7dxUKnjVQFl9bWMJNkKMscmjXx4uEOnru/jc76CqokgQNDOcZbExG0cti8sQmMx3jm/Dm+srpxlovyG5tk3iVFcgpA+nudhw6zIKYEjok4V4EE7+PAUQjHflxVRfAe3nuoClxwCOLhJUDqGGdAIBJixLP3cMHD+6q2bcQul3MO3ofY0Y52W1Dtn06TBEma1CK6gnMOZZHXHW5VqHoNQYyqSVWNik9UMqOhYUQ8e+95oygYuPiwgP6qtnQsnDkzBMK+KvZJkTMRMWJXXlUiC1gVVPsaIHFBIQo47wGRAMKOKm5jlodRnNe2aTzrtra2ysPDtOidao97K+m43zfj4bwZjdsYFjIalGJ7tmm6NqNDw3wQCncg5PcN+QOBP2DQASkdivpDsbwnlnfJ8K5a3iJDWwK+bxO6D9CWKO0o40AVR550KKS5qJYC8sLGC0wAKAAIAggDIoAoQ5ShSjIxdkMAZTYBIE9ElVgqiHgsqjmx5sTIKWhJbFxlrM9NGYhYiYzuANgyRjeN0ePu85XP133+okJPvixB+F6A1tfWWudN5+3vvHzpexfYrB7e28J4v0+ZMUCICyOvCkeMxtIs7g6G+Mj1V1ABIJOAguKJM2dhS4ftzW3MtRpwVbRRLS7M4LkXb8GkCRwTbh/s4c7eDrI0hYrg0RMn8cTJkxgfHGLc7SEhhfpoA/KiKJ2gOTcDNJt4/u593B0cSWWSwhHuetAtUeoGEQf1tQXfsrXHg4NxQd4m7eCzUHZTET0tTDF205rWm6E2AazHZLJFVT0kEhBLi+LgVT5WNIm04Erg02HJtEuorn/m/uaFb+hdnL+wMGvywy78KIclgiLaFlgFvb19dE4s450XL+Aj117GzVEXadbCnf09PLpxEllq0T3so51atNoZ9g/7WFtbwGg0RFACWYvHzp7Fx65fgwPQV4//3wsv4dy3fD0aK4vI7+0jIUTxqUDWMBgd9LB75z5WHjlLX3/honlld/vRvWL03TbR++32iaPRaHe/Flav7UAbo0VhBIATRT/40E+TxJ8+c8YyG46BHjHGm5khIYr2OMEW0XOEaDGIXdG6G6+R/Rww8ezKsXP3+P9rEocCMNZgIpsMM1QU4zzHOC+Qpim8dxpigsgIpCUIWqkYkswoBSPBi7QDh2KOnRvoxgawuXlFH8LbfdWGrXSeeabCv/7XR6S0Q0QjVYVCo7+ZYof+mAFNjCC+Hi4EggaFBseke4bDtt/acZ/jIQJwVV5jUdg8FjUM9Hg83DBYdQwRQkcIIgwRhipDSwvJLJRsRp5LqEmhVGlqEogB1FZBM2hoGcMdJZqDoCKiAKIWQzMBG2YikfgUWDbx6hWRmMeu9P9n70+bJMmu7EDw3PueqpqZ7/sSHuGxZcaSGbkikdhRqAKqUNuQRYLkNGfYnJHhIjIz/A0F/IL+NtLSI9IyPSMjIz0iI012V7NIVhG1YE0AmYlcYvdY3MP33XZd3rt3Pjw1c49AoLBUsYWNsiuiEeZmaqpqpmpm55137jnMRACrKDxDxQIeKgURFwoUhignkYwtpQYmU+JM4HIukoJiOO6QNzb21h7LUhSJ6eueASDWnwTPXwTwF78siP7ZjcrPqVvXr9uhW7de+fJLb33x5cWFK2n9eGhrbQuGtZypIcAQcgF4bAh2YhTvfHgbG2kdsBbOOyyMT+DK4gJWPryLz7zyIo4PW+h2UkxPjuLJkz28euMS6pnD1PwMvrdyF4UKrHcYJoPPX7+GccM43N6H76SoJFQGFRFECRwnGJoYx1Fe4L1Hq2jCuYKSI8d2jQ2vK3MHJAKysAR4DyVyGhxPcgEZQYcUHCQcR4NfmkENAPSgBoVfIRnHigLLWrbYyWH54Ki2paEVqXaVqgTuggQ0pMyizhXHYpP7a536yx9vbp0/f/XFSjI6Qs1WN/zwlVZvBsHSrrm7j4tXLuITL1zC2ns/gEJw0Gng4e4ezo+OYPn8AvY2dzFcjVE4QbPVQeE8xibHkLBBQz2qUYxOkSOJItw93sH7T7bwueWzaOzXoZ0ubBlQwQQYKHYeb2BydopeP7uE25sXhv/s8coVreC3xWi9PTf3LezsdJ8JG1GsArgYQBazOQJhb3hk+Oz1q1cjKEgI5JwrwVtw//DeA0xlTHNw6zClHCPEOONEHM7UB4OqgKqAwCAKASBcehsTB1DO1NMsoATuAhXR46OGxFGcQuWAQMcAXATAxcrqlGuqlIuw9wUbI+K9J1zOCStvEvBuPzL5P8eL8s+//nVP3/hG6sUfq2raA8d8+n0E9/24e1p0AsBEAmjqoY3IczP76WEy+lPuK5X86w47p3W+1xnIQ47JTGaQ5xYiJvPKUOVcawQoFUomicVCNIa3uWdSA7VKqLBhpyIojaqDrIYJgFEnIIYQMxOIlKEqSmBiYSZRgWOFg5ADSSGKjJzPSE0GohTWpFJIZrwp8sg50/WeTKzBti5INaLnej2flmv8IuD5TSqf+9NY6J/pQf7FL37Rfu8HfzHz9tDM737y8sWvjhkaWl/fou5xE8MVhncueKArwccRJuansdZo4wePHiAjgpBB7jK8eOYMfDvFwuQYdrYO0Gi0cf7cLNY39nDpwhmsbe6hiGPU5iawvr8LG0XwRY5ri+fxxvIyXKOJ1t4BLBTqg980RxwkYUM10FANdza39P7RDqWG846XTW/MujIdeJEUlsQC6pwLDi8FPJgEVBWiQolYWmxk8HMzqAGAHtSg8CvqB73uCTCKBciUCDkiARlPpKQhQldBLExdEbatAnjUdnjw7uNHL759/vzC9NhITPtHyNMuIijEe1hrYb2gvruHmaU5fOLCeXz39m08yVowUYxba49x7vU3cG9tExOJxdbOAWYnx3FUb+Pc2Vl8cGsVY3MTmKpU8MaLV/EXNz9AYSLABF/oa0tnMLIwjePH62BRkA+AtVJhNFtdbD1Yw/zVS/j81Su8srs79qjofNZHI49Gu3K/getPgFv5U2/DMrCz0yLUxvzjRw+O/9W/+r9uGza7EGVAa1BY5z1BldiYAJi9qLE26CmKPKQ3ck9ygJBeiCA/IA6BHwFAa4mp+wCaUGqhQUSqQsQAEZOKgpigospkvHdFd3Nre4+i5IlX3SOWHGAgU6rUEoLzFHr/C4hMEtDAclHQKrohMCZ4XvN/xmErAvjCMHtiaC+90RguGzdLB46eN3cJ30REoZJDNW+ZyP81+wNOsay3JLxfl4GkvNc5LVlpgqYEVRrSIS85CWJHEHZBbwIGawzVmigNgbRiQFZIORhLswiJMkjJWAVEVVQss4iIqLIHqQeRU1IH1cIoChLNSTkjMrnP8txYKlhjRyk8GRXmoHt+Kqq7p3u+/lc5arx5AoYv5/QLgGj8nOmEBEDT27enJrr8lV9/66UvL40MXz7e2pHd1S1UbXDH8GVoTtcBlalx5JUKvvvjj7GdtyA2QlrkePXcecResbe9jcWRMVgCLp2fw8bWPmZmxrGxe4zRyXFkkcX3b9+BI8CqYIgMPnX5BUxGEfb3DuDTFLWIoYUPzhteITZGZWIMLQDvPHyIQxRIKe56E60XjG0VbYHEhdx3EiJyIPIg9iDyRCTokpAhHSPWOg0SCQc1ANCDGtSvCvtMT9/uxfp6OiiDVQIL7QU0VD7W1jaRgou05mgrYb61Ut+/9N7q6sSXL56PkuEhyrrd/jQ7iSJWIDtu4nhrB5eWl/DGxUtYv/k+KCJ0igKP93bx+plFcLuLVqODWq2Co3obO3tHWFqchFqLlZ19TCzMoBYlaLkCFEV43D7EX965j9956QrswSFcs42EghZaPVBJCPsbuxibncTlmSn9xPK5aPv2h0vC7VcqlaGXaGzjoF5H/tR74j3VVKmIYuwcHLb+7b/+19uArgKsgE4AXAmNQv33rheZ7YI0QIJJNLgEYXqa6ZVnwJmeJH/05APUA7bmZNFTfs7kAc0BHHFSe2yjaMUVfi+OTA4F4lhZU2E1SqryFLBZ7QOinBBfp8tlQ1gcv67Vz03o8MKC4s+B2dlbev36dQWAr3/96/qTTn+/oB2XPn+iX0J0PJhZe7e//vWv0z/8+tdtHMc1NnZYICGFBgRmcxLjzQyFQksXk+BkEgYmxARrTFyFVi9cv96+efPmz2T/vv71r9OtW7dod/c6XbmyRWtra9ztdinLMgKATqfDzjnK82FO45Z1eW7Ee1YRUtVyqRBUybs8MpRXXSYjxJiAYEZE55V1xgDDEI0hIBME786reibySvAmXD8exI5AHmQEgOewniOinBiFArlRm7GlXKEZicnzgorhyBeu4jyniTDXxdpYluNY+ucfwNMOGz2w3GOiv4gyuDPMWBTF02eur58unThuXaenpSBPNSD+1Ovki8vLlSerqy99ef7iP339wvL1pCj04eN1RpHBViOID+fRKwHVGKPzs7h9cIQfrj1ETgTnBZYI8+NTiLIc48PDcEUOEKPZ7GJ0uAYixuTkOPLIoqMej7a3EJXs84szS3h9eRndw2Mcbx3ACqCl9zNbg8IrbLUCMzKMOweHuHu4iw5IMjHtwtIOKY4Nc+bABOfYAULMLliJG0/MnrLcExkBSOu9gKbT0emDGtQAQA9qUP+rd+IIdna4DKAgbAUWmkVIRAjMHtoJTFsvgIK58IWrZ0nlbivrnPtgbfXKa4sLtenxEZsd1+HyvGRbg6SCCof9JzuYWJjFr924ju/fv4s9l4GZ8XBrE4sjY5iJLYaGh7C+fYCxsRqYGVt7xyBrcGFxGkciuLS4hA9XH6LwAjWEdx7fx6sXzmJucRb791dhvA9a2FzAMUHSArur2zg/PkZfuPIiHu/vx+8f7V6r+OLt3FQ/AOoNPG+av4DaOOry2OQeA6uiKFRlwoCqot46L2SYPRNl3kvKhrsg6hIoZUKuhEIYjp0KCGXjFwoH9SzwZMgHg+swpa+qDIEBq4VS5EkrIKoQoQrVKgQJE5nwBOkS8aF42RCVx2T42HnvYjaUqVIVQEqkhjrKXFNrj8WYAHyW0pTXvSfU67yyl1vAR8AfxbjV5VMDgRxAAcB94xvfkFPA/5fXTT/nWacdCsrbBkCMWm0ceX7B++KKQidDUiOfsPilnoPBZRJhSIxjBgrnWCWvthvHi965c7cOnmRE1Pwpx35q4AJbNpdW/uIvUC1v95ou5dT6pwc3z3M1MQASwIwCPAOmBRAvQDEHQ2PldimuVD2xSQWasiIHUQ4hiMAzQVTUK6ljGEekTkAeCgel3BhkqsgFmoM0Z0RFSCEn1yUV02bh6MR1Y/V0YMp1BJfGd3+Oc3YKPC+fHoTdejZzqGdrV9Wfl4Xe2t29cTEZ/92vvHLj6nQcj+w/XkVj9xA1S3DOh3PtgdwQKjMTyKoJ/vJH72PPp9Aohi9yvHr+MsathaQpijTHUC0BHDBSq2B1fQ+TM2NYXd/C6OIsPnqyCmECi0cNjM9fewkzcYKDx+vw3RSxJYjz4TuLCIgs4tEhdJjx/QcPsetS5GyKnE3LEx8JSVpAkFgLwKr3XkDeg9iB2FGWe5ARIhZmI5Om5Q/ZaKm1H9SgBgB6UIP6FWKiNSQllD+XBjhgVhgTNKHB1/h01LVkMGlHko1hLu7cPdxdvbu7NzazND8ajdTQ2UmpYrlUlBISA2StNo639rB0dhGfvXId/+ajHyGJE7TSHAedNiYrM8iog7NL83j4eB3GMM4sTGF7r47jwzrqTnB16QwebG2gURSgKMZu3sWffXwb//jtN5FMjKGze4AKARQHbFStRDjeO8L++ibmzp+jL1y5gvXvHZ3xaeeGVHl2eAm7wZmqrHWjNMQCwPlcujn8IUMSUrTF6wjgYiZjAGjuCwdQCtUOnHaIqAPDHRNAdS5EBQOehJyHLwAqQOQA76wn7wC1FgpYLlPLDKAWqpGHVjiyFahWRaXKyhWGWgZI2BRCRdsYPialumXuehEtgkCYkQQunJiFiJWZg/tC0KXTRFqNFhamqumUTnvJlypxZZksTxKZxBijUcwOIoWIKximUGLPhh1AhYjm4lwG0syL5EXhnBp15EXgAEdOyXuhKFbvvXgxPgKQqxJTEcEklSSiihNfNcoJiVinYuA9qSo7kTiOo/HGcf3i8MjIJyJrpkovg9IEmaFeoOqhZdAFE5eJj4okinh6/kx1ZHzyNe9dk9jci2LbYq6QNRyJiDEmhjGkRVEoQymJrXHiK058DbBDhrQGUKwqTAQhgmciKbyXmK1yRERsyRKRlJ8HFVERB1U1IhpneT6kqmOkOuG9jAIYVi+JsYaY2W9tb2WNVqfFbNtC3DZK0HDW1AuESR1DCzVaKMiJimdDjkhzIc4BnxNpTmxzhikAV9QAl9uK40L7590Yo8sAVldifa63M55lok/Y5+UiAOYl72n1NAN9Oaf+vM3lUyErJwD6r5IFmVfm5qZ0Z+dzn7t+4ytXZmYn8uNj2nq8AcuhSdR5wESMwgNaTTCyMI3vr23go70N+DKwKGaDi3MzaO8cgdIMb16/hO//8CNcu3wOj9e28crLL+DDB09w49VrWDk8wqOdbURJBJeleHF6Ca+ePYvuwTGOtg9gqTS0AYLXugDRcBXx2Age1Ou4ubupKbOmHLULpgMlND3IGxh2DgCcemIBkY8dOzJFYKGJJSxGiEhhrQAV+c9YNjWoQQ0A9KAG9YuDZ5xqLItKVw4rEKEJZjkCgGAQgD6IHmbvXbeRCj85RnHnRw8fnnlhcnxkYmyE0nob4n0/GY6ZwN5jf2Mby7PT+PxL1/HugxWsd45hbYLbq6uYrA2BnODhxg6mpsbgC4etnUPUhitIPTA3kuDR+hZuXL6Md+7egXMexhh8uLmGG1vncG1uGp2jJopuhsj0GvgU1gh217YxOj2OGwvz+OKLL4788e1by4jyq+3O5BZwuHXCMkba5sIDeW6V2gY4UlEl2GPDLgHYCIQYRgwbB2guopkhkwpJCtJUCDlZdtZ7B5BzBh5kHIhc8FkjcUwCIjEKZJCgfwY4jiNWVcsqVkUiGBOTIoZqxDAWrJahYGLxoMIy50Sk1lomYkMirKpUBalrkZokli2T9q3LXKfD1vrqf/Xf/Ffz5xbOvZT74pPO66sqdIYZw4bJMgEBEqojIscEp2AHIGemLkE7XqkDICVGqkDBwWBEKWh+hUgFZJyoeiKoV2UFEle4EQVGoTqqIkOqmoj3RkXAROq9N6JIQBgmYKRWG4q8c8TEZZOmnly2TP2mS2ZGq5Xi//Kv/hX+T//8nyVs7UuqOk3Mu0SUEbEl1aoqIiIiAkTDsYGZrTIS8b4GcIWZIgJM0KOzlMMRz6TeGhOs4ZiU2JSfIVFRVQpSbBIR40SsKiICrEAtKZGKB5ORoiiKf/kv/0X63W99xySj48id857IG6bgts4QGHJeJWdCDoEzpC6orjU3oikppwRk3mmmNsutJC616g13hSgWInMycHpu8+DPrtUo0uWiIP8MK718Sg6yXK738zYPfnLy8tDezsonvzC9/MXPvHDpWuIKs7G2iaLZQa1qQEqgOHheF5HB2Nw0DkTxl/fvoaEOwhbOF7ixfBG28BivxmDLuHN/FRfOLYAIGBqu4qjZRlc86nmB91dWIEygIscQWXzxpZcwX02w9WgVebuN0YQB70OAERvAGMRjw8giix/evYfNvIXUVlzO5lAMbwHcAqkAyqWRjwdBIsQepI5IfJfYD7PxzEbq3FCwVWwZDe4nA/A8qAGAHtSgflVA9GlXBurLOba8Ys4KO4eJEmHWT4NoQFPmokiiA5sWt+8f7790//B48bML83E83KTsoI6ojMv1IjBESI9aaO3u4+KFZXzmxav41z9+BwJFK+/i4e4OPn/9Gpr7B2h2cogrMDJWRaPZRTstEBUOY0kMrQ5jsjaE7WYdNq6goTm+decOlt76BEZmp9Da2AFraf0rAmsUWauNnQdPsPzyFXzh6gu0urs780H94IuI4s3JycnG4eFh6cgRK6LDAl10HWvDkjLAKcMlIHBwawaTKokP4TIE68R4573JQVRYkHPkHEpWCoCExqLCIyGPDBJYfJIM0ASgjEoaLC+UoNAoUoKoei9krbOq1jk1hkr9tTHU+6pSBRPIKrySahE01VTqlQ8UlRHBSqxYbrMbGTHtvb2RhIdemJmf/0K71fwCsZkDqGaIDDOTZWiw1CPV4AwSGiMBIaLS5lsUREKl2R5UtQSjGuypAcOsfe0DEwhETMSlFwkLwm0E9wxAlMoGTCKAnffGFQ6KvHQuKZMIoWWMug2cu4S/oYozZ84giixBMaKEqqguAeHwScGlXrnM7yBV9YAqSXAaJACsqhDvCRwi1akvZFcpE3t6rylsqYwUJyCECClIQhMcIQBqaGiI06GhYUmzzDKbYLShKAicQTSDIeZwsJ4UjokKEspFNWfmMAATzUi1S4zUAynHNmNFnsEVxiSe2yrGRmLtsWyVsh3E8S8I2KrB6q5sIOypDpbK26s94PwTz3v3rwLQ9CbetAfND89eiMe+9puvvvr28ugwtzY3cbCxgyQ2CLkpCkNALoRkahTR9Dj+w617uHe8CzEGThUjUQXzI+PoHrdQEcVwNUZiI3Q6GbY2DnD58hLqWY4bL1/F7d09PDncRRxXUGQdXJlZxCcuLiM7PkZ9Zx8RSdBbqwISApnMcAVmZAiP6g28t76KFCQpqFMQbSqwRqQdA1IouPSjVIAEznky3hNbP0QsLZCCmgrqJb0aBW4NAPSgBgB6UIP6FQXSJZheAbCsYK8HpTc0AIwAaKo+xURnbFtRUnu01209fH/tybmX5+bmx+amOGu0Ic7BMCBFmG4nlfCDOTaGT195AT+8v4LV9iFsVMHqzg7mxidQ84qF0RrarSaKQpHnDufPzWF16xCGLJ48XscrFy6hdecmOkUOMgYrxzt4d3UNv3bhPFpHx8ibbcQGIAewEqoJ43j7ANPze1g6cwa/9tLV8e3v/uDT293u2lClWvdjYw/q9ZlO0AEkDkWri8IyW/Y5fMdDIqvWkCuMGmWBtd4rwxoCvML3mErAoSAomcBQKQMkgBioUYA8okJCCgR5lAA0Cu8paRyVXsNiVNVA1VhVAygbowxYglWCgiwsQMplpguILPeAc5dIYyJlZg0AqqpAG0W3G+VdN57m3etZlt54553vLzWarVocJcwcjAANA9aeNOwREWwUoQTTASwSwMZAywRGopDSSD1EzQamJ63oeVszA6IlGpXgFc7cjxekEgRbY0umGYisLdMZe/slUGkNqCpQUURxhGazgWajAQm6faiqAcGIIumBa/X+pJtTAnAK3uEK5x2cSPDq9iEc58TLOwwDxIsCShxaFeFVynYABlTgvQ+R8wDEezjvlYggPoTqOOfx2c98WqYmJlEUuZKxsUITAsVsjFVVFhARqwpEDMg51QykBcjkxFJYaEaqqSi6ZDRlLzlHccGAo07qyZywz+ixz7dOyyve1Z/Poi6A6NXLeMYq+0QLvfzUc2L9q8AzAMj4xmJy7D/3669cf+PG4vyMtpu0ef8JkXOwNQN4hhpFIUDOFuMLM3jQaOK7j+4jJUJQRgt+7ROfAOptZN0U587Mo15votNKceHsDCpJDA9gr96CG2ng40cPQapQX2CYLL708ssYZ4PtjS34VheVhEEakkC9AI4Iw2PD0GoF7969h+2irRlHeUa86UGPBLIJsmlQ74fAFCJSS2Uzcd95g2WU29JgEwbLzCeJr4Ma1ABAD2pQv4rAucdCXw6PbXnFnOhhSHw4WTcAPgWAovBp5mg7tvbmzb2Ncx9vLk1+cXnJjM6M09HqNqoJgziwc1HMaO0fo769i+WrL+BLr7yC/9f3vglRQQ7F491dfO7aVezu7KKihMgC1UoFj1d3kAzFMFGECwszaHhgcXIad7c34NQiY+C7D1dwcWYaC3NTOOh0QXmBmAkQhS39l7dWntD45DheP7dY2Tp44fwf3bz5ay7KWwKTY2zvSb0+3sVWLJirpUhTyYuoQOQ7kCQm8RHYWqhEgLGIJAr5FsT9BFNVBoIg11jAO6glUqdOwteKEwsW2JK1Kn3OSoNjgnhCICs5sKHGqAoDJhjTQhgFFBZwULVKsBZw3gIQjcKvuNYAuF762a2T6fZWbuOWkymIXrbGns2KotLqtKlWUTAbEBEMEWxhwpYQyGzrCvRCZDgkVQZXDGIwBQbZk4NAS8BL/UWZwD1GnJ4CzWSN6f99Qun5/pXonCsDZsICLyUaU2jvPoT1vPOlG4cvL1GFE6+iChGF9556bHGwwtN+NLiTAIDJcPkJoNCgqD2wrgCDxCsECultA4A6BwLgvIeE6QCoKEQ8hX0pCvFw3sGLsKgYZjYq3oaZA7FQtcwwBLAXEBmoCLwx5KDIiDUnMTmpZiTajQxSEc3Y2twUvnCR88Yk3phImA/VmOQU+/wz0wb1OUwygDfDOPry85+0+ixr/dOZVboyNTXUPNh+5Yvzl3/7S9evnqmJN+uP1rVz3ECtytACIKMgY1AIY+TMDPJKBX/y/gfYcl14DqEpU5VhNI+aGBHBxOgQnqzvYWJ8CMtnZ3Hr/mNcOn8Gj7b2ceHKeXy4sYHNo31EcQyfZ7hx5iLeunQR3YNDHGzuIeYwgPKl77NThR2toDo+ivv1Jj7a2kAH8F1ww7N5CIOHEDogktwrw/SvUvJE7IlEiEi6xAJqSzkDFbTPxpR++wP986AwiPIe1KB+hV05el/2AMrpx97Sd04YCim1AIjYtRyOCo5uHam/+cHmZr2h6qoT40qVBIWXcp6zZBUZONraQ3p4hDfOn8WLU4soXAZrI2weHmH94Ai2VsPw2DDSwsHGBtOTI5gcG8H+/iFQFIh8gdmREYwnFYh6FGyx7zr43oOH0LERDM1MAVEMmADmxCusIXTrHazeeoRRYvriS1eS1xeXXk866W9WVT9R9dX5yclmDESKnZ0c9fEuhqgJHWnAo1l4bRVe2s5Ih8inIJ+DyBkLNRZkjBpj1BqjkTEaQzU2RhPHUjHMNcNShXJNDddUuKpCNajUoFKFSsUaU1HhiionqiYxhhNrNIbjSFUjNWyNMQxrycAq4EOeNUU+IvIAiSPyRCxdop6FHnpOCXmes3NUAWjaOb/IxOOxjdhQSOpQ9aXVd8muUjkWCP7TgZFmArEhYksgIsNM3FuIyBpLxlgiMkTE1He2JiIiLhciYiYqw2ZKLA1rLAyd/B30zVwC9x6zzacu1BP1ERtGFFsYy4giiyiKYIwFsyUbRWSjiKgcIPS2ix4wV8CwgbEWRAwyDCYK9xkT2G+iMr+FIIQA3q0BODiBOAmgn5khZVLlaWdCphDNTszwXqhvXcjgkODtjYoYEWdYgz80iLwhckSci9NUVLsk2mWjXWNsyiZKjfN5ZovCdCPH3BSiI7XWivn5tM/PWirq024r7wbwvRKH5bQUpPd377HAbOtPsayLpdG4dHlo+nO/9crLn5mJ47Hmzi721rapkpyYmagCmQd4uIba7BS+//gJPtpdh2eGU0HVxHjtxSugIoeBot5oYX52HM1mG9t7h7hwfhGZFwyNjyAaGcHK9hbYMNQVGCWLz1+9gqo47K9vQtMMzBosL40iLwTeGFTGhpHFFu89WdetvKneRl3H0ZYXrBDshiVuIeciPv1eEQQoev7PJ8C514Tdmw34zzwBdFCDGgDoQQ3qbzShMArNLz3w3LOxQ/uUiiP1ecV220pPPNvbH+1srHy8tdvRWo1G5iY0E4AsB7Ahiig2cO0Ux1vbGGPG5196GUNkAfFwJLi59gTHaY61/SMMjQ1ha+8AzVYX6+v7WF6cRdpJ0T1uYZgMJodHAfEhrSyK8dH2E3zwZBu1qUmgUoGAEMWmr5WNDXCwtYfd1XXMVCr8+WsvjixEQzeiNP29yHVuiMgE0A70K1YL7J3LMORTJL4DW+mAbRfGpAWbPCLOLXFOngo4+H5ON5R9uQBqDNQAajzUGAMDp9ZatQBsqdCwgWlWthalLlgZoXOPgrzWAIB6IgG8z0gcPBWepPAiuSMpiE2B0hgCp72Wl9uM5Tbn+agpyI8AWFDxE8aYhEBkmEGljEHEl5KFkHoYbOIC3JMQ8QHxPiQiakib7Gl8FYCohL97QyYN3szoRXH39Ca9RaQ3o9Hjy8u0xRN2uCcZIaKwfyIonUpmLFle1VLLWlrbBXkJ90NXDDO4THyknqQEFEQZ1Au8KeUlqievTaTU8St8uU9xDkVeQJyHl7CE5zh47wPYL+Pb0QvLCbrrknEnRfk+E8QAMExqQWQEwmFQAgWRs8xZRCZlRZeN7bKxqZc05cIVzNYFt5Xg9NADz6u/9MD5WUD97gmDfeun6KVP2OefANFfBOzm7u7UaEFf/cr1l798bWZ2LD8+Mqu3HsGyh7UI2gkDOCU4YzGyNIv1NMc379xEGwIp7QrPTM9iYXQU7XoD6hxqSYzDejMMWgC0ujn2Gi2MTU/h2x/exG79CMYwSASfOH8JL51ZQH17B0dbe0ii8tqSMOGWi8IMVVGZHsfDozp+sPYQbSJJKTr0hu6p1TVSf0hEmbXwBAg8+TKe3YHZE5GnlATUPv1d2evI1J8zZGZQgxoA6EEN6n+dzPPzpnbNaTZFTkB0gNFEJOAsTzk6Til+sI/ig2/fv7+/k2VudHYa0dAQcncCwlQVrB57GztwrRbeOH8ON86ch3MZoijGXruBg6yD+XNncNDo4PKFZYxNjGB+dgKbWwcYq1awOD0O7aQ4NzGJhYkpOJ/DKaENj+/cu4tD7zC+MA1hC9/DaKIwlmC84MntNUiziZcWF/jLr9yYnlTzRs27X6vkdG10tF0pvwMEeNdhayvH0VCOKMth4hy5yVC4jNhkRD4HcUbEORHnIHKgyBlE3oB8CD4hAcgbkMBDACuA7bFRAkA8UVh82XQI8s6TtwRPFkIQRyQOXgovnJPnnFhTiEmd14xFc3JchjgEEK0q5Jxj5Dkjz9m5rhXSIZCZATBk2ZoAKglRnARfZScBGPoeMA1yCNEAicWVgLJMUmQOs9geitC2GUBpCUUDoywB4HJolOxLQahMaLQoJR6nQlJ6Ds0nzhulWlwlaJ/1pJkvAP4gKSEO+mQpTzohjEBYS56Tgqe0oZIEZoYyQxTl8QCMwBj35CE9AGyIwna0PFZVhCbEXr+q9JsJe880vajxcsBQBr+ohIGDculrrQBLqZ4hZpbAa2pRkC+EC8+cEZvUe029aMrW5rmJitTmjjvWMxulnub9dN067dP8c7PQ8tzvhF4qYc9P+la1BNjv/jRrNkpnL0zF3fxTv37x2hffPn/+SlJkduP+Y2StFiyF2GwNHadw1qI2NwE/XMN/+OgjbGZNqLHIxOHaufO4fu4sfviDH2FubBRzk+MoXIHF+SmYyGBkZBhkLYYnxtEWwf3NdRgbwxcF5pIhfPm11zBKhP0nWyBXAKplX0bZuBDZ0IBMBt9/+BhbRVu7ZLtd0JYD7pPSjhftgMQ5Tz70L3gPIkfOOyrIg3JPZAILzc/KN2LFT4+VH9SgBgB6UIP6FQPTT7PQ1oYfhvDj0P/RDMmE7Iwp0i5HmxJFP755tP3g3Scbda3VdGJhWj0IvtSWujyE9aWNNg7Wt1FzvmzuqaDIOwADd9bXsNtqoQBhc/8Qu7vHaHe6mJsdQ6PRwu7OHiZqFdQUeOnsMkYrVRSugEYJtvMWvnv/AezEMKqTI8h9mFonExjMKCG4ThcPbj6gmjj69OUL0dvnz89UivxzIz7/dKXLS1NTU5VTmnAPrBdPgWgyec4mL9hkRJIRmxTEqfecei+pF0m9xJn3FBai3BPl3lLuI8m9l9wTFUSce+K89IgunCVHxAURFUSUO0cFiAuQL0gkJ5IsIskiljRmzoglIyMZscnYZHnOhU/TTHsAWnWCZgKINpWKjQy5IZNEkwwkzCEam5TgigLW2MDIisK54LjnfGCUvQhEgk5aiXEa04JCPPkJsFVIoKODQpSCcYiUALmvhS5htpaSDToFWvmUjjockwTfZ2UY4gDcTz2nB1JFCaDec7WMSUfJSJesNYK5s+LpGJTguFGCejaw5eCCe7pwDvvuNUwyhePqW4n0jxGllhzlMVC5lEJ3KvXvRCKqAUOWShJhNSBlZpAICUAOJIUXzbzXjI1khfM558aNRnHBHeMD+3ys/dju09WP4u6B6DfpZzDPz9dFX8dTwSon4Pkp0H26zOfGzo0f7a69/Mrowu//5o3rL8/Ftrb9cJWO1vdQSbh0TwnnJXMKO1bD6OIc3l3fwI+3V+GZ4RWYqNawMDaB/Y0t/MYn30C72cHGxh6qUYy1jR2YyOKw0UI9zZEbg3fu3MFx1gHEwyrw2asv49LUOI42t9HcO0JsQ1qpUBgU5oVgeHIMlfEx3D84xHubq+gQa0r2yFleBfSxiB5bSzkAb0EezrsoIhc+m+F/YvZE/DR43jKK9YqU7huDGtQAQA9qUL/aqYTP3l4JLPRWXw8tT01PltUh8injOBN+cAz50Xce3nt0b/+wSMZGEQ9VkKeuP40PAiqxQWv/CK39PVwYG8Xbl14EqcJai5bLsbq3h/mzi1A2WD43j3qjg2a7i+mpUYyN1JB1uvCdDtKjY1xZXELFGjgvKAzw463HePfRGkbnp2CHqxAOwKfHnScJ43hrH+v3HmE6tvjStSvJldHpC1GWfWbY0mdsy00Dl6Pyu6AECKMecexgug5sC+QuTwqTkTNpkB2bFGy6INNFbLog6do43GfZdCGmCzEpPGeOOAWZFMQZghSkcM4X1lMRRSVojshRFBdEkhFx7hzlxJwRc+7Y5M7YjIzNiG1eOMnzgh0VzhGz9JzlvC94z3uGc6ZR5BGTrYr6mle1ZMovOxMAIxNgTUiPDA4UHkVRwDkXGOhSzsF9q40AFPsglKgMIidwycRqyT73LqegOT6xpOPSKq73WI9Z7kk4pGS7uRflTT33i3JfPWs78QhedOjLPaDl5Voyy1TahfRZ7ZOXEXTKwUSu/+XfZ517nLoGkGyIw/GU/4qETtBw/0mTIkrrvRMmPOg0AAgzCVRViYNA5zTbzX1li1ornoiLxNicjeRsorzGtrA2KtrtrjBbMSYSY4wwsy6VQvyfU//8syQFJ4+Vse8nIPrd08D5WfDM1zFTPWrvXr8Yjfzm775x4wtLtepcY3sb24/WEScKNsGahQ1DmOHiCGOL89jopvizW0G64cHw4nBxbhHFcQPDlrHxZBvVxOLK5XPYO6pj6cwsjDVAZDG9OIsiNni4twnLBk48LozN4LNXLkOaLWw9XAc7378WyDCcAIgrGJqewpEqvvPgAXZ8isxERW543QkeENs9EHe8J+89CZH3nsg5zwU5VxBxQVw4StkTtfVU2FTw/vurZ/kGNagBgB7UoH7FXDmeAdGrWv66n+j7iJ4G0kSSmSJte932xrz3qHN867srK0euEvnxhWmQNRDnIS6kyDED3UYbx9t7iIscv37jOi6OTqPIUyRRBffW13HnyQZstYonOwdYWJjGULWC9fU9+NwjT3NMDQ1jqlLBfG0EsyOjKKSAA9Bmj2+v3MdWmmFkYQoZU0j68AqfB41sZBTr956gvr1DL0xP8Vdff6W2GA+9XCm6v1mLzCcmKgdzCNYZ5ffBLcFOVLLwxoNNkZHLmX1KbDIy2o1ZumDpwtsu2HbJm25EJiVvUpBPIwr/g0weERdUssuOXAGKHcXsHLNDj91iXzimwjEVURzWL5zP6dmFfUHsi+AGwALqaojHPsaY9wxVVvUmc86oKoFVDUHFC7IsQ1FkyLMUeZ5CxcO7AuI9vPMococszeCyHFmaosgLqBeId/C+CO4S3oWYbVXAeYh3QSssHuIcxEnQTrugEfY+PFaUfzsXrOOCfrpksUWCFENOAP1pfTTTiVhCT2mrWU8wfU+rTcRPI5negECk3I+Hdy7omMv7tPSzhhf48jhFwu08z5EXBXx5LbvCIU1TZGmKPMuQ5zk6aYo0y5CFRbMsVw0svpakuBAgpOqh6kUhwQMk2NiREfEiLmYJ57YwRV4ULjPWdU3mjYk8sxWiIy1ZewWe48/8VOz2uz933PZPunIAzwDz58ajX5+ZqVGtuDTq/Fd+77XXvvra4uKCNBvR+p1HhDwjQ4DPHIgVvhDkhjE8NwU3XMO//fGP8aSUbnhxODc9i9mhIZydmoCmHmfnphCxwY8+uIPJyTHce7QJT4RW4bDTauN7Nz8OrLZ6jJLFl166gaXhYew+2kB62ERkGEXuwkAKgFNgeGoMdmwYH6xv4sPtJ0iJfEfRUeI1Ba/mog0iX5SuOeJAHvCOyBeBeTZ99rl1MjMXvivXB+4bg8LAxm5Qg/pbaml36j6jYH8CngNV9nQ6IbPzVdPMnX2QaefjdzdXL7++c3b41amJ4aGZcXQPjsFG4VwAQsYoDjb2kYwMY/rsGXzh2nU8eefbyHwBT8DdzXWce/11bO0fgaiDVqOJq5fP4uHaNpbPzGJtcx9DozUc7x3gxfkzaKcpjrttEBtsF238x5t38bVPvIrR+SnU17YxFDM4L62rDKDdHHffvYsbn6/Q6+eWsH3cnPk3H7z7lks79ZFKTVCZ+OFRerQHoOi/B9Z6SNcNo4oWSEmF08L7iiqnKlzOTzNUuVDlvuMCDAgeMQxyeBTB/5mikhMDPKGwjAjkXEERQIhOzo0DNGZ2xFwQsQOxJzZPBcURsRCnwl3r6ZQedkSHySRCWWEdwB3vfC4KWVhcpOHhYRjD5EvdsPb0zaU0IxC3QerBFFIljbHBxaLUJRDCfc+KbVXLBrpSK90LREEJfoOGOkg2AgOMvptFkDxLKTMJ++gdD7jHUJea6lL3TH1dSXhMqQTRIHiRMrI5uMIEPTVKaUpgmHsa5t4LIVAYLJTWdeH52h8EBFAdni/ehWeU7h4QBbg8IlUUeaFxEktRFEKAB9STIR+p8SJwhtkD6gGSkEFD3gPOeXYRjFOGIyZHJvPUNgImDdIN04/t/mv2PPyUehNYqQcfxBWglCM8101iGcuJTQ8XqdP80leuvvHlt86fvRZnqVldeYzuUQPVIYaWn31hi8wR4okRjC7O4j/cuY+PDwIgduKRsMG1M2eBZgs7u0eYHRvC1s4usqzAjWsXcevuKj7zqdfw0cM1zJ5dwIP9Pew26ojYAOLx+tkL+PQLl9DY2sHu4y1UYgaxQjOFkiIrBNHIEKrTY9hod/Gtlfs4Jq+ZqWYO2Myde0yx3baK1Dmv1kYGANkI4hw5EBXE7HraZ2YTbGyect6IBsB5UAMAPahB/S1NJ5QTP65VxdYCMFNa2gXkIBDhPhNNpF1jcpHiOJL47pbPPvzzO3eWz7z1ZnVkfoobhw1YdWQSgzx1QRuqgqOtPdTGR/Hq2SXcXD+P7208RBTF2O80cGv9CV6+eA55o46KjfBkcx+xsTg6bKIaR2CnmBmuoJMVuDi7gI83VpF7DzYGt4628J2Vcfz6C+eRN1O4ehOGta/PTaqMbruDhx+s4IW3XqLPv3iJ9xvN2T97dO+rVOTk2SCAaHsIjBVAAexZwaT3Le3QMIZUVRgqzKRUVSbkjrWipCImSxNOEmVVPd1bhvipYcoJyFY4hQNFRISoXD9HaWVBvmB2ROyqbFzGuQc5CUxzrT+IoY6R4MzQlB4rqcqaZhAV14Vif3RktFE1yF9/9UYFgVpTlEYYfYmDnpIglO4VfdkGCNqfiAgAVnsbITrRE5dAspceGFaS0mcZ/YCUYJHHfS0znboQBaFhz+AE0IcmxqDL1tJ7WqQMbAH1WWzV0lG73Bgxh8ZI6uU1nhyrCdHc5XGHs9ED9VI+F6ecRMoIxrCNvqyEgjJDAct8KhOyxPiqvshyXxsa9gAclJxXdQw4VXVQ+PKD5VXgLZMnYleQc4WqZ+M8sS2lG83y3Af2eR2nFQNlrfQY6Fs/S/OMnxKAQkCXcD1W3Ir1FHh+XkMcj082p4rD9pufm734937t6ouvThljNh8+pqMn+6gmQSakhiAMuALgsRomlhawclzHtx/cRUoKIQNSwYWFM1h78AhX5mYwtTiD44M6KnGEmfkJPFrbwdTUGH7w8V1Mzc1hu9HAt29/hIoxEO+xVBnBr914CUmR4cHDNSDPYCoGJAoTAUoKsMHw9DhoeAjvfHxX7zd2NTNWMtCBN+ZjBj9UpWOQOBtZhgLWkhLIU7AXdDkVrsLGUWo8uKVjZKTes7BbB55hnwdAelADAD2oQf0tA9GnKhbsAZgSKmk+BrNA9anmJGNM1vK6aZjvfLC/+dpLW0sjv/HChZGh6XE0tvcQQ6BewTEhYkJzv4HDzR3MXDqPr7zyCh7t72I7b8Oywd2NNQwnFcSpx8JIDSYzGB2uod5soZJYZJkDhDA9XkPjIMPixDQe7G0hR4Qmebzz+BGWJsZx9dwc9u/kKPI2bETwuQKWEEeEgyd7qIw9wtmrl+m3X78R1bvdyR9tP/mSi22UmwqNJtn7jaHDPRwmDgsAnBGoekYbqsMKbUsHwzQMoKVNRlblqpKACiZWzrohaTCpABmARGMqb1Gv1Q6qpbxYg1i36J8BpSCXESJ2xMZlbDwxeyr16O1WBgAYJlJiI8xtYWY9KvXQY9IkNpFTMk22vP7f/bf/7fq//7f/81SaZtMgjaVMlzSnmvdUpMTtBNWgEVYEVrivJy4b9bgEwqIaxL7iwWRPfJ65B4xDE18v0bDn+wzVPtgknLDS2qOky/322G4QwKcaA6kE5L0rt4S5QUNNVNrclcwzpK99PonhDkpnlJZ5UIBMz9YOJ6Etir4DSR8RSZCDSDnw6Dl5lOmKqqrKTKIKr1AHouLRg0cF2aTw3hcKFMrkmNQJ4AnkmcmTUuGEHMQ7GxtfI/UZi7AxUqr5wcxPOW+sVyrylFdzv+EP+gsCaHrKqu4WUMo/fpqPMb+5sFDJtnZffWV0/u//wduvX12sVIbqW9vYub9JURSCUsSFN12Z4E2EqTNzaNsIf/zjH2LPd0PjoAhmRyfwyvJ5dPf3MWQsdjb3MDMxBgLweHUTZ88uwkEhlQoO8y7ee3gfprwGKyB86eUbuDo7jc3bK2jsHGI4KQN2nMImDOeB6uQIhmencO/gGO+sPUQbQBd8mBPuCOFdZV0j1a4D1CIiQMk5AOSE2DgQu4TIpyn7fnN171z0o7sH4HlQAwA9qEH9bZd0lD+eqwwshQ5z59AH0arUB9FE2iHyozV7nKV4VM+7t769cn/2xbmZ4bmFaWod1+HSDGwDDaheEBnFwfoehifHcG5qCp+/cg3/5sMfIicgdR53N9bxu5/8JG6+9zFeWJzF1vYhxsZrODxqYHlpDgdHLdQP61ienkC1GMZeo45G1gGbGAea48/u3MPUJ17D2NlpHD4ogCIPx+4DHqhUCRt311EdqmLu3Fl89dWX7VG7feZOc++zNUsFIkujzr3fGPP7kEoBawUAGkQK32bA0Bi6qIfhA0FSZq2Zmgori6mQagolIiBRJVCOk3a3jFSVQYmUeJWektEQCUAliA6yDeLMU9d4Ig4sJPcb35SItd77QS+P06hSPbVuOEbTGl7/f/4//u+3AdQAdgDGAErK1A+czDj0PanpJwdSPw1v6Sn1z7NqoOet9+zlRn/F9vVv4DL+aY/zT1nvecf0vNegZZugPieUhEraHS4sklNUTaNaJRMvGRnKVbXwgCOQA5MzSo4seVd4l3DkJc99GiXCzELMetq2ri/f6Ek4esAZ1WcDTn4RKzU6edPf/ZlA8Pr167Z4/PjKPNW++HtvvPqpy2Pj4+n+Hj259RgGDlFMKLoCjgMrn3tgZHEC0eQ4/vjDW7jX3IUrXTcSw7i+dBZP7j1AFUChjMvLC9ja2gcbg6FaFVFscGtlHW9+6g2898MfYLfdQGIM1Htcm1nCpy9fQnZcx/ajjTL0k+CdwkYBPHtjMDo/jSyO8Zf3P8STrKkp21bK9m7B9A4Yd7ziEETeqhqomnLOQohIiIIHNDH7GrF0qC0hSvGU+0boGxkA6EH9rSszeAsGNajnsVEgoAG0J4BR9MIwqIz25v66RMicg/GRErztZO3FyPPcy8tnLYlH86BJNg7+wt5LYIUyh7woMDw6hDOLi9g+rGOjeQRmRitPYYixNDsLcQ6GAO8F01OjePRgC/Pzk+h0U+ztHwNKWD5/Fk/2duHFA8zo5F106hmunj8LaxidVgfWlGRpyYAyA4d7DQyPV2l2eorGR0bxZHt/qO3SOZBxuTN1CB07lhxJ4rFtFaPAFIAukQ4xa/ekyRIVFNpGAueACEBUo9KxjUKDn2qQwhKBkPTft1ISXW6HT4PnIM3gzHNqhMgIsxFmoxVirZTgmbmpQ8zSDbaDCiJ0AYxKzLl6FniKqsOIk6qPo8TZuNK1cdLgODm2leQ4SpIWx0lmk4raakJRpcI2qZCJE9gkoSiOwVFYoiiBjWKYKEYUJzBxAhvHiJJK/z6bJLBxArYROI7BSXiOjWI1NkKUxKA4BsdhOyZOYOIYJo5hKwlMnJCJo7CdStiWiWNQFMFWKmHbcQwbx7BJAmOjsP04gYmisM0kAUfhcYoTsI0RJ5VwzDbs10bltsvX8/Tt8HeUhH1zFIHjcDzhdVfURDHYRBoliZg48TaKvI2TwkZJYWyc20pSmCTJomotVaYuA11i7jJRF0QZEWfMlIpQ2zK1RLlhgKZl2ybSTGzhuGOEciPMDTXGKBFh21pt9Jw3VnrR3R8qsPXTnHV+XvCMn+e5fwjwvU5nstZxv/+P3nr7dz99cfmyO65Hjz++T67TRlzpXeYEMgTPjMr0OGYvncUPnmzj3935CC0SeGJ4FXzh1TcR5w7TtQRDxmJqcgQrD9ZxcXkRWVZgaKiKdu4wPjOFNhQ/vH87HLQKpm0F/9vPfA7nR4bx4INbSI8bSCoMeA1uHcwoQBiamcDo4jx+uL6NP7l/SxuMtI3oYWbNd4jp+wBvC3EWAcapRmzJlgbhSlYLUpMTF0WWGRez8VXjfWaM9H2fWzUBDmUAngc1ANCDGtSgngHSE4S2EIZL5vmEgaZTzKkCLKziAZnutNpz5yZnRs5MT5hus0nddhqm9EtvXmVCu9mFsRbzc9MYG5/EnbUnaPsCYIP94zrOLy0BXkAqQWOqgvHRIWRpgcgYLC3O4uioiUazjaSWoN5uQslACKh3G0iQ4MXzi8jbXeTNDGwV4hQqBLIEX3gc7rcwPFbF1Pg4hqpD5snWTtyVdArErmDeNj5ruijK0Y4Fbavd8TBl2zVGccqOrApohhxDSMJ7VyhRRCf9fv01EzrRFqNkMsNCRBpkGqxEJMRGiL2QYzHGeiLurQuAUGejKecyzKydHisZ7Nko8x0T52CFshcnKtr1Xg696oaoPvCqd73oPa+6Lip1ARRCiShiL2J6O3LOo0eVe+k5WZQ6Z0VfytH/v7zf91INy2AWaBgEFeJVSymH9KURCoVSsM/TUv9QXiui/fWktw/RMKV/KpVQ6CQARgF4CscIDc4eqicBMF566YOnUhUl2NH1XpP3pR92uW0g+F33whRFVRUkDuJExXnV3CsyIU2FkIpoJqKpF0mJKDXMqSp1RTVjoowMcgVSAjrE1ACh4UBNZdO10Mwb9eyshEFSrtZaYWZtMQNJcgo8v6u/hN759Gecn6HW/8rndycnR7qNxst///ob/8UXrrz4mRHn4gcf3qXG9hElFQqfLyi4ZH9RrWLuwllsZAX+h3ffxY7vQtiiEI+5kTHMVIdB3S5G4xjHx3UMJwmgiqIo0ElzOHUoiFFEBn/8w+/DlfE9kSp+6+pr+PJLV3HweA0799cRlzaGcABZghMFkhhTy2dwAMK/fu99rOVN3wTvddj8pTfm+0q0Rmy6BmqsmhiWElU1pWzJkdOC2ORskCdiHXPXN3vyDWsF1ioaj2XAPg9qAKAHNahBPQugCagDGCd0CBiSAJ6DoLQv40AL6hMvBtZZprjr0nFJ3eLlhflkOImpvt8AcfCC9WVSofOKtJNhZGIY8zOzSL3Hys4GwAYCxebuDs6fWcTB7jHGRivY2T5E2s0xOTGCja1dGGLMTI9jbHQII8MjUGOw2zgGkYXC4/CogfHaEM7OT6LT7sJ1HIwJEeNeFKZq0W6kqB81MTk5QnNT04ij2Dze3h3ycAkBzifV7bhIm/ls7NBIFK1Y0WZFm4CxoH2dKnW5XYAKzShGTKraawx8ZrF9xq/HTp8CzoGBZhbiXEBe2BghZ4T6jLPRY6pjiHPtUgoYo53wY66nUkIIIuTEmsgwKxOpSmFAdQV2YGmNlB8S0aqo22TmFhGTJR5jwzUQYi4TSpiDhy4RhcY/cxI40gtAYSb0Ug6ZObhRhPuVeol+QYIAY23P+kKZT4WjBO9uorDb0nKaA8Ir94Pyds+5gzgcE8ypIJbyeILjR2gWJFM+xmE/XAajMIV0QhCBLAcHkFOBLb3XbIhgeqmGxvR8VBQED9ICoExBXWbuqCINDDMyQHMlyhTIQJQb4ozAWRRkHLkCXSI0vaeGhWlY5haxdjJwzlYdOyvMVpkzZWa1Pfa5WlXsVZ+XCviLgmf6BcAzERGSbveFPzj/8j/93Vde+eKI+Omth2vYX9+hJKG+13bQqBPUJpi5tIRiZAj/vx++j7vtPXi2KFQwPz6Jt69ew+76JhbHx3F0cISrF5exsbGPxfkpbO8c4aXrF5GKYmJ+Bh+trWG7dQzLDFLBtfEF/KNPfwa208bKB7cBKRCZEFPf89wrQBidm0Zldhp/evue/mhnDR0bNVsw9zqgb4Gj+56pKQCxaswGCalGHEaz4ogLA8qZXc65zZlT3zLGl/74AUBHkaJeH7DPgxoA6EENalDPk3GULDQAdAEMA30Q3QPQSbC7M/ACD2fEJY12Y25uaHz0/MJ07NKM0mYXXAJnADCxRdrN4LzH5NQoFuZmsXNQx2bjCMYY5F4Q2QizkxMgUcxOj8OAcXjcxPlzc0i7OXb3DlFkBUQ84koFrSxDO09BbFDA4WC/jsXpGcyMj6Db7II4MIlOw0vgiJF2MnQ7Kc4uzdD81DREyGzs7w17kppXOszJHo6oa3W7VQ+sSBhQzAItAiaCZKJbDiZGAQJi6rHQsM8B0CXQC0spAwEpUabEokQ+NBEyC3eN9IBzcH6oo1aC7hoRhonQ6THPp2rCOZN6a7yhSLwzxoio5y6RHHnwnnq/q4o9WD1mpZyUKi4vZp0rJiBSdUVhpChIigJSOEieQ4oi+DznOXxRwBd5WFwBV+RweQGX5/Auh+RFWLICUjj1hYMvHHxeQIsCWuTQoiAtHNTl5X4KlPskda63Tu9+aLlvdQ6a51Dvw7acC+tk4TE5tV7/+Iui700tzpXHXkBc+XwXXo/4cFvKx8K2CngReO/gxUPUQ8SLqpapdOgC3AG0C6UMhIKJHTEVIV2QCgFyIs2JKSdIwYqMmDsk1DLW1BVoiNeWiUxXwAV3xAfZTkPLAYZuGaNIEsXd4WfBs/6Sn3H+eZlnVdB/83Wc/Z3FS7/1v3njzf9yNo6W9lbXae32Y4oihYkI4gATM8CMXA3GlmdhpyfxJ7fu47tbD5Axw4NRqMenr76E7LiBKgExEYqswPFRC0tnZrC1c4izS7O4u7qF8bkp3N7Ywsfrj8BkwPCYMlV87VOfxQuTY3j48R00tg8QxwQpSrvMmOG8ojY1jsmzZ7DSaOKPP/4Q+1qgCbPdYfOej+L3mbErQV4VsUpCRIlTtRI+X06YcwtkbJClYl3C3udEgp58w1rFkycD9nlQGDQRDmpQg3peJ5aUtnYCXA6I+QDApBK8P61F6NnaZSLFVuTMB03yc395/+7ombHR88vL86ZTb1HW6VLP4UCcRxwbHG7sY2ishjNXLuN33ngT6396gK28BcMxbj95DFo8i+mkisOjOmaGhzE7M4ad3WMMD1dx7swMGs0uDhttxMNVvHT2HH60ch+ZdyBjsek7+LNb9/F33ryB8XNz2H+0CXgPgFE4gRIQVw2Odw+x8tF9XHz5Rfz61Reok2cj33x056qofBVUaedtbgFHB8D1LNh7rShwnWDa3G/Wcg4kwkBLiWqqVVLS4Atc5jGebrDr/+CGNMFgT0dECkqFuiw0HIA1s5Xwf6PPWAPAQY8J+yk1BCUHggACRwVYCmKbwWkLkXTB7GtxJevs12uvfuITu//in/+zZu5cAVZlpb57RQgaCdKN3uUhqqccNMK6hNJPukfRqgYXO4B7Th+l1YeW5mJUXj4UbO2CCQYTQannK106hPT8llUB4lLaIf2Ib9Vgf0dlV6ZqiCLvJQT2JCHM3E9NFPGlZ2BPyqF93wkqJSs9hp0oMNSBDWdMTEzgf/qf/gj/3//P/9vb6pATlVwDs+wZpKpKBAgxeQCOiHxIn4EnJSekhRAVhjQj1QyiOdg6ynKhuPrUOe27bxhTSjfe1V+wSfCv5RH9h3/4h0z0jdo/m7v4G1996cbXFivx3OHmlnl88zElSVDJuFRhIobPFd4aDC9Oojo/jW89XMWfP7qL1AAOBlDGb7z+Fhp7Rxg1jPmZSextH2KoWkGtkiDLClSrCTiJEA1XYIaquL2+ChDBQBEr4YsvvoRXz8xh/8k6Dp7sIbIcvN5Lu8WsEJhqFSOz02gy4Zs3b+u262ibI9cB9sWax8SoB+WQRDAmUaXYKdsACEQ8kY/YF1DriOGHiKV52ve5H5yCv6lzMahBDQD0oAb1qwuoVwhYDj8WUck8nw5XCeWylrbakX1c8d13VtpHS9+6d39k5vUbM5NnZmn7/joMl56+XkCWwBBsP9zE2MQYLs/O4tev38D/8P47SKWAtRHubW3i0tufQmf/EK00Q6NRYGKkhjTLcXTcxsL8BKrDVTTyHFuHDZybnsb97S3kQiBjcbe9h2/eXMGvX72AyvQ4WruHYAg0P+njqwwZbD3egk0sLb5wEb927QofNJvj7+2vvSmOjhDF7cmqeedw/OgQWyjCe3JLsXodQE5YCtKJOrOMiDDAQl0lrXgCqnTiCEZ9FEq95kH0QHEp5ehwAModPuX9ewKee1ZmM6fsM7ZOnwGRUzMIaRkYXfp854WDTQpEyGGtj6pVBfbbZxYWm//0//h/yCsRl7A0TM3pqVHUM3YNz6Uyn7lo6FlPjdIDg3rb45/07KDneSvqM54fz4vY45/inXF6G8/rlqNTCEh/xnO9AN4JhmLGw4cPAfHEbOBdruSNUMgiRzn8EAYJmEVVHTM7VnVCyFUpY9XUMqdeNDOsOcg7VuOJu8IcS5h1AOSp81n9m2I7f157O/2/feMbtb8zMvel33v99d+7ODr8+vHWVmXlwxVi6wAKITgUGYgSClXUyrCUj3cP8Sf3buEQBcAxsiLH65dexMLoGB5v7+P6C+fxre/+CG9ev4wiLXDvwRO8cv0yMl9gZX0b44uz+Pc//BHaLoOhIN14efocvvzKy0C7g/W7qzDqEFUZReaDVp0ZXg3GZqaQTIzj2ysP8fHhFjrM2mXbdMbsCPEOPBUuZgvVCCIVGGPhAVhyXsg74gKFuMQWrptGHtwWkBH0fJ+NOUlsHTDPgxoA6EENalA/ww9MQ3jwMrADwVzZfeU9l/O8AWuMmkKK4rCp8Qojf//97bXZ82tTo28vzVXGmuN0vLEHYwNCE6+wMSHvdPHk3mNcGRnCF66+gCd7e/ju+gpEBQU8fvzwAS7PzGO0VkUiwM7mHmq1GGPjw3j4eBsjI8OojlYwlkQ4u3AGmQKPdzaRI0LbAO8drKP2KMZnL59FVhTI9hqBORWF5gqqEOIEWLv7BDAGS1cu0e+/+UbkfiSzHxxsfJqJuy2OWpNZ9vEhlg6BdRcw1y0BrjPWC8WCFYgQM4v3RMFyjqUrKSqogCCsqs8Tl56AZ+pqz66OiKXHPp8Gzz0A3QNWIkILALZOpdOJCGEIQAaKoZQ/hQvDcWEv8fZKlQBknU4nb7aaeLi3z/fu3aUoigNoIQrhJuVEQy8wRYlgjOkD18D2Bra2tB+BKb2kS2EsiAkSmFnYXpBKT+NcJg8ytEwy7IFaCsRtb7uK4PHbb0QMoSaqAhUfwDyVlokiEAiIOISjyAmsd86DyxQ8Lx5QhfM+XMIEuMLBAPDBmBsiHqSCTquN5XPn8Oprr1G90WCAmZgMmJgIDLBIMF1RBnmoFuqlAKEQQs7EOZHmqpoZ4lSIU2Jk3iO3ahxFJGiJnhYW9r2fo+jZpsH/5N8BU8DIpyvTr//jT336axfGRj+VHhyM3fv4ofo8Q6Vm4HIfzl/EyDNBMjmMqXMLeNho4X/88XvY8Sk8G+RFjqXJKcyNjOKdH7yDNy5fxg/f+xgvX17G9vYBmvU2Li4vwEYWqzsHeOOTr+Lu7i42m0dIjAV5h8XKKP7OJ9/CdGyx8tFddI8aSGqEIhMQAWwIIgbDk2MYnZvG/YM6vv1wBQ0SNBBlLZUnSvaRKo4lGITHEElgOIZTApG35L0nLiLn88L4PMujAmw8jPF/Bfs8ANCDGgDoQQ1qUM8F0T3z3DKpcJWAZQ4gumDsiQJKmDgl5WDODdNRqvLxoeRnv3Xv7uLS2Mj8mcWZuN1sU9HuBpurwoNBSKoGx9uH2FhZxYWXr+G3Xn0F64cHeNw5gmGDR7tbqMYV6MgYpNXG/Jlp1I8aABPm5ydQiRJsHRyhNlLF6r3HePHcAtIsxcbxIWAikFH8cGsNtSTGa2emIU6Q7TdhjEBE4PPAu8YJsH5/HUk1wbmzS/j9119n/z4ufHSw8UUYbbXb1k/X+Ob+2EIdW1t5yUQLcD1EDooQiwgQ9ZQiqAFQSaEnIJqeg6IV1FXq9MDyCXgO7DPrs0EazKw9EL3zHAa6t58cQIQIBVzJencUXFNgXe3xKwLAC6sYY6Msy6KNjU2O4xiM0DQYQGqQcnDZTAcQPBTWGBjD/WQ+opMmv35kNxCa73pSCyJYa8oWwRD/bawpJR8CY0yZZlgGuPT476ATgUiZMqghZrsnJXEuL93HGF4V6j3Ee2g5UPLOl08GpIwy994jK8JUhEi4Fqi0TVQRKLgE1gpjGFnaxfz8DKy1ZI1lAFZVLIEjIcpVVQwZAcOTilOgEEJKhJQUqZJmRJQTUUrEKZhTqM8hxhHYdwnKIwA6J4Or50R3/ycHbH8I8H8NVD83vPDa77/xxtdenJj4srRbC3d/fF+KNOOoyshTQQh0VKSpRzwyhImlOWxkGf7njz7CRtGGYwOnioqJcO3sMmyR4+2rL2Jv5wiXzs7j8LCBkVoVo8NVCAgr6zu4fuMqbm1s4Tt3PoYhAsSjBoOvvvIGri3MYef+I+w82kSUhPPaq7wrqIxWMTo/hWMV/NndO9jIm9o1Ns84OvCMO0p4AHAHRgkqMQwnRtWWwytHGbmIOO+arKgYm7M3rsMdD7Yn7PMvxuIPalADAD2oQf0tBtHPmbVf1aeY6KIw8FLmPgfgVpBJ22Q2IrYfPc6b89++/7D2uzeuTk6emTXbDzYBFXAUEBEZQhQDO6s7mJidxLnZOXzl1Vfw33//O6jDI7Yx7qw/giwsY3lsAqvbe6gZA+kKup02Rmo1GAJGqxV00hztvSNMJUPoVjMcdduAMdhDF99eXcFQNcHFxSk45+FbXZANudYqAFuAxePBRw9BYCwvzPLv3bjB9GNd/uh483fA0NQKzdTdR3tYaACnQPQqgKUlOhLxE64JYATSJW2KN7UqACFSkNIpcPssEx3YZ5ZgWXci3egB5h5Qnnv2yaen+cNtog4pLIAIKLQACiq10dD2HisAiaJaOBwRVpHEmCiKkwpZa4PjQb/ZMYBOywbMJmiUS2b6tENG0EPTCUgut9ED0D0Lv5BoeCqJ0PDpN+Kku00VZKISKJ3Y3vUIdWtMSA7sgfRAdsOIQK2F864Evwbeeaj35VsUBgRWFFEcQ6DwzgW9dxlvKM71rDbgnCuPV8DMcEVOqmCADRFFxDBExKJaCqDJA1SAkDEoY1AKohSE1JDtepGuKLpGkVrmvGDvMhU/yhXpkvsJULYOAHH8vwRgo/Ldjb9iRj/7+2++9g9fnpv5qm81Zu6+e5eydpuihKBOQ2y6IRQOMNUY4+dmcRwZ/Lv3b+Je+wC5NfAKkCq+/PbbOFxdhxdBJ/eYGh8BiaB+VMfcxChWN7YxvzCP4fFR0FAV77+7AiEEBxQRvH3uRXz2ymWkR0d4fOchSDyMZ4ABMQgNhGwwPj+JeHwYf377AW4dbmtKLB3wcUF6G7B3obQDJgeVCNAIqhYeFtDCgsSBHJEvEuacmB2zdWD2ffDMrNiKJfSEDBjoQQ2KB2/BoAb1czcbnVoi/QnNpAiXumjKQgx1vUu8khF9+P7u+sZ7T7a68fiojM1OqArBmtB0ph6IIobPcqzeeYyifoS3Lyzjcy9cRSwhLhomwpPDXWgtRnViFMOTo4iTGNVaDTYxiCKLvd1DsChmR4cxEce4ceEShpIKMu+RksG2dPHNe3ex0c0wdmYaGkcQzzBRYECdC5HW6nM8+PgBNXd26er0BP29t96ovjl97sJwUfzmqM9/Jzbu9clqNrG0tBQ9JaNdX/dIEn8Ux86YlmeOPNh4MmWiIBkPIq0xS+XZd7n9PCwzgdO652dr71mN7OnbQ+W5K0h6aggA2iZSLITtGZMoAIqiKFJozXsXO+eQ5zmyokBRFMjzHM65fnOeFw+vvs/YqoYYbe89nC/9mzW4rTgv5eIDq1uqg1Wk7+HcY7cDeA0+zb3tiQjEBYmFSs/3OURqq1eoE6hzcIUDNDQGOufKY/EQH/ZTZMF1wzmPPHfI86K0MwyPi/el/V7JdJcNh1CBuKLv5B2Y6eCWJsGS2BDIAGoBMUSByyYVB2gGaKaqGYhSMpyJUurUpyCkpJqKSOG9FDkVHiBtA0DzJ8/zEv4Xc9/Ra8DkV8zYb//vP//Zf/LKwsJXtN0+c+/D+1H7qI6oQhCvEK9ga+AcIDbG5IV5dCoJ/vjDW/jx0SY6FExoCu9x7fxFxF5wtHuAqeEhzIwPgwXY2tjHC+cXsLNzhNmZaTgmtFXw777/fTSyLgwbsAheHJ/H77/9Fqre4f6Hd9A9asAmVPqNa2g+VcbY3ARGZqdwf/8YP1h7qE1y2oZtZcpPQOY2GV5HxG3AAcqxYY7hNFJWMiB1JB7kC2LOM+aCM+uY28F143Rwyi/QgDmoQQ0A9KAGNajnJ50tPeV1FVIKtWagVQYAqposJ7PTpeTOAfzt76093H1cb7qxhSmtjtbUZ4LIEMR5eBHYhNDYP8b6yhoqrsAXr13BpdFpsHgYKJpZhu/e/Bh73S62G010nQMZg/3DNkxUevlCUT84xjATpNXG1bPLIACZeGTGYN018RcPH2JfgYnlOfBQApcH+ysQ4J0iqjCgOVZ+fB+t7R2cH6rR333z1eTVqcVrcdr5ylDW/e0q6auu1ZrFwkJ8qh8ugOhKxR9Gka/blp+wXWe6kePUOjIBRHdBmlLPfeNp0Hza8/mEiS4BNLMuMOvOKTb6J8CzKtWfZrYFRIKYBBUKzNlWAAJ+ISMAlsAJwFUQohKQk4jAl5ILaC9sxAdJRy9ERcqgFOrjznISIsgxSp8RSLm+ipZ30QnwhgYWubyvx1L3/KG1DGrpOWywlm+2KsAcZBu9hEmEv1E+15Sez9ST6JMB6ERaQj0dNk72Z9nCsAmMNjMME2xv/HEq3CXQ50oIimUDhTUEYiYlqINqAQ3MM6nmUM3IUCaqGYnmIprDS0HEHiEyumwq/claB4A8/zli1n/5+sM/BJ0FFq8MzX35H33mU//k+uzsb1G3e+7OB3ekfngMW2MUXiAU5DXOC1wUYfz8DHR0GN+8/wA/2n+CNoCcDFLvMD8+gQoIt378Md669gLSVopWo4tms41PvPYCbj5YxfLyHLaOjoFKBevHB9huHiNmCxaHGVPB777+JhaHKli79wh7a7uwFlCEoBuwIk8F0UgNU0tz2M8d/uL+fWz7Dlqwrmvsrlr7wBOtiWgD3otRExmjMStHURyE/B4QIiooppzYFMjYtcl4Om1b149Qjwb650ENagCgBzWov47t1Yo+YxYbALR4AxUDVc5SSMqm3YrMZtfaDx6nrYd/fu9+swGS8YUpcMVCXUgQozL8IqkY7G3sYe3hY8xWYvzem2/gTGUE6h3iOEE966BLgunFBTTyHBNTY5idnYAXhfOKOLKoxBY+d5B2Cps7XD9/EcZYpKLoMONuaw9/eu8umpHF0MIUtBLBFwprGDYyQc4REdTluPPuPbT393BuqEZfe+sT0Sdnly+N5vrVMcl/v5LhtYmjdGoOc6dBtMfqqsfOiEMc+yNrvbUdZ0zsuGsd29yxsa5GLDUKASpEpBg+DZ6oxJlHffZ5p9/9f1IzvRvecy9ABQDGThjtsH4BjfPy3J0Cab4oKOh4uaLQRJW4D1aJgnVbuRhrQMYGWYYGqNpr2CMwuPdYGbhChsCWYC3DMoX7WHtE+FPyD9UAorVvm6f9+/uP6wljjbJJkcqURGaCAYGpbGrsr0ZPi4YJZchKbwDgy9wXAgnAegLkRaSPVntpiyAKmmgpmxUBFgiByBIRlwsACDOcZXKRoRyGMlLNWJEZ4oyYMmLJPUvOxhdVZv+Tg6mTgdPST4/e/hthnv/Fm29G//U3MP3a0Nzf+4NPvvWv3jp77kum25388Q8+1MbhEUeVkO6ovV9MCwhbTC3Nojozjb9YeYTvPHmAJgE5GxTicH5uHuen5mC7GV69dB5Zu4tOs4uLy/OoVWJ8dOsRrlw8h2Y3x/T8HFxssbq/F3TP6jGsFl956XW8fGYeG49W8ej2I0SRlrIvAkUE9QQii8nFGaBWwzuPV3HnaBsdkG+RaebMa7kxj4S5DksOxhgYtaocecB4DwoDTClAVMCxIzYF2DqYjq/3Ggd74Hk10uAFPwDPgxrUAEAPalC/fGMhsG70qQ42rRGgDBWDRBgVUA5yhehRS3mlQ/ThraPdh++ubabRxKiOL07DUUiVEwG8AzwA9R7r9zZwvLWLlxfm8Zs3XsUoWVCRwtoY956s4aPHjxCPDuOjB2uot7popwVGRms4rrcQxxGyLMfizAQoTVETxZmJSXgV5Ap0iHG3uYc/uX0XRa2KibNzkCgGhGHA0BxQpzCWQFTg3gf3cPRkky5NjNLfe+uN5NNnLiwNpf43qkX2e+NEb+eVfGpurg+iS+e3FcHWkEeS+CiKvLXtExCd5i6zuUuN8cSpUDcVavfdN5S5ocx1YWbdO+0DjGBZt3DKbeO0nnrq+Q4fgpikIPbBcxrAgifgMk10uwwgIqOJITalRLsPYr2Xp/zcegHuZbBfAKNUgsuy2VDRTxsP3tEl8AxeywQYE5z1wgYC4C79mXvuHVDtO2ownrYbPwHWeqLRxgkYD+mBDC7juUW1BPUhfbAHwkOC4sl2zTMseP8iZwYZ05dxiAJsTI8QBwGsohzANKhkxgVgL4RCRQtxvoBQQUoFERVCmhNxERO7oiBJMxIQKVFHTyLbn1dv/k2DaPrDP/xD+jfvvrv0qaG5//M//sxn/sknls6+ktWPx259cMe0Do/JxoSiEBSZhxqgKAS5EKbOzWL87AK+9/gJ/uzRXdThkSPY2lWNxWQ0hO7BIRZGR9A6amFnZx9XXziDlYebcE5wYXke+40mOqo4SLv40x+8g9RlsAQkqvj85Wv48isvIa/X8eCjB5Aih0IgXqHh7YIXwsj8OCYWZnD/4BjvPHmMBok2yeQp86ZAVxWyA1AOgOE0UlULqAEcB2NCOBA5OF8Qu5yy3I0E7bP0nTfWjWJ1tQeeBwB6UIMaAOhBDepvAETjtD63TSUT3bMHJhBpJ+Fum3ira+OP65CPvv3o/t7tg6NiaG5Kh6fGtCgzWURCzolagisKrNx8jObeAd66cA5fuHQVFVUY8SAyWN3dgRkexks3XoJnxuTEKBqtDs6encP+QR0TY0PY2trF5HAN1E0xbhO8fP4iDDNyAB1m3G5s4z/eXUE3TjB1YQESxfAFECUW5BlMDGsZSAusfLCC1TsrOFNN6Hdfe6nyhfMXz485+UKl6PzOGPAp6cpCANFvngbRHuujfqdS8XEc+zjuuCiqFX0g3c0dd40nMp7ZCHPbG9PyR9b6A2tlL8QFy1Z/+hhYKv+f+8m4ODo4BabbKCUBRD4h8iCStAs9kXuknOfDwYXOGkNMiExo/LPW9iUQfUkFeiGK4X5jQqOhLZsHjekxwApDgKXwWK/lz5Tx2abHHhsDYw1sGZfNRIiMhTUG9lTctjG2HxNuyuM7iREPriAhJjxsr8eYWxukGNxjxNmcMOvW9F1D+k2OPVBfOo9Q6ThiDfcjxXsR4grAGNv/CJQ2fCSqKIccQgQPkBMiR0S5kObGUA6hHEQ5PBXE7InY15iFOC1BNJezD8f6c8Zw/9Lg+R9cvx79d9/4xo1fHz/7j/93n/3sP7w6NfF653Bv5OZ7N+lo5wDxkIFT6VsZigPUWEycncHomTl879ET/Lt7N1GHhzMxiAxiIlxbOo8h8Xhl+Sz2Ng8QMXDp/AJu3VvFwvwUqrUEu8dNNHOP6uQ4Hh/so+NzRGzAonhp+gx+6/VXYfMUd398B1mzhahqwiSLBg1PlnpURmtYuLSE7W6OP7l5U3d9VzsUuQ7xsRhe9YY3QdwKKT8cQTUKIzgQYIWIQpokUUbEOXGtYC61z8xBuhGaBntW4TIIThnUoDCI8h7UoH7JRqNTyzhjwVMpH2BINcg3oAZGA4AOcdZqDDkpOGdDJvXZZLvZnTgzMVmbGR+lrJOSyzxMheG8lP7QBi4r0G51MTs3ibPz89g/bGK7dQxihlPB3uERRoaG0Gl2ABWknQytbheVaoRmt4vZmQm0212cXZzHcb2OKIrRyXK0iizocplx0Kmj3fW4fHYJw9UYaSsFQWAiArnQKWYThnqPxn4TIg5n5qZwcWGB4HVsd/9oSpAPRVHcFodGlB1lXXT9yY/tnqJeR2t+Hh0A45wpUa5EI2XSoFFmK8ZEwpyrMUY61gqSJOguk0RhrcIYQBUNVWoxoy1CXQBVVeqeOkGTAI51lIfEGzXeQI3xnkCU+zgxzok4GOMxRhi3w+boaGvs6vVXzv29r/3BK41GY+rxo0emtJUjQCFe4IoCrnAQ70ODngtaaC+lVVwAjvDOhQZB/3RzYV8yUTYG9taRpx4LbPFTTYWq0B6zXW7vtLQDp9ZXH/blXfB29qWNXe+YvXNwzof1nIfzwXXDi0NR5MiLHIVz8N6hcC40I7redsLxFHmOqckJXLhwQd/5/vfwF3/+Z2ri2IlqAUIGUEaE1BB1FNRVSBdEXSJKDXHQQwMplLtC0o2MTRV5nql1bNRzpxfdbpUoBTNrCfC1Ya3isKLPxOb8sow0fWVurvb+48eXf3P+8n/x9z/51j9/eW52qbW/F9187xZ1G01EFYZQUGYRB7pdPGP24gKmzi/h+4/W8Ud3PsIhchQcw6tHBMKLZ85ivjYE12yhsV/H8uIM0jxFvd7B1MQYRoZqeLyxj3iohtkzC/jO7bvYON5DxAYkHhdrk/iHn/0szgxVsfLBHew92UFSKQNbDJWBNgRTrWD+0hn4ag1/cusu3j9YR4uttDiqF8auCvNtgDdB6IZpEzBATOTJGFZV8cScgTklog4n3DHkU5aoaEbiEEWCbavAk2dZ5wF4HtSgMLCxG9Sg/jq2dqWd3cIpL2MODWsgCbScEjIoQL5ITIqKP2inZoWJ3r/X3J/7y5WHI3/39VcqU+fmsXH/CaTIQ6OWV7AlGEuo7x5i9e5DnL96Cb/16iuov5PibmMXkbFoZV28t3IfX33rk3iy8hhTM+NI0xSRYdg4wuFxA9YaPFxZw+L8FDaO6riysIihxjE2DvaRlfKCjw83YD5m/Nb1FzG1PIuDxzsw6mCsAVxwgrARQdVj4/4TWGY6++J5+q0b12mkWln4jzdvf2G/200oiocwav980k7uHh4edkN/Uvnju7KiwJuydbnOS2mq3rfFOcc9KUaQa0SKKArAeXVIyuQ5AO8CuB5A0jIA7/uA6fAUcD79d5tIq0SqlAshBogEXQRru1IvfeD3CYADaYdEm/Pz89mXvvRrMTFDfZBwKPX0wKGZsOf7zGW8NgFQ4qBwKAFu8Gku5R4lexueE2TiPfzbC1M50V3jKW9fPbVu8ITWk0jvvpq6dMzw0veK7jUs9poE0dNQE6PsaCwDX0IkeFCElDZ5FDTPPVb89JXvnEe1WgEzI4osoCqlbZ2UQeBeAS+qngiOQd4QeVH2IDhDVChQAFIQ2BXOeSvsybBQh4WYy2TK4759IVA2ERYFAV0KMo53nxea+PMOgPHK3Fzt4c7Olb9/7uq//N3XX/+tFyYnZ7bXn9iPf3CLirQLk3Bw2xACGYIUAjYWs+dnA/O8uoE/uvMR9jVDxhYKIGbGqxcvYzKqoL61ixoTLl04gwcP1jE9OYqpuXE0mh2s7RxiZnEGQ1MT+NP3P8Be5zjMMKhgylTx26+/gSszU1i7s4L1u0+QVE7OJyxBPEBsMX9+EUMzM/jzew/x/Y2HaDFpU7ndAZ4o4baCtqC+yzAkUMulgyHUOO/Jk1AOpYxUu6SaEmlORexaUcfDxIIoEqAizzDPA9nGoAY1YKAHNai/NhMdJFCtccKwELxnaEZAFCQMrlxAQIUAIi85eWONV09K6sca7eZETHbk/NwcRRbUOmiCGSBL8Lkv7cQUzYMWTAycmZ/B9MQUHm/voFmkYBsjLXIcNVtYmp/H5tYuqkmCbprCMqMSxajGMcZGhpClBdJuBvWC0dFRNLoddIscYAMBcNStI215nJ2dwsRYFZ2jFMYLrCWQEkgBY4Pc4GivDic55ifGaG5iwg5Vktr2zv5kmqcjzGCV5CgarbS73a5/uvlyS3F4qI3GC9pqWe0sRjIJIIoi2bZWEceCJyOC+ooAe2F9bJXP3QvweGaG4Bz1pBhTAGoB6NEhes2cCUE9R8Yb1RCKB0DJs1TI+9wYgSrNGGMbjUbl2ks3Jr7yla+c8yLTSZIMJXHMNo4RxzEqSYw4SZDECeIoQmQjJFEEawziJEEUR4iiCLG1iCKLKLIUWQtrI0TWgkvZhWFTSiJM6ZbyTCS3hoh38WU6YD/Cp9Qla4DMwdYupBBq33mubCakE+cNNhwkAYaDDMQwrDWwJhxXOMbwGpNKgqh8TZVKBdWkgjiOYeMIcRLBWos4TlCpJGHy31q89/578s0/+RMfVau5iGZgdAF0DHGHQB0wOkroklJKTCkRMihnzJoqUaaOUjaUsaIQWzhyxjNb6bHPvfAUIgr9oMYo6rECEU6uiV8c1F2enBxN9vc/9Q+uvvlf/sNPvf3V2The3njwiFc+uEcu7cJWAnhmE5hn7wUgg+lz8xg5M4t31jbxx7c/wp5myNiElEcV3Dh3AfO1Edy9fQuvXb4IhmLtyQ7GRocwOT6Ch6vbGBqpYWx6HFvNNjZaDazsbYDIwEAxpIy/+8bb+MwLF1Df2sH9D+6DyYG5dGExDFaCz4GJM9OYPreI+8dN/PGtD7EtqbQ5anfIPPTWfKzGrKj4Ywg5MsykaoLZCgEgb1kzBWfE2iFjOwTqskHW1ayAte5EuvFo4Pc8qEENGOhBDeo/YYUmNwmMaxrEzJr02s6AtMdQk+t6X1fGY0L0Hms+9ZcP7k1MVCojry3O8kirS429QzAphNHXl8YVYOPeOoaHh/HyubP4ndfexH//w+/iyOcgslg73MPo8CgWlxbROTxCrVJBN+2WMdOM40YL587MAxhCQYStvUNcO3MWdzaeoN7twJsIHSnw0eE6cNfhy1cvYfbSHI4f7cKlGWzMkEJBILANPsYbd9aRpRmuvHINn718iYdqtbl//+HHn1lpHA3zEGBc8m2ZmHh0dHTULocSesLclwziCmgdb56aEn73Z3vMrsSK5ULhPYFZDwBMle4bkziZY66X8eCkKiqCHqPZAsJgh1nX63VCkvhvf+e79b//B197nBX5GVcUNQBDomIhZVNhELULaV8/QRz0zdSzdoYqSEEgYlEppdAEIaUeU13GyPTVF3K6V057QBindcVgY/qPBTmHgokhOHHk6HnoEYWBTj8+PLh695sYy5l85ZIaP4ko1xPGvO/SEVILA4NdHn+pma5UEt3d2/OcVJz3vgCQGlBXCSkIGYFyEjhl+OByrg4CJ0adCnlWeCInRLEQiaKMan8e+/yT9e4vBZ7/xZtvRu+8e2u2dth6/R+88bm/+6Vr1782QjL6+M6KPrr5kEg94gqjyCXEuDPBOwXBYvbCPIbmp/GtlTV88+Ed7GtegmdCRIrPvPwK0t1DeH+M1y+cx5PHm+hmGV65dhHHR03cebiJT3/iZbx/9yE6cYz9vItbW2tBfw6BVcVvXHsFX7j2Ily9jpWPVpB3O4irBlqOpQwDvguMzU9g/MwMNtsp/sPNm1jPm9qhqNsQ2nCGPjaGbzvQPhsroSO4lJKFzkH1RB6EHCSp8yaN1KdkJU+zuID1Hswl+7z6LPs8qEENagCgBzUo/E3Y2ZVoyCjYBwAdGgg9VKlKTIog+CxNeBVEAqY0he6rykcR0fSezxb+fOXexZEkrl06N0dZt4v2YRMmYrg0ELgmMiDv8Pj2KuJqDW+dP4dWnuNfv/cOGvCIbIyP1x4iXVjCJy69gDsf3cKVswvY2z3A+PgwxkaGcHBUhxfF+MQYlqbG0cgLvHLhIt5fuY9WnoI4QpM8bh5vwtwBfvOlFzGxPIOj1T1InsMkHCK/y1/iqEbYW9uDOODF167Sm0tLNJxUx//0o1uvv7+7UZNYhp2t/vHI2NjaWr3eLOUczwIfAt6lv6JR89n7OKQeXg9Sjjzn0+Eph88mHHYAJNC+x3AVGMqGqK1dDsbOSqCqPzw6bh5ufeshwNMgjgCdBaiKwNwpQCUQhOsLj9FHn+H+AKwZxAmAGlSHQBxD1YS0ixNge0rDgVMaDfSDTHrSCXkGI5YOHc/mYp7ooelkPSlxD/FTUeBh/+j50ml/nyfdkidbVh+21btTezaA4gFTmErSVUWbiNoiaBOho0BXSTMQclXkRFSAxIuHI5DzrJ7JSrCSQBndTn3v7zAMOnr6zBujiCIFbv2i4Jn+AcC7y8vRn7777tnrduorX/v0W3/w5rlzb1V9PnT3gzvYfLhJURxkLJKX8dwM+EIhxmL+wjyS6Sn8xf3H+Oaj2ziCR8YGCoZRh7OTM7CdDNNJhBEbYXtrH7NT4xgdnsPq2g68V5xbWsDNRxvgoRrs+CjuP7gNASEiAovgk0uX8OsvX0fFFfjo5goaB8eIE4LLfNkAGsZ8yWgVk0uzyKIE3/zoFu7Wd6TN1rVh95yhm0J8z3nZAVHGzFb602EGhkQAcpao8ISMiNKIpcsmSjn3OYx1MM7DWsF6ZcA8D2pQGEg4BjUo/KdtJqwDrXHCiNJp8ONQwFF8GuVoaeMgIPIMyQtxwtA4c9l82s6Gl6anzcTYENr1DnzuYQyd+PcaQtbJ0Ol2MT4xgrML8+hkHmuHO/AqADH2m8dIc4eF2Rncf/AY48ND2Ds8AguQRBFGR6t49GQTlSRGo1lH1s0xNzsLMOGg04JhAwdBI+2gftTFmdkpTE+PotPoAr2mNil1tVxqtPdbaDSaNDJUocXpaZqbGE98KmPHx405lWKUkuQ4sWPNVt7K/wpg/AsCoz2gfgaYCrrf4RAhTd2QBknQmKHCkQp3I5AFgC5AjhQgFCh6oNJArQUXNq6MMNlYTRxlsHGLoujYRPEe23iHLW8ZG22yibZg7Tax2TZRtMlxvMZxvEI2us02uslk7tgkfszMdZBhjmyFiC0bS2wYJoqIjQ0BKP9/9v58SbIsve5Df9/e+xyfw2MeMiKHysyaq7qr5xFogqBEiiIEUGBTMvHavTI9gOy+AU0PoRe4ZrL7h66uQBqMF5QAghAIdKO70VNVZVUOlWNkZswePp5p7/3dP45nVHajAVLgIEDyZebpHh7unuF+jruvvc761kocYgziLGJtnZLhEiRJ5tF2FhGj4hySpipJouKcClLfPk3nt7WI1BnVYi2mrhAXY12dT+2cGufqRkfnojE2OOsq55JCrCnF2dKkjdKkrjKJq4y1XpyrT2kaJEm8OBfEJVGsDTZJKuPSwjmbxRjGYszIiJwDI0THCDNRk4mRzGGzYMitSq7U2c9qTKnEUqCsKuuDwYuJUXydgmfMUF8qktHDukIaHrYjHP+bKqJy8f22sbFRPjv81S8uX/p//KNf/sbf/fze7rthNOjf/tNbcvzwQNKO1A+oXPjafQW4lEuv7pKsr/D7d+7zB49ucy41eY5iibHinSuvsNftM9g/oOccZZZx8+olTk/OGQ5nuMTwxuuvsH90hjZTpNfiX/z4h+Shqu08MfLZ9T3+q1/6JVaM4f5Hd3n+8BlJKvMIRDBO5mU8jo1rW9jVZf744WP+aP+eDkWZ4AaZsfeitT+NwjPETI11Sp0FaFRERDQoVBo1V8JMkJlEnYp1mXGhyGNSYbOAtZGTJMLjl9XnBRZYYEGgF1jg37kHek6iV2Ap1lNgMcoLRa9DRUU6PyI/J9GIYoqQShq8ahEx3qG9aTHtF9PQubq1KZ12KpPz6bzkgovaZ5capoOcsipYWe3xyt4ek1nJ4/MT1BgUx2Ay5NKlS+xubTKdTHlld4cX9dRZXnJ5d5PhaMIru5dIrOH8fMil7W0q7xnPpmAMXiKjYsZsWrG+2mdtrUs+K/C5xzm5GGbCCK5pyc4yzk+G9HoN2VpZ5dqlnTQRt3F2dr6RZdOGsz4kbnU28ZPs38GX8qee6OGusFxJ7wWBVhV0ySyhkmg02lZxOrdQ+LmJQkRTGjQopdR2nZoS1IoGfIg+apwqcUjU46jxUEN8HkN4ppHnMYYDjRypchBDfIrIQ1W9E2P8WH342Hju+ej3XZLMRKQtRlaNdW2Z584ZY0TmJE2lHjaUuUcaeVG2YuapD/XPJnG1HcOYi9xojBGSOo3MzPOkrTXzXGq5iJt7oV5aa1WsiSHGICIlMeYx6lSjTiPMVGOmQqaquYaYq5KrIdeouUYtFApVLVEKYswEJqKMjJiBwJkqQ0RGKmZqhKkxJlOVLIrJRCU3hgIkF0NpoykxVKL4qNaLaBDTjOJDrFM32ogUFyR66pzWiujt/112gi+sXO9vS3g7GY7/1t+6/uZv/toX3vvbN5eXr5enp80PvvuBDg/P5uQ5XhBVl1h8AdJssPP6Ltrv8bsf3eOP9u9yLpHCOIIqDuXdV27SDXD+9IhrW+usdlv4wjOb5ABcurROu93h4bNjtJmQ9Lv88ME9hsWMxBhsjNzorvF//9avcLnd5Nn9h9x//yHWKsZCrBST1tGBvhLWr27T3lrnxwdH/O7dW5ypZyy2mIp9HJy9JVbug4wVUTEqIKIhgpGoSCWihWBmGJmKdVODZGKT3BRaeZN7jAkkSWDWDDAMC/K8wAILAr3AAv++4+y4UKGX+BlfdAWgpcBLSrRkERH1eI2SVgaTK5Tge5PZdC1Rm76ys2WaqZHhyaTupBCIXjHOYJ0wPq+jXTc319ha3+DsfMLh5LweOEN4dPiMfm+JRmJ5+Hiftf4SIXishdF4RquVcnw0wACNxHJ0eEi308EHT1ZVKEIwMMynnJ/n7Kyvsr7aw5cVVe7n5SGRWCkhKmnH4bOSg8cnuARZX+lzZWvLLnfa/bPT8xuDbNhNJPqeW5oud1M/LIrw7+bQ8DGM9piueOnGKI0YTUMbohrMBJWkVEOCXAx11oUjWq9lEqlqe41F1VprxaAhasyN2LEKA5AzhDPgjMgQZIjlHLEDjD02Yg+Mic9i1OfYcKghnqVJe1RWhY1VvhF9dTn6Yjn60kZfSKhKCVVJ9CXqK9SXaFUSq/pyrEpimdfnfn4qC7QqRMuyPlWFqPdofX1dsFGVxKog+oLo/fy+BdFXRF8RqlJj5dU0U68xFojMUB0rOhZkiugUkVqZRKdizASoT8ZMgQyRzAhTRMYgwwhnYuQsomfAyIhMxMgUJTOGXCALqlnibCbWFWq0FCiNM96q80liK+PxqdHgxUQTQhSRuY2jjrCz1uokSZThg/iSBegvfF9+AZIb29tro5Nnn+97fvM3P/fFf/R333v3i1e7ndbxw8fm1vduSTXLJGnUyrMvY73QEEOVR0ynxc4bl/HdNv/Lrbt859k9RqKUkhBUsRp588o1XFFiZyW7a0s4VSajKURlZ3uVsvBkhec8z/FW2Ll5ld/90Z9ylk3q3PAY2U7b/N+++Td4Z2uDZw8e8tGf3saacJHCIlLPLwQv9LdW6e9u8niW8b98fItn1UynJqlmxg5yY+5E5G4MnKgRP5+2MIiilojYyiYmF8hAZ2LtVIJmxiVZUfqyYRJfueixNpKmgcl+WKjPCyzAwgO9wAL8BylTQcDqPKI2smX0ZW8uMVe0bdDJSw5TiRhb5BqPQX5ivWlbfPr9Z4++uNRsLH12Z9Mu72ScH57hnGIw8zY7cE54/vgA00jYuf4Kf++9z5N/z/PR4Bm1idPy0/t3+dpb77Kzt8tgNKbjHBoDG6tdBucTblze5vB0QK/d4dLWOrefPOPVrUvsD045Hg4pRIhGuZudUPy05FfeeJXLVzY5f3JMMZriUiFaxYdI8BFSkBD55NZ9BmdjufH2TT6/t5uudDtr//Ljj3/1x0/394YyectL83fW2+sfN2fN8332i3+LL+r5vOAtoXlTjkMQQjB95mUcdbyakpl4MQWH6ExEO8D008IbEImV+MqJnTpDVJXMQoKqC1iHw+Js7WUPAaJW1ro8mGpM0HNsGGFdTiJaTmbhq9/4cvn22++ms2zWCDFaDaGOxEMJMRJirN08RtDwaa13Mi9wifPsZ0RQX99WjRAVYvAINfl70Vio8aXhwxeth/pp5F2aNsxgcKZ/+K/+Fb4+ClLi7AxljGr1gpzWQ4VWNUTFEMWaqFFN7RHBgqgRE6JqoegsGqaoTFHJo+ATqDCmQmOlKrkVyaNq4aIWQU2ZGPU+BJ8aguCUVEV9atAo2lEhgxiDDC11/EyaxjrO8F9LnqXuKfyCK1cfbM0Ojv7e6921v/drn3vv3S9eubLV8GXj/k/vsX/7Magn7QghF7Bgmw6Zb1bX77Lz2mUm1vI7P/6QH53sMxGoxKKqNEXY6K/TLCKTszOu7u0iZeDsdMSr1y8xHs14+uyMRqfB8uoyfpaRC/zz73+PUZldkOd11+QffuWX+PyVXZ7df8CtP/0YwUMixKKuZjJWqAqls95jZW+D48rzLz7+mCf5kJkkYYqZlNgnYuSZMW4UDRpDtMYajTHGxNkQQ/TEWIZKMyuSi7GZBM2MdXlR+hLjvDE2XLQO1sknC9/zAgssCPQCC/yHyoNG4RH1ZBvU9d7zhsJVUbyHOFPESEfVTC+IWx6wzVmEg6JhfzgtisZhyFt//OD+W0vt9sprr1yqCcXhGUmj/pLXCDYxxCqwf2cfYy2vvHKNb3/lK/wPf/SvuDs+Ro2l0siffPwhn3vlJo1mg8FwSMtYssk53V6Lx/uHNBspg7MBp2cDrm2ucXf/gJu7O8SoHI+HYAznKFV5TnnrY3755g3evH6J8/0Tpifndb+JUXxVq+N1rJpy+OSQyXjGzc++ymsb63b9i1/c2On1239w587aQTHdWWm1/2jS5vsrs5VPBgzG/5YkOnDvnnD1quB9NDqSEDp0gQminTlxfnGHDqJTJiCdl2mCIhLEm0odzDvnEsU60ASRBB8NVg0iipUqhJjjbIZqjqVg6qr+lT7DyWN+7Td+vfPf/rf/z82gsWONsVIXrciLHaYeKdX5FRd+X+qxU+Gl+GXRnx8YnAcuR/20UEXiy3OtPzuDGaOSJo7f/Re/b/74j79jY1SJUb2oToGRqhaS2ACoBlUjqBgToyGg+HqsUA0Rq0ZUowYRLQXJa1uG5DFqkRoTBPVR1YOpEC1FyWPUIiaxTKJWIRgvRoIXiaEqMcaRU2BIQFVUo4hY1kQ0NUafP+pEuPVvYifQr6+93hsOb71hz4q/8zcuXf+Pfu2LX3j35trqchgPufuTOxzce1rvr6khFHpRcS4iFHmktdFn741rPM8L/n8//DG3J4dMROfkGVJRbmxfZsk5wnTKm3uXeb5/yMbKEssrXUaTjGeHZ9x8ZY/zLOfW4wP6l9a4/fQJx9MRTmrbxrIk/Bdf+ia/8ubrPL9/n1vfv0U1y0hbllBGxAoYqIqI67VZv7JFkTb441u3uT060pnYOMUMC3GPozP3gMMosUBFsMYSiAiBIAGRAtEcY2ZiYi5BMzE2l9KXbeP8zDg/NknAFJFjF2E/LFI3FlhgQaAXWOA/tArNpyTa6s+ZpDwhGGK0c/IsF3RI8mCtzjS4x1OMc9jG42rS+KP7D95Y6rzVWdnbIoYo4+MhNhWUiK8C1hq0rHj44UOcS7h6+TK//vkv8z99/zs8nJ2h1pJXJR8+us8XX3+TrrH4yYS1fo/9/SOuXd3m4aPn7F5aoyg9Z4fn3NzZ5PHRKW9c2qM76vH44CmVKplzPPZjfu/ePWbFNd67vIVtWM6fnUEI88IOoaoCYgXTEkbDET/97ge88sZV2bm6p3/j9Vdbl1ZXX/2d99/f/Wh8eLXXbG41O80/bsfdj59mT0+A4i/5xV0r0Y86wk4ZBzFKP45FpCNdRPVnitanCmgXYaJT05aWKhIzlZiWEmiYigIqSnXOqiBYRUId6GZtkBhCUHCexFRUWmHrlAmwYb610/Fosppn+aVHT/dbZ2dn4uaZxi8otJnHwc3jqz+t5kYxUucP169E7X2eE3BUBKISUWLUOi/6JRKt8+0gqtSdKUqj0eD6tVeYTiaiqFExgo1V9GFiXXIW0QKdE1RzUWoTUfHGGG/qudG6ml5RJ0REfERLVQqgcCLeqwaLeGvFhxgrUSmdM2UZtSTGSqKtkOATscEjLxJA9CIuZerAgDEjdS6Nz9M0wq1/rZXgW3zLDTofrx6c3n73iu3+nb/57pd/8xs3r+9d6/fc+PBQP/7+R0wHY0lbBjUR7+uljGkYfB7xFvqX11i9ssMngxH/662P+SQ7JhPwNsGo0rSGL7/1LpOjU/KTAf1Ok+HZgO21PqCMxzOy1HHztSvc239Oa2kZs9zmBw8/4Ww2qWvdNdIXx69/7st84+Z1jp884db3b1HOMmzL4GOESnFNiy8VmzbYuLpNbHf4k4dP+OHhY50ZE6aSDLOojyrRj4GHGsIAXDAGMaH+TDHWxirGComFMzbDmFyCZGJ8bqyWJrjKGOcx01p5dkmETljE1i2wwIJAL7DAf0gVOtbU44JEK9x8IQVGHHBslLW5Ej0vAOFTIq2ZSMBUsyRJHtuK74qwdGt02JT3efXvvvNWunZli7LwUmU5xtY8zAdFmgYblQe3HqAqvHX1Mvqlr/L/+f532J8NEGuZFAXf+fADvv7OZyiynNNJxubWGofH52xuLnN6OqLZbNBwhsn5lNV2i8HRCUuNlMsbW3VjoQ9EY9gPE/7Fg3tMg+cLV3ZYSxucPDpEgwdTDz9VVUSN4FoW1cC9D+8zHo7l+pvXeW93y652O53f//ijL/xg/9GlgY7e1Ub127vp+h/n5cnBaR0895f5Aq+tHOnVSIxiVQWmDFUV7UpXVSaMQUR78zt0ISqZqDalKSbkqEmlEoiS1OzOgNQKbFCDQ4IH23AhBCkRKRFTIlpXgyPa8W0zhJbAMtauHR8dpe/f+lCbzaaozsnxXHG29tPxE2tfKNAvO3zmu0cdO8e8J7BOZ5jnNFchzFdi9dxqnIfAxLkiXZQVa6srXLlyBRGDETEQBaQU64aoHhko5pnj1kRxUcRFEZwzPkatUNQoRAMmQgQVI16jVBipQMsophKRADFUqpVV8SKmDDGWEo0PaqpoxIs3wRsfEYlibJSyimJsRETpikpm1BgTD5vNwKNH/i+wbtSWjS98wR1/9P21cjr7m19c2fv7f+ezn/mlz+7trrg8c/ff/1gO7u5TzTIaPUuZhXqOIKkHK6scYpKwem2d5d0tPjw44Xc//IhnYUxuLB6IvmKp3eP6xhb+bMjk8JRX9jYpsnxulYpUlefatUucDMY8Pj5jHAKtXpuP7t9hkE1JxGB5QZ6/wt9+9x3Gh0f8+I9+jJ/MSLsWH5UYqfPWg5A0Gqxe3SRdXuYnhyf84cO7nEuMY5LJTPV+SJIPxXA/CkOD8y8+j2wkYiWEECubmDJEUyCmEBMLUVeUVst26cqZyT22ClhbDw4eNgPcW5DnBRZgMUS4wAL8H5DI8RLOtC6V3oDJnAgtzVvymFd8qwq0paXOePGKSIzS8EEorEqBajoqJitV5ru7m5tuZbkt2SSnyivEKLVN1oBRqqJieDYiSQ3Xd3dYX17l4fMDplWB2Do5YP/wkOvXLmMwjEcjjBgSa7DOcJEPYqDZaNBrN8lnOe1Gi5X+MqPZlCpG1DoKKp6fnzGdBLa21uiv9siyiiqr6gdxNeGLvraagDI8HXN2eibddkOubG2Ya1vbaS9p9M4Hw42izC7bVNel0fKtdHk0rabZX/pLfDiE9XWyuTRaS7yllqbSvjHavMgclrnfF5mRSoKKbagpC4ggNk3nVDaKxwgg1ko0VgIiXok5RjI05NgqI0kqMqvdbjOZTE63vvL1b37ua1/76peOT046w/HYNNIEN28xNGKxLsElDuccNkmw1uGSFGst1tWXRaT+vbUYYzHWYu08+s4YjHXYi/P69869aD00pGlKDIFOp8ve3i4PHj6Qf/Jbv0WIsUD1wKg8FMO+IkOJ5CJ4ROokDCNBlUpEvEG8iASDBBHxYqWKVqqoWqlSiZFKRD3gNeIt4kW0CmIrK1SKqURifTtCKWK8MdaXla+Csd7Yyhvngs1T79zMn7XbnidPwp9Dni/ea//4W99yf/Kd77yxVMlv/kc33v7N3/zSF7/y1tbmZnZ87D75yR15+sk+sSpwTYOvYu1wSAwa6yJL222yfnOHdG2Z79zf5/fufMRBnJEbQxBDiIHVdpd3rlzj/PkRDVW2VpYIVcVkNGa136MsPSKWybRgMM3Y2N2GTofvf3KHYTHDisER6anl19/7Cv/JZ99ldHjEre99SD6a4FpCVIUAlrp3SbGsX9uiu7HO7cE5//zjD/Qo5oxNOptiHlfG/UQTeztGPTHG5rWhXtUao1gCagocOaqZBptbYi7qcrG+DKUrK1vUiRvO1bF1R2mE3ssRgQsssMCCQC+wwP/ROAOGCpswVcii0NYXVW/SrnsOxEstIrXwQOIzH3OLC2K1cTodLsdA++rmpm23EopxLuWswiUWK3Vbmm0IsfKMzia0Oyl7mxusLS1zcHLKpMzAGFQMz44P6S8v00ybiAZiiIQq0GgkVCFS5CXOCGdnQ7bWVhgNx1gxbG1scjocUARPEEswyslszMnZhH5viY2NZbyPzMZ1Vbixtcoaqlqkd6khnxQcPjtF1bO+3OXq5qa5sr7ZLWblpZPz4x31Yck50k7a8Y2qN5sxq/5yJHpXWNeXSzgiIlqIaGGMFiI0VRmJUKoKpJKoCgliK8SCiLMX9NskdTxcEKIV40M0JUKOjTmaZDgKzhsVCN1umk4mZztf+eo3Pvu1b3zzvaOjo+bp6Zm4JMWIQaMi1l1wQRGw5oWdox4SjbGu6DbGzP3R1Ne91BGjGi/WYhfXxrl/em7hUFVK72k0Gly+fIUnT57wT//JP9WosUDlQEXvE+UxKiMsZRRRsYJBxBqrRggSCUCMhmiFqKoBY4Io3ojxGPUiEubrDA8SrJgqYCtnxCcipWAqNVQSYinGVsa60lhXRaUyzlc2TSuXN6okmZPn/f2/SHnmW9/6lmsdH299/969L7/V2fi13/zyV3/jb7/79udXrVk+evCE2z+5LePTc6xETKN+TUOluKSOCqwCJCs9Nm9eomg1+b1bd/nu0/ucSt0u6Of9Nle3dlhvtGlFkLJka6XPwcEx7WbKzsYak0nNXTu9Dp2lHofjCdpr86P79xiVGSKGRCNLWH7tM1/iP37nTbKzUz78/gdMzoYkjfroQiwVN1/IBm9YvbJBe2OVJ7Ocf/7RBzypJkxNGkdwXCIfRisfirEHCrmoBisWg1GUiJUyWs0xJgtIjsbcGlsY60tTudIb57HBIxJJkro0ZZLoQn1eYIEFgV5gAf6K+KJ/7uczYAT0hU68UKArTYyX2YUynQCQgCFUEmaqkkVCbzAa9kMZ21e3N027lVBMM4EIUVGZZ0Q3DaGsOD8e0e4kXN3ZYnt1nefHp4yKDIxQhshoOuXSzjbjaYYx0GqknJ5N6PaaGIEQIr1Ok+k0Y6nbJhHD8HzMcn+ZoMq4zIlYghGG1ZRnJ0Oca7C3t0WznTKb5sQYEAsGQX09LFdnEkeOn58xPD1nrd9hb32N69s7ZqnRWx4Nx9cn2fAVKzFtLLUmDdfLr5QTf/y/TxWTOh96qEy2YcPWaQ7GKM5FjFFEtJgvYOYKtXhSSfwFQ5UyONyc50q0EEWj+hhVA6IlPhREm2OrnElawkmAJTod15hOB5e+/LVvvvtLv/zL7xwdHTXPBmdira1NxKaOS7NisObTauxPqXD9Jxmxc1/5vPyvth9fRInX96urwW1N+ec2jpqI17cRQow0m02uXLnCs6dP+ae/9VvEGEtVDg32E7HyWNROxYgXjQLGqqhFo2jQGIQQIYoYjYgKGqyYoGgQVW9UvCJzwisBojdivUr0aqQMMZZqKOfkuTQ2lKWnVExpS186bZaJ5tV5Q31WK89/HnmWb/Ett7vW7Hzy0Z9e61Thl/+TV9/5b379c5//9c9f2bschufp7R/d4uGth6JVSdIWNEQ0gCQGsUr0QjSO9s4Kmzd22c8KfuenH/Hh8DlDEynE4lUxwFZ/hVfWNxgeHNG2lkQFXwaWui3WlpfYf3pCp9NGnGVSVPg0IXRa/Oj+XcZljpl7npcl4Tfe+zL/0TtvUg0GvP/d95mdj2i0TF3yiGBtnaYSvLByeY3+ziaHZcXvfPwhD7JznYrTIWZaGfdYk+THWPNUlKmGqPWRCAPEiFBFKMC8IM55RPJofBGsrXy0HpPV6rO1EeciB07hyYI8L7DAgkAvsAB/lQpWfsHv1iADuvMJMUoAaWnLeCpJQHJJCGKiQarKSmEiRVDfGYzHq6lJm7ubayZNrGTnGRpC3axsIMzjznzpGZ6OaKYJr+xts9Ff5eDojFE5Q6wl955HRwdsb2+hEYajCZd3txieTxErdFoNzodjksSRFyUEpZkmJMbSbHZodToMJkOCCl6ETAuen58znXp2tjdYXeuRT0vKWYU19WHz4JV5qQNJImSTGUf7JwJBdjaW5fW9y3ZvbS2NuV+ZjiY3ynJ6LUm9Zq2V82ExHf9cxMS/4QLmTBkOldEoMpkok21lapTVlyIGL6w0qSQaX3RWixMnuJqHQhSRiBWJUcRTmQpDgXElVivKZgXTCMv0ekk6mZxtf/lr33jrl7/1N945Pj1pnJ+fSyNN54UmDmsNYsAZg7O2rouTefX2nDT/LJWRn4mnk7lCWls16lbCC+Lt6qrvi4i8qDQbDa5evsL+k8f8k9/6LUIIlcZ4ZK25r8QnQIaqijEOIZnPTYqKqLEmKBrViIoQVTRKHWMXDOJrOwseUQ/6oia6ciKVRlOGKKXDlmKksC4WVQiFTaRMKlekaVGet0yZHfcrpk88w+HPJ0Bc5Kx/+9vftj98/M9W8+Hp33yvu/lf/5df/vrf/08/+95ndlrp8tNP7icfff9DOX9+Ko2mQUPEFxFFsKmBAMEbTLvB8pUN+pe3+eGT5/zuRx/zsBwwNUKhgtdI6hy7a5ssGUd2Pma922F9ucfofEK33WI6nZLnFUYMly9vczqaUTnLiMhHTx8xq4oL8rwqCb/5ha/xdz7zDvnZKbd+8CHjk3NcQ9Cqnsy0Sa2Q+wq6G33Wrmxz4iP/y8e3uDM5JbNOR5iyEPNMjbkt1nyiqgON0RusWIPgVYMRb0VKIyZXiXkwJo8h5thQYExJ6aquTXzT+Fi8IM9HVqEd4WxBoBdYYEGgF1jgr5wnWn7256HAspABHb1Qnj2VAMarGnAG0ADRJklZorP6ZqF1cn6+0natxs7asklTQz4tUB8wL2X/GgNl7hkPJ/S6TXY3Nri0ts7RyRln+QxjLCqGs/GI1fU1Wq0Gnzx+wsbqMlXlKX3JUqdLUVZojDjnyGY5qUvIphlpkiDWkFclpUa8WArxnGYjjs+ndLtdtrZWcNaSTfM6QC7Wtg7mQ27GCdEHTg8GnB0N6LYTdtdW5Y3LV9KtldXVyfloezgarieqKyvdJek0N86HxTD/S6SjvHT5TGEXRgKrLw1yqho0MV5VHCo0VbBewIm8vP1EohUTYmJ8I2jVMGVVOVdRpAEmEZaku+3SydnZ+i/90q+89q1f+dbbR0dHzePjY+Ocu8hlDiEQVdEY69N8u/kYUHReJz1XnkXq4cE5cYbazlFWJTHWUWyqgRg/fUximD92IAaPEcP1Gzc4eP6c//n/+z9RxVCKdUfAA5x5KkZyatE6sY6GGHGqiLFGoX7OdcK3RokS1BDESPBE76zxasWjxjvBBxEvMVYKpRhKhysqEwt1MdcQClc1ilSqYti2ZXZ8XDKZVHD25xZ3fPutb6c2HOw8/NM//dKrcenv/Wdvvvfr/9kXPv/Ln720fSM/OWnf/tMPzaMPH6KxJGmaOicbqdNK0joiMERDstJj4/oORavBH3x8nz96/AmHmpNbQzn3Ozes49rWJdaSlGo85tXdbUaDEdk4p+kcG2t9zs7GXLu6Q1Dl3pNDYiPFrXR5/+EnTKuyXhRpZNWk/Odf+hq/dPMG1fkZH/7gQwZHZzTatt6e86MORKhKpbfRZ+XyJhPj+P1793j//DkzsTq2aZmLnAaRu6rcU6OHWMmIGgWD1iMQwVqpECmDaC41eS5SY4tgKSlthXG+NLNQvMh7TpLIJI3wQBelKQsssCDQCyzw14RUj4B1JVNe9kOjrTl5VjNPX9AQYggxFoGYiTiqWK6eDM577bSdbq72Sa1INasQFLFC8BFVQ9o0VEXF4GRIt9Ngd32d7dV1hsMJJ7MxIkIVPEeDM7r9Ppura5ycnLK23EOi4L2vvbmmjqbrdlp4H1jqtplNZqyvrtDt95kWGZmvCGLxoozKKc9PzjEu5dL2Ou12g9kkRwtP0rJ1TJqve01sw+JSIRvOOHx6AlrJWr/D29eu8treXrMh7srp8emNaTZZdkbzlfZSZZc61Ww2+9/TYqh/prmQM2G0IvQVQjBLqqbQxLSZm4odAo2XUlJqq0eFaBSJVN4Hsb4yscI5T+4iTBSWhNSl5eRs+evf/OYr3/zGN9/IsqIj1piVlRVZ6i2x1OvR7/fr86UllpaW6C0t0Wy16C8vY4yQ5/U64UUNN3U/IjEGDEIjbbC7u8dKf4Xl/hKr/WVWV5ZZ7q+wurLCyuoqqysrrK4ss7KySr/fZ3V1hSePH/Fb//NvoWihIkcKjyTKMzEUeAwiSVRJBXEKRmvFOUTRIEIQkSA4b9V4BW+wlcF4MD6KVoipJJoKoQjGFi5qYazJNcTCSMhd1cwbjbI46/VK9vfLuVXj55VP8xZvJb2VXvdKI+58sv/D11qZ/+bXLt34jf/y69/49rfeeO29VSO9J3fvy63v3eL86FTSpmCQ+WJCEGsQZ/ABgljaWyssX9nieVHxLz66w08H+wwlUlhLpUKMgbXeEjc2dwjnIxoR+mlKagyT0Zit9T6+CpyejGg2U9RajoYTXn/3dZ5Ox/zo/l3KGOuBQY2suSb/1dd/mW/cuE52esyH37vF6PictCmEEAHBNgwalBAN/e1l+pc3mCYJv3/nHj86faJTYxliqqkyCMbeV2PuYNg3kkzEaqWYKAYsRLFSIaYIooWIKQihiMYWwYYCayvC3LpRF6XUZSmHSYQnC/K8wAIsYuwWWIC/gj5o+TlyIJ+25z0ysBcZxMDKCwJtDBrnC9q6agMxAeOyEn06ifqTKEnPaJn+wf27rzr7euvN9RVZFuHsyQkafF2w4ut6YmuhnGXc/skdXn0n8treJX7jC1+AH/yAW4NDxBiqqNzff8KN3Su89Zl3eHT3E9Y7LUJVURQlZV6RWIv6gEXRomQpSTg7PMV1W7x26TL3nj9jmE3JEIIYPDP+4NEdDgZDvnr9KpuvXmL8/IzsZIxIrMPhjBDn3mjXtlB4Hnz4gNODU3n17ZtcfeUy/8VXvpS8sbOz+wcfffz3frr/5J2TbPTPOt3O7/W2tj4qD5PxPvvVzxEw/Qu2h/5s/XpSt6fPEzm6YmLUaEBiLfuKiIgoagRRVdUEtEIioE3Q/OcXSDvhRapx0en0zjudzvGbb7y2/Oabb7ioEaROOxFl3jSoaC0ukxcFs2wmjx4/YnA+oNFo1iUpL9oFjcGIoSgK1jc2eOP112k2mzQbaf0aWi5i7OaCNWJqqwcRjIONjU2MNTFW0SOmMkiwIEHVOAcaUS+EGKNHVaIYjEqwtt5nDS6IEEECYr1I9BEJIQbvxFQQKzFUErSwaOGtKyTEwrhQuKrKx01bcLxScXrP/yKrxlvgpv2rbc/pihudv1KG4otfW7/69b/1mc+8+flrVzfaIXRPnz6z9259IqfPjnEO0radF8rUdoiodfZ18ILtduhtreD6PX54cMyfPLjHqWYURiipjwQY4PLGFh0VypMhm702m8s9nj4+4jSr2FxdQRCyrGDvyiaDccbB+RjTbXL76JCPnz4ioPOGwcCma/FffP2X+fqNVxg8f8qt733IdDDCNWqCH71iEyHmii9h+VKf9Ws7jI3jD+7c5UenT5gZq2O1ITfmXI15pKq3EbOPyJBYVQQXCUHFuSAQgsS6tKYmz6UYU2JsiURPbjwmCxgb58b4ehagzqmPi9bBBRZYEOgFFvir3lb48yRaoRkhCCYKxkQ0C2jDoKGujK6VT4U8IumMlKfTQn9kVDvE3PzL+3duJvaN5o3lJbMmwumjY2JVYZuCzyK+AqxSzDLuf3AfZwxXNzf4B1/6Cr/94x/z06PHtcLsPbce3afIc9aaLbKgnJ+OuHllh7PTIc1mwnSa02w3GE9yNjZXcInlfJYzOTzh+tYl9gfHHA/PKRQCQpDA+6PnDD/K+eor17h2ZQvXSBkfDiFUJKkhVLV9gSgYJzhrmAxGfPDd9xmensqVm6/wyzdvpK/tXFr73r0HnT+8/VH7k9PDz0wm01uu0/vx9XTlVhk6z/ZHSxO45f8NiMDPbo/nVtkwOgTtyURF2nEGkANaSqMRBU1iiZqaPNeugJK6gg8QYjTgDeyA9wY3VUjyD299cPDf//f//b3ReNwX1PoQGzLPChcRomrUGFUQKatS+v2++c1vf1uNMfIiiUPEEKpwMWio83rvWM+c8Tv/7J9x//4npGlC9HWhipF5bjRgnCWGOmklSROOjo9j9KGKXifG6sBamQYIDvDU6SMposFqCEEkqY+CeGKtUkaJnii1Gm2pQlCPhAojXoJWIlqJkVKcFpXX0piiMJUrZ9ouaRYlx/0K/gx5BpDX19Y6UWSncfbsc40Y37vaWXnzm298+drXX399b7vTWc7Oz+ztuw/08e3Hkmc5jaZFbL1QRAUxEKLBh0C0jvb6EitXthiEyB9/fIfbZwdM8FRGCAgxRjqtFmudHmkRaBjL7tYqw7MhTx4dsrbSY2mpzeNHB/R6HdY2lpmVnueDMVdfv8ZPHz/i8dNjjAhOBBsDl9vLfPsrX+Pzl3c5efSYWz/8iNloUhPmqBfWJWsNvhSWtvss720yxPKH9+7xo6PHTER0pCZmxo6Dkccx6m2sfYxwRow51lUxhIDUg5tBYkWQSsSUSChFbCFiy4apqqK0HpMHjKkHJV4M0wL1AvIvXHQusMAC/KUybBdYYIF/T4OFP3e6aiC3rFYW7x2+kRJ9AmpQNS9xP5PE0FQNq00xb3R98dW2hq9ccZ0rf/u1NzrX+z1TnJ8zeHqK92VdBVx6ooBLLDFXbCPlldevsHl5l3MVfufHP+U7j2+TGyFg8DGwu7LOG5f2mJ4MkBDpt1NmkynGWKyzhBiYTHMwwurGGk9PBkirwbkvKazw5OgADzixJETaqqxJk89s7fLe5Us0q4rRwYByPKlzJWLA6LyFz4IVwSj4XOmuLbH36mW2dne10e9znOXyJ/c+qf741oeHd4cHP64kfV9b6e3K2AeFTffHpjodDAYzPrUG/CKYT09XDVu5parsCyvHKHYMGiwx2GYzOo2J0xhdqbmFVKBURDyVLeshwqIkSSrObGQtCmWZYkyfSX6TUH0JzBdBr4J059u8qim6FkBEbAMtl6+9+ub6P/nt325PphP34UcfkSYNqX3PdSuh9x5jLN57di9d4utf/Rr/zX/zX/M//b//XxjX1ug9F5WEL3+ki7y4OmJMZZPkXJGHovoD48xPDfrEBylcwyZeY8vE2MKYRghqrbVaq83RAyHGemgQxDsxlZdQSTAVJpapmKoyvhJvS2N9KdZWtkgqa7Nq2GxWHPY83HuR7Xwh3lxfWWl3jNmuxtlNV5af2Wv0vvLFmzff/eabb+y+trXZKMdDfXLvMQ8+fsDsfCLG1YtCDbVdQxHEzYdUrcF1mvQvrWGXu3x8eMr3Hj/gaT6kBLwxhBgxwFp/ma2lZcrzMT1naNuUhhHKWcn6apfReEaeV6yvLbG83OPuw+esbm9wXnkOpmOenh4SUBIRbIxc76zxj771N3hjc42DBw+59cPbzMZTkkb9Ftag2ISLgcaVvXXW97YZG8sf3L3HnxzeZ4Lo1DTiRHQarH2skVtB5TapPSTqlBhLLB5x3iI+SAg2SAVSisRCjMkrY/OG8WVhbUnhqnnqRsTamkRbG2k0Avv78aX3ycLCscACLDzQCyzw12WhKp8OFa5AN0qdDFEKmtS1yeg8FaI+jwgRgkTJsElmNMZCy/7ZaNxeX151a/0eIshsmBFDqI8tiaARTCKEvOLsaIgYZW9rjStbW4QSng+OCUSMsQyyKYPpmPXNdZwYRqMpzlmsFfKyoqo83V4bHwLTaY5zDg2RRITUJvSWligrT+FLPBDEUFBxPBkzGOWsLi+zsbFcR+pNKzREXGJwqYVQEw1RSJuWKi85enLC8dGxmOjZWl7itZ0teffalc5Wp3+1muWfHY8G7/iy3E2Mthum5dppy/QalnFZ6i8gBi8vXoBdWFcQUVQpjFEotea4DdIUBS+oF0sDC1isWEk0hFAfDsfX553546saKieJcyrNRp4kydiY5Ngm6WPr0rti0x/bJP0Tm6bfTZL0R0m780ko4/mVq1cb3/6H325n2axxeHAgxlhQFVUlhMCLPnLvPSvLK1y+vMcf/P7v649/+EMa7Q4RgnVJJc4VxtjCJa4yzlV17rItjHUzm7izqPIIw0fGmTuqPItGpkElQjSIsRowYo0YQ7RighGpECoxprDWFpFYJCbJxWimUfPUSq42ZhpNZkzMbGJyW6ZFQlmOE62KRsPTbAaGD14onXaPvXRvaam32WhsF8PT102W/a3Lrv2f/+rrb//aP/zmN9/+W++8tbqROvf49id8/ONb7N95Ij7LxTWEKDrXTA1qBJMYggrqHJ3tZTZv7DFQ4Q/v3ec7T+5x4DMKMXVHvEIrTbmxe5mk8iRVwHlltdPFokzGM1rNhOADKGxurTKaZhycDnHtFrkz3D18xvPRGSJCIpBG5e2VS3z7K1/j7e119u894P3vfUiZF3X6zLw50lpBIgQvLG2vsryzydQ5/vD+A75/8ECnxjCRJE6UTNP0KCB3YoyfoHoEZorGwoqrjDFB51GBBuuxWonGUowpKzEFPpQh2opgAjb3GBP7IrEQ4SLG8blVGOlL9o2FCr3AAgsCvcACf21U6Jeu34R+kAsBUUup6/xk7oXGfNqaIdGIq0KMmY/MRIiZz9tHg+FSr9V168tL0uokzIY5hIhLTW1gvagwVoYnI/KiYHNtmVd2dpBgOTg7pdSAGMOsLDkcDNja3qbVrPOgfRnq5sLUMRxNWFrqEKkzpH3lMVIXufiqZG11FWstkzzDowQxVBIZlBP2j09RtVza3mBtYwkfIuWsQn0kSaVuRRQg1Ie8k8RQZQWnz0/k5PmR4Eu5tLYsb1+9mty4tNNcbfWWpAy70/H4zTIfvmNVLydp07TSlTLpJmWWZb/oNZ8fuj5WhkOYTJTNzZoIX5wqrbyPaZUICaB1Kkf9KEIIUes1TUORSi/U3prmEoMJriKvfDgX4Zmq3lPkVgjxw6j246jhExv1kU3ssyqfDlbW1uXb3/52vyir/vHxsUucreXVeTFKncQBGiPL/T5XLl/it3/7t/nxD78POK9CHoOeq+qJxngSkVMxchpDOMbaA9XwWJB7au3H1shtFZ4iDEVMaYwAaolirENEDfOq7lIJhUAuSB5EMgk2Vwl5IpJp0FyR3EjMbGVyR5lPVcuyacoiScJOksSeCL0QpNfrmUajkfZtv7u0VG6F0fEX0zz7T1/vrv+DX7nx5t/4za9+9c1ffeettc3UNQ4fPLa3f/ShPPzgvmSjiSQtg3FCKOuMZmMNJrFEhGgMreUlNq9fIl1b5qfPj/i9Ox9xe3zMRJRCDF4VQdlcWWO9s0TqI2FSsNHrsdRuMRyM8VVFr9ui3+9xPpyyttpnPM3wCL2NVaYo944OGGQTUutwRJpR+dLOTf7RL32DK0sdPnn/Nnd/epcQKkzDEEPteRY7z/+Ojv7WKhtXdiibLf7lvbt87+A+ExFmrhlnxuYV5giRTzDyQFUPEcYIubG2EiPBhuhRauI8z9dGpBRji2h8RbQlYj3GeYyPGBOLefY5xijWKhMDjOKn8xgLLLAACw/0AgvwV90P/QuGDO8Jz/eULRdRDTVZLoTYmEvI+sJ2AEisJBQYPfUQY5AYER4VY37/3p0b3Hitfb2/ZDZfEU73j6iyHJOA2vqhxEIInmefPKUoSq6/fp1f+8Jn6bWa/PMPf8xpKMAYKo189+MPuLK2xfXtLYYHJ6ys9Dk7HbC80mc0nhGBsqyoqopWr0PqHOQRCk9XLJfXNjkbj5iVORl1ZnQVM6b7n/D0/JzPX77M9WuX0PUZZ/vHVHlOYrXONp6TRkVJGkIoI+PjMz4+HfL84VPZvb7H1t4l+Qdf/mLzG2++0freJ/e3/uTenVc+OTm5MRqNrqu1P0m9+2mvu3rnlPJkMmllcFz+gqHDAAiPHs3JxFXDTmnwPuK9dVJqKJsxRokxrdx8OyhiQktMyMTEl/ylEWPq5kPjQ+V9QWychzxamhIxZUEzKRi6CgahBGlu9psMQ+mMXWo1mrsbm5sbW1ubDiSNMVLL4y/tLDHSSFPaDatpmgAarJE8+niG8kycHIt14xhiGVUqk9gKJRdjJ6oMJYZTNZwFbyYuNQVIpB6U9EpExKiilSiKxYP1YkzlQywlUhGlEtR7qEySejGlN3nqXZJXzqWeNA1Yq+wDO0GKonCuKFpLtt3ta7kZJoOr6YTXr3fW3/nc9Vfe/Nobr117ZW21LUUhZw8e8fDuI06fnaK+IklqF1OsIgiYdN6ymBiKUtEkZW13ne7WGk8nU777wS1uDw4YEShEqOaB2ok1bK2s0xGLLSsMhtVul9H5GFFlZ2sNDYFslnN4OGB9YwWPkIVAe3WZ06rk/cf3a8uGsZjoaanwzatv8htf+SJLRvj4R7d4evcJSkCsEEMdVWeTuYvGC6uX11je3mBoDH9w52O+f/CQMaoTkpj5kAVjj8Tah4H4iMCJMXaG1O09MUa1lhic1FnbwZQgnyrPxhcNY6pCbIXJ67KUen/8dFF4oT7bhf95gQUWBHqBBf7apnP8HKxySIQorNQkukPBNDbmBPrCziG18mmKYOQsSgjTCKLofjmxv3f3oyvxxuvdV1d6sr6ncrZ/TD7JsE1BRfF5RKzBJoazpyeE3HPtret85ZUrdJpNfuf9n/AoO8cYgwcenR4yrUp2+6s8H02wxlAEpdltUhQlqspSq8twPKXZbBHLkjRJSIqSpeU+VoXzPGFWzMhDIIohEvhgcsjhx0O+ePkV3tpeZ/O1XWYn50yOh5RZQWJNTUR8JFYgVkialhiU4bMzhkdD9jf22bm2y8blHf3bb77O569d63y4//Tmd27fvXL7+PlnTrPJj0rcdzbarXurfX1WyvbpLM7GnVEnf87z6udSCOZK3CPlORFuCuRhtFUZqspTVR7ftmg0bQBrYmZmAeMDacNz3Aiw/7KaV8JOXg8YRiE3CucvBuhexPCZTgiM4Hw4OH/yT//pbz1od7t7qtpApAuSaFRrjCHGIAgYEUJVsbm5FfcfPw5gZ4g5Bv8IkQca9cBYO1IrOcRSVUqEXKJmIiYXTIaGAkslIb74e40650WjC0ruFMEl0QcfUhFfIZVJqKTC4/BiYhBDMDlBJInGzoIxNhpjdCtG8WVpfd/bZJi0uoZl49kupsdXOtjXr3bX3vnGa6+//fkbV7cuL680XVHIs4/vcPj4QM+PBuJnJUlqoVkPmcaoWGdQqQdNyzISKqG3s8LypQ0mCt95+JQfPHnAYZhQChRYvEYMSqfZZrXTY7nRZHJyRrvVZrnT4fxswNrKEhqV45MB0QdW+0tsbqzz9PAErKW1ssTdkyOenR0TmVeux8CyafC333mPX3nzDRq+4Kc/vMXBw+ekDaEKSqwLQkkaQvQQKmHz6jqdrVUGRvgXd+7ww+MnOjGGqaRxCpmKPQnoYzH6CDXHYpgYkUqiiaAqVpQQIyLBI5VIKMWYAjEFNhSUriyMrWrbhg2IxBcV9hfDgxcDhI8Wto0FFmAxRLjAAn8d328vWwrkU3X5qoGyTnXol44YLSEkxEaKhgRVl6JS1ndTUElUU9Wwkvpwo0f8Uo/w9Uu2ff3rl19pv762bNKq5PTREWWZEyUSEUIVMa6OVCuzQLvf5errV9ncu8Sd0wG//aMfcW90RIFQiSWoZ6XTY6u3Qs9ahkentFLHUqfNZDKh3Wrhvae/3OPgcEB/ZYlpllMC4yLDddpU1nI6GTGZToFIKoYUpaNwubnMezu7vLO7RSN6Bs+OmZ5MsESMkboUJCjGOaIPGFOvRXypeBVay122Lm+ye/0qzf6KnhWFfvTsefX+4yeTD589OXmSDR6WmA+CSX4aG8kdm7YPq2DG5aQsTjmt/jVxXvW22tuz7FeGjXmD4bFRaAZ49DIh1n/N5+svUv4S6C2RhCtU4ctY+SrwhiDrQBekIXUnYn0MQeqpQCPGhxAmMfLcJe42Rj4S9FGMDIKYDIcniDp8QMTXKQ3iRYxHJJSIpkWhNBBIBVWjLw2tioiCRDHGI8aLKYMYE8SYKDNREBWZKnSBycURllZs2V7Dp2FadbTMdoTw2grJ597d2n3zizdu7L13+fLypaVO22dZcvLsQE6ePOfo0bHEypOkdS21D3WzJsK8GEgIQQhOaPQ7LF/agE6LO0dnfO/BQx5nA6aEurlF50ctrGOjv8pys83o+IR+q8Var4cvK8qsIE2EZrPB4GzE7s4W3geKsiIrK1yrQX9jhY/393lydkRiDKJaq9Vpl7//pa/xjdduMDs+4sM/vcXg+SlJc955jiLOICihjDibsLq3ztLWOmch8ru3b/Ph+QETsTrCamZMpsacqMijEOJj6+xzFTMg6hQxuZVYBKQUkYIQC5eYIgSTiYkZYorKhwKxJWauPFtbDw2+rDq/OF2oz49eDA4uBggXWGBBoBdY4K/d+838WUJ91UAQtiqD9wbvHSE4QiMh+hSNL8wY8zi1mkRTamqtX20o15c0fLWr/ssb0rz5zWs3Wm+vrxpX5AyfnTIejLCJJYgSVYghzMtXwBrH1beusHV5l4Os4n/94AN+cvCIKZHKWKoYaIjl9SvXWGu2OHl2yHK7SafZYDbN8MGT5yXNZoOqCogBmyYUMdR1377CtNqcTEZM8lmdKoHBSqCl0Cfh1f4G713e5cbmKmE04fz5KdPBBGfAmpqm6tzG8KKhzxPxHkKAtNdm6/IOm5d3WNnapBDD/eMT//7jh+MPHj06ejwc7I/VPyqMeYBNHmij9TgKBz7aoW/67PS0W71ELvQX50f/mWzpf1s1T4AG7faKU3tVVK5rjHtBpW+MtIxqK4q0NWpH0a6gLVSCQUdB9blo/ETEfSIS9r135zSrHGnHeTmPeSmNIyImwmz+t3Zoz/PGVWNNnlvMy2OaqKqIFIpIlFyiiKmPc3z69EU12jQGl6Qxbdhmqym+U41GKz6EzSXYu9RcfuXzr1x/5d3LVy+/ur2xsZIk7Ww4sIODYzn45DmjozMMkSQ1dYa119rxn8x7hExt3QkIzeU2KzvrNJZ7PBlN+f6jx3x0esCQqrZrYAgaMQLtRoutlXXiLKMplnaakIrgi9pu1G40MPM2wBAjvV6Ps/MRSbNBq9/jNJty79ljihjqchRRTFRe62/x97/yNT5zaZPTp8/48Ae3GA+GOCtEMx9XMOASQznzpEnK5itbLG2t83iS8Xt3bnNncsJERCe4kGEKL3oq1j1VMY/ReKDKGcgU4gyR0mBLbJ2yQTSZiMmROBNjs8qHHDEVxpUXto2X0zb+DHG+UJ9fJs8LJXqBBRYEeoEF/lqq0C+dbgrkNenZKCzeW0KoVeiQ1gRaowM1LwKJ50q0STSmqmY5jdVrXfVf6Wr42rokV762d73z9vqqNKuK8fGA8dkEkyg+RMI80MAllqrwKIZL13fZu3GV3Kb8q7t3+d/u3OJcS7wx+Kg4Max1e7x19RWOnz3D+linU8xLQhJX24etM4QQa4IblbTZ4Hw6g0aKaTU5OD9jls3wc5KSEmkorJkmr69t8sbmJpc6TXSWMz4eESY5+IBrGmIZCUSigPcRUjNXpKGqIq7VYu3SOjtXdnR9c0Ntuy3H46l+cnRS/eTRo8n9k4Pn+5Pzhxn+gZLs02wcqnFHwZmTAjPIYjbsdDqzw8PDCvhF+dL672F/SFla6lCaHtF3EucS1Zj4SlM0trDSNUZ6eO1EidEEGUYjhxh5RimnMHo5vk8+PbKxVy/K/gyiQBRWgyGEudk42o62TYzB0qoVaY3RkCONRmpVo3UxJiaaZmJDJ430JMae9UU/+qIvsLKTdtavr29tv723t/v23pXtS/1ev6mxMTo5k6P95xw+PMDPcjEaaKZ1rXX0ilaKOKlXSgmEUgkqJO0GSzvLNFd6DKvAh8+O+OmzpxzGCZmBUi1e67eBM4bNlTXaJqEYjWknKd1WEw2KLyuMQL/bJvjALM/odDpMs4Jmu8Uwy9m+fIkPHn7C6WREFQPOGGyMtBC+cuVVfv0rX2GzkfD0k4fc/fEdqjzDpoYYXxTXCGgkVkqj02Jlb43W6jJPZwW/d+cj7mdDpmJ0bJzPxWZeOQd5rsJTEQ416plJ7Dh6zYyVDOp6bhEpkFggJpNgZmJ0VvmQYVw+V54rrP2UPBtTl6VYWw8NPvoZ28bLlqWFlWOBBRYEeoEF/toT6LkqfVV+ToW2hOCIMSE2krmVw37qiX5pQNHF1BZhNQ281pHwlSXCN1ZU9j6zttv88uU9aYdKZmcjRsdDggZIDCEoiqBmnq0bDatba1x/6zraaPHTZwf8y9sf8mg6wBtDpULQwOWNLZbSBqmPGB/oJCkt5zg7GdLpNCiKAoyQpA4fApNpRm9piWlZMi5ymv0eBXA0HDArc1DFGUuqtSK9SpM31rd4e3eLjUZCdT4jG0yppjloQKVWK32sCbpGxaaWoBADRBUUQ3+tp9t726xurbO6vqExSfXp2Xm49Wzff7T/tLx3eDA7KoenBTxRSW6bNLkTbfKgEn0+CzIIeZg2aJTHHL/sX47/Hoi0/Czx/XOuX1uznAK4CIfVv6WSOB9O3XOsZW6pqhLv00aMPk2S0AzBNq01TVvFhmhstRPXdcKSVNWaVvmmi7qTatjsSrr22tal5dd2dtqvbW83b25tJk0jiZ9l9uT5kXn64KmcHw+QEMQKWCP1SUB0ni6CQqxLeHAG0oTe+hKd9T6TGLn19JAPnj/jwE+YCeQiVFEJQGoTlrtd2jZB85KWcXSaKaHyJM4Ro9JIHGVR4ayhrDxLS10CyjArWN1c58nglPNswsnovH4rieA0smob/M03P8t//N67NEPFnZ9+xOPbj7ASsQ1DlQcigjUGYiT4SKffYf3KJqbb4+7ZkP/t/h19Wk2ZGqNjnM+QabTJAMNBDHokxpyieqbC2BiZGpVMkLxuF5QiEAui5CI2ExOnlXEZNYEu5+T505ruC9U5jT/nd37ZPrQgzwsssCDQCyzw1xbmF5PpuQq9E+QlAm1rP/ScQKfRkasjnZPo8uLL0CQaGzGG9VR5raXh6131n1/FXn1rabPx1WtXTB/Iz8ecHQ6IeHDzwaegGFt/FMQSOv0OV9+4xvLWJg/PR/zuB+9z6+QpGRDmlo4U4dqlPfoupRiO6CUpViFNHZPxlFYrZZZlNNIGRoS88DTaDYKBcVYyrXI0bUAz5fnZCb6qUIVEhCaRtgrrpsX1/irv7O2w1mzgRzPGJ0PKSY5KJKJEIqpCVAgKqME1DKpKVXgQIW02Wd9aY2tvm+WNVbpLfWaKPjk501v7T4rbT/ezZ+cnw5Nydl4SDoOkjzUxd4J193zSeFZgziTIxDd8dnZ2VlCHRcdfkKzy1+2z38Be2u+PG2Xp2taylEhcVe/XGmLWLGyYEFcTjWsuhlW8X0nQpb5Ne7tLy53Xtnfbr1/ebVzfWHfLaWJDntvx4JyD/SM5Oxro9HwsYe5vds6ivi6HQSNJIlgrELXegcVg0pSljWVaqz1GwfPJ8RkfPnvGfj5kKpEc8GLqoycaWVtaZrW9hBQllJ5m6kiMoD7ig5/788PFZkqcJW02ODg9J4jQ21pjWObc2X9YDwqKkCBYjVztrPD3v/J1Pndll8nJER/+4BaDgxPShtRtkhGCj4gV0sQSM+itdti4tk1otfjRkwO+8+Q+RzHXmZg4EltmmLGY9DTEcIyVYxVzLqIjvE4lkSlRMqLmOMlAchHNa/JsMiRm3roZNmSUrsAW5YXybG3EuVjbNWDuddY/x2q0iK9bYIEFgV5ggf8z2jiqP6tCx2iJ0REbjhgSUEcSHZpYyvKinjoBU2lsorLhgn+jK+GLy8T3llT23uxvtb+4t2tWrZFqMuXk6Rnel5iGxfuIADYxRB9QDy5NuXRjjys3r3GSe/7wzm2+++AuQ62IxlLFiDWG5U6Hy6sbmLwkZjnqA51mA50XgDjnKIqSbrfFdFZQxYB1lqTVYFZ5clVmRGYhcDY8I2JwIqSiNIBOFDZdm9c3tri5sc5qIyUfTRkdD8lHM5CAmftQoxpiNa+hsSBGsVp/xFVVxIql2Wmysb3GxnZNppu9nk59JU/PBtzZfxofHB/k+yeDs+P8/GlO3C8xz4OzJ2qTM+/sibrkcBZlP7hwOBgMRv+ByLP8Bakuf+lF3N7eXqMcDJYo002bhEsWuWxi2E2MbJtQrVP6VadxOcUsrSad7qXV5c619c305tamvbK6alZaLTHBy3g01MHBCWeHpzI4GVIVFdYaXNuiIRKriGAg1rFudu5rVwWN0Og1WdpYpre+wrCqeHAy4P2n+zzLRozwlFYoVPCqRFW6jSarnSV6NsFFJRtNuLq3zWgwJssyer02PtT7Z1F5nK2bNFWEcV7QXV1GWg1+dO8ukyoHalXcxUgKfGbrMr/x5a/yymqfp/cfcO/9u2TDCc4JYkxNnAVsIrX9RC1rO6ssb69TpCk/ePKU7z75RAd4xtgwFZMXxpyruBMx5sSHcCYiI2PtNMYwE5Esxpgb6zJq9TlzIrMQNROJM8Rk3tgXynOBKUqcq36GPFur7Futa7rv8QuU5kVxygILLAj0Agv8n4pEv6RG35xfzufeVW/mPtUXSrRDmzWJ1piQuHqwUEuhevGwiUND02pYTa252ayK93qEz3dV9641V7pfe+UVu9ttUY3GMng+oCoKJIWyCPMPA8U6QYNCdKztbnDl1WvQavHTZ4f8y48+5NH0DC9QIagqG/0VukmT3ZUV8uGITuqQEPFliRWDtYaqrGri4YSyqDAuIfMe10zJfKBylnHwzIInm03wMeBEaBglCUob3PDWYQAA2eZJREFUw1bS4/XNba6trbHsDDormA5GFNMMX1aoAbEGFQix9tYaEVxal8jglVgqISjiLJ1+l5WNFd3cXWdtfY3OUpesCnoymvJsMIh3Dw/Cg4PD4nAymox8dT4K1WGGf1ght6J1H5tm8si228d9Y8avH/5y/j/yP4a/4vucvcrVRPvnrbKQpdTouiXuOI3XtaxuEqobDr3UIVntJmmnnzYb1za33c1Ll+zu6pps95dM2xoJ+ZRyMuXseMDp4RnT4USmo2lNKtN5ffVcWRYRNNZHOEQM0UeIYJ2l1WvQW1+mvbLEVJV7B8d8fHDA0+ycMZ7CCJXWjX5hvhhbWVpmKUlIKiVmBf12CycCRLJZTrPZoNNucXRySqPZpL9cl6KcTyc0Om2STouDyZjT8YhxkSHGYYm4GFk2Cb/6zuf41XfepuFL7n5wh8d3H0P0pA1bDzuWEVElaVhCGbDGsH55k7VL2wyqwB/cvcdPz/Z1DDoi8TNjsmDdwKOHqnJsrD2PMcyMqVXmGGMhInW9u9gcNLMisxh1hpipmDgVY7PKxhmlLbBlibU1eXYufKo8/7mq88+T6AUWWGBBoBdYgP8zWDn+zVTo+aDXhZVDY0ISU6JLEtRWVSU492kNuGpKFZYbYi63tXq7E8Pn2xpuXkq7S1++fNW+vrpiNJtx+vSEbDiFBGLUedS01uqaV6I3dFa67F6/zMbeJR6eDvnf7n7MT58/ZkokWksZAhbY2diiZ1NSVYrRiJV2G4kRJ6aupA7KykqX48MhnX6bKgTEJYzLkiJEkm6bia/IgmdWFcxmU3zwODE4FIfSUsOG6/La2hZv7Wyy1kgJsxmTwZjJ2YTKh3nsnXxqSwmxfqF9HeH34lMvBCWGQJImNNoNllf7bG9vsr61ztJKX72xTIpKTyfT8PjkND44PCz3B2fF8/FoejQbD8aUDzP4Tg7fPYGPgXPA/+N//I8/3cL/Xf3Pf/cfeMf6xy/+/cf1n3Dzf/gfkunBQS8WxZat4o0UfSMhvp4iVxvYrWXX6m8stdvrnW5zb3ktubq5YXfX12W53SY1IqEsmY6mnB4dy/P952TnM8qioCo91pn6daW2NmisO2VQEFMP+cUghKAk7QadXpveao/GUotpFG4/P+b20QEH+TnTeRGKR+sBQQRnHb3eEv12h5hlJAE61tFtphRZRlmUtBpNrAUfIkUVaLdbdHsdDk7OmVUVr715k0dnZzw6es5gNiVQ52onKFbhle4af/e9L/D1V28wPjnmgx/d4vjp8byTZL6gnBdOJtbWz83VyvP21T0OphW/f/s2Hw2fMxHCudoyM3YSjDlVY45i1BNVHdrEZTFoAVpojBUiJcaUIAUieSI6i6JTopmI2KmYOK1szJrW5nmZFNi8wphAmvo/hzy/sGcsvM4LLLAg0Ass8H8ZK8ecUM+HCZlnD4d5WsLPWjlSNKYktkGMKahDMfhKXupHsmmadF2oLjkf32zH8r22+jc3TLL6mY3d9LOXtqSjyuDglPPDc8TxaZMaipi6WjtUik1Tti5vsXNlD9vp8oPHj/i9W+9zUEwIxlApBI20koSdtQ0ur65yvP+MzV6P2WjK9voys0lGXpRsrK9wdHxOJDKe5XT7fYbZtE4/aDSZ+ZLO8jKD6ZhKlNF4TBk8VgQLJCgtFTZsh+vLa7y2vsHu8hLiKyZnY8aDET6v0BDqgbVk7rWdRwxr0Do1IerchxuJ814RiUKjmbK0skRvtc/a1hqra6ukrRbRGMbeczKd8ujkNByOzkfHw/Hjg8Hg8WA2fXaWTwdTwmlGPJrCQQWHOZzlMAQyhOrf+CNXL/4RwO2x57K1zHnvrTFGjTGx1Wr5ra0tf/369Xh0dCQPHz50nJ83/bDserJlgbUU1gU2LGw0kfUmdrXrko0l19jaWFpa311bX9pc6jfXe123s7oia52mJKoqlZfZeMr5cMT5yYDhYMx4NKUsKqKGmjSbuttHVYl+XjyfzBdgAlrVWc4qgmmktJZa9NdWSHttDkcT7h0dc+fkiCM/IyPUy8Z5JJ2I4Ixhtb9CKhYtSho2oWFgqdmmzHJMVLwvWV9bZjwc02y1GAxHXLu6y/OTc/IQ6C33ORiNSHptHjx/yqSs2zYtYGKkg/C1m2/xd9/7PFvNlEd3PuGTW/fJp1Ncs/bWx1KxUj8vI0AQGp0W29e26Kwuc38w5g/v3NWH+Tljo9U4mmluk0EJZ2rsGapDRaaIZkQKMVIaY8oQQokxlUlsGaOWRiSzUafR6IRgJmJ0YqyblVXIW8blWe179hfK82ESfwF5/ncVsbjAAgssCPQCC/x1GOb6BZnQO0GIsR4oPI2GfjQXVo46laOBs01iaFJpilOHal0jKBJw9aCbVW0mkS2pyrc6Er7UIb6+rGbj7dWdxhevXJZli2SDEYODAT5WiIHg64QEYwyYuhhCsCytL3Pl1Sus7Wxx9/jsYsAwB4K1+BAQMaz2emwvLbPkEjQvKKcTlrtdZpOcRiNhOs1ptZq4NGE0meGaKYiljAGTWCLKYDrFdloMsinToiAvy9pDLYZEIImRBrBq2lxZWubVjS12ej26icVnObPzMdkwI5YeEwJRIs7Oi8IjmCi1XQXFWJCoGARCJBSBqIJxlmarSavXpr++rCubK3T6PVq9LlGMFCEy9RVHowkn48n0YDg8PptOnp5Mx4/PJtP9IlSH47I4O69mkwyyDKo4j8fzL1Y5YGzNhOyLfcDOTwrGgKvqhOR0fhsihAiVeWmg0UHSgXaK6bdINjou2Wo3Gjttm1xa7XS2tpb6SxvdbmOj3zOb/R7LzRatNIEYNJQV5Wwmk/Mho+Mhs9GUyXhGnmX4GDDO1GU2qkStzcwxcJGAAgadF+ahdUE4akg7DXobfVpLPXKBo/GU+8cnfHJ6xHGYUgDeGIIKQZVApJ00aDcatGxKN0nqwkfjiCGQWkcqwmwyYX2lT+UrQoiMJxM21lZQhFlZksfI2vYm52XJg4NnDGYTPPX+7DRiFS61evyd977IL7/1JmE84qMf3+LZw2do9JhEMKZOdZEwtzXFSCyFpfU+O9cuIZ02tw6O+KP7d/VZOdExUk1ww5mYIxJ7GFXOozITI5WqekQqEQqilBgKVS1BSmNtgWhBjDMRMyEyETFTsUyMdVlR+k+tG875T4cG0/hStrMuyPMCCywI9AIL/F+cRN80UAk7ZW0o9d7MiXRt5QjBEZuO6BtoaOJs08XY9Bob4CwOqScDpQIJNV2LrcSwmWh4rRH8F5cIb3ZUt680l5tfvnrVvLaxIvlgyPHTY6bjKcZIfehaBB8jEhVn6yG9tN1k5+o2l67uMUX4k4cP+c69OxyUM4IIQQw+BpaaLTaXV1lptiDLcXM7h6iiIVKVHkztWbaJI01ThpMpZRUQJ4izzMqKaAWaDXJVBpMR02xGQOsAZWNIYiQBejh226tcX1/n2vo6a40UU1ZkoxnFeEY+nECs6vg0ozixWCPzabY6xkOsYJN6wi2WcR4SqIRKiQjGGWwjod1t0V3q0V3u0l7qatJsqE0a6hpprERC5n2clVXIyhAneR4GWaazqoxZWYXcB59XRZhVpZa+lKKqTFUFG1ApQyWqQYg6zxiuUwqNFRER46zFGCOpdSTWauIcqXH0Wk1aaSpN66STNEy/nZqlZsv20qZpJc4uNRsmNSISggRfSTGZUEwzyaYZ52cjJuMZVV5Q5RUmRmwiiK39y5i6nloBHyGqghOi1sOBqma+n8yzxZsp7ZUuS6t9Ypoy8hVPB+fcOTjk2WzASMs6UcPU93nB9Zppg+VenwaGRBXNC5rO4cTSbDSoypIqr+i2myS2VqjPzoZsb62RJAmjWcbR2Rk7e5eYhMCz0TlnkyGZ94hxGA2IKh2EL1x9jf/kc59jr9fm4Mk+d9+/x+h0SJIaQqxrxEUEYyGZl7o451jeWmV1ex3faPKDJ/v6vcf3GOB1jK2mmPNCzL439qmqnAOlWFPL8UGjhuDFuQK0VJEcYo5IDpIbMTNRP0XMROIL60Yya1Yhz40rL6wbf1Z9jgvleYEFFgR6gQUWVo5PbRzzQcJQl168bOUYRksnurpgJTRwtuViaPkqNq01jVCrlAriCcFT5xcba03TCKvi/Y1W8O+2tXqni17eSdrdL+9dM29srWOLgtPnh4wHE4S64KLyEaLgjCBGiWU9BNZb7XHl5jWWNte5fXjCH3z8MbdPnpGhtRodI1GVlXaP65cu4acZXes4Pxmwvtwjz0varSbn4wmKUlaRtJmSpinnwxHLK8ucDs9pd9sUMTLIJkijiUlTxnnGaDqmDAEzjyBLRUhipIVlxTa53F3l+sYGe/0+K40G0Wfk52Nm5xOqrKjZYBVwBoyr/boiQigimJo8ipVPA+suyHSo/eIi9e2swdiEpJHS6rWxTUur1aLT7dBoNXFpA9togLGITeoM6xA1aFBExYcgQeuBx8p7fKiH06LWGdeqinUWZy1CTWAT60icBcAgNJzDGSFUFU6EUJYUs1ldX50XZJMp+TSnmNaKfFWUaFkRY5wr8AbrpH5OOre4CIRy/uQFosR6waN1BrOPiopBrIMkIe20aPV7JN0WGfB8OObB6TH7o3NOy8mFTaME5gc4MEDTJaws9UlUWG62mQwGtBtN1pZ6nJ0O6LZboJBlOSu9Ls5Zjg5PubS9Rll5EDgaDFhZX6cUqIxweH7G4egcIzJ/jWqv8157mb/59mf4xhuvwWzCnQ9vs//JU1CPGEGROkc81kkbtYW7rv5e3Vmjv7nKmVf+6JP7fHD6VCcSdYIrM7GDAtn38Myk6SDGUAdMirEYFerNXVnnCoxkQTTH68yIzKLVGWomVnQqMU68sVOMy6h8jk2Ki5run4ms+xn1OS7I8wILLAj0AgssUjleVqGBi4HC+BKJrlXohFA1Ug3N0tkWMbSt2mawMZ0/TrRBQvDBW4fW3mhNNIZlNLzSDP6dLuHdLnp5jWTpc9uX7VvbWyxJkNn5iOHROdm0wDYNGmsiEULEpfUfGrJI2mmxc2Wb3Wt7lGmD799/yB/d+ZjnxQRvhIghxNrW0W932Fleo5emFJNa8UShmTrG0wndbo/haEy73SFoxIeKTqfLeDrFJo4AVCjiHJOyQJ1jWhVMsozC13wlnSuNiSpNhC4Jq2mHqyur7C732Wy3WE5TTOkppzOy4RSf5Wjl0eDrjWDAuPo5IzWBjiHWhHpOslHFzJXqykd8ULzqBXuJEUUE5yzGOiSxuDSl0UhJ0hSXWNKGw9k6pSRNU0Tq/y9JHKq1Ampr13ZNWkMkxIjGSBU8wUeCr8m89zUprsqKED0+r/B5SfRR0PoIgrHz9hQxOKkbJJkL8NI0VDOPah1nyNzmgggy59WhUrBCQFBnUOtoLXdpLnUwrSa5GE6ynKfDIQ9Oj3k+PWdCVds0pPatvFCyGy4hdQndZoumdbgQkLKilTRIrSWGgDUWibVdxJee5V6H2TQjxkiv16LTaXF4ek6r1cK2m5xmM05HQ06mo/oNZQyGuoq7h+PL11/j73zu86y3Ug73n3LngztMByOQiLjatqRqEGsxAuojBsvSSo/NvXW00eLBYMifPHnI4+xcx0KYqM1ysefB2edeeabIuXGmiBEhRocRC2CMCTGEAiQ3RqYqMkOZgE4RmUjUiRg7EaNTMWEm1uamdEVmi+qiptuYSJqGenBw/2XivBgYXGCBBYFeYIEFif6URL8lUH5a8U0QNl4qWAnBERsp0TdwoUVhW7jYRmMDax0+CFi1oIiE4EPEoRbr8NWSil5Og3+7rfpuj3BtCVl6tbeefP3mdempSjEcMT2fMBtOEVsXSIRYl5c4AWsNsYpY6+ivL3P1xlXaK8s8HY35kweP+NGTBwxiSZSadNVDhk1Wl/p0XUK/2WJ0PmSp3QRVyqIiTVLG0yntdotplmGtxRghK0tWVlZ4dnxIp9PFe0+hSnd1lYPBKd4Ik2xCUVb14BqQimBREoUU6JKw1exyub/C5f4Km902vcQhvqSczChHM4pZTiwrNMw7mrUmzGKoI9hE5rXNdQFNNLUKja1TJpgTcA06T5+YK9UKMcwJtgiiUg+k6dx/LfXra+fndd/I/PG0HnjERFTmynSoCa6gFyS4Nnso1kh92dY+bwREYj0UGgVRrS06L3UqxlQuhivn64M6dtDU7FmjIIml0WuStFukvQ621WSmyqAseXQ24MngnIPpmEGckqNU1EtAjxBVMXPi3EoaLHd7NIylmk1pWkcoSzaWV5hNpuRFTrfToZmknA2GrK0u48uK6WTKSn+JbrfFwfEpSSOlAqTRQFPDncePCDEizmHrJ0AT4dXVHb75xpt89vIeFBmffHyPpw+eUVUlxr5o4qxNQWIEDaDB4BLH+s4aS5srZGL54OCAHz19wknM4lSMH2Onhdgzjz5H7aEaGWFNZYAQoxODs9ZZjaoIJWiBylSFCVGnxspYlJGImYSo4xdDg1KF3BhbZKaoLpRnY+Kn1o1mhHu/SH1eYIEFFgR6gQUWJPpnSXT1aTLHmjfEaPDeEULSjI00Rt8sNbRQ28LGFtamFnX4C291DCEEIOCcot4ZjT1ULtngX2treGtJ9GZbdeVyo9f4zOa2udrvSVMj45NzpucTYgwYa/DzWDjViE0sxHqgrNFqsLm7wd7Vy9Bu8eHTA/747l0+GRySoVQidYscSmodV7d3SUXQokJ8YDqZsrq8DATG4xnNVpOyKDDWElTJq4LV5RUm0ym9bo+z0YgyBsroMc0mpXpMs8VoMqYKgbIsUGo/i8PgJOIUWkBXUlZck8v9Wpne6nVYaqW44PHTnHyUUUwy/Kwi4Gsyq7UNAK0TPdQA1hCj1vxWX1gdau+yzJtDjDU1uwm1XcJag6itkyqC1uRYaiYr8wxlqbuuL6LgjApR5qowUg93Ut+/1lnnRFpqtbqe85tbTGK8+D+MFYzWg5TGzsm5yMVzePGNEKNgUotrpbi5NaXRbaGJYxqUk1nOs+GQR2dnHOUTzmNBVvdbUopQqdazrPO4uFajSTttsNRqU0xntMRC8Kj3bK2tUxYlk8mYXrtTDy3W7JMyr0luUVTsXdpkOss4H01wzYSNnS2Gec5HD+/jVTHzdA2JAQdcavT4xmtv8s2336Qr8OSTRzy4/ZDxcIhJpM4kL+O88Kf26GgAgqW33GNjbxPbaXOQ5fzJo4fcGR4wEXSKLaeY88rYw2jsgaqegcxUYxAxghFrxNgYvDXG1C3lUUtjTIYwUZGxEcYiZhxVhxjGEu3YG501bMhM5QpjknJqM49I/At8zwvyvMACCwK9wAIL/MXJHD8Xb7d2oUQ7YkyaMU3zGBqJsy3V0PLRNLGaWjTFewtWAiGCeOtcCAG16l1Q6ZoQt62Em80YX+sQXumobq7iup/d3LVvb29IM3qK4YTsfEqZF6idWxpeEC4xGBG0irjU0el1uPzKLmtbm0wx/OTxE75z9y5PZoM6rcPY+ts/Rho2YWt1nW6a0naOk6MTNlaW0RiZTjM6rSalr2rSbgVfhbkfWSirikariUksw8mEtN1kNMsIIngR8jInGkNZFYRQV3/buTJtVEmplek2llXXZqPbZbPXZbu3xHKzQSNGJETwnmpWUmYFPitRH/BVVZNOU5PlOtINrLU1iS5DbX2wtbJbWzJqhViQ+ZF9ufBWv3gMMXrR0GeoyTpz0h3i3Kcd5aWUu/q6GGrLRzRxTrKZk/d62K+O8Jur0aoXKrkAxhrEuDreLU1IOym2meJaDUzaoDLC1AdOJhP2z895Ph5zWkwZaUmJUkgdBVLpC0ZXE/zEWRKb0EwSuo0W5XRK26W1MmwdjSTFijDNpqgqvXYXNM6TXGSu/lNXcofAyeCUpNlmY3uTs+mEJ8eH5FWJqpK4BAkeo8qabfClG6/xjZs3uby8xPnxCY/uPuLoyTEaA9HF2sOtisZ5tXha555bsaxsrLK+t4VPmrx/eMj3Hz/gWTXRqYhmdb7zoEKeq7XPjbGDKOT4oKrRAta6pM5iRzSEEMRQgeTGmkyESVQdx6gjm9gRUUdi7ViiTj4tS0kLbPYLlOf9lwnzywR6gQUWWBDoBRZYgE9LVvi5dI6fLVk59Ib+pySamKYkoUEeWqg2cY0mJjbw2rBWXV0eQsRJrUT7Fw3esRt8XE+Ey2mIN5rqX+kSdpZUlm8sraef292V9dSJH03IRxNm5xlRA5IaQtA6sqyeL7sg0mmasn5pnd0reyxvrPHkfMz37j3gTx/f59jPqIBgXD2MB6SJZb2/Qr/VpprliA80jKEsy3mUXm0tqHwgdQllWdBqNsnygiRNmGQTjLW0Oz0G4zGu2SQLHtdoMM5nVKFO/MjzHD/3OpsX6rSAm+fDNRB6psFS2mS92War22Oj26GTJHScJRGB0hOqknxSUBYlvqiIIRB8mCvPoCHUr8cFB471oJ4RxL9oGAGROoVEw4XTA2NqRVg0Mp/lqwmysRdlHvpCqZ7H8NV8ulasdZ6UobZ+zbyvCbPBzIm74lJH0nC4JKHRaWDTBNtKUWspojL2nkGWczCacDgZcV5kjHzBlKpO0BDmthwI87/AugSjkCZpnajR7TA8PaHX7uJnM3qtDmnimE0nLHeXOD07ptVs41xCp91mODwHasLfbjRxLqGoSoIGxlnO9Rs3KIjcfvyILM9qom0MVut2wB6W1ze2+dV3PsO7l3cJ0zGP7j7g8b198lmGdQY1QhEiUfTi2+/FUYBut836pXU6q33OK+WHT5/xo8MnOlDPFBOnYotKZBhN+jyizxUdiLO5AvhoBU2MtQZVYs2gfUQq50zuVTPQmQYmRswI0bEkdiSqIx91gnUzqphhXIkryj/bNPhnyPPLpSkLLLDAgkAvsMACfzGJ/ouU6GZCDEkdbxebONtEY9uqaWE0JagL8+FC7MUXsFisVfUtfFxyxq6bKr/cRm508Nfbqms7Sbv53uYle2N1maQqpRxn5KMps2lRD18xH6AL1PFnGuviiSg02y2297bY3r2E63R4Mhjz3U/u8f7Tx5zGnBKIxhLmMXmdZovL2zv4rCAfTVhd6lJkOUagkTaYzmYkiaMqqtqDHepD8GmjQeUrGs0Gw9GEdq/DrKwovKcigLEs9ZcZTSeUGphMp5RVeRGHZ5ELsiqqOOqRy3oQ0bGctllv91jrtFlKU1baLdpJQiKCRSAGyrwgFJ5QVoSyIgaPhnAxgEhUJNZxeTAv5RCph/jEzAf35rF1c2labH17jYqIQXR+n7lNBMP88txbjRCNIInBOVuvaqzFJpbUJaTNBNdIMYkhiuBVKGNkVJQMZrP/P3t/Hi7bVVaLw+N951xNNbs/+/TJSXOSkARIICAoYKSxoVO6gA2CV1Rsr6Jexe6e5Prz+33eaw+fDRdUrsqV5IrXBkVFSQRBekR6EiA5Jznt7qtqdXO+7/fHXFW79j57nyY5acA1nqeeql1Vu2quptYa813jHQPLRYaT/T5OZQMs+QwZBGVt4+IJoSmUEPyeQWAA1hi02h0wCJPtDmK2WDp5DFPdiUBsWy3k/QyWw/jLskQrjqFQzExP4OSpRcQ2RlaWuPiivVhcXoG1Fl4FlRe0Om0cW1mGJ2Cl30O/yBExw4BA4pEAuGJ2D572qKtx/cX7YF2BE4eP4shdR9BbXA3rMCL4SuEkVJ+Vw9hd5WFtjOkdU5iZnwaSFIdXe/jo0Xvx+bVTugbogIwMyOQV8bJXPkaGjythFUCp4gGQIWajEEvGKIMF3pcCKpmRszGZEx0QoS+qPShWTcRrEF0j0TU2tl8an6GKCnBejcJSRg2DI81zQ54bNGgIdIMGDS6InGM87nuYVFjb20XiU7WmreLbUG7BaAIYq6pGvKdaG6AQURgDqBr2rgWVGaO6J/b+8jb85ZOk++Y0mrh6x67o6vl52pHEcL0B+qs99JbWgkTAIDQY1heUrQ2EVKsgWehOTmDvxXtx4LIDKI3FJw/fh3+960585tRRLGsFT8Gxw2nQv3bSNnbOzkHLErPdLpZOLYJUkMYxiqLATHcKq7017JybweLSCjrdNlZXVlE5j8nJSZxaWkTaaiF3JSYmZ7DWX0VelkjTDipxyH2FpNNBL8tQViWceIj3cHU1d6jdNajJdO1hEoPRgkHHJpiIQ6V6utPFZBL+bkcWiaGRywWrhETEugqNSqA+uGd48YFgS3DXCImIIdBlmPA3TFIhhHI5KYMMh4ZAE3YFjmrnCGNgouDHR1GwlwskORBgUUFWVljNcqzkGRYHffTKAr2qRK+q0NcSJTxKhOscFWjknAEQPAQCwLKBqSUYsTGIiDHR6WCw1gd8BUuMualpVEWGoiggzqOdpPDOgwBExqLbamFxZQlsDFppCmYD5wWlVChdhYnpGSz1eojSBA6CY6dOovQOjGCnyHWIzr7OLJ50+ZV48pWXYS6NceyeIzj8hcNYOrYIOAeb1gEtdVVePMAxQSUk2SSdFLO75tCZmUZfFZ85cRIfvfdunJACfSLpgas+8cCzXQTRCShOqeoaEVcAWFUtERuFGrJMIHj1WsH7nNhkzBgANFBCT4j6TNojNatgXaudN/qVkwHYFjDFkDy7LWQbjddzgwYNgW7QoMGFIdEAsJ+xxxPK0kBCUmHHe+t9nKj6RMS31HJbhdtQaXloysyxlN7AKMNYgYcAPlwyBgB1EZi6KN3u1MtlE9CDXbiL26o79kYT6eP3X8wXTXRhyop8lqG3vIqsnwc3A0MQB3gvqPvcQopbqTAcYXpuEnsv3oP5Pbvh4hSfOHIf3v3ZT+HOpRMYjMU5OxUYNkitxVS7i07SghWFiiBhg7zfx0SnjbXeGuZn5nDi1AnMTM8iLzJ4qTXJYCgDK701TE5MwYlDNhhgYnIKq4M+ojhBLxsgnZiEg2KttwKvwds4L4s6dU+hdZXagmCojgtUrWPFgQiMGAYttkjYoBsnaNkY7ThCaiN0ogjdJEbLWrTiGGnt5xxHNhh2157Ddqj7RfheAtdOHYLQjKa1T3GIx/YAhAnOeVSiEAB55ZGVJQrnkDmHQVVhLc/QL0tkZYnMlcjFI0eFArUWGKHx0df6ZVf7PA9ZmgFgbQxmgzRtwZclGIRWHKObJMj6vWCTxxaTnTbEV8izAdIoRVUVmJ+Zw7ETx7Brbh5V5dDvDZCmMZw4TE5MYrXfhzEGWVVibn4Hjq0swyQRVtb6WO6thDGwhSGF8R4RgH3taTzhssvx5CuuxFwaY+XESdx79704ds8xuLIIhffIQFXhnIQGSmaIeKgQ0lYSQnBmJ0FpByfyEh85fDfuWjmpKxDtAz6PkjxTrFZKS2SjBRVZItU+QE5VYKyNAEQy3CUAAbQi5lydHwDowVAfQn1L1CPLfRHtWcaaF9Mn1l5lfIbK5nXSYNA9R5E/A3luKs8NGjQEukGDBrj/cg6cFriy0eIuSn0c5+qTSExLreuocNsbaUG1hUJjxBzMlQGFIQchB+MrwArgGKptq2Y2ctXFqa8e1SG9sg2/a0pt5+D0vHn0nt00RYaoyFFlGVZPrqH0FRAZiCh8neYGDtVbqIKcwlqLHXt3YPe+fZjauQNrXvDp+47iX+/6PL6wfAKDWjYgFEItAMFEu4MdU7MoixJWAZQFJtIU8B5lWaLb6qB0JTqtNlbW1tButbCyuoy03YbzDs55GLuuuVYAzjlESYrSOXhocLkwBhxFyMsKMIysyIMntXPwIvDiN2wQA6rJtY5mOcObre9jEBJYpGQQmwiJsbDEiA2Hai4RosjAEiNiDlIHGjs0q4xIc+UcnCpK7+FUUakPMhVRVF5QikfhK5RwcFA4BDLsx1jYuhwDUKWamNdNhvXaiYyFtREIila7AzgPX5RBquEFkTEoiwJWATYGM5OTWFg8hTiygBIm2ynKsgKzgWWDylUjyUS324ETQS8b1LHtBFgLYUKr28bdx45ibdAP1WZjwfX8LgGwK53Akw9eiSdefjl2tBKUq6v40p134/jh4yizAiYKK905CVHsw6ZJQxCnIGZMzXQxtXMG1ErR88Cnjp3Ap04ewwmfaZ8gAzJVRtR3sIvCfFJVlzSyPYBK8iJMDO89GyYLY6yQEMAKhVfxhSHTF9IeEXog6sH5NUPcI+K+F+0TmwGxDCojA1Q2BxclrK02kueR20Yj22jQoCHQDRo0uICJhZtu+3lLn2gfJ1gn0W0n3IGRFpy2wBwzq5HKAyCBMQ4kJUAueLCBoBxHItPqq32x1yu7cFe1IBe3Vad22nb86J176YodcxS7EpLnyFYyrK72UVYOHHOdXCchlIIAa0KpU7wijhNMzs/gokv2Y2rHLNac4lP33YePHbkHd54M0g4BgrxD62ZDG2Oi3cXc1DSKQR+znS6WFxeQ2hjOVbBkABUYa5DGEXpZhiRN0e8PkCQJsiwDaou0QZGh3e4gy3IQAa1uF6uDHry44PpmI3gCyFhUIqNkRSVCWRbwWgebqMDUG0hqIjpsUGRaJ9MEBevWG3Crywy66QDtxxjU0ILBr1s5r5cpCZDgEA0Za/ILGzQQZtSPmQiGGUmSwloLdQ6piUaOIb4qQ6U9boFc8EtmIsTWQlyJJEqQF2WQmRCh22lh0O9jqjuBbJChdA5pEsM7wezMFJZWVkHWBBm4tfAmyE0K53DfieMopZZ5sAky/VqqcfHEHB67/wBuuPRS7JvqoFhdxeEvHcaJIycwWOuDOKQphrCZsCLZUEi0qcJErjvZweTcFNKpLlwU44uLS/jokSM4kq+gB2AA9gPiojRmRYw94Sp/HMxLYB6AyddG6EyizGxYSEMWvBcBk2fAiZOM2fSUdE1Ie0y8SoqeIe6LaB8kGbEZVMbnaWkKY6KyP2wa3JgyuJ10o0GDBo8QmGYVNGjwlYBVANOEAQET6892kMCogshr5QUQkAGDAVJmUgWFMA8z8iAGm7pcDA9SJ4QCSpkYGoiJBpVqKVAMpDLH15ajlazgKE7Q7bQpTmIkSQTxCldWgATizMwhSGToOgGC9x691T5OHFvAyuIyWonBVRfvx1X79mPP5By4UpRZDq8uXCNnAycegyLDcm8FmXMwcYz2xCQK75EmKfrZALOzs1jr9yGiKKsCbBhQQVl5xLFFWYSwlW6ng15/DVOTk2AyyAYDQB267dD8FkcJyClclqGdtIDKwdoILILYxrBsYJkQJyniJAW8gK0NDX3GQjk06HlQXQ0mVCFRAxVCpHUxvBGQ17cBAdmm2/hzRX3L688afkY1+pvgCChUQxUfFDTSzDDWBrIMxkR3Aq2kBeMV3XYbVJQw3mOi1YHmOdiVIRmQo5DU6Cq00xTelYgMwZCBK0sYIkx0JzDoryKO4pAiCKCsHHbMzqLTbmFheRlkLEooWtNTWBj04SNGrypw5MRxLPXW4FXDeoXCiqClwOVT87jximvxnOsejyddfgniKseXPncXPv3xz2Lx6Cl4V4JiHk0WRIN1INf2J+qAKI0xs2sGs3t2wHS7OJaX+Mi99+L9R76E+1ymqwBWYVzfRANvkgXHfJTYHBPVU1CsgbWEQqAEMkwQVVUFiGs3PCmJKCOlnqr0wLoKolUis0KKNRD3IOgR68AZGYijrKW2yE1ZVkZCw2AUeRij25DnpvLcoEFTgW7QoMGDp4uu5Rx7PI0aC52zkJZNfTUu52g7kRYMt6CcQjUa+ywF1TZ3EFf3kQEKy05aUJkmlb2x95e3mS5L1e2LVWfmKUqv3rnHXjEzR5PGwLgKRa+PtaU15HlNYmsiqRIIO6AQLzAIQSxRHGNydhJ79u/G7K4dQJziiwsL+OgXv4hPHz2MBZehqPW6QgaiIS3QGotOq4PZiSmQeLiiRDdJkGcDTLbb6A/6SOIYrnKIoxh5UQbZR7eLvCxRVsVIwJCkCfqDNdiohbzog20SVg0RhIDKVTDMqERgkxSFqyDig2bZxrXGNlSqg5RFRhHhbCx8UaBmd/X7pHbi0LpOTHWpUcf0OnU1efgchQjxoch8GPs9nAipBm9nsKml7TaspziGVi6QaS+wxoCcgGobuMhG8K5EzBYkiiSN4V2FqqrQanVgDWMw6KGVtGGZsdZbxfzsDgwGA5SVx0S3DRGPsqywc24Oy6urcKrIygKtThcT01M4snASZBmLKysYlEVYL2zBIaoRDGCSDC6e2oEnHLwSj7n4Ikwag3J1FUcPH8WJ+44hW+sFXmkZKgIFw7vANU3dvCqlgNhgcnYC0/NTMK0W1kTx+ZML+PSpY3pf0UcfwAAkOUxVWTvwMIsieoKZjiuwAtIBG+vCfoZa4c/MDBKpObuqJ8MViHIiHcDpQCz3mLQnoj3D3CfPA2IdEJuirFzRYltkbB1svi7bYNZNEd0NeW7QoCHQDRo0eAgkHXyanAOOMbMx9jsRlxTWtyCmDZUWmNPgE82RVzX15yiIaoUAecALCAIHhneWmTuiMhup22dEL+uSHmyJ39sBpvamk9Gjduymy2ankXpHKArka330Vwcoy6DfZcuBHUhNpjnYtmkdj21NhKnZCew7sAdzu3dCoxj3La/i3w7fg88dP4p71xaRQevmNwMfxKewZJDEMZIoxs7ZObiyhC8KRAy4skQnaaG3NsDU5ASICQuLC4iiGKqCTruLtd4qWmkbVVXCeQ+PQEi9hHEZa+HUo93uYpANUFUVlAhRksKJD2zHB600GYZqrQO3taZZQpw2VCHOgeNAuAEK98YEH2cvUEMIWgTUpDgkIdKQPEsdK27MKG0wXD2ore6gEPGwURwqsWUBECNKYvi8QBRFIK1t4OIEKgpf5oiiCO20jWIwgPgC3c4EvBeUroC1ESxZZIM1JHELNug2oCKYmpxAfzBAHEfwCmRFgcp77Nm3F4UK7jl+DGDC0upKWK8I0hFSAdcx3zM2xRW79uDxl1yGK/fsRscQ1haXcO/d9+HU0VPI1gZgEhgbmie9q7XbFKQoIgp4gTFAZ6KD7vQkWlMdVJHFl5ZW8ckTR/GltSXtAZoT6wDscuJCiHpCZoGIT6piQUHLUM2IpQJIVIQAYmI2AJgNK1TEizqytiKiXEQzJsogvk8R9yA8INYevAyITVZVrkjZFjmbqraq82cgz+NBKQ0aNGgIdIMGDR5aEl0xILROolsWUsUQl8Ca1IpvQSVVNak3kkDVwsPAmHFprgQmRwIamTMwnIugOgHFfES4uOXKK1qql7WguzqgzqUTs/bquZ20t9tBqh4uy7G21Ed/bRB8kQ1GXsYqqNNBajLNQSdNSmhPtjG/dx579u9F3GljIcvw+eMn8cnD9+Dw8gKWXY4MGLlS+CHJBBAbiyiyuHjfReivLMMIMNudwvFj9wU5AxvMTk1haWURqoCtA1qIGKKCiYkpLK8so9XpoirLkb44zzPESQuiChNFyPMsVJ6JkLS7yFaWkHQm4OqGw2BT56CVQ5S2grbYhWAXEQ8IwSQxfFWGqnKt94YKyEYgZkhVgWxoWfR5jihtgY1FkfVCtZsYnCRwg0HIzzEMl+cwcRy050mCsj8YEflWqwM4ByZGPljD1NQsiqwPZoOqKtBJ27Bs4H2JPCswNTEBaw0WFk5h59w8rI1wYuEUdu+cx1qvD+c9bBTBRhF6ZYHZ+TkcWziFfpGjdA5ZHatuiWEoEHcG0AZjR2sC1x24FNdedAD7pieRqMfxo8dw9PAxLJ1aRjbIYIayDAquJSCu/bM1VORduE/bMSZnJzA5MwUXRbh3rY9PHj+Kzy+d1BUIckAysmVOPKiI1wRYAXgVTCvG2jXvXU+VBhCtjGUn9QyHmUmCEoghEGI4MlSJSMFkcxBlRnQgpBmIB8Tap9AwmFHli4JNAS4cmB2Yg955o+Z5K5/nRvPcoEFDoBs0aPAQSjp4y0p0sLkLPtHiY6hPI2tSFUlVJfEwEdRFIY9aDWACE/VlfXK3HhYeIAGcoPBsDKdeaZZcdSAFXRHDX56o39MGpmcpal02NWuunNuBGWspUYUb5MjWMgz6GZx3tQEY1/HVWqcO6qgRT33IdEvaKabmp7Brzy5MzkyjYsLx3gCfPHwEd548hntXFjGAwNUOE2otnADee7BhpFGMVpwgNRYRG3TTFP1eD+Q9YhujKHJE1qB0Dt3OJPqDfpiJGIuiyBBFEaqyRHdyCnmeh34yH6rOlSsRJW2o+mDf1u6izDNwFKMqcxBbqCpMHEPKHGxCbLavShAHRbqKh4kTVFUJYw1cniGKkvA+X4KNDVVrG8GwQZVn4MiCjUXlq2AbaCOYOFSY2TAMmVpS4kKst41g2QS/67JAmrTgigFanQm4Iof3FdqtDqphCIw4dDtTqMoSiY1hDIUARVXkZQEbJRCmkADZ7mA16yNOUxxfPIVBWQTnkjpX3BLDQMG1/d+cSXH5rt147MWX4ODunZiOE5SDPk4ePYGjR45haWEFlatATLBRsPBz3o8SFyOO6sRHgVFG0koxMd1Fd7oLiSwWC4fPLJzAXUuncKLKtA9oRlwVoF5JvCLgJWVeAnhVoQMClWy5Eu9LgEuAKmY4JXUikKAxYWWGiIgA5JmoAFEuQgVIMwPKwZp55kHkJavYZ4kxOZe2zIYez8wyiufeWHluyHODBg2BbtCgwcNcjebTSPS8Y3jP6+4cSQRxMVRiRJJATGLVxKoSe+cik7D1CJwHUAr/C0FivQG8917goLCWoZJC3SS87CLCxYnq5W2Vi1P1O9vAxCxH0aUTc3zF3A6aSyKwc6iyAv21Hop+EYgRAWzNWPFVQDxU/4YKtZSCKIkxNTuJ+d07sGffHnAcY3GQ456Ti/j8sWO469QxnCx6GNQSD08Eb6NAxlRhiJHGCSYmutDKodNqw+clysEa2q0OCAZZ1kc7baOqKiRpDFdVSNI2iiJDng1gozhElqvCe4ekPYFs0AOY4MXDcNAci9ZGJkpga1GVWf2/jCLrw0QxiAhEDCYOVm/1nAW15zWb8D2GLchaVEUGNlHYwBzCZ5QJzlVBblKTcqiA64ZQtgbiHFQVNoqgXpEkCaqygDEGpALvg9TdGq53IEYUR3DOIbYxvAvLyhEhSYP1X9zuoJdnyMsCcZri1KlTqMQBhDo1sXYnqZMdO2Dsn5rDow8cwBXzO3HZrnkkABZPnsSxe4/h+L0nkfXzEDBT78WCIINRIOwPBHCdeklkkKYJJqY66E51YVttLOYF7lpYxGcXj+nRaoAMQMHGDUB5AVr1MMcVdAxESyAagKistTWAQhVwxOQgUpIxlYhUYKqGltsCcizwxlDlSUoSLgAqPElhiArPkkFMBrY5KleAbQnO3ZQxbmWD04bR2qpuK5/nhjw3aNAQ6AYNGjyMJLq+r8NW3IhEh0q0iIVIBI1jRBJHYmNViZxqBKuxUWO9qgXUwsEYo+yHrmnea6hEAzCxQVnEUG2DaYoIO43z+2KVS9rQi1vwcy2gvcO07KWTM3Tx5DR2dFowVYlyMEC+mqPMi1GFcaSRVkBEQVAQh0OVBicRsLVotRLs2DmD3ft2YW5+Dg4GR1dW8fmjx/HFUydwz8oSTuRrGKAOCzEmOHlUFTxCJTSOY6Q2wcz0NIrBAImNAe/BbFBmfUQmAgAM+iuYnJiF9w4TE10sLS2g3Z6Adw5FVUJUQESIogRlkcHaGFVVotXuIsv6wR2ituMzhmu7CIZzBVQVUZTCubKeKzDiOEWVDwAGkrSDIutDoLBRgqookCQpiBRlVQViaxgmSmpXaoWvCkxNzqK3FoJIrI2gdTW4qiq0O10UeYYkTlBVDtNTkyjLEoNBD1OT01hdXUYUxfDi4ZUwOTmJJElwYmkRM3MzWFpdwdLaKkQUla+gAOJ6IkAQsEjtAkPY2Z3GZfO7cO3+/bhs9y5MxRb52hpOHD2BE/ceR3+ph7IswrLb4BpSSUhrZBOaN6FhwgAB1BNsatGd6mJiahJIYqwUFe5dW8PnFo7hWNFDH9Ai6Jyrks1aCTqhhCOAOa6qK8Qox5wCSQECsxJzBWiplS+ZuRRQCUMliEoGKhBVxkslRJUnqgAp4akEcQGWAsQFjC9QmhJsS5i8AnMIKdq66txY1TVo0BDoBg0aPDIr0WNhKxDCnONhauGISGsSJSqRqkQa2agSiaEaAxpBNYLTCEYjY4xBsOolP/wuZkaIBuf6/S0ITRvCnkjlEqPVRS2V3S3odBtIZrnFl8/soEtnpjFtDGIofF6g6Oforfbh6uY8IYRmvDqUJVQ2UVdtCVo6GCa00gSTU13s3LUDsztmMDU3h0wU9y6t4DP3HcXnTxzDkZUlLFUZ8qGfMnMIT5EgF6Har7rV6qCVtlBlGTrtDsR5dJIY6j2qqgKBUGR9pK0O1DlYY1CUOVqdSVRFNqI/Ih5J0kZvbQkcpcHGr65Kq3dgNlAR2DgBxEPEw5gI3ofmQFfmSJIWmBl5PkAUh0ZFMjbEf/sqVI+JwdbC1zIOYyKor2CMhSszpEkrND/6CoxQIU/SNgZFjjhJYMmg3+/DWAtAkbQ7cK5CnKbw3iNOUyyvrUJE4JxHlg9Q1V7NdcI3DNWhMSKwCOmMc3EHV+7dj4M7d+HKffsw322j6PewcPIUjh85jqXlZRT9HFJ5WMuBwoLgReEkTJi0njipKsQJVAlJJ8HE1CS6011QkmCtEnxxaRGfXzipx/IVDADkYMmJyopMVqguCfExsLkPimNgWlHVilQZzBaAZSYDMAvEg6kipRyiOYhyY6jwIjlApRCVBlSBpIKnkogqEFdEXFbkq5i5JHZlUZoKbCtwFmK5h5KN9YAUbCHXaBoGGzRoCHSDBg0eeZroA7U2YCy1cCjpEOG6Gm2hiYX4OIZGam1UqcRB2lEmgIm8q2IAkTHGqLKBgRGvBHhimDocGoBHBKauIcxDZL8hPZCq35eKzLWAdqI+3hl1+EB3GlfMz9FMHCNSgeQl+it9DPoZsqyAQGAsQ0jhg2sdqJ4eGF1PA2QNoSXtTgszc9OYmp3B1Mw0WlMdrBYOi3mJuxcWcOfx4/jS4gks5gNko9FSWCsAvAbZANd2cVEUo91KQ2DIYIA4ikPwSBxhsLKKtCa5g7UVxHELDKCVJMjzDMxAFCUoqrIeNOCcR5KkKMsC1hqU+QDMBsx2pJcmY0CqwXkDwwjqMFZVgY2S0Hzpq0DWvQNbCxsl8DWpF/FoxSFcBhB4Bay1QbdNDDW1VKUzAQUhThKYyGJxZSXMh8QjKzJU3kOcHyUVEjwMm7Bj1fZ3BkCXDOZbE7hkx05cuXc39s/MYW6ijcg7LC+t4Ni9J3Dq2ALKMkNZVGH7xRTMRJRqglxPjqK6FOsxchaJ0xidyQ5aE11wK8FK5XB4dVW/uLiAI/0l7UF9QeRysmWhyISoL8qLAjoO4CiAU0rUgzUlxBMEMUgjYo6Y2SD0Bjr1voAg58hmxtAAogMiykFceu8rgCoiriKiypEPBLriqqTKpWSqnNiBczeK5R6S5ygSHBlJNpp47gYNGgLdoEGDL59K9EECKhqR6F1CqCoT8pxlSKZtS1Mr4iNVsaVKHEU2VpXEVZoY5cQbjY3RyDuNGYjE1/Z3BsrGiHgReKUQ1KQpM02R4V3iqn2p4iKrujuFn05VWm1oNBelfGBiFpfNzmFvtwt2jlyWo7/aQ5EVyLIczjsoE8jUPslax2jXF+EjSyARDH1CmBjtyRZmZqbRnZrAzM45tCYmkTnB8bUe7l1axuHFUzi8tITjq8voaYmqrk6H6ncImNOxtL8QKx1s0+I4BrNFZO0oXTCJE2Srq0jTFgwUzpVIk1ZoViSGMQaiirLKav1uCu8qsIbqd5K0IKIoXIG4loAYNkjbLfT6PYAIUZxARFCVJQhAnKbIiwwMDs2HVVl7QgvanS6y/hrYRmh3J7C8ugg2ESamZtDPMlTioQoUeQ4lwIlHURbrHtTEIT0RCksGjKCrNgASECZtgvmJSRzYMY8D8/O4aHYGuya6kLLA2vIqThw9gVNHF9DvZ3CVg5KGdEDD8Cp1tHatAa83qqqvdfChOTFpt9CaaqM10YFttbGQlziytoLPHD+qR/NVzQApmYsCNMjBawXxEoiXIbRMRCsiugroGhFlYOOCo7NnCCIAxkSREScAixKZEs7nAsrYUt8SD7yXzEZceO8LUCDPADlirlBWjog8ETsidhnlHszjxDlY1J0ezb2ZQDdo0KAh0A0aNHiENxZinUiXjF1COC6E2VobrcoQMRAx0NRCfBQaDW0M8SnUJMZI4vMqATTmKIoBRPBq63quMoyKDyHSMMwAYibTVZU5iN9Ngt0RdGcKPxdBJlsq7RSI5zgxF03M0EWTM7RvcgItBnyeo8wz9Ff7KPIKRRVSBI3h0GDn60othZBqaLAzM0wQLxAJjYNJO0WnO4HJmQns2LUD3clJVMxYKyqcWF3DkcVFHFk4hVODNSxmA2TeoYAfkWqpbfKCB0SwmtOxSOw0SRHFMcQ5GGK0W63a79mj3WqjyAvE1qCqPJJWgmzQg3MODCAyEbz38N4PC9WhCY9oZIEHDi4a6gXOuUDSI4tBbw1puwtmRjYYoDPRhagiz/NAytMWKhc02pX39ecJvAt+1agDWnR4uYI5GKOI1juNIgIQgzDBMea7k9g9OYWLd81j7/QUZjttTLdakLLAwomTWDq5hJVTy8h6GZwPUg9QqOzDAN5p0DTXUhxQCD5hpaB5ZoY1Fu3JFtKJDqJ2C5VhnMpLfHFxCXevLuBk0ccA6jNwWRL6JZvFUrGg4CUwrzC451UzY7kQp7mSVrVBiwAgtkwAjDgBWw5zJCYPpVxEMkAHhmgA4gER5yBfEHEF4pKIHXHlUJAnYp8T+TYZP+DMg0hOt6gbNQvKFlrnhjw3aNAQ6AYNGnwZpRbWRPrAxmq0CI2aDNeJtIUkEdRHiCSGmAQqCSpNjOHEMKfeu9irRmyMEe949K21PoKNYfE+AlOLmSbVy7RCZll0zkBmEpXpFmMyET+ZAq0piqJ97Sm+fMc8drQS6hqG1RDrnfczZP0cZV5CJDSZYeQPTKjzRkLjYb2k1jCkqkNa2CBKLNI0RXuyg/ldO9Bqd2GTGGoNemWFxf4AJ9Z6OLaygvtWl7DYX8NaVSBXh2qMBQ2r1QAFElpLLkx9WCXmUHnmIMmI4yRY0RlTSzoUcZLUDXIGg0EfcRwhimNURQlrLQRAWZYwUZ0mGEUoixLMYUNWVdBCqyrKMlSflcJ68K6CQqF1KMyQ7jOF4BqoB1GwCwzJ7WFVRgDaHGEiaWEmbWPP9Cx2T89g3/Qk9s5OIWGCVCWyfg8rp5axtrKK1aVVlIMipDJ6ARsGMUE0THKEAO9DYiLben2JjK4WsLFI4hjtyTbSbhsaRchFcbLI8IWFU7ivv4pTVaaD0BzoM1BWglYdYUHZnoDqAojXoJQjNAJKkLqz904cIAJjPHOodUMAcc4DcGxNCaICpDkRD+AleDmTZMRcgrigylVE5OpqswdIMmIBZ36CSNaYw24xrDqP/J0jBe7cHIzSkOcGDRoC3aBBgy9Td46xsJQhkQZG4SvwjCm/Xo0WiaCJhUoURxKXhSTWmFSVU0ATqMZ+2HAItoAffQ/DsMAbeLWwHEM0BnNCpIk6aRvSKRY3F4nfkxLmU+h0qmh1QNGudIIvmpyh/dNTmI5jsuLB3qMcZMj6A5SDEqV3EOeDHMAaqADe+dpjIXS5EaiOwA66XdKwuIYN4laMTreNyaluSLCbmEDc7kCNwVpRYrXIsdDv41RvDUeXl7HQ72E56yFzFQrxcNBQpd7EjGTTYVagdSy3rrtlDMk28Zh0YihnoFHMNwijxj2qCS9v2Lyn8zEiCpZvY8+Nb/wIQARGDEYnSbFzagZz7Q7mJiawe2YGc5NdzLTaaFsDKUusrqxgsLqGlaVlrK2tIu9lcJmDikcdShjkGaIh3AV1AuP6qEFSrwFVCAg2jZC0U7S6HZg0gTcGfRHct7qKe1dX9Gh/GctSIQe0AElBtsqJBh5YAvEpUZwE05KqZmCughpeAAGxYQWx866qAFRkraNRTL1WEFQgKoDQMEgyIs45iHMiLsi5gkKj4JA8C1HmiUh6RDrydSZSEOm608YoHEUayUaDBg2BbtCgwVcOicbpRBpYD1+ROoBFeFwfDU1NIj4qVJJIJVFrYqgkqib1rophOIb3MZijEMYCA8AyWyNeGEYN2NTs0iu8UHBD8C14P2NEdyXA/kT93pQwF6t2W0A0G7XMvu407ZucxK5uF20QYgiKQYY8y5Ct5ahKB+89ZMhVKFSAnQYHB6JA3gwIxoZFpLpaLU4BUtjIIIpjtNotpJ02Jqe76E51EcUxOI7hidErSvTLEv2ywHI/w3J/gOVeD6t5hr4rkFUOWVWiFA+HdYLtxxgUjVWxaTOrGpFlWn+trhBvscFOO5gPSbKpSbKFRWwtWjZCy0aYbnfQTlLMdDqYn5zCTLeLiVaK6VaKiAmsAnUO/V4fvdVVLJ9axtpqD1kW7AbVOxAhuGdAIfXqHi6DqsLWnt6B+1OYsNTuGiYyiJIIyUQLcbsNTlPkYBxdW8XRtVUcXlvBqaKPAUQLQCtiX4JdCc4r1R7YLCnTAkCLqroKUAbDQbAuwgDYRIbCnIVK73xJjJKMKQFUgBZQU4powUYyIs3gKQdxRiQ5MRd11bkk4pLZOCLjiAZCRNIbEmZAwTwk0Tq6bSTPjctGgwYNgW7QoMFXWPT3OBejUUw3QMABACWfZns3qkgnUaI+VpVYbWgyhEri1CTQKoXXBMoRoBEMIkSRhapZ/x4RuKqCsSV8MIDmKIqldFPk3U4D3WeBPTGwK1G3IwYmEyCdIGvn0w7vm5jC3qkpTFmLBACJR5UVqPICWT+DcxXEBQ201nZ4xPW8QMYdLkwdMldXdQ1BRaFVHTPOBGODC0SrnSJtp0jTBN3JLoyNECUJ0jSFEFBUHrnzKLxiJcvQL0sMygL9okA/z5C7IbF2KKqg53YQVN7BidS6asCrjNdsN2w0A4JlAyaGZQNLhFacILYmaL3jCLGN0EkStKxFJ21hotVGK4ox1WmjHUVIrEU7iVAWBcR7iKvQ7w2Q9wZYW1vD2loPZV4Gb+6qCnpoDkEmgSjraEDea13dH1oBKggCwxREFJ5AxsBaiziJEKcJkm4KjaOQGJgXuHd1Fcf6PT3aX8GqVJoBUgCuIFNVxKUDFaLIxZgBmNcgWFXoClT7xJwD5NgYCMDqKwMBmcioiDr1viTmgozJGVQISQHRXMRmgGQgzQ1RVledCyIuiLkM5NlUROyYretTf73SDCiMCY+ZFSdZsYfDDnU6eW6CURo0aAh0gwYNvsJINLYoaI4R6zGN9HhFet0/OoLEEVQiQKPImqQSSaGcGmjiVRI4TRBzDEUEwxFU67Kl8zCmhEgJkQKAC2bAaqHahtI0oPPkZa+FXJwQ743Uz0XquzGQpoCdMQnvSFvY2ZrA3qkpmowjJASQKyFFhSLLMVgr4CoH72rzaiLAUiiNYt3RA1I3BRKBTSCEWrtwEGloVpRaw8sMZkZkLaLIIkkTJK04hLK0UsRxiqiVwMZRiCY3DBgDJwqhQJIr70NTnyrK4WMfovC8CpwIeFg1JwIz1dIOwBqDpLbTswCMIaTWwpqgvrbGBALrPAiKsijgKg9XVsj6GYoiR167mxRViSIr4ZwDVOGrarSeiAATBdmLF0WIBwzWc2Cg3pKhiq+BZItXGCZYYrAxsGmCVqeFtJWCkwgVM1bKEicGGY7113B0sIqlItMeVAvAl+DSgbKKOCuJ+7A8ADj3UhPcyBTqJAehgPclsXUMiPj6i1Wp5qtOhUoABUcmAzSDUg5IESrNlEF4AEhBJAUx5wgV54qIK2ZTERk34MyDedggqCOpxgIrdg0rzkaxHxizqWsqzw0aNAS6QYMG/4GJNAMHscH6Do4x48zmajRU7Mito/AJIIkxJoVK6g0nUE0AjaEwCARMQOIAlCAqQVTBkwMcoLAAJ6zSFe9mobSTQHsssMeg2hUBO2LoRKySxoBtAzTBMc2lHezqTGBXt4PJOKYWM8h7+KJAOSjh8wpV5UJQiyq8Sh3UUbMdrpMPa35NPEzACy4RtaA70PyRSwXVldlAMImDWzIZhjEMYy3iNAIbCzYGURwhii2stTARI4pCOiIzh8Y7MrX8YegmwuGjRUCEOq0xBIt4L1BRiHeonIN4j6IoUbkK3nm4wqGqKrjKw7uQ7OecC5IVXRfyEOq4cMsjEiyqtR1eXYkfOZ0EYl0z1DodkECqYGbESYQojpC0E8StBHG7DWGDtarCyf4AJwZ9HF5ZxEI50D4EedBU+IpMkYP7QrwsoGWnWCFgIIYrgqoqKVnWUKQXB1AFgSOCY+KwUogkpMCLMJuSSHMB5VAdADKABIkGQLn3nNuIcwrpgSWxK6kcap3JMxeOiHwt15CRs8ZQpgEgOGwAY5Hcjb9zgwYNgW7QoMF/sGPAVvfbVKMdj2zvRpZ3OkakfRJZG6v6FKqJU0kNmwTgxDtnAGNhlAAS+NLB2gogh9J7mEBKDGBhOPVF1QZ0gplmxMssMe0glTkjMmdJp2NgKlFpW0iaACYB0QTHmGu1aVdnAjs7HXSsxYSJEEHh8xJVXqDKS7jKoSwqOPHwKkBdZw8a5FDxFVWoCkiDjpeG7BHBSo90PR2xLmDXpFPq99YVW9U6zrsO3WOCUi0jqZMQmWlMJgGYYeKirjcJioZoc+90RGSHGmnv6l42YDSQkBi+Pu4hGSYT/vY18RdR0DBFsX59lPo4nDAQRtKX2ucEbBhRHCFOY7TbLUSdBGQtPBH6zmNxkOP4oIfjvVWcyvvoq0MGoAS0DNrmogRWiKOTnmhBiFaIaOArnxNUlamWcpMla0ihSl48DDv1WkK1IkYFsFfxjpgdgIqMKSCagXgAkqx218hBnHvvcwsuKeGiqlwJ4iqt3TXCLfPM7NeGDYLMggVW7Bm3pQNq0owtrOka8tygQUOgGzRo8B+QSJ8DiR7TRoswVoTRCbZ3qSaRSNBHI7KJqsQqwa3DOxcZw9YbWMBQyJ+GwCOUVGv2DA8D5hhADGgMry2A2gDaRDoJwiSRzrDHDEOnjfqpGOhEKmkMiQ0QtQAzwRFNRSntbE9gZ6eL2VYLXWsREYCyQlU65IMcvqpQlCWc87V/tARtNDAim4RgNRG4qQSiqRSqtrXEgcfIa2haXBfAMgfJCKQm0kO9dV3NprrEPdQRD51CQmxfTX6HLLyuhNPQpWOklQ7ldA3+cPBeRx+hUk8OhkQZtT68/nICQIJRzKNITfAlOIQYE7obozSGjWJESYykk8LaCJ4JAxEMnMdinmExG+Bkv4elYoCeOuQIsvKKWHKQr8C5MvdgzIKIHPOejinrEtgUBFYVbwEkgLYASgFEofjNqupdaAikAqSFOl8Sc6mqJRglwxQgykA6ACizxJkXzYh8UbtrlJULxLm+eRD7DmW+H6QaMpJsMAsWrABcE+cN1ebNlnTaaJ4bNGgIdIMGDRoSfQYSDWywvJsZSzMcVqNDCEsEtTEgiTUSAyZW1ci7ygIwwTS5ZqjwWitrGTCGVa14WEBtTaQjMFuIt8HlAwmptgHtMtGUQmetl1lDMm1UurGiHUOTCBolALfAPBO3ab7TxUzSxlyrjZlWiyIALA7qPaqigvc+VKnLEq6sIJUE9kk0okZU+zAT1aSYw+rRofRBass6UciwSbGmWIS6ymy01lqvv1droj2sFpNSMC2mMblFvSXESfj/2uYufE3QcIMA8YBQ0CarYN0OTwkkGrTghJG2GxLGwFyzagLY1rKTNEarFcPGFjAGaiwcGJnz2qsqHFtdxULex2I+0GWXoQC0BKQiSAX2JchXxE6IS2HT98ASvB4H6X0AnVClVbBxzGrESQrSFpg6pNQBNAU4qttbvTpfkeE8aJo1V0EB1RzW5GyogATyLBRkG7a2pXPOFSCuYlBVEldg4wJ5HoWgyOla5yF5HjUHbkecm3CUBg0aAt2gQYPmuHAmt45xEj1sMNwmzXBMHx2pRIhsVJUaWasWTo3TkdUd17Z3bIwxHmrhvYVyxKIWESzARiA0ytYGAFYO/88x4FtQahO0C+i0EcwY6I4YMmsh04lqx0JjA9gEoEkT01Tcpqk41R2dDs22WpoaSy1jEBsDAw+X5/BFCfWCclChLIOmGCqAC02GWus4FEELTUMphgAiEuYH6350oJp9j+QU9ZpcV0fUleuRDlmHPY/B6aIu1NdOfVAVqAbiTULjPD+QctL1zx5tzJqkg0aabTYGxjJsZGGTCCaOYNIINooBYjhSDCqHXlViKctwqtfHYt7Xnit1TSspAe8A5wiVI1NUiqwi6jtwX9kMxGumhAEi2wfRqlZuFUQrAA3YGC8VmNmngHaUqKOiHRPZFhSxqJh6fuIMRt7NmRdkUM2YbQ6iPBBnHYBkAM85WDIQF3C+AKhKiF1BhQOzA1FoEByGoAyJszFhBW9IEhwFopyNRDdo0KAh0A0aNGgI9JaVaAQSPURZ11fPQKRVbe3YYQG1kapFZE1VVcZaY+t8bOsqNcZaGyrUGpnYRL7QuLbDM3XCYbhUbsgDcBARGKMwBnDOwmvMrG2BTpHSHMTvtETzrDobQ6cBPxEDHauSGiBKAG7DUEJMXZtgtt3BVJpiIk4wmcSYiCxiMCImQAS+quBLB60cxAnKMtyLCqqyCmR6GDFex6NIXcHmUcMhAFoPOSGEVMNh9XqYgU207jCotWWIYl2bvP45WotMaPQeKMCGUdN8EBmw4dHNWgNjLDi24MjCWAuKGGBGIUC/qtB3Dv3KYa3MAnEe9LXnchQqWkClAJwDiiqki/Q9uFdBewqz5onWAOoJow/YTKEFk5bCXEK0gEgJIsdgFe8NAzFALTXUhqANphYbSgAa2h968b4EqGCmQQhPMQOoZgDlIB6QaAbSgScfiDP7HBWPdM7Mxg0ok5o8rzcI0lCQPu7nfJpk42wEukGDBg2BbtCgQUOgtyXT2FiNHmJM2jHnGKo0RqQ5SDtCGAtUDKBB7hHuOYIaILKVlhYwsTEm+EiHlMMYTi0MgjdGyIX2MCY0II4S5jwMDLxzFtCYmTuiNMksM1rpLKA7DGGHId0h4qYiUDeGppFqwhAbAdYAHAHcgaFunKJrInRNhOlWmyZbLbRii7aNkHBwn7DEIFGoF6gXeO8glUBV4EXgSlfrmkNCotYufuPa5dBkqOsRhoRR5MpQozx0xGACSOsq9lBKwqHKPfSIZlM7glgGmZDCyHEUCDoTDBsIE4QIFYBMBIOqQq/IsZJn6LlS18oCa2WJgZTIoeoB9YBUgBNw5YhyBx5URGtKZsmRLimwyMQrAl1TogGDchFUMLU0oqrCMhojqARgJTaREe8jCMdsNSWi1DuJiSlhIuO9JzIsTOwALQBkRJxJcNfI1m3pdABQTiwZOZNXiSsDeTZlkGtsIdUYD0EZEujTGwUb8tygQYOGQDdo0OC8jg2MM1vdjeHAmKxjTNoBz4ASpsY00tpiaJ+haXAUVmVATaxqSqiJ1EZqJYJqrMoJUCVeYQ3YAmDvPUxs1HtIUPsabyyJ9xADEu8cDIz1cBaGgx+10RReO4B2QTRJ0ClAp4ximlSnWTEZESYMpBMBKatGBt5GAEUAxSCKySBhg7aJ0I0TtKMYnShGO06QGovUGBgiitkgiSyktp2zhgPzl5AhoyKBEEvNw0ThSUFSa5INAX49XIXZwPvg7BEUIHW1mgDl4IZBHDyqh52BAoVXhROENERVLZxDqYK8KjEoS6yVJdaqCn1fou9KFOKQQ1AFsqwCUgeI48gpqBJo5oj7orLmQCvKZlnVr7AxK6K6pko9MGUgKQHjGPAQsEAI1jIqYTbM4v16KqbAgMlCEJHRKMxfxKioMZYhAoWoA1BSZAqQZhDNIJTBSEbCNYn2ObHJULmiIi6TkCJYZWwdaOC31DhbKzjOY4T5NOKMM5Dnhjg3aNCcJBs0aNDgnFMLtzt+0EYyvYlIzwmNXDtCRXrYeUfQIYluMVQMVGysEqnaWK3ETjWGSgwggrIFvDEwDCh579UYqx5e4dd9eI21gFMCPHsoG4A9YOuExJgNUlFtQbRDqhOATjJoioApgk4xaIIgXQttx6oJQ+O6Sm1MsIcmDvoCsiBK2CA1MRK2SIxBRIzIGiRRBMOMxFjExoJVEZFBbA1Yg10e1zZ2w+qzJQ7skgA/5k0dTDYUQ7MMD0FZBRs+V3tbV86h9IEkOwhKVRSuQikeeVWhUA8nDlVdVS4AdYB6kHqw90TOAZWHKVQ1V6JMiTIPHRCoT5HpiZc1r7pm2PSJaOBEckAzkCmZjRNIPUg1UASdO5OFCDOzEfFcG73xkESzBauSUREma2stC1SVHCAlsylAQf8sRBmkyg1siOBmyYm4qJzPQVyCTAViB87dSOfMLFgiBYxgHsBJK9sQ53MhzQ15btCgOUE2aNCgwVkJNM6BQG/hJ70FkYYQZjUQZ5F1Er2qhK5SLfUIumnVCBpFUI1hTQzVGE4jY4wFqsg7GKyTYwoGzaiZm1UPB3jAwAbCY9YH6r0jGBgDY7zTOLg9aAegCRiaIvhpCE2R6iSpdgzQMvApAzErIoJaIo0IiEjFBH+K0BBJY+R6eG+IweD6MakNEdjEFDymmWms7E80rDRr3eo39HuuJdTqVcLaFA+vqr6O2faq6uDhR8Q4mHAE871gzgFiL4DzisoRVwKqBFwpUSlAIYZz9TpQ1T6D+gLKmJGJaK6QAsFGrs5BIQ8RB4Mgo2EDiCcAYRsiMsE5JWwrDk2fBAAiUgu3EUYFAJbXLeGYnIS0yhJkCzZUiEhRa55zkM9BXETMZVWZIiFXFmwqkHEYTxE0RrBIGhw1hrctpRrA9t7ODXFu0KBBQ6AbNGhwv0j0ZpKsZzimbOHcMU6kAcxJIM+L9TunttNM15Z4kQZbvFIiazVWHemkrYcaeM/GGHh4Cj4aUHgPA6iHFQM/iln2Q2JkATgQjAmVUu9iMLXA3IL3bYBaUE0hkhCQMDQBkBKQAtoWopQUqSVNGJKSUkRQC5BhqCXAkCozUNv+EfEoimSUvzKygsb649FztJ7MsYHMjT9Xe4CogrR2shYNRFkUcAJyouQ8tABRQcSZqg6UMfDEoRlPtFBwCeYipGtLCaYKwh4QZa6/U6Aw5OEhYcpgwrjEI9iOeIZXw5FhgK2oD3GLTghQZgmW0wyIMCkYYLDWEyCFUC23RgWiCqCSiAp4KTxxWRPnMjhscAlyVUpcEZkq49zX+vihbCM4a5w8K3HeikRLQ5wbNGjQEOgGDRo8GJVonIVEb1GNHkI2PRbCjDBEaOTiMbpPbW2JF0EliiIbwlq0JtIqsS+9MbFhQNkDbAB4X/veGSgAD09DEh1ulryBRU2oyUCNV7WAswAiOLYAbG2zZ8Jjb4NWV2MEP+o69EViBtU63lq6UDdLmsCbWVSHPX8I3JaJ6wxEApGE1kAGlFmFlJiH3FrBaiBDnYowqYrSsDYNIgp5K8GDQwhQH0ysnYA9AKesBQEhiAQoiCgXoRyQEoADyMHAM4yTkKMoo8I4mAM5xnCdIjIGlQcxM4nIsJmUmZnhQQiaZ4YBMQyBAakqsEDBRkS8cmREZKhnh2djnXjvjLUVIBWESoAKIl+BuHTkSjBXcUkVEVfMxhGxH5Dx4MG6ZGNInpkVxyPB6dHbQGNN16BBg4ZAN2jQ4EECn8Mxg85Mvg8CqDYRaGDj327dEm8jkeZaJ20gEkETC/UxVOsKtEnGKtIWI39p5Zro1dnVEA+vBjYQQyLxzkmdwaewULi6uS38L21opAwpiYRRnElNklUtwxjAW4gGU2WABMPKMxgQiICYa7cHEQ3yXxmuXKqlDQyuv1OUAGFmJgGIwcFbeih7CIHjVFPcWg7BAITr946yx4VZa+7twLXsIkgwwr2BB0jYGIGHCLzAe3AcQ8oSMIbHSHSdm2hG21ngg4hFQcNKNAMEZkDCrIUZkNqAj8OoRbwIG+PhvRDV1oQg54kq46iiyDsQlVQnB1JVVSWxS0CuYOPaxJ7I+D71Tw9D2UCeG2eNBg0aNAS6QYMGD19K4bkeQza5d1wDoKRAorcj0H5d3jFy8AAAz5gC1S4eXEs77FDaEanGOtRIQ6OaSNc2eSB4TzUBrHm0UwNSwKj367KO9aDrQJ6NMeTD/wZC5pwO32cs4J2OV+d5nWNviU2kjcYkAg6AHXuroxAVGD7f1N/hR9+jNNRbeyBUelkNjGF4tQgdlkb8ekDN2Bi1JvAChtQWgFIPO4zNk8BAa8/toFoOmevEhilMIhBcRgxtlD0YI6ir/mwMxHuFH+nPg/OF92KG74V4EDw8eQ/vLJELoprYkfMOIEfkSoBcSexTIk/EPlScN1jT6eg+PNaN5Lkhzg0aNGgIdIMGDR5ef2icZ0V6WIUeekXT1gR6M4neQtqxAkJ3FBlu1yPDJY4iG6lq5KoyWDqrWgQpB8MaHjUsAlyTvKEWGsbacSJFUA3kOTE1vyVB4XRYrQ4EOrzZ2EB+vXMwdp2MeQc1FkoUKeDUOSjgPBDVjs9uFIdiIwtXOYTUO6UxYl2T34qstVyHzZB3zphaqhJi0euqu0c9cTAWhg3gDYMtFMH9ot4uzEZq9i5MUPCI2IuI9zCmJtCi8FA2BhKstjHUKvNQf00UmhMBAbwYWPFww+bNYWUfoaEP6sN69PVVgNrDmzzgPOLYo3IOSeJQskuo9ETscmIPkIBzXyfDrFec10NQ5AxhKLKJKDf65gYNGjQEukGDBg/5MYPOQ8axTUPigbNUo8dI9LwQTo6q04xJbzZFho+SDqESAbBQy0BlgqudJQCslfKocoshAQYBVgMBtgCUvHNhrIEcqxlVjZ16t161NNaSh1vnuzUxMxbwfpQXKNYCgUB7H6rNToFIbAR1FYKaIhDrzZOMOjIlIqBiwBqjwwhzZVjL3rngRmIMe+8tmC0Aw2BTu19Y8TAMcJCCAAIoh6K8ihcFiTBYBCIMIzCQWplRE08/JMu63ojpxcAGAkzkAS/eQYy1QuTFAQoHtTZSuEodSK0NIg9XheWPYhJU5BGTVFSFzynJA+TSutKchfRA2VBtHo/fHiYJWisbifMoglvQ6JsbNGjQEOgGDRo8Ao8fdG6OHOcSxrIdmd4k75jyjBVldLyFiE01NXkg0QaqJoayqnIVyCZFiIxWJTuArbX1PeCcUpBNANZacm58rA6AVYugshiSQmBDEjfXbh6wFnWleQgHYNjABoQK9JDERQAqqe8BRLBRkGi4Kny3hYZxwpIDGKq1Xd76RMAYwx6ODQzBGKPOWQSfbCPwzGyMiA+NfTAk3hNTvQwMDXnf5MX7oIOOjcB7T6FiHCrL482XREPJiwfgg3bZeecoVImJPFAJokhRkUaAApVWYRFHVeMYUCSpUFlKMfw84vD/xNIhlj4N1onzVqR5Q8V52CR4ZJwwC5rwkwYNGjQEukGDBl9mUeC6DXHegkgfxMbq65A4G93SwWNeQly494wVqUmlGLTUhJTDjKEJj6q4qhxDg5WzFow4pgo6dJTDUHMc1eOpqnocqoQoChx3hAqIouHDILGIImysJo+qyDVZRiDMRFsQuQgjeQkqqtl6Tc4DWUZdeTYwBhYMpwx48nX1ebRejamr0iHwBWADg6Bdrvv+pPTBmcSTck2ShcjVtiV+SI4NIN6SGFg/1ItbC3GOBHBio8gTkasqJwB8TCQlaEi0x/Xe69XfghQpAJCmgObD9xELQIpAmrWuOutpCYLMipOs2LVl/PZ25LlBgwYNGgLdoEGDL1vt9FmI9EEC7hz6R2N7rfT4845HFemha0cPhI5uSDxsocWqSvkoPnzMUUOVNjmOIIZSuXl8ZSidjoj16Q2WtK5hPm15ayI3TqA3vLfWaVveKN+AgVOGDRVoAGxscPoY13V7X68joxQq0GAE3TIHJxKz3uTovcJADYwEYkxijPHee28sOSJyzkFGWmU4D4oFqCRCLFWYCNRV6WHVuZZZDAkz5TV5bWubSAcA2vWyD4gU6K+vFyJFD4oJ0g2kGcBpxBmb47dPaxBsiHODBg0aAt2gQYOv2OPNFuRzncButL87E4bVacejpMPF2sFjahQXTljTQEg7qOPDW2OWdBmAFqADAurnVSkBUGy5DDkByTqB1tOI8FYEGWcg0EMyzBFiqqCMSCkCWMtQgXZWTWgqDH8b3eACMtRtY+QkYmtdiduwTjHuBGKsVe+cgMjXlWVvI3KOyAVJBQlQBp3y0DmESBJQkF1QLa0gkjblMhiS4SF53fR4oh7A2ngVfv3xukRjkRRzWJdoAMDx8SCUUey2nCE5sEGDBg0aAt2gQYP/MIEt21R2hxKPO3G6dvru+n17xlw83CYiq+G1KVDtLV2T1g4BPYw7cGz47vrvFlqUDYn2kHRruqGKnkIpx3iFOg8MPEkB5ADSmjDmoz+RKyEBoQAhSXhdylFXyisQopE3NUOtWZ9UWLIRyFUONrKjei4cCFbJjbnkDY3ynBs1822w1CNHApCvULmxivJ4ZbmWZWSKDIo2CQak6IyR5h4pJsaqxpur7ys1GZ6pn10ixSwQorYBzAFYsGOacR6rNG9bbW4aAxs0aNAQ6AYNGjREemsyPZJ3nOF/D2Bd7uFPt8ODBCI9o4QQNBLes6KECV0nzD0A3bFjpG6SZaiezZHkTNAN/zuoiXwLCNptEFR4TMJBGyQnMRiFnjbBiEYfGa0vV6RUrausUVWVhsexAtWIiNK6dllB7EKleWgTl61rkccrzEOCvE6W15drXH4xxOJ49Z31dJJcP94DBF3zEBuIszTV5gYNGjQEukGDBg3Om0iPmhO3OZ5tZ4/n10n0nBAWaks8AJgSOu1zxkmy6mapxvbHz0C+z0Sat15e3aDHHrtP18nzhu/PKZSwT/uqLaQltRhlTC6xLk8J5DcBlIglXyfNMkaW10NKxsnyOFEeEuS5+hsWtiHIpz1ntnl892bf5sa/uUGDBg2BbtCgQYNzPE4xtvSRPttx7eAWoS3jlng1kd6KKC8JYQrACoCpLYi16pnHsVYT1UkAqwCmaHvCN/yOcZKum5obVU+PUx9oqFqftuyt8zq+twAN0pQN1WU5I2kerz4vbEeMx7EVYTab3nu3bp/cuIE8N2jQoEFDoBs0aNDgPEn0mY5f21ji4QzSDgBztV769EpzwNKGKjW2aR7c2BC3Tr6D9ndmi9EujT0evj6UlqgSVmsSvpm09+rv724jMdmAzqYv7WNbacn4+Ifx2MPmvvHlWyQ9nTRvR543E+Utq8zYJuykIc4NGjRoCHSDBg0aPEBJB59niMsWOEBbh7UIYdeIwK6T2SE5XRxzzZjZ9L5xrIwRydmhtGGz+8Y2ZHPW82mEWGR7crxV9Xwca7qRaJ9xDZNucb8xvGRhK9J8JoIMAHcjaNPv1jPIWrYizo3GuUGDBg2BbtCgQYMLWIk+nzjxcZK2Ddk+sC7v2FPfD4mrCG0gsdtVqYG6okzrfs9zwEaJw5kqtZvSFufGdMRzABaUMDs2hqVtiTxtKRE5bW1sWz3faCk3fG3kw7yZOJ9RinEmHbiehTw3aNCgQUOgGzRo0OACNxaeD3HGlg4YW372Adq2On18SG5r0rpQk1tsapybZ8XJMxFno8CR+vF+YNvY8i0I9jyAk/Xrs0pYBIIVXP2WGT37sX2MdA+l3lu6ZyySYr5+bhRiMm4rt4E06zk2Tp5NttGgQYMGDYFu0KBBgweJRJ/tWKZnIWy0RXV70+PNco8tCO68EE4CgdhuVWHeSuZwZOzvA2NSh/1nSFyssQfA0c0kexPhHhL8zVXmszU/bqVx3sXrzYNHT/NkPtO6xjlUnRvi3KBBg4ZAN2jQoMFDfOw6l8qzPkDrvDrE5c4zEGps0gB7WifNR7YjiXruiY0HzkyqTxvHFuR6fqzyvKCEuU3OIBts5zZJNfYPF2O4THdvVT3efE9bLPf5bpMGDRo0aAh0gwYNGnyZSkW2qXofOMNx9G49BxnJ/Tku05mbI7dzHdlUNR/Hya2kJltpnLe1mjuTrhkNaW7QoEFDoBs0aNDgP95x8kyyETrP9EF9gJX186jOb+M4smfsXUe3c9G4+0zjPpN2uZFkNGjQoCHQDRo0aNDgnI6ddB4k+lwI+/l+Fp2B9J+JnJ+J3J8rgW4qzA0aNGgIdIMGDRo0eEQfm/UcK9jnkuCoF/jvBg0aNGgIdIMGDRo0+IrQdI8f989Hm9wQ5AYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KBBgwYNGjRo0KABGhu7Bl/GuywRoPqV46pFFH6GD+YyDb9jiEfC+ts8pq3wcIyTiL6i9q9zWfciIdb75ptvHt4rEemX87Jseo027lanLxpziC//St/2X27bs9keDRo0aHA/oaqkqmcLgoACdK7vfSjHPu6/OxzfdmN8iMdOqhvH9EBvm0I7tro9UA/jC71NzlhM2LRMX8m/IQIQAWjVt/gRuszDfY3P8bdu6uWKAST1La6fP+O6OnToED8c236b3xaP3bZ7nb5c9sPx39Wm5xo0+LKBbVZBgy+DioQCaO3YsWN6bs+eSSuWVYsqz1Eyl0JEWpalp+XlHER9ANUjpYpIRPHk5GQnTeeiLDvliKioQynM7t27k7m5uXRiYkcCAMvLx/tEtAwgv4BD4NnZ2e4VV1xzibW8q1KloqiW+/nawurJkz2aLkqsTCuwopvimWXTPbZItdt0m6GpqanRSXHjibNLnY5wHMc2mpiwbW5FSBCllFhjDKsV8p6NMcIiQkaMAFT13aB/97Fjy6tHjqwBqC7QNrGYnJzYP7mrpalSWVWOjZHpKLLp9HScIokGfuA90YCIVgEMvkJ+Q8mePXsm5ucvmuAULaa4lTB1OKIpVZ5kpbYTZ9iYtZOnFu75/OEvfga93hIA90ggXsysqqp1hXK4T8a/9Ju/OfXkG26Y3bdjz/zczpm5TtqZUJIOyKQExGAYAAwBC0CAKAS+KErf662U9953LL/nyD3Ln73zzuN/94533EdExwCsDL9j7AoRPRSBMvW24prkCwC/xfdyff7W+nehX0b7YQSg29m5M6bBQIioqpcxuuKKK6a73eldSTveYYyxVe5OFUX/C9PT08fvuOMOhwYNGglHgwbnfOJMl5fz3d73DxbOXeqc7CQRS8bkzMiI2RmwEmkJY9ZmJmcXfuVXfnXxZ37mJ0/ddNNNx2+77bbyYRo3A5g8derUwUL1oPFok6UisbbvVIWEIg/fEe8nGdwRQI21S1k++NIrvv3bP33HHXccvxCE8dSpU5Oq+vg8L5/pxV8jUDJs7iU2hyPLJ4lszgbeewAGyspiDERVBYCwMeHkXc9GLBF5gL33bGDIkzB5EOBZiLg+sRM8iGj9UroHSEQsE0WqlKj6FEBLvcZEMACxV7UKGKgyEXkiKsBYaKXpPXd+8Yuff9LjHncPgKX7SxZUlU6cONExxlyci1wLkTkIsbGmYDZe1SVQbatS4r24Tre1dPcX7rn3q77qyXd3OtF9S0tLK1+Ov6EPfehD0dVX3zDv3OqBonCXOPG7VXVKxU1WXudEdaeqnyOljoqndrtz6o73/MvHvu2mm97e3bPzw72jR0893Jf0h7vfDTfc0Pnpn/7p2Wc++9mdNEk67GmamXaRwcXGmEsBHBDndwI6paodgGIhGCKi+jdJYbZHaphEVUtRXRPBMa/6ubXV1U+t9VY/d/zEiWN/+sdvXX3zm984WFtbWwCwysxOVR/Uibmqmn6/P18Bu1FVM7AWRrUyxlRRFPmqqpiIbOF9XJZlkhjjhTmfmZjo/fZv//bCD/3QDy0C6D8SucYnPvGJzsGDBy/u5fnePCt3AL4NVQ9r84i5cs6l3rm9XuSgiFwCUGKMvTtKonf/+H/5L//41je/+QgRuUbS0QBNBbpBgzOTHSLSoiguaXXMy6yZ+0ZVOcCGh9UkBcOrCAyzioiqQkAovvfVrzr57//+sX96y1v++A8OHTp0+JZbbnk4KjRxL89vmJ7d8RIwngkgJQAQSF0/ojB0MAAmQBlwx0/J8aKSNwJ4+6FDh+695ZZb5IGsv263u9uY6JXW8tMAzNcvV17giOFUQsVZN8yoBQqorJeWNZTEWIExfSm4/i4hENf/CQIEBB6VphVh4SDhKQKIwsvDS+Tg+n+1JjiK+oNEHDMvVqV7L5D82cGDF91x5513lvdne9588830sz/7swcF/MKu5RcxeBYQYmaBCAAmArgeuooXf9111y7+wqGf/fAv/NzP3nrjja981x13vLmsq4JfFvi93/u96Oqrr97JkX9+pz35DV3Bo8CY4FAFNBKqnBaAUYBVAMu4uBUnuwEY3y8XAZwa25QP9TGAVJVuvfVWs3//FfMXX7r7cbMzM88hmMdAdd5GHBNxRJAIIjEzR2yNrau3hNMlGGHbBp201nKONghzkeGDc3Mzz5yemSovuuji8tHXXLvyfT/wvZ/5q796+1+87jd+9f3Hjh07CowmlxdUIz6cJCwB3TSKvr5F9ByTJo/2oi0OPxlVKGwUEwEURTFpKyVomNx671ef8rQb3w7Yv7zhhus+8uEPf9g9YqrSqrT/oovSiy+++Dq20c9OdqNrJrtqiGDCAEkAVoIQMVsACQGRQGDBj//Ix//9+r/7q7+p0G7/PbLsWHN2bNCgQYMzoNYfJqurq99SOf9+r9rXc4AXVVXNDt979FNP+uqveR2A65n5IbvaMpQuLC4uTuWl+/nS+084Va/niFMLi9kNT3jS3wF42a233moe6DhOLS9/VV5WH/HeVyKiKqIPB6S+ne09XjeuLBGvqlre8d73fckknV9MpnZehhtuiO7XPqWHuFcUr8qd/0DpfXGOQ3dHj584csOTnvy/YMw33/C857W/HK7eDbf/ffctHsjL8qec9+9S1ZOqWm1e505EK++19F6zMrx86//58z5M8qG4O/WCh3p5x+U/L3/5yzuf/Oxnn9TL858pq+p/FaX7p7Jy91TOZ/4cdmURqSfXWz8e3+f8pn20cM451eOV13ffe/zk/37bX/71f73msTc8FUBnTNpBF3KZ//pd79rdy7JfKyv3Re+927yttkPlnO8Xxee/9wd/+LcAPO3GG2/sPpL2w3e+851Pq7z+sfN+4VyPF1kRfqI/+3O/cArAL+666KJrmzNjg0cSuFkFDR7BmCiduxjAFRwam6SuHqmI6PhjEVEJDdtaOB/v37v7qt/6rd+6aefu/d9srb3q0KGHtkHFGGMhchWpXkR1ETaMURT12H09ZowtT2Stcc4/HsC1n/zkJ+mBkhcRSRiYYmZLRIJQNRvdht+77d9jj8/rVi+TE1Fff87whk3fEW6ihNOfd14UgBHvLmbCdSrVVbjnnuQ810t4380AgS+D6jXMzH6bfWn8+yvnaPfO+b0/8RM/+fUEet6RD35wJ8LkDo9kFwMiwpve9Kb5uZ2TX0PMLybmr4LqDgA8voxUV1KJCMw0XFPqnIuJsI+Jug+HTvZHfuRHJk8sLT3+DW9600suv+Sy77TGfo8qXh5H5unWmouIOBERdV7C72jjthvJLIbrYvyy/wYJQC3JUFVs3v7WGCbVnUx46t6dO771ec9/7vf84z/+3Stuu+1tL9l36aWPVdXu0LnjQuGnfuqnsLq6OgWmrobfr3rv1QtEwnUS8eEqloiIQkQAiBehdhwffM43feM3myR5wcc/97nZR8JEr3Z1sY9//BOuJ8hzDPMkxn5v2OZ44J3TyFq97/gJffvf/K0DsCYXtjekQYMGDb5iYZIkueTYiRM/Xzm/drYizLCy5EXVeZW8LERV87f+nz//FLP96f37r5k99BAQn1Hlb3V1Pivd25z3par6DUR/rAo8qoJJqH8traz6xz7uCRmAXzn0rnfZ+3sSrPWeOHFi8WvLsvqihsu8ci6VnwdUaR6r8I2uCgyry+dR/R5WBkvnVFXlH991h5qo/YFkcvpHMLn/vMjBcJscOnSI+0Xxq7lz4lW9O8vyiog6VSmc80VV+e/87u/5EIAXXPPkJ89+GVSf7X0LC88pnLvVqS55VfHei2yzDbyqOpXh+tY/fstbPZnkVNqZfvlDQcTqai7feOON6ac//em9a2vZM/KqenPh/D2lc73Ka+W8965ehhGx9H7LfW5DlXnsdS/hGBEuxsjo/52Iuk2fNfZ54r33pfNV5bVXen/4E5/+7Bu/7wd/8KkAdh08eDC5AA4SxEwAMP1nf/FX/2+lemfpnN8w/k1XcobLPxxv5b0/tbTsn3Lj0z8J4OsOHTr0sDqp1Ns0eu2hQwcr73/NOVee6SqBH7sqkJelqqr80Vv+VIjN5zpTs88Cboiavq0GTQW6QYNzIgJx5L2PVU/fT7drJCEomJQSG1FRltFLX/yCS3/j9a/7uiNHPvWM22+/ffKhqsp0QynFqqoJ+trT9Y7DZdC68KIAiElBF846yxjrH0hX8ebK3fht8/Nn9MobKozP0deVxixBwiojgJCqYKIr/n4ftwjM1piR7prO5D8dDMeJQBRZyz/1X37y0tn53a/8wic/+agLefn+Qag+mz+49dYdc5OTX0PA1wGYYICYmbarxpIqWFHveiO3BOdB8hA1CRIA+ydv/bOnXnbllT/dake3RMzfxIS9xpgOMyyIRjXysHlodKs/6DTR74bXN1pebvgtMgDDvN3+SczMkWFrSDtQ2XP1o6587q/92q//4h+8+Y9+9M4777wuSLUfmAVl/bXlr//ar7+/3+t9WhGWZzj+0YePVddreRqICN57mpue4pfcdNMukLnp11/3puvX2wkeNoOC9Lu+4zteBOZnKpE50xUTHm4rVTAz+nmOP/3Tt66oyGe7E9PHgA9XzVmxQUOgGzQ41x30fl4i9QDYGCqqMv3+V3/fdT/x06994R133PHor//6l3ceuuYaoZqzbUtKiQihFSn0NIXOOqoAVLj9AgzBqujDEIKweZJwrgEq4+8fJ7iqCog6KBU97ssD3CbnthxD4s9EZVXh0Y+6auqnfuonn5SvrV36u7/7u4+4aljtpYtDv/mb7W/+puc8X4meboyZBzD6Eck2k7lAYsbWksIrsFrbLj7Y5Nnc+pd/eVFWFN+xc37mew3wAsPmKcy80wTSpRjNogmihOFgdRMpFtWhhmOL/YzOGtozTsq3CjhSVY2MZQJ2x5F92ite8fIXf+DDH/3eR1/3+BcS0fQDkHSoquLGG28s33PHP3303z728U+R4dx5Jxsm2/U+udVvzBpDXhUvedGLuvsvOvCs3vLxq84lrOhB2hehqjh06FCyd99FN4jIo3CWA6+qAqrwIoiM0Y989GP0znf+w6ejdOItx1fL+5qzYYOGQDdocM4n19Krkic6/aQ0fmLQsZPl+ImPiIiIVcTv/oWf//kbb/rWb3/uP/zDH19z00N0adPUdg6bx7UVsaQhdVYoEWW4QHo/a60MT1vMfN6pf+PreStysVlnetpybXrvWavVY5+jqhj5HKhCCSvKehzBWu+8cfOmAx9tH8gzqmgO/zbM6rwzr3rVd0993bO+4bpXv/rVV916662PxMvJ9gde9p2XtJLoZSp6g/deSISoJs9nSnkL/KXeVwwVULnPMtYe5FCU5H0f+chlL3j+859jrH0NAy8yzPtGGm0isOqoBsu8Ph+t3wBRDcS5Pg7osBq9aV+TMDGol3N9a5/L/jlaL0FnQQSoYSbn/OU3PP7677jt/7z1R5/ytV/7dSKy54E0/95+++0ewOG/+du//WSZF3cRmXK49KNJwTa/Pa7Xxd49u+Jv/daXXSpS7RIRfhgLH8kLXnDT/lYa74qYY+KzD2U4CQIgb3zDG/vFoPf+b3/ZC/8cq0cWHw4nmAYNGgLd4MsSRUGOmd1WrmGbq7ibT4DDHdtwuDDY6Xbmf/3Xfu3bn3bj05932y23HLjppkPRgz1+GRnByZbEcvNjCv+jUKwB6OMClKB1vTHnnK20zs1nVbe9FHumSvPZKmJD8kOjz1t/nlROKPyd6HTKbQdxFgJN4A0Hvc3LOqyC6ZCUrRNtcpXDjpmZ+Gde+9M3pe3JF/34r/1aPLbp8EhwO/hf/+vWiyamu8+wbC6JrUm4lr9s9XvZLOWo13cwXGaTQdxnFbT4II43es973nPJEx/72Jcx8JPMfIVhNqpqhnMcHVaUxza31kaLw22jw0GHRsBNGyOQSidad0yu7zSiocx+rr7Cm95HDLC1xjjnk0cdPHjDH7/5j2551rO+4XkvfelL5w8dOmTvbwMlEcnv/fYbPnbXnXf9NRleCddNVHGW30492QAD9C3f/HwzNTU3OzGxd/amm27ih+NKyPNvumnvRQf2PpsUewnAcCJ3pvHX1Wd89N/+3f3t29/+Xo6i93/pkkvc/fm9N2jQEOgG/0FxEwByhshtbJrfnuCNnq+rNMNqjbEWrnLRvj279v3eG37vBVdccfVLb/ubX5l+KKJjN5z+xy4Rn7Y867pGZaZVAL1rr71WH8oTx2ZCVVUOlXNwzmlVVVo5p1Xl1u+ravSeqnLDx/Vrm9/rTvv/sr5VLtzKcEPpHErvULoKpasgIlK6CuL1ZOyTu3H55dWFWt4zEfqhdnso5YiiCEVZ8o1f+7UX/9hrfuzxR/71X6957nOf136knNiJSJ/7ouc8ioluAtFuAg3Z8wYJw+bf0IarNuvF9xzQL0RJa/lB0mnH7/nABy590lc/5eUKfCuJXMZAuvk3ufmqx/iSiNbWFN7Xvx+CeEFZliiqCt5LINpEICZVQEW8Vr7S0pXqazmLbvqOzfvEds/r6CqP4Uqke8klF1/9xj/8/Vd93TOe9bJbbrll7v5WokWElpdP3PUv7/uXO5zzx52IH1kMbdf7UY+NmaGieMITbqDnfcvzH9PrHX1qls0kD4cjx8+85qf2djsTzxbVPcNIx3EpylbHHqmTJv/8bW9zJ08ee+fll1zz7jtuuaUhzg0aAt2gwbnjNgWy2kZNz1rB3Ez+ZJwgqCKxloqyoquvvOLRv/8Hb/qWyPuv27t379yD3AwWmt/Am6Ulpy9L/VhElUKS2ODh0C2OE4YosoishbWWoiiiyFqKIlvfRxRF0eg9UWSHj8N7ovH3bnwcR1F9H26RDbfYWkqsRWItYhshthFaSQpmllardVxVDl9yyc4F3HGHv/9LKRtkNVtNzE7bPuPkCkTWGP7PP/xDV137mOu++Z3vfOeOh7uhcNg4+L73ve+SNEqeqtAbmLgTroAML4uPVWrH9rczSIoqACdi5f6FnMTV1Un7Lx/60KVPePzjX+jEvcQYcy2YFbXE5Iy2cxtOXgT1Al9P4Jz3iCOLJI6RRBGsNWAiOC+onCdSUGIMtaKIWnFMsbUInZIO3vuRDOR8uuRoKO0ANC9Lvmjfvif9zu/9zrcfvOqq57zyla/c9QAm6f3X/c7vfObkyZP/SsxHa+nIWcdXNxMiTWJ93vOf99goaT3t3R9/R/IwNBDSddddsxPQq601XS/1EXm84XPTJM57D2sM3XPkXvent9520pjk43fe+fF7m8pzAzRJhA0aXPBo3y1kEwriOkpuU4UxjiwXVaVPfcpXX/EHf/jm73v5d3z74qH/+l9vByC3PAhVDgUYzOQBHVUzh81pm6QO45UZBUoA7sI3xJ99vYoIjDFYWl7Rv/7rv4Yx1htjSiJy9UyGRMChaZ44EASFCZpHlVBOB2r1cv1nOHcyQUShKsThcq0SjdIM4VVJxRsJck4yzBARTdJ05ciRI/8Ko5/+1Kc+9YBTJUeX/jedwEcaWl2XCgzdOJQoOFUYpqIodc/unQdvufnml7zkxS9890033XTstttue1gcAoaJk69//evTR11zzYtI/bNBbFQ8as4FEI/tAVRHS+rIFWXrSRQ8gMxOxw6nLijR5zf+8R/vu/6x1389VL/fEO1z3gsxB7HVFr/b8W0y7ppReQ9VQpokAKCLq2v4yMc+p//2sY/pXXd9QZdXVmRtdUWLohRV0ThJMDk5hR1zczhw6QE87vrr6epHPYqnuh0GwA5C4oQia8/aejeut673EYrimIqykCsOHrz+f77xTa/5xm/4+tXp6el/OnTo0Mr5JIoOfbk//dGPLr3zHX//tlf8p1ccUNH9YFKuV8yZrp4Ya+BE8MxnPXP/Vz3pyVf9yz+/K+bwW3rIPMh/6Zd+aWcUJRcDGm9wPBkrauim8YsqIiK84+//fuXzn/nkR2Z37VtaPH5vo3tu0BDoBg3ODzcR8NfMvJH9bXfpb/h42Eiz3UkvspZK7ye+7WUvfezq8spzfvD7v29FVT9yyy23XNDR9/t9mkpT2kDaaoKAM1TY6kYuvpAVzfvTiX/48GG8+tU/KEVZ3KuCT6q4TwG6CmgC2B1g3kOEKSjHIQRFKwCZqOYAFQAqQCqoegRTFKnjvgk6amzSeqIgoYhHUwB2gbELSt16DSxC5N8B/DVa0x9CtqAP9KIbja3rM62a8TP3iMABiCODwnn7zd/yzfv+06u+7xV/8KY3OGa+/aEgKNs0a5lnP/uFs2kreQKBHmVqMjqSMqlCx3Ynv8WEYZt95EJHVfPXfM3XtL/tJS99ARO+l5j3MJEd/zLdhjBvmDSrwnlBHEXIS6f/8r7349Zbb6Pbb78d9953nyycONEH/CqAlfq2BiADUAwNegBEczt3dy+/5NK5pzztqTuf89znzD3u8Y9vz01NUiUCrpsEz/ab4nqmEUJPFNbGXJZl/HVPfcrlv/363/nR73nVd0U333zzrbfccsv9IYL93/qt//mRF734BXd3Ol0HIRYO3nY8XB+bpDejyZ8I5qen+bu/+7s6//LP72o/1LvlC1/ykm8kwouJKAlVeqJ1Z0hdPxZumjisDTL6wz/8w8MG+ON0ZuJOHH/YbPgaNGgIdIMvV9yGNE1ZnJrx4+eWJ9Rt6q1UM7PN1UZrjPHez/ynV333N37+rruWiejEu971rnuf/vSnO1zYEjTz2BhoGx30xi5/ggLRw/XbHI4riqIqTdNjXvRvjI3+gYS/ZAx6qhLlpNMK3cFCXaMa1dqTSohKDyosUelInAU8EXk48ojG5Ks1m3MEjUAeRAJVFqauOJljg1ktpQ0IyPIKjP1i5KN/7/WOnbqQmjXmcyKRY3aDOiR4ZABYw+0f/dH//Mx3vvMfPr26vPixb/iGb1i77bbbPB7i6vN73/ve3fv2zb+EgOvjKGp5H6aQwwmlEkYa4XEqomPNmpt/OwJlALGser5Al0D0m77pm7pv+qM/en4cRS8C4Vrd5LB49okewXkPYwwiZvzjP92O173u9fS37/i7rMz7hwG6k0x8X9RqL0St9oo1ZlW9rKkxA2LNLXNFIHEAuTyzywuL7Q+cODb1gQ+8b+43fuM3dr7oRS/c8wM/+IOXf+3TnnYVGZ6S+qoRbZK8bDZvHlZWh6TQGoO8KtNv/daXPvk97373USI6ftNNN/3rbbfdlp2PnIqZ/cc+9p7Ff//EJz711V/zNZ/33h80MEw01hms41dVdLwRllQVz3zGM3ZfeumVzz527PBf5nl+pJaU6IO5P95www100f79jwH0BkNsRTdVn4nCjHlsAlBVFaIo0re97c/pQx/8wKloZubD933mMwuN80aDhkA3aHA/kCNlpdOvNG/2Gj6tGWqT/pnW0xCCw0J4L1viq3/hF37u2Z/9zGfuffrTn/53t95669GXvvSl/gI2GBABMGMn4LO6UKiSEuyF+m1GYw4N5+jdOqz4DLzKR8jwnw3WFv7ppfRSvubQNed8IrsFwM9v8/yhscc/N3o8vAJwaPSmQ+P/FyQ2+mDKgTbYvNWXmJUIPH4FYcwyrKicve4x1+7+rzff8sTv/U+v+PAXsuw9tXb9ITnp33zzzXTNNddEj3viEx9Dilcx00HnRYmZQOuTBdXhBE5rXdG624lslnIMHTpECEDsE2dwYZo17a/8ym9eNjM18yqBfBUpC9X6nQ0NjDWpGncKGZKvyjnEkcXi0jJuvvm/6Rvf+MYyG6wtRa2pOztTc+9RpdvjtvnM8jG/UGXHh9XmbXHo0CHcfPPNuPnmm/l1r3td+89uu/XiP7vt1q/5of/8muf93M/9zLV7ds7vKr1vW2PAtSPIuBRhfP7Ow1z0OgRERLjTbuE///iPf+07/u7v+3//939/96FDh750Pvvx8Pt+5//3hg9df/3jrkmS5IABorplkni8P3Rj6gtYlaqqwoGL9l/0kpte8or/8d//P58xho94rw/61ZDXv/71s0mczhtDbRApDbtYaKP8RepJabBNNMiKArfedtvxKs8/f/ljHtP/zAc/2JwEGzRo0AD3K8p76pJjx078Qln53nrqq2wb07tVXPZW8dnDz6qcE1Ud3PWlL33w6kc/+qUA5h9o3PeQrK6tre3Mi/Lv11N3/RnHOIzkXVxeLq674UkfAvB9D8RPdhjlvbLSf1JRR3kP19+2cc7ea1U5UVX97OfvPDw5OfsziCeueLjCGC60xduhQ4c4K6rfGC7umfaVYUyy816r+n48+tl7Uee8OK9+YXll5Znf+JzbAOyrvbbpobhScOjQIX7P+99/feX1lyvnFqSOsXde1YlqFeKd1YkfLY/3PsRW1/Hd1VgctKqOtv+tt/3ZXQC+f3bfvv0XYN3Ta1/72suW1tZ+onT+C15US6/iRdWJhKj3Tb+LjRHdqkVZqarqBz74YXnCE57sAFStzvRnujM7X5ckk9+ENL0ImJ2s54z3Z/3zK1/5ynTPnit3ALjusY9/wk/+47ve9c+qmpXOee+9DEPmvV+PA/djMeCj+3rsWVGKqrpf+v/+j48C+LZLL330rvMdVH086hw5cvS7iqpaElV1quLHIu9lfYdWV2/z8FuuRFXlX977ryd37tzzbTfddJN5oMe3szVa3HDDs6aOnTz5zaXz/1gfU0S13qYatvdwmw9vrgrb9p/++d2+1e6+Je12bzxw4EDanAIboHHhaNDg/u+fMla0HWpMt9JBb+Vssd3zwwO+NQZetHXZgQPX/v6b3vS9O3bsevrtt98ePxgnmbO7h4y/rnTBfpsWW9pybe++se7CoGSOofS9/wgHvM0OJONVUd4kA9LaktcYJvGOZqcmJ3/2ta+9gdm+bH7+okseivhkVcUtt9xCNzz2cU+B+OczUbduL6tTz8NuRKAQ0T0elzyssG8VdU2jJkIKOZYjvfoDWR79gR/+4WvbrdaLCdhJUDAp6Zivs27ypg5jqrOtqwpxZPF/3vYX+KZvfDY+9KEPl1Mzu25XpTfma/kfdTr2vcjzw8DiatDe36/qv7z5zW/Ojx793ClV/fePf+RD//e5z37u//zLt//t2yJjlpVAXkRF1q0pdcyJg4lghvtLvSyGGU7VfOd3fselB6+65uWHD9951fk6ttx8880AqP+Od7z9Pi+yUHnvxoU4NLL027g9pa5El2VFT3zCEyae87znfdNtt91244N1zh9ut9e//n/MTExNPY+Aq3QUPEMjCdRo/dTWnRSE5PAi+pa3vMVng95nHv/YZ3zk7rvvbmK7GzQEukGD+4vi9EuE2C64Y7s0wjNpWwUgMGnlffLkr/qqZ77hjW946R133PHU9773va0HOvYeelueKLcPF9FRIiEpLlwToXM0rMBuTqLbMnFtjMQrNELQwuIr3dVlu5TIrfTq49vRGCbnvT7j6542//0/9MMvO3787kezMQ/ucAHs2bOnfffdd3+1MeZZxpqrAURBWjL2e6GN+t2hLzqNES+zeXI19IoOC2geaJIdEfEPvPa1M7t2734sFE+whjsYCzqisfGcLssiFEWJJI7wJ295K771ZS/TtcFgsTUx9Z7BYPAWUvpT51Y/uLi4uDq2SBfCelKZ+c4kif7qW573nD/6i7/523cb4lNelWSUjbmuxBgelzZPSIwx5JzXi/bumfqeV3331zqXX//EJ37j5HmOUwHFb/3W756879773meMWVxvpdy4V2wxUSZmQhQZ88IXvuDriaKvveX22/FgekI/5jFXTBPoiWR4r24xkRlO3kaOKyIgYtz1xS8Uf/62P/8cc3TX+973V2vYKj2rQYOGQDdocF6OYxiTMZ9RQ3yu5AdjR2cKWkKqnNNvef43P/u//8qv/tg//MM/HPyRH/mR5IGdZLpnrXRuvzzKD/Zvc3Pz3LjLRL3irSXMI/adhyOE4aHyvd6uGXW7uHIiCmEVY9HR9arp/MSPv+ZRV1372Ee1W635W2+99UGr9CmAW2+9dffO3Xteo6RPFy+yPrlU0JjueTQx21Th5aG2e7sJZpAnP6CJXP250Xe/9KVfzcZcH4qQ641jvG47Mx4kNCKklfNIkhjv/Kfb9dWvfrUzNlqGjd9fluWvJpH+VZYtHtt0rNALdMxREcHyj/3Y6v79+z/w4he+4A0f/MhH32ONKbx6BWhs/W5/RayeoJAq8JIXvzi68qprbvjwh//hhu/7vu8z52tp9/GPf+hL//Suf36rF9wzCuccs1scbsvhVbohQWVjIAA/+aufvOuZ3/AN++c+8YnWgxEgRUR4+U/8RAfW7jfME2a4B21zzBuuo8o5ZSL8yVv+9+rCiWN/MbVj18fr9zeNgw0aAt2gwYWCiGw44W9ZQa2JzblEUmvNzA0zGSYCafvHfvTHnvjqV//QT77uda97LBuj9/s30tu+8fFMFU1a50APeljKGSUuqjEx77NiJr9iD341Ed5K4nI2u8RxGCYqK0eXXXJx+7Wv/emX93qD7/j93/99+yBOPNJrr7tuvzXmYGTNVE1Mab0sqWBS6ChK/v7sKEIAjErMDyTO+Zd/+Zejq6686pnw/ilDD+PNrh+8RaiLiCCyBnffcxjf/+rvl/5g0Dc2fbtUxW90kskP9nq9RQQLxAeNaNEtt8jhw4eXfVm+/0d/9DV/efLkwr8QqFCs539vDkjasG8QYK1B5Twuv+wS+8xnPfOZ3vtnLS0tnde+ISJ06NChlTe94fc/sbh4apGBkL646UO4vqIwkh3Vkp3KOdo5N8vf9q0vu2xhYeHGJzzh6ycvpMxouK3/nx95zZOjKHqlIcxtl/a5uWk3shZHjh7D2972f/sA/vmqy776zsa2rkFDoBs0eIBIAsmRoQMSM59GRDcfoIfvOdNl+eGOz2NepERMqqpsee6//T//7Zue/dxveZF4/2g9n2iyc9RBb6xeDv/eQM4umAZ6syD0TAEum06KkQI7AG3jK1y+ga0irbeoQI9bEG5+3RqGCPhF3/It173gxTd97Tve8Y6Lbzp0KL6QBG9oE/apT33qmk6r9VIm7KJN0qbTlwen7XPDZRmvwJ+WRBgmcbbW499vPPe5z+0kUXSFNWYPgWk8SGg8iGTL3yyR/tdDN+OuOz/b605Ov6Msi/+9f/eOd6+uHll6qC7xE5Ew88L73nPHP/3e773h7aq6WFTVqIY7+u1utd/Urw1fevGLX7yvOzF9xW233dY5Hzs5IsIv/uIvyvvff8fiRz7ysY874B45w4Ru8wcbIlIAT/mar77q8suvfOGHP/HuHRe6MZiIdO/e3VeR6I0EdOt9irbqtwjjVTjvwcz4q7/6K3ziYx/pzezaf++//uttWUOgGzQEukEDPGANtG5XQd1MQreqPm++dHimfL760jE553jnjtmJ//Gr//3FV137mJcQ0fwDcMOotcdnlwcMF1VUqfbgpQej4rrtSff0qisTtOWGPs9fgdhqX9nu8ZmuHAxv3juanOjoz//caw8kre4zb//DP5y9kFVoIqJDhw6lB6+88qkMvBLAzo2R8XVIz6bfyXbyp9P3wXV4qSvQ9/NyPxHprl27OjMz8weZebpuGyOtI8VxmiXc+naoI51x+7tux1v/9E8HSXvqU1lVvMmXa++6++67y4f68v4v/MIvMBHd/cv/7y/f8bGPffyjrSReHk5NRNct7WSrY5MqjGF4AI973PX66Ec/ZhrAldddd137/HZVBYDq13/tN97Z7/U/MJTybJZibT25M3Dey5VXHtz77Oc8+6koipkL6RZDROYf//EfD5jIXMZMM+vOnVtfKVQQnCjIGKz2B/TWP71tBURfMiYqL3SAT4MGDYFu8B8SKZHy+slj1AS3uZI2fH7zpVQ/fpnzLNrp4dkkshZ5WUVXX3XlgTe+8Y3PaLcnnvvDP/zDO863e35cAh3sp/U00rblyYVGnVx0oXyg6RyJ5DiRB4gUFA1PhttMDjbfcJb3nstnXLBlP98K9FYyjc371Zk+hw2jrBxueNz1V//Yj//4d5+8++6LLhRRISLceOON8Xd9z/c8mYieyMwp10l5G2U5gCqNtuXmsW+eVJ4lQIah599EOiTdr3jFK/ZPTE28SIGLMSbJ1trHYt1LeVOkc0je0Ne//repyAefjpL4j3y/+iRCmuBDTq5uueUWJQIGg5W7/vhP/uR3q9J9mgjwQjpWbK47Kja7ANUuGZWj6alJesaznnkQwIuWBoPd5zO5UlXcdNNN5Tv/7u3vu+sLX/w3Y4z4sO1Gtilnkq0NZ+QvesmLE8BMP/WpT7XQB7gu6+38yle+snv99Y//bgieF+bpfNr+NjruIXirO6+ImPWf3/1uvPs9//w525n421OrJ5eas16DhkA3aIALE6UCHjlcjSqom0/4m7WsQ620tXadRG9xctmqQk2qFMcRlc7FT33yVz36j/7kT1504sSJy7/3d383Oh81R3fTyXEzkTntfnRNmkBKDIA/+clP0gXrxNyi0XLr5RnOFNRYa7vtpB2NXeansUY63XgLzU7b3HTYDLWxGY/09M8Jn/Vg7VFyDrr0zVW84f50NoJTa+kBoPXDP/gDlz/q2sc8MU3TPQ9UBjTUmL7lLW/hvbv3fgMpnraZPK9PgtY5nOq69eN2eu6zkGB+IFdenv/8F+6Io+hpAHZpuKRB4Hpc21TzvfeIoggf/NBH9J//+d2ebPtOMvE7gezkw1idVBHFoUOHVl//G7/64S/e/aV7RMiJOF0/hqzHbI47nuiwwk5ETIQnPOHxu0Hmq1eX+9Pne3Xi1ltvFQCrf/Hn//doVpSLBLhhLyOdwZ4StSOIquKJT7ih+/RnPuu5d9xxx/VsWC/EceU1r3lN3J3oXK+Qy004FtN21pA8tn86AX73d34XUhX///buOz6O8tob+O88z8yuenfF2MY2xTa9BAIEmxZIKDcFk5CQQkISLoR7X1IuCQlXCAgJ7SYEQjEthNAiOhhITLGxwdjYGAw24Co3Fcvq0mrLPM95/5jZ1UpayZIslyTn+/kswmtZ2jKzc+bMec7ZWJBXNB/t7a2SgRYSQAsxXF04bO+P00yXpdODHaUUnn76aTz11FPQWiORSPTKDGVajJj6wGcmRylOGFv8pXPP+ezs+/78xdk/+tG0efPmDbiUIxKJdCvD2GFJSdAVgQiwxLrHvknDtQizr4xqz9ci4XlOw/b6EZFI0yhrbbZ//CdmZs3M2dbaEmvtaGvtGGvtKGu5lJkLmTmPmXODrwXBfUXBrZCZ84NbobVcbK0daa0dZ62dGNz2sZZL4JfA0+4o4eirlKVrvLrCQGtGtdYw1mLc2NGh8qv/94xIJHKU9hej7tSEtx/+8Ic5RSNGHKIJJ2itJiCYjNfzpCQZRCcft9Y6KDvmfsqHMkXAO//ST58+LV8R9nUdnZWs3KC01nUWyQxtehbcv2/u3Lm2YXvtutzC/Pfbtm/dGJTz78naWLruuussgNY35y/8CMDanp9MRKledslyLKS6jgS713777Zc9dt8JY1u214eHUodMBNw3+96qtWvWvqWU6gjOkrivqyfp6yqstcjLycm/4BtfOxvAoTv72UJEPGnSpMIxY8YcoZUeq5Vy+itVS76/xjPICjlYsnSJXbhgQTvpcFXJ4dPWoXfnUiEgo7yFGKxZQPRFskzK9mxKMZByjMamJlx99f/i0MMO5/2nTEbc88h1nG61if0t8tNEZAEYtoUXXnjBj2q3VdPJJ598V3l5+baKioodDmvoJKIiUhmDs/4un5N/QBy2Ud5wnLSDa++FZD2DxmQ2v3REmXvV1b8aw8YcOXrk2E+Li/M2jhw5Ml7d2JgTa+koa+1o35c9r5QIrv90dasOhdrJclRnaQNmZeM2xMyOJdJKWSYizzIbzZpZWSeesDnWmCJjTQkR5ZFfydtMpDbNeWXup2+++tIW+P1MeHdkDPoq1di4cSMKCgpQWFi4wy4qCEYsG4ucs876wmk/+M/Llt97159eYWaTutw+hIWDV1559RSX6GIiTOneUrf79qSIUlnn6uparFu/DieccHzGDGWGNGt6pp6HulDPH/4BV2tdALATnL2B0xbtMlGqo3J6OzjHcbmltZ3eeGOeB+C1kOO+nvY4eM+WzPt1yHffeeffzz/vvHE5uVmTlSJtmf0TjmSwHNQnq7QBMToYbrL/5Mk4/NBDnOpN60mRghnExYmgPzWqqze999Y7bz9y0LSph2Y5qtBa7rOjTK8OP4Bzysknjz/m2M+OfHfxIsX+BjbkBa0/+8XVU/MLCi4lwn696vH7vDhhQdB45ulnvJamhg/yS0atWvvKK0YOekICaCGGQ+UsAJVsreH+yi766vs8evQY1G+rwze/9S288MLzKCstRcLz4AZDLlINpvsNiNhPKoZDpT+54opZa1evcSsqKu5g5s3UvWC497/v7CQutJQsIc7UAzXjcwCRAjn91B4PPmhM9t1VeoeLyJKPb/SIEXT9NeU5AL6QMHYqW26BHye4AGUrpXKJECYFxRaGGYkgS+gxLPsXa60ClLJk/YFjUBZsg5FpikBwSCFEfrbZVX6kFAfQWFdT+/Gbr770xIwZ31k0f/5DsV0RPPU3HZKCQFRrjX+8OhctzS342U9/ikQiAcdxdnwiZw3l5+Xm/NePL5ty711/Ovizn/3sp0EN76Ccf/756qijzg6PHj/6ABCdpJQaETw+6qv9nud5CIVCuONPdyAS6cRJnzsRnmegdnC9kRQBhtPXIhr455EYZM0wjjji+BGkMVYFG123TiHoPuAllZ5lCyKNrVu34r3lHxilwitclKwEtuwVQzWYGeXl5aaiomJVLBFbnafzbBAcc/Lct4+WkMl2csjNycaEiRODlQ6DD1yNMURETbfe8se1/3HOuS1jRo9KXb3aUU270hqe59F++00MfeMb39jn3cWLJlxzzTVb4e9zQynT4fO++pUS7TiHM3MRrPXD6j6mwQKAZy1CjstVW7bSM888H1fKeVGHsl+HDE4REkALMVym8UCGI2RqZQcA0c4oO2629+47izu/f/EP1N8efyzHcV2y7BcY72hBWGrYBBF5nmezsrL2/+2Nv/vqujVrm4joGWb+tL8gOholAqkdDjDpmQH271N6OAPogfaG7vH4yBijSelJjlaToND38V71dYfK8A2q7+kVnGr/YS3sZADr1mxZuhZANQCzK3ti9/f3+fkFuKbiWlzwjW9i7OhRqTKh/n6edhTFPcNTp009/Lc33nzuL6/8+e1KqU7rd7cYcPuyyspKs7mm5jgX6ksKvC8ANyiloUxXMqy1cF0X6zZU4d577+Wf/+znA0kL9rqaz9YygASRsoM9KWFmnH76zHFhNzSZiJxM2z8ylBZZ6y+4Xb16NZqbmuI5+QXb6+pWdOxNpYbXXHMNV1RURFqamhvLSosT1iKkg3r0jCfiaScK/ksKjNtnHxrq/p088a5as7L+rbcWvjrrvPMKLPMUG3xe7ai+nYhIAXzqKaccPWLE2C/ecccdfyGi+GDa6iWvMhx11Nk5+XlZY8C2WDshjQw9D/uoy6aXX345um71qvW5JSOXNtdWbZTWdQJSAy3E8CgPPm8dp6sPdF91dZkOXEpr43leR1FJ2bo5zz275udX/qIhpLVnjIXlZGl1363LrLWAtX4zXK2Vl0jw6JEj973jT3f814QJk75ERPuWl5f3eRCMq5iiPoLnfmtP/Zhc74p9M7kYLlObtky14FpraEVM/pov62eJrE07sRm2G/lXu5n9OgKynlcKYIrX2T5uOF8LO5hEV/AeFRcXo3rzZnPNtdd6RGQS1nKmYSvdehuDoB3NBEz73vcu+o8TT5x5gLU2PJj1hMysH3nkkbKRZSO/QsTna02h5GLOjK34kOw7TFxx/W+4YXt9PDcvLwrAMga9kJEBxEnFzVCy+gdOO2C84+j9mVmnL4Tsr91kMrj65NPVCWvijURqr62JXb9+fdwY22aNX/fSz/NBz4WGY8eMJgBZnufRTqzda/j9zbc91BGJvKuUgrWWbdrI1p77dXq3ImMs77//lM984Ytn/kd7e3tpcFI3qPe4oqKCbrnlF9OcUOgwpZ0BnQxYtlBE3NoRwYMPPLQNoNfCoaxqCZ6FBNBCDH8EbRnKDqWJATMbsG2KxuJLcwtL/n7nH29b+Nsbb24OuQ4by9YmWyr11yUjLUgKOQ558YRz+GGHlt59z10/yM8v/N6LL74Y6qu9XTweV+krsXbQLqxn3BZkoGdiuLtw9NcHOtPJSRD4KPbbmalkAn+X3Lo6P1AQeJVa45UM5wFWQe3w5KtHzSgSCQ9KO+0PP/SX+jmv/L09y3W9eCLBfQ4hSXZ9sZastTSyrHTi1df8+oq8vLxjggWFNID6UlxyySWlp3/hC99gwnFKKdfargefqWuI51k4jsazL8zhxx99LE5K1xljNwOIYpA7EYEtgLiKazOU+uPSkhGjAL1veqa1z9KC5CLNYHfctGlTB2A/ZVc17a1dGWrrazsZaCBFif7KgNLrYZKlVCNGjFCAzp04cWIYQ/hwC7a5+JIlCzesWbOm1gKeTdYyp2cb+jppJyArHFLfvei7I2Kx2EGTJ08uGMRrTEFLPX3EUYefzsaeTUCorwWJ6U/PGgutFL/8yt/xwQfvbXGycp92ObZxGMewCyEBtBBdq95gh7L4CooMgBZy3Q9jxr6cW1D8xFW/+OULD/3lrxtDjlae5zFSi+Z7juDNPJHOdR2KJxLOmWd8ftJNN99y9rJly7512GGHjcgwFlfFolE3ff9KXW5P3vrKAoMJ7A9KBOZhuCPofgLlfksaOEhBD/cEs95DFrrdn2MtcnZHD+j+HiIpxcoNbY7H4m9VXFPxZkt7xzbXdckGmehMr6PyA0MiIsQ9r+BzJ5540pVXXTXZWksDGU7CzLjiiitL8wsKziDwAcyUqtnIFDwba6EUoam5Bdf/5gbP88xGhlpBhNUAIqQGV4rB/hK/uMrTQyqdycnJLmTY0uQ+0HN/yrz2wA/+IpHOFgDLwm64fm/9YGpsaoqytc0AeemfGX3vX13bdk5OjgrnZJds3NiQP9SoMTgRi774wkvLErH4WyCKp1eU99yX079qgCwzjjziiH1OP+OLF65fv37/gfYrT34WX3HFFTorO3siM0/Uqu/q+p5lRp5n8Pijj0XjnZHN4w84ZE1dXV2HZKCFBNBC7JI2domhbdhae4BtIuL1Xrv7Xn5O6evh3KxHLrnkkrkvvPL3rVmuaxOJRKo3MKfXIfczuU1rjZgx9uIfXTz10h//18Xvv//+CWeeeWYqg6OUYgBOW2trniLSGWt90wYf9G4rpsB+8bQargx08tCdPM71lX3u6ziYHvDbXZAqSp1MkF/6kBZIO2ytO5zt/AZTwsFpX7242VQycsRr7y5e9NSf//yXpQQ0GWMYfV1Z6D5e3nFct+T7F//g6LFjJxw2c+ZM1V8Jj1KKb731rn3G77fvSQo4OKR1PsFmDsyCW8L62b377nsAyxYvaisoLXkXNvG2dpx1fgZ6sCvEiAF4anCBd+rBZWVlZRM4t+fJQs8Txt710AzPS7QDWFmcU9S4t2ago+3RBFtEkovfKG3gE/rpru6fiIe064RGAInCnSnHKi8vp2uuvurt2pravxNUjNO6hfQ3NRNKkfEMFxbkjfjyV750FoCDr7766tBA9i9mxrhx47InTJkylYhHhxzda/BRptfBGAOtNZYuW4bXX3ttbSiU80HzlvqoHOKEBNBC7KoAWik7mMNnV6KH4gA3OaTrgfr22tq1TQcfdNA70UTsoYu+/d3KJcvfbwr7QTSnZ1kH0OKMlH/AyL7pphsnn3nWORe+8sorJ91zzz0uABXUE2Z1tnSUwe8ukbrsyd3qATljMOQfjYe5BjpTRjl4PLaPsc/dDrp9/YwBZJQHuigqOeK366o3Je/i4f3AU0NoN0AAc33ceu8XFhbOv/ba8qc/+mT1Ytd1E5b77gSj0gZcsLVOSXHxhX/60+0/nD9/fl5fpT/JDPWFF553igZ+pkGjgtpV6iug8ayFqzU+XbsOv//DbZ2hrNyNMDwPwJKw69Zav4ad+ptU1/v9YwCw1Dm0YRuOUg6I3EyPu89Fm+Q3siBwDEDdfvuNiOytH0wePGQqPcj4+vrjIVPbtutopZQqBWwBdm5BIwBsenfZux9Z60U8azkoye6W+c30viutYJlx5he+EJp28GHTKyoqDigvL1cDGK5Df7j77pGF+fnfVMDBO8o6c1ovbAbwwgsvcGtL46KC0rK/NzaujcrgFCEBtBC7hlVQQxrjprSOA9iuXTd5EDbLli2LTDvhhA8a6mufueySS56trqurDbkueZ4/UYzSAss+D4Z+FppgDeVmZ+Xffsftnzv0iKPP/dGPfvSZMy+/3A0y0LntnZFxpFVWMmub7D3NyYNpX5lpf3ZMkNWZN1wp3swHuGRw10dAY61N9RSmDBP9OMNzGGyJR+r1ZgZ1LyNhAB1KUccOYvZdJhnLa6UJQFs8hm2f+9zntjXW1//j9jvumBfpjMa4q3tZn6UcQVaZHEcXnfb506ddcMEFh1lr83uWJgXBt77nnntGl5SUHAjCeCK/vrS/4NdaC03E1113A9Vs3bQulJf3LHneuwA2KqVbgqeiktMgB/a+7FxXMWMtJTfz/sqDerba8TuYuBZApz7oIG9v/WByydUAwhQcQ9OndPZTV556bYhtLhwdHoZLS+ZPt91Zt21bw8ekVHtyQuWOSra0UpTwPOy37zj33HPO/g8A56xatUoN4EoPnzJjRqHjOMcrrffJUL7W63dbf0onNm/egoceepgdJ7TBxYhPAOy1768QEkCLf4EtVDEN4RqyZk4AaFZetxoQWjV/fvtnPnPm+0uXLH7iiit+uqCtI1IP8ocQWGYwda8hRI+gmlIPSyPuec6UiRNG3nfv7JOLS8oueGP2/TP2mzp1PIB9op2RSQTkpLesoNS0wcxz3lIBvOUggJ457Bno9EBG9Vgslz5gpduAjmQwnVzNn5ZZMsGfkzeTocNCfze/ZVrXv4P1q0WDXHS941LdcAbOQw8LKeaE0fFiTU1CKVU7+093vTV37muva4Wm4ASFM5Um2OQJk1JkjOHsnKyJ//OLq75SUDBiVI+BKOTXPV/hfv3r3zyNCZ9VSuuuTmjU6yoAMyNhDMKOg+demMNPVv4tnlNUtioW6ZxTVrbfBgDNrut2sLWKlKLB1IUT7dyhIRaNWvaj8H6Ddk5/jQhQBBQWFBIA3Vxbu9cen4qKikKkKJ+DRZI7OjHx9ysEU0o7EEskDEB2Z2v4iQgLFrxe9+ab8192gK3BFY+Mkwl7nQT4PfH1BRd8ff+ikpFHVFZWFgdZaO7r9/3yl78clR0KHa2IJqiuK2z9vr8JY0BEuP/Pf/a2btlUn51bWFtTsywimWchAbQQuw4rP29Lgz+4KAMgqpQyPZOkS5a80nb66Rcu+ttjjzx5w29/t8DRqsUYY5LxjM1UI5wW7ai0sc3RRIKPOeqISXfdddd5sVjkh/XV274E4DMmET9AATk2bbpbzymIGbs3+GE0DWOjd7+0uI+AnXpMgjPBwS75/8kJdam67WSbttSKf4IBpf6cfqMMX7tlxJL3K398DJMCEzFABqA2AOuK80dvGs4hC2oIay/ZWoC9eCgvL4ply6wxhgoLcz/6+c9+cV99fcPmZBuxPsfNwx8PT/6JyPipUw/68i23/O4gZg71qBFWV1999Yjs3OyvKlInEUD+a0OpQJODFoz+lEw/s9fc2obf/vZGLxbtXGOJliQiLR+vWbO4HUDMCTvRtOqBgV+sSE21t0PaFjs6O+OKKNrf4CNO68Jh/bMNIgDjx493AZTUrF4d3ls/mMrKSrOUokIwOwM9KUk+96amJhuNRFpyw1kdw7Q8uPrRhx+b09rWvsn/FZYznQhnuhqQiCfooIMO5G988+ulAA5/8cUX8/t5Dnz2f3z1aOU4XwGQN5CTVcMMR2ve1tiEZ55+NgKiZUZjqxzahATQQuzqGujBRpPJxW42WaPYq4MHA+C5c//aecghh7x242+ue/iRRx9/I+y6rdYPFLlnNravHUcRwXUcinme+tr555Vdd/1vZ7Y1b/8OEZ0fjcamAshha0HMhB20ses2xaB7YniXDlAhZJ7Ax5waD8zWzyUyWzABVhFZAiwH/aFV0COaAWYD9oxlzzOIJzzEYglEY3FEY3F0xuLoiMbQGY0hEnzt7IyhIxJFZ2cU7R0RdEQiqq0z2kKEdwC8/7WvnV2/x6eU+S+SlxsfGU9mVJubm1vWrPno0zvvurve84xnjO0WKBlm/2QjuVg0GOesFZF2naKzzz3rS4cceeSxQeZaKaX44YcfHpWdm3s6AZO0ggNYSm6QmcptEsbCCRYOLl70ViKvqOyv0WjbEwCSkxvjrnJjO1EuT4PsgZLahOtqajoAblXBJMNMJRyU1vLPrzHx75869cA8ANM6a5pKhmvx6HAbNXZMmIgKg5aTg+o0s317owFMTXFxWdPOdrVhZlJKJV566dlt73/w4TYmRI3hjFeUevXR97cnCrkunXPuuQeHw9nfXr26anSm1zzZK/rgQ6ZOscYcrzTl9PfeJLdZzzNwlMJLL72ElR+taMopKHkmEu34UGqfBWQSoRC7NsYzGNQawlSAYf0YN8Rs+zpJtB999FHT6NF5b11+6WVq+tSpOPyIw05ga0cGgSP6G0mLrsJSuErBGKOvuuoXpWvXrs576M8PRrXjMIAsay1IKb9cwtruEUqGn8fgXRgv2F6X5nseWJOB8+bNm3HllVfC8wyR0h4RRdhfTBdioqxUz1lr/ZWbfpI0qpVuUwotmlSr1rqdSEVAFNcOxaCcuNY6phUSBGVIKctsGAaWlF8lQoAJZ2U1Llqy6FMAH1ZUVHi79ARiAAFMMN/Dmzw5nNiypavbypQpU7bdesvNj5577tmhIw4/7HMJz7ByNKmgACW5eCr4gz9+GwTP87JGjRp1ym+uvW47ETXMmnXpJmZ2zjzrrM+EQqHzYO245ILV9Nr59Dph43kIuw6vrdpIv//DHxrJCc0zhDfQ2bklLTZNZGeHYjyIPYiHqd/Jpq3VDZ5nasPh0KgdNBVO/brkpaKxY8cW5+QWntjY2vgWgPV74wfT5P0nO5ZttlZa2/Tpohlat/Xc12prawyAusO/eHLTltlrhquLTeShBx947Zhjjhrnav25tAtu/ScClIJnDB9/7LEjTj3t84e/NOe5PK0VjEmbmOl/NtCN992XF3JCo7SmYoJKDW7pcx9ihtYaHZ1RPPbo47Ce15ydnb0i0rK9rmfOQAgJoIUYZhpD6wIAv4VcjrXG6S97U1fXUc/c/up3LvqOM+eFOeF9xo452fO8sOM4qr9R4d2yaH4ADWs8/sMffh9a/M5id1tdLaUt8IIJvqbXQu8gF83DP4mwK57ro8NI6rm2tbXhqaee5kQiXgegCsCWIMbJgX/5NhQMyeDg/hiANgCNAOoA1Af/3wogknbrDL43Hvy7VEVC8DUe3BK7etsaaB/oIPtm3nzzTa+rVJ2xZs2adiL62y23/t/EP91x+zG5hQVh+A2boZJLxtKCjGQm0FHKtdbud+YZnz/tvPPO76ysvPODF198ObusuPhUz/NOdBwnr+fId5VMw7Of2zNsoQH85jc3mOrNVWvySkY/0h5vX9cj9LWhUCgxlC2J/JaGg+7CkQzUPvrog5qOSOdGx3EO1lolF4Vm6q2WVoOviJmx777jCo48+ujDF85/rTQoj9nrgq2iggLXM8ZxHDftrLfrYWaaRqiU3/miqqrKAmh++f77I8HFLN65+JkxY8aMxAMP3PePn1955cQDpkw5zhij/D7k3Uesw2/HElwZ8QPoRCKBgvw8+vrXZ+W8NOe5rF6xNjPGjTsu/I2zzjpaO5jsN3Txe6ZQ3y2gwZbhaoUFixfTG6+91hDOzvu4oam1IbmuWo5uQgJoIXYhM7TOCWB/285jts6ODj7M3E5EL1/x05+W3nPXnWOLi0sONNZmqUFcX9VaI5FIUFFhIe67/17U1tbA+t1AUkE2p9U/W+bUIj506znMySEWGP71mGrAl5q11igsKjYdHdHXc/PzHs0rKfgoi3PizJZMyFNsw8QcISAbRFEmpVg7jnUTIRMPZ5lwtjHZeXkmu7PThkIhLioqsjk5ORyZONEWjx3LADDmgAMYmAfMA6ZPn84AMGvWLAbAyasAw5+DH2olkbUZAnDLzBEi2nTyKSevu/ii706OGZvl+r1xkxNEeiwkC3p/WwvHcab/4hf/M27kyBHNp5xycghAkVIqOz14Tp6EEZF/AsaMWMJDVijEr8x91T7y8F/qQrn57xnEF6O9Pb1vcrD40DWDic9Si2RJMTD4IUbJxzz3lde3tLa1rs/PzzO6j+/pmZ1VipBIJLi0pFifcvLMgoXzX8sxxtBwD+/ZyZMu+t73vpentC5Sfn9CAMofod7VEDpTVxI4joNNW7biww8/tACiw7l9z5s3zxBR7YtzXtjwX5f9uE5rNZaI3L4mI6afkWh/MSHOPPML7mFHHjPyg/fezWHmzmAbJCLi55+/M6+kuPgCZswEMfQAFpkGz4/vuXs2JeKdK3ILyp6NtSaa5KgmJIAWYjewgyzhSB3o/LHHrrWsB3BQtEqptqcrn5hzwP4HuOX/++ufKqXGQSlopaivS+DpgQD7i2WQ8Dwcd/xnSYEQ9xLQQSCo0g5amdq9pc383itSbcwWnme8Ti/2YVZcLaz6eGsL/lWK6geZ/qIdfHc4HH79lltuLTr1lFOvnDhh3+yEMdYJ0n8ZS3+S7b2szTryyCOzDjnkkBGu66r0wTo9M9Cprh5B95SWtnb69a+vpkQs+nJhycj7Wmo2ZawVD6Zq8GA7HrI1wa9TPMTSmNqm5qZN++4z1vQM4voa8pEeUM6YeVKosLDksHB+/vszZsxYO3/+fIs9HzyDmZ3//M/LD1VaT9NB5xRFNlmzkznJnlyIqjVWrlqFDz9cmcjKyjfRaNtwPjYmIn7g3nvfPu/LX71n4sTxlwIYF2wClKkcTQUPWZF/Qj+irCTvBxd//0s/vvTdJgDz03/+AQccoR1K7KdJjSSlLILn3tfJjTEGjlZ4b/n7/Oqrr7LWoXVGm7eBlg6pfxaQRYRC7JZ4Z2gHFL97gPa76A5ospdSSm363Q3XvXDf/X9+NuQ6W0gRWbbcVw/engsN2e+vCuMZxBMJKFLdx4IHNdOUYcfjbuEaq91xibP/Gm9iIhiX1Pbm5uaW9LkgQ7z9S26GRIREIrHh01UfvfDA/Q++ZIFaIlLs692Ro0egaIxhx3HIGMOZ+jT3DDg9z0PIdXHf/Q90LFvyzryc4tFPt9Rseg99lLyw1kM6I1Pa4Z1cvNm0fPnybZ4/rhEDbfXmOC7FPIMTTjhBf27mzJPj7e0nBQND9vRiwmSbQT3loCnHKeAof3dXgFKpLjXp7QbTu80EazNo1apVUS/RWVdUVBQf/hItSx9//PHa9z5a8VI87tUmO8NkqsPuOvn3s+rWX3mY87mTTjxt/H6TDw5a4RER4eyzz85RKjFJa12kVdcoov7ez2Rd+KOPPeE1Nmz7KLeg8L1oU1P17ijNEkICaCF25mDiX2IksEsDP/5YmjVr1tbLL/vRH557bs4bIGr3rLUDW2jG6UMKoPy6TyilutqQ9bPTUaq41pL1Fz6q3ZVVyxTY+UfWbtlH3snbXmOwUZhh218sydZaOuqoo7Zcf135be8ue+91pVS7YbbdnniPIDq5XWjtj0J2HIeSQVpfwYlnDMKuy6tWr8b/3fp/tToU+uPY/ccv7K+O1tmJKxD+mtzBZ6CDgNdbsGBBS2c0FrGmd4u/PqdfBgMow452Lv7BxUc7TviEb3zjG0V7+liVfJz/7/+VZ2Vn5RwOxtQgQkZ6n+7UhE/qaodpGSDlcEc0irlz524HsNzzTOsuysTyLTfc0NzY1PQxA9v7nfyZ3hNea4ob4xxwwIGjL//xj8cEax0UEfE119ww3nX1mSCMSKtk6Tv7bC1CjsNr1m/AU0891UHafcFAvSlZZyEBtBC7eQMdStopqOE0SBvVPZCDz5NPPhmfMWNGzTe/+c2/LF6y5BnHcaxnrT9mOMNwgp4BT3JAiSaVseZ4QA/GsgZI7Y6AoN9L+QwyFv+2lzVo4OPJeenSpZ0A1vzm+hseauvoeBYgDz16ZvcVzKRvJ5RhWArSWuMZa3Hj725KVG/ZWF8ydmzV2iVLWvt7StbGd+ZqxlADaAaA5198sfXjTz5Zp7VuT7ZB61nGkSkIc7RGzDN05udP11//5oXTampqzj344GNH7MkstFKKL7/88nB+vh6nFEa4WrmOUt0fTBA8p6aaAjCWYa2FUsCatWuxZPHSKkDPSSSc+l1wMsxEhEWLFtW/8+7ie0mphUGfcR5IO0sCEHYdNWPmzOk5OTmfmz59ejYz46CDJk1h2HO0UiN7DP/JOCEzmfh+/oUXvKr1a+rzioqXdDTVrZWjmZAAWojdhyzUkNIWNtnJIuQOOrCcOXNmvKOj5d1vfetbcz5dvWaJq3UHW0uZJnz1Gg7S/QjTaxgLDexAOMwZaBp0YBkcGP12Ev/uGyENLHhh5o4Xn33qnbmvzH0ZpD40xnSooOvBUFONqdpnaxF2HH5t3nx6/LFHV4Zy8/8Wqa+v3dG/N/4PoAEvoEy1xFA7dVVDKYXGurq6N99c8A8D1AAEa+2ARokH30OOo/HrX181acJ++5+7evXyUqUU74kAOjklsuLGG0flF+acp5SanL5pUNq0Ups2dTDZfSXhGWiAH330CTQ1bGsYO3biBy0tm1p3YS1w55fPOWdpZ0fnRv9R2MwDfnq8F67W5BnD06dNPeLU0884f9WqVcffOXv2Kbm5uadqRVMAZGf6991+jr8YlJvb2vHoI49tJaIXwuR+jK7e5EJIAC3E7ohd1I7XcGXsspBM6tEQOlpUVFSwUqpt3erVSy763kWV2xuaqrRSnud53UodMk1X612SwYMMdcmfZD2sgQIP6HXrVWtBxENcw7n3blBDeGEH+h6S33O3tfzqinc3bNjwvNa6xtqgir7H0JrB/Gz/ZAboiEa5ouJaG492LhszYd/HOjo6tu/oDfYSCd3rPe6jpr9bBM07G3MyMG5c3V8f/evcbfUNW5UipNeF97V1JtcHOFoh7nl84JRJJXfdfdcxnsefGTVqVBkR2T2xeLCmpiY3x3WPZuavwdqJqRPMDJduOBgKQwA8a+E4Gltr6vDC8897IDRNnz6pMWgwRLviypJSisvLy2Nr1q3ZzoRGY/xmRhlf+25XBBjEjJys8PivfOXLZ4RCWV///Kmn/AjA6czIyvSZ1/PPcc9AK8UvPP8iPvzgg/U6K/9v2127VRYOCgmghdjtGWg7qEZa1P0yIuIY0lodttZSefkbmxe/9dacn/785293dEZrichaf7FXr5rhnv/P6Svw2T8w0cBWKiVDfrULFhllXkCYvsAtfREh4GkF+69WHT/gxnWD6xcNkL/dfPzx+xsee+Kxylg8sZLBEVaKbT/DLHYURMc9D46j8fBfHzFvL3izLqugZPPGVfGmgXR5VMyKk8M8g5Hs/dWvdi0iVDtVu87MxJs3Rz9avnzjwgUL6gF4fb3GnOHqhwYQcl2KegZf+PypJXfNvve/a2pqzj3ppJMc5t2zyDYIkNU999zjFJWVnegqdZ4mGq2Vcrot+EyvJVYqta9bANYauFrhueeft5+sXLE5p7i0au7cubt8n6qoqODHH33ik45I57sgFU8v8eiz/tw/ASQA+MwxR4/81a9++eXJkyafaYyZorXW/Z94+Vf9lH/ig0cefTSWiHfWHHzgoRtQU9MJ6fssJIAWYjcnDK1VQ/ns5aALh8vuULdxrqg42bv88ss3/+XB+x+47bY/zvWM7UwYay1z6lJtei1r8s/JBWLJeujBZD3TDlI03OvmgkvgAy3wsJa5HZbi/6IfebSjbPxgM9Bp24JX8atfbVr09jtPKKUXgVlx2pTM3lP/qM9I1bMWrqt5c3U1br7pRo8UPZKVlf0MsDYxgHMASiRsKtgkteN6nOQjYb9mmXa2bhhAx42/+93imtq6D/3RG10nmNzH65scWU7w66HjxoZ++P3vHPTgQw9/8+133rmQiLLStuVhvlrjKy8vV0TEDz74YOjb3/72KY5SFwCYoZTK7bn9JPdz9Hg/yW9tyfWNTZg9+15LpF/TOjQ37WRil2RkrbVgZtx44w3v1tTWzLVsY+n3U4be5Mn3QGsNZsbUgw5yr7766iIABVrrcM+Fg9R7GlNqbPeCt97mhW++udwJ5y3cvr2qXTLPQgJoIfbA9kkYWhVusDzeBXinDq633357TGv1zq9+eeWTjz3xt9fDITeSMBYMsO2jtV3vJ0E7LqRN/qyug9QezdgQYMBotUQx2QyHNBkufurJJ73a3Nr+DjO12yD9zz2CdAu/5Rd3mzTYFV0Za6Gg6K677o6sX7Pmo8IRY15s3rZ1xWCCEhpSpGkBQFnrqZ15HWbNmuUte3fxvMonn1qilGLPml4PXFHvKi1KtX0EtCKVMCb83W9feOycF+dcPGn/A8+31k6dMWNWXhBI8y7I4NrFixeXXnjhd091QlnfVMCpSqmxfTU2oR693AlAwhg4StHTTz1jP3hvaUd2QfGStvrqpUOYDzXUk+ZN895Y8KGxpt2zBghO7DN9VvX8/+CW8bXNlMFm+IG5sYynn3qaO9pblpaMKFq4ZcsWT8o3hATQQuyhklUaynI5vwlzKLjcu1N+/eur1YwZM16/+KLv3zF/4dufhh0dNcYwkhk1a2GC7M5QspbpK9UUKSi1+ycXq2D0bldPa7YM2wmYxL/jh+LOTombN2+eAdDwzNPPfGKM9ykxYsmfa3qU0qTXkXrMSF7hSBh/4eAHK1fhvvvu2+yEsp5kTmwaYBxMANh1XYugKEj10Uou03mc8tPlbnAlZ8imTZvmHXXUUR/+/tZbl7//4YeNIe0YE5SSqOQv7PE4ko+N0nqna6XIGJN9+mmnHvPi88/feOG3LvrR/PmVR1prR40Zc1TOG2+84QQlF7QTQ1IIgLr8ttvCjcyFhxx+1KlM9icK9iyl1Jgd7ZSpdQ8AEp4HrTRq6rfj97fdFiHtfgJFm+GPqd/lO3eyd/Zdd9/RtLW6Zh2UbkfQJrGvDkJ9lLDQjvrHJ8d2a6WwrqqKKyufiisntKasoODT3XSyIIQE0EIgY90uD77lBLMGKMy840mEA6knfPPNN6NZWc4HP/zhxX9cs77qg5DWyvM8Tg5QUBkGYGAIi9SIBrlqcofcgccUlFaWohRcJ+SEQiHt14OXU9CNgJhZ7eSNhnrbmcz89OnTifoJCLv18k7Lig5lEklQb2p/8t8/Xby5amMlkWpNmwzYz/sf9AwPAh1jwddeez3X19ZsLB21z5yWurqtg+utTSZTA46+FsCmynr9TjAhYzy9s/vO8uXLE1VV61dce03FnEg83qSUgoE/BBsZrs707GaTCqK1Vp4xoakHHTDivvvu+cozz71w0ymnfv6PNTXLvnjyySeXEhErpZJj4Km8vFyVl5f3t72pZD11UNrAl19+m3vlBRdMy/a8q12HrtJaHclKFQHQmba99FZu6VMuPWvgaGXLyyvw6coVW/OLy/4YSXQu213Z2IqKCiYivL906foFb86/E8CqYLQkD/SzaSCDb5LnQMb401Yf/esj8frarVuyc3LrVq1aFZfMs5AAWog9g5VSQ+oDQYYVgBCGIQOdjHt+9rOfNa7++ONXL7v00udq6rd/SMqBZQsGDSpg7jejM8SAbbj6dCQDKs8Yp6m5obizvSWXiLiiosImxwUTkd3JW3IhpkNEoeArpf389Bul/93OHJCbmppUeks37mOctGUetslwra31Vdf/7qZFkUhka9yYRLI9jLUWyJABTHv9EXY0Xnz5Jbzw7DPv5eYXvaS8yAb4GcwBb2yumzmA3vEkOasAZJmQ5+zspmWtxbRpx3363NNPvXDjjTdXE5H1EoluCwjtAGvOHa2R8AxCIXffL5179rGVlX8757kXX/reT372P1dMPfjQS6y1p1lrxyS32R7bbc+bJSI7bty4rMrK5w5taGj+2s23XvaTsuLiSx2lZjlKHQagiABl+69576pjZ0bCeMgOhfHk08+q+2bfXZddULwwYaML0N5evxtLs5IvYuMdt922sLmpZZOxltn6W/dAFpIO6MSfCMZaOFrztu0NeLLy6VaAX9VueJ0cvsS/OkdeArEXswxleQjHHBssInTg0DBmdbzyN96orzj55Od/9pOfZt09+56ScMgdpRQ7/rGEhrdj80wAFTv7ExMghAdWKxMsMDIMjB4zxrnzzj+VhELhg6dPPeTw7GzdaoxrXddxAA4ZY3QysvW8BGntWNdNRj7p89PjqT+HQkAk4ql4POZ2dLSHE4lEOBihbkMhFXec7IQKkQEAY61KROKOtVbF4wnOycmJtsU7mi+56KLGTZs2tQ7m0nBywVl1dXXQYhuwsFCsQNR9jDmnTZPrSsrSkGrSkwsK//LA7M1f/OKZi7721S+XedaOT9bEU9rI41QLNPYHbxARtjc3o7y83CbisddLx45+tqaqKjHYDKa1qs8xir3Ht3eLehWALGscJ70kZKib9aqPFzfus8+Ud68tL397/ykHFF94wax9IrE4wuEQcY8+2f3tR8wMRyuy1rK1zIXFheFzz/rCGaeddtoZ3/nudxqq1m9YWL21ek71tpoVdduao9trahMN7Q1eZ2enyc3Pt8VZWRg//gB97LGfcWbMOM7JLigIudCjtRuaQWzPIPB0pZTj+Cc6lplVatvI0NsdQblNcoGo53kIuy5Wr1lvf3LFT6JE+i2j3Ofjjdta90T/aqUUL1u2rPX95ctXzpg58whrvYnJnvQKgy2Q61720dWj3MBxFZ5+6hmsWrWiPj+/7OXWhvhqqX0WEkALsQcD6KGmY1OZPAxvCW/FySeb8vLyNRUVFS9PmDhx5HXXVZzDxowNDkQ0PEH0cC4idAf8EiqloIJoq6ykGD/6wcVZAL5ujD2SGRsYYCYeqUFjmTmXg8va1NW7IdV7m1MXs1P3gZO9FSi5PkwR6eS1/GTlgk2VEvjFDgqWDWtHR6uqNr2flZU/B8ArRNQykClrmQZb+o/Mb+7CPceYJ1sU9h7DTUPNAo4aNWrbr6785aMnnnj8xLGjRo33rGXtF7pDpU2vS5YCReMx5Iaz8L8332I+WLa0PbdoxMbaqqotQwlGlLJ2oDNUeowg9GugrdUYjmwoM7IPmVLvbtt45+U/vswpG1l2wZmnnhxuj8d1TihEGGTWXytFWoEsA3FrEAq7fOj0acWHTp92irU4OtIZiSSM1+l5XpOxttEablUKUe04pB0nL8sNlypHlcEi11Eqi8F5RE4+EVytus5lqY+gsfvpVfBZ4xlordDS0srf//73Ozdv2rAyr3jky+1N294A0LEHAspk3+34zb+/9fHPHn9cnuM4lxOR5q5qk53OQjuOg+aWVjzy6ONRtnZrXl7u2ra2jW07edIlhATQQuzkZUj2j/9qwNmz4ABr/XZRNNwf4FxRURE//vjjV/72+msfP+jA/fO/feGFpxpjRvu1l5mTOn093oyXq5MJr3nD8XAT6J4RHvAiOvKs1QSMI9IlWuOgoPQhVwH5QU0ohr+QrHfFjQ5+FYFHK0dlAdh8yCGHfLBixYqOwfya1taC7mcmwXvS7T0I3kBKeyRB9KmsP41y0AFGbW1thIhWzZ5977pfXHllm9IqWwFOKmhM2zY84yE3nMXLV3xI986+t1WHsl8i8AoMcfCGUsomoyg/s907695zYEuqc8wwl/itfeWV+KxZsz6trKx89OKLvocnKh+fdcKxxxZ2xmIcDocp/XXgtPemr24RyTY9rt96jYxlRykqVIoK83JzgoW9thNEnQo6amE96++eIQA5AHK0o7RKj2xT/6HU62CYM3YKSTvb8F9bANZY/OiSS2MLF8xbl1c88sH2ztZ/AGjbgy1hwMyGiNZs3rx17eRJEz1mDlGqUdHAf07vEwhOlm9g0Tvv0FsL3/zQCee8UNPRtA3DFKALAamBFgLDNop6QNPbQAzYOHbN5DJatGhR23HHHbfkB9//fuUbb8xfqLVuSSQStutqfO+R35naP2XKajEPX8zvdZUgDLr8wNEaWmsohRwA+wDYRwFFweeGHYYbw1q2/tSbPr/P+CtJres4I8A4FlDHb6xtHjWoOeUAFRS0UjBhOfOKsPTe3t2G2/ifldfMvEYPscady2eUt//2ht+88/aiRUscrW3CeH63jbSyDWstjPVLAm6//Q5u2r6tNq+w5Ln25tiqoWYvrdXco+V0r+2rW0cO6raYcNhPPisrKxNnXn7521s3V/3lW9+48B9Lli2ryQ6HORqLI1OpFvUzgKbb9EIiaK3SW69ZAtjRTpYmVULEYzXReFepfRXRKEWUT4Bi/wKINRbB2YMf9zEz2HYtv+C0KY49W7klJ5QSwD+85NL4E48/8kleUdmT7dG25xGNbtoLjrNMROYfL79SYzxvrTUmqgbwuu6oXj7twox98MGHLNvEh0X5Ra+gtbVdyjeEBNBC7Pntk3a48K57S67k/xgAcSIyu+rS6BlnnBEbH4+/8p3vfffJ9z9Y8b7ruh3GmAwTsWko46LV4sandz7L65FipBZS0kAPmmnfRxn+XXoHg9TX9Fv6ff38PUEpUn45g+rrRhRsB4pAxLkgdYxJJMYO9qVob88j9NOFI1Ub2jNI8tvO6b/H/u4ONat2zbxrbCIafeWmG296orZu2zZXOwmllE12jdBKgZTibNflJUvfM0888bftoZz8jzqjsfeBtsbhyOYppfrc5lL/z93aceyKAIhfuf32+LQZM5ZvWL/2xi9/6cuv/uO11xtywqF43EuwZw0y1dsO5MQybQBREFMTMTOl//vkyawK6q0UQMSsdNBt3u+qx8nJQ6kade7jlN7zPLiug0gkwt/+zkXxhx64b2NOSdmz7Tb+J3R21gXfukeneSZPQv74x9+vraraNMd1nIbkid0QM9qphbBaET78aJV97bXXtykVWjNhwuiqYOGDEBJAC7FHB6lQ71IBytD2qmemyrLZ5RmQiooKu16p2Oaqqtcuu/TH926trt2itTaeZzIG+H1lmtP/zk/G+knSDcuWhXa2jjBmos5Q2+v1FbRwP90j0v+ur+c90Mxij34CRKRgGCGQGqWMlzvY1yKe157ena7XVLX0dmTp9wczUNyams7wTvQZZmZu/sfLcxb89dHHZm/ZUr1h9Zq1av2GKlpXVYU169djzdp1tHb9Bqoov6Yj0tb8Um5e/u/jbdsH2bauO2NMVzWKtUgudu0ZlCanZyYXw7FfkaCDOvNhD6JXzZ/fcejpp39SvWXznV/9ylcfeuChh2uzXNcjpRBLJDgYK93rak2mQC7TdsbB4j6kTwtVqiu1TtStVWG3NpLJ1nrMoKBPdfKKBQclHZ61iMfjcF2XN2zYyF/+8lfNY48+vD2vsPT+SEfiIbS2Jket817SzQjr1q3bsOz99+ZGPdPcV4Z4R01D019jYy0TESorKzsbt9e+WFhaunDZsmX/dn3jBaQGWoi9cfu0lp2++q9mCqSTB3xrmQBoJHZtHV7QRWL7228veOOqX/7ygHvunf31rJB7gLWGiRRlKtFIr+3kXnW4DMsWAIUatjTmAYgMcRgBA6B4PD7ooI/7mLCYKZjpb3jMQPvI9heY90z7BSUYjjf49oSUG4u5zKSTkQITd29+3MdzY8sAkBOL1RXCXwxmhngZHRMmTKj6xU/+56n7Zs+OW2OPsZZHszEFxhpLpFpIUfWmqo0bw7mFrzZtq35nZwOwBMd1MoC2Qc1wpveKe7RQtP6/yWVr3F0V1K2YOzdSXl6+9Dc33WS+/91vmzWfrj71f678+YHFhQX5sUScHaVJa53qfjGQbS71XIIAOL0QN3lyRD0C577Kq9L3zfQ2jwnPg9IOQqEQXvn7XLrsssvM+nVr1uUXlj7d1hl/BvG2qr2t/tcYQ0QUufaGG6pmzjyladSoEUzWQqddlbA9omrqY2IqkV/zHXJdbK2uwVNPPROHUgtKC/dd0VRfo/Z0xl0ICaDFv7VVFasIgENsHfRRG9nrQJcWDFljFIAQO6x2/awXS+Xl5dsrKir+st/kSRN+ddUv9yVQWOvUgIY+M9AZgsXkHdmdsaYSAI07Mc0r5HmcpQaZdt5Rdjj97/ur397RQs+BBs/BfaygyCGyYI6QUoPNdKmoUiGrggBaBcsSe5RvZNzG/K9FkQRGAFNqgbVD3lg2btwYBbB67Ser7gXwBoBpgBoDKA+wWwC7sqSkpKqxsbF9ODbOeCTuEpIVCarv9zK1+jUVbjoAFVvjZe3CfYcrKirMtGnTPti+vb3hd7+9vvGthW998frfXHfwSZ87oQCAE00kyHEc6AzbXK8/p7Vi7Bb8kt8XRhH1Wo7c84pJXye81loYY6C0RlYohIamZtx88632tt//vj0ai23OKyp7qa15++0AatPWCOw1ks9r9YoVsYULFqw677yvTGbG6D5XbjMny1x6tRhM1uwrpVBZ+SSvWvlBe2HpqE1r1y5plavaAlLCIcSeVRmc4BlmN/0icnqmyPYYesFpbVqt9ftAA4ndkQniioqK+KxZs6oryv934b33PrDMcXQ8qIcOyjL6CZzTL0enSjgpl2JUBozYmQxgKBHvzEmrgR70YsX+OiCkFltlGAvd7X0awJjzgQx28L9HJQCuV8qJDDaG0DEKMdixPTJuSJv8l2mstf+4qJjBY4A2Z5CLFzPxysvLm4877rgPx40b9/zIkRMeGDVq/EOFE/Z9ecKMGauD4NnuZPaZAagEJ9zuHfm4q991etAY1H6r5LdadgBVqK3J2tX7zqpVq+LbtoW2Tpo07fEFC9649/TTP//qf/+/nzZ8umadl+W6log4nvA4fQR6z8sSnDYSPH3/ShY2c4YDXjJTnRrkktoGu6YKGmuR8Dw/4xoKcTTh8aNPVNrTTj/D3vjb69s8S0tyCor+0N7ccRuAevSeC7O3abnrjjsf6+zoXEQ9Jil2607TK6AObsnXVyk0tbTSffc/0EHKrYqD2uWoJSAZaCH2Gv5nNvnLuqhHRqQr45w8eFJXIoqUBRAjb/cdzKZNmxYrLBz16hX/779L9xm3zwH/cc5ZZfF4HFprECkC99GROe1yc1cQpxxrTdhvJjDkQRaamZzk8JCM2cf0nGPa//cVzPasG04G0V339/fv/d8w4Kw0OBUcdf18FQWbDUy2edAfdo5H6XWvqsfl6t413f57orRigHKt4ULAqOGqnwfQGdy6opuNG4dzk9TBIJC49WuN0pqKdJ1EqOTrmxaDIq0J4u6xNrZ+PTaP23//eQ219W1/vO3/6p9//sUTL/zWhVO+/d1v5+2/3wT/8VgLTiRYKQXHccDM3Z4Pd61yTWvmnLl9JFPvliPJVn6e8fxaIddhR2t0RDrxzLPP01133415r7/RBqjlOQVlr3kJ74NIS8d7QOfWvf6zlBnM5Z1EFctXffzxus8cfWTCGONorSlZ+kbg1ElE+jUZorSFk8bAdV373HPPq48/XrVRZ+c+0xmJ10jnDSEBtBB7gfLyaVxRgbhWKmKNl0iwAlnb1WYLBKbkxzwHAw/8zDOzhvES7QA2a+127K7HXFFRwURU5TjOP/7zkv88eL/9Xj750IOnj43HE9RVR5kWrnIqdvZXtGuNRDwedH2wMa2pDWgwO3FgstaysdbCElLttkDJyWnUNU56IAlV7lkzzKl/mZrS1msGDGf+6dR7eEzQQKzX62QtwyVFndEoLNsWgD/OKcxuaG8c1OvCzFmeZbbGWrAxSJZwMPlt7WzQGjd5ImGMheMAXsL4HQHJxv3OZ9h1PRqHNwBhG+eIBVfD8hhmzks126C0wJEBIn8kvWFLLjSsNXHA1intdOzO/X7LmjXVxcXF7fljJ9dXbdi07fpr//fYh//68PivXfD1sq9++Uv506ZNy8rLznKSVw2sscF7RkEmPe0MIENLwuSJmU1tz5za//x9lJDlOtDKPzRu3LSZ3nhjHu6+Z7ZdunRps0lEN2QXln1CoLmRlsjLQEd9cB7yTzE0ROvrLICWl16c896hB09f7LjOkdbaXGZ/alXXQBsCwXbbRvyFA34pUGc0pv784J+N9eJrikeOfaWhumqbBNBCAmgh9h4doXB4u6OdOkchC1qFe3xAc/rN+E0GLBHihQVF6wEszs8vbmxqqtudWR760peuWllZWfHb7170fXr00b+eetD+U/I8Y0Ouv2KH+isBKCgotK7rGoDr8rLytrZh284kAaMlJaVtIdeJA+BQKMT9BGq8g8BuIMHfQALBXo8hmBCSqtRJa7tCFoDSYAJsOBzuCIVDawF8MuPoo5sqN2wY1MnEqFEFkbDrRhRg4GdjVT/bE+CXS3NOTk4coGqF0BbA9YY5UNiVAYdXWlpQZz27mBxdBujJjtPVGtKmX6EPeh4r/8oNF5WU1AC8Iltn1Ud2X2DEANDU1NSGpqb3i8dM2mptbMHGqk0H3/Sb6464/Q+3HXDWF784ZsbMGQUnHn981v4H7K+zsrK19gdokgHIGCZif+BNUDlFKnURKgioVVfGWfuDZRhd9eFcXVOHt99+mxcsWGBeevllb+3qTxKA0xbOyX0vq7D48Y62yGLEWmrht2vjf6bAMThRICL6xwUXXsCTJkz8hQeepLTjkoKjgOT1KjZd51rBfQrGAlqB/zHnlfhbb71VHc4u/LAh2loD/2KFTB4UEkALsadVVFQwgMhNt/zfp53t7a95idhpzJhgjAlau7EHogiY26BUmwJ1sOUIE7Vm5+Rs3lZXuwzAW5tCXuNuPsBxZWVFfNasWWsrKytvvfii773x2ROPP7qxofEYWB7L4BwGuQA5YNbWWu1nvhjMBGaO1G6rXw4Vegfo3O7PQhmy+C233ri9sz1ax2zHguBaYwAiGGspmX0jkAFzHKQMMyvLrJnZCY6byVx12iVuCx1EvBxMbmPbtZAzKH8gf/IdpS6LM7MHy56/AJA9EBLKr2lOMMgjIstgIgsNgqOUJiaySqmY46hGrfSK+vrG1wFUVVZWJgbZVcRWVVV1/PcVV2z0Yt5mIto3mDnuB1vGeETUDqI2RYhaa1U87ikn5HZUV9dshHIWmFhiPVD9T9GmK9njd86cOdWLFi19prW9tTmRSBwbj8X3Y7Z5/t9zFKCIUqrTgj1rDcMi4YSytjU0bX8fCC1uaFCNeyLOA9DZVLO+GiUlzcWFpeucbHdhY9320icrHy99svLxsn3GjR974EEH7jt16tRxRxxxxOgp++9fUjqiLK8gLz+rIC/XycnNg+uoPs/wjLXo6Iigra0NTc3NVLVxI5YueRfvLllKa9et9davr2o3ichmQH+Uk1+6XCm1PhqPbYptb6sC2ndmYe/esm003fy7382bMuWgyPbG7ce2d7QfHk8kJllj8olBRCrBbONQygODwHAd13WM53EoFGpYsvTdVV4iPj+7oOStWEN1ByT7LPDvPuJNiL1PKYDDABwPYCL8Mbxe0N6tHf6Y3Pa0etJ2AHUANsNfEZ/YwwMMigBMA3AwgJHwRwg7QaLVDZ5POPhKAFrh5rwbCme/FW9v+HQnDkrJmHcsgK8BOAbAmNTvAFqC19ALXqNE2rjo5ONLZit12mATnXZTPUqoM9VvmOB3xNN+T/rNS/vdnPb70tsXxgA0A1gN4FMA24cYwBCAEwCcDuAgAFnBz25L25YiwX3J/slRADWh/NIV8baGdTt5QrOnPuOzg31nfwDjgm0QwXOLBs/XC15/D0BDsP9sQY8a7T39VL7znW9nvfXWB/lr175fFmzPYwCMdMPZZWVlpSXj9x1fOH7C+MKyESMKCvIL87JzsrM1UZiZHc8YFYtGEenoQHtHh9m6tdrbtHVrvKa6Otbe3tZp4tF2f99wmnR2TkNudvbmmGc/jcW9jxFtqu6xzf2rZFudYLuYCmB8sG1Qj/0SwWeVDp5zM4B1eXmjV7S319bLIUpIAC0E9sqVL3T++ee7C5YvL+S2eJ61Vtus3EjhyLyOA0aMiB577LFm+vTpvQ5kK1eu5CCLvScPclReXk7Tp08nYBZWrpzXbX9b3Pi0Xrt4cTje2prb2ZDItY7nOCFE6zZGtgP1HcPx2MvLy9Ujj7ycV9+8eX9YjIfxHKuw1c0p3LTf6IMajzrqnMSYMdUMzAQwD/5XdP0RwCrMU5tXrdKt27bp9sZG1+kgNx7vdD3PcTjUoRADgGwGokCYiaNBJXQ2WcdzPS9s46Pz8+NFRUVebORIs++0aebSmTPtvHkZHvBMoGb1amqqrqa2xkbqbG0lVAEzZ070pk+fzueff/5OdTk46oc/dLf/fWFpR0f7PtYaFyHdWlaQtW3SGWe0HVvyFQPMw/Tp1/DKldcQMBM1Y1cTli3D7NmzzT9rf9tggRhVVlYG298srBwxj6bXz2S/380spPre7F37T6bjFAXbNaZPn04rV66k+++/392yZUs2gDz4o+ZHAhgVfC0FkB+cROi0yYAJ/+RBtztZ2W2kdIMTcra54ew6RU5dc6KtEQ0N0R7dUP6pyjUGuG0oAEhuGytXjghea3/nTH62dt0PTJ9ez5WVlaisrOSdGfIjhATQQuwe6RlPuxdN+RqOfVD1OLh7w/zcCBiXhcI2f6hKS1YcqIsNIZtKPUas0wDrWjnDnIY9vC2NCwFbKNiOEjL8Af/ki46h5s2boQA4tbUJV+tmVynlxrR2EvG443qeZg4RM1M8HmciZROOZ2LxuInGYibS2emh3U0ATelXRiQwFEJIAC3+pbdf/ife3/if6DOAd+Pv5L3kdWDZb8S/cUzQV2mWELKzyEsghJxwCCHHNdk3hBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCiH97/x8SC0RMvr9/gwAAAABJRU5ErkJggg==";

// Embedded Yalda Gym Official Logo (Base64 JPEG for 100% self-contained delivery)
const YALDA_LOGO_BASE64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCALSBAADASIAAhEBAxEB/8QAHgABAAICAwEBAQAAAAAAAAAAAAEIBwkCBQYEAwr/xABSEAEAAQMDAQUGAgcDCAYHCQEAAQIDBAUGEQcIEiExQRMiUWFxgRSRCRUyQlKhwSOisRckM2KCkrLRFiVTcsLSNURUc4OjsxgnNENjZJTD8PH/xAAeAQEAAgIDAQEBAAAAAAAAAAAABwgFBgEDBAIJCv/EAEURAQABAwICBggCCAQGAQUBAAABAgMEBREGBxIhMUFRYRMicYGRobHBCNEUIzJCUnLh8BUzYpIkgqKywvEWNkNEU2Pi/9oADAMBAAIRAxEAPwDYL68B6/YflU3gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+weoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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mqe2Z65AHW6wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+wev2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6h6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+weoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEgiPOUgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQP/2Q==";

// Embedded Developer Official Portrait (Base64 JPEG for 100% self-contained delivery)
const DEVELOPER_PHOTO_BASE64 = "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";

// Embedded B Koodak Bold WOFF2 font for 100% self-contained delivery without external CDNs
const BKOODAK_WOFF2_BASE64 = "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";

const SHARED_FONT_CSS = `
@font-face {
    font-family: 'B Koodak';
    font-style: normal;
    font-weight: normal;
    font-display: swap;
    src: local('B Koodak'), local('BKoodak'), local('B-Koodak'),
         url('/fonts/bkoodak.woff2') format('woff2');
    unicode-range: U+0600-06FF, U+FB50-FDFF, U+FE70-FEFF, U+0750-077F, U+08A0-08FF, U+200C, U+200D;
}
@font-face {
    font-family: 'B Koodak';
    font-style: normal;
    font-weight: 700 800;
    font-display: swap;
    src: local('B Koodak Bold'), local('BKoodak Bold'), local('B-Koodak Bold'),
         local('B Koodak'), local('BKoodak'), local('B-Koodak'),
         url('/fonts/bkoodak.woff2') format('woff2');
    unicode-range: U+0600-06FF, U+FB50-FDFF, U+FE70-FEFF, U+0750-077F, U+08A0-08FF, U+200C, U+200D;
}
:root {
    --font-heading: 'B Koodak', Cambria, Georgia, serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, Arial, sans-serif;
    --font-body: 'B Koodak', Cambria, Georgia, serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, Arial, sans-serif;
    --font-latin: Cambria, Georgia, serif;
}
`;

// ============================================================================
// Landing Page Caching & Security Header Configuration
// ============================================================================
const LANDING_PAGE_ETAG = 'W/"landing-v3.4.5-nemov-opt"';
const LANDING_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "public, max-age=180, s-maxage=3600, stale-while-revalidate=86400",
    "ETag": LANDING_PAGE_ETAG,
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Alt-Svc": "clear",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:; frame-ancestors 'self'; base-uri 'self'; form-action 'self';",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Vary": "Accept-Encoding"
};

let cachedLandingHtml = null;
function getLandingHtml() {
    if (!cachedLandingHtml) {
        cachedLandingHtml = renderLandingPage();
    }
    return cachedLandingHtml;
}

function createLandingResponse(request) {
    if (request && request.method !== "GET" && request.method !== "HEAD") {
        return new Response("Method Not Allowed", {
            status: 405,
            headers: {
                "Allow": "GET, HEAD, OPTIONS",
                ...LANDING_HEADERS
            }
        });
    }
    const ifNoneMatch = request && request.headers && (request.headers.get("if-none-match") || request.headers.get("If-None-Match"));
    if (ifNoneMatch && (ifNoneMatch === LANDING_PAGE_ETAG || ifNoneMatch.includes(LANDING_PAGE_ETAG))) {
        return new Response(null, {
            status: 304,
            headers: LANDING_HEADERS
        });
    }
    if (request && request.method === "HEAD") {
        return new Response(null, {
            status: 200,
            headers: LANDING_HEADERS
        });
    }
    return new Response(getLandingHtml(), {
        status: 200,
        headers: LANDING_HEADERS
    });
}

function renderLandingPage() {
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>نرم‌افزار مدیریت ورزشی نِمُو (Nemov) | نسخه ۳.۳.۰</title>
    
    <!-- SEO Semantic Meta Tags -->
    <meta name="description" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov). پرونده سلامت فیزیکی، بانک ویدیو حرکات، رژیم غذایی و کالری‌شماری هوشمند، حسابداری مالی و صدور شناسنامه چاپی بدون نیاز به اینترنت با پشتیبان‌گیری ابری.">
    <meta name="keywords" content="نمو, Nemov, نرم افزار مدیریت ورزشی نمو, نرم افزار مدیریت باشگاه, نرم افزار بدنسازی, برنامه تمرینی, برنامه غذایی بدنسازی, مدیریت باشگاه بدنسازی, باشگاه بدنسازی یلدا, محراب حاجی پور, ابوالفضل صمدی, Nemov App">
    <link rel="canonical" href="https://nemovapp.ir/">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
    <meta name="author" content="مهندس ابوالفضل صمدی کوچکسرائی">
    <meta name="publisher" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov)">
    <meta name="application-name" content="نِمُو">
    <meta name="theme-color" content="#090A0E">
    <meta name="msapplication-TileColor" content="#DC2626">

    <!-- Open Graph Meta Tags (Telegram, WhatsApp, Social Cards) -->
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="نرم‌افزار مدیریت ورزشی نِمُو | Nemov">
    <meta property="og:title" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov) | نسخه ۳.۳.۰">
    <meta property="og:description" content="سامانه یکپارچه مربیگری و اتوماسیون باشگاه؛ پرونده سلامت، بانک حرکات با ویدیو، طراحی تخصصی رژیم غذایی، حسابداری مالی و صدور شناسنامه چاپی.">
    <meta property="og:url" content="https://nemovapp.ir/">
    <meta property="og:image" content="https://nemovapp.ir/images/nemov_logo.png">
    <meta property="og:image:secure_url" content="https://nemovapp.ir/images/nemov_logo.png">
    <meta property="og:image:type" content="image/png">
    <meta property="og:image:width" content="512">
    <meta property="og:image:height" content="512">
    <meta property="og:image:alt" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov)">
    <meta property="og:locale" content="fa_IR">

    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov) | نسخه ۳.۳.۰">
    <meta name="twitter:description" content="سامانه یکپارچه مربیگری و اتوماسیون باشگاه؛ پرونده سلامت، بانک حرکات با ویدیو، طراحی تخصصی رژیم غذایی، حسابداری مالی و صدور شناسنامه چاپی.">
    <meta name="twitter:image" content="https://nemovapp.ir/images/nemov_logo.png">
    <meta name="twitter:image:alt" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov)">

    <!-- Preload Critical Above-The-Fold Assets -->
    <link rel="preload" href="/images/nemov_logo.png" as="image" type="image/png">
    <link rel="preload" href="/fonts/bkoodak.woff2" as="font" type="font/woff2" crossorigin>

    <!-- Favicon -->
    <link rel="icon" type="image/png" href="/images/nemov_logo.png">

    <!-- Structured Data JSON-LD Schema.org (SoftwareApplication, SportsActivityLocation, Person) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "SoftwareApplication",
          "@id": "https://nemovapp.ir/#software",
          "name": "نرم‌افزار مدیریت ورزشی نِمُو",
          "alternateName": ["Nemov", "Nemov Sports Management Software", "همیار باشگاه"],
          "applicationCategory": "SportsApplication",
          "operatingSystem": "Windows 10, Windows 11",
          "description": "نرم‌افزار مدیریت ورزشی نِمُو (Nemov)؛ شامل پرونده سلامت، طراحی تمرین با ویدیو، رژیم غذایی و کالری‌شماری، حسابداری و صدور شناسنامه ورزشی چاپی.",
          "url": "https://nemovapp.ir/",
          "image": "https://nemovapp.ir/images/nemov_logo.png",
          "version": "3.3.0",
          "softwareVersion": "3.3.0",
          "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "IRR",
            "availability": "https://schema.org/InStock"
          },
          "author": {
            "@type": "Person",
            "@id": "https://nemovapp.ir/#author",
            "name": "مهندس ابوالفضل صمدی کوچکسرائی",
            "alternateName": "Abolfazl Samadi",
            "image": "https://nemovapp.ir/images/developer_photo.jpg",
            "email": "support@nemovapp.ir",
            "url": "https://t.me/AqaSamadi"
          },
          "featureList": [
            "پرونده سلامت و فیزیک ورزشکار",
            "طراحی تمرین و بانک حرکات با ویدیو",
            "طراحی تخصصی برنامه غذایی و کالری‌شماری",
            "موتور صدور شناسنامه و PDF چاپی حرفه‌ای",
            "حسابداری، صندوق و مدیریت شهریه",
            "سامانه اطلاع‌رسانی پیامکی هوشمند",
            "امنیت ۱۰۰٪ آفلاین با همگام‌سازی ابری"
          ]
        },
        {
          "@type": ["SportsActivityLocation", "ExerciseGym"],
          "@id": "https://nemovapp.ir/#yalda-gym",
          "name": "باشگاه بدنسازی یلدا",
          "alternateName": "Yalda Gym",
          "image": "https://nemovapp.ir/images/yalda_logo.jpg",
          "url": "https://nemovapp.ir/#partner-gyms",
          "address": {
            "@type": "PostalAddress",
            "streetAddress": "خیابان کوچکسرا، نبش شقایق ۳",
            "addressLocality": "قائمشهر",
            "addressRegion": "مازندران",
            "addressCountry": "IR"
          },
          "founder": {
            "@type": "Person",
            "name": "محراب حاجی‌پور",
            "jobTitle": "مدیریت باشگاه بدنسازی یلدا"
          },
          "openingHoursSpecification": [
            {
              "@type": "OpeningHoursSpecification",
              "dayOfWeek": ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
              "opens": "08:00",
              "closes": "12:00",
              "description": "سانس صبح بانوان"
            },
            {
              "@type": "OpeningHoursSpecification",
              "dayOfWeek": ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
              "opens": "15:00",
              "closes": "19:00",
              "description": "سانس عصر بانوان"
            },
            {
              "@type": "OpeningHoursSpecification",
              "dayOfWeek": ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
              "opens": "12:00",
              "closes": "15:00",
              "description": "سانس ظهر آقایان"
            },
            {
              "@type": "OpeningHoursSpecification",
              "dayOfWeek": ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
              "opens": "19:00",
              "closes": "23:00",
              "description": "سانس شب آقایان"
            }
          ]
        },
        {
          "@type": "Person",
          "@id": "https://nemovapp.ir/#author",
          "name": "مهندس ابوالفضل صمدی کوچکسرائی",
          "alternateName": "Abolfazl Samadi",
          "image": "https://nemovapp.ir/images/developer_photo.jpg",
          "jobTitle": "Software Developer & Architect",
          "email": "support@nemovapp.ir",
          "url": "https://t.me/AqaSamadi"
        }
      ]
    }
    </script>

    <style>
        /* Shared Fonts: B Koodak with fallback to system fonts */
        @font-face {
            font-family: 'B Koodak';
            font-style: normal;
            font-weight: normal;
            font-display: swap;
            src: local('B Koodak'), local('BKoodak'), local('B-Koodak'),
                 url('/fonts/bkoodak.woff2') format('woff2');
            unicode-range: U+0600-06FF, U+FB50-FDFF, U+FE70-FEFF, U+0750-077F, U+08A0-08FF, U+200C, U+200D;
        }
        @font-face {
            font-family: 'B Koodak';
            font-style: normal;
            font-weight: 700 800;
            font-display: swap;
            src: local('B Koodak Bold'), local('BKoodak Bold'), local('B-Koodak Bold'),
                 local('B Koodak'), local('BKoodak'), local('B-Koodak'),
                 url('/fonts/bkoodak.woff2') format('woff2');
            unicode-range: U+0600-06FF, U+FB50-FDFF, U+FE70-FEFF, U+0750-077F, U+08A0-08FF, U+200C, U+200D;
        }

        :root {
            --bg-base: #090A0E;
            --bg-card: rgba(18, 21, 30, 0.78);
            --bg-card-hover: rgba(26, 30, 42, 0.95);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(220, 38, 38, 0.4);
            --crimson: #DC2626;
            --crimson-light: #EF4444;
            --crimson-dark: #991B1B;
            --text-main: #FFFFFF;
            --text-sub: #E2E8F0;
            --text-muted: #94A3B8;
            --text-dim: #94A3B8;
            --accent-gold: #F59E0B;
            --accent-green: #10B981;
            --font-main: 'B Koodak', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 'Vazirmatn', Tahoma, Arial, sans-serif;
        }

        /* Accessibility Skip Link */
        .skip-link {
            position: absolute;
            top: -100px;
            right: 20px;
            background: var(--crimson);
            color: #FFFFFF;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 700;
            z-index: 9999;
            text-decoration: none;
            transition: top 0.2s ease;
        }
        .skip-link:focus {
            top: 15px;
            outline: 2px solid #FFFFFF;
        }

        /* Reset & Base Setup */
        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            max-width: 100%;
        }

        html {
            scroll-behavior: smooth;
            scroll-padding-top: 80px;
            background: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font-main);
            overflow-x: hidden;
            width: 100%;
        }

        :focus-visible {
            outline: 2px solid var(--crimson-light);
            outline-offset: 3px;
        }

        body {
            background: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font-main);
            line-height: 1.65;
            direction: rtl;
            overflow-x: hidden;
            width: 100%;
            position: relative;
        }

        /* Ambient Glow Layer */
        .ambient-glow {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 500px;
            background: radial-gradient(circle at 50% 10%, rgba(220, 38, 38, 0.12), transparent 70%);
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }

        /* Navbar */
        .navbar {
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            background: rgba(9, 10, 14, 0.92);
            border-bottom: 1px solid var(--border-subtle);
            padding: 12px 24px;
            width: 100%;
        }

        .nav-container {
            max-width: 1240px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            width: 100%;
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: inherit;
            flex-shrink: 0;
        }

        .brand-logo-img {
            width: 44px;
            height: 44px;
            object-fit: contain;
            border-radius: 10px;
            flex-shrink: 0;
            filter: drop-shadow(0 4px 10px rgba(220, 38, 38, 0.35));
        }

        .brand-icon-box {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(220, 38, 38, 0.25), rgba(153, 27, 27, 0.4));
            border: 1px solid rgba(220, 38, 38, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
            flex-shrink: 0;
        }

        .brand-text-box {
            display: flex;
            flex-direction: column;
            text-align: right;
        }

        .brand-title {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.3px;
            color: #FFFFFF;
            line-height: 1.2;
            white-space: nowrap;
        }

        .brand-subtitle {
            font-size: 11px;
            color: var(--crimson-light);
            font-weight: 600;
            letter-spacing: 0.2px;
            white-space: nowrap;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 6px;
            list-style: none;
        }

        .nav-link {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 14px;
            padding: 8px 14px;
            border-radius: 8px;
            transition: all 0.2s ease;
            font-weight: 500;
            white-space: nowrap;
        }

        .nav-link:hover {
            color: #FFFFFF;
            background: rgba(255, 255, 255, 0.05);
        }

        .nav-cta {
            background: linear-gradient(135deg, var(--crimson), var(--crimson-dark));
            color: #FFFFFF !important;
            padding: 8px 18px;
            border-radius: 10px;
            font-size: 13.5px;
            font-weight: 700;
            border: 1px solid rgba(239, 68, 68, 0.4);
            box-shadow: 0 4px 14px rgba(220, 38, 38, 0.35);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.25s ease;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .nav-cta:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220, 38, 38, 0.55);
            background: linear-gradient(135deg, var(--crimson-light), var(--crimson));
        }

        /* Section Layouts */
        .section {
            position: relative;
            z-index: 1;
            padding: 70px 20px;
            max-width: 1240px;
            margin: 0 auto;
            width: 100%;
        }

        .section-header {
            text-align: center;
            max-width: 800px;
            margin: 0 auto 48px;
        }

        .section-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 5px 14px;
            border-radius: 30px;
            background: rgba(220, 38, 38, 0.12);
            border: 1px solid rgba(220, 38, 38, 0.32);
            color: #FCA5A5;
            font-size: 12.5px;
            font-weight: 600;
            margin-bottom: 16px;
        }

        .section-title {
            font-size: clamp(22px, 3.8vw, 36px);
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.35;
            margin-bottom: 14px;
        }

        .section-subtitle {
            font-size: clamp(13.5px, 2vw, 16.5px);
            color: var(--text-muted);
            line-height: 1.7;
        }

        /* Hero Section */
        .hero {
            text-align: center;
            padding: 70px 20px 40px;
            position: relative;
            z-index: 1;
            width: 100%;
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 6px 16px;
            border-radius: 30px;
            background: rgba(220, 38, 38, 0.12);
            border: 1px solid rgba(220, 38, 38, 0.35);
            color: #FCA5A5;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 24px;
            line-height: 1.45;
            text-align: center;
            max-width: 100%;
            word-break: break-word;
            flex-wrap: wrap;
        }

        .hero-badge span:last-child {
            word-break: break-word;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--crimson-light);
            box-shadow: 0 0 10px var(--crimson-light);
            animation: pulseAnimation 2s infinite;
            flex-shrink: 0;
        }

        @keyframes pulseAnimation {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.4); opacity: 0.6; }
        }

        .hero-title {
            font-size: clamp(26px, 5.2vw, 56px);
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.3;
            margin-bottom: 16px;
            letter-spacing: -0.5px;
            word-break: break-word;
        }

        .hero-title-gradient {
            background: linear-gradient(135deg, #EF4444 0%, #F87171 50%, #FCA5A5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }

        .hero-tagline {
            font-size: clamp(15px, 2.4vw, 22px);
            color: var(--text-sub);
            font-weight: 600;
            max-width: 900px;
            margin: 0 auto 18px;
            line-height: 1.55;
        }

        .hero-desc {
            font-size: clamp(13px, 1.7vw, 16px);
            color: var(--text-muted);
            max-width: 860px;
            margin: 0 auto 34px;
            line-height: 1.8;
        }

        .hero-buttons {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
            flex-wrap: wrap;
            margin-bottom: 48px;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--crimson) 0%, var(--crimson-dark) 100%);
            color: #FFFFFF;
            padding: 13px 26px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            text-decoration: none;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 10px 24px rgba(220, 38, 38, 0.4);
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.25s ease;
        }

        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 14px 30px rgba(220, 38, 38, 0.6);
            background: linear-gradient(135deg, var(--crimson-light) 0%, var(--crimson) 100%);
        }

        .btn-secondary {
            background: rgba(22, 26, 36, 0.85);
            color: var(--text-sub);
            padding: 13px 24px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            text-decoration: none;
            border: 1px solid var(--border-subtle);
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.25s ease;
        }

        .btn-secondary:hover {
            background: rgba(30, 36, 50, 0.95);
            border-color: rgba(255, 255, 255, 0.2);
            color: #FFFFFF;
            transform: translateY(-2px);
        }

        /* Highlights Grid */
        .highlights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            max-width: 1140px;
            margin: 0 auto;
            text-align: right;
            width: 100%;
        }

        .highlight-card {
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
        }

        .highlight-card:hover {
            border-color: var(--border-glow);
            background: var(--bg-card-hover);
            transform: translateY(-2px);
        }

        .highlight-icon {
            font-size: 24px;
            flex-shrink: 0;
            width: 42px;
            height: 42px;
            border-radius: 10px;
            background: rgba(220, 38, 38, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .highlight-text h3 {
            font-size: 14.5px;
            font-weight: 700;
            color: #FFFFFF;
            margin-bottom: 3px;
        }

        .highlight-text p {
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        /* 8 Features Grid (Symmetric 4x2 or 2x4) */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            width: 100%;
        }

        .feature-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 18px;
            padding: 24px 20px;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .feature-card:hover {
            transform: translateY(-5px);
            border-color: var(--border-glow);
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5), 0 0 25px rgba(220, 38, 38, 0.18);
            background: var(--bg-card-hover);
        }

        .feature-top-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .feature-icon-wrapper {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(220, 38, 38, 0.22), rgba(153, 27, 27, 0.35));
            border: 1px solid rgba(220, 38, 38, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 14px rgba(220, 38, 38, 0.25);
            flex-shrink: 0;
        }

        .feature-module-badge {
            font-size: 11px;
            font-weight: 700;
            color: #FCA5A5;
            background: rgba(220, 38, 38, 0.15);
            border: 1px solid rgba(220, 38, 38, 0.3);
            padding: 3px 10px;
            border-radius: 20px;
            letter-spacing: 0.2px;
        }

        .feature-title {
            font-size: 17.5px;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 14px;
            line-height: 1.35;
        }

        .feature-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: auto;
        }

        .feature-item {
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.6;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .feature-item::before {
            content: "•";
            color: var(--crimson-light);
            font-size: 18px;
            line-height: 1;
            flex-shrink: 0;
            margin-top: 1px;
        }

        /* Partner Gyms Section */
        .partner-gyms-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 22px;
            width: 100%;
        }

        .gym-card {
            background: linear-gradient(155deg, rgba(22, 26, 36, 0.95) 0%, rgba(13, 15, 22, 0.98) 100%);
            border: 1px solid rgba(220, 38, 38, 0.35);
            border-radius: 20px;
            padding: 26px 22px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55), 0 0 30px rgba(220, 38, 38, 0.12);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .gym-status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #6EE7B7;
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 18px;
            align-self: flex-start;
        }

        .gym-status-badge::before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 6px #10B981;
        }

        .gym-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 18px;
        }

        .gym-logo-frame {
            width: 72px;
            height: 72px;
            border-radius: 50%;
            border: 2px solid var(--crimson);
            box-shadow: 0 0 16px rgba(220, 38, 38, 0.5);
            overflow: hidden;
            flex-shrink: 0;
            background: #000;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .gym-logo-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .gym-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .gym-name {
            font-size: 20px;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.25;
        }

        .gym-name-en {
            font-size: 11.5px;
            color: var(--text-dim);
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        .gym-manager {
            font-size: 13px;
            color: var(--accent-gold);
            font-weight: 700;
            margin-top: 3px;
        }

        .gym-address-box {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 18px;
            font-size: 12.5px;
            color: var(--text-sub);
            display: flex;
            align-items: center;
            gap: 8px;
            line-height: 1.5;
        }

        .shifts-section-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .shifts-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 18px;
        }

        .shift-card {
            border-radius: 10px;
            padding: 10px 8px;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .shift-card-female {
            background: rgba(236, 72, 153, 0.08);
            border: 1px solid rgba(236, 72, 153, 0.25);
        }

        .shift-card-male {
            background: rgba(59, 130, 246, 0.08);
            border: 1px solid rgba(59, 130, 246, 0.25);
        }

        .shift-label {
            font-size: 11.5px;
            font-weight: 700;
        }

        .shift-card-female .shift-label { color: #F472B6; }
        .shift-card-male .shift-label { color: #60A5FA; }

        .shift-time {
            font-size: 12px;
            font-weight: 700;
            color: #FFFFFF;
            direction: rtl;
        }

        .gym-features-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: auto;
        }

        .gym-feature-pill {
            font-size: 11px;
            color: var(--text-sub);
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 3px 8px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        /* Prospective Gym Card */
        .gym-join-card {
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
        }

        .gym-join-card:hover {
            border-color: var(--crimson-light);
            background: var(--bg-card-hover);
            transform: translateY(-4px);
        }

        .join-icon-box {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: rgba(220, 38, 38, 0.12);
            border: 1px solid rgba(220, 38, 38, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            margin-bottom: 16px;
        }

        .join-title {
            font-size: 18px;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 8px;
        }

        .join-desc {
            font-size: 13px;
            color: var(--text-muted);
            max-width: 380px;
            margin-bottom: 20px;
            line-height: 1.65;
        }

        /* Security & Architecture Section */
        .security-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 18px;
            width: 100%;
        }

        .security-card {
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
        }

        .security-card:hover {
            border-color: var(--border-glow);
            transform: translateY(-3px);
            background: var(--bg-card-hover);
        }

        .security-icon-box {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            background: rgba(220, 38, 38, 0.14);
            border: 1px solid rgba(220, 38, 38, 0.28);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            margin-bottom: 2px;
        }

        .security-card h3 {
            font-size: 16.5px;
            font-weight: 800;
            color: #FFFFFF;
        }

        .security-card p {
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.65;
        }

        /* Developer & Support Section */
        .developer-card {
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
        }

        .developer-avatar-box {
            width: 88px;
            height: 88px;
            border-radius: 50%;
            border: 3px solid var(--crimson-light);
            box-shadow: 0 0 28px rgba(220, 38, 38, 0.45), 0 8px 20px rgba(0, 0, 0, 0.6);
            margin-bottom: 16px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #11141c;
            flex-shrink: 0;
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        }

        .developer-avatar-box:hover {
            transform: scale(1.05);
            border-color: #EF4444;
            box-shadow: 0 0 36px rgba(239, 68, 68, 0.6), 0 10px 24px rgba(0, 0, 0, 0.7);
        }

        .developer-avatar-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 20%;
            display: block;
            border-radius: 50%;
        }

        .developer-avatar {
            width: 88px;
            height: 88px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .developer-name {
            font-size: 22px;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 4px;
        }

        .developer-role {
            font-size: 13.5px;
            color: var(--crimson-light);
            font-weight: 700;
            margin-bottom: 12px;
        }

        .developer-bio {
            font-size: 13.5px;
            color: var(--text-muted);
            max-width: 620px;
            line-height: 1.7;
            margin-bottom: 24px;
        }

        .contact-links-grid {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
            width: 100%;
        }

        .contact-btn {
            padding: 11px 20px;
            border-radius: 10px;
            font-size: 13.5px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.25s ease;
            direction: ltr;
            word-break: break-all;
        }

        .contact-btn-email {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #FFFFFF;
        }

        .contact-btn-email:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }

        .contact-btn-telegram {
            background: linear-gradient(135deg, #0088cc, #006699);
            border: 1px solid rgba(0, 136, 204, 0.4);
            color: #FFFFFF;
            box-shadow: 0 6px 18px rgba(0, 136, 204, 0.35);
        }

        .contact-btn-telegram:hover {
            background: linear-gradient(135deg, #0099e6, #0077b3);
            box-shadow: 0 8px 24px rgba(0, 136, 204, 0.5);
            transform: translateY(-2px);
        }

        /* Footer */
        .footer {
            background: #060709;
            border-top: 1px solid var(--border-subtle);
            padding: 36px 16px;
            text-align: center;
            position: relative;
            z-index: 1;
            width: 100%;
        }

        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .footer-brand {
            font-size: 16px;
            font-weight: 800;
            color: #FFFFFF;
        }

        .footer-copy {
            font-size: 12.5px;
            color: var(--text-muted);
            line-height: 1.6;
            max-width: 680px;
        }

        .footer-badges {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
            margin-top: 6px;
        }

        .footer-badge {
            font-size: 11px;
            color: var(--text-dim);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 4px 10px;
            border-radius: 6px;
        }

        /* Responsive Breakpoints */
        @media (max-width: 1100px) {
            .nav-links { display: none; }
            .features-grid { grid-template-columns: repeat(2, 1fr); }
            .partner-gyms-grid { grid-template-columns: 1fr; }
        }

        @media (max-width: 768px) {
            .section { padding: 45px 14px; }
            .hero { padding: 45px 14px 30px; }
            .shifts-grid { grid-template-columns: 1fr; }
            .gym-header { flex-direction: column; text-align: center; }
            .gym-info { align-items: center; }
            .gym-status-badge { align-self: center; }
            .contact-links-grid { flex-direction: column; width: 100%; }
            .contact-btn { width: 100%; justify-content: center; }
            .feature-card { padding: 20px 16px; }
            .gym-card { padding: 20px 16px; }
            .developer-card { padding: 24px 16px; }
        }

        @media (max-width: 640px) {
            .navbar { padding: 8px 10px; }
            .nav-container { gap: 6px; }
            .nav-brand { min-width: 0; flex-shrink: 1; gap: 6px; }
            .brand-logo-img { width: 30px; height: 30px; border-radius: 6px; }
            .brand-icon-box { width: 28px; height: 28px; font-size: 14px; border-radius: 6px; }
            .brand-text-box { min-width: 0; }
            .brand-title { font-size: 12px; max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .brand-subtitle { display: none; }
            .nav-cta { padding: 6px 9px; font-size: 11px; gap: 3px; border-radius: 8px; flex-shrink: 0; }
            .hero { padding: 35px 10px 24px; }
            .hero-logo-3d-wrapper { width: 95px; height: 95px; margin: 0 auto 14px auto; }
            .hero-logo-3d { width: 88px; height: 88px; }
            .hero-badge { font-size: 11px; padding: 5px 12px; border-radius: 20px; }
            .hero-title { font-size: 23px; line-height: 1.35; }
            .hero-tagline { font-size: 13.5px; margin-bottom: 12px; }
            .hero-desc { font-size: 12px; margin-bottom: 22px; }
            .hero-buttons { flex-direction: column; width: 100%; gap: 10px; margin-bottom: 30px; }
            .btn-primary, .btn-secondary { width: 100%; justify-content: center; padding: 11px 16px; font-size: 13.5px; }
            .section { padding: 35px 10px; }
            .section-title { font-size: 20px; }
            .section-subtitle { font-size: 12px; }
            .features-grid { grid-template-columns: 1fr; }
            .partner-gyms-grid { grid-template-columns: 1fr; }
            .highlights-grid { grid-template-columns: 1fr; }
            .security-grid { grid-template-columns: 1fr; }
            .shifts-grid { grid-template-columns: 1fr; }
            .gym-card { padding: 18px 12px; }
            .gym-name { font-size: 17.5px; }
            .gym-status-badge { font-size: 11px; padding: 3px 8px; white-space: normal; text-align: center; }
            .developer-card { padding: 20px 12px; }
            .developer-avatar-box { width: 78px; height: 78px; margin-bottom: 14px; }
            .developer-name { font-size: 19px; }
            .contact-btn { font-size: 12px; padding: 10px 14px; }
            .join-title { font-size: 17px; }
            .join-desc { font-size: 12px; }
            .btn-join { width: 100%; justify-content: center; font-size: 13px !important; padding: 11px 16px !important; }
        }

        /* ==========================================================================
           Package 2: Modern 3D Mockup, Infinite Frosted Marquee, 3D Tilt & Scroll
           ========================================================================== */
        
        /* Global Overflow-X Protection */
        html, body {
            overflow-x: clip !important;
            max-width: 100% !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        #main-content {
            overflow-x: clip;
            width: 100%;
            max-width: 100%;
        }

        /* Top Scroll Progress Bar */
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

        /* 3D Continuous Rotating Nemov Logo (Hardware-Accelerated & Ultra-Fluid 60fps) */
        .hero-logo-3d-wrapper {
            perspective: 1000px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px auto;
            width: 140px;
            height: 140px;
            position: relative;
        }

        .hero-logo-3d-wrapper::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 115%;
            height: 115%;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(220, 38, 38, 0.42) 0%, rgba(220, 38, 38, 0.12) 55%, transparent 75%);
            filter: blur(14px);
            pointer-events: none;
            z-index: 0;
            transition: opacity 0.3s ease;
        }

        .hero-logo-3d-wrapper:hover::before {
            background: radial-gradient(circle, rgba(239, 68, 68, 0.65) 0%, rgba(220, 38, 38, 0.22) 58%, transparent 78%);
        }

        .hero-logo-3d {
            width: 130px;
            height: 130px;
            object-fit: contain;
            image-rendering: -webkit-optimize-contrast;
            transform-style: preserve-3d;
            animation: rotateLogo3D 8s linear infinite !important;
            will-change: transform;
            cursor: pointer;
            position: relative;
            z-index: 1;
            filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.55));
            backface-visibility: visible;
        }

        .hero-logo-3d:hover {
            animation-play-state: running !important;
        }

        @keyframes rotateLogo3D {
            0% {
                transform: perspective(1000px) rotateY(0deg);
            }
            100% {
                transform: perspective(1000px) rotateY(360deg);
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
        }

        .mockup-perspective-wrapper {
            position: relative;
            transform-style: preserve-3d;
            transform: rotateX(6deg) rotateY(-2deg) rotateZ(0.5deg);
            transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.6s ease;
            animation: heroFloat 6s ease-in-out infinite alternate;
        }

        @keyframes heroFloat {
            0% {
                transform: rotateX(6deg) rotateY(-2deg) rotateZ(0.5deg) translateY(0);
            }
            100% {
                transform: rotateX(8deg) rotateY(-1deg) rotateZ(0.8deg) translateY(-10px);
            }
        }

        .app-window-frame {
            background: linear-gradient(165deg, rgba(22, 27, 40, 0.98) 0%, rgba(12, 14, 22, 0.99) 100%);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 18px;
            box-shadow: 0 30px 70px rgba(0, 0, 0, 0.75), 0 0 45px rgba(220, 38, 38, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.15);
            overflow: hidden;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            text-align: right;
        }

        .window-titlebar {
            background: #141824;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            padding: 11px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }

        .window-controls {
            display: flex;
            align-items: center;
            gap: 7px;
            direction: ltr;
        }

        .win-btn {
            width: 11px;
            height: 11px;
            border-radius: 50%;
            display: inline-block;
        }
        .win-close { background: #EF4444; box-shadow: 0 0 6px rgba(239, 68, 68, 0.6); }
        .win-min { background: #F59E0B; box-shadow: 0 0 6px rgba(245, 158, 11, 0.5); }
        .win-max { background: #10B981; box-shadow: 0 0 6px rgba(16, 185, 129, 0.5); }

        .window-title-text {
            font-size: 12.5px;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
        }

        .win-logo-mini {
            width: 18px;
            height: 18px;
            border-radius: 4px;
        }

        .window-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 10px;
            border-radius: 20px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #6EE7B7;
            font-size: 11px;
            font-weight: 700;
        }

        .live-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 6px #10B981;
            animation: pulseAnimation 2s infinite;
        }

        .window-content-grid {
            display: grid;
            grid-template-columns: 190px 1fr;
            min-height: 290px;
        }

        .mock-sidebar {
            background: #0E111A;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            padding: 16px 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .mock-nav-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 9px 12px;
            border-radius: 8px;
            font-size: 12.5px;
            color: #CBD5E1;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .mock-nav-item.active {
            background: rgba(220, 38, 38, 0.25);
            border: 1px solid rgba(239, 68, 68, 0.5);
            color: #FFFFFF;
            font-weight: 700;
        }

        .mock-workspace {
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .mock-stats-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }

        .mock-stat-card {
            background: rgba(26, 32, 48, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .mock-stat-card.highlight-card-mock {
            background: rgba(220, 38, 38, 0.16);
            border-color: rgba(239, 68, 68, 0.4);
        }

        .mock-stat-num {
            font-size: 20px;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.1;
        }

        .mock-stat-label {
            font-size: 11.5px;
            color: #CBD5E1;
            font-weight: 600;
        }

        .mock-dashboard-body {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .mock-panel {
            background: rgba(22, 27, 40, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 14px 16px;
        }

        .mock-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }

        .mock-panel-title {
            font-size: 13px;
            font-weight: 800;
            color: #FFFFFF;
        }

        .mock-tag-active {
            font-size: 11px;
            font-weight: 700;
            color: #FCA5A5;
            background: rgba(220, 38, 38, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 3px 9px;
            border-radius: 6px;
        }

        .mock-rows {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .mock-data-row {
            background: rgba(30, 37, 54, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 9px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            font-size: 12px;
        }

        .row-name {
            color: #FFFFFF;
            font-weight: 600;
            margin-left: auto;
        }

        .row-badge {
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }

        .badge-green {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #6EE7B7;
        }

        .badge-crimson {
            background: rgba(220, 38, 38, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #FCA5A5;
        }

        /* Floating Glass Widgets with Blur Effect (Strictly Outside Window Frame) */
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
        }

        /* Infinite Moving Marquee with Frosted Glass Cards (کادرهای با پس‌زمینه تار) */
        .marquee-section {
            position: relative;
            z-index: 2;
            padding: 24px 0;
            margin: 10px 0 35px;
            width: 100%;
            overflow: hidden;
            direction: ltr; /* Guarantees 100% smooth uniform continuous animation */
            mask-image: linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%);
            -webkit-mask-image: linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%);
        }

        .marquee-track {
            max-width: none !important;
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
            max-width: none !important;
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
            max-width: none !important;
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
        }

        .marquee-card:hover {
            background: rgba(32, 40, 58, 0.95);
            border-color: rgba(239, 68, 68, 0.55);
            box-shadow: 0 12px 28px rgba(220, 38, 38, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.18);
            transform: translateY(-3px);
        }

        .marquee-card-icon {
            font-size: 22px;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: rgba(220, 38, 38, 0.16);
            border: 1px solid rgba(239, 68, 68, 0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .marquee-card-text {
            display: flex;
            flex-direction: column;
            gap: 2px;
            text-align: right;
        }

        .marquee-card-title {
            font-size: 13.5px;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.3;
        }

        .marquee-card-desc {
            font-size: 11px;
            color: #CBD5E1;
            font-weight: 500;
        }

        /* 3D Tilt Effect & Dynamic Light Glare */
        .tilt-enabled {
            transition: transform 0.22s cubic-bezier(0.2, 0, 0.2, 1), box-shadow 0.22s ease, border-color 0.22s ease;
            will-change: transform;
            transform-style: preserve-3d;
            position: relative;
        }

        .tilt-glare-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: inherit;
            background: radial-gradient(circle 240px at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(220, 38, 38, 0.18), transparent 80%);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            z-index: 2;
        }

        .tilt-enabled:hover .tilt-glare-overlay {
            opacity: 1;
        }

        /* Scroll Reveal (ScrollTrigger Equivalent) - Default is visible so no blank layout */
        .reveal-on-scroll {
            transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1), transform 0.7s cubic-bezier(0.16, 1, 0.3, 1), filter 0.6s ease;
            will-change: opacity, transform, filter;
        }

        .reveal-pending {
            opacity: 0 !important;
            transform: translateY(26px) !important;
            filter: blur(4px) !important;
        }

        .reveal-pending.revealed {
            opacity: 1 !important;
            transform: translateY(0) !important;
            filter: blur(0) !important;
        }

        /* Staggered cascading entry for the 8 features */
        .features-grid .feature-card:nth-child(1) { transition-delay: 0.04s; }
        .features-grid .feature-card:nth-child(2) { transition-delay: 0.08s; }
        .features-grid .feature-card:nth-child(3) { transition-delay: 0.12s; }
        .features-grid .feature-card:nth-child(4) { transition-delay: 0.16s; }
        .features-grid .feature-card:nth-child(5) { transition-delay: 0.20s; }
        .features-grid .feature-card:nth-child(6) { transition-delay: 0.24s; }
        .features-grid .feature-card:nth-child(7) { transition-delay: 0.28s; }
        .features-grid .feature-card:nth-child(8) { transition-delay: 0.32s; }

        @media (max-width: 768px) {
            .window-content-grid { grid-template-columns: 1fr; }
            .mock-sidebar { display: none; }
            .floating-glass-widget { display: none; }
            .mockup-perspective-wrapper {
                transform: rotateX(2deg) rotateY(0deg) !important;
                animation: none;
            }
        }

        @media (max-width: 640px) {
            .hero-badge { white-space: normal; text-align: center; max-width: 95%; font-size: 11px; padding: 6px 12px; }
            .hero-title { font-size: 20px !important; line-height: 1.35; word-break: normal; }
            .hero-title-gradient { display: inline !important; }
            .hero-tagline { font-size: 13px; line-height: 1.5; }
            .hero-desc { font-size: 11.5px; line-height: 1.7; }
            .hero-mockup-container { margin: 24px auto 30px; padding: 0; width: 100%; max-width: 100%; overflow: hidden; box-sizing: border-box; }
            .mockup-perspective-wrapper { transform: none !important; width: 100%; max-width: 100%; box-sizing: border-box; }
            .app-window-frame { width: 100%; max-width: 100%; box-sizing: border-box; border-radius: 12px; }
            .window-titlebar { padding: 8px 10px; flex-wrap: wrap; gap: 8px; }
            .window-title-text { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
            .window-status-pill { padding: 2px 8px; font-size: 10px; }
            .mock-workspace { padding: 12px 10px; width: 100%; box-sizing: border-box; }
            .mock-stats-row { grid-template-columns: 1fr; gap: 8px; }
            .mock-data-row { flex-wrap: wrap; gap: 6px; padding: 8px 10px; font-size: 11px; }
            .row-name { width: 100%; }
            .marquee-card { padding: 10px 14px; gap: 8px; border-radius: 12px; }
            .marquee-card-icon { width: 32px; height: 32px; font-size: 17px; }
            .marquee-card-title { font-size: 12px; }
            .marquee-card-desc { font-size: 10px; }
        }

        @media (prefers-reduced-motion: reduce) {
            .reveal-pending {
                opacity: 1 !important;
                transform: none !important;
                filter: none !important;
                transition: none !important;
            }
            .marquee-track {
                animation: none !important;
            }
            .mockup-perspective-wrapper {
                animation: none !important;
                transform: none !important;
            }
            .floating-glass-widget {
                animation: none !important;
            }
        }

    </style>
</head>
<body>
    <div id="scroll-progress-bar" class="scroll-progress-bar" aria-hidden="true"></div>
    <a href="#main-content" class="skip-link">پرش به محتوای اصلی</a>
    <div class="ambient-glow" aria-hidden="true"></div>

    <!-- Sticky Navigation Bar (Confidential: Strictly No Admin Login Button) -->
    <header class="navbar" role="banner">
        <div class="nav-container">
            <a href="#" class="nav-brand" aria-label="نرم‌افزار مدیریت ورزشی نِمُو - صفحه اصلی">
                <img src="/images/nemov_logo.png" alt="لوگوی نرم‌افزار مدیریت ورزشی نِمُو" class="brand-logo-img" width="44" height="44">
                <div class="brand-text-box">
                    <span class="brand-title">نرم‌افزار مدیریت ورزشی نِمُو</span>
                    <span class="brand-subtitle">Nemov</span>
                </div>
            </a>
            <nav role="navigation" aria-label="ناوبری اصلی">
                <ul class="nav-links">
                    <li><a href="#features" class="nav-link">ماژول‌ها و امکانات</a></li>
                    <li><a href="#partner-gyms" class="nav-link">باشگاه‌های عضو</a></li>
                    <li><a href="#security" class="nav-link">امنیت و پایداری</a></li>
                    <li><a href="#contact" class="nav-link">ارتباط با توسعه‌دهنده</a></li>
                </ul>
            </nav>
            <a href="#features" class="nav-cta" aria-label="مشاهده امکانات و ماژول‌های نرم‌افزار">مشاهده امکانات 📋</a>
        </div>
    </header>

    <!-- Hero Section -->
    <main id="main-content">
        <section class="hero" aria-labelledby="hero-heading">
            <!-- Continuous 3D Rotating Nemov Logo (Never pauses on hover) -->
            <div class="hero-logo-3d-wrapper" aria-hidden="true">
                <img src="/images/nemov_logo.png" alt="لوگوی سه‌بعدی چرخان نرم‌افزار مدیریت ورزشی نِمُو" class="hero-logo-3d" width="130" height="130">
            </div>
            <div class="hero-badge">
                <span class="pulse-dot"></span>
                <span>🏆 سامانه جامع مدیریت هوشمند و مربیگری باشگاه‌های ورزشی | Nemov</span>
            </div>
            <h1 id="hero-heading" class="hero-title">
                <span class="hero-title-gradient">نرم‌افزار مدیریت ورزشی نِمُو (Nemov)</span>
            </h1>
            <p class="hero-tagline">
                راهکار یکپارچه و پیشرفته برای مربیان حرفه‌ای و مدیران باشگاه‌های بدنسازی
            </p>
            <p class="hero-desc">
                طراحی‌شده بر پایه کارکرد ۱۰۰٪ مستقل و آفلاین روی ویندوز همراه با امنیت و همگام‌سازی ابری؛ مجهز به پرونده الکترونیک سلامت، بانک جامع ویدیوهای تمرینی، طراحی هوشمند رژیم غذایی و کالری‌شماری، حسابداری و صندوق، و صدور فوری شناسنامه چاپی بدون نیاز به اینترنت.
            </p>
            <div class="hero-buttons">
                <a href="#features" class="btn-primary" aria-label="مشاهده امکانات و ماژول‌ها">مشاهده امکانات و ماژول‌ها 📋</a>
                <a href="#partner-gyms" class="btn-secondary" aria-label="مشاهده باشگاه‌های عضو سامانه">باشگاه‌های عضو سامانه 🏋️‍♂️</a>
            </div>

            <!-- 3D Perspective App Mockup with Floating Sports Widgets -->
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
                            <span class="widget-subline">پشتیبان خودکار در سرور</span>
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

                    <!-- Main 3D App Window Frame -->
                    <div class="app-window-frame">
                        <!-- Window Titlebar -->
                        <div class="window-titlebar">
                            <div class="window-controls">
                                <span class="win-btn win-close"></span>
                                <span class="win-btn win-min"></span>
                                <span class="win-btn win-max"></span>
                            </div>
                            <div class="window-title-text">
                                <img src="/images/nemov_logo.png" alt="" class="win-logo-mini" width="18" height="18">
                                <span>نرم‌افزار مدیریت ورزشی نِمُو (Nemov) - نسخه ۳.۳.۰ [پایگاه داده آفلاین فعال]</span>
                            </div>
                            <div class="window-status-pill">
                                <span class="live-dot"></span>
                                <span>۱۰۰٪ آماده و آفلاین</span>
                            </div>
                        </div>

                        <!-- Window Content (Mockup Dashboard) -->
                        <div class="window-content-grid">
                            <!-- Mini Sidebar -->
                            <aside class="mock-sidebar">
                                <div class="mock-nav-item active"><span class="mock-nav-icon">📊</span><span>داشبورد</span></div>
                                <div class="mock-nav-item"><span class="mock-nav-icon">👥</span><span>ورزشکاران</span></div>
                                <div class="mock-nav-item"><span class="mock-nav-icon">🏋️‍♂️</span><span>برنامه تمرین</span></div>
                                <div class="mock-nav-item"><span class="mock-nav-icon">🥗</span><span>رژیم غذایی</span></div>
                                <div class="mock-nav-item"><span class="mock-nav-icon">💰</span><span>حسابداری</span></div>
                                <div class="mock-nav-item"><span class="mock-nav-icon">⚙️</span><span>تنظیمات تم</span></div>
                            </aside>

                            <!-- Mock Main Workspace -->
                            <div class="mock-workspace">
                                <!-- Top Stat Cards in Mockup -->
                                <div class="mock-stats-row">
                                    <div class="mock-stat-card">
                                        <span class="mock-stat-num">۴۸</span>
                                        <span class="mock-stat-label">ورزشکار فعال در دوره</span>
                                    </div>
                                    <div class="mock-stat-card">
                                        <span class="mock-stat-num">۱۰۰٪</span>
                                        <span class="mock-stat-label">پایداری بدون اینترنت</span>
                                    </div>
                                    <div class="mock-stat-card highlight-card-mock">
                                        <span class="mock-stat-num">۱۷ تم</span>
                                        <span class="mock-stat-label">شخصی‌سازی برندینگ</span>
                                    </div>
                                </div>

                                <!-- Mock Content Preview: Workout & Health Card -->
                                <div class="mock-dashboard-body">
                                    <div class="mock-panel mock-workout-panel">
                                        <div class="mock-panel-header">
                                            <span class="mock-panel-title">📋 آخرین پرونده‌های ارزیابی فیزیک و BMR</span>
                                            <span class="mock-tag-active">تایید مربی</span>
                                        </div>
                                        <div class="mock-rows">
                                            <div class="mock-data-row">
                                                <span class="row-avatar">👤</span>
                                                <span class="row-name">علی رضایی (دوره هایپرتروفی)</span>
                                                <span class="row-badge badge-green">BMR: 1840 kcal</span>
                                                <span class="row-badge badge-crimson">PDF صادر شد</span>
                                            </div>
                                            <div class="mock-data-row">
                                                <span class="row-avatar">👤</span>
                                                <span class="row-name">محمد حسینی (کاهش چربی)</span>
                                                <span class="row-badge badge-green">چربی: 14.2%</span>
                                                <span class="row-badge badge-crimson">پیامک ارسال شد</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Highlights -->
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
                        <p>همگام‌سازی رمزنگاری‌شده با سرورهای امن در پس‌زمینه</p>
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
            </div>
        </section>

        <!-- Infinite Moving Marquee with Frosted Glass Cards (کادرهای با پس‌زمینه تار) -->
        <section class="marquee-section" aria-label="خلاصه امکانات و قابلیت‌های برجسته نرم‌افزار نِمُو">
            <div class="marquee-track">
                <!-- Group 1 -->
                <div class="marquee-group">
                    <div class="marquee-card">
                        <span class="marquee-card-icon">📋</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">پرونده سلامت فیزیکی</strong>
                            <span class="marquee-card-desc">ترکیب بدنی، BMR و غربالگری</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🏋️‍♂️</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">طراحی هوشمند تمرین</strong>
                            <span class="marquee-card-desc">بانک ویدیویی و آناتومی عضلات</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🥗</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">برنامه غذایی و کالری‌شماری</strong>
                            <span class="marquee-card-desc">محاسبه درشت‌مغذی‌ها و TDEE</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">📄</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">موتور صدور PDF چاپی</strong>
                            <span class="marquee-card-desc">شناسنامه ورزشی با لوگوی باشگاه</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">💰</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">حسابداری و مدیریت شهریه</strong>
                            <span class="marquee-card-desc">کنترل صندوق و یادآوری سررسید</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">📩</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">سامانه پیامکی هوشمند</strong>
                            <span class="marquee-card-desc">تحویل آنی بدون بلک‌لیست</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">⚡</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">کارکرد ۱۰۰٪ آفلاین</strong>
                            <span class="marquee-card-desc">پایداری مطلق روی سیستم ویندوز</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">☁️</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">پشتیبان‌گیری خودکار ابری</strong>
                            <span class="marquee-card-desc">همگام‌سازی امن با سرور</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🎨</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">۱۷ تم رنگی اختصاصی</strong>
                            <span class="marquee-card-desc">۱۲ تم دارک و ۵ تم لایت لوکس</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🛡️</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">امنیت و حریم خصوصی داده‌ها</strong>
                            <span class="marquee-card-desc">پایگاه داده محلی رمزنگاری‌شده</span>
                        </div>
                    </div>
                </div>

                <!-- Group 2 (Duplicate for Seamless Infinite Loop) -->
                <div class="marquee-group" aria-hidden="true">
                    <div class="marquee-card">
                        <span class="marquee-card-icon">📋</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">پرونده سلامت فیزیکی</strong>
                            <span class="marquee-card-desc">ترکیب بدنی، BMR و غربالگری</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🏋️‍♂️</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">طراحی هوشمند تمرین</strong>
                            <span class="marquee-card-desc">بانک ویدیویی و آناتومی عضلات</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🥗</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">برنامه غذایی و کالری‌شماری</strong>
                            <span class="marquee-card-desc">محاسبه درشت‌مغذی‌ها و TDEE</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">📄</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">موتور صدور PDF چاپی</strong>
                            <span class="marquee-card-desc">شناسنامه ورزشی با لوگوی باشگاه</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">💰</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">حسابداری و مدیریت شهریه</strong>
                            <span class="marquee-card-desc">کنترل صندوق و یادآوری سررسید</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">📩</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">سامانه پیامکی هوشمند</strong>
                            <span class="marquee-card-desc">تحویل آنی بدون بلک‌لیست</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">⚡</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">کارکرد ۱۰۰٪ آفلاین</strong>
                            <span class="marquee-card-desc">پایداری مطلق روی سیستم ویندوز</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">☁️</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">پشتیبان‌گیری خودکار ابری</strong>
                            <span class="marquee-card-desc">همگام‌سازی امن با سرور</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🎨</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">۱۷ تم رنگی اختصاصی</strong>
                            <span class="marquee-card-desc">۱۲ تم دارک و ۵ تم لایت لوکس</span>
                        </div>
                    </div>
                    <div class="marquee-card">
                        <span class="marquee-card-icon">🛡️</span>
                        <div class="marquee-card-text">
                            <strong class="marquee-card-title">امنیت و حریم خصوصی داده‌ها</strong>
                            <span class="marquee-card-desc">پایگاه داده محلی رمزنگاری‌شده</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 8 Main Modules Grid (Symmetric Layout) -->
        <section id="features" class="section" role="region" aria-labelledby="features-heading">
            <div class="section-header">
                <div class="section-pill">معماری جامع و ماژولار</div>
                <h2 id="features-heading" class="section-title">ویترین کامل قابلیت‌ها و ماژول‌های سیستم</h2>
                <p class="section-subtitle">
                    هشت ماژول تخصصی و کاملاً یکپارچه، طراحی‌شده بر اساس نیازهای میدانی مدیران باشگاه‌ها و مربیان ورزشی
                </p>
            </div>

            <div class="features-grid">
                <!-- Module 1 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-1">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">📋</div>
                        <span class="feature-module-badge">ماژول ۱</span>
                    </div>
                    <h3 id="module-title-1" class="feature-title">پرونده سلامت و فیزیک ورزشکار</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">ارزیابی ترکیب بدنی و شاخص‌های آنتروپومتریک شامل BMR، درصد چربی، توده عضلانی و نسبت دور کمر به باسن (WHR).</li>
                        <li class="feature-item">تست‌های تخصصی غربالگری ناهنجاری‌های اسکلتی و قامتی (لوردوز، کیفوز، اسکولیوز، افتادگی شانه، پای پرانتزی و ضربدری).</li>
                        <li class="feature-item">آلبوم تصویری پیشرفت فیزیکی با قابلیت مقایسه دوره‌ای عکس‌های قبل و بعد ورزشکار در زوایای استاندارد.</li>
                        <li class="feature-item">بایگانی دائمی سوابق پزشکی، تاریخچه آسیب‌های ورزشی، بیماری‌ها و منع‌های تمرینی.</li>
                    </ul>
                </article>

                <!-- Module 2 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-2">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🏋️‍♂️</div>
                        <span class="feature-module-badge">ماژول ۲</span>
                    </div>
                    <h3 id="module-title-2" class="feature-title">طراحی تمرین و بانک حرکات با ویدیو</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">کتابخانه غنی حرکات ورزشی تفکیک‌شده بر اساس گروه‌های عضلانی هدف و تجهیزات تمرینی باشگاه.</li>
                        <li class="feature-item">پخش ویدیوی تکنیک صحیح اجرای حرکت و بررسی زوایای آناتومیکی جهت پیشگیری از آسیب و اجرای استاندارد.</li>
                        <li class="feature-item">طراحی هوشمند جلسات تمرینی شامل تعداد ست‌ها، دامنه‌های تکرار، زمان استراحت، سوپرست و دراپ‌ست.</li>
                        <li class="feature-item">قابلیت ایجاد، ویرایش و ذخیره الگوهای تمرینی آماده برای سطوح مبتدی، متوسط و پیشرفته.</li>
                    </ul>
                </article>

                <!-- Module 3 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-3">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🥗</div>
                        <span class="feature-module-badge">ماژول ۳</span>
                    </div>
                    <h3 id="module-title-3" class="feature-title">طراحی تخصصی برنامه غذایی و کالری‌شماری</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">بانک جامع غذاهای سنتی و مدرن ایرانی همراه با جدول ارزش غذایی دقیق و میزان پروتئین و کالری.</li>
                        <li class="feature-item">محاسبه‌گر خودکار نرخ متابولیسم پایه (BMR) و کل انرژی مصرفی روزانه (TDEE) متناسب با تیپ بدنی.</li>
                        <li class="feature-item">تفکیک هوشمند درشت‌مغذی‌ها (پروتئین، کربوهیدرات، چربی مفید) برای وعده‌ها و میان‌وعده‌های روزانه.</li>
                        <li class="feature-item">ماژول اختصاصی تجویز، زمان‌بندی و دوز بهینه مصرف مکمل‌های ورزشی مجاز و نوشیدنی‌های ورزشی.</li>
                    </ul>
                </article>

                <!-- Module 4 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-4">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">📄</div>
                        <span class="feature-module-badge">ماژول ۴</span>
                    </div>
                    <h3 id="module-title-4" class="feature-title">موتور صدور شناسنامه و PDF چاپی حرفه‌ای</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">صدور شناسنامه سلامت فیزیکی و ورزشی بسیار شکیل و فشرده در قالب‌های استاندارد A4 و A5.</li>
                        <li class="feature-item">خروجی چاپی برنامه‌های تمرینی و غذایی با سربرگ و لوگوی اختصاصی باشگاه.</li>
                        <li class="feature-item">تولید ۱۰۰٪ آفلاین و آنی بدون وابستگی به اینترنت یا نرم‌افزارهای جانبی.</li>
                        <li class="feature-item">طراحی تایپوگرافی اصیل با فونت فارسی بهینه، عدم به هم ریختگی فونت و خوانایی عالی در چاپ.</li>
                    </ul>
                </article>

                <!-- Module 5 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-5">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">💰</div>
                        <span class="feature-module-badge">ماژول ۵</span>
                    </div>
                    <h3 id="module-title-5" class="feature-title">حسابداری، صندوق و مدیریت شهریه</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">ثبت و مدیریت دوره‌ها، پکیج‌های عضویت ماهانه، فصلی، سالانه و سانس‌های خصوصی مربیگری.</li>
                        <li class="feature-item">سیستم صندوق و ثبت روش‌های مختلف پرداخت (نقدی، کارت‌خوان، کارت‌به‌کارت و تخفیف‌ها).</li>
                        <li class="feature-item">گزارش‌گیری جامع از دریافتی‌ها، تراز سود و زیان و بررسی لیست اعضای بدهکار در چند ثانیه.</li>
                        <li class="feature-item">یادآوری هوشمند تاریخ تمدید دوره‌ها و شناسایی خودکار اعضای با عضویت رو به پایان.</li>
                    </ul>
                </article>

                <!-- Module 6 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-6">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">📩</div>
                        <span class="feature-module-badge">ماژول ۶</span>
                    </div>
                    <h3 id="module-title-6" class="feature-title">سامانه اطلاع‌رسانی پیامکی هوشمند</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">ارسال پیامک از خطوط خدماتی بدون تداخل با بلک‌لیست مخابراتی برای اطمینان از تحویل ۱۰۰٪ پیام‌ها.</li>
                        <li class="feature-item">تبریک خودکار سالروز تولد ورزشکاران جهت ارتقای تعامل، حس وفاداری و رضایت ورزشکار.</li>
                        <li class="feature-item">یادآوری خودکار سررسید شهریه، پیامک‌های خوش‌آمدگویی و تایید ثبت‌نام در سامانه.</li>
                        <li class="feature-item">ارسال پیامک‌های گروهی سریع برای اعلام رویدادها، تغییر ساعات کاری و تعطیلی‌های باشگاه.</li>
                    </ul>
                </article>

                <!-- Module 7 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-7">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🛡️</div>
                        <span class="feature-module-badge">ماژول ۷</span>
                    </div>
                    <h3 id="module-title-7" class="feature-title">امنیت ۱۰۰٪ آفلاین با همگام‌سازی ابری</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">کارکرد کاملاً مستقل روی سیستم‌عامل ویندوز بدون وابستگی به اینترنت در سالن ورزشی.</li>
                        <li class="feature-item">پایگاه داده محلی سریع و ایمن با رمزنگاری قوی برای حفاظت از حریم خصوصی ورزشکاران.</li>
                        <li class="feature-item">پشتیبان‌گیری خودکار و هوشمند در پایان روز کاری روی سرورهای ابری کلودفلر.</li>
                        <li class="feature-item">قابلیت بازیابی آنی اطلاعات در صورت آسیب سیستم یا تعویض رایانه باشگاه بدون فوت وقت.</li>
                    </ul>
                </article>

                <!-- Module 8 -->
                <article class="feature-card reveal-on-scroll" aria-labelledby="module-title-8">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🎨</div>
                        <span class="feature-module-badge">ماژول ۸</span>
                    </div>
                    <h3 id="module-title-8" class="feature-title">شخصی‌سازی، تم‌ها و برندینگ باشگاه</h3>
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <ul class="feature-list">
                        <li class="feature-item">موتور تم اختصاصی با کلکسیون ۱۷ پالت رنگی مدرن (۱۲ تم دارک و ۵ تم لایت) متناسب با سلیقه مربی.</li>
                        <li class="feature-item">بارگذاری لوگو و نام اختصاصی باشگاه ورزشی با بازنشانی آنی به لوگوی پیش‌فرض نِمُو در صورت تمایل.</li>
                        <li class="feature-item">درج خودکار لوگو و نام باشگاه در سربرگ و واترمارک برنامه‌های تمرینی و تغذیه PDF.</li>
                        <li class="feature-item">انعکاس نام اختصاصی باشگاه در تمامی پیامک‌های خودکار ارسالی به ورزشکاران جهت تثبیت برند مجموعه.</li>
                    </ul>
                </article>
            </div>
        </section>

        <!-- Partner Gyms Section -->
        <section id="partner-gyms" class="section" role="region" aria-labelledby="partner-gyms-heading">
            <div class="section-header">
                <div class="section-pill">شبکه باشگاه‌های پیشرو</div>
                <h2 id="partner-gyms-heading" class="section-title">باشگاه‌های مجهز به نرم‌افزار نِمُو (Nemov)</h2>
                <p class="section-subtitle">
                    مجموعه‌های ورزشی ممتازی که با تجهیز به این سامانه، بالاترین استاندارد مربیگری و رضایت ورزشکاران را به ارمغان آورده‌اند
                </p>
            </div>

            <div class="partner-gyms-grid">
                <!-- Gym 1: Yalda Gym (باشگاه بدنسازی یلدا) -->
                <article class="gym-card reveal-on-scroll" aria-labelledby="gym-name-yalda">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="gym-status-badge">باشگاه برتر عضو سامانه • استان مازندران</div>
                    
                    <div class="gym-header">
                        <div class="gym-logo-frame">
                            <img src="/images/yalda_logo.jpg" alt="لوگوی رسمی باشگاه بدنسازی یلدا" class="gym-logo-img" loading="lazy" width="72" height="72">
                        </div>
                        <div class="gym-info">
                            <h3 id="gym-name-yalda" class="gym-name">باشگاه بدنسازی یلدا</h3>
                            <span class="gym-name-en">Yalda Gym • Since 2006</span>
                            <span class="gym-manager">مدیریت: جناب آقای محراب حاجی‌پور</span>
                        </div>
                    </div>

                    <div class="gym-address-box">
                        <span>📍</span>
                        <span>مازندران، قائمشهر، خیابان کوچکسرا، نبش شقایق ۳</span>
                    </div>

                    <div class="shifts-section-title">
                        <span>⏰</span>
                        <span>ساعات دقیق سانس‌ها و شیفت‌های کاری مجموعه:</span>
                    </div>

                    <div class="shifts-grid" role="region" aria-label="ساعات دقیق سانس‌ها و شیفت‌های کاری مجموعه">
                        <div class="shift-card shift-card-female">
                            <span class="shift-label">👩 سانس بانوان (صبح)</span>
                            <span class="shift-time">۸:۰۰ صبح الی ۱۲:۰۰ ظهر</span>
                        </div>
                        <div class="shift-card shift-card-female">
                            <span class="shift-label">👩 سانس بانوان (عصر)</span>
                            <span class="shift-time">۱۵:۰۰ الی ۱۹:۰۰ (۳ تا ۷ غروب)</span>
                        </div>
                        <div class="shift-card shift-card-male">
                            <span class="shift-label">👨 سانس آقایان (ظهر)</span>
                            <span class="shift-time">۱۲:۰۰ ظهر الی ۱۵:۰۰ (۳ بعدازظهر)</span>
                        </div>
                        <div class="shift-card shift-card-male">
                            <span class="shift-label">👨 سانس آقایان (شب)</span>
                            <span class="shift-time">۱۹:۰۰ الی ۲۳:۰۰ (۷ غروب تا ۱۱ شب)</span>
                        </div>
                    </div>

                    <div class="gym-features-badges">
                        <span class="gym-feature-pill">✓ پرونده الکترونیک سلامت</span>
                        <span class="gym-feature-pill">✓ تمرینات ویدیویی</span>
                        <span class="gym-feature-pill">✓ رژیم و کالری‌شماری</span>
                        <span class="gym-feature-pill">✓ اطلاع‌رسانی پیامکی</span>
                        <span class="gym-feature-pill">✓ پشتیبان‌گیری ابری فعال</span>
                    </div>
                </article>

                <!-- Modular Prospective Card: Join Platform -->
                <article class="gym-join-card" aria-labelledby="join-heading">
                    <div class="tilt-glare-overlay" aria-hidden="true"></div>
                    <div class="join-icon-box" aria-hidden="true">🏆</div>
                    <h3 id="join-heading" class="join-title">باشگاه خود را مجهز کنید</h3>
                    <p class="join-desc">
                        آیا مایلید مجموعه ورزشی شما نیز به نرم‌افزار مدیریت ورزشی نِمُو مجهز شده و از اتوماسیون مربیگری، ارزیابی بدنی و پشتیبان‌گیری ابری بهره‌مند شود؟
                    </p>
                    <a href="https://t.me/AqaSamadi" target="_blank" rel="noopener noreferrer" class="btn-primary btn-join" aria-label="مشاوره و درخواست تجهیز باشگاه در تلگرام (باز شدن در تب جدید)">
                        مشاوره و درخواست تجهیز باشگاه 🚀
                    </a>
                </article>
            </div>
        </section>

        <!-- Security & Architecture Section -->
        <section id="security" class="section" role="region" aria-labelledby="security-heading">
            <div class="section-header">
                <div class="section-pill">معماری پایدار و امن</div>
                <h2 id="security-heading" class="section-title">عملکرد ۱۰۰٪ مستقل و امنیت در تراز صنعتی</h2>
                <p class="section-subtitle">
                    خیال شما از بابت قطعی اینترنت، سرعت نرم‌افزار و حفظ اطلاعات محرمانه ورزشکاران برای همیشه راحت خواهد بود
                </p>
            </div>

            <div class="security-grid">
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
                    <h3>پشتیبان‌گیری ابری خودکار در سرور</h3>
                    <p>
                        با اتصال به اینترنت، بکاپ‌های امنیتی به صورت خودکار به فضای ابری امن سرور ارسال می‌شوند تا در صورت نقص سخت‌افزاری، اطلاعات بلافاصله بازیابی شوند.
                    </p>
                </div>
            </div>
        </section>

        <!-- Developer Profile & Official Support Section -->
        <section id="contact" class="section" role="region" aria-labelledby="contact-heading">
            <div class="section-header">
                <div class="section-pill">پشتیبانی و توسعه رسمی</div>
                <h2 id="contact-heading" class="section-title">توسعه‌دهنده نرم‌افزار نِمُو (Nemov)</h2>
                <p class="section-subtitle">
                    راه‌های ارتباطی رسمی جهت مشاوره، پشتیبانی فنی و تجهیز باشگاه‌های ورزشی
                </p>
            </div>

            <div class="developer-card reveal-on-scroll">
                <div class="tilt-glare-overlay" aria-hidden="true"></div>
                <div class="developer-avatar-box">
                    <img src="/images/developer_photo.jpg" alt="مهندس ابوالفضل صمدی کوچکسرائی - توسعه‌دهنده نرم‌افزار مدیریت ورزشی نِمُو (Nemov)" class="developer-avatar-img" width="88" height="88" loading="lazy">
                </div>
                <h3 class="developer-name">مهندس ابوالفضل صمدی کوچکسرائی</h3>
                <span class="developer-role">توسعه‌دهنده و طراح نرم‌افزار | Software Developer & Architect</span>
                <p class="developer-bio">
                    دانشجوی رشته مهندسی کامپیوتر دانشگاه صنعتی نوشیروانی بابل
                </p>

                <div class="contact-links-grid">
                    <a href="mailto:support@nemovapp.ir" class="contact-btn contact-btn-email" aria-label="ارسال ایمیل به پشتیبانی رسمی نرم‌افزار نِمُو">
                        <span aria-hidden="true">📧</span>
                        <span>support@nemovapp.ir</span>
                    </a>
                    <a href="https://t.me/AqaSamadi" target="_blank" rel="noopener noreferrer" class="contact-btn contact-btn-telegram" aria-label="ارتباط در تلگرام با مهندس ابوالفضل صمدی (باز شدن در تب جدید)">
                        <span aria-hidden="true">✈️</span>
                        <span>Telegram: @AqaSamadi</span>
                    </a>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer (Strictly No Admin Login Link) -->
    <footer class="footer" role="contentinfo">
        <div class="footer-content">
            <div class="footer-brand">نرم‌افزار مدیریت ورزشی نِمُو • Nemov</div>
            <p class="footer-copy">
                تمامی حقوق مادی و معنوی این وب‌سایت و سامانه مدیریت ورزشی نِمُو محفوظ است © ۲۰۲۶ • توسعه‌دهنده: مهندس ابوالفضل صمدی کوچکسرائی
            </p>
        </div>
    </footer>
    <!-- Interactive Enhancements: ScrollTrigger / Reveal, 3D Tilt & Progress -->
    <script>
        (function() {
            // 1. Scroll Progress Bar
            var progressBar = document.getElementById('scroll-progress-bar');
            if (progressBar) {
                window.addEventListener('scroll', function() {
                    var docH = document.documentElement.scrollHeight - window.innerHeight;
                    var scrolled = docH > 0 ? (window.scrollY / docH) * 100 : 0;
                    progressBar.style.width = scrolled + '%';
                }, { passive: true });
            }

            // 2. ScrollTrigger / Reveal Animations with Intelligent Below-Fold Logic
            var revealElements = document.querySelectorAll('.reveal-on-scroll');
            var vh = window.innerHeight || document.documentElement.clientHeight || 800;

            // Only elements below the fold start hidden
            revealElements.forEach(function(el) {
                var rect = el.getBoundingClientRect();
                if (rect.top > vh * 0.92) {
                    el.classList.add('reveal-pending');
                }
            });

            if ('IntersectionObserver' in window) {
                var observer = new IntersectionObserver(function(entries, obs) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('revealed');
                            obs.unobserve(entry.target);
                        }
                    });
                }, {
                    threshold: 0.05,
                    rootMargin: '0px 0px 40px 0px'
                });
                revealElements.forEach(function(el) { observer.observe(el); });
            } else {
                // Fallback for legacy browsers lacking IntersectionObserver
                var ticking = false;
                function checkScrollReveals() {
                    var currentVh = window.innerHeight || document.documentElement.clientHeight || 800;
                    document.querySelectorAll('.reveal-pending:not(.revealed)').forEach(function(el) {
                        var rect = el.getBoundingClientRect();
                        if (rect.top <= currentVh * 0.95 && rect.bottom >= 0) {
                            el.classList.add('revealed');
                        }
                    });
                }
                function onScrollCheck() {
                    if (!ticking) {
                        requestAnimationFrame(function() {
                            checkScrollReveals();
                            ticking = false;
                        });
                        ticking = true;
                    }
                }
                window.addEventListener('scroll', onScrollCheck, { passive: true });
                window.addEventListener('resize', onScrollCheck, { passive: true });
            }

            // 3. 3D Tilt Effect strictly for Desktop Fine-Pointer Devices (Bypassed entirely on touch/mobile)
            var isDesktopFinePointer = false;
            try {
                isDesktopFinePointer = window.matchMedia && 
                                       window.matchMedia('(hover: hover) and (pointer: fine)').matches &&
                                       !('ontouchstart' in window) &&
                                       navigator.maxTouchPoints <= 1;
            } catch(e) {
                isDesktopFinePointer = false;
            }

            if (isDesktopFinePointer) {
                var tiltCards = document.querySelectorAll('.feature-card, .highlight-card, .gym-card, .gym-join-card, .security-card, .developer-card');
                tiltCards.forEach(function(card) {
                    card.classList.add('tilt-enabled');
                    var rafId = null;
                    card.addEventListener('mousemove', function(e) {
                        if (rafId) cancelAnimationFrame(rafId);
                        rafId = requestAnimationFrame(function() {
                            var rect = card.getBoundingClientRect();
                            var x = e.clientX - rect.left;
                            var y = e.clientY - rect.top;
                            var centerX = rect.width / 2;
                            var centerY = rect.height / 2;
                            var rotateX = ((y - centerY) / centerY) * -6;
                            var rotateY = ((x - centerX) / centerX) * 6;

                            card.style.transform = 'perspective(1000px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) translateY(-5px)';
                            card.style.setProperty('--mouse-x', ((x / rect.width) * 100) + '%');
                            card.style.setProperty('--mouse-y', ((y / rect.height) * 100) + '%');
                        });
                    }, { passive: true });
                    card.addEventListener('mouseleave', function() {
                        if (rafId) cancelAnimationFrame(rafId);
                        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)';
                    });
                });
            }
        })();
    </script>
</body>
</html>`;
}

function renderLoginPage(error = null) {
    const errorHtml = error ? `<div class="error-alert">${escapeHtml(error)}</div>` : '';
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به سرور ابری کلودفلر یلدا</title>
    <style>
        ${SHARED_FONT_CSS}
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0F0F0F;
            color: #FFFFFF;
            font-family: var(--font-body);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
            overflow-x: hidden;
        }
        .card {
            background-color: #1A1A1A;
            border: 1px solid #2D2D2D;
            border-top: 4px solid #8B0000;
            border-radius: 14px;
            width: 100%;
            max-width: 400px;
            padding: 36px 28px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.6);
        }
        .logo-box { text-align: center; margin-bottom: 24px; }
        .logo-box h1 { font-family: var(--font-heading); font-size: 21px; font-weight: 800; color: #FFFFFF; margin-bottom: 6px; }
        .logo-box p { font-size: 13px; color: #9CA3AF; }
        .input-group { margin-bottom: 18px; }
        .input-group label { display: block; font-size: 13px; font-weight: bold; color: #D1D5DB; margin-bottom: 8px; }
        .input-group input {
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
        }
        .input-group input:focus { border-color: #8B0000; }
        .btn-submit {
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
            touch-action: manipulation;
        }
        .btn-submit:hover { background-color: #A91D22; }
        .btn-submit:active { transform: scale(0.98); }
        .error-alert { background-color: rgba(220, 38, 38, 0.15); border: 1px solid #DC2626; color: #F87171; padding: 12px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 20px; text-align: center; }
        @media (max-width: 480px) {
            .card {
                padding: 26px 18px;
                border-radius: 12px;
            }
            .logo-box h1 {
                font-size: 19px;
            }
            .input-group input {
                font-size: 16px;
            }
        }
        @media (max-width: 360px) {
            body {
                padding: 10px;
            }
            .card {
                padding: 20px 14px;
                border-radius: 10px;
            }
            .logo-box h1 {
                font-size: 17px;
            }
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-box">
            <h1>☁️ سرور ابری کلودفلر یلدا</h1>
            <p>ورود مدیر کل به سامانه مانیتورینگ دیتابیس‌ها</p>
        </div>
        ${errorHtml}
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
</html>`;
}

function renderDashboardPage(trainers, totalSizeMb, lastActivity, mediaList = [], totalMediaSizeMb = "0", defaultTab = "backups", originUrl = "", smsList = [], totalSmsRemaining = 0, totalSmsSent = 0, smsLogs = []) {
    const trainerRowsHtml = trainers.length > 0 ? trainers.map((t, idx) => `
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">${idx + 1}</td>
            <td class="name-cell">${escapeHtml(t.trainer_name || "مربی ناشناس")}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #9CA3AF;">${escapeHtml(t.phone)}</td>
            <td><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(t.last_backup_shamsi || "-")}</span></td>
            <td style="color: #60A5FA; font-weight: bold;"><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(t.file_size_mb || 0)} MB</span></td>
            <td>
                <div class="actions-group">
                    <a href="/api/backup/download/${encodeURIComponent(t.phone)}" class="btn-action btn-download" title="دریافت فایل SQLite دیتابیس مربی">
                        📥 دانلود دیتابیس
                    </a>
                    <button type="button" class="btn-action" style="background: #10B981; color: #FFF;" onclick="quickFillRecharge('${escapeJs(t.phone)}', '${escapeJs(t.trainer_name || '')}')" title="شارژ سریع بسته پیامک برای این مربی">
                        ⚡ شارژ پیامک
                    </button>
                    <form action="/api/backup/delete/${encodeURIComponent(t.phone)}" method="POST" style="display: inline;" onsubmit="return confirm('آیا از حذف دیتابیس مربی \\'${escapeJs(t.trainer_name || t.phone)}\\' از سرور اطمینان دارید؟');">
                        <button type="submit" class="btn-action btn-delete" title="حذف این نسخه پشتیبان از سرور">🗑️</button>
                    </form>
                </div>
            </td>
        </tr>
    `).join("") : '';

    const mediaRowsHtml = mediaList.length > 0 ? mediaList.map((m, idx) => {
        const isVid = m.type === "video";
        const typeBadge = isVid 
            ? `<span class="badge-type badge-video">🎬 ویدیو</span>` 
            : `<span class="badge-type badge-image">🖼️ تصویر</span>`;
        
        let playBtn = '';
        if (isVid) {
            playBtn = `<a href="/video/${encodeURIComponent(m.filename)}" target="_blank" class="btn-action btn-play">▶️ پخش ویدیو</a>`;
        } else {
            playBtn = `<a href="/image/${encodeURIComponent(m.filename)}" target="_blank" class="btn-action btn-play">🔍 نمایش تصویر</a>`;
        }

        return `
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">${idx + 1}</td>
            <td>${typeBadge}</td>
            <td class="name-cell" style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(m.filename)}"><span dir="auto" style="unicode-bidi: isolate;">${escapeHtml(m.filename)}</span></td>
            <td class="filename-cell" style="direction: ltr; text-align: right; font-family: var(--font-latin); font-size: 11.5px; color: #9CA3AF; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(m.filename)}</span></td>
            <td style="color: #A78BFA; font-weight: bold;"><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(m.file_size_mb || 0)} MB</span></td>
            <td><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(m.upload_shamsi || "-")}</span></td>
            <td>
                <div class="actions-group">
                    ${playBtn}
                    <button type="button" class="btn-action btn-copy" onclick="copyMediaLink('${escapeJs(m.url)}')" title="کپی کردن لینک مستقیم برای ارسال به شاگرد یا مربی">
                        📋 کپی لینک
                    </button>
                    <form action="/api/media/delete" method="POST" style="display: inline;" onsubmit="return confirm('آیا از حذف کامل فایل رسانه \\'${escapeJs(m.filename)}\\' از سرور اطمینان دارید؟');">
                        <input type="hidden" name="filename" value="${escapeHtml(m.filename)}">
                        <input type="hidden" name="type" value="${escapeHtml(m.type)}">
                        <button type="submit" class="btn-action btn-delete">🗑️</button>
                    </form>
                </div>
            </td>
        </tr>
        `;
    }).join("") : '';

    const smsRowsHtml = smsList.length > 0 ? smsList.map((s, idx) => {
        const rem = s.remaining || 0;
        const totalCred = s.total_credited || 0;
        const used = s.total_used || 0;
        const isZero = rem === 0 && totalCred === 0;
        
        let statusBadge = '';
        if (isZero) {
            statusBadge = `<span class="badge-type" style="background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444;">غیرفعال / شارژ نشده</span>`;
        } else if (rem <= 10) {
            statusBadge = `<span class="badge-type" style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B;">رو به اتمام ⚠️</span>`;
        } else {
            statusBadge = `<span class="badge-type" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;">فعال و پر اعتبار ✅</span>`;
        }

        return `
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">${idx + 1}</td>
            <td class="name-cell">${escapeHtml(s.trainer_name || "مربی")}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #9CA3AF;">${escapeHtml(s.phone)}</td>
            <td style="color: ${rem > 0 ? '#10B981' : '#EF4444'}; font-weight: bold; font-size: 15px;">${rem.toLocaleString('fa-IR')} <span style="font-size: 11px; font-weight: normal; color: #A1A1AA;">پیامک</span></td>
            <td style="color: #60A5FA;">${totalCred.toLocaleString('fa-IR')}</td>
            <td style="color: #F87171;">${used.toLocaleString('fa-IR')}</td>
            <td style="font-size: 12px; color: #A1A1AA;"><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(s.last_recharge_shamsi || "-")}</span></td>
            <td>${statusBadge}</td>
            <td>
                <div class="actions-group">
                    <button type="button" class="btn-action" style="background: #10B981; color: #FFF;" onclick="quickFillRecharge('${escapeJs(s.phone)}', '${escapeJs(s.trainer_name || '')}')">
                        ➕ شارژ مجدد
                    </button>
                </div>
            </td>
        </tr>
        `;
    }).join("") : '';

    const smsLogsHtml = (Array.isArray(smsLogs) && smsLogs.length > 0) ? smsLogs.slice(0, 30).map((l, idx) => {
        let typeBadge = '';
        if (l.type === "registration") typeBadge = `<span class="badge-type" style="background: #1E3A8A; color: #93C5FD; border: 1px solid #2563EB;">ثبت‌نام شاگرد</span>`;
        else if (l.type === "expiration_reminder") typeBadge = `<span class="badge-type" style="background: #78350F; color: #FCD34D; border: 1px solid #D97706;">یادآوری تمدید</span>`;
        else if (l.type === "plan_assigned") typeBadge = `<span class="badge-type" style="background: #064E3B; color: #6EE7B7; border: 1px solid #059669;">برنامه تمرینی</span>`;
        else typeBadge = `<span class="badge-type" style="background: #374151; color: #D1D5DB;">عمومی</span>`;

        return `
        <tr>
            <td style="color: #A1A1AA; font-family: monospace;">${idx + 1}</td>
            <td class="name-cell">${escapeHtml(l.trainer_name || "مربی")}</td>
            <td>${typeBadge}</td>
            <td class="name-cell" style="font-weight: normal; color: #E4E4E7;">${escapeHtml(l.member_name || "-")}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #60A5FA;">${escapeHtml(l.recipient)}</td>
            <td style="font-size: 12px; color: #A1A1AA;"><span dir="ltr" style="unicode-bidi: isolate;">${escapeHtml(l.date_shamsi || "-")}</span></td>
            <td style="font-size: 11px; color: #10B981;">${escapeHtml(l.detail || "موفق")}</td>
        </tr>
        `;
    }).join("") : '';

    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مدیریت ابری و استودیوی رسانه - باشگاه یلدا</title>
    <style>
        ${SHARED_FONT_CSS}
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0F0F0F;
            color: #F3F4F6;
            font-family: var(--font-body);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }
        header {
            background-color: #18181B;
            border-bottom: 1px solid #27272A;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .brand h1 {
            font-family: var(--font-heading);
            font-size: 17px;
            font-weight: 800;
            color: #FFFFFF;
        }
        .badge-live {
            background-color: rgba(245, 158, 11, 0.15);
            color: #F59E0B;
            border: 1px solid #F59E0B;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: bold;
            font-family: var(--font-heading);
        }
        .btn-logout {
            background-color: #27272A;
            color: #EF4444;
            border: 1px solid #3F3F46;
            padding: 8px 16px;
            min-height: 40px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 13px;
            font-weight: bold;
            font-family: var(--font-heading);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
            white-space: nowrap;
        }
        .btn-logout:hover { background-color: #DC2626; color: #FFFFFF; }
        
        .container {
            max-width: 1240px;
            width: 100%;
            margin: 0 auto;
            padding: 20px 16px;
            flex: 1;
            box-sizing: border-box;
        }
        
        /* Tabs Navigation - Smooth horizontal touch scrolling */
        .tabs-nav {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            border-bottom: 2px solid #27272A;
            padding-bottom: 12px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            white-space: nowrap;
            scrollbar-width: thin;
        }
        .tabs-nav::-webkit-scrollbar {
            height: 4px;
        }
        .tabs-nav::-webkit-scrollbar-thumb {
            background: #3F3F46;
            border-radius: 4px;
        }
        .tab-btn {
            background-color: #18181B;
            color: #A1A1AA;
            border: 1px solid #27272A;
            padding: 10px 18px;
            min-height: 44px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13.5px;
            font-weight: bold;
            font-family: var(--font-heading);
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            flex-shrink: 0;
            touch-action: manipulation;
        }
        .tab-btn:hover { background-color: #27272A; color: #FFFFFF; }
        .tab-btn.active {
            background-color: #8B0000;
            color: #FFFFFF;
            border-color: #8B0000;
            box-shadow: 0 4px 12px rgba(139, 0, 0, 0.35);
        }
        .tab-panel { display: none; }
        .tab-panel.active { display: block; }

        /* Stats Grid - Responsive 1 to 3 columns */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background-color: #18181B;
            border: 1px solid #27272A;
            border-radius: 12px;
            padding: 18px;
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .stat-icon {
            width: 48px;
            height: 48px;
            flex-shrink: 0;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }
        .icon-red { background-color: rgba(139, 0, 0, 0.2); color: #EF4444; border: 1px solid #8B0000; }
        .icon-blue { background-color: rgba(37, 99, 235, 0.2); color: #60A5FA; border: 1px solid #2563EB; }
        .icon-green { background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #10B981; }
        .icon-purple { background-color: rgba(139, 92, 246, 0.2); color: #A78BFA; border: 1px solid #8B5CF6; }
        .stat-info h3 {
            font-family: var(--font-heading);
            font-size: 20px;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 2px;
        }
        .stat-info p {
            font-size: 12px;
            color: #A1A1AA;
        }
        
        /* Tables & Cards */
        .table-card {
            background-color: #18181B;
            border: 1px solid #27272A;
            border-radius: 12px;
            overflow: hidden;
        }
        .table-header {
            padding: 14px 18px;
            border-bottom: 1px solid #27272A;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        .table-header h2 {
            font-family: var(--font-heading);
            font-size: 15px;
            font-weight: bold;
            color: #FFFFFF;
        }
        .search-input {
            background-color: #27272A;
            border: 1px solid #3F3F46;
            color: #FFFFFF;
            padding: 8px 14px;
            min-height: 38px;
            border-radius: 8px;
            font-size: 13px;
            font-family: var(--font-body);
            width: 260px;
            max-width: 100%;
            outline: none;
            transition: border-color 0.2s;
            box-sizing: border-box;
        }
        .search-input:focus { border-color: #8B0000; }
        
        /* Responsive Table Container with Smooth Scrolling */
        .table-responsive {
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        .table-responsive::-webkit-scrollbar {
            height: 6px;
        }
        .table-responsive::-webkit-scrollbar-thumb {
            background: #3F3F46;
            border-radius: 4px;
        }
        table {
            width: 100%;
            min-width: 620px;
            border-collapse: collapse;
            text-align: right;
            font-size: 13px;
        }
        th {
            background-color: #202024;
            color: #A1A1AA;
            padding: 12px 16px;
            font-weight: bold;
            border-bottom: 1px solid #27272A;
            white-space: nowrap;
            font-family: var(--font-heading);
        }
        td {
            padding: 12px 16px;
            border-bottom: 1px solid #27272A;
            color: #E4E4E7;
            vertical-align: middle;
            font-family: var(--font-body);
        }
        .name-cell {
            font-family: 'B Koodak', Cambria, Georgia, serif !important;
            font-weight: bold;
            color: #FFFFFF;
        }
        .filename-cell {
            font-family: var(--font-latin) !important;
        }
        tr:hover td { background-color: #202024; }
        
        .badge-type {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
            font-family: var(--font-heading);
        }
        .badge-video { background-color: #1E1B4B; color: #A5B4FC; border: 1px solid #4338CA; }
        .badge-image { background-color: #064E3B; color: #6EE7B7; border: 1px solid #059669; }

        .actions-group {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
            flex-wrap: nowrap;
        }
        .btn-action {
            white-space: nowrap;
            flex-shrink: 0;
            min-height: 36px;
            padding: 6px 12px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            font-size: 12px;
            font-family: var(--font-heading);
            display: inline-flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            border: none;
            transition: background 0.2s, transform 0.1s;
            touch-action: manipulation;
        }
        .btn-action:active { transform: scale(0.96); }
        .btn-download { background-color: #2563EB; color: #FFFFFF; }
        .btn-download:hover { background-color: #1D4ED8; }
        .btn-play { background-color: #059669; color: #FFFFFF; min-width: 100px; justify-content: center; }
        .btn-play:hover { background-color: #047857; }
        .btn-copy { background-color: #6366F1; color: #FFFFFF; min-width: 80px; justify-content: center; }
        .btn-copy:hover { background-color: #4F46E5; }
        .btn-delete { background-color: #DC2626 !important; color: #FFFFFF !important; border: 1px solid #B91C1C; min-width: 54px; justify-content: center; }
        .btn-delete:hover { background-color: #B91C1C !important; border-color: #991B1B; color: #FFFFFF !important; }
        
        .empty-state { padding: 45px 20px; text-align: center; color: #71717A; }
        footer { text-align: center; padding: 20px 16px; font-size: 12px; color: #71717A; border-top: 1px solid #27272A; line-height: 1.6; }
        
        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #10B981;
            color: #FFFFFF;
            padding: 12px 22px;
            border-radius: 8px;
            font-size: 13.5px;
            font-weight: bold;
            font-family: var(--font-heading);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            z-index: 9999;
            display: none;
            max-width: 90vw;
            text-align: center;
        }
        .toast.show { display: block; animation: fadeInOut 3s forwards; }
        @keyframes fadeInOut {
            0% { opacity: 0; bottom: 10px; }
            15% { opacity: 1; bottom: 24px; }
            85% { opacity: 1; bottom: 24px; }
            100% { opacity: 0; bottom: 10px; }
        }

        /* Responsive Media Queries */
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
            }
            .stat-card {
                padding: 14px;
            }
            .stat-icon {
                width: 42px;
                height: 42px;
                font-size: 18px;
            }
            .stat-info h3 {
                font-size: 17px;
            }
        }
        @media (max-width: 640px) {
            header {
                padding: 12px 16px;
            }
            .table-header {
                flex-direction: column;
                align-items: stretch;
            }
            .search-input {
                width: 100%;
                font-size: 16px !important;
            }
            .recharge-form {
                flex-direction: column;
                align-items: stretch !important;
            }
            .recharge-field, .recharge-quick-amounts {
                width: 100% !important;
                min-width: 100% !important;
            }
            .recharge-field input {
                font-size: 16px !important;
            }
        }
        @media (max-width: 480px) {
            .stats-grid {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            .brand h1 {
                font-size: 15px;
                word-break: break-word;
                overflow-wrap: anywhere;
            }
            .container {
                padding: 14px 10px;
            }
            .table-card {
                padding: 14px 12px !important;
            }
            .quick-buttons-row {
                display: grid !important;
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 6px !important;
            }
            .btn-logout {
                width: 100%;
                text-align: center;
                min-height: 44px;
            }
        }
        @media (max-width: 360px) {
            .brand h1 {
                font-size: 13.5px;
            }
            .container {
                padding: 10px 6px;
            }
            .table-card {
                padding: 10px 8px !important;
            }
            .tab-btn {
                padding: 8px 12px;
                font-size: 12px;
                min-height: 40px;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <h1>☁️ سرور ابری کلودفلر باشگاه یلدا (Cloudflare Serverless)</h1>
            <span class="badge-live">ورکر آنلاین ⚡</span>
        </div>
        <a href="/logout" class="btn-logout">خروج از پنل</a>
    </header>

    <div class="container">
        <!-- Tab Navigation -->
        <div class="tabs-nav">
            <button id="btnTabBackups" class="tab-btn ${defaultTab === 'backups' ? 'active' : ''}" onclick="switchTab('backups')">
                💾 پایگاه‌داده‌ها و بکاپ‌ها (${trainers.length})
            </button>
            <button id="btnTabMedia" class="tab-btn ${defaultTab === 'media' ? 'active' : ''}" onclick="switchTab('media')">
                🎬 بانک رسانه‌ها و ویدیوهای حرکات (${mediaList.length})
            </button>
            <button id="btnTabMessages" class="tab-btn ${defaultTab === 'messages' ? 'active' : ''}" onclick="switchTab('messages')">
                📱 مدیریت بسته‌های پیامکی (${smsList.length})
            </button>
        </div>

        <!-- Tab Panel 1: Backups -->
        <div id="panelBackups" class="tab-panel ${defaultTab === 'backups' ? 'active' : ''}">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon icon-red">👥</div>
                    <div class="stat-info">
                        <h3>${trainers.length}</h3>
                        <p>مربیان دارای نسخه پشتیبان</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon icon-blue">💾</div>
                    <div class="stat-info">
                        <h3>${totalSizeMb} MB</h3>
                        <p>مجموع حجم دیتابیس‌ها در کلودفلر</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon icon-green">⏱️</div>
                    <div class="stat-info">
                        <h3 style="font-size: 16px;">${lastActivity}</h3>
                        <p>آخرین فعالیت پشتیبان‌گیری</p>
                    </div>
                </div>
            </div>

            <div class="table-card">
                <div class="table-header">
                    <h2>📋 لیست پایگاه‌داده‌های مربیان (Cloudflare R2 Storage)</h2>
                    <input type="text" id="searchBackupsInput" class="search-input" placeholder="🔍 جستجو بر اساس نام یا شماره..." onkeyup="filterTable('trainersTable', 'searchBackupsInput', [1, 2])">
                </div>

                ${trainers.length > 0 ? `
                <div class="table-responsive">
                    <table id="trainersTable">
                        <thead>
                            <tr>
                                <th>ردیف</th>
                                <th>نام مربی</th>
                                <th>شماره تماس (شناسه)</th>
                                <th>تاریخ آخرین پشتیبان‌گیری</th>
                                <th>حجم دیتابیس</th>
                                <th>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${trainerRowsHtml}
                        </tbody>
                    </table>
                </div>
                ` : `
                <div class="empty-state">
                    <p style="font-size: 16px; margin-bottom: 6px;">هنوز هیچ نسخه پشتیبانی در سرور ابری کلودفلر ثبت نشده است.</p>
                    <p style="font-size: 13px;">به محض اینکه مربیان از طریق نرم‌افزار گزینه «ذخیره در سرور» را انتخاب کنند، اطلاعات آنها در اینجا ظاهر می‌شود.</p>
                </div>
                `}
            </div>
        </div>

        <!-- Tab Panel 2: Media Studio -->
        <div id="panelMedia" class="tab-panel ${defaultTab === 'media' ? 'active' : ''}">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon icon-purple">🎬</div>
                    <div class="stat-info">
                        <h3>${mediaList.length}</h3>
                        <p>تعداد کل ویدیوها و تصاویر</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon icon-blue">📦</div>
                    <div class="stat-info">
                        <h3>${totalMediaSizeMb} MB</h3>
                        <p>مجموع حجم رسانه‌ها در کلودفلر</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon icon-green">⏱️</div>
                    <div class="stat-info">
                        <h3 style="font-size: 15px;">${mediaList.length > 0 ? mediaList[0].upload_shamsi : "هنوز رسانه‌ای آپلود نشده"}</h3>
                        <p>آخرین آپلود رسانه حرکات</p>
                    </div>
                </div>
            </div>

            <div class="table-card">
                <div class="table-header">
                    <h2>🎬 بانک ویدیوها و تصاویر آموزشی حرکات ورزشی</h2>
                    <input type="text" id="searchMediaInput" class="search-input" placeholder="🔍 جستجو بر اساس نام حرکت یا فایل..." onkeyup="filterTable('mediaTable', 'searchMediaInput', [2, 3])">
                </div>

                ${mediaList.length > 0 ? `
                <div class="table-responsive">
                    <table id="mediaTable">
                        <thead>
                            <tr>
                                <th>ردیف</th>
                                <th>نوع رسانه</th>
                                <th>نام حرکت / عنوان</th>
                                <th>نام فایل</th>
                                <th>حجم</th>
                                <th>تاریخ آپلود</th>
                                <th>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${mediaRowsHtml}
                        </tbody>
                    </table>
                </div>
                ` : `
                <div class="empty-state">
                    <p style="font-size: 16px; margin-bottom: 6px;">هنوز هیچ ویدیو یا تصویری در سرور آپلود نشده است.</p>
                    <p style="font-size: 13px;">با ضبط یا آپلود ویدیوی تمرینات در نرم‌افزار یلدا، فایل‌ها به صورت خودکار در این استودیو قرار می‌گیرند.</p>
                </div>
                `}
            </div>
        </div>

        <!-- Tab Panel 3: SMS Packages Management -->
        <div id="panelMessages" class="tab-panel ${defaultTab === 'messages' ? 'active' : ''}">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon icon-green">👥</div>
                    <div class="stat-info">
                        <h3>${smsList.length} نفر</h3>
                        <p>مربیان فعال در سامانه پیامک</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon icon-blue">📩</div>
                    <div class="stat-info">
                        <h3>${totalSmsRemaining.toLocaleString('fa-IR')} عدد</h3>
                        <p>مجموع اعتبار باقیمانده پیامک‌ها</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon icon-purple">📤</div>
                    <div class="stat-info">
                        <h3>${totalSmsSent.toLocaleString('fa-IR')} پیامک</h3>
                        <p>کل پیامک‌های ارسال‌شده به شاگردان</p>
                    </div>
                </div>
            </div>

            <!-- Quick Recharge Card -->
            <div class="table-card" style="margin-bottom: 24px; padding: 20px;">
                <h2 style="font-family: var(--font-heading); font-size: 16px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    ⚡ شارژ آنلاین و فعال‌سازی بسته پیامک برای مربی
                </h2>
                <p style="font-size: 13px; color: #A1A1AA; margin-bottom: 18px;">
                    پس از واریز کارت‌به‌کارت مربی، شماره موبایل و تعداد پیامک مورد نظر را تعیین و دکمه شارژ را بزنید. اعتبار بلافاصله در نرم‌افزار دسکتاپ مربی اعمال خواهد شد.
                </p>

                <form action="/api/admin/sms/recharge" method="POST" class="recharge-form" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end;">
                    <div class="recharge-field" style="flex: 1 1 160px; min-width: 140px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB; white-space: nowrap;">شماره موبایل مربی (شناسه)</label>
                        <input type="text" id="rechargePhone" name="phone" required placeholder="مثال: 09123456789" style="width: 100%; height: 44px; padding: 0 12px; background: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; font-size: 13px; direction: ltr; box-sizing: border-box;">
                    </div>
                    <div class="recharge-field" style="flex: 1 1 150px; min-width: 140px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB; white-space: nowrap;">نام مربی</label>
                        <input type="text" id="rechargeName" name="trainer_name" placeholder="نام مربی (اختیاری)" style="width: 100%; height: 44px; padding: 0 12px; background: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; font-size: 13px; box-sizing: border-box;">
                    </div>
                    <div class="recharge-field" style="flex: 0.8 1 120px; min-width: 110px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB; white-space: nowrap;">تعداد پیامک بسته</label>
                        <input type="number" id="rechargeAmount" name="amount" min="1" value="100" required style="width: 100%; height: 44px; padding: 0 10px; background: #27272A; border: 1px solid #3F3F46; border-radius: 6px; color: #FFFFFF; font-size: 13px; text-align: center; direction: ltr; box-sizing: border-box;">
                    </div>
                    <div class="recharge-quick-amounts" style="flex: 1.5 1 260px; min-width: 220px;">
                        <label style="display: block; font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #D1D5DB; white-space: nowrap;">بسته‌های سریع</label>
                        <div class="quick-buttons-row" style="display: flex; gap: 6px; width: 100%;">
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; padding: 0 6px; font-size: 12px; font-weight: bold; justify-content: center; white-space: nowrap; box-sizing: border-box;" onclick="setAmount(100)">۱۰۰ تایی</button>
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; padding: 0 6px; font-size: 12px; font-weight: bold; justify-content: center; white-space: nowrap; box-sizing: border-box;" onclick="setAmount(250)">۲۵۰ تایی</button>
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; padding: 0 6px; font-size: 12px; font-weight: bold; justify-content: center; white-space: nowrap; box-sizing: border-box;" onclick="setAmount(500)">۵۰۰ تایی</button>
                            <button type="button" class="btn-action" style="background: #3F3F46; color: #FFF; flex: 1; height: 44px; padding: 0 6px; font-size: 12px; font-weight: bold; justify-content: center; white-space: nowrap; box-sizing: border-box;" onclick="setAmount(1000)">۱۰۰۰ تایی</button>
                        </div>
                    </div>
                    <div class="recharge-field" style="flex: 1 1 160px; min-width: 150px;">
                        <button type="submit" class="btn-action" style="background: #10B981; color: #FFFFFF; height: 44px; width: 100%; padding: 0 16px; font-size: 13px; justify-content: center; font-weight: bold; cursor: pointer; white-space: nowrap; box-sizing: border-box;">
                            🚀 ثبت و شارژ حساب مربی
                        </button>
                    </div>
                </form>
            </div>

            <!-- Coaches Table -->
            <div class="table-card" style="margin-bottom: 24px;">
                <div class="table-header">
                    <h2>📋 لیست مربیان و وضعیت اعتبار پیامک‌ها</h2>
                    <input type="text" id="searchSmsInput" class="search-input" placeholder="🔍 جستجو بر اساس نام یا شماره مربی..." onkeyup="filterTable('smsTable', 'searchSmsInput', [1, 2])">
                </div>

                ${smsList.length > 0 ? `
                <div class="table-responsive">
                    <table id="smsTable">
                        <thead>
                            <tr>
                                <th>ردیف</th>
                                <th>نام مربی</th>
                                <th>شماره تماس</th>
                                <th>اعتبار باقیمانده</th>
                                <th>کل شارژشده</th>
                                <th>تعداد مصرفی</th>
                                <th>آخرین تاریخ شارژ</th>
                                <th>وضعیت</th>
                                <th>عملیات</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${smsRowsHtml}
                        </tbody>
                    </table>
                </div>
                ` : `
                <div class="empty-state">
                    <p style="font-size: 16px; margin-bottom: 6px;">هنوز هیچ مربی در سامانه پیامکی شارژ نشده است.</p>
                    <p style="font-size: 13px;">از طریق کادر بالا می‌توانید اولین بسته پیامکی را برای مربیان شارژ و فعال نمایید.</p>
                </div>
                `}
            </div>

            <!-- SMS Send Logs Table -->
            <div class="table-card">
                <div class="table-header">
                    <h2>📤 گزارش آخرین پیامک‌های ارسالی مربیان به شاگردان</h2>
                </div>

                ${smsLogs.length > 0 ? `
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>ردیف</th>
                                <th>مربی فرستنده</th>
                                <th>نوع پیامک</th>
                                <th>نام شاگرد</th>
                                <th>شماره دریافت‌کننده</th>
                                <th>تاریخ و ساعت</th>
                                <th>وضعیت ارسال</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${smsLogsHtml}
                        </tbody>
                    </table>
                </div>
                ` : `
                <div class="empty-state">
                    <p style="font-size: 15px; margin-bottom: 4px;">هنوز هیچ پیامی توسط مربیان ارسال نشده است.</p>
                </div>
                `}
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <footer>
        توسعه داده شده برای سامانه هوشمند مدیریت باشگاه یلدا • قدرت گرفته از شبکه لبه ابری Cloudflare Workers © 2026
    </footer>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

            if (tab === 'media') {
                document.getElementById('btnTabMedia').classList.add('active');
                document.getElementById('panelMedia').classList.add('active');
            } else if (tab === 'messages') {
                document.getElementById('btnTabMessages').classList.add('active');
                document.getElementById('panelMessages').classList.add('active');
            } else {
                document.getElementById('btnTabBackups').classList.add('active');
                document.getElementById('panelBackups').classList.add('active');
            }
            if (window.history && window.history.replaceState) {
                history.replaceState(null, '', '?tab=' + tab);
            }
        }

        function setAmount(num) {
            document.getElementById('rechargeAmount').value = num;
        }

        function quickFillRecharge(phone, name) {
            document.getElementById('rechargePhone').value = phone;
            document.getElementById('rechargeName').value = name;
            switchTab('messages');
            document.getElementById('rechargeAmount').focus();
        }

        function copyMediaLink(url) {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(showToast);
            } else {
                var ta = document.createElement('textarea');
                ta.value = url;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast();
            }
        }

        function showToast() {
            var t = document.getElementById('toast');
            t.textContent = '✅ لینک مستقیم رسانه با موفقیت در کلیپ‌بورد کپی شد!';
            t.className = 'toast show';
            setTimeout(function() { t.className = 'toast'; }, 3000);
        }

        function filterTable(tableId, inputId, colIndices) {
            var input = document.getElementById(inputId);
            var filter = input.value.toLowerCase();
            var table = document.getElementById(tableId);
            if (!table) return;
            var tr = table.getElementsByTagName("tr");
            for (var i = 1; i < tr.length; i++) {
                var matched = false;
                for (var j = 0; j < colIndices.length; j++) {
                    var td = tr[i].getElementsByTagName("td")[colIndices[j]];
                    if (td) {
                        var text = td.textContent || td.innerText;
                        if (text.toLowerCase().indexOf(filter) > -1) {
                            matched = true;
                            break;
                        }
                    }
                }
                tr[i].style.display = matched ? "" : "none";
            }
        }
    </script>
</body>
</html>`;
}

function renderSandboxedVideoPlayer(title, videoStreamUrl) {
    const safeTitle = escapeHtml(title);
    const safeUrl = escapeHtml(videoStreamUrl);
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${safeTitle} | راهنمای اجرای حرکت</title>
    <style>
        ${SHARED_FONT_CSS}
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0d0d0d;
            color: #ffffff;
            font-family: var(--font-body);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
            overflow-x: hidden;
        }
        .player-container {
            width: 100%;
            max-width: 760px;
            background: #181818;
            border-radius: 16px;
            border: 1px solid #2a2a2a;
            box-shadow: 0 16px 40px rgba(0,0,0,0.8);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .player-header {
            padding: 14px 18px;
            background: linear-gradient(135deg, #1f1f1f, #141414);
            border-bottom: 1px solid #262626;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
        }
        .header-title-box h1 {
            font-family: var(--font-heading);
            font-size: 16px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 2px;
        }
        .header-title-box p {
            font-size: 11.5px;
            color: #9e9e9e;
        }
        .gym-badge {
            background-color: #8B0000;
            color: #ffffff;
            font-family: var(--font-heading);
            font-size: 11px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 20px;
            letter-spacing: 0.3px;
            white-space: nowrap;
        }
        .video-box {
            position: relative;
            width: 100%;
            background-color: #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            overflow: hidden;
            min-height: 320px;
        }
        video {
            width: 100%;
            height: auto;
            max-height: 75vh;
            min-height: 280px;
            display: block;
            outline: none;
            background-color: #000;
            object-fit: contain;
        }
        .play-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 68px;
            height: 68px;
            background: rgba(139, 0, 0, 0.88);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
            opacity: 0;
            z-index: 5;
        }
        .play-overlay.show {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        .play-overlay svg {
            width: 32px;
            height: 32px;
            fill: #ffffff;
            margin-left: 3px;
        }
        .error-message {
            display: none;
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(15, 15, 15, 0.95);
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
            text-align: center;
            z-index: 10;
        }
        .error-message.show {
            display: flex;
        }
        .error-icon {
            font-size: 40px;
            margin-bottom: 12px;
        }
        .error-text {
            color: #f87171;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .error-sub {
            color: #888888;
            font-size: 12px;
            max-width: 320px;
            line-height: 1.5;
        }
        .player-footer {
            padding: 12px 18px;
            background: #141414;
            border-top: 1px solid #242424;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 12px;
            color: #777777;
        }
        .player-footer span {
            color: #A91D22;
            font-weight: bold;
        }
        .download-link {
            font-size: 11.5px;
            color: #60a5fa;
            text-decoration: none;
        }
        .download-link:hover {
            text-decoration: underline;
        }
        @media (max-width: 640px) {
            body { padding: 6px 4px; justify-content: center; }
            .player-container {
                width: 100%;
                max-width: 100%;
                border-radius: 12px;
                border: 1px solid #262626;
            }
            .player-header { padding: 10px 14px; }
            .header-title-box h1 { font-size: 15px; }
            .header-title-box p { font-size: 11px; }
            .gym-badge { font-size: 10px; padding: 3px 8px; }
            .video-box {
                min-height: 360px;
                max-height: 78vh;
            }
            video {
                width: 100%;
                height: auto;
                max-height: 78vh;
                min-height: 300px;
            }
            .play-overlay { width: 60px; height: 60px; }
            .play-overlay svg { width: 28px; height: 28px; }
            .player-footer { padding: 10px 14px; font-size: 11.5px; }
        }
    </style>
</head>
<body>
    <div class="player-container">
        <div class="player-header">
            <div class="header-title-box">
                <h1>🎬 ${safeTitle}</h1>
                <p>پخش اختصاصی حرکت بدنسازی</p>
            </div>
            <div class="gym-badge">باشگاه یلدا</div>
        </div>
        <div class="video-box" id="videoBox">
            <video id="gymVideo" playsinline preload="metadata" loop>
                <source src="${safeUrl}" type="video/mp4">
                مرورگر شما از پخش مستقیم ویدیو پشتیبانی نمی‌کند.
            </video>
            <div class="play-overlay" id="playOverlay">
                <svg viewBox="0 0 24 24">
                    <polygon points="5,3 19,12 5,21"></polygon>
                </svg>
            </div>
            <div class="error-message" id="errorMessage">
                <div class="error-icon">⚠️</div>
                <div class="error-text">خطا در بارگذاری یا پخش ویدیو</div>
                <div class="error-sub">فایل ویدیویی در سرور کلودفلر پردازش نشده یا اتصال اینترنت پایدار نیست.</div>
            </div>
        </div>
        <div class="player-footer">
            <div>طراحی شده برای ورزشکاران • <span>باشگاه یلدا</span></div>
            <a class="download-link" href="${safeUrl}" download>دانلود فایل ویدیو 📥</a>
        </div>
    </div>

    <script>
        const video = document.getElementById('gymVideo');
        video.loop = true;
        const box = document.getElementById('videoBox');
        const overlay = document.getElementById('playOverlay');
        const err = document.getElementById('errorMessage');

        function updateOverlay() {
            if (video.paused || video.ended) {
                overlay.classList.add('show');
            } else {
                overlay.classList.remove('show');
            }
        }

        box.addEventListener('click', (e) => {
            if (e.target.closest('.error-message')) return;
            if (video.paused) {
                video.play().catch(e => {
                    console.error("Autoplay prevent:", e);
                    updateOverlay();
                });
            } else {
                video.pause();
            }
        });

        video.addEventListener('play', updateOverlay);
        video.addEventListener('pause', updateOverlay);
        video.addEventListener('ended', () => {
            video.currentTime = 0;
            video.play().catch(() => updateOverlay());
        });

        video.addEventListener('error', (e) => {
            console.error("Video load error", e);
            err.classList.add('show');
            overlay.classList.remove('show');
        });

        window.addEventListener('DOMContentLoaded', () => {
            updateOverlay();
            video.play().catch(() => updateOverlay());
        });
    </script>
</body>
</html>`;
}

function renderSandboxedImageViewer(title, imageUrl) {
    const safeTitle = escapeHtml(title);
    const safeUrl = escapeHtml(imageUrl);
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${safeTitle} | باشگاه بدنسازی یلدا</title>
    <style>
        ${SHARED_FONT_CSS}
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0d0d0d;
            color: #ffffff;
            font-family: var(--font-body);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
            overflow-x: hidden;
        }
        .viewer-container {
            width: 100%;
            max-width: 680px;
            background: #181818;
            border: 1px solid #282828;
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
            display: flex;
            flex-direction: column;
        }
        .viewer-header {
            padding: 14px 18px;
            background: #141414;
            border-bottom: 1px solid #242424;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
        }
        .header-title-box h1 {
            font-family: var(--font-heading);
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 2px;
        }
        .header-title-box p {
            font-size: 12px;
            color: #888888;
        }
        .gym-badge {
            background: #8B0000;
            color: #ffffff;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            font-family: var(--font-heading);
            white-space: nowrap;
        }
        .image-box {
            position: relative;
            background: #0F0F0F;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 250px;
            max-height: 75vh;
            overflow: hidden;
            padding: 10px;
        }
        .image-box img {
            max-width: 100%;
            height: auto;
            max-height: 72vh;
            object-fit: contain;
            display: block;
            border-radius: 8px;
        }
        .viewer-footer {
            padding: 12px 18px;
            background: #141414;
            border-top: 1px solid #242424;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 12px;
            color: #777777;
        }
        .viewer-footer span {
            color: #A91D22;
            font-weight: bold;
        }
        .download-link {
            font-size: 11.5px;
            color: #60a5fa;
            text-decoration: none;
        }
        .download-link:hover {
            text-decoration: underline;
        }
        @media (max-width: 480px) {
            body { padding: 10px; }
            .viewer-header { padding: 12px 14px; }
            .header-title-box h1 { font-size: 15px; }
        }
    </style>
</head>
<body>
    <div class="viewer-container">
        <div class="viewer-header">
            <div class="header-title-box">
                <h1>🖼️ ${safeTitle}</h1>
                <p>تصویر و الگوی حرکتی ورزشکار</p>
            </div>
            <div class="gym-badge">باشگاه بدنسازی یلدا</div>
        </div>
        <div class="image-box">
            <img src="${safeUrl}" alt="${safeTitle}" loading="lazy" />
        </div>
        <div class="viewer-footer">
            <div>برنامه تمرینی اختصاصی • <span>سامانه هوشمند یلدا</span></div>
            <a class="download-link" href="${safeUrl}" target="_blank" download>دریافت تصویر باکیفیت اصلی 📥</a>
        </div>
    </div>
</body>
</html>`;
}

function renderIsolatedNotFoundPage(title = "رسانه یافت نشد", msg = "فایل درخواستی در مخزن سرور موجود نیست یا حذف شده است.") {
    const safeTitle = escapeHtml(title);
    const safeMsg = escapeHtml(msg);
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${safeTitle}</title>
    <style>
        ${SHARED_FONT_CSS}
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #0F0F0F;
            color: #fff;
            font-family: var(--font-body);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
            text-align: center;
            overflow-x: hidden;
        }
        .box {
            background: #1A1A1A;
            border: 1px solid #333;
            padding: 30px 24px;
            border-radius: 12px;
            max-width: 380px;
            width: 100%;
        }
        h2 {
            font-family: var(--font-heading);
            font-size: 18px;
            margin-bottom: 10px;
            color: #DC2626;
        }
        p { font-size: 13px; color: #aaa; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="box">
        <h2>⚠️ ${safeTitle}</h2>
        <p>${safeMsg}</p>
    </div>
</body>
</html>`;
}
