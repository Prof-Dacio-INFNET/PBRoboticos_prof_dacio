from setuptools import setup
package_name = 'aula13_instancia'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/'+package_name]),
        ('share/'+package_name, ['package.xml']),
        ('share/'+package_name+'/launch', ['launch/instancia.launch.py']),
        ('share/'+package_name+'/config', ['config/instancia.yaml']),
        ('share/'+package_name+'/rviz', ['rviz/segmentacao.rviz']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Prof. Dacio', maintainer_email='dacioms@exemplo.com',
    description='Aula 13: da mascara a instancia (contagem, fusao e separacao)',
    license='MIT',
    entry_points={'console_scripts': [
        'publicador_cena = aula13_instancia.publicador_cena:main',
        'segmentador_instancia = aula13_instancia.segmentador_instancia:main',
    ]},
)
