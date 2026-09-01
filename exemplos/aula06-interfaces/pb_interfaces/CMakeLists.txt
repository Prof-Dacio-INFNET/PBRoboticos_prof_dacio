cmake_minimum_required(VERSION 3.8)
project(pb_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)          # por causa do Header em Deteccoes.msg
find_package(action_msgs REQUIRED)       # toda action depende deste

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Deteccao.msg"
  "msg/Deteccoes.msg"
  "msg/ComandoMovimento.msg"              # Aula 7: a fronteira perceber/agir
  "srv/StatusVisao.srv"
  "action/VarrerCena.action"             # acrescentado na Aula 7: o pacote CRESCE
  DEPENDENCIES std_msgs action_msgs      # esqueca e o Header ou a action nao resolvem
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
