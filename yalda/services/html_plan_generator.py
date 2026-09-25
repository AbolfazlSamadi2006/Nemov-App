import os
import json
from pathlib import Path
import config
from yalda.models.database_models import WorkoutPlan, Member
from yalda.utils.jalali_date import get_today_shamsi

class HTMLPlanGenerator:
    @staticmethod
    def generate_html_plan(member: Member, workout_plan: WorkoutPlan, output_filepath: str = None) -> str:
        """
        Generates a standalone, dark-themed, ultra-responsive HTML workout plan
        with embedded video players, auto-play modal deep linking, and mobile-friendly design.
        """
        if not output_filepath:
            exports_dir = config.DATA_DIR / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            safe_name = "".join(c for c in member.full_name if c.isalnum() or c in (' ', '_', '-')).strip()
            output_filepath = str(exports_dir / f"برنامه_تمرینی_{safe_name}.html")

        goal_map = {
            "hypertrophy": "هایپرتروفی (عضله‌سازی)",
            "fat_loss": "چربی‌سوزی و کاهش وزن",
            "strength": "افزایش قدرت بی‌هوازی",
            "corrective": "حرکات اصلاحی و بهبود قامت",
            "general_fitness": "آمادگی جسمانی عمومی",
            "endurance": "استقامت عضلانی"
        }
        goal_fa = goal_map.get(workout_plan.goal, workout_plan.goal or "-")

        # Collect trainer info
        trainer_name = "مربی باشگاه یلدا"
        trainer_phone = "-"
        try:
            from yalda.auth.authentication import CurrentUser
            from yalda.models.database_models import User
            from yalda.database.connection import SessionLocal

            trainer_user = None

            # 1. Check member's assigned trainer first
            if member:
                user_id = getattr(member, 'user_id', None)
                if user_id:
                    with SessionLocal() as db:
                        trainer_user = db.query(User).filter(User.id == user_id).first()

            # 2. Check logged-in user if trainer_user is not found or is admin
            curr_user = CurrentUser.get()
            if curr_user:
                if not trainer_user or (getattr(trainer_user, 'role', '') == "admin" and getattr(curr_user, 'role', '') == "trainer"):
                    trainer_user = curr_user
                elif not getattr(trainer_user, 'phone', None) and getattr(curr_user, 'phone', None):
                    trainer_user = curr_user

            # 3. Fallback to active gym trainer if still admin or missing phone
            if not trainer_user or (not getattr(trainer_user, 'phone', None) and getattr(trainer_user, 'role', '') == "admin"):
                with SessionLocal() as db:
                    candidate = db.query(User).filter(User.role == "trainer", User.phone.isnot(None), User.phone != "").first()
                    if candidate:
                        trainer_user = candidate

            if trainer_user:
                fn = trainer_user.first_name or ""
                ln = trainer_user.last_name or ""
                name = trainer_user.display_name or trainer_user.full_name or f"{fn} {ln}".strip()
                if name:
                    trainer_name = name
                if trainer_user.phone:
                    trainer_phone = trainer_user.phone
        except Exception:
            pass

        # Build days HTML
        days_html = []
        for day in workout_plan.days:
            exercises_rows = []
            for idx, we in enumerate(day.workout_exercises, start=1):
                ex = we.exercise
                ex_id = ex.id if ex else idx
                ex_name = ex.name_fa if ex else "-"
                
                # Video target URL
                video_url = None
                if ex:
                    video_url = ex.video_cloud_url or ex.video_url
                    if not video_url and ex.media_path and os.path.exists(ex.media_path):
                        # Relative or local file path
                        video_url = Path(ex.media_path).as_uri()

                notes = we.trainer_notes or (ex.description if ex and ex.description else "-")

                safe_title = ex_name.replace("'", "\\'")
                if video_url:
                    name_html = f"""<a href="javascript:void(0)" onclick="openVideoModal('{video_url}', '{safe_title}')" class="exercise-video-link" title="مشاهده فیلم اجرای حرکت"><strong>{ex_name}</strong> <span class="video-badge">🎬 فیلم</span></a>"""
                else:
                    name_html = f"<strong>{ex_name}</strong>"

                exercises_rows.append(f"""
                <tr id="exercise-{ex_id}">
                    <td class="col-num">{idx}</td>
                    <td class="col-name">
                        <div class="name-box">
                            {name_html}
                            {f'<span class="sub-muscle">({ex.secondary_muscles})</span>' if ex and ex.secondary_muscles else ''}
                        </div>
                    </td>
                    <td class="col-sets"><strong>{we.sets}</strong></td>
                    <td class="col-reps">{we.reps}</td>
                    <td class="col-weight">{we.weight_suggestion or "-"}</td>
                    <td class="col-rest">{we.rest_seconds} ثانیه</td>
                    <td class="col-tempo">{we.tempo or "-"}</td>
                    <td class="col-notes">{notes}</td>
                </tr>
                """)

            days_html.append(f"""
            <div class="day-section">
                <div class="day-header">
                    <h2>◄ {day.day_title}</h2>
                </div>
                <div class="table-responsive">
                    <table class="exercise-table">
                        <thead>
                            <tr>
                                <th>ردیف</th>
                                <th>نام حرکت ورزشی</th>
                                <th>ست</th>
                                <th>تکرار</th>
                                <th>وزنه (kg)</th>
                                <th>استراحت</th>
                                <th>ریتم</th>
                                <th>توضیحات و نکات مربی</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(exercises_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
            """)

        full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>برنامه تمرینی {member.full_name} | باشگاه بدنسازی یلدا</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        :root {{
            --bg-color: #0F0F0F;
            --surface-color: #1A1A1A;
            --card-color: #212121;
            --primary-accent: #8B0000;
            --primary-hover: #A91D22;
            --border-color: #333333;
            --text-primary: #FFFFFF;
            --text-secondary: #B0B0B0;
            --text-muted: #737373;
            --success-color: #2E7D32;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 16px;
            font-size: 14px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1050px;
            margin: 0 auto;
        }}
        /* Header Banner */
        .gym-header {{
            background: linear-gradient(135deg, #1C0505 0%, #171717 100%);
            border: 1px solid #4A0E0E;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-title h1 {{
            font-size: 22px;
            font-weight: 800;
            color: #FFFFFF;
            margin-bottom: 6px;
        }}
        .header-title p {{
            font-size: 12.5px;
            color: var(--text-secondary);
        }}
        .gym-badge {{
            background-color: var(--primary-accent);
            color: #FFF;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
        }}
        /* Info Cards Grid */
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}
        .info-card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 18px;
        }}
        .info-card .label {{
            font-size: 11.5px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .info-card .value {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
        }}
        /* Day Sections */
        .day-section {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            margin-bottom: 24px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .day-header {{
            background-color: #242424;
            border-bottom: 2px solid var(--primary-accent);
            padding: 14px 20px;
        }}
        .day-header h2 {{
            font-size: 16px;
            font-weight: 800;
            color: #FFFFFF;
        }}
        .table-responsive {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        .exercise-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: center;
        }}
        .exercise-table th {{
            background-color: #1a1a1a;
            color: #d1d5db;
            padding: 12px 10px;
            font-size: 12px;
            font-weight: 700;
            border-bottom: 1px solid var(--border-color);
        }}
        .exercise-table td {{
            padding: 12px 10px;
            border-bottom: 1px solid #262626;
            font-size: 13px;
            vertical-align: middle;
        }}
        .exercise-table tr:hover {{
            background-color: #242424;
        }}
        .col-name {{
            text-align: right;
            min-width: 170px;
        }}
        .name-box strong {{
            display: block;
            color: #FFFFFF;
            font-size: 13.5px;
        }}
        .sub-muscle {{
            font-size: 11px;
            color: #F87171;
        }}
        /* Hyperlinked Exercise Name & Video Badge */
        .exercise-video-link {{
            color: #60A5FA;
            text-decoration: underline;
            text-underline-offset: 3px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: color 0.2s, transform 0.15s;
        }}
        .exercise-video-link:hover {{
            color: #93C5FD;
            text-decoration-color: #93C5FD;
        }}
        .video-badge {{
            background: rgba(29, 78, 216, 0.25);
            border: 1px solid #1D4ED8;
            color: #93C5FD;
            font-size: 10.5px;
            padding: 1px 6px;
            border-radius: 4px;
            font-weight: normal;
        }}
        .no-video {{
            color: #555;
            font-size: 16px;
        }}
        /* Video Modal */
        .modal-backdrop {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(0, 0, 0, 0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            padding: 16px;
            backdrop-filter: blur(4px);
        }}
        .modal-card {{
            background-color: #171717;
            border: 1px solid #333333;
            border-radius: 16px;
            width: 100%;
            max-width: 540px;
            overflow: hidden;
            box-shadow: 0 20px 50px rgba(0,0,0,0.9);
            animation: modalFadeIn 0.25s ease-out;
        }}
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .modal-header {{
            padding: 14px 18px;
            background: linear-gradient(135deg, #212121, #171717);
            border-bottom: 1px solid #2B2B2B;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-header h3 {{
            font-size: 15px;
            font-weight: 800;
            color: #FFF;
        }}
        .btn-close {{
            background: none;
            border: none;
            color: #A3A3A3;
            font-size: 24px;
            line-height: 1;
            cursor: pointer;
            padding: 0 4px;
        }}
        .btn-close:hover {{
            color: #FFF;
        }}
        .modal-body {{
            background-color: #000;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-body video {{
            width: 100%;
            max-height: 70vh;
            outline: none;
            display: block;
        }}
        /* Footer */
        footer {{
            text-align: center;
            padding: 30px 10px;
            font-size: 12px;
            color: var(--text-muted);
        }}
        footer strong {{
            color: #F87171;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="gym-header">
            <div class="header-title">
                <h1>برنامه تمرینی اختصاصی</h1>
                <p>باشگاه بدنسازی یلدا • مربی: {trainer_name}</p>
            </div>
            <div class="gym-badge">
                نسخه تعاملی چندرسانه‌ای
            </div>
        </header>

        <!-- Athlete Info Cards -->
        <section class="info-grid">
            <div class="info-card">
                <div class="label">نام ورزشکار</div>
                <div class="value">{member.full_name}</div>
            </div>
            <div class="info-card">
                <div class="label">هدف تمرین</div>
                <div class="value">{goal_fa}</div>
            </div>
            <div class="info-card">
                <div class="label">تعداد روزهای تمرین</div>
                <div class="value">{workout_plan.days_per_week} روز در هفته</div>
            </div>
            <div class="info-card">
                <div class="label">شماره تماس مربی</div>
                <div class="value">{trainer_phone}</div>
            </div>
        </section>

        <!-- Days and Exercises -->
        {''.join(days_html)}

        <!-- Footer -->
        <footer>
            طراحی و صادر شده توسط سامانه هوشمند مدیریت باشگاه <strong>یلدا</strong> • {get_today_shamsi()}
        </footer>
    </div>

    <!-- Video Modal -->
    <div id="videoModal" class="modal-backdrop" onclick="closeOnBackdrop(event)">
        <div class="modal-card">
            <div class="modal-header">
                <h3 id="modalExerciseTitle">🎬 فرم اجرای حرکت</h3>
                <button class="btn-close" onclick="closeVideoModal()">&times;</button>
            </div>
            <div class="modal-body">
                <video id="modalVideoPlayer" controls playsinline loop></video>
            </div>
        </div>
    </div>

    <script>
        const modal = document.getElementById('videoModal');
        const videoPlayer = document.getElementById('modalVideoPlayer');
        const modalTitle = document.getElementById('modalExerciseTitle');

        function openVideoModal(videoUrl, title) {{
            if (!videoUrl) return;
            modalTitle.textContent = '🎬 ' + (title || 'فرم اجرای حرکت');
            videoPlayer.src = videoUrl;
            modal.style.display = 'flex';
            videoPlayer.play().catch(e => console.log('Autoplay prevented', e));
        }}

        function closeVideoModal() {{
            videoPlayer.pause();
            videoPlayer.removeAttribute('src');
            modal.style.display = 'none';
        }}

        function closeOnBackdrop(e) {{
            if (e.target === modal) {{
                closeVideoModal();
            }}
        }}

        // Deep-link Support: check hash or query param on load
        window.addEventListener('DOMContentLoaded', () => {{
            const hash = window.location.hash;
            if (hash && hash.startsWith('#exercise-')) {{
                const targetRow = document.querySelector(hash);
                if (targetRow) {{
                    targetRow.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    targetRow.style.backgroundColor = 'rgba(139, 0, 0, 0.3)';
                    const playBtn = targetRow.querySelector('.btn-play, .thumb-container');
                    if (playBtn) {{
                        playBtn.click();
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(full_html)

        return output_filepath
