cmake_minimum_required(VERSION 3.8)
project(agrobo_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Detection.msg"
  "msg/DetectionArray.msg"
  "msg/FieldState.msg"
  "msg/Fruit.msg"
  "msg/HarvestLot.msg"
  "msg/MarketTrade.msg"
  "msg/PlantState.msg"
  "msg/RobotStatus.msg"
  "msg/SensorFrame.msg"
  "msg/Weed.msg"
  "srv/AdvanceDay.srv"
  "srv/EvaluateParcels.srv"
  "srv/FieldInteract.srv"
  "srv/GetFieldState.srv"
  "srv/PlanCoverage.srv"
  "action/DoseNutrients.action"
  "action/HarvestRows.action"
  "action/HaulToHub.action"
  "action/PrepField.action"
  "action/ProcessLot.action"
  "action/ScoutField.action"
  "action/SellInventory.action"
  "action/Transplant.action"
  "action/WeedZone.action"
  DEPENDENCIES std_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
