import os
import signal
import threading
from control import BraillePrinterDriver
from queue import Queue
import time
from DriverCommunicator import BrailleDriverCommunicator

PIPE_PATH = "/var/run/user/1000/text2touch_pipe"

# Spooler queue to manage print jobs
SPOOLER_QUEUE = Queue()

CONTROL      = BraillePrinterDriver()
DRIVER_COMMS = BrailleDriverCommunicator()

def spool_job(data: str) -> None:
    '''
    Adds a print job to the spooler queue.

    Args:
        data (string): The entire text to be printed
    Returns:
        None
    '''
    SPOOLER_QUEUE.put(data)
    print(f"Job added to spooler. Queue size: {SPOOLER_QUEUE.qsize()}")

def process_spooler() -> None:
    '''
    Continuously processes jobs from the spooler queue.
    This function should run in a separate thread.

    Returns:
        None
    '''
    while True:
        job = SPOOLER_QUEUE.get()  # blocks until a job is available
        print(f"Processing job. Queue size: {SPOOLER_QUEUE.qsize()}")
        print_job(job)
        SPOOLER_QUEUE.task_done()
        pause_for_next_job()

def pause_for_next_job() -> None:
    '''
    Waits to start the next job in the spooler queue.
    This function should be called when a job is completed.

    Returns:
        None
    '''
    while True:
        command = DRIVER_COMMS.read_cmd()
        if command == "next":
            return
        elif input("Next doc? (y/n): ").strip().lower() == "y":
            return
        else:
            time.sleep(1)  # wait for a second before checking again

def print_job(data: str) -> None:
    '''
    Sets up a chunk of data to be printed. This is meant to be the entry point of 
    a thread, where each thread is a job to be printed.

    Args:
        data (string): The entire text to be printed
    Returns:
        None
    '''
    # critical section because ecoding will be running the hardware
    for line in data.split('\n'):
        transliteration = CONTROL.transliterate_string(line.strip())
        CONTROL.encode_string(transliteration)

def handle_kill(sig, frame) -> None:
    '''Do routine cleanup and remove pipe. For when a kill signal is detected'''
    os.remove(PIPE_PATH)
    SPOOLER_THREAD.join()
    exit(0)

def safe_start_pipe(path: str) -> None:
    try:
        os.mkfifo(path)
    except FileExistsError:
        print(f"{path} pipe already exists, carrying on as normal")
        # TODO: clear pipe here?
    except OSError as e:
        print(f"Error creating {path} pipe:", e)
        exit(-1)
    finally:
        print(f"{path} pipe ready")

SPOOLER_THREAD: threading.Thread = threading.Thread(target=process_spooler, daemon=True)
def main() -> None:
    signal.signal(signal.SIGINT, handle_kill)

    # Set up pipes
    safe_start_pipe(PIPE_PATH)

    # Start spooler thread
    SPOOLER_THREAD.start()
    print("Spooler thread started")

    while True:
        # have to keep opening the pipe because the connection closes
        # after all writers are done
        with open(PIPE_PATH, "r") as pipe:
            spool_job(pipe.read().strip())

if __name__ == "__main__":
    main()

