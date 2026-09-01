"""Demo 1 -- setas guiando a camera.

    ros2 launch demo_visual demo1.launch.py
    ros2 launch demo_visual demo1.launch.py janela:=false     # sem janela, so topico
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('dispositivo', default_value='0'),
        DeclareLaunchArgument('janela', default_value='true'),
        Node(package='demo_visual', executable='guia_visual', name='guia_visual',
             output='screen',
             parameters=[{'dispositivo': LaunchConfiguration('dispositivo'),
                          'janela': LaunchConfiguration('janela')}]),
    ])
