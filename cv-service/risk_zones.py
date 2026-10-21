import cv2
import numpy as np
from lwcc import LWCC

IMAGE = "Crowd.jpg"
ROWS = 4
COLS = 4
AREA_PER_ZONE_M2 = 4.0  # ASSUMPTION for the demo, not a measured value


def risk_level(people_per_m2):
    if people_per_m2 < 2:
        return "GREEN", (0, 200, 0)
    elif people_per_m2 <= 4:
        return "AMBER", (0, 165, 255)
    else:
        return "RED", (0, 0, 255)


model = LWCC.load_model(model_name="CSRNet", model_weights="SHA")
total, density_map = LWCC.get_count(IMAGE, model=model, return_density=True)
density_map = np.clip(np.squeeze(density_map), 0, None)

h, w = density_map.shape
zone_h = h // ROWS
zone_w = w // COLS

image = cv2.imread(IMAGE)
img_h, img_w = image.shape[:2]
img_zone_h = img_h // ROWS
img_zone_w = img_w // COLS
overlay = image.copy()

results = []
for r in range(ROWS):
    for c in range(COLS):
        y1 = r * zone_h
        x1 = c * zone_w
        y2 = h if r == ROWS - 1 else y1 + zone_h
        x2 = w if c == COLS - 1 else x1 + zone_w
        count = float(density_map[y1:y2, x1:x2].sum())

        people_per_m2 = count / AREA_PER_ZONE_M2
        level, color = risk_level(people_per_m2)

        ix1 = c * img_zone_w
        iy1 = r * img_zone_h
        ix2 = img_w if c == COLS - 1 else ix1 + img_zone_w
        iy2 = img_h if r == ROWS - 1 else iy1 + img_zone_h
        cv2.rectangle(overlay, (ix1, iy1), (ix2, iy2), color, -1)

        zone_number = r * COLS + c + 1
        results.append((zone_number, ix1, iy1, count, people_per_m2, level))

cv2.addWeighted(overlay, 0.35, image, 0.65, 0, image)

print("Zone  People  p/m2   Level")
for zone_number, ix1, iy1, count, ppm2, level in results:
    print(f"Z{zone_number:<4} {count:6.1f}  {ppm2:4.2f}   {level}")
    cv2.putText(image, f"Z{zone_number} {level}", (ix1 + 20, iy1 + 80),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)
    cv2.putText(image, f"{ppm2:.1f} p/m2", (ix1 + 20, iy1 + 170),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)

cv2.imwrite("risk_output.jpg", image)
print("Saved risk_output.jpg")