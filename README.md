# PBRoboticos — Material da Disciplina · Prof. Dácio (INFNET 2026.2)

Repositório **público de material** do Projeto de Bloco: Sistemas Robóticos — consulta permanente dos alunos. Atualizado a cada aula: consulte pelo navegador ou clone e rode `git pull` semanalmente:

```bash
gh repo clone Prof-Dacio-INFNET/PBRoboticos_prof_dacio
```

## Estrutura

- `aulas/` — por aula: roteiro, PDF da apresentação e arquivos usados em sala (ex.: `etapa02-aula03/`)
- `tutoriais/` — guias de ambiente (WSL2 + ROS 2 Humble, workspace/colcon, câmera via usbipd), processo (GitHub e entregas, uso de IA) e as tarefas semanais
- `recursos/` — o que estrutura o projeto do semestre: catálogo de projetos, derivações e aplicações, simulação × hardware real, gates de cada TP, desafios opcionais e `check-ambiente.sh`
- `exemplos/` — pacotes ROS 2 prontos para rodar, por aula (`aula02-comunicacao`, `aula03-visao`) e por TP (`tp1…tp5`), sob licença MIT
- `cheatsheets/` — consulta rápida de comandos (ROS 2, colcon, git, OpenCV, Gazebo…)

## Regras de entrega (resumo — o oficial está no Moodle)

**A entrega oficial de todo TP é no MOODLE** (ZIP de códigos + PDF + links). O repositório individual `projeto-pb-<usuario>` é **complementar e obrigatório**: é nele que o desenvolvimento acontece, e a tag `tpN` é o que se corrige como código. Não é opcional nem dispensável — a organização do repositório, o histórico de commits e a rastreabilidade das decisões são critérios de avaliação em todos os TPs.

Arquivos grandes e vídeos vão por **link público ou não-listado** (nunca privado). A responsabilidade de acessibilidade é do aluno: se o avaliador não consegue abrir, não existe.

**Requisitos:** Ubuntu 22.04 (WSL2 ou nativo) + ROS 2 Humble + Python 3.10 — ver `tutoriais/`.

## Licença e citação

© 2026 Dácio Moreira de Souza. Material didático sob **CC BY-NC-ND 4.0** (citação obrigatória; proibidos uso comercial e distribuição modificada) — ver `LICENSE.md`. Códigos em `exemplos/` sob **MIT** (`exemplos/LICENSE`), reutilizáveis nos projetos dos alunos com manutenção do aviso de copyright.

## Onde consultar este material

- **GitHub (fonte):** https://github.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio
- **Site (GitHub Pages):** https://prof-dacio-infnet.github.io/PBRoboticos_prof_dacio/
- **Espelho + arquivos grandes:** https://daciosouza.com.br/PB_sistRoboticos/
