"""DEMO 2 -- o "robo" que recebe os comandos.

Quatro servicos, um por marcador. Cada chamada imprime um banner grande no
terminal e guarda o estado. Nao ha robo nenhum aqui: ha o LUGAR onde o robo
entraria.

E esse o ponto pedagogico do no. Quem detecta nao sabe o que acontece depois;
quem age nao sabe como foi detectado. Trocar este arquivo por um driver de
motor nao exige tocar no detector -- e trocar o detector por um modelo treinado
nao exige tocar aqui.
"""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from .formas import MARCADORES

LARGURA = 62


def banner(texto, simbolo='='):
    linha = simbolo * LARGURA
    return '\n%s\n%s\n%s' % (linha, texto.center(LARGURA), linha)


class PainelRobo(Node):
    def __init__(self):
        super().__init__('painel_robo')
        self.estado = 'ocioso'
        self.contagem = {}

        # Uma fabrica de callbacks: cada servico precisa de um callback proprio,
        # e fechar sobre a variavel do laco sem o argumento padrao e o classico
        # jeito de todos os quatro apontarem para o ultimo marcador.
        self.servicos = []
        for nome, _, caminho in MARCADORES:
            self.servicos.append(
                self.create_service(Trigger, caminho, self._fazer(nome, caminho)))

        self.get_logger().info('painel do robo no ar - %d servicos: %s'
                               % (len(MARCADORES), ', '.join(m[2] for m in MARCADORES)))

    def _fazer(self, nome, caminho):
        acoes = {
            'triangulo': ('PARAR', 'motores em zero, freio acionado'),
            'quadrado':  ('SEGUIR LINHA', 'controle de trajetoria assumindo'),
            'circulo':   ('GIRAR 90 GRAUS', 'rotacao no proprio eixo'),
            'cruz':      ('PARADA DE EMERGENCIA', 'corte de potencia, requer rearme'),
        }

        def callback(req, resp, nome=nome, caminho=caminho):
            titulo, detalhe = acoes.get(nome, (nome.upper(), ''))
            self.contagem[nome] = self.contagem.get(nome, 0) + 1
            self.estado = titulo
            print(banner('%s   <<<   %s' % (titulo, caminho)))
            print('   %s' % detalhe)
            print('   (aqui entraria o comando real nos motores)\n')
            resp.success = True
            resp.message = '%s executado (%dx nesta sessao)' % (titulo, self.contagem[nome])
            return resp

        return callback


def main():
    rclpy.init()
    no = PainelRobo()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
