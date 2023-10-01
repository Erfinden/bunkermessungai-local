from flask import Flask, render_template, request, redirect
import threading
import time
import json
import requests
import platform
import os
import datetime

main_url = "https://bunkermessungai.de:5000"

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("GPIO library not installed. This code is intended to run on Raspberry Pi.")

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.cleanup()
PowerLED = 23
StatusLED = 24
GPIO.setup(PowerLED, GPIO.OUT)
GPIO.setup(StatusLED, GPIO.OUT)
GPIO.output(PowerLED, GPIO.HIGH)

with open('/home/bunkermessungai-local/config.json', 'r') as f:
    config = json.load(f)

capturing = False
capture_thread = None

def capture_and_upload():
    global capturing
    while capturing:
        with open('/home/bunkermessungai-local/config.json', 'r') as f:
            config = json.load(f)
        try:
            if platform.system() == 'Windows':
                capture_image_windows(config['key'])
            elif platform.system() == 'Linux':
                capture_image_linux(config['key'])
            time.sleep(86400 / int(config['time']))
        except Exception as e:
            print("Error:", e)

def upload_image(key):
    url = f'{main_url}/upload'
    files = {'image': open("static/images/captured_image.jpg", 'rb')}
    data = {'key': key}
    try:
        response = requests.post(url, files=files, data=data)
        print(response.text)
    except:
        print("Error uploading Image")

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
    url = f'{main_url}/status_cam'
    data = {'key': key}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print(response.text)
        config['ping_success'] = True
        GPIO.output(StatusLED, GPIO.HIGH)
    except requests.RequestException as e:
        print(f"Error pinging the server: {e}")
        config['ping_success'] = False
        GPIO.output(StatusLED, GPIO.LOW)
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
    config['key'] = key
    config['time'] = time
    with open('/home/bunkermessungai-local/config.json', 'w') as f:
        json.dump(config, f, indent=4)
    return redirect('/')

if __name__ == '__main__':
    try:
        threading.Thread(target=periodic_ping).start()
        app.run(host='0.0.0.0', port=80)
    except KeyboardInterrupt:
        print("Server stopped by user.")
        GPIO.cleanup()
