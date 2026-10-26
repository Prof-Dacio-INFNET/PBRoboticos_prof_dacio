"""O Nav2 sobre o mundo da Aula 11: mapa conhecido, AMCL, planejador, DWB.

    ros2 launch aula15_nav2 nav2.launch.py
    ros2 launch aula15_nav2 nav2.launch.py --show-args
    ros2 launch aula15_nav2 nav2.launch.py rviz:=true
    ros2 launch aula15_nav2 nav2.launch.py mapa:=$PB_DIR/maps/mapa.yaml
    ros2 launch aula15_nav2 nav2.launch.py pose_inicial_auto:=true
    ros2 launch aula15_nav2 nav2.launch.py deriva:=6.0

ADVERTENCIA, e ela vale para o pacote inteiro: NADA DISTO FOI EXECUTADO. Nao
havia ROS 2 na maquina em que este arquivo foi escrito -- sem colcon build, sem
ros2 launch, sem Nav2 no ar. Os nomes de no, de executavel, de parametro e de
plugin foram conferidos contra a FONTE do nav2_bringup do Humble (as URLs estao
no README-pacote.md). A ordem em que as pecas sobem e a estrutura sao copia do
bringup oficial. Mas o sistema inteiro nunca rodou junto, e a primeira execucao
e sua.

O QUE ESTE LAUNCH MONTA, em ordem:

    1. o mundo da Aula 11, com `map_odom:=false`
       Igual ao slam.launch.py da Aula 12, e pelo mesmo motivo: o placeholder
       de map -> odom tem de sair, porque agora quem publica essa aresta e o
       AMCL. Dois publicadores da mesma aresta nao dao erro -- dao arvore
       quebrada e laser tremendo, que e o defeito mais caro do TP4.
       Vai tambem com `piloto:=false`, e pelo mesmo tipo de motivo: o piloto
       reativo da Aula 11 publica /cmd_vel, o Nav2 publica /cmd_vel, e dois
       publicadores no mesmo topico TAMBEM nao dao erro -- dao um robo que
       obedece ao ultimo que falou. O sintoma e andar truncado, nunca uma
       mensagem. Confira com `ros2 topic info /cmd_vel --verbose`: com este
       launch tem de aparecer UM publicador, o velocity_smoother.

    2. map_server       le o mapa.yaml e publica /map (transient local)
    3. amcl             publica map -> odom, calculado a partir do /scan
    4. lifecycle_manager_localization   ativa os dois acima, nesta ordem

    5. controller_server (DWB), smoother_server, planner_server (NavFn),
       behavior_server, waypoint_follower, velocity_smoother
    6. lifecycle_manager_navigation     ativa os seis acima, nesta ordem

    7. rviz2            so com rviz:=true

A arvore de TF que resulta:

    map -> odom           o AMCL, corrigindo a deriva da odometria
    odom -> base_footprint    o no `mundo` da Aula 11 (com deriva)
    base_footprint -> laser_frame      transformada estatica
    base_footprint -> ...     o robot_state_publisher, se modelo:=true

A CADEIA DO /cmd_vel, que e a parte que mais confunde:

    controller_server  publica cmd_vel, remapeado para /cmd_vel_nav
    velocity_smoother  ouve /cmd_vel_nav, publica /cmd_vel
    no `mundo`         ouve /cmd_vel

Os dois remapeamentos abaixo sao os MESMOS do navigation_launch.py do Humble.
Se voce tirar o velocity_smoother sem desfazer os remapeamentos, o
controller_server fica falando em /cmd_vel_nav e ninguem ouve: o robo nao anda
e nenhum no reclama.

POSE INICIAL -- a decisao pedagogica deste launch:

    O padrao e MANUAL. O AMCL sobe esperando, e quem da a pose e voce, com o
    "2D Pose Estimate" do RViz2. Pose inicial errada e o erro classico do G4.0,
    e vale fazer o gesto com a mao pelo menos uma vez: a nuvem de particulas
    nasce onde voce clicou, e voce VE ela se fechar (ou nao) nos primeiros
    metros.

    `pose_inicial_auto:=true` sobrepoe o `set_initial_pose` do AMCL e entrega a
    pose de largada do robo na Aula 11 -- (2,0 ; 4,0 ; 0,0). Serve para repetir
    um teste sem reclicar, e para rodar sem tela. Use depois de ter feito o
    gesto pelo menos uma vez.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# Os dois gerenciadores de ciclo de vida, com as MESMAS listas do
# localization_launch.py e do navigation_launch.py do Humble. A ordem importa:
# o gerenciador configura e ativa um no por vez, nesta sequencia.
#
# Se um nome aqui nao corresponder a um no realmente no ar, o gerenciador fica
# preso esperando e o Nav2 inteiro para em "Configuring" -- sem mensagem de
# erro, apenas silencio. E o jeito numero um de perder uma hora.
NOS_LOCALIZACAO = ['map_server', 'amcl']
NOS_NAVEGACAO = ['controller_server', 'smoother_server', 'planner_server',
                 'behavior_server', 'bt_navigator', 'waypoint_follower',
                 'velocity_smoother']


def generate_launch_description():
    pkg = get_package_share_directory('aula15_nav2')
    mundo_pkg = get_package_share_directory('aula11_mundo')

    params = LaunchConfiguration('params')
    mapa = LaunchConfiguration('mapa')
    rviz = LaunchConfiguration('rviz')
    deriva = LaunchConfiguration('deriva')
    modelo = LaunchConfiguration('modelo')
    autostart = LaunchConfiguration('autostart')
    pose_auto = LaunchConfiguration('pose_inicial_auto')
    pose_x = LaunchConfiguration('pose_x')
    pose_y = LaunchConfiguration('pose_y')
    pose_yaw = LaunchConfiguration('pose_yaw')

    # `use_sim_time` e `autostart` vao fora do YAML porque sao decisao de
    # EXECUCAO, nao de robo. O YAML tem use_sim_time: false em todos os nos; se
    # um dia voce entrar com Gazebo, troca-se no YAML e nos gerenciadores.
    comum = {'use_sim_time': False}

    # Remapeamento de /tf e /tf_static, que o nav2_bringup faz, NAO esta aqui:
    # ele existe para o Nav2 funcionar dentro de namespace, e este launch nao
    # usa namespace. Com namespace vazio o remapeamento e identidade -- ruido.
    #
    # Estes dois, ao contrario, sao estruturais (ver o docstring).
    remap_controlador = [('cmd_vel', 'cmd_vel_nav')]
    remap_suavizador = [('cmd_vel', 'cmd_vel_nav'),
                        ('cmd_vel_smoothed', 'cmd_vel')]

    # A pose inicial, sobreposta sobre o YAML. Vem DEPOIS do arquivo na lista
    # de `parameters`, e por isso ganha dele -- o que se espera de quem digitou
    # agora. `value_type` nao e detalhe: argumento de launch e sempre texto, e
    # sem a coercao o AMCL recebe a string "false" e reclama de tipo.
    pose_inicial = {
        'set_initial_pose': ParameterValue(pose_auto, value_type=bool),
        'initial_pose.x': ParameterValue(pose_x, value_type=float),
        'initial_pose.y': ParameterValue(pose_y, value_type=float),
        'initial_pose.yaw': ParameterValue(pose_yaw, value_type=float),
    }

    return LaunchDescription([
        DeclareLaunchArgument(
            'mapa', default_value=os.path.join(pkg, 'maps', 'mapa.yaml'),
            description='caminho do .yaml do mapa estatico; o padrao e o mapa '
                        'embutido, gerado da grade da Aula 11'),
        DeclareLaunchArgument(
            'params', default_value=os.path.join(pkg, 'config', 'nav2.yaml'),
            description='YAML de parametros do Nav2'),
        DeclareLaunchArgument(
            'rviz', default_value='false',
            description='abrir o RViz2 com a nuvem de particulas e os costmaps; '
                        'fica false para o launch subir em maquina sem tela'),
        DeclareLaunchArgument(
            'deriva', default_value='3.0',
            description='erro sistematico da odometria, em % -- e o que o AMCL '
                        'tem de corrigir para a navegacao fechar'),
        DeclareLaunchArgument(
            'modelo', default_value='true',
            description='subir o URDF da Aula 9 (precisa de meu_robo_description); '
                        'ponha false em maquina que nao tem o pacote'),
        DeclareLaunchArgument(
            'autostart', default_value='true',
            description='ativar os nos do Nav2 automaticamente; com false voce '
                        'faz a transicao a mao com `ros2 lifecycle set`'),
        DeclareLaunchArgument(
            'pose_inicial_auto', default_value='false',
            description='true entrega a pose inicial ao AMCL pelo parametro; '
                        'false (padrao) espera o seu "2D Pose Estimate" no RViz2'),
        DeclareLaunchArgument(
            'pose_x', default_value='2.0',
            description='x da pose inicial, usado so com pose_inicial_auto:=true'),
        DeclareLaunchArgument(
            'pose_y', default_value='4.0',
            description='y da pose inicial, usado so com pose_inicial_auto:=true'),
        DeclareLaunchArgument(
            'pose_yaw', default_value='0.0',
            description='yaw da pose inicial, em rad, com pose_inicial_auto:=true'),

        # --------------------------------------------------------------- 1
        # O mundo da Aula 11, SEM o placeholder de map -> odom e SEM o piloto
        # reativo -- os dois seriam publicador duplicado de algo que o Nav2
        # publica (a aresta map -> odom e o /cmd_vel). O `rviz:=false` e fixo:
        # quem abre o RViz2 aqui e este launch, com a configuracao deste
        # pacote. Os parametros do mundo ficam os da Aula 11: com o piloto
        # fora, nao ha nada a ajustar nele por causa do Nav2.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(mundo_pkg, 'launch', 'mundo.launch.py')),
            launch_arguments={'map_odom': 'false',
                              'piloto': 'false',
                              'deriva': deriva,
                              'modelo': modelo,
                              'rviz': 'false'}.items(),
        ),

        # --------------------------------------------------------------- 2
        # O mapa estatico. `yaml_filename` vem do argumento `mapa:=` e
        # sobrepoe o valor vazio do YAML.
        Node(package='nav2_map_server', executable='map_server', name='map_server',
             output='screen',
             parameters=[params, comum,
                         {'yaml_filename': ParameterValue(mapa, value_type=str)}]),

        # --------------------------------------------------------------- 3
        # Quem passa a publicar map -> odom. Na Aula 12 era o slam_toolbox,
        # construindo o mapa; aqui o mapa ja existe e o trabalho e so se achar
        # dentro dele. Mesma aresta, problema diferente.
        Node(package='nav2_amcl', executable='amcl', name='amcl',
             output='screen',
             parameters=[params, comum, pose_inicial]),

        # --------------------------------------------------------------- 4
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_localization', output='screen',
             parameters=[comum,
                         {'autostart': ParameterValue(autostart, value_type=bool)},
                         {'node_names': NOS_LOCALIZACAO},
                         # 10 s em vez dos 4 s padrao: na WSL2 um no lento na
                         # ativacao faz o gerenciador declarar o bond perdido e
                         # DERRUBAR o Nav2 inteiro. O sintoma e tudo subir e
                         # morrer uns segundos depois.
                         {'bond_timeout': 10.0}]),

        # --------------------------------------------------------------- 5
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server', output='screen',
             parameters=[params, comum], remappings=remap_controlador),
        Node(package='nav2_smoother', executable='smoother_server',
             name='smoother_server', output='screen',
             parameters=[params, comum]),
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen',
             parameters=[params, comum]),
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen',
             parameters=[params, comum]),
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen',
             parameters=[params, comum]),
        Node(package='nav2_waypoint_follower', executable='waypoint_follower',
             name='waypoint_follower', output='screen',
             parameters=[params, comum]),
        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             name='velocity_smoother', output='screen',
             parameters=[params, comum], remappings=remap_suavizador),

        # --------------------------------------------------------------- 6
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[comum,
                         {'autostart': ParameterValue(autostart, value_type=bool)},
                         {'node_names': NOS_NAVEGACAO},
                         {'bond_timeout': 10.0}]),

        # --------------------------------------------------------------- 7
        # O "-d" nao e detalhe: sem ele o rviz2 abre com Grid e mais nada, a
        # janela parece vazia, e o aluno conclui que o sistema nao subiu.
        Node(package='rviz2', executable='rviz2', name='rviz2',
             condition=IfCondition(rviz), output='screen',
             arguments=['-d', os.path.join(pkg, 'rviz', 'nav2.rviz')]),
    ])
