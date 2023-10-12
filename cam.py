from flask import Flask, render_template, request, redirect
import threading
import time
import json
import requests
import platform
import os
import datetime

cookies = {'access_token_cookie': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTY5NjY5NjA5OSwianRpIjoiMzE1YmU3NzItYzlhZC00ZGZkLTliYWUtYmUyY2IwZGJmMmE5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6InRlc3QiLCJuYmYiOjE2OTY2OTYwOTksImV4cCI6MTY5NjY5Njk5OX0.STtFU-gxvgoIvsT9qY2dldnJVevBtyS_g8aRZrOSQn4'}

# try to import GPIO on linux
if platform.system() == 'Linux':
    try:
        import RPI.GPIO
        import RPi.GPIO as GPIO
    except:
        print("")
        print("GPIO library not installed: pip install RPI.GPIO when on a rasperry pi, else ignore")
        print("")

with open('config.json', 'r') as f:
    config = json.load(f)


app = Flask(__name__)

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

main_url = config["main_url"]
capturing = False
capture_thread = None

def capture_and_upload():
    global capturing
    while capturing:
        with open('config.json', 'r') as f:
            config = json.load(f)
        try:
            # Capture and upload image
            if platform.system() == 'Windows':
                capture_image_windows(config['key'])
            elif platform.system() == 'Linux':
                capture_image_linux(config['key'])
            
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


def capture_image_windows(key):
    import cv2
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("static/images/captured_image.jpg", frame)
        upload_image(key)
    cap.release()

def capture_image_linux(key):
    try:
        os.system("sudo fswebcam -r 1280x720 --no-banner /home/bunkermessungai-local/static/images/captured_image.jpg")
        upload_image(key)
    except:
        print("Failed to capture image.")

@app.route('/')
def index():
    image_path = os.path.join(app.static_folder, 'images', 'captured_image.jpg')
    last_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(image_path)) + datetime.timedelta(hours=1)
    formatted_last_modified = last_modified_time.strftime('%d/%m/%Y %H:%M:%S')
    config_key = config['key']
    if config_key == "":
        config_key = None
    return render_template('index.html', last_modified=formatted_last_modified, capturing=capturing, config=config, config_key=config_key)

@app.route('/start_capture')
def start_capture():
    global capturing, capture_thread
    if not capturing:
        capturing = True
        capture_thread = threading.Thread(target=capture_and_upload)
        capture_thread.start()
    return redirect('/')

@app.route('/stop_capture')
def stop_capture():
    global capturing
    capturing = False
    if capture_thread:
        capture_thread.join()
    return redirect('/')

def ping_server(key):
    global config
    global cookies
    url = f'{main_url}/status_cam'
    data = {'key': key}
    cookies=cookies
    try:
        response = requests.post(url, data=data,cookies=cookies)
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


if __name__ == '__main__':
    try:
        # Start threads for periodic pinging and data fetching
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
