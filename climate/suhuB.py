#!/home/pi/code/envPumma/bin/python3

import os
import glob
import time

# These two lines mount the device:
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
try:
    # Get all the filenames begin with 28 in the path base_dir.
    device_folder = glob.glob(base_dir + '28-00000f9e11ee')[0] 
    device_file = device_folder + '/w1_slave'
except IndexError:
    device_folder = None
    device_file = None

def read_rom():
    if not device_folder:
        return None
    try:
        name_file = device_folder + '/name'
        with open(name_file, 'r') as f:
            return f.readline().strip()
    except Exception:
        return None

def read_temp_raw():
    if not device_file:
        return None
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        return lines
    except Exception:
        return None

def read_temp():
    try:
        lines = read_temp_raw()
        if lines is None:
            return None
        # Analyze if the last 3 characters are 'YES'.
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(1)
            lines = read_temp_raw()
            if lines is None:
                return None
        # Find the index of 't=' in a string.
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            # Read the temperature.
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            return temp_c
    except Exception:
        return None

#while True:
temp = read_temp()
if temp is not None:
    print(f"{temp:.2f}")
else:
    print("Error reading temperature")
time.sleep(4)
