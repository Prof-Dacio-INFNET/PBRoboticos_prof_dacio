"""Manda o Nav2 cumprir uma rota de poses, uma de cada vez.

    ros2 run aula15_nav2 rota
    ros2 run aula15_nav2 rota --ros-args -p voltas:=3
    ros2 run aula15_nav2 rota --ros-args -p rota:="[2.0, 4.0, 0.0, 9.0, 2.0, 1.57]"

ADVERTENCIA: este arquivo NAO FOI EXECUTADO. Nao havia ROS 2 na maquina em que
ele foi escrito. Os nomes de action, de campo e de status foram lidos na FONTE
do Humble (as URLs estao no README-pacote.md), mas nenhum goal foi enviado.

O QUE ELE E, e por que ele e tao pequeno:

    O item 1 do TP4 pede "um no Python que envie objetivos sequenciais ao Nav2,
    definindo uma rota de patrulha ou inspecao". Isto e esse no -- e ele e um
    CLIENTE DE ACAO, exatamente o que voces escreveram nas Aulas 7 e 8.

    O Nav2 nao e uma biblioteca que voce chama: e um servidor de acao que voce
    contrata. `navigate_to_pose` tem objetivo, feedback e resultado, aceita
    cancelamento e demora -- os quatro motivos pelos quais acao existe. Quem
    entendeu a Aula 8 ja sabe navegar; o que falta e o nome do servidor.

A INTERFACE, copiada da fonte do Humble (nav2_msgs/action/NavigateToPose):

    goal:      geometry_msgs/PoseStamped pose
               string behavior_tree          <- vazio = a arvore padrao
    result:    std_msgs/Empty result         <- SIM, vazio: quem conta se deu
                                                certo e o STATUS, nao o result
    feedback:  geometry_msgs/PoseStamped current_pose
               builtin_interfaces/Duration navigation_time
               builtin_interfaces/Duration estimated_time_remaining
               int16 number_of_recoveries
               float32 distance_remaining

    O `result` ser vazio no Humble e a pegadinha da entrega: quem tentar ler
    `resultado.result.error_code` escreve codigo que nao compila contra esta
    versao -- esse campo nasceu depois do Humble. O que diz se chegou e
    `GoalStatus.STATUS_SUCCEEDED`, que vem do envelope da acao.

POR QUE UMA POSE DE CADA VEZ, e nao `follow_waypoints`:

    Existe `follow_waypoints` (lista inteira de uma vez) e
    `navigate_through_poses` (a lista como um unico plano). Os tres servem, e o
    enunciado aceita qualquer um. Este no usa `navigate_to_pose` em sequencia
    porque e o unico dos tres em que VOCE ve, no seu codigo, o goal ser
    aceito, o feedback chegar e o status voltar -- uma vez por ponto. Os outros
    dois escondem justamente a parte que o TP4 cobra que voce explique.

    Quando a rota tiver 20 pontos e voce quiser o Nav2 planejando o conjunto,
    troque para `navigate_through_poses` e diga isso no relatorio.

A ARMADILHA DO `spin_until_future_complete`:

    Este no bloqueia de proposito: manda um goal, espera, manda o proximo. Isso
    so e legitimo porque a espera acontece no `main`, FORA de qualquer callback.
    Chamar `spin_until_future_complete` DENTRO de um callback travaria o no para
    sempre -- o executor estaria esperando por si mesmo. E o mesmo cuidado da
    Aula 8, e o sintoma e o pior possivel: nada acontece e nada reclama.
"""
import math

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node

# A rota padrao e um retangulo dentro do mundo da Aula 11: sala 1, porta,
# sala 2, e volta. Em [x, y, yaw] achatado, porque parametro do ROS 2 nao
# aceita lista de listas -- e porque assim da para trocar a rota pela linha de
# comando sem reconstruir o pacote.
ROTA_PADRAO = [
    2.0, 4.0, 0.0,      # perto da largada, olhando para a porta
    6.1, 4.0, 0.0,      # a porta, no meio do vao de 1,2 m
    9.0, 5.5, 1.57,     # sala 2, canto de cima
    9.0, 2.2, -1.57,    # sala 2, canto de baixo
    6.1, 4.0, 3.14,     # a porta de volta, olhando para a sala 1
]


def pose_stamped(no, quadro, x, y, yaw):
    """Monta a PoseStamped que o goal pede, com o yaw virado em quaternio.

    Quaternio de uma rotacao so em z: (0, 0, sin(yaw/2), cos(yaw/2)). Nao
    precisa de tf_transformations para isto, e uma dependencia a menos.

    O `frame_id` e `map` de proposito: o objetivo e um lugar NO MAPA, nao um
    deslocamento a partir do robo. Mandar o goal em `base_link` com (2, 4) pede
    "ande 2 m para a frente e 4 m para a esquerda", que e outra coisa -- e o
    Nav2 obedece sem reclamar.
    """
    alvo = PoseStamped()
    alvo.header.frame_id = quadro
    alvo.header.stamp = no.get_clock().now().to_msg()
    alvo.pose.position.x = float(x)
    alvo.pose.position.y = float(y)
    alvo.pose.orientation.z = math.sin(float(yaw) / 2.0)
    alvo.pose.orientation.w = math.cos(float(yaw) / 2.0)
    return alvo


class Rota(Node):
    """Cliente de acao que percorre uma lista de poses, uma por vez."""

    def __init__(self):
        super().__init__('rota')
        self.declare_parameter('rota', ROTA_PADRAO)
        self.declare_parameter('voltas', 1)
        self.declare_parameter('quadro', 'map')
        self.declare_parameter('espera_servidor_s', 30.0)

        bruta = list(self.get_parameter('rota').value)
        if len(bruta) % 3 != 0 or not bruta:
            raise SystemExit(
                'a rota tem de ter multiplos de 3 numeros (x, y, yaw por ponto); '
                f'recebi {len(bruta)}')
        self.pontos = [tuple(bruta[i:i + 3]) for i in range(0, len(bruta), 3)]
        self.voltas = int(self.get_parameter('voltas').value)
        self.quadro = self.get_parameter('quadro').value
        self.espera = float(self.get_parameter('espera_servidor_s').value)

        self.cliente = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.ultimo_aviso = None

    def esperar_servidor(self):
        """Espera o `navigate_to_pose` existir, e diz o que fazer se nao existir.

        O servidor so aparece depois que o `bt_navigator` esta ATIVO -- nao
        basta o processo estar no ar. Se o gerenciador de ciclo de vida travou
        em "Configuring", este wait estoura, e a causa esta la, nao aqui.
        """
        self.get_logger().info('esperando o servidor navigate_to_pose...')
        if not self.cliente.wait_for_server(timeout_sec=self.espera):
            raise SystemExit(
                'o servidor navigate_to_pose nao apareceu em '
                f'{self.espera:.0f} s.\n'
                '  confira:  ros2 action list | grep navigate\n'
                '            ros2 lifecycle get /bt_navigator   # tem de ser active\n'
                '  e lembre: sem a pose inicial o AMCL nao publica map -> odom, e o\n'
                '  bt_navigator fica esperando a TF -- de o 2D Pose Estimate no RViz2.')
        self.get_logger().info('servidor no ar.')

    def ao_receber_feedback(self, msg):
        """Imprime a distancia que falta, no maximo uma vez por metro.

        O feedback chega varias vezes por segundo. Imprimir todas afoga o
        terminal e esconde o que importa -- inclusive o
        `number_of_recoveries`, que e o numero mais interessante da navegacao:
        ele conta quantas vezes o Nav2 teve de se desenrascar.
        """
        f = msg.feedback
        marca = round(float(f.distance_remaining))
        if marca != self.ultimo_aviso:
            self.ultimo_aviso = marca
            self.get_logger().info(
                f'  faltam {f.distance_remaining:.1f} m  '
                f'(recuperacoes: {f.number_of_recoveries})')

    def ir_para(self, ponto, etiqueta):
        """Manda UM goal e espera o status dele. Devolve True se chegou."""
        x, y, yaw = ponto
        objetivo = NavigateToPose.Goal()
        objetivo.pose = pose_stamped(self, self.quadro, x, y, yaw)
        self.get_logger().info(f'{etiqueta}: indo para ({x:.2f}, {y:.2f}, {yaw:.2f})')
        self.ultimo_aviso = None

        envio = self.cliente.send_goal_async(
            objetivo, feedback_callback=self.ao_receber_feedback)
        rclpy.spin_until_future_complete(self, envio)
        punho = envio.result()
        if punho is None or not punho.accepted:
            # Goal RECUSADO nao e goal que falhou: o servidor nem tentou. A
            # causa de longe mais comum e objetivo fora do mapa ou em celula
            # ocupada -- veja a mensagem do planner_server no outro terminal.
            self.get_logger().error(f'{etiqueta}: goal RECUSADO pelo servidor')
            return False

        conclusao = punho.get_result_async()
        rclpy.spin_until_future_complete(self, conclusao)
        status = conclusao.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'{etiqueta}: chegou.')
            return True

        # No Humble o `result` desta acao e um std_msgs/Empty: nao ha codigo de
        # erro para ler. O que sobra e o status, e e o suficiente.
        nomes = {GoalStatus.STATUS_ABORTED: 'ABORTADO (o Nav2 desistiu)',
                 GoalStatus.STATUS_CANCELED: 'CANCELADO',
                 GoalStatus.STATUS_UNKNOWN: 'DESCONHECIDO'}
        self.get_logger().error(
            f'{etiqueta}: {nomes.get(status, f"status {status}")}')
        return False

    def percorrer(self):
        """A rota inteira. `voltas:=0` patrulha para sempre."""
        volta = 0
        while self.voltas == 0 or volta < self.voltas:
            volta += 1
            for i, ponto in enumerate(self.pontos, start=1):
                etiqueta = f'[volta {volta} ponto {i}/{len(self.pontos)}]'
                if not self.ir_para(ponto, etiqueta):
                    self.get_logger().warn(
                        f'{etiqueta} nao foi cumprido -- seguindo para o proximo. '
                        'Rota de patrulha que para no primeiro tropeco nao patrulha.')
            self.get_logger().info(f'volta {volta} concluida.')


def main():
    rclpy.init()
    no = Rota()
    try:
        no.esperar_servidor()
        no.percorrer()
    except KeyboardInterrupt:
        # Ctrl-C aqui NAO cancela o goal em andamento: o Nav2 continua indo para
        # o ultimo ponto. Para parar o robo de verdade:
        #   ros2 action send_goal ... nao; use o botao Cancel do RViz2, ou
        #   ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
        no.get_logger().info('interrompido (o goal em andamento segue valendo)')
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
