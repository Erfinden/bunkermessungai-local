#!/bin/bash
#!/bin/bash
function install_raspi {
    # Install Raspberrypi specific packages
    sudo apt install -y libraspberrypi-bin
    ###### Set Hostname to bunkermessungai.local ######
    # Install Avahi Daemon
    sudo apt install -y avahi-daemon

    # Configure Avahi Daemon
    sudo sed -i 's/#host-name=.*$/host-name=bunkermessungai/' /etc/avahi/avahi-daemon.conf
    ###################################################


    ###### Auto Run Script on Boot ######
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
    #####################################
}


# Install Prerequisites
sudo apt install -y python3-pip python3 git fswebcam
# Clone the repo
sudo git clone https://github.com/Erfinden/bunkermessungai-local /home/bunkermessungai-local

# Install required Python packages
sudo pip install -r /home/bunkermessungai-local/requirements.txt


# Check if running on Raspberry Pi
if [[ $(uname -m) == "arm"* ]]; then
    echo "Running on Raspberry Pi, setting up Kamera, Hostname and Autostart."
    install_raspi
else
    echo "Not running on Raspberry Pi, Skipping further setup."
fi

echo "Installation completed successfully."
echo "Reboot? (y/n)"
read -r REBOOT
if [[ "$REBOOT" == "y" ]]; then
    sudo reboot
fi
