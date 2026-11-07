cmake_minimum_required(VERSION 3.15)
project(MQTTMotorController)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Platform-specific vcpkg paths
if(WIN32)
    if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
        set(CMAKE_TOOLCHAIN_FILE "C:/vcpkg/scripts/buildsystems/vcpkg.cmake"
            CACHE STRING "")
    endif()
elseif(APPLE)
    if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
        set(CMAKE_TOOLCHAIN_FILE "$ENV{HOME}/vcpkg/scripts/buildsystems/vcpkg.cmake"
            CACHE STRING "")
    endif()
endif()

# Enable vcpkg manifest mode if vcpkg.json exists
if(EXISTS "${CMAKE_SOURCE_DIR}/vcpkg.json")
    set(VCPKG_MANIFEST_DIR "${CMAKE_SOURCE_DIR}")
endif()

# Find required packages
find_package(eclipse-paho-mqtt-c REQUIRED)
find_package(PahoMqttCpp REQUIRED)
find_package(nlohmann_json REQUIRED)

# Add executable
add_executable(mqtt_app src/client.cpp)

# Link libraries
target_link_libraries(mqtt_app 
    PRIVATE 
    PahoMqttCpp::paho-mqttpp3
    nlohmann_json::nlohmann_json
)

# Windows-specific: copy DLLs to output directory
if(WIN32)
    add_custom_command(TARGET mqtt_app POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:PahoMqttCpp::paho-mqttpp3>
        $<TARGET_FILE_DIR:mqtt_app>
    )
endif()