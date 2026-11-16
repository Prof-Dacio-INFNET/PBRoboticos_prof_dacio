"""O no que conversa com o move_group: tres clientes de acao e um de servico.

ADVERTENCIA: escrito sem ROS 2, a partir da fonte do Humble (URLs no
README), e conferido pelo testar.py com dubles do rclpy. EXECUTADO pela
primeira vez em 16/11 (WSL2 do professor, Humble, MoveIt 2.5.10): a cena pelo
servico, o planejamento pela /move_action e a execucao pela
/execute_trajectory conversaram com o move_group. A acao da garra
(/panda_hand_controller/gripper_cmd) NUNCA foi chamada de verdade.

POR QUE rclpy PURO, e nao uma biblioteca do MoveIt:

    O MoveIt 2 nao e uma biblioteca que voce chama: e um no (move_group) que
    oferece ACOES e SERVICOS. Quem entendeu as Aulas 7, 8 e 15 ja sabe usa-lo
    -- e o mesmo cliente de acao do `rota.py` do Nav2, com outra mensagem.

    Ate a versao 2.5.9 do Humble nao havia API Python oficial pelo apt; a
    `moveit_py` foi portada para o Humble na 2.5.10 (01/09/2026). Este exemplo
    nao depende dela: funciona em qualquer Humble com o MoveIt do apt, e
    mostra o que a API esconde.

OS NOMES, lidos na fonte (moveit2 branch humble,
moveit_ros/move_group/include/moveit/move_group/capability_names.h, e
ros2_controllers branch humble, gripper_controllers):

    /move_action            moveit_msgs/action/MoveGroup         planejar (e executar)
    /execute_trajectory     moveit_msgs/action/ExecuteTrajectory executar um plano pronto
    /apply_planning_scene   moveit_msgs/srv/ApplyPlanningScene   mudar a cena, COM resposta
    /panda_hand_controller/gripper_cmd  control_msgs/action/GripperCommand  a garra

A ARMADILHA DO `spin_until_future_complete` (a mesma do rota.py):

    Este no bloqueia de proposito -- pede, espera, pede o proximo. Isso so e
    legitimo porque a espera acontece no fluxo principal, FORA de qualquer
    callback. Dentro de um callback, o executor esperaria por si mesmo.
"""
import time

import rclpy
from control_msgs.action import GripperCommand
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.srv import ApplyPlanningScene
from rclpy.action import ActionClient
from rclpy.node import Node

from aula18_moveit import codigos, mensagens
from aula18_moveit.sequencia import Resultado

ACAO_MOVER = '/move_action'
ACAO_EXECUTAR = '/execute_trajectory'
SERVICO_CENA = '/apply_planning_scene'
ACAO_GARRA = '/panda_hand_controller/gripper_cmd'

CONFIRA_MOVE_GROUP = (
    '  confira, em outro terminal:\n'
    '      ros2 node list | grep move_group\n'
    '      ros2 action list | grep -E "move_action|execute_trajectory"\n'
    '      ros2 service list | grep apply_planning_scene\n'
    '  e olhe o Terminal A: a linha "You can start planning now!" tem de ter\n'
    '  aparecido. Sem ela, o move_group nao terminou de subir -- a causa esta\n'
    '  la, nao aqui.')

CONFIRA_GARRA = (
    '  confira, em outro terminal:\n'
    '      ros2 control list_controllers      # panda_hand_controller active\n'
    '      ros2 action list | grep gripper_cmd')


class ClienteMoveIt(Node):
    """Base dos tres nos: parametros comuns, espera dos servidores, pedidos."""

    def __init__(self, nome):
        super().__init__(nome)
        self.declare_parameter('espera_servidor_s', 20.0)
        self.declare_parameter('tempo_planejamento', 5.0)
        self.declare_parameter('tentativas', 1)
        self.declare_parameter('velocidade', 0.5)
        self.declare_parameter('prazo_execucao_s', 60.0)
        self.espera = float(self.get_parameter('espera_servidor_s').value)
        self.tempo = float(self.get_parameter('tempo_planejamento').value)
        self.tentativas = int(self.get_parameter('tentativas').value)
        self.velocidade = float(self.get_parameter('velocidade').value)
        self.prazo_exec = float(self.get_parameter('prazo_execucao_s').value)

        self.mover_cli = ActionClient(self, MoveGroup, ACAO_MOVER)
        self.exec_cli = ActionClient(self, ExecuteTrajectory, ACAO_EXECUTAR)
        self.cena_cli = self.create_client(ApplyPlanningScene, SERVICO_CENA)
        self.garra_cli = None

    # ------------------------------------------------------------ esperas

    def esperar_move_group(self, precisa_executar=True, precisa_cena=True):
        """Espera os servidores do move_group. Devolve False e diz o que olhar."""
        faltam = []
        self.get_logger().info('esperando o move_group (ate %.0f s)...' % self.espera)
        if not self.mover_cli.wait_for_server(timeout_sec=self.espera):
            faltam.append(ACAO_MOVER)
        if precisa_executar and not self.exec_cli.wait_for_server(timeout_sec=2.0):
            faltam.append(ACAO_EXECUTAR)
        if precisa_cena and not self.cena_cli.wait_for_service(timeout_sec=2.0):
            faltam.append(SERVICO_CENA)
        if faltam:
            self.get_logger().error('nao achei: %s\n%s' % (', '.join(faltam),
                                                           CONFIRA_MOVE_GROUP))
            return False
        self.get_logger().info('achei o move_group.')
        return True

    def esperar_garra(self):
        if self.garra_cli is None:
            self.garra_cli = ActionClient(self, GripperCommand, ACAO_GARRA)
        if not self.garra_cli.wait_for_server(timeout_sec=self.espera):
            self.get_logger().error('nao achei a acao %s\n%s' % (ACAO_GARRA, CONFIRA_GARRA))
            return False
        return True

    # ------------------------------------------------------------- a cena

    def aplicar_cena(self, diff, prazo=5.0):
        """Manda um PlanningScene de diferenca pelo SERVICO. True/False/None.

        Por que servico e nao o topico /planning_scene: o topico nao responde.
        Um publicador criado e usado em seguida pode publicar antes de o
        move_group o descobrir, e a mensagem se perde sem aviso -- a caixa
        nao aparece e ninguem reclama. O servico so volta depois que o
        move_group aplicou a diferenca, e diz se conseguiu (`success`). E a
        "atualizacao sincrona" do tutorial planning_scene_ros_api do Humble.
        """
        req = ApplyPlanningScene.Request()
        req.scene = diff
        fut = self.cena_cli.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=prazo)
        if not fut.done() or fut.result() is None:
            self.get_logger().error('o %s nao respondeu em %.0f s' % (SERVICO_CENA, prazo))
            return None
        return bool(fut.result().success)

    # ----------------------------------------------------------- o movimento

    def _esperar_acao(self, cliente, goal, prazo):
        """Envia um goal e espera. Devolve (aceito, resposta_ou_None, segundos)."""
        t0 = time.monotonic()
        envio = cliente.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, envio, timeout_sec=prazo)
        punho = envio.result() if envio.done() else None
        if punho is None or not punho.accepted:
            return False, None, time.monotonic() - t0
        fim = punho.get_result_async()
        rclpy.spin_until_future_complete(self, fim, timeout_sec=prazo)
        if not fim.done() or fim.result() is None:
            punho.cancel_goal_async()   # melhor esforco: nao fica pendurado
            return True, None, time.monotonic() - t0
        return True, fim.result().result, time.monotonic() - t0

    def mover(self, alvo, modo='executar'):
        """Planeja (e executa) UM alvo. Devolve um sequencia.Resultado.

        modo 'planejar'  plan_only = True; o robo nao se mexe
        modo 'executar'  plan_only = True e, se deu SUCCESS, manda a trajetoria
                         para /execute_trajectory -- plan e execute separados,
                         como os botoes Plan e Execute do RViz2
        modo 'direto'    plan_only = False: o move_group planeja e executa
                         num pedido so (o "Plan & Execute"); o planning_time
                         nao vem preenchido nesse caminho (lido em
                         move_action_capability.cpp), so o relogio conta
        """
        if alvo['tipo'] == 'juntas':
            restr = mensagens.restricoes_de_juntas(alvo['valores'])
        else:
            x, y, z = alvo['valores'][:3]
            q = alvo.get('orientacao', mensagens.PARA_BAIXO)
            restr = mensagens.restricoes_de_pose(x, y, z, q)
        goal = mensagens.pedido(restr, so_planejar=(modo != 'direto'), tempo=self.tempo,
                                tentativas=self.tentativas, velocidade=self.velocidade,
                                aceleracao=self.velocidade)
        prazo = self.tempo + 10.0 if modo != 'direto' else self.tempo + self.prazo_exec
        aceito, res, seg = self._esperar_acao(self.mover_cli, goal, prazo)
        r = Resultado(alvo['nome'], tempo_relogio=seg)
        if not aceito:
            r.recusado = True
            return r
        if res is None:
            r.sem_resposta = True
            return r
        r.codigo = int(res.error_code.val)
        r.tempo_moveit = float(res.planning_time)
        r.trajetoria = res.planned_trajectory
        r.pontos = mensagens.pontos(res.planned_trajectory)
        r.comprimento = mensagens.comprimento_juntas(res.planned_trajectory)
        if modo == 'direto':
            r.execucao = r.codigo
        elif modo == 'executar' and r.codigo == codigos.SUCESSO:
            r.execucao = self.executar(res.planned_trajectory)
        return r

    def executar(self, trajetoria):
        """Manda uma trajetoria pronta para /execute_trajectory. Devolve o codigo."""
        if mensagens.pontos(trajetoria) == 0:
            return codigos.SUCESSO      # nada a executar: o robo ja estava la
        goal = ExecuteTrajectory.Goal()
        goal.trajectory = trajetoria
        aceito, res, _ = self._esperar_acao(self.exec_cli, goal, self.prazo_exec)
        if not aceito:
            return codigos.EXEC_RECUSADA
        if res is None:
            return codigos.EXEC_SEM_RESPOSTA
        return int(res.error_code.val)

    def garra(self, posicao, forca=10.0):
        """Abre/fecha a garra. `posicao` e a da junta panda_finger_joint1 (m).

        0,035 = aberta (estado `open` do SRDF), 0,0 = fechada. Nao e a
        abertura entre os dedos: e a de UM dedo; a abertura e o dobro.
        Devolve True se o controlador disse reached_goal.
        """
        goal = GripperCommand.Goal()
        goal.command.position = float(posicao)
        goal.command.max_effort = float(forca)
        aceito, res, _ = self._esperar_acao(self.garra_cli, goal, 15.0)
        if not aceito or res is None:
            return False
        return bool(res.reached_goal)
