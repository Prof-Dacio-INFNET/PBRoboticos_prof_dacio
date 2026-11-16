"""O numero que o MoveIt devolve, virado em nome e em "o que olhar".

ADVERTENCIA: a tabela foi copiada da fonte do Humble e conferida pelo
testar.py contra ela; as DICAS sao leitura de codigo e experiencia. No ensaio
de 16/11 (WSL2, Humble, MoveIt 2.5.10) apareceram de verdade SUCCESS,
INVALID_MOTION_PLAN (1 vez) e START_STATE_INVALID; as outras nunca foram vistas.
Nenhuma dica e veredito: elas dizem onde olhar, nao o que esta errado.

Todo resultado do MoveIt carrega um `moveit_msgs/MoveItErrorCodes`, que e um
inteiro so (`val`). O numero sozinho nao ensina nada -- `-27` nao diz que a
pose estava dentro da caixa. Este modulo nao importa nada do ROS 2 de
proposito: ele roda no testar.py sem dubles, e voce pode importa-lo do seu
proprio no.

Fonte (branch humble, a mesma do apt `ros-humble-moveit-msgs` 2.2.3):
    https://github.com/moveit/moveit_msgs/blob/humble/msg/MoveItErrorCodes.msg

DE ONDE VEM CADA CODIGO, no caminho que este exemplo usa (acao /move_action,
planejador OMPL), lido em moveit2 branch humble:

    moveit_planners/ompl/ompl_interface/src/model_based_planning_context.cpp
        logPlannerStatus(): TIMEOUT -> TIMED_OUT, INVALID_GOAL ->
        GOAL_STATE_INVALID, INVALID_START -> START_STATE_INVALID, "solucao
        aproximada" -> PLANNING_FAILED.

    Repare no que NAO esta na lista: NO_IK_SOLUTION e GOAL_IN_COLLISION nao
    sao devolvidos por esse caminho. O OMPL resolve a IK por dentro, amostrando
    estados que satisfacam a pose; quando nenhum serve (pose fora do alcance OU
    dentro da caixa), ele diz "Invalid goal state" ou estoura o tempo. Por isso
    a pose dentro da caixa aparece aqui como GOAL_STATE_INVALID ou TIMED_OUT, e
    nao com o nome que voce esperaria. NO_IK_SOLUTION aparece no servico
    /compute_ik, que este exemplo nao usa.
"""

# Copiado de MoveItErrorCodes.msg, branch humble, na ordem do arquivo.
CODIGOS = {
    1: 'SUCCESS',
    99999: 'FAILURE',
    -1: 'PLANNING_FAILED',
    -2: 'INVALID_MOTION_PLAN',
    -3: 'MOTION_PLAN_INVALIDATED_BY_ENVIRONMENT_CHANGE',
    -4: 'CONTROL_FAILED',
    -5: 'UNABLE_TO_AQUIRE_SENSOR_DATA',
    -6: 'TIMED_OUT',
    -7: 'PREEMPTED',
    -10: 'START_STATE_IN_COLLISION',
    -11: 'START_STATE_VIOLATES_PATH_CONSTRAINTS',
    -26: 'START_STATE_INVALID',
    -12: 'GOAL_IN_COLLISION',
    -13: 'GOAL_VIOLATES_PATH_CONSTRAINTS',
    -14: 'GOAL_CONSTRAINTS_VIOLATED',
    -27: 'GOAL_STATE_INVALID',
    -28: 'UNRECOGNIZED_GOAL_TYPE',
    -15: 'INVALID_GROUP_NAME',
    -16: 'INVALID_GOAL_CONSTRAINTS',
    -17: 'INVALID_ROBOT_STATE',
    -18: 'INVALID_LINK_NAME',
    -19: 'INVALID_OBJECT_NAME',
    -21: 'FRAME_TRANSFORM_FAILURE',
    -22: 'COLLISION_CHECKING_UNAVAILABLE',
    -23: 'ROBOT_STATE_STALE',
    -24: 'SENSOR_INFO_STALE',
    -25: 'COMMUNICATION_FAILURE',
    -29: 'CRASH',
    -30: 'ABORT',
    -31: 'NO_IK_SOLUTION',
}

SUCESSO = 1

# Dois codigos que NAO sao do MoveIt: sao deste exemplo, para quando a
# execucao nem teve resposta. Ficam fora de CODIGOS (que e copia da fonte) e
# fora da faixa que o MoveIt usa.
EXEC_RECUSADA = -1001
EXEC_SEM_RESPOSTA = -1002
LOCAIS = {EXEC_RECUSADA: 'EXECUCAO_RECUSADA', EXEC_SEM_RESPOSTA: 'EXECUCAO_SEM_RESPOSTA'}

# Visto no ensaio de 16/11: o braco parou DENTRO do volume onde a caixa foi
# posta depois, e todo plano seguinte nasceu em colisao (o Terminal A dizia
# "Found a contact between 'caixa' ... and 'panda_link5'" e "Start state
# appears to be in collision"). Nenhum plano sai dai: o braco nao se move
# enquanto o objeto estiver em cima dele. A saida e tirar, voltar, repor.
SAIR_DE_DENTRO = (
    'o braco esta DENTRO de um objeto da cena (o Terminal A diz qual, em "Found a contact '
    'between"). Nenhum plano parte dai. Faca, nesta ordem: (1) ros2 run aula18_moveit cena '
    '--ros-args -p acao:=remover; (2) ros2 run aula18_moveit tres_poses (ele volta ao '
    'ready no fim); (3) ros2 run aula18_moveit cena, para repor a caixa')

# Onde olhar, por codigo. Curto de proposito: a frase vai para o terminal.
DICAS = {
    'SUCCESS': 'o move_group diz que deu certo; confira no RViz2 se e o que voce queria',
    'FAILURE': 'falha generica -- a explicacao esta no Terminal A, no log do move_group',
    'PLANNING_FAILED': 'o planejador nao achou caminho. O OMPL e aleatorio: rode de novo; '
                       'se repetir, aumente tempo_planejamento ou afaste a pose do obstaculo',
    'INVALID_MOTION_PLAN': 'achou um plano mas o pos-processamento o invalidou; '
                           'olhe o Terminal A e rode de novo (no ensaio de 16/11 saiu 1 vez, '
                           'numa pose que deu SUCCESS nas outras execucoes)',
    'MOTION_PLAN_INVALIDATED_BY_ENVIRONMENT_CHANGE': 'a cena mudou durante a execucao '
                                                     '(alguem rodou o `cena` no meio?)',
    'CONTROL_FAILED': 'o controlador nao cumpriu a trajetoria: '
                      'ros2 control list_controllers (panda_arm_controller tem de estar active)',
    'TIMED_OUT': 'o tempo de planejamento acabou. No OMPL isso costuma ser pose em colisao '
                 'ou fora do alcance, nao "pouco tempo"',
    'PREEMPTED': 'o pedido foi cancelado (Ctrl-C, ou outro pedido chegou por cima)',
    'START_STATE_IN_COLLISION': SAIR_DE_DENTRO,
    'START_STATE_INVALID': SAIR_DE_DENTRO,
    'GOAL_IN_COLLISION': 'o objetivo encosta em algo da cena',
    'GOAL_STATE_INVALID': 'nenhum estado do braco satisfaz a pose sem colidir: pose DENTRO de '
                          'um objeto, ou fora do alcance (~0,85 m do panda_link0)',
    'INVALID_GROUP_NAME': 'o grupo nao existe; no Panda e panda_arm',
    'INVALID_GOAL_CONSTRAINTS': 'a restricao de objetivo esta mal montada (quadro, link ou '
                                'tolerancia zero)',
    'INVALID_LINK_NAME': 'o link nao existe; no Panda o efetuador e panda_link8',
    'FRAME_TRANSFORM_FAILURE': 'quadro desconhecido; use panda_link0',
    'NO_IK_SOLUTION': 'sem cinematica inversa para a pose: fora do alcance ou orientacao '
                      'impossivel',
    'EXECUCAO_RECUSADA': 'o /execute_trajectory recusou o plano; olhe o Terminal A',
    'EXECUCAO_SEM_RESPOSTA': 'a execucao nao terminou no prazo: '
                             'ros2 control list_controllers (panda_arm_controller active?)',
}


def nome(val):
    """`-27` -> 'GOAL_STATE_INVALID'. Codigo fora da tabela vira 'CODIGO_<n>'."""
    try:
        val = int(val)
    except (TypeError, ValueError):
        return 'CODIGO_?'
    return CODIGOS.get(val, LOCAIS.get(val, 'CODIGO_%d' % val))


def dica(val):
    """A frase de onde olhar. Codigo sem dica cai no log do move_group."""
    return DICAS.get(nome(val), 'olhe o Terminal A, no log do move_group')


def descrever(val):
    """'GOAL_STATE_INVALID (-27)', o formato que vai para a tabela."""
    try:
        return '%s (%d)' % (nome(val), int(val))
    except (TypeError, ValueError):
        return nome(val)
