from time import sleep
from adafruit_motorkit import MotorKit

kit = MotorKit()

for i in range(10):
    kit.stepper1.onestep()
    print("Stepping one step on motor 1")
    sleep(1)

