"""Sobe a cena e o segmentador de instancia, sem camera nenhuma.

    ros2 launch aula13_instancia instancia.launch.py
    ros2 launch aula13_instancia instancia.launch.py metodo:=cor_watershed
    ros2 launch aula13_instancia instancia.launch.py saida:=instancia
    ros2 launch aula13_instancia instancia.launch.py rviz:=true
    ros2 launch aula13_instancia instancia.launch.py pasta:=/caminho/para/cena
    ros2 launch aula13_instancia instancia.launch.py fps:=1.0

Dois argumentos, duas perguntas diferentes:

  metodo   QUAL algoritmo separa as instancias (cor_conectada, cor_watershed,
           modelo). E a aula inteira em uma linha: a MESMA mascara, lida de
           dois jeitos. Suba com `cor_conectada` e conte; suba com
           `cor_watershed` e conte de novo.
  saida    QUAL figura vai no /vision/segmented (classe_alpha -- o padrao, o
           que o item 3 do enunciado do TP3 pede --, instancia, mascara).

Para VER a imagem, duas estradas. O RViz2 e o que o enunciado pede:

    ros2 launch aula13_instancia instancia.launch.py rviz:=true
    ros2 topic echo /vision/instancias
    ros2 run rqt_image_view rqt_image_view /vision/segmented   # alternativa

No RViz2 avulso: Add -> Image, topico /vision/segmented, e o display em
"Best Effort" -- este no publica imagem como dado de sensor, e um display
que pede RELIABLE fica em branco SEM dar erro. O rviz/segmentacao.rviz
deste pacote (rviz:=true) ja vem com isso resolvido.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    metodo = LaunchConfiguration('metodo')
    saida = LaunchConfiguration('saida')
    alpha = LaunchConfiguration('alpha')
    rviz = LaunchConfiguration('rviz')
    pasta = LaunchConfiguration('pasta')
    fps = LaunchConfiguration('fps')
    pkg = get_package_share_directory('aula13_instancia')
    params = os.path.join(pkg, 'config', 'instancia.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('metodo', default_value='cor_conectada',
                              description='cor_conectada | cor_watershed | modelo'),
        DeclareLaunchArgument('saida', default_value='classe_alpha',
                              description='classe_alpha | instancia | mascara'),
        DeclareLaunchArgument('alpha', default_value='0.5',
                              description='transparencia da camada por classe (0 a 1)'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='abrir o RViz2 ja com o display Image do '
                                          '/vision/segmented em Best Effort'),
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
        # O YAML vem primeiro e os argumentos depois: linha de comando
        # SOBREPOE o arquivo, que e o que se espera de quem digitou agora.
        Node(package='aula13_instancia', executable='segmentador_instancia',
             name='segmentador_instancia', output='screen',
             parameters=[params,
                         {'metodo': ParameterValue(metodo, value_type=str),
                          'saida': ParameterValue(saida, value_type=str),
                          'alpha': ParameterValue(alpha, value_type=float)}]),
        # O frame `camera` existir e' o que tira o "Global Status: Warn" do
        # RViz2. As imagens nao precisam de TF para aparecer -- o aviso vem do
        # Fixed Frame, que e' do mundo 3D --, mas painel amarelo numa aula que
        # ensina a desconfiar de aviso e' ruido caro: o aluno passa a ignorar
        # amarelo, e o proximo amarelo vai ser de verdade. Pai `world` de
        # proposito: `map` e' do SLAM, e colidir com ele seria pior que o aviso.
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='tf_camera', output='log',
             condition=IfCondition(rviz),
             arguments=['0', '0', '0', '0', '0', '0', 'world', 'camera']),
        # rviz:=true abre o RViz2 com o display Image ja apontado e em
        # Best Effort. Fica desligado por padrao para o launch continuar
        # subindo em maquina sem tela (CI, servidor, WSL sem X).
        Node(package='rviz2', executable='rviz2', name='rviz2',
             condition=IfCondition(rviz), output='screen',
             arguments=['-d', os.path.join(pkg, 'rviz', 'segmentacao.rviz')]),
    ])
