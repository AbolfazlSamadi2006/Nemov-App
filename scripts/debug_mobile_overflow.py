import subprocess
import pathlib

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ARTIFACTS_DIR = pathlib.Path(r"C:\Users\user\.gemini\antigravity\brain\4b6897a3-c508-4ec6-8c8a-20cd600f30a6")
temp_html = ARTIFACTS_DIR / "temp_landing.html"

# Inject JS script to find overflowing elements
script_to_inject = """
<script>
window.addEventListener('load', function() {
    var docW = document.documentElement.clientWidth;
    var all = document.querySelectorAll('*');
    var overflowing = [];
    all.forEach(function(el) {
        var rect = el.getBoundingClientRect();
        if (rect.right > docW + 1 || rect.left < -1 || rect.width > docW + 1) {
            overflowing.push({
                tag: el.tagName,
                cls: el.className,
                id: el.id,
                width: rect.width,
                left: rect.left,
                right: rect.right
            });
        }
    });
    console.log('DOC_WIDTH: ' + docW);
    console.log('OVERFLOWING_COUNT: ' + overflowing.length);
    overflowing.slice(0, 15).forEach(function(o) {
        console.log('OVERFLOW: ' + o.tag + '.' + o.cls + ' w=' + o.width + ' l=' + o.left + ' r=' + o.right);
    });
});
</script>
"""

content = temp_html.read_text(encoding="utf-8")
temp_test_html = ARTIFACTS_DIR / "temp_debug.html"
temp_test_html.write_text(content.replace("</body>", script_to_inject + "</body>"), encoding="utf-8")

cmd = [
    EDGE_EXE,
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--window-size=390,844",
    str(temp_test_html.resolve())
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
