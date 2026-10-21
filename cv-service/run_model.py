import cv2
import numpy as np
import torch
from csrnet import CSRNet

img = cv2.imread("Crowd.jpg")
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img = cv2.resize(img, (1024, 768))

x = img.astype(np.float32) / 255.0
mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
x = (x - mean) / std

x = torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0)

model = CSRNet().eval()

with torch.no_grad():
    density = model(x)

print("Input shape:", tuple(x.shape))
print("Density map shape:", tuple(density.shape))
print("Sum of density map:", density.sum().item())
