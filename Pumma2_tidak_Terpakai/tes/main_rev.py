#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
import os
from datetime import datetime
import threading

# Konfigurasi Serial
SERIAL_PORT = '/dev/Nano'
BAUD_RATE = 115200
MAX_RETRIES = 5  

# Konfigurasi MQTT
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"

# Global variables
ser = None
client = None
last_send_time = 0
event_stop = threading.Event()
lock = threading.Lock()

def init_serial():
    """Inisialisasi koneksi serial dengan retry jika gagal."""
    retries = MAX_RETRIES
    while retries:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("Serial connected")
            return ser
        except serial.SerialException:
            print("Failed to connect to serial, retrying...")
            retries -= 1
            time.sleep(5)
    print("Serial connection failed after retries. Rebooting...")
    os.system("sudo systemctl restart ardunano.service")
    return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
    else:
        print(f"Failed to connect to MQTT, return code {rc}")

def mqtt_loop():
    """Loop MQTT yang berjalan di thread terpisah."""
    global client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

def save_log(ts_human, ts_current, maxbotic1):
    """Simpan data ke log file."""
    date_str = datetime.now().strftime("%d-%m-%Y")
    file_path = f"/home/pi/Data/Log_maxbo/Log_MB{date_str}.txt"
    with open(file_path, "a") as file:
        file.write(f"{ts_human},{ts_current},{maxbotic1}\n")

def process_data(data):
    """Proses dan kirim data ke MQTT."""
    global last_send_time

    try:
        ts_nano = data.get("TS_Nano", 0)
        maxbotic_1 = float(data.get("Maxbotic1", 0.0))
        maxbotic_2 = float(data.get("Maxbotic2", 0))

        maxbotic1 = round(4.0 - (maxbotic_1 / 100), 2)
        maxbotic2 = round(4.0 - (maxbotic_2 / 100), 2)

        ts_human = datetime.utcfromtimestamp(ts_nano).strftime('%Y-%m-%d %H:%M:%S')
        ts_current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        new_data = {
            "TS": ts_current,
            "TS_Nano": ts_human,
            "maxbotic2": maxbotic2
        }

        with lock:
            if time.time() - last_send_time >= 1:
                client.publish(MQTT_TOPIC, json.dumps(new_data), qos=1)
                last_send_time = time.time()
                save_log(ts_human, ts_current, maxbotic1)
                print("Data sent:", new_data)

    except (ValueError, TypeError, KeyError) as e:
        print(f"Error processing data: {e}")

def read_serial():
    """Membaca data dari serial port setiap 1 detik."""
    global ser
    buffer = ""
    
    while not event_stop.is_set():
        try:
            chunk = ser.readline().decode('utf-8', errors='ignore').strip()
            if chunk:
                buffer += chunk
                if buffer.startswith("{") and buffer.endswith("}"):
                    try:
                        data = json.loads(buffer)
                        process_data(data)
                        buffer = ""
                    except json.JSONDecodeError:
                        print(f"JSON Decode Error: {buffer}")
                        buffer = ""
                elif len(buffer) > 700:
                    print("Buffer terlalu panjang, reset...")
                    buffer = ""

        except serial.SerialException:
            print("Serial read error. Reinitializing connection...")
            ser.close()
            ser = init_serial()

        time.sleep(1)  # Jeda 1 detik agar pembacaan tetap stabil

def check_serial_timeout():
    """Memeriksa apakah koneksi serial masih aktif, jika tidak restart."""
    global ser
    while not event_stop.is_set():
        try:
            ser.write(b'\n')
            time.sleep(1)
            if ser.in_waiting == 0:
                print("No data received, restarting serial connection...")
                ser.close()
                ser = init_serial()
        except serial.SerialException:
            print("Serial connection error. Reinitializing...")
            ser.close()
            ser = init_serial()
        time.sleep(5)

if __name__ == "__main__":
    ser = init_serial()
    
    mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
    serial_thread = threading.Thread(target=read_serial, daemon=True)
    timeout_thread = threading.Thread(target=check_serial_timeout, daemon=True)
    
    mqtt_thread.start()
    serial_thread.start()
    timeout_thread.start()
    
    try:
        while True:
            time.sleep(1)  # Pastikan loop utama berjalan dengan stabil
    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
        event_stop.set()
        if ser:
            ser.close()
        client.disconnect()
