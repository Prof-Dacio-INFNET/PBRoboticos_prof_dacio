"""Sobe os tres nos que fazem um URDF virar um robo na tela.

    ros2 launch meu_robo_description ver_robo.launch.py
    ros2 launch meu_robo_description ver_robo.launch.py gui:=false

Os tres papeis, e e importante nao confundi-los:

  robot_state_publisher  le o URDF, escuta /joint_states e PUBLICA A TF.
                         E ele que transforma "descricao" em "geometria viva".
  joint_state_publisher_gui  inventa /joint_states com sliders. Existe so para
                         voce mexer nas juntas sem ter robo nenhum. Num robo de
                         verdade, quem publica /joint_states sao os encoders.
  rviz2                  so DESENHA. Nao calcula nada. Se algo nao aparece, o
                         problema quase nunca esta nele.
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
    pkg = get_package_share_directory('meu_robo_description')
    urdf = os.path.join(pkg, 'urdf', 'meu_robo.urdf')
    rviz = os.path.join(pkg, 'rviz', 'meu_robo.rviz')
    gui = LaunchConfiguration('gui')

    # ParameterValue com value_type=str: sem isso o launch tenta adivinhar o
    # tipo do XML e o robot_state_publisher recebe lixo. Erro classico.
    descricao = ParameterValue(Command(['cat ', urdf]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true',
                              description='sliders para mover as juntas'),

        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', output='screen',
             parameters=[{'robot_description': descricao}]),

        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui',
             name='joint_state_publisher_gui', condition=IfCondition(gui)),

        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', rviz], output='screen'),
    ])
