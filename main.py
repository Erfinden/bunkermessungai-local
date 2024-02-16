from flask import Flask, render_template, request, redirect, flash
import json
import os
from datetime import datetime, timedelta
from tools import *
import state

refresh_config()

app = Flask(__name__)
app.secret_key = Fernet.generate_key()



@app.route('/')
def index():
    refresh_config()
    capturing = state.config["capturing"]
    image_path = os.path.join(app.static_folder, 'images', 'captured_image.jpg')
    
    if os.path.exists(image_path):
        last_modified_time = datetime.fromtimestamp(os.path.getmtime(image_path)) + timedelta(hours=1)
        formatted_last_modified = last_modified_time.strftime('%d/%m/%Y %H:%M:%S')
    else:
        formatted_last_modified = ""
    
    config_key = state.config['key']
    
    if os.path.exists("config/credentials.enc"):
        username, _ = decrypt_credentials()
    else:
        username = "Not logged in!"

    if config_key == "":
        config_key = None

    return render_template('index.html', last_modified=formatted_last_modified, capturing=capturing, config=state.config, config_key=config_key, username=username)

@app.route('/reboot')
def reboot():
    os.system("sudo systemctl restart cam.service")
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    message, success = login_to_server(username, password)
    if not success:
        flash(message)
    return redirect('/')

@app.route('/logout', methods=['POST'])
def logout():
    if os.path.exists("config/credentials.enc"):
        os.remove("config/credentials.enc")
    state.cookies = {}
    state.logged_in.clear()  # Clear the logged_in event
    default_config()  # Reset the config to default values
    return redirect('/')

@app.route('/start_capture')
def start_capture():
    edit_config("capturing", True)
    return redirect('/')

@app.route('/stop_capture')
def stop_capture():
    edit_config("capturing", False)
    return redirect('/')


@app.route('/update_config', methods=['POST'])
def update_config():
    key = request.form.get('key')
    time = request.form.get('time')
    dayonly = request.form.get('dayonly')
    
    # Brenner Fields - these are now lists
    brenner_ips = request.form.getlist('brenner_ip')
    brenner_names = request.form.getlist('brenner_name')
    
    edit_config("dayonly", True if dayonly == "on" else False)
    edit_config("key", key)
    edit_config("time", time)
    edit_config("brenner", [{"ip": ip, "name": name} for ip, name in zip(brenner_ips, brenner_names)])

if __name__ == '__main__':
    try:
        setup()
        app.run(host='0.0.0.0', port=80)
    except KeyboardInterrupt:
        print("Server stopped by user.")
        GPIO_cleanup()