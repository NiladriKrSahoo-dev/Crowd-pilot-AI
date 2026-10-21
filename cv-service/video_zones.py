import cv2
import numpy as np
from collections import deque
from lwcc import LWCC

VIDEO = "crowd_video.mp4"
ROWS = 3
COLS = 4
AREA_PER_ZONE_M2 = 4.0   # ASSUMPTION for the demo, not a measured value
SAMPLE_EVERY_SEC = 1
SMOOTH_N = 3
ALERT_AFTER = 3


def risk_level(people_per_m2):
    if people_per_m2 < 2:
        return "GREEN"
    elif people_per_m2 <= 4:
        return "AMBER"
    else:
        return "RED"


model = LWCC.load_model(model_name="CSRNet", model_weights="SHA")

cap = cv2.VideoCapture(VIDEO)
if not cap.isOpened():
    print("Could not open", VIDEO)
    raise SystemExit

fps = cap.get(cv2.CAP_PROP_FPS)
step = int(fps * SAMPLE_EVERY_SEC)

history = [[deque(maxlen=SMOOTH_N) for _ in range(COLS)] for _ in range(ROWS)]
red_streak = np.zeros((ROWS, COLS), dtype=int)

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
        zone_h = h // ROWS
        zone_w = w // COLS

        print(f"\n--- t = {frame_no / fps:.0f}s   total = {float(total):.0f} people ---")
        for r in range(ROWS):
            row_text = []
            for c in range(COLS):
                y1 = r * zone_h
                x1 = c * zone_w
                y2 = h if r == ROWS - 1 else y1 + zone_h
                x2 = w if c == COLS - 1 else x1 + zone_w
                count = float(dm[y1:y2, x1:x2].sum())

                history[r][c].append(count)
                smooth = sum(history[r][c]) / len(history[r][c])
                ppm2 = smooth / AREA_PER_ZONE_M2
                level = risk_level(ppm2)

                if level == "RED":
                    red_streak[r, c] += 1
                else:
                    red_streak[r, c] = 0

                zone_number = r * COLS + c + 1
                row_text.append(f"Z{zone_number}:{ppm2:4.1f}{level[0]}")

                if red_streak[r, c] == ALERT_AFTER:
                    print(f"   >>> ALERT: Z{zone_number} RED for {ALERT_AFTER} readings in a row")
            print("  ".join(row_text))

    frame_no += 1

cap.release()
print("\nDone.")