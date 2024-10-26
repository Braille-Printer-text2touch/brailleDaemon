# gives access to SINGLE, DOUBLE, FORWARD, BACKWARD, INTERLEAVE, MICROSTEP
from adafruit_motor import stepper
from adafruit_motorkit import MotorKit
import RPi.GPIO as GPIO
import tomllib
from time import sleep
from math import pi

#########
# Settings
######
PIPE_PATH = "/var/run/user/1000/text2type_pipe"
CHARS_PER_LINE = 30
STEPPER_PAUSE = 0.5 # in seconds
DEBUG = True
SOL_PAUSE = 0.5 # was able to get this down to 0.1
SOL_0 = 17
SOL_1 = 23
SOL_2 = 27
STEPPER_0_RADIUS = 1 #TODO: get actual value
STEPPER_1_RADIUS = 0.75
########

########
# Helpful things
######
SOL_CHANNELS = (SOL_0, SOL_1, SOL_2)
CHAR_ENCODES: dict[str, list[list[bool]]] = {}
KIT = MotorKit()
STEPS_PER_CM_0: float = 200 / (2 * STEPPER_0_RADIUS * pi) #TODO: make this more stable
STEPS_PER_CM_1: float = 200 / (2 * STEPPER_1_RADIUS * pi) #TODO: make this more stable
########

def setup():
    '''Sets up the global variables and surrounding environment'''
    global CHAR_ENCODES
    global JOB_COUNT
    GPIO.setmode(GPIO.BCM) # use broadcom (GPIO) pin numbers
    with open("../characterEncodings.toml", "rb") as f:
        CHAR_ENCODES = tomllib.load(f)
    JOB_COUNT = 0 # for jobs to increment
    GPIO.setup(SOL_CHANNELS, GPIO.OUT) # setup solenoid pins

def cleanup() -> None:
    '''Clean up resources used and stop hold current on steppers'''
    GPIO.cleanup()
    KIT.stepper1.release()
    KIT.stepper2.release()

def move_stepper_cm(motor: int, distance: int | float = 1) -> None:
    '''
    Move a stepper motor by one centimeter.

    Args:
        motor (int): The stepper motor to run. 0 for stepper 0, 1 for stepper 1.
        distance (int | float): How many centimeters to move by. Defaults to 1.
    Returns:
        None
    '''
    dir = stepper.FORWARD if distance > 0 else stepper.BACKWARD
    chosen_motor = KIT.stepper1 if motor == 0 else KIT.stepper2

    for _ in range(int(STEPS_PER_CM_0 * distance)):
        chosen_motor.onestep(direction = dir)
        sleep(STEPPER_PAUSE)


def print_half_character(*sol_values: bool) -> None:
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
    if len(sol_values) != 3:
        raise ValueError("print_half_character(): need exactly three values for solenoids")

    if sum(sol_values) > 0:
        # only bother running solenoid if there are values that need to be 
        # printed. otherwise, just move to next half
        GPIO.output(SOL_CHANNELS, sol_values)
        sleep(SOL_PAUSE)
        GPIO.output(SOL_CHANNELS, GPIO.LOW)
        sleep(SOL_PAUSE)
    move_stepper_cm(1, 0.1) # 0.1 cm over for next half of character
    sleep(STEPPER_PAUSE)

def encode_char(char: str) -> None:
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

    DEBUG and print("encode_char(): printing " + char)
    if encode := CHAR_ENCODES.get(char):
        # second half first because paper is punched upside down, 
        # so the characters need to be vertically reflected 
        # Also, ecode[1] is passed because it is a sub array with three values 
        # one for each solenoid channeli.
        print_half_character(*encode[1])
        print_half_character(*encode[0])

    elif char == ' ':
        move_stepper_cm(1, 0.2) # 0.2 cm over for a space
    else:
        DEBUG and print("*** encode_char(): '" + char + "' not found ***")


def encode_string(s: str) -> None:
    '''
    Print a string of characters onto the paper. This will handle chunking and 
    putting the characters in the correct order.

    Args:
        s (string): The string to be printed
    Returns:
        None
    '''
    DEBUG and print("encode_string(): printing " + s)
    chunk = 0 # start at the first chunk of the string
    chars_to_print = len(s) # keep track of how many characters we've printed
    while chars_to_print > 0:
        in_index = chunk * CHARS_PER_LINE
        out_index = in_index + min(CHARS_PER_LINE, chars_to_print)
        DEBUG and print(f"encode_string(): chunk {chunk} '{s[in_index:out_index]}'")

        for char in s[in_index:out_index]:
            encode_char(char)

        # difference between out_index and in_index 
        # is how many characters that we're printed in this iteration
        chars_to_print -= out_index - in_index
        chunk += 1

    KIT.stepper1.release()
    KIT.stepper2.release()
