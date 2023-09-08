#!/bin/bash

# install important stuff
sudo apt-get install -y python3-pip nano git python3 

# Install fswebcam
sudo apt-get install fswebcam

# Install Avahi Daemon
sudo apt-get install avahi-daemon

# Configure Avahi Daemon
sudo sed -i 's/#host-name=.*$/host-name=bunkermessungai/' /etc/avahi/avahi-daemon.conf

# Restart Avahi Daemon
sudo systemctl restart avahi-daemon

# Install required Python packages
pip install Flask requests git

# Clone the repo
git clone https://github.com/Erfinden/bunkermessungai.local /home

# Define the path to the cam.py script and the desired service name
SCRIPT_PATH="/home/bunkermessungai.local/cam.py"
SERVICE_NAME="cam"

# Get the current user and group
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

# Create the systemd service unit file
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
echo "[Unit]" | sudo tee "$SERVICE_FILE" > /dev/null
echo "Description=Run cam.py script" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "[Service]" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "ExecStart=/usr/bin/python3 $SCRIPT_PATH" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "Restart=always" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "User=$CURRENT_USER" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "Group=$CURRENT_GROUP" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "[Install]" | sudo tee -a "$SERVICE_FILE" > /dev/null
echo "WantedBy=multi-user.target" | sudo tee -a "$SERVICE_FILE" > /dev/null

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable "$SERVICE_NAME.service"
sudo systemctl start "$SERVICE_NAME.service"

echo "Installation completed successfully."
