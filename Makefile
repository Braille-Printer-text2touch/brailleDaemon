COMP=gcc
FLAGS=-Wall

all:
	$(COMP) $(FLAGS) -o build/main main.c

tests:
	$(COMP) $(FLAGS) -o build/tests -DTESTING tests.c main.c

clean:
	rm build/main build/tests
