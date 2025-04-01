import os
import signal
import threading
import control

SPOOLER_SEM = threading.Semaphore() # automatically w/ count 1
JOB_COUNT = 0
PIPE_PATH = "/var/run/user/1000/text2touch_pipe"
STATUS_PIPE_PATH = "/var/run/user/1000/text2touch_status_pipe"

def print_job(data: str) -> None:
    '''
    Sets up a chunk of data to be printed. This is meant to be the entry point of 
    a thread, where each thread is a job to be printed.

    Args:
        data (string): The entire text to be printed
    Returns:
        None
    '''
    global JOB_COUNT
    JOB_COUNT += 1
    SPOOLER_SEM.acquire()
    # critical section because ecoding will be running the hardware
    for line in data.split('\n'):
        transliteration = control.transliterate_string(line.strip())
        control.encode_string(transliteration)
    JOB_COUNT -= 1
    if JOB_COUNT > 0:
        input(f"\n There are {JOB_COUNT} other jobs waiting. Press enter to start the next.")
    SPOOLER_SEM.release()

def handle_kill(sig, frame) -> None:
    '''Do routine cleanup and remove pipe. For when a kill signal is detected'''
    control.cleanup()
    os.remove(PIPE_PATH)
    exit(0)

def main() -> None:
    control.setup()
    signal.signal(signal.SIGINT, handle_kill)

    # Set up pipe
    try:
        os.mkfifo(PIPE_PATH)
    except FileExistsError:
        print("Pipe already exists, carrying on as normal")
        # TODO: clear pipe here?
    except OSError as e:
        print("Error creating pipe:", e)
        exit(-1)
    finally:
        print("Pipe ready at " + PIPE_PATH)

    while True:
        # have to keep opening the pipe because the connection closes
        # after all writers are done
        with open(PIPE_PATH, "r") as pipe:
            print_job(pipe.read().strip())

main()

