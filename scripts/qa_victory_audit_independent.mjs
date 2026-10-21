// Independent Victory Audit Test Suite for Cloudflare Worker Speed & Responsive UI Optimization
import worker from '../nemov_cloud_server/cloudflare_worker/index.js';
import fs from 'fs';
import path from 'path';

// Color helpers
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const RESET = '\x1b[0m';

let passedTests = 0;
let failedTests = 0;

function assert(condition, message) {
    if (condition) {
        passedTests++;
        console.log(`  ${GREEN}✔ PASS:${RESET} ${message}`);
    } else {
        failedTests++;
        console.error(`  ${RED}✖ FAIL:${RESET} ${message}`);
    }
}

// Mock Cloudflare Worker KV Store
class MockKV {
    constructor() {
        this.store = new Map();
        this.listCallCount = 0;
        this.getCallCount = 0;
        this.concurrentOperations = 0;
        this.maxConcurrentOperations = 0;
    }

    async get(key, options = {}) {
        this.getCallCount++;
        this.concurrentOperations++;
        this.maxConcurrentOperations = Math.max(this.maxConcurrentOperations, this.concurrentOperations);
        await new Promise(r => setTimeout(r, 2)); // simulate async I/O
        this.concurrentOperations--;

        const item = this.store.get(key);
        if (!item) return null;

        if (options.type === 'json') {
            try {
                if (typeof item.value === 'string') {
                    return JSON.parse(item.value);
                }
                return item.value;
            } catch (e) {
                return null;
            }
        }
        if (options.type === 'arrayBuffer') {
            if (Buffer.isBuffer(item.value)) {
                return item.value.buffer.slice(item.value.byteOffset, item.value.byteOffset + item.value.byteLength);
            }
            if (typeof item.value === 'string') {
                const buf = Buffer.from(item.value, 'utf-8');
                return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
            }
            return item.value;
        }
        return item.value;
    }

    async put(key, value, options = {}) {
        let storedVal = value;
        if (typeof value === 'object' && !Buffer.isBuffer(value) && !(value instanceof ArrayBuffer)) {
            storedVal = JSON.stringify(value);
        }
        this.store.set(key, {
            value: storedVal,
            metadata: options.metadata || null
        });
    }

    async delete(key) {
        this.store.delete(key);
    }

    async list(options = {}) {
        this.listCallCount++;
        this.concurrentOperations++;
        this.maxConcurrentOperations = Math.max(this.maxConcurrentOperations, this.concurrentOperations);
        await new Promise(r => setTimeout(r, 2));
        this.concurrentOperations--;

        const prefix = options.prefix || '';
        const keys = [];
        for (const [k, v] of this.store.entries()) {
            if (k.startsWith(prefix)) {
                keys.push({
                    name: k,
                    metadata: v.metadata
                });
            }
        }
        return {
            keys: keys,
            list_complete: true,
            cursor: null
        };
    }
}

// Mock Cloudflare Worker R2 Bucket
class MockR2 {
    constructor() {
        this.objects = new Map();
    }

    async put(key, body, options = {}) {
        let buffer;
        if (body instanceof ArrayBuffer) {
            buffer = Buffer.from(body);
        } else if (Buffer.isBuffer(body)) {
            buffer = body;
        } else if (typeof body === 'string') {
            buffer = Buffer.from(body, 'utf-8');
        } else if (body && typeof body.arrayBuffer === 'function') {
            buffer = Buffer.from(await body.arrayBuffer());
        } else {
            buffer = Buffer.from(String(body));
        }

        const obj = {
            key,
            size: buffer.length,
            uploaded: new Date(),
            customMetadata: options.customMetadata || {},
            httpMetadata: options.httpMetadata || {},
            buffer
        };
        this.objects.set(key, obj);
        return obj;
    }

    async get(key, options = {}) {
        const obj = this.objects.get(key);
        if (!obj) return null;

        let resBuffer = obj.buffer;
        let isRange = false;
        let rangeHeader = null;

        if (options.range) {
            isRange = true;
            let start = 0;
            let end = obj.size - 1;

            if (options.range.suffix !== undefined) {
                start = Math.max(0, obj.size - options.range.suffix);
                end = obj.size - 1;
            } else {
                start = options.range.offset || 0;
                if (options.range.length !== undefined) {
                    end = Math.min(obj.size - 1, start + options.range.length - 1);
                }
            }
            resBuffer = obj.buffer.subarray(start, end + 1);
            rangeHeader = `bytes ${start}-${end}/${obj.size}`;
        }

        return {
            key: obj.key,
            size: obj.size,
            uploaded: obj.uploaded,
            customMetadata: obj.customMetadata,
            httpMetadata: obj.httpMetadata,
            range: isRange ? rangeHeader : undefined,
            async arrayBuffer() {
                return resBuffer.buffer.slice(resBuffer.byteOffset, resBuffer.byteOffset + resBuffer.byteLength);
            },
            async text() {
                return resBuffer.toString('utf-8');
            },
            async json() {
                return JSON.parse(resBuffer.toString('utf-8'));
            },
            body: {
                getReader() {
                    let done = false;
                    return {
                        async read() {
                            if (done) return { done: true, value: undefined };
                            done = true;
                            return { done: false, value: new Uint8Array(resBuffer) };
                        }
                    };
                }
            }
        };
    }

    async delete(key) {
        this.objects.delete(key);
    }

    async list(options = {}) {
        const prefix = options.prefix || '';
        const objs = [];
        for (const [k, v] of this.objects.entries()) {
            if (k.startsWith(prefix)) {
                objs.push({
                    key: k,
                    size: v.size,
                    uploaded: v.uploaded
                });
            }
        }
        return { objects: objs, truncated: false };
    }
}

async function runAudit() {
    console.log(`${BLUE}====================================================${RESET}`);
    console.log(`${BLUE}   INDEPENDENT VICTORY AUDIT EXECUTION SUITE       ${RESET}`);
    console.log(`${BLUE}   Target: Cloudflare Worker Speed & UI Optimizer   ${RESET}`);
    console.log(`${BLUE}====================================================${RESET}\n`);

    const sourcePath = path.resolve('nemov_cloud_server/cloudflare_worker/index.js');
    const sourceCode = fs.readFileSync(sourcePath, 'utf-8');

    // ----------------------------------------------------
    // TEST SUITE 1: Security, CDN Absence & Font Delivery
    // ----------------------------------------------------
    console.log(`${YELLOW}>>> Test Suite 1: CDN Absence & Static Font Delivery${RESET}`);

    // Check absence of cdn.jsdelivr.net and external CDNs
    assert(!sourceCode.includes('cdn.jsdelivr.net'), 'Source code contains zero occurrences of cdn.jsdelivr.net');
    assert(!sourceCode.includes('unpkg.com'), 'Source code contains zero occurrences of unpkg.com');
    assert(!sourceCode.includes('cdnjs.cloudflare.com'), 'Source code contains zero occurrences of cdnjs.cloudflare.com');
    assert(!sourceCode.includes('fonts.googleapis.com'), 'Source code contains zero occurrences of fonts.googleapis.com');

    // Setup Worker Environment with storage
    const kv = new MockKV();
    const r2 = new MockR2();
    const env = {
        BACKUPS_KV: kv,
        BACKUPS_R2: r2,
        ADMIN_USER: 'Abolfazl',
        ADMIN_PASS: 'Abolfazl2006',
        SECRET_API_KEY: 'yalda_cloud_sec_2006_gym'
    };
    const ctx = { waitUntil: (p) => p };

    // Request WOFF2 font via GET /fonts/bkoodak.woff2
    const fontReq = new Request('http://localhost/fonts/bkoodak.woff2');
    const fontRes = await worker.fetch(fontReq, env, ctx);
    assert(fontRes.status === 200, `GET /fonts/bkoodak.woff2 returned HTTP 200 (got ${fontRes.status})`);
    assert(fontRes.headers.get('Content-Type') === 'font/woff2', 'Content-Type header is font/woff2');
    assert(fontRes.headers.get('Cache-Control')?.includes('immutable'), 'Font response has immutable caching header');
    assert(fontRes.headers.get('Access-Control-Allow-Origin') === '*', 'Font response has permissive CORS header');

    const fontBuf = Buffer.from(await fontRes.arrayBuffer());
    assert(fontBuf.length > 30000, `WOFF2 font payload is genuine binary (${fontBuf.length} bytes)`);
    assert(fontBuf.subarray(0, 4).toString('ascii') === 'wOF2', 'WOFF2 header magic bytes match "wOF2"');

    // Request alias /fonts/BKoodak.woff2
    const fontAliasReq = new Request('http://localhost/fonts/BKoodak.woff2');
    const fontAliasRes = await worker.fetch(fontAliasReq, env, ctx);
    assert(fontAliasRes.status === 200, 'GET /fonts/BKoodak.woff2 alias returns HTTP 200');

    // ----------------------------------------------------
    // TEST SUITE 2: Font Fallbacks & Responsive UI Checks
    // ----------------------------------------------------
    console.log(`\n${YELLOW}>>> Test Suite 2: Font Cascade & Responsive Layout Rules${RESET}`);

    assert(sourceCode.includes("font-family: 'B Koodak'"), "Defines font-family 'B Koodak'");
    assert(sourceCode.includes('font-display: swap'), 'Font configuration includes font-display: swap');
    assert(sourceCode.includes("local('B Koodak')"), "Includes local('B Koodak') font cascade");
    assert(sourceCode.includes("local('BKoodak')"), "Includes local('BKoodak') font cascade");
    assert(sourceCode.includes("local('B-Koodak')"), "Includes local('B-Koodak') font cascade");
    assert(sourceCode.includes('--font-heading:'), 'Defines --font-heading CSS variable with system fallbacks');

    // Fetch Login Page (GET /login)
    const loginReq = new Request('http://localhost/login');
    const loginRes = await worker.fetch(loginReq, env, ctx);
    const loginHtml = await loginRes.text();
    assert(loginRes.status === 200, 'GET /login returns HTTP 200');
    assert(loginHtml.includes('<meta name="viewport" content="width=device-width, initial-scale=1.0">'), 'Login page includes standard responsive viewport meta tag');
    assert(loginHtml.includes('height: 48px;'), 'Login page buttons/inputs have 48px ergonomic touch target height');
    assert(loginHtml.includes('@media (max-width: 480px)'), 'Login page contains mobile breakpoint rules (480px)');
    assert(loginHtml.includes('@media (max-width: 360px)'), 'Login page contains ultra-narrow breakpoint rules (360px)');
    assert(!loginHtml.includes('cdn.jsdelivr.net'), 'Login HTML rendered output contains no external CDN');

    // ----------------------------------------------------
    // TEST SUITE 3: KV Parallelization & TTFB Acceleration
    // ----------------------------------------------------
    console.log(`\n${YELLOW}>>> Test Suite 3: KV Promise.all Acceleration & Robustness${RESET}`);

    // Seed KV with multiple trainers, videos, images, and sms records
    for (let i = 1; i <= 15; i++) {
        const phone = `091200000${i < 10 ? '0' + i : i}`;
        await kv.put(`meta_${phone}`, {
            trainer_name: `مربی تست شماره ${i}`,
            phone: phone,
            file_size_mb: '12.5',
            last_backup_iso: new Date().toISOString(),
            last_backup_shamsi: `1405/07/${i < 10 ? '0' + i : i}`
        }, {
            metadata: {
                trainer_name: `مربی تست شماره ${i}`,
                phone: phone,
                file_size_mb: '12.5',
                last_backup_iso: new Date().toISOString(),
                last_backup_shamsi: `1405/07/${i < 10 ? '0' + i : i}`
            }
        });

        await kv.put(`vmeta_movement_${i}.mp4`, {
            filename: `movement_${i}.mp4`,
            fileSizeMb: '25.0',
            uploadDate: new Date().toISOString()
        });

        await kv.put(`imeta_pose_${i}.jpg`, {
            filename: `pose_${i}.jpg`,
            fileSizeMb: '2.5',
            uploadDate: new Date().toISOString()
        });

        await kv.put(`sms_trainer_${phone}`, {
            trainer_phone: phone,
            trainer_name: `مربی تست شماره ${i}`,
            remaining: 50,
            total_credited: 100,
            total_used: 50
        });
    }

    // Set valid login session cookie
    const validSessionCookie = 'yalda_admin_session=yalda_auth_token_secret_2006_gym';
    const authHeaders = {
        'Cookie': validSessionCookie
    };

    // Reset KV call metrics
    kv.listCallCount = 0;
    kv.getCallCount = 0;
    kv.maxConcurrentOperations = 0;

    const dashReq = new Request('http://localhost/', { headers: authHeaders });
    const dashRes = await worker.fetch(dashReq, env, ctx);
    const dashHtml = await dashRes.text();

    assert(dashRes.status === 200, 'GET / with authenticated session returns HTTP 200');
    assert(kv.listCallCount >= 4, `KV list queries executed (${kv.listCallCount} calls)`);
    assert(kv.maxConcurrentOperations >= 2, `KV operations executed in parallel (max concurrency reached: ${kv.maxConcurrentOperations})`);

    // Verify dashboard content integrity
    assert(dashHtml.includes('<meta name="viewport" content="width=device-width, initial-scale=1.0">'), 'Dashboard HTML contains responsive viewport');
    assert(dashHtml.includes('.table-responsive'), 'Dashboard contains .table-responsive scrollable containers');
    assert(dashHtml.includes('overflow-x: auto'), 'Dashboard contains horizontal scroll handling');
    assert(dashHtml.includes('-webkit-overflow-scrolling: touch'), 'Dashboard enables smooth iOS touch momentum scrolling');
    assert(dashHtml.includes('.tabs-nav'), 'Dashboard contains responsive tabs navigation');
    assert(dashHtml.includes('.stats-grid'), 'Dashboard contains responsive stats grid');
    assert(dashHtml.includes('مربی تست شماره 1'), 'Dashboard renders seeded trainer names correctly');
    assert(dashHtml.includes('movement_1.mp4'), 'Dashboard renders seeded media items correctly');
    assert(dashHtml.includes('pose_1.jpg'), 'Dashboard renders seeded images correctly');

    // Verify error boundary resiliency (KV fails gracefully)
    const failingKv = {
        async list() { throw new Error('Simulated KV failure'); },
        async get() { throw new Error('Simulated KV failure'); }
    };
    const failEnv = { ...env, BACKUPS_KV: failingKv };
    const failReq = new Request('http://localhost/', { headers: authHeaders });
    let failRes;
    try {
        failRes = await worker.fetch(failReq, failEnv, ctx);
    } catch (e) {
        failRes = null;
    }
    assert(failRes && failRes.status === 200, 'Dashboard handles KV failure gracefully without 500 crash');

    // ----------------------------------------------------
    // TEST SUITE 4: Functional API Regressions
    // ----------------------------------------------------
    console.log(`\n${YELLOW}>>> Test Suite 4: End-to-End API Regressions${RESET}`);

    // 1. Login with bad password
    const badLoginForm = new FormData();
    badLoginForm.append('username', 'Abolfazl');
    badLoginForm.append('password', 'wrong_password');
    const badLoginReq = new Request('http://localhost/login', {
        method: 'POST',
        body: badLoginForm
    });
    const badLoginRes = await worker.fetch(badLoginReq, env, ctx);
    const badLoginText = await badLoginRes.text();
    assert(badLoginText.includes('نام کاربری یا رمز عبور اشتباه است'), 'Bad login returns Persian error alert');

    // 2. Login with correct credentials
    const goodLoginForm = new FormData();
    goodLoginForm.append('username', 'Abolfazl');
    goodLoginForm.append('password', 'Abolfazl2006');
    const goodLoginReq = new Request('http://localhost/login', {
        method: 'POST',
        body: goodLoginForm
    });
    const goodLoginRes = await worker.fetch(goodLoginReq, env, ctx);
    assert(goodLoginRes.status === 303, 'Correct login redirects (HTTP 303)');
    assert(goodLoginRes.headers.get('Set-Cookie')?.includes('yalda_admin_session='), 'Set-Cookie contains yalda_admin_session token');

    // 3. Backup Upload API
    const backupPhone = '09351234567';
    const fakeSqliteBlob = new Blob(['SQLite format 3\0\x04\x00fake_database_content_test_bytes'], { type: 'application/octet-stream' });
    const uploadForm = new FormData();
    uploadForm.append('phone', backupPhone);
    uploadForm.append('trainer_name', 'مربی آرش');
    uploadForm.append('file', fakeSqliteBlob, 'yalda.db');

    const uploadReq = new Request('http://localhost/api/backup/upload', {
        method: 'POST',
        headers: {
            'X-API-Key': 'yalda_cloud_sec_2006_gym'
        },
        body: uploadForm
    });
    const uploadRes = await worker.fetch(uploadReq, env, ctx);
    assert(uploadRes.status === 200, 'POST /api/backup/upload returns HTTP 200');

    // 4. Backup Download API
    const downloadReq = new Request(`http://localhost/api/backup/download/${backupPhone}`, {
        headers: { 'X-API-Key': 'yalda_cloud_sec_2006_gym' }
    });
    const downloadRes = await worker.fetch(downloadReq, env, ctx);
    assert(downloadRes.status === 200, 'GET /api/backup/download/:phone returns HTTP 200');
    const downloadedBuf = Buffer.from(await downloadRes.arrayBuffer());
    assert(downloadedBuf.toString().includes('SQLite format 3'), 'Downloaded file content matches uploaded SQLite binary');

    // 5. Video Stream Range Request
    const videoData = Buffer.alloc(1000, 0xAA);
    await kv.put('video_test_video.mp4', videoData);

    // Range request: first 100 bytes (bytes=0-99) with Accept: video/mp4
    const rangeReq1 = new Request('http://localhost/video/test_video.mp4?raw=1', {
        headers: {
            'Range': 'bytes=0-99',
            'Accept': 'video/mp4'
        }
    });
    const rangeRes1 = await worker.fetch(rangeReq1, env, ctx);
    assert(rangeRes1.status === 206, 'Video Range request returns HTTP 206 Partial Content');
    assert(rangeRes1.headers.get('Content-Range')?.includes('bytes 0-99/1000'), 'Content-Range header formatted correctly');

    // Range request: suffix range for Safari (bytes=-100)
    const rangeReqSafari = new Request('http://localhost/video/test_video.mp4?raw=1', {
        headers: {
            'Range': 'bytes=-100',
            'Accept': 'video/mp4'
        }
    });
    const rangeResSafari = await worker.fetch(rangeReqSafari, env, ctx);
    assert(rangeResSafari.status === 206, 'Safari suffix Range request (bytes=-N) returns HTTP 206');
    assert(rangeResSafari.headers.get('Content-Range')?.includes('bytes 900-999/1000'), 'Suffix range correctly offsets from end of file');

    // 6. Image Sandboxed Viewer & Direct Raw
    const imgData = Buffer.from('\xFF\xD8\xFF\xE0\x00\x10JFIFfake_image_bytes');
    await kv.put('image_test_image.jpg', imgData);

    const imgViewerReq = new Request('http://localhost/image/test_image.jpg', {
        headers: { 'Accept': 'text/html,application/xhtml+xml' }
    });
    const imgViewerRes = await worker.fetch(imgViewerReq, env, ctx);
    const imgViewerHtml = await imgViewerRes.text();
    assert(imgViewerRes.status === 200, 'GET /image/:filename with Accept: text/html returns HTTP 200');
    assert(imgViewerHtml.includes('<meta name="viewport" content="width=device-width, initial-scale=1.0">'), 'Sandboxed image viewer includes responsive viewport');
    assert(imgViewerHtml.includes('test_image.jpg'), 'Sandboxed image viewer displays image filename');

    // 7. Backup Delete API (via Desktop Client Key)
    const deleteReq = new Request(`http://localhost/api/backup/delete/${backupPhone}`, {
        method: 'POST',
        headers: { 'X-API-Key': 'yalda_cloud_sec_2006_gym' }
    });
    const deleteRes = await worker.fetch(deleteReq, env, ctx);
    assert(deleteRes.status === 200, 'POST /api/backup/delete/:phone via X-API-Key returns HTTP 200');

    // Verify deletion occurred in KV
    const checkDeletedKv = await kv.get(`meta_${backupPhone}`);
    assert(checkDeletedKv === null, 'Deleted backup metadata removed from KV');

    // 8. SMS Recharge API
    const rechargeReq = new Request('http://localhost/api/admin/sms/recharge', {
        method: 'POST',
        headers: {
            'X-API-Key': 'yalda_cloud_sec_2006_gym',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            phone: '09121112233',
            amount: 150
        })
    });
    const rechargeRes = await worker.fetch(rechargeReq, env, ctx);
    assert(rechargeRes.status === 200, 'POST /api/admin/sms/recharge returns HTTP 200');
    const rechargeJson = await rechargeRes.json();
    assert(rechargeJson.success === true, 'SMS recharge response indicates success');
    assert(rechargeJson.remaining >= 150, `Trainer SMS account credited correctly (remaining: ${rechargeJson.remaining})`);

    // 9. Logout
    const logoutReq = new Request('http://localhost/logout');
    const logoutRes = await worker.fetch(logoutReq, env, ctx);
    assert(logoutRes.status === 303, 'GET /logout redirects (HTTP 303)');
    assert(logoutRes.headers.get('Set-Cookie')?.includes('Max-Age=0'), 'Set-Cookie clears auth session token');

    console.log(`\n${BLUE}====================================================${RESET}`);
    console.log(`Total tests run: ${passedTests + failedTests}`);
    console.log(`Passed: ${GREEN}${passedTests}${RESET}`);
    console.log(`Failed: ${failedTests > 0 ? RED : GREEN}${failedTests}${RESET}`);
    console.log(`${BLUE}====================================================${RESET}\n`);

    if (failedTests > 0) {
        process.exit(1);
    }
}

runAudit().catch(err => {
    console.error(`${RED}Fatal audit test error:${RESET}`, err);
    process.exit(1);
});
