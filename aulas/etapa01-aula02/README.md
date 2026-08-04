# Aula 2 — Primeiros nós: tópicos e serviços

**Terça, 28/07/2026 · sala SJ205 · Etapa 1**

[:material-file-pdf-box: Slides da Aula 2 (PDF)](apresentacao-aula02.pdf){ .md-button .md-button--primary }
[:material-code-tags: Exemplo `aula02-comunicacao`](../../exemplos/aula02-comunicacao/index.md){ .md-button }

## O que foi visto

Saímos do "rodar o exemplo dos outros" para o "escrever o meu". A aula construiu um pacote `ament_python` do zero, com um **publisher**, um **subscriber** e um **serviço**, e mostrou o papel de cada arquivo: `package.xml` declara dependências, `setup.py` registra os executáveis em `entry_points`, e o `launch` sobe tudo com um comando só.

A discussão central foi **quando usar tópico e quando usar serviço**. Fluxo contínuo, com muitos ouvintes possíveis e sem garantia de resposta, é tópico — é assim que a imagem da câmera vai viajar. Pergunta pontual que precisa de resposta é serviço — é assim que o `/vision/status` do TP1 vai funcionar. Tarefa longa, com progresso e cancelamento, é ação, e fica para o TP2.

## Exemplo da aula

O pacote [`aula02-comunicacao`](../../exemplos/aula02-comunicacao/index.md) tem os três nós e um launch. O serviço `/contagem` responde quantas mensagens passaram — é o embrião direto do `/vision/status`, e vale rodar `ros2 service call /contagem ...` para sentir a diferença entre perguntar e ouvir.

## Tarefa e desafio

- [Tarefa da Aula 2 — primeiros nós](../../tutoriais/tarefa-aula02-primeiros-nos.md)
- [Desafio 1 — comunicação](../../recursos/desafios/desafio-01-comunicacao.md) (opcional, sem nota, aquecimento para o TP1)

## Os três erros que apareceram mais

O campeão absoluto é **"package not found" depois do build**: faltou `source install/setup.bash` *naquele* terminal. Cada aba nova precisa do source, e isso não muda nunca — vale colocar no `~/.bashrc` o source do ROS, mas o do workspace é melhor manter manual, para você lembrar de qual workspace está usando.

O segundo é **editar Python e nada mudar**: sem `--symlink-install` no `colcon build`, o código instalado é uma cópia. Com a flag, é um link, e a edição vale na hora.

O terceiro é **renomear pacote pela metade**: o nome precisa bater em quatro lugares — `package.xml`, `setup.py`, `resource/<nome_do_pacote>` e `setup.cfg` —, e a edição é sempre em `src/`. O `setup.cfg` é o mais esquecido, e é ele que faz o `ros2 launch` reclamar de `libexec directory .../lib/<pacote> does not exist`. O passo a passo com a sequência de comandos está em [renomear um pacote ROS 2](../../tutoriais/renomear-pacote-ros2.md).
