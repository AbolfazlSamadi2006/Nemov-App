/**
 * Yalda Gym Cloudflare Worker - Serverless Backup Server & Admin Dashboard
 * Author: Abolfazl Samadi
 */

const SECRET_API_KEY = "yalda_cloud_sec_2006_gym";
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

// Constant-time string equality helper mitigating timing side-channel attacks
function timingSafeEqual(a, b) {
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
    let kv = env.BACKUPS_KV || env.KV || env.BACKUP_KV || env.YALDA_KV || env.yalda_backups_kv || null;
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
        const secretApiKey = (env && env.SECRET_API_KEY) || SECRET_API_KEY;

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

        if (path === "/images/yalda_logo.jpg" || path === "/yalda_logo.jpg" || path === "/logo.jpg" || path === "/favicon.ico") {
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

Sitemap: https://gymassistantapp.ir/sitemap.xml
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
    <loc>https://gymassistantapp.ir/</loc>
    <lastmod>2026-10-01</lastmod>
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

// Embedded Yalda Gym Official Logo (Base64 JPEG for 100% self-contained delivery)
const YALDA_LOGO_BASE64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCALSBAADASIAAhEBAxEB/8QAHgABAAICAwEBAQAAAAAAAAAAAAEIBwkCBQYEAwr/xABSEAEAAQMDAQUGAgcDCAYHCQEAAQIDBAUGEQcIEiExQRMiUWFxgRSRCRUyQlKhwSOisRckM2KCkrLRFiVTcsLSNURUc4OjsxgnNENjZJTD8PH/xAAeAQEAAgIDAQEBAAAAAAAAAAAABwgFBgEDBAIJCv/EAEURAQABAwICBggCCAQGAQUBAAABAgMEBREGBxIhMUFRYRMicYGRobHBCNEUIzJCUnLh8BUzYpIkgqKywvEWNkNEU2Pi/9oADAMBAAIRAxEAPwDYL68B6/YflU3gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+weoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOFy9atUzVcuU0xHjM1TxDrNx7iwduafXn5tyIiI92n1qn4QwHvDqVrO4rty3TlV42N+zFm1PHMfOWZ0vRb+pzvT1U+LPaPw/k6xO9HVR4z9vFm3Uuo2ztLvVWMjXLE3KfOm3Pf4n4Tw+Gnq5smau7VqdVMfxTbnhWWb+Rduc1U92Ofi51V3JjuzM8Nup4PxIjaqqZn3fk3mjgPCppiK7lUz7vyW00ndW39coivTNWx73P7sVx3vy83bRMSp7p2p5GmXvbWLtymqPGJpllbYXWDIpvWtP1yqarFU92m7V5x9WH1LhS7j0zcxp6UR3d/wDVgdW4Kv4lM3cSrp0x3T2/1ZsHCxet5Fmi/ariqiuO9TMeUw5tQmJidpaPMbTtIAOAAAAAAAAAAAAADmPiAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADheu0WbVV25V3aaImZn5ObzXUTU6tL2pnXqJmK6rfcjj5zx/V3Y9qb92m1HfMQ78axOTeos09tUxHxYO3/AL3ubo1m97GqurFs1TRYiJ4iYj18XkKqau9NVXnVPM/J+VE1RfrmfWeX796KvGJ9Uy4+PbxLcWrUbREJ8xcS3g2qbFmNqYh+dUceNMeL8qva8/sPp4cZj5O+mXpidn4RFc+dL9KLfs4iuiKq5554ieOJTMOHeqiZiPBzvu53mrqZ16Kbwuahi16Dm3ZmuzHes97z7vrSyr5qr9OtZu6buTGyIqmnuXYiqPjTzELT26u/RTX8Y5RjxRgxiZnTojaKuv3of4x06nBz+nRG0Vxv7+9MfAOPEa01IAAAAAAOYCfsCO98IPH6Hh6yeHwch/tI4lPP0SbiO78U8QB1yImn4ET6SmEVHlIkI8YHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAeoev2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOQAOfkjn5JAO9BzEnEHdg6gEcTHlJz8TYS8Z1bornZmVcppmYomjnj4TVD2fm6zc2nTquhZuBEczes1UR4evD1YN2LGTbuT2RMfV7NPvRj5du7PZFUT81TYppi7cp8OafBxtzHj9UZeNk4WXet36Kqa4uTTVE+cTHgiieY5TRG0xvErARtNPSid3696JlE8S488HPPq42cJlFu1M1TPejhPg4U1VUzMR6ufY5jfudntaxNes2abf7VV2mmPrNULZY8TFi3E/wAMK5dKdCvajuPHu+z5os1Tdr59PgshTT3aYp+EcI94wv015FFuJ7I+qLeOsim5lW7UT10x9f8A0TPjCSY5Iae0UA8QDwTTRVXMRTEzPyeX3h1R6bdP8WvM3vvvQ9EtUVxRVOZm0UTFU+nHPLI4GkZ+qXIt4Vmq5VPdTEy+K7lFuN652enmeDxVZ3t+kq7Lm0Iu2tN1rWN05Nm53Js6PgzVE/61Ny7NFuY+lSv2+P0t+5sibmP0u6O4OJEXebWXr2ZVfmq1x5TYtRTEVc8ePtJj5Jg4b/DpzD4lmmcfAqppnvr9X5T1sdd1nDs9tW7ZPxMzHETP0hNdE0R3rsdyPjV4Q0xby/SBdrfedzIinqJZ2/i3+f8ANtFwLNiLcf6tyaarsf77DO7eqXVDelqm3vrqfujXrduZmi3qWr38iimflTXVMR9k76J+Brii/R6XWcuixT37RNX16P1Yu7xNbidrVG/v/wDbedubrV0b2ZN+jdfVfaOlXceJquY+Tq9im/ER8LXe78z8ohh/c36RLsnbcx6ruPv7K1y5TMx7HS9Mv11/ablNFM/7zUlsTpF1K6qZcYnT3YGr69c/erxsSquimOeOaq5jiI5n4rW9M/0U3WLcns8rqXu3RtnYlXPesY9P47Mjy492iabcRPj+/wAx8Hu1X8PvKfgOjp8Ua3VVVH7tE0xM+6Iqn5vijVs/L/yLezOu4/0svQ7TrfO3Njbs1S5/Dk0WcSI+8VXHkI/Sq7s3fqFOkdKezrn6tm3I9yx7e7l3Jn192zRE8M29Of0b3Ze2D7LI1Pbeobwz7VdN2MjXMyqqiKoiPCLNruW5o5iZ4rirz85WN27tTamz8GnS9obW0nQsKmZqjH0zCt41qJnznu0REc/ND+t8TcntEoqtaDpdzJrj965XVTE+fVP/AIw99qxqV6d7tcUx/f8Afaqzszqv+kL6lYf4nE6E7I2Xi3KIuWsnXsq9buVR5ceyiqqumflXRSyltXZnajvZNvK3z1m2/j2q6ebuJpG37czRV8IuXZnmPn3YZpmqqfGZmfrKET6rxvay5mnAwLNinyoiqfjX0mUtWJt/tVTMvj0rEzMLDtWM/U7mffopiK79dumia5+PdpiIj7PsBodyublU11dsvR2ohIPkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOF+q7TaqqsURXciPdpmeImfqxzuPdfWPR6qrmn9PtP1CxNU8TYzZmuI+cTwySPdgZlvEr6V21Tcjwq3+0w8OfiXcy1NFm9Vbnxp2+8SrrqXaT3ro+T+G1jYcYNfPEfiO/TE/SfKU4nan1G7EV39q2u7PrRdnmfpyz9qGk6bq1irF1LAx8m1VHE0XbcVRMfdi7dXZs2Tq9VzN29Vd0LOqiYibHv2efnameI+3CUtA1vgjNqizquDFuZ/eiapj69SJNf0DmBg73tH1D0sfw1U0xV842n4x7HUYvam0Sbnc1Da+fYpj9qqm7TV/J6LTO0f0v1CqKL+q3sGZ/9qszT/hywTu3phvjYVya9b06rO0+meYz8SZuUcf69ERFVH8/q8zVFqvu12KbdVufWI55n4eMpbxOUHBfEdj9I0q/PX3Uzvt8UTX+b/G3DuROLqlEdKO6ujb6dFdPSN67T17uRpG4cDKqufs0279M1T/s+buonmOYUQ/B2LlUVTTVbqjymiqYmPymHotI3/wBQdtVUVaLvLOi1biIixkR+It8R6RTXM8fZrGs/h3zbP6zTciKo8Ko2ltuj/iHxq9qNWxZp86J3+U/muaK+bZ7UGRbopo3jodFUd7u1X8Ke7MfP2czP/F9mXNrdStlbxjjQtexr13jmbNVXcuR9aZ4n1Q3r/Amu8OVT+mWJ6P8AFHXHxjs96Y+H+P8Ah7iWIjByI6c/u1erV8J7fdu9Nx8E+ccSRMT4wNQneO1uTDHV3YNdNyrX9MsRNuqOb1FMeU/xMPRT7PmK5iOJXEv2LeRaqtXaIroqjiqmY8Jhi/ePRTC1O7czNBu0Y9dcTNVmqOaZq+U8+DeNC4jt27cY+XO23ZP5pF4b4rt2bUYmdO0R2VfaWCarlNMeE8/RxovTVPjbmPq9DndNtx6Pk1UZGnZMxTPPeijvU/nEvxjbOq5MxasYGRVV8rc8NzjLx6o6VFcTHju3+nOxK6YqoriY8d3T9+J9X26ZpmTqeVbxsW1Ndy5Pu0xHPL1WgdIdzapVT7WxGPb9arvhx9uWZNmdPNJ2pZprppi/lzHv3qo4/KOfBhtS4gxcKiYt1dKrwj7sDq/FGFp9ExZq6dfhH3lx6cbPjbGlRVkRTOVfiJuTEeUceEfZ7AiPSHxa1ruh7a029rO5dZwtKwMema7uTmX6bVuin4zVVMQjym3l6zlbWqJruVT2RG8ogzcyrKu1ZF+eueuX2y5UW6q54iOeFMOsf6UToxsW5e0rpho2Xv8A1O3M0Tet3fweBRPjEz7aqmqq5x4T7tHdmP3oUa6s9tjtKdaZvYmub5uaFpF3mP1XoVM4lnuzHE01VRVNy5E/CuqY+Sx/Lz8KPHPG9VN2/Z/R7U99fbt7Pza5l69jY8TFE9KW2Pqd2nOg/R+3ejfPUfS7GZYiqZ0/FuRkZVVVMc9z2dHM0zPp3uI+aoXUz9LPpluu/g9H+mt/Iimuabeoazd7lNdPHhVFqjxiefSZlro9lFVybl6qu7cqnma7lU1VTP1lMURRPuT/ACXU4K/BRwloMU3taqnJrjt36oifZG27XMjiPJuz6nqwzr1D7cvaa6m27uJqXUC9o+Heo9nXjaPbjFpqp558aqfe5+cTDBmdezNXzLmfrOoZWflXZ71y9lXqrtdc/GaqpmZIqqnwmnj5ox7GVnZ1rTdLxL+bmX6optY+Pbm5crn4RTHjKyuncD8IcD4npsbFtWbdPbPRpp/9yw9V+/kVdczMyim3Rb8KKYiPk40XaruRbw8OxcyMm9VFu3atUTVXXVM8RERHjM8+i43Qv9GZ1e6i/hta6t5s7D0K5xXOL3Kbup36OfGn2fPFnmOY5rnmPD3JhsH6OdlroZ0FxrdHTrY+Haz4o7l7V8+mMvUL3MRFXN6uPcie7EzTbimnnyhAPMv8XnB/BXTw9CqjJvRH7serE+G/Yy2FoORk+tcjaGsvo1+j07RHVqLOoa5pVOxdFux3oytYomL9dPjHu48e/Hl+93fuu50k/Rs9nzpzVa1HdGFlb01WiOZuanXxjRV4T7tqniPCY8JlbCaqqvGapn6oUB5hfie4648uTTOTNi1P7tE7fPt+DasXRcXG/d3nzfLpGl6Xt/Ao0vQdKw9Nw7czNOPh2KbNuJnzmKaYiH1TzPnIK+5edk59ybuVcmuqe+ZmZ+bK00U0RtTGwA8r6AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABxuWrd6iq3doproqjiaao5iYYf6g9n7SNZqv6vtGLem6hVE1TZiP7G7V849PszEM7oXEmpcOZEZGBdmmYns36pa/xDwvpfFGNONqVqKo7p/ej2T2/ZRjWcDVNt6hXo25MO5g59ufCiqPduR8aKvWHG3MV2qLlvjmqPGfguHvnp/oG/NNnC1fGp9tb5nHyaaY9pZq+MT8PkqfvbbGvdOdejQdcs0TYuzM4WXTTMWsmj5VTPhVHrTPj9uJm5PLfmti8V25x8vai/Edk/vecKc8w+V2dwbd9Pj73MaZ6qvDyq8Pb2T8nW+xivjvVTHHwc7GHTTXF7Epm1kW59pTet1TRXE/WHGaqqqIrmmaJjzjnn8uH6RXc9nPs6u7PHCXr1mjKommuiK4mOyUTxcuW56VE7S91tHrvvbaPdxNZt/rjBp8Iirn21MfKr1+7Pmx+p21N+4sXdHz6YyKY5uYtz3btH1plUOacmrmJuVRz6xPi42Ma/h5dGoaZl3cXOtTE2r1uru1RPr4x5oV4z5LaTrFM38SJtXp8OxMHB/OTWuHJpsZlXprMdW1U9cR5Vdvx3hes4hgHpx2hrtm7Z0HqDxEz3bdGoU0d2O9/+p6fePuz1jZNjLs05GLeou2rkRVTXRVzEx8YlU7ifhDU+E8ibGdRMR3T3StrwtxjpXF2N+kafc3nvpn9qn2x946nOaYnwmIn6w4xZoieYopj7Oaaaaq57tFMzM+kNZoiuuejT1zLad9nGKYh8Ou69oe19IyNe3Jq+JpenYlE3L2TlXYt0UUxHPnPr8vOWAe0924+lfZwpvbdt3KN071mmO5ouFd93EmY5irKuRzFvwmJiiOa5iY8Iie81Z9bu0j1e7Q2tVan1A1+5+BoqmcbSMSZt4WNHwpt8+M/OqZmfiszyk/DFxPzHroy8umcfF365qielMeUfdhc7W7GJM009crz9fP0pO19t3snbPQfQ6dw59PetTrWbTNGJbq96O9bo/aucTFMxzxExMqB9Uus3VbrVq1erdSt56hqkTXNdvEm5NGNZ8ZmIotU+7HHPHPHPHq8XZoi3xHERw/XnmZfp3y1/D1wby8xaf0XHpuXf4643q3/vwaXm6tkZlXrTtDhRaot/s0REfBzqiYjy4RLhV3pn3qv5p2oiixa6Funq8mM7Z63KPg/Gu5FuZmrwn4R5vR9Pun++eq257OzOm+2szXdXvRz7LHp923RzETXcrmYpt0RzHNVUxEc+bZ52ZP0c2xek9eHvTqvkY+7t20f2tFju86bg1cRx3KKoibtcTz79cRHlxTExzMCc3uf3C/KnDn9Kuxcyevo2qZiZmfPwjdldP0q/nTvTG1Pipt2dOwZ1e681WNc121d2ftKuYqnPzLUxkZFHh/obU+M8xPhVPENmnQvsr9F+z1hURsTa1m5rE092/rebTF7NuTxVE8VzH9nHFdUcUceE8Tyy1TFNFFNu3TFFFEd2mmmOIpiPKIhL8qeaP4iOLuZmRXTfvzax57LdM9W3nPe3fC0jHw46o3nxTMzV4zKOOAQJNU1TvLKh5BxDgRzPpB4yny9CZhyOPEpjw9JOZOTrDvQlHmcTHkbCQieRwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOj3ls/Rd76He0PXMSi9aueNFUx71qv0qpn0l3g9GJl3sG9Tfx6ppqpneJh58vEsZ1irGyaYqoqjaYnsmFKNzbZ1DYWt3NrazTPNEzVi3uPdvWufCY+b4ImJnjn5rZdVOnWF1E27XgTFFrUbHNzCyZjxt3PhM/wz6qkUWc/AzsnR9Xx6sfPwa5s5FqqPKqJ84+UrxcqePbXFWnRj36tr9HVMePmozzQ5f3ODNQm5YiZx7m80z4eNM+cP3mZ445fnXR5VxVVEx5eL9OHzZeVOLTFc26rkTPdiimOaqqp8ohLddymmiZu1bUx1z7EXW6aq6opp7XDOpnJpi1+FpyLtz3KLdMc11zPlELL9n7aG9tr6DcndGXVbxsjivGwblXfrsRxHnPp9HydFukFvRbFnd258WJ1S/RFVmxX4xjUz6f8Ae+Pw8mWdW1bStA0nO1/XdRx9P0zTMevKzMrIrii1Ys0RzVXVM+ERERKofNrmFZ4tyf8AAtHtekpiYjpbb1VTH8Pfst1yg5bZGg0067qdU0VzHq0b7bRMdtX5d3e/TOzsLS8HI1TU82ziYWJbqvZF+9XFFu3RTHM1VVT5RDW92tv0kmo6lezOnHZzy6sbEmmvHztyd2YuXOfCYxv4I8/f8/Hw482M+2X24db69ajkbB6e5OTpewMS5NNVUTNF7V5pnj2lzymm3PnFH3nx8IqjRTTa92imFqPw8/hLtWbNniTjKneuraqm1Mfs9+8x4pR1XXpqmbWP2eKKqb1/Iu5ubeuZGTfrm5dvXapqruVTPMzMz4zMz6v1iIp8ogiJqnmU+r9FsHCsabZizi0RTTHVEbbNTrrmud6pcaqYnx8iKqao4pnxj4pfjfuU2/e54iPOX3duRYpm7Vtt3uKY36nOau741TEM3dmTsl9Q+03rftNMtXNH2ni1f57rd+3MUTxPjbsx+/X9PCPV7jsadiDcHX/VcbfvUDFydL6d4l2K455t39YmmfG1a9abf8Vz7U+PM07bdB0HQtraNibd2zpGLpemYFqmzjYmLbi3bt0RHEREQoh+If8AFXj8KRc4d4Xq6eT1xVXHZT7J8Wz6Toc5G1691Q8V0S6CdNez7tWja/TzQ7eNVXRTGbn3IirKzq4/eu1+c+MzxT5Rz4QyH5+YTMQ/LjWNaztfzK87Ubk3LlU7zMzu3a1aos0xRRG0QCO8li9nYAc+PAEzERy8lu3qlsfZFqbu49xYeHx+7XdiKvy83Tde73UKz07z56a8xq00+E0xE1xR693n974NYms6hruoajkXtxZuXk53tKovTk11VVxVz488/NJHBHAtrie3Vk370U00zt0Y66vf4R4SlPl7y7t8YxVfv5EUUUztNMddf9I8J617t0duPpno1yq3o+Jn6tNMzH9jRFNM/PmqYY21jt/7iuV106DsfEtUT+xVk35mqPrER/VUzmfKITx8ZS/h8t+HsSNqrPTnxqmfttCecHlBwthxHTszcnxqqn6RtCxv/wBuzrDVd786ZoNNHP7EWK58Pr3ns9mdvbKqz7WNvnbNu3j1zEVX8SZnu/OYlT/xPCY8Ye3I4E4eyKJonGpp843iWQyuWHC2VZm1GLTT507xP1bcNnb12/vrR7Oubcz7eTjXo5iaZ5mPlLvoaxugPXLV+kO57NV69dv6Lk1xRk481cxRE+Hep+nLZRt7XdO3JpGNrelZNN/Fy7cXLddM8xMSgDjPhC9wvk+r61mr9mr7T5x81YOPeB8jg3N6Mb1WK/2KvtPnHzdhPhKfMmOUUz6NL7mhJAcAAAAAAAcwACOfjCQDnkRx6wmJ5AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgntG9Pqr9u11A0a33b+NT7LUKaaY/tLf7tf1jjiflMfBnZ82pafjargX9OzLVNyxk26rdyirymmY4lsvCfEeRwxqlvOsVTG0xv5x3tY4w4ascV6Rd069EbzG9M+FUdk/afLdSG3eovWYvW586e9wyf0F6bxunVY3xrFuZwMCru4dmqPC5d9a5+Pd9Pn9GP9zbSz9tbzvbHtU1137mRTRif69q5Puz9v6LgbQ29jbV25gaBh0RTRiWaaJ49avWZ+/KzvNvmLFrQrFrTavWyae2O6naN59/YrDyj5fVZ2v3r2pW/UxZ2mJ769+qJ9m28+7xdtcuW7Nuu9euU27Vqma666p4pppiOZmZ9I4amO3n2ytU60a7kdI+nmfXjbF0rI4zLtueKtXyaKv2qpjx9lTP7NPlMx3p5mI4sF+kq7UV7ZG36Og2xdRijXNese01q/armK8TEnyt8x5VXPH7R82sOzbmzbin1iEsfhH5A0ZlNPGmv294n/KiY/wCr2+CyevapMVfo1rsjtKaKaaKaJ9IfrE8xEfCOPJxiJqnxc36X2bcUR6sbR2NQmdzmfi4V1dzjw55c351VdyJ48Zfd2qejvM7ebiO0rrpiOeVquxN2MNR6+61a37vzFvYew9MvRVEVRNNWqXaZ/wBFR69z+KqPo8b2POy3rnaW35FeZj3cbZehXqK9Zz/2Yuz5xjW59a6o8+P2afGeOaYnczoGg6PtbRMLbW3dOsYGmadZpx8bHs0RTRbopjiIiIUM/FR+I+nhexXwpw7cicmuNrlUT+xEx2dXZV9G0aHpE35i/dj1fq/fAwNP0bTsbSdMxbOJhYdqmzYsWqYpot0UxxFMRHlEQ+iK6Z8IqiVd+2jvHd+zthafk7S1HLwruRnRbu38fwqppimZ4+/Cpejdp7rdpNcV073ycqI/dyKKa4/wfnbo3AWo8VYf+KUX6d6pn9qZ3mY75nae1YPhjlfqPE+mxn4NyiI3mOjO8T1eyGz3mEeChe2u3Zv/AAK6Le4tDws+1Ex3q7dU0VzH+DOOwu2d003XXbxNXru6Pk1zFPGRHFHP/e8ng1Hl5r2mxNdVnp0x30zv8u35PLq3LHiXSKZruY/Tpjvo9b5dvyWD4g8YfDpes6XreLRmaVnWMqzcjmmu1XFUTH2fdz8Wl1267U9GuNpaFXRVbqmmuNpg7xPxgmPgjxiXw+XLzVN7X3Z7wdS0271K2dpvs9Qx+a9Ss2qfC9R/2nHxj1484WxieJcMixaybNdi/bpuW7lM01U1RzExLOcPa7k8PZ1GXjz2dsd0x3xLP8NcQ5XDOo29QxZ66Z647qo74n++qetp2iODlk7tE9Maul3UvP0rHs+z07Nn8ZhcR4RbrnmaP9meY+nDGK3eDm2tRxqMqxO9NcRMe9ezStRs6vhWs7Hnei5TEx7/AMuwjxER5pepkEVRzC4/Yc6sXaqMnpprGZzFv+20/vz49396mPv4qcu/6fbpzdlb10jcmDcmmvDyqKq+J86Ofej8mv8AFGi0a/pd3Dqjr23p8qo7Py97UeN+HrfEui3sOqPW23pnwqjs/Jtu83GfCXx6HqVvWNIw9Us1RNGXZou0zHwmIl9tSoFdE2q5oq7Y6lFK6KrdU0VdsdSQjyHw+QAAmZjyEVTxEyQOF/JsY1qq9kXaLdFMTNVVdXERDGW6+0n0h2fcrsaru/FrvW54qtY/N2uPtTyqH2put28Nw7+1bZmDrN/E0bTLkWPY2K5pi7VxE1TVMePn4cK+xTTT4R+cym3hzlTbysajL1O7MdOImKae6J6+uZ7/AHLA8KcladRxLebqt6YiuIqimjtiJ643me/2Qv3qXbs6TYlybeDh6pnRE/tUWO5H97h1dXb62FFfu7W1iafn7P8A8yjPj8k+Lc6OV/DtEbTRVPtqn7bJBtcl+F7cbVU11e2qfsvZidvjprcvRbzNA1jGon9+aKaoj7RMyy30u68dPurl2/j7S1Kq5kY1MV3bN23VRXET68THi1bz4eiyfYTwLt/qhqGbbqmKMbTpiqI8p71Uf8mv8U8u9E0/Sr2ZjRVTXRG8etvHz/NqXHHKrQtG0a/qOH0qarcbxvVvHb5r9ojwnhMI/eV/VqSAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcxBz6g8jrewNO1jfWh70vW6JvaTRdo8f3u9Hu/lPLh1h6n6F0Y6Y7h6nbhqicTQ8Sq7Ra54nIvz7tq1T8665pp+72Py+LXH+lj6w1XMranQnScriizzr2tU0z4VVTE0Y1urj4R7SuYn+KifRLvKPhTK5l8W4Gh35mq1TMb/6aIneWGyLePpFq9kWKYiq5O8+dW0Rv8IUR3jvTcvUveesb/wB4ZdWRq+t5VeVkVzVMxTz+zRTzMzFNNPFNMc+EREOqnmJ4mfD0cfLuzHlKfH1fu5o2lY2hYFvTMSno0W4iI26uqIR1crqu1zXV2ylHzCfGOGS36nwU1ePk9D066fbl6s760jp3s/F9vqesX4tUzP7Fmj9+5XPpTTHMz9HnL1ymzbm5VzER5to/6M3s7/8AQfY2R1q3NgTRre6rfc02m5TxVj4HPn4+MTXMc/SIQfz75q2OVfCt3M6cfpFcdG3HnMMlpeFObfiju71ouifSHbHQzpto/TnauPRTZ06xH4nI49/LyZ8bl6ufWaquZ+UcRHEREPcg/DXV9VydbzruoZlXSuXKpqmZ8ZndJlu3Tapiinsh8ep6PpWs484mradj5lmfO3ftxXT+UsU727KfR3eVi5E7Zs6VkVeNN7Topx5ifjxTHE/eJZi5iQwNWztLrivEu1UTHhMwyun6xn6VXFeFeqtz/pmYUJ6i9iDeW36L2dsnUadYxrUTX7C7Hdv8R6RMeFU/krlq+i6roWbc03WtOv4eTaniu1eommqPtLcFxz8mNOrnQfZfVfTLlvVcCizn00z7HMtUxFyir05n1j5Slbh3mvkW66bGsU9Kmf3o6pj2x2T9U0cJ86szHuRj69HpLc9XTiNqo9sdkx8J9rXj0+6xb/6Z5tvK23ruRFimfew7lyqbNcfDu+n1heDoh2rNpdTbVGk6xXTpes0xETau1RFNyfjTMz4qOdUelu4+le472h67Ymbfen8PkUx7l6j0mPm8hYv38W/RlYl6uzftT3qLlFXdqpn5TCSNb4W0ji/Fi/RtFVUb010/fx+qVuIeCNC47w4zMfaK6o3puU9/t8ff1txVFdFdMV26u9TV5TE+EuSqHZS7S1zcsYvTzed+P1hbomnGyq6v9PEek8/vLXU1d6OVa9f0LK4ezKsTKjrjsnumPGFTOI+Hs3hnOqwc2naY64numO6YJghMnn4sJ3MEq328NmUalsfTt44+PR7fR8juXa4jx9lc4iY/3u7P2UWbTOvmkRrfSTcuB7GLlVeDXNMTHPjEctWcfCfTwWT5UahVlaLVj1//AGqpiPZPX9d1suSGp15eh3MSuf8AKrmI9lXX9d0eSQSemkR6pRINmHZV3BXr/RXQbt29VcrxLc4lU1TzPuT3f6MvT5Kq9gTWLuVsfXNGuXZq/B6jNdFMz+zTXRT5feJWqVF4zw/0DXsm13dKZj2T1/dQ/jnC/wAP4izLEdnTmY9lXX90UpRHmlq8tUAAHG7PFuqflLk+fUa/Z4V65H7tuqf5PqiOlVEPqmN6ohqk6rZE5PUvc96qrvTOq5Mc/KLlUQ8rxDstzZ/603Jquo88/ic2/d/OuZdZPw+S7OJb9Fj0UeERHyfoVpdv0ODZt+FFMfCISInyPV3veVLY9gPFn/pJuLM4jiMW3Rz8+9MqnVLldgDF/wA23NmTHldtW+f9nlpnMG56Ph3J84iPnCOea9z0fCeV59GP+qFxARSqgpUkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+wev2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACZ4JmIeM6mdVNp9Ldv3td3JqFujux/ZWIqibl2r4Ux5y9GLi3s27TYsUzVVVO0RHbL0YmJfzr1OPjUzVXVO0RHXMy9Freu6Tt3T7uq61n2cTFsUzVXdu1xTTER83WbH6h7Q6i6ZOr7P1mzqONTXVbqrt8+7VHnE8qF7g3V1a7W28f1PouPdxtFpu+5ajmLNij+O5VH7VS5fQfojonRPas6Np1yu/l5VUXczIr87lzjjw+ER6Q3TXeFsPhzTo/Tb++ZVtMW6dpimO/pT4/319rduIeEcThjT6Izb++ZVtPo6dpimP9U+P99fayhao9pcpo+MtE/ac6hVdVe0DvbekZFV/Hv6ncxsSa6eJjHs/wBnbjj5U0w3W9VNfjanTDd25fxdOLVpuiZl+3eqniKLkWau5PM/63DQHbu3ci5dy71Xerv3Krtc/GqqZmZ/muf+A7hui9qefrlyjeaYiiJ8N+uUKcUXtqabUe1+iYjlCaX6gw0uXLiPg48Rzw5PzqjiJr7zmd9t9uxxDJHZv6QZvXrrdtnprj0V/g8jIjM1S7H/AOTg2vfu1czExzMRMRz5zMR6t6WDgYGlYWPpel4tGNh4dqjHx7NuOKbdumIimmI+EREQof8Aom+lUaXs7dnW3U8aYytdyI0PSq6omJ/B2Ziu/VT6TTVdmmn62al9340/i+5h3OLuM6tLt172sb1do7N/6R9ZSJoGHGPj+kmOuQ+QR4+KpDPAAB9QBj/rH0o0fqptLL0TMs26MqqiZx7/AHeardfpMNY+7tr6nszceftnWLfcy8C7Nuv4THpMfKY4lt4nxhTXt09LbNqnB6naZZ7tUVRiZ8U0+dP7lc/fw+8Jd5W8TV4mZ/hORV+rufs+VX9ez27Ju5OcYXNN1CNFyav1V39nyr/Kez27KgYWdl6dl2c/Bv1WcjHri5brpniaao8Ylsm7MnWK31X2LZqy7lP620yIxsyn1qqiI4q+ktak+TL/AGVeoF3YfVrT7d7ImjA1uqnAyKfKnvTVHcqn6T4feUn8ecPW9d0quqmP1tuJqpnv6u2PfHzTBzS4Vt8RaLXet0/rrUTVTPftHbHvj5tl6I8JKaoqpiqmeYmPAnzhVSYmJ2lTF1+48aMzQNSxZiJ9riXaOPrRLUdq2NVhapl4lXnZv125+1Uw2+Zsc4d+Pjbq/wAGpLe9Pd3hrVPwz78f35TjybuT/wAXR3erP/csRyDuz6XNt921E/OXSgJwWTARILh/o+rnORu+zE+VGLV+c3P+S5alX6PWr/rjesT5ewweP968uqq5zNp6PEl72Uf9sKUc1v8A6tyv+X/spRHmlEecpaBKOwAB0m9cn8HtXVcrnj2WLcq55+EO7eI625EYvSbdd7vd3u6VkcT/ALEvbptv02Zat+NVMfOHs0636bMtW/GqmPjMNVPjM1TPnNUz/MJ85+qJldV+htMbUxCUeqUesj6J84Xm7Aun1Wdj6/nT5ZGoUxE/92jhRn1bBewxj02ujVd7uTTVe1PImZmPOI44lHnNCuaOHbkR31Ux89/siLnVf9FwxNEfvV0x9Z+yxKPKYSjnmY4VghUFIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEzwPC9XOq23+lG1snXtYyaIyIpmMXH73vXrnpTEPTh4l7Ov04+PTNVdU7REPVh4d/UL9GLjUzVXVO0RHfL4utXWnbPRzbdeqarfpvaheiacLBoqj2l6v6elMes//APFGdD0LqT2r+ot3L1K/f/C0V/216mmfYYlv0oojyiZj7+sussWeoXac6oTFy7XeyMu571U8zawseJ9I9OI/OWw3pX0u270q2ti7c0HHpj2dPN6/VEd+9c9aqp+MpjvfofLPA6FvavPuR29sUR5f31z19nUnDJpweU+mxao2ualdjrnti3E+H99c+SOl3S3bfS3bePoGg4dFEWqY9pd45ruVeszPrL2gIby8u9nXqsjIqmqqqd5mUG5WXezr1WRkVTVXVO8zLCXbcu1WeyX1OuUXO5V+p4iJ54871tpHwqZixTz8G7LtyWq7nZJ6lRREzxpdEz9Pb22k/G8LVNM+kP1K/AZaj/47m3P9aP8Aij/NpfsI5jnhK/bVB82ZcmzYqrj6RD6Xrui+zLfUTrTsTY+RiVZeNq+v4dnKs0+dWNF2mq9/8umufs1/i3VI0TQsvUJnb0dFU/J3WKPSXIpbo+zP07p6U9n3YOw5xLuLkYGi2b2bZu/t28vI5v5FM/S7drj7MmJnuxPdo/Zp92PpHgh/PXxFqdes6tk6hc7bldVXxmZSzZo9Hbpo8IRPqlEeiWGl2AAAAHqx51+25Z3N0n3Hp9yxN2r8DcuW6Ijme/THep4+8QyG6jd1qL22dTt1eVWNcif92Xu0y/VjZtq9R201Uz8Je/S8irFzrN+jtpqpn4TDUTzzz9U2Mm9g37eZjVTTdsVxcomPOKonmE3aPZ3rlv8Ahrqj+b86qefD4rqdVXb2P0F2i/Z2n96PrDbR0z3FTuvYehbg71M1ZuBZu192eeKpojvR+fL07EHZPyasnodt6quvvTbouW+flFcsvqZa5jU4ep5Fijsprqj4SoBruLTg6pkY1HZRXVEeyJl8+o3ItYGTdnyotV1flEtSO778ZO6dXyI8YuZ16qPvXLa/u/JjD2tq2TM8ezwr0x9e5LUblX5ycm9kVTzNy5VVP5pf5N256OXc/lj/ALk68g7X6zNu+VEfV+c+Qif6HpCblkUomeCPOT14Bc39H3p8fqzdWr93xuZNrG5+VFPe/wDGuCrN2D9Fr0/pbnanVE8alqd65T9KYpo/8KzKqPMK/GRxFkzHdMR8IiFHOZGTGXxRl1xPZVt8IiPsiPOUojzmUtLlo4AAxV2oc6dP6G7qyKZ4mcSm1/v3KKP/ABMqsI9sfKjH6Da9biriq9VjUR//ACLc/wBGd4Xt+l1rEo8blH/dDP8AClqb2u4duO+7R/3Q1weaJ80i4q/YiPVJA5cap8JmfSGyXsf4cYvQvQbsU8fiaK70/OZqn/k1tV096mY+McNpXZ60ijROje1NPo8O7p9uufrVHe/qirm7eijR7drvqrj5RKCue+R0NIx7H8Ve/wAIn82RZ8IRSlEequSrKQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABFdUUxMzPER4zJHWOq3TuXS9paDm7h1nJpsYeDZrvXK6vhTEzx9fBrT6x9UtxddN+Rds27tWL7X8PpmHHnFMz4TMfxT6sqds7rbd3Fr3+Tbb2bP6u06rnUKqJ8Lt6PKj5xT/j9HLsV9H6df1uvqPrNjv4mn1+ywqKqfCq7+9X9uU78JaRj8H6PXxDqEfrao9SJ7onsj21fKPesVwTo2LwLoNfFeqU73qo/V0z3RPZ76u/wj3rC9mrojp/SraFm/kWqa9a1CmLuXdmPGJmPCmPlHLM6KKYpp4iOIjyShjVdTv6vl15mTO9VU7/ANPcgbVtUydazLmdl1b11zvP5eyO4AY9jmIO2Do+pbg7L/UnSNJx6r+Te0Wuum3TMRM0266a6vPw8KaJn7NHOJM12aa/SX9B+79Dq3PtHXdt0zETq2l5WDEz5RNy1VRE/nL+fe/i1abnZemXP28PIu49X1oqmP6P0y/ARrFNWLqOl1Tt0aoqj3xs03im310Vp4gce8RVEv0b3jfbdp7ksR+jy27f1/tb7RyrVvvW9Ds5upXp5jwpixVbif8AeuwrtM8Lefossau92jtWzIo5px9uZFMz8O9dtcf4IV/EPqdWk8uNUv09vo5j4sjpVE15dER4tsRPkIqfg9PXUlEjz5SR5D5AAAAB0O/My3p+0NWzL1cUUWsS5VVM+kd2XfT4MT9p3c1nbXR3Xr9253K8mx+Gtx6zVXVFP9WS0fGqzNQs2Ke2qqmPmymiYlWdqVjGojeaq6Y+Mw1l1VTXXXXM8zVXVP8ANw595y8IcYiZnwjmV0H6CURFuiI8IbKuyNaqtdCtB71PHfm9VH09pUzKx52f9Dvbd6Rba0y/bmi5GFRdrpnzia478x/eZDU34ju039XyblPZNdX1UC4lvU5Gs5V2id4m5XMf7peB66azGhdLNw58192aMK5ET9Y4/q1XWomKI582w7trbgt6R0gyMGm/NF/Ub9uzRER+1Heiao/KGvNOnKTEmzo9y/Mft1/KI/rKyHIzA9Do97LmP269vdER990T/RKJ+CZ8kqJwRBPr9Ex5P1wMS9qGoY2nY9Peu5d+ixRHxqqniP8AFxMxTG8uu7ci1RNdXZEbtlnZZ0OnQ+i23bXspoqycaMqqJjx71z3p/xZcdJsnTP1PtPSdMm3FFWNh2rc0x5RMUxDu58FMdaypzdRv5E/vVVT835961lzn6jfyp/frqn4zJHqEDGMYAAK79uPJqs9H4sxPEX8+zRPziOav/CsQrF29c2mz0z0nGmfG/q1NMR9Ldc/0bXwPbm7xDixH8cT8OtuXL6j0nFGFH/9In4dah56iPVbdelIAFuO/cot+c1VxTEfWW2bpli1YWwNvYtdPdqtadYpqj4TFENT2DRNeoYlER55FuP70Nue1qPZ7d023xx3cW3H92EMc469sbFo/wBVU/KFduflyfR4dvzrn6O1CRAitoAAAAAAHMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMX9oXqnjdLunmoapFyJzsm3OPiUc+M3KvCJ+3PLKFUxETMtenbN6jxuvqLO2MK/VVh6HHcrjn3artURM/lDcuBNBjX9XotXI3t0etV7I7vfPU3vl1w1/wDJ9ct49yP1dHr1+yO73ztDBeLiaruzX7ODZmq/qOr5VNqmZnmarlyrjmfvLaf0n2Pg9Pti6TtrCtxTGNj0e0q48aq5j3qp+czzKi/Y12X/ANK+r9vUb9nv42g405czMeHtKp7lMflNU/ZsXpiIjiI8G683NYmq/a0m3Pq0R0p9s9nwj6t+53676TMs6LZnai3HSqjznsj3R9UhPkIYQMAA526u5XFXwaMO1nsW5027Se/dr/gqMXG/WtzOw7dPlGPf/tbf92qG8yGtH9LJ0wjTt37Q6yYGLMWNaxqtE1Kui3PFOTZ5rs1V1eXNduqqmI+FiVvPwacWUaDx5GnX6+jRk0zTG/fVEbxDAcRWPS4vTjuUM84KYKfFPPD9jqNp2qR7Kal4f0TOJbu9T99Z1XHfsaRjUU/7V2rn/hhR2qqJXo/RK3KKeo3UCzP7VWk4lUfa7X/zV7/FRO/LHUpj+H7wy2h7xm0NnCJ80uPq/DrvSW5AOAAAAAlSzt49QqcnN0fp5g3oqizznZkUz5cxxbif70/kt9ujcWnbU0DO3Dqt6LeJg2ar12r4RDVT1E3hmb+3vq+7c2qrvZ+RVVbpmee5ajwop+1MRCVuVOhTm6lVqNyPUtR1fzT2fCN5+CZeTHDtWpazOpXKf1diOqe7pz2fCN5+Dzk+T0fTfbV7eG/tA2xZtzXOoZ1u3ciPS3E81z9qYmXnJ+C0HYZ6c3NY3fnb/wAu1H4XS7U42NNUed6qYmqqPpT4f7Upy4i1SjRtLvZlU7TTTO3809UfNZDjHWaNB0TIzap2mKZin+aeqPmvJpmNTh4GPi0092LVqmjj4cRw+qSOUVeETKnNVU11TVPeoZVVNdU1T3qV9vrclV3UNubYtXYmmmL2VepifKeKYp/xqVHZV7Tu66t2dZdbvUXfaY+n1UYFn/4ce9/empipbvg/T50zQ8bHnt6O8+2rr++y8vL3S50jhvFx6o2qmnpT7avW+4ifSEjZW6Ilk7s2bRubx6xaDgRYi5YxLv42/wB6OY7tHj/jwxjPjK4XYJ2bc9pre+L1viJmMGzVPrEe9V/PhrXGGpf4VomRkRPX0ejHtq6vu0rmHq/+C8OZORE7VTT0Y9tXV/Vcq3TFFEUUxxFMcQmpMCoczvO6jKKU8nMHg4DmPifQ8ACOVOf0g+p8Y+zdIoqn3r+VfuR6c00URH/FK4vPhKiXb01SMnfmhaVFM/5pg1X+fT+0q4/8CQOWVj0vEdqr+GKp/wCmY+6SOU2L+k8V42/7vSq+FMqwALRLpgR5APo0v/0rh8z/AOs2/wDiht027x+pMHjy/D0f4Q1EYNXc1DFr4/ZyLc/3obc9qXoyNt6ZfpiYivFt1RE+fjTCFOckfqcWfOr7K5c/InbCn+f/AMXaesJRPmlBEq4gAAiaojxfhe1DCx471/Ls24j1rriH1Tbqr/ZjdzFM1dUQ+g4dDn792VpdHtNR3ZpONT8bmXRTH85dJ/lw6R+X+Ubb0zM8REaja5/4nto0rOuR0qLNUx/LP5PXb07Mu9du1VPspn8nueIRx8JdXpe6dva1RTc0rWsLKiuOafZX6auY+0u15+TyXLVyzPRuRMT5vNctV2qujciYnz6gB1vgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHQb81+ztfaOqa/kV923hY9d2qefKIhqe13VsrXtXzNZzapm/m3q71c8+tU8tgvbS3Jd0Lovm4NiuaLmr37eFFUTxxEz3qvzppqj7tdnj4LDcotOizp13OmOuuraPZTH5z8lo+ROlRZ0y/qNUdddXRj2Ux+c/JdTsA7emzom4d012+KsrJjEpqn1oopiY/nVK3TAPYns2rfRTGuW4jm5m5E1z8+/MM/Sinj3JqyuIMmqruq6PujqQfzCy683ibMuV91c0+6nqj6I86kojzS0+WmAAHrwwn2zOktPWbs6bs2vj43ttUwMf9c6VxR3q4ysaJrimmP4q6PaW//iM2T8SaaavdrpiqmqJpqifWJ84Z3hnW73DesY2rY87VWq6ao907/N13rVN63Nursl/O1jXO/TE+U+U/V+lXmzl21eiU9DO0DrWkYGL7LQdfqnWNI7tHFFNq7VM12o4iI9yvmOI8qe78WDpjmfB/QBwJxPj8ZcOY2r4tW9NymJ+MdcfFFWTZqx7s26u5xXM/RVanOL123HpnE8Z2gzV5/wDZ3Kf/ADKacLQ/o1tctaP2qNNwr0f+l9KzMOj3uPeimm59/CiUcfiPwJ1DlpqlqO63M/B7NHr6GZRPm3AOM+bl9UT5vwrmNpmEmpCJ5HyAACKqopjmUzPDEXaK63aR0g2hcr9rTe1vUaarWn4sVe9VXx+3Pwpp9Z+kesPfpmm5GrZVGJi09Kuqdo/vye/TNNydXy6MLEp6Vdc7RH990d7BnbU6zxfvR0x0DO71HEXNSmirw484tz945n7KheER4Pq1PU87WtRydX1PIrv5eZdqvXblc8zNUzzL458ZW44d0Szw/p9GFa7u2fGrvn++5eXhHhyxwtpVvAtdsddU+NU9s/l5P3wcLL1PNsafg2aruRlXKbVqimOZqqmeIbRehPTvH6a9ONK0CiiIyZtReyauPGq7VHNX81Uuxd0bubk3DX1F1nG4wdLq7mHFdPMXbvrVH0XwiOI4hD3NfiOMi9TpFieqjrq/m7o933QHzq4spzsqjRMarei3117fxd0e6PnPkPH9Wd7Y/T7YOsbpv1RE4WNVVbiZ/arnwpp+8zEPYKkdvDf9nH0XS+n+Nc/tsyucrJiKvK3Tx3Yn6zz+UI74U0mda1eziTG9MzvV/LHXPyRdwdos8Qa3j4G29NVUTV/LHXPyUuy8zJ1DLv5+bdqu38m7XduV1T41VVTMzM/m/IFwIiIjaF8bdFNuiKKeyEeUJ8oRPj4QVeQ+026K7tym3bpmqu5VFFMR6zM8No3QPYljp30u0XRJtxTkzYi9lTx4zdq8aufpzx9lC+zV0+udQOq+lY123M4Om1fjcmeOYnueNFP3q4+0Suf2ouqGZ0o6a1VaDVTRqWfVGLjVTVxNvnzqiPWYhD3MnIvavmYvDuHPr1z0p+kb+yN5V75vZd7XNSxOF8KfWqnpT4bz1Rv7I3lkHdXVPYGy7Fy9ubdWBg+zjxouXY7/APux4/yYg1vtwdJdN9pTp1Go6lXRMxHsrXdpq+cVT6KCalqeo6vlXM7Vs6/l5F6qa7ly9XNU1TPnPi+bn0iHq07lJpViiJzLlVyry9WPz+bIaVyM0mxRE6hequVeW1Mfefmuhk/pAtIprqjF2FnVR6TVfofHH6QKmavHYN6I+V+OVO/H4pjn1ln6eXHDdMbfo/8A1Vfm2mnlHwpTG36PM/8ANV+a8G3O3rtDPy6bGv7az9Ot1TEe171NcRzPyWh0bVsLXNLxdX0677TGy7VN61V8aao5iWn2I7/uz48tsfSrTatI6dbc0+uua6rGm49MzMecxbhGPMjhTS9As2b+BTNM1zMTG8zHVEeKF+bHBek8K02LumxNPpJneJmZjq28Xqpjza6e2lq34/rhl4MeWnYONZj580zX/wCJsWqnimZau+0dq/6962boz4p4ijJjGjx5/wBHHd5/k6+UOP6TVrt6f3aJ+cx/V88j8Wb3ENd/uotz85iPzY3PiIhYpbVIAJtVdy/ar/guU1fzbaenWTGZsXQcmI49rp9ir86Iak6p45n7tpXZ81q3r3SHbGfanw/AW7c/WmO7/RD3OGzNWBj3Y7qpj4x/RX7n1Yqqw8S9EdUVVR8Y/oyJUmPInyRSr/3KypeB6x9Xtv8ARzbH/SHXabl2q7X7LGsW4967Xxzx8nvlZ+3jpkZXS7D1Gav/AMFn25448+97v9Wf4VwMfVNYx8PK/Yrq2nZsfCWm42r63jYOXv6OuqInZgbffbP6q7qvV2tAqsaDhT4UexjvXuPnVPh/JiDWt/b53FXcr1neOsZUXZ5qoqzK+5P+zE8fydD4yRHHqtdgaHpumURRiWKadvKN/jPWuvpfCmjaPbi3h49NO3ftEz8Z6zwnz8fqj2dH8MOQyu7OxaojqiIdjoG4db23qdjU9F1bLwr1m5TV3rN2qjnieeJ484+TbLtHVP11tjStV7/e/F4lq7M/GZpiWoa5+zVxPE8NqPQXJuZXSDal67VM1Tpdjmfj7kIZ5w4tucTHyYj1oqmN/bET9le+fGDapsYmVTTEVdKqJn2xv9nvqvJMeSKvIp8kBdytiQAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKm/pAdWqsbX2tosR4ZmbevzP/ALuiI/8A7FI581yP0hdFddOyKoie7RVncz6czFlTefJanlvbpo4bx5jv6Uz/ALpXK5PUU08J2Zjvqrmf90r9dhLWrOb0oytKomZrwNSuxV/tcVf1WUlRjsGb4x9J3PrOy8u53Y1KinJxufW5E8VR+XH5Lzx5IP5i4NWFxBfmY6q9qo98fmrlzM06vTeJsmmqNornpR5xVH57uMebk4z4S5RPLR5aEAOAIkRPhPJAq1+kP6Df5X+itzc+i4XtdybL72dizRTzXdxuP7a1+URV9aWoGxdi9birjifWPg/oiuWrV+3VZv26blq5TNFdFUcxVTPhMTHw4aXe212fMrs/dasuzhYtz/ovuiqvUtHvxRPcpiqrm5Y58u9RVPl58TTPERMP0h/BNzZ6M18Fajc2j9q1v59se5qPEmDExGTRHtYDZg7HOv2ds9qjptquRV3bder/AIOZ59b9uqzT/erhiCe5zERM+TsNr7iydnbu0HeGNRTVe0LU8XUbcVc8VVWr1NcRPy91fjmJpMazwvn6fVG/Tt1x8mq4dz0d+mqO6X9CFccVzHwlxqcMbMs6hiY+oY9dNdrJs0XqKqZ5iqKqYmJj836T4v58c+xOLlXLNXbTVMfCdkrUT0qYlESlx4cnll9BM8Eyxv1k637T6O6NOdrmVTXmXqaoxcOiYm7eqj4RzzxHMcz5Q9WDg5Go36cbFomqursiHrwcDI1PIpxcSiaq6uqIh93Vrq3tnpNtm/rmvZdMXu7VTi41M/2l+5x4U0x9fX0a1OpXUPXeqG7cvdmv3Zm7enu2LUT7ti1z7tFPyjn7zzL6OqXVHcvVnct3cO4b8xREzGNjUzPcsUfCI+PzePmeFnOCeC7PDNj0171siqOuf4Y/hj7z3rfcuOXtrhPH/SsmIqya465/hj+GPvPeiZ4ew6UdNdY6p7vxdt6XZuey78V5d+KeabVqPGZn5+kOi2xtjW9463jbe29hV5Wbl1xTTTTHhTHrVV8Ihso6AdF9M6QbTt4NNui7qeTEXMzJmn3q6/h9I8oh38a8WWuGcKehMTer/Zjw/wBU+UfOXq5i8c2eEsCbdmYnIrjamPD/AFT5R3eMvcbO2no+ytu4W29ExabGLhWqbdNNMcc8R5z85d2Cq1+9cybk3bs71TO8z5qYXrtd+5VduzvVM7zM98y+TVdRx9J0/I1LLuRRZxrdVyuqfSIjmZas+sm+8jqN1E1fcty5VNiu9NrGpmeYptUzxT/JcztldV6dm7Cq2tpt+j9Za9zj8RV71uzx71XhPPy+7X7EcREJ75TaDOPjV6rejrr9Wn+WO2ffPV7lluR/DU2Me5rd+nrr9Wj2R2z756vcAifGeExLAkR6omYjz9Ez4QyH0H6a5XU/qFgaNFmqrBxq4yMyrjmIopnmKfvPh+bzZmXawMevKvztTREzPueHU9Qs6ViXMzInaiiJmfcuJ2N+llOy+n9O59Sxu7qmu8ZE96PeoteVFP5eP1lhXt0bv/Wu9tM2tYuf2emWZvXaYn9+vjj+ULu1zh7b0Kuv3bWPg2JnjyimKYarOpe8Mjfu+tZ3XkVTP43Jqm3HpFFPu0/yiEKcA+m4j4jyNcv9lO+3lNXVEe6ndXLllRf4s4syeIMmN4o3mPKauqmI9lO7zICdFmzkjyRPlKY8gfrgW5v5+PYop5quXaaIj4zM8Nu227XsNA02zEcdzFt0/lTDU5snHpyt6bfxav2b2qYtur6TdphttwLcWsSxbp8qLdMR+SEOcl2Oji2/5p+kK2c/L293CteVc/8Aa/LW9StaRpOXqd+Yi3jWartXM8RxENSm69Wua5ubVdXuRxVmZl2958+dUy2NdqXeVG0OkWsXLd6KMnOtfhLHPrVV4f4ctaMzNU8z5z4vXyf0+bWJfzqo/bmKY9kdc/OWR5D6VNvGydSqj9qYpj2R1z85hACZFggAEVRz4fGGwzsS6x+sOjlnBqr71WnZNyzxz5RzzH+LXnK4PYH3H3Kte2tN6nvV10ZdNNU+nHE8I/5m4k5XD9yqntommr57T9UVc49P/TOGK7kR126qavntP1XNlFKYR5Sq9CnKfVXrtwxH+RXJmfP8bj8f78LCq5dufKptdHpxpmO9ezbHH2qiW08ERNXEOJt/HDbeBKZq4kwoj/8AZS1/x5I/5pR68LcL2wepT5JI8hy41RzFX0bTegNuq10f2pbrjiadMsf8ENWlqiq5cpt0xzVXVFMR8Zltl6Z6f+q9jaLp8UzTFjCs0xE+fHchD3OG5EYGPb75qmfhH9VfufV6mMPEs981VT8I/q9PV5FPkmfJFPkr/wBysqQHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACsvbz0Kc7pppeuWrXeq0vUY79X8Nu5TNM/3ooUM+bap1r2Za35011zbtdn2ly/jVTZj4XKfepn84hquvWb2NeuY2RaqtXbVc0V0VRxNMxPExMLI8p9RpydHqxJn1rVU/Crrj57rX8jtUoydEuYG/rWq5n3VdcfPd3vT7eOXsDeWk7tw+Zq0/JpuXKY/ft8+9T945bTtj7v0rfG28HcOkX6btnLs0180z5TMczDUhPksN2Vu0JV041SjaG5b3/UmZc4t3ap8MeuZ/wd/MfhSrXcSMzFp3vW+7xp8PbHbHvejm5wVXxBh06jhU73rUdn8VPbt7Y7YbCJjmHGOYfhpupYeq4drPwMii9YvUxVRXTPMTD6fNWmqmq3VNFUbTCpVVM0TNNUbTBE8iO78DnjzfOz5SiU8x8Q7BET6MNdrPs+YHaO6P6hs6mizb1/A5z9By66Y5tZdMf6OavOKLke7V48fs1ePdhmbjx5PGJiYnxhm+HNfzeGNUs6rp9c03LdUTEx5d3vdd61TfomiuN4l/PHm6bqWhalmaDruDewdT069Xi5eNep7tdq7RPFVMxPlMTEvmy5iuzVRPwbM+332ItydT9wYnVroloVrK3BlTRja3ptFyi1+KiPCnIiapinvRHEVePjERPnHjiDYv6KfrLuCinJ33vfQdsUTTTVFizRXmXfnE8d2KZ+8v2A4Z/FLwRqXCNvL1jLpt3qqOjXR21b7bT1drQb+h5NGRNNqneO6V9eyJvez1D7MXTjdFE1e0nRben3+9PNU3sSqrGrmfrVZmr7suMW9m7oVi9nTpfi9M8HcuXrdjFyb+TRfyKIommbtXeqppiPKnvTM/eWUe9xHMvyP44ysHP4izMnTJ3sV3Kppns3iZ37G941NVNqmK+3ZPzcK7lNFM111RTTHnMvFdROsWxOmODOZurWrNiqaebdiJ7125Pj4U0x4+nn5KWdY+19vDftd/SNpe10XSKpmjv0z/b3aefPvR+zzHpDt4c4J1PiKqKrVHRt99dXVHu8Z9jfuFuAdY4quROPR0bXfXV1U+7xn2LA9c+1ztzpzVe0HaXsdZ1uImmYpnvWbFXxrmJ8fXwj4eiiW7d27h3xrl7ce6tTvZ+den9u5VzFFPpTTH7tMfCHU111111XLldVdyueaqqp5mZ+comfBYvhvhPT+GbXRxqd7kx61c9s/lHlHvWt4Q4D0zhCz/w9PSuzHrVz2z7PCPKPfucuy27tzWd2avj6FoOFcyszJqimmimPL5z8IfZsnYW6uomt2tA2pplzKyLtURXXx/Z2aZnjvV1ekNhXQbs67e6TaRbv5FunL1u9RE5OVVHjz8KfhHLz8V8X4nDNj1piq9P7NP3nwj6vJxzx/g8IY80b9LIqj1aY+s+EfV8/Z47O2j9J9GtahqFFvL17JoirIyJpj3Jn92n4RDNxEcRxAq5qmqZWsZNWXl1dKqr+9o8lONW1bL1vLqzc2uaq6vH6R5Drtwa5g7d0jK1nUb1NrHxLVV25VVPERFMTP9HYzPEKfdtTrdTZsU9K9AyYm9e4ualXRP7NHjxb5+M8xM/L6vfw1oV7iHUbeHajqnrqnwpjtn++9kuE+Hb/ABPqtrT7MdUzvVPhTHbP5eatnWjqRl9Ud/ahuS7XX+FiubOHbmfCizE+Hh8Z83hjjiOPgLd4mLawrFGNZjammIiI8oXr0/Bs6Zi28THp2ooiIiPYeRAifg9D2Jopru100W6Jrqqnu00x5zPwbE+yT0jq6d7Eo1TVMbuarrHF+93qfeop/dp+0K0dknovd6g7wt7r1jEqnQ9GuxVTNUe7fvxxMU/OI55n7NhVdVjAxZrqmLdq1TzPpFMQhDmpxNFW2iY079k17fKn7z7lbudHGEXao4ew5322m5t491P3n3MEdsPqVGy+m1/RMO/NvUNdicazNNXExTzHfn8plrwZY7S3VC/1O6lZmRYye/pWmVTjYNMeXEcRXV8+ao5+nDE7feBdB/wHR6LdcbXK/Wq9s9ke6Pnuk3ljw1/8b0K3Tdja7d9er39ke6PnuANySIifJIA9D05pmrqFtemPHnWcP/61LbRj8RZo+Hdhqd6XR/8AeTtaOOf+uMT/AOrS2l7p1/E2vtjO1/Mri3Ywsau9VMz5RTTygrm9RVfy8OzRG8zFW3vmFZOetNWRqmHYtxvVNMxHtmqNlOe3Tv2jUdf07Y+Hf5owqfxORET+9PhEKpvQb/3dmb63jqu6c2qZrzciqqiJ/do592Py4efSzw3pMaJpdnC76Y6/bPXPzTnwZodPD2iWMHb1ojer+aeufmAjmWcbQkREwTIJZY7Lm8Z2h1g0m5duxRj6jM4dyZnjxq8v5sTx4v0xMu9p2bj6jjVzRexbtN+3VHpVTPMf4PHqOHTqOJdxK+yumY+MMTrum0avpt7Cr7K6Zj5Nw9uumuiK6fKY5hMw8d0j3rg782FpG4MO7FXt8aj2kc+NNcUx3on7vZT5KZZmNXhZFePcjaqmZifcoFl41zCv1492NqqZmJjzidj5qldvrW7dG3dC0Km5Hfv5NV2qn5Ux/wA5hbSJ8Gvbtsbs/X3VajQ7N6KrOiWO5VEeldcRVP8ALhvHLLBnL4gt191uJqn4bR85hIfKXTqs/iezXEbxbia593V9ZhXxEftJnyRC0K6BPklHnP0JB6bpfoN3c/UXbei2Yj/ONTsTVzHMdymqKqv5RLbDh49GLj27NuOKaKYpiPhxHCgfYj2RXuDqVf3LftzOLouPPdnjw9tV5ffjlsDiOIV55u6lF/UbWFTP+XTvPtq6/psqdzv1WnL1u3hUT1Wqev21df02J8iPInyERoVAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPUPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABPkAIqpiqmaZ8pa8O170lvbF35d3RgY006Vrtc3eaY923e/ej7+f5tiDyHVHpxoPU/aeXtzXMam5FyiarFz961d492qPu27gviSeGtTpv1/5dXq1x5ePtjtbvwDxZVwjq9OVV12qvVrjynv8AbHa1QomOXq+pHTncPTLct/buv4tdE0zM2LvHu3aOfCYl5Sfktfj5FrKtU37NUVU1RvEx3wu1h5ljULFORj1RVRVG8THZMM3dCu09ufpNet6Pq/tdV0CqribVVUTcsR8aJnzj5SvP086y7D6l4NGVtrW7N27VHNdiqe7con4TE+LVVz6S+vStW1TQ82jUtF1HIwsq3PNN2zcmmqPyaLxPy907iCqci3+rvT3x2T7Y+8Iy4x5U6ZxLXVl40+hvz3xHqzPnH3huCiqKv2Z5S1y7L7YfVvatNvH1HMta1j0ecZMcVzH/AHoZq252+dq36aaN0bWzcKuKfeuY9UXaZn5R4SiDUeWOvYUz6KiLkeNM/adpQTq3KPiXTKp9Hai7T40T9p2lbAYJ03tn9Es+mJr1XPx6p84u4sx/V21Pax6IV096N1zHymxU1u5wnrdudqsWv/bLU6+Edetz0asO5/sq/JmAYN1HtkdEMCnn9eZeRM+UWcWqr/k8drvb06f4lfd0Hb+p6hE0/tVxFrifpPL04/BWv5U7UYtfvjb67PXi8CcSZlXRtYdfvjb67LR8xHq4XL1q1TNd25TTTHnNVXEQohuft3b/ANR71rbe38DTaPS5cqm7Vx9J8GIN29dOqm9Jrp1veOdNm5zE2bNfs6OJ9OKePD6tt0/lPq+RtOXXTbp9vSn4R1fNu+lcktfzdqsyqizT5z0p+EdXzX+3/wBpDpX08i5a1bcmPfyqP/Vsar2tzn4cU88fdV7qf24d3bmou6X0+0v9R4lXNP4y/wB25kVR/q08TTR/OforL5zMzMzM+szzycpL0XltoukzFy7TN2uO+rs/29nx3S9w/wAn9C0aqm9kxN+5H8X7O/8AL2fHd9eqatqmuZ13VNa1LJzsu/V3rl6/cmuqqfrL5JJn18nd7S2TujfWpU6VtXR8jPv1zxM26Zmmj51VeUN8rrtY1vpVTFNNPuiI+yT67mNp9maq5iiimPKIiPo6Nlrox2ct59XMq3l02bmmaHFUe0zbtHjXHPjFumfOfn5LA9GuxPp2kV2Nc6l3qM/JpiK6cGj/AENE/wCt61LVadpeBpOLbwtOxbWPYtRFNFu3TxTEfCIRJxVzQsYkVYukevX/AB/ux7PGfl7UFcac5rGNTVh6B69fZNyf2Y/ljvnz7Pa8j0u6Q7Q6UaNTpW2sCmiqY5vZFfjcvVes1S9wCBsvMv596rIya5qrntme1W3MzcjUL9WTlVzXXV1zMzvMhM8DqN0bm0naWi5Wva1lUWMXEtzcuV1T4REOq1arvVxbtxvM9UQ6bVqu/XFu3G9U9URHfLxnXTq5pfSbZmTq+RXTczbtM2sSzz413Jjw+0ectZWuazqG4tXzNc1W/Vey867Veu11T4zVM8vcdcOsOq9X94ZGrXKrlrS7Fc0YONM/s0fxTHxljlaXgXhSnhvB6V6P11zrq8vCn3d/muXyz4Kp4U030t+P+Iu7TV5R3U+7v8wn4ImfSE+TeUmInwh6Tp1sHWupe7cLaeiWpm5k1x7a7x4WbXPvVz//ALzdFgYObqmbZ07T8avIycmuLdq3RHM1VTPEQ2NdmroTidKtsW87UseirXdQopuZNzjxo5jwoj5Q1HjHii1wzgzcjru1dVEefjPlCP8AmFxpZ4R06aqZ3v17xRH3nyhkXpzsTSOne08Da+j2It2cS1TTPHnVVxHeqn4zM+MyxH2vOsVvYeyrm2NMux+ttbomzT3ao71q1P7VX9GXeom+9F6d7Uzd0a3k02rOLbmqmJnxrq48KYj1mZaw+pPUPXOpu68zc+t3qqpvVzFi1M+Fq1z7tMfZD3AHDd7iPUp1XO67dFW87/vVdu3n4z/VAnLLhO/xbq86tqG9VqirpTM/vV9sR8euf6vKzM1TNVUzMz4zMgLHrdRG0bQCPGDkcpnyCfIB6Dp1emz1C2vcieP+ucOP/nUrVdtPrF7HTcPpnomTEXMmmnIzq6KvK34x3J+s8fblT7Ss+5pOqYWq2KYm7g5FvJtxP8VFUVR/OH0bh3Bqu6dZydd1rKqv5WVX3qq5+HpH0hr2oaBa1LU8fPvRExZido8522+Hb7Wlatwnb1jiDF1W/tNFimdo8at+r3R2+3Z13kBz6NhbqfYPCDn5AiY5RMcJ5+B4TAFJMIj4w5Atd2IurtnRs7J6baxkcWsqucjBqqnwiqeIqoj8ufvK70TFVPMeUtP2javn7f1bE1zS7s28rBu03rVUT5VRLZd0F6z6R1X2fj5tN6i3qONTFrLszV401xHjP0lAXNHhaqzkf4xjU+rX+3t3VePv+qrfOXg2rCzP8cxKf1dz9vbuq8ff9fa9xvPcuJs/a+o7kzrkU2cGxVdqmfk1T7x3Ll7w3PqW5s6qar+ffquzz8PKI+0RC1XbV62UXrP+SvbuXE+0mK9TuUVfu+E02/vPEz+Snja+V3D1Wm4FWffp2ru9nj0Y7PjPX8G7cl+F7mlafXqmTTtXe26Pj0I/Oev4CJ8IJng45nlKSbiPIiKq6ooopmqqqYppiI85nygmfRnvsndEsrqJuyzu3VsSZ0DR7sV+9Hu370eMUx8YifGWP1XU7Gj4debkztTTHxnuiPOWG1/W8bh7T7mflTtTTHxnuiPOZWu7LPS+rpv00xKM6zFGpanxl5U/vRNUeFM/SOP5syuNq3Rat027dMU00xxER6Q5Sp7q2o3dWzbmZen1q5mf6e5Q7VtSvaxnXc7InequZmff3e5HnP0SRHAx7HAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8B1Z6NbQ6t6LXpm4cTu36aZ/D5VriLtmr40zx/Jr76w9Bt49IdXuWsvGu5+kVVT7DPtW57vd+Ff8Mtob4tV0XStaw7uBqmn2MrHvU92u3dtxVTVHziW9cJ8dZvDVXoqvXsz20z3edM930lIfBfMTUeEbkW95uWO+iZ7POme76NP31g4hfHqh2JNo7jnI1TZOVOi51XvU2OO9Yqn6en2Vi3h2ZesGzrtUXtsXc+xTM8X8SYriY+PHnCe9G430bWqY9Feimr+Grqn59U+6Vm+H+ZPD/EFEejvRbr/hr9Wfdv1T7pYr4n0k8fg+rUtK1LSL34fVsDIxLv8ABetzRP8AN8rbKaorjpUzvDebd23dp6VuqJjy6zn5J5mfijn5wc/Ry+0niiZ49Ud+JrptxzNVU8RTETMzLl81V00RvVOzkiZ4l6nRelvUbcdUU6LszVMjveU+wmiPrzVwyzs7sW9UdertXtd/DaRjVTHe79XtLkR9I9WIzte0zTaZqyr9NO3dvG/wjrYDUuLNE0mmasvJop27t4mfhHWr75ePBHEz5xHzn0XnxuwnsvC0LJtXdXzM3VLlqYovV1dyimr04pj/AJqab12brGwdyZu2NbszbyMO5NHM+VdPpVHy4eLROK9M4huV28GveafGNt48YjwY/hvjrSOK71yxp1czVR4xtvHjEeCyHRfsZWd06Zjbn3prPexb0U3LeLi1cRVTMcxzVx4+fot9svp7tLYWl2tK2zomLhWrccTNu3EVVT8ZmI8ZYO7E3UyndGxrmz867H47QpiiiJnxqseVE/y4+yyqvvHWsaxc1K7g51yejRPVEdUbd07exVvmLrOu39Xv4Gp3Z6NFU7Ux1U7d07eceJxwImZ5THi0JHQCKqoppmqfKAfnkX7WParv3q4ot0R3qqpniIhr97VfaIu9SNZubK2plTG3dPucXr1FUx+Mux8/WiJjw+M+Pwe07WnaTv3r+Z0t2dl1Wopn2ep5FFUxVx/2cTH81Q44jwiE/cuOCP0SmnWNQp9eeuime6P4p857vDtWU5TcuvQRTr2p0+t226Z7v9U+fh4drkiefQ5+EJTIsOiI4RMz4cUzMzPERHnMv0tWb2TdpsY9uu7cuTFNFFFPM1T8IiFsOy/2W87L1LH331F0uqzj2Ji5hYV6PGqr0rrj5eHEMPrmu4egYtWVl1dnZHfVPhH99TW+JuJ8HhfBqzMyqN4jqp366p8Ij+9nqeyP2cp0PBtdRd8afNOp5MRXg49yPHHtzH7UxPlVP8vrytBr2u6XtrScjWtYyreNiYtubly5XMRFMRHP9H5a7r2ibQ0a9q2sZlnCwsSiaqq657tMRHo199ortIap1Z1GvRNCuXcTbuNXMU0RVMTkzE/tVR8PhCv+FgapzI1arKveraieue6mP4afP/3KrumaVrHNfXKsvImYtRPrVd1FPdTT5/8AuXW9ozr3qPWPcf4bT67uPt3T65pxbEzMe3qiZ/ta4+MxPhHpH3YfBYvTtOx9KxaMTFp6NFMbR+c+c962WjaPiaFh0YOFT0aKY/uZ8570TJ4p9T6PayiI59SYSA4+XkmJ9DiDmIBIjmfSDiZ9QSjyOYjwfth4eXqOXZwMDGuZGTfqii3at096qqqfhBMxEby+a66bdM1VztEIxMTL1DKtYWDj138i/VFu3bojmaqpnwhb/a3Yps6h0ruXNVy5s7myrf4m3X+7aq7vu2+OPL4vRdl7swRtOm1vffFi3d1W5T3sfGmOYx4n4/63+C08UxTTFNMRER4Rwg3jbmNctZNOJo9fVRO9VUd8x3R5ePirTzD5r3py6cLQbm1Nud6q4/emO6PGnx8WoHXdB1ja+sZWga9hV4udh3KrV23VHlMesfGPhL4J+MNkHXvs27c6sYtzV8WKcHXbVEzbyKKY4ucR4U1/GFA98dPt1dPdUr0vcul3saqKpi3cmn3LsR60z6pD4V4xwuJrEdGYpvRHrU/ePGPolfgfj7A4txqael0b8R61M+PjHjH073m4SjmEtvSCO92fvjc+w9Qr1La2rX8G9cp7lz2dXEVR848pdEjmHxdtUX6Jt3IiaZ7Ynrh05GPZy7c2b9MVUz2xMbxPufTqOoZurZt7UtRybmRk5Fc13LlyrmqqZ+cvnOUTy+qaYpjo09jsoopt0xRTG0QcePJMz6Oz0HbG4d0ZdOBt7R8rUMiZiO5YtzVx9Z8o+6znR3sT6zn5GPrfU25Tj40d25Tp1urmqr14rqjy+kMNrHEOnaHam5mXIie6P3p9kf3DW+IeLtJ4Zszcz7sRV3Ux11T7I/uGHOiHQjdHWXXqLWNYuYmiWKonMz6qfCY/go+NU/lH8myPZGy9D2Ft3E23t/Dt42Ji0d2mmmOOfnPxn5vq23tjRNqaZZ0jQtOsYeNZpimmi1RFMcR9Haq3cY8aZPFF6KIjoWaeyn7z4z9FSOOePczjLI2n1LFM+rR958Z+gImeClpGzQUgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA41W6K44qpifrDkETMdh2Oh1vYu09xUzRrWgYWXFUcT7S1TLwGs9lXojrUzN3ZmPY5nnnHrqtTz9aZhl0ZPE1rUcDqxr9dPsqmPuyeJrWpYEbYt+uj2VTH0lgS52KehlU8/qPKj6Z17/AMyI7EvQrmJnQ8ueP/397/zM+DJxxlr8f/l3P90spHGnEMRt+m3P98/mw/pPZP6HaTERRsyzkTH/ALRcqu/8Uy9jovSTpzt+nuaPtDTcamau9xRYp8/i9ePBf4g1XK6r2RXV7ap/NjcjXdUy4mL+RXV7apn7vxtYeNYpiizYt0RHhERTEP1imI8oSMVVXVXO9U7sXMzPaeHkrb2uuhNvfG3bm9NBsxGsaXRNVymmnxvWo8Zj6wsk43LdN2iaK6eaao4mPjDKaJrGRoWdRm489dM/GO+J9rMaBreVw7qFvUMSdqqZ7PGO+J8pauegXUHI6YdUNO1auaqLGRXGFl0zPEdyqqPGfpMQ2hYWTbzMSzl2p5ovW6blM/KY5Ud7XHZ2yNvZ1/qTtDFmvT8mua87Hop8bNczz3449Gaux/1Yq3/09taLqFyKtQ0SmMauZnmarcRxTP5JP4+tY/EmmWeI8Dr29WuO+PDf2T1fBLfMujE4s0uxxXpnd6tyO+nw39k9XsmGfao9SnyT5uMeEob7UFuUxyTTFUTTMcxPgDgYB6g9jbplvnXcncVNeXpmbl1d+9XjV+FdXrM0zzDxOX2ANtVRM4e+dQo+EV2aKv8AktocQ23F464gw7dNq1k1dGmNo32nq98S3DB4/wCJNOtRYxsuqKY7I6p+sSqVifo/9t0zE5m+tQuR8KLFFP8Azeh0nsK9KcO5Fep5epajEedNy93In/d4WU8IfPnahhabjXMzOybVizapmuuu5VFMUxHrMy7bnHnEeT6n6TV1+ERH0h33OYvFWTHo5zK+vw2j6Q8Js/oP0t2NNNe39p4lm7RHHtaqe/XP1meZfv1N6vbL6SaLXqe48ymmYpmLGLb8bl6r4U0/ePHyYU62ds/Qtv0X9C6b+z1XUY5oryqv9Ban5fxT9PBS3cu6dw7w1W9re5tUu5uXfqmqqqufCPlEeUR8obfw9wDqfENyM7Xa6oo8Kpma6vj2R5z8G98KcsdX4qu05/ENddNrwqmZrq+P7Me34PddZuvu7usefV+PuVYWk26pnHwbdXhEfGuY/anwYwj4QePqc/BO2DgY2m2KcbEoiminsiP7+azOmaXh6PjU4mDbiiinsiP76580o5+D9MXFyc7JoxMSxcv37s92i3bpmqqqfhEQsj0f7GO6t13cfV9/97SdLq4r/DUzHt7lPz/h/wAXl1bW8HRLPps65FMeHfPsjtl4de4l0zhuxN/UbsUx3R3z5RHbLBWyNhbp6hazb0Ta2l3cu9VVEV1xHFu1TP71dXlELp7D7F209C2zetbhu/j9ZzMeqi5fn9i1Mx5UR8vj5s77G6fbW6eaLa0LaulWcLGtx+5T41z8ap85n5y9JwgXiXmbm6lc9Fp29q3E/wDNV7fD2KxcYc3dS1y76LTN7Nmme6fWq8N57o8o98y1J9Qdmaj0+3hqO09TtVU14V2qm3XMeFy3z7tUfWHnZbRerfQbY/V7B9nr2FNvNtxM2MuzPduW6vr6x8pVW3H2Ed/4FVyvb2vYOoWome7F3m3XMenxj+aR+HuZOk6jj0051z0V2IiJ6XZM+MT5+aWeFObujajiU29UueivRERO/ZM+MTHj4SrFH1colmmOx91w780RoOJ4Txz+Lo4l3uldh/q5m085+RpWB/3701/8MNnucWaHajerKo/3RP0ble4/4asR0q82j3Tv9FeUfzXB272BK4qt3ty72rrjn37WLYiImPlVVP8ARmHZvZH6PbSuWsyrQf1nl2vGLudVNzx/7v7M/k1/UOZug4UTFuubk/6Y+87NW1PnNw3g0z6Cqq7V/pjaPjO33UW6cdFuoXVPOt4+2dGrpxKq+7czr8dyzb+PjP7U/KF5OhvZe2p0kpt6vmTTqmvVU8XMq7RHFHh4xRHlTH82ZtP0zD0zHpxsLHt2bdEcU00U8REPr4hEfE3MbUNdpnHsfqrM90ds+2ftG0IM4w5parxRFWNa/VWJ/dieuf5p6t/Z1QimmmiOKaYiPkkEddqMCYifCXRbr2Rtjemn1abuPR8bNszExEXbcTxz8Hejts3rmPXFy1VNNUd8dUu2zfuY9cXbNU01R2TE7SqhvnsJbZ1O9cytm63f0qu5zPsqqfa24n6TPP8ANinVuwz1fwaqv1ZmaRqNEeUzem1VP2mJj+bYL4ImaY8ZnhveBzL4gwqYom5FcR/FG8/Hqn5pE03mxxRp1EW4vRXEfxxE/PqlrQyeyV2gse7NunY1F2I/eo1HHiP71cS7HR+xt141Snv5W3sLTqeeOcjPt1f/AE5qbDtT3DomjWpvapqWNi24867t2mmI+8yx1uPtN9G9s1XKMveGLfuW/wBqjG5uzz8PdbRjcx+J9Qp6OLiU1T400Vz/AOTasTmxxnqUdDDx6a58abdU/fZWnQuwLvjN4r17emn4FPPjTjWJv8x9Zmn/AAZY2j2Gul+jXLeRuHJztauUTE929c9nRz9KOOY+r5NZ7eXTrEuV2tH0PU8/j9mvuxbpn/e8XgtY7f8AuCqq5TomxMeimf2K72XM/nEU/wBXquTzC1mOjt6KmfDo0f8A+nrvRzR1+JpmKrdM+HRo/qt9trY+09n4lOFtvQsTAs0+EU2rcR/N3scRHg156j23Os2d3ox40fEpmfd7mNVVMR9Zq/o8tm9qrr9mxVTO/q7NE+VNrCsRx9J7vLERyq17Mqm5k3qN57ZmqqZ+ksRHJjijNr9Jk3KOlPbNVUzP0ls170IiumZ8Ko5+HLVdldeOtGZMze6kav4/wXIo/wCGIfRs/r91Y2fuLH1+neOo6hTbni9jZd6blu5R6xxPlPzh31cns+m3NUZFE1bdUbT1+W/c9NzkXrFFqquL9E1RHVEb9c+G7aX5o8peK6SdT9I6q7RxtyaXVEVVx3b1rnxt1+sS9rMeCJsrEvYN+rHyKejVTO0whjMxL2Bfrxsino10ztMT3TCRET4peaXmAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB82o6dharh3dPz8ei/YvUzTXRXHMTE+aq8dM9S7OHWbH3ntTFyL+y9euRj6nZt0zVGFNU+Ffh5URM+foti/HLw8XOx68XMx7d6zciaa6K6YmKon0mGd0bXb2k+kszHStXI6NdPdMePlMdsT4svpms39NouWIne1cjaqnunz9sd0udm7bvWqbtmuK6K4iqmqJ5iYlyqcMexaxbNGPZpimi3HdpiPSH6MHO3S6uxiZ236gBw4AAdHvXcF/a22c/XsbTMjUbuJZquW8bHpmqu5VEeERENbPVztAdS+peo5GHuPKv6TgxXNNOl0c24pjx/bifGZ8Z820GqmmuJpqpiYn0mHn9f6ebF3VRTb3Hs/RtSppnmn8Vg27vdn4x3onhvPBnE2ncOXarmZi+kqnsq366fZExt7+qW98EcV6fwtkTkZWJF6ruq366fZExMb/BqQiqnjwmOEe0t88TXHP1bR7vZy6K3K+//k60WmZ9KcOiI/KI4ffpvQ7pHpVyLuJ0529FceVU6damqPv3Un1839LiN6bFcz7o/NMtznzptNG9rFrmfCZiPn1/Rq80nbu4Nfuex0LQs/Ua4mImnGx67sxz5c92J4Zp6c9jzqdvDKt3Ny4//R7Aniaqr0d69VHyiPCPvP2bB8bQ9HwqYowtKxLFMeUW7VNMR+UPtimIjiPKPRrWp83su9TNGDZijfvmelP0iPlLU9Y556nl25t6dYptb98z0p93VEfKWKelXZw6ddLrNF3T9KozNRiI72bkxFdzniPKfTxjnwZWppppiIpjiI8ISIqz9Sy9UvTfy7k11T3zKGdR1PM1a/OTm3JrrnvmdwB4XhDiPgAHEHEAbhxAAAAATPDzW8uoe0NhaZc1bdGt42FYt/x3IiqqeJniI85nw8ndj413KuRas0zVVPZERvLusY93KuRasUzVVPZERvMvSTMOm3BvDa+1cOrP3Dr2Bp9inwmvIyKaI5+HjPmp71V7c+rZ1d7SulumU41nmaf1ll0z35jxjmijn6TE1fkrFuTde5t4Z9ep7q1/N1TIrmZ72RdmqKflTT5Ux8ojhKug8qM/NiLupVeipnu7avh2R7+vyTHw1yX1XVIi9qlXoKJ7u2v4dke/r8l3d+9uTYm379zB2jgX9dvU+EXYibVnn5VT4z+X3YA3f2xesG55u2sDOsaNjXI4ijEo96P9qeZYN+kCV9L4E0LS4jo2Yrqjvr9afh2fJN2jcruG9GiJix6SuP3q/W+XZHuh2etbp3NuS5Xc3BuDO1Cqueaov36qon7c8Oqpppoju0U8RDkNuot0WqehbiIjwjqhvtjGs41PQs0RTHlGyPFIjmPi+nelHickAcR8Ez5ACxfYv6pUbS3xXs7UL/cxNb/0XenimL0eUfeGwKJiY5ieYaftE1K7o2t4OsWapi5g5NvIpmJ4nmmqJ/o2w7B3Hj7s2hpWv41cVUZmLbucxPPjNMK/829Fox8q3qdqP8zqq9sdk++FWOd/D1OFqFrVbUdV2Nqv5o/OPo76fCXJFSY8kPILAHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASAK+9pTtLUdJJo21oeJGTrmXa9pTNf7FmifKqfj8o+Sh+797bo31qler7p1e/m365mYiuqe5RHwpp8oWG7ee3MnE3xo25abVU2MzGqx6q+PCKqJ5iPymfyVdjxnmVouXekafi6PZzceiPSVx61XbO++0x5R5LicqNA0rG0KxqOPbibtyPWqnrnffaY8ojwgjy4jwIj4p5hEzwkBK6RHPgjxkHLmHGZ+Ce6eEAjmT3pcvsjmPWqIHBxPrJw527N+9PFmxduTPlFFEz/g7nSNi7117n9TbR1jN4/7HDuVf4Q+K7tu1G9dURHnOzzX83GxY3v3KaY85iPq6TwOYZM0zs0dcdWt+2xtg5Vunjn/ADi7RZn8q5iXp8DsX9dcyOcjSdMw/wD32fRP/B3mJvcRaRj9VzJtx/zR+bX8njjh3Dno3sy3E/zRP03YKq4lsO7FO7Lev9IremVXJqvaPk14tUTP7vhNP8pYCtdhLqtcj+21fRbfPnxdrq4/urGdmLoLrfRDTtWx9Z121n16pdpu9y1b7tNuYjjz58ef6I55h69omraNVZs5FNVyJiaYjr8p+Uom5q8V8Pa/oc4+Hk013aaommI39k93hMs5T5IpSRHCvncrOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcyDmJmOwAHAwt2rem9fUHphl/grUVZ2mf53Y8PGe741RH1jlrbmmuiZpuUzTVTPExMcTEtxN+xbybNdi7TFVFdM0zE+sS1s9qHpPe6a9QsnIxLE06Rq9c5GLVEeFNUz71Hlx4T/JOnKbiGmaa9GvT1/tUfePv8Vi+SHFFNPpNByJ7fWo/8o+/xYbnw8UeMuXmj+UJuWQOIhL0Ozenu89/51Gn7R2/l6hXVMRVcoon2Vv51Vz4RHhPqtL087B9FNuzn9Rdwe1u+FVWHgzNNEfKaqo5n7RDAazxRpegx/xt2Iq/hjrq+EffZqXEHG+icMxtn3oir+GOur4R2e/ZT7Ew83UL0Y2n4d/LvVeVuxbmuqftDKm0Oy91h3hbtZGPt78BYuTHv5tXs54+Pd81/tkdHun+wManH27tzDs1Rxzdm3E11T8Zq85ezotUURxTTFP0hFWrc3rkzNGmWYiP4quv5R+coV1vntkV1TRpFiKY/ir65+EdUfGVN9o9gSZrt3957xucc81WcK3ERMfDvVeLLu3ux/0T0Kmibu3J1G7RPPtMu5VXPP24hm7iIGgZ/Hev6hM+kyJiPCn1Y+SLtT5g8SarM+nyqoie6mejHy2eb0rpzsbRKaKdK2npeNNEcRNvFopn8+OXoKMe1bpiii1RTTT4REQ/Qaxdy79+d7tc1e2ZlqV7JvZE9K7XNU+czKIpiPJPHzB0by6TiDjgHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAxz106U4PVnZOToVy3bjNo/tcO9MeNu7ETxP0nyn6sjD14Obe07Ioysedq6Z3iXs0/Pv6ZlUZmNV0a6JiYnzhqW1XpvvXSN4Xdi5GgZder27ns6bVFuZ78c8RXE/wAM/FZzpB2Iqq5x9b6nZcV0zFNdOnWKpiPpXV6/SFv69D0q5n/rOvT7FWX3e57abcd/j4c+fD7oiIjiElaxzV1HPxqbOJT6KdvWmOuZnv28I+fmlbXecus6niU42JEWZ22qqjtmfKe76+bqNubU2/tPTrWlbe0jFwcWzHFFFm3FMR+Tt4jgEXXb1y/XNd2qZme+UQ3btd+ublyZmqe2Z65AHW6wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+wev2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQkgPX7B6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6/YPX7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABISQHr9g9fsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEhJAev2D1+wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEkB6h6/YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJCSA9fsHr9gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkJID1+weoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASEgiPOUgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQP/2Q==";

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
const LANDING_PAGE_ETAG = 'W/"landing-v2.0.3-20261001"';
const LANDING_HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800",
    "ETag": LANDING_PAGE_ETAG,
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
    if (ifNoneMatch && (ifNoneMatch === LANDING_PAGE_ETAG || ifNoneMatch.includes(LANDING_PAGE_ETAG) || ifNoneMatch === "*")) {
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
    <link rel="canonical" href="https://gymassistantapp.ir/">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
    <meta name="author" content="ابوالفضل صمدی کوچکسرائی">
    <meta name="publisher" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov)">
    <meta name="application-name" content="نِمُو">
    <meta name="theme-color" content="#090A0E">
    <meta name="msapplication-TileColor" content="#DC2626">

    <!-- Open Graph Meta Tags (Telegram, WhatsApp, Social Cards) -->
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="نرم‌افزار مدیریت ورزشی نِمُو | Nemov">
    <meta property="og:title" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov) | نسخه ۳.۳.۰">
    <meta property="og:description" content="سامانه یکپارچه مربیگری و اتوماسیون باشگاه؛ پرونده سلامت، بانک حرکات با ویدیو، طراحی تخصصی رژیم غذایی، حسابداری مالی و صدور شناسنامه چاپی.">
    <meta property="og:url" content="https://gymassistantapp.ir/">
    <meta property="og:image" content="https://gymassistantapp.ir/images/yalda_logo.jpg">
    <meta property="og:image:secure_url" content="https://gymassistantapp.ir/images/yalda_logo.jpg">
    <meta property="og:image:type" content="image/jpeg">
    <meta property="og:image:width" content="600">
    <meta property="og:image:height" content="600">
    <meta property="og:image:alt" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov)">
    <meta property="og:locale" content="fa_IR">

    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov) | نسخه ۳.۳.۰">
    <meta name="twitter:description" content="سامانه یکپارچه مربیگری و اتوماسیون باشگاه؛ پرونده سلامت، بانک حرکات با ویدیو، طراحی تخصصی رژیم غذایی، حسابداری مالی و صدور شناسنامه چاپی.">
    <meta name="twitter:image" content="https://gymassistantapp.ir/images/yalda_logo.jpg">
    <meta name="twitter:image:alt" content="نرم‌افزار مدیریت ورزشی نِمُو (Nemov)">

    <!-- Favicon -->
    <link rel="icon" type="image/jpeg" href="/images/yalda_logo.jpg">

    <!-- Structured Data JSON-LD Schema.org (SoftwareApplication, SportsActivityLocation, Person) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "SoftwareApplication",
          "@id": "https://gymassistantapp.ir/#software",
          "name": "نرم‌افزار مدیریت ورزشی نِمُو",
          "alternateName": ["Nemov", "Nemov Sports Management Software", "همیار باشگاه"],
          "applicationCategory": "SportsApplication",
          "operatingSystem": "Windows 10, Windows 11",
          "description": "نرم‌افزار مدیریت ورزشی نِمُو (Nemov)؛ شامل پرونده سلامت، طراحی تمرین با ویدیو، رژیم غذایی و کالری‌شماری، حسابداری و صدور شناسنامه ورزشی چاپی.",
          "url": "https://gymassistantapp.ir/",
          "image": "https://gymassistantapp.ir/images/yalda_logo.jpg",
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
            "@id": "https://gymassistantapp.ir/#author",
            "name": "ابوالفضل صمدی کوچکسرائی",
            "alternateName": "Abolfazl Samadi",
            "image": "https://gymassistantapp.ir/images/developer_photo.jpg",
            "email": "gymassistantapp.support@gmail.com",
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
          "@id": "https://gymassistantapp.ir/#yalda-gym",
          "name": "باشگاه بدنسازی یلدا",
          "alternateName": "Yalda Gym",
          "image": "https://gymassistantapp.ir/images/yalda_logo.jpg",
          "url": "https://gymassistantapp.ir/#partner-gyms",
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
          "@id": "https://gymassistantapp.ir/#author",
          "name": "ابوالفضل صمدی کوچکسرائی",
          "alternateName": "Abolfazl Samadi",
          "image": "https://gymassistantapp.ir/images/developer_photo.jpg",
          "jobTitle": "Software Developer & Architect",
          "email": "gymassistantapp.support@gmail.com",
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

        /* 7 Features Grid */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
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
        @media (max-width: 1024px) {
            .nav-links { display: none; }
            .features-grid { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
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
            .navbar { padding: 10px 12px; }
            .nav-container { gap: 8px; }
            .brand-icon-box { width: 32px; height: 32px; font-size: 15px; border-radius: 8px; }
            .brand-title { font-size: 14.5px; }
            .brand-subtitle { display: none; }
            .nav-cta { padding: 6px 10px; font-size: 11px; gap: 4px; border-radius: 8px; }
            .hero { padding: 35px 10px 24px; }
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
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">پرش به محتوای اصلی</a>
    <div class="ambient-glow" aria-hidden="true"></div>

    <!-- Sticky Navigation Bar (Confidential: Strictly No Admin Login Button) -->
    <header class="navbar" role="banner">
        <div class="nav-container">
            <a href="#" class="nav-brand" aria-label="همیار باشگاه - صفحه اصلی">
                <div class="brand-icon-box" aria-hidden="true">🏋️‍♂️</div>
                <div class="brand-text-box">
                    <span class="brand-title">همیار باشگاه</span>
                    <span class="brand-subtitle">Gym Assistant App</span>
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
            <div class="hero-badge">
                <span class="pulse-dot"></span>
                <span>🏆 سامانه جامع مدیریت هوشمند و مربیگری باشگاه‌های ورزشی | Gym Assistant App</span>
            </div>
            <h1 id="hero-heading" class="hero-title">
                <span class="hero-title-gradient">همیار باشگاه</span>؛ نسل نوین مربیگری و اتوماسیون ورزشی
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

            <!-- Quick Highlights -->
            <div class="highlights-grid">
                <div class="highlight-card">
                    <div class="highlight-icon">⚡</div>
                    <div class="highlight-text">
                        <h3>کارکرد ۱۰۰٪ آفلاین</h3>
                        <p>پایداری مطلق در سالن ورزشی و چاپ برنامه‌ها بدون وابستگی به اینترنت</p>
                    </div>
                </div>
                <div class="highlight-card">
                    <div class="highlight-icon">🛡️</div>
                    <div class="highlight-text">
                        <h3>پشتیبان‌گیری ابری</h3>
                        <p>همگام‌سازی رمزنگاری‌شده با سرورهای توزیع‌شده کلودفلر در پس‌زمینه</p>
                    </div>
                </div>
                <div class="highlight-card">
                    <div class="highlight-icon">📄</div>
                    <div class="highlight-text">
                        <h3>شناسنامه چاپی شکیل</h3>
                        <p>تولید سریع و استاندارد PDF فارسی برای ارزیابی فیزیک و برنامه‌ها</p>
                    </div>
                </div>
                <div class="highlight-card">
                    <div class="highlight-icon">💰</div>
                    <div class="highlight-text">
                        <h3>مدیریت مالی و شهریه</h3>
                        <p>کنترل دوره‌ها، صندوق، تراز مالی و یادآوری هوشمند سررسید اعضا</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- 7 Main Modules Grid -->
        <section id="features" class="section" role="region" aria-labelledby="features-heading">
            <div class="section-header">
                <div class="section-pill">معماری جامع و ماژولار</div>
                <h2 id="features-heading" class="section-title">ویترین کامل قابلیت‌ها و ماژول‌های سیستم</h2>
                <p class="section-subtitle">
                    هفت ماژول تخصصی و کاملاً یکپارچه، طراحی‌شده بر اساس نیازهای میدانی مدیران باشگاه‌ها و مربیان ورزشی
                </p>
            </div>

            <div class="features-grid">
                <!-- Module 1 -->
                <article class="feature-card" aria-labelledby="module-title-1">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">📋</div>
                        <span class="feature-module-badge">ماژول ۱</span>
                    </div>
                    <h3 id="module-title-1" class="feature-title">پرونده سلامت و فیزیک ورزشکار</h3>
                    <ul class="feature-list">
                        <li class="feature-item">ارزیابی ترکیب بدنی و شاخص‌های آنتروپومتریک شامل BMI، درصد چربی، توده عضلانی و نسبت دور کمر به باسن (WHR).</li>
                        <li class="feature-item">تست‌های تخصصی غربالگری ناهنجاری‌های اسکلتی و قامتی (لوردوز، کیفوز، اسکولیوز، افتادگی شانه، پای پرانتزی و ضربدری).</li>
                        <li class="feature-item">آلبوم تصویری پیشرفت فیزیکی با قابلیت مقایسه دوره‌ای عکس‌های قبل و بعد ورزشکار در زوایای استاندارد.</li>
                        <li class="feature-item">بایگانی دائمی سوابق پزشکی، تاریخچه آسیب‌های ورزشی، بیماری‌ها و منع‌های تمرینی.</li>
                    </ul>
                </article>

                <!-- Module 2 -->
                <article class="feature-card" aria-labelledby="module-title-2">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🏋️‍♂️</div>
                        <span class="feature-module-badge">ماژول ۲</span>
                    </div>
                    <h3 id="module-title-2" class="feature-title">طراحی تمرین و بانک حرکات با ویدیو</h3>
                    <ul class="feature-list">
                        <li class="feature-item">کتابخانه غنی حرکات ورزشی تفکیک‌شده بر اساس گروه‌های عضلانی هدف و تجهیزات تمرینی باشگاه.</li>
                        <li class="feature-item">پخش ویدیوی تکنیک صحیح اجرای حرکت و بررسی زوایای آناتومیکی جهت پیشگیری از آسیب و اجرای استاندارد.</li>
                        <li class="feature-item">طراحی هوشمند جلسات تمرینی شامل تعداد ست‌ها، دامنه‌های تکرار، زمان استراحت، سوپرست و دراپ‌ست.</li>
                        <li class="feature-item">قابلیت ایجاد، ویرایش و ذخیره الگوهای تمرینی آماده برای سطوح مبتدی، متوسط و پیشرفته.</li>
                    </ul>
                </article>

                <!-- Module 3 -->
                <article class="feature-card" aria-labelledby="module-title-3">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🥗</div>
                        <span class="feature-module-badge">ماژول ۳</span>
                    </div>
                    <h3 id="module-title-3" class="feature-title">طراحی تخصصی برنامه غذایی و کالری‌شماری</h3>
                    <ul class="feature-list">
                        <li class="feature-item">بانک جامع غذاهای سنتی و مدرن ایرانی همراه با جدول ارزش غذایی دقیق و میزان پروتئین و کالری.</li>
                        <li class="feature-item">محاسبه‌گر خودکار نرخ متابولیسم پایه (BMR) و کل انرژی مصرفی روزانه (TDEE) متناسب با تیپ بدنی.</li>
                        <li class="feature-item">تفکیک هوشمند درشت‌مغذی‌ها (پروتئین، کربوهیدرات، چربی مفید) برای وعده‌ها و میان‌وعده‌های روزانه.</li>
                        <li class="feature-item">ماژول اختصاصی تجویز، زمان‌بندی و دوز بهینه مصرف مکمل‌های ورزشی مجاز و نوشیدنی‌های ورزشی.</li>
                    </ul>
                </article>

                <!-- Module 4 -->
                <article class="feature-card" aria-labelledby="module-title-4">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">📄</div>
                        <span class="feature-module-badge">ماژول ۴</span>
                    </div>
                    <h3 id="module-title-4" class="feature-title">موتور صدور شناسنامه و PDF چاپی حرفه‌ای</h3>
                    <ul class="feature-list">
                        <li class="feature-item">صدور شناسنامه سلامت فیزیکی و ورزشی بسیار شکیل و فشرده در قالب‌های استاندارد A4 و A5.</li>
                        <li class="feature-item">خروجی چاپی برنامه‌های تمرینی و غذایی با سربرگ، لوگوی اختصاصی باشگاه و امضای رسمی مربی.</li>
                        <li class="feature-item">تولید ۱۰۰٪ آفلاین و آنی بدون وابستگی به اینترنت یا نرم‌افزارهای جانبی.</li>
                        <li class="feature-item">طراحی تایپوگرافی اصیل با فونت فارسی بهینه، عدم به هم ریختگی فونت و خوانایی عالی در چاپ.</li>
                    </ul>
                </article>

                <!-- Module 5 -->
                <article class="feature-card" aria-labelledby="module-title-5">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">💰</div>
                        <span class="feature-module-badge">ماژول ۵</span>
                    </div>
                    <h3 id="module-title-5" class="feature-title">حسابداری، صندوق و مدیریت شهریه</h3>
                    <ul class="feature-list">
                        <li class="feature-item">ثبت و مدیریت دوره‌ها، پکیج‌های عضویت ماهانه، فصلی، سالانه و سانس‌های خصوصی مربیگری.</li>
                        <li class="feature-item">سیستم صندوق و ثبت روش‌های مختلف پرداخت (نقدی، کارت‌خوان، کارت‌به‌کارت و تخفیف‌ها).</li>
                        <li class="feature-item">گزارش‌گیری جامع از دریافتی‌ها، تراز سود و زیان و بررسی لیست اعضای بدهکار در چند ثانیه.</li>
                        <li class="feature-item">یادآوری هوشمند تاریخ تمدید دوره‌ها و شناسایی خودکار اعضای با عضویت رو به پایان.</li>
                    </ul>
                </article>

                <!-- Module 6 -->
                <article class="feature-card" aria-labelledby="module-title-6">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">📩</div>
                        <span class="feature-module-badge">ماژول ۶</span>
                    </div>
                    <h3 id="module-title-6" class="feature-title">سامانه اطلاع‌رسانی پیامکی هوشمند</h3>
                    <ul class="feature-list">
                        <li class="feature-item">ارسال پیامک از خطوط خدماتی بدون تداخل با بلک‌لیست مخابراتی برای اطمینان از تحویل ۱۰۰٪ پیام‌ها.</li>
                        <li class="feature-item">تبریک خودکار سالروز تولد ورزشکاران جهت ارتقای تعامل، حس وفاداری و رضایت ورزشکار.</li>
                        <li class="feature-item">یادآوری خودکار سررسید شهریه، پیامک‌های خوش‌آمدگویی و تایید ثبت‌نام در سامانه.</li>
                        <li class="feature-item">ارسال پیامک‌های گروهی سریع برای اعلام رویدادها، تغییر ساعات کاری و تعطیلی‌های باشگاه.</li>
                    </ul>
                </article>

                <!-- Module 7 -->
                <article class="feature-card" aria-labelledby="module-title-7">
                    <div class="feature-top-bar">
                        <div class="feature-icon-wrapper" aria-hidden="true">🛡️</div>
                        <span class="feature-module-badge">ماژول ۷</span>
                    </div>
                    <h3 id="module-title-7" class="feature-title">امنیت ۱۰۰٪ آفلاین با همگام‌سازی ابری</h3>
                    <ul class="feature-list">
                        <li class="feature-item">کارکرد کاملاً مستقل روی سیستم‌عامل ویندوز بدون وابستگی به اینترنت در سالن ورزشی.</li>
                        <li class="feature-item">پایگاه داده محلی سریع و ایمن با رمزنگاری قوی برای حفاظت از حریم خصوصی ورزشکاران.</li>
                        <li class="feature-item">پشتیبان‌گیری خودکار و هوشمند در پایان روز کاری روی سرورهای ابری کلودفلر.</li>
                        <li class="feature-item">قابلیت بازیابی آنی اطلاعات در صورت آسیب سیستم یا تعویض رایانه باشگاه بدون فوت وقت.</li>
                    </ul>
                </article>
            </div>
        </section>

        <!-- Partner Gyms Section -->
        <section id="partner-gyms" class="section" role="region" aria-labelledby="partner-gyms-heading">
            <div class="section-header">
                <div class="section-pill">شبکه باشگاه‌های پیشرو</div>
                <h2 id="partner-gyms-heading" class="section-title">باشگاه‌های مجهز به سامانه همیار باشگاه</h2>
                <p class="section-subtitle">
                    مجموعه‌های ورزشی ممتازی که با تجهیز به این سامانه، بالاترین استاندارد مربیگری و رضایت ورزشکاران را به ارمغان آورده‌اند
                </p>
            </div>

            <div class="partner-gyms-grid">
                <!-- Gym 1: Yalda Gym (باشگاه بدنسازی یلدا) -->
                <article class="gym-card" aria-labelledby="gym-name-yalda">
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
                    <div class="join-icon-box" aria-hidden="true">🏆</div>
                    <h3 id="join-heading" class="join-title">باشگاه خود را مجهز کنید</h3>
                    <p class="join-desc">
                        آیا مایلید مجموعه ورزشی شما نیز به سامانه همیار باشگاه مجهز شده و از اتوماسیون مربیگری، ارزیابی بدنی و پشتیبان‌گیری ابری بهره‌مند شود؟
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
                <div class="security-card">
                    <div class="security-icon-box" aria-hidden="true">💻</div>
                    <h3>استقلال ۱۰۰٪ از اینترنت در باشگاه</h3>
                    <p>
                        تمام فرایندهای اصلی سامانه شامل ثبت‌نام ورزشکار، ارزیابی فیزیک، طراحی برنامه و صدور PDF چاپی به صورت ۱۰۰٪ آفلاین و محلی روی سیستم باشگاه اجرا می‌شود.
                    </p>
                </div>
                <div class="security-card">
                    <div class="security-icon-box" aria-hidden="true">🔒</div>
                    <h3>حفظ حریم خصوصی و رمزنگاری داده‌ها</h3>
                    <p>
                        پرونده‌های پزشکی، اندازه‌گیری‌های بدنی و تصاویر پیشرفت ورزشکاران روی پایگاه داده محلی ایمن و غیرقابل دسترسی توسط افراد غیرمجاز حفاظت می‌شوند.
                    </p>
                </div>
                <div class="security-card">
                    <div class="security-icon-box" aria-hidden="true">☁️</div>
                    <h3>پشتیبان‌گیری ابری خودکار در کلودفلر</h3>
                    <p>
                        با اتصال به اینترنت، بکاپ‌های امنیتی به صورت خودکار به فضای ابری توزیع‌شده Cloudflare ارسال می‌شوند تا در صورت نقص سخت‌افزاری، اطلاعات بلافاصله بازیابی شوند.
                    </p>
                </div>
            </div>
        </section>

        <!-- Developer Profile & Official Support Section -->
        <section id="contact" class="section" role="region" aria-labelledby="contact-heading">
            <div class="section-header">
                <div class="section-pill">پشتیبانی و توسعه رسمی</div>
                <h2 id="contact-heading" class="section-title">توسعه‌دهنده نرم‌افزار همیار باشگاه</h2>
                <p class="section-subtitle">
                    راه‌های ارتباطی رسمی جهت مشاوره، پشتیبانی فنی و تجهیز باشگاه‌های ورزشی
                </p>
            </div>

            <div class="developer-card">
                <div class="developer-avatar-box">
                    <img src="/images/developer_photo.jpg" alt="ابوالفضل صمدی کوچکسرائی - توسعه‌دهنده نرم‌افزار همیار باشگاه" class="developer-avatar-img" width="88" height="88" loading="lazy">
                </div>
                <h3 class="developer-name">ابوالفضل صمدی کوچکسرائی</h3>
                <span class="developer-role">توسعه‌دهنده و طراح نرم‌افزار | Software Developer & Architect</span>
                <p class="developer-bio">
                    مهندسی سیستم‌های اتوماسیون ورزشی، پیاده‌سازی نرم‌افزارهای دسکتاپ ویندوز، و زیرساخت‌های سرورلس ابری کلودفلر با تمرکز بر سرعت فوق‌سریع، کارکرد آفلاین و امنیت حداکثری.
                </p>

                <div class="contact-links-grid">
                    <a href="mailto:gymassistantapp.support@gmail.com" class="contact-btn contact-btn-email" aria-label="ارسال ایمیل به پشتیبانی رسمی همیار باشگاه">
                        <span aria-hidden="true">📧</span>
                        <span>gymassistantapp.support@gmail.com</span>
                    </a>
                    <a href="https://t.me/AqaSamadi" target="_blank" rel="noopener noreferrer" class="contact-btn contact-btn-telegram" aria-label="ارتباط در تلگرام با ابوالفضل صمدی (باز شدن در تب جدید)">
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
            <div class="footer-brand">همیار باشگاه • Gym Assistant App</div>
            <p class="footer-copy">
                تمامی حقوق مادی و معنوی این وب‌سایت و سامانه همیار باشگاه محفوظ است © ۲۰۲۶ • توسعه‌دهنده: ابوالفضل صمدی کوچکسرائی
            </p>
            <div class="footer-badges">
                <span class="footer-badge">Cloudflare Edge Worker</span>
                <span class="footer-badge">پاسخ‌دهی زیر ۱۰۰ میلی‌ثانیه</span>
                <span class="footer-badge">۱۰۰٪ مستقل از CDNهای خارجی</span>
                <span class="footer-badge">نسخه رسمی v2.0</span>
            </div>
        </div>
    </footer>
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
