#!/bin/bash

# Activate legacy camera automaticly, if needed  
sudo bash -c 'if grep -q "^start_x=" /boot/config.txt; then sed -i "s/^start_x=.*/start_x=1/" /boot/config.txt; else echo "start_x=1" >> /boot/config.txt; fi'
sudo bash -c 'if grep -q "^gpu_mem=" /boot/config.txt; then sed -i "s/^gpu_mem=.*/gpu_mem=128/" /boot/config.txt; else echo "gpu_mem=128" >> /boot/config.txt; fi'
sudo bash -c 'if grep -q "^camera_auto_detect=" /boot/config.txt; then sed -i "s/^camera_auto_detect=.*/#camera_auto_detect=1/" /boot/config.txt; else echo "#camera_auto_detect=1" >> /boot/config.txt; fi'

# install important stuff
sudo apt install -y python3-pip python3 git

# Install fswebcam
sudo apt install fswebcam

# Install Avahi Daemon
sudo apt install avahi-daemon

# Configure Avahi Daemon
sudo sed -i 's/#host-name=.*$/host-name=bunkermessungai/' /etc/avahi/avahi-daemon.conf

# Restart Avahi Daemon
sudo systemctl restart avahi-daemon

# Install required Python packages
sudo pip install flask requests RPi.GPIO cryptography apscheduler

# Clone the repo
sudo git clone https://github.com/Erfinden/bunkermessungai-local /home/bunkermessungai-local

# Define the path to the cam.py script and the desired service name
SCRIPT_PATH="/home/bunkermessungai-local/cam.py"
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
sleep 1
echo "rebooting in ...3"
sleep 1
echo "rebooting in ...2"
sleep 1
echo "rebooting in ...1"
sudo reboot
