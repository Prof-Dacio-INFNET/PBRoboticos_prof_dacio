from setuptools import setup
import os
from glob import glob

package_name = 'aula16_arvore'

# As arvores sao a fonte de leitura do exemplo e moram em
# `exemplos/aula16-arvore-bag/arvores/`, um nivel ACIMA deste pacote. O bloco
# de download as copia para dentro dele antes do `colcon build`, e e por isso
# que a busca tenta os dois lugares -- a pasta de fontes do material e a copia
# que vai para o workspace.
#
# O `raise` existe porque a falha silenciosa aqui e cruel: `glob` que nao acha
# nada devolve lista vazia, o `colcon build` passa limpo, o pacote instala sem
# nenhuma arvore, e o erro so aparece la na frente, no bt_navigator, como
# "Error loading XML file" com um caminho que existe na sua pasta de fontes.
ARVORES = sorted(glob('arvores/*.xml')) or sorted(glob('../arvores/*.xml'))
if not ARVORES:
    raise SystemExit(
        'nao achei nenhum XML em arvores/ nem em ../arvores/.\n'
        'O pacote precisa das arvores de comportamento ao lado dele:\n'
        '  cp -r <material>/exemplos/aula16-arvore-bag/arvores '
        '<workspace>/src/aula16_arvore/\n'
        'O bloco "Baixar" do README ja faz isso -- confira se ele rodou inteiro.')

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        # E o caminho INSTALADO que vai no parametro `arvore:=`: o bt_navigator
        # le o XML em tempo de execucao, e apontar para a pasta de fontes
        # funciona na sua maquina e quebra na do avaliador.
        (os.path.join('share', package_name, 'arvores'), ARVORES),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dacio Moreira de Souza',
    maintainer_email='dacioms@gmail.com',
    description='Arvore de comportamento, portao de obstaculo e analise de bag.',
    license='MIT',
    entry_points={'console_scripts': [
        # O portao de 0,5 m: cancela, espera 2 s, reenvia o mesmo objetivo.
        'vigia = aula16_arvore.vigia:main',
        # O bag virando CSV: assina os topicos com o bag tocando.
        'gravar_pose = aula16_arvore.gravar_pose:main',
    ]},
)
