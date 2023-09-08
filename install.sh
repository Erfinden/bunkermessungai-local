#!/bin/bash

# Install fswebcam
sudo apt-get install fswebcam

# Install Avahi Daemon
sudo apt-get install avahi-daemon

# Configure Avahi Daemon
sudo sed -i 's/#host-name=.*$/host-name=bunkermessungai/' /etc/avahi/avahi-daemon.conf

# Restart Avahi Daemon
sudo systemctl restart avahi-daemon

# Install required Python packages
pip install Flask requests

echo "Installation completed successfully."
