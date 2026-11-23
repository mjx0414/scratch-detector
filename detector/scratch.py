"""
手机屏幕划痕检测算法
==================
划痕 = 屏幕上一道又细又长的线。难点是屏幕有渐变和反光，直接阈值会误判背景。

步骤（讲人话）：
  1. 局部对比度：用形态学估计"局部背景"，像素与背景差异大的地方响应强
     —— 划痕处会突然变暗/变亮，形成细长的强响应带
  2. 阈值二值化 + 小闭运算连接断裂的线段
  3. 连通域分析：对每个候选区域用"旋转矩形"量真实长度和宽度
     —— 旋转矩形不受划痕倾斜角度影响，能准确判断"细长"
  4. 筛选：长度够长、宽度够细、长宽比大的才算划痕，其余是反光/噪点

纯传统视觉算法，无需训练数据。
"""
import cv2
import numpy as np


def detect_scratches(image_bgr, sensitivity=1.0):
    """
    检测划痕。sensitivity 0.5(宽松) ~ 2.0(严格)
    返回 dict(count, scratches[{box,length,width,angle,contrast}], threshold)
    """
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # --- 1. 局部对比度 ---
    small = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    bg_close = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, small)
    bg_open = cv2.morphologyEx(gray, cv2.MORPH_OPEN, small)
    dark_line = cv2.subtract(bg_close, gray)
    bright_line = cv2.subtract(gray, bg_open)
    response = cv2.max(dark_line, bright_line)

    # 灵敏度 -> 阈值
    thresh = max(10, int(16 / max(0.4, sensitivity)))
    _, binary = cv2.threshold(response, thresh, 255, cv2.THRESH_BINARY)
    acc = cv2.morphologyEx(binary, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

    # --- 2. 连通域 + 旋转矩形量测 ---
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(acc, 8)
    scratches = []
    min_len = max(20, int(32 / max(0.4, sensitivity)))
    max_width = max(7, int(9 * sensitivity))       # 划痕最大宽度(像素)
    min_ratio = 4.0                                # 长宽比下限

    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if max(bw, bh) < min_len:
            continue
        mask = (labels == i).astype(np.uint8) * 255
        pts = cv2.findNonZero(mask)
        if pts is None:
            continue
        rect = cv2.minAreaRect(pts)
        (_, _), (rw, rh), angle = rect
        length, width = max(rw, rh), min(rw, rh)
        if length < min_len or width > max_width:
            continue
        if length / max(0.1, width) < min_ratio:
            continue
        if area < length * 0.8:
            continue
        # 角度归一到 0~180，沿长边方向
        if rw < rh:
            angle += 90
        angle = angle % 180
        contrast = int(response[labels == i].mean())
        scratches.append({
            "box": [int(x), int(y), int(x + bw), int(y + bh)],
            "length": int(round(length)),
            "width": round(width, 1),
            "angle": int(round(angle)),
            "contrast": contrast,
            "cx": round(float(centroids[i][0]), 1),
            "cy": round(float(centroids[i][1]), 1),
        })

    scratches.sort(key=lambda s: -s["length"])
    return {
        "width": w, "height": h, "count": len(scratches),
        "scratches": scratches, "threshold": thresh,
    }


def draw_scratches(image_bgr, result, color=(0, 0, 255)):
    out = image_bgr.copy()
    for s in result["scratches"]:
        x1, y1, x2, y2 = s["box"]
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
    return out
