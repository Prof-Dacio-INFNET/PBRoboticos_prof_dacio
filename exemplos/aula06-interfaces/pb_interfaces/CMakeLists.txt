cmake_minimum_required(VERSION 3.8)
project(pb_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)          # por causa do Header em Deteccoes.msg

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Deteccao.msg"
  "msg/Deteccoes.msg"
  "srv/StatusVisao.srv"
  DEPENDENCIES std_msgs                  # esqueca esta linha e o Header nao resolve
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
