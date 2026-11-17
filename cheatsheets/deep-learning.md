# Deep Learning — Keras/CNN, YOLO (TP2–TP5)

Venv (uv): `uv pip install tensorflow ultralytics`

**CPU ou GPU.** As CNNs do curso treinam em ~1 min na CPU (`tensorflow-cpu`, venv da [`aula17-cnn`](../exemplos/aula17-cnn/index.md)); a GPU vale a pena em treino de visão maior (YOLO). TensorFlow com GPU vai num venv separado e pode **não** funcionar na série RTX 50; torch com GPU na série 50 pede `--torch-backend cu130`. Receitas, teste decisivo e plano B: [CPU ou GPU: os dois caminhos](../tutoriais/gpu-cpu.md).
```python
# CNN simples (Keras) com augmentation
from tensorflow import keras; from tensorflow.keras import layers
aug = keras.Sequential([layers.RandomRotation(0.08), layers.RandomZoom(0.2), layers.RandomFlip("horizontal")])
model = keras.Sequential([aug, layers.Rescaling(1./255),
  layers.Conv2D(32,3,activation='relu'), layers.BatchNormalization(), layers.MaxPooling2D(),
  layers.Conv2D(64,3,activation='relu'), layers.MaxPooling2D(), layers.Flatten(),
  layers.Dense(128,activation='relu'), layers.Dropout(0.5), layers.Dense(N,activation='softmax')])
model.compile('adam','sparse_categorical_crossentropy',metrics=['accuracy'])
h = model.fit(ds_train, validation_data=ds_val, epochs=30)   # plote h.history['accuracy']/['loss']
```
```python
# YOLO (ultralytics) — detecção/segmentação
from ultralytics import YOLO
m = YOLO('yolov8n.pt')                 # ou yolov8n-seg.pt p/ segmentação
r = m('frame.jpg')                     # ou m.track(...) p/ rastreamento
for b in r[0].boxes: print(b.cls, b.conf, b.xyxy)
```
Dica: compare curvas com e sem augmentation (generalização) — pedido no TP4.
