import RPi.GPIO as GPIO
from adafruit_motor import stepper
from time import sleep
import control

control.setup()

if input("Test steppers? (y/N) ").lower() == 'y':
    print("Testing stepper 0")
    for i in range(20):
        control.KIT.stepper1.onestep() if i < 10 else control.KIT.stepper1.onestep(direction = stepper.BACKWARD)
        sleep(control.STEPPER_PAUSE)
    sleep(1)
    print("Moving stepper 0 by 20 steps")
    control.move_stepper_n_steps(0, 20)

    print("Testing stepper 1")
    for i in range(20):
        control.KIT.stepper2.onestep() if i < 10 else control.KIT.stepper2.onestep(direction = stepper.BACKWARD)
        sleep(control.STEPPER_PAUSE)
    sleep(1)
    print("Moving stepper 1 by 20 steps")
    control.move_stepper_n_steps(1, 20)

if input("Test solenoids? (y/N) ").lower() == 'y':
    print("Testing solenoid 0")
    GPIO.output(control.SOL_0, GPIO.HIGH)
    sleep(control.SOL_PAUSE)
    GPIO.output(control.SOL_0, GPIO.LOW)
    sleep(control.SOL_PAUSE)
    sleep(1)

    print("Testing solenoid 1")
    GPIO.output(control.SOL_1, GPIO.HIGH)
    sleep(control.SOL_PAUSE)
    GPIO.output(control.SOL_1, GPIO.LOW)
    sleep(control.SOL_PAUSE)
    sleep(1)

    print("Testing solenoid 2")
    GPIO.output(control.SOL_2, GPIO.HIGH)
    sleep(control.SOL_PAUSE)
    GPIO.output(control.SOL_2, GPIO.LOW)
    sleep(control.SOL_PAUSE)
    sleep(3)

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

control.cleanup()
