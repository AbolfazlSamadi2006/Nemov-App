/**
 * Yalda Gym Cloudflare Worker - Serverless Backup Server & Admin Dashboard
 * Author: Abolfazl Samadi
 */

const SECRET_API_KEY = "yalda_cloud_sec_2006_gym";
const ADMIN_USER = "admin";
const ADMIN_PASS = "2006";
const AUTH_COOKIE_NAME = "yalda_admin_session";
const AUTH_SECRET_TOKEN = "yalda_auth_token_secret_2006_gym";

// Gregorian to Shamsi date converter
function toShamsi(date) {
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

function getCookie(request, name) {
    const cookieString = request.headers.get("Cookie") || "";
    const cookies = cookieString.split(";").map(c => c.trim());
    for (const cookie of cookies) {
        const [k, v] = cookie.split("=");
        if (k === name) return decodeURIComponent(v);
    }
    return null;
}

function isAuthenticated(request) {
    const token = getCookie(request, AUTH_COOKIE_NAME);
    return token === AUTH_SECRET_TOKEN;
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

export default {
    async fetch(request, env, ctx) {
        const { r2, kv } = getStorage(env);
        const url = new URL(request.url);
        const path = url.pathname;
        const method = request.method;

        // CORS Headers
        const corsHeaders = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key, Authorization"
        };

        if (method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        // ====================================================================
        // 1. API: Upload Backup (POST /api/backup/upload)
        // ====================================================================
        if (path === "/api/backup/upload" && method === "POST") {
            const apiKey = request.headers.get("X-API-Key") || request.headers.get("x-api-key");
            if (apiKey !== SECRET_API_KEY) {
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

                const phone = phoneRaw.replace(/\D/g, "");
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
                    await kv.put(`meta_${phone}`, JSON.stringify(metadata));
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
            const phone = path.replace("/api/backup/download/", "").replace(/\D/g, "");
            const apiKey = request.headers.get("X-API-Key");
            const authed = isAuthenticated(request) || apiKey === SECRET_API_KEY;

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
            if (apiKey !== SECRET_API_KEY && !isAuthenticated(request)) {
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
                const contentType = isImage ? (mimeMap[ext] || 'image/jpeg') : 'video/mp4';
                const r2Folder = isImage ? 'images/' : 'videos/';
                const kvPrefix = isImage ? 'image_' : 'video_';
                const metaPrefix = isImage ? 'imeta_' : 'vmeta_';

                if (kv) {
                    await kv.put(`${kvPrefix}${filename}`, fileBytes);
                    await kv.put(`${metaPrefix}${filename}`, JSON.stringify({ filename, fileSizeMb, uploadDate: new Date().toISOString() }));
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
            const filename = decodeURIComponent(rawFilename);
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
                const totalLength = videoBody.byteLength;
                const rangeHeader = request.headers.get("Range");

                if (rangeHeader) {
                    const match = rangeHeader.match(/bytes=(\d*)-(\d*)/);
                    if (match) {
                        let start = match[1] ? parseInt(match[1], 10) : 0;
                        let end = match[2] ? parseInt(match[2], 10) : totalLength - 1;

                        if (isNaN(start)) start = 0;
                        if (isNaN(end) || end >= totalLength) end = totalLength - 1;

                        if (start > end || start >= totalLength) {
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
                                "Content-Type": "video/mp4",
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
                        "Content-Type": "video/mp4",
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
            const filename = decodeURIComponent(rawFilename);

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
        if (path === "/login" && method === "POST") {
            const formData = await request.formData();
            const username = formData.get("username");
            const password = formData.get("password");

            if (username === ADMIN_USER && password === ADMIN_PASS) {
                return new Response(null, {
                    status: 303,
                    headers: {
                        "Location": "/",
                        "Set-Cookie": `${AUTH_COOKIE_NAME}=${AUTH_SECRET_TOKEN}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000`
                    }
                });
            }

            return new Response(renderLoginPage("نام کاربری یا رمز عبور اشتباه است."), {
                headers: { "Content-Type": "text/html; charset=utf-8" }
            });
        }

        if (path === "/logout") {
            return new Response(null, {
                status: 303,
                headers: {
                    "Location": "/",
                    "Set-Cookie": `${AUTH_COOKIE_NAME}=; Path=/; HttpOnly; Max-Age=0`
                }
            });
        }

        // ====================================================================
        // 4. Web: Delete Backup (POST /api/backup/delete/:phone)
        // ====================================================================
        if (path.startsWith("/api/backup/delete/") && method === "POST") {
            if (!isAuthenticated(request)) {
                return new Response("دسترسی غیرمجاز", { status: 401 });
            }
            const phone = path.replace("/api/backup/delete/", "").replace(/\D/g, "");
            if (kv) {
                await kv.delete(`db_${phone}`);
                await kv.delete(`meta_${phone}`);
            } else if (r2) {
                await r2.delete(`backups/${phone}/yalda.db`);
                await r2.delete(`backups/${phone}/metadata.json`);
            }
            return new Response(null, { status: 303, headers: { "Location": "/" } });
        }

        // ====================================================================
        // 5. Web: Home Dashboard (GET /)
        // ====================================================================
        if (path === "/" || path === "") {
            if (!isAuthenticated(request)) {
                return new Response(renderLoginPage(), {
                    headers: { "Content-Type": "text/html; charset=utf-8" }
                });
            }

            // Fetch list of trainers
            let trainers = [];
            let totalSize = 0;

            if (kv) {
                const list = await kv.list({ prefix: "meta_" });
                for (const key of list.keys) {
                    const meta = await kv.get(key.name, { type: "json" });
                    if (meta) {
                        trainers.push(meta);
                        totalSize += (meta.file_size_mb || 0);
                    }
                }
            } else if (r2) {
                const list = await r2.list({ prefix: "backups/" });
                const metaKeys = list.objects.filter(o => o.key.endsWith("metadata.json"));
                for (const item of metaKeys) {
                    const metaObj = await r2.get(item.key);
                    if (metaObj) {
                        try {
                            const meta = await metaObj.json();
                            trainers.push(meta);
                            totalSize += (meta.file_size_mb || 0);
                        } catch (e) {}
                    }
                }
            }

            trainers.sort((a, b) => (b.last_backup_iso || "").localeCompare(a.last_backup_iso || ""));
            const lastActivity = trainers.length > 0 ? trainers[0].last_backup_shamsi : "هنوز ثبتی انجام نشده";

            return new Response(renderDashboardPage(trainers, totalSize.toFixed(2), lastActivity), {
                headers: { "Content-Type": "text/html; charset=utf-8" }
            });
        }

        return new Response("Not Found", { status: 404 });
    }
};

// ============================================================================
// HTML Page Renderers (Dark Red Gym Theme)
// ============================================================================

function renderLoginPage(error = null) {
    const errorHtml = error ? `<div class="error-alert">${error}</div>` : '';
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به سرور ابری کلودفلر یلدا</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }
        body { background-color: #0F0F0F; color: #FFFFFF; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .card { background-color: #1A1A1A; border: 1px solid #2D2D2D; border-top: 4px solid #8B0000; border-radius: 12px; width: 100%; max-width: 400px; padding: 35px 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .logo-box { text-align: center; margin-bottom: 25px; }
        .logo-box h1 { font-size: 20px; font-weight: 800; color: #FFFFFF; margin-bottom: 5px; }
        .logo-box p { font-size: 13px; color: #9CA3AF; }
        .input-group { margin-bottom: 18px; }
        .input-group label { display: block; font-size: 13px; font-weight: bold; color: #D1D5DB; margin-bottom: 6px; }
        .input-group input { width: 100%; height: 42px; background-color: #262626; border: 1px solid #3F3F46; border-radius: 8px; padding: 0 12px; color: #FFFFFF; font-size: 14px; outline: none; }
        .input-group input:focus { border-color: #8B0000; }
        .btn-submit { width: 100%; height: 44px; background-color: #8B0000; color: #FFFFFF; font-size: 15px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; }
        .btn-submit:hover { background-color: #A91D22; }
        .error-alert { background-color: rgba(220, 38, 38, 0.15); border: 1px solid #DC2626; color: #F87171; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 20px; text-align: center; }
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

function renderDashboardPage(trainers, totalSizeMb, lastActivity) {
    const rowsHtml = trainers.length > 0 ? trainers.map((t, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td style="font-weight: bold; color: #FFFFFF;">${t.trainer_name || "مربی"}</td>
            <td style="direction: ltr; text-align: right; font-family: monospace; color: #60A5FA;">${t.phone}</td>
            <td>${t.last_backup_shamsi}</td>
            <td>${t.file_size_mb} MB</td>
            <td>
                <a href="/api/backup/download/${t.phone}" class="btn-download">⬇️ دانلود دیتابیس</a>
                <form action="/api/backup/delete/${t.phone}" method="POST" style="display: inline;" onsubmit="return confirm('آیا از حذف بک‌آپ این مربی اطمینان دارید؟');">
                    <button type="submit" class="btn-delete">🗑️ حذف</button>
                </form>
            </td>
        </tr>
    `).join("") : '';

    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت ابری کلودفلر - باشگاه یلدا</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }
        body { background-color: #0F0F0F; color: #F3F4F6; min-height: 100vh; display: flex; flex-direction: column; }
        header { background-color: #18181B; border-bottom: 1px solid #27272A; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
        .brand { display: flex; align-items: center; gap: 12px; }
        .brand h1 { font-size: 18px; font-weight: 800; color: #FFFFFF; }
        .badge-live { background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: bold; }
        .btn-logout { background-color: #27272A; color: #EF4444; border: 1px solid #3F3F46; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; }
        .btn-logout:hover { background-color: #DC2626; color: #FFFFFF; }
        .container { max-width: 1200px; width: 100%; margin: 0 auto; padding: 28px 20px; flex: 1; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; margin-bottom: 28px; }
        .stat-card { background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; }
        .stat-icon { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
        .icon-red { background-color: rgba(139, 0, 0, 0.2); color: #EF4444; border: 1px solid #8B0000; }
        .icon-blue { background-color: rgba(37, 99, 235, 0.2); color: #60A5FA; border: 1px solid #2563EB; }
        .icon-green { background-color: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #10B981; }
        .stat-info h3 { font-size: 22px; font-weight: 800; color: #FFFFFF; margin-bottom: 2px; }
        .stat-info p { font-size: 12px; color: #A1A1AA; }
        .table-card { background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; overflow: hidden; }
        .table-header { padding: 16px 20px; border-bottom: 1px solid #27272A; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
        .table-header h2 { font-size: 16px; font-weight: bold; color: #FFFFFF; }
        .search-input { background-color: #27272A; border: 1px solid #3F3F46; color: #FFFFFF; padding: 8px 14px; border-radius: 8px; font-size: 13px; width: 260px; outline: none; }
        .search-input:focus { border-color: #8B0000; }
        table { width: 100%; border-collapse: collapse; text-align: right; font-size: 13px; }
        th { background-color: #202024; color: #A1A1AA; padding: 12px 18px; font-weight: bold; border-bottom: 1px solid #27272A; }
        td { padding: 14px 18px; border-bottom: 1px solid #27272A; color: #E4E4E7; }
        tr:hover td { background-color: #202024; }
        .btn-download { background-color: #2563EB; color: #FFFFFF; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 12px; display: inline-flex; align-items: center; gap: 4px; }
        .btn-download:hover { background-color: #1D4ED8; }
        .btn-delete { background-color: transparent; color: #EF4444; border: 1px solid #EF4444; padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; margin-right: 6px; }
        .btn-delete:hover { background-color: #EF4444; color: #FFFFFF; }
        .empty-state { padding: 40px 20px; text-align: center; color: #71717A; }
        footer { text-align: center; padding: 20px; font-size: 12px; color: #71717A; border-top: 1px solid #27272A; }
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
                <input type="text" id="searchInput" class="search-input" placeholder="🔍 جستجو بر اساس نام یا شماره..." onkeyup="filterTable()">
            </div>

            ${trainers.length > 0 ? `
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
                    ${rowsHtml}
                </tbody>
            </table>
            ` : `
            <div class="empty-state">
                <p style="font-size: 16px; margin-bottom: 6px;">هنوز هیچ نسخه پشتیبانی در سرور ابری کلودفلر ثبت نشده است.</p>
                <p style="font-size: 13px;">به محض اینکه مربیان از طریق نرم‌افزار گزینه «ذخیره در سرور» را انتخاب کنند، اطلاعات آنها در اینجا ظاهر می‌شود.</p>
            </div>
            `}
        </div>
    </div>

    <footer>
        توسعه داده شده برای سامانه هوشمند مدیریت باشگاه یلدا • قدرت گرفته از شبکه لبه ابری Cloudflare Workers © 2026
    </footer>

    <script>
        function filterTable() {
            var input = document.getElementById("searchInput");
            var filter = input.value.toLowerCase();
            var table = document.getElementById("trainersTable");
            if (!table) return;
            var tr = table.getElementsByTagName("tr");
            for (var i = 1; i < tr.length; i++) {
                var tdName = tr[i].getElementsByTagName("td")[1];
                var tdPhone = tr[i].getElementsByTagName("td")[2];
                if (tdName || tdPhone) {
                    var txtValueName = tdName.textContent || tdName.innerText;
                    var txtValuePhone = tdPhone.textContent || tdPhone.innerText;
                    if (txtValueName.toLowerCase().indexOf(filter) > -1 || txtValuePhone.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }
    </script>
</body>
</html>`;
}

function renderSandboxedVideoPlayer(title, videoStreamUrl) {
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>${title} | راهنمای اجرای حرکت</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }
        body {
            background-color: #0d0d0d;
            color: #ffffff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
        }
        .player-container {
            width: 100%;
            max-width: 540px;
            background: #181818;
            border-radius: 18px;
            border: 1px solid #2a2a2a;
            box-shadow: 0 16px 40px rgba(0,0,0,0.8);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .player-header {
            padding: 16px 20px;
            background: linear-gradient(135deg, #1f1f1f, #141414);
            border-bottom: 1px solid #262626;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header-title-box h1 {
            font-size: 17px;
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
            font-size: 11px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 20px;
            letter-spacing: 0.3px;
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
        }
        video {
            width: 100%;
            max-height: 70vh;
            display: block;
            outline: none;
            background-color: #000;
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
            padding: 20px;
            text-align: center;
            z-index: 10;
        }
        .error-message p {
            color: #ef4444;
            font-size: 13.5px;
            margin-bottom: 12px;
        }
        .retry-btn {
            background: #8B0000;
            color: #ffffff;
            border: none;
            padding: 8px 18px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
        }
        .retry-btn:hover {
            background: #a91d22;
        }
        .player-footer {
            padding: 12px 18px;
            background: #141414;
            border-top: 1px solid #242424;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            color: #777777;
        }
        .player-footer span {
            color: #A91D22;
            font-weight: bold;
        }
        .controls-hint {
            font-size: 11px;
            color: #666666;
        }
    </style>
</head>
<body>
    <div class="player-container">
        <div class="player-header">
            <div class="header-title-box">
                <h1>🎬 ${title}</h1>
                <p>فرم اجرای صحیح حرکت ورزشی</p>
            </div>
            <div class="gym-badge">باشگاه بدنسازی یلدا</div>
        </div>
        <div class="video-box" id="videoBox">
            <video id="player" controls autoplay muted loop playsinline preload="auto">
                <source src="${videoStreamUrl}" type="video/mp4">
                مرورگر شما از پخش مستقیم ویدیو پشتیبانی نمی‌کند.
            </video>
            <div class="play-overlay" id="playOverlay">
                <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </div>
            <div class="error-message" id="errorMessage">
                <p>⚠️ خطا در بارگذاری ویدیو حرکت</p>
                <button class="retry-btn" onclick="retryVideo()">تلاش مجدد</button>
            </div>
        </div>
        <div class="player-footer">
            <div>برنامه تمرینی اختصاصی • <span>سامانه هوشمند یلدا</span></div>
            <div class="controls-hint">کلیک برای پخش / توقف</div>
        </div>
    </div>
    <script>
        const video = document.getElementById('player');
        const overlay = document.getElementById('playOverlay');
        const errBox = document.getElementById('errorMessage');
        const box = document.getElementById('videoBox');

        function updateOverlay() {
            if (video.paused || video.ended) {
                overlay.classList.add('show');
            } else {
                overlay.classList.remove('show');
            }
        }

        box.addEventListener('click', (e) => {
            if (e.target.tagName.toLowerCase() === 'button') return;
            if (video.paused) {
                video.play().catch(e => console.log('Autoplay blocked:', e));
            } else {
                video.pause();
            }
        });

        video.addEventListener('play', updateOverlay);
        video.addEventListener('pause', updateOverlay);
        video.addEventListener('ended', updateOverlay);

        video.addEventListener('error', () => {
            errBox.style.display = 'flex';
        });

        function retryVideo() {
            errBox.style.display = 'none';
            const src = "${videoStreamUrl}&r=" + Date.now();
            video.src = src;
            video.load();
            video.play().catch(e => console.log('Retry play error:', e));
        }

        window.addEventListener('DOMContentLoaded', () => {
            updateOverlay();
            video.play().catch(() => updateOverlay());
        });
    </script>
</body>
</html>`;
}

function renderSandboxedImageViewer(title, imageUrl) {
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} | باشگاه بدنسازی یلدا</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0d0d0d;
            color: #ffffff;
            font-family: 'Vazirmatn', sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 16px;
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
            padding: 16px 20px;
            background: #141414;
            border-bottom: 1px solid #242424;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header-title-box h1 {
            font-size: 17px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 3px;
        }
        .header-title-box p {
            font-size: 12px;
            color: #888888;
        }
        .gym-badge {
            background: #8B0000;
            color: #ffffff;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11.5px;
            font-weight: bold;
        }
        .image-box {
            position: relative;
            background: #0F0F0F;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 300px;
            max-height: 75vh;
            overflow: hidden;
            padding: 10px;
        }
        .image-box img {
            max-width: 100%;
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
    </style>
</head>
<body>
    <div class="viewer-container">
        <div class="viewer-header">
            <div class="header-title-box">
                <h1>🖼️ ${title}</h1>
                <p>تصویر و الگوی حرکتی ورزشکار</p>
            </div>
            <div class="gym-badge">باشگاه بدنسازی یلدا</div>
        </div>
        <div class="image-box">
            <img src="${imageUrl}" alt="${title}" loading="lazy" />
        </div>
        <div class="viewer-footer">
            <div>برنامه تمرینی اختصاصی • <span>سامانه هوشمند یلدا</span></div>
            <a class="download-link" href="${imageUrl}" target="_blank" download>دریافت تصویر باکیفیت اصلی 📥</a>
        </div>
    </div>
</body>
</html>`;
}

function renderIsolatedNotFoundPage(title = "رسانه یافت نشد", msg = "فایل درخواستی در مخزن سرور موجود نیست یا حذف شده است.") {
    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body { background: #0F0F0F; color: #fff; font-family: 'Vazirmatn', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }
        .box { background: #1A1A1A; border: 1px solid #333; padding: 30px; border-radius: 12px; max-width: 360px; }
        h2 { font-size: 18px; margin-bottom: 10px; color: #DC2626; }
        p { font-size: 13px; color: #aaa; }
    </style>
</head>
<body>
    <div class="box">
        <h2>⚠️ ${title}</h2>
        <p>${msg}</p>
    </div>
</body>
</html>`;
}

