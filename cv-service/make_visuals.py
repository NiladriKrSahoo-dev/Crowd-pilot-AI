import os
import cv2
import numpy as np
from lwcc import LWCC

VIDEO = "crowd_video.mp4"
FRAME_NO = 150            # 150 frames = 5 seconds into the clip
ROWS = 3
COLS = 4
POINTS = [(108, 254), (1266, 300), (2284, 342), (2296, 1058),
          (1144, 1068), (24, 1060), (8, 330)]
BACKGROUND = "photo"       # "dark" = heatmap on black, "blur" = blurred photo, "photo" = original frame
OUT_DIR = "visuals"

os.makedirs(OUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME_NO)
ok, frame = cap.read()
cap.release()
if not ok:
    print("Could not read a frame from", VIDEO)
    raise SystemExit
fh, fw = frame.shape[:2]

cv2.imwrite("frame_tmp.jpg", frame)
model = LWCC.load_model(model_name="CSRNet", model_weights="SHA")
_, dm = LWCC.get_count("frame_tmp.jpg", model=model, return_density=True)
dm = np.clip(np.squeeze(dm), 0, None)
h, w = dm.shape

poly_full = np.array(POINTS, dtype=np.int32)
poly_small = np.array([[x * w / fw, y * h / fh] for x, y in POINTS],
                      dtype=np.int32)
mask_full = np.zeros((fh, fw), dtype=np.uint8)
cv2.fillPoly(mask_full, [poly_full], 1)
mask_small = np.zeros((h, w), dtype=np.uint8)
cv2.fillPoly(mask_small, [poly_small], 1)

everyone = int(round(float(dm.sum())))
inside = int(round(float((dm * mask_small).sum())))
print("everyone:", everyone, " inside the floor:", inside)

if BACKGROUND == "photo":
    base = frame.copy()
elif BACKGROUND == "blur":
    base = cv2.GaussianBlur(frame, (0, 0), 18)
else:
    base = np.full_like(frame, 25)


def heat_overlay(img, only_inside=False):
    up = cv2.resize(dm, (fw, fh), interpolation=cv2.INTER_CUBIC)
    up = cv2.GaussianBlur(up, (0, 0), 20)
    norm = np.clip(up / (np.percentile(up, 99) + 1e-6), 0, 1)
    if only_inside:
        norm = norm * mask_full
    heat = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
    alpha = (norm * 0.8)[..., None]
    out = img.astype(np.float32) * (1 - alpha) + heat.astype(np.float32) * alpha
    return out.astype(np.uint8)


def dim_outside(img, factor=0.7):
    m = mask_full[..., None].astype(np.float32)
    return (img.astype(np.float32) * (m + (1 - m) * factor)).astype(np.uint8)


def draw_outline(img):
    cv2.polylines(img, [poly_full], True, (255, 255, 0), 8)
    return img


def outlined_text(img, text, org, scale, thickness):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, org, font, scale, (0, 0, 0), thickness + 6)
    cv2.putText(img, text, org, font, scale, (255, 255, 255), thickness)


def banner(img, title, subtitle):
    strip = np.zeros((170, fw, 3), dtype=np.uint8)
    cv2.putText(strip, title, (40, 85), cv2.FONT_HERSHEY_SIMPLEX, 2.3,
                (255, 255, 255), 5)
    cv2.putText(strip, subtitle, (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.3,
                (200, 200, 200), 3)
    return np.vstack([strip, img])


def draw_zone_counts(img):
    zh = h // ROWS
    zw = w // COLS
    for r in range(ROWS):
        for c in range(COLS):
            y1 = r * zh
            x1 = c * zw
            y2 = h if r == ROWS - 1 else y1 + zh
            x2 = w if c == COLS - 1 else x1 + zw
            n = float((dm[y1:y2, x1:x2] * mask_small[y1:y2, x1:x2]).sum())

            X1 = int(x1 * fw / w)
            X2 = int(x2 * fw / w)
            Y1 = int(y1 * fh / h)
            Y2 = int(y2 * fh / h)
            cv2.rectangle(img, (X1, Y1), (X2, Y2), (255, 255, 255), 2)

            label = f"{n:.0f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 3.5, 8)
            cx = (X1 + X2) // 2 - tw // 2
            cy = (Y1 + Y2) // 2 + th // 2
            outlined_text(img, label, (cx, cy), 3.5, 8)
    return img


# Picture 1: density heatmap
pic1 = draw_outline(heat_overlay(base))
pic1 = banner(pic1, "Crowd density estimate",
              f"~{inside} people on the hall floor  |  prototype on a stock video clip")

# Picture 2: people per zone, only inside the floor outline
pic2 = draw_outline(dim_outside(base))
pic2 = draw_zone_counts(pic2)
pic2 = banner(pic2, "People per zone",
              "counted only inside the floor outline (zones are a test grid)")

# Picture 3: before / after
left = banner(heat_overlay(base), f"Counting everything: {everyone} people",
              "includes the crowd outside the glass doors")
right = draw_outline(heat_overlay(dim_outside(base), only_inside=True))
right = banner(right, f"Counting only the floor: {inside} people",
               "the model ignores everything outside the outline")
small_h = int(left.shape[0] * 1160 / fw)
pic3 = np.vstack([cv2.resize(left, (1160, small_h)), cv2.resize(right, (1160, small_h))])

for name, pic in [("1_heatmap", pic1), ("2_zones", pic2), ("3_before_after", pic3)]:
    path = os.path.join(OUT_DIR, f"crowd_pilot_{name}.jpg")
    cv2.imwrite(path, pic, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("Saved", path)