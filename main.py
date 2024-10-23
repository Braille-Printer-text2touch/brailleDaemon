from adafruit_motorkit import MotorKit
# gives access to SINGLE, DOUBLE, FORWARD, BACKWARD, INTERLEAVE, MICROSTEP
from adafruit_motor import stepper
import RPi.GPIO as GPIO

from time import sleep
import os
import signal
import tomllib
import threading

#########
# Settings
######
PIPE_PATH = "/var/run/user/1000/text2type_pipe"
DEBUG = True
ERROR_DEBUG = True
CHARS_PER_LINE = 30
STEPPER_PAUSE = 0.5 # in seconds
SOL_0 = 4
SOL_1 = 17
SOL_2 = 18
########

########
# Setup 
#####
SPOOLER_SEM = threading.Semaphore() # automatically w/ count 1
GPIO.setmode(GPIO.BCM) # use broadcom (GPIO) pin numbers
SOL_CHANNELS = (SOL_0, SOL_1, SOL_2)
with open("characterEncodings.toml", "rb") as f:
    CHAR_ENCODES: dict[str, list[list[bool]]] = tomllib.load(f)
JOB_COUNT = 0 # for jobs to increment

def cleanExit(sig, frame) -> None:
    '''Clean up. For when a kill signal is detected'''
    print("\nCleaning up")
    os.remove(PIPE_PATH)
    GPIO.cleanup()
    print("Cleaned up! Until next time, user.")
    exit(0)

signal.signal(signal.SIGINT, cleanExit)
#######

def printHalfCharacter(*sol_values: bool) -> None:
    '''
    Runs all three solenoids at specified parameters and resets them after.
    Additionally moves the print head. This function runs hardware.

    Args:
        sol_values (tuple<bool>):
            A tuple of exectly 3 boolean values. For each value at index i, 
            if true, solenoid i is set high, otherwise set low.
    Returns:
        None
    '''
    GPIO.output(SOL_CHANNELS, sol_values)
    sleep(0.1)
    GPIO.output(SOL_CHANNELS, GPIO.LOW)
    sleep(0.1)
    kit.stepper1.onestep()
    sleep(STEPPER_PAUSE)

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
        # so the characters need to be vertically reflected 
        # Also, ecode[1] is passed because it is a sub array with three values 
        # one for each solenoid channeli.
        printHalfCharacter(*encode[1])
        printHalfCharacter(*encode[0])

    elif char == ' ':
        kit.stepper1.onestep(style = stepper.DOUBLE)
    else:
        ERROR_DEBUG and print("*** encodeChar(): '" + char + "' not found ***")


def encodeString(s: str) -> None:
    '''
    Print a string of characters onto the paper. This will handle chunking and 
    putting the characters in the correct order.

    Args:
        s (string): The string to be printed
    Returns:
        None
    '''
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

def print_job(data: str) -> None:
    '''
    Sets up a chunk of data to be printed. This is meant to be the entry point of 
    a thread, where each thread is a job to be printed.

    Args:
        data (string): The entire text to be printed
    Returns:
        None
    '''
    global JOB_COUNT
    JOB_COUNT += 1
    SPOOLER_SEM.acquire()
    # critical section because ecoding will be running the hardware
    for line in data.split('\n'): encodeString(line.strip())
    JOB_COUNT -= 1
    if JOB_COUNT > 0:
        input(f"\n There are {JOB_COUNT} other jobs waiting. Press enter to start the next.")
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

    # setup solenoid pins
    GPIO.setup(SOL_CHANNELS, GPIO.OUT)

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
