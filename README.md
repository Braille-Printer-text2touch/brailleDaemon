# Braille Printer Daemon

Takes in requests from various interfaces and runs the Raspberry PI's GPIO pins
accordingly.

Will be prototyped in Python using CircuitPython and daughter board libraries provided by Adafruit.
Future work may include porting that functionality to C.

Requires [Adafruit's CircuitPython Motor Kit library](https://docs.circuitpython.org/projects/motorkit/en/latest/), which has
it's own set of dependencies.

## Using the Daemon

On the Pi, the daemon runs in a virtual environment with all dependencies. To use:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python3 daemon.py
```

### Running the Entire System

Text2Touch is made of several components, including the braille printer daemon, a web server, and an IPP printer. To run the entire system, you need to start each component separately. The following script shows an example of how to do this.

```bash
#!/bin/bash

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root."
  exit 1
fi

# Function to kill a process by script name if running
kill_process() {
  local script_name=$1
  local pids
  pids=$(pgrep -f "$script_name")
  if [ -n "$pids" ]; then
    echo "Killing existing processes for $script_name"
    kill $pids
  fi
}

kill_process "daemon.py"
kill_process "app.py"
kill_process "ipp.py"

cd webInterface
.venv/bin/python3 app.py &
cd ..

cd Pseudo-IPP-Printer
.venv/bin/python3 ipp.py &

# Advertise the IPP printer over mDNS
avahi-publish-service "Braille Printer" _ipp._tcp 631 &
cd ..

cd brailleDaemon/py
.venv/bin/python3 daemon.py
```

## Configuration

`config.toml` can be modified to change certain specifics about the driver. It comes with default values for all fields.

## Structure

This repository contains two major parts of the Braille printer project:

- the daemon, which listens for incoming messages on a FIFO named pipe and runs the driver accordingly
- the driver, which drives the machinery

The daemon exists in `daemon.py` (shocking) and the driver exists for the most part in `control.py`. There is an abstraction for the driver to interact with the rest of the system through POSIX message queues in `DriverCommunicator.py`

Coming into the named pipe should just be ASCII characters that have a direct Braille representation ([read more about ASCII Braille](https://en.wikipedia.org/wiki/Braille_ASCII)).

These ASCII characters are then sent through the transliteration unit (`transcriber.py`), which will handle turning the English string into a Braille string (see common Braille contractions, punctuation, etc. below).

There are also a couple tests for both physical and logical testing. `tester.py` walks a user through testing the driver's interations with the machinery. Both `DriverCommunicator.py` and `transcriber.py` can be run on their own, e.g. `python3 DriverCommunicator.py`, to run a seires of unit tests on their logic.

## Braille

The braille alphabet, for reference:

![Braille Alphabet picture should be here...](https://www.tsbvi.edu/wp-content/uploads/assets/images/in-body/fw-ibi-braille_alphabet.jpg)

Common braille contractions and punctuation, for reference:

![Braille Contractions picture should be here...](./resources/braille-quick-reference.png)
