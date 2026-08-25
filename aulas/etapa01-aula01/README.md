# Aula 1 — Abertura, ROS 2 e o projeto do semestre

**Terça, 21/07/2026 · sala SJ205 · Etapa 1**

[:material-file-pdf-box: Slides da Aula 1 (PDF)](apresentacao-aula01.pdf){ .md-button .md-button--primary }

## Baixar o material desta aula

A Aula 1 não tem pacote para compilar — o material que importa é o script que confere o seu ambiente. Baixe e rode:

```bash
# baixar o material (pode repetir sempre)
rm -rf /tmp/PBRoboticos_prof_dacio
cd /tmp && git clone --depth 1 https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio.git

bash /tmp/PBRoboticos_prof_dacio/recursos/check-ambiente.sh
```

Ele detecta a sua rota (WSL2, VirtualBox ou nativo), confere Ubuntu, ROS 2, `colcon`, `git`, `gh`, `uv`, o `ROS_DOMAIN_ID` e a procedência do OpenCV e do NumPy. **Rode antes de pedir ajuda:** a saída dele é metade do diagnóstico.

## O que foi visto

A aula abriu o bloco apresentando o que é um sistema robótico do ponto de vista de software: um conjunto de processos independentes que trocam informação por uma rede, e não um programa monolítico. A partir daí veio o vocabulário do ROS 2 — nós, tópicos, serviços, ações e parâmetros — com a analogia da mensageria: o tópico é um canal em que qualquer um publica e qualquer um assina, o serviço é uma pergunta com resposta, e a ação é uma tarefa longa que informa progresso e pode ser cancelada.

Na parte prática rodamos `talker`/`listener`, o `turtlesim` com teleoperação, e usamos `rqt_graph` e `ros2 topic echo` para **ver** o grafo existindo enquanto a tartaruga se move. O efeito é proposital: o grafo deixa de ser diagrama de slide e passa a ser algo observável com comando de terminal.

A aula terminou apresentando a estrutura do semestre — cinco TPs que são cinco cortes do mesmo projeto — e o catálogo de projetos.

## Para fazer depois desta aula

Deixe o ambiente pronto: **Ubuntu 22.04 (jammy)**, ROS 2 Humble, git, `gh` e `uv`. Escolha **uma rota por máquina** — WSL2 é a padrão; VirtualBox é a rota das máquinas do laboratório e de quem não consegue WSL2; Ubuntu nativo também vale. O tutorial valida cada pré-requisito antes de instalar, e existe um motivo para insistir na versão: o `wsl --install` sem argumento instala uma versão de Ubuntu mais nova, e o `ros-humble-desktop` **não existe** fora do jammy. Se `lsb_release -a` não disser 22.04, pare e corrija antes de qualquer outra coisa.

- [Setup ROS 2 Humble no WSL2](../../tutoriais/setup-ros2-humble-wsl2.md) — rota padrão
- [Ambiente alternativo: ROS 2 Humble no VirtualBox](../../tutoriais/setup-ros2-humble-virtualbox.md) — laboratório, Windows Home, política corporativa
- [Manual do aluno: GitHub e entregas](../../tutoriais/manual-do-aluno-github.md)
- [Catálogo de projetos](../../recursos/catalogo-projetos.md) — comece a pensar no seu

## Duas regras que valem o semestre inteiro

O **`ROS_DOMAIN_ID` é o seu número de chamada**. Sem isso, na rede do laboratório todo mundo enxerga os nós de todo mundo, e você vai passar meia hora depurando um comportamento que é de outra pessoa.

O repositório mora **dentro do Linux**, na home (`~`) — nunca numa pasta que é do Windows por baixo: `/mnt/c/...` no WSL2, `/media/sf_<nome>` no VirtualBox. Clonar lá funciona e é lento a ponto de atrapalhar, além de gerar problemas de permissão e de fim de linha que aparecem só no `colcon build`.
