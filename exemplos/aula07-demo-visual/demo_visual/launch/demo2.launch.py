"""Demo 2 -- folhas impressas disparando servicos.

    ros2 launch demo_visual demo2.launch.py
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('dispositivo', default_value='0'),
        DeclareLaunchArgument('janela', default_value='true'),
        Node(package='demo_visual', executable='painel_robo', name='painel_robo',
             output='screen'),
        Node(package='demo_visual', executable='detector_marcadores',
             name='detector_marcadores', output='screen',
             parameters=[{'dispositivo': LaunchConfiguration('dispositivo'),
                          'janela': LaunchConfiguration('janela')}]),
    ])
