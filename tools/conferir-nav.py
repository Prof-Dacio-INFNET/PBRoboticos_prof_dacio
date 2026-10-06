#!/usr/bin/env python3
"""Confere que todo item do nav: do mkdocs.yml existe em docs/.

O MkDocs apenas avisa quando o nav aponta para uma página inexistente; o build
segue e o item some do menu silenciosamente. Aqui isso é erro: publicar um menu
com buraco é pior do que não publicar.

Uso:
    python3 tools/conferir-nav.py
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def conferir_home() -> list[str]:
    """A home destaca a mesma aula que a tabela marca como proxima?

    Existe porque a secao "Aula mais recente" do INICIO.md e' escrita a mao e
    ficou tres aulas para tras sem ninguem notar -- ela continuava anunciando a
    Aula 9 quando a 12 ja estava publicada. Coisa que precisa ser lembrada a
    cada semana nao se corrige lembrando melhor.
    """
    erros = []
    inicio = (RAIZ / 'INICIO.md').read_text(encoding='utf-8')
    tabela = (RAIZ / 'aulas' / 'README.md').read_text(encoding='utf-8')

    # A aula marcada como proxima na tabela de aulas.
    m = re.search(r'\[Aula (\d+)\]\((etapa\d+-aula\d+)/index\.md\)[^\n]*pb-tag next', tabela)
    if not m:
        return ['aulas/README.md: nenhuma aula marcada com pb-tag next']
    numero, pasta = m.group(1), m.group(2)

    secao = inicio.split('## Aula mais recente', 1)
    if len(secao) < 2:
        return ['INICIO.md: nao achei a secao "Aula mais recente"']
    secao = secao[1].split('\n## ', 1)[0]

    if f'aulas/{pasta}/index.md' not in secao:
        erros.append(f'INICIO.md destaca uma aula diferente da marcada como proxima '
                     f'(esperado aulas/{pasta}/index.md, da Aula {numero})')
    if not re.search(rf'\*\*Aula {numero} ', secao):
        erros.append(f'INICIO.md: o titulo da secao nao diz "Aula {numero}"')
    return erros


def main() -> int:
    cfg = (RAIZ / "mkdocs.yml").read_text(encoding="utf-8")
    if "\nnav:" not in cfg:
        print("ERRO: mkdocs.yml não tem seção nav:.")
        return 1
    nav = cfg.split("\nnav:", 1)[1]
    alvos = re.findall(r"([\w./-]+\.md)\s*$", nav, flags=re.M)

    docs = RAIZ / "docs"
    faltando = [a for a in alvos if not (docs / a).exists()]
    if faltando:
        print("Páginas do nav que NÃO existem em docs/:")
        for a in faltando:
            print("  -", a)
        return 1

    # O caminho inverso: páginas montadas que ninguém alcança pelo menu.
    # Não é erro (a busca continua encontrando), mas é quase sempre esquecimento.
    no_nav = set(alvos)
    orfas = sorted(
        str(p.relative_to(docs))
        for p in docs.rglob("*.md")
        if str(p.relative_to(docs)) not in no_nav
    )
    if orfas:
        print(f"aviso: {len(orfas)} página(s) fora do nav (existem no site, não aparecem no menu):")
        for a in orfas:
            print("  -", a)

    problemas = conferir_home()
    if problemas:
        print('Home desalinhada da tabela de aulas:')
        for x in problemas:
            print('  ', x)
        return 1

    print(f"nav ok: {len(alvos)} páginas conferidas; home alinhada com a tabela")
    return 0


if __name__ == "__main__":
    sys.exit(main())
