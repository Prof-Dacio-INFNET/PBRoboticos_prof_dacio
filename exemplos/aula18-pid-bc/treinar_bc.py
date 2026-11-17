#!/usr/bin/env python3
"""Treina a CNN do Behavioral Cloning: quadro da camera -> direcao em [-1, 1].

    VENV="$PB_DIR/.venv-cnn/bin/python"            # o venv da aula17-cnn
    $VENV treinar_bc.py --pasta dataset --saida modelo
    $VENV treinar_bc.py --pasta dataset --saida modelo --comparar-divisao
    $VENV treinar_bc.py --pasta amostra/dataset --epocas 1 --saida /tmp/m   # o testar.py

Le PASTA/acoes.csv (o coletar.py escreve; colunas usadas: arquivo, episodio,
direcao) e os PNG ao lado. Uma regressao, nao uma classificacao: a saida e um
numero so, LINEAR, e a perda e o erro quadratico medio. Linear e nao tanh:
com tanh, a primeira epoca levou a saida para +1 em todos os quadros, a tanh
saturou, o gradiente zerou, e a perda ficou parada em 1,19 da segunda epoca em
diante (medido). O recorte em [-1, 1] fica para a inferencia (rede.py). A metrica que se le
e o ERRO MEDIO ABSOLUTO (MAE) em unidades de volante: 0,05 = 2 graus de roda.

A DIVISAO E POR EPISODIO. Quadros vizinhos (0,2 s de distancia) sao quase a
mesma imagem com quase o mesmo rotulo. Sorteando QUADROS para a validacao, cada
quadro de validacao tem um gemeo no treino, e a validacao mede memoria, nao
generalizacao. Sorteando EPISODIOS (estradas inteiras), a validacao e uma
estrada que a rede nunca viu. --comparar-divisao treina das duas formas e
mede as duas redes no mesmo episodio separado: o numero que a divisao por
quadro promete e o que ela entrega.

A LINHA DE BASE e "prever sempre a media do treino": o MAE de uma rede que nao
olha a imagem. Com um dataset quase todo de reta, ela ja e baixa -- e e por
isso que o MAE sozinho nao diz se a rede aprendeu a fazer curva. A tabela
separa o MAE nos quadros de reta (|direcao| < LIMIAR_CURVA) e de curva.

O QUE SAI em SAIDA/:
    pesos.npz          os pesos para o rede.py (NumPy) -- e o que o dirigir_bc.py le
    modelo.keras       o modelo do Keras, para quem quiser abrir
    referencia.npz     5 entradas da validacao e a saida do Keras para elas
                       (o testar.py confere o rede.py contra isto)
    historico.json, curvas.png, divisao.csv, tabela.txt
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

import numpy as np  # noqa: E402

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rede  # noqa: E402  (so NumPy)

# ------------------------------------------------------------------------------
# HIPERPARAMETROS -- declarados antes de qualquer resultado.
# ------------------------------------------------------------------------------
EPOCAS = 30
SEMENTE = 7
LOTE = 32
TAXA_APRENDIZADO = 3e-4      # Adam. 1e-3 (o padrao) colapsou para "sempre ~0" (medido)
# A rede aprende direcao x ESCALA_ROTULO, e a inferencia divide de volta. O
# volante de uma curva deste mapa e ~0,06, e o ruido da saida da rede recem-
# inicializada e de varias unidades: sem a escala, o caminho mais curto para
# baixar a perda e responder sempre ~0, e a rede para ali. Medido em 567
# quadros (3 episodios): MAE na curva 0,088 sem escala, 0,040 com escala 10 e
# 3e-4, contra 0,097 de "sempre a media". O rede.py le a escala do pesos.npz.
ESCALA_ROTULO = 10.0
FILTROS = (16, 32, 64)       # tres blocos Conv3x3 -> BatchNorm -> ReLU -> MaxPool
DENSA = 64
DROPOUT = 0.3
# A mesma armadilha da aula17-cnn: com o momentum padrao do Keras (0,99) e
# poucos passos por epoca, as medias moveis da BatchNormalization ainda
# lembram o valor inicial quando o treino acaba, e a validacao (que usa as
# medias moveis) despenca. 0,9 resolve.
BN_MOMENTO = 0.9
FRACAO_VALIDACAO = 0.2       # de episodios (ou de quadros, na divisao por quadro)
LIMIAR_CURVA = 0.02          # |direcao| abaixo disto conta como "reta" (o do histograma.py)


def ler_dataset(pastas):
    """Lista de (caminho_png, episodio_global, direcao). Episodio e (pasta, episodio)."""
    linhas = []
    for pasta in pastas:
        pasta = pathlib.Path(pasta)
        caminho = pasta / 'acoes.csv'
        if not caminho.exists():
            sys.exit('nao achei %s: grave com o coletar.py' % caminho)
        with open(caminho, newline='') as f:
            leitor = csv.DictReader(f)
            faltam = {'arquivo', 'episodio', 'direcao'} - set(leitor.fieldnames or ())
            if faltam:
                sys.exit('%s: faltam as colunas %s' % (caminho, sorted(faltam)))
            for r in leitor:
                linhas.append((str(pasta / r['arquivo']), '%s:%s' % (pasta.name, r['episodio']),
                               float(r['direcao'])))
    if len(linhas) < 10:
        sys.exit('%d quadros: poucos para treinar' % len(linhas))
    return linhas


def carregar(linhas):
    import cv2
    xs = []
    for caminho, _, _ in linhas:
        img = cv2.imread(caminho, cv2.IMREAD_COLOR)     # BGR, como o MetaDrive entrega
        if img is None:
            sys.exit('nao consegui ler %s' % caminho)
        xs.append(rede.preparar(img))
    return np.stack(xs), np.array([d for _, _, d in linhas], np.float32)


def dividir_por_episodio(episodios, fracao, semente):
    """Sorteia EPISODIOS inteiros para a validacao (pelo menos 1, e pelo menos 1 no treino)."""
    unicos = sorted(set(episodios))
    if len(unicos) < 2:
        sys.exit('um episodio so: nao da para dividir por episodio. Grave mais de um.')
    rng = np.random.default_rng(semente)
    n_val = min(len(unicos) - 1, max(1, int(round(len(unicos) * fracao))))
    val = set(rng.choice(unicos, size=n_val, replace=False).tolist())
    ep = np.array(episodios)
    va = np.flatnonzero(np.isin(ep, list(val)))
    tr = np.flatnonzero(~np.isin(ep, list(val)))
    return tr, va, sorted(val)


def dividir_por_quadro(indices, fracao, semente):
    rng = np.random.default_rng(semente)
    idx = rng.permutation(indices)
    n_val = max(1, int(round(len(idx) * fracao)))
    return np.sort(idx[n_val:]), np.sort(idx[:n_val])


def construir(semente, bn_momento):
    import keras
    from keras import layers
    keras.utils.set_random_seed(semente)
    entrada = keras.Input(shape=rede.ENTRADA, name='imagem')
    x = layers.Rescaling(1.0 / 255.0, name='escala')(entrada)
    for i, f in enumerate(FILTROS):
        x = layers.Conv2D(f, 3, padding='same', use_bias=False, name='conv%d' % i)(x)
        x = layers.BatchNormalization(momentum=bn_momento, epsilon=rede.EPS_BN,
                                      name='bn%d' % i)(x)
        x = layers.Activation('relu', name='relu%d' % i)(x)
        x = layers.MaxPooling2D(name='pool%d' % i)(x)
    x = layers.Flatten(name='achatar')(x)
    x = layers.Dense(DENSA, activation='relu', name='densa')(x)
    x = layers.Dropout(DROPOUT, seed=semente, name='dropout')(x)
    saida = layers.Dense(1, name='saida')(x)
    modelo = keras.Model(entrada, saida, name='bc')
    modelo.compile(optimizer=keras.optimizers.Adam(TAXA_APRENDIZADO), loss='mse',
                   metrics=['mae'])
    return modelo


def exportar(modelo, caminho):
    """Os pesos do Keras num .npz com os nomes que o rede.Rede espera."""
    d = {'n_conv': np.array(len(FILTROS)), 'escala_rotulo': np.array(ESCALA_ROTULO)}
    for i in range(len(FILTROS)):
        d['conv%d' % i] = modelo.get_layer('conv%d' % i).get_weights()[0]
        gama, beta, media, var = modelo.get_layer('bn%d' % i).get_weights()
        d.update({'bn%d_gama' % i: gama, 'bn%d_beta' % i: beta,
                  'bn%d_media' % i: media, 'bn%d_var' % i: var})
    d['densa_w'], d['densa_b'] = modelo.get_layer('densa').get_weights()
    d['saida_w'], d['saida_b'] = modelo.get_layer('saida').get_weights()
    np.savez_compressed(caminho, **d)


def espelhar(x, y):
    """Junta ao treino cada quadro espelhado na horizontal, com a direcao trocada de sinal.

    Uma curva a direita espelhada e uma curva a esquerda: e o remedio barato
    para um dataset que so tem curva para um lado. O preco: a faixa amarela,
    que fica sempre a esquerda do carro, aparece a direita nos espelhados.
    Vale so no TREINO -- a validacao continua sendo a estrada como ela e.
    """
    return (np.concatenate([x, x[:, :, ::-1]]), np.concatenate([y, -y]))


def treinar(xtr, ytr, xva, yva, args, nome):
    import tensorflow as tf
    if args.espelhar:
        xtr, ytr = espelhar(xtr, ytr)
    modelo = construir(args.semente, args.bn_momento)
    ytr, yva = ytr * ESCALA_ROTULO, yva * ESCALA_ROTULO     # a rede ve o rotulo escalado
    ds_tr = (tf.data.Dataset.from_tensor_slices((xtr, ytr))
             .shuffle(len(xtr), seed=args.semente, reshuffle_each_iteration=True)
             .batch(args.lote))
    ds_va = tf.data.Dataset.from_tensor_slices((xva, yva)).batch(args.lote)
    print('\n=== %s: %d treino / %d validacao ===' % (nome, len(xtr), len(xva)), flush=True)
    t0 = time.perf_counter()
    h = modelo.fit(ds_tr, validation_data=ds_va, epochs=args.epocas, verbose=2)
    # de volta a unidades de volante, para as curvas e a tabela
    hist = {k: [float(v) / (ESCALA_ROTULO if 'mae' in k else ESCALA_ROTULO ** 2) for v in vs]
            for k, vs in h.history.items()}
    hist['segundos'] = time.perf_counter() - t0
    return modelo, hist


def mae(prev, y, mascara=None):
    if mascara is not None:
        if not mascara.any():
            return float('nan')
        prev, y = prev[mascara], y[mascara]
    return float(np.mean(np.abs(prev - y)))


def prever(modelo, x):
    """Desfaz a escala e recorta em [-1, 1], como o rede.py: e o que vai ao volante."""
    y = modelo.predict(x, verbose=0, batch_size=256).reshape(-1) / ESCALA_ROTULO
    return np.clip(y, -1.0, 1.0)


def salvar_curvas(historicos, caminho, base=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=110)
    cores = ('#14213D', '#FCA311', '#2a9d8f', '#e76f51')
    for (nome, h), cor in zip(historicos, cores):
        ep = range(1, len(h['mae']) + 1)
        ax.plot(ep, h['mae'], color=cor, ls='--', lw=1.2, label='%s treino' % nome)
        ax.plot(ep, h['val_mae'], color=cor, lw=2.0, label='%s validacao' % nome)
    if base is not None:
        ax.axhline(base, color='#888888', ls=':', lw=1.5,
                   label='"sempre a media" no episodio separado')
    ax.set_xlabel('epoca')
    ax.set_ylabel('MAE da direcao (unidades de volante)')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def principal():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pasta', required=True, nargs='+', help='pasta(s) com acoes.csv e PNG')
    ap.add_argument('--saida', default='modelo', help='(modelo)')
    ap.add_argument('--epocas', type=int, default=EPOCAS, help='(%d)' % EPOCAS)
    ap.add_argument('--semente', type=int, default=SEMENTE, help='(%d)' % SEMENTE)
    ap.add_argument('--lote', type=int, default=LOTE, help='(%d)' % LOTE)
    ap.add_argument('--bn-momento', type=float, default=BN_MOMENTO,
                    help='(%g; o padrao do Keras e 0.99 -- leia o topo)' % BN_MOMENTO)
    ap.add_argument('--espelhar', action='store_true',
                    help='junta ao treino os quadros espelhados com a direcao trocada de sinal')
    ap.add_argument('--comparar-divisao', action='store_true',
                   help='treina tambem com divisao por QUADRO e mede as duas no mesmo '
                   'episodio separado')
    args = ap.parse_args()

    linhas = ler_dataset(args.pasta)
    episodios = [e for _, e, _ in linhas]
    xs, ys = carregar(linhas)
    tr, va, ep_val = dividir_por_episodio(episodios, FRACAO_VALIDACAO, args.semente)
    saida = pathlib.Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    import tensorflow as tf
    tf.config.experimental.enable_op_determinism()
    print('tensorflow %s; %d quadros, %d episodios; validacao = episodios %s'
          % (tf.__version__, len(ys), len(set(episodios)), ', '.join(ep_val)))
    # na GPU o TensorFlow entra sozinho se a enxergar; CUDA_VISIBLE_DEVICES="" a esconde
    print('dispositivos: ' + ', '.join(d.device_type for d in tf.config.list_physical_devices()))
    import keras
    if keras.backend.backend() != 'tensorflow':
        # com KERAS_BACKEND=torch quem treina e o torch, e a lista acima nao vale
        print('keras %s com backend %s' % (keras.__version__, keras.backend.backend()))

    modelo, hist = treinar(xs[tr], ys[tr], xs[va], ys[va], args, 'divisao por episodio')
    historicos = [('por episodio', hist)]
    prev_va = prever(modelo, xs[va])
    media_tr = float(np.mean(ys[tr]))
    reta = np.abs(ys[va]) < LIMIAR_CURVA
    res = [('por episodio', mae(prever(modelo, xs[tr]), ys[tr]), hist['val_mae'][-1],
            mae(prev_va, ys[va]), mae(prev_va, ys[va], reta), mae(prev_va, ys[va], ~reta),
            hist['segundos'])]

    modelo.save(saida / 'modelo.keras')
    exportar(modelo, saida / 'pesos.npz')
    k = min(5, len(va))
    np.savez_compressed(saida / 'referencia.npz', entrada=xs[va[:k]], saida=prev_va[:k])
    with open(saida / 'divisao.csv', 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(('arquivo', 'episodio', 'direcao', 'conjunto', 'prevista'))
        prev_todos = prever(modelo, xs)
        conj = np.where(np.isin(np.arange(len(ys)), va), 'validacao', 'treino')
        for i, (arq, ep, d) in enumerate(linhas):
            w.writerow((arq, ep, '%.4f' % d, conj[i], '%.4f' % prev_todos[i]))

    if args.comparar_divisao:
        # a divisao por QUADRO dentro dos episodios de treino; o episodio separado
        # fica de fora das duas, para medir as duas redes no mesmo lugar
        tr_q, va_q = dividir_por_quadro(tr, FRACAO_VALIDACAO, args.semente)
        m_q, h_q = treinar(xs[tr_q], ys[tr_q], xs[va_q], ys[va_q], args, 'divisao por quadro')
        historicos.append(('por quadro', h_q))
        p_q = prever(m_q, xs[va])
        res.append(('por quadro', mae(prever(m_q, xs[tr_q]), ys[tr_q]), h_q['val_mae'][-1],
                    mae(p_q, ys[va]), mae(p_q, ys[va], reta), mae(p_q, ys[va], ~reta),
                    h_q['segundos']))
    (saida / 'historico.json').write_text(json.dumps(dict(historicos), indent=1))
    salvar_curvas(historicos, saida / 'curvas.png',
                  mae(np.full_like(ys[va], media_tr), ys[va]))

    cont_reta = int(np.sum(np.abs(ys) < LIMIAR_CURVA))
    t = ['dados   : %s -- %d quadros, %d episodios; |direcao| < %.2f em %d (%.0f%%)'
         % (' + '.join(pathlib.Path(p).name for p in args.pasta), len(ys), len(set(episodios)),
            LIMIAR_CURVA, cont_reta, 100.0 * cont_reta / len(ys)),
         'validacao: episodio(s) %s -- %d quadros (%d de reta, %d de curva)'
         % (', '.join(ep_val), len(va), int(reta.sum()), int((~reta).sum())),
         'treino  : %d epocas, lote %d, entrada %dx%d, BN momentum %g, semente %d%s'
         % (args.epocas, args.lote, rede.ENTRADA[1], rede.ENTRADA[0], args.bn_momento,
            args.semente, ', ESPELHADO (treino x2)' if args.espelhar else ''),
         '',
         'linha de base "sempre a media do treino" (%.3f): MAE %.3f no episodio separado'
         % (media_tr, mae(np.full_like(ys[va], media_tr), ys[va])),
         'linha de base "sempre zero":                  MAE %.3f'
         % mae(np.zeros_like(ys[va]), ys[va]),
         '',
         'divisao        MAE_treino  MAE_val(propria)  MAE_ep_separado   reta    curva   tempo']
    for nome, m_tr, m_val, m_sep, m_r, m_c, seg in res:
        t.append('%-13s  %10.3f  %16.3f  %15.3f  %6.3f  %6.3f  %5.0f s'
                 % (nome, m_tr, m_val, m_sep, m_r, m_c, seg))
    t.append('MAE em unidades de volante (1,0 = 40 graus de roda). MAE_val(propria) e a')
    t.append('validacao que cada divisao reporta; MAE_ep_separado e a do episodio que')
    t.append('nenhuma das duas viu. reta/curva: o MAE do episodio separado em cada parte.')
    base = np.full_like(ys[va], media_tr)
    t.append('%-13s  %10s  %16s  %15.3f  %6.3f  %6.3f'
             % ('sempre media', '-', '-', mae(base, ys[va]), mae(base, ys[va], reta),
                mae(base, ys[va], ~reta)))
    # as armadilhas, medidas sem simulador: o MESMO modelo, a entrada preparada errado
    p_rgb = prever(modelo, np.ascontiguousarray(xs[va][..., ::-1]))
    p_255 = prever(modelo, xs[va].astype(np.float32) * 255.0)   # = esquecer o /255
    t.append('')
    t.append('o modelo "por episodio", no episodio separado, com a entrada ERRADA:')
    for nome, pv in (('RGB, nao BGR', p_rgb), ('sem o /255', p_255)):
        t.append('%-13s  %10s  %16s  %15.3f  %6.3f  %6.3f   (saida media %+.3f)'
                 % (nome, '-', '-', mae(pv, ys[va]), mae(pv, ys[va], reta),
                    mae(pv, ys[va], ~reta), float(np.mean(pv))))
    tabela = '\n'.join(t)
    (saida / 'tabela.txt').write_text(tabela + '\n')
    print('\n' + tabela)
    print('\npesos para o dirigir_bc.py: %s' % (saida / 'pesos.npz'))


if __name__ == '__main__':
    principal()
