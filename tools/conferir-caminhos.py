#!/usr/bin/env python3
"""Confere convenções de caminho e de instalação no material publicado.

Existe porque o mesmo erro apareceu duas vezes: `~/ros2_ws` no lugar de
`~/projeto-pb-SEU-USUARIO/ros2_ws`. Um erro que reincide não se corrige
relendo com mais cuidado — se corrige com uma verificação que falha sozinha.

Por que o caminho importa: o workspace do aluno mora DENTRO do repositório do
projeto dele. Um comando que manda copiar para `~/ros2_ws` põe o pacote fora do
repositório, e o aluno descobre isso no dia da entrega, quando o avaliador
clona e não acha o pacote.

As regras de instalação (`sudo uv`, `--system`, `pip` no python do sistema) só
valem DENTRO de bloco de código, porque o material discute essas armadilhas em
prosa de propósito — dizer "nunca faça X" não pode disparar o conferidor.

Uso:
    python3 tools/conferir-caminhos.py
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
IGNORAR = {'docs', 'site', '.git', '__pycache__', '.github'}
EXTENSOES = {'.md', '.py', '.sh', '.yaml', '.yml', '.txt'}

# Valem em qualquer lugar: prosa, comentário ou comando.
REGRAS_SEMPRE = [
    (re.compile(r'~/ros2_ws'),
     'workspace fora do repositório do projeto; use ~/projeto-pb-SEU-USUARIO/ros2_ws'),
    (re.compile(r'~/projeto-pb-(?!SEU-USUARIO\b)[A-Za-z0-9._-]+'),
     'caminho com usuário real no material do aluno; use SEU-USUARIO'),
]

# Valem só dentro de bloco de código, e nunca em linha de comentário.
REGRAS_COMANDO = [
    (re.compile(r'\bsudo\s+uv\b'),
     'sudo uv é proibido pela regra da disciplina'),
    (re.compile(r'\buv\s+pip\s+install\b.*--system'),
     'uv --system é proibido pela regra da disciplina; use um venv'),
    (re.compile(r'\bsudo\s+pip\b'),
     'pip como root; use apt'),
]

EXCECAO_COMANDO = re.compile(r'--break-system-packages|venv|virtualenv|requirements', re.I)
COMENTARIO = re.compile(r'^\s*#')


def linhas_com_contexto(p: pathlib.Path):
    """Devolve (n, linha, em_bloco_de_codigo)."""
    try:
        linhas = p.read_text(encoding='utf-8').splitlines()
    except UnicodeDecodeError:
        return
    # Em .md, bloco é entre cercas ```; em .py/.sh o arquivo inteiro é código,
    # exceto as docstrings -- que são prosa, e onde o material explica as
    # armadilhas de instalação pelo nome.
    cercado = p.suffix == '.md'
    dentro = not cercado
    em_docstring = False
    for n, linha in enumerate(linhas, 1):
        if cercado:
            if linha.lstrip().startswith('```'):
                dentro = not dentro
                continue
            yield n, linha, dentro
            continue

        aspas = linha.count('"""') + linha.count("'''")
        era_docstring = em_docstring
        if aspas % 2 == 1:
            em_docstring = not em_docstring
        # Linha de abertura/fechamento também é prosa.
        yield n, linha, not (em_docstring or era_docstring)


FECHO = re.compile(r'^\s*```')
ATIVA_VENV = re.compile(r'(^|\s)\.\s+\S*venv\S*/bin/activate|source\s+\S*venv\S*/bin/activate')
UV_ALVO = re.compile(r'uv\s+pip\s+install\b[^\n]*--python\s+\S*venv\S*')
VENV_STDLIB = re.compile(r'python3?(\.\d+)?\s+-m\s+venv\b')
PIP_INSTALL = re.compile(r'(?<!uv )\bpip\s+install\b')


def blocos_de_codigo(texto: str):
    """Devolve [(primeira_linha, [linhas])] de cada bloco cercado por ```."""
    saida, atual, inicio = [], None, 0
    for n, linha in enumerate(texto.split('\n'), 1):
        if FECHO.match(linha):
            if atual is None:
                atual, inicio = [], n + 1
            else:
                saida.append((inicio, atual))
                atual = None
            continue
        if atual is not None:
            atual.append(linha)
    return saida


def conferir_venv(p: pathlib.Path, texto: str, achados: list):
    """Duas regras que so' fazem sentido vendo o BLOCO inteiro.

    A primeira: `pip install` sem venv ativo cai em --user e reescreve o numpy,
    o OpenCV e o setuptools que o ROS 2 usa. Os sintomas nao apontam para a
    causa -- colcon com `--uninstall not recognized`, cv_bridge com
    `_ARRAY_API not found` -- e o cheatsheet de OpenCV ja descreve o estrago.
    A forma do uv que nao tem esse risco e' `uv pip install --python
    <venv>/bin/python`: ela diz onde instalar, entao nao existe "esqueci de
    ativar".

    A segunda: `python -m venv` nao e' a ferramenta da disciplina. Ele depende
    do ensurepip (pacote python3.10-venv), falha calado quando ele falta, e ai
    a saida facil e' rodar o pip solto -- que e' exatamente a primeira regra.
    O `uv venv` cria o ambiente sem ensurepip e nao tem esse modo de falha.
    """
    for inicio, linhas in blocos_de_codigo(texto):
        corpo = '\n'.join(linhas)
        tem_pip = any(PIP_INSTALL.search(l) and not COMENTARIO.match(l)
                      and '--break-system-packages' not in l for l in linhas)
        if tem_pip and not (ATIVA_VENV.search(corpo) or UV_ALVO.search(corpo)):
            achados.append((p, inicio, 'pip install em bloco sem venv ativo: cai em --user e '
                            'reescreve numpy/OpenCV/setuptools do ROS 2 (use uv pip install '
                            '--python <venv>/bin/python)', corpo.strip()[:88]))
        if VENV_STDLIB.search(corpo):
            achados.append((p, inicio, 'a disciplina gerencia ambiente com uv: troque '
                            '`python3 -m venv` por `uv venv --system-site-packages`',
                            corpo.strip()[:88]))


def main() -> int:
    eu = pathlib.Path(__file__).resolve()
    achados = []

    for p in RAIZ.rglob('*'):
        if p.is_dir() or p.suffix not in EXTENSOES:
            continue
        if any(parte in IGNORAR for parte in p.parts) or p.resolve() == eu:
            continue

        if p.suffix == '.md':
            conferir_venv(p.relative_to(RAIZ), p.read_text(encoding='utf-8'), achados)

        for n, linha, em_codigo in linhas_com_contexto(p):
            for padrao, porque in REGRAS_SEMPRE:
                if padrao.search(linha):
                    achados.append((p.relative_to(RAIZ), n, porque, linha.strip()[:88]))
            if em_codigo and not COMENTARIO.match(linha) and not EXCECAO_COMANDO.search(linha):
                for padrao, porque in REGRAS_COMANDO:
                    if padrao.search(linha):
                        achados.append((p.relative_to(RAIZ), n, porque, linha.strip()[:88]))

    if achados:
        print(f'{len(achados)} problema(s) de convenção:')
        for arq, n, porque, linha in achados:
            print(f'  {arq}:{n}  {porque}')
            print(f'      {linha}')
        return 1

    print('caminhos ok: nenhuma violação de convenção')
    return 0


if __name__ == '__main__':
    sys.exit(main())
