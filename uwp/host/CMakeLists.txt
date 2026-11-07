# UWP / Xbox Series Dev Mode host executable for Xash3D FWGS.
#
# Configure with:
#   cmake -G "Visual Studio 17 2022" -A x64 \
#         -DCMAKE_SYSTEM_NAME=WindowsStore -DCMAKE_SYSTEM_VERSION=10.0 \
#         -DSDL2_SOURCE_DIR=<SDL2 source> -DSDL2_LIBRARY=<path to UWP SDL2.lib>
#
# Only the executable is used from this project; packaging is done by
# scripts/gha/build_uwp.ps1 with MakeAppx, so the layout stays explicit.

cmake_minimum_required(VERSION 3.20)
project(xash3d_uwp CXX)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "WindowsStore")
	message(FATAL_ERROR "This project must be configured with -DCMAKE_SYSTEM_NAME=WindowsStore")
endif()

set(SDL2_SOURCE_DIR "" CACHE PATH "SDL2 source tree (for headers and the WinRT main)")
set(SDL2_LIBRARY "" CACHE FILEPATH "SDL2.lib import library built from VisualC-WinRT/SDL-UWP.vcxproj")

add_executable(xash3d_uwp WIN32
	main.cpp
	${SDL2_SOURCE_DIR}/src/main/winrt/SDL_winrt_main_NonXAML.cpp
)

# SDL's WinRT entry point must be compiled as C++/CX
set_target_properties(xash3d_uwp PROPERTIES VS_WINRT_COMPONENT TRUE)

target_include_directories(xash3d_uwp PRIVATE ${SDL2_SOURCE_DIR}/include)
target_link_libraries(xash3d_uwp PRIVATE ${SDL2_LIBRARY})
target_compile_definitions(xash3d_uwp PRIVATE _CRT_SECURE_NO_WARNINGS)
