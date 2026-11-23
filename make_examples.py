"""
生成带真值标注的手机屏幕划痕测试图（共 11 张）。
- screen_1~3：原始深色屏幕
- screen_4~11：新增，多种屏幕风格/光照/划痕形态
每张都保存已知位置、长度、角度、明暗类型的真值，用于真实验证。
"""
import cv2
import numpy as np
import json
import os
import math
import random

ROOT = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(ROOT, "examples")
os.makedirs(EX, exist_ok=True)
random.seed(20261123)

W, H = 900, 1600


def make_screen(style=0, glow_angle=0.7, glow_strength=28):
    """生成模拟屏幕。style: 0深蓝灰 1纯黑OLED 2亮银灰 3紫蓝壁纸 4暖色"""
    yy, xx = np.mgrid[0:H, 0:W]
    base = np.zeros((H, W, 3), dtype=np.uint8)
    if style == 0:                      # 深蓝灰（原样）
        for c, val in enumerate([38, 46, 58]):
            base[:, :, c] = (val + (yy / H) * 22).astype(np.uint8)
    elif style == 1:                    # OLED 纯黑，带轻微冷色
        for c, val in enumerate([16, 18, 24]):
            base[:, :, c] = (val + (yy / H) * 8).astype(np.uint8)
    elif style == 2:                    # 亮银灰
        for c, val in enumerate([200, 205, 210]):
            base[:, :, c] = np.clip(val - (yy / H) * 18, 0, 255).astype(np.uint8)
    elif style == 3:                    # 紫蓝渐变壁纸
        t = (yy / H)
        base[:, :, 0] = (40 + 60 * t).astype(np.uint8)
        base[:, :, 1] = (30 + 20 * t).astype(np.uint8)
        base[:, :, 2] = (90 + 50 * (1 - t)).astype(np.uint8)
    elif style == 4:                    # 暖米色
        for c, val in enumerate([225, 218, 200]):
            base[:, :, c] = np.clip(val - (yy / H) * 25, 0, 255).astype(np.uint8)

    # 反光带（方向/强度可变）
    glow = np.clip(glow_strength * np.exp(
        -((xx - glow_angle * yy - 200) ** 2) / (2 * 130 ** 2)), 0, None).astype(np.uint8)
    base = cv2.add(base, cv2.merge([glow, glow, glow]))
    # 细微噪点
    noise = np.random.normal(0, 2.2, (H, W)).astype(np.int16)
    base = np.clip(base.astype(np.int16) + noise[:, :, None], 0, 255).astype(np.uint8)
    return base


def add_scratch(img, x1, y1, length, angle_deg, delta=45, thickness=2, bright=False):
    """画一道划痕。颜色相对起点背景动态计算，暗线/亮线均可。"""
    rad = math.radians(angle_deg)
    x2 = int(x1 + length * math.cos(rad))
    y2 = int(y1 + length * math.sin(rad))
    # 取起点附近背景均值
    ys = slice(max(0, y1 - 3), min(H, y1 + 4))
    xs = slice(max(0, x1 - 3), min(W, x1 + 4))
    bg = img[ys, xs].mean(axis=(0, 1))
    if bright:
        color = tuple(int(np.clip(v + delta, 0, 255)) for v in bg)
    else:
        color = tuple(int(np.clip(v - delta, 0, 255)) for v in bg)
    cv2.line(img, (x1, y1), (x2, y2), color, thickness=thickness, lineType=cv2.LINE_AA)
    return {"box": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
            "length": length, "angle": angle_deg,
            "type": "bright" if bright else "dark"}


# 原始 3 张（保持风格 0）
original = {
    "screen_1.jpg": (0, 0.7, 28, [(120,300,180,25),(600,520,220,-40),(200,900,150,80),(560,1150,200,5)]),
    "screen_2.jpg": (0, 0.7, 28, [(150,240,260,10),(430,700,170,-70),(620,1000,140,45),(180,1300,190,-15),(500,420,120,88)]),
    "screen_3.jpg": (0, 0.7, 28, [(300,360,200,-30),(250,820,240,60),(580,1220,160,20)]),
}

# 新增 8 张：风格、反光角度、反光强度、划痕列表
new = {
    # 纯黑 OLED，4 道暗划痕，方向分散
    "screen_4.jpg": (1, 0.5, 18, [(180,260,210,15),(560,500,240,-35),(220,880,190,70),(600,1200,170,-10)]),
    # 纯黑 OLED，含 1 道亮划痕
    "screen_5.jpg": (1, -0.4, 22, [(200,320,230,-25),(540,640,180,55),(300,1050,250,5),(650,400,150,80)]),
    # 亮银灰屏，暗划痕对比明显
    "screen_6.jpg": (2, 0.8, 30, [(150,380,250,-15),(520,720,200,40),(250,1100,230,-60),(600,300,170,75)]),
    # 亮银灰屏，混合亮划痕
    "screen_7.jpg": (2, 0.3, 25, [(180,280,220,30),(480,600,190,-50),(300,900,240,10),(620,1250,160,-80)]),
    # 紫蓝壁纸，3 道长划痕
    "screen_8.jpg": (3, 0.6, 26, [(140,340,270,20),(500,680,230,-45),(260,1150,250,65)]),
    # 紫蓝壁纸，5 道密集划痕
    "screen_9.jpg": (3, -0.5, 20, [(120,250,190,35),(400,480,150,-20),(620,760,180,60),(200,1000,210,-70),(520,1280,170,15)]),
    # 暖色屏，4 道划痕
    "screen_10.jpg": (4, 0.7, 24, [(160,330,240,-30),(520,560,210,45),(280,950,200,10),(600,1180,180,-65)]),
    # 暖色屏，含亮划痕，划痕更细
    "screen_11.jpg": (4, 0.2, 28, [(200,300,230,25),(560,620,190,-40),(240,1020,220,80),(480,1300,160,-5)]),
}

all_gt = {}
for name, cfg in {**original, **new}.items():
    style, glow_ang, glow_str, scratches = cfg
    img = make_screen(style, glow_ang, glow_str)
    gt = []
    for idx, (x1, y1, length, angle) in enumerate(scratches):
        # 新增图中每隔几道放一道亮划痕，增加形态多样性
        bright = (name in new and idx == 1 and name in ("screen_5.jpg", "screen_7.jpg", "screen_11.jpg"))
        delta = 42 if bright else 46
        thickness = 2 if not bright else 2
        gt.append(add_scratch(img, x1, y1, length, angle, delta, thickness, bright))
    path = os.path.join(EX, name)
    cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 96])
    all_gt[name] = {"size": [W, H], "scratches": gt}
    print(f"生成 {name}: 风格{style} · {len(gt)} 道划痕")

with open(os.path.join(EX, "ground_truth.json"), "w", encoding="utf-8") as f:
    json.dump(all_gt, f, ensure_ascii=False, indent=2)
print(f"\n完成！共 {len(all_gt)} 张图，真值已保存 examples/ground_truth.json")
