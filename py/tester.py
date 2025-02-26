import RPi.GPIO as GPIO
from time import sleep
import control
from math import pi

TEST_MESSAGE = "Hello!\nThis is a test. !123"

control.setup()

# if input("Music? (y/N) ").lower() == 'y':
#     control.set_microsteps(control.HEAD_STEPPER, 32)
#     control.set_microsteps(control.PAPER_STEPPER, 4)
# 
#     for _ in range(200):
#         control.HEAD_STEPPER.onestep(style=stepper.MICROSTEP)
#         control.PAPER_STEPPER.onestep(style=stepper.MICROSTEP)

if input("Test steppers? (y/N) ").lower() == 'y':
    n_steps = control.mm_to_steps(control.PAPER_STEPPER_DIAMETER * 2 * pi, 10)
    print("Testing Paper Stepper (10 mm)")
    control.move_stepper_n_steps(control.PAPER_STEPPER, n_steps)
    sleep(1)

    n_steps = control.mm_to_steps(control.PAPER_STEPPER_DIAMETER * 2 * pi, 10)
    print("Testing Paper Stepper (10 mm)")
    control.move_stepper_n_steps(control.PAPER_STEPPER, -n_steps)
    sleep(1)

    n_steps = control.mm_to_steps(control.HEAD_STEPPER_DIAMETER * 2 * pi, 10)
    print("Testing Head Stepper (10 mm)")
    control.move_stepper_n_steps(control.HEAD_STEPPER, n_steps)
    sleep(1)

    n_steps = control.mm_to_steps(control.HEAD_STEPPER_DIAMETER * 2 * pi, 10)
    print("Testing Head Stepper (10 mm)")
    control.move_stepper_n_steps(control.HEAD_STEPPER, -n_steps)
    sleep(1)

if input("Test solenoids? (y/N) ").lower() == 'y':
    if control.PWM_SOLENOIDS is not None:
        for i in range(3):
            print(f"Testing solenoid {i}")
            control.PWM_SOLENOIDS[i].start(control.SOL_DUTY_CYCLE)
            sleep(control.SOL_PAUSE)
            control.PWM_SOLENOIDS[i].stop()
            sleep(control.SOL_PAUSE)
    else:
        print("PWM_SOLENOIDS is None. Please run setup() first")

if input("Test button? (y/N) ").lower() == 'y':
    print("Waiting for button press")
    while (GPIO.input(control.BUTTON) == GPIO.HIGH):
        sleep(0.5)
    print("Button pressed")

    if (
        input("\033[33mTest starting the head? THIS CAN BREAK STUFF IF THE BUTTON IS NOT WORKING (y/N) \033[0m").lower() == 'y'
        and input("Are you sure? (y/N) ") == 'y'
    ):
        control.reset_print_head()

        if input("Start print head? (y/N) ") == 'y':
            control.start_print_head()

if input("Test new line? \033[33mBUTTON SHOULD BE TESTED AND WORKING\033[0m (y/N) ").lower() == 'y':
    control.new_line()

if input("Test braille printing in terminal? (y/N) ").lower() == 'y':
    while s := input("Enter string to see braille encoding, or nothing to end. DON'T CTRL-C!\n"):
        try:
            for c in s:
                print(control.ascii2braille(c), end="")
            print() # new line
        except Exception as e:
            print(e)

if input("Test braille printing w/ hardware? (y/N) ").lower() == 'y':
    while s := input("Input string to test printing, or nothing to end. DON'T CTRL-C!\n"):
        control.encode_string(s)

if input("Test with test message? (y/N) ").lower() == 'y':
    control.reset_print_head()
    control.start_print_head()
    for line in TEST_MESSAGE.split("\n"):
        control.encode_string(line)
    control.eject_paper()

control.cleanup()
