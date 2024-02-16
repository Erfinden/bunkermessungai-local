#!/bin/bash

# Install Prerequisites
sudo apt install -y python3-pip python3 git fswebcam libraspberrypi-bin

# Enable camera module
sudo raspi-config nonint do_camera 0

# Install Avahi Daemon
sudo apt install avahi-daemon

# Configure Avahi Daemon
sudo sed -i 's/#host-name=.*$/host-name=bunkermessungai/' /etc/avahi/avahi-daemon.conf

# Install required Python packages
sudo pip install -r ../requirements.txt

# Clone the repo
sudo git clone https://github.com/Erfinden/bunkermessungai-local /home/bunkermessungai-local


# Define the path to the main.py script and the desired service name
SCRIPT_PATH="/home/bunkermessungai-local/main.py"
SERVICE_NAME="cam"

# Get the current user and group for the service
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

# Create the systemd service unit file
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Run cam.py script

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH
Restart=always
User=$CURRENT_USER
Group=$CURRENT_GROUP

[Install]
WantedBy=multi-user.target
EOF


# Restart Avahi Daemon
sudo systemctl restart avahi-daemon

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable "$SERVICE_NAME.service"
sudo systemctl start "$SERVICE_NAME.service"

echo "Installation completed successfully."
sleep 1
echo "rebooting in ...3"
sleep 1
echo "rebooting in ...2"
sleep 1
echo "rebooting in ...1"
sudo reboot
