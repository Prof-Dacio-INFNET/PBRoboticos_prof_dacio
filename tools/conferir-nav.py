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

    print(f"nav ok: {len(alvos)} páginas conferidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
