"""
生成“纯黑手机屏幕 + 多道清晰划痕”展示图
==========================================
按用户要求：屏幕只有黑色，不要其他颜色；划痕多一些、明显一些。
生成 4 张，每张都带真值文件，并用 detector 自检确保全部可检出。

运行: python make_black_photos.py
输出: black_screen_1.jpg ~ black_screen_4.jpg + black_ground_truth.json
"""
import os
import json
import cv2
import numpy as np

from detector import detect_scratches

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "examples_black")
os.makedirs(OUT, exist_ok=True)

W, H = 900, 1600

# 每张图的划痕: (x1,y1,length,angle_deg,type)  type: dark/bright
# 全黑屏上用明亮的浅灰划痕最清晰（真实屏幕划痕在熄屏黑 backgrounds 上呈反光细线）
CONFIGS = {
    "black_screen_1.jpg": [
        (150, 240, 230, 20, "bright"),
        (560, 380, 200, -35, "bright"),
        (220, 760, 260, 75, "bright"),
        (520, 1080, 210, 5, "bright"),
        (300, 1300, 180, -20, "bright"),
    ],
    "black_screen_2.jpg": [
        (130, 300, 250, -15, "bright"),
        (520, 520, 190, 45, "bright"),
        (260, 820, 240, 60, "bright"),
        (600, 1120, 200, -10, "bright"),
        (180, 1300, 170, 30, "bright"),
    ],
    "black_screen_3.jpg": [
        (180, 260, 220, 35, "bright"),
        (540, 480, 210, -40, "bright"),
        (240, 900, 250, 80, "bright"),
        (560, 1200, 190, 0, "bright"),
    ],
    "black_screen_4.jpg": [
        (140, 280, 240, 10, "bright"),
        (520, 420, 200, -30, "bright"),
        (280, 780, 230, 55, "bright"),
        (560, 1050, 220, -60, "bright"),
        (200, 1320, 180, 15, "bright"),
    ],
}


def make_black_screen():
    """纯黑屏幕：只有极轻微的暗部噪点，无任何彩色背景/渐变"""
    rng = np.random.default_rng(7)
    img = np.zeros((H, W, 3), dtype=np.uint8)
    # 加一层非常轻的暗噪，避免绝对纯黑导致jpeg压缩伪影
    noise = rng.normal(0, 1.2, (H, W)).astype(np.int16)
    for c in range(3):
        img[:, :, c] = np.clip(6 + noise, 0, 20).astype(np.uint8)
    return img


def draw_scratch(img, x, y, length, angle, typ="bright"):
    rad = np.deg2rad(angle)
    x2 = int(x + length * np.cos(rad))
    y2 = int(y + length * np.sin(rad))
    # 黑屏上划痕呈亮线，带一点柔和边缘
    delta = 95 if typ == "bright" else -70
    color = tuple(int(np.clip(img[y, x, c] + delta, 0, 255)) for c in range(3))
    cv2.line(img, (x, y), (x2, y2), color, thickness=3, lineType=cv2.LINE_AA)
    # 给框一个最小厚度，避免水平/垂直划痕出现零高度/零宽度的退化框
    bx1, by1 = min(x, x2), min(y, y2)
    bx2, by2 = max(x, x2), max(y, y2)
    if bx2 - bx1 < 3:
        cx = (bx1 + bx2) // 2
        bx1, bx2 = cx - 2, cx + 2
    if by2 - by1 < 3:
        cy = (by1 + by2) // 2
        by1, by2 = cy - 2, cy + 2
    box = [bx1, by1, bx2, by2]
    return {"box": box, "length": length, "angle": angle, "type": typ}


def main():
    truth = {}
    for name, scratches in CONFIGS.items():
        img = make_black_screen()
        gt_scratches = [draw_scratch(img, *s) for s in scratches]
        cv2.imwrite(os.path.join(OUT, name), img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        truth[name] = {"size": [W, H], "scratches": gt_scratches}

        # 自检：用当前算法检测，确认全部可检出
        r = detect_scratches(img, 1.0)
        ok = "OK" if r["count"] == len(scratches) else f"只检出 {r['count']}/{len(scratches)}"
        print(f"{name}: 真值 {len(scratches)} 道, 检出 {r['count']} 道 -> {ok}")

    with open(os.path.join(OUT, "black_ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(truth, f, ensure_ascii=False, indent=2)
    print("\n输出目录:", OUT)


if __name__ == "__main__":
    main()
