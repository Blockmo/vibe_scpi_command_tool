# -*- coding: utf-8 -*-
"""產生 All-In-One 的應用程式圖示 Assets/app.ico（16~256 多尺寸）與預覽 Assets/app_preview.png。

設計：圓角方塊、青綠 → 天藍對角漸層（同介面 logo），中間一條深色「訊號波形」
（平線 → 上衝 → 下衝 → 回到平線），代表各式量測 / 訊號儀器的整合。
小尺寸（≤32px）單獨繪製並加粗線條，避免縮小後糊掉。

用法：python tools/make_icon.py
"""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "Assets")

C1 = (45, 212, 191)    # #2DD4BF 青綠
C2 = (56, 189, 248)    # #38BDF8 天藍
INK = (6, 35, 31)      # #06231F 深色波形（同 OnAccent）

# 波形折點（正規化座標 0~1）
WAVE = [(0.17, 0.56), (0.35, 0.56), (0.44, 0.27), (0.555, 0.76), (0.635, 0.44), (0.69, 0.56), (0.83, 0.56)]


def render(size: int) -> Image.Image:
    ss = 8 if size <= 64 else 4                     # 超取樣倍數
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 對角漸層
    grad = Image.new("RGBA", (S, S))
    gp = grad.load()
    for y in range(S):
        for x in range(S):
            t = (x + y) / (2 * (S - 1))
            gp[x, y] = tuple(int(C1[i] + (C2[i] - C1[i]) * t) for i in range(3)) + (255,)

    # 圓角遮罩（小尺寸邊距較小，保留辨識面積）
    margin = int(S * (0.04 if size <= 32 else 0.06))
    radius = int(S * 0.23)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([margin, margin, S - margin - 1, S - margin - 1], radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # 上緣淡淡的高光：由上往下漸淡（不留硬邊）
    hl = Image.new("L", (S, S), 0)
    hp = hl.load()
    fade_end = S * 0.6
    for y in range(S):
        a = int(46 * max(0.0, 1 - (y - margin) / (fade_end - margin))) if y >= margin else 0
        for x in range(S):
            hp[x, y] = a
    white = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    img = Image.composite(white, img, Image.composite(hl, Image.new("L", (S, S), 0), mask))

    # 波形（小尺寸加粗）
    width_ratio = 0.13 if size <= 16 else 0.115 if size <= 32 else 0.085
    w = max(1, int(S * width_ratio))
    pts = [(x * S, y * S) for x, y in WAVE]
    d = ImageDraw.Draw(img)
    d.line(pts, fill=INK + (255,), width=w, joint="curve")
    r = w / 2
    for (x, y) in (pts[0], pts[-1]):                # 圓頭
        d.ellipse([x - r, y - r, x + r, y + r], fill=INK + (255,))

    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    big = imgs[-1]
    big.save(os.path.join(OUT, "app.ico"), format="ICO",
             sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    # 預覽：各尺寸排一排（深 / 淺底各一列）
    pad = 16
    W = sum(sizes) + pad * (len(sizes) + 1)
    H = 256 * 2 + pad * 3
    prev = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    ImageDraw.Draw(prev).rectangle([0, 0, W, 256 + pad * 1.5], fill=(14, 18, 23, 255))
    x = pad
    for s, im in zip(sizes, imgs):
        prev.alpha_composite(im, (x, pad + 256 - s))
        prev.alpha_composite(im, (x, pad * 2 + 256 + 256 - s))
        x += s + pad
    prev.save(os.path.join(OUT, "app_preview.png"))
    print("saved", os.path.join(OUT, "app.ico"))


if __name__ == "__main__":
    main()
