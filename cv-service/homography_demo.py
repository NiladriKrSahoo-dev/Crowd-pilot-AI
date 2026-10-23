import cv2
import numpy as np

# A floor we "measured": a rectangle 6 m wide and 4 m deep.
REAL_W = 6.0
REAL_H = 4.0
real_pts = np.array([[0, 0], [REAL_W, 0], [REAL_W, REAL_H], [0, REAL_H]],
                    dtype=np.float32)

# Where those four floor corners appear in the camera picture (pixels):
# near-left, near-right, far-right, far-left.
image_pts = np.array([[100, 580], [900, 580], [700, 200], [300, 200]],
                     dtype=np.float32)

H = cv2.getPerspectiveTransform(image_pts, real_pts)

IMG_W = 1000
IMG_H = 600
ROWS = 3
COLS = 4
cell_w = IMG_W / COLS
cell_h = IMG_H / ROWS

print("Real floor area:", REAL_W * REAL_H, "m2")
print("\nFloor area behind each picture zone (m2):")

total = 0.0
for r in range(ROWS):
    row_text = []
    for c in range(COLS):
        x1 = c * cell_w
        y1 = r * cell_h
        x2 = x1 + cell_w
        y2 = y1 + cell_h
        cell = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        dtype=np.float32)

        area_px, inter = cv2.intersectConvexConvex(cell, image_pts)
        if area_px > 0:
            inter = inter.reshape(-1, 1, 2).astype(np.float32)
            floor_pts = cv2.perspectiveTransform(inter, H)
            area_m2 = float(cv2.contourArea(floor_pts))
        else:
            area_m2 = 0.0

        total += area_m2
        row_text.append(f"Z{r * COLS + c + 1}: {area_m2:5.2f}")
    print("  ".join(row_text))

print("\nSum of zones:", round(total, 2), "m2")