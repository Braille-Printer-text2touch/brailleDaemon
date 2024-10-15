from time import sleep
from adafruit_motorkit import MotorKit

kit = MotorKit()

for i in range(10):
    kit.stepper1.onestep()
    sleep(1)

