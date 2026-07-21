# Catálogo de Projetos — PB Sistemas Robóticos 2026.2

Para o **TP1** você escolhe o projeto que vai desenvolver o semestre inteiro. **A escolha é livre com aprovação do professor** — este catálogo traz opções ponderadas para acelerar sua decisão e servir de régua para propostas próprias.

## O teste decisivo: o projeto sobrevive aos 5 TPs?

Seu projeto precisa comportar, em sequência: **TP1** ROS 2 básico + pipeline de visão · **TP2** interfaces customizadas + rastreamento (YOLO) + URDF · **TP3** launch + SLAM + segmentação · **TP4** Nav2 (navegação autônoma) + percepção veicular no MetaDrive + CNN · **TP5** MoveIt 2 + validação (Raspberry Pi OU drone PX4) + Behavioral Cloning/PID/PPO. Projeto que não tem *onde navegar* ou *o que perceber* quebra no meio — escolha com isso em mente. (O módulo veicular dos TPs 4–5 roda no MetaDrive para todos, independentemente do projeto.)

## Opções sugeridas

| # | Projeto | Percepção (TP1–3) | Navegação (TP3–4) | Dificuldade | Risco principal |
|---|---|---|---|---|---|
| 1 | **Robô de inspeção visual** — patrulha ambientes e detecta anomalias (objetos fora do lugar, "vazamentos", EPIs) | detecção/segmentação de anomalias | rota de patrulha Nav2 | ●●○ | definir "anomalia" detectável cedo |
| 2 | **Seguidor de alvo** — segue uma pessoa/objeto mantendo distância | rastreamento YOLO + estimativa de distância | seguimento reativo + Nav2 | ●●○ | oclusões e perda de alvo |
| 3 | **Sentinela de segurança** — vigia área, detecta intrusos e investiga | detecção de pessoas, faces | patrulha + ir-até-o-evento | ●●○ | parecido com 1 (diferencie o comportamento) |
| 4 | **Entregador indoor** — transporta itens entre pontos (escritório/hospital) | detecção de marcadores/objetos, semáforos de porta | navegação ponto-a-ponto forte | ●●○ | manipulação no TP5 (pick-and-place do item ajuda!) |
| 5 | **Inventário de prateleiras** — percorre corredores contando/classificando itens | detecção + classificação (CNN) intensas | corredores mapeados (SLAM) | ●●● | dataset próprio dá trabalho |
| 6 | **Assistente de estacionamento/condução** — foco veicular: faixas, vagas, sinais | visão veicular clássica + CNN (forte sinergia com TP4–5) | MetaDrive/highway como palco principal | ●●● | parte "robô físico/Gazebo" precisa existir também |
| 7 | **Drone de inspeção** — inspeção aérea de estruturas (opção B do TP5 nativa) | detecção em imagem aérea | waypoints 3D (PX4) | ●●●● | curva do PX4; simulação exigente |

Todos são viáveis; 1–4 são os caminhos mais seguros; 5–7 têm mais brilho e mais risco — combine com sua experiência.

## Proposta própria? Ótimo — passe neste checklist

1. Tem **o que perceber** (câmera obrigatória; classes de objetos definidas)? 2. Tem **onde navegar** (mapa/ambiente para SLAM e Nav2)? 3. Tem **tarefa de longa duração** para virar Action no TP2? 4. Sobrevive ao TP5 (algo para manipular OU validável em RPi/drone)? 5. Roda no seu hardware (simulação conta!)? 6. Você consegue demonstrar o caso de uso e "vender" o projeto (apresentação/vídeo)?

Aprovação: traga projeto + respostas do checklist na mentoria (bloco 3 da aula) ou Infnet.Online até a semana da leitura do TP1.

## O que entregar no TP1 sobre a escolha

`PROJETO.md` preenchido (objetivo, justificativa, funcionalidades, sensores, arquitetura prevista, **plano TP a TP**, riscos) — é a "escolha tecnicamente fundamentada" que o enunciado exige. Mudanças depois são bem-vindas **e registradas** em `docs/decisoes.md`.
