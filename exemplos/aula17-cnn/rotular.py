#!/usr/bin/env python3
"""Rotula os quadros REAIS do MetaDrive: propoe pelo estado.csv, voce revisa.

    python3 rotular.py --pasta quadros                 # revisao por teclado, com janela
    python3 rotular.py --pasta quadros --sem-janela    # revisao so pelo terminal
    python3 rotular.py --pasta quadros --so-sugestao   # grava a sugestao, sem revisar

Roda com o python3 DO SISTEMA (o OpenCV do apt tem janela; o do venv da CNN e
o `opencv-python-headless`, que nao tem `imshow`). So precisa de cv2 e csv; o
--sem-janela e o --so-sugestao nem importam o cv2.

Le PASTA/estado.csv, que o capturar_frames.py da aula17-metadrive escreve
(uma linha por quadro, com a coluna `rotulo_sugerido`), mostra cada quadro
com a sugestao, e grava PASTA/rotulos.csv com as colunas

    arquivo,classe,sugerido,revisado

`classe` e o rotulo final, o que o treinar.py le (as outras colunas ele
ignora); `sugerido` fica ao lado para que o numero de correcoes saia de uma
conta e nao da memoria: e esse numero que vai para o relatorio. `revisado` e 1
so nos quadros em que voce apertou 1/2/3 ou Enter; nos outros (0) a `classe` e
a sugestao que ninguem olhou. Linhas do estado.csv cujo PNG nao existe na pasta
(a amostra/ do repositorio tem 12 dos 60) sao puladas, com aviso.

TECLAS, na janela OU no terminal de onde o script foi chamado (as duas valem):
    1 / 2 / 3     via_livre / obstaculo / cruzamento, e avanca
    Enter, espaco aceita o rotulo mostrado (a sugestao, se ainda nao revisou) e avanca
    seta esq., a  volta um quadro          seta dir., d  avanca sem mudar
    s             grava agora              q, Esc, Ctrl+C  grava e sai
Maiusculas valem (CapsLock), e o teclado numerico tambem. Cada passo imprime
uma linha no terminal (`  7/20 quadro018.png -> obstaculo (sugerido via_livre)`),
para haver retorno mesmo com a janela atras de outra. Uma tecla sem funcao
imprime `tecla sem funcao: codigo N (0xHEX)`: e esse codigo que se manda a
quem for consertar, se alguma tecla nao responder.
Se o rotulos.csv ja existir, a revisao CONTINUA dele: da para parar e voltar.
So as linhas com revisado=1 contam como revisadas; um rotulos.csv antigo, sem
essa coluna, e lido como "nada revisado" (com aviso).

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
import os
import pathlib
import shutil
import sys

CLASSES = ('via_livre', 'obstaculo', 'cruzamento')
COLUNAS_ESTADO = ('arquivo', 'rotulo_sugerido')
COLUNAS_SAIDA = ('arquivo', 'classe', 'sugerido', 'revisado')
ESCALA = 2                     # o quadro de 320x240 aparece a 640x480
SALVAR_A_CADA = 20             # grava sozinho de tantos em tantos quadros
SONDAGEM_MS = 50               # de quanto em quanto tempo olha a janela e o terminal

# A revisao trabalha com SIMBOLOS, nao com codigos: '1' '2' '3' 'aceita' 'volta'
# 'avanca' 'grava' 'sai'. normalizar_tecla traduz o codigo do cv2.waitKeyEx;
# decodificar_terminal traduz os bytes do terminal.
#
# Codigos brutos das setas no cv2.waitKeyEx: GTK (o OpenCV do apt), Windows, Qt (o do pip).
SETA_ESQ = (65361, 2424832, 16777234)
SETA_DIR = (65363, 2555904, 16777236)
# No GTK o codigo e o keysym do X (16 bits) com os modificadores acima do bit 16:
# NumLock ligado soma 0x100000, e a tecla `1` chega como 1048625 (0x100031).
KEYSYM = {
    0xFF51: 'volta', 0xFF53: 'avanca',            # Left, Right
    0xFF96: 'volta', 0xFF98: 'avanca',            # KP_Left, KP_Right (NumLock desligado)
    0xFFB1: '1', 0xFFB2: '2', 0xFFB3: '3',        # KP_1..KP_3
    0xFF8D: 'aceita', 0xFF0D: 'aceita',           # KP_Enter, Return
    0xFF1B: 'sai',                                # Escape
}
ASCII = {
    ord('1'): '1', ord('2'): '2', ord('3'): '3',
    13: 'aceita', 10: 'aceita', 32: 'aceita',
    27: 'sai', ord('q'): 'sai', ord('Q'): 'sai',
    ord('s'): 'grava', ord('S'): 'grava',
    ord('a'): 'volta', ord('A'): 'volta',
    ord('d'): 'avanca', ord('D'): 'avanca',
}
TECLAS = ('1/2/3 rotulam e avancam, Enter ou espaco aceita, setas ou a/d andam, '
          's grava, q/Esc/Ctrl+C gravam e saem')


def normalizar_tecla(bruta):
    """Codigo do cv2.waitKeyEx (ou um byte do terminal) -> simbolo, ou None.

    Tenta, nesta ordem: as setas pelos codigos brutos conhecidos; os 16 bits de
    baixo (keysym do GTK, com ou sem modificador); e, se esses 16 bits forem um
    caractere de 8 bits, o ASCII. A guarda dos 16 bits importa: sem ela, a seta
    esquerda do GTK (0xFF51) viraria 'Q' (0x51) e sairia do programa.
    """
    if bruta is None or bruta < 0:
        return None
    if bruta in SETA_ESQ:
        return 'volta'
    if bruta in SETA_DIR:
        return 'avanca'
    baixo = bruta & 0xFFFF
    if baixo in KEYSYM:
        return KEYSYM[baixo]
    if baixo < 0x100:
        return ASCII.get(bruta & 0xFF)
    return None


def decodificar_terminal(dados, fim):
    """Bytes lidos do terminal -> ([(simbolo ou None, descricao)], bytes que sobraram).

    Setas chegam como ESC [ C / ESC [ D (ou ESC O C / ESC O D). Um ESC no fim do
    que foi lido pode ser o comeco de uma seta: com fim=False ele fica no resto,
    para esperar o que vem; com fim=True (ja esperou) e o Esc sozinho, e sai.
    """
    eventos, k, n = [], 0, len(dados)
    while k < n:
        b = dados[k]
        if b != 0x1b:
            eventos.append((normalizar_tecla(b), f'codigo {b} (0x{b:X})'))
            k += 1
            continue
        if k + 1 >= n or dados[k + 1] in b'[O':
            j = k + 2                      # fim da sequencia: o primeiro byte de 0x40 a 0x7E
            if k + 1 < n and dados[k + 1] == ord('['):
                while j < n and not 0x40 <= dados[j] <= 0x7e:
                    j += 1
            if j >= n:                     # incompleta
                if not fim:
                    break
                if k + 1 >= n:
                    eventos.append(('sai', 'Esc'))
                else:
                    eventos.append((None, _seq(dados[k:])))
                k = n
                continue
            simbolo = {ord('C'): 'avanca', ord('D'): 'volta'}.get(dados[j])
            eventos.append((simbolo, _seq(dados[k:j + 1])))
            k = j + 1
        elif dados[k + 1] == 0x1b:         # Esc Esc: o primeiro e Esc sozinho
            eventos.append(('sai', 'Esc'))
            k += 1
        else:                              # ESC + letra: Alt+letra, nao e Esc
            eventos.append((None, _seq(dados[k:k + 2]) + ' (Alt+tecla?)'))
            k += 2
    return eventos, bytes(dados[k:])


def _seq(dados):
    """b'\\x1b[A' -> 'sequencia ESC[A', legivel na linha de `tecla sem funcao`."""
    return 'sequencia ESC' + bytes(dados[1:]).decode('latin-1')


class Terminal:
    """Le teclas do terminal sem esperar Enter e sem eco; restaura tudo na saida.

    `with Terminal() as t:` -- t.ativo e False se a entrada nao e um terminal
    (ou se nao ha termios, no Windows); entao t.ler() devolve sempre [].
    Ctrl+C continua gerando KeyboardInterrupt (ISIG fica ligado).
    """

    def __init__(self):
        self.fd, self.antigo, self.resto, self.ativo = None, None, b'', False

    def __enter__(self):
        try:
            import termios
        except ImportError:
            return self
        if not sys.stdin.isatty():
            return self
        self.fd = sys.stdin.fileno()
        self.antigo = termios.tcgetattr(self.fd)
        novo = termios.tcgetattr(self.fd)
        novo[3] &= ~(termios.ICANON | termios.ECHO)
        novo[6][termios.VMIN], novo[6][termios.VTIME] = 1, 0
        termios.tcsetattr(self.fd, termios.TCSANOW, novo)
        self.ativo = True
        return self

    def __exit__(self, *exc):
        if self.antigo is not None:
            import termios
            # TCSAFLUSH descarta o que foi digitado e nao lido: nada sobra para o shell
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.antigo)
            self.antigo, self.ativo = None, False
        return False

    def _ler_disponivel(self, espera):
        import select
        pronto, _, _ = select.select([self.fd], [], [], espera)
        if not pronto:
            return True
        lido = os.read(self.fd, 1024)
        self.resto += lido
        return bool(lido)

    def ler(self, espera):
        """Espera ate `espera` segundos por teclas; devolve [(simbolo, descricao)]."""
        if not self.ativo:
            return []
        if not self._ler_disponivel(espera):
            return [('sai', 'fim da entrada')]
        if not self.resto:
            return []
        eventos, self.resto = decodificar_terminal(self.resto, fim=False)
        if self.resto:                     # ESC ou seta pela metade: da ~50 ms ao resto
            self._ler_disponivel(SONDAGEM_MS / 1000)
            mais, self.resto = decodificar_terminal(self.resto, fim=True)
            eventos += mais
        return eventos


class Janela:
    """A janela do OpenCV. O cv2 so e importado aqui."""

    NOME = 'rotular -- 1/2/3, Enter, setas, q'

    def __init__(self, pasta):
        import cv2
        self.cv2, self.pasta = cv2, pathlib.Path(pasta)
        self.detecta_fechar, self.mostrou = False, False
        try:
            cv2.namedWindow(self.NOME, cv2.WINDOW_AUTOSIZE)
        except cv2.error:
            sys.exit('este OpenCV nao abre janela (e o headless do venv?). Rode com o python3 do '
                     'sistema, ou use --sem-janela (revisao pelo terminal) ou --so-sugestao')

    def mostrar(self, i, n, arquivo, sugerido, atual, revisados):
        img = self.cv2.imread(str(self.pasta / arquivo))
        if img is None:
            sys.exit(f'nao consegui ler {arquivo}')
        primeira = not self.mostrou
        self.cv2.imshow(self.NOME, _painel(self.cv2, img, i, n, arquivo, sugerido, atual,
                                           revisados))
        if primeira:
            self.mostrou = True
            self.cv2.waitKey(1)
            # Alguns backends nao sabem dizer se a janela esta visivel (devolvem -1 ou
            # lancam). So confia na propriedade se ela disser 1 com a janela aberta.
            self.detecta_fechar = self._visivel() >= 1
            if not self.detecta_fechar:
                print('aviso: este OpenCV nao diz se a janela foi fechada no X; saia com q',
                      flush=True)

    def _visivel(self):
        try:
            return self.cv2.getWindowProperty(self.NOME, self.cv2.WND_PROP_VISIBLE)
        except self.cv2.error:
            return -1

    def esperar(self, ms):
        """Codigo bruto da tecla apertada na janela, ou -1 se nada em `ms` ms."""
        return self.cv2.waitKeyEx(ms)

    def fechada(self):
        """Janela fechada no X? (Com sondagem, o -1 do waitKeyEx nao diz mais isso.)"""
        return self.detecta_fechar and self._visivel() < 1

    def fechar(self):
        try:
            self.cv2.destroyAllWindows()
        except self.cv2.error:
            pass


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
    """{arquivo: classe} dos quadros REVISADOS de um rotulos.csv anterior.

    So entram as linhas com revisado=1: as outras sao a sugestao gravada, e
    conta-las como revisadas e mentir no relatorio. Um rotulos.csv antigo (sem a
    coluna `revisado`) nao diz quem olhou o que: vale como nada revisado. Se ele
    tiver linhas com classe diferente da sugestao, e copiado antes para
    rotulos.antigo.csv, porque a proxima gravacao as voltaria para a sugestao.
    """
    caminho = pathlib.Path(caminho)
    if not caminho.exists():
        return {}
    with open(caminho, newline='') as f:
        leitor = csv.DictReader(f)
        linhas = list(leitor)
        colunas = leitor.fieldnames or ()
    if 'revisado' not in colunas:
        diferentes = sum(1 for r in linhas if r.get('classe') != r.get('sugerido'))
        print(f'aviso: {caminho} nao tem a coluna `revisado` (versao antiga do rotular.py): '
              'nenhum quadro conta como revisado; a revisao recomeca do primeiro')
        if diferentes:
            copia = caminho.with_name(caminho.stem + '.antigo.csv')
            shutil.copy2(caminho, copia)
            print(f'aviso: {diferentes} linhas dele tinham classe diferente da sugestao; '
                  f'copiei o arquivo para {copia} antes de regravar')
        return {}
    return {r['arquivo']: r['classe'] for r in linhas
            if r.get('revisado') == '1' and r.get('classe') in CLASSES}


def gravar(caminho, estado, rotulo):
    """Escreve arquivo,classe,sugerido,revisado; devolve quantas linhas diferem da sugestao."""
    with open(caminho, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(COLUNAS_SAIDA)
        for arquivo, sug in estado:
            w.writerow((arquivo, rotulo.get(arquivo, sug), sug, int(arquivo in rotulo)))
    return sum(1 for arquivo, sug in estado if rotulo.get(arquivo, sug) != sug)


def aplicar_tecla(simbolo, i, n, arquivo, sugerido, rotulo):
    """Funcao pura da revisao: (simbolo, posicao) -> (nova posicao, sair?, gravar?).

    Recebe o simbolo de normalizar_tecla / decodificar_terminal, nao o codigo
    bruto. Separada da janela para o testar.py conferir o teclado sem tela
    nenhuma. `rotulo` e alterado no lugar; estar nele e o que marca "revisado".
    """
    if simbolo == 'sai':
        return i, True, True
    if simbolo == 'grava':
        return i, False, True
    if simbolo in ('1', '2', '3'):
        rotulo[arquivo] = CLASSES[int(simbolo) - 1]
        return min(i + 1, n - 1), False, False
    if simbolo == 'aceita':
        rotulo[arquivo] = rotulo.get(arquivo, sugerido)
        return min(i + 1, n - 1), False, False
    if simbolo == 'volta':
        return max(i - 1, 0), False, False
    if simbolo == 'avanca':
        return min(i + 1, n - 1), False, False
    return i, False, False


def _linha_quadro(i, n, arquivo, sugerido, rotulo):
    """`  8/20 quadro019.png  rotulo via_livre (sugerido via_livre), nao revisado`"""
    situacao = 'revisado' if arquivo in rotulo else 'nao revisado'
    return (f'  {i + 1}/{n} {arquivo}  rotulo {rotulo.get(arquivo, sugerido)} '
            f'(sugerido {sugerido}), {situacao}')


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


def _passo(simbolo, i, estado, rotulo, sem_janela):
    """Aplica um simbolo e imprime a linha de progresso. Devolve (i, sair?, gravar?)."""
    n = len(estado)
    arquivo, sug = estado[i]
    novo, sair, salvar = aplicar_tecla(simbolo, i, n, arquivo, sug, rotulo)
    if simbolo in ('1', '2', '3', 'aceita'):
        print(f'  {i + 1}/{n} {arquivo} -> {rotulo[arquivo]} (sugerido {sug})')
        if novo == i:
            print('  (ultimo quadro; q grava e sai)')
    if novo != i and (sem_janela or simbolo in ('volta', 'avanca')):
        print(_linha_quadro(novo, n, estado[novo][0], estado[novo][1], rotulo))
    sys.stdout.flush()
    return novo, sair, salvar


def revisar(pasta, estado, rotulo, saida, sem_janela=False):
    """O laco da revisao. Devolve o dicionario de rotulos revisados.

    Sonda a janela (waitKeyEx com espera curta) e o terminal, alternando: a
    tecla vale onde estiver o foco. Com --sem-janela, so o terminal.
    """
    n = len(estado)
    i, desde_gravar = 0, 0
    # comeca no primeiro quadro ainda nao revisado
    while i < n - 1 and estado[i][0] in rotulo:
        i += 1
    tela = None if sem_janela else Janela(pasta)
    try:
        with Terminal() as term:
            if sem_janela and not term.ativo:
                sys.exit('--sem-janela le as teclas do terminal, e a entrada nao e um terminal')
            if sem_janela:
                print(f'revisao pelo terminal. Teclas: {TECLAS}')
                print(_linha_quadro(i, n, estado[i][0], estado[i][1], rotulo))
            elif term.ativo:
                print(f'teclas valem na janela ou neste terminal: {TECLAS}')
            else:
                print(f'teclas na janela (a entrada nao e um terminal): {TECLAS}')
            sys.stdout.flush()
            mudou, sair = True, False
            try:
                while not sair:
                    if tela is None:
                        eventos = term.ler(0.5)
                    else:
                        if mudou:
                            arquivo, sug = estado[i]
                            tela.mostrar(i, n, arquivo, sug, rotulo.get(arquivo, sug),
                                         len(rotulo))
                            mudou = False
                        bruta = tela.esperar(SONDAGEM_MS)
                        eventos = [] if bruta == -1 else [
                            (normalizar_tecla(bruta), f'codigo {bruta} (0x{bruta:X})')]
                        eventos += term.ler(0)
                        if not eventos and tela.fechada():
                            print('janela fechada: gravando e saindo', flush=True)
                            break
                    for simbolo, descricao in eventos:
                        if simbolo is None:
                            print(f'tecla sem funcao: {descricao}', flush=True)
                            continue
                        i, sair, salvar = _passo(simbolo, i, estado, rotulo, sem_janela)
                        mudou, desde_gravar = True, desde_gravar + 1
                        if salvar or desde_gravar >= SALVAR_A_CADA:
                            gravar(saida, estado, rotulo)
                            desde_gravar = 0
                            if simbolo == 'grava':
                                print(f'gravado {saida}: {len(rotulo)} revisados', flush=True)
                        if sair:
                            break
            except KeyboardInterrupt:
                print('\nCtrl+C: gravando e saindo', flush=True)
    finally:
        if tela is not None:
            tela.fechar()
    return rotulo


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pasta', required=True, help='pasta com os quadroNNN.png e o estado.csv')
    ap.add_argument('--saida', help='CSV de saida (padrao PASTA/rotulos.csv)')
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument('--so-sugestao', action='store_true',
                      help='grava a sugestao do estado.csv sem abrir janela')
    modo.add_argument('--sem-janela', action='store_true',
                      help='revisao so pelo terminal, sem imshow (se o WSLg falhar)')
    a = ap.parse_args()

    saida = pathlib.Path(a.saida) if a.saida else pathlib.Path(a.pasta) / 'rotulos.csv'
    estado, ausentes = ler_estado(a.pasta)
    if not estado:
        sys.exit(f'nenhum PNG do estado.csv existe em {a.pasta}')
    if ausentes:
        print(f'aviso: {ausentes} linhas do estado.csv sem PNG na pasta -- puladas')
    rotulo = ler_rotulos_existentes(saida)
    if rotulo:
        print(f'continuando {saida}: {len(rotulo)} quadros ja revisados')
    if not a.so_sugestao:
        rotulo = revisar(a.pasta, estado, rotulo, saida, sem_janela=a.sem_janela)
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
