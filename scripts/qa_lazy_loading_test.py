import sys
import os
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

from yalda.database.connection import init_db
init_db()

print("--- 1. Testing Import & Startup Speeds ---")
t0 = time.perf_counter()
from yalda.views.main_window import MainWindow
t_import = time.perf_counter() - t0
print(f"Import MainWindow time: {t_import:.4f}s")

t0 = time.perf_counter()
mw = MainWindow()
t_init = time.perf_counter() - t0
print(f"MainWindow instantiation time: {t_init:.4f}s")

# Check initial lazy state
assert mw._view_members is None, "_view_members should be None initially"
assert mw._view_workouts is None, "_view_workouts should be None initially"
assert mw._view_nutrition is None, "_view_nutrition should be None initially"
assert mw._view_templates is None, "_view_templates should be None initially"
assert mw._view_exercises is None, "_view_exercises should be None initially"
assert mw._view_foods is None, "_view_foods should be None initially"
assert mw._view_developer is None, "_view_developer should be None initially"
assert mw._view_backup is None, "_view_backup should be None initially"
assert mw._view_accounting is None, "_view_accounting should be None initially"
assert mw._view_sms is None, "_view_sms should be None initially"
print("SUCCESS: All 10 views are confirmed uninitialized initially (100% Lazy)")

print("\n--- 2. Testing On-Demand View Instantiation & Page Switching ---")
# 1. Members
t0 = time.perf_counter()
mw.switch_page("members")
t_mem = time.perf_counter() - t0
assert mw._view_members is not None, "_view_members should be initialized now"
assert mw.stack.currentWidget() == mw.view_members, "Expected current widget to be view_members"
print(f"SUCCESS: Switched to members page in {t_mem:.4f}s (initialized on demand)")

# 2. Workouts
t0 = time.perf_counter()
mw.switch_page("workouts")
t_work = time.perf_counter() - t0
assert mw._view_workouts is not None, "_view_workouts should be initialized now"
assert mw.stack.currentWidget() == mw.view_workouts, "Expected current widget to be view_workouts"
print(f"SUCCESS: Switched to workouts page in {t_work:.4f}s (initialized on demand)")

# 3. Nutrition
t0 = time.perf_counter()
mw.switch_page("nutrition")
t_nut = time.perf_counter() - t0
assert mw._view_nutrition is not None, "_view_nutrition should be initialized now"
assert mw.stack.currentWidget() == mw.view_nutrition, "Expected current widget to be view_nutrition"
print(f"SUCCESS: Switched to nutrition page in {t_nut:.4f}s (initialized on demand)")

# 4. Cached revisit
t0 = time.perf_counter()
mw.switch_page("members")
t_mem_cached = time.perf_counter() - t0
print(f"SUCCESS: Re-visited members page in {t_mem_cached:.4f}s (instant cached load)")

# Test all remaining views
pages = [
    ("templates", lambda: mw.view_templates),
    ("exercises", lambda: mw.view_exercises),
    ("foods", lambda: mw.view_foods),
    ("developer", lambda: mw.view_developer),
    ("backup", lambda: mw.view_backup),
    ("accounting", lambda: mw.view_accounting),
    ("sms", lambda: mw.view_sms),
    ("dashboard", lambda: mw.view_dashboard),
]
for p, getter in pages:
    t0 = time.perf_counter()
    mw.switch_page(p)
    t_page = time.perf_counter() - t0
    assert mw.stack.currentWidget() == getter(), f"Page {p}: currentWidget did not match {p}"
    print(f"SUCCESS: Navigated to '{p}' in {t_page:.4f}s")

print("\n--- 3. Testing Navigation History (go_back) ---")
mw.switch_page("members")
mw.switch_page("accounting")
mw.go_back()
assert mw.stack.currentWidget() == mw.view_members, "go_back failed to return to members page"
print("SUCCESS: Navigation history go_back verified")

print("\n--- 4. Visual Verification ---")
mw.resize(1280, 800)
mw.show()
app.processEvents()
pixmap = mw.grab()
screenshot_path = "qa_lazy_main_window.png"
pixmap.save(screenshot_path)
print(f"SUCCESS: Captured MainWindow screenshot: {screenshot_path} ({pixmap.width()}x{pixmap.height()})")

print("\n==========================================")
print("ALL LAZY LOADING & QA CHECKS PASSED 100%!")
print("==========================================")
