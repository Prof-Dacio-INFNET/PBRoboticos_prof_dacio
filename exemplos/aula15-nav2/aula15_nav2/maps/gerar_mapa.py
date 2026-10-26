"""Gera o par mapa.pgm + mapa.yaml a partir da grade do Mundo da Aula 11.

Isto NAO e' um no ROS 2. E' a ferramenta que produziu os arquivos que estao
nesta pasta, guardada aqui para que a procedencia do mapa fique registrada:
ninguem desenhou este mapa a mao, ele saiu da MESMA classe `Mundo` que o
simulador da Aula 11 usa para gerar o /scan.

    python3 gerar_mapa.py                 # regera mapa.pgm e mapa.yaml
    python3 gerar_mapa.py --conferir      # so' confere o par que ja' existe

Por que um mapa pronto: o Nav2 nao sobe sem mapa, e o aluno que esta na Aula 15
pode ainda nao ter rodado o SLAM da Aula 12 ate' o fim. Com este mapa o exemplo
anda no primeiro `ros2 launch`; depois ele troca pelo mapa DELE e e' isso que o
G4.0 cobra.

O formato e' o do nav2_map_server, e as tres armadilhas dele estao comentadas
no codigo: a ordem das linhas, o sentido do `negate` e os dois limiares.
"""
import argparse
import importlib.util
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))

# A grade de origem vive no pacote da Aula 11, dois exemplos atras. Carregamos
# o modulo por caminho em vez de `import aula11_mundo.mapa` de proposito: assim
# este script roda na arvore de fontes, sem precisar de colcon build nenhum.
CAMINHO_MAPA_A11 = os.path.normpath(os.path.join(
    AQUI, '..', '..', '..', 'aula11-mundo', 'aula11_mundo', 'aula11_mundo', 'mapa.py'))

# Valores de pixel. Sao os MESMOS que o `map_saver_cli` escreve, de proposito:
# se o aluno salvar o mapa dele com o map_saver, os dois arquivos sao
# comparaveis pixel a pixel.
LIVRE = 254        # branco  -> celula livre
OCUPADO = 0        # preto   -> parede

# Limiares do map_server. Com negate=0 ele calcula shade = (255 - pixel)/255 e
# compara: shade > occupied_thresh e' parede, shade < free_thresh e' livre, e o
# que sobra no meio e' DESCONHECIDO. Com LIVRE=254 o shade da' 0,004 e com
# OCUPADO=0 da' 1,0 -- os dois bem longe da faixa cinzenta, que e' o que se
# quer: mapa binario nao deve ter celula ambigua.
OCCUPIED_THRESH = 0.65
FREE_THRESH = 0.25


def carregar_mundo():
    """Importa a classe Mundo da Aula 11 pelo caminho do arquivo."""
    if not os.path.exists(CAMINHO_MAPA_A11):
        raise SystemExit(f'nao achei a grade da Aula 11 em {CAMINHO_MAPA_A11}')
    spec = importlib.util.spec_from_file_location('mapa_aula11', CAMINHO_MAPA_A11)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.Mundo()


def escrever_pgm(caminho, imagem):
    """PGM binario P5, 8 bits. Cabecalho ASCII, dados crus depois."""
    altura, largura = imagem.shape
    with open(caminho, 'wb') as f:
        f.write(f'P5\n{largura} {altura}\n255\n'.encode('ascii'))
        f.write(np.ascontiguousarray(imagem, dtype=np.uint8).tobytes())


def ler_pgm(caminho):
    """Le um PGM P5 de 8 bits. Tolera comentarios (#) no cabecalho."""
    with open(caminho, 'rb') as f:
        bruto = f.read()
    if not bruto.startswith(b'P5'):
        raise ValueError('nao e PGM binario P5')
    campos, i = [], 2
    while len(campos) < 3:
        while i < len(bruto) and bruto[i:i + 1].isspace():
            i += 1
        if bruto[i:i + 1] == b'#':
            while i < len(bruto) and bruto[i:i + 1] != b'\n':
                i += 1
            continue
        j = i
        while j < len(bruto) and not bruto[j:j + 1].isspace():
            j += 1
        campos.append(int(bruto[i:j]))
        i = j
    largura, altura, maxval = campos
    if maxval != 255:
        raise ValueError(f'maxval {maxval}: este leitor so trata 8 bits')
    i += 1                                     # o unico byte branco apos maxval
    dados = np.frombuffer(bruto[i:i + largura * altura], dtype=np.uint8)
    return dados.reshape(altura, largura)


def gerar(mundo, pasta):
    """Escreve mapa.pgm e mapa.yaml a partir da grade booleana do mundo."""
    imagem = np.where(mundo.grade, OCUPADO, LIVRE).astype(np.uint8)

    # ARMADILHA 1, a que mais custa: o PGM tem a linha 0 em CIMA, e o
    # OccupancyGrid tem a linha 0 na ORIGEM (canto inferior esquerdo). O
    # map_server le a linha j do PGM para a linha (altura - 1 - j) da grade.
    # Sem este flipud o mapa carrega, nao da erro nenhum, e fica espelhado em
    # y -- o obstaculo da sala norte aparece na sala sul e o AMCL converge para
    # a pose errada com cara de convergencia boa.
    imagem = np.flipud(imagem)

    pgm = os.path.join(pasta, 'mapa.pgm')
    yml = os.path.join(pasta, 'mapa.yaml')
    escrever_pgm(pgm, imagem)

    # ARMADILHA 2: `image:` e' relativo a' PASTA DO YAML, nao ao diretorio de
    # onde voce rodou o launch. Por isso fica so' o nome do arquivo aqui.
    #
    # ARMADILHA 3: origin e' o canto INFERIOR ESQUERDO do mapa no quadro `map`,
    # em [x, y, yaw]. A grade da Aula 11 comeca em (0, 0) e o /mundo_real e'
    # publicado com origin (0, 0), entao aqui tambem e' (0, 0) -- e com isso o
    # mapa estatico e a verdade do simulador ficam sobrepostos no RViz2. Mexer
    # neste par desloca o mapa inteiro sem avisar.
    with open(yml, 'w', encoding='ascii') as f:
        f.write('# Gerado por gerar_mapa.py a partir da grade da Aula 11.\n')
        f.write('# Nao edite a mao: rode o script de novo.\n')
        f.write('image: mapa.pgm\n')
        f.write('mode: trinary\n')
        f.write(f'resolution: {mundo.res}\n')
        f.write('origin: [0.0, 0.0, 0.0]\n')
        f.write('negate: 0\n')
        f.write(f'occupied_thresh: {OCCUPIED_THRESH}\n')
        f.write(f'free_thresh: {FREE_THRESH}\n')
    return pgm, yml


def conferir(mundo, pasta):
    """Rele o PGM, desfaz o flip e compara celula a celula com a grade."""
    imagem = ler_pgm(os.path.join(pasta, 'mapa.pgm'))
    if imagem.shape != mundo.grade.shape:
        raise SystemExit(f'forma {imagem.shape} != grade {mundo.grade.shape}')

    # O caminho de volta, exatamente como o map_server faria: desfaz o flip e
    # aplica o limiar de ocupacao sobre o shade.
    shade = (255.0 - np.flipud(imagem).astype(float)) / 255.0
    ocupado = shade > OCCUPIED_THRESH
    livre = shade < FREE_THRESH
    ambiguo = int((~ocupado & ~livre).sum())

    iguais = int((ocupado == mundo.grade).sum())
    total = mundo.grade.size
    paredes = int(mundo.grade.sum())
    print(f'grade        : {mundo.nx} x {mundo.ny} celulas, res {mundo.res} m')
    print(f'paredes       : {paredes} celulas na origem, '
          f'{int(ocupado.sum())} relidas do PGM')
    print(f'acerto        : {iguais}/{total} celulas ({100.0 * iguais / total:.4f}%)')
    print(f'ambiguas      : {ambiguo} celulas cairiam como DESCONHECIDO')
    if iguais != total or ambiguo:
        raise SystemExit('o par mapa.pgm/mapa.yaml NAO reproduz a grade')
    print('ok            : o par reproduz a grade da Aula 11 celula a celula')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--conferir', action='store_true',
                    help='nao reescreve nada, so confere o par existente')
    ap.add_argument('--pasta', default=AQUI, help='onde gravar (padrao: esta pasta)')
    args = ap.parse_args()

    mundo = carregar_mundo()
    if not args.conferir:
        pgm, yml = gerar(mundo, args.pasta)
        print('escrito       :', pgm)
        print('escrito       :', yml)
    conferir(mundo, args.pasta)
    return 0


if __name__ == '__main__':
    sys.exit(main())
