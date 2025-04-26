from typing import Any, TextIO
# gives access to SINGLE, DOUBLE, FORWARD, BACKWARD, INTERLEAVE, MICROSTEP
from adafruit_motor import stepper
from adafruit_motorkit import MotorKit
import RPi.GPIO as GPIO
from time import sleep
import math
from transcriber import BrailleTranscriber
import tomllib

DEBUG = True

class BraillePrinterDriver:
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    motor_kit = MotorKit()

    CHARS_PER_LINE = config["SIZES"]["CHARS_PER_LINE"]
    SERIAL_SOLENOIDS = config["SOLENOIDS"]["SERIAL_SOLENOIDS"]
    SOL_PAUSE = config["SOLENOIDS"]["SOL_PAUSE"]
    SOL_DUTY_CYCLE = config["SOLENOIDS"]["SOL_DUTY_CYCLE"]
    SOL_PWM_FREQ = config["SOLENOIDS"]["SOL_PWM_FREQ"]
    MICROSTEPS = config["STEPPERS"]["MICROSTEPS"]
    SOL_0_PIN  = config["PINS"]["SOL_0_PIN"]
    SOL_1_PIN  = config["PINS"]["SOL_1_PIN"]
    SOL_2_PIN  = config["PINS"]["SOL_2_PIN"]
    BUTTON_PIN = config["PINS"]["BUTTON_PIN"]
    PAPER_STEPPER_DIAMETER = config["SIZES"]["PAPER_STEPPER_DIAMETER"]
    HEAD_STEPPER_DIAMETER = config["SIZES"]["HEAD_STEPPER_DIAMETER"]
    STEPPER_DEGREES = config["STEPPERS"]["STEPPER_DEGREES"]

    SOL_CHANNELS      = (SOL_0_PIN, SOL_1_PIN, SOL_2_PIN)
    STEPS_PER_ROTATION = int(360 / STEPPER_DEGREES) * MICROSTEPS
    HALF_CHAR_STEPS   = int(config["SIZES"]["HALF_CHAR_STEPS"]  / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
    SPACE_STEPS       = int(config["SIZES"]["SPACE_STEPS"]      / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
    RESET_STEPS       = int(config["SIZES"]["RESET_STEPS"]      / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
    NEW_LINE_STEPS    = int(config["SIZES"]["NEW_LINE_STEPS"]   / ((math.pi * HEAD_STEPPER_DIAMETER)  / STEPS_PER_ROTATION))
    EJECT_STEPS       = int(config["SIZES"]["EJECT_STEPS"]      / ((math.pi * PAPER_STEPPER_DIAMETER) / STEPS_PER_ROTATION))

    def __init__(self) -> None:
        assert(self.SPACE_STEPS >= 2 * self.HALF_CHAR_STEPS)

        self.head_stepper = self.motor_kit.stepper2
        self.paper_stepper = self.motor_kit.stepper1

        # solenoid GPIO setup
        GPIO.setmode(GPIO.BCM) # use broadcom (GPIO) pin numbers
        GPIO.setup(self.SOL_CHANNELS, GPIO.OUT) # setup solenoid pins

        self.pwm_solenoids: list[GPIO.PWM] = [GPIO.PWM(channel, self.SOL_PWM_FREQ) for channel in self.SOL_CHANNELS]

        # set pull up resistor on button
        GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # stepper motor setup
        for stepper in [self.head_stepper, self.paper_stepper]:
            self.set_microsteps(stepper, self.MICROSTEPS)

        # ensure steppers are released
        self.head_stepper.release()
        self.paper_stepper.release()

        self.transcriber = BrailleTranscriber()
        
        self.__diagnostic_message = "0: Machine up and running\n"

    def __del__(self):
        '''Clean up resources used and stop hold current on steppers'''
        GPIO.cleanup()
        self.head_stepper.release()
        self.paper_stepper.release()

    def set_microsteps(self, stepper, microsteps):
        '''
        Set the microsteps for a stepper motor. "Hijacks" Adafruits library.
        '''
        stepper._curve = [
            int(round(0xFFFF * math.sin(math.pi / (2 * microsteps) * i)))
            for i in range(microsteps + 1)
        ]
        stepper._current_microstep = 0
        stepper._microsteps = microsteps
        stepper._update_coils()

    def reset_print_head(self) -> None:
        '''
        Moves the print head to the edge of the container.
        Should be used before calling start_print_head().

        Returns:
            None
        '''
        # reach edge of enclosure
        while GPIO.input(self.BUTTON_PIN) == GPIO.HIGH:
            self.head_stepper.onestep(style=stepper.MICROSTEP)

        self.head_stepper.release()


    def start_print_head(self) -> None:
        '''
        Moves the print head over the printing area (from edge of container).
        Is meant to be used after reset_print_head().

        Returns:
            None
        '''
        # move over to start of line
        self.__move_stepper_n_steps(self.head_stepper, self.RESET_STEPS)

    def new_line(self) -> None:
        self.__move_stepper_n_steps(self.paper_stepper, -self.NEW_LINE_STEPS)
        self.reset_print_head()
        self.start_print_head()

    def eject_paper(self) -> None:
        self.__move_stepper_n_steps(self.paper_stepper, -self.EJECT_STEPS)

    def __mm_to_steps(self, circumference_mm: float, n_mm: float) -> int:
        return int(n_mm / (circumference_mm / self.STEPS_PER_ROTATION)) # return number of steps to move n_mm

    def __move_stepper_n_steps(self, motor: stepper.StepperMotor, n: int) -> None:
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
        dir = stepper.FORWARD if ((n > 0) ^ (motor == self.head_stepper)) else stepper.BACKWARD

        # we've selected the direction above based on the sign of n
        # so we can just print for the absolute value of n here
        for _ in range(abs(n)):
            motor.onestep(direction = dir, style=stepper.MICROSTEP)

        motor.release()

    def __print_half_character(self, *sol_values: bool, serial_solenoids=True) -> None:
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

        # only bother running solenoid if there are values that need to be 
        # printed. otherwise, just move to next half
        if sum(sol_values) > 0:
            if serial_solenoids:
                for i in range(3):
                    # GPIO.output(SOL_CHANNELS[i], sol_values[i])
                    if sol_values[i]: # if this solenoid should fire
                        self.pwm_solenoids[i].start(self.SOL_DUTY_CYCLE)
                        sleep(self.SOL_PAUSE)
                        self.pwm_solenoids[i].stop()
                        sleep(self.SOL_PAUSE)
            else:
                for i in range(3):
                    if sol_values[i]: # if this solenoid should fire
                        self.PWM_SOLENOIDS[i].start(self.SOL_DUTY_CYCLE)
                sleep(self.SOL_PAUSE)
                for i in range(3):
                    self.PWM_SOLENOIDS[i].stop()
                sleep(self.SOL_PAUSE)

    def encode_char(self, char: str) -> None:
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
            self.new_line()
            return

        _ = DEBUG and print("encode_char(): printing " + char)
        try:
            unicode_braille = self.transcriber.ascii2braille(char)
        except Exception as e:
            _ = DEBUG and print(e)
            return

        _ = DEBUG and print("encode_char(): printing (braille) " + unicode_braille)
        array_braille = self.transcriber.braille2array(unicode_braille)

        # second half first because paper is punched upside down, 
        # so the characters need to be vertically reflected 
        sleep(self.SOL_PAUSE)
        self.__print_half_character(*array_braille[1], serial_solenoids=self.SERIAL_SOLENOIDS)
        self.__move_stepper_n_steps(self.head_stepper, self.HALF_CHAR_STEPS)

        sleep(self.SOL_PAUSE)
        self.__print_half_character(*array_braille[0], serial_solenoids=self.SERIAL_SOLENOIDS)
        self.__move_stepper_n_steps(self.head_stepper, self.SPACE_STEPS - self.HALF_CHAR_STEPS) # because one half char was already printed

    def encode_string(self, s: str) -> None:
        '''
        Print a string of characters onto the paper. This will handle chunking and 
        putting the characters in the correct order, along with transliterations.

        This function really acts as the entry point for the whole printing process.

        Args:
            s (string): The string to be printed
        Returns:
            None
        '''
        _ = DEBUG and print("encode_string(): printing " + s)
        transliterated_s = self.transcriber.transliterate_string(s)
        _ = DEBUG and print("encode_string(): printing (transliterated)" + transliterated_s)

        chunk = 0 # start at the first chunk of the string
        chars_to_print = len(transliterated_s) # keep track of how many characters we've printed

        while chars_to_print > 0:
            in_index = chunk * self.CHARS_PER_LINE
            out_index = in_index + min(self.CHARS_PER_LINE, chars_to_print)
            _ = DEBUG and print(f"encode_string(): chunk {chunk} '{transliterated_s[in_index:out_index]}'")

            for char in reversed(transliterated_s[in_index:out_index]):
                self.encode_char(char)

            # difference between out_index and in_index 
            # is how many characters that we're printed in this iteration
            chars_to_print -= out_index - in_index
            chunk += 1
            self.new_line()

        self.head_stepper.release()
        self.paper_stepper.release()

    def write_diagnostic_message(self, output: TextIO) -> None:
        '''
        Sends a diagnostic message to some writable output. This can be used to print out
        any errors or debug information.
        '''
        output.write(self.__diagnostic_message)
