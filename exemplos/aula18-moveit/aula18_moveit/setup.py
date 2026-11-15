from setuptools import setup

package_name = 'aula18_moveit'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dacio Moreira de Souza',
    maintainer_email='dacioms@gmail.com',
    description='MoveIt 2 pelo rclpy: Collision Object, tres poses e pick-and-place no Panda.',
    license='MIT',
    entry_points={'console_scripts': [
        # A caixa (Collision Object) na frente do Panda: acao:=adicionar|remover.
        'cena = aula18_moveit.cena:main',
        # As tres poses do efetuador, planejadas e executadas, com ou sem a caixa.
        'tres_poses = aula18_moveit.tres_poses:main',
        # ROTEIRO, nunca executado: pre-pegada, pegada, anexar, levar, soltar.
        'pegar_e_soltar = aula18_moveit.pegar_e_soltar:main',
    ]},
)
