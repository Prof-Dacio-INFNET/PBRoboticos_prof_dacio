# OpenCV 4 — referência (DR2 / TP1–TP2)

Instalação: **pelo apt, no sistema** — `sudo apt install python3-opencv` (e `ros-humble-cv-bridge` se for usar com ROS 2), o que fixa a versão **4.5.4**, que é contra a qual o `cv_bridge` foi compilado. Não instale `opencv-python` nem `numpy` por pip fora de um venv: o pip traz OpenCV 5 e NumPy 2, e ambos quebram o `cv_bridge` com `KeyError: 16` — o OpenCV 5 renumerou as constantes de tipo, e sob NumPy 2 a extensão em C++ nem carrega. Dentro de um venv (`uv venv --system-site-packages`), o uv é bem-vindo para o que **não** for OpenCV/NumPy.
```python
import cv2, numpy as np
img = cv2.imread('f.png'); cap = cv2.VideoCapture(0)   # arquivo / webcam
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)            # segmentação por cor
mask = cv2.inRange(hsv, (35,80,80), (85,255,255))     # faixa de cor (ex.: verde)
edges = cv2.Canny(gray, 100, 200)                     # bordas
lines = cv2.HoughLinesP(edges,1,np.pi/180,50,minLineLength=40,maxLineGap=10)  # faixas
circles = cv2.HoughCircles(gray,cv2.HOUGH_GRADIENT,1,20,param1=100,param2=30) # sinais
corners = cv2.goodFeaturesToTrack(gray,100,0.01,10)   # Harris/Shi-Tomasi
faces = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
cv2.imshow('w', img); cv2.waitKey(1)
```
Integração ROS: use `cv_bridge` p/ converter `sensor_msgs/Image` ↔ `cv2` (`imgmsg_to_cv2`).
