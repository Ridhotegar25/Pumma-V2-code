#!/home/pi/code/envPumma/bin/python3

import serial
import time
import os
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# Konfigurasi Serial
port = '/dev/Nano'
baudrate = 9600

# Konfigurasi MQTT
MQTT_BROKER = ""  # Ganti dengan broker MQTT yang digunakan
MQTT_PORT = 1883
MQTT_TOPIC = ""
MQTT_USERNAME = ""  # Ganti dengan username MQTT
MQTT_PASSWORD = ""  # Ganti dengan password MQTT

# Fungsi untuk menghubungkan ke serial
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

# Fungsi untuk menghubungkan ke MQTT
def connect_mqtt():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("Connected to MQTT Broker")
    except Exception as e:
        print(f"Failed to connect to MQTT Broker: {e}")
    
    return client

# Fungsi utama
def main():
    ser = connect_serial(port, baudrate)
    mqtt_client = connect_mqtt()
    
    folder_path = "/home/pi/Data/Log_maxbo"
    os.makedirs(folder_path, exist_ok=True)
    
    while True:
        try:
            ser.flushInput()  # Bersihkan buffer input sebelum membaca
            data1 = ser.readline().decode('utf-8').strip().rstrip(',')  # Hapus koma di akhir
            
            # Pastikan data yang diterima valid
            try:
                data_measur_real = round(float(data1) / 100, 2)  # Konversi ke float sebelum operasi matematika
                data_measure = round(2.198 - data_measur_real, 2)
                data = round(1 + data_measure, 2)
            except ValueError:
                print(f"Invalid data received: {data1}")
                continue  # Skip iterasi jika data tidak valid
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            filename = f"Log_MB{datetime.now().strftime('%d-%m-%Y')}.txt"
            file_path = os.path.join(folder_path, filename)
            
            # Simpan ke log file
            with open(file_path, 'a') as file:
                file.write(f"{timestamp}, {data}\n")
            
            # Format JSON untuk MQTT
            payload = {
                "TS": timestamp,
                "TS_Nano":timestamp,
                "maxbotic2": data
            }
            payload_json = json.dumps(payload)
            
            # Kirim data ke MQTT
            try:
                mqtt_client.publish(MQTT_TOPIC, payload_json)
                print(f"MQTT Published: {payload_json}")
            except Exception as e:
                print(f"MQTT Publish Error: {e}")
                mqtt_client = connect_mqtt()  # Reconnect jika gagal
            
            print(f"Data real: {data_measur_real}, Data Measure : {data_measure}")
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
