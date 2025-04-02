#!/home/pi/code/envPumma/bin/python3

import time
from lps28dfw import LPS28DFW, LPS28DFW_OK, LPS28DFW_10Hz  # Import necessary constants

# Create sensor object
sensor = LPS28DFW()

# Initialize sensor
if sensor.begin() != LPS28DFW_OK:
    print("Failed to initialize sensor!")
    exit()

# Configure sensor
config = {
    'odr': LPS28DFW_10Hz,  # 10 Hz output data rate
    'avg': 0x00            # No averaging
}
sensor.set_mode_config(config)

# Main loop
while True:
    if sensor.get_sensor_data() == LPS28DFW_OK:
        print(f"Pressure: {sensor.data['pressure']:.2f} hPa")
        print(f"Temperature: {sensor.data['temperature']:.2f} °C")
    time.sleep(1)
