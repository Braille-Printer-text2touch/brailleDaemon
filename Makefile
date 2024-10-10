COMP=gcc

all:
	$(COMP) -o build/main main.c

tests:
	$(COMP) -o build/tests -DTESTING tests.c main.c

clean:
	rm main tests
