"""Sobe o pipeline de visão inteiro com um comando.

    ros2 launch aula03_visao visao.launch.py                 # fonte sintética
    ros2 launch aula03_visao visao.launch.py fonte:=webcam   # webcam (usbipd no WSL2)
    ros2 launch aula03_visao visao.launch.py monitor:=true   # + cliente do serviço
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    fonte = LaunchConfiguration('fonte')
    monitor = LaunchConfiguration('monitor')
    params = os.path.join(
        get_package_share_directory('aula03_visao'), 'config', 'segmentacao.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('fonte', default_value='sintetico',
                              description='sintetico | webcam | video'),
        DeclareLaunchArgument('monitor', default_value='false',
                              description='sobe tambem o cliente do /vision/status'),
        Node(package='aula03_visao', executable='publicador_camera',
             name='publicador_camera', output='screen',
             parameters=[{'fonte': fonte}]),
        Node(package='aula03_visao', executable='segmentador_hsv',
             name='segmentador_hsv', output='screen',
             parameters=[params]),
        Node(package='aula03_visao', executable='monitor',
             name='monitor', output='screen',
             condition=IfCondition(monitor)),
    ])
