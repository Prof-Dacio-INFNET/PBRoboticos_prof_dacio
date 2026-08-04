# Tutoriais

Guias passo a passo da disciplina. Dois tipos convivem aqui: os **guias de ambiente**, que você segue uma vez e volta a consultar quando algo quebra, e as **tarefas semanais**, que acompanham cada aula e vão virando pedaços do seu TP.

Todos os guias de setup **validam os pré-requisitos antes de instalar** e fixam as versões alvo. Isso é deliberado: a maior parte dos problemas de ambiente nesta disciplina vem de instalar a coisa certa na versão errada, e o erro só aparece três passos depois.

## Ambiente

| Guia | Quando usar |
|---|---|
| [Ambiente: ROS 2 Humble no WSL2](setup-ros2-humble-wsl2.md) | primeira instalação, e sempre que precisar refazer |
| [Workspace e colcon](workspace-colcon.md) | criar pacotes, compilar, entender `source install/setup.bash` |
| [Renomear um pacote ROS 2](renomear-pacote-ros2.md) | adotar um exemplo da aula como seu — os 4 lugares do nome, o `setup.cfg` e o erro de `libexec` |
| [Câmera USB no WSL2 (usbipd)](camera-wsl2-usbipd.md) | passar a webcam do Windows para o Linux (Etapa 2 em diante) |

## Processo e entregas

| Guia | Quando usar |
|---|---|
| [Manual do aluno: GitHub e entregas](manual-do-aluno-github.md) | aceitar o assignment, branches, tags, o que entregar onde |
| [Uso de IA na disciplina](orientacao-uso-ia.md) | antes de usar qualquer assistente — as regras de declaração |

## Tarefas semanais

| Tarefa | Aula | Vira o quê no TP |
|---|---|---|
| [Primeiros nós — tópicos e serviços](tarefa-aula02-primeiros-nos.md) | Aula 2 | estrutura de pacote e o serviço do TP1 |
| [Pipeline de visão](tarefa-aula03-visao.md) | Aula 3 | itens 3 e 4 do TP1 |

## Uma regra que economiza horas

Sempre que um comando falhar, leia a mensagem **inteira** antes de procurar solução — em ROS 2 a linha útil raramente é a última. E antes de pedir ajuda, tenha em mãos: o comando exato que você rodou, a saída completa do erro, o que você já tentou e o resultado de `lsb_release -a`. Pergunta com diagnóstico costuma ser resolvida em minutos; "não está funcionando" leva a semana.
