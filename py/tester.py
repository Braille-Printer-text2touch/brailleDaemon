######################################
## This file to test the printer hardware,
## Not nesseccarily the purely logical parts
## of the driver.
######################################
import RPi.GPIO as GPIO
from time import sleep
from control import BraillePrinterDriver
from math import pi

TEST_MESSAGE = "Hello!\nThis is a test. !123"

driver = BraillePrinterDriver()

# if input("Test steppers? (y/N) ").lower() == 'y':
#     n_steps = driver.__mm_to_steps(driver.PAPER_STEPPER_DIAMETER * 2 * pi, 10)
#     print("Testing Paper Stepper (10 mm)")
#     driver.__move_stepper_n_steps(driver.PAPER_STEPPER, n_steps)
#     sleep(1)
# 
#     n_steps = driver.__mm_to_steps(driver.PAPER_STEPPER_DIAMETER * 2 * pi, 10)
#     print("Testing Paper Stepper (10 mm)")
#     driver.__move_stepper_n_steps(driver.PAPER_STEPPER, -n_steps)
#     sleep(1)
# 
#     n_steps = driver.__mm_to_steps(driver.HEAD_STEPPER_DIAMETER * 2 * pi, 10)
#     print("Testing Head Stepper (10 mm)")
#     driver.__move_stepper_n_steps(driver.HEAD_STEPPER, n_steps)
#     sleep(1)
# 
#     n_steps = driver.__mm_to_steps(driver.HEAD_STEPPER_DIAMETER * 2 * pi, 10)
#     print("Testing Head Stepper (10 mm)")
#     driver.__move_stepper_n_steps(driver.HEAD_STEPPER, -n_steps)
#     sleep(1)

if input("Test solenoids? (y/N) ").lower() == 'y':
    for i in range(3):
        print(f"Testing solenoid {i}")
        driver.pwm_solenoids[i].start(driver.SOL_DUTY_CYCLE)
        sleep(driver.SOL_PAUSE)
        driver.pwm_solenoids[i].stop()
        sleep(driver.SOL_PAUSE)

if input("Test button? (y/N) ").lower() == 'y':
    print("Waiting for button press")
    while (GPIO.input(driver.BUTTON_PIN) == GPIO.HIGH):
        sleep(0.5)
    print("Button pressed")

    if (
        input("\033[33mTest starting the head? THIS CAN BREAK STUFF IF THE BUTTON IS NOT WORKING (y/N) \033[0m").lower() == 'y'
        and input("Are you sure? (y/N) ") == 'y'
    ):
        driver.reset_print_head()

        if input("Start print head? (y/N) ") == 'y':
            driver.start_print_head()

if input("Test new line? \033[33mBUTTON SHOULD BE TESTED AND WORKING\033[0m (y/N) ").lower() == 'y':
    driver.new_line()

# if input("Test braille printing in terminal? (y/N) ").lower() == 'y':
#     while s := input("Enter string to see braille encoding, or nothing to end. DON'T CTRL-C!\n"):
#         try:
#             for c in s:
#                 print(driver.ascii2braille(c), end="")
#             print() # new line
#         except Exception as e:
#             print(e)

if input("Test braille printing w/ hardware? (y/N) ").lower() == 'y':
    while s := input("Input string to test printing, or nothing to end. DON'T CTRL-C!\n"):
        driver.encode_string(s)

if input("Test with test message? (y/N) ").lower() == 'y':
    driver.reset_print_head()
    driver.start_print_head()
    for line in TEST_MESSAGE.split("\n"):
        driver.encode_string(line)
    driver.eject_paper()

