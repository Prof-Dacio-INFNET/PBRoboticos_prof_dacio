"""Teste offline do miolo de visão — roda SEM ROS 2 instalado.

Dois usos:

    python3 teste_offline.py                    # cena sintética: 2 vermelhos + 1 azul
    python3 teste_offline.py minha_foto.jpg     # a MESMA segmentação sobre uma foto sua

O primeiro modo é a garantia de que a cena sintética e a segmentação HSV
realmente encontram os 2 objetos vermelhos e ignoram o distrator azul.

O segundo é o que serve à tarefa da semana: sem webcam passada para o WSL2 e
sem WSLg para abrir janela, você ainda consegue medir os limiares do SEU objeto
— tire uma foto com o celular, mande para dentro do WSL e rode aqui. O script
imprime a contagem, salva a máscara e sugere o bloco de YAML.

Os limiares saem de `aula03_visao/config/segmentacao.yaml` quando o PyYAML
estiver disponível; senão, dos valores de vermelho embutidos abaixo.
"""
import sys
import types
from unittest.mock import MagicMock

# --- stubs mínimos para importar os nós sem ROS 2 instalado -----------------
for nome in ('rclpy', 'rclpy.node', 'rclpy.qos', 'sensor_msgs', 'sensor_msgs.msg',
             'std_msgs', 'std_msgs.msg', 'std_srvs', 'std_srvs.srv', 'cv_bridge'):
    if nome not in sys.modules:
        mod = types.ModuleType(nome)
        mod.__getattr__ = lambda _n: MagicMock()  # type: ignore[attr-defined]
        sys.modules[nome] = mod
sys.modules['rclpy.node'].Node = object
sys.modules['sensor_msgs.msg'].Image = MagicMock

import pathlib  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, 'aula03_visao')
from aula03_visao.amostrar_hsv import sugerir_faixas, yaml_sugerido  # noqa: E402
from aula03_visao.publicador_camera import PublicadorCamera  # noqa: E402
from aula03_visao.segmentador_hsv import SegmentadorHSV  # noqa: E402

AQUI = pathlib.Path(__file__).resolve().parent
YAML = AQUI / 'aula03_visao' / 'config' / 'segmentacao.yaml'

PADRAO = {'h_min': 0, 'h_max': 10, 'h_min2': 170, 'h_max2': 180,
          's_min': 120, 'v_min': 70, 'area_min': 400.0}


class Falso:
    """Simula get_parameter(nome).value."""

    def __init__(self, d):
        self.d = d

    def get_parameter(self, nome):
        return types.SimpleNamespace(value=self.d[nome])


def carregar_params():
    """Lê o YAML da disciplina; cai nos padrões se o PyYAML não existir."""
    try:
        import yaml
    except ImportError:
        print('(PyYAML ausente — usando os limiares embutidos)')
        return dict(PADRAO)
    if not YAML.exists():
        print(f'({YAML} não encontrado — usando os limiares embutidos)')
        return dict(PADRAO)
    p = dict(PADRAO)
    p.update(yaml.safe_load(YAML.read_text(encoding='utf-8'))
             ['segmentador_hsv']['ros__parameters'])
    print(f'(limiares lidos de {YAML.relative_to(AQUI)})')
    return p


def segmentar(frame, params):
    """Aplica exatamente a máscara do nó da aula — sem duplicar a regra aqui."""
    seg = object.__new__(SegmentadorHSV)
    seg.get_parameter = Falso(params).get_parameter
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m = seg.mascara(hsv)
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    objetos = [c for c in contornos if cv2.contourArea(c) >= float(params['area_min'])]
    return m, objetos


def modo_cena(params):
    pub = object.__new__(PublicadorCamera)
    pub.altura, pub.largura = 480, 640
    falhas = 0
    for k in range(0, 60, 5):
        pub.k = k
        frame = pub.frame_sintetico()
        m, objetos = segmentar(frame, params)
        n = len(objetos)
        estado = 'ok' if n == 2 else 'ATENCAO (sobreposicao/borda)'
        print(f'frame {k:3d}: {n} objeto(s) vermelho(s) -> {estado}')
        falhas += (n != 2)
        if k == 0:
            cv2.imwrite('/tmp/aula03_frame.png', frame)
            cv2.imwrite('/tmp/aula03_mascara.png', m)
    print(f'\nframes fora do esperado: {falhas}/12 '
          '(alguns são normais quando os dois círculos se sobrepõem)')
    print('PNGs em /tmp/aula03_frame.png e /tmp/aula03_mascara.png')
    return 0


def modo_foto(caminho, params):
    frame = cv2.imread(caminho)
    if frame is None:
        print(f"ERRO: nao consegui abrir '{caminho}'. Dentro do WSL, o disco do "
              'Windows fica em /mnt/c/Users/<voce>/...')
        return 1
    h, w = frame.shape[:2]
    m, objetos = segmentar(frame, params)
    cobertura = 100.0 * float((m > 0).sum()) / (h * w)
    print(f'{caminho}: {w}x{h}')
    print(f'mascara cobre {cobertura:.1f}% da imagem · '
          f'{len(objetos)} objeto(s) acima de area_min={params["area_min"]}')
    for i, c in enumerate(sorted(objetos, key=cv2.contourArea, reverse=True)[:5], 1):
        x, y, cw, ch = cv2.boundingRect(c)
        print(f'  {i}. area={cv2.contourArea(c):8.0f} px²  caixa=({x},{y},{cw},{ch})')

    if cobertura > 60:
        print('\nDIAGNOSTICO: mascara quase toda branca. Se a foto e do ambiente inteiro, '
              'a faixa de matiz esta larga demais ou o fundo tem a cor do objeto — aperte '
              's_min/v_min primeiro. Se voce recortou a foto NO objeto, 60-90% e o esperado.')
    elif cobertura < 0.2:
        print('\nDIAGNOSTICO: mascara quase toda preta — os limiares nao cobrem a cor do '
              'seu objeto. Amostre a cor real (abaixo) antes de mexer no palpite.')

    # A parte que a tarefa pede: medir em vez de chutar. Sem janela para clicar,
    # amostramos os pixels mais saturados — que é onde a cor do objeto vive.
    #
    # Pegamos os 3% mais saturados por CONTAGEM (argsort), não por limiar de
    # percentil: em foto com fundo neutro a maioria dos pixels tem S=0, o
    # percentil 97 cai em zero e o ">= 0" acaba selecionando a imagem inteira —
    # a sugestao sai com s_min: 0, que é o mesmo que não filtrar nada.
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    plano = hsv.reshape(-1, 3)
    topo = plano[np.argsort(plano[:, 1])[::-1][:max(1, len(plano) // 33)]]
    fortes = topo[(topo[:, 1] >= 40) & (topo[:, 2] >= 40)]  # descarta cinza e sombra
    print('\n--- sugestao a partir dos 3% de pixels mais saturados da foto ---')
    print('(recorte a foto no objeto para a sugestao ficar boa: com o objeto ocupando')
    print(' pouco do quadro, os pixels saturados podem ser de outra coisa)')
    if len(fortes) < 20:
        print('poucos pixels coloridos nesta foto — ela esta escura demais, ou o objeto '
              'e acinzentado. Segmentacao por cor pode nao ser o caminho aqui.')
        p_sug = None
    else:
        amostras = [tuple(int(v) for v in px)
                    for px in fortes[::max(1, len(fortes) // 200)]]
        p_sug = sugerir_faixas(amostras)
        if p_sug['_duas_faixas']:
            print('ATENCAO: sairam duas faixas de matiz. Ou o seu objeto e vermelho (a cor')
            print('da a volta no circulo, e ai esta certo), ou a foto tem DUAS coisas')
            print('coloridas diferentes — nesse caso recorte no objeto e rode de novo.')
    print(yaml_sugerido(p_sug, float(params['area_min'])))
    cv2.imwrite('/tmp/aula03_mascara.png', m)
    print('\nMascara salva em /tmp/aula03_mascara.png — abra e confira se marcou o objeto.')
    return 0


def autoteste():
    """Confere a regra que mais erra sozinha: vermelho vira DUAS faixas de matiz."""
    vermelho = [(2, 200, 180), (178, 210, 160), (5, 190, 200), (175, 220, 170)]
    azul = [(105, 200, 180), (112, 190, 170), (118, 205, 165)]
    pv, pa = sugerir_faixas(vermelho), sugerir_faixas(azul)
    erros = []
    if not pv['_duas_faixas']:
        erros.append('vermelho deveria gerar duas faixas de matiz')
    if pa['_duas_faixas']:
        erros.append('azul nao deveria gerar duas faixas')
    if not (pa['h_min'] <= 105 and pa['h_max'] >= 118):
        erros.append(f'faixa do azul nao cobre as amostras: {pa}')
    if pv['h_max'] >= pv['h_min2']:
        erros.append(f'as duas faixas do vermelho se encostam: {pv}')
    for e in erros:
        print('FALHA:', e)
    print('autoteste de sugerir_faixas:', 'ok' if not erros else f'{len(erros)} falha(s)')
    return 1 if erros else 0


def main():
    params = carregar_params()
    ruim = autoteste()
    print()
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args:
        return modo_foto(args[0], params) or ruim
    return modo_cena(params) or ruim


if __name__ == '__main__':
    raise SystemExit(main())
