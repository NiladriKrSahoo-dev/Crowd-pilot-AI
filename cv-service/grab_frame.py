import cv2

cap = cv2.VideoCapture("crowd_video.mp4")
cap.set(cv2.CAP_PROP_POS_FRAMES, 150)
ok, frame = cap.read()
h, w = frame.shape[:2]
ROWS, COLS = 3, 4

for r in range(1, ROWS):
    cv2.line(frame, (0, r * h // ROWS), (w, r * h // ROWS), (0, 255, 0), 3)
for c in range(1, COLS):
    cv2.line(frame, (c * w // COLS, 0), (c * w // COLS, h), (0, 255, 0), 3)
for r in range(ROWS):
    for c in range(COLS):
        cv2.putText(frame, f"Z{r * COLS + c + 1}",
                    (c * w // COLS + 20, r * h // ROWS + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 4)

cv2.imwrite("frame_t5_grid.jpg", frame)
print("Saved frame_t5_grid.jpg")