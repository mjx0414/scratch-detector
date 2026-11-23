"""
真实验证：把算法检测结果与人工真值对比，计算真实准确率。
不编数字——所有指标都由下面真实计算得出。
"""
import cv2
import json
import os
import time
from detector import detect_scratches

ROOT = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(ROOT, "examples")
GT = json.load(open(os.path.join(EX, "ground_truth.json"), encoding="utf-8"))


def iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def match(detections, truths):
    """把每个真值划痕匹配到 IoU 最大的检测框，返回匹配对"""
    used = set()
    pairs = []
    for t in truths:
        best_i, best_iou = -1, 0
        for i, d in enumerate(detections):
            if i in used:
                continue
            v = iou(d["box"], t["box"])
            if v > best_iou:
                best_i, best_iou = i, v
        if best_i >= 0 and best_iou >= 0.15:
            used.add(best_i)
            pairs.append((best_i, best_iou))
    return pairs


def run():
    total_gt = 0
    total_detected = 0
    total_matched = 0
    length_errors = []
    angle_errors = []
    per_image = []
    times = []

    for name, info in GT.items():
        img = cv2.imread(os.path.join(EX, name))
        truths = info["scratches"]
        t0 = time.perf_counter()
        result = detect_scratches(img, sensitivity=1.0)
        took = (time.perf_counter() - t0) * 1000
        times.append(took)

        dets = result["scratches"]
        pairs = match(dets, truths)
        matched = len(pairs)
        total_gt += len(truths)
        total_detected += len(dets)
        total_matched += matched

        for di, iou_v in pairs:
            d = dets[di]
            # 找对应真值（按匹配顺序不严格，这里用 IoU 再定位一次）
            for t in truths:
                if iou(d["box"], t["box"]) >= iou_v - 1e-6:
                    length_errors.append(abs(d["length"] - t["length"]))
                    # 角度差异取最小夹角
                    diff = abs(d["angle"] - t["angle"]) % 180
                    angle_errors.append(min(diff, 180 - diff))
                    break

        recall = matched / len(truths) if truths else 0
        precision = matched / len(dets) if dets else 0
        per_image.append({
            "image": name,
            "truth": len(truths),
            "detected": len(dets),
            "matched": matched,
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "tookMs": round(took, 1),
        })
        print(f"{name}: 真值 {len(truths)} / 检测 {len(dets)} / 匹配 {matched} "
              f"| 召回 {recall*100:.0f}% | 精确 {precision*100:.0f}% | {took:.0f}ms")

    recall = total_matched / total_gt if total_gt else 0
    precision = total_matched / total_detected if total_detected else 0
    result = {
        "summary": {
            "totalTruth": total_gt,
            "totalDetected": total_detected,
            "totalMatched": total_matched,
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "meanLengthErrorPx": round(sum(length_errors) / len(length_errors), 2) if length_errors else None,
            "meanAngleErrorDeg": round(sum(angle_errors) / len(angle_errors), 2) if angle_errors else None,
            "avgTimeMs": round(sum(times) / len(times), 1),
        },
        "perImage": per_image,
        "config": {"sensitivity": 1.0, "iouMatchThreshold": 0.15},
    }

    out = os.path.join(ROOT, "experiments", "results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n=== 汇总 ===")
    print(f"召回率 {recall*100:.1f}% | 精确率 {precision*100:.1f}% "
          f"| 长度平均误差 {result['summary']['meanLengthErrorPx']}px "
          f"| 角度平均误差 {result['summary']['meanAngleErrorDeg']}° "
          f"| 平均耗时 {result['summary']['avgTimeMs']}ms")
    print("已保存", out)
    return result


if __name__ == "__main__":
    run()
