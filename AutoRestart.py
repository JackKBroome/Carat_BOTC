import atexit
import os.path
import subprocess
import sys
import time

carat_file = "Carat.py"
utility_file = "utility.py"
carat_update_file = "Carat_UPDATE.py"
utility_update_file = "utility_UPDATE.py"

bot_process = None


# terminate subprocess properly
def terminate_bot():
    if bot_process is not None and bot_process.poll() is None:
        bot_process.terminate()
        bot_process.wait()


def ensure_newest():
    # check whether update files for Carat.py/utility.py exist, if they do, replace old files
    if os.path.exists(carat_update_file) and os.path.exists(utility_update_file):
        if os.path.exists(carat_file):
            os.remove(carat_file)
        os.rename(carat_update_file, carat_file)
        if os.path.exists(utility_file):
            os.remove(utility_file)
        os.rename(utility_update_file, utility_file)


def main():
    global bot_process
    # register terminate_bot to be triggered when AutoRestart is stopped
    atexit.register(terminate_bot)
    while True:
        ensure_newest()
        bot_process = subprocess.Popen([sys.executable, carat_file])
        bot_process.wait()
        time.sleep(10)  # Add a delay before restarting to avoid rapid restarts


if __name__ == "__main__":
    main()
