############################
## This script is used to abstract sending and receiving
## driver information to/from the rest of the system
## 
## Author: Kenneth Howes, 2025, kenneth.howes53@gmail.com
############################
import posix_ipc
from typing import Callable
import threading

class BrailleDriverCommunicator:
    STATUS_QUEUE = "/text2touch_status_pipe"
    COMMAND_QUEUE = "/text2touch_command_pipe"

    def __init__(self):
        if not posix_ipc.MESSAGE_QUEUES_SUPPORTED:
            raise SystemError("Messages queues are not supported on this system")

        # create message queue if need be
        self.status_mq = posix_ipc.MessageQueue(self.STATUS_QUEUE, posix_ipc.O_CREAT)
        self.command_mq = posix_ipc.MessageQueue(self.COMMAND_QUEUE, posix_ipc.O_CREAT)
    
    def stop(self) -> None:
        print("\nExiting...")
        try:
            # remove process from message queue
            posix_ipc.unlink_message_queue(self.STATUS_QUEUE)
            posix_ipc.unlink_message_queue(self.COMMAND_QUEUE)
        except posix_ipc.ExistentialError:
            pass
    
    def write_status(self, message: str, priority: int = 0) -> None:
        self.status_mq.send(message, None, priority)

    def read_status(self) -> str:
        message, priority = self.status_mq.receive()
        return message.decode()
        
    def write_cmd(self, message: str, priority: int = 0) -> None:
        self.command_mq.send(message, None, priority)

    def read_cmd(self) -> str:
        message, priority = self.command_mq.receive()
        return message.decode()
    
    def listen_status(self, listen_cb: Callable[[str], None]) -> None:
        def thread():
            while True:
                listen_cb(self.read_status())

        threading.Thread(target=thread,daemon=True).start()

    def listen_cmd(self, listen_cb: Callable[[str], None]) -> None:
        def thread():
            while True:
                listen_cb(self.read_cmd())

        threading.Thread(target=thread,daemon=True).start()


if __name__ == "__main__":
    from time import sleep

    driver_comm = BrailleDriverCommunicator()
    driver_comm.write_status("hello")
    sleep(1)
    assert(driver_comm.read_status() == "hello")
    driver_comm.write_cmd("commanding!")
    sleep(1)
    assert(driver_comm.read_cmd() == "commanding!")

    # setup dummy listeners
    driver_comm.listen_status(print)
    driver_comm.listen_cmd(print)

    # send messages to listeners
    driver_comm.write_status("status")
    driver_comm.write_cmd("command")

    sleep(5) # time for the daemon listeners to do their work
    # should see 'status' and 'command' in terminal

    driver_comm.stop()
