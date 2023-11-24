set(OP_NAME place_io)

set(CMAKE_DEPENDS_IN_PROJECT_ONLY ON)

set(TARGET_NAME ${OP_NAME})

set(INCLUDE_DIRS 
  ${CMAKE_CURRENT_SOURCE_DIR}/..
  ${LIMBO_SOURCE_DIR}
  ${Boost_INCLUDE_DIRS}
  ${ZLIB_INCLUDE_DIRS}
  )

set(LINK_LIBS 
  #draw_place_cxx
  utility_cxx
  # begin targets in Limbo 
  lefparseradapt
  defparseradapt
  verilogparser
  bookshelfparser
  gdsparser
  programoptions
  gzstream
  # end targets in Limbo 
  OpenMP::OpenMP_CXX
  ${ZLIB_LIBRARIES}
  )

if(CAIRO_FOUND)
  set(INCLUDE_DIRS ${INCLUDE_DIRS} ${CAIRO_INCLUDE_DIRS})
  set(LINK_LIBS ${LINK_LIBS} ${CAIRO_LIBRARIES})
  set(DRAWPLACE 1)
else()
  set(DRAWPLACE 0)
endif()

add_library(${TARGET_NAME}_cpp_a STATIC   
  src/BenchMetrics.cpp  
  src/BinMap.cpp  
  src/Enums.cpp  
  src/Net.cpp  
  src/Node.cpp  
  src/Region.cpp  
  src/Group.cpp  
  src/Params.cpp  
  src/PlaceDB.cpp  
  src/DefWriter.cpp
  src/BookshelfWriter.cpp
  src/Dataflow.cpp)
target_include_directories(${TARGET_NAME}_cpp_a PRIVATE ${INCLUDE_DIRS})
target_link_libraries(${TARGET_NAME}_cpp_a PRIVATE ${LINK_LIBS} ${TORCH_LIBRARIES})

install(TARGETS 
  ${TARGET_NAME}_cpp_a 
  DESTINATION dreamplace/ops/${OP_NAME})

add_library(${TARGET_NAME}_cpp_so SHARED   
  src/BenchMetrics.cpp  
  src/BinMap.cpp  
  src/Enums.cpp  
  src/Net.cpp  
  src/Node.cpp  
  src/Region.cpp  
  src/Group.cpp  
  src/Params.cpp  
  src/PlaceDB.cpp  
  src/DefWriter.cpp
  src/BookshelfWriter.cpp
  src/Dataflow.cpp
  )
target_include_directories(${TARGET_NAME}_cpp_so PRIVATE ${INCLUDE_DIRS})
target_link_libraries(${TARGET_NAME}_cpp_so PRIVATE ${LINK_LIBS} ${TORCH_LIBRARIES})

install(TARGETS 
  ${TARGET_NAME}_cpp_so 
  DESTINATION dreamplace/ops/${OP_NAME})
install(TARGETS 
  ${TARGET_NAME}_cpp_so 
  DESTINATION .)

add_pytorch_extension(${TARGET_NAME}_cpp 
  src/PyPlaceDB.cpp  
  src/PybindPlaceDB.cpp  
  src/PybindPyPlaceDB.cpp
  src/place_io.cpp
  EXTRA_INCLUDE_DIRS ${INCLUDE_DIRS}
  EXTRA_LINK_LIBRARIES ${LINK_LIBS}
  EXTRA_DEFINITIONS DRAWPLACE=${DRAWPLACE})
target_link_libraries(${TARGET_NAME}_cpp PRIVATE ${TARGET_NAME}_cpp_so)

install(TARGETS 
  ${TARGET_NAME}_cpp 
  DESTINATION dreamplace/ops/${OP_NAME})
file(GLOB INSTALL_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/*.py)
install(FILES ${INSTALL_SRCS} DESTINATION dreamplace/ops/${OP_NAME})

add_executable(mytest 
  src/mytest.cpp)
target_include_directories(mytest PRIVATE ${INCLUDE_DIRS})
target_link_libraries(mytest PRIVATE ${LINK_LIBS} ${TARGET_NAME}_cpp_a)
install(TARGETS mytest DESTINATION dreamplace/ops/${OP_NAME})