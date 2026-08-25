"""Sobe o detector e o monitor.

    ros2 launch aula06_percepcao percepcao.launch.py
    ros2 launch aula06_percepcao percepcao.launch.py fonte:=topico classe:=tomate_maduro
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    fonte = LaunchConfiguration('fonte')
    classe = LaunchConfiguration('classe')
    return LaunchDescription([
        DeclareLaunchArgument('fonte', default_value='sintetico',
                              description='sintetico | topico'),
        DeclareLaunchArgument('classe', default_value='objeto_alvo',
                              description='rotulo do seu dominio'),
        Node(package='aula06_percepcao', executable='detector', name='detector',
             output='screen',
             parameters=[{'fonte': fonte, 'classe': classe}]),
        Node(package='aula06_percepcao', executable='monitor', name='monitor_deteccoes',
             output='screen'),
    ])
