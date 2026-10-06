#!/usr/bin/env python3
"""Confere os blocos de comando do material do aluno.

Os comandos são o que mais falha: eles são copiados e colados por trinta pessoas
ao mesmo tempo, e um erro ali consome a aula inteira. Este conferidor roda três
verificações sobre cada bloco ```bash do material publicado.

  1. SINTAXE      — `bash -n`, com os marcadores <assim> trocados por um nome
                    válido antes (eles são para o aluno preencher, não para o
                    shell interpretar).
  2. VARIÁVEIS    — toda variável usada precisa ter sido definida antes, no
                    mesmo arquivo, lendo de cima para baixo — que é como o aluno
                    lê. É isto que garante a convenção PB_USER/PB_WS: a página
                    que manda usar "$PB_WS" tem de ter mandado defini-lo antes.
                    Depois de um `source`, nomes desconhecidos passam: eles
                    podem ter vindo do arquivo lido.
                    E um bloco que herda $PB_* de outro precisa da guarda
                    `: "${PB_WS:?...}"`: sem ela, variavel vazia vira caminho
                    absoluto e o erro nao diz o que faltou.
  3. CAMINHOS     — todo caminho do repositório citado num comando (exemplos/,
                    recursos/, tutoriais/) tem de existir de verdade.

Uso:
    python3 tools/conferir-comandos.py
"""
import pathlib
import re
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SECOES = ('aulas', 'exemplos', 'tutoriais', 'recursos', 'cheatsheets')

BLOCO = re.compile(r'^```(bash|sh|shell)\s*$(.*?)^```\s*$', re.M | re.S)
USO_VAR = re.compile(r'\$\{?([A-Z_][A-Z0-9_]*)\}?')
DEF_VAR = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=', re.M)
SOURCE = re.compile(r'^\s*(?:source|\.)\s+\S', re.M)
USO_PB = re.compile(r'\$\{?PB_[A-Z_]+')
DEF_PB = re.compile(r'^\s*(?:export\s+)?PB_[A-Z_]+=', re.M)
GUARDA_PB = re.compile(r':\s*"\$\{PB_[A-Z_]+:\?')
CAMINHO_REPO = re.compile(r'(?<![\w/.-])((?:' + '|'.join(SECOES) + r')/[A-Za-z0-9._/-]+)')
PLACEHOLDER = re.compile(r'<[^<>\s]{1,40}>')

# Variáveis que o ambiente fornece: usá-las sem definir é correto.
AMBIENTE = {
    'HOME', 'USER', 'PATH', 'PWD', 'SHELL', 'PYTHONPATH', 'LD_LIBRARY_PATH',
    'AMENT_PREFIX_PATH', 'ROS_DOMAIN_ID', 'ROS_DISTRO', 'DISPLAY',
    'LIBGL_ALWAYS_SOFTWARE', 'QT_QPA_PLATFORM', 'WSL_DISTRO_NAME',
    'HTTPS_PROXY', 'BASH_SOURCE', 'IFS', 'OSTYPE',
}

achados = []


def registrar(arq, n, porque, trecho=''):
    achados.append((arq, n, porque, trecho.strip()[:88]))


def linha_do_bloco(texto, pos):
    return texto[:pos].count('\n') + 1


def conferir_sintaxe(arq, n, corpo):
    limpo = PLACEHOLDER.sub('ALVO', corpo)
    with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False, encoding='utf-8') as fh:
        fh.write(limpo)
        caminho = fh.name
    r = subprocess.run(['bash', '-n', caminho], capture_output=True, text=True)
    pathlib.Path(caminho).unlink(missing_ok=True)
    if r.returncode != 0:
        msg = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'erro de sintaxe'
        registrar(arq, n, 'bash -n recusou o bloco', msg)


def conferir_variaveis(arq, n, corpo, definidas):
    # `source arquivo` traz nomes que não estão escritos no bloco. Depois de um
    # source, qualquer maiúscula pode ter vindo de lá, e cobrar definição no
    # texto seria falso positivo -- é o caso de /etc/os-release.
    # Linha a linha, na ordem em que o aluno digita: a definicao da linha de
    # cima vale para a de baixo. Conferir o bloco inteiro de uma vez -- como
    # esta funcao fazia antes -- acusava a propria linha que define.
    houve_source = False
    for linha in corpo.splitlines():
        if not houve_source:
            for m in USO_VAR.finditer(linha):
                nome = m.group(1)
                if nome in AMBIENTE or nome in definidas:
                    continue
                registrar(arq, n, f'usa ${nome} sem ter definido antes', linha)
        definidas.update(DEF_VAR.findall(linha))
        if SOURCE.match(linha):
            houve_source = True

    # Um bloco que USA as variaveis do projeto sem defini-las precisa da guarda
    # `: "${PB_WS:?...}"`. Sem ela, uma variavel vazia vira caminho absoluto --
    # "$PB_WS/install/setup.bash" virou "/install/setup.bash" --, e o erro nao
    # diz o que faltou. A guarda troca isso por uma mensagem que nomeia a causa.
    if USO_PB.search(corpo) and not DEF_PB.search(corpo) and not GUARDA_PB.search(corpo):
        registrar(arq, n, 'usa $PB_* herdado sem a guarda `: "${PB_WS:?...}"`',
                  next((l for l in corpo.splitlines() if USO_PB.search(l)), ''))


def conferir_caminhos(arq, n, corpo):
    for m in CAMINHO_REPO.finditer(corpo):
        alvo = m.group(1).rstrip('/.,')
        if any(c in alvo for c in '<>*$'):
            continue
        if not (RAIZ / alvo).exists():
            registrar(arq, n, f'cita um caminho do repositório que não existe: {alvo}')


def main() -> int:
    arquivos = sorted(
        p for s in SECOES for p in (RAIZ / s).rglob('*.md')
        if '__pycache__' not in p.parts
    )

    blocos = 0
    for p in arquivos:
        texto = p.read_text(encoding='utf-8')
        rel = p.relative_to(RAIZ)
        definidas: set[str] = set()
        for m in BLOCO.finditer(texto):
            corpo = m.group(2)
            n = linha_do_bloco(texto, m.start())
            blocos += 1
            conferir_sintaxe(rel, n, corpo)
            conferir_variaveis(rel, n, corpo, definidas)
            conferir_caminhos(rel, n, corpo)

    if achados:
        print(f'{len(achados)} problema(s) em {blocos} blocos de comando:')
        for arq, n, porque, trecho in achados:
            print(f'  {arq}:{n}  {porque}')
            if trecho:
                print(f'      {trecho}')
        return 1

    print(f'comandos ok: {blocos} blocos conferidos em {len(arquivos)} arquivos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
