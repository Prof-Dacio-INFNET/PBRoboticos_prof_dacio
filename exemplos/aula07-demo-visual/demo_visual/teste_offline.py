#!/usr/bin/env python3
"""Plano B absoluto do Demo 1: roda SEM ROS 2.

    python3 teste_offline.py              # usa a webcam
    python3 teste_offline.py foto.jpg     # usa uma foto, sem camera nenhuma

Se isto roda e o no ROS nao, o problema esta no ROS. Se nem isto roda, o
problema esta na camera ou no OpenCV -- e voce acabou de dividir o espaco de
busca pela metade sem depurar nada.
"""
import sys
import cv2

from demo_visual.piloto import processar

if len(sys.argv) > 1:
    img = cv2.imread(sys.argv[1])
    if img is None:
        sys.exit('nao consegui ler a imagem: %s' % sys.argv[1])
    img, acao, motivo, ex, ey, ea, area, _ = processar(img)
    print('acao=%s | %s | erro_x=%+.2f erro_y=%+.2f erro_area=%+.2f area=%d'
          % (acao, motivo, ex, ey, ea, area))
    cv2.imwrite('saida.png', img)
    print('imagem anotada em saida.png')
    sys.exit(0)

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    sys.exit('camera nao abriu — no WSL2, refaca o usbipd attach')
print('Ctrl+C para sair')
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        frame, acao, _, ex, ey, ea, area, _ = processar(frame)
        cv2.imshow('teste offline - Demo 1', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    cv2.destroyAllWindows()
