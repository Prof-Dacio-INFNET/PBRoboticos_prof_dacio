from setuptools import setup
import os
from glob import glob

package_name = 'aula06_percepcao'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dacio Moreira de Souza',
    maintainer_email='dacioms@gmail.com',
    description='Percepcao publicando interfaces proprias -- Aula 6, Etapa 3.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'detector = aula06_percepcao.detector:main',
            'monitor  = aula06_percepcao.monitor:main',
        ],
    },
)
