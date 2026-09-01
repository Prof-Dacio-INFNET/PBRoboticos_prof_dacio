from setuptools import setup
import os
from glob import glob

package_name = 'demo_visual'

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
    description='Demos de abertura da Aula 7: setas de movimento e marcadores impressos.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'guia_visual        = demo_visual.guia_visual:main',
            'detector_marcadores = demo_visual.detector_marcadores:main',
            'painel_robo        = demo_visual.painel_robo:main',
        ],
    },
)
