#!/bin/bash
# Activate the virtual environment and run the Flask application

# Absolute path to your virtual environment's activate script
source /path/to/your/venv/bin/activate

# Change directory to your project's base directory
cd /root/traffic_monitor

# Run the Flask application
exec python app.py

