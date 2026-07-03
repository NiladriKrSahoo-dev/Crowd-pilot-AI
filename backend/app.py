import cv2
import urllib.request
from ultralytics import YOLO

print("1. Loading AI Model...")
model = YOLO("yolov8n.pt")

print("2. Downloading test crowd image...")
url = "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/bus.jpg"
urllib.request.urlretrieve(url, "test_crowd.jpg")

print("3. AI is analyzing the image...")
results = model("test_crowd.jpg")

print("4. Drawing bounding boxes...")
annotated_frame = results[0].plot()

print("5. Saving output file...")
cv2.imwrite("ai_output.jpg", annotated_frame)

print("SUCCESS! Look at your file explorer on the left and click 'ai_output.jpg'")
