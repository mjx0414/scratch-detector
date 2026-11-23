/* 屏幕医生 · 前端 */
(function () {
  const $ = (id) => document.getElementById(id);
  const state = { currentSrc: null, name: "屏幕", scratches: [], w: 0, h: 0, sens: 1.0 };
  const PALETTE = ["#e11d48", "#f59e0b", "#8b5cf6", "#0ea5e9", "#10b981", "#ec4899"];

  async function init() {
    await Promise.all([loadExamples(), loadExperiment()]);
    bindEvents();
  }

  async function loadExamples() {
    const list = await fetch("/api/examples").then((x) => x.json());
    const box = $("example-list");
    box.innerHTML = "";
    list.forEach((ex, i) => {
      const d = document.createElement("div");
      d.className = "example-thumb";
      d.innerHTML = `<img src="${ex.src}"><span>${ex.name.replace(".jpg", "")}</span>`;
      d.onclick = () => selectImage(ex.src, ex.name, d, true);
      box.appendChild(d);
      if (i === 0) { d.classList.add("active"); selectImage(ex.src, ex.name, d, true); }
    });
  }

  async function loadExperiment() {
    const r = await fetch("/api/results").then((x) => x.json());
    const s = r.summary;
    $("stat-recall").textContent = (s.recall * 100).toFixed(0) + "%";
    $("stat-precision").textContent = (s.precision * 100).toFixed(0) + "%";
    $("stat-error").textContent = s.meanLengthErrorPx + "px";
    $("stat-speed").textContent = s.avgTimeMs + "ms";
    $("stat-note").textContent = `以上指标来自 ${s.totalTruth} 道人工标注划痕的真实检测实验 · 检出 ${s.totalMatched}/${s.totalTruth}`;
    $("exp-tbody").innerHTML = r.perImage.map((p) => `
      <tr><td>${p.image}</td><td>${p.truth}</td><td>${p.matched}</td>
      <td class="good">${(p.recall * 100).toFixed(0)}%</td>
      <td class="good">${(p.precision * 100).toFixed(0)}%</td><td>${p.tookMs}ms</td></tr>
    `).join("");
    $("exp-honest").innerHTML = `💡 <b>诚实说明：</b>这些测试图是程序生成的——我们在模拟屏幕上画了 ${s.totalTruth} 道已知位置的划痕，算法逐道去找，检出 ${s.totalMatched} 道，长度平均只差 ${s.meanLengthErrorPx}px。真实手机屏幕的反光、指纹、贴膜会干扰结果，灵敏度滑块就是用来应对不同情况的。上传你自己的照片试试看。`;
  }

  function selectImage(src, name, thumb, auto) {
    state.currentSrc = src; state.name = name || "屏幕";
    if (thumb) { document.querySelectorAll(".example-thumb").forEach(x => x.classList.remove("active")); thumb.classList.add("active"); }
    const img = $("target-image");
    img.onload = () => {
      state.w = img.naturalWidth; state.h = img.naturalHeight;
      $("placeholder").hidden = true; $("media-stage").hidden = false;
      clearResults();
      if (auto) runDetection();
    };
    img.src = src;
  }

  function handleFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    const rd = new FileReader();
    rd.onload = (e) => { selectImage(e.target.result, file.name, null, false);
      document.querySelectorAll(".example-thumb").forEach(x => x.classList.remove("active")); };
    rd.readAsDataURL(file);
  }

  async function runDetection() {
    if (!state.currentSrc) { alert("请先选一张图片"); return; }
    const btn = $("detect-btn"); btn.disabled = true; btn.textContent = "检测中…";
    $("detect-meta").textContent = "算法正在分析屏幕…";
    try {
      const r = await fetch("/api/detect", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: state.currentSrc, sensitivity: state.sens }),
      }).then(x => x.json());
      if (r.error) throw new Error(r.error);
      state.scratches = r.scratches || []; state.w = r.width; state.h = r.height;
      drawBoxes(); renderResults();
      $("detect-meta").textContent = `完成！找到 ${r.count} 道划痕，用时 ${r.tookMs}ms`;
    } catch (e) { $("detect-meta").textContent = "检测失败：" + e.message; }
    finally { btn.disabled = false; btn.textContent = "🔍 开始检测"; }
  }

  function svg(tag, attrs) { const el = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const k in attrs) el.setAttribute(k, attrs[k]); return el; }

  function drawBoxes() {
    const ov = $("overlay"); ov.innerHTML = "";
    ov.setAttribute("viewBox", `0 0 ${state.w} ${state.h}`);
    const fs = Math.max(13, Math.round(Math.min(state.w, state.h) / 42));
    const sw = Math.max(2, Math.round(Math.min(state.w, state.h) / 260));
    state.scratches.forEach((s, i) => {
      const [x1, y1, x2, y2] = s.box;
      const c = PALETTE[i % PALETTE.length];
      const bw = Math.max(2, x2 - x1), bh = Math.max(2, y2 - y1);
      ov.appendChild(svg("rect", { x: x1, y: y1, width: bw, height: bh,
        fill: c, "fill-opacity": .12, stroke: c, "stroke-width": sw }));
      const label = `划痕${i + 1} · ${s.length}px`;
      let tx = x1, ty = y1 - fs * 1.6;
      if (ty < 0) ty = y1 + 3;
      const tw = label.length * fs * .7 + 10, th = fs * 1.45;
      ov.appendChild(svg("rect", { x: tx, y: ty, width: tw, height: th, rx: 3, fill: c }));
      const t = svg("text", { x: tx + 5, y: ty + fs * 1.05, fill: "#fff",
        "font-size": fs, "font-weight": 800, "font-family": "Microsoft YaHei,sans-serif" });
      t.textContent = label; ov.appendChild(t);
    });
  }

  function renderResults() {
    const box = $("result-list"); const n = state.scratches.length;
    $("result-count").textContent = n ? `${n} 道` : "没找到";
    if (!n) { box.innerHTML = '<div class="result-empty">没检测到划痕，试试调高灵敏度或换张图</div>'; return; }
    box.innerHTML = state.scratches.map((s, i) => `
      <div class="result-item">
        <div class="result-top"><span class="result-id" style="color:${PALETTE[i % PALETTE.length]}">划痕 ${i + 1}</span>
        <span class="result-badge">清晰度 ${s.contrast}</span></div>
        <div class="result-metrics">
          <div class="metric"><b>${s.length} px</b>长度</div>
          <div class="metric"><b>${s.width} px</b>宽度</div>
          <div class="metric"><b>${s.angle}°</b>方向</div>
        </div>
      </div>`).join("");
  }

  function clearResults() {
    state.scratches = []; $("overlay").innerHTML = "";
    $("result-count").textContent = "—";
    $("result-list").innerHTML = '<div class="result-empty">检测结果会显示在这里</div>';
  }

  function sensWord(v) { return v <= 0.7 ? "宽松" : v >= 1.5 ? "严格" : "标准"; }

  function bindEvents() {
    $("detect-btn").onclick = runDetection;
    $("file-input").onchange = (e) => handleFile(e.target.files[0]);
    $("sens-slider").oninput = (e) => {
      const v = Number(e.target.value) / 10; state.sens = v;
      $("sens-value").textContent = sensWord(v) + " " + v.toFixed(1);
    };
    $("sens-slider").onchange = () => { if (state.currentSrc) runDetection(); };
    const wrap = $("canvas-wrap");
    ["dragenter","dragover"].forEach(ev => wrap.addEventListener(ev, e => { e.preventDefault(); wrap.classList.add("dragover"); }));
    ["dragleave","drop"].forEach(ev => wrap.addEventListener(ev, e => { e.preventDefault(); wrap.classList.remove("dragover"); }));
    wrap.addEventListener("drop", e => { if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]); });
    $("present-btn").onclick = () => {
      const on = document.body.classList.toggle("present");
      $("present-btn").textContent = on ? "退出演讲" : "⛶ 演讲模式";
      if (on) document.documentElement.requestFullscreen?.().catch(()=>{});
      else if (document.fullscreenElement) document.exitFullscreen?.();
    };
    document.addEventListener("keydown", e => {
      if (e.key.toLowerCase() === "p" && !e.target.matches("input,textarea")) $("present-btn").click();
    });
  }
  init();
})();
