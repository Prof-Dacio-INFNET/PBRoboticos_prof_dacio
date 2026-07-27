"""Sobe os 3 nós de uma vez — base para o bringup do seu projeto."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='aula02_comunicacao', executable='publicador'),
        Node(package='aula02_comunicacao', executable='assinante'),
        Node(package='aula02_comunicacao', executable='servico_contagem'),
    ])
