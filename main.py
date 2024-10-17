from time import sleep
from adafruit_motorkit import MotorKit
# gives access to SINGLE, DOUBLE, FORWARD, BACKWARD, INTERLEAVE, MICROSTEP
from adafruit_motor import stepper
import os
import signal
import tomllib
import threading

SPOOLER_SEM = threading.Semaphore() # automatically w/ count 1
PIPE_PATH = "/var/run/user/1000/text2type_pipe"
DEBUG = True
ERROR_DEBUG = True
CHARS_PER_LINE = 30
STEPPER_PAUSE = 0.5 # in seconds

with open("characterEncodings.toml", "rb") as f:
    CHAR_ENCODES = tomllib.load(f)

def cleanExit(sig, frame) -> None:
    '''Clean up. For when a kill signal is detected'''
    print("Cleaning up")
    os.remove(PIPE_PATH)
    print("Cleaned up! Until next time, user.")
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
    if encode := CHAR_ENCODES.get(char):
        # second half first because paper is punched upside down,
        # so the characters need to be vertically reversed
        encode[1][0] # and solonoid 0
        encode[1][1] # and solonoid 1
        encode[1][2] # and solonoid 2
        kit.stepper1.onestep()
        sleep(STEPPER_PAUSE)
        encode[0][0] # and solonoid 0
        encode[0][1] # and solonoid 1
        encode[0][2] # and solonoid 2
        kit.stepper1.onestep()
        sleep(STEPPER_PAUSE)
    elif char == ' ':
        kit.stepper1.onestep(style = stepper.DOUBLE)
    else:
        ERROR_DEBUG and print("*** encodeChar(): '" + char + "' not found ***")


def encodeString(s: str) -> None:
    DEBUG and print("encodeString(): printing " + s)
    chunk = 0 # start at the first chunk of the string
    chars_to_print = len(s) # keep track of how many characters we've printed
    while chars_to_print > 0:
        in_index = chunk * CHARS_PER_LINE
        out_index = in_index + min(CHARS_PER_LINE, chars_to_print)
        DEBUG and print(f"encodeString(): chunk {chunk} '{s[in_index:out_index]}'")

        # string should be reversed, because the paper is punched upside down
        for char in reversed(s[in_index:out_index]):
            encodeChar(char)

        # difference is how many characters that we're printed in this iteration
        chars_to_print -= out_index - in_index
        chunk += 1

def print_job(data: str):
    SPOOLER_SEM.acquire()
    # critical section because ecoding will be running the hardware
    for line in data.split('\n'): encodeString(line.strip())
    SPOOLER_SEM.release()

def main() -> None:
    # Set up pipe
    try:
        os.mkfifo(PIPE_PATH)
    except FileExistsError:
        print("Pipe already exists, carrying on as normal")
        # TODO: clear pipe here?
    except OSError as e:
        print("Error creating pipe:", e)
        exit(-1)
    finally:
        print("Pipe ready at " + PIPE_PATH)

    while True:
        # have to keep opening the pipe because the connection closes
        # after all writers are done
        with open(PIPE_PATH, "r") as pipe:
            new_job = threading.Thread(
                target=print_job,
                args=(pipe.read().strip(),)
            )
        new_job.start()

main()
