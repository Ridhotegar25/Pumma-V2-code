#!/home/pi/code/envPumma/bin/python3

import serial
import os
from datetime import datetime

port = '/dev/Nano'
BAUDRATE = 9600

def connect_serial():
    try:
        ser = serial.Serial(port, BAUDRATE, timeout=1)
        ser.flush()
        return ser
    except serial.SerialException as e:
        print("Gagal konek ke serial:", e)
        return None

def read_sensor_once(ser):
    try:
        ser.flushInput()
        line = ser.readline().decode('utf-8').strip().rstrip(',')
        if not line:
            return None
        try:
            data_measur_real = round(float(line) / 100, 2)
            data_measure = round(2.198 - data_measur_real, 2)
            data = round(1 + data_measure, 2)
            return {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "value": data
            }
        except ValueError:
            print(f"Data tidak valid: {line}")
            return None
    except Exception as e:
        print("Error membaca data sensor:", e)
        return None

def save_sensor_data(log_folder, timestamp, value):
    os.makedirs(log_folder, exist_ok=True)
    filename = f"Log_MB{datetime.now().strftime('%d-%m-%Y')}.txt"
    path = os.path.join(log_folder, filename)
    with open(path, 'a') as f:
        f.write(f"{timestamp}, ,{value}\n")  # Format dengan kolom ke-3
