#!/usr/bin/env python3
"""O Behavioral Cloning dirigindo em malha fechada, medido pela MESMA regua do PID.

    PY="$PB_DIR/.venv-metadrive/bin/python"         # o venv do MetaDrive, NAO o da CNN
    $PY dirigir_bc.py --modelo modelo/pesos.npz --saida resultados/bc
    $PY dirigir_bc.py --modelo modelo/pesos.npz --episodios 3 --inverter-canais

E so um atalho para `avaliar.py --controlador bc`: o laco, as sementes, as
colunas e o resumo sao os do avaliar.py. O que este arquivo define e o
controlador: a cada passo ele pega o quadro da camera, prepara (rede.preparar),
passa pela rede em NumPy (rede.Rede) e devolve [direcao, acelerador]. O
acelerador e o mesmo do PID (pid.acelerador): so a direcao vem da rede.

OS DOIS VENVS. A rede foi treinada no venv do TensorFlow; aqui roda o venv do
MetaDrive, que nao tem TensorFlow. O treinar_bc.py exporta os pesos para um
.npz, e o rede.py refaz a conta em NumPy. Nada a instalar, nenhum servidor,
nenhum segundo processo -- e o testar.py confere que a conta bate com a do
Keras.

AS DUAS ARMADILHAS, para reproduzir de proposito:
    --inverter-canais   entrega RGB a uma rede que treinou com BGR (quem
                        converte "por garantia" com cv2.cvtColor ou [..., ::-1])
    --sem-normalizar    esquece o /255 que o treino fez dentro da rede
"""
import argparse
import sys
import time

import pid as piloto_pid
import rede


class PilotoBC:
    precisa_imagem = True

    def __init__(self, pesos, vel_alvo=piloto_pid.VEL_ALVO_KMH, inverter_canais=False,
                 sem_normalizar=False):
        self.rede = rede.Rede(pesos)
        self.vel_alvo = vel_alvo
        self.inverter, self.normalizar = inverter_canais, not sem_normalizar
        self.nome = 'bc %s%s' % ('(RGB!) ' if inverter_canais else '',
                                 '(sem /255!) ' if sem_normalizar else '')
        self.nome = self.nome.strip()
        self.ms = []

    def reiniciar(self):
        pass

    def agir(self, env, obs):
        quadro = obs['image'][..., -1]          # (120, 160, 3) uint8 BGR
        if self.inverter:
            quadro = quadro[..., ::-1]          # a armadilha: agora e RGB
        t0 = time.perf_counter()
        d = self.rede(rede.preparar(quadro), normalizar=self.normalizar)
        self.ms.append(1000.0 * (time.perf_counter() - t0))
        return [d, piloto_pid.acelerador(env.agent.speed_km_h, self.vel_alvo)]


def principal(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modelo', required=True, help='o pesos.npz do treinar_bc.py')
    p.add_argument('--episodios', type=int, default=10, help='(10)')
    p.add_argument('--semente-inicial', type=int, default=None,
                   help='(a do avaliar.py, 100)')
    p.add_argument('--inverter-canais', action='store_true')
    p.add_argument('--sem-normalizar', action='store_true')
    p.add_argument('--empurrao', type=float, default=0.0,
                   help='forca o volante a este valor por 1 s no inicio (o do avaliar.py)')
    p.add_argument('--trajetoria', help='CSV com desvio e direcao a cada passo')
    p.add_argument('--saida', help='grava SAIDA.csv e SAIDA-resumo.md')
    args = p.parse_args(argv)
    resto = ['--controlador', 'bc', '--modelo', args.modelo, '--episodios', str(args.episodios)]
    if args.semente_inicial is not None:
        resto += ['--semente-inicial', str(args.semente_inicial)]
    if args.inverter_canais:
        resto.append('--inverter-canais')
    if args.sem_normalizar:
        resto.append('--sem-normalizar')
    if args.empurrao:
        resto += ['--empurrao', str(args.empurrao)]
    if args.trajetoria:
        resto += ['--trajetoria', args.trajetoria]
    if args.saida:
        resto += ['--saida', args.saida]
    import avaliar
    return avaliar.principal(resto)


if __name__ == '__main__':
    sys.exit(principal())
