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
    print("Moving stepper 0 by 1 cm")
    control.move_stepper_cm(0)

    print("Testing stepper 1")
    for i in range(20):
        control.KIT.stepper2.onestep() if i < 10 else control.KIT.stepper2.onestep(direction = stepper.BACKWARD)
        sleep(control.STEPPER_PAUSE)
    sleep(1)
    print("Moving stepper 1 by 1 cm")
    control.move_stepper_cm(1)

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

if input("Test braille printing in terminal? (y/N) ").lower() == 'y':
    while c := input("Enter character to see braille encoding, or nothing to end. DON'T CTRL-C!\n"):
        if encoding := control.CHAR_ENCODES.get(c):
            for row in zip(encoding[0], encoding[1]): print(row)
        else:
            print("Didn't find character " + c)

if input("Test braille printing w/ hardware? (y/N) ").lower() == 'y':
    while s := input("Input string to test printing, or nothing to end. DON'T CTRL-C!\n"):
        control.encode_string(s)

control.cleanup()
