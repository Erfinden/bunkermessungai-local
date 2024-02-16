import requests
from astral import LocationInfo
from astral.sun import sun
from datetime import date, datetime
import pytz
import os
import json
import platform
from cryptography.fernet import Fernet
import time
import state
import threading

def get_location_info():
    try:
        # Use the ip-api.com JSON endpoint for geolocation data
        response = requests.get('http://ip-api.com/json/')
        data = response.json()

        # Check for success status
        if data['status'] == 'success':
            latitude = data['lat']
            longitude = data['lon']
            return latitude, longitude
        else:
            return None, None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None

def sunrise_sunset():
    latitude, longitude = get_location_info()

    if latitude and longitude:
        print(f"Latitude: {latitude}, Longitude: {longitude}")
    else:
        return("Could not obtain location information.")


    # Create a LocationInfo object
    location = LocationInfo(latitude=latitude, longitude=longitude)

    # Use today's date for the calculation
    today = date.today()

    # Calculate sunrise and sunset times
    s = sun(location.observer, date=today)

    sunrise = s['sunrise'].strftime('%H:%M')
    sunset = s['sunset'].strftime('%H:%M')

    print(f"Sunrise: {sunrise}")
    print(f"Sunset: {sunset}")
    return sunrise, sunset

# HDG Brenner data fetching

class HdgComm:
    def __init__(self, url, q):
        if not url or not q:
            return
        self.base_url = f"http://{url}"
        self.data_query = {'nodes': q}
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

    def data_refresh(self, cb):
        try:
            response = requests.post(
                f"{self.base_url}/ApiManager.php?action=dataRefresh",
                data=self.data_query,
                headers=self.headers,
                timeout=5  # set a timeout for the request
            )
            if response.json():
                return cb(response.json(), "")
            else:
                return cb("", "Keine Daten erhalten")
        except requests.exceptions.ConnectTimeout:
            return cb("", f"Verbindung zu {self.base_url} hat zu lange gedauert (Timeout)")
        except requests.exceptions.RequestException as error:
            return cb("", f"Fehler bei Anfrage an {self.base_url}: {str(error)}")
        except Exception as e:
            return cb("", f"Unerwarteter Fehler: {str(e)}")



def callback(data, error, brenner_name, ip_adress):
    brenner_data = []
    if data:
        for item in data:
            if 'text' in item:
                brenner_info = f"{brenner_name}, (Ip: {ip_adress}), {item['text']}"
                brenner_data.append(brenner_info)
                print(brenner_info)
    else:
        print("Fehler:", error)
    
    # Combine brenner data into a single string and upload
    return "; ".join(brenner_data)



def fetch_data_from_brenner():
    if "brenner" in state.config:
        q = "22069"  # Query parameter for data fetching

        # Fetch and print data for each IP address
        all_brenner_data = []
        for idx, brenner in enumerate(state.config['brenner'], start=1):
            ip_address = brenner['ip']
            brenner_name = brenner.get('name', f'brenner[{idx}]')
            hdg_comm = HdgComm(ip_address, q)
            
            # Get brenner data
            brenner_data = hdg_comm.data_refresh(lambda data, error: callback(data, error, brenner_name, ip_address))
            all_brenner_data.append(brenner_data)

        return all_brenner_data
    

# Initialize login state
def initialize_login_state():
    if os.path.exists("config/credentials.enc"):
        try:
            # Attempt to decrypt the credentials to see if they are valid
            username, password = decrypt_credentials()
            # Send a request to the server to validate the credentials and get token
            login_to_server(username, password)
            state.logged_in.set()
        except Exception as e:
            print(f"Error validating credentials: {str(e)}")
            state.logged_in.clear()
    else:
        state.logged_in.clear()


def setup():
    # Create config.json if it doesn't exist with default values
    if not os.path.exists("config/config.json"):
        with open("config/config.json", "w") as f:
            config = {
                "key": "",
                "time": "5",
                "ping_success": False,
                "main_url": "http://localhost:5000",
                "capturing": False,
                "dayonly": False,
            }
            json.dump(config, f)
    
    # If the folder static/images doesnt exist create it
    if not os.path.exists("static/images"):
        os.makedirs("static/images")

    # Setup GPIO
    Setup_GPIO()

    # Generate a key if it doesn't exist
    generate_key()

    # Load default config values
    default_config()

    # Check if already logged in and set the event accordingly
    initialize_login_state() 

    # Start the capture and upload thread
    threading.Thread(target=periodic_ping).start()
    threading.Thread(target=capture_and_upload).start()

def Setup_GPIO():
    # Try to setup GPIO
    if platform.system() == 'Linux':
        try:
            import RPI.GPIO
            import RPi.GPIO as GPIO
        except:
            print("")
            print("GPIO library not installed: pip install RPI.GPIO For Led indicators, else ignore")
            print("")

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
        GPIO.setup(state.PowerLED, GPIO.OUT)
        GPIO.setup(state.StatusLED, GPIO.OUT)
        GPIO.output(state.PowerLED, GPIO.HIGH)
    except:
        pass

def GPIO_cleanup():
    if platform.system() == 'Linux':
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass

# Initialize login state
def initialize_login_state():
    if os.path.exists("config/credentials.enc"):
        try:
            # Attempt to decrypt the credentials to see if they are valid
            username, password = decrypt_credentials()
            # Send a request to the server to validate the credentials and get token
            login_to_server(username, password)
            state.logged_in.set()
        except Exception as e:
            print(f"Error validating credentials: {str(e)}")
            state.logged_in.clear()
    else:
        state.logged_in.clear()

def edit_config(key, value):
    state.config[key] = value
    with open('config/config.json', 'w') as f:
        json.dump(state.config, f)
    refresh_config()


def refresh_config():
    with open('config/config.json', 'r') as f:
        file_content = f.read().strip()
        if file_content:
            try:
                state.config = json.loads(file_content)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in config.json")
                state.config = {}  # Ensure config is a dictionary even after an error
        else:
            print("Error: config.json is empty")
            state.config = {}  # Ensure config is a dictionary even if file is empty

def default_config():
    edit_config("ping_success", False)
    edit_config("capturing", False)

def generate_key():
    """Generates a key and save it into a file if it doesn't exist."""
    if not os.path.exists("config/secret.key"):
        key = Fernet.generate_key()
        with open("config/secret.key", "wb") as key_file:
            key_file.write(key)
    

def load_key():
    """Loads the key from the current directory named `config/secret.key`."""
    return open("config/secret.key", "rb").read()

def encrypt_credentials(username, password):
    """Encrypts the username and password and stores them in a file."""
    key = load_key()
    cipher_suite = Fernet(key)
    encrypted_data = {
        "username": cipher_suite.encrypt(username.encode()).decode(),
        "password": cipher_suite.encrypt(password.encode()).decode()
    }
    
    with open("config/credentials.enc", "w") as file:
        json.dump(encrypted_data, file)

def decrypt_credentials():
    """Decrypts the username and password and returns them."""
    key = load_key()
    cipher_suite = Fernet(key)

    with open("config/credentials.enc", "r") as file:
        encrypted_data = json.load(file)

    decrypted_data = {
        "username": cipher_suite.decrypt(encrypted_data["username"].encode()).decode(),
        "password": cipher_suite.decrypt(encrypted_data["password"].encode()).decode()
    }

    return decrypted_data["username"], decrypted_data["password"]

def login_to_server(username, password):
    """Login to the server, update the access token cookie, and store encrypted credentials."""
    data = {
        "username": username,
        "password": password
    }
    try:
        response = requests.post(f'{state.config["main_url"]}/login', json=data)
        if response.status_code == 200:
            state.cookies['access_token_cookie'] = response.cookies['access_token_cookie']
            encrypt_credentials(username, password)  # Store the credentials once successfully logged in
            state.logged_in.set()  # Signal that login is successful
            print("Login successful")
            return "Login successful", True
        else:
            return f"Failed to login: {response.json()['message']}", False
    except Exception as e:
        return f"Error during login: {str(e)}", False

    


def capture_and_upload():
    class Capturing_stopped(Exception): pass
    while True:
        while state.logged_in.is_set():
            time.sleep(1)
            refresh_config()
            capturing = state.config["capturing"]
            day_only = state.config["dayonly"]

            while capturing == True:
                try:
                    # Get sunrise and sunset times
                    sunrise, sunset = sunrise_sunset()

                    # Get current time
                    current_time = datetime.now()

                    # Wenn day_only aktiv ist, berechne die Schlafzeit basierend auf Tageslichtstunden
                    if day_only:
                        # Berechne die Dauer des Tageslichts
                        daylight_duration = sunset - sunrise
                        # Berechne die Gesamtanzahl der Aufnahmen pro Tag
                        total_captures = 86400 / int(state.config['time'])
                        # Berechne die Schlafzeit basierend auf der Anzahl der Tageslichtstunden
                        if daylight_duration.total_seconds() > 0:
                            sleep_time = daylight_duration.total_seconds() / total_captures
                        else:
                            sleep_time = float('inf')  # Unendlich warten, wenn keine Tageslichtstunden vorhanden sind

                        # Check if current time is within daytime range
                        if current_time.time() < sunrise.time() or current_time.time() > sunset.time():
                            print("Skipping capture. Not within daytime range.")
                            time.sleep(sleep_time)  # Schlaf für die berechnete Zeit
                            continue
                    else:
                        # Setze Schlafzeit für die Nacht
                        sleep_time = 86400 / int(state.config['time'])

                    # Capture and upload image
                    if platform.system() == 'Windows':
                        capture_image_windows()
                    elif platform.system() == 'Linux':
                        capture_image_linux()

                    # Fetch and print data for each IP address
                    upload_image()

                    sleep_time = int(sleep_time)
                    # Sleep for the calculated amount of time
                    for i in range(sleep_time):
                        time.sleep(1)
                        if not state.config["capturing"]:
                            raise Capturing_stopped

                except Capturing_stopped:
                    print("Capturing stopped")
                    break
                except Exception as e:
                    print("Error:", e)


def upload_image():
    brenner_info = fetch_data_from_brenner()
    if brenner_info == "[]" or brenner_info == "" or brenner_info == None or brenner_info == []:
        brenner_info = "No Brenner Data!"

    key = state.config['key']
    url = f'{state.config["main_url"]}/upload'
    files = {'image': open("static/images/captured_image.jpg", 'rb')}
    data = {'key': key, 'brenner': brenner_info}
    try:
        response = requests.post(url, files=files, data=data, cookies=state.cookies)
        print(response.json())
    except Exception as e:
        print("Error uploading Image. error: \n" + str(e))  # Convert the exception to a string


def capture_image_windows():
    import cv2

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("static/images/captured_image.jpg", frame)
    cap.release()

def capture_image_linux():
    try:
        os.system("sudo fswebcam -r 1280x720 --no-banner /home/bunkermessungai-local/static/images/captured_image.jpg")
    except:
        print("Failed to capture image.")


def ping_server(key):
    url = f'{state.config["main_url"]}/status_cam'
    data = {'key': key}

    try:
        response = requests.post(url, data=data, cookies=state.cookies)
        response_json = response.json()
        
        # Check for token expiration
        if response_json.get('message') == "Token expired, relogin!":
            print("Token expired!")
            if os.path.exists("config/credentials.enc"):
                username, password = decrypt_credentials()
                login_to_server(username, password)
                # Retry the ping after re-login
                response = requests.post(url, data=data, cookies=state.cookies)
            else:
                print("Token expired and no encrypted credentials found. Please login.")
        elif response_json.get('message') == "No token, relogin!":
            print("Token missing! Please login.")
            edit_config('ping_success', False)
            try:
                username, password = decrypt_credentials()
                login_to_server(username, password)
            except:
                pass
            return  # Skip further processing
        

        print(response.text)
        edit_config('ping_success', True)
        if platform.system() == 'Linux':
            try:
                import RPi.GPIO as GPIO
                GPIO.output(state.StatusLED, GPIO.HIGH)
            except:
                pass
    except requests.RequestException as e:
        print(f"Error pinging the server: {e}")
        edit_config('ping_success', False)
        if platform.system() == 'Linux':
            try:
                GPIO.output(state.StatusLED, GPIO.LOW)
            except:
                pass
    except Exception as e:
        print(f"Unexpected error: {e}")

def periodic_ping():
    while True:
        while state.logged_in.is_set():
            ping_server(state.config['key'])
            time.sleep(10)

