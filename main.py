from time import sleep
from adafruit_motorkit import MotorKit
import os
import signal
import tomllib

PIPE_PATH = "/var/run/user/1000/text2type_pipe"
DEBUG = True

with open("characterEncodings.toml", "rb") as f:
    CHAR_ENCODES = tomllib.load(f)

def cleanExit() -> None:
    '''Clean up. For when a kill signal is detected'''
    os.remove(PIPE_PATH)
    exit(0)

signal.signal(signal.SIGINT, cleanExit)

kit = MotorKit()
def encodeChar(char: str) -> None:
    '''
    Print a character onto the paper. This function runs hardware

    Args:
        char (character): The character to be printed
    Returns:
        None
    '''

    ####################
    # each character is a unique combination of six dots (2 horizontally, 3 vertically)
    # in our hardware this is split vertically into two sets of 3 dots
    # each solonoid is responsible for 1 dot, two times per character
    # example: 'n' in braille. * is a dot, . is no dot
    #
    # * * solonoid 0 row
    # . * solonoid 1 row
    # * . solonoid 2 row
    #
    ##########

    DEBUG and print("encodeChar(): printing " + char)
    # match char:
    #     case 'a':
    #         # solonoid 0
    #         kit.stepper1.onestep()
    #         sleep(0.1)
    if encode := CHAR_ENCODES.get(char):
        encode[0][0] # and solonoid 0
        encode[0][1] # and solonoid 1
        encode[0][2] # and solonoid 2
        kit.stepper1.onestep()
        sleep(0.1)
        encode[1][0] # and solonoid 0
        encode[1][1] # and solonoid 1
        encode[1][2] # and solonoid 2
        kit.stepper1.onestep()
        sleep(0.1)

def main() -> None:

    # Set up pipe
    try:
        os.mkfifo(PIPE_PATH)
    except FileExistsError:
        print("Pipe already exists, carrying on as normal")
        # TODO: clear out pipe here?
    except OSError as e:
        print("Error creating pipe:", e)
        exit(-1)
    finally:
        print("Pipe ready at " + PIPE_PATH)

    while True:
        # have to keep opening the pipe because the connection closes
        # after all writers are done
        with open(PIPE_PATH, "r") as pipe:
            for char in pipe.readline().strip(): encodeChar(char.lower())

# example code to drive motors
# for i in range(10):
#     kit.stepper1.onestep()
#     print("Stepping one step on motor 1")
#     sleep(1)

main()
