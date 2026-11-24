"""
生成 GitHub Pages 静态展示页
=============================
带后端的网页别人从 GitHub 点开是打不开的（localhost 只在本机有效）。
本脚本把 11 张样例图的检测结果"预先算好"存成 JS 数据，
网页端读取展示 —— 别人点开 GitHub Pages 链接即可看到完整界面和结果。

注意：静态页是"预计算演示"，不能上传自己的照片实时检测，页面里已明确标注。
运行: python build_static_page.py
"""
import os
import json
import shutil
import time

import cv2

from detector import detect_scratches

ROOT = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(ROOT, "examples")
DOCS = os.path.join(ROOT, "docs")
STATIC_EXAMPLES = os.path.join(DOCS, "examples")


def main():
    os.makedirs(STATIC_EXAMPLES, exist_ok=True)

    with open(os.path.join(EXAMPLES, "ground_truth.json"), encoding="utf-8") as f:
        truth = json.load(f)

    # 静态页只放 4 张有代表性的图（覆盖不同屏幕色调），其余 11 张仍留在 experiments 作真值
    SELECTED = ["screen_1.jpg", "screen_4.jpg", "screen_8.jpg", "screen_10.jpg"]

    # 清理旧的多余图片
    for old in os.listdir(STATIC_EXAMPLES):
        if old.endswith(".jpg") and old not in SELECTED:
            os.remove(os.path.join(STATIC_EXAMPLES, old))
            print("removed old", old)

    names = SELECTED

    precomputed = []
    for name in names:
        img = cv2.imread(os.path.join(EXAMPLES, name))
        if img is None:
            print("skip", name)
            continue
        t0 = time.perf_counter()
        result = detect_scratches(img, sensitivity=1.0)
        took = round((time.perf_counter() - t0) * 1000, 1)
        shutil.copy2(os.path.join(EXAMPLES, name), os.path.join(STATIC_EXAMPLES, name))
        precomputed.append({
            "name": name,
            "src": "examples/" + name,
            "width": result["width"],
            "height": result["height"],
            "count": result["count"],
            "scratches": result["scratches"],
            "tookMs": took,
        })
        print(f"{name}: {result['count']} scratches, {took}ms")

    with open(os.path.join(ROOT, "experiments", "results.json"), encoding="utf-8") as f:
        results = json.load(f)

    data = {
        "examples": precomputed,
        "results": results,
        "note": "检测结果由本项目算法在本地预先计算，静态页仅作展示；实时检测请按 README 在本地运行。",
    }
    out_js = "window.PRECOMPUTED = " + json.dumps(data, ensure_ascii=False) + ";\n"
    with open(os.path.join(DOCS, "data.js"), "w", encoding="utf-8") as f:
        f.write(out_js)

    print(f"\nOK: {len(precomputed)} images -> docs/data.js ({len(out_js)} chars)")
    print("images copied to", STATIC_EXAMPLES)


if __name__ == "__main__":
    main()
