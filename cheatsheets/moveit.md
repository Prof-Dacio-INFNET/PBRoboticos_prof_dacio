# MoveIt 2 — manipulação 3D (TP5)

O item 1 do TP5 pede **≥3 poses destino evitando colisões**, com Collision Object, `ros2_control` e cinemática inversa no RViz2 (gate G5.1). O exemplo completo, com o que foi e o que não foi verificado, é o `exemplos/aula18-moveit`.

## Instalar (Humble, uma vez)

```bash
sudo apt update
sudo apt install -y ros-humble-moveit ros-humble-moveit-resources-panda-moveit-config \
  ros-humble-ros2-control ros-humble-ros2-controllers
```

São quatro porque o pacote do Panda **não** traz o `move_group` (as dependências estão comentadas no `package.xml` dele) e o MoveIt não traz os controladores.

## Subir o Panda de demonstração

```bash
# ── um terminal novo ──
source /opt/ros/humble/setup.bash
ros2 launch moveit_resources_panda_moveit_config demo.launch.py
```

Sobe `move_group`, RViz2 e `ros2_control` com hardware falso (`mock_components`). Pronto quando o terminal diz `You can start planning now!`.

## Os nomes do Panda (SRDF/URDF do Humble)

| O quê | Nome |
|---|---|
| grupo do braço | `panda_arm` (cadeia `panda_link0` → `panda_link8`) |
| grupo da garra | `hand` |
| efetuador / quadro base | `panda_link8` / `panda_link0` |
| estados nomeados | `ready`, `extended`, `transport` (braço); `open`, `close` (garra) |
| controladores | `panda_arm_controller`, `panda_hand_controller`, `joint_state_broadcaster` |

## As interfaces do `move_group` (o que um nó seu chama)

| Nome | Tipo | Para quê |
|---|---|---|
| `/move_action` | `moveit_msgs/action/MoveGroup` | planejar (`plan_only: true`) ou planejar e executar |
| `/execute_trajectory` | `moveit_msgs/action/ExecuteTrajectory` | executar um plano pronto |
| `/apply_planning_scene` | `moveit_msgs/srv/ApplyPlanningScene` | pôr/tirar objetos de colisão, com resposta |
| `/panda_hand_controller/gripper_cmd` | `control_msgs/action/GripperCommand` | abrir e fechar a garra |

## Diagnóstico rápido

```bash
# ── outro terminal, com o demo no ar ──
source /opt/ros/humble/setup.bash
ros2 action list | grep -E "move_action|execute_trajectory|gripper_cmd"
ros2 control list_controllers
ros2 run tf2_ros tf2_echo panda_link0 panda_link8
```

A última linha dá a pose atual do efetuador: arraste o marcador no RViz2, clique *Plan & Execute*, e copie a pose — é uma pose válida por construção.

## Conceitos em uma linha

- **Planning group**: o conjunto de juntas que se planeja junto (`panda_arm`).
- **IK**: pose da ponta → ângulos das juntas. Você pede pose; o MoveIt resolve a IK dentro do planejamento.
- **OMPL**: planejador por sorteio — duas execuções iguais dão trajetórias diferentes.
- **Collision Object**: objeto **declarado** na cena; o MoveIt não enxerga, desvia do que foi declarado.
- **Plan × execute**: calcular a trajetória × mandá-la ao controlador do `ros2_control`.
- **Código de erro**: `MoveItErrorCodes.val` — `1` é `SUCCESS`; pose dentro de obstáculo costuma vir como `GOAL_STATE_INVALID (-27)` ou `TIMED_OUT (-6)`, não `NO_IK_SOLUTION`.

## Configurar o SEU braço (opcional, custa 1–2 dias)

```bash
# ── um terminal novo ──
source /opt/ros/humble/setup.bash
ros2 launch moveit_setup_assistant setup_assistant.launch.py
```

Gera o `*_moveit_config` com `demo.launch.py` próprio. O exemplo da Aula 18 explica quando vale a pena e quando o Panda basta.
