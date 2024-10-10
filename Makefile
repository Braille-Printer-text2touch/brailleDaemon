CC=gcc
FLAGS=-Wall
BUILD_DIR=build
OBJ_DIR=obj

all: init daemon tests

init:
	mkdir -p $(BUILD_DIR)
	mkdir -p $(OBJ_DIR)

daemon: $(OBJ_DIR)/main.o
	$(CC) $(FLAGS) -o $(BUILD_DIR)/main $^

$(OBJ_DIR)/%.o: %.c
	$(CC) -c -o $@ $<

tests: $(OBJ_DIR)/tests.o $(OBJ_DIR)/main.o
	$(CC) $(FLAGS) -o $(BUILD_DIR)/tests -DTESTING $^

clean:
	rm -rf $(BUILD_DIR)
	rm -rf $(OBJ_DIR)
