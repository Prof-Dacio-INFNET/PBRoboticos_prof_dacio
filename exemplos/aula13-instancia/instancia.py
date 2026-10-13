"""Reexporta os detectores do pacote ROS 2. UMA implementacao, dois usos.

O algoritmo mora em `aula13_instancia/aula13_instancia/instancia.py`, dentro do
pacote -- e tem de morar la, porque depois do `colcon build` o no ROS 2 so
enxerga o que esta dentro do pacote. Este arquivo e a ponta de fora: deixa o
`avaliar.py` e o `testar.py` rodarem sem ROS 2 nenhum, importando o mesmo
codigo que o no importa.

Nao e elegancia, e seguranca: se o offline e o no tivessem cada um a sua copia,
elas iam divergir num detalhe de limiar por volta da terceira semana, e a
medida da aula deixaria de valer para o no sem ninguem perceber. A regua tem de
medir o que vai rodar.

    from instancia import DETECTORES, detectar, CONFIG_PADRAO
"""
import os
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent


def _achar_pacote():
    """Acha o pacote aula13_instancia em qualquer das posicoes plausiveis.

    O aluno pode estar rodando de dentro do material, da raiz do workspace, ou
    com o workspace sourceado. Se nao achar, diga o que faltou: um ImportError
    de tres linhas nao ensina nada a ninguem (a licao e a mesma do
    comparar_mapas.py da Aula 12).
    """
    candidatos = [AQUI / 'aula13_instancia',            # dentro do material
                  AQUI / 'src' / 'aula13_instancia']    # raiz do workspace
    if os.environ.get('PB_WS'):
        candidatos.append(pathlib.Path(os.environ['PB_WS']) / 'src' / 'aula13_instancia')
    for c in candidatos:
        if (c / 'aula13_instancia' / 'instancia.py').is_file():
            sys.path.insert(0, str(c))
            return str(c)
    try:
        import aula13_instancia.instancia                            # noqa: F401
        return 'pacote aula13_instancia instalado (workspace sourceado)'
    except ImportError:
        sys.exit(
            'nao achei o pacote aula13_instancia, que e onde o algoritmo mora.\n'
            'Tres saidas:\n'
            '  1) rode daqui de dentro do material, onde aula13_instancia/ fica ao lado;\n'
            '  2) copie aula13_instancia/ para a raiz do seu workspace (src/);\n'
            '  3) ou sourceie o workspace:  source "$PB_WS/install/setup.bash"')


ONDE_PACOTE = _achar_pacote()

from aula13_instancia.instancia import (                             # noqa: E402
    CLASSES_PADRAO, CONFIG_PADRAO, DETECTORES, INSTRUCAO_MODELO, PALETA,
    ModeloIndisponivel, cor_conectada, cor_watershed, detectar,
    instancia_de_mascara, mascara_classe, modelo, modelo_disponivel, opcao,
    pintar_instancias)

__all__ = ['CLASSES_PADRAO', 'CONFIG_PADRAO', 'DETECTORES', 'INSTRUCAO_MODELO',
           'ONDE_PACOTE', 'PALETA', 'ModeloIndisponivel', 'cor_conectada',
           'cor_watershed', 'detectar', 'instancia_de_mascara',
           'mascara_classe', 'modelo', 'modelo_disponivel', 'opcao',
           'pintar_instancias']
