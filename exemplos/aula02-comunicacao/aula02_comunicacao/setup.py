from setuptools import setup
package_name = 'aula02_comunicacao'
setup(
    name=package_name, version='0.1.0', packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/'+package_name]),
        ('share/'+package_name, ['package.xml']),
        ('share/'+package_name+'/launch', ['launch/comunicacao.launch.py']),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Prof. Dacio', maintainer_email='dacioms@exemplo.com',
    description='Aula 2: pub/sub + serviço', license='MIT',
    entry_points={'console_scripts': [
        'publicador = aula02_comunicacao.publicador:main',
        'assinante = aula02_comunicacao.assinante:main',
        'servico_contagem = aula02_comunicacao.servico_contagem:main',
    ]},
)
