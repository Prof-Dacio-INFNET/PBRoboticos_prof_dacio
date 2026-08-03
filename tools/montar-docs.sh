#!/usr/bin/env bash
# Monta a pasta docs/ a partir da estrutura real do repositório.
#
# A pasta docs/ é DESCARTÁVEL e não é versionada: existe só como entrada do
# MkDocs. Montá-la a cada build é o que impede que o material tenha duas
# versões — "a que se lê no GitHub" e "a que se lê no site".
#
# Este script é o mesmo em CI e na máquina do professor, de propósito: quando a
# montagem local diverge da montagem do workflow, o defeito só aparece depois
# de publicado. Foi exatamente assim que o CSS da identidade visual sumiu do
# site sem que nenhum build local reclamasse.
#
# Uso:
#   ./tools/montar-docs.sh          # monta docs/
#   mkdocs build --strict           # e então valide
set -euo pipefail

cd "$(dirname "$0")/.."

# Pastas de conteúdo: cada uma vira uma seção do menu.
SECOES=(aulas tutoriais recursos exemplos cheatsheets)

rm -rf docs && mkdir -p docs

# Página inicial: INICIO.md se existir, senão o README do repositório.
if [ -f INICIO.md ]; then
  cp INICIO.md docs/index.md
else
  cp README.md docs/index.md
fi
if [ -f LICENSE.md ]; then cp LICENSE.md docs/licenca.md; fi

# assets/ NÃO é seção de conteúdo: é a identidade visual (CSS da paleta).
# Copiada depois da poda de pastas vazias — ver comentário mais abaixo.
for d in "${SECOES[@]}"; do
  if [ -d "$d" ]; then cp -r "$d" "docs/$d"; fi
done

# README.md de cada pasta vira a página de abertura da seção.
find docs -mindepth 2 -name README.md -print0 |
  while IFS= read -r -d '' f; do mv "$f" "$(dirname "$f")/index.md"; done

# Arquivos de controle que não devem ir para o site.
find docs -name '.gitkeep' -delete
find docs -name '__pycache__' -type d -prune -exec rm -rf {} +

# Remove pastas de CONTEÚDO que não contêm nenhuma página (evita seção vazia
# no menu). Restrito às seções: uma varredura em docs/ inteiro apagaria
# docs/assets/, que legitimamente não tem nenhum .md.
for s in "${SECOES[@]}"; do
  [ -d "docs/$s" ] || continue
  for d in $(find "docs/$s" -mindepth 1 -type d | sort -r); do
    if [ -z "$(find "$d" -name '*.md' -print -quit)" ]; then rm -rf "$d"; fi
  done
  if [ -z "$(find "docs/$s" -name '*.md' -print -quit)" ]; then rm -rf "docs/$s"; fi
done

# Só agora a identidade visual, a salvo da poda.
if [ -d assets ]; then cp -r assets docs/assets; fi

# Pré-condição: sem este arquivo o site publica na paleta padrão do Material
# (índigo) em vez da paleta da disciplina, e nada no build reclama.
if [ ! -f docs/assets/extra.css ]; then
  echo "ERRO: docs/assets/extra.css não foi montado — o site sairia sem a identidade visual." >&2
  exit 1
fi

echo "--- paginas publicadas ---"
find docs -name '*.md' | sort
echo "--- assets ---"
find docs/assets -type f | sort
