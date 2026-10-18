from threading import Thread
from signal import pause
from gpiozero import Button

import logging, json, os
import urllib.request, urllib.error

logger = logging.getLogger(__name__)

URL = os.getenv("URL", "http://127.0.0.1:80")
NEXT_BUTTON_GPIO = int(os.getenv("NEXT_BUTTON_GPIO", "22"))
PREVIOUS_BUTTON_GPIO = int(os.getenv("PREVIOUS_BUTTON_GPIO", "23"))

next_button = Button(NEXT_BUTTON_GPIO, pull_up=True, bounce_time=0.05)
back_button = Button(PREVIOUS_BUTTON_GPIO, pull_up=True, bounce_time=0.05)

gpio_thread = None

def do_request(req: urllib.request.Request):
    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
            if data["status"] == "error":
                logger.error(data)
            else:
                logger.debug(data)
    except urllib.error.HTTPError as e:
        logger.error(f"HTTPError: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError: {e}")

def next_button_pressed():
    logger.debug("Next button pressed")
    req = urllib.request.Request(
        f"{URL}/next", data=b"{}", headers={"Content-Type": "application/json"}
    )
    do_request(req)

def back_button_pressed():
    logger.debug("Back button pressed")
    req = urllib.request.Request(
        f"{URL}/previous", data=b"{}", headers={"Content-Type": "application/json"}
    )
    do_request(req)


next_button.when_pressed = next_button_pressed
back_button.when_pressed = back_button_pressed

def monitor_buttons():
    print("Monitoring GPIO Buttons")
    pause()

def start_button_thread():
    global gpio_thread
    gpio_thread = Thread(target=monitor_buttons, daemon=True)
    gpio_thread.start()


if __name__ == "__main__":
    start_button_thread()
    if gpio_thread is not None:
        gpio_thread.join()
