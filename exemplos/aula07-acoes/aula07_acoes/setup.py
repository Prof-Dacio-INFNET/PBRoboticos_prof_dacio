from setuptools import setup
import os
from glob import glob

package_name = 'aula07_acoes'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dacio Moreira de Souza',
    maintainer_email='dacioms@gmail.com',
    description='Acoes ROS 2: tarefa longa, feedback e cancelamento -- Aula 7.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'servidor_varredura = aula07_acoes.servidor_varredura:main',
            'cliente_varredura  = aula07_acoes.cliente_varredura:main',
        ],
    },
)
