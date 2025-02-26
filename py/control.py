# gives access to SINGLE, DOUBLE, FORWARD, BACKWARD, INTERLEAVE, MICROSTEP
from adafruit_motor import stepper
from adafruit_motorkit import MotorKit
import RPi.GPIO as GPIO
from time import sleep
import math

#########
# Settings
######
PIPE_PATH = "/var/run/user/1000/text2type_pipe"
CHARS_PER_LINE = 30 # how many characters can be printed horizontally per line
DEBUG = True

### Solenoids
SERIAL_SOLENOIDS = True # whether or not the solenoids fire in serial (one after another) or all at the same time
SOL_PAUSE = 0.5 # how long to wait after firing a solenoid
SOL_DUTY_CYCLE = 50 # PWM duty cycle (0.0-100.0)
SOL_PWM_FREQ = 800 # PWM frequency (Hz)
PWM_SOLENOIDS: list[GPIO.PWM] | None = None # the actual PWM instances to drive in the code (setup in setup())

### Stepper Motors
MICROSTEPS = 4

### Various GPIO aliases (numbers in BCM)
SOL_0  = 27
SOL_1  = 23
SOL_2  = 17
BUTTON = 20
########

########
# Globals
######
KIT = MotorKit()
########

########
# Helpful things
######
SOL_CHANNELS = (SOL_0, SOL_1, SOL_2)
BRAILLE_JUMP = "⠀⠮⠐⠼⠫⠩⠯⠄⠷⠾⠡⠬⠠⠤⠨⠌⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔⠱⠰⠣⠿⠜⠹⠈⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵⠪⠳⠻⠘⠸"
STEPS_PER_ROTATION = 200 * MICROSTEPS

### Aliases
HEAD_STEPPER = KIT.stepper2
PAPER_STEPPER = KIT.stepper1

### Physical Sizes (mm)
PAPER_STEPPER_DIAMETER = 30.1625
HEAD_STEPPER_DIAMETER = 12.7

### Various precalculated steps
#### Integer values come from official ADA Braille standards (in mm)
#### or measurements
HALF_CHAR_STEPS   = int(2.4      / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
SPACE_STEPS       = int(6.85     / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
RESET_STEPS       = int(34       / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
NEW_LINE_STEPS    = int(10.1     / ((math.pi * PAPER_STEPPER_DIAMETER) / STEPS_PER_ROTATION))
EJECT_STEPS       = int(279      / ((math.pi * PAPER_STEPPER_DIAMETER) / STEPS_PER_ROTATION))

### Assertions
assert(SPACE_STEPS >= 2 * HALF_CHAR_STEPS)
########

########
# Type definitions
######
BrailleHalfChar = tuple[bool, bool, bool]
BrailleArray = tuple[BrailleHalfChar, BrailleHalfChar]
########

def set_microsteps(stepper, microsteps):
    stepper._curve = [
        int(round(0xFFFF * math.sin(math.pi / (2 * microsteps) * i)))
        for i in range(microsteps + 1)
    ]
    stepper._current_microstep = 0
    stepper._microsteps = microsteps
    stepper._update_coils()

def setup():
    '''Sets up the global variables and surrounding environment'''

    # solenoid GPIO setup
    GPIO.setmode(GPIO.BCM) # use broadcom (GPIO) pin numbers
    GPIO.setup(SOL_CHANNELS, GPIO.OUT) # setup solenoid pins

    global PWM_SOLENOIDS
    PWM_SOLENOIDS = [GPIO.PWM(channel, SOL_PWM_FREQ) for channel in SOL_CHANNELS]

    # set pull up resistor on button
    GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    for stepper in [HEAD_STEPPER, PAPER_STEPPER]:
        set_microsteps(stepper, MICROSTEPS)

    HEAD_STEPPER.release()
    PAPER_STEPPER.release()

def cleanup() -> None:
    '''Clean up resources used and stop hold current on steppers'''
    GPIO.cleanup()
    HEAD_STEPPER.release()
    PAPER_STEPPER.release()

# TODO: is this function even necessary?
def set_button_callback(callback) -> None:
    '''
    Set a callback function for when the button is pressed.

    Args:
        callback (function): The function to call when the button is pressed.
    Returns:
        None
    '''
    GPIO.add_event_detect(BUTTON, GPIO.FALLING, callback=callback)

def reset_print_head() -> None:
    '''
    Moves the print head to the edge of the container.
    Should be used before calling start_print_head().

    Returns:
        None
    '''
    # reach edge of enclosure
    while GPIO.input(BUTTON) == GPIO.HIGH:
        HEAD_STEPPER.onestep(style=stepper.MICROSTEP)

    HEAD_STEPPER.release()


def start_print_head() -> None:
    '''
    Moves the print head over the printing area (from edge of container).
    Is meant to be used after reset_print_head().

    Returns:
        None
    '''
    # move over to start of line
    move_stepper_n_steps(HEAD_STEPPER, RESET_STEPS)

def new_line() -> None:
    move_stepper_n_steps(PAPER_STEPPER, -NEW_LINE_STEPS)
    reset_print_head()
    start_print_head()

def eject_paper() -> None:
    move_stepper_n_steps(PAPER_STEPPER, -EJECT_STEPS)

def mm_to_steps(circumference_mm: float, n_mm: float) -> int:
    return int(n_mm / (circumference_mm / STEPS_PER_ROTATION)) # return number of steps to move n_mm

def move_stepper_n_steps(motor: stepper.StepperMotor, n: int) -> None:
    '''
    Move a stepper motor by n steps.

    Args:
        motor (int): The stepper motor to run. 0 for stepper 0, 1 for stepper 1.
        distance (int): How many steps to move by.
    Returns:
        None
    '''
    # if n > 0, for motor1 step backward 
    # if n > 0, for motor0 step forward 
    # xor acts as selective invertor
    dir = stepper.FORWARD if ((n > 0) ^ (motor == HEAD_STEPPER)) else stepper.BACKWARD

    # we've selected the direction above based on the sign of n
    # so we can just print for the absolute value of n here
    for _ in range(abs(n)):
        motor.onestep(direction = dir, style=stepper.MICROSTEP)

    motor.release()

def print_half_character(*sol_values: bool, serial_solenoids=True) -> None:
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
    if PWM_SOLENOIDS is None:
        raise ValueError("PWM_SOLENOIDS cannot be None. Ensure setup() is run first.")

    if len(sol_values) != 3:
        raise ValueError("print_half_character(): need exactly three values for solenoids")

    # only bother running solenoid if there are values that need to be 
    # printed. otherwise, just move to next half
    if sum(sol_values) > 0:
        if serial_solenoids:
            for i in range(3):
                # GPIO.output(SOL_CHANNELS[i], sol_values[i])
                if sol_values[i]: # if this solenoid should fire
                    PWM_SOLENOIDS[i].start(SOL_DUTY_CYCLE)
                    sleep(SOL_PAUSE)
                    PWM_SOLENOIDS[i].stop()
                    sleep(SOL_PAUSE)
        else:
            for i in range(3):
                if sol_values[i]: # if this solenoid should fire
                    PWM_SOLENOIDS[i].start(SOL_DUTY_CYCLE)
            sleep(SOL_PAUSE)
            for i in range(3):
                PWM_SOLENOIDS[i].stop()
            sleep(SOL_PAUSE)

def ascii2braille(c: str) -> str:
    '''
    Takes a unicode character in the range 0x20 (SPACE) to 0x5F (underscore) and 
    returns its unicode brialle representation.

    The ASCII characters to be translated to braille exist in the range 0x20 (SPACE)
    to 0x5F (underscore), thus determining the chracter in question is a simple substraction from 0x20
    which can then be used to index a specially crafted string as a jump table

    Inputs:
        c: str, the character to transliterate
    Outputs:
        str: the transliterated braille character (unicode)
    '''
    # only uppercase characters are in the proper range
    ascii_offset = ord(c.upper()) - 0x20
    if not (0x0 <= ascii_offset <= 0x3F):
        # out of range
        raise Exception("Unsupported character")

    return BRAILLE_JUMP[ascii_offset]

def braille2array(b: str) -> BrailleArray:
    '''
    Takes a braille unicode character and returns its array representation for 
    running the solenoids.
    
    Braille characters start at 0x2800 and, for the first 0x3F characters,
    increment by counting in binary down the left column then down the right column
    Example:
        0x101110
    is
          .
        .
        . .

    Inputs:
        b: str, the utf8 braille character to convert
    Outputs:
        BrailleArray: the character represented by two BrailleHalfChar
    '''
    braille_offset = ord(b) - 0x2800
    if not (0x0 <= braille_offset <= 0x3F):
        # out of range
        raise Exception("Unsupported character")

    return (
            (bool(braille_offset & 1 << 0), bool(braille_offset & 1 << 1), bool(braille_offset & 1 << 2)),
            (bool(braille_offset & 1 << 3), bool(braille_offset & 1 << 4), bool(braille_offset & 1 << 5))
           )

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

    if char == '\n':
        new_line()
        return

    _ = DEBUG and print("encode_char(): printing " + char)
    try:
        unicode_braille = ascii2braille(char)
    except Exception as e:
        _ = DEBUG and print(e)
        return

    _ = DEBUG and print("encode_char(): printing (braille) " + unicode_braille)
    array_braille = braille2array(unicode_braille)

    # second half first because paper is punched upside down, 
    # so the characters need to be vertically reflected 
    sleep(SOL_PAUSE)
    print_half_character(*array_braille[1], serial_solenoids=SERIAL_SOLENOIDS)
    move_stepper_n_steps(HEAD_STEPPER, HALF_CHAR_STEPS)

    sleep(SOL_PAUSE)
    print_half_character(*array_braille[0], serial_solenoids=SERIAL_SOLENOIDS)
    move_stepper_n_steps(HEAD_STEPPER, SPACE_STEPS - HALF_CHAR_STEPS) # because one half char was already printed

def encode_string(s: str) -> None:
    '''
    Print a string of characters onto the paper. This will handle chunking and 
    putting the characters in the correct order.

    Args:
        s (string): The string to be printed
    Returns:
        None
    '''
    _ = DEBUG and print("encode_string(): printing " + s)
    chunk = 0 # start at the first chunk of the string
    chars_to_print = len(s) # keep track of how many characters we've printed
    while chars_to_print > 0:
        in_index = chunk * CHARS_PER_LINE
        out_index = in_index + min(CHARS_PER_LINE, chars_to_print)
        _ = DEBUG and print(f"encode_string(): chunk {chunk} '{s[in_index:out_index]}'")

        for char in reversed(s[in_index:out_index]):
            encode_char(char)

        # difference between out_index and in_index 
        # is how many characters that we're printed in this iteration
        chars_to_print -= out_index - in_index
        chunk += 1
        new_line()

    HEAD_STEPPER.release()
    PAPER_STEPPER.release()
