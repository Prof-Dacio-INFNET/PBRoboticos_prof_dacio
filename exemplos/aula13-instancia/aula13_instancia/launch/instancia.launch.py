"""Sobe a cena e o segmentador de instancia, sem camera nenhuma.

    ros2 launch aula13_instancia instancia.launch.py
    ros2 launch aula13_instancia instancia.launch.py metodo:=cor_watershed
    ros2 launch aula13_instancia instancia.launch.py pasta:=/caminho/para/cena
    ros2 launch aula13_instancia instancia.launch.py fps:=1.0

O argumento `metodo` e a aula inteira em uma linha de comando: a MESMA mascara,
lida de dois jeitos. Suba com `cor_conectada`, abra o rqt_image_view e conte as
cores; suba com `cor_watershed` e conte de novo. O `/vision/instancias` diz o
numero, e a imagem diz por que ele e esse.

    ros2 topic echo /vision/instancias
    ros2 run rqt_image_view rqt_image_view /vision/segmented
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    metodo = LaunchConfiguration('metodo')
    pasta = LaunchConfiguration('pasta')
    fps = LaunchConfiguration('fps')
    params = os.path.join(
        get_package_share_directory('aula13_instancia'), 'config', 'instancia.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('metodo', default_value='cor_conectada',
                              description='cor_conectada | cor_watershed'),
        DeclareLaunchArgument('pasta', default_value='',
                              description='pasta com quadro*.png (padrao: ./cena)'),
        DeclareLaunchArgument('fps', default_value='4.0',
                              description='quadros por segundo da cena'),
        Node(package='aula13_instancia', executable='publicador_cena',
             name='publicador_cena', output='screen',
             # ParameterValue com value_type: sem isso o `fps:=1.0` chega como
             # STRING e o no reclama de tipo. Argumento de launch e sempre texto.
             parameters=[{'pasta': ParameterValue(pasta, value_type=str),
                          'fps': ParameterValue(fps, value_type=float)}]),
        # O YAML vem primeiro e o metodo depois: argumento de linha de comando
        # SOBREPOE o arquivo, que e o que se espera de quem digitou agora.
        Node(package='aula13_instancia', executable='segmentador_instancia',
             name='segmentador_instancia', output='screen',
             parameters=[params, {'metodo': ParameterValue(metodo, value_type=str)}]),
    ])
