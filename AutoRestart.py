import subprocess
import sys
import time


def main():
    while True:
        bot_process = subprocess.Popen([sys.executable, "Carat.py"])
        bot_process.wait()
        time.sleep(10)  # Add a delay before restarting to avoid rapid restarts


if __name__ == "__main__":
    main()
