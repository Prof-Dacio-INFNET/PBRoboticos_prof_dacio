---
titulo: "Desafio 2 — visão robusta"
aula: 3
etapa: 2
nota: false
prazo: null
dificuldade: "média"
---

# Desafio 2 — visão robusta

**Opcional · sem nota · sem prazo · publicado com a Aula 3**

A [tarefa da semana](../../tutoriais/tarefa-aula03-visao.md) pede um pipeline que funciona. Este desafio pede um pipeline que **continua funcionando quando o mundo não colabora** — que é a única coisa que distingue visão computacional de demonstração de visão computacional.

Se você fizer só a tarefa, o TP1 sai. Se fizer este desafio também, o TP1 sai com o parágrafo de análise que costuma separar DL de DML na rubrica, porque você terá números para falar de robustez em vez de adjetivos.

## O que fazer

Quatro provocações, em ordem crescente de interesse. Faça as que couberem no seu tempo — parar na segunda é perfeitamente legítimo.

### 1. Duas classes, uma métrica

Detecte **duas classes** ao mesmo tempo e publique a contagem de cada uma. Depois monte uma pequena tabela de acerto: pegue vinte quadros, anote a contagem verdadeira olhando para a imagem, compare com o que o sistema disse, e calcule quantos por cento bateram.

Vinte quadros anotados à mão parece pouco e é o suficiente para o número deixar de ser opinião. É também a primeira vez em que você vai perceber que "está funcionando bem" e "acerta 70%" podem ser a mesma frase.

### 2. Quebre a iluminação de propósito

Rode o mesmo pipeline, sem mudar um parâmetro sequer, em três condições: luz normal, luz fraca (apague metade das lâmpadas ou feche a cortina) e contraluz (objeto entre você e a janela). Registre a taxa de acerto em cada uma.

O resultado esperado é que o contraluz destrua a sua segmentação. Bom. A pergunta que vale é **qual canal falhou** — foi o V que despencou, foi o S, foi o H que deslizou? Meça com o amostrador de HSV em cada condição e escreva a resposta. Quem sabe qual canal falha sabe qual limiar afrouxar.

### 3. Sobreviva à oclusão

Faça um objeto passar parcialmente na frente do outro e observe a contagem cair. Agora tente **não deixar cair**, escolhendo uma destas defesas:

| Defesa | Como | Custo |
|---|---|---|
| área máxima | dois objetos fundidos viram um contorno grande demais — descarte ou marque como "fusão" | trivial, resolve pouco |
| razão de aspecto | um contorno muito mais largo que alto provavelmente são dois | trivial, funciona em casos limpos |
| memória entre quadros | se contava 2 e agora conta 1 sem ninguém sair de cena, mantenha 2 por N quadros | médio, é o embrião do tracking do TP2 |
| `watershed` | separa contornos fundidos por transformada de distância | alto, mas é a resposta "certa" |

Não existe resposta única. Existe a resposta que você **justifica** — e a justificativa importa mais do que o resultado, porque é ela que vai para o relatório.

### 4. Meça o custo do que você acrescentou

Compare a taxa de saída (`ros2 topic hz /vision/contagem`) antes e depois das suas melhorias. Robustez quase sempre custa quadros por segundo. Saber **quanto** custou é o tipo de dado que ninguém traz e todo avaliador nota.

## O que isso vira depois

| Aqui você faz | Aparece de novo em |
|---|---|
| duas classes + métrica de acerto | TP1 item 4, e a análise do relatório |
| falha por iluminação diagnosticada por canal | TP2, quando o detector por aparência precisar de dados variados |
| memória entre quadros | TP2, tracking com métrica (gate G2.4) |
| custo em Hz do processamento | TP3 em diante, quando SLAM e navegação disputarem CPU com a visão |

## Como entregar, se quiser

Comente no Infnet.Online com o link do commit. Não há nota nem prazo, e o retorno costuma ser mais direto do que o de um TP justamente porque o escopo é pequeno.

Se for entregar, deixe em `docs/evidencias/aula03/desafio2.md` a tabela das três condições de iluminação e um parágrafo com a defesa de oclusão que você escolheu e por quê. Duas páginas no máximo — a graça está na medida, não na prosa.

!!! note "Prioridade"
    Ambiente de pé, [tarefa da semana](../../tutoriais/tarefa-aula03-visao.md), projeto declarado (gate **G1.1**, vence em 11/08) — nessa ordem, e só então o desafio. Um desafio feito com o ambiente meio funcionando produz mais frustração do que aprendizado.
