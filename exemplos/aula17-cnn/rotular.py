#!/usr/bin/env python3
"""Rotula os quadros REAIS do MetaDrive: propoe pelo estado.csv, voce revisa.

    python3 rotular.py --pasta quadros                 # revisao por teclado (precisa de tela)
    python3 rotular.py --pasta quadros --so-sugestao   # grava a sugestao, sem revisar

Roda com o python3 DO SISTEMA (o OpenCV do apt tem janela; o do venv da CNN e
o `opencv-python-headless`, que nao tem `imshow`). So precisa de cv2 e csv.

Le PASTA/estado.csv, que o capturar_frames.py da aula17-metadrive escreve
(uma linha por quadro, com a coluna `rotulo_sugerido`), mostra cada quadro
com a sugestao, e grava PASTA/rotulos.csv com as colunas

    arquivo,classe,sugerido

`classe` e o rotulo final, o que o treinar.py le; `sugerido` fica ao lado para
que o numero de correcoes saia de uma conta e nao da memoria: e esse numero
que vai para o relatorio. Linhas do estado.csv cujo PNG nao existe na pasta
(a amostra/ do repositorio tem 12 dos 60) sao puladas, com aviso.

TECLAS na janela:
    1 / 2 / 3     via_livre / obstaculo / cruzamento, e avanca
    Enter, espaco aceita o rotulo mostrado (a sugestao, se ainda nao revisou) e avanca
    seta esq., a  volta um quadro          seta dir., d  avanca sem mudar
    s             grava agora              q, Esc        grava e sai
Se o rotulos.csv ja existir, a revisao CONTINUA dele: da para parar e voltar.

POR QUE NAO ROTULAR COM A PROPRIA REDE. A tentacao e treinar com os 60
rotulos revisados e deixar a rede rotular os outros 440. Isso e circular: o
rotulo e a resposta contra a qual a rede vai ser MEDIDA. Se quem escreve a
resposta e a rede, a matriz de confusao passa a medir quanto a rede concorda
consigo mesma -- e ela concorda muito. Os erros que ela comete viram verdade,
e nenhum numero da tabela consegue mostrar isso.

POR QUE A REVISAO MANUAL E OBRIGATORIA NO RELATORIO. A sugestao do estado.csv
e geometria sobre o estado do simulador, nao visao: ela chama de cruzamento
os metros ANTES do cruzamento (o bloco em que a faixa termina), nao ve se o
carro da frente estava escondido por uma curva, e nao conta o carro da faixa
vizinha que ocupa o meio da imagem. A rede vai aprender o que voce rotular;
se voce nao olhou, ela aprende a regra do script, e a acuracia mede quanto
ela imita o script. Diga no relatorio quantas linhas voce corrigiu e por que.
"""
import argparse
import csv
import pathlib
import sys

CLASSES = ('via_livre', 'obstaculo', 'cruzamento')
COLUNAS_ESTADO = ('arquivo', 'rotulo_sugerido')
ESCALA = 2                     # o quadro de 320x240 aparece a 640x480
SALVAR_A_CADA = 20             # grava sozinho de tantos em tantos quadros

# codigos de tecla do cv2.waitKeyEx: GTK (o OpenCV do apt), Windows e Qt (o do pip).
# Se as setas nao responderem no seu, `a` e `d` fazem o mesmo.
SETA_ESQ = (65361, 2424832, 16777234)
SETA_DIR = (65363, 2555904, 16777236)
ENTER = (13, 10, 32)
ESC = 27


def ler_estado(pasta):
    """Lista de (arquivo, sugerido) das linhas cujo PNG existe; e quantas faltaram."""
    caminho = pathlib.Path(pasta) / 'estado.csv'
    if not caminho.exists():
        sys.exit(f'nao achei {caminho}: e o capturar_frames.py da aula17-metadrive que o grava')
    with open(caminho, newline='') as f:
        leitor = csv.DictReader(f)
        faltam = set(COLUNAS_ESTADO) - set(leitor.fieldnames or ())
        if faltam:
            sys.exit(f'{caminho}: faltam as colunas {sorted(faltam)}')
        linhas, ausentes = [], 0
        for r in leitor:
            sug = r['rotulo_sugerido']
            if sug not in CLASSES:
                sys.exit(f'{caminho}: rotulo_sugerido {sug!r} nao e uma de {CLASSES}')
            if (pathlib.Path(pasta) / r['arquivo']).exists():
                linhas.append((r['arquivo'], sug))
            else:
                ausentes += 1
    return linhas, ausentes


def ler_rotulos_existentes(caminho):
    """{arquivo: classe} de um rotulos.csv anterior, para continuar a revisao."""
    caminho = pathlib.Path(caminho)
    if not caminho.exists():
        return {}
    with open(caminho, newline='') as f:
        return {r['arquivo']: r['classe'] for r in csv.DictReader(f)
                if r.get('classe') in CLASSES}


def gravar(caminho, estado, rotulo):
    """Escreve arquivo,classe,sugerido; devolve quantas linhas diferem da sugestao."""
    with open(caminho, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(('arquivo', 'classe', 'sugerido'))
        for arquivo, sug in estado:
            w.writerow((arquivo, rotulo.get(arquivo, sug), sug))
    return sum(1 for arquivo, sug in estado if rotulo.get(arquivo, sug) != sug)


def aplicar_tecla(tecla, i, n, arquivo, sugerido, rotulo):
    """Funcao pura da revisao: (tecla, posicao) -> (nova posicao, sair?, gravar?).

    Separada da janela para o testar.py conferir o teclado sem tela nenhuma.
    `rotulo` e alterado no lugar.
    """
    if tecla in (ord('q'), ESC):
        return i, True, True
    if tecla == ord('s'):
        return i, False, True
    if tecla in (ord('1'), ord('2'), ord('3')):
        rotulo[arquivo] = CLASSES[tecla - ord('1')]
        return min(i + 1, n - 1), False, False
    if tecla in ENTER:
        rotulo[arquivo] = rotulo.get(arquivo, sugerido)
        return min(i + 1, n - 1), False, False
    if tecla in SETA_ESQ or tecla == ord('a'):
        return max(i - 1, 0), False, False
    if tecla in SETA_DIR or tecla == ord('d'):
        return min(i + 1, n - 1), False, False
    return i, False, False


def _painel(cv2, img, i, n, arquivo, sugerido, atual, revisados):
    """O quadro ampliado com uma faixa de texto embaixo."""
    import numpy as np
    grande = cv2.resize(img, None, fx=ESCALA, fy=ESCALA, interpolation=cv2.INTER_NEAREST)
    faixa = np.full((70, grande.shape[1], 3), 30, np.uint8)
    cor = (80, 220, 80) if atual == sugerido else (60, 160, 255)
    cv2.putText(faixa, f'{i + 1}/{n}  {arquivo}  revisados {revisados}', (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(faixa, f'sugerido: {sugerido}   rotulo: {atual}', (8, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor, 1, cv2.LINE_AA)
    cv2.putText(faixa, '1 livre  2 obstaculo  3 cruzamento  Enter aceita  <- ->  q sai',
                (8, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 170, 170), 1, cv2.LINE_AA)
    return np.vstack([grande, faixa])


def revisar(pasta, estado, rotulo, saida):
    """O laco da janela. Devolve o dicionario de rotulos revisados."""
    import cv2
    janela = 'rotular -- 1/2/3, Enter, setas, q'
    try:
        cv2.namedWindow(janela, cv2.WINDOW_AUTOSIZE)
    except cv2.error:
        sys.exit('este OpenCV nao abre janela (e o headless do venv?). Rode com o python3 do '
                 'sistema, ou use --so-sugestao')
    i, desde_gravar = 0, 0
    # comeca no primeiro quadro ainda nao revisado
    while i < len(estado) - 1 and estado[i][0] in rotulo:
        i += 1
    while True:
        arquivo, sug = estado[i]
        img = cv2.imread(str(pathlib.Path(pasta) / arquivo))
        if img is None:
            sys.exit(f'nao consegui ler {arquivo}')
        cv2.imshow(janela, _painel(cv2, img, i, len(estado), arquivo, sug,
                                   rotulo.get(arquivo, sug), len(rotulo)))
        tecla = cv2.waitKeyEx(0)
        if tecla == -1:            # janela fechada no X
            break
        i, sair, salvar = aplicar_tecla(tecla, i, len(estado), arquivo, sug, rotulo)
        desde_gravar += 1
        if salvar or desde_gravar >= SALVAR_A_CADA:
            gravar(saida, estado, rotulo)
            desde_gravar = 0
        if sair:
            break
    cv2.destroyAllWindows()
    return rotulo


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pasta', required=True, help='pasta com os quadroNNN.png e o estado.csv')
    ap.add_argument('--saida', help='CSV de saida (padrao PASTA/rotulos.csv)')
    ap.add_argument('--so-sugestao', action='store_true',
                    help='grava a sugestao do estado.csv sem abrir janela')
    a = ap.parse_args()

    saida = pathlib.Path(a.saida) if a.saida else pathlib.Path(a.pasta) / 'rotulos.csv'
    estado, ausentes = ler_estado(a.pasta)
    if not estado:
        sys.exit(f'nenhum PNG do estado.csv existe em {a.pasta}')
    if ausentes:
        print(f'aviso: {ausentes} linhas do estado.csv sem PNG na pasta -- puladas')
    rotulo = ler_rotulos_existentes(saida)
    if rotulo:
        print(f'continuando {saida}: {len(rotulo)} quadros ja tinham rotulo')
    if not a.so_sugestao:
        rotulo = revisar(a.pasta, estado, rotulo, saida)
    corrigidos = gravar(saida, estado, rotulo)

    contagem = {c: 0 for c in CLASSES}
    for arquivo, sug in estado:
        contagem[rotulo.get(arquivo, sug)] += 1
    revisados = sum(1 for arquivo, _ in estado if arquivo in rotulo)
    print(f'{len(estado)} quadros em {saida}: ' + ', '.join(f'{c} {k}'
                                                        for c, k in contagem.items()))
    print(f'revisados a mao: {revisados}; diferentes da sugestao: {corrigidos}')
    if a.so_sugestao and not revisados:
        print('so a sugestao: ninguem olhou estes quadros. O item 4 pede a revisao.')
    vazias = [c for c, k in contagem.items() if k == 0]
    if vazias:
        print('olhe: nenhuma imagem de ' + ', '.join(vazias)
              + ' -- a matriz de confusao vai ter essa linha vazia')


if __name__ == '__main__':
    main()
