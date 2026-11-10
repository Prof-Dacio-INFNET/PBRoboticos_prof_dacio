"""Cancela o objetivo quando o /scan ve menos de 0,5 m, espera 2 s e reenvia.

    ros2 run aula16_arvore vigia
    ros2 run aula16_arvore vigia --ros-args -p objetivo:="[10.5, 6.5, 1.57]"
    ros2 run aula16_arvore vigia --ros-args -p limiar_m:=0.6 -p espera_s:=3.0
    ros2 run aula16_arvore vigia --ros-args \\
      -p arvore:=/caminho/do/share/aula16_arvore/arvores/com_espera.xml

O QUE JA FOI EXECUTADO: em 09/11/2026, numa maquina com Humble e o Nav2 da
Aula 15, com `-p limiar_m:=0.75`, este no cancelou o goal com o /scan a
0,70 m, esperou 2 s, reenviou o MESMO goal e o Nav2 o cumpriu ("1
interrupcao(oes) no caminho"). A primeira execucao do dia, ~20 s depois de
subir o Nav2, terminou em status 6 (ABORTADO) 3,4 s apos o envio; a seguinte
completou -- causa nao confirmada. O que mudou DEPOIS desse ensaio e nao foi
executado com ROS 2: a publicacao do /estado_vigia em cada transicao
(`publicar_estado`) e o filtro do feedback com distancia 0,0. O `testar.py`
exercita os dois com dubles do rclpy, o que nao e' a mesma coisa.

O QUE ELE E: o CAMINHO DE CLIENTE do item 2 do TP4.

    O enunciado pede uma arvore de comportamento que interrompa a navegacao
    quando um sensor vir obstaculo a menos de 0,5 m, espere 2 s e retome o
    objetivo. Ha dois caminhos para isso, e eles NAO sao equivalentes:

    ARVORE   um no de condicao dentro da arvore do bt_navigator, lendo o
             /scan e devolvendo SUCCESS abaixo de 0,5 m. No Humble ele NAO
             EXISTE pronto: nenhum no de condicao do `nav2_behavior_tree`
             mede distancia a obstaculo (o mais perto e o `DistanceTraveled`,
             que mede o quanto o ROBO andou). Escrever um e C++, plugin,
             `plugin_lib_names` e recompilar o workspace. E o caminho certo
             para producao e o caminho caro para uma aula de duas horas.

    CLIENTE  este no: le o /scan em Python, e quando o portao dispara ele
             CANCELA o goal pela interface da acao, espera, e manda o MESMO
             goal de novo. O Nav2 nao sabe que ele existe -- e nao precisa
             saber: cancelar e reenviar sao operacoes publicas da acao.

    A diferenca honesta, para o relatorio: a arvore reage dentro de um tick
    (o `bt_loop_duration` e 10 ms no Humble); este no reage no proximo /scan,
    que a 5 Hz e ate 200 ms depois. Para um robo a 0,35 m/s isso e 7 cm. Para
    um robo a 1,5 m/s seriam 30 cm, e ai o caminho de cliente nao serve mais.

    O `arvores/com_espera.xml` deste exemplo faz a OUTRA metade: a espera de
    2 s dentro da arvore, com nos prontos do Humble. Ela cobre a falha da
    navegacao, nao o portao de 0,5 m. Os dois juntos cobrem o item inteiro, e
    o README explica a divisao.

A ARMADILHA QUE O `rota.py` DA AULA 15 DOCUMENTA, e que aqui muda de lado:

    No `rota.py` as esperas acontecem no `main`, FORA de callback, e por isso
    `rclpy.spin_until_future_complete` e legitimo la. Aqui NAO E, e isso e
    o ponto deste arquivo: todo o trabalho acontece dentro de callbacks (do
    /scan, do resultado do cancelamento, do temporizador). Chamar
    `spin_until_future_complete` dentro de um callback trava o no para
    sempre: o executor so processa a proxima coisa quando o callback atual
    RETORNA, e o callback esta esperando o executor processar a proxima
    coisa. O executor fica esperando por si mesmo, e o sintoma e o pior
    possivel -- nada acontece e nada reclama.

    O jeito assincrono, que e o deste arquivo:

      futuro = self.punho.cancel_goal_async()
      futuro.add_done_callback(self.ao_cancelar)     # e retorna JA
      ...
      def ao_cancelar(self, futuro):                 # o executor chama depois
          self.estado = 'esperando'
          self.timer = self.create_timer(self.espera_s, self.fim_da_espera)

    Nada bloqueia. A maquina de estados avanca de callback em callback, que
    e como um no ROS 2 bem escrito se parece.

POR QUE NAO PRECISA DE TRAVA (lock), ainda que pareca:

    `self.estado` e lido e escrito por quatro callbacks diferentes. Isso so e
    seguro porque o executor padrao do rclpy e de uma thread so e todo
    callback nasce no mesmo grupo (MutuallyExclusiveCallbackGroup): dois
    callbacks deste no NUNCA rodam ao mesmo tempo. Se um dia voce trocar por
    `MultiThreadedExecutor` para ganhar paralelismo, esta maquina de estados
    passa a precisar de trava -- e ela vai quebrar de um jeito que so aparece
    uma vez por hora.

O TEMPORIZADOR DE UMA SO VEZ, que o rclpy nao tem:

    `create_timer` e sempre periodico. A espera de 2 s e um evento unico, e o
    idioma do rclpy para isso e criar o temporizador e cancela-lo dentro do
    proprio callback dele. E o que `fim_da_espera` faz na primeira linha.
    Esquecer essa linha da um robo que reenvia o objetivo a cada 2 s para
    sempre -- e, como o goal novo substitui o anterior, o robo fica andando
    mas o `number_of_recoveries` do feedback nunca passa de zero e nada no
    sistema parece errado.
"""
import math

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32, String

from aula16_arvore.varredura import SETOR_PADRAO_GRAUS, menor_distancia

# O objetivo padrao, em [x, y, yaw] achatado -- a mesma forma do `rota.py` da
# Aula 15, e pelo mesmo motivo: parametro do ROS 2 nao aceita lista de listas.
# Ate 09/11 o padrao era (9.0, 5.5), que cai DENTRO do obstaculo retangular da
# sala 2 do mundo da Aula 11 (8,6-9,6 x 5,2-5,8): o Nav2 recusa o goal e o
# vigia nao tem o que vigiar. Conferido com Mundo().ocupado(9.0, 5.5) == True.
OBJETIVO_PADRAO = [10.5, 6.5, 1.57]

# Os dois numeros do enunciado. Nao sao escolha nossa.
LIMIAR_PADRAO_M = 0.5
ESPERA_PADRAO_S = 2.0

# Carencia depois de retomar. Sem ela, o robo reenvia o goal, anda 10 cm,
# ve o MESMO obstaculo e cancela de novo -- e fica assim para sempre. A
# carencia nao conserta isso; ela so troca "para sempre" por "a cada 1,5 s",
# e e isso que a coluna de reincidencia do `medir_sessao.py` acusa. O
# conserto de verdade esta no README: obstaculo que nao anda nao e caso de
# esperar, e caso de replanejar -- e replanejar e exatamente o que a arvore
# padrao do Nav2 ja faz sozinha.
CARENCIA_PADRAO_S = 1.5

# Os quatro estados que vao para o /estado_vigia, e dai para a coluna
# `estado` do CSV. Sao os mesmos nomes do `simular_sessao.py`: a regua
# offline nao distingue sessao simulada de sessao gravada, e nao deve mesmo.
NAVEGANDO = 'navegando'
INTERROMPIDO = 'interrompido'
ESPERANDO = 'esperando'
RETOMANDO = 'retomando'


def pose_stamped(no, quadro, x, y, yaw):
    """A PoseStamped do goal, com o yaw virado em quaternio.

    `frame_id` e `map` de proposito, como no `rota.py`: o objetivo e um lugar
    NO MAPA. O mesmo goal em `base_link` pede "ande x metros para a frente e
    y para a esquerda", que e outra coisa -- e o Nav2 obedece sem reclamar.
    """
    alvo = PoseStamped()
    alvo.header.frame_id = quadro
    alvo.header.stamp = no.get_clock().now().to_msg()
    alvo.pose.position.x = float(x)
    alvo.pose.position.y = float(y)
    alvo.pose.orientation.z = math.sin(float(yaw) / 2.0)
    alvo.pose.orientation.w = math.cos(float(yaw) / 2.0)
    return alvo


class Vigia(Node):
    """Maquina de quatro estados em cima de um cliente da acao navigate_to_pose."""

    def __init__(self):
        super().__init__('vigia')
        self.declare_parameter('objetivo', OBJETIVO_PADRAO)
        self.declare_parameter('quadro', 'map')
        self.declare_parameter('limiar_m', LIMIAR_PADRAO_M)
        self.declare_parameter('espera_s', ESPERA_PADRAO_S)
        self.declare_parameter('carencia_s', CARENCIA_PADRAO_S)
        self.declare_parameter('setor_graus', SETOR_PADRAO_GRAUS)
        self.declare_parameter('espera_servidor_s', 30.0)
        # O XML da sua arvore de comportamento, como no `rota.py`. Vazio = a
        # arvore padrao do bt_navigator. O caminho tem de existir na maquina
        # que roda o bt_navigator, e o jeito robusto e apontar para dentro do
        # share do pacote INSTALADO, nunca para a pasta de fontes.
        self.declare_parameter('arvore', '')

        bruto = list(self.get_parameter('objetivo').value)
        if len(bruto) != 3:
            raise SystemExit('objetivo tem de ser [x, y, yaw]; recebi %d '
                             'numero(s)' % len(bruto))
        self.objetivo = tuple(float(v) for v in bruto)
        self.quadro = self.get_parameter('quadro').value
        self.limiar = float(self.get_parameter('limiar_m').value)
        self.espera_s = float(self.get_parameter('espera_s').value)
        self.carencia_s = float(self.get_parameter('carencia_s').value)
        self.setor = float(self.get_parameter('setor_graus').value)
        self.espera_servidor = float(self.get_parameter('espera_servidor_s').value)
        self.arvore = self.get_parameter('arvore').value

        self.estado = NAVEGANDO
        self.punho = None            # o goal handle em andamento
        self.timer_espera = None     # o temporizador de uma vez so
        self.t_carencia = 0.0        # ate quando o portao fica desarmado
        self.interrupcoes = 0
        self.ultima_dist = float('inf')

        self.cliente = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.create_subscription(LaserScan, 'scan', self.ao_scan,
                                 qos_profile_sensor_data)
        # Estes dois publicadores existem para o BAG: e deles que saem a
        # coluna `estado` e a coluna `dist_min_scan` do CSV da analise. Sem
        # eles, o bag registra o que o robo fez e nao registra POR QUE -- e o
        # grafico do item 2 fica sem como marcar as interrupcoes.
        self.pub_estado = self.create_publisher(String, 'estado_vigia', 10)
        self.pub_dist = self.create_publisher(Float32, 'dist_min', 10)
        self.create_timer(0.1, self.ao_publicar)

    # ------------------------------------------------------------ o portao
    def ao_scan(self, msg):
        """O sensor. Dispara o portao -- e so ele decide interromper."""
        self.ultima_dist = menor_distancia(msg, self.setor)
        if self.estado != NAVEGANDO or self.punho is None:
            return
        if self.agora() < self.t_carencia:
            return
        if self.ultima_dist < self.limiar:
            self.interromper()

    def agora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def publicar_estado(self):
        """Publica o estado AGORA. Chamado a 10 Hz e em cada transicao.

        So' o temporizador de 10 Hz nao basta: no ensaio de 09/11/2026 o
        `interrompido` durou ~2 ms (do pedido de cancelamento ate a resposta)
        e o `retomando` dura so' ate o goal novo ser aceito: nenhum dos dois
        chegou ao bag. Com a
        publicacao na transicao, o bag guarda os quatro estados, cada um com
        o carimbo de quando aconteceu.
        """
        m = String()
        m.data = self.estado
        self.pub_estado.publish(m)

    def ao_publicar(self):
        """Publica estado e distancia a 10 Hz, para o `ros2 bag record`."""
        self.publicar_estado()
        d = Float32()
        # Vai o proprio `inf` quando o setor estiver vazio. Um Float32
        # carrega inf sem reclamar, e quem for plotar o /dist_min direto do
        # bag decide o que fazer com o pico. Trocar inf por zero aqui seria
        # mentir ao contrario: zero e obstaculo encostado, nao "nao vi nada".
        # Quem converte isso para o CSV e o `gravar_pose.py`, com o
        # `range_max` do laser em maos.
        d.data = float(self.ultima_dist)
        self.pub_dist.publish(d)

    # -------------------------------------------------- a maquina de estados
    def enviar_objetivo(self):
        """Manda (ou REMANDA) o mesmo objetivo. Nada bloqueia aqui."""
        x, y, yaw = self.objetivo
        meta = NavigateToPose.Goal()
        meta.pose = pose_stamped(self, self.quadro, x, y, yaw)
        # O campo que aponta a SUA arvore naquele objetivo. Vazio, vale a
        # padrao do bt_navigator. E metade do item 2 do TP4 de graca.
        meta.behavior_tree = self.arvore
        self.get_logger().info(
            'enviando objetivo (%.2f, %.2f, %.2f)%s'
            % (x, y, yaw, ' com arvore %s' % self.arvore if self.arvore else ''))
        self.cliente.send_goal_async(
            meta, feedback_callback=self.ao_feedback
        ).add_done_callback(self.ao_aceitar)

    def ao_aceitar(self, futuro):
        """O servidor aceitou (ou recusou) o goal."""
        punho = futuro.result()
        if punho is None or not punho.accepted:
            # Recusado nao e falhou: o servidor nem tentou. Quase sempre e
            # objetivo fora do mapa ou em celula ocupada/inflada -- a
            # mensagem util sai no terminal do planner_server.
            self.get_logger().error('goal RECUSADO pelo servidor')
            # `punho` volta a None de proposito: sem goal valido, o portao
            # fica DESARMADO (veja a guarda em `ao_scan`). Deixar aqui o
            # punho do goal anterior, ja cancelado, faria o proximo /scan
            # abaixo de 0,5 m pedir o cancelamento de um goal que nao existe
            # mais -- e o robo ficaria preso em `esperando` para sempre.
            self.punho = None
            self.estado = NAVEGANDO
            self.publicar_estado()
            return
        self.punho = punho
        self.estado = NAVEGANDO
        self.publicar_estado()
        punho.get_result_async().add_done_callback(self.ao_resultado)

    def ao_feedback(self, msg):
        """So para o log ficar legivel: uma linha por metro que falta."""
        f = msg.feedback
        # O primeiro feedback chega antes de o Nav2 ter caminho, com
        # distance_remaining = 0.0: "faltam 0.0 m" logo depois do envio.
        if f.distance_remaining <= 0.0:
            return
        if int(f.distance_remaining) != getattr(self, '_marca', None):
            self._marca = int(f.distance_remaining)
            self.get_logger().info(
                '  faltam %.1f m (recuperacoes do Nav2: %d)'
                % (f.distance_remaining, f.number_of_recoveries))

    def ao_resultado(self, futuro):
        """Chegou, foi abortado, ou foi cancelado POR NOS."""
        status = futuro.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(
                'objetivo cumprido. %d interrupcao(oes) no caminho.'
                % self.interrupcoes)
            self.punho = None
            return
        if status == GoalStatus.STATUS_CANCELED:
            # Esperado: fomos nos que cancelamos. Quem retoma e o
            # temporizador da espera, nao este callback.
            self.get_logger().info('goal cancelado (pelo vigia)')
            return
        # No Humble o `result` desta acao e um std_msgs/Empty: nao ha codigo
        # de erro para ler. Quem escrever `resultado.result.error_code`
        # escreve codigo de uma versao posterior ao Humble.
        self.get_logger().error(
            'goal terminou em status %d (ABORTADO e o caso comum: o Nav2 '
            'desistiu depois de esgotar as recuperacoes da arvore)' % status)
        self.punho = None

    def interromper(self):
        """O portao disparou: cancela o goal em andamento. Sem bloquear."""
        self.interrupcoes += 1
        self.estado = INTERROMPIDO
        self.publicar_estado()
        self.get_logger().warn(
            'obstaculo a %.2f m (< %.2f m): cancelando o objetivo'
            % (self.ultima_dist, self.limiar))
        self.punho.cancel_goal_async().add_done_callback(self.ao_cancelar)

    def ao_cancelar(self, futuro):
        """O cancelamento foi processado. Comeca a espera de 2 s.

        O `futuro.result()` aqui e uma CancelGoal.Response, com um campo
        `goals_canceling`: lista vazia significa que o servidor nao cancelou
        nada -- quase sempre porque o goal ja tinha terminado sozinho entre o
        /scan e esta resposta. Esperar 2 s nesse caso nao estraga nada, e a
        alternativa (tratar o caso) custa mais codigo do que vale numa aula.
        """
        resposta = futuro.result()
        quantos = len(getattr(resposta, 'goals_canceling', []))
        self.estado = ESPERANDO
        self.publicar_estado()
        self.get_logger().info(
            'cancelamento aceito (%d goal em cancelamento); esperando %.1f s'
            % (quantos, self.espera_s))
        self.timer_espera = self.create_timer(self.espera_s, self.fim_da_espera)

    def fim_da_espera(self):
        """Passaram-se os 2 s: reenvia o MESMO objetivo.

        A primeira linha e obrigatoria: `create_timer` do rclpy e periodico, e
        sem o cancelamento este callback voltaria a cada 2 s para sempre.
        """
        self.timer_espera.cancel()
        self.destroy_timer(self.timer_espera)
        self.timer_espera = None
        self.estado = RETOMANDO
        self.publicar_estado()
        self.t_carencia = self.agora() + self.carencia_s
        self.get_logger().info('espera cumprida; retomando o MESMO objetivo')
        self.enviar_objetivo()

    # ------------------------------------------------------------- partida
    def esperar_servidor(self):
        """Bloqueia ate o `navigate_to_pose` existir -- e isto e legitimo.

        Legitimo porque acontece no `main`, FORA de qualquer callback, antes
        do `spin`. E a mesma distincao do `rota.py` da Aula 15, e e a razao
        de este arquivo ter o paragrafo da armadilha no topo.

        O servidor so aparece depois que o `bt_navigator` esta ATIVO -- nao
        basta o processo estar no ar.
        """
        self.get_logger().info('esperando o servidor navigate_to_pose...')
        if not self.cliente.wait_for_server(timeout_sec=self.espera_servidor):
            raise SystemExit(
                'o servidor navigate_to_pose nao apareceu em %.0f s.\n'
                '  confira:  ros2 action list | grep navigate\n'
                '            ros2 lifecycle get /bt_navigator   # tem de ser '
                'active\n'
                '  e lembre: sem a pose inicial o AMCL nao publica map -> odom,\n'
                '  e o bt_navigator fica esperando a TF.' % self.espera_servidor)
        self.get_logger().info('servidor no ar.')


def main():
    rclpy.init()
    no = Vigia()
    try:
        no.esperar_servidor()
        no.enviar_objetivo()
        rclpy.spin(no)
    except KeyboardInterrupt:
        no.get_logger().info('interrompido (o goal em andamento segue valendo)')
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
