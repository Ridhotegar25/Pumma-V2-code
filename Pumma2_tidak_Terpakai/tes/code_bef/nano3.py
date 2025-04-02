#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
import os
from datetime import datetime
import multiprocessing
import psutil
import select

# Konfigurasi Serial
SERIAL_PORT = '/dev/Nano'  # Pastikan ini sesuai dengan aturan udev
BAUD_RATE = 115200
MAX_RETRIES = 5
RECONNECT_INTERVAL = 2  # Jeda waktu reconnect jika gagal

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# Global variables untuk multiproses
data_queue = multiprocessing.Queue()

def init_serial():
    """Membuka koneksi serial dengan retry jika gagal."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1, exclusive=True)
            print("Serial connected on", SERIAL_PORT)
            return ser
        except serial.SerialException as e:
            print(f"Serial connection failed ({e}), retrying in {RECONNECT_INTERVAL} seconds...")
            retries += 1
            time.sleep(RECONNECT_INTERVAL)
    print("Serial connection failed after retries. Skipping serial init.")
    return None

def mqtt_connect():
    """Menghubungkan ke broker MQTT dan menjalankan loop."""
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker")
        else:
            print(f"Failed to connect to MQTT, return code {rc}. Retrying...")

    def on_disconnect(client, userdata, rc):
        print("MQTT Disconnected. Attempting to reconnect...")
        while True:
            try:
                client.reconnect()
                print("Reconnected to MQTT Broker")
                break
            except:
                print("Reconnection failed. Retrying in 5 seconds...")
                time.sleep(5)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    
    return client

def save_log(ts_nano, maxbotic1):
    """Menyimpan data ke dalam file log."""
    date_str = datetime.now().strftime("%d-%m-%Y")
    file_path = f"/home/pi/Data/Log_maxbo/Log_MB{date_str}.txt"
    with open(file_path, "a") as file:
        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{ts_nano},{maxbotic1}\n")

def process_data(data_queue):
    """Memproses data dari serial dan mengirim ke MQTT."""
    client = mqtt_connect()
    last_send_time = time.time()
    
    while True:
        try:
            if not data_queue.empty():
                data = data_queue.get()
                
                ts_nano = data.get("TS_Nano", "")
                air_pres = float(data.get("Air_Pres", 0.0))
                maxbotic_1 = float(data.get("Maxbotic1", 0))
                maxbotic1 = 4.0 - (maxbotic_1 / 100)
                
                current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_data = {
                    "TS": current_timestamp,
                    "TS_Nano": ts_nano,
                    "air_pressure": air_pres,
                    "maxbotic1": maxbotic1
                }

                # Publish data setiap 1 detik
                if time.time() - last_send_time >= 1:
                    client.publish(MQTT_TOPIC, json.dumps(new_data), qos=1)
                    last_send_time = time.time()
                    save_log(ts_nano, maxbotic1)
                    print("Data sent:", new_data)
            time.sleep(0.1)
        except Exception as e:
            print("Error in process_data:", e)
            time.sleep(1)

def read_serial(data_queue):
    """Membaca data dari serial tanpa blocking dan mengirim ke queue."""
    ser = init_serial()
    
    while True:
        if ser and ser.is_open:
            try:
                readable, _, _ = select.select([ser], [], [], 1)  # Tunggu data tanpa blocking
                if readable:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            print("Serial Data Received:", data)  # Debug
                            data_queue.put(data)  # Kirim ke antrian untuk diproses
                        except json.JSONDecodeError:
                            print("Error decoding JSON line:", line)
            except (serial.SerialException, OSError):
                print("Serial read error. Reinitializing connection...")
                ser.close()
                ser = init_serial()
        else:
            print("Serial port is closed. Reconnecting...")
            ser = init_serial()
        time.sleep(0.1)

if __name__ == "__main__":
    # Menetapkan prioritas proses ke low
    try:
        psutil.Process().nice(10)  # Prioritas rendah agar tidak membebani CPU
    except ImportError:
        pass
    
    # Buat proses terpisah untuk membaca serial
    serial_process = multiprocessing.Process(target=read_serial, args=(data_queue,))
    serial_process.daemon = True
    serial_process.start()

    # Buat proses terpisah untuk memproses data
    processing_process = multiprocessing.Process(target=process_data, args=(data_queue,))
    processing_process.daemon = True
    processing_process.start()

    # Loop utama untuk menjaga program tetap berjalan
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
