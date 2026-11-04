"""월간 리포트 HTML 조립: python assemble.py <본문.html> <data.json> <출력.html>

본문(month_template.html을 복사해 그 달 내용으로 고친 파일)의 __CSS__, __HELPERS__, __DATA__ 자리를 채운다.
"""
import sys
from pathlib import Path

here = Path(__file__).parent
body, data, out = sys.argv[1:4]
js = (here / "_helpers.js").read_text()
for line in ["const nights = D.nights.slice(1, -1);\n", "const S = D.summary;\n", "const wakeAvg = avg(nights.map(n => n.wakings));\n"]:
    js = js.replace(line, "")
html = Path(body).read_text().replace("__CSS__", (here / "_css.html").read_text()).replace("__HELPERS__", js).replace("__DATA__", Path(data).read_text())
Path(out).write_text(html)
print("wrote", out)
