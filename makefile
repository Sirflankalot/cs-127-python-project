WARNINGS=-fdiagnostics-color=always -Wall -Wcast-align -Wcast-qual -Wconversion -Wctor-dtor-privacy -Wdisabled-optimization -Wdouble-promotion -Wextra -Wformat=2 -Winit-self -Wlogical-op -Wmissing-include-dirs -Wno-sign-conversion -Wnoexcept -Wold-style-cast -Woverloaded-virtual -Wpedantic -Wredundant-decls -Wshadow -Wstrict-aliasing=1 -Wstrict-null-sentinel -Wstrict-overflow=5 -Wswitch-default -Wundef -Wno-unknown-pragmas -Wuseless-cast -Wno-unknown-warning-option
OPTIMIZATION=-O0
FLAGS=-g -fPIC -isystem third-party -isystem third-party/sparsehash/include -std=c++14 $(OPTIMIZATION)

all: corelib/libdatabase.so

corelib/libdatabase.so: corelib/database.cpp
	$(CXX) $(WARNINGS) $(FLAGS) -shared -o corelib/libdatabase.so corelib/database.cpp $(EXTRAFLAGS) -lpthread -licuio -licui18n -licuuc -licudata -lsqlite3

clean:
	rm -f corelib/libdatabase.so