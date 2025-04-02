#!/home/pi/code/envPumma/bin/python3

import minimalmodbus
import time
import os
import psutil
import threading
from datetime import datetime

# Lock untuk menghindari konflik antar proses yang mengakses port serial
serial_lock = threading.Lock()

# Konfigurasi port serial dan perangkat
def create_instrument():
    instrument = minimalmodbus.Instrument('/dev/Water_Press', 1)  # Port serial dan Unit ID
    instrument.serial.baudrate = 9600
    instrument.serial.bytesize = 8
    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 1  # Timeout dalam detik
    instrument.mode = minimalmodbus.MODE_RTU
    return instrument

# Parameter komunikasi
ADDRESS = 2  # Alamat register pertama
NUM_REGISTERS = 10  # Jumlah register yang akan dibaca

# Path untuk menyimpan log
LOG_DIR = "/home/pi/Data/LogSeaWater"
LOG_RAW = "/home/pi/Data/Raw_WP"
os.makedirs(LOG_DIR, exist_ok=True)  # Pastikan folder log ada

# Fungsi untuk mendapatkan nama file log berdasarkan tanggal saat ini
def get_log_filename():
    date_str = datetime.now().strftime("%d-%m-%Y")
    return os.path.join(LOG_DIR, f"Log_WP {date_str}.txt")

def get_log_filename1():
    date_str = datetime.now().strftime("%d-%m-%Y")
    return os.path.join(LOG_RAW, f"Raw_WP {date_str}.txt")

# Fungsi untuk mencatat data ke file log
def log_data(water_level_pressure):
    try:
        with open(get_log_filename(), "a") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp}, {water_level_pressure}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def raw_data(MPa,kPa,water_level_pressure,bar,mbar,kg_cm2,psi,mH2O,mmH2O,celcius):
    try:
        with open(get_log_filename1(), "a") as log_file:
            timestamp1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp1}{MPa},{kPa},{water_level_pressure},{bar},{mbar},{kg_cm2},{psi},{mH2O},{mmH2O},{celcius}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

# Fungsi untuk membaca data Modbus
def read_modbus_data(instrument):
    try:
        with serial_lock:  # Gunakan lock agar tidak ada proses lain yang mengakses port secara bersamaan
            instrument.serial.reset_input_buffer()
            instrument.serial.reset_output_buffer()
            
            response = instrument.read_registers(ADDRESS, NUM_REGISTERS, functioncode=3)
            
            if len(response) >= 9:
                MPa = response[0]
                kPa = response[1]
                Pa = response[2]
                water_level_pressure = Pa /100 
                bar = response[3]
                mbar = response[4]
                kg_cm2 = response[5]
                psi = response[6]
                mH2O = response[7]
                mmH2O = response[8]
                celcius = response[9]

                # Jika nilai terbaca lebih dari 65000, set ke 0
                if response[2] > 65000:
                    water_level_pressure = 0
                
                log_data(water_level_pressure)  # Simpan ke file log
                raw_data(MPa,kPa,water_level_pressure,bar,mbar,kg_cm2,psi,mH2O,mmH2O,celcius)
                print(f"Water_Level_Pressure: {water_level_pressure}")
                print(f"Data WP: {MPa},{kPa},{water_level_pressure},{bar},{mbar},{kg_cm2},{psi},{mH2O},{mmH2O},{celcius}")
                return MPa,kPa,Pa,water_level_pressure,bar,mbar,kg_cm2,psi,mH2O,mmH2O,celcius  # Return nilai untuk digunakan di main.py
            else:
                print("Response data is incomplete.")
                return None
    except Exception as e:
        print(f"Error reading Modbus data: {e}")
        return None

# Fungsi untuk membaca data sensor
def get_sensor_data():
    instrument = None
    try:
        instrument = create_instrument()
        print("Reading Modbus RTU data...")

        for _ in range(3):  # Coba membaca hingga 3 kali jika gagal
            water_level_pressure = read_modbus_data(instrument)
            if water_level_pressure is not None:
                return water_level_pressure
            time.sleep(1)  # Tunggu sebelum mencoba lagi
        
        return None  # Jika masih gagal setelah 3 kali percobaan
    except Exception as e:
        print(f"Error in get_sensor_data: {e}")
        return None
    finally:
        if instrument and instrument.serial.is_open:
            instrument.serial.close()  # Tutup port serial dengan benar
            print("Serial port closed.")

if __name__ == "__main__":
#    try:
#        psutil.Process().nice(-10)  # Prioritas lebih tinggi (nilai lebih rendah = prioritas tinggi)
#    except Exception as e:
#        print(f"Error setting process priority: {e}")
    
#    print("Starting sensor data collection...")
    
    while True:
        water_level_pressure = get_sensor_data()
        
        if water_level_pressure is None:
            print("Data reading failed, retrying...")
            time.sleep(1.5)  # Tunggu lebih lama jika terjadi kegagalan
        else:
            time.sleep(1)  # Interval pembacaan data sensor yang stabil
