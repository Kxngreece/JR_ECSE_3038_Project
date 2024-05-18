This repository contains the code for an IoT Smart Home System that can monitor temperature, presence, and control connected devices like fans and lights based on user preferences and sensor data.

API server code (Python):
models.py: Defines data models for user settings (Settings), sensor data (sensors), and API responses (updatedSettings).
main.py: Implements the FastAPI application with functionalities like:
get_data (GET /graph): Retrieves sensor data from the database.
update_settings (PUT /settings): Updates user settings for temperature and light turn-on time. It also calculates the light turn-off time based on user-specified duration and sunset.
createSensors (POST /sensors): Creates a new entry in the database for received sensor data.
get_device_states (GET /sensors): Retrieves the desired on/off state for fan and light based on current sensor data and user preferences (currently a simplified logic).
turn_on_components (GET /sensors): Determines the desired on/off state for fan and light based on more comprehensive logic, considering presence, temperature, user settings, and previous light states.