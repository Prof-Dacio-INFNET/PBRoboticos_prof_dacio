"""Sobe a percepcao da Aula 6 e o servidor da action da Aula 7.

    ros2 launch aula07_acoes varredura.launch.py
    ros2 launch aula07_acoes varredura.launch.py classe:=tomate_maduro
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    classe = LaunchConfiguration('classe')
    return LaunchDescription([
        DeclareLaunchArgument('classe', default_value='objeto_alvo'),
        Node(package='aula06_percepcao', executable='detector', name='detector',
             output='screen', parameters=[{'fonte': 'sintetico', 'classe': classe}]),
        Node(package='aula07_acoes', executable='servidor_varredura',
             name='servidor_varredura', output='screen'),
    ])
