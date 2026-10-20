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

AS DUAS FIGURAS, no fim do arquivo (o no escolhe uma pelo parametro `saida`):

  pintar_instancias   uma cor por INSTANCIA. E a figura da aula: duas pecas
                      encostadas pintadas de uma cor so e a fusao na tela.
  sobrepor_classes    uma cor por CLASSE, translucida (alpha) sobre o frame, com
                      contorno por instancia. E o que o item 3 do enunciado do
                      TP3 pede, e o padrao do /vision/segmented.
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


# --------------------------------------------------------------------------
# Sobreposicao POR CLASSE -- o que o item 3 do enunciado do TP3 pede
# --------------------------------------------------------------------------
# Paleta da camada por CLASSE (BGR). Proposito diferente da PALETA acima, e por
# isso as cores sao outras: la a cor diz QUAL instancia, aqui ela diz QUAL
# classe, e a camada entra translucida sobre o frame.
#
# Por que ela NAO usa a cor do proprio objeto (o 'cor' de CLASSES_PADRAO):
# misturar vermelho com vermelho a 50% devolve vermelho. A mascara ficaria
# invisivel exatamente onde ela precisa aparecer -- sobre o objeto. Entao a
# camada usa cores que o dominio nao usa, e quem diz o nome da classe e o
# rotulo de texto. Para forcar a cor do dominio, veja CORES_CLASSE abaixo.
#
# A ORDEM importa, e foi escolhida olhando a tela: misturar duas cores
# COMPLEMENTARES a 50% devolve cinza (vermelho sob ciano vira cinza, e parece
# defeito). As posicoes em que as tres classes deste exemplo caem levam cores
# vizinhas, nao opostas, e a peca sai tingida em vez de lavada.
PALETA_CLASSE = ((130, 160, 40), (30, 140, 245), (220, 200, 30), (200, 40, 200),
                 (60, 230, 140), (170, 60, 90), (150, 120, 255), (40, 210, 230))

# Ponto de extensao de uma linha, para o SEU dominio:
#     from aula13_instancia import instancia
#     instancia.CORES_CLASSE['tomate_maduro'] = (40, 40, 210)
CORES_CLASSE = {}


def cor_da_classe(classe):
    """Cor BGR estavel por NOME de classe: a mesma em toda execucao.

    Nao usa hash(): o hash de str do Python e semeado por processo
    (PYTHONHASHSEED), e a cor de uma classe mudaria de uma execucao para a
    outra -- o que inutiliza comparar duas capturas de tela, que e metade do
    trabalho do relatorio do TP3.

    Com mais classes do que cores na paleta ha repeticao. E aceitavel porque o
    rotulo de texto desempata; quando atrapalhar, fixe a cor em CORES_CLASSE.
    """
    nome = str(classe)
    if nome in CORES_CLASSE:
        return CORES_CLASSE[nome]
    soma = 0
    for i, letra in enumerate(nome):
        soma += (i + 1) * ord(letra)
    return PALETA_CLASSE[soma % len(PALETA_CLASSE)]


def _tinta_do_rotulo(cor):
    """Preto ou branco -- o que tiver contraste com o fundo do rotulo."""
    b, g, r = (int(v) for v in cor)
    luz = 0.114 * b + 0.587 * g + 0.299 * r
    return (0, 0, 0) if luz > 140 else (255, 255, 255)


def _rotular(img, texto, canto, cor):
    """Nome da classe com retangulo SOLIDO atras, ancorado no canto da bbox.

    O fundo solido nao e enfeite: texto fino sobre mascara translucida nao se
    le no projetor da sala nem no print do relatorio. A caixa sobe a partir do
    topo da bbox e e presa dentro do quadro, para nao sair pela borda.
    """
    fonte, escala, grossura = cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
    (largura_txt, altura_txt), base = cv2.getTextSize(texto, fonte, escala, grossura)
    caixa_l, caixa_a = largura_txt + 6, altura_txt + base + 6
    altura, largura = img.shape[:2]
    x = max(0, min(int(canto[0]), largura - caixa_l - 1))
    y = max(caixa_a, min(int(canto[1]), altura - 1))
    cv2.rectangle(img, (x, y - caixa_a), (x + caixa_l, y), cor, -1)
    cv2.putText(img, texto, (x + 3, y - base - 3), fonte, escala,
                _tinta_do_rotulo(cor), grossura, cv2.LINE_AA)


def sobrepor_classes(bgr, instancias, alpha=0.5, contorno=True):
    """Mascaras coloridas POR CLASSE, com transparencia, sobre o frame.

    E o item 3 do enunciado do TP3 ao pe da letra: uma cor por CLASSE (nao por
    instancia), misturada com `alpha` sobre o quadro original, pronta para ir
    ao /vision/segmented e ser vista no RViz2.

    Tres decisoes que parecem detalhe e nao sao:

    1. A mistura acontece SO onde ha mascara. Um addWeighted no quadro inteiro
       escurece o fundo tambem, e a imagem deixa de ser comparavel com o frame
       cru -- que e o uso numero um dela no relatorio. Fora da uniao das
       mascaras o pixel sai identico ao original, byte a byte; so o rotulo
       escreve por cima, porque e anotacao, nao mascara.
    2. O contorno de cada INSTANCIA vai em cor solida, recortado na mascara.
       Sem ele, duas pecas da MESMA classe encostadas viram uma mancha unica --
       a cor diz a classe, e a classe das duas e a mesma. E a fusao da Aula 13
       voltando pela porta da frente: a camada por classe a esconde de novo, e
       o contorno e o que impede.
    3. Cada instancia leva o nome da classe com fundo solido atras do texto.

    Compare com `pintar_instancias`, ao lado: la a cor diz QUAL objeto, aqui
    ela diz DE QUE tipo. Sao as duas perguntas do TP3, e nao a mesma figura.
    """
    alpha = float(min(max(float(alpha), 0.0), 1.0))
    camada = np.zeros_like(bgr)
    uniao = np.zeros(bgr.shape[:2], np.uint8)
    for inst in instancias:
        dentro = inst['mascara'] > 0
        camada[dentro] = cor_da_classe(inst.get('classe', 'desconhecida'))
        uniao[dentro] = 255
    misturado = cv2.addWeighted(bgr, 1.0 - alpha, camada, alpha, 0)
    saida = np.ascontiguousarray(
        np.where(uniao[:, :, None] > 0, misturado, bgr), dtype=np.uint8)

    if contorno:
        for inst in instancias:
            cnts, _ = cv2.findContours((inst['mascara'] > 0).astype(np.uint8),
                                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(saida, cnts, -1,
                             cor_da_classe(inst.get('classe', 'desconhecida')), 2)
        # O traco de 2 px fica metade para fora da mascara; devolver o que
        # esta fora da uniao mantem a promessa do item 1 acima.
        fora = uniao == 0
        saida[fora] = bgr[fora]

    for inst in instancias:
        x, y, _, _ = inst['bbox']
        classe = str(inst.get('classe', 'desconhecida'))
        _rotular(saida, classe, (x, y - 1), cor_da_classe(classe))
    return saida
