############################
## This script is used to abstract sending the driver information to the system
## 
## Author: Kenneth Howes, 2025, kenneth.howes53@gmail.com
############################
import posix_ipc

class BrailleDriverInfoPoster:
    QUEUE_NAME = "/text2touch-driver-info"

    def __init__(self):
        if not posix_ipc.MESSAGE_QUEUES_SUPPORTED:
            raise SystemError("Messages queues are not supported on this system")

        # create message queue if need be
        self.mq = posix_ipc.MessageQueue(self.QUEUE_NAME, posix_ipc.O_CREAT)
    
    def stop(self) -> None:
        print("\nExiting...")
        try:
            # remove process from message queue
            posix_ipc.unlink_message_queue(self.QUEUE_NAME)
        except posix_ipc.ExistentialError:
            pass
        
    def write(self, message: str, priority: int = 0) -> None:
        self.mq.send(message, None, priority)

if __name__ == "__main__":
    from time import sleep

    driver_info = BrailleDriverInfoPoster()
    while (True):
      # send hello every 5 seconds
      driver_info.write("hello")
      sleep(5)
