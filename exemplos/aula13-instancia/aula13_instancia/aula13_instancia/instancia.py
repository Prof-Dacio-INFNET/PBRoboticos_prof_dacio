"""Da mascara a instancia: tres detectores com a MESMA assinatura.

ESTE e o arquivo de verdade do algoritmo. O `instancia.py` da raiz do exemplo
e um carregador de tres linhas que reexporta o que esta aqui -- nao ha duas
implementacoes, e o que roda offline (avaliar.py) e o que roda dentro do no
ROS 2 sao o mesmo codigo. Se divergissem, a medida da aula nao valeria para o
no, e e justamente a medida que a aula vende.

O CONTRATO (e o da Aula 10, de volta):

    def detectar(bgr: np.ndarray, cfg: dict) -> list[dict]
        '''Devolve uma lista de instancias:
           {mascara, bbox, centroide, area, classe}.'''

Tres implementacoes atendem a ele:

  cor_conectada   mascara HSV por classe + componentes conexas. E a heranca
                  direta da Aula 3 -- e e a que FUNDE pecas encostadas.
  cor_watershed   a MESMA mascara, mas com distanceTransform + maximos locais
                  como sementes e watershed para separar o que se encosta.
  modelo          adaptador para um modelo pre-treinado de segmentacao por
                  instancia (ultralytics YOLOv8-seg). Import OPCIONAL: se o
                  pacote nao estiver instalado, ele se declara indisponivel e
                  nao derruba nada.

O PONTO DA AULA, em uma frase: a segmentacao por cor diz ONDE ha objeto, nao
QUANTOS. Duas pecas que se encostam viram uma componente conexa, e o detector
devolve "1" com toda a convicao -- sem excecao, sem aviso, com uma contagem
plausivel. Erro que nao da erro e o erro mais caro que existe.
"""
import cv2
import numpy as np

# Faixa por classe: (h1_min, h1_max, h2_min, h2_max, s_min, v_min).
# Duas faixas de matiz porque o VERMELHO da a volta no circulo de H (que no
# OpenCV vai de 0 a 179). Para as outras cores as duas faixas sao iguais --
# a mesma convencao do config/segmentacao.yaml da Aula 3.
CLASSES_PADRAO = {
    'vermelho': {'faixa': (0, 10, 170, 180, 120, 60), 'cor': (40, 40, 210)},
    'azul': {'faixa': (95, 130, 95, 130, 110, 60), 'cor': (200, 110, 40)},
    'verde': {'faixa': (40, 85, 40, 85, 90, 60), 'cor': (60, 180, 70)},
}

CONFIG_PADRAO = {
    'metodo': 'cor_conectada',
    'classes': CLASSES_PADRAO,
    'area_min': 400.0,          # px^2; abaixo disso e sal-e-pimenta, nao peca
    'nucleo': 5,                # lado do elemento estruturante (0 desliga)
    'fracao_semente': 0.60,     # altura do corte na transformada de distancia
    'modelo_arquivo': 'yolov8n-seg.pt',
    'modelo_confianca': 0.25,
    'classe_por_cor': False,    # ver a nota em `modelo`
}

# Paleta para pintar instancia por instancia (BGR). Ela existe aqui, e nao no
# no ROS 2, para que a figura do avaliador e o topico /vision/segmented usem
# as MESMAS cores: o aluno compara a tela com a figura sem traduzir nada.
PALETA = ((180, 119, 31), (14, 127, 255), (44, 160, 44), (40, 39, 214),
          (189, 103, 148), (75, 86, 140), (194, 119, 227), (127, 127, 127),
          (34, 189, 188), (207, 190, 23))


def opcao(cfg, chave):
    """Le uma opcao do cfg caindo no padrao. cfg=None tambem funciona."""
    if cfg is None:
        return CONFIG_PADRAO[chave]
    return cfg.get(chave, CONFIG_PADRAO[chave])


def mascara_classe(hsv, faixa, nucleo=5):
    """Mascara binaria de UMA classe de cor, com as duas faixas de matiz.

    A morfologia (abertura e depois fechamento) tira sal-e-pimenta e fecha
    buraco. Repare no que ela NAO faz: nao separa peca encostada. O gargalo
    entre duas pecas coladas tem ~25 px e sobrevive a abertura 5x5 inteiro --
    por isso a componente conexa continua vendo uma mancha so.
    """
    h1a, h1b, h2a, h2b, s_min, v_min = [int(v) for v in faixa]
    baixo1 = np.array([h1a, s_min, v_min], np.uint8)
    alto1 = np.array([h1b, 255, 255], np.uint8)
    baixo2 = np.array([h2a, s_min, v_min], np.uint8)
    alto2 = np.array([h2b, 255, 255], np.uint8)
    m = cv2.bitwise_or(cv2.inRange(hsv, baixo1, alto1),
                       cv2.inRange(hsv, baixo2, alto2))
    nucleo = int(nucleo)
    if nucleo >= 3:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (nucleo, nucleo))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    return m


def instancia_de_mascara(mascara, classe):
    """Fecha o contrato a partir de uma mascara 0/255: bbox, centroide, area."""
    ys, xs = np.nonzero(mascara)
    if len(xs) == 0:
        return None
    x, y = int(xs.min()), int(ys.min())
    return {'mascara': mascara, 'classe': classe, 'area': float(len(xs)),
            'bbox': (x, y, int(xs.max()) - x + 1, int(ys.max()) - y + 1),
            'centroide': (float(xs.mean()), float(ys.mean()))}


# --------------------------------------------------------------------------
# 1) cor_conectada -- a heranca da Aula 3
# --------------------------------------------------------------------------
def cor_conectada(bgr, cfg=None):
    """Mascara HSV por classe + cv2.connectedComponentsWithStats.

    Uma componente conexa = uma instancia. E a leitura mais natural da mascara
    da Aula 3, custa quase nada e funciona perfeitamente... enquanto as pecas
    nao se tocam.

    Quando duas se tocam, a mancha e uma, a resposta e "1", e nao ha erro para
    capturar: o programa nao quebra, o topico publica, o print sai bonito. Essa
    e a falha que a regua do avaliar.py existe para tornar visivel.
    """
    area_min = float(opcao(cfg, 'area_min'))
    nucleo = opcao(cfg, 'nucleo')
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    saida = []
    for classe, d in opcao(cfg, 'classes').items():
        m = mascara_classe(hsv, d['faixa'], nucleo)
        n, rotulos, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] < area_min:
                continue
            inst = instancia_de_mascara((rotulos == i).astype(np.uint8) * 255, classe)
            if inst is not None:
                saida.append(inst)
    return saida


# --------------------------------------------------------------------------
# 2) cor_watershed -- a MESMA mascara, separada
# --------------------------------------------------------------------------
def _sementes(m, fracao):
    """Nucleo de cada peca: a parte alta da transformada de distancia.

    A transformada de distancia da, em cada pixel, a distancia ate a borda da
    mascara. O centro de uma peca e um maximo local; o gargalo entre duas pecas
    encostadas e um vale. Cortar na altura `fracao * pico` deixa um nucleo por
    peca e joga o gargalo fora.

    O corte e por COMPONENTE, nao global: uma peca pequena no mesmo quadro de
    uma grande sobreviveria mal a um limiar unico, e e um erro comum (o nucleo
    da peca pequena desaparece e ela e absorvida pela vizinha).
    """
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    sem = np.zeros_like(m)
    n, rotulos, _, _ = cv2.connectedComponentsWithStats(m, 8)
    for i in range(1, n):
        comp = rotulos == i
        pico = float(dist[comp].max())
        if pico <= 0.0:
            continue
        sem[comp & (dist >= fracao * pico)] = 255
    return sem


def cor_watershed(bgr, cfg=None):
    """Mesma mascara da Aula 3, mas com uma linha de agua entre as pecas.

    Receita, nesta ordem:
      1. mascara HSV por classe (igual, igualzinho ao cor_conectada);
      2. transformada de distancia -> nucleo de cada peca vira SEMENTE;
      3. marcadores: 1 = fundo, 2.. = sementes, 0 = o que falta decidir;
      4. cv2.watershed cresce as sementes dentro da mascara e desenha a
         fronteira onde as frentes se encontram.

    O watershed olha a IMAGEM, nao so a mascara: e o gradiente da borda da peca
    que impede o fundo de invadir o objeto. Por isso ele recebe uma copia
    suavizada -- o ruido da cena faz gradiente fraco e atrapalharia a frente.

    Preco honesto: a fronteira do watershed consome ~1 px do perimetro de cada
    instancia, e e por isso que o IoU dos casados fica em ~0,9 e nao em ~0,97.
    Separar custa um pouco de area. Vale a pena, e o numero mostra o quanto.
    """
    area_min = float(opcao(cfg, 'area_min'))
    nucleo = opcao(cfg, 'nucleo')
    fracao = float(opcao(cfg, 'fracao_semente'))
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    suave = cv2.GaussianBlur(bgr, (5, 5), 0)
    saida = []
    for classe, d in opcao(cfg, 'classes').items():
        m = mascara_classe(hsv, d['faixa'], nucleo)
        if not m.any():
            continue
        sem = _sementes(m, fracao)
        n, rot_sem = cv2.connectedComponents(sem, 8)
        if n <= 1:
            continue
        marcadores = rot_sem.astype(np.int32) + 1      # 1 = fundo, 2.. = sementes
        marcadores[(m > 0) & (sem == 0)] = 0           # 0 = a decidir
        cv2.watershed(suave, marcadores)
        for i in range(2, n + 1):
            mi = (marcadores == i).astype(np.uint8) * 255
            if int(np.count_nonzero(mi)) < area_min:
                continue
            inst = instancia_de_mascara(mi, classe)
            if inst is not None:
                saida.append(inst)
    return saida


# --------------------------------------------------------------------------
# 3) modelo -- adaptador OPCIONAL para um modelo pre-treinado
# --------------------------------------------------------------------------
INSTRUCAO_MODELO = (
    'o detector `modelo` precisa do ultralytics, que NAO entra na doutrina da\n'
    '  disciplina (so apt: python3-opencv, python3-numpy, python3-yaml).\n'
    '  Se quiser medi-lo, o ambiente e gerenciado com uv, e sem ativar nada:\n'
    '      uv venv --system-site-packages .venv-yolo\n'
    '      uv pip install --python .venv-yolo/bin/python ultralytics\n'
    '      .venv-yolo/bin/python avaliar.py      # agora com a linha do modelo\n'
    '  O yolov8n-seg.pt (~7 MB) e baixado na primeira execucao.\n'
    '  Sem o uv:  curl -LsSf https://astral.sh/uv/install.sh | sh\n'
    '\n'
    '  NUNCA `pip install` sem ambiente ativo: ele cai em --user e instala\n'
    '  numpy 2, opencv-python 5 e setuptools 84 por cima do que o ROS 2 usa.\n'
    '  O colcon passa a falhar com `--uninstall not recognized`, o cv_bridge\n'
    '  com `_ARRAY_API not found` ou `KeyError: 16`, e codigo que funcionava\n'
    '  quebra porque o OpenCV 5 mudou retornos. O `--python` acima existe\n'
    '  justamente para nao haver "esqueci de ativar". Para desfazer:\n'
    '      mv ~/.local/lib/python3.10/site-packages \\\n'
    '         ~/.local/lib/python3.10/site-packages.guardado')


_MODELO = None
_MOTIVO = ''


class ModeloIndisponivel(RuntimeError):
    """Levantada so se alguem chamar `modelo` sem conferir disponibilidade."""


def modelo_disponivel(cfg=None):
    """Devolve (ok, motivo). NUNCA levanta excecao -- e esse o contrato.

    O import mora aqui dentro, e nao no topo do arquivo, exatamente para que
    um ambiente sem ultralytics continue rodando os outros dois detectores.
    Dependencia opcional que quebra o import do modulo nao e opcional.
    """
    global _MODELO, _MOTIVO
    if _MODELO is not None:
        return True, ''
    try:
        from ultralytics import YOLO
    except Exception as erro:                  # ImportError, mas tambem ABI do NumPy
        _MOTIVO = '%s: %s' % (type(erro).__name__, erro)
        return False, _MOTIVO
    try:
        _MODELO = YOLO(opcao(cfg, 'modelo_arquivo'))
    except Exception as erro:                  # sem rede na primeira vez, arquivo errado
        _MOTIVO = 'ultralytics instalado, mas nao abri o modelo (%s: %s)' % (
            type(erro).__name__, erro)
        return False, _MOTIVO
    return True, ''


def _classe_por_cor(hsv, mascara, classes):
    """Vota a classe pela cor DENTRO da mascara prevista.

    E o remendo honesto do paragrafo abaixo: o modelo acha a instancia, a cor
    diz de que classe ela e. Fica atras de cfg['classe_por_cor'] para que o
    padrao mostre a falha em vez de esconde-la.
    """
    melhor, melhor_n = 'desconhecida', 0
    for classe, d in classes.items():
        m = mascara_classe(hsv, d['faixa'], 0)
        n = int(np.count_nonzero(cv2.bitwise_and(m, m, mask=mascara)))
        if n > melhor_n:
            melhor, melhor_n = classe, n
    return melhor


def modelo(bgr, cfg=None):
    """Segmentacao por instancia com um modelo pre-treinado (YOLOv8-seg).

    A ARMADILHA, e ela vale documentar porque o aluno vai cair nela no TP3: o
    modelo nao conhece as classes do SEU dominio. Ele conhece as 80 classes do
    COCO -- pessoa, carro, cachorro. "Peca vermelha" e "peca azul" nao estao
    la. Entao ele costuma achar as instancias certas (inclusive as encostadas,
    que e onde o metodo classico falha) e erra a classe, enquanto o metodo
    classico acerta a classe e erra a separacao.

    Por isso a classe sai prefixada com 'coco:': na tabela do avaliador, o
    acerto de classe cai para perto de zero e a conversa fica concreta. Ligue
    cfg['classe_por_cor'] = True para votar a classe pela cor dentro da mascara
    -- um hibrido de tres linhas que costuma ser a resposta certa no TP3.

    Medir isto com a MESMA regua e o ponto: o modelo nao entra como ato de fe,
    entra como uma linha a mais na tabela.
    """
    ok, motivo = modelo_disponivel(cfg)
    if not ok:
        raise ModeloIndisponivel(motivo + '\n' + INSTRUCAO_MODELO)

    area_min = float(opcao(cfg, 'area_min'))
    conf = float(opcao(cfg, 'modelo_confianca'))
    por_cor = bool(opcao(cfg, 'classe_por_cor'))
    altura, largura = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV) if por_cor else None

    resultado = _MODELO.predict(bgr, conf=conf, verbose=False)[0]
    if resultado.masks is None:
        return []
    nomes = getattr(resultado, 'names', {})
    classes = [int(c) for c in resultado.boxes.cls.tolist()]
    saida = []
    for bruta, indice in zip(resultado.masks.data.cpu().numpy(), classes):
        # A mascara sai na resolucao do modelo; volta para a da imagem.
        m = cv2.resize(bruta.astype(np.float32), (largura, altura),
                       interpolation=cv2.INTER_NEAREST)
        m = (m > 0.5).astype(np.uint8) * 255
        if int(np.count_nonzero(m)) < area_min:
            continue
        classe = ('coco:%s' % nomes.get(indice, indice)) if not por_cor else \
            _classe_por_cor(hsv, m, opcao(cfg, 'classes'))
        inst = instancia_de_mascara(m, classe)
        if inst is not None:
            saida.append(inst)
    return saida


DETECTORES = {
    'cor_conectada': cor_conectada,
    'cor_watershed': cor_watershed,
    'modelo': modelo,
}


def detectar(bgr, cfg=None):
    """Despacha pelo cfg['metodo']. E por aqui que o no ROS 2 entra.

    O no le o metodo de um parametro, monta o cfg e chama esta funcao. Trocar
    de metodo em producao e, de verdade, uma linha no YAML.
    """
    metodo = opcao(cfg, 'metodo')
    if metodo not in DETECTORES:
        raise KeyError('metodo desconhecido: %s (tenho: %s)'
                       % (metodo, ', '.join(DETECTORES)))
    return DETECTORES[metodo](bgr, cfg)


def pintar_instancias(bgr, instancias, alfa=0.55, contorno=True):
    """Pinta UMA COR POR INSTANCIA sobre a imagem. E o que vai no topico.

    A diferenca com a Aula 3 e exatamente esta: la a cor dizia a CLASSE, aqui
    ela diz a INSTANCIA. Duas pecas vermelhas encostadas pintadas de uma cor so
    e um erro que se ve na tela, antes de qualquer metrica.
    """
    camada = np.zeros_like(bgr)
    for i, inst in enumerate(instancias):
        camada[inst['mascara'] > 0] = PALETA[i % len(PALETA)]
    saida = cv2.addWeighted(bgr, 1.0, camada, alfa, 0)
    if contorno:
        # Contorno da INSTANCIA, nao a caixa: e ele que mostra a linha onde o
        # watershed cortou. Com caixa, duas pecas encostadas ficam com dois
        # retangulos sobrepostos e nao se ve onde foi o corte.
        for i, inst in enumerate(instancias):
            cnts, _ = cv2.findContours((inst['mascara'] > 0).astype(np.uint8),
                                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(saida, cnts, -1, PALETA[i % len(PALETA)], 2)
    return saida
