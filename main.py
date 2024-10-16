from time import sleep
from adafruit_motorkit import MotorKit
import os

PIPE_PATH = "/var/run/user/1000/text2type_pipe"

kit = MotorKit()

# Set up pipe
try:
    os.mkfifo(PIPE_PATH)
except FileExistsError:
    print("Pipe already exists, carrying on as normal")
except OSError as e:
    print("Error creating pipe:", e)
finally:
    print("Pipe ready at " + PIPE_PATH)

while True:
    # have to keep opening the pipe because the connection closes
    # after all writers are done
    with open(PIPE_PATH, "r") as pipe:
            print(pipe.read())

os.remove(PIPE_PATH)

# example code to drive motors
# for i in range(10):
#     kit.stepper1.onestep()
#     print("Stepping one step on motor 1")
#     sleep(1)

