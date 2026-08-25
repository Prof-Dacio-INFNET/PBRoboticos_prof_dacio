---
titulo: "Checklist de entrega do TP1"
tipo: entrega
etapa: 2
prazo: "sexta, 28/08/2026"
---

# Checklist de entrega do TP1

**Prazo: sexta, 28/08/2026.** A entrega **oficial e formal** é no **Moodle** — ZIP dos códigos, PDF do relatório e os links. É ela que gera registro acadêmico, e sem ela não há nota. O **GitHub é complementar e obrigatório**, e é critério de avaliação: é onde o processo fica visível.

Faça este checklist **de cima para baixo, num dia em que ainda dá tempo de consertar**. Cada item tem um comando que responde sim ou não.

## 1. O repositório está no estado certo

```bash
cd ~/projeto-pb-SEU-USUARIO
git status                       # tem que estar limpo
git log --oneline -10            # um commit por gate, mensagens começando pelo código
```

Se o `git status` mostrar arquivo modificado, decida: entra na entrega ou não entra. Arquivo não commitado **não existe** para quem avalia.

## 2. As evidências estão commitadas

```bash
ls docs/evidencias/tp1/
```

O TP1 pede cinco: `check-ambiente.txt` (G1.0), `topic-hz.txt` (G1.2), `segmentacao.png` (G1.3), `rqt_graph.png` (G1.4) e o `relatorio-tp1.md` fechado (G1.5). Evidência que ficou só no seu terminal não conta — o terminal fecha.

## 3. O `PROJETO.md` reflete a verdade

Todo gate marcado com `[x]`, `[ ]` ou `[!]`. Um `[!]` declarado é honestidade e custa pouco; um gate marcado `[x]` sem evidência é o contrário, e é fácil de verificar.

## 4. Branch e tag

```bash
git checkout main
git pull
git checkout -b entrega-tp1
git push -u origin entrega-tp1

git tag -a tp1 -m "Entrega do TP1"
git push origin tp1

git tag --list                   # tem que listar tp1
```

A tag **congela** o código avaliado. Commit depois da tag não é considerado, e é isso que protege você: o que veio depois não conta contra.

## 5. O ZIP e o PDF

O ZIP é do **código**, não do repositório inteiro: sem `build/`, sem `install/`, sem `log/`, sem `.git/`.

```bash
cd ~/projeto-pb-SEU-USUARIO
zip -r tp1-SEUNOME.zip . -x "*/build/*" "*/install/*" "*/log/*" ".git/*" "*.pyc" "*__pycache__*"
unzip -l tp1-SEUNOME.zip | tail -5      # confira o tamanho e o que entrou
```

O PDF é o `docs/relatorio-tp1.md` exportado. Confira que as imagens apareceram no PDF — referência quebrada no Markdown vira espaço em branco no PDF, e o avaliador não vê o que você viu.

## 6. Arquivos grandes vão por link, nunca no Git

Vídeo, dataset, bag e peso de modelo **não** entram no repositório. Publique em link acessível — YouTube **público ou não-listado, nunca privado** — e ponha o link no relatório e no README.

## 7. A conferência que separa entrega boa de entrega perdida

Abra uma **janela anônima** e teste, um por um: a página do repositório no GitHub, cada link do relatório, o vídeo, o ZIP baixado do Moodle.

**Se o avaliador não consegue abrir, não existe.** Repositório privado, link do Drive restrito, vídeo privado no YouTube — os três já custaram nota a alguém, e nenhum deles dá erro na sua máquina, porque você está logado.

## 8. Postar no Moodle

ZIP + PDF + link do repositório + link do vídeo, se houver. Confira que o envio foi **concluído** e não ficou em rascunho.

---

## Escada de recuperação, se algo não vai dar tempo

Não entregue nada é sempre a pior opção, e não é a única. Nesta ordem:

1. **Entregue o que funciona e declare o que não funciona.** Uma limitação escrita na seção "limitações conhecidas" vale muito mais do que a mesma falha descoberta pelo avaliador.
2. **Substitua o item pelo plano B declarado no G1.1.** É para isso que o plano B existe, e usá-lo não é derrota — é o comportamento que o projeto previu.
3. **Entregue com o gate marcado `[!]` e um parágrafo dizendo o que faltou e por quê.** Um `[!]` explicado mostra controle do próprio projeto.

O que não funciona é entregar em silêncio esperando que ninguém rode o comando. Alguém roda.
