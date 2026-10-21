import cv2

image = cv2.imread("Crowd.jpg")

if image is None:
    print("Could not load Crowd.jpg - check the file name and folder")
    raise SystemExit

height, width = image.shape[:2]
print("Image size:", width, "x"
, height)

ROWS = 4
COLS = 4
zone_h = height // ROWS
zone_w = width // COLS

for r in range(ROWS):
    for c in range(COLS):
        x1 = c * zone_w
        y1 = r * zone_h
        x2 = x1 + zone_w
        y2 = y1 + zone_h

        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)

        zone_number = r * COLS + c + 1
        cv2.putText(image, "Z" + str(zone_number), (x1 + 20, y1 + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 4)

cv2.imwrite("zones_output.jpg", image)
print("Saved zones_output.jpg")
