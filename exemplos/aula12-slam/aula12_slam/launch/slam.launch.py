"""O SLAM assume a aresta map -> odom.

    ros2 launch aula12_slam slam.launch.py
    ros2 launch aula12_slam slam.launch.py deriva:=6.0    # erro maior, correcao maior
    ros2 launch aula12_slam slam.launch.py rviz:=false

A unica diferenca estrutural em relacao a Aula 11 esta numa linha: o mundo sobe
com `map_odom:=false`. O placeholder sai, e quem passa a publicar map -> odom e'
o slam_toolbox -- agora com um valor CALCULADO, nao com identidade.

Dois publicadores da mesma aresta nao dao erro: dao arvore quebrada, que e' o
defeito mais caro do TP3. Se voce esquecer o map_odom:=false, o `view_frames`
mostra o estrago e o laser fica tremendo na tela.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('aula12_slam')
    mundo_pkg = get_package_share_directory('aula11_mundo')

    slam_params = LaunchConfiguration('slam_params')
    deriva = LaunchConfiguration('deriva')
    rviz = LaunchConfiguration('rviz')

    return LaunchDescription([
        DeclareLaunchArgument(
            'slam_params', default_value=os.path.join(pkg, 'config', 'slam.yaml'),
            description='YAML de parametros do slam_toolbox'),
        DeclareLaunchArgument(
            'deriva', default_value='3.0',
            description='erro sistematico da odometria, em % -- e o que o SLAM corrige'),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='abrir o RViz2 com o mapa do SLAM ao lado do mundo real'),

        # O mundo da Aula 11, SEM o placeholder de map -> odom.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(mundo_pkg, 'launch', 'mundo.launch.py')),
            launch_arguments={'map_odom': 'false',
                              'deriva': deriva,
                              'rviz': 'false'}.items(),
        ),

        # Quem passa a publicar map -> odom.
        Node(package='slam_toolbox', executable='async_slam_toolbox_node',
             name='slam_toolbox', output='screen',
             parameters=[slam_params]),

        Node(package='rviz2', executable='rviz2', name='rviz2',
             condition=IfCondition(rviz), output='screen',
             arguments=['-d', os.path.join(pkg, 'rviz', 'slam.rviz')]),
    ])
