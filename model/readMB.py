#!/home/pi/code/envPumma/bin/python3

import serial
import time
import os
from datetime import datetime

port = '/dev/Nano'

def connect_serial(port, baudrate=9600):
    while True:
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            ser.flush()  # Bersihkan buffer input
            print("Connected to Arduino on", port)
            return ser
        except serial.SerialException:
            print("Failed to connect. Retrying...")
            time.sleep(5)  # Coba lagi setelah 5 detik

def main():
    ser = connect_serial(port)
    
    folder_path = "/home/pi/Data/Log_maxbo"
    os.makedirs(folder_path, exist_ok=True)
    
    while True:
        try:
            ser.flushInput()  # Bersihkan buffer input sebelum membaca
            data1 = ser.readline().decode('utf-8').strip().rstrip(',')  # Hapus koma di akhir
            
            # Pastikan data yang diterima valid
            try:
                data_measur_real = round(float(data1) / 100, 2)  # Konversi ke float sebelum operasi matematika
                data_measure = round(2.198 - data_measur_real,2)
                data = round(1 + data_measure,2)
            except ValueError:
                print(f"Invalid data received: {data1}")
                continue  # Skip iterasi jika data tidak valid
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            filename = f"Log_MB{datetime.now().strftime('%d-%m-%Y')}.txt"
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'a') as file:
                file.write(f"{timestamp}, {data}\n")
            
            print(f"Data real: {data_measur_real},Data Measure : {data_measure}")
            print(f"Saved: {timestamp}, {data}")
            
            time.sleep(1)  # Interval 1 detik
        
        except serial.SerialException:
            print("Serial connection lost. Reconnecting...")
            ser = connect_serial(port)
        except Exception as e:
            print("Error:", e)
            time.sleep(1)

if __name__ == "__main__":
    main()
