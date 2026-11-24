"""
对 4 张纯黑屏幕展示图做真实验证
输出 experiments/results_black.json，供静态展示页使用
"""
import os
import json
import time
import cv2

from detector import detect_scratches

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "examples_black")
GT_PATH = os.path.join(SRC, "black_ground_truth.json")
OUT = os.path.join(ROOT, "experiments", "results_black.json")


def iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / max(1.0, area_a + area_b - inter)


def main():
    gt = json.load(open(GT_PATH, encoding="utf-8"))
    per_image = []
    total_truth = total_detected = total_matched = 0
    len_errors = []
    times = []

    for name, g in gt.items():
        img = cv2.imread(os.path.join(SRC, name))
        t0 = time.perf_counter()
        r = detect_scratches(img, 1.0)
        took = (time.perf_counter() - t0) * 1000
        times.append(took)

        truth_boxes = [s["box"] for s in g["scratches"]]
        truth_lens = [s["length"] for s in g["scratches"]]
        det_boxes = [s["box"] for s in r["scratches"]]
        det_lens = [s["length"] for s in r["scratches"]]

        matched = 0
        for tb, tl in zip(truth_boxes, truth_lens):
            best = -1; best_iou = 0.3
            for i, db in enumerate(det_boxes):
                v = iou(tb, db)
                if v > best_iou:
                    best_iou = v; best = i
            if best >= 0:
                matched += 1
                len_errors.append(abs(det_lens[best] - tl))

        total_truth += len(truth_boxes)
        total_detected += len(det_boxes)
        total_matched += matched
        per_image.append({
            "image": name, "truth": len(truth_boxes), "detected": len(det_boxes),
            "matched": matched,
            "recall": matched / max(1, len(truth_boxes)),
            "precision": matched / max(1, len(det_boxes)),
            "tookMs": round(took, 1),
        })
        print(f"{name}: truth {len(truth_boxes)} / detected {len(det_boxes)} / matched {matched}")

    summary = {
        "totalTruth": total_truth,
        "totalDetected": total_detected,
        "totalMatched": total_matched,
        "recall": total_matched / max(1, total_truth),
        "precision": total_matched / max(1, total_detected),
        "meanLengthErrorPx": round(sum(len_errors) / max(1, len(len_errors)), 2),
        "avgTimeMs": round(sum(times) / max(1, len(times)), 1),
    }
    data = {"summary": summary, "perImage": per_image}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\nsummary:", json.dumps(summary, ensure_ascii=False))
    print("saved:", OUT)


if __name__ == "__main__":
    main()
