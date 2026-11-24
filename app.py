"""
手机划痕检测工作台
启动: python app.py
访问: http://localhost:3300
"""
import os
import base64
import glob
import time
from flask import Flask, request, jsonify, send_from_directory

from detector import detect_scratches

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
EXAMPLES = os.path.join(ROOT, "examples_black")

app = Flask(__name__, static_folder=None)


@app.route("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(WEB, filename)


@app.route("/api/examples")
def examples():
    out = []
    # 按文件名自然顺序排列（screen_1 … screen_11）
    def order(p):
        import re
        n = os.path.basename(p)
        m = re.search(r"(\d+)", n)
        return (int(m.group(1)) if m else 999, n)
    for path in sorted(glob.glob(os.path.join(EXAMPLES, "black_screen_*.jpg")), key=order):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        out.append({"name": os.path.basename(path),
                    "src": "data:image/jpeg;base64," + b64})
    return jsonify(out)


@app.route("/api/detect", methods=["POST"])
def detect():
    import cv2
    import numpy as np
    data = request.get_json(silent=True) or {}
    src = data.get("image", "")
    sens = float(data.get("sensitivity", 1.0))
    sens = max(0.4, min(2.5, sens))
    if "," in src and src.strip().startswith("data:"):
        src = src.split(",", 1)[1]
    try:
        raw = base64.b64decode(src)
    except Exception:
        return jsonify({"error": "图片数据无效"}), 400
    img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "无法解析图片"}), 400

    t0 = time.perf_counter()
    result = detect_scratches(img, sensitivity=sens)
    took = round((time.perf_counter() - t0) * 1000, 1)

    return jsonify({
        "width": result["width"], "height": result["height"],
        "count": result["count"], "scratches": result["scratches"],
        "threshold": result["threshold"], "tookMs": took,
        "sensitivity": sens,
    })


@app.route("/api/results")
def results():
    with open(os.path.join(ROOT, "experiments", "results_black.json"), encoding="utf-8") as f:
        return jsonify(__import__("json").load(f))


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "engine": "形态学对比度+旋转矩形"})


if __name__ == "__main__":
    print("=" * 50)
    print("  手机划痕检测工作台")
    print("  打开: http://localhost:3300")
    print("=" * 50, flush=True)
    app.run(host="127.0.0.1", port=3300, debug=False, threaded=True)
