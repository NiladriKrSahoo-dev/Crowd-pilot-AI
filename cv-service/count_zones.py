import numpy as np
from lwcc import LWCC

IMAGE = "Crowd.jpg"
ROWS = 4
COLS = 4

model = LWCC.load_model(model_name="CSRNet", model_weights="SHA")
total, density = LWCC.get_count(IMAGE, model=model, return_density=True)
density = np.squeeze(density)

print("Total people (estimate):", round(float(total)))
print("Density map shape:", density.shape)

h, w = density.shape
zone_h = h // ROWS
zone_w = w // COLS

counts = np.zeros((ROWS, COLS))
for r in range(ROWS):
    for c in range(COLS):
        y1 = r * zone_h
        x1 = c * zone_w
        y2 = h if r == ROWS - 1 else y1 + zone_h
        x2 = w if c == COLS - 1 else x1 + zone_w
        counts[r, c] = density[y1:y2, x1:x2].sum()

print("\nPeople per zone:")
for r in range(ROWS):
    print("  ".join(f"Z{r * COLS + c + 1}: {counts[r, c]:5.1f}" for c in range(COLS)))

busiest = int(counts.argmax()) + 1
print("\nBusiest zone: Z" + str(busiest))
print("Sum of zones:", round(float(counts.sum()), 1))