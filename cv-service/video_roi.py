import cv2
import numpy as np
from lwcc import LWCC

VIDEO = "crowd_video.mp4"
ROWS = 3
COLS = 4
POINTS = [(108, 254), (1266, 300), (2284, 342), (2296, 1058),
          (1144, 1068), (24, 1060), (8, 330)]
SAMPLE_EVERY_SEC = 1

model = LWCC.load_model(model_name="CSRNet", model_weights="SHA")

cap = cv2.VideoCapture(VIDEO)
if not cap.isOpened():
    print("Could not open", VIDEO)
    raise SystemExit

fps = cap.get(cv2.CAP_PROP_FPS)
frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
step = int(fps * SAMPLE_EVERY_SEC)

mask = None
frame_no = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break

    if frame_no % step == 0:
        cv2.imwrite("frame_tmp.jpg", frame)
        total, dm = LWCC.get_count("frame_tmp.jpg", model=model,
                                   return_density=True)
        dm = np.clip(np.squeeze(dm), 0, None)
        h, w = dm.shape

        if mask is None:
            scaled = np.array([[x * w / frame_w, y * h / frame_h]
                               for x, y in POINTS], dtype=np.int32)
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [scaled], 1)

        everyone = float(dm.sum())
        inside = float((dm * mask).sum())
        print(f"\nt = {frame_no / fps:.0f}s   everyone = {everyone:.0f}   "
              f"inside floor = {inside:.0f}   outside = {everyone - inside:.0f}")

        zone_h = h // ROWS
        zone_w = w // COLS
        for r in range(ROWS):
            row_text = []
            for c in range(COLS):
                y1 = r * zone_h
                x1 = c * zone_w
                y2 = h if r == ROWS - 1 else y1 + zone_h
                x2 = w if c == COLS - 1 else x1 + zone_w
                n = float((dm[y1:y2, x1:x2] * mask[y1:y2, x1:x2]).sum())
                row_text.append(f"Z{r * COLS + c + 1}:{n:5.1f}")
            print("  ".join(row_text))

    frame_no += 1

cap.release()
print("\nDone.")