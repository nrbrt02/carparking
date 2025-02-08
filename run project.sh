#!/bin/bash

# Change to the directory where your Python project is located
# cd "carparking"

# Activate the virtual environment
source venv/Scripts/activate

# Run your Python project
python manage.py runserver

# Deactivate the virtual environment after the project completes
deactivate

# Wait for user input before closing the window
read -p "Press [Enter] key to exit..."
