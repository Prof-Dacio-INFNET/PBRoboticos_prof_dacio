#!/usr/bin/env python3
"""A rede do BC em NumPy puro: o preparo da imagem e a inferencia.

E o arquivo que atravessa a fronteira entre os dois venvs. O treinar_bc.py
(venv do TensorFlow) importa `preparar` daqui e exporta os pesos para um .npz;
o dirigir_bc.py (venv do MetaDrive) importa `preparar` e `Rede` daqui e roda a
mesma conta sem TensorFlow nenhum. Por isso este arquivo so importa NumPy.

POR QUE NAO CARREGAR O .keras NO VENV DO METADRIVE: os dois venvs nao
convivem. O TensorFlow 2.21 traz NumPy 2 e o venv da CNN e isolado; o
MetaDrive tem o dele. Instalar TensorFlow no venv do MetaDrive e trazer mais
1,5 GB e uma segunda resolucao de NumPy para dentro de um ambiente que hoje
funciona -- e a regra da disciplina e nao mexer no que funciona. A rede tem
tres convolucoes e duas densas: em NumPy sao umas 40 linhas, e o testar.py
confere que a saida bate com a do Keras.

O PREPARO, igual no treino e na direcao (se divergir, a rede ve outra coisa):
    1. corta as CORTE_TOPO linhas de cima (ceu e horizonte, nada de estrada)
    2. pega 1 pixel a cada 2 nas duas direcoes: 160x120 -> 80x35
    3. mantem BGR, a ordem que o MetaDrive entrega e o cv2.imread le
    4. divide por 255 (dentro da rede, na camada `escala` do Keras; aqui, em
       `Rede.__call__`)
e na saida, o inverso do treino: divide por `escala_rotulo` (10) e recorta
em [-1, 1].
"""
import numpy as np

CORTE_TOPO = 50          # linhas de 160x120 descartadas no topo (o horizonte fica em ~55)
PASSO_PIXEL = 2          # 160x120 -> 80x35 depois do corte
ENTRADA = (35, 80, 3)    # altura, largura, canais -- o que a rede recebe
EPS_BN = 1e-3            # o epsilon padrao da BatchNormalization do Keras


def preparar(img_bgr):
    """(120, 160, 3) uint8 BGR -> (35, 80, 3) uint8 BGR. Sem cv2: igual em todo lugar."""
    if img_bgr.shape[:2] != (120, 160):
        raise ValueError('esperava um quadro 160x120, veio %s' % (img_bgr.shape,))
    return np.ascontiguousarray(img_bgr[CORTE_TOPO::PASSO_PIXEL, ::PASSO_PIXEL])


def _conv_same(x, k):
    """Convolucao 3x3, passo 1, padding 'same', sem bias. x (A, L, C), k (3, 3, C, F)."""
    kh, kw = k.shape[:2]
    xp = np.pad(x, ((kh // 2, kh // 2), (kw // 2, kw // 2), (0, 0)))
    janelas = np.lib.stride_tricks.sliding_window_view(xp, (kh, kw), axis=(0, 1))
    # janelas: (A, L, C, kh, kw) -> soma em C, kh, kw contra k (kh, kw, C, F)
    return np.einsum('ijcuv,uvcf->ijf', janelas, k, optimize=True)


def _maxpool2(x):
    """MaxPooling2D(2) do Keras: janelas 2x2 sem sobreposicao; a sobra e descartada."""
    a, l = x.shape[0] // 2 * 2, x.shape[1] // 2 * 2
    x = x[:a, :l]
    return x.reshape(a // 2, 2, l // 2, 2, -1).max(axis=(1, 3))


class Rede:
    """Le o pesos.npz que o treinar_bc.py exporta e faz a inferencia de UM quadro."""

    def __init__(self, caminho):
        p = np.load(caminho)
        self.n_conv = int(p['n_conv'])
        # a rede foi treinada para prever direcao x escala (treinar_bc.ESCALA_ROTULO)
        self.escala = float(p['escala_rotulo']) if 'escala_rotulo' in p.files else 1.0
        self.p = {k: p[k].astype(np.float32) for k in p.files}

    def __call__(self, entrada, normalizar=True):
        """entrada (35, 80, 3) uint8 -> direcao em [-1, 1] (float)."""
        x = entrada.astype(np.float32)
        if normalizar:
            x = x / 255.0
        p = self.p
        for i in range(self.n_conv):
            x = _conv_same(x, p['conv%d' % i])
            x = (x - p['bn%d_media' % i]) / np.sqrt(p['bn%d_var' % i] + EPS_BN)
            x = x * p['bn%d_gama' % i] + p['bn%d_beta' % i]
            x = np.maximum(x, 0.0)
            x = _maxpool2(x)
        x = x.reshape(-1)                           # mesma ordem do Flatten do Keras (A, L, C)
        x = np.maximum(x @ p['densa_w'] + p['densa_b'], 0.0)
        # Dropout: na inferencia e identidade. A saida e linear (sem tanh); o
        # volante do MetaDrive vai de -1 a 1, entao o recorte e aqui.
        y = (x @ p['saida_w'] + p['saida_b']) / self.escala
        return float(np.clip(y[0], -1.0, 1.0))
