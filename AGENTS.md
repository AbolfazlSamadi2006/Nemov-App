# Project Rules: Surgical Scope Isolation & Safety Protocol

1. **Strict Scope Isolation (عدم دستکاری بخش‌های نامربوط)**:
   - Only touch the exact components, functions, or files specified by the user.
   - Never modify unrelated styling, colors, layout, or logic.

2. **Automated Pre-Change Backup (بکاپ‌گیری خودکار قبل از هر تغییر)**:
   - Always run the backup script before making code changes:
     `.\venv\Scripts\python.exe C:\Users\user\.gemini\config\skills\isolated-changes\scripts\create_backup.py -p . -a YaldaGym -t <change_tag>`
   - Backups reside in: `C:\Users\user\.gemini\antigravity\project_backups`

3. **Pre-Existing / Unrelated Errors Policy**:
   - If unrelated errors or bugs are found, DO NOT fix them automatically; report them to the user and wait for explicit instructions.

4. **Mandatory Indirect Dependencies**:
   - Only apply indirect changes if strictly necessary for the requested feature/fix to work. Document and explain them clearly.

5. **Post-Change Verification**:
   - Verify using `git diff` that no unintended files or lines were touched.

6. **Codebase & API Consistency Verification (تطابق کامل متدها، مدل‌ها و متغیرها با ساختار موجود)**:
   - Always inspect existing definitions, signatures, and usage patterns before calling or referencing them.

7. **Mandatory Post-Change Visual & Functional QA Inspection (بررسی و کنترل کیفیت ظاهری و عملکردی پس از هر تغییر)**:
   - Whenever adding a feature or applying a modification (UI widgets, tables, buttons, PDFs, Excel exports, layouts, or logic), ALWAYS perform an end-to-end visual and functional verification of the modified component before delivering the final result.
   - Check geometry, alignment, margins/padding, clipping/truncation, text direction (RTL/BiDi), and runtime behavior using test renders, geometry checks, or verification scripts.
   - Proactively detect and fix any visual distortion, overlap, clipping, or bug in the modified target so the delivered output is 100% complete and flawless.

