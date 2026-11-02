"""Sobe o `gravar_pose` sozinho, para rodar ao lado do `ros2 bag play`.

    ros2 launch aula16_arvore analise.launch.py
    ros2 launch aula16_arvore analise.launch.py saida:=sessao.csv hz:=10.0
    ros2 launch aula16_arvore analise.launch.py use_sim_time:=false

ADVERTENCIA: ESTE LAUNCH NAO FOI EXECUTADO. Nao havia ROS 2 na maquina em que
ele foi escrito. Ele passa no `ast.parse` e no `tools/conferir-launch.py` do
repositorio, e nada alem disso.

POR QUE ELE SOBE UM NO SO, e nao o Nav2 inteiro:

    Porque este launch e o da ANALISE, nao o da navegacao. O ponto do gate
    G4.4 e que a analise rode com o robo DESLIGADO: um terminal toca o bag,
    outro roda isto, e o CSV sai. Se este launch subisse o Nav2, voce teria
    dois AMCL publicando /amcl_pose -- o do bag e o que acabou de subir --,
    e ninguem reclamaria de nada. Dois publicadores no mesmo topico e o
    defeito recorrente desta disciplina: aconteceu com o /cmd_vel na Aula 15
    e com o map -> odom na Aula 12.

    A sequencia, em dois terminais:

      terminal 1:  ros2 launch aula16_arvore analise.launch.py
      terminal 2:  ros2 bag play minha-sessao --clock

    E quando o bag acabar, Ctrl-C no terminal 1. O CSV ja esta completo: o
    `gravar_pose` da flush em cada linha.

`use_sim_time` VEM `true` POR PADRAO, e isso e o contrario do resto do
material:

    Nos outros pacotes desta disciplina ele e `false`, porque nao ha Gazebo e
    ninguem publica /clock. Aqui e `true` porque quem publica o /clock e o
    proprio `ros2 bag play --clock`. Sem isso, o no carimba as linhas com o
    relogio de HOJE e os intervalos saem errados quando o bag toca em
    `--rate` diferente de 1.

    Se voce tocar o bag SEM `--clock`, passe `use_sim_time:=false` aqui --
    senao o no fica esperando um /clock que nunca chega e NAO GRAVA NADA, sem
    uma linha de erro. E o mesmo modo de falha do `use_sim_time: true` sem
    Gazebo da Aula 15, agora do outro lado.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    saida = LaunchConfiguration('saida')
    hz = LaunchConfiguration('hz')
    setor_graus = LaunchConfiguration('setor_graus')
    use_sim_time = LaunchConfiguration('use_sim_time')
    exigir_amcl = LaunchConfiguration('exigir_amcl')

    return LaunchDescription([
        DeclareLaunchArgument(
            'saida', default_value='sessao.csv',
            description='arquivo CSV de saida, relativo ao diretorio de onde '
                        'voce rodou o launch'),
        DeclareLaunchArgument(
            'hz', default_value='10.0',
            description='linhas por segundo no CSV (a taxa da retencao de '
                        'ordem zero)'),
        DeclareLaunchArgument(
            'setor_graus', default_value='60.0',
            description='meia-largura do setor frontal do /scan, em graus. '
                        'TEM DE SER O MESMO do vigia que gravou o bag, senao '
                        'a coluna dist_min_scan nao explica as interrupcoes'),
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='true com `ros2 bag play --clock`; false sem --clock'),
        DeclareLaunchArgument(
            'exigir_amcl', default_value='true',
            description='nao grava linha antes do primeiro /amcl_pose, para o '
                        'CSV nao comecar com uma perna falsa em (0, 0)'),
        Node(
            package='aula16_arvore',
            executable='gravar_pose',
            name='gravar_pose',
            output='screen',
            parameters=[{
                'saida': saida,
                'hz': hz,
                'setor_graus': setor_graus,
                'exigir_amcl': exigir_amcl,
                'use_sim_time': use_sim_time,
            }],
            # Os remapeamentos ficam explicitos ainda que sejam a identidade:
            # e aqui que voce muda se o seu robo publica em /scan_filtered ou
            # em /odometry/filtered (saida tipica do robot_localization).
            remappings=[
                ('odom', '/odom'),
                ('amcl_pose', '/amcl_pose'),
                ('scan', '/scan'),
                ('cmd_vel', '/cmd_vel'),
                ('estado_vigia', '/estado_vigia'),
            ],
        ),
    ])
