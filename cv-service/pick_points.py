import cv2

WIN = "click floor corners, press q when done"
SCALE = 0.5

cap = cv2.VideoCapture("crowd_video.mp4")
cap.set(cv2.CAP_PROP_POS_FRAMES, 150)
ok, frame = cap.read()
cap.release()

small = cv2.resize(frame, None, fx=SCALE, fy=SCALE)
points = []


def on_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        real = (int(x / SCALE), int(y / SCALE))
        points.append(real)
        cv2.circle(small, (x, y), 6, (0, 0, 255), -1)
        if len(points) > 1:
            px = int(points[-2][0] * SCALE)
            py = int(points[-2][1] * SCALE)
            cv2.line(small, (px, py), (x, y), (0, 255, 0), 2)
        print("point", len(points), real)


cv2.namedWindow(WIN)
cv2.setMouseCallback(WIN, on_click)

while True:
    cv2.imshow(WIN, small)
    if cv2.waitKey(20) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
print("POINTS =", points)