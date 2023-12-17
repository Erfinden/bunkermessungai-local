from flask import Flask, render_template, request, redirect
import threading
import time
import json
import requests
import platform
import os
import datetime
from cryptography.fernet import Fernet

app = Flask(__name__)

# create config.json if it doesn't exist with default values
if not os.path.exists("config.json"):
    with open("config.json", "w") as f:
        config = {
            "key": "",
            "time": "5",
            "ping_success": False,
            "main_url": "https://bunkermessungai.de:5000",
            "capturing": False
        }
        json.dump(config, f)

# Define global variables
cookies = {}
config = {}

# If the folder static/images doesnt exist create it
if not os.path.exists("static/images"):
    os.makedirs("static/images")


def refresh_config():
    global config
    with open('config.json', 'r') as f:
        file_content = f.read().strip()
        if file_content:
            try:
                config = json.loads(file_content)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in config.json")
        else:
            print("Error: config.json is empty")

# Initialize the config variable
refresh_config()
main_url = config["main_url"]

# Try to setup GPIO
if platform.system() == 'Linux':
    try:
        import RPI.GPIO
        import RPi.GPIO as GPIO
    except:
        print("")
        print("GPIO library not installed: pip install RPI.GPIO when on a rasperry pi, else ignore")
        print("")

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.cleanup()
    PowerLED = 23
    StatusLED = 24
    GPIO.setup(PowerLED, GPIO.OUT)
    GPIO.setup(StatusLED, GPIO.OUT)
    GPIO.output(PowerLED, GPIO.HIGH)
except:
    pass

def generate_key():
    """Generates a key and save it into a file if it doesn't exist."""
    if not os.path.exists("secret.key"):
        key = Fernet.generate_key()
        with open("secret.key", "wb") as key_file:
            key_file.write(key)

generate_key()

def load_key():
    """Loads the key from the current directory named `secret.key`."""
    return open("secret.key", "rb").read()

def encrypt_credentials(username, password):
    """Encrypts the username and password and stores them in a file."""
    key = load_key()
    cipher_suite = Fernet(key)
    encrypted_data = {
        "username": cipher_suite.encrypt(username.encode()).decode(),
        "password": cipher_suite.encrypt(password.encode()).decode()
    }
    
    with open("credentials.enc", "w") as file:
        json.dump(encrypted_data, file)

def decrypt_credentials():
    """Decrypts the username and password and returns them."""
    key = load_key()
    cipher_suite = Fernet(key)

    with open("credentials.enc", "r") as file:
        encrypted_data = json.load(file)

    decrypted_data = {
        "username": cipher_suite.decrypt(encrypted_data["username"].encode()).decode(),
        "password": cipher_suite.decrypt(encrypted_data["password"].encode()).decode()
    }

    return decrypted_data["username"], decrypted_data["password"]

def login_to_server(username, password):
    """Login to the server, update the access token cookie, and store encrypted credentials."""
    global cookies

    data = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(f'{main_url}/login', json=data)
        if response.status_code == 200:
            cookies['access_token_cookie'] = response.cookies['access_token_cookie']
            encrypt_credentials(username, password)  # Store the credentials once successfully logged in
        else:
            print("Failed to login:", response.json())
    except Exception as e:
        print("Error during login:", e)


def capture_and_upload():
    while True:
        refresh_config()
        capturing = config["capturing"]
        
        if capturing == True:
            try:
                # Capture and upload image
                if platform.system() == 'Windows':
                    capture_image_windows()
                elif platform.system() == 'Linux':
                    capture_image_linux()
                
                # Fetch and print data for each IP address
                fetch_data_from_brenner()
                
                # Sleep for the appropriate amount of time
                time.sleep(86400 / int(config['time']))
            except Exception as e:
                print("Error:", e)


def upload_image(key, brenner_info):
    global cookies
    url = f'{main_url}/upload'
    files = {'image': open("static/images/captured_image.jpg", 'rb')}
    data = {'key': key, 'brenner': brenner_info}
    cookies=cookies
    try:
        response = requests.post(url, files=files, data=data, cookies=cookies)
        print(response.json())
    except Exception as e:
        print("Error uploading Image. error: \n"+ e)


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


@app.route('/')
def index():
    refresh_config()
    capturing = config["capturing"]
    image_path = os.path.join(app.static_folder, 'images', 'captured_image.jpg')
    
    if os.path.exists(image_path):
        last_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(image_path)) + datetime.timedelta(hours=1)
        formatted_last_modified = last_modified_time.strftime('%d/%m/%Y %H:%M:%S')
    else:
        formatted_last_modified = ""
    
    config_key = config['key']
    
    if os.path.exists("credentials.enc"):
        username, _ = decrypt_credentials()
    else:
        username = "Not logged in!"

    if config_key == "":
        config_key = None

    return render_template('index.html', last_modified=formatted_last_modified, capturing=capturing, config=config, config_key=config_key, username=username)

@app.route('/reboot')
def reboot():
    os.system("sudo reboot")
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    login_to_server(username, password)
    return redirect('/')

@app.route('/logout', methods=['POST'])
def logout():
    if os.path.exists("credentials.enc"):
        os.remove("credentials.enc")
    global cookies
    cookies = {}
    return redirect('/')

@app.route('/start_capture')
def start_capture():
    refresh_config()    
    config["capturing"] = True
    with open('config.json', 'w') as f:
        json.dump(config, f)
    return redirect('/')

@app.route('/stop_capture')
def stop_capture():
    refresh_config()
    config["capturing"] = False
    with open('config.json', 'w') as f:
        json.dump(config, f)
    return redirect('/')

def ping_server(key):
    global config
    global cookies
    url = f'{main_url}/status_cam'
    data = {'key': key}

    try:
        response = requests.post(url, data=data, cookies=cookies)
        response_json = response.json()
        
        # Check for token expiration
        if response_json.get('message') == "Token expired, relogin!":
            print("Token expired!")
            if os.path.exists("credentials.enc"):
                username, password = decrypt_credentials()
                login_to_server(username, password)
                # Retry the ping after re-login
                response = requests.post(url, data=data, cookies=cookies)
            else:
                print("Token expired and no encrypted credentials found. Please login.")
        elif response_json.get('message') == "No token, relogin!":
            print("Token missing! Please login.")
            try:
                username, password = decrypt_credentials()
                login_to_server(username, password)
            except:
                pass
            return  # Skip further processing
        
        

        print(response.text)
        config['ping_success'] = True
        if platform.system() == 'Linux':
            try:
                GPIO.output(StatusLED, GPIO.HIGH)
            except:
                pass
    except requests.RequestException as e:
        print(f"Error pinging the server: {e}")
        config['ping_success'] = False
        if platform.system() == 'Linux':
            try:
                GPIO.output(StatusLED, GPIO.LOW)
            except:
                pass
    except Exception as e:
        print(f"Unexpected error: {e}")

def periodic_ping():
    global config
    while True:
        ping_server(config['key'])
        time.sleep(10)

@app.route('/update_config', methods=['POST'])
def update_config():
    global config
    
    key = request.form.get('key')
    time = request.form.get('time')
    
    # Brenner Fields - these are now lists
    brenner_ips = request.form.getlist('brenner_ip')
    brenner_names = request.form.getlist('brenner_name')
    
    config['key'] = key
    config['time'] = time
    config['brenner'] = [
        {"ip": ip, "name": name} for ip, name in zip(brenner_ips, brenner_names)
    ]
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    return redirect('/')



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
    refresh_config()
    if "brenner" in config:
        q = "22069"  # Query parameter for data fetching

        # Fetch and print data for each IP address
        all_brenner_data = []
        for idx, brenner in enumerate(config['brenner'], start=1):
            ip_address = brenner['ip']
            brenner_name = brenner.get('name', f'brenner[{idx}]')
            hdg_comm = HdgComm(ip_address, q)
            
            # Get brenner data
            brenner_data = hdg_comm.data_refresh(lambda data, error: callback(data, error, brenner_name, ip_address))
            all_brenner_data.append(brenner_data)

        # Combine all brenner data into a single string and upload
        upload_image(config['key'], "; ".join(all_brenner_data))
    else: # No brenner data
        print("uploading image without brenner data")
        upload_image(config['key'], "")

if __name__ == '__main__':
    try:
        # Start threads for periodic pinging and data fetching
        threading.Thread(target=capture_and_upload).start()
        threading.Thread(target=periodic_ping).start()
        # Run Flask
        app.run(host='0.0.0.0', port=80)
    except KeyboardInterrupt:
        print("Server stopped by user.")
        if platform.system() == 'Linux':
            try:
                GPIO.cleanup()
            except:
                pass
