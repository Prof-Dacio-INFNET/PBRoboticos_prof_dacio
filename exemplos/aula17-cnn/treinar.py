#!/usr/bin/env python3
"""Treina a MESMA CNN duas vezes -- sem e com augmentation -- e compara.

    VENV=../.venv-cnn/bin/python                    # o venv do README
    $VENV treinar.py --pasta sintetico --saida resultado
    $VENV treinar.py --pasta quadros-s7 quadros-s8 --saida resultado-metadrive
    $VENV treinar.py --pasta /tmp/mini --epocas 1 --saida /tmp/r   # o testar.py faz isto

Le PASTA/rotulos.csv (colunas `arquivo,classe`; outras colunas sao ignoradas),
divide treino/validacao UMA vez, com semente fixa, e treina duas rodadas que
so diferem numa coisa: a rodada `com` passa as imagens de treino por
RandomRotation(+-15 graus), RandomZoom(0,2) e RandomFlip('horizontal') antes da
rede. Mesma divisao, mesma ordem de lotes, mesmos pesos iniciais, mesmas
epocas. Sem isso, a diferenca entre as curvas mediria a sorte, nao o
augmentation -- e e a terceira armadilha do README.

O QUE SAI em SAIDA/:
    historico_sem.json, historico_com.json   perda e acuracia por epoca (curvas.py)
    modelo_sem.keras, modelo_com.keras       os dois modelos treinados
    matriz_sem.png/.csv, matriz_com.png/.csv a matriz de confusao na validacao
    divisao.csv                              quem foi para treino e quem foi para validacao
    tabela.txt                               a tabela final, igual a impressa
    exemplos_augmentation.png                uma imagem por classe e 4 versoes aumentadas

A MATRIZ DE CONFUSAO e a peca que o gate G4.6 pede, e o motivo esta na
tabela: a linha "sempre a classe mais comum" diz a acuracia de uma rede que
nao olha a imagem. Com 54:0:6, essa rede acerta 90%. Acuracia sozinha nao
distingue as duas; o recall por classe distingue.

As imagens sao lidas com cv2.imread, em BGR, e entram na rede assim. Tanto
faz BGR ou RGB, desde que quem treina e quem usa leiam do mesmo jeito.
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time

# Antes do import do TensorFlow: so avisos e erros (o nivel padrao imprime
# uma dezena de linhas de INFO sobre instrucoes de CPU que nao interessam).
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# ------------------------------------------------------------------------------
# HIPERPARAMETROS -- declarados aqui, antes de qualquer resultado.
# ------------------------------------------------------------------------------
CLASSES = ('via_livre', 'obstaculo', 'cruzamento')
EPOCAS = 20
SEMENTE = 7
TAMANHO = (128, 96)            # LARGURA x ALTURA de entrada da rede
FRACAO_VALIDACAO = 0.2
LOTE = 32
TAXA_APRENDIZADO = 1e-3        # Adam
FILTROS = (16, 32, 64)         # tres blocos Conv -> BatchNorm -> ReLU -> MaxPool
DENSA = 64
DROPOUT = 0.5                  # o enunciado pede 0,5
# momentum das medias moveis da BatchNormalization. O padrao do Keras e 0.99, e
# com ele, NESTE tamanho de conjunto, a rede nao funciona na inferencia: 400
# imagens em lotes de 32 sao 13 passos por epoca, 260 em 20 epocas, e
# 0.99 ** 260 = 0.07 -- 7% da variancia movel ainda e o valor INICIAL (1.0),
# muito maior que a variancia de verdade. No treino a BN usa as estatisticas
# do lote e acerta; na validacao usa as moveis e erra tudo. Medido: treino 0.91,
# validacao 0.33 (uma classe so). Com 0.9, 0.9 ** 260 ~ 1e-12. Para ver a
# falha: --bn-momento 0.99.
BN_MOMENTO = 0.9
# o augmentation do enunciado, nas unidades do Keras:
ROTACAO = 15.0 / 360.0         # RandomRotation recebe FRACAO de volta: 15 graus = 0,0417
ZOOM = 0.2                     # RandomZoom(0.2): ate 20% para dentro ou para fora
FLIP = 'horizontal'


def ler_tamanho(texto):
    """'128x96' -> (128, 96)."""
    try:
        w, h = (int(v) for v in texto.lower().split('x'))
    except ValueError:
        raise argparse.ArgumentTypeError(f'tamanho {texto!r}: use LARGURAxALTURA, ex. 128x96')
    if w < 32 or h < 32:
        raise argparse.ArgumentTypeError('tamanho minimo 32x32')
    return w, h


def ler_rotulos(caminho):
    """Lista de (arquivo, indice_da_classe). Para com mensagem se algo nao bate."""
    caminho = pathlib.Path(caminho)
    if not caminho.exists():
        sys.exit(f'nao achei {caminho}: gere com gerar_sintetico.py ou rotular.py')
    with open(caminho, newline='') as f:
        leitor = csv.DictReader(f)
        faltam = {'arquivo', 'classe'} - set(leitor.fieldnames or ())
        if faltam:
            sys.exit(f'{caminho}: faltam as colunas {sorted(faltam)}')
        linhas = []
        for n, r in enumerate(leitor, start=2):
            if r['classe'] not in CLASSES:
                sys.exit(f'{caminho}, linha {n}: classe {r["classe"]!r} nao e uma de {CLASSES}')
            linhas.append((r['arquivo'], CLASSES.index(r['classe'])))
    if len(linhas) < 4:
        sys.exit(f'{caminho}: {len(linhas)} linhas -- poucas para dividir treino e validacao')
    return linhas


def carregar_imagens(pasta, linhas, tamanho):
    """Array (N, A, L, 3) uint8 e vetor de rotulos. Redimensiona se precisar."""
    pasta = pathlib.Path(pasta)
    xs, ys = [], []
    for arquivo, y in linhas:
        img = cv2.imread(str(pasta / arquivo), cv2.IMREAD_COLOR)
        if img is None:
            sys.exit(f'nao consegui ler {pasta / arquivo}')
        if (img.shape[1], img.shape[0]) != tamanho:
            img = cv2.resize(img, tamanho, interpolation=cv2.INTER_AREA)
        xs.append(img)
        ys.append(y)
    return np.stack(xs), np.array(ys, np.int64)


def dividir(ys, fracao, semente):
    """Indices de treino e de validacao, estratificados quando der.

    Estratificar garante que a validacao tenha a mesma proporcao de classes
    que o todo -- sem isso, com 6 cruzamentos em 60, a validacao pode sair
    sem nenhum. Se alguma classe presente tiver um so exemplo, nao ha como
    estratificar, e a divisao vira aleatoria simples (com aviso).
    """
    from sklearn.model_selection import train_test_split
    idx = np.arange(len(ys))
    _, contagem = np.unique(ys, return_counts=True)
    n_val = max(1, int(round(len(ys) * fracao)))
    estratos = ys if contagem.min() >= 2 and n_val >= len(contagem) else None
    if estratos is None:
        print('aviso: alguma classe tem 1 exemplo so -- divisao sem estratificar')
    tr, va = train_test_split(idx, test_size=n_val, random_state=semente, shuffle=True,
                              stratify=estratos)
    return np.sort(tr), np.sort(va)


def construir_nucleo(entrada, semente, bn_momento=BN_MOMENTO):
    """A rede propriamente dita, SEM augmentation. Sai com os pesos iniciais fixos.

    keras.utils.set_random_seed antes de construir faz os inicializadores
    sortearem os mesmos pesos todas as vezes: e isso que garante que `sem` e
    `com` partem do mesmo ponto. O testar.py confere peso a peso.
    """
    import keras
    from keras import layers
    keras.utils.set_random_seed(semente)
    x = entrada
    x = layers.Rescaling(1.0 / 255.0, name='escala')(x)
    for i, f in enumerate(FILTROS):
        # sem bias na convolucao: a BatchNormalization logo depois ja tem o seu
        x = layers.Conv2D(f, 3, padding='same', use_bias=False, name=f'conv{i}')(x)
        x = layers.BatchNormalization(momentum=bn_momento, name=f'bn{i}')(x)
        x = layers.Activation('relu', name=f'relu{i}')(x)
        x = layers.MaxPooling2D(name=f'pool{i}')(x)
    x = layers.Flatten(name='achatar')(x)
    x = layers.Dense(DENSA, activation='relu', name='densa')(x)
    x = layers.Dropout(DROPOUT, seed=semente, name='dropout')(x)
    saida = layers.Dense(len(CLASSES), activation='softmax', name='classes')(x)
    return saida


def camadas_augmentation(semente):
    """As tres camadas do enunciado. So agem no treino; na inferencia sao identidade."""
    from keras import layers
    return [layers.RandomRotation(ROTACAO, fill_mode='reflect', seed=semente, name='rotacao'),
            layers.RandomZoom(ZOOM, fill_mode='reflect', seed=semente + 1, name='zoom'),
            layers.RandomFlip(FLIP, seed=semente + 2, name='flip')]


def construir_modelo(com_augmentation, tamanho, semente, bn_momento=BN_MOMENTO):
    """Entrada -> [augmentation] -> nucleo. O nucleo e identico nas duas rodadas.

    As camadas de augmentation nao tem peso, e sao criadas DEPOIS do nucleo
    ter sorteado os seus -- assim elas nao consomem numeros do gerador antes
    dos inicializadores e nao mudam os pesos iniciais.
    """
    import keras
    w, h = tamanho
    entrada = keras.Input(shape=(h, w, 3), name='imagem')
    # o nucleo e construido sobre uma entrada propria e depois aplicado como bloco
    entrada_nucleo = keras.Input(shape=(h, w, 3), name='imagem_nucleo')
    nucleo = keras.Model(entrada_nucleo, construir_nucleo(entrada_nucleo, semente, bn_momento),
                         name='nucleo')
    x = entrada
    if com_augmentation:
        for camada in camadas_augmentation(semente):
            x = camada(x)
    modelo = keras.Model(entrada, nucleo(x), name='com' if com_augmentation else 'sem')
    modelo.compile(optimizer=keras.optimizers.Adam(TAXA_APRENDIZADO),
                   loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return modelo


def matriz_confusao(y_verdade, y_previsto):
    """3x3, linhas = verdade, colunas = previsto, sempre nas tres classes.

    labels= fixo: sem ele, uma classe ausente (o obstaculo do 54:0:6) sumiria
    da matriz e ela viraria 2x2 -- escondendo exatamente o que se quer ver.
    """
    from sklearn.metrics import confusion_matrix
    return confusion_matrix(y_verdade, y_previsto, labels=list(range(len(CLASSES))))


def recall_por_classe(m):
    """Recall de cada classe; None se a classe nao aparece na validacao."""
    return [None if m[i].sum() == 0 else m[i, i] / m[i].sum() for i in range(len(CLASSES))]


def pior_recall(m):
    """(classe, recall) da pior classe PRESENTE na validacao."""
    rec = [(r, CLASSES[i]) for i, r in enumerate(recall_por_classe(m)) if r is not None]
    r, c = min(rec)
    return c, r


def salvar_matriz(m, titulo, base):
    """Grava base.csv e base.png."""
    with open(f'{base}.csv', 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['verdade\\previsto'] + list(CLASSES))
        for c, linha in zip(CLASSES, m):
            w.writerow([c] + [int(v) for v in linha])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.8, 4.2), dpi=120)
    # normalizada por linha para a cor (recall), contagem crua no texto
    soma = m.sum(axis=1, keepdims=True)
    frac = np.divide(m, soma, out=np.zeros(m.shape, float), where=soma > 0)
    ax.imshow(frac, cmap='Blues', vmin=0.0, vmax=1.0)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, str(int(m[i, j])), ha='center', va='center', fontsize=12,
                    color='white' if frac[i, j] > 0.6 else '#1a1a19')
    ax.set_xticks(range(len(CLASSES)), CLASSES, fontsize=9)
    ax.set_yticks(range(len(CLASSES)), CLASSES, fontsize=9)
    ax.set_xlabel('previsto')
    ax.set_ylabel('verdade')
    ax.set_title(titulo, fontsize=10)
    fig.tight_layout()
    fig.savefig(f'{base}.png')
    plt.close(fig)


def salvar_exemplos_augmentation(xs, ys, semente, caminho, n=4):
    """Uma imagem por classe presente e n versoes aumentadas ao lado.

    Serve para OLHAR o que o augmentation faz antes de confiar nele: e aqui que
    se ve a faixa amarela indo para a direita com o flip.
    """
    import keras
    camadas = keras.Sequential(camadas_augmentation(semente))
    linhas = []
    for k in range(len(CLASSES)):
        idx = np.flatnonzero(ys == k)
        if len(idx) == 0:
            continue
        img = xs[idx[0]]
        lote = np.repeat(img[None].astype('float32'), n, axis=0)
        aum = np.asarray(camadas(lote, training=True)).clip(0, 255).astype(np.uint8)
        linha = np.hstack([img] + [np.pad(a, ((0, 0), (4, 0), (0, 0)), constant_values=255)
                                   for a in aum])
        cv2.putText(linha, CLASSES[k], (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (255, 255, 255), 1, cv2.LINE_AA)
        linhas.append(np.pad(linha, ((0, 4), (0, 0), (0, 0)), constant_values=255))
    cv2.imwrite(str(caminho), np.vstack(linhas))


def validacao_perturbada(xva, semente):
    """A validacao passada UMA vez pelas camadas de augmentation, com semente fixa.

    A validacao normal nunca passa pelo augmentation -- e e certo que nao passe:
    ela mede a tarefa como ela e. Mas, se as imagens de validacao nunca estao
    giradas nem espelhadas, a rodada `com` paga o preco do augmentation (aprende
    mais devagar) sem ter onde cobrar o beneficio. Esta segunda medida pergunta
    o que o augmentation promete: a rede aguenta a camera torta? As duas rodadas
    sao medidas sobre o MESMO conjunto perturbado, gerado antes delas.
    """
    import keras
    camadas = keras.Sequential(camadas_augmentation(semente + 1000))
    return np.asarray(camadas(xva.astype('float32'), training=True)).clip(0, 255)


def treinar_rodada(nome, com_aug, dados, args, saida):
    """Uma rodada completa: constroi, treina, avalia, grava. Devolve o resumo."""
    import tensorflow as tf
    xtr, ytr, xva, yva, xva_pert = dados
    modelo = construir_modelo(com_aug, args.tamanho, args.semente, args.bn_momento)
    # mesma ordem de lotes nas duas rodadas: embaralhamento semeado pela mesma semente
    ds_tr = (tf.data.Dataset.from_tensor_slices((xtr, ytr))
             .shuffle(len(xtr), seed=args.semente, reshuffle_each_iteration=True)
             .batch(args.lote))
    ds_va = tf.data.Dataset.from_tensor_slices((xva, yva)).batch(args.lote)
    t0 = time.perf_counter()
    hist = modelo.fit(ds_tr, validation_data=ds_va, epochs=args.epocas, verbose=2)
    segundos = time.perf_counter() - t0
    h = {k: [float(v) for v in vs] for k, vs in hist.history.items()}
    h['segundos'] = segundos
    with open(saida / f'historico_{nome}.json', 'w') as f:
        json.dump(h, f, indent=1)
    modelo.save(saida / f'modelo_{nome}.keras')
    prev = np.argmax(modelo.predict(xva, verbose=0), axis=1)
    m = matriz_confusao(yva, prev)
    titulo = f'{nome} augmentation -- validacao ({len(yva)} imagens)'
    salvar_matriz(m, titulo, saida / f'matriz_{nome}')
    acc_pert = float(np.mean(np.argmax(modelo.predict(xva_pert, verbose=0), axis=1) == yva))
    return {'acc_pert': acc_pert, 'nome': nome, 'acc': h['val_accuracy'][-1],
            'perda': h['val_loss'][-1],
            'acc_treino': h['accuracy'][-1], 'melhor': max(h['val_accuracy']),
            'melhor_ep': int(np.argmax(h['val_accuracy'])) + 1, 'matriz': m,
            'segundos': segundos}


def montar_tabela(r_sem, r_com, ytr, yva, args, n_total, fonte):
    """O texto da tabela final, igual na tela e no tabela.txt."""
    def fmt_rec(m):
        return '  '.join('  n/a ' if r is None else f'{r:6.3f}' for r in recall_por_classe(m))

    contagem = np.bincount(np.concatenate([ytr, yva]), minlength=len(CLASSES))
    maioria = int(np.argmax(np.bincount(ytr, minlength=len(CLASSES))))
    base = float(np.mean(yva == maioria))
    linhas = [
        f'dados   : {fonte} -- {n_total} imagens, ' + ', '.join(
            f'{c} {int(k)}' for c, k in zip(CLASSES, contagem)),
        f'divisao : {len(ytr)} treino / {len(yva)} validacao, semente {args.semente}; '
        f'{args.epocas} epocas, lote {args.lote}, entrada {args.tamanho[0]}x{args.tamanho[1]}, '
        f'BN momentum {args.bn_momento}',
        f'linha de base: responder SEMPRE "{CLASSES[maioria]}" acerta {base:.3f} da validacao',
        '',
        'rodada  acc_val  perda_val  acc_treino  melhor_acc_val(ep)  pior recall'
        '          acc_val_pert   tempo',
    ]
    for r in (r_sem, r_com):
        c, rec = pior_recall(r['matriz'])
        linhas.append(f'{r["nome"]:<6}  {r["acc"]:7.3f}  {r["perda"]:9.3f}'
                      f'  {r["acc_treino"]:10.3f}  {r["melhor"]:10.3f} ({r["melhor_ep"]:2d})'
                      f'     {c:<10} {rec:6.3f}  {r["acc_pert"]:12.3f}'
                      f'  {r["segundos"]:6.1f} s')
    linhas.append(f'diferenca (com - sem) na acc_val final: {r_com["acc"] - r_sem["acc"]:+.3f}'
                  f'; na acc_val_pert: {r_com["acc_pert"] - r_sem["acc_pert"]:+.3f}')
    linhas.append('acc_val_pert = a MESMA validacao passada uma vez (semente fixa) por rotacao,'
                  ' zoom e flip')
    linhas.append('')
    linhas.append('recall por classe   ' + '  '.join(f'{c[:6]:>6}' for c in CLASSES))
    for r in (r_sem, r_com):
        linhas.append(f'  {r["nome"]:<17} {fmt_rec(r["matriz"])}')
    linhas.append('')
    for r in (r_sem, r_com):
        linhas.append(f'matriz {r["nome"]} (linha = verdade, coluna = previsto, '
                      + ' / '.join(CLASSES) + ')')
        for c, linha in zip(CLASSES, r['matriz']):
            linhas.append(f'  {c:<11}' + ''.join(f'{int(v):6d}' for v in linha))
    return '\n'.join(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pasta', required=True, nargs='+',
                    help='pasta(s) com as imagens e o rotulos.csv; varias pastas (uma por '
                    'semente do MetaDrive, por exemplo) sao juntadas')
    ap.add_argument('--rotulos', help='CSV de rotulos (padrao PASTA/rotulos.csv; '
                    'so com uma --pasta)')
    ap.add_argument('--saida', default='resultado', help='pasta de saida (padrao resultado)')
    ap.add_argument('--epocas', type=int, default=EPOCAS, help=f'padrao {EPOCAS}')
    ap.add_argument('--semente', type=int, default=SEMENTE, help=f'padrao {SEMENTE}')
    ap.add_argument('--tamanho', type=ler_tamanho, default=TAMANHO,
                    help='LARGURAxALTURA de entrada (padrao %dx%d)' % TAMANHO)
    ap.add_argument('--lote', type=int, default=LOTE, help=f'padrao {LOTE}')
    ap.add_argument('--bn-momento', type=float, default=BN_MOMENTO,
                    help=f'momentum da BatchNormalization (padrao {BN_MOMENTO}; o do Keras '
                    'e 0.99 -- leia o comentario no topo antes de mudar)')
    args = ap.parse_args()

    if args.rotulos and len(args.pasta) > 1:
        ap.error('--rotulos so vale com uma --pasta; com varias, cada uma tem o seu rotulos.csv')
    # o caminho de cada imagem passa a incluir a pasta: e assim que varias pastas
    # se juntam, e e assim que o divisao.csv diz de onde veio cada uma
    linhas = []
    for pasta in args.pasta:
        csv_pasta = args.rotulos or pathlib.Path(pasta) / 'rotulos.csv'
        linhas += [(str(pathlib.Path(pasta) / a), y) for a, y in ler_rotulos(csv_pasta)]
    xs, ys = carregar_imagens('', linhas, args.tamanho)
    tr, va = dividir(ys, FRACAO_VALIDACAO, args.semente)
    saida = pathlib.Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    with open(saida / 'divisao.csv', 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(('arquivo', 'classe', 'conjunto'))
        conj = {int(i): 'treino' for i in tr} | {int(i): 'validacao' for i in va}
        for i, (arquivo, y) in enumerate(linhas):
            w.writerow((arquivo, CLASSES[y], conj[i]))

    import tensorflow as tf
    # determinismo de operacao: a mesma semente da os mesmos numeros de uma
    # execucao para a outra, na mesma maquina (outra CPU pode diferir na 3a casa)
    tf.config.experimental.enable_op_determinism()
    print(f'tensorflow {tf.__version__}, dispositivos: '
          + ', '.join(d.device_type for d in tf.config.list_physical_devices()))
    salvar_exemplos_augmentation(xs[tr], ys[tr], args.semente,
                                 saida / 'exemplos_augmentation.png')

    dados = (xs[tr], ys[tr], xs[va], ys[va], validacao_perturbada(xs[va], args.semente))
    resultados = []
    for nome, com_aug in (('sem', False), ('com', True)):
        print(f'\n=== rodada {nome} augmentation ===')
        resultados.append(treinar_rodada(nome, com_aug, dados, args, saida))

    fonte = ' + '.join(pathlib.Path(p).name for p in args.pasta)
    tabela = montar_tabela(*resultados, ys[tr], ys[va], args, len(ys), fonte)
    (saida / 'tabela.txt').write_text(tabela + '\n')
    print('\n' + tabela)
    print(f'\narquivos em {saida}/ ; as curvas: curvas.py --pasta {saida}')


if __name__ == '__main__':
    main()
