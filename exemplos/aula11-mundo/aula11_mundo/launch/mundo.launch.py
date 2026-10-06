"""Sobe o mundo inteiro com um comando -- o mesmo formato que o G3.0 cobra.

    ros2 launch aula11_mundo mundo.launch.py
    ros2 launch aula11_mundo mundo.launch.py --show-args
    ros2 launch aula11_mundo mundo.launch.py deriva:=0.0      # odometria perfeita
    ros2 launch aula11_mundo mundo.launch.py modelo:=false    # sem o URDF da Aula 9
    ros2 launch aula11_mundo mundo.launch.py rviz:=true

A arvore de TF que isto produz e' exatamente a que o G3.2 pede:

    map -> odom -> base_footprint -> (links do URDF) -> camera_link
                                  -> laser_frame

Quem publica o que, e e' isto que precisa estar claro antes do SLAM:

    map -> odom          ESTE LAUNCH, por enquanto, como identidade fixa.
                         Sai com map_odom:=false, que e' o que a Aula 12 faz
                         quando o slam_toolbox assume a aresta.
                         E' um PLACEHOLDER. No TP3 quem publica e' o SLAM, e a
                         identidade vira correcao -- e' esse o trabalho dele.
    odom -> base_footprint   o no `mundo`, integrando a odometria (com deriva).
    base_footprint -> ...    o robot_state_publisher, lendo o URDF.
    base_footprint -> laser  transformada estatica: o sensor nao se mexe.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('aula11_mundo')
    padrao = os.path.join(pkg, 'config', 'mundo.yaml')
    config_rviz = os.path.join(pkg, 'rviz', 'mundo.rviz')

    params = LaunchConfiguration('params')
    deriva = LaunchConfiguration('deriva')
    modelo = LaunchConfiguration('modelo')
    rviz = LaunchConfiguration('rviz')

    try:
        desc = get_package_share_directory('meu_robo_description')
        urdf = os.path.join(desc, 'urdf', 'meu_robo.urdf')
    except Exception:
        urdf = ''

    acoes = [
        DeclareLaunchArgument('params', default_value=padrao,
                              description='YAML de parametros'),
        DeclareLaunchArgument('deriva', default_value='3.0',
                              description='erro sistematico da odometria, em %'),
        DeclareLaunchArgument('modelo', default_value='true',
                              description='subir o URDF (precisa de meu_robo_description)'),
        DeclareLaunchArgument('map_odom', default_value='true',
                              description='publicar o placeholder map->odom; '
                                          'ponha false quando o SLAM assumir'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='abrir o RViz2 ja configurado (o G3.2 nao depende dele)'),

        Node(package='aula11_mundo', executable='mundo', name='mundo',
             output='screen',
             parameters=[params, {'deriva_pct': ParameterValue(deriva, value_type=float)}]),

        Node(package='aula11_mundo', executable='piloto', name='piloto',
             output='screen', parameters=[params]),

        # PLACEHOLDER: quem publica map -> odom de verdade e' o slam_toolbox.
        # Enquanto e' identidade, o robo "acredita" na propria odometria --
        # e e' por isso que o laser desliza para fora das paredes.
        #
        # Dois publicadores da MESMA aresta quebram a arvore, entao quando o
        # SLAM entrar este no tem de sair: suba com map_odom:=false.
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='map_para_odom',
             condition=IfCondition(LaunchConfiguration('map_odom')),
             arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']),

        Node(package='tf2_ros', executable='static_transform_publisher',
             name='base_para_laser',
             arguments=['0.10', '0', '0.18', '0', '0', '0',
                        'base_footprint', 'laser_frame']),
    ]

    if urdf:
        descricao = ParameterValue(Command(['cat ', urdf]), value_type=str)
        acoes.append(
            Node(package='robot_state_publisher', executable='robot_state_publisher',
                 name='robot_state_publisher', output='screen',
                 condition=IfCondition(modelo),
                 parameters=[{'robot_description': descricao}]))

    # O "-d" nao e' detalhe: sem ele o rviz2 abre com Grid e mais nada, a
    # janela parece vazia, e o aluno conclui que o sistema nao subiu.
    acoes.append(
        Node(package='rviz2', executable='rviz2', name='rviz2',
             condition=IfCondition(rviz), output='screen',
             arguments=['-d', config_rviz]))

    return LaunchDescription(acoes)
