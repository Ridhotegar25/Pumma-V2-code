#!/home/pi/code/envPumma/bin/python3

import serial
import json
import paho.mqtt.client as mqtt
import time
import os
from datetime import datetime
import threading
import psutil

# Konfigurasi
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
MQTT_BROKER = "vps.isi-net.org"
MQTT_PORT = 1883
MQTT_TOPIC = "Pumma/Sebesi_serial"
MQTT_USER = "unila"
MQTT_PASSWORD = "pwdMQTT@123"
LOG_DIR = "/home/pi/Data/Log_maxbo/"

# Variabel global
ser = None
client = None
last_send_time = 0
event_stop = threading.Event()

# Inisialisasi Serial
def init_serial():
    for _ in range(5):
        try:
            return serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        except serial.SerialException:
            print("Gagal koneksi serial, retrying...")
            time.sleep(5)
    os.system("sudo systemctl restart ardunano.service")
    return None

# MQTT Callback
def on_connect(client, userdata, flags, rc):
    print("MQTT Connected" if rc == 0 else f"MQTT Failed {rc}")

def on_disconnect(client, userdata, rc):
    print("MQTT Disconnected, Reconnecting...")
    while not event_stop.is_set():
        try:
            client.reconnect()
            print("MQTT Reconnected")
            break
        except:
            time.sleep(5)

# MQTT Loop
def mqtt_loop():
    global client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# Simpan Log
def save_log(ts_human, ts_current, maxbotic1):
    file_path = f"{LOG_DIR}Log_MB{datetime.now().strftime('%d-%m-%Y')}.txt"
    with open(file_path, "a") as file:
        file.write(f"{ts_human},{ts_current},{maxbotic1}\n")

# Proses Data
def process_data(data):
    global last_send_time
    try:
        ts_nano = data.get("TS_Nano", 0)
        maxbotic1 = 4.0 - (float(data.get("Maxbotic1", 0)) / 100)
        maxbotic2 = 4.0 - (float(data.get("Maxbotic2", 0)) / 100)
        ts_human = datetime.utcfromtimestamp(ts_nano).strftime('%Y-%m-%d %H:%M:%S')
        ts_current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payload = json.dumps({"TS": ts_current, "TS_Nano": ts_human, "maxbotic1": maxbotic1, "maxbotic2": maxbotic2})

        if time.time() - last_send_time >= 1:
            client.publish(MQTT_TOPIC, payload, qos=1)
            last_send_time = time.time()
            save_log(ts_human, ts_current, maxbotic1)
            print("Data sent:", payload)
    except Exception as e:
        print("Error processing data:", e)

# Baca Serial
def read_serial():
    global ser
    buffer = ""
    while not event_stop.is_set():
        try:
            chunk = ser.readline().decode('utf-8', errors='ignore').strip()
            if chunk:
                buffer += chunk
                if buffer.startswith("{") and buffer.endswith("}"):
                    try:
                        process_data(json.loads(buffer))
                    except json.JSONDecodeError:
                        print("Invalid JSON:", buffer)
                    buffer = ""
                elif len(buffer) > 500:
                    buffer = ""
        except serial.SerialException:
            ser.close()
            ser = init_serial()
        time.sleep(0.05)

# Cek Timeout Serial
def check_serial_timeout():
    global ser
    while not event_stop.is_set():
        try:
            ser.write(b'\n')
            time.sleep(1)
            if ser.in_waiting == 0:
                ser.close()
                ser = init_serial()
        except serial.SerialException:
            ser.close()
            ser = init_serial()
        time.sleep(10)

if __name__ == "__main__":
    try:
        psutil.Process().nice(10)
    except Exception as e:
        print("Failed to set priority:", e)

    ser = init_serial()
    threading.Thread(target=mqtt_loop, daemon=True).start()
    threading.Thread(target=read_serial, daemon=True).start()
    threading.Thread(target=check_serial_timeout, daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        event_stop.set()
        if ser:
            ser.close()
        client.disconnect()
