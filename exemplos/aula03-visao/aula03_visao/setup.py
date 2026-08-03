from setuptools import setup
package_name = 'aula03_visao'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/'+package_name]),
        ('share/'+package_name, ['package.xml']),
        ('share/'+package_name+'/launch', ['launch/visao.launch.py']),
        ('share/'+package_name+'/config', ['config/segmentacao.yaml']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Prof. Dacio', maintainer_email='dacioms@exemplo.com',
    description='Aula 3: pipeline de visao (camera -> segmentacao HSV -> contagem + servico)',
    license='MIT',
    entry_points={'console_scripts': [
        'publicador_camera = aula03_visao.publicador_camera:main',
        'segmentador_hsv = aula03_visao.segmentador_hsv:main',
        'monitor = aula03_visao.monitor:main',
        'amostrar_hsv = aula03_visao.amostrar_hsv:main',
    ]},
)
