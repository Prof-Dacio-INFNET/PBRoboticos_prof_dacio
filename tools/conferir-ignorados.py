#!/usr/bin/env python3
"""Acusa arquivo de material que o .gitignore esta engolindo.

    python3 tools/conferir-ignorados.py

Em 15/11/2026 o `exemplos/aula18-ppo/amostra/modelo_ppo.zip` passou em todos os
testes locais e nao foi para o repositorio: a regra `*.zip` do .gitignore o
ignorou em silencio, e o exemplo quebrou no primeiro clone. Este conferidor
lista o que o git ignora dentro das pastas publicadas. Cache e saida de build
sao esperados; qualquer outra coisa e um arquivo que existe aqui e nao existe
para quem clona.
"""
import subprocess
import sys

PASTAS = ('exemplos', 'aulas', 'recursos', 'cheatsheets', 'tutoriais', 'tools')
ESPERADOS = ('__pycache__/', '.pyc', 'node_modules/', '.egg-info/',
             '/build/', '/install/', '/log/', '.pytest_cache/')


def main():
    saida = subprocess.run(
        ['git', 'status', '--ignored', '--porcelain', '--', *PASTAS],
        capture_output=True, text=True, check=True).stdout
    engolidos = []
    for linha in saida.splitlines():
        if not linha.startswith('!! '):
            continue
        caminho = linha[3:]
        if any(e in '/' + caminho for e in ESPERADOS):
            continue
        engolidos.append(caminho)
    if engolidos:
        print('ignorados FALHOU: o .gitignore esta engolindo material:')
        for c in engolidos:
            print('  ' + c)
        print('ou o arquivo nao devia existir (apague), ou precisa de uma '
              'excecao `!caminho` no .gitignore.')
        return 1
    print('ignorados ok: nada do material esta sendo ignorado pelo git')
    return 0


if __name__ == '__main__':
    sys.exit(main())
