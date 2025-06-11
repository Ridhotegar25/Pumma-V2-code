#!/home/pi/code/envPumma/bin/python3

import minimalmodbus
import time
import os
import psutil
import threading
from datetime import datetime
import fcntl  # Untuk locking file

# Lock untuk menghindari konflik antar proses yang mengakses port serial
serial_lock = threading.Lock()

def create_instrument():
    instrument = minimalmodbus.Instrument('/dev/Water_Press', 1)
    instrument.serial.baudrate = 9600
    instrument.serial.bytesize = 8
    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 1
    instrument.mode = minimalmodbus.MODE_RTU
    return instrument

ADDRESS = 2
NUM_REGISTERS = 10

LOG_DIR = "/home/pi/Data/LogSeaWater"
LOG_RAW = "/home/pi/Data/Raw_WP"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(LOG_RAW, exist_ok=True)

def get_log_filename():
    date_str = datetime.now().strftime("%d-%m-%Y")
    return os.path.join(LOG_DIR, f"Log_WP {date_str}.txt")

def get_log_filename1():
    date_str = datetime.now().strftime("%d-%m-%Y")
    return os.path.join(LOG_RAW, f"Raw_WP {date_str}.txt")

_last_log_time = None

def log_data(water_level_pressure):
    global _last_log_time
    try:
        now = datetime.now()
        if _last_log_time and (now - _last_log_time).total_seconds() < 1:
            return  # Hindari duplikasi akibat pemanggilan berdekatan
        _last_log_time = now

        filepath = get_log_filename()
        with open(filepath, "a") as log_file:
            fcntl.flock(log_file, fcntl.LOCK_EX)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp}, {water_level_pressure}\n")
            fcntl.flock(log_file, fcntl.LOCK_UN)
    except Exception as e:
        print(f"Error writing to log file: {e}")

def raw_data(MPa, kPa, water_level_pressure, bar, mbar, kg_cm2, psi, mH2O, mmH2O, celcius):
    try:
        filepath = get_log_filename1()
        with open(filepath, "a") as log_file:
            fcntl.flock(log_file, fcntl.LOCK_EX)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp},{MPa},{kPa},{water_level_pressure},{bar},{mbar},{kg_cm2},{psi},{mH2O},{mmH2O},{celcius}\n")
            fcntl.flock(log_file, fcntl.LOCK_UN)
    except Exception as e:
        print(f"Error writing to log file: {e}")

def read_modbus_data(instrument):
    try:
        with serial_lock:
            instrument.serial.reset_input_buffer()
            instrument.serial.reset_output_buffer()

            response = instrument.read_registers(ADDRESS, NUM_REGISTERS, functioncode=3)
            if len(response) >= 9:
                MPa = response[0]
                kPa = response[1]
                Pa = response[2]
                water_level_pressure = Pa / 100
                bar = response[3]
                mbar = response[4]
                kg_cm2 = response[5]
                psi = response[6]
                mH2O = response[7]
                mmH2O = response[8]
                celcius = response[9]

                if response[2] > 65000:
                    water_level_pressure = 0

                log_data(water_level_pressure)
                raw_data(MPa, kPa, water_level_pressure, bar, mbar, kg_cm2, psi, mH2O, mmH2O, celcius)
                print(f"Water_Level_Pressure: {water_level_pressure}")
                return MPa, kPa, Pa, water_level_pressure, bar, mbar, kg_cm2, psi, mH2O, mmH2O, celcius
            else:
                print("Response data is incomplete.")
                return None
    except Exception as e:
        print(f"Error reading Modbus data: {e}")
        return None

def get_sensor_data():
    instrument = None
    try:
        instrument = create_instrument()
        print("Reading Modbus RTU data...")

        for _ in range(3):
            water_level_pressure = read_modbus_data(instrument)
            if water_level_pressure is not None:
                return water_level_pressure
            time.sleep(1)
        return None
    except Exception as e:
        print(f"Error in get_sensor_data: {e}")
        return None
    finally:
        if instrument and instrument.serial.is_open:
            instrument.serial.close()
            print("Serial port closed.")

# Hindari menjalankan loop saat di-import
if __name__ == "__main__":
    print("readWP.py dijalankan langsung — tidak disarankan jika dipakai oleh main.py.")
    while True:
        data = get_sensor_data()
        if data is None:
            print("Data reading failed, retrying...")
            time.sleep(1.5)
        else:
            time.sleep(1)
