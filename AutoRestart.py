import atexit
import subprocess
import sys
import time

bot_process = None


# terminate subprocess properly
def terminate_bot():
    if bot_process is not None and bot_process.poll() is None:
        bot_process.terminate()
        bot_process.wait()


def main():
    global bot_process
    # register terminate_bot to be triggered when AutoRestart is stopped
    atexit.register(terminate_bot)
    while True:
        bot_process = subprocess.Popen([sys.executable, "Carat.py"])
        bot_process.wait()
        time.sleep(10)  # Add a delay before restarting to avoid rapid restarts


if __name__ == "__main__":
    main()
