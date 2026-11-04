const $ = (s) => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmtH = (h) => { const m = Math.round(h * 60); return `${Math.floor(m / 60)}시간 ${String(m % 60).padStart(2, "0")}분`; };
const clock = (h) => { h = ((h % 24) + 24) % 24; const m = Math.round(h * 60); return `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`; };
const md = (iso) => `${+iso.slice(5, 7)}/${+iso.slice(8, 10)}`;
const avg = (a) => a.reduce((s, x) => s + x, 0) / (a.length || 1);
const median = (a) => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };

// 밤 단위 데이터: 첫 줄(9/30 밤, 기록 시작 전)과 마지막 줄(10/31 밤, 기록 끝에서 잘림)은 뺀다
const nights = D.nights.slice(1, -1);
const S = D.summary;
const wakeAvg = avg(nights.map(n => n.wakings));

// ---------- tooltip ----------
const tip = $("#tip");
function showTip(e, html) {
  tip.innerHTML = html; tip.style.opacity = 1;
  const x = (e.touches ? e.touches[0].clientX : e.clientX), y = (e.touches ? e.touches[0].clientY : e.clientY);
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(Math.max(8, x - w / 2), innerWidth - w - 8) + "px";
  tip.style.top = (y - h - 14 < 8 ? y + 18 : y - h - 14) + "px";
}
function hideTip() { tip.style.opacity = 0; }
addEventListener("scroll", hideTip, { passive: true });

function el(tag, attrs = {}, parent) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}
function txt(parent, x, y, s, attrs = {}) { const t = el("text", { x, y, ...attrs }, parent); t.textContent = s; return t; }
function svgFor(box, h) {
  box.innerHTML = "";
  const w = Math.max(280, box.clientWidth);
  const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img" }, box);
  return { svg, w, h };
}
function hover(node, html) {
  node.addEventListener("pointerenter", e => showTip(e, html));
  node.addEventListener("pointermove", e => showTip(e, html));
  node.addEventListener("pointerleave", hideTip);
  node.addEventListener("touchstart", e => showTip(e, html), { passive: true });
}
// 위쪽만 둥근 막대 (4px)
function colPath(x, y, w, h, r = 4) {
  if (h <= 0) return "";
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}
function grid(svg, x0, x1, ys, fmt, yScale) {
  ys.forEach(v => {
    const y = yScale(v);
    el("line", { x1: x0, x2: x1, y1: y, y2: y, stroke: css("--line"), "stroke-width": 1 }, svg);
    txt(svg, x0 - 6, y + 4, fmt(v), { "text-anchor": "end" });
  });
}

