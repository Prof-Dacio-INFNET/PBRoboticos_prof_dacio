from setuptools import setup
import os
from glob import glob

package_name = 'aula15_nav2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
        # O mapa pronto. Os dois arquivos, PGM e YAML, tem de cair na MESMA
        # pasta instalada: o `image:` do mapa.yaml e relativo a ela.
        # O gerar_mapa.py NAO e instalado de proposito -- e ferramenta de
        # preparacao do material, nao coisa que roda em tempo de execucao.
        (os.path.join('share', package_name, 'maps'),
         glob('maps/*.pgm') + glob('maps/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dacio Moreira de Souza',
    maintainer_email='dacioms@gmail.com',
    description='Nav2 sobre o mundo minimo: mapa conhecido, AMCL, NavFn e DWB.',
    license='MIT',
    entry_points={'console_scripts': [
        # O cliente de acao que cumpre a rota. E o item 1 do TP4 em 150 linhas.
        'rota = aula15_nav2.rota:main',
    ]},
)
