import threading

logged_in = threading.Event()

# GPIO
PowerLED = 23
StatusLED = 24

# Configuration
config = {}
cookies = {}