from typing import Any, TextIO
# gives access to SINGLE, DOUBLE, FORWARD, BACKWARD, INTERLEAVE, MICROSTEP
from adafruit_motor import stepper
from adafruit_motorkit import MotorKit
import RPi.GPIO as GPIO
from time import sleep
import math
import tomllib

#########
# Settings
######
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

def __toml_open_and_load(file_path: str) -> dict[str, Any]:
    with open(file_path, "rb") as f:
        return tomllib.load(f)

class BraillePrinterDriver:
    def __new__(cls):
        # load all the toml files for transliteration
        # these are class variables because they are shared across all instances
        cls.BRAILLE_JUMP = "⠀⠮⠐⠼⠫⠩⠯⠄⠷⠾⠡⠬⠠⠤⠨⠌⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔⠱⠰⠣⠿⠜⠹⠈⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵⠪⠳⠻⠘⠸"
        cls.BRAILLE_SHORTFORMS    = __toml_open_and_load("../brailleTransliterations/shortforms.toml")
        cls.ALPHABETIC_WORD_SIGNS = __toml_open_and_load("../brailleTransliterations/alphabetic-word-signs.toml")
        cls.STRONG_CONTRACTIONS   = __toml_open_and_load("../brailleTransliterations/strong-contractions.toml")
        cls.LOWER_CONTRACTIONS    = __toml_open_and_load("../brailleTransliterations/lower-contractions.toml")
        cls.DOT_56_FINAL_LETTER   = __toml_open_and_load("../brailleTransliterations/dot-56.toml")
        cls.DOT_46_FINAL_LETTER   = __toml_open_and_load("../brailleTransliterations/dot-46.toml")
        cls.DOT_5_WORDS           = __toml_open_and_load("../brailleTransliterations/dot-5.toml")
        cls.DOT_45_WORDS          = __toml_open_and_load("../brailleTransliterations/dot-45.toml")
        cls.DOT_456_WORDS         = __toml_open_and_load("../brailleTransliterations/dot-456.toml")
        cls.BRAILLE_SPECIAL_SYMBOLS = __toml_open_and_load("../brailleTransliterations/special-symbols.toml")

    def __init__(self, head_stepper: stepper.StepperMotor, paper_stepper: stepper.StepperMotor) -> None:
        self.head_stepper = head_stepper
        self.paper_stepper = paper_stepper

        # solenoid GPIO setup
        GPIO.setmode(GPIO.BCM) # use broadcom (GPIO) pin numbers
        GPIO.setup(SOL_CHANNELS, GPIO.OUT) # setup solenoid pins

        self.PWM_SOLENOIDS = [GPIO.PWM(channel, SOL_PWM_FREQ) for channel in SOL_CHANNELS]

        # set pull up resistor on button
        GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # stepper motor setup
        for stepper in [self.head_stepper, self.paper_stepper]:
            self.set_microsteps(stepper, MICROSTEPS)

        # ensure steppers are released
        HEAD_STEPPER.release()
        PAPER_STEPPER.release()
        
        self.__diagnostic_message = "Machine up and running\n"

    def __del__(self):
        '''Clean up resources used and stop hold current on steppers'''
        GPIO.cleanup()
        HEAD_STEPPER.release()
        PAPER_STEPPER.release()

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
        while GPIO.input(BUTTON) == GPIO.HIGH:
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
        self.move_stepper_n_steps(self.head_stepper, RESET_STEPS)

    def new_line(self) -> None:
        self.move_stepper_n_steps(self.paper_stepper, -NEW_LINE_STEPS)
        self.reset_print_head()
        self.start_print_head()

    def eject_paper(self) -> None:
        self.move_stepper_n_steps(self.paper_stepper, -EJECT_STEPS)

    def __mm_to_steps(self, circumference_mm: float, n_mm: float) -> int:
        return int(n_mm / (circumference_mm / STEPS_PER_ROTATION)) # return number of steps to move n_mm

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

    @staticmethod
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
    
        return BraillePrinterDriver.BRAILLE_JUMP[ascii_offset]

    @staticmethod
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
            unicode_braille = self.ascii2braille(char)
        except Exception as e:
            _ = DEBUG and print(e)
            return

        _ = DEBUG and print("encode_char(): printing (braille) " + unicode_braille)
        array_braille = self.braille2array(unicode_braille)

        # second half first because paper is punched upside down, 
        # so the characters need to be vertically reflected 
        sleep(SOL_PAUSE)
        self.print_half_character(*array_braille[1], serial_solenoids=SERIAL_SOLENOIDS)
        self.move_stepper_n_steps(self.head_stepper, HALF_CHAR_STEPS)

        sleep(SOL_PAUSE)
        self.print_half_character(*array_braille[0], serial_solenoids=SERIAL_SOLENOIDS)
        self.move_stepper_n_steps(self.head_stepper, SPACE_STEPS - HALF_CHAR_STEPS) # because one half char was already printed

    def encode_string(self, s: str) -> None:
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
                self.encode_char(char)

            # difference between out_index and in_index 
            # is how many characters that we're printed in this iteration
            chars_to_print -= out_index - in_index
            chunk += 1
            self.new_line()

        self.head_stepper.release()
        self.paper_stepper.release()

    def transliterate_string(self, s: str) -> str:
        '''
        Take a string composed of ASCII characters (0x20-0x5F) and apply Braille 
        contractions, shorthands, and punctuation.
        This string can then be sent to encode_string() to be printed.

        The string should NOT have new lines present.

        Args:
            s (string): The string to be transliterated, devoid of new lines
        Returns:
            string, the transliterated string
        '''
        words = s.split(" ")
        transliterated_words: list[str] = []
        for word in words:
            # shortforms
            if word in self.BRAILLE_SHORTFORMS:
                transliterated_words.append(self.BRAILLE_SHORTFORMS[word])

            # numbers
            elif word.isnumeric():
                transliterated_words.append('#' + word) # prefix with number prefix '#'

            # special symbols
            # TODO: these might move into a different translation section, when we go symbol by symbol

            # alphabetic word signs
            elif word in self.ALPHABETIC_WORD_SIGNS:
                transliterated_words.append(self.ALPHABETIC_WORD_SIGNS[word])

            # contractions
            elif word in self.STRONG_CONTRACTIONS:
                transliterated_words.append(self.STRONG_CONTRACTIONS[word])
            elif word in self.LOWER_CONTRACTIONS:
                transliterated_words.append(self.LOWER_CONTRACTIONS[word])

            # final-letter combinations
            # try to replace the suffix and see if anything changed
            # if so, add the changed word
            elif (suffix_word := self.__replace_suffixes(self.DOT_56_FINAL_LETTER, word)) != word:
                transliterated_words.append(suffix_word)
            elif (suffix_word := self.__replace_suffixes(self.DOT_46_FINAL_LETTER, word)) != word:
                transliterated_words.append(suffix_word)

            # more contractions!
            elif word in self.DOT_5_WORDS:
                transliterated_words.append(self.DOT_5_WORDS[word])
            elif word in self.DOT_45_WORDS:
                transliterated_words.append(self.DOT_45_WORDS[word])
            elif word in self.DOT_456_WORDS:
                transliterated_words.append(self.DOT_45_WORDS[word])

            # if nothing else, just add the word
            else:
                transliterated_words.append(word)

        transliterated_string = " ".join(transliterated_words) # add spaces between processed words
        return self.__transliterate_symbols(transliterated_string)

    def write_diagnostic_message(self, output: TextIO) -> None:
        '''
        Sends a diagnostic message to the user. This can be used to print out
        any errors or debug information.
        '''
        output.write(self.__diagnostic_message)

    @staticmethod
    def __replace_suffixes(suffixes: dict, word: str) -> str:
        for suffix in suffixes.keys():
            if word.endswith(suffix):
                return word.removesuffix(suffix) + suffixes[suffix]
        return word
    
    @staticmethod
    def __replace_prefix(prefixes: dict, word: str) -> str:
        for prefix in prefixes.keys():
            if word.startswith(prefix):
                return word.removeprefix(prefix) + prefixes[prefix]
        return word

    def __transliterate_symbols(self, s: str) -> str:
        all_chars = list(s)

        for index, c in enumerate(all_chars):
            if c in self.BRAILLE_SPECIAL_SYMBOLS:
                all_chars[index] = self.BRAILLE_SPECIAL_SYMBOLS[c]

        return "".join(all_chars)
